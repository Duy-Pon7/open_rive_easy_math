"""Validate the exported one-shot trigger and compare the burst with the SVG."""
import base64,io,json,threading,xml.etree.ElementTree as ET
import numpy as np
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
from serve_clappers import server,ROOT

QA=ROOT/'verification'
def decode(value):return Image.open(io.BytesIO(base64.b64decode(value.split(',')[1]))).convert('RGBA')
def rays(im):
    p=np.array(im).astype(float)
    return int(np.count_nonzero((p[:,:,0]>p[:,:,2]+60)&(p[:,:,1]>p[:,:,2]+60)&(abs(p[:,:,0]-p[:,:,1])<45)&(p[:,:,3]>25)))
def similarity(a,b):
    aa=np.array(a).astype(float);bb=np.array(b).astype(float)
    ma=aa[:,:,3]>127;mb=bb[:,:,3]>127
    iou=float(np.count_nonzero(ma&mb)/np.count_nonzero(ma|mb))
    ca=aa[:,:,:3]*aa[:,:,3:]/255+255-aa[:,:,3:]
    cb=bb[:,:,:3]*bb[:,:,3:]/255+255-bb[:,:,3:]
    return dict(silhouette_iou=iou,mean_rgb_error=float(np.abs(ca-cb).mean()))
