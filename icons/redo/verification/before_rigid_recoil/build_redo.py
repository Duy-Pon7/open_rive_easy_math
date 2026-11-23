"""Travel a solid arrowhead around the ring with its body trailing behind."""
from pathlib import Path
import json, math, shutil, subprocess, xml.etree.ElementTree as ET
from svgpathtools import parse_path, Path as SVGPath, CubicBezier, Line

ROOT = Path(__file__).resolve().parents[1]
counter = 0
CENTER=complex(26,24)
BASE=complex((40.1444+35.8619)/2,(4.69182+9.00616)/2)
RADIUS=abs(BASE-CENTER)
END_ANGLE=math.atan2((BASE-CENTER).imag,(BASE-CENTER).real)+math.tau
START_ANGLE=math.pi/4
TANGENT=complex(-math.sin(END_ANGLE),math.cos(END_ANGLE))
HEAD_WEIGHTS=[0,.35,.7,.95,1,1,.9,.7,.4,.2,0]

def add(parent, tag, **attrs):
    global counter
    counter += 1
    return ET.SubElement(parent, tag, {**{k:str(v) for k,v in attrs.items()}, 'id':f'0:{counter}'})

def ease(t):
    return t*t*t*(t*(t*6-15)+10)

def interpolate(frame, points):
    for (a,x),(b,y) in zip(points,points[1:]):
        if frame <= b:
            return x+(y-x)*ease(max(0,(frame-a)/(b-a)))
    return points[-1][1]

def key(anim, obj, prop, seq):
    keyed = add(add(anim,'KeyedObject',objectId=obj.get('id')),'KeyedProperty',property=prop)
    for frame,value in seq:
        add(keyed,'KeyFrameDouble',frame=frame,value=f'{value:.9f}',interpolationType='linear')

def pose(frame):
    angle=START_ANGLE+(END_ANGLE-START_ANGLE)*ease(min(1,frame/48))
    point=CENTER+RADIUS*complex(math.cos(angle),math.sin(angle))
    return point,angle-END_ANGLE,angle

def push(frame):
    return interpolate(frame,[(0,0),(48,0),(55,2.4),(67,0),(81,0)])

def reveal_point(frame, index, count=20):
    angle=math.radians(30)+(pose(frame)[2]+math.radians(3)-math.radians(30))*index/count
    return 2+60*math.cos(angle),60*math.sin(angle)

def head_segments(original,frame=0):
    segments=list(original[:10])+[Line(original[9].end,original[0].start)]
    result=[]
    for i,s in enumerate(segments):
        a=TANGENT*push(frame)*HEAD_WEIGHTS[i]
        b=TANGENT*push(frame)*HEAD_WEIGHTS[(i+1)%len(segments)]
        if isinstance(s,CubicBezier):result.append(CubicBezier(s.start+a,s.control1+a,s.control2+b,s.end+b))
        else:result.append(Line(s.start+a,s.end+b))
    return result

def geometry(shape,segments,offset=0j):
    path=add(shape,'PointsPath',name='Original SVG contour',isClosed='true')
    def handles(s):
        if isinstance(s,CubicBezier):return s.control1,s.control2
        if isinstance(s,Line):return s.start,s.end
        raise ValueError(type(s))
    vertices=[]
    for n,s in enumerate(segments):
        p=s.start;incoming=handles(segments[n-1])[1]-p;outgoing=handles(s)[0]-p
        vertex=add(path,'CubicDetachedVertex',x=(p-offset).real,y=(p-offset).imag,
            inRotation=math.atan2(incoming.imag,incoming.real),inDistance=abs(incoming),
            outRotation=math.atan2(outgoing.imag,outgoing.real),outDistance=abs(outgoing))
        vertices.append((vertex,p-offset))
    add(add(shape,'Fill'),'SolidColor',colorValue='FF0D99FF')
    return vertices

