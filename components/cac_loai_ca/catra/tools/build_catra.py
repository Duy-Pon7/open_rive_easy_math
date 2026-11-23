"""Native SVG vectors, connected tail deformation and fin animation via OpenRive MCP."""
from pathlib import Path
import argparse
import base64
import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np
from svgpathtools import CubicBezier, Line, Path as SvgPath, parse_path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
SOURCE = ROOT.parent/'catra.svg'
WIDTH, HEIGHT = 196, 115
OFFSET = (20, 20)
FRAMES = 120
spec = importlib.util.spec_from_file_location('vectors', REPO/'co/tools/build_co.py')
vec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vec)
sys.path.insert(0, str(REPO/'loa_doc/tools'))
from mcp_client import OpenRive


def subdivide(data):
    paths = []
    for contour in parse_path(data).continuous_subpaths():
        pieces = []
        for segment in contour:
            assert isinstance(segment, (CubicBezier, Line))
            span = abs(segment.end-segment.start)
            if isinstance(segment, CubicBezier):
                span = max(span, abs(segment.control1-segment.start), abs(segment.control2-segment.end))
            n = max(1, math.ceil(span/9))
            for i in range(n):
                part = segment.cropped(i/n, (i+1)/n)
                start = pieces[-1].end if pieces else part.start
                end = segment.end if i==n-1 else part.end
                pieces.append(CubicBezier(start,part.control1,part.control2,end) if isinstance(part,CubicBezier) else Line(start,end))
        paths.append(SvgPath(*pieces).d())
    return ' '.join(paths)


def deformation(frame):
    """A continuous rear-body wave keeps all body layers and masks attached."""
    xs = np.arange(-30,201,.25)
    u = np.maximum(0, (70-xs)/70)
    phase = 2*math.pi*(2*frame/FRAMES-.32*u)
    wave = 4.2*u**1.65*np.sin(phase)
    slope = -4.2/70*(1.65*u**.65*np.sin(phase)-2*math.pi*.32*u**1.65*np.cos(phase))
    tx = np.sqrt(1-np.clip(slope,-.85,.85)**2)
    integral = np.r_[0,np.cumsum((tx[:-1]+tx[1:])*.125)]
    xmap = 100+integral-np.interp(100,xs,integral)
    def point(p):
        x,y = p.real,p.imag
        sy = float(np.interp(x,xs,slope))
        sx = math.sqrt(1-min(.85,abs(sy))**2)
        return complex(float(np.interp(x,xs,xmap))-(y-37)*sy,
                       37+float(np.interp(x,xs,wave))+(y-37)*sx)
    return point


