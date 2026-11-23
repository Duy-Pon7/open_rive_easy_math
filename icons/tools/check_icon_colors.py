"""Exercise the actual color binding in both delivered Rive files."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import base64,io,json,threading
import numpy as np
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
    extensions_map={**SimpleHTTPRequestHandler.extensions_map,'.mjs':'text/javascript','.wasm':'application/wasm'}
    def log_message(self,*args):pass
def decode(url):return Image.open(io.BytesIO(base64.b64decode(url.split(',')[1]))).convert('RGBA')

def main():
    app=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT)))
    threading.Thread(target=app.serve_forever,daemon=True).start()
    palette=['#0d99ff','#22c55e','#ef4444','#a855f7','#123456','#000000','#ffffff']
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge')
        for name in ['tick','redo']:
            page=browser.new_page(viewport={'width':900,'height':800})
            page.goto(f'http://127.0.0.1:{app.server_port}/{name}/preview.html')
            page.wait_for_function('window.ready || window.failure');assert page.evaluate('window.failure') is None
            result={};samples=[]
            for label,t in [('during_motion',.4),('after_stop',1.6)]:
                page.evaluate('(n)=>window[n].fresh()',name)
                page.evaluate('([n,t])=>window[n].advance(t)',[name,t])
                before=np.array(decode(page.evaluate('(n)=>window[n].draw()',name)))
                elapsed=page.evaluate('(n)=>window[n].info().elapsed',name)
                for color in palette:
                    im=decode(page.evaluate('([n,c])=>window[n].setColor(c)',[name,color]));pixels=np.array(im)
                    expected=tuple(bytes.fromhex(color[1:]));solid=pixels[:,:,3]==255
                    # Layered AA edges can round a fully opaque RGB channel by 1.
                    result[label+'_'+color]=bool(np.any(solid) and np.max(np.abs(pixels[:,:,:3][solid].astype(float)-expected))<=1)
                    result[label+'_geometry_unchanged_'+color]=np.array_equal(pixels[:,:,3],before[:,:,3])
                    result[label+'_does_not_restart_'+color]=page.evaluate('(n)=>window[n].info().elapsed',name)==elapsed
                    if label=='after_stop':samples.append((color,im))
            page.evaluate('''()=>{const input=document.getElementById('iconColor');input.value='#22c55e';input.dispatchEvent(new Event('input',{bubbles:true}));}''')
            result['color_picker_works']=page.evaluate('(n)=>window[n].color()',name)=='#22c55e'
            page.evaluate('(n)=>{window[n].fresh();window[n].advance(1.6);}',name)
            pixels=np.array(decode(page.evaluate('(n)=>window[n].draw()',name)))
            result['replay_keeps_selected_color']=bool(np.max(np.abs(pixels[:,:,:3][pixels[:,:,3]==255].astype(float)-(34,197,94)))<=1)
            sheet=Image.new('RGB',(216*len(samples),246),'#e8edf4');draw=ImageDraw.Draw(sheet)
            for i,(color,im) in enumerate(samples):sheet.paste(im,(i*216,24),im);draw.text((i*216+12,8),color,fill='#17304d')
            sheet.save(ROOT/name/(name+'_colors.png'))
            page.screenshot(path=str(ROOT/name/'verification/color_picker.png'))
            (ROOT/name/'verification/color_validation.json').write_text(json.dumps(result,indent=2))
            print(name,json.dumps({'passed':sum(result.values()),'checks':len(result),'failures':[k for k,v in result.items() if not v]}),flush=True)
            assert all(result.values()),result
            page.close()
        browser.close()
    app.shutdown()

if __name__=='__main__':main()
