"""Shared eyelid drawing and a separate automatic/manual native blink layer."""
AUTO_FRAMES=300
AUTO_START=156
BLINK_FRAMES=18
EYES=[('LeftEyeOpen',114,164,[34,33,32,31,30,29]),('RightEyeOpen',197,160,[38,37,36,35])]
CURVES=[
    ('LeftClosedLid',[(90,159),(102,176),(124,178),(137,161)],'#141414',2.1,1),
    ('RightClosedLid',[(177,157),(187,172),(207,172),(216,153)],'#141414',2.0,1),
    ('LeftLidCrease',[(92,153),(104,145),(124,146),(135,154)],'#D29762',1,.45),
    ('RightLidCrease',[(179,150),(190,142),(207,143),(215,149)],'#D29762',1,.45),
]
PROFILES={
    'scaleY':[(0,1),(3,.55),(5,.12),(6,.001),(9,.001),(12,.4),(15,.85),(18,1)],
    'openOpacity':[(0,1),(5,1),(6,0),(9,0),(10,1),(18,1)],
    'closedOpacity':[(0,0),(3,0),(5,.6),(6,1),(9,1),(11,.4),(13,0),(18,0)],
}


def animation_tracks(auto=False):
    out=[]
    for name,_,_,_ in EYES:
        out += [(name,'scaleY',PROFILES['scaleY']),(name,'opacity',PROFILES['openOpacity'])]
    out += [('ClosedEyes','opacity',PROFILES['closedOpacity'])]
    if auto:
        out=[(name,prop,[(0,keys[0][1]),(AUTO_START-1,keys[0][1])]+[(AUTO_START+f,v) for f,v in keys]+[(AUTO_FRAMES,keys[-1][1])]) for name,prop,keys in out]
    return out


def add_to_rml(art,sm,vec):
    add=vec.add
    head=next(n for n in art.iter() if n.get('name')=='HeadCoordinates')
    nodes={}
    for name,x,y,indices in EYES:
        group=add(head,'Node',name=name,x=x,y=y)
        content=add(group,'Node',name=name+'Coordinates',x=-x,y=-y)
        for i in indices:
            shape=next(s for s in head if s.get('name')==f'SVG_{i:03d}')
            head.remove(shape);content.append(shape)
        head.remove(group);head.insert(0,group);nodes[name]=group
    closed=add(head,'Node',name='ClosedEyes',opacity=0)
    head.remove(closed);head.insert(0,closed);nodes['ClosedEyes']=closed
    for name,points,color,width,opacity in CURVES:
        shape=add(closed,'Shape',name=name,opacity=opacity)
        a,b,c,d=points
        vec.path_geometry(shape,f'M{a[0]} {a[1]} C{b[0]} {b[1]} {c[0]} {c[1]} {d[0]} {d[1]}')
        vec.color(add(shape,'Stroke',thickness=width,cap='round',join='round'),color)
    animations=[]
    for auto,name,duration,loop in [(True,'blink_auto',AUTO_FRAMES,'loop'),(False,'blink_once',BLINK_FRAMES,'oneShot')]:
        anim=add(art,'LinearAnimation',name=name,fps=60,duration=duration,loopValue=loop)
        for obj,prop,keys in animation_tracks(auto):vec.key(anim,nodes[obj],prop,keys)
        animations.append(anim)
    trigger=add(sm,'StateMachineTrigger',name='blink')
    layer=add(sm,'StateMachineLayer',name='Blinking')
    add(layer,'AnyState',x=-200,y=-160);add(layer,'ExitState',x=700,y=-160)
    entry=add(layer,'EntryState',x=-200,y=0)
    automatic=add(layer,'AnimationState',animationId=animations[0].get('id'),reset='true',x=40,y=0)
    manual=add(layer,'AnimationState',animationId=animations[1].get('id'),reset='true',x=340,y=0)
    add(entry,'StateTransition',stateToId=automatic.get('id'),duration=0)
    tr=add(automatic,'StateTransition',stateToId=manual.get('id'),duration=0)
    add(tr,'TransitionTriggerCondition',inputId=trigger.get('id'))
    add(manual,'StateTransition',stateToId=automatic.get('id'),duration=0,enableExitTime='true',exitTimeIsPercetange='true',exitTime=100)