def fin_tracks():
    result = {}
    for f in range(0,FRAMES+1,2):
        t = 2*math.pi*f/FRAMES
        values = {
            ('FishRoot','x'):20+.65*math.sin(t),
            ('FishRoot','y'):20+.55*math.sin(t),
            ('DorsalFin','y'):19.3,
            ('DorsalFin','rotationDegrees'):4.5*math.sin(2*t-.5),
            ('DorsalFin','scaleX'):1-.035*math.sin(2*t-.5)**2,
            ('PelvicFin','y'):48.5,
            ('PelvicFin','rotationDegrees'):6*math.sin(2*t+.7),
            ('PelvicFin','scaleY'):1-.12*math.sin(2*t+.7)**2,
            ('AnalFin','y'):57.5,
            ('AnalFin','rotationDegrees'):7*math.sin(4*t+.2),
            ('AnalFin','scaleY'):1-.15*math.sin(4*t+.2)**2,
            ('PectoralFin','rotationDegrees'):8*math.sin(4*t-.6),
            ('PectoralFin','scaleY'):1-.14*math.sin(4*t-.6)**2,
        }
        for key,value in values.items():
            result.setdefault(key,[]).append((f,round(value,8)))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base',default='http://127.0.0.1:56545')
    args = parser.parse_args()
    source=ROOT/'source';qa=ROOT/'verification'
    source.mkdir(parents=True,exist_ok=True);qa.mkdir(exist_ok=True)
    svg=ET.parse(SOURCE).getroot()
    definitions={e.get('id'):e for e in svg.iter() if e.get('id')}
    add=vec.add
    root=ET.Element('Rive',version='1',kind='fragment')
    art=add(root,'Artboard',name='Ca Tra',width=WIDTH,height=HEIGHT,clip='true')
    style=add(art,'LayoutComponentStyle',name='Transparent canvas with fin clearance')
    art.set('styleId',style.get('id'))
    coords=add(art,'Node',name='FishRoot',x=OFFSET[0],y=OFFSET[1])
    vertices=[]

    def geometry(shape,data,label):
        vs=vec.path_geometry(shape,subdivide(data))
        for i,v in enumerate(vs):
            v.set('name',f'{label} vertex {i}')
            p=complex(float(v.get('x')),float(v.get('y')))
            a=float(v.get('inDistance'))*complex(math.cos(float(v.get('inRotation'))),math.sin(float(v.get('inRotation'))))
            b=float(v.get('outDistance'))*complex(math.cos(float(v.get('outRotation'))),math.sin(float(v.get('outRotation'))))
            if p.real<85 or (p+a).real<85 or (p+b).real<85:
                vertices.append((v,p,a,b))

    def convert(parent,e,name,clips=()):
        tag=e.tag.split('}')[-1]
        if tag in ('mask','defs'):return
        if tag=='g':
            group=add(parent,'Node',name=name)
            if e.get('mask'):
                clipper=add(group,'Shape',name=name+' mask')
                for child in definitions[e.get('mask')[5:-1]]:
                    geometry(clipper,child.get('d'),name+' mask')
                clips+=(clipper.get('id'),)
            for i,child in reversed(list(enumerate(e))):
                convert(group,child,f'{name}.{i}',clips)
            return
        assert tag=='path'
        fins={'Dorsal fin':('DorsalFin',90,18),'Anal fin':('AnalFin',85,59),'Pelvic fin':('PelvicFin',58,50),'Pectoral fin':('PectoralFin',105,47)}
        if name in fins:
            label,x,y=fins[name]
            pivot=add(parent,'Node',name=label,x=x,y=y)
            parent=add(pivot,'Node',name=label+'Coordinates',x=-x,y=-y)
        shape=add(parent,'Shape',name=name)
        geometry(shape,e.get('d'),name)
        if e.get('fill','none')!='none':vec.color(add(shape,'Fill',fillRule='nonZero'),e.get('fill'))
        for clip in clips:add(shape,'ClippingShape',sourceId=clip)

    labels={0:'Dorsal fin',1:'Anal fin',2:'Pelvic fin',3:'Body and tail',5:'Body shading',6:'Pectoral fin',7:'Gill flap',8:'Eye white',10:'Pupil'}
    for i,e in reversed(list(enumerate(svg))):convert(coords,e,labels.get(i,f'SVG {i}'))
    idle=add(art,'LinearAnimation',name='idle',fps=60,duration=60,loopValue='loop')
    swim=add(art,'LinearAnimation',name='swim',fps=60,duration=FRAMES,loopValue='loop')
    samples=list(range(0,FRAMES+1,2));maps=[deformation(f) for f in samples]
    for v,p,a,b in vertices:
        poses=[]
        for transform in maps:
            q=transform(p);poses.append(vec.vertex_values(q,transform(p+a)-q,transform(p+b)-q))
        for prop in ('x','y','inRotation','inDistance','outRotation','outDistance'):
            numbers=[float(pose[prop]) for pose in poses]
            base=float(v.get(prop))
            if prop.endswith('Rotation'):
                numbers=np.unwrap(numbers).tolist()
                base+=round((numbers[0]-base)/(2*math.pi))*2*math.pi
                v.set(prop,str(base))
            vec.key(idle,v,prop,[(0,base),(60,base)])
            vec.key(swim,v,prop,list(zip(samples,numbers)))
    sm=add(art,'StateMachine',name='CaTraController');art.set('defaultStateMachineId',sm.get('id'))
    swimming=add(sm,'StateMachineBool',name='is_swimming',value='false')
    layer=add(sm,'StateMachineLayer',name='Locomotion')
    add(layer,'AnyState',x=-200,y=-150);add(layer,'ExitState',x=650,y=-150)
    entry=add(layer,'EntryState',x=-200,y=0)
    rest=add(layer,'AnimationState',animationId=idle.get('id'),reset='true',x=40,y=0)
    moving=add(layer,'AnimationState',animationId=swim.get('id'),reset='true',x=340,y=0)
    add(entry,'StateTransition',stateToId=rest.get('id'),duration=0)
    for start,end,op in [(rest,moving,'equal'),(moving,rest,'notEqual')]:
        transition=add(start,'StateTransition',stateToId=end.get('id'),duration=200,enableEarlyExit='true')
        add(transition,'TransitionBoolCondition',inputId=swimming.get('id'),opValue=op)
    art.remove(sm);art.insert(list(art).index(idle),sm)
    ET.indent(root)
    (source/'scene.rml').write_bytes(ET.tostring(root,encoding='utf-8',xml_declaration=True))
    (source/'rive.yaml').write_text(f'name: catra\nmain: Ca Tra\nartboard:\n  width: {WIDTH}\n  height: {HEIGHT}\n')
    cli=str(Path.home()/'.rive/bin/rive.exe')
    for flags,filename in [(['--verify','--format=json'],'rive_verify.json'),(['--once','--format=json'],'rive_build.json')]:
        result=subprocess.run([cli,str(source),*flags],capture_output=True,text=True,encoding='utf8')
        (qa/filename).write_text(result.stdout,encoding='utf8')
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    client=OpenRive(args.base)
    meta_path=ROOT/'openrive.json';local=source/'build/catra.riv'
    encoded=base64.b64encode(local.read_bytes()).decode()
    if meta_path.exists():
        project=json.loads(meta_path.read_text())['project_id']
        snapshot=client.snapshot(project)
        (qa/'before-rebuild.json').write_text(json.dumps(snapshot))
        made=client.call('import_riv',dict(name='Ca Tra rebuild staging',dataBase64=encoded))
        staging=made['id']
        client.update(project,client.snapshot(staging)['doc'],snapshot['meta']['updatedAt'])
        client.call('delete_project',dict(project=staging))
    else:
        made=client.call('import_riv',dict(name='Ca Tra - Idle and Swim',dataBase64=encoded));project=made['id']
    meta=dict(project_id=project,base_url=args.base,editor_url=args.base+'/editor/'+project)
    meta_path.write_text(json.dumps(meta,indent=2))
    baseline={('FishRoot','x'):20,('FishRoot','y'):20,('DorsalFin','y'):18,('DorsalFin','rotationDegrees'):0,('DorsalFin','scaleX'):1,('PelvicFin','y'):50,('PelvicFin','rotationDegrees'):0,('PelvicFin','scaleY'):1,('AnalFin','y'):59,('AnalFin','rotationDegrees'):0,('AnalFin','scaleY'):1,('PectoralFin','rotationDegrees'):0,('PectoralFin','scaleY'):1}
    ops=[]
    for (obj,prop),samples in fin_tracks().items():
        for timeline,values in [('swim',samples),('idle',[(0,baseline[obj,prop]),(60,baseline[obj,prop])])]:
            ops.append(dict(op='add_keyframes',timeline=timeline,object=obj,property=prop,keys=[dict(frame=f,value=v,ease='linear') for f,v in values]))
    result=client.call('apply_edit_plan',dict(project=project,operations=ops))
    (qa/'animation-mcp.json').write_text(json.dumps(result,indent=2))
    for tool,filename in [('get_project','openrive-inspect.json'),('diagnose_project','openrive-diagnostics.json')]:
        result=client.call(tool,dict(project=project));(qa/filename).write_text(json.dumps(result,indent=2))
        if tool=='diagnose_project':
            assert result['valid'],result
            print(json.dumps(result),flush=True)
    result=client.call('export_riv',dict(project=project));data=base64.b64decode(result['dataBase64'])
    (ROOT/'catra.riv').write_bytes(data)
    (ROOT/'openrive-project.json').write_text(json.dumps(client.snapshot(project)['doc'],indent=2))
    (qa/'manifest.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),rive_sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),canvas=[WIDTH,HEIGHT],svg_offset=OFFSET,loop_seconds=FRAMES/60,tail_beat_seconds=1,animated_vertices=len(vertices),default_is_swimming=False),indent=2))
    runtime=ROOT/'runtime';runtime.mkdir(exist_ok=True)
    for name in ['canvas_advanced.mjs','rive.wasm','rive_fallback.wasm','package.json']:shutil.copyfile(REPO/'fish/runtime'/name,runtime/name)
    print(meta['editor_url'],flush=True)


if __name__=='__main__':main()
