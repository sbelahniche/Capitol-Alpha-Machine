"""Optimize exported saver scenes without editing the main site's animations."""
from pathlib import Path

HERE = Path(__file__).parent


def replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise ValueError(f"Scene source changed; expected one occurrence of {old[:80]!r}")
    return source.replace(old, new, 1)


def optimize_scene(scene: str, number: str, *, preview: bool = False, stats: bool = False) -> str:
    """Return a saver scene. Native savers (preview=False) draw through the
    WebGL2 canvas in gpu-canvas.js on WebKit's own frame cadence, falling back
    to the CPU canvas when WebGL2 is unavailable. Website previews keep their
    paced CPU canvas. stats=True overlays live frame timing (diagnostics only)."""
    runtime = (HERE / 'runtime.js').read_text().replace(
        '__CAPITOL_PREVIEW__', 'true' if preview else 'false')
    scripts = f'<script>{runtime}</script>'
    if stats and not preview:
        scripts = '<script>window.__capitolStats=true;</script>\n' + scripts
    if not preview:
        scripts += f"\n<script>{(HERE / 'gpu-canvas.js').read_text()}</script>"
    scene = replace_once(scene, '</head>', f'{scripts}\n</head>')
    if preview:
        scene = replace_once(scene, "const ctx=cv.getContext('2d');",
                             "const ctx=cv.getContext('2d', {alpha:false});\nwindow.__capitolCacheText(ctx);")
        # Limit backing-store work on Retina/4K/5K displays; keep CSS coordinates.
        scene = replace_once(scene, 'DPR=Math.min(2,window.devicePixelRatio||1);',
                             'DPR=Math.min(2,window.devicePixelRatio||1,Math.sqrt(4000000/(W*H)));')
    else:
        scene = replace_once(scene, "const ctx=cv.getContext('2d');", "const ctx=window.__capitolContext(cv);")
        # Full website resolution on the GPU; four-million-pixel cap on the CPU fallback.
        scene = replace_once(scene, 'DPR=Math.min(2,window.devicePixelRatio||1);', 'DPR=window.__capitolDPR(W,H);')
    if not preview:
        # The dot grid never changes for a given size; the GPU canvas records
        # it once and copies it into each frame.
        scene = replace_once(scene, 'function dotGrid(){',
                             "function dotGrid(){if(ctx.capitolReplay){ctx.capitolReplay('dots',drawDotGrid);return;}drawDotGrid();}\nfunction drawDotGrid(){")
    if number == '02':
        scene = replace_once(scene, 'const NB=8,buck=Array.from({length:NB},()=>[]);',
                             'const NB=8,buck=domeBuckets;for(const bucket of buck)bucket.length=0;')
        scene = replace_once(scene, 'function drawDome(t){',
                             'const domeBuckets=Array.from({length:8},()=>[]);\nfunction drawDome(t){')
        scene = replace_once(scene, 'for(let j=0;j<col.list.length;j++){\n      let y=',
                             '''// Visit only visible rows, including the wrap around the tape.
    // Two sorted ranges retain the original row order and lock tie-breaking.
    const first=Math.ceil(off/rowH), end=Math.min(col.list.length,Math.floor((off+H)/rowH)+1);
    const wrapEnd=Math.max(0,Math.min(first,Math.floor((off+H-tapeLen)/rowH)+1));
    ctx.save();ctx.beginPath();ctx.rect(c*colW+4,0,colW-8,H);ctx.clip();
    for(let index=0;index<wrapEnd+end-first;index++){
      const j=index<wrapEnd?index:first+index-wrapEnd;
      let y=''')
        scene = replace_once(scene, 'ctx.save();ctx.beginPath();ctx.rect(c*colW+4,0,colW-8,H);ctx.clip();\n      ctx.fillText(label, colX, y, colW-12);\n      ctx.restore();',
                             'ctx.fillText(label, colX, y, colW-12);')
        scene = replace_once(scene, '\n    if(headRow>=0){', '\n    ctx.restore();\n    if(headRow>=0){')
        if preview:
            scene = replace_once(scene, 'let COLS=[],colW=0,rowH=15,nCols=0;',
                                 'let labelAtlas;\nlet COLS=[],colW=0,rowH=15,nCols=0;')
            scene = replace_once(scene, 'colW=175; nCols=',
                                 "colW=175; labelAtlas=window.__capitolCreateLabelAtlas(PJ.TICK,'11px '+MONO,colW-12,DPR); nCols=")
            scene = replace_once(scene, 'ctx.fillText(label, colX, y, colW-12);',
                                 'labelAtlas.draw(ctx,tr[1],colX,y,Number(a.toFixed(2)));')
            scene = scene.replace('ctx.measureText(label).width', 'labelAtlas.widths[tr[1]]')
        else:
            # The GPU canvas caches glyphs itself and keeps labels sharp at
            # full resolution; the label atlas is only for the CPU fallback.
            scene = replace_once(scene, 'let COLS=[],colW=0,rowH=15,nCols=0;',
                                 'let labelAtlas;\nconst labelWidth=i=>labelAtlas?labelAtlas.widths[i]:ctx.measureText(PJ.TICK[i]).width;\n'
                                 'let COLS=[],colW=0,rowH=15,nCols=0;')
            scene = replace_once(scene, 'colW=175; nCols=',
                                 "colW=175; labelAtlas=window.__capitolGPU?null:window.__capitolCreateLabelAtlas(PJ.TICK,'11px '+MONO,colW-12,DPR); nCols=")
            # Scrolling labels and the locked ticker are drawn at quarter-pixel
            # positions; whole-pixel snapping made them step 1-2-1-1-2 px per frame.
            scene = replace_once(scene, 'ctx.fillText(label, colX, y, colW-12);',
                                 'if(labelAtlas)labelAtlas.draw(ctx,tr[1],colX,y,Number(a.toFixed(2)));\n'
                                 '      else{ctx.capitolMovingText=true;ctx.fillText(label, colX, y, colW-12);ctx.capitolMovingText=false;}')
            scene = replace_once(scene, 'fitText(ticker,locked.x,locked.y,tradeW-8);',
                                 'ctx.capitolMovingText=true;fitText(ticker,locked.x,locked.y,tradeW-8);ctx.capitolMovingText=false;')
            scene = scene.replace('ctx.measureText(label).width', 'labelWidth(tr[1])')
            # Reuse identical color strings per opacity instead of building two
            # new strings for every visible row on every frame.
            scene = replace_once(scene, 'let labelAtlas;\n',
                                 "let labelAtlas;\nconst rowInk=new Map(),ink=a=>{let s=rowInk.get(a);if(!s){s='rgba(255,255,255,'+a.toFixed(2)+')';rowInk.set(a,s);}return s;};\n")
            scene = replace_once(scene, "ctx.fillStyle='rgba(255,255,255,'+a.toFixed(2)+')';", 'ctx.fillStyle=ink(a);')
            scene = replace_once(scene, "ctx.fillStyle='rgba(255,255,255,'+barA.toFixed(2)+')';", 'ctx.fillStyle=ink(barA);')
        # Candidates are only consumed when acquiring a new lock. Avoid one
        # object allocation per visible row during every frame of a held lock.
        start = scene.index('      const amtP=amountPct(tr);')
        end = scene.index('\n\n      // Lock candidates', start)
        candidate = scene[start:end]
        scene = scene[:start] + scene[end:]
        scene = replace_once(scene, '        if(maxHold>=LOCK_HOLD_MIN){',
                             '        if(maxHold>=LOCK_HOLD_MIN){\n' + candidate)
    elif number == '04':
        scene = replace_once(scene, 'function resize(){',
                             'const totalVolume=ROWS.reduce((sum,row)=>sum+row.total,0);\nfunction resize(){')
        scene = replace_once(scene, 'ROWS.reduce((a,r)=>a+r.total,0)', 'totalVolume')
        scene = replace_once(scene, 'plot.rowH=clamp(plot.rowGap*0.42,5,14);',
                             '''plot.rowH=clamp(plot.rowGap*0.42,5,14);
  for(const tr of TRADES){tr.x=xOf(tr.ms);tr.y=yOf(tr.row);tr.h=plot.rowH*(0.6+tr.signal*1.85);}''')
        scene = replace_once(scene, 'Math.abs(xOf(tr.ms)-lock.x)', 'Math.abs(tr.x-lock.x)')
        scene = replace_once(scene, 'const x=xOf(tr.ms),y=yOf(tr.row);\n    if(x<',
                             'const x=tr.x,y=tr.y;\n    if(x<')
        scene = replace_once(scene, 'const h=plot.rowH*(0.6+tr.signal*1.85);', 'const h=tr.h;')
        scene = replace_once(scene, 'function tradeAlpha(tr,tt){',
                             "const tradeInk=Array.from({length:1001},(_,i)=>'rgba(255,255,255,'+(i/1000).toFixed(3)+')');\nfunction tradeAlpha(tr,tt){")
        scene = replace_once(scene, "ctx.fillStyle='rgba(255,255,255,'+intensity.toFixed(3)+')';",
                             'ctx.fillStyle=tradeInk[Math.round(intensity*1000)];')
    if number in ('04', '05'):
        # Flooring fractional progress every frame stranded Returns at zero
        # (22 * 1/60 < 1). Accumulate first, round only the displayed count.
        rate = '22' if number == '04' else '70'
        scene = replace_once(scene, f'Math.floor(tradeCount+dt*{rate})', f'tradeCount+dt*{rate}')
        scene = replace_once(scene, "z4(tradeCount)", "z4(Math.floor(tradeCount))")
    return scene
