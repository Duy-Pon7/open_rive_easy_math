"""Verify exported Rive vectors, swimming loop, stop/resume and frame bounds."""
import base64
import hashlib
import io
import json
import math
import threading
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright
from serve_fish import ROOT,server
from motion import FRAMES
from svgpathtools import Line,parse_path

QA=ROOT/'verification'


def decode(data):
    return Image.open(io.BytesIO(base64.b64decode(data.split(',')[1]))).convert('RGBA')


def white(im):
    return Image.alpha_composite(Image.new('RGBA',im.size,'white'),im).convert('RGB')


def error(a,b):
    return float(np.abs(np.asarray(white(a),dtype=float)-np.asarray(white(b),dtype=float)).mean())


def attachment_report(page,cycle):
    body=parse_path(ET.parse(ROOT/'fish.svg').getroot()[8].get('d'))
    roots={}
    for fin,xs,edge in [('dorsal',range(790,991,4),min),('ventral',range(815,946,4),max)]:
        roots[fin]=[]
        for x in xs:
            intersections=body.intersect(Line(complex(x,0),complex(x,1001)))
            y=edge(body.point(hit[0][0]).imag for hit in intersections)
            roots[fin].extend((x,y+offset) for offset in [-3,-2,-1,0,1,2,3])
    missing={fin:0 for fin in roots};minimum={fin:255 for fin in roots}
    worst=[]
    for i in range(17):
        time=cycle*i/16
        im=decode(page.evaluate('time=>fish.pose(time)',time))
        alpha=np.array(im)[:,:,3]
        t=2*math.pi*i/16
        angle=math.radians(.3*math.sin(t));c=math.cos(angle);s=math.sin(angle)
        dx=900+4*math.sin(t);dy=500+5*math.sin(t)
        bad=0
        for fin,points in roots.items():
            values=[]
            for x,y in points:
                px=round(dx+c*(x-900)-s*(y-500))
                py=round(dy+s*(x-900)+c*(y-500))
                values.append(int(alpha[py,px]))
            minimum[fin]=min(minimum[fin],min(values))
            absent=sum(v<200 for v in values)
            missing[fin]+=absent;bad+=absent
        worst.append((bad,i,im))
    worst.sort(key=lambda row:row[0],reverse=True)
    return {'missing_seam_samples':missing,'minimum_alpha':minimum,'poses':17},worst[0][2]


