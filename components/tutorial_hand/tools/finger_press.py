"""Move only the index fingertip vertically, retaining its original round contour."""
import base64,json
from pathlib import Path
import requests
from motion import BASE_Y, HEIGHT, CONTACT_FRAME, PROFILES, TOUCH_X, TOUCH_Y, PALETTE, feedback

ROOT=Path(__file__).resolve().parents[1]

def main():
    meta=json.loads((ROOT/'openrive.json').read_text())
    url=meta['base_url']+'/api/projects/'+meta['project_id']
    response=requests.get(url,timeout=15);response.raise_for_status();snapshot=response.json()
    backup=ROOT/'verification/before-finger-press-project.json'
    if not backup.exists():backup.write_text(json.dumps(snapshot,indent=2))
    backup=ROOT/'verification/before-contact-only-feedback-project.json'
    if not backup.exists():backup.write_text(json.dumps(snapshot,indent=2))
    backup=ROOT/'verification/before-single-circle-palette-project.json'
    if not backup.exists():backup.write_text(json.dumps(snapshot,indent=2))
    backup=ROOT/'verification/before-touch-feedback-project.json'
    if not backup.exists():backup.write_text(json.dumps(snapshot,indent=2))
    backup=ROOT/'verification/before-gentle-release-project.json'
    if not backup.exists():backup.write_text(json.dumps(snapshot,indent=2))
    doc=snapshot['doc'];art=doc['artboards'][0]
    hand=next(o for o in art['objects'] if o['props'].get('name')=='Hand')
    silhouette=next(o for o in art['objects'] if o['props'].get('name')=='Hand silhouette')
    path=next(o for o in art['objects'] if o['type']=='PointsPath' and o['props'].get('parentId')==silhouette['id'])
    vertices=[o for o in art['objects'] if o['type']=='CubicDetachedVertex' and o['props'].get('parentId')==path['id']]
    tip=vertices[6:9]
    assert all(v['props']['y']<110 for v in tip)
    hand['props']['y']=BASE_Y
    art['artboard']['props']['height']=HEIGHT
    touch=next(o for o in art['objects'] if o['props'].get('name')=='Touch Feedback')
    touch['props'].update(x=TOUCH_X,y=TOUCH_Y,opacity=1,scaleX=1,scaleY=1)
    # MCP inserts newly-created objects at the front. Put the feedback behind
    # the hand, and the darker disk in front of the lighter disk.
    def subtree(obj):
        result=[obj]
        for child in art['objects']:
            if child['props'].get('parentId')==obj['id']:result.extend(subtree(child))
        return result
    inner=next(o for o in art['objects'] if o['props'].get('name')=='Touch Inner')
    outer=next(o for o in art['objects'] if o['props'].get('name')=='Touch Outer')
    paints=[]
    for disk in [inner,outer]:
        disk['props'].update(opacity=0,scaleX=.001,scaleY=.001)
        paint=next(o for o in subtree(disk) if o['type']=='SolidColor')
        paint['props']['colorValue']=int('FF'+PALETTE[0][1][1:],16)
        paints.append(paint)
    effect_objects=[touch]+subtree(inner)+subtree(outer)
    effect_ids={o['id'] for o in effect_objects}
    art['objects']=[o for o in art['objects'] if o['id'] not in effect_ids]+effect_objects
    for animation in art['animations']:
        name=animation['props']['name']
        if name not in PROFILES:continue
        profile=PROFILES[name]
        tracks=[]
        for i,obj in enumerate([hand]+tip):
            base=BASE_Y if i==0 else obj['props']['y']
            tag=f'finger-{name}-{i}'
            keys=[{'id':f'{tag}-{f}','type':'KeyFrameDouble','props':{'frame':f,'value':base+(0 if i==0 else offset),'interpolationType':1}} for f,offset in profile]
            tracks.append({'id':tag,'type':'KeyedObject','props':{'objectId':obj['id']},'children':[{'id':tag+'-y','type':'KeyedProperty','props':{'propertyKey':14 if i==0 else 25},'children':keys}]})
        # Node scaleX=16, scaleY=17, opacity=18 in the Rive schema.
        for part,disk in [('inner',inner),('outer',outer)]:
            properties=[]
            for prop,property_key in [('scaleX',16),('scaleY',17),('opacity',18)]:
                tag=f'touch-{name}-{part}-{prop}'
                keys=[{'id':f'{tag}-{f}','type':'KeyFrameDouble','props':{'frame':f,'value':feedback(f,name,part)[int(prop=='opacity')],'interpolationType':1}} for f,offset in profile]
                properties.append({'id':tag,'type':'KeyedProperty','props':{'propertyKey':property_key},'children':keys})
            tracks.append({'id':f'touch-{name}-{part}','type':'KeyedObject','props':{'objectId':disk['id']},'children':properties})
        animation['children']=tracks
        animation['props'].update(duration=profile[-1][0],fps=60,speed=1)
    # Color runs on a separate layer, so changing paintColor never replays a press.
    sm=next(s for s in art['stateMachines'] if s['props'].get('name')=='TutorialHand')
    gesture=next(c for c in sm['children'] if c['type']=='StateMachineLayer' and c['props'].get('name')=='Finger gesture')
    animation_ids={a['props']['name']:a['id'] for a in art['animations']}
    gesture_states={name:next(c for c in gesture['children'] if c['props'].get('animationId')==animation_ids[name]) for name in ['idle','press_down','release_up']}
    pressing=gesture_states['press_down']
    release_transition=next(c for c in pressing['children'] if c['props'].get('stateToId')==gesture_states['release_up']['id'])
    release_transition['props'].update(flags=36,exitTime=CONTACT_FRAME*1000//60,duration=60)
    pressing['children']=[c for c in pressing['children'] if c['id']!='cancel-press-before-contact']
    bool_input=next(c for c in sm['children'] if c['type']=='StateMachineBool' and c['props'].get('name')=='is_pressed')
    pressing['children'].insert(1,{'id':'cancel-press-before-contact','type':'StateTransition','props':{'stateToId':gesture_states['idle']['id'],'flags':32,'duration':180},'children':[{'id':'cancel-press-before-contact-condition','type':'TransitionBoolCondition','props':{'inputId':bool_input['id'],'opValue':1}}]})
    sm['children']=[c for c in sm['children'] if c['props'].get('name') not in ['paintColor','Paint color selection']]
    control={'id':'touch-paint-color-input','type':'StateMachineNumber','props':{'name':'paintColor','value':0}}
    sm['children'].insert(1,control)
    layer={'id':'touch-paint-color-layer','type':'StateMachineLayer','props':{'name':'Paint color selection'},'children':[]}
    entry={'id':'touch-color-entry','type':'EntryState','props':{},'children':[]}
    states=[]
    art['animations']=[a for a in art['animations'] if not a['props'].get('name','').startswith('Paint_Color_')]
    for index,(color_name,hex_color) in enumerate(PALETTE):
        tag=f'touch-color-{index}'
        anim={'id':tag+'-anim','type':'LinearAnimation','props':{'name':'Paint_Color_'+color_name,'duration':1,'fps':60},'children':[]}
        for i,paint in enumerate(paints):
            key={'id':f'{tag}-value-{i}','type':'KeyFrameColor','props':{'frame':0,'value':int('FF'+hex_color[1:],16),'interpolationType':0}}
            prop={'id':f'{tag}-prop-{i}','type':'KeyedProperty','props':{'propertyKey':37},'children':[key]}
            anim['children'].append({'id':f'{tag}-paint-{i}','type':'KeyedObject','props':{'objectId':paint['id']},'children':[prop]})
        art['animations'].append(anim)
        states.append({'id':tag+'-state','type':'AnimationState','props':{'animationId':anim['id']},'children':[]})
    for source_index,source in [(-1,entry),*enumerate(states)]:
        for target in [1,2,0]:
            if source_index==target:continue
            tag=f'touch-color-transition-{source_index}-{target}'
            transition={'id':tag,'type':'StateTransition','props':{'stateToId':states[target]['id'],'duration':0},'children':[]}
            for op,value in ([(1,1),(1,2)] if target==0 else [(0,target)]):
                transition['children'].append({'id':f'{tag}-condition-{value}','type':'TransitionNumberCondition','props':{'inputId':control['id'],'opValue':op,'value':value}})
            source['children'].append(transition)
    layer['children']=[{'id':'touch-color-any','type':'AnyState','props':{}},{'id':'touch-color-exit','type':'ExitState','props':{}},entry]+states
    sm['children'].append(layer)
    payload={'doc':json.dumps(doc),'riv':base64.b64encode((ROOT/'tutorial_hand.riv').read_bytes()).decode(),'expectedUpdatedAt':snapshot['meta']['updatedAt']}
    response=requests.put(url,json=payload,timeout=30)
    if not response.ok:raise RuntimeError(f'{response.status_code}: {response.text[:1000]}')
    (ROOT/'verification/finger-press-save.json').write_text(response.text)
    print('Saved: two-circle press to small-circle hold; paintColor 0 Blue, 1 Yellow, 2 Pink')

if __name__=='__main__':main()
