/* Deterministic regression checks for scene output and scheduler lifecycle.
 * The canvas recorder verifies drawing geometry, not GPU timing or pixels. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const index = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const bundle = fs.readFileSync(path.join(root, 'capitoltrades_data.js'), 'utf8');
const runtime = fs.readFileSync(path.join(__dirname, 'runtime.js'), 'utf8');

function schedulerTest() {
  let next = 0;
  const queued = new Map(), events = {}, docEvents = {};
  const parent = {postMessage() {}};
  const doc = {hidden:false, addEventListener(name, fn) { docEvents[name] = fn; }};
  const context = vm.createContext({parent, location:{origin:'https://example.test'}, document:doc,
    requestAnimationFrame(fn) {queued.set(++next, fn); return next;},
    cancelAnimationFrame(id) {queued.delete(id);},
    addEventListener(name, fn) {events[name] = fn;}});
  context.window = context;
  vm.runInContext(runtime.replace('__CAPITOL_PREVIEW__', 'true'), context);
  let frames = [];
  function render(t) {frames.push(t); context.requestAnimationFrame(render);}
  context.requestAnimationFrame(render);
  function tick(t) {const entries = [...queued.values()];queued.clear();entries.forEach(fn => fn(t));}
  function message(data, source = parent, origin = 'https://example.test') {events.message({data, source, origin});}
  tick(0);
  assert.equal(frames.length, 1, 'paused previews paint one still frame');
  assert.equal(queued.size, 0, 'paused previews schedule no background work');
  message('cam:play', {});
  message('cam:play', parent, 'https://attacker.test');
  assert.equal(queued.size, 0, 'untrusted control messages cannot resume a preview');
  message('cam:play');
  for (let i=0;i<=120;i++) tick(i*1000/120);
  assert.ok(frames.length <= 32, '120Hz display is limited to 30 rendered frames/sec');
  message('cam:pause');
  const pausedTime = frames.at(-1), count = frames.length;
  tick(60000);
  assert.equal(frames.length, count);
  message('cam:play');tick(60000);
  assert.equal(frames.at(-1), pausedTime, 'resume excludes time spent paused');
  doc.hidden = true;docEvents.visibilitychange();
  assert.equal(queued.size, 0, 'hidden tabs cancel pending native frames');
  doc.hidden = false;docEvents.visibilitychange();tick(120000);
  assert.equal(frames.at(-1), pausedTime, 'resume excludes time spent hidden');
  message('cam:pause');
  const canceled = context.requestAnimationFrame(() => {throw Error('canceled callback ran');});
  context.cancelAnimationFrame(canceled);
  message('cam:play');tick(120100);
  const standaloneDoc = {hidden:false, addEventListener(name, fn) {this[name]=fn;}};
  const standaloneQueue = new Map();
  const standalone = vm.createContext({document:standaloneDoc, location:{origin:'null'},
    requestAnimationFrame(fn) {standaloneQueue.set(++next,fn);return next;},
    cancelAnimationFrame(id) {standaloneQueue.delete(id);}, addEventListener() {}});
  standalone.window = standalone;standalone.parent = standalone;
  vm.runInContext(runtime.replace('__CAPITOL_PREVIEW__', 'true'), standalone);
  standalone.requestAnimationFrame(() => {});
  assert.equal(standaloneQueue.size,1,'standalone preview starts playing');
  standaloneDoc.hidden=true;standaloneDoc.visibilitychange();
  assert.equal(standaloneQueue.size,0,'standalone preview also sleeps in hidden tabs');
  standaloneDoc.hidden=false;standaloneDoc.visibilitychange();
  assert.equal(standaloneQueue.size,1,'standalone preview resumes when visible');
  standaloneQueue.clear();
  standaloneDoc.hidden=true;
  const native = vm.createContext({document:standaloneDoc,
    requestAnimationFrame(fn) {standaloneQueue.set(++next,fn);return next;},
    cancelAnimationFrame(id) {standaloneQueue.delete(id);},addEventListener() {}});
  native.window=native;native.parent=native;
  vm.runInContext(runtime.replace('__CAPITOL_PREVIEW__', 'false'), native);
  native.requestAnimationFrame(() => {});
  assert.equal(standaloneQueue.size,1,'native saver keeps running in an occluded macOS host');
  console.log('Scheduler: 30fps, paused/hidden idle, resume clock, cancellation and message provenance passed.');
}

function sceneContext(html, width, height) {
  let calls = [], measurements = 0, saves = 0, state = {}, stack = [], seed = 123;
  const properties = ['font','fillStyle','strokeStyle','globalAlpha','textAlign','lineWidth','shadowBlur','shadowColor','globalCompositeOperation'];
  const ctx = {measureText(text) {measurements++; return {width:String(text).length*6};},
    save() {saves++; stack.push({...state});}, restore() {state=stack.pop();},
    setTransform() {}, beginPath() {}, rect() {}, clip() {},
    createLinearGradient() {return {addColorStop() {}};}};
  for (const p of properties) Object.defineProperty(ctx, p, {get() {return state[p];},set(v) {state[p]=v;}});
  for (const method of ['fillRect','strokeRect','fillText','moveTo','lineTo','stroke','arc','fill','translate','rotate']) {
    const relevant = method.startsWith('fill') || method==='fill' ?
      ['fillStyle','globalAlpha','globalCompositeOperation','shadowBlur','shadowColor',...(method==='fillText'?['font','textAlign']:[])] :
      method.startsWith('stroke') ? ['strokeStyle','lineWidth','globalAlpha','globalCompositeOperation'] : [];
    ctx[method] = (...args) => calls.push([method,args.map(v=>typeof v==='number'?Math.round(v*1e8)/1e8:v),Object.fromEntries(relevant.filter(p=>state[p]!==undefined).map(p=>[p,state[p]]))]);
  }
  const canvas = {parentElement:{getBoundingClientRect() {return {width,height};}},getContext() {return ctx;}};
  const math = Object.create(Math);
  math.random = () => ((seed = (1664525*seed+1013904223)>>>0)/4294967296);
  const context = vm.createContext({Math:math, document:{getElementById() {return canvas;}},
    devicePixelRatio:2, requestAnimationFrame() {return 1;},cancelAnimationFrame() {}, addEventListener() {}});
  context.window = context;
  context.parent = context;
  vm.runInContext(runtime.replace('__CAPITOL_PREVIEW__','false'),context);
  vm.runInContext(bundle, context);
  // Native exports retain placeholders until the host inserts the data.
  html = html.replace(/window\.__CAPITOL_TRADES_(SCENE\d+)__/g, 'window.CAPITOL_TRADES_$1');
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
  vm.runInContext(scripts.at(-1)[1]+'\nglobalThis.render=frame;', context);
  return {context, canvas, render(t) {calls=[];context.render(t);return calls;},
    stats() {return {measurements,saves};}};
}

schedulerTest();
for (const [number, name] of [['02','The Ledger'],['04','Returns Spectrum'],['05','Policy Proximity']]) {
  const original=JSON.parse(index.match(new RegExp('<script id="scene'+number+'-html" type="application/json">([\\s\\S]*?)</script>'))[1]);
  const optimized=fs.readFileSync(path.join(root,'build',name+'.saver/Contents/Resources/scene.html'),'utf8');
  for (const [width,height] of [[1512,982],[320,360],[2560,1440]]) {
    const before=sceneContext(original,width,height), after=sceneContext(optimized,width,height);
    let expectedCount=0,previousTime=0;
    for (const t of [0,100,250,1000,2500,4000,6000,8000,12000,20000]) {
      const output=after.render(t),baseline=before.render(t);
      const counter=call=>call[0]==='fillText'&&String(call[1][0]).startsWith('TRADES ');
      assert.deepEqual(output.filter(call=>!counter(call)),baseline.filter(call=>!counter(call)),name+' draw output changed at '+width+'px / '+t+'ms');
      if(number!=='02') {
        expectedCount+=Math.min(.05,(t-previousTime)/1000)*(number==='04'?22:70);
        assert.equal(output.find(counter)[1][0],'TRADES '+String(Math.floor(expectedCount)).padStart(4,'0'),'trade counter must accumulate fractional frames');
        previousTime=t;
      }
    }
    assert.ok(Math.floor(after.canvas.width)*Math.floor(after.canvas.height) <= 4000000, 'backing store exceeds pixel budget');
    console.log(name+' '+width+'x'+height+': identical canvas draw commands; '+JSON.stringify({before:before.stats(),after:after.stats()}));
  }
}
