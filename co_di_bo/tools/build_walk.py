"""Build native Rive vectors with continuous sleeve and trouser morphs."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
import xml.etree.ElementTree as ET
from motion import FRAMES,SAMPLES,arms,pants,node_tracks
from blinking import add_to_rml
from directions import add_to_rml as add_directions
from deformation import PROPS,refine_pants,vertex_tracks

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('svg_rml',ROOT.parent/'co/tools/build_co.py')
vec=importlib.util.module_from_spec(spec);spec.loader.exec_module(vec)
add=vec.add


def build(write_asset=True):
    out=ROOT/'source';qa=ROOT/'verification'
    out.mkdir(exist_ok=True);qa.mkdir(exist_ok=True)
    svg=ET.parse(ROOT/'co_di_bo.svg').getroot()
    definitions={e.get('id'):e for e in svg.iter() if e.get('id')}
    root=ET.Element('Rive',version='1',kind='fragment')
    art=add(root,'Artboard',name='Co Walking',width=489,height=868,clip='true')
    style=add(art,'LayoutComponentStyle',name='Original SVG canvas');art.set('styleId',style.get('id'))
    facing=add(art,'Node',name='FacingRoot')
    rig=add(facing,'Node',name='CharacterRoot',x=244,y=550)
    coords=add(rig,'Node',name='SVGCoordinates',x=-244,y=-550)
    morphs=[];counts={'paths':0,'gradients':0,'morph_properties':0}

    def group(parent,name,x=0,y=0):
        pivot=add(parent,'Node',name=name,x=x,y=y)
        content=add(pivot,'Node',name=name+'Coordinates',x=-x,y=-y)
        return pivot,content

    def convert(parent,i,warp=None):
        e=svg[i];tag=e.tag.split('}')[-1]
        if tag=='path':
            shape=add(parent,'Shape',name=f'SVG_{i:03d}')
            vertices=vec.path_geometry(shape,refine_pants(e.get('d')) if i==190 else e.get('d'))
            vec.color(add(shape,'Fill',fillRule='nonZero'),e.get('fill'))
            counts['paths']+=1
            if warp:
                for v in vertices:morphs.append((v,warp))
        elif tag=='circle':
            x,y,r=map(float,[e.get('cx'),e.get('cy'),e.get('r')])
            shape=add(parent,'Shape',name=f'CheekGradient_{i}',x=x,y=y,opacity=e.get('fill-opacity','1'))
            add(shape,'Ellipse',width=2*r,height=2*r)
            gradient=add(add(shape,'Fill'),'RadialGradient',startX=0,startY=0,endX=r,endY=0)
            for stop in definitions[e.get('fill')[5:-1]]:
                add(gradient,'GradientStop',position=stop.get('offset','0'),colorValue='FF'+stop.get('stop-color').lstrip('#'))
            counts['gradients']+=1
        else:raise ValueError(tag)

    details,content=group(coords,'HeadDetails',244,315)
    for i in range(223,201,-1):convert(content,i)
    hands,content=group(coords,'Hands')
    for i in range(201,194,-1):convert(content,i,arms)
    right,content=group(coords,'RightFoot',302,747)
    for i in [194,193]:convert(content,i)
    left,content=group(coords,'LeftFoot',195,750)
    for i in [192,191]:convert(content,i)
    trousers,content=group(coords,'Trousers')
    convert(content,190,pants)
    garment,content=group(coords,'Garment')
    for i in range(189,153,-1):convert(content,i,arms)
    head,content=group(coords,'Head',244,315)
    for i in range(153,-1,-1):convert(content,i)
    joints=add(coords,'Node',name='LegJoints')
    for (name,prop),value in node_tracks()[0].items():
        if name.endswith('Joint') and prop=='x':
            add(joints,'Node',name=name,x=value,y=node_tracks()[0][name,'y'])
    nodes={e.get('name'):e for e in art.iter() if e.get('name')}
    idle=add(art,'LinearAnimation',name='idle',fps=60,duration=60,loopValue='loop')
    walk=add(art,'LinearAnimation',name='walk',fps=60,duration=FRAMES,loopValue='loop')
    base,tracks=node_tracks()
    for (name,prop),values in tracks.items():
        rest=base[name,prop]
        if prop=='rotationDegrees':prop='rotation';values=[math.radians(v) for v in values]
        vec.key(walk,nodes[name],prop,list(enumerate(values)))
        vec.key(idle,nodes[name],prop,[(0,rest),(60,rest)])
    for vertex,warp in morphs:
        original={p:float(vertex.get(p)) for p in PROPS}
        for prop,keys in vertex_tracks(original,warp).items():
            vec.key(walk,vertex,prop,keys)
            vec.key(idle,vertex,prop,[(0,original[prop]),(60,original[prop])])
            counts['morph_properties']+=1
    sm=add(art,'StateMachine',name='CoWalkController');art.set('defaultStateMachineId',sm.get('id'))
    inp=add(sm,'StateMachineBool',name='is_walking',value='true')
    layer=add(sm,'StateMachineLayer',name='Walking')
    add(layer,'AnyState',x=-200,y=-160);add(layer,'ExitState',x=700,y=-160)
    entry=add(layer,'EntryState',x=-200,y=0)
    standing=add(layer,'AnimationState',animationId=idle.get('id'),reset='true',x=40,y=0)
    walking=add(layer,'AnimationState',animationId=walk.get('id'),reset='true',x=340,y=0)
    add(entry,'StateTransition',stateToId=standing.get('id'),duration=0)
    for src,target,op in [(standing,walking,'equal'),(walking,standing,'notEqual')]:
        transition=add(src,'StateTransition',stateToId=target.get('id'),duration=180,enableEarlyExit='true')
        add(transition,'TransitionBoolCondition',inputId=inp.get('id'),opValue=op)
    add_to_rml(art,sm,vec)
    add_directions(art,sm,facing,vec)
    art.remove(sm);art.insert(list(art).index(idle),sm)
    ET.indent(root)
    (out/'scene.rml').write_bytes(ET.tostring(root,encoding='utf-8',xml_declaration=True))
    (out/'rive.yaml').write_text('name: co_di_bo\nmain: Co Walking\nartboard:\n  width: 489\n  height: 868\n')
    cli=str(Path.home()/'.rive/bin/rive.exe')
    for flags,name in [(['--verify','--format=json'],'rive_verify.json'),(['--once','--format=json'],'rive_build.json')]:
        result=subprocess.run([cli,str(out),*flags],capture_output=True,text=True,encoding='utf8')
        (qa/name).write_text(result.stdout,encoding='utf8')
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    if write_asset:shutil.copyfile(out/'build/co_di_bo.riv',ROOT/'co_di_bo.riv')
    manifest={'source_sha256':hashlib.sha256((ROOT/'co_di_bo.svg').read_bytes()).hexdigest(),
        'native_vectors':True,'canvas':[489,868],'walk_seconds':FRAMES/60,
        'step_count_per_cycle':2,'cloth_morph_hz':30,'counts':counts,
        'leg_rig':'two-segment hip/knee/ankle IK, constant lengths 104/103 px',
        'swing_lift_px':28,'stride_px':32,
        'input':{'is_walking':True,'blink':'Trigger','facing_left':False},
        'direction_states':['idle','walk','idle_left','walk_left'],'auto_blink_seconds':5,
        'blink_seconds':.3,'closed_eye_details':['curved dark lash','subtle upper lid crease'],
        'joints':'Shared continuous deformation across sleeve/hand and trouser/ankle boundaries.'}
    (qa/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source-only',action='store_true')
    build(write_asset=not parser.parse_args().source_only)
