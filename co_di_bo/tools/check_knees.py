"""Verify exported joint tracks, knee flexion and rendered before/after poses."""
import json
import math
import threading
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
from svgpathtools import parse_path
from check_walk import decode,white,error
from serve_walk import ROOT,server

QA=ROOT/'verification'


def main():
    results=[]
    def check(name,passed,**details):
        results.append(dict(test=name,passed=bool(passed),**details))
        print(name,'PASS' if passed else 'FAIL',flush=True)
    art=json.loads((ROOT/'openrive-project.json').read_text())['artboards'][0]
    names={o['props'].get('name'):o for o in art['objects']}
    animation=next(a for a in art['animations'] if a['props']['name']=='walk')
    positions={}
    for side in ['Left','Right']:
        for joint in ['Hip','Knee','Ankle']:
            name=side+joint+'Joint';tracks={}
            for ko in animation['children']:
                if ko['props'].get('objectId')==names[name]['id']:
                    for prop in ko['children']:
                        tracks[prop['props']['propertyKey']]={int(k['props'].get('frame',0)):float(k['props'].get('value',0)) for k in prop['children']}
            positions[name]=[complex(tracks[13][f],tracks[14][f]) for f in range(73)]
    angles={}
    for side in ['Left','Right']:
        h=positions[side+'HipJoint'];k=positions[side+'KneeJoint'];a=positions[side+'AnkleJoint']
        upper=[abs(x-y) for x,y in zip(h,k)];lower=[abs(x-y) for x,y in zip(k,a)]
        flex=[]
        for hip,knee,ankle in zip(h,k,a):
            u=hip-knee;v=ankle-knee
            flex.append(180-math.degrees(math.acos(max(-1,min(1,(u.real*v.real+u.imag*v.imag)/(abs(u)*abs(v)))))))
        angles[side]=flex
        check(side.lower()+'_leg_keeps_segment_lengths',max(upper)-min(upper)<.002 and max(lower)-min(lower)<.002,thigh_range=[min(upper),max(upper)],shin_range=[min(lower),max(lower)])
        check(side.lower()+'_knee_bends_and_extends',max(flex)>58 and min(flex)<32 and max(flex)-min(flex)>30,flexion_range_degrees=[min(flex),max(flex)])
    check('knees_alternate_during_swing',angles['Right'][18]>angles['Left'][18]+25 and angles['Left'][54]>angles['Right'][54]+25)
    app=server();threading.Thread(target=app.serve_forever,daemon=True).start()
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge');page=browser.new_page()
        url=f'http://127.0.0.1:{app.server_port}/preview.html'
        page.goto(url);page.wait_for_function('window.ready || window.failure');assert page.evaluate('window.failure') is None
        # Compare with the actual delivered file from before the knee update.
        old=browser.new_page();old.route('**/co_di_bo.riv',lambda route:route.fulfill(body=(QA/'before-knees.riv').read_bytes(),content_type='application/octet-stream'))
        old.goto(url);old.wait_for_function('window.ready || window.failure');assert old.evaluate('window.failure') is None
        changes=[];sheet=Image.new('RGB',(4*260,2*330),'#f7f0f5')
        svg=ET.parse(ROOT/'co_di_bo.svg').getroot()
        cuffs={side:parse_path(svg[index].get('d'))[0] for side,index in [('Left',191),('Right',193)]}
        bob_tracks={}
        for ko in animation['children']:
            if ko['props'].get('objectId')==names['CharacterRoot']['id']:
                for prop in ko['children']:
                    if prop['props']['propertyKey']==14:
                        bob_tracks={int(k['props'].get('frame',0)):float(k['props'].get('value',0))-550 for k in prop['children']}
        cuff_misses=0;minimum_alpha=255
        for i,f in enumerate([6,18,42,54]):
            before=decode(old.evaluate('f=>coWalk.pose(f/60,"walk")',f))
            after=decode(page.evaluate('f=>coWalk.pose(f/60,"walk")',f))
            alpha=np.array(after)[:,:,3]
            for side,bind in [('Left',complex(195,750)),('Right',complex(302,747))]:
                shift=positions[side+'AnkleJoint'][f]-bind+complex(0,bob_tracks[f])
                for t in np.linspace(.05,.95,25):
                    point=cuffs[side].point(t)+shift
                    value=int(alpha[round(point.imag),round(point.real)])
                    minimum_alpha=min(minimum_alpha,value);cuff_misses+=value<40
            region=(115,555,405,840)
            changes.append(error(before.crop((130,610,395,695)),after.crop((130,610,395,695))))
            for row,(im,label) in enumerate([(before,'Before'),(after,'Knee bend')]):
                sheet.paste(white(im).crop(region).resize((260,285)),(i*260,row*330))
                ImageDraw.Draw(sheet).text((i*260+12,row*330+300),f'{label} - {f/60:.2f}s',fill='#533e55')
        check('knee_deformation_visible_in_exported_frames',min(changes)>2,mean_rgb_changes=changes)
        check('cuffs_remain_joined_to_ankles',cuff_misses==0,transparent_samples=cuff_misses,minimum_alpha=minimum_alpha)
        sheet.save(ROOT/'co_di_bo_knees.png')
        for walking,left in [(False,False),(False,True),(True,False),(True,True)]:
            page.evaluate('v=>{coWalk.fresh(v[0],v[1]);coWalk.advance(.3);}',[walking,left])
            image=decode(page.evaluate('coWalk.draw()'))
            check('valid_pose_'+str(walking)+'_'+str(left),image.getchannel('A').getbbox() is not None)
        browser.close()
    app.shutdown()
    (QA/'knee_validation.json').write_text(json.dumps(results,indent=2))
    if not all(r['passed'] for r in results):raise SystemExit(1)


if __name__=='__main__':main()
