"""Verify delivered .riv in the real WASM runtime; save inspectable previews."""
import base64
import hashlib
import io
import json
import threading
import xml.etree.ElementTree as ET
import numpy as np
from svgpathtools import parse_path
from PIL import Image,ImageDraw,ImageOps
from playwright.sync_api import sync_playwright
from motion import FRAMES,gait,arms,leg_pose,THIGH_LENGTH,SHIN_LENGTH
from serve_walk import ROOT,server

QA=ROOT/'verification'
def decode(data):return Image.open(io.BytesIO(base64.b64decode(data.split(',')[1]))).convert('RGBA')
def white(im):return Image.alpha_composite(Image.new('RGBA',im.size,'white'),im).convert('RGB')
def error(a,b):return float(np.abs(np.asarray(white(a),dtype=float)-np.asarray(white(b),dtype=float)).mean())

def main():
    results=[]
    def check(name,passed,**details):
        results.append(dict(test=name,passed=bool(passed),**details));print(name,'PASS' if passed else 'FAIL',flush=True)
    manifest=json.loads((QA/'source_manifest.json').read_text())
    check('source_svg_unchanged',hashlib.sha256((ROOT/'huy_di_bo.svg').read_bytes()).hexdigest()==manifest['source_sha256'])
    app=server();threading.Thread(target=app.serve_forever,daemon=True).start()
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge')
        page=browser.new_page(viewport={'width':266,'height':772},device_scale_factor=1)
        page.goto((ROOT/'huy_di_bo.svg').as_uri())
        source=Image.open(io.BytesIO(page.screenshot(omit_background=True))).convert('RGBA')
        reference=Image.new('RGBA',(314,820));reference.paste(source,(24,24))
        reference.save(QA/'source.png')
        page.goto(f'http://127.0.0.1:{app.server_port}/preview.html')
        page.wait_for_function('window.ready || window.failure');assert page.evaluate('window.failure') is None
        page.evaluate('huyWalk.fresh();huyWalk.advance(.4)')
        check('default_walk_controller','walk' in page.evaluate('huyWalk.events()'))
        page.evaluate('huyWalk.fresh(false);huyWalk.advance(.4)')
        idle=decode(page.evaluate('huyWalk.draw()'));idle.save(QA/'idle.png')
        mae=error(reference,idle)
        check('original_svg_fidelity',mae<1,mean_rgb_error=mae)
        eye_box=(108,160,245,208)
        eye_error=error(reference.crop(eye_box),idle.crop(eye_box))
        check('eye_details_match_svg',eye_error<1.5,mean_rgb_error=eye_error)
        frames=[decode(page.evaluate('t=>huyWalk.pose(t)',f/60)) for f in range(FRAMES+1)]
        check('continuous_walk',len({hashlib.sha256(im.tobytes()).hexdigest() for im in frames[:-1]})>65)
        check('seamless_walk_loop',error(frames[0],frames[-1])<.02,mean_rgb_error=error(frames[0],frames[-1]))
        bounds=[im.getchannel('A').getbbox() for im in frames]
        check('no_clipping',all(b and b[0]>0 and b[1]>0 and b[2]<314 and b[3]<820 for b in bounds))
        for name,box in [('left_arm',(24,360,100,548)),('right_arm',(222,360,292,540)),('knees',(45,565,265,675))]:
            change=max(error(frames[0].crop(box),im.crop(box)) for im in frames)
            check(name+'_moves',change>1,maximum_rgb_change=change)
        def sole(im,box):
            b=im.crop(box).getchannel('A').getbbox();return box[1]+b[3] if b else 0
        left=(40,705,165,815);right=(165,685,290,800)
        soles=[[sole(im,box) for im in [frames[18],frames[54]]] for box in [left,right]]
        check('alternating_24px_foot_lift',abs(soles[0][0]-soles[0][1]-24)<=1 and abs(soles[1][1]-soles[1][0]-24)<=1,soles=soles)
        check('stance_foot_grounded',soles[0][0]==sole(idle,left) and soles[1][1]==sole(idle,right))
        svg=ET.parse(ROOT/'huy_di_bo.svg').getroot()
        misses=0;placket_alpha=255
        for f,im in enumerate(frames):
            alpha=np.asarray(im)[:,:,3];g=gait(f)
            for y in range(448,474,2):
                placket_alpha=min(placket_alpha,int(alpha[round(y+24+g['bob']),185]))
            for index,count,side in [(2,2,None),(9,1,None),(46,3,'left'),(53,2,'right')]:
                for segment in list(parse_path(svg[index].get('d')))[:count]:
                    for t in [.15,.35,.55,.75,.9]:
                        point=segment.point(t)
                        point=point+complex(g[side+'_x'],g[side+'_y']) if side else arms(point,f)
                        point+=complex(24,24+g['bob'])
                        y,x=round(point.imag),round(point.real)
                        misses+=int(alpha[y-1:y+2,x-1:x+2].max())<40
        check('wrists_and_cuffs_stay_joined',misses==0,transparent_samples=misses)
        check('shirt_front_slit_has_underlay',placket_alpha>=250,minimum_alpha=placket_alpha)
        page.evaluate('huyWalk.fresh(true);huyWalk.advance(.4);huyWalk.setWalking(false);huyWalk.advance(.4)')
        check('stop_restores_idle',error(idle,decode(page.evaluate('huyWalk.draw()')))<.01)
        page.evaluate('huyWalk.setWalking(true);huyWalk.advance(.4)')
        check('resume_walk','walk' in page.evaluate('huyWalk.events()') and error(idle,decode(page.evaluate('huyWalk.draw()')))>.3)
        for _ in range(5):page.evaluate('huyWalk.setWalking(false);huyWalk.advance(.1);huyWalk.setWalking(true);huyWalk.advance(.1)')
        page.evaluate('huyWalk.setWalking(false);huyWalk.advance(.4)')
        check('rapid_toggle_returns_idle',error(idle,decode(page.evaluate('huyWalk.draw()')))<.01)
        for walking in [False,True]:
            page.evaluate('v=>{huyWalk.fresh(v,false);huyWalk.advance(.3)}',walking)
            right_state=decode(page.evaluate('huyWalk.draw()'))
            page.evaluate('v=>{huyWalk.fresh(v,true);huyWalk.advance(.3)}',walking)
            left_state=decode(page.evaluate('huyWalk.draw()'))
            expected='walk_left' if walking else 'idle_left'
            check(expected+'_controller',expected in page.evaluate('huyWalk.events()') and error(ImageOps.mirror(right_state),left_state)<.3)
        for anim in ['idle','walk']:
            right_im=decode(page.evaluate('a=>huyWalk.pose(.3,a)',anim))
            left_im=decode(page.evaluate('a=>huyWalk.pose(.3,a+"_left")',anim))
            check(anim+'_mirrors',error(ImageOps.mirror(right_im),left_im)<.3)
        page.evaluate('huyWalk.fresh(false);huyWalk.advance(2.7)')
        closed=decode(page.evaluate('huyWalk.draw()'));closed.save(QA/'blink.png')
        eye=(105,160,245,210)
        check('automatic_blink',error(idle.crop(eye),closed.crop(eye))>4)
        page.evaluate('huyWalk.advance(.6)')
        check('blink_reopens',error(idle,decode(page.evaluate('huyWalk.draw()')))<.01)
        page.evaluate('huyWalk.blink();huyWalk.advance(.12)')
        manual=decode(page.evaluate('huyWalk.draw()'))
        check('trigger_blink',error(idle.crop(eye),manual.crop(eye))>4)
        page.evaluate('huyWalk.advance(.6)')
        check('trigger_blink_reopens',error(idle,decode(page.evaluate('huyWalk.draw()')))<.01)
        for side in ['left','right']:
            poses=[leg_pose(side,f) for f in range(FRAMES+1)]
            check(side+'_leg_segment_lengths',all(abs(abs(k-h)-THIGH_LENGTH)<1e-6 and abs(abs(a-k)-SHIN_LENGTH)<1e-6 for h,k,a in poses))
        sheet=Image.new('RGB',(6*200,560),'#f4f6f8')
        for i,f in enumerate([0,12,24,36,48,60]):
            sheet.paste(white(frames[f]).resize((200,522)),(i*200,0));ImageDraw.Draw(sheet).text((i*200+12,535),f'{f/60:.1f}s',fill='#183c58')
        sheet.save(ROOT/'huy_di_bo_states.png')
        gif=[white(im).resize((220,574)) for im in frames[:-1:2]]
        gif[0].save(ROOT/'huy_di_bo_demo.gif',save_all=True,append_images=gif[1:],duration=[33,33,34]*12,loop=0)
        sheet=Image.new('RGB',(628,820),'#f4f6f8')
        sheet.paste(white(idle),(0,0));sheet.paste(white(closed),(314,0));sheet.save(ROOT/'huy_di_bo_blink.png')
        browser.close()
    app.shutdown()
    (QA/'runtime_validation.json').write_text(json.dumps(results,indent=2))
    if not all(r['passed'] for r in results):raise SystemExit(1)

if __name__=='__main__':main()
