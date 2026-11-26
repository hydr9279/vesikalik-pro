import asyncio
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
        await pg.evaluate("S.ayar.model='isnet'; adimaGit(2)")
        await pg.wait_for_function("S.adim===2 && !mesgul", timeout=300000); await pg.wait_for_timeout(2500)
        await pg.screenshot(path=f'{OUT}/t0.png')
        await pg.evaluate("""()=>{const i=document.querySelector('#k_po');i.value=70;i.dispatchEvent(new Event('input',{bubbles:true}))}""")
        await pg.wait_for_timeout(300)
        print('filter', await pg.evaluate("sahneResmi().style.filter"))
        await pg.screenshot(path=f'{OUT}/t1.png')
        await pg.evaluate("""()=>{const i=document.querySelector('#k_po');i.dispatchEvent(new Event('change',{bubbles:true}))}""")
        await pg.wait_for_function("S.st.rotus.pozlama===70", timeout=60000); await pg.wait_for_timeout(1500)
        print('sonra filter', repr(await pg.evaluate("sahneResmi().style.filter")), errs)
        await pg.screenshot(path=f'{OUT}/t2.png')
        # fon çubuğu canlı (adım 1)
        await pg.evaluate("adimaGit(1)"); await pg.wait_for_function("S.adim===1 && !mesgul", timeout=120000); await pg.wait_for_timeout(1500)
        print('matte canlı')
        n=await pg.evaluate("""async()=>{const inp=document.querySelector('#k_yu');if(!inp)return 'yok';let ch=0,last=sahneResmi().src.length;
          for(let v=20;v<=80;v+=10){inp.value=v;inp.dispatchEvent(new Event('input',{bubbles:true}));await new Promise(r=>setTimeout(r,500));const n=sahneResmi().src.length;if(n!=last){ch++;last=n}}
          inp.dispatchEvent(new Event('change',{bubbles:true}));await new Promise(r=>setTimeout(r,4000));return [ch,S.st.matte.yumusaklik]}""")
        print(n, errs)
        await b.close()
asyncio.run(main())
