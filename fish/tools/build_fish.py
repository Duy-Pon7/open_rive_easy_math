"""Convert original fish SVG paths into native Rive vectors and animation."""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
import xml.etree.ElementTree as ET
from motion import BASE, FRAMES, tracks

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('svg_rml',ROOT.parent/'co/tools/build_co.py')
vec=importlib.util.module_from_spec(spec)
spec.loader.exec_module(vec)
add=vec.add


def build():
    out=ROOT/'source';qa=ROOT/'verification'
    out.mkdir(exist_ok=True);qa.mkdir(exist_ok=True)
    svg=ET.parse(ROOT/'fish.svg').getroot()
    root=ET.Element('Rive',version='1',kind='fragment')
    art=add(root,'Artboard',name='Fish',width=1570,height=1001,clip='true')
    style=add(art,'LayoutComponentStyle',name='Original SVG canvas')
    art.set('styleId',style.get('id'))
    fish=add(art,'Node',name='FishRoot',x=900,y=500)
    coords=add(fish,'Node',name='SVGCoordinates',x=-900,y=-500)

    def group(parent,name,x=0,y=0):
        pivot=add(parent,'Node',name=name,x=x,y=y)
        content=add(pivot,'Node',name=name+'Coordinates',x=-x,y=-y)
        return pivot,content

    def path(parent,index):
        element=svg[index]
        assert element.tag.split('}')[-1]=='path'
        shape=add(parent,'Shape',name=f'SVG_{index:02d}')
        vec.path_geometry(shape,element.get('d'))
        vec.color(add(shape,'Fill',fillRule='nonZero'),element.get('fill'))

    # RML sibling drawing order is the reverse of SVG painter order.
    body,content=group(coords,'Body')
    for i in [14,13,12,11]:path(content,i)
    pectoral,fincontent=group(content,'PectoralFin',1010,585)
    path(fincontent,10)
    path(content,9);path(content,8)
    # The body covers the inset fin roots throughout their rotations.
    dorsal,content=group(coords,'DorsalFin',900,298)
    for i in range(20,14,-1):path(content,i)
    ventral,content=group(coords,'VentralFin',872,727)
    for i in range(26,20,-1):path(content,i)
    tail,content=group(coords,'Tail',600,505)
    for i in range(7,-1,-1):path(content,i)
    nodes={e.get('name'):e for e in art.iter() if e.get('name')}
    idle=add(art,'LinearAnimation',name='idle',fps=60,duration=60,loopValue='loop')
    swim=add(art,'LinearAnimation',name='swim',fps=60,duration=FRAMES,loopValue='loop')
    for (name,prop),values in tracks().items():
        base=BASE[name,prop]
        if prop=='rotationDegrees':
            prop='rotation';values=[math.radians(v) for v in values];base=math.radians(base)
        vec.key(swim,nodes[name],prop,list(enumerate(values)))
        vec.key(idle,nodes[name],prop,[(0,base),(60,base)])
    sm=add(art,'StateMachine',name='FishController')
    art.set('defaultStateMachineId',sm.get('id'))
    swimming=add(sm,'StateMachineBool',name='is_swimming',value='true')
    layer=add(sm,'StateMachineLayer',name='Swimming')
    add(layer,'AnyState',x=-200,y=-160);add(layer,'ExitState',x=700,y=-160)
    entry=add(layer,'EntryState',x=-200,y=0)
    standing=add(layer,'AnimationState',animationId=idle.get('id'),reset='true',x=40,y=0)
    moving=add(layer,'AnimationState',animationId=swim.get('id'),reset='true',x=340,y=0)
    add(entry,'StateTransition',stateToId=standing.get('id'),duration=0)
    transition=add(standing,'StateTransition',stateToId=moving.get('id'),duration=180,enableEarlyExit='true')
    add(transition,'TransitionBoolCondition',inputId=swimming.get('id'),opValue='equal')
    transition=add(moving,'StateTransition',stateToId=standing.get('id'),duration=180,enableEarlyExit='true')
    add(transition,'TransitionBoolCondition',inputId=swimming.get('id'),opValue='notEqual')
    art.remove(sm);art.insert(list(art).index(idle),sm)
    ET.indent(root)
    (out/'scene.rml').write_bytes(ET.tostring(root,encoding='utf-8',xml_declaration=True))
    (out/'rive.yaml').write_text('name: fish_swim\nmain: Fish\nartboard:\n  width: 1570\n  height: 1001\n')
    cli=str(Path.home()/'.rive/bin/rive.exe')
    for flags,name in [(['--verify','--format=json'],'rive_verify.json'),(['--once','--format=json'],'rive_build.json')]:
        p=subprocess.run([cli,str(out),*flags],capture_output=True,text=True,encoding='utf8')
        (qa/name).write_text(p.stdout,encoding='utf8')
        if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    shutil.copyfile(out/'build/fish_swim.riv',ROOT/'fish_swim.riv')
    (qa/'source_manifest.json').write_text(json.dumps({'source_sha256':hashlib.sha256((ROOT/'fish.svg').read_bytes()).hexdigest(),
        'native_vectors':True,'svg_paths_preserved':len(svg),'canvas':[1570,1001],
        'swim_loop_seconds':FRAMES/60,'tail_beat_seconds':FRAMES/120,
        'fin_roots_inset_px':{'dorsal':12,'ventral':20},
        'input':{'is_swimming':True}},indent=2))
    print('Built fish_swim.riv',flush=True)


if __name__=='__main__':build()
