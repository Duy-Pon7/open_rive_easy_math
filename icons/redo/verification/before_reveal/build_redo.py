"""Build the original redo vector with a single clockwise turn and bounce."""
from pathlib import Path
import json, math, shutil, subprocess, xml.etree.ElementTree as ET
from svgpathtools import parse_path, CubicBezier, Line

ROOT = Path(__file__).resolve().parents[1]
counter = 0

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

def build():
    source=ROOT/'source'; qa=ROOT/'verification'
    source.mkdir(exist_ok=True);qa.mkdir(exist_ok=True)
    root=ET.Element('Rive',version='1',kind='fragment')
    art=add(root,'Artboard',name='Redo',width=72,height=72,clip='true')
    style=add(art,'LayoutComponentStyle',name='Canvas');art.set('styleId',style.get('id'))
    pivot=add(art,'Node',name='Redo Motion',x=36,y=36)
    svg=ET.parse(ROOT/'redo.svg').getroot()
    for i,element in enumerate(svg):
        shape=add(pivot,'Shape',name=f'Redo Arrow {i+1}',x=-24,y=-24)
        for contour in parse_path(element.get('d')).continuous_subpaths():
            segments=list(contour)
            path=add(shape,'PointsPath',name='Original SVG contour',isClosed=str(contour.isclosed()).lower())
            def handles(segment):
                if isinstance(segment,CubicBezier):return segment.control1,segment.control2
                if isinstance(segment,Line):return segment.start,segment.end
                raise ValueError(type(segment))
            for n,segment in enumerate(segments):
                point=segment.start
                incoming=handles(segments[n-1])[1]-point
                outgoing=handles(segment)[0]-point
                add(path,'CubicDetachedVertex',x=point.real,y=point.imag,
                    inRotation=math.atan2(incoming.imag,incoming.real),inDistance=abs(incoming),
                    outRotation=math.atan2(outgoing.imag,outgoing.real),outDistance=abs(outgoing))
        add(add(shape,'Fill'),'SolidColor',colorValue='FF'+element.get('fill').lstrip('#'))
    animation=add(art,'LinearAnimation',name='redo',fps=60,duration=81,loopValue='oneShot')
    key(animation,pivot,'rotation',[(f,math.tau*ease(min(1,f/48))) for f in range(82)])
    profiles={
        'y':[(0,36),(48,36),(54,37.2),(63,32.5),(73,36),(81,36)],
        'scaleX':[(0,1),(48,1),(54,1.09),(63,.97),(73,1),(81,1)],
        'scaleY':[(0,1),(48,1),(54,.91),(63,1.04),(73,1),(81,1)]}
    for prop,points in profiles.items():
        key(animation,pivot,prop,[(f,interpolate(f,points)) for f in range(82)])
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
    move=ET.SubElement(animated,'g',transform='translate(24 24)')
    turn=ET.SubElement(move,'g')
    scale=ET.SubElement(turn,'g')
    content=ET.SubElement(scale,'g',transform='translate(-24 -24)')
    for element in svg:ET.SubElement(content,'path',d=element.get('d'),fill=element.get('fill'))
    times=';'.join(f'{f/81:.9f}' for f in range(82))
    def svg_animation(parent,type_,values):
        ET.SubElement(parent,'animateTransform',attributeName='transform',type=type_,values=';'.join(values),keyTimes=times,dur='1.35s',repeatCount='1',fill='freeze',calcMode='linear')
    svg_animation(move,'translate',[f'24 {interpolate(f,profiles["y"])-12:.9f}' for f in range(82)])
    svg_animation(turn,'rotate',[f'{360*ease(min(1,f/48)):.9f}' for f in range(82)])
    svg_animation(scale,'scale',[f'{interpolate(f,profiles["scaleX"]):.9f} {interpolate(f,profiles["scaleY"]):.9f}' for f in range(82)])
    ET.indent(animated)
    (ROOT/'redo_animated.svg').write_bytes(ET.tostring(animated,encoding='utf-8',xml_declaration=True))
    print(json.dumps({'file':str(ROOT/'redo.riv'),'duration_seconds':1.35,'loop':'oneShot','rotation_degrees':360,'bounce_count':1}))

if __name__=='__main__':build()
