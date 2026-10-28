"""Add one native numeric property controlling balloon and splash palettes."""
from pathlib import Path
import json
import requests

import add_fall as rive

ROOT = Path(__file__).resolve().parent.parent
PALETTES = {
    'Blue': {
        '#4299fd':'#4299FD', '#2d6ebd':'#2D6EBD', '#c0dbfc':'#C0DBFC',
        '#66b8fd':'#66B8FD', '#3995fe':'#3995FE', '#126ed4':'#126ED4', '#c1e0fd':'#C1E0FD',
    },
    'Yellow': {
        '#4299fd':'#F8CE44', '#2d6ebd':'#BA9020', '#c0dbfc':'#FFF0B8',
        '#66b8fd':'#FFD96B', '#3995fe':'#F4C033', '#126ed4':'#CA941A', '#c1e0fd':'#FFF3C6',
    },
    'Pink': {
        '#4299fd':'#F27AAF', '#2d6ebd':'#BA467C', '#c0dbfc':'#FFD5E8',
        '#66b8fd':'#FFA3CC', '#3995fe':'#EF6DA7', '#126ed4':'#CB3E80', '#c1e0fd':'#FFE0EF',
    },
}


def build():
    url = rive.BASE + '/api/projects/' + rive.PROJECT
    response = requests.get(url);response.raise_for_status()
    snapshot = response.json();doc = snapshot['doc'];art = doc['artboards'][0]
    if any(o['props'].get('name') == 'balloonColor' for o in doc['top']):
        raise RuntimeError('balloonColor already exists; use focused edits.')
    objects = {o['id']:o for o in art['objects']}
    targets = {}
    for color in art['objects']:
        if color['type'] != 'SolidColor':
            continue
        rgb = '#%06x' % (color['props'].get('colorValue',0) & 0xffffff)
        if rgb not in PALETTES['Blue']:
            continue
        fill = objects[color['props']['parentId']]
        shape = objects[fill['props']['parentId']]
        targets[shape['id']] = rgb
    assert len(targets) == 26, 'Review target artwork if shape count changes.'
    operations = [{'op':'add_property','name':'balloonColor','type':'number','value':0}]
    for name, palette in PALETTES.items():
        animation = 'Balloon ' + name
        operations.append({'op':'add_timeline','name':animation,'duration':1,'fps':60,'loop':'loop'})
        for shape, rgb in targets.items():
            operations.append({'op':'add_keyframes','timeline':animation,'object':shape,
                               'property':'fill','keys':[{'frame':0,'value':palette[rgb],'ease':'hold'}]})
    machine = 'Palette Assembly'
    operations.append({'op':'add_state_machine','name':machine})
    for name in PALETTES:
        operations.append({'op':'add_state','stateMachine':machine,'timeline':'Balloon '+name})
    for value, name in enumerate(PALETTES):
        for source in ['Entry'] + ['Balloon '+other for other in PALETTES if other != name]:
            operations.append({'op':'add_transition','stateMachine':machine,'from':source,
                               'to':'Balloon '+name,'durationMs':0,
                               'conditions':[{'property':'balloonColor','op':'==','value':value}]})
    rive.apply(operations)
    # The MCP exposes state machine creation, but no add-layer operation.
    # Move the generated native layer into the existing controller using the documented project API.
    response = requests.get(url);response.raise_for_status();snapshot = response.json();doc = snapshot['doc']
    art = doc['artboards'][0]
    controller = next(sm for sm in art['stateMachines'] if sm['props']['name']=='Run Controller')
    palette = next(sm for sm in art['stateMachines'] if sm['props']['name']==machine)
    assert len(palette['children']) == 1
    layer = palette['children'][0];layer['props']['name'] = 'Balloon Color'
    controller['children'].append(layer)
    art['stateMachines'] = [sm for sm in art['stateMachines'] if sm['id'] != palette['id']]
    response = requests.put(url,json={'doc':json.dumps(doc),'stateMachines':len(art['stateMachines']),
                                     'expectedUpdatedAt':snapshot['meta']['updatedAt']})
    response.raise_for_status()
    rive.export()
    diagnostics = rive.result(rive.call('diagnose_project',{'project':rive.PROJECT}))
    (ROOT/'verification/color-diagnostics.json').write_text(json.dumps(diagnostics,indent=2))
    (ROOT/'verification/balloon-palettes.json').write_text(json.dumps(PALETTES,indent=2))
    print(json.dumps({'colored_shapes':len(targets),'valid':diagnostics['valid']}))


if __name__ == '__main__':
    build()
