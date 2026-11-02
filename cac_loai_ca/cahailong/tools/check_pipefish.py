"""Check rigid body constraints and real exported Rive playback in Edge."""
import base64
import io
import json
import threading

import numpy as np
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright
from serve_pipefish import ROOT, server

QA = ROOT/'verification'

def decode(value):
    return Image.open(io.BytesIO(base64.b64decode(value.split(',')[1]))).convert('RGBA')

def white(image):
    return Image.alpha_composite(Image.new('RGBA', image.size, 'white'),image).convert('RGB')

def difference(a,b):
    return float(np.abs(np.asarray(white(a),dtype=float)-np.asarray(white(b),dtype=float)).mean())

def main():
    reports = []
    def check(name,passed,**details):
        reports.append(dict(test=name,passed=bool(passed),**details))
        print(name,'PASS' if passed else 'FAIL',details,flush=True)
    art = json.loads((ROOT/'openrive-project.json').read_text())['artboards'][0]
    objects = {o['id']:o for o in art['objects']}
    tracks = [child for animation in art['animations'] for child in animation['children'] if child['type']=='KeyedObject']
    animated = {objects[t['props']['objectId']]['props']['name'] for t in tracks}
    check('no_body_or_tail_deformation',animated == {'FishRoot','PectoralFin'},animated_nodes=sorted(animated))
    # Root may translate/rotate; it must never scale or alter body geometry.
    root_tracks = [p['props']['propertyKey'] for t in tracks if objects[t['props']['objectId']]['props']['name']=='FishRoot' for p in t['children']]
    check('whole_body_has_rigid_transforms_only',set(root_tracks)=={13,14,15},property_keys=sorted(set(root_tracks)))
    app = server();threading.Thread(target=app.serve_forever,daemon=True).start()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge')
        page = browser.new_page(viewport={'width':1340,'height':324},device_scale_factor=1)
        svg = (ROOT.parent/'cahailong.svg').read_text().replace('width="287" height="25"','width="1148" height="100"')
        page.set_content('<style>body{margin:0}svg{position:absolute;left:96px;top:112px}</style>'+svg)
        ref = Image.open(io.BytesIO(page.screenshot(omit_background=True))).convert('RGBA');ref.save(QA/'source.png')
        page.goto(f'http://127.0.0.1:{app.server_port}/preview.html')
        page.wait_for_function('window.ready || window.failure',timeout=60000)
        assert page.evaluate('window.failure') is None,page.evaluate('window.failure')
        events = page.evaluate('pipefish.fresh();pipefish.advance(.4);pipefish.events()')
        check('default_idle','idle' in events)
        idle = decode(page.evaluate('pipefish.draw()'));idle.save(QA/'idle.png')
        mae = difference(ref,idle)
        check('original_svg_fidelity',mae<.6,mean_rgb_error=mae,source_bounds=ref.getchannel('A').getbbox(),rive_bounds=idle.getchannel('A').getbbox())
        page.evaluate('pipefish.advance(2)')
        check('idle_still',difference(idle,decode(page.evaluate('pipefish.draw()')))<.001)
        page.evaluate('pipefish.setSwim(true);pipefish.advance(.4)')
        check('enter_swim','swim' in page.evaluate('pipefish.events()'))
        frames = []
        for i in range(121):
            if i:page.evaluate('pipefish.advance(1/60)')
            frames.append(decode(page.evaluate('pipefish.draw()')))
        boxes = [im.getchannel('A').getbbox() for im in frames]
        check('no_clipping',all(b and b[0]>0 and b[1]>0 and b[2]<1340 and b[3]<324 for b in boxes),extents=[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)])
        check('seamless_loop',difference(frames[0],frames[-1])<.025,mean_rgb_error=difference(frames[0],frames[-1]))
        check('continuous_motion',len({im.tobytes() for im in frames[:-1]})>=110)
        page.evaluate('pipefish.setSwim(false);pipefish.advance(.5)')
        check('return_to_exact_idle',difference(idle,decode(page.evaluate('pipefish.draw()')))<.01)
        page.evaluate('pipefish.clearEvents();pipefish.setSwim(true);pipefish.advance(.5)')
        check('resume_swim','swim' in page.evaluate('pipefish.events()') and difference(idle,decode(page.evaluate('pipefish.draw()')))>.1)
        for _ in range(8):page.evaluate('pipefish.setSwim(false);pipefish.advance(.08);pipefish.setSwim(true);pipefish.advance(.08)')
        page.evaluate('pipefish.setSwim(false);pipefish.advance(.6)')
        check('rapid_toggle_recovers_idle',difference(idle,decode(page.evaluate('pipefish.draw()')))<.01)
        # One complete fin cycle, returning whole-body position as little as possible.
        poses = [decode(page.evaluate('(t)=>pipefish.pose(t)',i*.4/6)) for i in range(6)]
        sheet = Image.new('RGB',(1340,3*190),'#edf4f2')
        for i,im in enumerate(poses):
            x,y = (i%2)*670,(i//2)*190
            sheet.paste(white(im).resize((670,162)),(x,y))
            ImageDraw.Draw(sheet).text((x+16,y+165),f'swim {i*.4/6:.3f}s',fill='#183b36')
        sheet.save(ROOT/'cahailong_states.png')
        gif = [white(im).resize((1005,243)) for im in frames[:-1:2]]
        gif[0].save(ROOT/'cahailong_swim.gif',save_all=True,append_images=gif[1:],duration=[33,33,34]*20,loop=0,disposal=2)
        page.set_viewport_size({'width':1200,'height':740});page.reload()
        page.wait_for_function('window.ready || window.failure')
        page.screenshot(path=str(QA/'preview.png'))
        browser.close()
    app.shutdown()
    (QA/'runtime_validation.json').write_text(json.dumps(reports,indent=2))
    if not all(r['passed'] for r in reports):raise SystemExit(1)

if __name__ == '__main__':main()
