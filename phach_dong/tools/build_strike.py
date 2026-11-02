"""Native crossed clappers: one trigger, one strike, original SVG burst."""
from pathlib import Path
import argparse,base64,hashlib,json,xml.etree.ElementTree as ET
from svgpathtools import parse_path,CubicBezier,Line
from mcp_client import OpenRive

ROOT=Path(__file__).resolve().parents[1]
UPPER=[(0,0),(5,-7),(8,-4),(10,0),(11,0),(16,-4),(24,0),(36,0)]
LOWER=[(0,0),(5,4),(8,2),(10,0),(11,0),(16,2),(24,0),(36,0)]
FLASH=[(0,0),(9,0),(10,1),(13,1),(17,.6),(22,0),(36,0)]
REVISION='single-strike-original-burst-v1'

def points(data,anchor=(0,0)):
    contours=parse_path(data).continuous_subpaths()
    assert len(contours)==1 and contours[0].isclosed()
    segs=list(contours[0]);out=[]
    for i,s in enumerate(segs):
        prev=segs[i-1];p=s.start
        assert isinstance(s,(CubicBezier,Line))
        a=prev.control2-p if isinstance(prev,CubicBezier) else 0j
        b=s.control1-p if isinstance(s,CubicBezier) else 0j
        out.append(dict(x=p.real-anchor[0],y=p.imag-anchor[1],inX=a.real,inY=a.imag,outX=b.real,outY=b.imag))
    return out

