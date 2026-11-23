"""Build Loi from the supplied SVG, without importing buffalo build side effects.

Same native viseme and input contract as Huy and Vy, with Loi-specific SVG grouping,
canvas, facial coordinates and elliptical cheek gradients.
Requires svgpathtools and Rive CLI 1.6.0. Run from any directory.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import shutil
import subprocess
import xml.etree.ElementTree as ET
from svgpathtools import parse_path, CubicBezier, QuadraticBezier, Line

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'loi.svg'
PROJECT = ROOT / 'source'
QA = ROOT / 'verification'
NAMES = ['REST', 'MBP', 'A_OPEN', 'E_I_WIDE', 'O_ROUND', 'U_ROUND',
         'CENTRAL', 'FV', 'DENTAL', 'NARROW', 'MID_OPEN', 'WIDE_TALK']
CLI = shutil.which('rive') or str(Path.home() / '.rive/bin/rive.exe')
counter = 0


def add(parent, tag, **attrs):
    global counter
    counter += 1
    attrs = {k: str(v) for k, v in attrs.items()}
    attrs['id'] = f'0:{counter}'
    return ET.SubElement(parent, tag, attrs)


def color(parent, value):
    value = {'black': '#000000', 'white': '#FFFFFF'}.get(value, value)
    return add(parent, 'SolidColor', colorValue='FF' + value.lstrip('#').upper())


def path_geometry(shape, d):
    """Exact SVG cubic/line conversion; quadratic handles become cubic handles."""
    vertices = []
    for sub in parse_path(d).continuous_subpaths():
        segs = list(sub)
        if not segs:
            continue
        closed = sub.isclosed()
        path = add(shape, 'PointsPath', isClosed=str(closed).lower())
        def handles(seg):
            if isinstance(seg, CubicBezier):
                return seg.control1, seg.control2
            if isinstance(seg, QuadraticBezier):
                return seg.start + (seg.control-seg.start)*2/3, seg.end + (seg.control-seg.end)*2/3
            if not isinstance(seg, Line):
                raise ValueError('Unsupported SVG segment: ' + type(seg).__name__)
            return seg.start, seg.end
        for i in range(len(segs) + (not closed)):
            p = segs[i].start if i < len(segs) else segs[-1].end
            prev = segs[i-1] if i or closed else None
            nxt = segs[i] if i < len(segs) else None
            a = handles(prev)[1]-p if prev else 0j
            b = handles(nxt)[0]-p if nxt else 0j
            vertices.append(add(path, 'CubicDetachedVertex', **vertex_values(p, a, b)))
    return vertices


def vertex_values(p, a, b):
    return dict(x=f'{p.real:.7f}', y=f'{p.imag:.7f}',
                inRotation=f'{math.atan2(a.imag,a.real):.9f}', inDistance=f'{abs(a):.7f}',
                outRotation=f'{math.atan2(b.imag,b.real):.9f}', outDistance=f'{abs(b):.7f}')


def animation(art, name, duration=1, loop='oneShot'):
    return add(art, 'LinearAnimation', name=name, fps=60, duration=duration, loopValue=loop)


def key(anim, obj, prop, values):
    ko = add(anim, 'KeyedObject', objectId=obj.get('id'))
    kp = add(ko, 'KeyedProperty', property=prop)
    for frame, value in values:
        add(kp, 'KeyFrameDouble', frame=frame, value=f'{float(value):.9f}', interpolationType='linear')


def build():
    global counter
    counter = 0
    PROJECT.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    svg = ET.parse(SOURCE).getroot()
    elements = list(svg[0])
    definitions = {e.get('id'): e for e in svg.iter() if e.get('id')}
    root = ET.Element('Rive', version='1', kind='fragment')
    art = add(root, 'Artboard', name='Loi Speaking VI', width=642, height=1259, clip='true')
    style = add(art, 'LayoutComponentStyle', name='Original SVG canvas')
    art.set('styleId', style.get('id'))
    rig = add(art, 'Node', name='CharacterRoot')
    head = add(rig, 'Node', name='Head', x=320, y=515)
    head_content = add(head, 'Node', name='OriginalHeadCoordinates', x=-320, y=-515)
    mouth = add(head_content, 'Node', name='MouthRig')
    brows = add(head_content, 'Node', name='Eyebrows')
    eyes = add(head_content, 'Node', name='Eyes', x=0, y=335)
    eyes_content = add(eyes, 'Node', name='OriginalEyeCoordinates', y=-335)
    face = add(head_content, 'Node', name='FaceHairEars')
    body = add(rig, 'Node', name='Body')

    def convert(parent, element, label, clips=()):
        tag = element.tag.split('}')[-1]
        if tag == 'g':
            group = add(parent, 'Node', name=label, opacity=element.get('opacity', '1'))
            mask = element.get('mask')
            if mask:
                maskdef = definitions[mask[5:-1]]
                clipper = add(group, 'Shape', name=label + ' mask geometry')
                for e in maskdef:
                    path_geometry(clipper, e.get('d'))
                clips = clips + (clipper.get('id'),)
            for j, e in reversed(list(enumerate(element))):
                convert(group, e, f'{label}.{j}', clips)
        elif tag == 'path':
            shape = add(parent, 'Shape', name=label, opacity=element.get('opacity', '1'))
            val = element.get('fill', 'none')
            if val.startswith('url'):
                import re
                definition = definitions[val[5:-1]]
                x, y, rx, ry = map(float, re.findall(r'[-\d.]+', definition.get('gradientTransform')))
                scale_y = ry / rx
                shape.set('scaleY', str(scale_y))
                path = parse_path(element.get('d'))
                path_geometry(shape, path.scaled(1, 1 / scale_y, origin=0j).d())
            else:
                path_geometry(shape, element.get('d'))
            if val != 'none':
                paint = add(shape, 'Fill', fillRule='nonZero')
                if val.startswith('url'):
                    definition = definitions[val[5:-1]]
                    grad = add(paint, 'RadialGradient', startX=x, startY=y/scale_y, endX=x+rx, endY=y/scale_y)
                    for stop in definition:
                        add(grad, 'GradientStop', position=stop.get('offset', '0'),
                            colorValue='FF'+stop.get('stop-color').lstrip('#'))
                else:
                    color(paint, val)
            if element.get('stroke'):
                paint = add(shape, 'Stroke', thickness=element.get('stroke-width', '1'), cap='butt', join='miter')
                color(paint, element.get('stroke'))
            for clip in clips:
                add(shape, 'ClippingShape', sourceId=clip)
            return shape

    # SVG paints back-to-front; RML siblings paint front-to-back.
    for i, e in reversed(list(enumerate(elements))):
        if i == 23 or e.tag.split('}')[-1] in ('mask', 'defs'):
            continue
        parent = brows if i in (19,20) else eyes_content if i in (11,13,14,15,17,18) else face if i in (0,1,2,3,8,10,21,22,24,25,31) else body
        convert(parent, e, f'SVG_{i:02d}')

    original = elements[23].get('d')
    # Front-to-back: teeth and tongue are clipped to the morphing cavity.
    teeth = add(mouth, 'Shape', name='Teeth', x=318, y=419, opacity=0)
    toothrect = add(teeth, 'Rectangle', width=40, height=7)
    color(add(teeth, 'Fill'), '#FCEFE2')
    tongue = add(mouth, 'Shape', name='Tongue', x=318, y=443, opacity=0)
    tongueellipse = add(tongue, 'Ellipse', width=32, height=13)
    color(add(tongue, 'Fill'), '#F38A2D')
    cavity = add(mouth, 'Shape', name='MouthInterior', opacity=0)
    inner = path_geometry(cavity, original)
    color(add(cavity, 'Fill'), '#59281F')
    outline = add(mouth, 'Shape', name='MouthOutline')
    outer = path_geometry(outline, original)
    color(add(outline, 'Fill'), '#B25426')
    for shape in (teeth, tongue):
        add(shape, 'ClippingShape', sourceId=cavity.get('id'))
    # One continuous, shared vertex topology for every viseme, including REST.
    n = len(outer)
    base = [{k:float(v.get(k)) for k in ('x','y','inRotation','inDistance','outRotation','outDistance')} for v in outer]
    # Width, height, center Y, upper-teeth amount, tongue amount.
    specs = [(61.2,12,431.4,0,0), (56,3.5,431.4,0,0), (54,46,432.5,1,1),
             (72,18,431.4,1,0), (34,39,432.5,0,0), (23,26,431.7,0,0),
             (44,24,431.7,0,0), (53,10.5,431.4,1,0), (56,19,431.7,1,1),
             (44,8.5,431.4,0,0), (54,29,432.2,1,.6), (76,42,432.5,1,1)]
    sm = add(art, 'StateMachine', name='LoiVietnameseLipSync')
    art.set('defaultStateMachineId', sm.get('id'))
    inputs = {name:add(sm, kind, name=name) for name,kind in
              [('viseme_id','StateMachineNumber'),('is_talking','StateMachineBool'),
               ('blink','StateMachineTrigger'),('reset','StateMachineTrigger'),
               ('head_only','StateMachineBool')]}
    poses = []
    for idx, (name, spec) in enumerate(zip(NAMES, specs)):
        anim = animation(art, 'mouth_rest' if idx == 0 else 'viseme_'+name)
        poses.append(anim)
        w,h,cy,t,lg = spec
        for vertices, scale in ((outer,1), (inner,.86)):
            for j,v in enumerate(vertices):
                if idx == 0:
                    vals = base[j]
                else:
                    theta = math.pi + j*2*math.pi/n
                    rx,ry=w/2*scale,h/2*scale
                    p=complex(318+rx*math.cos(theta),cy+ry*math.sin(theta))
                    tangent=complex(-rx*math.sin(theta),ry*math.cos(theta))
                    delta=tangent*(4/3*math.tan(math.pi/(2*n)))
                    vals=vertex_values(p,-delta,delta)
                for prop,value in vals.items():
                    key(anim,v,prop,[(0,value),(1,value)])
        for obj,prop,val in [(cavity,'opacity',int(idx not in (0,1))), (teeth,'opacity',t),
                             (tongue,'opacity',lg), (teeth,'y',cy-h*.31),
                             (toothrect,'width',w*.72),(toothrect,'height',7 if idx!=7 else 6),
                             (tongue,'y',cy+h*.30 if idx!=8 else cy+1),
                             (tongueellipse,'width',w*.58),(tongueellipse,'height',13 if idx!=8 else 6)]:
            key(anim,obj,prop,[(0,val),(1,val)])

    idle = animation(art,'idle_loop',180,'loop')
    key(idle,rig,'y',[(0,0),(90,-.7),(180,0)])
    micro_off=animation(art,'head_rest')
    key(micro_off,head,'rotation',[(0,0),(1,0)])
    micro=animation(art,'talk_micro_motion',96,'loop')
    key(micro,head,'rotation',[(0,0),(24,-.004),(48,.003),(72,-.002),(96,0)])
    opened=animation(art,'eyes_open')
    key(opened,eyes,'scaleY',[(0,1),(1,1)])
    blink=animation(art,'blink_once',15)
    key(blink,eyes,'scaleY',[(0,1),(5,.04),(7,.04),(15,1)])
    full_body=animation(art,'show_full_body')
    key(full_body,body,'opacity',[(0,1),(1,1)])
    head_only=animation(art,'show_head_only')
    key(head_only,body,'opacity',[(0,0),(1,0)])

    def layer(name, animations):
        lay=add(sm,'StateMachineLayer',name=name)
        any_state=add(lay,'AnyState',x=-300,y=-180)
        add(lay,'ExitState',x=1000,y=-180)
        entry=add(lay,'EntryState',x=-300,y=0)
        states=[add(lay,'AnimationState',animationId=a.get('id'),reset='true',
                    x=(i%4)*240,y=(i//4)*180) for i,a in enumerate(animations)]
        add(entry,'StateTransition',stateToId=states[0].get('id'))
        return states,any_state

    def transition(src,dst,conditions=(),duration=60,**attrs):
        tr=add(src,'StateTransition',stateToId=dst.get('id'),duration=duration,enableEarlyExit='true',**attrs)
        for typ,name,op,val in conditions:
            args=dict(inputId=inputs[name].get('id'))
            if op:args['opValue']=op
            if val is not None:args['value']=val
            add(tr,typ,**args)
        return tr
    yes=('TransitionBoolCondition','is_talking','equal',None)
    no=('TransitionBoolCondition','is_talking','notEqual',None)
    reset=('TransitionTriggerCondition','reset',None,None)
    states,_=layer('Mouth',poses+[poses[0]])
    for i,state in enumerate(states[:12]):
        transition(state,states[12],[reset])
        if i:transition(state,states[0],[no])
        for j,target in enumerate(states[:12]):
            if i != j:
                transition(state,target,[yes,('TransitionNumberCondition','viseme_id','equal',j)])
        if i:
            transition(state,states[0],[('TransitionNumberCondition','viseme_id','notEqual',j) for j in range(12)])
    # A reset holds REST until the host lowers is_talking. No stale ID reopens it.
    transition(states[12],states[0],[no])
    (rest_state,talk_state),_=layer('Head motion',[micro_off,micro])
    transition(rest_state,talk_state,[yes],duration=90)
    transition(talk_state,rest_state,[no],duration=90)
    (open_state,blink_state),_=layer('Blink',[opened,blink])
    transition(open_state,blink_state,[('TransitionTriggerCondition','blink',None,None)],duration=0)
    transition(blink_state,open_state,[],duration=0,enableExitTime='true',exitTimeIsPercetange='true',exitTime=100)
    layer('Idle',[idle])
    (full_state,head_state),_=layer('Head only',[full_body,head_only])
    transition(full_state,head_state,[('TransitionBoolCondition','head_only','equal',None)],duration=0)
    transition(head_state,full_state,[('TransitionBoolCondition','head_only','notEqual',None)],duration=0)
    # Keep the machine before timelines, so the editor opens the control graph.
    art.remove(sm)
    art.insert(list(art).index(poses[0]),sm)
    ET.indent(root)
    (PROJECT/'scene.rml').write_bytes(ET.tostring(root,encoding='utf-8',xml_declaration=True))
    (PROJECT/'rive.yaml').write_text('name: loi_noi_speaking_vi\nmain: Loi Speaking VI\nartboard:\n  width: 642\n  height: 1259\n',encoding='utf8')
    mapping=dict(artboard='Loi Speaking VI',state_machine='LoiVietnameseLipSync',
                 inputs={'viseme_id':'Number integer 0..11','is_talking':'Boolean','blink':'Trigger','reset':'Trigger','head_only':'Boolean (default false): true shows only the head; false shows the full character'},
                 transition_ms=60, tone_mapping=False, reset_behavior='REST latched until is_talking=false; stop host scheduling before reset',
                 visemes=[dict(id=i,name=name,animation='mouth_rest' if i==0 else 'viseme_'+name) for i,name in enumerate(NAMES)],
                 phonetic_groups={'MBP':['m','b','p'], 'A_OPEN':['a','ă'], 'E_I_WIDE':['e','ê','i','y'],
                     'O_ROUND':['o','ô'], 'U_ROUND':['u'], 'CENTRAL':['ơ','â','ư'], 'FV':['ph','v'],
                     'DENTAL':['t','th','đ','n','l'], 'NARROW':['s','x'], 'MID_OPEN':['h','c','k','g','ng','nh','ch','tr'],
                     'WIDE_TALK':['emphasis: optional, amplitude driven']},
                 dialect_notes=['Visual groups, not a complete phoneme inventory.',
                    'Southern v may use a glide: use CENTRAL/E_I_WIDE instead of FV when appropriate.',
                    'Northern/southern s/x, tr/ch, r/d/gi vary; calibrate from the actual voice.',
                    'Diphthongs use a sequence of shapes; final stops shorten/close the mouth.',
                    'Tone marks never select a distinct viseme. No claim of forced alignment.'])
    (ROOT/'loi_noi_viseme_map.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf8')
    manifest=dict(source=str(SOURCE.relative_to(ROOT)),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  svg_canvas=[642,1259],mouth_bounds=[270,395,367,466],head_pivot=[320,515],
                  mouth_vertex_count=n,objects=counter,native_vectors=True,raster_assets=0,
                  svg_paths_preserved_except_mouth=True,svg_masks_preserved=True,original_gradients_preserved=True)
    (QA/'source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    for flags,name in [(['--verify','--format=json'],'rive_verify.json'),(['--once','--format=json'],'rive_build.json')]:
        p=subprocess.run([CLI,str(PROJECT),*flags],capture_output=True,text=True,encoding='utf8')
        (QA/name).write_text(p.stdout,encoding='utf8')
        if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    p=subprocess.run([CLI,'inspect',str(PROJECT)],capture_output=True,text=True,encoding='utf8',check=True)
    (QA/'rive_inspect.json').write_text(p.stdout,encoding='utf8')
    shutil.copyfile(PROJECT/'build/loi_noi_speaking_vi.riv', ROOT/'loi_noi_speaking_vi.riv')
    print(json.dumps(manifest,indent=2))


if __name__ == '__main__':
    build()
