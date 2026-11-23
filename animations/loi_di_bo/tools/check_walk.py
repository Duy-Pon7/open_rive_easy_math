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
from motion import FRAMES,gait,arms,body,leg_pose,THIGH_LENGTH,SHIN_LENGTH
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
    check('source_svg_unchanged',hashlib.sha256((ROOT/'loi_di_bo.svg').read_bytes()).hexdigest()==manifest['source_sha256'])
    app=server();threading.Thread(target=app.serve_forever,daemon=True).start()
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge')
        page=browser.new_page(viewport={'width':328,'height':818},device_scale_factor=1)
        page.goto((ROOT/'loi_di_bo.svg').as_uri())
        source=Image.open(io.BytesIO(page.screenshot(omit_background=True))).convert('RGBA')
        reference=Image.new('RGBA',(376,866));reference.paste(source,(24,24))
        reference.save(QA/'source.png')
        page.goto(f'http://127.0.0.1:{app.server_port}/preview.html')
        page.wait_for_function('window.ready || window.failure');assert page.evaluate('window.failure') is None
        page.evaluate('loiWalk.fresh();loiWalk.advance(.4)')
        check('default_walk_controller','walk' in page.evaluate('loiWalk.events()'))
        page.evaluate('loiWalk.fresh(false);loiWalk.advance(.4)')
        idle=decode(page.evaluate('loiWalk.draw()'));idle.save(QA/'idle.png')
        mae=error(reference,idle)
        check('original_svg_fidelity',mae<1,mean_rgb_error=mae)
        eye_box=(175,190,314,240)
        eye_error=error(reference.crop(eye_box),idle.crop(eye_box))
        check('eye_details_match_svg',eye_error<1.5,mean_rgb_error=eye_error)
        frames=[decode(page.evaluate('t=>loiWalk.pose(t)',f/60)) for f in range(FRAMES+1)]
        check('continuous_walk',len({hashlib.sha256(im.tobytes()).hexdigest() for im in frames[:-1]})>65)
        check('seamless_walk_loop',error(frames[0],frames[-1])<.02,mean_rgb_error=error(frames[0],frames[-1]))
        bounds=[im.getchannel('A').getbbox() for im in frames]
        check('no_clipping',all(b and b[0]>0 and b[1]>0 and b[2]<376 and b[3]<866 for b in bounds))
        for name,box in [('left_arm',(50,420,145,600)),('right_arm',(290,420,365,600)),('knees',(75,600,310,735))]:
            change=max(error(frames[0].crop(box),im.crop(box)) for im in frames)
            check(name+'_moves',change>1,maximum_rgb_change=change)
        def sole(im,box):
            b=im.crop(box).getchannel('A').getbbox();return box[1]+b[3] if b else 0
        left=(85,745,215,855);right=(215,735,345,835)
        soles=[[sole(im,box) for im in [frames[18],frames[54]]] for box in [left,right]]
        check('alternating_28px_foot_lift',abs(soles[0][0]-soles[0][1]-28)<=1 and abs(soles[1][1]-soles[1][0]-28)<=1,soles=soles)
        check('stance_foot_grounded',soles[0][0]==sole(idle,left) and soles[1][1]==sole(idle,right))
        svg=ET.parse(ROOT/'loi_di_bo.svg').getroot()
        seams=[(35,[0,1,2],None),(53,[0],None),(109,[0],'left'),(111,[1,2],'right')]
        misses=0
        for f,im in enumerate(frames):
            alpha=np.asarray(im)[:,:,3];g=gait(f)
            for index,segments,side in seams:
                for j in segments:
                    segment=list(parse_path(svg[index].get('d')))[j]
                    for t in [.1,.3,.5,.7,.9]:
                        z=segment.point(t)
                        z=z+complex(g[side+'_x'],g[side+'_y']) if side else body(z,f)
                        z+=complex(24,24+g['bob']);x,y=round(z.real),round(z.imag)
                        misses+=int(alpha[y-1:y+2,x-1:x+2].max())<40
        check('wrists_and_trouser_cuffs_stay_joined',misses==0,transparent_samples=misses)
        minimum=10
        for f in range(0,FRAMES+1,3):
            for y in range(565,726,7):
                for x in range(65,280,7):
                    if source.getpixel((x,y))[3]<250:continue
                    z=complex(x,y)
                    dx=(body(z+.01,f)-body(z-.01,f))/.02
                    dy=(body(z+.01j,f)-body(z-.01j,f))/.02
                    minimum=min(minimum,dx.real*dy.imag-dx.imag*dy.real)
        check('trousers_do_not_fold_inside_out',minimum>.05,minimum_jacobian=minimum)
        page.evaluate('loiWalk.fresh(true);loiWalk.advance(.4);loiWalk.setWalking(false);loiWalk.advance(.4)')
        check('stop_restores_idle',error(idle,decode(page.evaluate('loiWalk.draw()')))<.01)
        page.evaluate('loiWalk.setWalking(true);loiWalk.advance(.4)')
        check('resume_walk','walk' in page.evaluate('loiWalk.events()') and error(idle,decode(page.evaluate('loiWalk.draw()')))>.3)
        for _ in range(5):page.evaluate('loiWalk.setWalking(false);loiWalk.advance(.1);loiWalk.setWalking(true);loiWalk.advance(.1)')
        page.evaluate('loiWalk.setWalking(false);loiWalk.advance(.4)')
        check('rapid_toggle_returns_idle',error(idle,decode(page.evaluate('loiWalk.draw()')))<.01)
        for walking in [False,True]:
            page.evaluate('v=>{loiWalk.fresh(v,false);loiWalk.advance(.3)}',walking)
            right_state=decode(page.evaluate('loiWalk.draw()'))
            page.evaluate('v=>{loiWalk.fresh(v,true);loiWalk.advance(.3)}',walking)
            left_state=decode(page.evaluate('loiWalk.draw()'))
            expected='walk_left' if walking else 'idle_left'
            check(expected+'_controller',expected in page.evaluate('loiWalk.events()') and error(ImageOps.mirror(right_state),left_state)<.3)
        for anim in ['idle','walk']:
            right_im=decode(page.evaluate('a=>loiWalk.pose(.3,a)',anim))
            left_im=decode(page.evaluate('a=>loiWalk.pose(.3,a+"_left")',anim))
            check(anim+'_mirrors',error(ImageOps.mirror(right_im),left_im)<.3)
        page.evaluate('loiWalk.fresh(false);loiWalk.advance(2.7)')
        closed=decode(page.evaluate('loiWalk.draw()'));closed.save(QA/'blink.png')
        eye=(175,190,314,240)
        check('automatic_blink',error(idle.crop(eye),closed.crop(eye))>4)
        page.evaluate('loiWalk.advance(.6)')
        check('blink_reopens',error(idle,decode(page.evaluate('loiWalk.draw()')))<.01)
        page.evaluate('loiWalk.blink();loiWalk.advance(.12)')
        manual=decode(page.evaluate('loiWalk.draw()'))
        check('trigger_blink',error(idle.crop(eye),manual.crop(eye))>4)
        page.evaluate('loiWalk.advance(.6)')
        check('trigger_blink_reopens',error(idle,decode(page.evaluate('loiWalk.draw()')))<.01)
        for side in ['left','right']:
            poses=[leg_pose(side,f) for f in range(FRAMES+1)]
            check(side+'_leg_segment_lengths',all(abs(abs(k-h)-THIGH_LENGTH)<1e-6 and abs(abs(a-k)-SHIN_LENGTH)<1e-6 for h,k,a in poses))
        sheet=Image.new('RGB',(6*220,540),'#f4f6f8')
        for i,f in enumerate([0,12,24,36,48,60]):
            sheet.paste(white(frames[f]).resize((220,507)),(i*220,0));ImageDraw.Draw(sheet).text((i*220+12,520),f'{f/60:.1f}s',fill='#183c58')
        sheet.save(ROOT/'loi_di_bo_states.png')
        gif=[white(im).resize((240,553)) for im in frames[:-1:2]]
        gif[0].save(ROOT/'loi_di_bo_demo.gif',save_all=True,append_images=gif[1:],duration=[33,33,34]*12,loop=0)
        sheet=Image.new('RGB',(752,866),'#f4f6f8')
        sheet.paste(white(idle),(0,0));sheet.paste(white(closed),(376,0));sheet.save(ROOT/'loi_di_bo_blink.png')
        browser.close()
    app.shutdown()
    (QA/'runtime_validation.json').write_text(json.dumps(results,indent=2))
    if not all(r['passed'] for r in results):raise SystemExit(1)

if __name__=='__main__':main()
