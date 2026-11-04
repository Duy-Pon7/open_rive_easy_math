"""Build the three-quarter Co speaking rig from the supplied SVG.

Same viseme contract as Co front view, preserving the 3/4 SVG canvas,
paint order, face proportions and gradients. Both eyes keep separate blink pivots.
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
from idle_motion import IDLE_FRAMES, head_radians, blink_keys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'co_goc_3_4.svg'
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
    elements = list(svg)
    definitions = {e.get('id'): e for e in svg.iter() if e.get('id')}
    root = ET.Element('Rive', version='1', kind='fragment')
    art = add(root, 'Artboard', name='Co Speaking VI', width=489, height=868, clip='true')
    style = add(art, 'LayoutComponentStyle', name='Original SVG canvas')
    art.set('styleId', style.get('id'))
    rig = add(art, 'Node', name='CharacterRoot')
    # Preserve SVG paint order: scarf foreground, clothing, then head base.
    front_head = add(rig, 'Node', name='HeadForeground', x=250, y=310)
    front_content = add(front_head, 'Node', name='OriginalForegroundCoordinates', x=-250, y=-310)
    body = add(rig, 'Node', name='Body')
    head = add(rig, 'Node', name='Head', x=250, y=310)
    head_content = add(head, 'Node', name='OriginalHeadCoordinates', x=-250, y=-310)
    brows = add(head_content, 'Node', name='Eyebrows')
    mouth = add(head_content, 'Node', name='MouthRig')
    nose = add(head_content, 'Node', name='NoseAndEar')
    # Different eye heights are retained; each lid scales around its own baseline.
    far_eye = add(head_content, 'Node', name='FarEye', y=217)
    far_content = add(far_eye, 'Node', name='FarEyeCoordinates', y=-217)
    near_eye = add(head_content, 'Node', name='NearEye', y=220)
    near_content = add(near_eye, 'Node', name='NearEyeCoordinates', y=-220)
    face = add(head_content, 'Node', name='FaceHairEarsScarf')

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
        elif tag in ('path', 'circle'):
            shape = add(parent, 'Shape', name=label, opacity=element.get('opacity', '1'))
            val = element.get('fill', 'none')
            if tag == 'circle':
                shape.set('x', element.get('cx')); shape.set('y', element.get('cy'))
                add(shape, 'Ellipse', width=2*float(element.get('r')), height=2*float(element.get('r')))
            else:
                path_geometry(shape, element.get('d'))
            if val != 'none':
                shape.set('opacity', str(float(element.get('opacity', '1'))*float(element.get('fill-opacity', '1'))))
                paint = add(shape, 'Fill', fillRule='nonZero')
                if val.startswith('url'):
                    definition = definitions[val[5:-1]]
                    # Original cheek gradients are circular, centered on the circle.
                    grad = add(paint, 'RadialGradient', startX=0, startY=0,
                               endX=float(element.get('r')), endY=0)
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
        if i == 151 or e.tag.split('}')[-1] in ('mask', 'defs'):
            continue
        parent = (front_content if i >= 202 else body if 154 <= i <= 201 else
                  brows if i in (152,153) else nose if i in (148,149,150) else
                  near_content if 140 <= i <= 143 else far_content if 144 <= i <= 147 else face)
        convert(parent, e, f'SVG_{i:03d}')

    # A fixed neck overlap sits behind both the rotating head and the collar.
    # Extend 15 px above the original neck so either idle tilt stays connected.
    neck_backing = add(rig, 'Shape', name='NeckBacking')
    path_geometry(neck_backing, 'M214.8 290 L273.2 290 L273.2 314 '
                  'L267 320 L229 317 L214.8 313 Z')
    color(add(neck_backing, 'Fill'), '#FDA34E')

    original = elements[151].get('d')
    # Front-to-back: teeth and tongue are clipped to the morphing cavity.
    teeth = add(mouth, 'Shape', name='Teeth', x=284, y=268, rotation=-.045, opacity=0)
    toothrect = add(teeth, 'Rectangle', width=24, height=4.2)
    color(add(teeth, 'Fill'), '#FCEFE2')
    tongue = add(mouth, 'Shape', name='Tongue', x=284, y=284, rotation=-.045, opacity=0)
    tongueellipse = add(tongue, 'Ellipse', width=19, height=7.8)
    color(add(tongue, 'Fill'), '#F38A2D')
    cavity = add(mouth, 'Shape', name='MouthInterior', opacity=0)
    inner = path_geometry(cavity, original)
    color(add(cavity, 'Fill'), '#59281F')
    outline = add(mouth, 'Shape', name='MouthOutline')
    outer = path_geometry(outline, original)
    color(add(outline, 'Fill'), '#CF5E24')
    for shape in (teeth, tongue):
        add(shape, 'ClippingShape', sourceId=cavity.get('id'))
    # One continuous, shared vertex topology for every viseme, including REST.
    n = len(outer)
    base = [{k:float(v.get(k)) for k in ('x','y','inRotation','inDistance','outRotation','outDistance')} for v in outer]
    # Width, height, center Y, upper-teeth amount, tongue amount.
    specs = [(38.2,7.9,273.8,0,0), (35.5,2.4,273.8,0,0), (34,29,277,1,1),
             (46,11.5,274.5,1,0), (21,25,276.5,0,0), (14.5,17,275.5,0,0),
             (28,15,275.5,0,0), (33,6.6,274,1,0), (35,12,275,1,1),
             (28,5.5,274,0,0), (34,18.5,276,1,.6), (48,26,276.5,1,1)]
    sm = add(art, 'StateMachine', name='CoVietnameseLipSync')
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
                    # Project the lip contour into the same right-facing 3/4 plane.
                    c,sn=math.cos(theta),math.sin(theta)
                    px=rx*c*(1-.14*c)
                    py=ry*sn*(1-.10*c)-.045*px
                    p=complex(285+px,cy+py)
                    dx=-rx*sn*(1-.28*c)
                    dy=ry*(c*(1-.10*c)+.10*sn*sn)-.045*dx
                    tangent=complex(dx,dy)
                    delta=tangent*(4/3*math.tan(math.pi/(2*n)))
                    vals=vertex_values(p,-delta,delta)
                for prop,value in vals.items():
                    key(anim,v,prop,[(0,value),(1,value)])
        for obj,prop,val in [(cavity,'opacity',int(idx not in (0,1))), (teeth,'opacity',t),
                             (tongue,'opacity',lg), (teeth,'y',cy-h*.31),
                             (toothrect,'width',w*.72),(toothrect,'height',4.2 if idx!=7 else 3.6),
                             (tongue,'y',cy+h*.30 if idx!=8 else cy+1),
                             (tongueellipse,'width',w*.58),(tongueellipse,'height',7.8 if idx!=8 else 3.6)]:
            key(anim,obj,prop,[(0,val),(1,val)])

    idle = animation(art,'idle_loop',180,'loop')
    key(idle,rig,'y',[(0,0),(90,-.7),(180,0)])
    micro_off=animation(art,'head_rest',IDLE_FRAMES,'loop')
    for node in (head,front_head):
        key(micro_off,node,'rotation',head_radians())
    micro=animation(art,'talk_micro_motion',96,'loop')
    for node in (head,front_head):
        key(micro,node,'rotation',[(0,0),(24,-.004),(48,.003),(72,-.002),(96,0)])
    opened=animation(art,'eyes_open')
    for eye in (near_eye,far_eye):
        key(opened,eye,'scaleY',[(0,1),(1,1)])
    blink=animation(art,'blink_once',15)
    for eye in (near_eye,far_eye):
        key(blink,eye,'scaleY',[(0,1),(5,.04),(7,.04),(15,1)])
    auto_blink=animation(art,'idle_blink_loop',IDLE_FRAMES,'loop')
    for eye in (near_eye,far_eye):
        key(auto_blink,eye,'scaleY',blink_keys())
    full_body=animation(art,'show_full_body')
    key(full_body,body,'opacity',[(0,1),(1,1)])
    key(full_body,neck_backing,'opacity',[(0,1),(1,1)])
    head_only=animation(art,'show_head_only')
    key(head_only,body,'opacity',[(0,0),(1,0)])
    key(head_only,neck_backing,'opacity',[(0,0),(1,0)])

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
    (open_state,blink_state,idle_eyes),_=layer('Blink',[opened,blink,auto_blink])
    transition(open_state,blink_state,[('TransitionTriggerCondition','blink',None,None)],duration=0)
    transition(open_state,idle_eyes,[no],duration=0)
    transition(blink_state,open_state,[],duration=0,enableExitTime='true',exitTimeIsPercetange='true',exitTime=100)
    transition(idle_eyes,blink_state,[('TransitionTriggerCondition','blink',None,None)],duration=0)
    transition(idle_eyes,open_state,[yes],duration=80)
    layer('Idle',[idle])
    (full_state,head_state),_=layer('Head only',[full_body,head_only])
    transition(full_state,head_state,[('TransitionBoolCondition','head_only','equal',None)],duration=0)
    transition(head_state,full_state,[('TransitionBoolCondition','head_only','notEqual',None)],duration=0)
    # Keep the machine before timelines, so the editor opens the control graph.
    art.remove(sm)
    art.insert(list(art).index(poses[0]),sm)
    ET.indent(root)
    (PROJECT/'scene.rml').write_bytes(ET.tostring(root,encoding='utf-8',xml_declaration=True))
    (PROJECT/'rive.yaml').write_text('name: co_goc_3_4_noi_speaking_vi\nmain: Co Speaking VI\nartboard:\n  width: 489\n  height: 868\n',encoding='utf8')
    mapping=dict(artboard='Co Speaking VI',state_machine='CoVietnameseLipSync',
                 source_svg='co_goc_3_4.svg',view='right-facing 3/4',
                 control_api='stateMachineInputs (same as co/co_noi_speaking_vi.riv)',
                 canvas=dict(width=489,height=868),
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
    (ROOT/'co_goc_3_4_noi_viseme_map.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf8')
    manifest=dict(source=str(SOURCE.relative_to(ROOT)),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  svg_canvas=[489,868],mouth_bounds=[251,255,312,296],head_pivot=[250,310],
                  view="right-facing three-quarter",independent_eye_pivots=[220,217],perspective_mouth=True,
                  mouth_vertex_count=n,objects=counter,native_vectors=True,raster_assets=0,
                  svg_paths_preserved_except_mouth=True,svg_masks_preserved=True,original_gradients_preserved=True)
    (QA/'source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    for flags,name in [(['--verify','--format=json'],'rive_verify.json'),(['--once','--format=json'],'rive_build.json')]:
        p=subprocess.run([CLI,str(PROJECT),*flags],capture_output=True,text=True,encoding='utf8')
        (QA/name).write_text(p.stdout,encoding='utf8')
        if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    p=subprocess.run([CLI,'inspect',str(PROJECT)],capture_output=True,text=True,encoding='utf8',check=True)
    (QA/'rive_inspect.json').write_text(p.stdout,encoding='utf8')
    shutil.copyfile(PROJECT/'build/co_goc_3_4_noi_speaking_vi.riv', ROOT/'co_goc_3_4_noi_speaking_vi.riv')
    print(json.dumps(manifest,indent=2))


if __name__ == '__main__':
    build()
