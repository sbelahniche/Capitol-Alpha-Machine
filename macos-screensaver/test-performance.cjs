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
const gpuCanvas = fs.readFileSync(path.join(__dirname, 'gpu-canvas.js'), 'utf8');

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
  assert.ok(frames.length >= 60 && frames.length <= 62, '120Hz display delivers 60 rendered frames/sec');
  for (const hz of [60, 120, 144, 59.94]) {
    message('cam:pause'); message('cam:play');
    const start = frames.length;
    for (let i=0;i<hz*5;i++) tick(2000+i*1000/hz+(i%3)*0.15);
    assert.ok(frames.length-start >= 298 && frames.length-start <= 301, 'stable 60fps cadence at '+hz+'Hz');
  }
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
  const nativeFrame = fn => {standaloneQueue.set(++next,fn);return next;};
  const native = vm.createContext({document:standaloneDoc, requestAnimationFrame:nativeFrame,
    cancelAnimationFrame(id) {standaloneQueue.delete(id);},addEventListener() {}});
  native.window=native;native.parent=native;
  vm.runInContext(runtime.replace('__CAPITOL_PREVIEW__', 'false'), native);
  assert.equal(native.requestAnimationFrame, nativeFrame, 'native savers use WebKit frame cadence without a pacing layer');
  native.requestAnimationFrame(() => {});
  assert.equal(standaloneQueue.size,1,'native saver keeps running in an occluded macOS host');
  console.log('Scheduler: preview 60fps pacing, paused/hidden idle, resume clock, cancellation and message provenance passed; native uses vsync cadence.');
}

function sceneContext(html, width, height) {
  let calls = [], measurements = 0, saves = 0, state = {globalAlpha:1}, stack = [], seed = 123;
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
  let rasterizedLabels = 0, imageDraws = 0;
  ctx.drawImage = (atlas,sx,sy,sw,sh,x,y) => {
    imageDraws++;
    const glyph=atlas.glyphs[Math.round(sy/sh)*(atlas.width/sw)+Math.round(sx/sw)];
    // Compare semantic placement/color with the original text commands.
    // Pixel equivalence is deliberately not asserted for cached glyphs.
    const alpha=ctx.globalAlpha;ctx.globalAlpha=1;
    ctx.fillText(glyph[0],x+2,y+20,glyph[3]);ctx.globalAlpha=alpha;
  };
  const createElement = () => {
    const atlas={glyphs:[],getContext() {return {
      scale() {}, measureText:ctx.measureText,
      fillText(...args) {rasterizedLabels++;atlas.glyphs.push(args);}
    };}};
    return atlas;
  };
  const canvas = {parentElement:{getBoundingClientRect() {return {width,height};}},getContext() {return ctx;}};
  const math = Object.create(Math);
  math.random = () => ((seed = (1664525*seed+1013904223)>>>0)/4294967296);
  const context = vm.createContext({Math:math, document:{createElement, getElementById() {return canvas;}},
    devicePixelRatio:2, requestAnimationFrame() {return 1;},cancelAnimationFrame() {}, addEventListener() {}});
  context.window = context;
  context.parent = context;
  vm.runInContext(runtime.replace('__CAPITOL_PREVIEW__','false'),context);
  // No WebGL2 here, so native scenes take the CPU canvas fallback.
  vm.runInContext(gpuCanvas,context);
  vm.runInContext(bundle, context);
  // Native exports retain placeholders until the host inserts the data.
  html = html.replace(/window\.__CAPITOL_TRADES_(SCENE\d+)__/g, 'window.CAPITOL_TRADES_$1');
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
  vm.runInContext(scripts.at(-1)[1]+'\nglobalThis.render=frame;', context);
  return {context, canvas, render(t) {calls=[];context.render(t);return calls;},
    stats() {return {measurements,saves,rasterizedLabels,imageDraws};}};
}

