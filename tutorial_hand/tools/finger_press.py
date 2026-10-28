"""Move only the index fingertip vertically, retaining its original round contour."""
import base64,json
from pathlib import Path
import requests
from motion import BASE_Y, HEIGHT, PROFILES

ROOT=Path(__file__).resolve().parents[1]

def main():
    meta=json.loads((ROOT/'openrive.json').read_text())
    url=meta['base_url']+'/api/projects/'+meta['project_id']
    response=requests.get(url,timeout=15);response.raise_for_status();snapshot=response.json()
    backup=ROOT/'verification/before-finger-press-project.json'
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
    for animation in art['animations']:
        name=animation['props']['name'];profile=PROFILES[name]
        tracks=[]
        for i,obj in enumerate([hand]+tip):
            base=BASE_Y if i==0 else obj['props']['y']
            tag=f'finger-{name}-{i}'
            keys=[{'id':f'{tag}-{f}','type':'KeyFrameDouble','props':{'frame':f,'value':base+(0 if i==0 else offset),'interpolationType':1}} for f,offset in profile]
            tracks.append({'id':tag,'type':'KeyedObject','props':{'objectId':obj['id']},'children':[{'id':tag+'-y','type':'KeyedProperty','props':{'propertyKey':14 if i==0 else 25},'children':keys}]})
        animation['children']=tracks
        animation['props'].update(duration=profile[-1][0],fps=60,speed=1)
    payload={'doc':json.dumps(doc),'riv':base64.b64encode((ROOT/'tutorial_hand.riv').read_bytes()).decode(),'expectedUpdatedAt':snapshot['meta']['updatedAt']}
    response=requests.put(url,json=payload,timeout=30)
    if not response.ok:raise RuntimeError(f'{response.status_code}: {response.text[:1000]}')
    (ROOT/'verification/finger-press-save.json').write_text(response.text)
    print('Saved: gentle 14 px press; release lifts 2 px then settles; 0.6 s each way')

if __name__=='__main__':main()
