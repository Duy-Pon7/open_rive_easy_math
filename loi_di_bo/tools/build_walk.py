"""Build Loi's native vectors and walking controller from the untouched SVG."""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
import xml.etree.ElementTree as ET
from motion import FRAMES,body,pants,arms,shirt,node_tracks
from deformation import PROPS,vertex_tracks,refine_pants,black_garment_paths
from blinking import add_to_rml
from directions import add_to_rml as add_directions

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('svg_rml',ROOT.parent/'co/tools/build_co.py')
vec=importlib.util.module_from_spec(spec);spec.loader.exec_module(vec)
add=vec.add
WIDTH,HEIGHT,PAD=376,866,24

def build():
    out=ROOT/'source';qa=ROOT/'verification'
    out.mkdir(exist_ok=True);qa.mkdir(exist_ok=True)
    svg=ET.parse(ROOT/'loi_di_bo.svg').getroot()
    definitions={e.get('id'):e for e in svg.iter() if e.get('id')}
    root=ET.Element('Rive',version='1',kind='fragment')
    art=add(root,'Artboard',name='Loi Walking',width=WIDTH,height=HEIGHT,clip='true')
    style=add(art,'LayoutComponentStyle',name='Canvas with motion margin');art.set('styleId',style.get('id'))
    facing=add(art,'Node',name='FacingRoot')
    margin=add(facing,'Node',name='MotionMargin',x=PAD,y=PAD)
    rig=add(margin,'Node',name='CharacterRoot',x=180,y=550)
    coords=add(rig,'Node',name='SVGCoordinates',x=-180,y=-550)
    morphs=[];counts={'paths':0,'gradients':0,'morph_properties':0}
    def group(name,x=0,y=0):
        pivot=add(coords,'Node',name=name,x=x,y=y)
        return add(pivot,'Node',name=name+'Coordinates',x=-x,y=-y)
    def convert(parent,i,warp=None):
        e=svg[i];tag=e.tag.split('}')[-1]
        shape=add(parent,'Shape',name=f'SVG_{i:03d}',opacity=e.get('fill-opacity','1'))
        if tag=='path':
            d=e.get('d')
            vertices=vec.path_geometry(shape,refine_pants(d) if i==0 else d)
            fill=add(shape,'Fill',fillRule='nonZero')
            if e.get('fill').startswith('url'):
                cx,cy,r=(279,236,28)
                gradient=add(fill,'RadialGradient',startX=cx,startY=cy,endX=cx+r,endY=cy)
                for stop in definitions[e.get('fill')[5:-1]]:
                    add(gradient,'GradientStop',position=stop.get('offset','0'),colorValue='FF'+stop.get('stop-color').lstrip('#'))
                counts['gradients']+=1
            else:vec.color(fill,e.get('fill'))
            if warp:morphs.extend((v,warp) for v in vertices)
            counts['paths']+=1
        elif tag=='circle':
            x,y,r=map(float,[e.get('cx'),e.get('cy'),e.get('r')])
            shape.set('x',str(x));shape.set('y',str(y))
            add(shape,'Ellipse',width=2*r,height=2*r)
            gradient=add(add(shape,'Fill'),'RadialGradient',startX=0,startY=0,endX=r,endY=0)
            for stop in definitions[e.get('fill')[5:-1]]:
                add(gradient,'GradientStop',position=stop.get('offset','0'),colorValue='FF'+stop.get('stop-color').lstrip('#'))
            counts['gradients']+=1
        else:raise ValueError(tag)
    # Rive siblings draw front to back; preserve original SVG overlap order.
    head=group('Head',190,292)
    for i in [113,112,*range(107,88,-1)]:convert(head,i)
    right=group('RightFoot',232,715)
    for i in [111,110]:convert(right,i)
    left=group('LeftFoot',123,724)
    for i in [109,108]:convert(left,i)
    garment=group('Garment')
    for i in range(88,0,-1):
        convert(garment,i,pants if i in [1,2,3,4,5,6,34,85,87] else arms)
    # The original black path included both palms and the trouser outline.
    # Separate it so an arm swing cannot drag a black flap out of the hip.
    for name,d,warp in zip(['SVG_000','TrousersContour'],black_garment_paths(svg),[shirt,pants]):
        shape=add(garment,'Shape',name=name)
        vertices=vec.path_geometry(shape,refine_pants(d))
        vec.color(add(shape,'Fill',fillRule='nonZero'),'#1A1919')
        morphs.extend((v,warp) for v in vertices)
        counts['paths']+=1
    joints=add(coords,'Node',name='LegJoints')
    base,tracks=node_tracks()
    for (name,prop),value in base.items():
        if name.endswith('Joint') and prop=='x':add(joints,'Node',name=name,x=value,y=base[name,'y'])
    nodes={e.get('name'):e for e in art.iter() if e.get('name')}
    idle=add(art,'LinearAnimation',name='idle',fps=60,duration=60,loopValue='loop')
    walk=add(art,'LinearAnimation',name='walk',fps=60,duration=FRAMES,loopValue='loop')
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
    sm=add(art,'StateMachine',name='LoiWalkController');art.set('defaultStateMachineId',sm.get('id'))
    add(sm,'StateMachineBool',name='is_walking',value='true')
    add(sm,'StateMachineLayer',name='Walking')
    add_to_rml(art,sm,vec)
    add_directions(art,sm,facing,vec)
    art.remove(sm);art.insert(list(art).index(idle),sm)
    ET.indent(root)
    (out/'scene.rml').write_bytes(ET.tostring(root,encoding='utf-8',xml_declaration=True))
    (out/'rive.yaml').write_text(f'name: loi_di_bo\nmain: Loi Walking\nartboard:\n  width: {WIDTH}\n  height: {HEIGHT}\n')
    cli=str(Path.home()/'.rive/bin/rive.exe')
    for flags,name in [(['--verify','--format=json'],'rive_verify.json'),(['--once','--format=json'],'rive_build.json')]:
        result=subprocess.run([cli,str(out),*flags],capture_output=True,text=True,encoding='utf8')
        (qa/name).write_text(result.stdout,encoding='utf8')
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    shutil.copyfile(out/'build/loi_di_bo.riv',ROOT/'loi_di_bo.riv')
    manifest={'source_sha256':hashlib.sha256((ROOT/'loi_di_bo.svg').read_bytes()).hexdigest(),
              'canvas':[WIDTH,HEIGHT],'svg_offset':[PAD,PAD],'native_vectors':True,'walk_seconds':FRAMES/60,
              'counts':counts,'step_count_per_cycle':2,'lift_px':28,'stride_px':24,
              'leg_rig':'Two-segment IK, continuous trouser silhouette and sleeve morphs, Jacobian tangents',
              'keyframe_tolerance':{'coordinates_px':.06,'tangent_angles_rad':.0005},
              'state_machine':'LoiWalkController','inputs':{'is_walking':True,'blink':'Trigger','facing_left':False}}
    (qa/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest),flush=True)

if __name__=='__main__':build()