def build():
    source=ROOT/'source'; qa=ROOT/'verification'
    source.mkdir(exist_ok=True);qa.mkdir(exist_ok=True)
    root=ET.Element('Rive',version='1',kind='fragment')
    art=add(root,'Artboard',name='Redo',width=72,height=72,clip='true')
    style=add(art,'LayoutComponentStyle',name='Canvas');art.set('styleId',style.get('id'))
    pivot=add(art,'Node',name='Stationary Icon',x=36,y=36)
    original=list(parse_path(ET.parse(ROOT/'redo.svg').getroot()[0].get('d')))
    # A tiny overlap inside the head removes a raster seam along the split.
    outer=original[-1].end;inner=original[10].start;overlap=TANGENT*.35
    body_segments=original[10:]+[Line(outer,outer+overlap),Line(outer+overlap,inner+overlap),Line(inner+overlap,inner)]
    point,rotation,_=pose(0)
    head=add(pivot,'Shape',name='Traveling Arrowhead',x=point.real-24,y=point.imag-24,rotation=rotation)
    head_vertices=geometry(head,head_segments(original),BASE)
    mask=add(pivot,'Shape',name='Growing Trail Mask')
    mask_path=add(mask,'PointsPath',name='Progressive sector',isClosed='true')
    add(mask_path,'StraightVertex',x=2,y=0)
    reveal_vertices=[]
    for index in range(21):
        x,y=reveal_point(0,index)
        reveal_vertices.append(add(mask_path,'StraightVertex',x=x,y=y))
    body=add(pivot,'Shape',name='Stationary Growing Trail',x=-24,y=-24)
    add(body,'ClippingShape',name='Behind moving head',sourceId=mask.get('id'))
    geometry(body,body_segments)
    animation=add(art,'LinearAnimation',name='redo',fps=60,duration=81,loopValue='oneShot')
    for index,vertex in enumerate(reveal_vertices):
        for axis,prop in enumerate(['x','y']):
            key(animation,vertex,prop,[(f,reveal_point(f,index)[axis]) for f in range(49)])
    for prop,axis in [('x',0),('y',1),('rotation',2)]:
        key(animation,head,prop,[(f,[pose(f)[0].real-24,pose(f)[0].imag-24,pose(f)[1]][axis]) for f in range(82)])
    for i,(vertex,point) in enumerate(head_vertices):
        for axis,prop in enumerate(['x','y']):
            key(animation,vertex,prop,[(f,(point+TANGENT*push(f)*HEAD_WEIGHTS[i]).real if axis==0 else (point+TANGENT*push(f)*HEAD_WEIGHTS[i]).imag) for f in range(48,82)])
    machine=add(art,'StateMachine',name='Redo');art.set('defaultStateMachineId',machine.get('id'))
    layer=add(machine,'StateMachineLayer',name='Play once')
    add(layer,'AnyState',x=0,y=-150);add(layer,'ExitState',x=450,y=-150)
    entry=add(layer,'EntryState',x=0,y=0)
    play=add(layer,'AnimationState',animationId=animation.get('id'),reset='true',x=240,y=0)
    add(entry,'StateTransition',stateToId=play.get('id'),duration=0)
    art.remove(machine);art.insert(list(art).index(animation),machine)
    ET.indent(root)
    (source/'scene.rml').write_bytes(ET.tostring(root,encoding='utf-8',xml_declaration=True))
    (source/'rive.yaml').write_text('name: redo\nmain: Redo\nartboard:\n  width: 72\n  height: 72\n')
    for args,name in [(['--verify','--format=json'],'rive_verify.json'),(['--once','--format=json'],'rive_build.json')]:
        result=subprocess.run(['rive',str(source),*args],capture_output=True,text=True,encoding='utf8')
        (qa/name).write_text(result.stdout,encoding='utf8')
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    shutil.copyfile(source/'build/redo.riv',ROOT/'redo.riv')
    # SVG alternative uses the same poses, easing samples and one-shot timing.
    animated=ET.Element('svg',width='48',height='48',viewBox='0 0 48 48',fill='none',xmlns='http://www.w3.org/2000/svg',overflow='visible')
    defs=ET.SubElement(animated,'defs')
    clip=ET.SubElement(defs,'clipPath',id='tail-to-head',clipPathUnits='userSpaceOnUse')
    mask_svg=ET.SubElement(clip,'path')
    ET.SubElement(animated,'path',d=SVGPath(*body_segments).d(),fill='#0D99FF',**{'clip-path':'url(#tail-to-head)'})
    paths=[]
    for frame in range(49):
        points=[(26,24),*[(x+24,y+24) for x,y in [reveal_point(frame,index) for index in range(21)]]]
        paths.append('M '+' L '.join(f'{x:.9f} {y:.9f}' for x,y in points)+' Z')
    mask_svg.set('d',paths[0])
    ET.SubElement(mask_svg,'animate',attributeName='d',values=';'.join(paths),keyTimes=';'.join(f'{f/48:.9f}' for f in range(49)),dur='0.8s',repeatCount='1',fill='freeze',calcMode='linear')
    times=';'.join(f'{f/81:.9f}' for f in range(82))
    def svg_animation(parent,type_,values):
        ET.SubElement(parent,'animateTransform',attributeName='transform',type=type_,values=';'.join(values),keyTimes=times,dur='1.35s',repeatCount='1',fill='freeze',calcMode='linear')
    move=ET.SubElement(animated,'g');turn=ET.SubElement(move,'g')
    local=ET.SubElement(turn,'g',transform=f'translate({-BASE.real} {-BASE.imag})')
    head_svg=ET.SubElement(local,'path',d=SVGPath(*head_segments(original)).d(),fill='#0D99FF')
    svg_animation(move,'translate',[f'{pose(f)[0].real:.9f} {pose(f)[0].imag:.9f}' for f in range(82)])
    svg_animation(turn,'rotate',[f'{math.degrees(pose(f)[1]):.9f}' for f in range(82)])
    ET.SubElement(head_svg,'animate',attributeName='d',values=';'.join(SVGPath(*head_segments(original,f)).d() for f in range(82)),keyTimes=times,dur='1.35s',repeatCount='1',fill='freeze',calcMode='linear')
    ET.indent(animated)
    (ROOT/'redo_animated.svg').write_bytes(ET.tostring(animated,encoding='utf-8',xml_declaration=True))
    print(json.dumps({'file':str(ROOT/'redo.riv'),'duration_seconds':1.35,'loop':'oneShot','motion':'solid traveling head with growing trail; head pushes and retracts','whole_icon_motion':False}))

if __name__=='__main__':build()
