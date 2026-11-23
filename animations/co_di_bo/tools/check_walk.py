"""Validate actual rendered walking motion, planted feet, joins and controller."""
import base64
import hashlib
import io
import json
import threading
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
from svgpathtools import parse_path
from motion import FRAMES,arms,gait
from serve_walk import ROOT,server

QA=ROOT/'verification'


def decode(data):
    return Image.open(io.BytesIO(base64.b64decode(data.split(',')[1]))).convert('RGBA')


def white(im):
    return Image.alpha_composite(Image.new('RGBA',im.size,'white'),im).convert('RGB')


def error(a,b):
    return float(np.abs(np.asarray(white(a),dtype=float)-np.asarray(white(b),dtype=float)).mean())


def main():
    app=server();threading.Thread(target=app.serve_forever,daemon=True).start()
    reports=[]
    def check(name,passed,**details):
        reports.append(dict(test=name,passed=bool(passed),**details))
        print(name,'PASS' if passed else 'FAIL',flush=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge')
        page=browser.new_page(viewport={'width':489,'height':868},device_scale_factor=1)
        page.goto((ROOT/'co_di_bo.svg').as_uri())
        reference=Image.open(io.BytesIO(page.screenshot(omit_background=True))).convert('RGBA')
        reference.save(QA/'source.png')
        page.goto(f'http://127.0.0.1:{app.server_port}/preview.html')
        page.wait_for_function('window.ready || window.failure')
        assert page.evaluate('window.failure') is None
        inputs=page.evaluate('coWalk.fresh()');page.evaluate('coWalk.advance(.4)')
        check('default_walk_controller',inputs=={'is_walking':True} and 'walk' in page.evaluate('coWalk.events()'))
        page.evaluate('coWalk.fresh(false);coWalk.advance(.3)')
        idle=decode(page.evaluate('coWalk.draw()'));idle.save(QA/'idle.png')
        mae=error(reference,idle)
        bounds=[im.getchannel('A').getbbox() for im in [reference,idle]]
        check('original_svg_fidelity',mae<1 and np.max(np.abs(np.array(bounds[0])-np.array(bounds[1])))<=1,mean_rgb_error=mae,alpha_bounds=bounds)
        page.evaluate('coWalk.setWalking(true);coWalk.advance(.4)')
        frames=[]
        for f in range(FRAMES+1):
            if f:page.evaluate('coWalk.advance(1/60)')
            frames.append(decode(page.evaluate('coWalk.draw()')))
        distinct={hashlib.sha256(np.array(im).tobytes()).hexdigest() for im in frames[:-1]}
        check('continuous_walk',len(distinct)>FRAMES*.9,distinct_frames=len(distinct))
        extents=[im.getchannel('A').getbbox() for im in frames]
        check('no_clipping',all(b and b[0]>0 and b[1]>0 and b[2]<489 and b[3]<868 for b in extents))
        loop_error=error(frames[0],frames[-1])
        check('seamless_1_2_second_loop',loop_error<.02,mean_rgb_error=loop_error)
        page.evaluate('coWalk.setWalking(false);coWalk.advance(.4)')
        check('stop_restores_exact_idle',np.array_equal(np.array(idle),np.array(decode(page.evaluate('coWalk.draw()')))))
        page.evaluate('coWalk.clearEvents();coWalk.setWalking(true);coWalk.advance(.5)')
        check('resume_walk','walk' in page.evaluate('coWalk.events()') and error(idle,decode(page.evaluate('coWalk.draw()')))>.2)
        for _ in range(6):page.evaluate('coWalk.setWalking(false);coWalk.advance(.1);coWalk.setWalking(true);coWalk.advance(.1)')
        page.evaluate('coWalk.setWalking(false);coWalk.advance(.4)')
        check('rapid_toggle_returns_to_idle',np.array_equal(np.array(idle),np.array(decode(page.evaluate('coWalk.draw()')))))
        poses=[]
        for f in range(0,FRAMES+1,6):poses.append(decode(page.evaluate('t=>coWalk.pose(t)',f/60)))
        for name,region in [('left_arm',(80,430,190,610)),('right_arm',(310,430,405,610)),('legs',(130,575,370,755))]:
            movement=max(error(poses[0].crop(region),im.crop(region)) for im in poses[1:])
            check(name+'_articulates',movement>1,max_mean_rgb_change=movement)
        quarter=decode(page.evaluate('coWalk.pose(.3)'));threequarter=decode(page.evaluate('coWalk.pose(.9)'))
        def sole(im,region):
            bounds=im.crop(region).getchannel('A').getbbox()
            return bounds[3]+region[1] if bounds else 0
        left_region=(140,770,261,840);right_region=(263,770,390,840)
        left_soles=[sole(im,left_region) for im in [quarter,threequarter]]
        right_soles=[sole(im,right_region) for im in [quarter,threequarter]]
        check('feet_alternate_lift_and_plant',26<=left_soles[0]-left_soles[1]<=30 and 26<=right_soles[1]-right_soles[0]<=30,left_soles=left_soles,right_soles=right_soles)
        original_left=sole(idle,left_region);original_right=sole(idle,right_region)
        check('stance_foot_stays_at_original_ground',left_soles[0]==original_left and right_soles[1]==original_right,ground=[original_left,original_right])
        svg=ET.parse(ROOT/'co_di_bo.svg').getroot()
        cuff_left=parse_path(svg[195].get('d'))
        cuff_right=parse_path(svg[199].get('d'))
        seams=[seg.point(t) for seg in list(cuff_left)[:2] for t in np.linspace(.05,.95,13)]
        seams += [seg.point(t) for seg in list(cuff_right)[-7:] for t in np.linspace(.1,.9,7)]
        misses=0;minimum=255
        for f,im in zip(range(0,FRAMES+1,6),poses):
            alpha=np.array(im)[:,:,3]
            for point in seams:
                mapped=arms(point,f);x=round(mapped.real);y=round(mapped.imag+gait(f)['bob'])
                value=int(alpha[y,x]);minimum=min(minimum,value)
                misses+=value<40
        check('wrists_stay_connected',misses==0,transparent_samples=misses,minimum_alpha=minimum)
        sheet=Image.new('RGB',(6*220,420),'#f7f0f5')
        for i,f in enumerate([0,12,24,36,48,60]):
            im=decode(page.evaluate('t=>coWalk.pose(t)',f/60));im.save(QA/f'walk_{f:02d}.png')
            sheet.paste(white(im).resize((220,390)),(i*220,0))
            ImageDraw.Draw(sheet).text((i*220+12,399),f'{f/60:.2f}s',fill='#533e55')
        sheet.save(ROOT/'co_di_bo_states.png')
        gif=[white(im).resize((293,521)) for im in frames[:-1:2]]
        gif[0].save(ROOT/'co_di_bo_demo.gif',save_all=True,append_images=gif[1:],duration=[33,33,34]*12,loop=0,disposal=2)
        browser.close()
    app.shutdown()
    (QA/'runtime_validation.json').write_text(json.dumps(reports,indent=2))
    if not all(r['passed'] for r in reports):raise SystemExit(1)


if __name__=='__main__':main()
