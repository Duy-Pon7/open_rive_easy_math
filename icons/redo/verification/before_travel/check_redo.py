"""Check the actual Rive runtime, export a contact sheet and one-shot GIF."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
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
        rest=decode(page.evaluate('redo.fresh()'))
        original=decode(page.evaluate('''async()=>{const image=new Image();image.src='./redo.svg';await image.decode();const canvas=document.createElement('canvas');canvas.width=canvas.height=216;canvas.getContext('2d').drawImage(image,36,36,144,144);return canvas.toDataURL();}'''))
        samples=[]
        for label,t in [('Empty',0),('Tail',.24),('Around curve',.4),('Head',.64),('Complete',.8),('Bounce',1.05),('Stopped',1.35)]:
            im=decode(page.evaluate('(t)=>redo.pose(t)',t));im.save(QA/(label.replace(' ','_').lower()+'.png'));samples.append((label,im))
        stopped=samples[-1][1]
        result['starts_empty']=rest.getchannel('A').getbbox() is None
        result['final_pose_matches_original_svg']=bool(np.abs(np.array(original).astype(float)-np.array(stopped).astype(float)).mean()<.5)
        full_alpha=np.array(samples[4][1])[:,:,3]
        areas=[];fixed_pixels=True
        for t in np.linspace(0,.8,49):
            reveal=decode(page.evaluate('(t)=>redo.pose(t)',float(t)))
            alpha=np.array(reveal)[:,:,3]
            areas.append(int((alpha>128).sum()))
            fixed_pixels &= not bool(np.any((alpha>128)&(full_alpha<64)))
        result['reveals_progressively']=all(a<=b for a,b in zip(areas,areas[1:])) and len(set(areas))>25
        result['revealed_pixels_stay_fixed']=fixed_pixels
        tail_alpha=np.array(samples[1][1])[:,:,3]
        result['tail_appears_before_head']=bool(tail_alpha[153,156]>128 and tail_alpha[60,165]==0)
        result['bounce_lifts_icon']=samples[5][1].getchannel('A').getbbox()[1]<samples[4][1].getchannel('A').getbbox()[1]-6
        page.evaluate('redo.fresh()')
        frames=[];bounds=[]
        for i in range(67):
            frame=decode(page.evaluate('()=>{redo.advance(1/30);return redo.draw()}'))
            bounds.append(frame.getchannel('A').getbbox())
            bg=Image.new('RGBA',frame.size,'#f3f6fb');bg.alpha_composite(frame);frames.append(bg.convert('RGB'))
        result['never_clips']=all(b[0]>0 and b[1]>0 and b[2]<216 and b[3]<216 for b in bounds if b)
        held=decode(page.evaluate('redo.draw()'))
        page.evaluate('redo.advance(5)')
        later=decode(page.evaluate('redo.draw()'))
        result['holds_final_pose_for_5_seconds']=np.array_equal(np.array(held),np.array(later))
        result['state_machine_holds_complete_icon']=np.array_equal(np.array(stopped),np.array(later))
        result['runtime']=page.evaluate('redo.info()')
        # No GIF loop extension: the sample plays once and stops.
        frames[0].save(ROOT/'redo_preview.gif',save_all=True,append_images=frames[1:],duration=33,disposal=2)
        sheet=Image.new('RGB',(216*len(samples),246),'white');draw=ImageDraw.Draw(sheet)
        for i,(label,im) in enumerate(samples):
            sheet.paste(im,(i*216,24),im);draw.text((i*216+12,8),label,fill='#17304d')
        sheet.save(QA/'motion_contact_sheet.png')
        page.screenshot(path=str(QA/'preview.png'))
        browser.close()
    app.shutdown()
    (QA/'runtime_validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    assert all(v for k,v in result.items() if k!='runtime'),result

if __name__=='__main__':main()
