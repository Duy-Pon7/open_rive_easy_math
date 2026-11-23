"""Preserve SVG painter order inside the two eye groups in the imported project."""
import json
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
def main():
    meta=json.loads((ROOT/'openrive.json').read_text())
    url=meta['base_url']+'/api/projects/'+meta['project_id']
    snap=requests.get(url,timeout=30).json();doc=snap['doc'];objects=doc['artboards'][0]['objects']
    names={o['props'].get('name'):o for o in objects}
    for group in ['LeftEyeOpenCoordinates','RightEyeOpenCoordinates']:
        parent=names[group]['id']
        starts=[i for i,o in enumerate(objects) if o['type']=='Shape' and o['props'].get('parentId')==parent]
        end=starts[-1]+1
        descendants={objects[starts[-1]]['id']}
        while end<len(objects) and objects[end]['props'].get('parentId') in descendants:
            descendants.add(objects[end]['id']);end+=1
        chunks=[objects[a:b] for a,b in zip(starts,starts[1:]+[end])]
        chunks.sort(key=lambda c:c[0]['props']['name'],reverse=True)
        objects[starts[0]:end]=[o for chunk in chunks for o in chunk]
    r=requests.put(url,json={'doc':json.dumps(doc),'expectedUpdatedAt':snap['meta']['updatedAt']},timeout=60)
    r.raise_for_status()
    print('Eye SVG painter order restored in existing project.')

if __name__=='__main__':main()