def main():
    app=server();threading.Thread(target=app.serve_forever,daemon=True).start();results=[]
    def check(name,passed,**extra):
        results.append(dict(test=name,passed=bool(passed),**extra));print(name,bool(passed),flush=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge');page=browser.new_page(viewport=dict(width=1200,height=800));errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(f'http://127.0.0.1:{app.server_port}/preview.html');page.wait_for_function('window.ready || window.failure',timeout=30000)
        assert page.evaluate('window.failure') is None,page.evaluate('window.failure')
        page.wait_for_timeout(200);idle=decode(page.evaluate('clappers.draw()'));idle.save(QA/'idle.png')
        check('starts_in_idle',page.evaluate('clappers.events().at(-1)')=='idle')
        page.wait_for_timeout(250)
        check('idle_stationary_without_calls',idle.tobytes()==decode(page.evaluate('clappers.draw()')).tobytes())
        check('no_burst_at_idle',rays(idle)==0)
        def reference(show_rays):
            svg=ET.parse(ROOT/'phach.svg').getroot()
            if not show_rays:
                for e in list(svg):
                    if e.get('fill')=='#E5DB6C':svg.remove(e)
            return decode(page.evaluate('''async (svg)=>{
                const i=new Image();i.src='data:image/svg+xml;base64,'+btoa(svg);await i.decode();
                const c=document.createElement('canvas');c.width=994;c.height=672;
                c.getContext('2d').drawImage(i,0,0,994,672);return c.toDataURL('image/png');
            }''',ET.tostring(svg,encoding='unicode')))
        source_idle=reference(False);source_burst=reference(True)
        source_idle.save(QA/'original_svg_idle_reference.png');source_burst.save(QA/'original_svg_burst_reference.png')
        match=similarity(idle,source_idle)
        check('idle_keeps_original_svg_positions',match['silhouette_iou']>.995 and match['mean_rgb_error']<1,**match)
        # Exercise the actual exported data-binding trigger, without the demo queue.
        page.evaluate('clappers.fireRaw()');page.wait_for_timeout(210)
        check('raw_hit_trigger_enters_hit',page.evaluate('clappers.events().at(-1)')=='hit')
        check('strike_has_visible_burst',rays(decode(page.evaluate('clappers.draw()')))>1000)
        page.wait_for_timeout(700)
        check('one_call_auto_returns_idle',page.evaluate('clappers.events().at(-1)')=='idle' and idle.tobytes()==decode(page.evaluate('clappers.draw()')).tobytes())
        count=page.evaluate("clappers.events().filter(x=>x==='hit').length")
        page.wait_for_timeout(1400)
        check('no_repeat_without_another_call',page.evaluate("clappers.events().filter(x=>x==='hit').length")==count and idle.tobytes()==decode(page.evaluate('clappers.draw()')).tobytes())
        page.evaluate('clappers.fireRaw()');page.wait_for_timeout(800)
        check('next_call_strikes_exactly_once',page.evaluate("clappers.events().filter(x=>x==='hit').length")==count+1 and page.evaluate('clappers.events().at(-1)')=='idle')
        # The app-facing helper queues rapid requests so none are overwritten.
        before=page.evaluate("clappers.events().filter(x=>x==='hit').length")
        page.evaluate('async ()=>{await Promise.all(Array.from({length:4},()=>clappers.hit()));}')
        page.wait_for_timeout(100)
        check('four_rapid_calls_produce_four_strikes',page.evaluate("clappers.events().filter(x=>x==='hit').length")==before+4,
              counts=page.evaluate('clappers.counts()'))
        check('queue_finishes_at_original_idle',idle.tobytes()==decode(page.evaluate('clappers.draw()')).tobytes() and not page.evaluate('clappers.counts().busy'))
        frames=[decode(page.evaluate('(t)=>clappers.pose(t)',f/60)) for f in range(37)]
        for label,f in [('open',5),('before_contact',9),('contact',10),('rebound',16),('settled',30)]:frames[f].save(QA/(label+'.png'))
        match=similarity(frames[10],source_burst)
        check('burst_matches_reference_svg_shape_size_and_placement',match['silhouette_iou']>.995 and match['mean_rgb_error']<1,**match)
        check('burst_only_after_contact',rays(frames[9])==0 and rays(frames[10])>1000)
        check('burst_fades_after_strike',rays(frames[22])==0 and rays(frames[36])==0)
        check('one_shot_ends_in_exact_idle',frames[36].tobytes()==idle.tobytes())
        bounds=[im.getchannel('A').getbbox() for im in frames]
        check('all_frames_inside_original_canvas',all(b and b[0]>=0 and b[1]>=0 and b[2]<=994 and b[3]<=672 for b in bounds))
        check('transparent_background',all(im.getpixel((993,671))[3]==0 for im in frames))
        check('no_runtime_errors',not errors,errors=errors)
        page.evaluate('()=>clappers.pose(10/60)');page.screenshot(path=str(QA/'preview.png'));browser.close()
    doc=json.loads((ROOT/'openrive-project.json').read_text());art=doc['artboards'][0]
    check('hit_timeline_is_one_shot',next(a for a in art['animations'] if a['props']['name']=='hit')['props']['loopValue']==0)
    check('only_hit_trigger_no_playing_boolean',[(o['type'],o['props'].get('name')) for o in doc['top'] if o['type'].startswith('ViewModelProperty')]==[('ViewModelPropertyTrigger','hit')])
    check('four_original_rays_and_no_ring',len([o for o in art['objects'] if o['props'].get('name','').startswith('Impact Ray ')])==4 and not any(o['props'].get('name')=='Impact Ring' for o in art['objects']))
    sheet=Image.new('RGB',(1200,325),'white');d=ImageDraw.Draw(sheet)
    for x,label,im in [(0,'IDLE',idle),(400,'HIT',frames[10]),(800,'RETURN TO IDLE',frames[36])]:
        thumb=im.resize((400,270));sheet.paste(thumb,(x,40),thumb);d.text((x+18,15),label,fill='#533a25')
    sheet.save(ROOT/'phach_states.png')
    gif=[]
    for im in frames:
        bg=Image.new('RGBA',im.size,'white');bg.alpha_composite(im);gif.append(bg.convert('RGB').resize((597,403)))
    # No GIF loop extension: the preview itself demonstrates one strike.
    gif[0].save(ROOT/'phach_demo.gif',save_all=True,append_images=gif[1:],duration=[17]*36+[900])
    (QA/'runtime_validation.json').write_text(json.dumps(results,indent=2));app.shutdown()
    assert all(r['passed'] for r in results),results

if __name__=='__main__':main()
