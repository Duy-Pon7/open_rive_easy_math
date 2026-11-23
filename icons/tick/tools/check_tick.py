"""Validate the delivered tick using Rive's WASM runtime and save previews."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import base64,io,json,threading
import numpy as np
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
QA=ROOT/'verification'
class Handler(SimpleHTTPRequestHandler):
    extensions_map={**SimpleHTTPRequestHandler.extensions_map,'.mjs':'text/javascript','.wasm':'application/wasm'}
    def log_message(self,*args):pass
def decode(data):return Image.open(io.BytesIO(base64.b64decode(data.split(',')[1]))).convert('RGBA')

def main():
    app=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT)))
    threading.Thread(target=app.serve_forever,daemon=True).start()
    result={}
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge')
        page=browser.new_page(viewport={'width':900,'height':750})
        page.goto(f'http://127.0.0.1:{app.server_port}/preview.html')
        page.wait_for_function('window.ready || window.failure')
        assert page.evaluate('window.failure') is None
        original=decode(page.evaluate('''async()=>{const im=new Image();im.src='./tick.svg';await im.decode();const c=document.createElement('canvas');c.width=c.height=216;c.getContext('2d').drawImage(im,36,36,144,144);return c.toDataURL();}'''))
        samples=[]
        for label,t in [('Start',0),('Short stroke',.25),('Long stroke',.5),('Complete',.8),('Retract',56/60),('Advance',63/60),('Stopped',1.35)]:
            im=decode(page.evaluate('(t)=>tick.pose(t)',t));im.save(QA/(label.replace(' ','_').lower()+'.png'));samples.append((label,im))
        alpha=[np.array(im)[:,:,3] for label,im in samples]
        areas=[int((a>128).sum()) for a in alpha]
        error=float(np.abs(np.array(original).astype(float)-np.array(samples[-1][1]).astype(float)).mean())
        result['final_matches_original_svg']=error<.5
        result['draws_first_leg_then_second']=areas[0]<areas[1]<areas[2]<areas[3] and bool(alpha[1][124,65]>128 and alpha[1][81,147]==0 and alpha[2][117,110]>128)
        result['shortens_then_advances']=areas[4]<areas[5]<areas[3] and areas[3]-areas[4]>150
        result['returns_exactly_to_complete_tick']=np.array_equal(alpha[3],alpha[6])
        body_region=np.zeros((216,216),dtype=bool);body_region[90:170,36:140]=True
        # Trimming retessellates the same path. Allow only tiny edge AA changes.
        body_errors=[np.abs(alpha[3].astype(float)-a.astype(float))[body_region] for a in alpha[4:]]
        result['existing_stroke_stays_fixed']=all(float(d.mean())<.25 and float(d.max())<24 for d in body_errors)
        # All interior pixels keep the source opacity. Only normal edge AA varies.
        result['solid_stroke_during_drawing']=all(float((a>250).sum())/max(1,int((a>0).sum()))>.78 for a in alpha[1:])
        page.evaluate('tick.fresh()');frames=[];bounds=[]
        for i in range(67):
            im=decode(page.evaluate('()=>{tick.advance(1/30);return tick.draw()}'))
            bounds.append(im.getchannel('A').getbbox())
            bg=Image.new('RGBA',im.size,'#f3f6fb');bg.alpha_composite(im);frames.append(bg.convert('RGB'))
        held=decode(page.evaluate('tick.draw()'));page.evaluate('tick.advance(5)');later=decode(page.evaluate('tick.draw()'))
        result['holds_final_pose_5_seconds']=np.array_equal(np.array(held),np.array(later))
        result['state_machine_finishes_complete']=np.array_equal(np.array(samples[-1][1]),np.array(later))
        result['never_clips']=all(b and b[0]>0 and b[1]>0 and b[2]<216 and b[3]<216 for b in bounds)
        result['runtime']={'original_rgba_mean_error':error,'solid_areas':areas}
        frames[0].save(ROOT/'tick_preview.gif',save_all=True,append_images=frames[1:],duration=33,disposal=2)
        sheet=Image.new('RGB',(216*len(samples),246),'white');draw=ImageDraw.Draw(sheet)
        for i,(label,im) in enumerate(samples):sheet.paste(im,(i*216,24),im);draw.text((i*216+12,8),label,fill='#17304d')
        sheet.save(QA/'motion_contact_sheet.png');page.screenshot(path=str(QA/'preview.png'));browser.close()
    app.shutdown();(QA/'runtime_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
    assert all(v for k,v in result.items() if k!='runtime'),result

if __name__=='__main__':main()
