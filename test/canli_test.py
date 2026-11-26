import asyncio, time
from playwright.async_api import async_playwright
OUT='/home/claude/vp/test/shots'
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
        pg=await b.new_page(viewport={'width':1440,'height':900})
        errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
        await pg.goto('http://127.0.0.1:8765/index.html'); await pg.wait_for_timeout(1500)
        await pg.evaluate("yollaEkle(['/home/claude/ornekler/orijinal/IMG_7923.JPG'])")
        await pg.wait_for_function("S.st && S.st.uygunluk", timeout=120000)
        await pg.evaluate("S.ayar.model='isnet'; adimaGit(3)")
        await pg.wait_for_function("S.adim===3 && !mesgul", timeout=300000); await pg.wait_for_timeout(2000)
        src0=await pg.evaluate("sahneResmi().src.length")
        r=await pg.evaluate("""async()=>{const t=[];const inp=document.querySelector('#k_zo');
          for(let v=100; v<=120; v+=2){const t0=performance.now(); inp.value=v; inp.dispatchEvent(new Event('input',{bubbles:true}));
            await new Promise(r=>setTimeout(r,60)); t.push(Math.round(performance.now()-t0));}
          await new Promise(r=>setTimeout(r,1500)); return {src:sahneResmi().src.length, busy:CANLI.busy, z:S.st.geom.zoom}}""")
        print('canli zoom', r, 'önce', src0)
        await pg.evaluate("document.querySelector('#k_zo').dispatchEvent(new Event('change',{bubbles:true}))")
        await pg.wait_for_timeout(2500)
        print('son zoom', await pg.evaluate("S.st.geom.zoom"))
        await pg.screenshot(path=f'{OUT}/c1.png')
        # çağrı süresi
        tm=await pg.evaluate("""async()=>{const t=[];for(let i=0;i<5;i++){const a=performance.now();await api.geom_onizle(S.cur,S.fid,{zoom:1+i*0.02});t.push(Math.round(performance.now()-a));}return t}""")
        print('geom_onizle ms', tm)
        # şekillendir
        await pg.evaluate("adimaGit(2)"); await pg.wait_for_function("S.adim===2 && !mesgul", timeout=300000); await pg.wait_for_timeout(2500)
        tm=await pg.evaluate("""async()=>{const t=[];for(let i=0;i<4;i++){const a=performance.now();await api.sekil_onizle(S.cur,S.fid,{tur:'it',pts:[[0.3,0.8],[0.32+i*0.01,0.8],[0.36+i*0.01,0.8]],r:0.08,guc:0.6});t.push(Math.round(performance.now()-a));}return t}""")
        print('sekil_onizle ms', tm, errs)
        await b.close()
asyncio.run(main())