// Exercise the actual atlas allocation and alpha restoration separately from
// the semantic draw recorder (which is not a raster comparison).
function atlasTest() {
  const atlases=[];
  const context=vm.createContext({requestAnimationFrame() {},cancelAnimationFrame() {},
    document:{createElement() {const canvas={getContext(){return {scale(){},measureText(t){return {width:t.length*6};},fillText(){}};}};atlases.push(canvas);return canvas;}}});
  context.window=context;context.parent=context;
  vm.runInContext(runtime.replace('__CAPITOL_PREVIEW__','false'),context);
  for(const count of [0,1,641,10000]) {
    const atlas=context.__capitolCreateLabelAtlas(Array(count).fill('AAPL'),'11px monospace',163,2);
    const canvas=atlases.at(-1);
    assert.ok(canvas.width*canvas.height<=4000000,'atlas respects rounded pixel budget');
    if(count) {
      let opacity;
      const ctx={globalAlpha:.5,drawImage(){opacity=this.globalAlpha;}};
      atlas.draw(ctx,0,12,30,.32);
      assert.equal(opacity,.16);assert.equal(ctx.globalAlpha,.5,'drawing restores alpha');
    }
  }
  console.log('Atlas: bounded allocation and opacity restoration passed.');
}
// Without WebGL2 the GPU module must hand back the CPU canvas unchanged
// in behavior: cached measurements and the four-million-pixel budget.
function gpuFallbackTest() {
  const ctx={measureText(t){return {width:t.length}}}, requested=[];
  const canvas={getContext(type,options){requested.push([type,options]);return type==='2d'?ctx:null;}};
  const context=vm.createContext({devicePixelRatio:2,document:{createElement(){return {getContext(){return null;}};}}});
  context.window=context;context.parent=context;
  vm.runInContext(runtime.replace('__CAPITOL_PREVIEW__','false'),context);
  vm.runInContext(gpuCanvas,context);
  assert.equal(context.__capitolContext(canvas),ctx,'falls back to the 2D canvas');
  assert.deepEqual(JSON.parse(JSON.stringify(requested)),[['2d',{alpha:false}]],'fallback uses an opaque 2D canvas');
  assert.ok(!context.__capitolGPU,'GPU flag stays off');
  assert.ok(Math.abs(context.__capitolDPR(2560,1440)-Math.sqrt(4000000/(2560*1440)))<1e-9,'fallback keeps pixel budget');
  assert.equal(ctx.measureText('AAPL'),ctx.measureText('AAPL'),'fallback caches measurements');
  context.__capitolGPU=true;
  assert.equal(context.__capitolDPR(2560,1440),2,'GPU path renders at full Retina resolution');
  console.log('GPU canvas: CPU fallback, cached text and resolution policy passed.');
}
atlasTest();
gpuFallbackTest();
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
      assert.deepEqual(output.filter(call=>!counter(call)),baseline.filter(call=>!counter(call)),name+' drawing geometry/styles changed at '+width+'px / '+t+'ms');
      if(number!=='02') {
        expectedCount+=Math.min(.05,(t-previousTime)/1000)*(number==='04'?22:70);
        assert.equal(output.find(counter)[1][0],'TRADES '+String(Math.floor(expectedCount)).padStart(4,'0'),'trade counter must accumulate fractional frames');
        previousTime=t;
      }
    }
    if(number==='02') {
      assert.ok(after.stats().imageDraws > 0, 'ledger must reuse rasterized labels');
      const rasterized=after.stats().rasterizedLabels;
      after.render(20100);
      assert.equal(after.stats().rasterizedLabels,rasterized,'steady frames never rerasterize labels');
    }
    assert.ok(Math.floor(after.canvas.width)*Math.floor(after.canvas.height) <= 4000000, 'backing store exceeds pixel budget');
    console.log(name+' '+width+'x'+height+': equivalent scene geometry and styles; '+JSON.stringify({before:before.stats(),after:after.stats()}));
  }
}