def key(obj,prop,seq,timeline='hit',ease='linear'):
    return dict(op='add_keyframes',timeline=timeline,object=obj,property=prop,
                keys=[dict(frame=f,value=v,ease=ease) for f,v in seq])

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base',default='http://127.0.0.1:56545')
    args=parser.parse_args();client=OpenRive(args.base);qa=ROOT/'verification';qa.mkdir(exist_ok=True)
    meta_path=ROOT/'openrive.json'
    if meta_path.exists():meta=json.loads(meta_path.read_text())
    else:
        made=client.call('create_project',dict(name='Phach Dong - Single Strike'))
        meta=dict(project_id=made['id'])
        meta_path.write_text(json.dumps(meta,indent=2))
    project=meta['project_id'];meta.update(base_url=args.base,editor_url=args.base+'/editor/'+project)
    def call(tool_name,**kwargs):return client.call(tool_name,dict(project=project,**kwargs))
    svg=list(ET.parse(ROOT/'phach.svg').getroot())
    if meta.get('motion_revision')!=REVISION:
        existing=call('get_project')['artboards'][0]
        if not any(c.get('name')=='Upper Clapper' for c in existing['children']):
            call('set_properties',object=existing['id'],properties=dict(name='Phach Dong',width=497,height=336))
            ops=[]
            for name,pivot,base,shade in [('Upper Clapper',(405,80),svg[0],svg[2][0]),('Lower Clapper',(450,180),svg[3],svg[5][0])]:
                ops.append(dict(op='add_group',name=name,x=pivot[0],y=pivot[1]))
                for suffix,e in [('Body',base),('Shading',shade)]:
                    ops.append(dict(op='add_path',parent=name,name=name+' '+suffix,x=0,y=0,
                                    points=points(e.get('d'),pivot),fill=e.get('fill'),closed=True))
            call('apply_edit_plan',operations=ops)
            for name in ['Upper Clapper','Lower Clapper']:call('add_clip',object=name+' Shading',source=name+' Body')
        snapshot=client.snapshot(project);doc=snapshot['doc']
        if isinstance(doc,str):doc=json.loads(doc)
        backup=qa/'before_single_strike_project.json'
        if not backup.exists():backup.write_text(json.dumps(doc,indent=2))
        art=doc['artboards'][0]
        # Retain only the two original clipped clappers and their descendants.
        keep={o['id'] for o in art['objects'] if o['props'].get('name') in ['Upper Clapper','Lower Clapper']}
        while True:
            expanded=keep|{o['id'] for o in art['objects'] if o['props'].get('parentId') in keep}
            if expanded==keep:break
            keep=expanded
        art['objects']=[o for o in art['objects'] if o['id'] in keep]
        for o in art['objects']:
            if o['props'].get('name') in ['Upper Clapper','Lower Clapper']:o['props']['rotation']=0
        art['animations']=[];art['stateMachines']=[]
        art['artboard']['props'].pop('viewModelId',None)
        art['artboard']['props'].pop('defaultStateMachineId',None)
        doc['top']=[o for o in doc['top'] if o['type']=='Backboard']
        client.update(project,doc,snapshot['meta']['updatedAt'])
        ops=[dict(op='add_group',name='Impact',x=0,y=0)]
        # These are the four exact paths from the supplied SVG/reference, at
        # their original positions and scale. No center ring is added.
        for i,(e,tip) in enumerate(zip(svg[6:],[(200,106),(224,101),(90,240),(76,217)])):
            ops.append(dict(op='add_path',parent='Impact',name=f'Impact Ray {i+1}',
                            x=tip[0],y=tip[1],points=points(e.get('d'),tip),fill=e.get('fill'),closed=True))
        ops.extend([dict(op='add_timeline',name='idle',duration=.6,fps=60,loop='loop'),
                    dict(op='add_timeline',name='hit',duration=.6,fps=60,loop='oneShot')])
        for name in ['Upper Clapper','Lower Clapper']:ops.append(key(name,'rotationDegrees',[(0,0),(36,0)],'idle'))
        ops.extend([key('Upper Clapper','rotationDegrees',UPPER,ease='easeInOut'),
                    key('Lower Clapper','rotationDegrees',LOWER,ease='easeInOut'),
                    key('Impact','opacity',[(0,0),(36,0)],'idle'),key('Impact','opacity',FLASH)])
        for i in range(1,5):
            for prop in ['scaleX','scaleY']:
                ops.append(key(f'Impact Ray {i}',prop,[(0,1),(36,1)],'idle'))
                ops.append(key(f'Impact Ray {i}',prop,[(0,.85),(9,.85),(10,1),(13,1),(22,.9),(36,1)]))
        ops.extend([
            dict(op='add_state_machine',name='PhachController'),
            dict(op='add_property',name='hit',type='trigger'),
            dict(op='add_state',stateMachine='PhachController',timeline='idle'),
            dict(op='add_state',stateMachine='PhachController',timeline='hit'),
            dict(op='add_transition',stateMachine='PhachController',**{'from':'entry','to':'idle'},durationMs=0),
            dict(op='add_transition',stateMachine='PhachController',**{'from':'idle','to':'hit'},durationMs=0,conditions=[dict(property='hit')]),
            dict(op='add_transition',stateMachine='PhachController',**{'from':'hit','to':'idle'},durationMs=0,exitTimeMs=600),
        ])
        (qa/'animation_plan.json').write_text(json.dumps(ops,indent=2))
        (qa/'single-strike-mcp.json').write_text(json.dumps(call('apply_edit_plan',operations=ops),indent=2))
        snapshot=client.snapshot(project);doc=snapshot['doc'];art=doc['artboards'][0]
        for o in art['objects']:
            if o['props'].get('name')=='Impact':o['props']['opacity']=0
        art['artboard']['props']['defaultStateMachineId']=art['stateMachines'][0]['id']
        def reset_states(node):
            if node['type']=='AnimationState':node['props']['reset']=True
            for child in node.get('children',[]):reset_states(child)
        for machine in art['stateMachines']:reset_states(machine)
        client.update(project,doc,snapshot['meta']['updatedAt'])
        meta.update(motion_revision=REVISION,phase='animated');meta_path.write_text(json.dumps(meta,indent=2))
    for name,file in [('get_project','openrive-inspect.json'),('diagnose_project','openrive-diagnostics.json')]:
        result=call(name);(qa/file).write_text(json.dumps(result,indent=2))
        if name=='diagnose_project':print('diagnostics',json.dumps(result),flush=True)
    data=base64.b64decode(call('export_riv')['dataBase64']);(ROOT/'phach_dong.riv').write_bytes(data)
    (ROOT/'openrive-project.json').write_text(json.dumps(client.snapshot(project)['doc'],indent=2))
    (qa/'source_manifest.json').write_text(json.dumps(dict(
        source_sha256=hashlib.sha256((ROOT/'phach.svg').read_bytes()).hexdigest(),
        riv_sha256=hashlib.sha256(data).hexdigest(),canvas=[497,336],native_vectors=True,native_clip_masks=2,
        strike_seconds=.6,loop=False,impact_frame=10,effect_paths='original SVG paths, positions and size',
        state_machine='PhachController',trigger_property='hit',idle_matches_original_svg=True,
        upper_keyframes=UPPER,lower_keyframes=LOWER,effect_opacity=FLASH,motion_revision=REVISION),indent=2))
    print(meta['editor_url'],len(data),'bytes',flush=True)

if __name__=='__main__':main()
