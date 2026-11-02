"""Verify the exported Rive runtime, SVG fidelity, appendage attachment and transitions."""
import base64
import io
import json
import threading

import numpy as np
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright
from scipy.ndimage import label
from serve_camuon import ROOT,server

QA=ROOT/'verification'

def decode(value):
    return Image.open(io.BytesIO(base64.b64decode(value.split(',')[1]))).convert('RGBA')

def white(image):
    return Image.alpha_composite(Image.new('RGBA',image.size,'white'),image).convert('RGB')

def difference(a,b):
    return float(np.abs(np.asarray(white(a),dtype=float)-np.asarray(white(b),dtype=float)).mean())

def main():
    reports=[]
    def check(name,passed,**details):
        reports.append(dict(test=name,passed=bool(passed),**details))
        print(name,'PASS' if passed else 'FAIL',details,flush=True)
    app=server();threading.Thread(target=app.serve_forever,daemon=True).start()
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge')
        page=browser.new_page(viewport={'width':816,'height':400},device_scale_factor=1)
        svg=(ROOT.parent/'camuon.svg').read_text().replace('width="164" height="60"','width="656" height="240"')
        page.set_content('<style>body{margin:0}svg{position:absolute;left:80px;top:80px}</style>'+svg)
        ref=Image.open(io.BytesIO(page.screenshot(omit_background=True))).convert('RGBA');ref.save(QA/'source.png')
        page.goto(f'http://127.0.0.1:{app.server_port}/preview.html')
        page.wait_for_function('window.ready || window.failure',timeout=60000)
        assert page.evaluate('window.failure') is None,page.evaluate('window.failure')
        events=page.evaluate('fish.fresh();fish.advance(.4);fish.events()')
        check('default_idle','idle' in events)
        idle=decode(page.evaluate('fish.draw()'));idle.save(QA/'idle.png')
        mae=difference(ref,idle)
        check('original_svg_fidelity',mae<.6,mean_rgb_error=mae,source_bounds=ref.getchannel('A').getbbox(),rive_bounds=idle.getchannel('A').getbbox())
        page.evaluate('fish.advance(2)')
        check('idle_still',difference(idle,decode(page.evaluate('fish.draw()')))<.001)
        page.evaluate('fish.setSwim(true);fish.advance(.4)')
        check('enter_swim','swim' in page.evaluate('fish.events()'))
        frames=[]
        for i in range(121):
            if i:page.evaluate('fish.advance(1/60)')
            frames.append(decode(page.evaluate('fish.draw()')))
        boxes=[im.getchannel('A').getbbox() for im in frames]
        check('no_clipping',all(b and b[0]>0 and b[1]>0 and b[2]<816 and b[3]<400 for b in boxes),extents=[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)])
        check('seamless_loop',difference(frames[0],frames[-1])<.025,mean_rgb_error=difference(frames[0],frames[-1]))
        check('continuous_motion',len({im.tobytes() for im in frames[:-1]})>=110)
        for name,region in [('tail',(70,145,215,320)),('dorsal_fin',(300,70,400,145)),('pelvic_fin',(270,260,360,325)),('anal_fin',(405,270,485,325))]:
            change=max(difference(frames[0].crop(region),im.crop(region)) for im in frames)
            check(name+'_moves',change>1,max_mean_rgb_change=change)
        components=[]
        for i in range(0,120,4):
            labels,count=label(np.asarray(frames[i])[:,:,3]>100)
            sizes=np.bincount(labels.ravel())[1:]
            components.append(int(sum(sizes>=10)))
        check('tail_and_fins_remain_attached',max(components)==1,poses=len(components),largest_component_count=max(components))
        page.evaluate('fish.setSwim(false);fish.advance(.5)')
        check('return_to_exact_idle',difference(idle,decode(page.evaluate('fish.draw()')))<.01)
        page.evaluate('fish.clearEvents();fish.setSwim(true);fish.advance(.5)')
        check('resume_swim','swim' in page.evaluate('fish.events()') and difference(idle,decode(page.evaluate('fish.draw()')))>.5)
        for _ in range(8):page.evaluate('fish.setSwim(false);fish.advance(.08);fish.setSwim(true);fish.advance(.08)')
        page.evaluate('fish.setSwim(false);fish.advance(.6)')
        check('rapid_toggle_recovers_idle',difference(idle,decode(page.evaluate('fish.draw()')))<.01)
        poses=[decode(page.evaluate('(t)=>fish.pose(t)',i*2/6)) for i in range(6)]
        sheet=Image.new('RGB',(3*408,2*225),'#edf4f2')
        for i,im in enumerate(poses):
            x,y=(i%3)*408,(i//3)*225
            sheet.paste(white(im).resize((408,200)),(x,y))
            ImageDraw.Draw(sheet).text((x+16,y+203),f'swim {i*2/6:.2f}s',fill='#183b36')
        sheet.save(ROOT/'camuon_states.png')
        gif=[white(im).resize((612,300)) for im in frames[:-1:2]]
        gif[0].save(ROOT/'camuon_swim.gif',save_all=True,append_images=gif[1:],duration=[33,33,34]*20,loop=0,disposal=2)
        page.set_viewport_size({'width':1200,'height':850});page.reload()
        page.wait_for_function('window.ready || window.failure')
        page.screenshot(path=str(QA/'preview.png'))
        browser.close()
    app.shutdown()
    (QA/'runtime_validation.json').write_text(json.dumps(reports,indent=2))
    if not all(r['passed'] for r in reports):raise SystemExit(1)

if __name__=='__main__':main()