def main():
    app=server();threading.Thread(target=app.serve_forever,daemon=True).start()
    reports=[]
    def check(name,passed,**details):
        reports.append(dict(test=name,passed=bool(passed),**details))
        print(name,'PASS' if passed else 'FAIL',flush=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge')
        page=browser.new_page(viewport={'width':1570,'height':1001},device_scale_factor=1)
        page.goto((ROOT/'fish.svg').as_uri())
        ref=Image.open(io.BytesIO(page.screenshot(omit_background=True))).convert('RGBA')
        ref.save(QA/'source.png')
        page.goto(f'http://127.0.0.1:{app.server_port}/preview.html')
        page.wait_for_function('window.ready || window.failure')
        assert page.evaluate('window.failure') is None
        default=page.evaluate('fish.fresh()');page.evaluate('fish.advance(.4)')
        check('default_is_swimming',default=={'is_swimming':True} and 'swim' in page.evaluate('fish.events()'))
        page.evaluate('fish.fresh(false);fish.advance(.3)')
        idle=decode(page.evaluate('fish.draw()'));idle.save(QA/'idle.png')
        bounds=[im.getchannel('A').getbbox() for im in [ref,idle]]
        mae=error(ref,idle)
        check('original_svg_fidelity',mae<1 and np.max(np.abs(np.array(bounds[0])-np.array(bounds[1])))<=1,mean_rgb_error=mae,alpha_bounds=bounds)
        page.evaluate('fish.setSwim(true);fish.advance(.4)')
        frames=[]
        for f in range(FRAMES+1):
            if f:page.evaluate('fish.advance(1/60)')
            frames.append(decode(page.evaluate('fish.draw()')))
        hashes={hashlib.sha256(np.asarray(im).tobytes()).hexdigest() for im in frames[:-1]}
        check('swim_is_continuously_animated',len(hashes)>FRAMES*.85,distinct_frames=len(hashes))
        bboxes=[im.getchannel('A').getbbox() for im in frames]
        check('no_clipping_in_full_cycle',all(b and b[0]>0 and b[1]>0 and b[2]<1570 and b[3]<1001 for b in bboxes),extents=[min(b[0] for b in bboxes),min(b[1] for b in bboxes),max(b[2] for b in bboxes),max(b[3] for b in bboxes)])
        loop_error=error(frames[0],frames[FRAMES])
        check('loop_is_seamless',loop_error<.02,mean_rgb_error=loop_error,seconds=FRAMES/60)
        for label,region in [('tail',(40,100,560,960)),('dorsal_fin',(590,5,1030,280)),('ventral_fin',(660,770,980,990)),('pectoral_fin',(830,570,1060,730))]:
            motion=max(error(frames[0].crop(region),im.crop(region)) for im in frames[1:])
            check(label+'_moves',motion>.5,max_mean_rgb_change=motion)
        page.evaluate('fish.setSwim(false);fish.advance(.4)')
        stopped=decode(page.evaluate('fish.draw()'))
        check('stop_returns_to_exact_idle',np.array_equal(np.array(idle),np.array(stopped)) and 'idle' in page.evaluate('fish.events()'))
        page.evaluate('fish.clearEvents();fish.setSwim(true);fish.advance(.5)')
        check('resume_swimming','swim' in page.evaluate('fish.events()') and error(idle,decode(page.evaluate('fish.draw()')))>.5)
        events=page.evaluate('fish.events()')
        for _ in range(6):page.evaluate('fish.setSwim(false);fish.advance(.1);fish.setSwim(true);fish.advance(.1)')
        page.evaluate('fish.setSwim(false);fish.advance(.4)')
        check('rapid_toggle_stabilizes_to_idle',np.array_equal(np.array(idle),np.array(decode(page.evaluate('fish.draw()')))))
        sheet=Image.new('RGB',(3*471,2*330),'#eef7fa')
        for i,f in enumerate(round(FRAMES*i/6) for i in range(6)):
            frames[f].save(QA/f'swim_{f:02d}.png')
            sheet.paste(white(frames[f]).resize((471,300)),((i%3)*471,(i//3)*330))
            ImageDraw.Draw(sheet).text(((i%3)*471+12,(i//3)*330+307),f'{f/60:.2f}s',fill='#244754')
        sheet.save(ROOT/'fish_swim_states.png')
        gif=[white(im).resize((628,400)) for im in frames[:-1:2]]
        gif[0].save(ROOT/'fish_swim_demo.gif',save_all=True,append_images=gif[1:],duration=([33,33,34]*((len(gif)+2)//3))[:len(gif)],loop=0,disposal=2)
        attachment,worst=attachment_report(page,FRAMES/60)
        worst.save(QA/'fin-attachment-fixed.png')
        check('both_fin_roots_remain_opaque',sum(attachment['missing_seam_samples'].values())==0,**attachment)
        old_path=QA/'before-fin-attachment.riv'
        if old_path.exists():
            old_page=browser.new_page()
            old_page.route('**/fish_swim.riv',lambda route:route.fulfill(body=old_path.read_bytes(),content_type='application/octet-stream'))
            old_page.goto(f'http://127.0.0.1:{app.server_port}/preview.html')
            old_page.wait_for_function('window.ready || window.failure')
            assert old_page.evaluate('window.failure') is None
            old_attachment,old_worst=attachment_report(old_page,1.6)
            old_worst.save(QA/'fin-attachment-before.png')
            (QA/'fin-attachment-regression.json').write_text(json.dumps({'before':old_attachment,'after':attachment},indent=2))
            check('attachment_regression_detects_original_gap',sum(old_attachment['missing_seam_samples'].values())>0,**old_attachment)
        doc=json.loads((ROOT/'openrive-project.json').read_text())
        swim=next(a for a in doc['artboards'][0]['animations'] if a['props'].get('name')=='swim')
        check('tail_beat_is_20_percent_slower',swim['props']['duration']==120,old_beat_seconds=.8,new_beat_seconds=1)
        browser.close()
    app.shutdown()
    (QA/'runtime_validation.json').write_text(json.dumps(reports,indent=2))
    if not all(r['passed'] for r in reports):raise SystemExit(1)


if __name__=='__main__':main()
