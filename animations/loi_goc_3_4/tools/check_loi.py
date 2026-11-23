"""Deterministic tests against the delivered .riv in the WASM Rive Runtime."""
from pathlib import Path
import base64
import hashlib
import io
import json
import threading
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright
from serve_loi import server, ROOT

QA=ROOT/'verification'
OUT=ROOT


def decode(url):
    return Image.open(io.BytesIO(base64.b64decode(url.split(',')[1]))).convert('RGBA')


def white(im):
    bg=Image.new('RGBA',im.size,'white')
    return Image.alpha_composite(bg,im).convert('RGB')


def same_mouth(a,b):
    return np.array_equal(np.array(a)[225:271,196:255],np.array(b)[225:271,196:255])


def check():
    QA.mkdir(exist_ok=True,parents=True)
    app=server()
    threading.Thread(target=app.serve_forever,daemon=True).start()
    reports=[]
    def result(name,passed,**details):
        reports.append(dict(test=name,status='PASS' if passed else 'FAIL',**details))
        print(name,reports[-1]['status'],flush=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge')
        page=browser.new_page(viewport={'width':328,'height':818},device_scale_factor=1)
        page.goto((ROOT/'loi_goc_3_4.svg').as_uri())
        page.screenshot(path=str(QA/'source.png'),omit_background=True)
        page.goto(f'http://127.0.0.1:{app.server_port}/preview.html')
        page.wait_for_function('window.ready || window.failure')
        assert page.evaluate('window.failure') is None
        inputs=page.evaluate('loi.fresh()')
        result('runtime_load_and_contract',set(inputs)=={'viseme_id','is_talking','blink','reset','head_only'},inputs=inputs,runtime='@rive-app/canvas-advanced 2.45.0')
        rest=decode(page.evaluate('loi.draw()'))
        rest.save(QA/'rest.png')
        head_only=decode(page.evaluate('()=>{loi.setHeadOnly(true);loi.advance(.1);return loi.draw();}'))
        head_only.save(QA/'head_only.png')
        baseline_head=decode(page.evaluate('()=>{loi.fresh();loi.advance(.1);return loi.draw();}'))
        result('head_only_hides_body_preserves_head',
               not np.any(np.array(head_only)[340:,:,3]) and
               np.array_equal(np.array(head_only)[:285],np.array(baseline_head)[:285]) and
               np.any(np.array(baseline_head)[350:,:,3]))
        restored=decode(page.evaluate('()=>{loi.fresh();loi.setHeadOnly(true);loi.advance(.1);loi.setHeadOnly(false);loi.advance(.1);return loi.draw();}'))
        full_expected=decode(page.evaluate('()=>{loi.fresh();loi.advance(.2);return loi.draw();}'))
        restored.save(QA/'restored.png');full_expected.save(QA/'full_expected.png')
        restored_diff=np.any(np.array(restored)!=np.array(full_expected),axis=2)
        result('head_only_false_restores_body',not np.any(restored_diff),changed_pixels=int(restored_diff.sum()))
        head_talking=decode(page.evaluate('()=>{loi.fresh();loi.setHeadOnly(true);loi.set(2,true);loi.advance(.275);loi.fire("blink");loi.advance(.075);return loi.draw();}'))
        full_talking=decode(page.evaluate('()=>{loi.fresh();loi.set(2,true);loi.advance(.275);loi.fire("blink");loi.advance(.075);return loi.draw();}'))
        result('head_only_preserves_talking_and_blink',
               np.array_equal(np.array(head_talking)[:285],np.array(full_talking)[:285]) and
               not np.any(np.array(head_talking)[340:,:,3]) and not same_mouth(head_talking,rest))
        page.evaluate('loi.fresh()')
        ref=Image.open(QA/'source.png').convert('RGBA')
        a,b=np.array(white(ref)),np.array(white(rest))
        mae=float(np.abs(a.astype(float)-b).mean())
        bbox=[list(im.getchannel('A').getbbox()) for im in (ref,rest)]
        result('source_design_match',mae<2 and np.max(np.abs(np.array(bbox[0])-bbox[1]))<=1,mean_absolute_rgb_error=mae,alpha_bounds=bbox)
        white(ref).save(QA/'source_white.png');white(rest).save(QA/'rest_white.png')
        names=page.evaluate('loi.names')
        poses=[]
        for i,name in enumerate(names):
            data=page.evaluate('(i)=>{loi.fresh();loi.set(i,true);loi.advance(.4);return loi.snapshot();}',i)
            im=decode(data['image']);im.save(QA/f'viseme_{i:02d}_{name}.png');poses.append(im)
            expected='mouth_rest' if i==0 else 'viseme_'+name
            result(f'input_{i:02d}_{name}',expected in data['events'],states=data['events'])
        # Every pose is compared at the same elapsed time: only mouth pixels may differ.
        mask=np.ones((818,328),dtype=bool);mask[225:271,196:255]=False
        outside=[int(np.max(np.abs(np.array(poses[0]).astype(int)-np.array(im).astype(int))[mask])) for im in poses]
        hashes=[hashlib.sha256(np.array(im)[225:271,196:255].tobytes()).hexdigest() for im in poses]
        result('12_distinct_mouths',len(set(hashes))==12,distinct=len(set(hashes)))
        changed_outside=[int(np.any(np.array(poses[0])!=np.array(im),axis=2)[mask].sum()) for im in poses]
        result('eyes_hair_body_unchanged_by_viseme',max(changed_outside)<=4,
               max_changed_pixels_outside_mouth=max(changed_outside),
               max_channel_difference_outside_mouth=max(outside),
               note='Allow at most 4 edge rasterization pixels outside the mouth; mouth pixels checked exactly.')
        # Tests all ordered pairs, checking destination state and absence of REST detours.
        pairs=page.evaluate('''()=>{const out=[];for(let a=0;a<12;a++)for(let b=0;b<12;b++)if(a!==b){loi.fresh();loi.set(a,true);loi.advance(.2);loi.clearEvents();loi.set(b,true);loi.advance(.2);const events=loi.events();const expected=b===0?'mouth_rest':'viseme_'+loi.names[b];out.push({from:a,to:b,events,pass:events.includes(expected)&&(b===0||!events.includes('mouth_rest'))});}return out;}''')
        (QA/'all_pairs.json').write_text(json.dumps(pairs,indent=2),encoding='utf8')
        result('all_132_direct_transitions',all(v['pass'] for v in pairs),pairs=len(pairs),failed=[v for v in pairs if not v['pass']])
        sweep=page.evaluate('''()=>{loi.fresh();const out=[];for(const id of [...Array(12).keys(),0]){loi.set(id,true);loi.advance(.15);out.push({id,events:loi.events()});loi.clearEvents();}return out;}''')
        (QA/'sweep.json').write_text(json.dumps(sweep,indent=2),encoding='utf8')
        result('0_to_11_to_0_sweep',all(('mouth_rest' if x['id']==0 else 'viseme_'+names[x['id']]) in x['events'] for x in sweep))
        stopped=page.evaluate('''()=>{loi.fresh();loi.set(11,true);loi.advance(.2);loi.clearEvents();loi.set(11,false);loi.advance(.2);return loi.snapshot();}''')
        stopped_im=decode(stopped['image']);stopped_im.save(QA/'stopped.png')
        expected_stopped=decode(page.evaluate('()=>{loi.fresh();loi.set(0,true);loi.advance(.2);loi.set(0,false);loi.advance(.2);return loi.draw();}'))
        result('stop_returns_rest',same_mouth(stopped_im,expected_stopped) and 'head_rest' in stopped['events'],events=stopped['events'])
        reset=page.evaluate('''()=>{loi.fresh();loi.set(11,true);loi.advance(.2);loi.clearEvents();loi.fire('reset');loi.advance(.2);return loi.snapshot();}''')
        reset_im=decode(reset['image']);reset_im.save(QA/'reset.png')
        result('native_reset_latches_rest',same_mouth(reset_im,poses[0]),events=reset['events'])
        page.evaluate('()=>{loi.set(0,false);loi.advance(.1);loi.set(4,true);loi.clearEvents();loi.advance(.2);}')
        result('resume_after_reset','viseme_O_ROUND' in page.evaluate('loi.events()'))
        for invalid in (-1,12,2.5):
            data=page.evaluate('''id=>{loi.fresh();loi.set(2,true);loi.advance(.2);loi.clearEvents();loi.set(id,true);loi.advance(.2);return loi.snapshot();}''',invalid)
            result(f'invalid_id_{invalid}_rests',same_mouth(decode(data['image']),poses[0]),events=data['events'])
        # Blink comparison at matched elapsed time: all differences must stay inside the eyes.
        baseline=decode(page.evaluate('()=>{loi.fresh();loi.set(2,true);loi.advance(.275);return loi.draw();}'))
        blinkdata=page.evaluate('''()=>{loi.fresh();loi.set(2,true);loi.advance(.2);loi.fire('blink');loi.advance(.075);return loi.snapshot();}''')
        blinkim=decode(blinkdata['image']);blinkim.save(QA/'blink_closed.png')
        diff=np.any(np.array(baseline)!=np.array(blinkim),axis=2)
        eye_mask=np.zeros_like(diff);eye_mask[160:217,147:292]=True
        result('blink_independent_of_mouth',int(diff.sum())>100 and not np.any(diff&~eye_mask),changed_eye_pixels=int(diff.sum()),events=blinkdata['events'])
        returned=decode(page.evaluate('()=>{loi.advance(.225);return loi.draw();}'))
        open_expected=decode(page.evaluate('()=>{loi.fresh();loi.set(2,true);loi.advance(.5);return loi.draw();}'))
        result('blink_returns_open',np.array_equal(np.array(returned),np.array(open_expected)))
        # Capture actual morph frames; source contains only one outline and one cavity.
        morph=[]
        for ms in (0,15,30,45,60,90):
            im=decode(page.evaluate('''ms=>{loi.fresh();loi.set(2,true);loi.advance(.2);loi.set(5,true);loi.advance(ms/1000);return loi.draw();}''',ms))
            im.save(QA/f'morph_{ms:03d}ms.png');morph.append(im)
        result('interpolated_transition_frames',len({np.array(im)[225:271,196:255].tobytes() for im in morph})>=5,distinct_samples=len({np.array(im)[225:271,196:255].tobytes() for im in morph}))
        # Execute every event in the exact demo sentence through the native inputs.
        sentence=page.evaluate('''()=>{loi.fresh();const rows=[];for(const e of loi.sentence){loi.clearEvents();loi.set(e.id,true);loi.advance(e.ms/1000);rows.push({...e,events:loi.events()});}loi.set(0,false);loi.advance(.2);return {rows,final:loi.inputValues(),image:loi.draw()};}''')
        decode(sentence.pop('image')).save(QA/'sentence_end.png')
        (QA/'sentence_demo.json').write_text(json.dumps(sentence,ensure_ascii=False,indent=2),encoding='utf8')
        result('vietnamese_sentence_demo',len(sentence['rows'])>40 and sentence['final']=={'id':0,'talking':False},events=len(sentence['rows']))
        # A portable animated preview is generated from actual runtime frames.
        frames=[]
        page.evaluate('loi.fresh()')
        for idx in [*range(12),0]:
            page.evaluate('id=>loi.set(id,true)',idx)
            for _ in range(6):
                frame=white(decode(page.evaluate('()=>{loi.advance(.075);return loi.draw();}'))).resize((232,579),Image.Resampling.LANCZOS)
                ImageDraw.Draw(frame).text((8,8),f'{idx:02d} {names[idx]}',fill='#16324a')
                frames.append(frame)
        frames[0].save(OUT/'loi_goc_3_4_noi_viseme_demo.gif',save_all=True,append_images=frames[1:],duration=75,loop=0)
        browser.close()
    app.shutdown()
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
    sheet=Image.new('RGB',(1200,900),'#edf3f7')
    for i,im in enumerate(poses):
        x=(i%4)*300;y=(i//4)*300
        crop=white(im).crop((140,135,302,282)).resize((280,222),Image.Resampling.LANCZOS)
        sheet.paste(crop,(x+10,y+42));ImageDraw.Draw(sheet).text((x+14,y+10),f'{i:02d}  {names[i]}',font=font,fill='#16324a')
    sheet.save(OUT/'loi_goc_3_4_noi_viseme_sheet.png')
    flutter_report=QA/'flutter_validation.json'
    report=dict(checks=reports,failures=sum(r['status']=='FAIL' for r in reports),
                flutter_runtime=json.loads(flutter_report.read_text(encoding='utf8')) if flutter_report.exists() else dict(status='NOT TESTED',reason='Run the separate Flutter test project.'),
                openrive_diagnostics=json.loads((ROOT/'verification/openrive-diagnostics.json').read_text(encoding='utf8')))
    (QA/'runtime_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    assert report['failures']==0, 'See verification/runtime_validation.json'


if __name__=='__main__':
    check()


