"""Check exported shorts contours for folds/cusps and render enlarged comparisons."""
import json
import math
from pathlib import Path
import threading
import numpy as np
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
from check_walk import decode
from serve_walk import server

ROOT=Path(__file__).resolve().parents[1]
PROPS={'x':24,'y':25,'inRotation':84,'inDistance':85,'outRotation':86,'outDistance':87}

def main():
    qa=ROOT/'verification';art=json.loads((ROOT/'openrive-project.json').read_text())['artboards'][0]
    objects=art['objects'];names={o['props'].get('name'):o for o in objects}
    shape=names['ShortsContour'];path=next(o for o in objects if o['type']=='PointsPath' and o['props'].get('parentId')==shape['id'])
    vertices=[o for o in objects if o['props'].get('parentId')==path['id']]
    results=[]
    def check(name,passed,**details):
        results.append({'test':name,'passed':bool(passed),**details});print(name,'PASS' if passed else 'FAIL',flush=True)
    check('independent_shorts_geometry','Trousers' in names and 'SVG_001' not in names and shape['props']['parentId']==names['TrousersCoordinates']['id'])
    animation=next(a for a in art['animations'] if a['props']['name']=='walk')
    tracks={}
    for obj in animation['children']:
        for prop in obj.get('children',[]):
            keys=sorted((float(k['props'].get('frame',0)),float(k['props'].get('value',0))) for k in prop['children'])
            tracks[obj['props']['objectId'],prop['props']['propertyKey']]=np.array(keys)
    rest=np.array([[v['props'].get(p,0) for p in PROPS] for v in vertices],dtype=float)
    def pose(frame):
        values=rest.copy()
        for i,v in enumerate(vertices):
            for j,prop in enumerate(PROPS):
                keys=tracks.get((v['id'],PROPS[prop]))
                if keys is not None:values[i,j]=np.interp(frame,keys[:,0],keys[:,1])
        return values
    def contour(values):
        pos=values[:,0]+1j*values[:,1]
        incoming=pos+values[:,3]*np.exp(1j*values[:,2])
        outgoing=pos+values[:,5]*np.exp(1j*values[:,4])
        samples=[]
        for t in np.linspace(0,1,8,endpoint=False):
            samples.append((1-t)**3*pos+3*(1-t)**2*t*outgoing+3*(1-t)*t*t*np.roll(incoming,-1)+t**3*np.roll(pos,-1))
        return np.array(samples).T.reshape(-1)
    def angle(values):
        return np.abs((values[:,4]-values[:,2]+2*math.pi)%(2*math.pi)-math.pi)*180/math.pi
    bind=contour(rest);left=(bind.real<75)&(bind.imag>500)&(bind.imag<620)
    right=(bind.real>210)&(bind.imag>500)&(bind.imag<620)
    left_indices=np.where(left)[0][np.argsort(bind.imag[left])]
    right_indices=np.where(right)[0][np.argsort(bind.imag[right])]
    smooth=(angle(rest)<.02)&(rest[:,3]>.01)&(rest[:,5]>.01)
    waist=rest[:,1]<=490
    max_cusp=0;max_waist_drift=0;crossings=0;hip_reversals=0;worst_step=0
    prior=None
    for frame in np.arange(0,72.01,.5):
        values=pose(frame);points=contour(values)
        max_cusp=max(max_cusp,float(angle(values)[smooth].max()))
        max_waist_drift=max(max_waist_drift,float(np.abs(values[waist,:2]-rest[waist,:2]).max()))
        hip_reversals+=int(np.any(np.diff(points.real[left_indices])>.04) or np.any(np.diff(points.real[right_indices])<-.04))
        if prior is not None:worst_step=max(worst_step,float(np.abs(points-prior).max()))
        prior=points
        # Proper crossings between non-adjacent sampled outline segments.
        p=np.column_stack([points.real,points.imag]);delta=np.roll(p,-1,axis=0)-p
        q=p[None,:,:]-p[:,None,:]
        denominator=delta[:,None,0]*delta[None,:,1]-delta[:,None,1]*delta[None,:,0]
        valid=np.abs(denominator)>1e-9
        t=np.divide(q[:,:,0]*delta[None,:,1]-q[:,:,1]*delta[None,:,0],denominator,out=np.zeros_like(denominator),where=valid)
        u=np.divide(q[:,:,0]*delta[:,None,1]-q[:,:,1]*delta[:,None,0],denominator,out=np.zeros_like(denominator),where=valid)
        crossings+=int(np.any(valid&(t>1e-5)&(t<1-1e-5)&(u>1e-5)&(u<1-1e-5)))
    check('no_shorts_outline_crossings',crossings==0,frames_with_crossings=crossings,poses_checked=145)
    check('smooth_hips_without_bulges',hip_reversals==0,poses_with_reversed_hip_edges=hip_reversals)
    check('smooth_bezier_joins',max_cusp<.15,maximum_cusp_degrees=max_cusp)
    check('waistband_stays_fixed',max_waist_drift<.001,maximum_drift_px=max_waist_drift)
    check('no_contour_jumps',worst_step<1.2,maximum_half_frame_displacement_px=worst_step)
    app=server();threading.Thread(target=app.serve_forever,daemon=True).start()
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge');page=browser.new_page()
        old=browser.new_page();old.route('**/huy_di_bo.riv',lambda route:route.fulfill(body=(qa/'before-crotch.riv').read_bytes(),content_type='application/octet-stream'))
        url=f'http://127.0.0.1:{app.server_port}/preview.html'
        for tab in [page,old]:
            tab.goto(url);tab.wait_for_function('window.ready || window.failure');assert tab.evaluate('window.failure') is None
            tab.evaluate('document.getElementById("scene").width=628;document.getElementById("scene").height=1640')
        frames=[0,6,12,18,24,28,36,42,48,54,60,66]
        sheet=Image.new('RGB',(4*506,3*530),'#171717')
        for i,frame in enumerate(frames):
            im=decode(page.evaluate('t=>huyWalk.pose(t)',frame/60)).crop((30*2,460*2,283*2,710*2))
            sheet.paste(im,((i%4)*506,(i//4)*530),im)
            ImageDraw.Draw(sheet).text(((i%4)*506+16,(i//4)*530+508),f'Frame {frame} / 72',fill='white')
        sheet.save(ROOT/'huy_di_bo_pants_fixed.png')
        comparison=Image.new('RGB',(4*506,2*530),'#171717')
        for row,tab in enumerate([old,page]):
            for col,frame in enumerate([0,18,28,54]):
                im=decode(tab.evaluate('t=>huyWalk.pose(t)',frame/60)).crop((30*2,460*2,283*2,710*2))
                comparison.paste(im,(col*506,row*530),im)
                ImageDraw.Draw(comparison).text((col*506+16,row*530+508),f'{"Before" if row==0 else "Fixed"} - frame {frame}',fill='white')
        comparison.save(ROOT/'huy_di_bo_pants_before_after.png');browser.close()
    app.shutdown();(qa/'pants_validation.json').write_text(json.dumps(results,indent=2))
    if not all(r['passed'] for r in results):raise SystemExit(1)

if __name__=='__main__':main()
