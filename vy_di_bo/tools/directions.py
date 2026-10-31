"""Four walking/standing states, mirroring the entire character and eyelids."""
import copy

STATES=[('idle',False,False),('walk',True,False),('idle_left',False,True),('walk_left',True,True)]


def add_to_rml(art,sm,wrapper,vec):
    add=vec.add
    original={a.get('name'):a for a in art if a.tag=='LinearAnimation'}
    for source,target in [('idle','idle_left'),('walk','walk_left')]:
        clone=copy.deepcopy(original[source])
        for node in clone.iter():
            vec.counter+=1;node.set('id',f'0:{vec.counter}')
        clone.set('name',target);art.append(clone)
        vec.key(clone,wrapper,'x',[(0,491),(float(clone.get('duration')),491)])
        vec.key(clone,wrapper,'scaleX',[(0,-1),(float(clone.get('duration')),-1)])
    for name in ['idle','walk']:
        vec.key(original[name],wrapper,'x',[(0,0),(float(original[name].get('duration')),0)])
        vec.key(original[name],wrapper,'scaleX',[(0,1),(float(original[name].get('duration')),1)])
    walking=next(n for n in sm if n.tag=='StateMachineBool' and n.get('name')=='is_walking')
    facing=add(sm,'StateMachineBool',name='facing_left',value='false')
    layer=next(n for n in sm if n.tag=='StateMachineLayer' and n.get('name')=='Walking')
    layer.clear();layer.set('name','Walking')
    vec.counter+=1;layer.set('id',f'0:{vec.counter}')
    add(layer,'AnyState',x=-200,y=-160);add(layer,'ExitState',x=800,y=-160)
    entry=add(layer,'EntryState',x=-200,y=0)
    animations={a.get('name'):a for a in art if a.tag=='LinearAnimation'}
    states=[add(layer,'AnimationState',animationId=animations[name].get('id'),reset='true',x=(i%2)*300,y=(i//2)*250) for i,(name,_,_) in enumerate(STATES)]
    for source_index,source in [(-1,entry),*enumerate(states)]:
        for target_index,(name,is_walking,is_left) in enumerate(STATES):
            if source_index==target_index:continue
            same_face=source_index>=0 and STATES[source_index][2]==is_left
            tr=add(source,'StateTransition',stateToId=states[target_index].get('id'),duration=180 if same_face else 0,enableEarlyExit='true')
            for inp,value in [(walking,is_walking),(facing,is_left)]:
                add(tr,'TransitionBoolCondition',inputId=inp.get('id'),opValue='equal' if value else 'notEqual')
