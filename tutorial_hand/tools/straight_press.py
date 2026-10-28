"""Replace vertex morph tracks with one slow vertical translation in the existing project."""
import base64,json
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]

def main():
    meta=json.loads((ROOT/'openrive.json').read_text())
    url=meta['base_url']+'/api/projects/'+meta['project_id']
    response=requests.get(url,timeout=15);response.raise_for_status();snapshot=response.json()
    (ROOT/'verification/before-straight-press-project.json').write_text(json.dumps(snapshot,indent=2))
    doc=snapshot['doc'];art=doc['artboards'][0]
    hand=next(o for o in art['objects'] if o['props'].get('name')=='Hand')
    hand['props']['y']=-93
    art['artboard']['props']['height']=265
    smooth=[(f,(f/36)**2*(3-2*f/36)) for f in range(0,37,6)]
    profiles={'idle':[(0,0),(1,0)],'hold':[(0,1),(60,1)],'press_down':smooth,'release_up':[(f,1-t) for f,t in smooth]}
    for animation in art['animations']:
        name=animation['props']['name'];profile=profiles[name]
        keyed=next(k for k in animation['children'] if k['props'].get('objectId')==hand['id'])
        yprop=next(k for k in keyed['children'] if k['props'].get('propertyKey')==14)
        yprop['children']=[{'id':f'straight-{name}-{frame}','type':'KeyFrameDouble','props':{'frame':frame,'value':-93+16*t,'interpolationType':1}} for frame,t in profile]
        keyed['children']=[yprop];animation['children']=[keyed]
        animation['props'].update(duration=profile[-1][0],fps=60,speed=1)
    # Use the editor's documented save route to replace whole animation tracks.
    # Keep all project, shape, animation and state machine IDs, and reject stale writes.
    payload={'doc':json.dumps(doc),'riv':base64.b64encode((ROOT/'tutorial_hand.riv').read_bytes()).decode(),'expectedUpdatedAt':snapshot['meta']['updatedAt']}
    response=requests.put(url,json=payload,timeout=30)
    if not response.ok:raise RuntimeError(f'{response.status_code}: {response.text[:1000]}')
    (ROOT/'verification/straight-press-save.json').write_text(response.text)
    print('Saved existing project: rigid vertical press, 16 px, 0.6 s down / 0.6 s up')

if __name__=='__main__':main()
