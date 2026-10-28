"""Build native vector finger press/hold/release from the original SVG."""
from pathlib import Path
import hashlib
import json
import math
import shutil
import subprocess
import xml.etree.ElementTree as ET
from svgpathtools import parse_path, CubicBezier, Line
from motion import BASE_Y, HEIGHT, PRESS_DEPTH, RELEASE_LIFT, PROFILES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'source'
QA = ROOT / 'verification'
counter = 0

def add(parent, tag, **attrs):
    global counter
    counter += 1
    return ET.SubElement(parent, tag, {**{k:str(v) for k,v in attrs.items()}, 'id':f'0:{counter}'})

def values(p, a, b):
    return dict(x=p.real,y=p.imag,inRotation=math.atan2(a.imag,a.real),inDistance=abs(a),outRotation=math.atan2(b.imag,b.real),outDistance=abs(b))

def geometry(shape, data):
    vertices = []
    for sub in parse_path(data).continuous_subpaths():
        segs=list(sub); path=add(shape,'PointsPath',isClosed=str(sub.isclosed()).lower())
        def handles(s):
            if isinstance(s,CubicBezier): return s.control1,s.control2
            if isinstance(s,Line): return s.start,s.end
            raise ValueError(type(s))
        for i,s in enumerate(segs):
            p=s.start; a=handles(segs[i-1])[1]; b=handles(s)[0]
            rest=values(p,a-p,b-p)
            vertex=add(path,'CubicDetachedVertex',**rest)
            vertices.append(vertex)
    return vertices

def key(anim,obj,prop,seq):
    ko=add(anim,'KeyedObject',objectId=obj.get('id'))
    kp=add(ko,'KeyedProperty',property=prop)
    for frame,value in seq:
        add(kp,'KeyFrameDouble',frame=frame,value=f'{value:.9f}',interpolationType='linear')

def build():
    OUT.mkdir(exist_ok=True);QA.mkdir(exist_ok=True)
    root=ET.Element('Rive',version='1',kind='fragment')
    art=add(root,'Artboard',name='Tutorial Hand',width=227,height=HEIGHT,clip='true')
    style=add(art,'LayoutComponentStyle',name='Original SVG canvas');art.set('styleId',style.get('id'))
    hand=add(art,'Node',name='Hand',y=BASE_Y)
    finger_vertices=[]
    svg=ET.parse(ROOT/'tutorial_hand.svg').getroot()
    for i,e in reversed(list(enumerate(svg))):
        shape=add(hand,'Shape',name='Hand silhouette' if i==0 else f'Finger crease {i}')
        vertices=geometry(shape,e.get('d'))
        if i==0:
            # These three vertices define the entire rounded fingertip. Move them
            # together, preserving x and all handles, while the two straight sides
            # shorten vertically into the fixed palm.
            finger_vertices=vertices[6:9]
        add(add(shape,'Fill'),'SolidColor',colorValue='FF'+e.get('fill').lstrip('#'))
    animations=[]
    for name,profile in PROFILES.items():
        duration=profile[-1][0]
        anim=add(art,'LinearAnimation',name=name,fps=60,duration=duration,loopValue='loop' if name in ('idle','hold') else 'oneShot')
        animations.append(anim)
        key(anim,hand,'y',[(f,BASE_Y) for f,offset in profile])
        for vertex in finger_vertices:
            base_y=float(vertex.get('y'))
            key(anim,vertex,'y',[(f,base_y+offset) for f,offset in profile])
    sm=add(art,'StateMachine',name='TutorialHand');art.set('defaultStateMachineId',sm.get('id'))
    inp=add(sm,'StateMachineBool',name='is_pressed',value='false')
    layer=add(sm,'StateMachineLayer',name='Finger gesture')
    add(layer,'AnyState',x=-250,y=-150);add(layer,'ExitState',x=1000,y=-150)
    entry=add(layer,'EntryState',x=-250,y=0)
    states=[add(layer,'AnimationState',animationId=a.get('id'),reset='true',x=i*240,y=0) for i,a in enumerate(animations)]
    add(entry,'StateTransition',stateToId=states[0].get('id'))
    def tr(a,b,pressed=None,exit=False,duration=0):
        attrs=dict(stateToId=states[b].get('id'),duration=duration,enableEarlyExit='true')
        if exit:attrs.update(enableExitTime='true',exitTimeIsPercetange='true',exitTime=100)
        node=add(states[a],'StateTransition',**attrs)
        if pressed is not None:add(node,'TransitionBoolCondition',inputId=inp.get('id'),opValue='equal' if pressed else 'notEqual')
    tr(0,1,True)
    tr(1,3,False,duration=60)
    tr(1,2,True,exit=True)
    tr(2,3,False)
    tr(3,1,True,duration=60)
    tr(3,0,False,exit=True)
    art.remove(sm);art.insert(list(art).index(animations[0]),sm)
    ET.indent(root)
    (OUT/'scene.rml').write_bytes(ET.tostring(root,encoding='utf-8',xml_declaration=True))
    (OUT/'rive.yaml').write_text(f'name: tutorial_hand\nmain: Tutorial Hand\nartboard:\n  width: 227\n  height: {HEIGHT}\n')
    for args,name in [(['--verify','--format=json'],'rive_verify.json'),(['--once','--format=json'],'rive_build.json')]:
        p=subprocess.run(['rive',str(OUT),*args],capture_output=True,text=True,encoding='utf8')
        (QA/name).write_text(p.stdout,encoding='utf8')
        if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    shutil.copyfile(OUT/'build/tutorial_hand.riv',ROOT/'tutorial_hand.riv')
    (QA/'source_manifest.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256((ROOT/'tutorial_hand.svg').read_bytes()).hexdigest(),native_vectors=True,canvas=[227,HEIGHT],source_crop=[0,-BASE_Y,227,342],press_seconds=.6,release_seconds=.6,fingertip_translation_y=PRESS_DEPTH,release_lift_px=RELEASE_LIFT,palm_stationary=True,fingertip_handles_unchanged=True,animated_vertex_indices=[6,7,8]),indent=2))
    print('Built',ROOT/'tutorial_hand.riv')

if __name__=='__main__':build()
