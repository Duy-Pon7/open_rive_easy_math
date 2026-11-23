"""Trace the source tick, retract its endpoint, then advance and hold."""
from pathlib import Path
import json, shutil, subprocess, xml.etree.ElementTree as ET
from svgpathtools import parse_path, Line

ROOT=Path(__file__).resolve().parents[1]
counter=0

def add(parent,tag,**attrs):
    global counter
    counter+=1
    return ET.SubElement(parent,tag,{**{k:str(v) for k,v in attrs.items()},'id':f'0:{counter}'})

def ease(t):return t*t*t*(t*(t*6-15)+10)

def progress(frame):
    if frame<=48:return .00001+.99999*ease(frame/48)
    if frame<=56:return 1-.08*ease((frame-48)/8)
    if frame<=69:return .92+.08*ease((frame-56)/13)
    return 1

def build():
    source=ROOT/'source';qa=ROOT/'verification'
    source.mkdir(exist_ok=True);qa.mkdir(exist_ok=True)
    svg=ET.parse(ROOT/'tick.svg').getroot();element=svg[0]
    segments=list(parse_path(element.get('d')))
    assert all(isinstance(s,Line) for s in segments)
    root=ET.Element('Rive',version='1',kind='fragment')
    art=add(root,'Artboard',name='Tick',width=72,height=72,clip='true')
    style=add(art,'LayoutComponentStyle',name='Canvas');art.set('styleId',style.get('id'))
    shape=add(art,'Shape',name='Tick Stroke',x=12,y=12)
    path=add(shape,'PointsPath',name='Original SVG centerline',isClosed='false')
    for point in [segments[0].start,*[s.end for s in segments]]:
        add(path,'StraightVertex',x=point.real,y=point.imag)
    stroke=add(shape,'Stroke',name='Constant Width',thickness=element.get('stroke-width'),cap=element.get('stroke-linecap'),join=element.get('stroke-linejoin'))
    add(stroke,'SolidColor',colorValue='FF'+element.get('stroke').lstrip('#'))
    trim=add(stroke,'TrimPath',name='Trace, Retract and Advance',start=0,end=progress(0),modeValue='sequential')
    animation=add(art,'LinearAnimation',name='tick',fps=60,duration=81,loopValue='oneShot')
    keyed=add(add(animation,'KeyedObject',objectId=trim.get('id')),'KeyedProperty',property='end')
    for frame in range(82):add(keyed,'KeyFrameDouble',frame=frame,value=f'{progress(frame):.9f}',interpolationType='linear')
    machine=add(art,'StateMachine',name='Tick');art.set('defaultStateMachineId',machine.get('id'))
    layer=add(machine,'StateMachineLayer',name='Play once')
    add(layer,'AnyState',x=0,y=-150);add(layer,'ExitState',x=450,y=-150)
    entry=add(layer,'EntryState',x=0,y=0)
    play=add(layer,'AnimationState',animationId=animation.get('id'),reset='true',x=240,y=0)
    add(entry,'StateTransition',stateToId=play.get('id'),duration=0)
    art.remove(machine);art.insert(list(art).index(animation),machine)
    ET.indent(root)
    (source/'scene.rml').write_bytes(ET.tostring(root,encoding='utf-8',xml_declaration=True))
    (source/'rive.yaml').write_text('name: tick\nmain: Tick\nartboard:\n  width: 72\n  height: 72\n')
    for args,name in [(['--verify','--format=json'],'rive_verify.json'),(['--once','--format=json'],'rive_build.json')]:
        result=subprocess.run(['rive',str(source),*args],capture_output=True,text=True,encoding='utf8')
        (qa/name).write_text(result.stdout,encoding='utf8')
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    shutil.copyfile(source/'build/tick.riv',ROOT/'tick.riv')
    # The SVG uses the identical path and round caps, without opacity changes.
    animated=ET.Element('svg',dict(svg.attrib))
    animated.set('xmlns','http://www.w3.org/2000/svg')
    attrs={**element.attrib,'pathLength':'1','stroke-dasharray':f'{progress(0)} 1.001'}
    animated_path=ET.SubElement(animated,'path',attrs)
    ET.SubElement(animated_path,'animate',attributeName='stroke-dasharray',values=';'.join(f'{progress(f):.9f} 1.001' for f in range(82)),keyTimes=';'.join(str(f/81) for f in range(82)),dur='1.35s',repeatCount='1',fill='freeze',calcMode='linear')
    ET.indent(animated)
    (ROOT/'tick_animated.svg').write_bytes(ET.tostring(animated,encoding='utf-8',xml_declaration=True))
    print(json.dumps({'file':str(ROOT/'tick.riv'),'duration_seconds':1.35,'width':element.get('stroke-width'),'motion':'trace; retract 8 percent; advance and stop'}))

if __name__=='__main__':build()
