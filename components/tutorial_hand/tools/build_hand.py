"""Build native vector finger press/hold/release from the original SVG."""
from pathlib import Path
import hashlib
import json
import math
import shutil
import subprocess
import xml.etree.ElementTree as ET
from svgpathtools import parse_path, CubicBezier, Line
from motion import BASE_Y, HEIGHT, PRESS_DEPTH, RELEASE_LIFT, CONTACT_FRAME, PRESS_END_FRAME, PROFILES, TOUCH_X, TOUCH_Y, PALETTE, feedback

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
    touch=add(art,'Node',name='Touch Feedback',x=TOUCH_X,y=TOUCH_Y)
    # RML paints siblings front-to-back: inner disk, outer disk, behind the hand.
    disks={};paints=[]
    for name,size,part in [('Touch Inner',44,'inner'),('Touch Outer',68,'outer')]:
        shape=add(touch,'Shape',name=name,opacity=0,scaleX=.001,scaleY=.001)
        disks[part]=shape
        add(shape,'Ellipse',width=size,height=size)
        paints.append(add(add(shape,'Fill'),'SolidColor',colorValue='FF'+PALETTE[0][1][1:]))
    animations=[]
    for name,profile in PROFILES.items():
        duration=profile[-1][0]
        anim=add(art,'LinearAnimation',name=name,fps=60,duration=duration,loopValue='loop' if name in ('idle','hold') else 'oneShot')
        animations.append(anim)
        key(anim,hand,'y',[(f,BASE_Y) for f,offset in profile])
        for vertex in finger_vertices:
            base_y=float(vertex.get('y'))
            key(anim,vertex,'y',[(f,base_y+offset) for f,offset in profile])
        for part,disk in disks.items():
            for prop in ['scaleX','scaleY','opacity']:
                key(anim,disk,prop,[(f,feedback(f,name,part)[int(prop=='opacity')]) for f,offset in profile])
    sm=add(art,'StateMachine',name='TutorialHand');art.set('defaultStateMachineId',sm.get('id'))
    inp=add(sm,'StateMachineBool',name='is_pressed',value='false')
    layer=add(sm,'StateMachineLayer',name='Finger gesture')
    add(layer,'AnyState',x=-250,y=-150);add(layer,'ExitState',x=1000,y=-150)
    entry=add(layer,'EntryState',x=-250,y=0)
    states=[add(layer,'AnimationState',animationId=a.get('id'),reset='true',x=i*240,y=0) for i,a in enumerate(animations)]
    add(entry,'StateTransition',stateToId=states[0].get('id'))
    def tr(a,b,pressed=None,exit=False,duration=0,**extra):
        attrs=dict(stateToId=states[b].get('id'),duration=duration,enableEarlyExit='true')
        if exit:attrs.update(enableExitTime='true',exitTimeIsPercetange='true',exitTime=100)
        attrs.update(extra)
        node=add(states[a],'StateTransition',**attrs)
        if pressed is not None:add(node,'TransitionBoolCondition',inputId=inp.get('id'),opValue='equal' if pressed else 'notEqual')
    tr(0,1,True)
    tr(1,3,False,duration=60,enableExitTime='true',exitTime=CONTACT_FRAME*1000//60)
    # A cancelled press before contact returns directly to idle without a flash.
    tr(1,0,False,duration=180)
    tr(1,2,True,exit=True)
    tr(2,3,False)
    tr(3,1,True,duration=60)
    tr(3,0,False,exit=True)
    color_input=add(sm,'StateMachineNumber',name='paintColor',value=0)
    colors=add(sm,'StateMachineLayer',name='Paint color selection')
    add(colors,'AnyState',x=-240,y=-160);add(colors,'ExitState',x=800,y=-160)
    color_entry=add(colors,'EntryState',x=-240,y=0);color_states=[]
    for index,(name,hex_color) in enumerate(PALETTE):
        anim=add(art,'LinearAnimation',name='Paint_Color_'+name,fps=60,duration=1,loopValue='oneShot')
        for paint in paints:
            ko=add(anim,'KeyedObject',objectId=paint.get('id'))
            kp=add(ko,'KeyedProperty',property='colorValue')
            add(kp,'KeyFrameColor',frame=0,value='FF'+hex_color[1:],interpolationType='hold')
        color_states.append(add(colors,'AnimationState',animationId=anim.get('id'),x=index*240,y=150))
    for source_index,source in [(-1,color_entry),*enumerate(color_states)]:
        for target in [1,2,0]:
            if source_index==target:continue
            transition=add(source,'StateTransition',stateToId=color_states[target].get('id'),duration=0)
            for op,value in ([('notEqual',1),('notEqual',2)] if target==0 else [('equal',target)]):
                add(transition,'TransitionNumberCondition',inputId=color_input.get('id'),opValue=op,value=value)
    art.remove(sm);art.insert(list(art).index(animations[0]),sm)
    ET.indent(root)
    (OUT/'scene.rml').write_bytes(ET.tostring(root,encoding='utf-8',xml_declaration=True))
    (OUT/'rive.yaml').write_text(f'name: tutorial_hand\nmain: Tutorial Hand\nartboard:\n  width: 227\n  height: {HEIGHT}\n')
    for args,name in [(['--verify','--format=json'],'rive_verify.json'),(['--once','--format=json'],'rive_build.json')]:
        p=subprocess.run(['rive',str(OUT),*args],capture_output=True,text=True,encoding='utf8')
        (QA/name).write_text(p.stdout,encoding='utf8')
        if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    shutil.copyfile(OUT/'build/tutorial_hand.riv',ROOT/'tutorial_hand.riv')
    (QA/'source_manifest.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256((ROOT/'tutorial_hand.svg').read_bytes()).hexdigest(),native_vectors=True,canvas=[227,HEIGHT],source_crop=[0,-BASE_Y,227,342],press_seconds=PRESS_END_FRAME/60,contact_seconds=CONTACT_FRAME/60,release_seconds=.6,fingertip_translation_y=PRESS_DEPTH,release_lift_px=RELEASE_LIFT,palm_stationary=True,fingertip_handles_unchanged=True,animated_vertex_indices=[6,7,8]),indent=2))
    print('Built',ROOT/'tutorial_hand.riv')

if __name__=='__main__':build()
