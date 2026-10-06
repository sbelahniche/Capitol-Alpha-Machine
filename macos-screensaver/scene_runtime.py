"""Optimize exported saver scenes without editing the main site's animations."""
from pathlib import Path


def replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise ValueError(f"Scene source changed; expected one occurrence of {old[:80]!r}")
    return source.replace(old, new, 1)


def optimize_scene(scene: str, number: str, *, preview: bool = False) -> str:
    runtime = (Path(__file__).parent / 'runtime.js').read_text().replace(
        '__CAPITOL_PREVIEW__', 'true' if preview else 'false')
    scene = replace_once(scene, '</head>', f'<script>{runtime}</script>\n</head>')
    scene = replace_once(scene, "const ctx=cv.getContext('2d');",
                         "const ctx=cv.getContext('2d', {alpha:false});\nwindow.__capitolCacheText(ctx);")
    # Limit backing-store work on Retina/4K/5K displays; keep CSS coordinates.
    scene = replace_once(scene, 'DPR=Math.min(2,window.devicePixelRatio||1);',
                         'DPR=Math.min(2,window.devicePixelRatio||1,Math.sqrt(4000000/(W*H)));')
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
    if number in ('04', '05'):
        # Flooring fractional progress every frame stranded Returns at zero
        # (22 * 1/60 < 1). Accumulate first, round only the displayed count.
        rate = '22' if number == '04' else '70'
        scene = replace_once(scene, f'Math.floor(tradeCount+dt*{rate})', f'tradeCount+dt*{rate}')
        scene = replace_once(scene, "z4(tradeCount)", "z4(Math.floor(tradeCount))")
    return scene
