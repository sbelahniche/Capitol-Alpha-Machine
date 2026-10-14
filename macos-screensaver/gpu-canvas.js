/* GPU canvas for the native screensavers.
 *
 * WebKit rasterizes 2D canvas commands one by one with CoreGraphics on the
 * CPU. The scenes issue 5,000-12,000 commands per frame at full-screen sizes,
 * which drops frames on large or multiple displays. This file implements the
 * subset of CanvasRenderingContext2D the three scenes use on WebGL2: every
 * rect, line and glyph becomes one instance in a buffer, drawn in order with
 * a few GPU draw calls per frame at full Retina resolution.
 *
 * Coverage is computed analytically per pixel (box filter for rects and butt
 * lines, distance for round caps, Gaussian for shadows), so edges match the
 * 2D canvas closely. Glyphs are rasterized once by the real 2D canvas at
 * device size and reused from an atlas; text shadows are blurred on the GPU
 * from the same glyphs.
 *
 * Text placement: static text snaps exactly like the 2D canvas so it stays
 * crisp. Text the scene marks as moving (ctx.capitolMovingText) is placed at
 * 1/4-pixel horizontal and 1/8-pixel vertical precision, so slowly scrolling
 * labels glide instead of stepping 1-2-1-1-2 whole pixels per frame.
 *
 * If WebGL2 is unavailable, __capitolContext returns the normal 2D context
 * and the scene keeps its existing CPU path. */
(() => {
  'use strict';
  const FLOATS = 20, MAX_INSTANCES = 16384, ATLAS = 2048, STAGE = 1024, INF = 1e6;
  const K_RECT = 0, K_ROUND = 1, K_MASK = 2, K_SOFT = 3, K_IMAGE = 4, K_GLOW = 5;
  const NO_CLIP = [-INF, -INF, INF, INF];

  const INSTANCE_VS = `#version 300 es
layout(location=0) in vec2 a_corner;
layout(location=1) in vec4 a_ou;
layout(location=2) in vec4 a_vk;
layout(location=3) in vec4 a_color;
layout(location=4) in vec4 a_clip;
layout(location=5) in vec4 a_uv;
uniform vec2 u_res;
out vec2 v_loc; out vec2 v_dev; out vec2 v_uv;
flat out vec2 v_size; flat out vec4 v_color; flat out vec4 v_clip; flat out vec2 v_ks; flat out vec4 v_uvr;
void main(){
  vec2 U=a_ou.zw, V=a_vk.xy;
  float lu=length(U), lv=length(V), kind=a_vk.z, sigma=a_vk.w;
  vec2 du=lu>0.0?U/lu:vec2(1.0,0.0), dv=lv>0.0?V/lv:vec2(0.0,1.0);
  float m=(kind==2.0||kind==4.0)?0.0:((kind==3.0||kind==5.0)?ceil(3.0*sigma)+1.0:1.0);
  vec2 l=a_corner*vec2(lu+2.0*m,lv+2.0*m)-m;
  vec2 dev=a_ou.xy+du*l.x+dv*l.y;
  v_loc=l; v_dev=dev; v_size=vec2(lu,lv); v_uv=mix(a_uv.xy,a_uv.zw,a_corner); v_uvr=a_uv;
  v_color=a_color; v_clip=a_clip; v_ks=vec2(kind,sigma);
  gl_Position=vec4(dev.x/u_res.x*2.0-1.0,1.0-dev.y/u_res.y*2.0,0.0,1.0);
}`;
  const COMMON_FS = `#version 300 es
precision highp float;
float cov1(float p,float len){return clamp(min(p+0.5,len)-max(p-0.5,0.0),0.0,1.0);}
float clipCov(vec2 d,vec4 c){return cov1(d.x-c.x,c.z-c.x)*cov1(d.y-c.y,c.w-c.y);}
`;
  const INSTANCE_FS = COMMON_FS + `
in vec2 v_loc; in vec2 v_dev; in vec2 v_uv;
flat in vec2 v_size; flat in vec4 v_color; flat in vec4 v_clip; flat in vec2 v_ks; flat in vec4 v_uvr;
uniform sampler2D u_glyphs; uniform sampler2D u_image;
out vec4 o;
float erf1(float x){float s=sign(x);x=abs(x);float t=1.0/(1.0+0.3275911*x);
  return s*(1.0-(((((1.061405429*t-1.453152027)*t)+1.421413741)*t-0.284496736)*t+0.254829592)*t*exp(-x*x));}
float soft(float p,float len,float s){float k=0.70710678/max(s,1e-3);return 0.5*(erf1((len-p)*k)+erf1(p*k));}
// Gaussian blur of a glyph cell, for text shadows.
float glow(){
  float s=clamp(v_ks.y,0.3,16.0),r=ceil(3.0*s),st=max(1.0,s*0.5),k=-0.5/(s*s),sum=0.0,wsum=0.0;
  for(float y=-r;y<=r;y+=st)for(float x=-r;x<=r;x+=st){
    float g=exp((x*x+y*y)*k);wsum+=g;
    vec2 q=v_loc+vec2(x,y);
    if(q.x>0.0&&q.y>0.0&&q.x<v_size.x&&q.y<v_size.y)sum+=g*textureLod(u_glyphs,mix(v_uvr.xy,v_uvr.zw,q/v_size),0.0).a;
  }
  return sum/wsum;
}
void main(){
  float kind=v_ks.x,c;
  float clip=clipCov(v_dev,v_clip);
  if(kind==4.0){o=textureLod(u_image,v_uv,0.0)*(v_color.a*clip);return;}
  if(kind==0.0)c=cov1(v_loc.x,v_size.x)*cov1(v_loc.y,v_size.y);
  else if(kind==1.0){float hw=v_size.y*0.5,len=max(v_size.x-2.0*hw,0.0);vec2 p=v_loc-vec2(hw);
    c=clamp(hw+0.5-length(vec2(p.x-clamp(p.x,0.0,len),p.y)),0.0,1.0);}
  else if(kind==2.0)c=textureLod(u_glyphs,v_uv,0.0).a;
  else if(kind==5.0)c=glow();
  else c=soft(v_loc.x,v_size.x,v_ks.y)*soft(v_loc.y,v_size.y,v_ks.y);
  float a=v_color.a*c*clip;
  o=vec4(v_color.rgb*a,a);
}`;
  const STRIP_VS = `#version 300 es
layout(location=0) in vec4 a_p;
uniform vec2 u_res;
out vec2 v_dev; out float v_across; flat out float v_hw;
void main(){v_dev=a_p.xy;v_across=a_p.z;v_hw=a_p.w;
  gl_Position=vec4(a_p.x/u_res.x*2.0-1.0,1.0-a_p.y/u_res.y*2.0,0.0,1.0);}`;
  const STRIP_FS = COMMON_FS + `
in vec2 v_dev; in float v_across; flat in float v_hw;
uniform vec4 u_color; uniform vec4 u_clip;
out vec4 o;
void main(){float a=u_color.a*cov1(v_across+v_hw,2.0*v_hw)*clipCov(v_dev,u_clip);o=vec4(u_color.rgb*a,a);}`;

  function compile(gl, vs, fs) {
    const program = gl.createProgram();
    for (const [type, source] of [[gl.VERTEX_SHADER, vs], [gl.FRAGMENT_SHADER, fs]]) {
      const shader = gl.createShader(type);
      gl.shaderSource(shader, source); gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
      gl.attachShader(program, shader);
    }
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
    return program;
  }

  function usable() {
    try {
      const probe = document.createElement('canvas');
      const gl = probe.getContext && probe.getContext('webgl2');
      if (!gl || typeof gl.createShader !== 'function') return false;
      compile(gl, INSTANCE_VS, INSTANCE_FS); compile(gl, STRIP_VS, STRIP_FS);
      const lose = gl.getExtension('WEBGL_lose_context');
      if (lose) lose.loseContext();
      return true;
    } catch (error) { return false; }
  }

  // ---- colors ----
  const colorCache = new Map();
  let colorProbe = null;
  let lastColorKey = null, lastColor = null;
  function parseColor(value) {
    if (value === lastColorKey) return lastColor;
    let c = colorCache.get(value);
    if (c) { lastColorKey = value; lastColor = c; return c; }
    if (c) return c;
    let s = String(value).trim().toLowerCase(), m;
    if ((m = /^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+%?)\s*)?\)$/.exec(s))) {
      let a = m[4] === undefined ? 1 : m[4].endsWith('%') ? parseFloat(m[4]) / 100 : parseFloat(m[4]);
      c = [m[1] / 255, m[2] / 255, m[3] / 255, Math.max(0, Math.min(1, a))];
    } else if ((m = /^#([0-9a-f]{3,8})$/.exec(s))) {
      let h = m[1];
      if (h.length <= 4) h = [...h].map(x => x + x).join('');
      const n = parseInt(h, 16);
      c = h.length === 8 ? [(n >>> 24) / 255, (n >>> 16 & 255) / 255, (n >>> 8 & 255) / 255, (n & 255) / 255]
        : [(n >> 16) / 255, (n >> 8 & 255) / 255, (n & 255) / 255, 1];
    } else {
      // Named or other CSS colors: let the browser normalize once.
      colorProbe = colorProbe || document.createElement('canvas').getContext('2d');
      colorProbe.fillStyle = '#000'; colorProbe.fillStyle = s;
      const normalized = colorProbe.fillStyle;
      c = normalized === s ? [0, 0, 0, 1] : parseColor(normalized);
    }
    if (colorCache.size > 4096) colorCache.clear();
    colorCache.set(value, c);
    lastColorKey = value; lastColor = c;
    return c;
  }

  // Some text engines place glyphs at fractional positions, others snap the
  // baseline to whole pixels. Probe once so static glyphs land exactly where
  // the 2D canvas would draw them: null = fractional, otherwise the fraction
  // at which the engine rounds up to the next pixel.
  function probeSnapping() {
    const c = document.createElement('canvas');
    c.width = 48; c.height = 48;
    const s = c.getContext('2d', {willReadFrequently:true});
    const render = (x, y) => {
      s.clearRect(0, 0, 48, 48); s.font = '20px monospace'; s.fillStyle = '#fff'; s.fillText('H', x, y);
      return s.getImageData(0, 0, 48, 48).data;
    };
    const same = (a, b) => { for (let i = 3; i < a.length; i += 4) if (a[i] !== b[i]) return false; return true; };
    const axis = shift => {
      const base = render(...shift(0)), next = render(...shift(1));
      const steps = [0.25, 0.5, 0.75].map(f => { const r = render(...shift(f)); return same(r, base) ? 0 : same(r, next) ? 1 : -1; });
      if (steps.includes(-1)) return null;
      const k = steps.indexOf(1);
      return k < 0 ? 1 : [0.25, 0.5, 0.75][k];
    };
    try { return [axis(f => [12 + f, 30]), axis(f => [12, 30 + f])]; } catch (error) { return [null, null]; }
  }

  function createGPUContext(canvas) {
    if (!usable()) return null;
    const gl = canvas.getContext('webgl2', {alpha:false, antialias:false, depth:false, stencil:false,
      premultipliedAlpha:true, preserveDrawingBuffer:false, powerPreference:'high-performance'});
    if (!gl) return null;

    const [snapX, snapY] = probeSnapping();
    const data = new Float32Array(MAX_INSTANCES * FLOATS);
    let count = 0, flushQueued = false, lost = false, batchBlend = 'source-over';
    let batchImage = null, resW = 0, resH = 0, instanceProgram, stripProgram, instanceVAO, stripVAO;
    let instanceBuffer, stripBuffer, glyphTexture, uRes, uStripRes, uStripColor, uStripClip;
    let recording = null, recordings = new Map();
    const imageTextures = new WeakMap();

    function init() {
      instanceProgram = compile(gl, INSTANCE_VS, INSTANCE_FS);
      stripProgram = compile(gl, STRIP_VS, STRIP_FS);
      uRes = gl.getUniformLocation(instanceProgram, 'u_res');
      uStripRes = gl.getUniformLocation(stripProgram, 'u_res');
      uStripColor = gl.getUniformLocation(stripProgram, 'u_color');
      uStripClip = gl.getUniformLocation(stripProgram, 'u_clip');
      gl.useProgram(instanceProgram);
      gl.uniform1i(gl.getUniformLocation(instanceProgram, 'u_glyphs'), 0);
      gl.uniform1i(gl.getUniformLocation(instanceProgram, 'u_image'), 1);

      instanceVAO = gl.createVertexArray();
      gl.bindVertexArray(instanceVAO);
      const quad = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, quad);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([0, 0, 1, 0, 0, 1, 1, 1]), gl.STATIC_DRAW);
      gl.enableVertexAttribArray(0);
      gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
      instanceBuffer = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, instanceBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, data.byteLength, gl.STREAM_DRAW);
      for (let i = 1; i <= 5; i++) {
        gl.enableVertexAttribArray(i);
        gl.vertexAttribPointer(i, 4, gl.FLOAT, false, FLOATS * 4, (i - 1) * 16);
        gl.vertexAttribDivisor(i, 1);
      }
      stripVAO = gl.createVertexArray();
      gl.bindVertexArray(stripVAO);
      stripBuffer = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, stripBuffer);
      gl.enableVertexAttribArray(0);
      gl.vertexAttribPointer(0, 4, gl.FLOAT, false, 0, 0);
      gl.bindVertexArray(null);

      glyphTexture = makeTexture();
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, ATLAS, ATLAS, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
      gl.enable(gl.BLEND);
      gl.disable(gl.DEPTH_TEST);
      resetAtlas();
    }
    function makeTexture() {
      const texture = gl.createTexture();
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      return texture;
    }

    function setBlend(mode) {
      if (mode === 'screen') gl.blendFuncSeparate(gl.ONE, gl.ONE_MINUS_SRC_COLOR, gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
      else gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    }
    function prepareTarget() {
      const w = canvas.width, h = canvas.height;
      if (w !== resW || h !== resH) { resW = w; resH = h; gl.viewport(0, 0, w, h); }
    }
    function flush() {
      uploadGlyphs();
      if (!count || lost) { count = 0; return; }
      prepareTarget();
      gl.useProgram(instanceProgram);
      gl.uniform2f(uRes, resW, resH);
      gl.bindVertexArray(instanceVAO);
      gl.bindBuffer(gl.ARRAY_BUFFER, instanceBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, data.subarray(0, count * FLOATS), gl.STREAM_DRAW);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, glyphTexture);
      gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, batchImage || glyphTexture);
      setBlend(batchBlend);
      gl.drawArraysInstanced(gl.TRIANGLE_STRIP, 0, 4, count);
      count = 0;
    }
    function queueFlush() {
      if (flushQueued) return;
      flushQueued = true;
      // Runs after the current requestAnimationFrame callback returns.
      queueMicrotask(() => { flushQueued = false; flush(); });
    }
    function push(ox, oy, ux, uy, vx, vy, kind, sigma, r, g, b, a, clip, u0, v0, u1, v1) {
      if (lost) return;
      if (count === MAX_INSTANCES) flush();
      const i = count++ * FLOATS;
      data[i] = ox; data[i + 1] = oy; data[i + 2] = ux; data[i + 3] = uy;
      data[i + 4] = vx; data[i + 5] = vy; data[i + 6] = kind; data[i + 7] = sigma;
      data[i + 8] = r; data[i + 9] = g; data[i + 10] = b; data[i + 11] = a;
      data[i + 12] = clip[0]; data[i + 13] = clip[1]; data[i + 14] = clip[2]; data[i + 15] = clip[3];
      data[i + 16] = u0; data[i + 17] = v0; data[i + 18] = u1; data[i + 19] = v1;
      if (recording) recording.push(data.slice(i, i + FLOATS));
      if (!flushQueued) queueFlush();
    }
    function useBlend(mode) {
      mode = mode === 'screen' ? 'screen' : 'source-over';
      if (mode !== batchBlend) { flush(); batchBlend = mode; }
    }

    // ---- glyph atlas ----
    // New glyphs are drawn into a CPU staging canvas and uploaded together:
    // one pixel readback per frame instead of one per glyph.
    let shelves, shelfY, fonts = new Map(), pending = [], stageX = 0, stageY = 0, stageRow = 0;
    const stage = document.createElement('canvas');
    stage.width = STAGE; stage.height = STAGE;
    const stageContext = stage.getContext('2d', {willReadFrequently:true});
    const measurer = document.createElement('canvas').getContext('2d');
    function resetAtlas() {
      uploadGlyphs();
      shelves = []; shelfY = 0; recordings.clear();
      for (const font of fonts.values()) font.glyphs.clear();
    }
    function allocate(w, h) {
      const bucket = Math.ceil(h / 4) * 4;
      for (const shelf of shelves) {
        if (shelf.h === bucket && shelf.x + w + 1 <= ATLAS) { const x = shelf.x; shelf.x += w + 1; return [x, shelf.y]; }
      }
      if (shelfY + bucket + 1 > ATLAS || w + 1 > ATLAS) return null;
      const shelf = {y:shelfY, h:bucket, x:w + 1};
      shelfY += bucket + 1; shelves.push(shelf);
      return [0, shelf.y];
    }
    function stageSpot(w, h) {
      if (w > STAGE || h > STAGE) return null;
      if (stageX + w > STAGE) { stageX = 0; stageY += stageRow + 1; stageRow = 0; }
      if (stageY + h > STAGE) { uploadGlyphs(); }
      const spot = [stageX, stageY];
      stageX += w + 1; stageRow = Math.max(stageRow, h);
      return spot;
    }
    function uploadGlyphs() {
      if (!pending.length) return;
      let bw = 0, bh = 0;
      for (const p of pending) { bw = Math.max(bw, p.sx + p.w * p.fx); bh = Math.max(bh, p.sy + p.h * p.fy); }
      const image = stageContext.getImageData(0, 0, bw, bh).data;
      const pixels = new Uint8Array(image.buffer, image.byteOffset, image.length);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, glyphTexture);
      gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
      for (const p of pending) {
        if (p.fx === 1 && p.fy === 1) {
          gl.pixelStorei(gl.UNPACK_ROW_LENGTH, bw);
          gl.pixelStorei(gl.UNPACK_SKIP_PIXELS, p.sx);
          gl.pixelStorei(gl.UNPACK_SKIP_ROWS, p.sy);
          gl.texSubImage2D(gl.TEXTURE_2D, 0, p.ax, p.ay, p.w, p.h, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
        } else {
          // Box-filter the supersampled glyph down to device pixels.
          const out = new Uint8Array(p.w * p.h * 4), n = p.fx * p.fy;
          for (let y = 0; y < p.h; y++) for (let x = 0; x < p.w; x++) {
            let sum = 0;
            for (let j = 0; j < p.fy; j++) {
              const row = (p.sy + y * p.fy + j) * bw + p.sx + x * p.fx;
              for (let i = 0; i < p.fx; i++) sum += pixels[(row + i) * 4 + 3];
            }
            const o = (y * p.w + x) * 4;
            out[o] = out[o + 1] = out[o + 2] = 255; out[o + 3] = Math.round(sum / n);
          }
          gl.pixelStorei(gl.UNPACK_ROW_LENGTH, 0);
          gl.pixelStorei(gl.UNPACK_SKIP_PIXELS, 0);
          gl.pixelStorei(gl.UNPACK_SKIP_ROWS, 0);
          gl.texSubImage2D(gl.TEXTURE_2D, 0, p.ax, p.ay, p.w, p.h, gl.RGBA, gl.UNSIGNED_BYTE, out);
        }
      }
      gl.pixelStorei(gl.UNPACK_ROW_LENGTH, 0);
      gl.pixelStorei(gl.UNPACK_SKIP_PIXELS, 0);
      gl.pixelStorei(gl.UNPACK_SKIP_ROWS, 0);
      stageContext.setTransform(1, 0, 0, 1, 0, 0);
      stageContext.clearRect(0, 0, bw, bh);
      pending = []; stageX = 0; stageY = 0; stageRow = 0;
    }
    let lastFontCss = null, lastFontScale = 0, lastFont = null;
    function fontFor(css, scale) {
      if (css === lastFontCss && scale === lastFontScale) return lastFont;
      const key = css + '|' + scale;
      let font = fonts.get(key);
      if (!font) {
        let px = 10;
        const device = css.replace(/(\d*\.?\d+)px/, (_, size) => { px = parseFloat(size) * scale; return px + 'px'; });
        font = {device, px, glyphs:new Map(), layouts:new Map(), advances:new Map()};
        if (fonts.size > 256) fonts.clear();
        fonts.set(key, font);
      }
      lastFontCss = css; lastFontScale = scale; lastFont = font;
      return font;
    }
    function layout(font, text) {
      let entry = font.layouts.get(text);
      if (entry) return entry;
      const codes = [], advances = [];
      let width = 0;
      measurer.font = font.device;
      for (const ch of text) {
        const code = ch.codePointAt(0);
        let advance = font.advances.get(code);
        if (advance === undefined) { advance = measurer.measureText(ch).width; font.advances.set(code, advance); }
        codes.push(code); advances.push(advance); width += advance;
      }
      entry = {codes, advances, width};
      if (font.layouts.size > 4096) font.layouts.clear();
      font.layouts.set(text, entry);
      return entry;
    }
    const EMPTY = {empty:true};
    function glyph(font, code, qx, qy, moving) {
      const key = ((code * 4 + qx) * 8 + qy) * 2 + (moving ? 1 : 0);
      let entry = font.glyphs.get(key);
      if (entry) return entry;
      entry = rasterize(font, code, qx, qy, moving);
      if (!entry) {
        // Atlas full: draw what is queued, then start a fresh atlas.
        flush(); resetAtlas();
        entry = rasterize(font, code, qx, qy, moving) || EMPTY;
      }
      font.glyphs.set(key, entry);
      return entry;
    }
    function rasterize(font, code, qx, qy, moving) {
      const ch = String.fromCodePoint(code);
      measurer.font = font.device;
      const m = measurer.measureText(ch);
      const left = Math.ceil(Math.max(0, m.actualBoundingBoxLeft || 0));
      const right = Math.ceil(m.actualBoundingBoxRight === undefined ? m.width : m.actualBoundingBoxRight);
      const ascent = Math.ceil(m.actualBoundingBoxAscent === undefined ? font.px : m.actualBoundingBoxAscent);
      const descent = Math.ceil(m.actualBoundingBoxDescent === undefined ? font.px * 0.3 : m.actualBoundingBoxDescent);
      if (left + right <= 0 || ascent + descent <= 0) return EMPTY;
      const pad = 2, w = left + right + 2 * pad + 1, h = ascent + descent + 2 * pad + 1;
      const bx = pad + left, by = pad + ascent;
      // On an axis where the engine snaps glyphs to whole pixels, draw the
      // subpixel offset at 4x (horizontal) or 8x (vertical) resolution and
      // box-filter it back down. Moving glyphs always use this path so every
      // offset is rasterized the same way.
      const fx = snapX !== null && (qx || moving) ? 4 : 1, fy = snapY !== null && (qy || moving) ? 8 : 1;
      const spot = allocate(w, h);
      if (!spot) return null;
      const st = stageSpot(w * fx, h * fy);
      if (!st) return EMPTY;
      const s = stageContext;
      s.setTransform(fx, 0, 0, fy, st[0], st[1]);
      s.font = font.device; s.fillStyle = '#fff'; s.textAlign = 'left'; s.textBaseline = 'alphabetic';
      s.fillText(ch, bx + qx / 4, by + qy / 8);
      pending.push({sx:st[0], sy:st[1], w, h, fx, fy, ax:spot[0], ay:spot[1]});
      return {bx, by, w, h, u0:spot[0] / ATLAS, v0:spot[1] / ATLAS, u1:(spot[0] + w) / ATLAS, v1:(spot[1] + h) / ATLAS};
    }

    // ---- context ----
    const measureCache = new Map();
    const ctx = {
      canvas,
      fillStyle:'#000', strokeStyle:'#000', globalAlpha:1, lineWidth:1, lineCap:'butt', lineJoin:'miter',
      miterLimit:10, font:'10px sans-serif', textAlign:'start', textBaseline:'alphabetic', direction:'ltr',
      shadowBlur:0, shadowColor:'rgba(0, 0, 0, 0)', shadowOffsetX:0, shadowOffsetY:0,
      globalCompositeOperation:'source-over', imageSmoothingEnabled:true, capitolMovingText:false,
      _m:[1, 0, 0, 1, 0, 0], _clip:NO_CLIP, _stack:[], _path:[], _sub:null,

      save() {
        this._stack.push([this.fillStyle, this.strokeStyle, this.globalAlpha, this.lineWidth, this.lineCap,
          this.lineJoin, this.miterLimit, this.font, this.textAlign, this.textBaseline, this.shadowBlur,
          this.shadowColor, this.shadowOffsetX, this.shadowOffsetY, this.globalCompositeOperation,
          this._m, this._clip]);
      },
      restore() {
        const s = this._stack.pop();
        if (!s) return;
        [this.fillStyle, this.strokeStyle, this.globalAlpha, this.lineWidth, this.lineCap, this.lineJoin,
          this.miterLimit, this.font, this.textAlign, this.textBaseline, this.shadowBlur, this.shadowColor,
          this.shadowOffsetX, this.shadowOffsetY, this.globalCompositeOperation, this._m, this._clip] = s;
      },
      // Transforms are replaced, never mutated, so save() can keep a reference.
      setTransform(a, b, c, d, e, f) {
        if (typeof a === 'object' && a) ({a, b, c, d, e, f} = a);
        this._m = [a, b, c, d, e, f];
      },
      resetTransform() { this._m = [1, 0, 0, 1, 0, 0]; },
      transform(a, b, c, d, e, f) {
        const m = this._m;
        this._m = [m[0] * a + m[2] * b, m[1] * a + m[3] * b, m[0] * c + m[2] * d, m[1] * c + m[3] * d,
          m[0] * e + m[2] * f + m[4], m[1] * e + m[3] * f + m[5]];
      },
      translate(x, y) { this.transform(1, 0, 0, 1, x, y); },
      scale(x, y) { this.transform(x, 0, 0, y, 0, 0); },
      rotate(angle) { const c = Math.cos(angle), s = Math.sin(angle); this.transform(c, s, -s, c, 0, 0); },

      _alpha() { const a = this.globalAlpha; return a >= 0 && a <= 1 ? a : 1; },
      _shadow() {
        return (this.shadowBlur > 0 || this.shadowOffsetX || this.shadowOffsetY) ? parseColor(this.shadowColor) : null;
      },
      fillRect(x, y, w, h) {
        if (!w || !h || !isFinite(x + y + w + h)) return;
        const c = parseColor(this.fillStyle), alpha = c[3] * this._alpha();
        if (this.globalCompositeOperation !== batchBlend) useBlend(this.globalCompositeOperation);
        const m = this._m, ox = m[0] * x + m[2] * y + m[4], oy = m[1] * x + m[3] * y + m[5];
        const shadow = this._shadow();
        if (shadow && shadow[3] * alpha > 0) {
          push(ox + this.shadowOffsetX, oy + this.shadowOffsetY, m[0] * w, m[1] * w, m[2] * h, m[3] * h, K_SOFT,
            Math.max(this.shadowBlur / 2, 0.01), shadow[0], shadow[1], shadow[2], shadow[3] * alpha, this._clip, 0, 0, 0, 0);
        }
        if (alpha > 0) push(ox, oy, m[0] * w, m[1] * w, m[2] * h, m[3] * h, K_RECT, 0, c[0], c[1], c[2], alpha, this._clip, 0, 0, 0, 0);
      },
      clearRect(x, y, w, h) {
        // Only full clears occur in practice; the canvas is opaque black.
        const saved = [this.fillStyle, this.globalAlpha, this.globalCompositeOperation, this.shadowBlur];
        this.fillStyle = '#000'; this.globalAlpha = 1; this.globalCompositeOperation = 'source-over'; this.shadowBlur = 0;
        this.fillRect(x, y, w, h);
        [this.fillStyle, this.globalAlpha, this.globalCompositeOperation, this.shadowBlur] = saved;
      },
      _bar(x, y, w, h, c, alpha) {
        const m = this._m;
        push(m[0] * x + m[4], m[3] * y + m[5], m[0] * w, 0, 0, m[3] * h, K_RECT, 0, c[0], c[1], c[2], alpha, this._clip, 0, 0, 0, 0);
      },
      strokeRect(x, y, w, h) {
        if (!isFinite(x + y + w + h)) return;
        const m = this._m;
        if (m[1] || m[2]) {
          // Rotated rectangles: stroke a temporary path, keeping the current one.
          const path = this._path, sub = this._sub;
          this.beginPath(); this.moveTo(x, y); this.lineTo(x + w, y); this.lineTo(x + w, y + h);
          this.lineTo(x, y + h); this.closePath(); this.stroke();
          this._path = path; this._sub = sub;
          return;
        }
        const c = parseColor(this.strokeStyle), alpha = c[3] * this._alpha();
        if (!(alpha > 0)) return;
        useBlend(this.globalCompositeOperation);
        const lw = this.lineWidth > 0 ? this.lineWidth : 1, hw = lw / 2;
        if (w < 0) { x += w; w = -w; }
        if (h < 0) { y += h; h = -h; }
        if (h - lw <= 0 || w - lw <= 0) { this._bar(x - hw, y - hw, w + lw, h + lw, c, alpha); return; }
        // Four non-overlapping bars, like a mitered rectangular stroke.
        this._bar(x - hw, y - hw, w + lw, lw, c, alpha);
        this._bar(x - hw, y + h - hw, w + lw, lw, c, alpha);
        this._bar(x - hw, y + hw, lw, h - lw, c, alpha);
        this._bar(x + w - hw, y + hw, lw, h - lw, c, alpha);
      },

      beginPath() { this._path = []; this._sub = null; },
      moveTo(x, y) {
        const m = this._m;
        this._sub = [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];
        this._path.push(this._sub);
      },
      lineTo(x, y) {
        if (!this._sub) { this.moveTo(x, y); return; }
        const m = this._m;
        this._sub.push(m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]);
      },
      closePath() {
        if (this._sub && this._sub.length > 2) this._sub.push(this._sub[0], this._sub[1]);
      },
      rect(x, y, w, h) {
        this._path.push({rect:[x, y, w, h], m:this._m});
        this.moveTo(x, y);
      },
      clip() {
        let box = null;
        for (const sub of this._path) {
          if (!sub.rect) continue;
          const [x, y, w, h] = sub.rect, m = sub.m;
          for (const px of [x, x + w]) for (const py of [y, y + h]) {
            const dx = m[0] * px + m[2] * py + m[4], dy = m[1] * px + m[3] * py + m[5];
            box = box ? [Math.min(box[0], dx), Math.min(box[1], dy), Math.max(box[2], dx), Math.max(box[3], dy)] : [dx, dy, dx, dy];
          }
        }
        if (!box) return;
        const c = this._clip;
        this._clip = [Math.max(c[0], box[0]), Math.max(c[1], box[1]), Math.min(c[2], box[2]), Math.min(c[3], box[3])];
      },
      fill() {
        for (const sub of this._path) {
          if (!sub.rect) continue;
          const saved = this._m;
          this._m = sub.m;
          this.fillRect(...sub.rect);
          this._m = saved;
        }
      },
      stroke() {
        const c = parseColor(this.strokeStyle), alpha = c[3] * this._alpha();
        const shadowColor = this._shadow();
        const shadow = shadowColor && shadowColor[3] * alpha > 0 ? [shadowColor[0], shadowColor[1], shadowColor[2], shadowColor[3] * alpha] : null;
        if (!(alpha > 0) && !shadow) return;
        useBlend(this.globalCompositeOperation);
        const m = this._m, scale = Math.sqrt(Math.abs(m[0] * m[3] - m[1] * m[2])) || 1;
        const hw = (this.lineWidth > 0 ? this.lineWidth : 1) * scale / 2, cap = this.lineCap;
        const color = [c[0], c[1], c[2], alpha];
        for (const sub of this._path) {
          if (sub.rect) {
            const saved = this._m;
            this._m = sub.m; this.strokeRect(...sub.rect); this._m = saved;
            continue;
          }
          // Drop repeated points; a segment needs two distinct points.
          const pts = [sub[0], sub[1]];
          for (let i = 2; i < sub.length; i += 2) {
            if (sub[i] !== pts[pts.length - 2] || sub[i + 1] !== pts[pts.length - 1]) pts.push(sub[i], sub[i + 1]);
          }
          if (pts.length === 4) this._segment(pts, hw, cap, color, shadow);
          else if (pts.length > 4) {
            if (shadow) for (let i = 0; i + 3 < pts.length; i += 2) this._segment(pts.slice(i, i + 4), hw, 'butt', null, shadow);
            if (alpha > 0) this._polyline(pts, hw, color);
          }
        }
      },
      _segment(p, hw, cap, color, shadow) {
        let dx = p[2] - p[0], dy = p[3] - p[1];
        const len = Math.hypot(dx, dy);
        if (!len) return;
        dx /= len; dy /= len;
        const nx = -dy * hw, ny = dx * hw, ext = cap === 'butt' ? 0 : hw;
        const ox = p[0] - dx * ext - nx, oy = p[1] - dy * ext - ny, L = len + 2 * ext;
        if (shadow) {
          push(ox + this.shadowOffsetX, oy + this.shadowOffsetY, dx * L, dy * L, nx * 2, ny * 2, K_SOFT,
            Math.max(this.shadowBlur / 2, 0.01), shadow[0], shadow[1], shadow[2], shadow[3], this._clip, 0, 0, 0, 0);
        }
        if (color && color[3] > 0) {
          push(ox, oy, dx * L, dy * L, nx * 2, ny * 2, cap === 'round' ? K_ROUND : K_RECT, 0,
            color[0], color[1], color[2], color[3], this._clip, 0, 0, 0, 0);
        }
      },
      _polyline(p, hw, color) {
        // A mitered triangle strip covers each pixel once, so translucent
        // curves have no doubled joints, matching a single canvas stroke.
        flush();
        const n = p.length / 2, ext = hw + 1, verts = new Float32Array(n * 8);
        for (let i = 0; i < n; i++) {
          const x = p[i * 2], y = p[i * 2 + 1];
          let ax = 0, ay = 0, bx = 0, by = 0;
          if (i > 0) { ax = x - p[i * 2 - 2]; ay = y - p[i * 2 - 1]; const l = Math.hypot(ax, ay); ax /= l; ay /= l; }
          if (i < n - 1) { bx = p[i * 2 + 2] - x; by = p[i * 2 + 3] - y; const l = Math.hypot(bx, by); bx /= l; by /= l; }
          if (i === 0) { ax = bx; ay = by; }
          if (i === n - 1) { bx = ax; by = ay; }
          let mx = -(ay + by), my = ax + bx;
          const ml = Math.hypot(mx, my);
          let k = 1;
          if (ml > 1e-6) {
            mx /= ml; my /= ml;
            const cos = mx * -by + my * bx;
            k = Math.min(1 / Math.max(cos, 1e-3), this.miterLimit > 0 ? this.miterLimit : 10);
          } else { mx = -by; my = bx; }
          verts.set([x + mx * ext * k, y + my * ext * k, ext, hw, x - mx * ext * k, y - my * ext * k, -ext, hw], i * 8);
        }
        prepareTarget();
        gl.useProgram(stripProgram);
        gl.uniform2f(uStripRes, resW, resH);
        gl.uniform4f(uStripColor, color[0], color[1], color[2], color[3]);
        gl.uniform4f(uStripClip, this._clip[0], this._clip[1], this._clip[2], this._clip[3]);
        gl.bindVertexArray(stripVAO);
        gl.bindBuffer(gl.ARRAY_BUFFER, stripBuffer);
        gl.bufferData(gl.ARRAY_BUFFER, verts, gl.STREAM_DRAW);
        setBlend(batchBlend);
        if (!lost) gl.drawArrays(gl.TRIANGLE_STRIP, 0, n * 2);
      },

      measureText(text) {
        let byFont = measureCache.get(this.font);
        if (!byFont) {
          if (measureCache.size > 64) measureCache.clear();
          byFont = new Map(); measureCache.set(this.font, byFont);
        }
        let metrics = byFont.get(text);
        if (metrics) return metrics;
        measurer.font = this.font;
        metrics = measurer.measureText(text);
        if (byFont.size > 4096) byFont.clear();
        byFont.set(text, metrics);
        return metrics;
      },
      fillText(text, x, y, maxWidth) {
        if (typeof text !== 'string') text = String(text);
        if (!text || !isFinite(x + y)) return;
        const c = parseColor(this.fillStyle), alpha = c[3] * this._alpha();
        const shadowColor = this._shadow();
        const shadowAlpha = shadowColor ? shadowColor[3] * alpha : 0;
        if (!(alpha > 0) && !(shadowAlpha > 0)) return;
        if (this.globalCompositeOperation !== batchBlend) useBlend(this.globalCompositeOperation);
        const m = this._m, scale = Math.sqrt(Math.abs(m[0] * m[3] - m[1] * m[2]));
        if (!scale) return;
        const font = fontFor(this.font, scale), run = layout(font, text);
        let sx = 1;
        if (maxWidth !== undefined) {
          if (!(maxWidth > 0)) return;
          if (run.width > maxWidth * scale) sx = maxWidth * scale / run.width;
        }
        const width = run.width * sx / scale, align = this.textAlign;
        const pen = x - (align === 'right' || align === 'end' ? width : align === 'center' ? width / 2 : 0);
        // A canvas draws the whole text's shadow first, then the text.
        if (shadowAlpha > 0) {
          this._glyphs(font, run, pen, y, sx, scale, K_GLOW, Math.max(this.shadowBlur / 2, 0.01),
            shadowColor[0], shadowColor[1], shadowColor[2], shadowAlpha, this.shadowOffsetX, this.shadowOffsetY);
        }
        if (alpha > 0) this._glyphs(font, run, pen, y, sx, scale, K_MASK, 0, c[0], c[1], c[2], alpha, 0, 0);
      },
      _glyphs(font, run, pen, y, sx, scale, kind, sigma, r, g, b, a, offX, offY) {
        const m = this._m, codes = run.codes, advances = run.advances, clip = this._clip;
        const ux = m[0] / scale, uy = m[1] / scale, vx = m[2] / scale, vy = m[3] / scale;
        const straight = !m[1] && !m[2] && m[0] > 0 && m[3] > 0, moving = this.capitolMovingText === true;
        let advance = 0;
        for (let i = 0; i < codes.length; i++) {
          const tx = pen + advance / scale;
          advance += advances[i] * sx;
          let px = m[0] * tx + m[2] * y + m[4] + offX, py = m[1] * tx + m[3] * y + m[5] + offY;
          let qx = 0, qy = 0;
          if (straight) {
            const fx = Math.floor(px), fy = Math.floor(py);
            // Moving text keeps the sub-step remainder (at most 1/8 px), which
            // linear filtering turns into exactly proportional motion.
            if (moving || snapX === null) {
              qx = Math.round((px - fx) * 4);
              if (qx === 4) { qx = 0; px = moving ? px : fx + 1; } else px = moving ? px - qx / 4 : fx;
            } else px = fx + (px - fx >= snapX ? 1 : 0);
            if (moving || snapY === null) {
              qy = Math.round((py - fy) * 8);
              if (qy === 8) { qy = 0; py = moving ? py : fy + 1; } else py = moving ? py - qy / 8 : fy;
            } else py = fy + (py - fy >= snapY ? 1 : 0);
          } else { px = Math.round(px); py = Math.round(py); }
          const e = glyph(font, codes[i], qx, qy, moving);
          if (e.empty) continue;
          push(px - (ux * e.bx * sx + vx * e.by), py - (uy * e.bx * sx + vy * e.by),
            ux * e.w * sx, uy * e.w * sx, vx * e.h, vy * e.h, kind, sigma, r, g, b, a, clip,
            e.u0, e.v0, e.u1, e.v1);
        }
      },
      drawImage(image, ...args) {
        let sx = 0, sy = 0, sw = image.width, sh = image.height, dx, dy, dw = sw, dh = sh;
        if (args.length === 2) [dx, dy] = args;
        else if (args.length === 4) [dx, dy, dw, dh] = args;
        else [sx, sy, sw, sh, dx, dy, dw, dh] = args;
        const alpha = this._alpha();
        if (!(alpha > 0) || !sw || !sh || !image.width || !image.height) return;
        let texture = imageTextures.get(image);
        if (!texture) {
          flush();
          texture = makeTexture();
          gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);
          gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
          gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
          imageTextures.set(image, texture);
        }
        if (texture !== batchImage) { flush(); batchImage = texture; }
        useBlend(this.globalCompositeOperation);
        const m = this._m;
        push(m[0] * dx + m[2] * dy + m[4], m[1] * dx + m[3] * dy + m[5], m[0] * dw, m[1] * dw, m[2] * dh, m[3] * dh,
          K_IMAGE, 0, 1, 1, 1, alpha, this._clip, sx / image.width, sy / image.height,
          (sx + sw) / image.width, (sy + sh) / image.height);
      },

      // Static layers (the dot grid) are recorded once per canvas size and
      // transform, then copied into later frames instead of redrawn.
      capitolReplay(key, draw) {
        const signature = key + '|' + canvas.width + 'x' + canvas.height + '|' + this._m.join(',') + '|' + this._clip.join(',');
        const saved = recordings.get(key);
        if (saved && saved.signature === signature) {
          useBlend(saved.blend);
          for (const instance of saved.instances) {
            if (count === MAX_INSTANCES) flush();
            data.set(instance, count++ * FLOATS);
          }
          if (saved.instances.length) queueFlush();
          this.fillStyle = saved.fillStyle; this.strokeStyle = saved.strokeStyle;
          return;
        }
        const blend = batchBlend;
        recording = [];
        try { draw(); } finally {
          recordings.set(key, {signature, blend, instances:recording, fillStyle:this.fillStyle, strokeStyle:this.strokeStyle});
          recording = null;
        }
      },
    };

    canvas.addEventListener('webglcontextlost', event => { event.preventDefault(); lost = true; count = 0; });
    canvas.addEventListener('webglcontextrestored', () => {
      lost = false; batchImage = null; resW = resH = 0; fonts = new Map(); lastFontCss = null; pending = [];
      stageX = stageY = stageRow = 0;
      init();
    });
    init();
    return ctx;
  }

  window.__capitolContext = canvas => {
    const gpu = createGPUContext(canvas);
    if (gpu) { window.__capitolGPU = true; return gpu; }
    const ctx = canvas.getContext('2d', {alpha:false});
    window.__capitolCacheText(ctx);
    return ctx;
  };
  // The GPU path renders at the website's resolution (up to 2x). The CPU
  // fallback keeps the four-million-pixel backing-store budget.
  window.__capitolDPR = (W, H) => window.__capitolGPU ? Math.min(2, window.devicePixelRatio || 1)
    : Math.min(2, window.devicePixelRatio || 1, Math.sqrt(4000000 / (W * H)));
})();
