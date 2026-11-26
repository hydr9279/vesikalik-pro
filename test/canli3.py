import asyncio
from playwright.async_api import async_playwright
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
        js="""async(f)=>{const t=[];for(let i=0;i<4;i++){const a=performance.now();await f(i);t.push(Math.round(performance.now()-a));}return t}"""
        print('matte', await pg.evaluate("("+js+")((i)=>api.matte_onizle(S.cur,S.fid,{yumusaklik:30+i*5}))"))
        print('bg', await pg.evaluate("("+js+")((i)=>api.bg_onizle(S.cur,S.fid,{fon_aydinlat:10+i*5}))"))
        print('rotus yumusatma', await pg.evaluate("("+js+")((i)=>api.rotus_onizle(S.cur,S.fid,{...S.st.rotus,yumusatma:20+i*8}))"))
        print('rotus pozlama', await pg.evaluate("("+js+")((i)=>api.rotus_onizle(S.cur,S.fid,{...S.st.rotus,pozlama:i*10}))"))
        print('rotus leke', await pg.evaluate("("+js+")((i)=>api.rotus_onizle(S.cur,S.fid,{...S.st.rotus,leke:40+i*10}))"))
        print('omuz', await pg.evaluate("("+js+")((i)=>api.omuz_onizle(S.cur,S.fid,i*0.2))"))
        # UI: rötuş çubuğu sürükle
        await pg.evaluate("api.omuz_onizle(S.cur,S.fid,0)")
        n=await pg.evaluate("""async()=>{const inp=document.querySelector('#k_yu2');let ch=0,last=sahneResmi().src.length;
          for(let v=25;v<=70;v+=5){inp.value=v;inp.dispatchEvent(new Event('input',{bubbles:true}));await new Promise(r=>setTimeout(r,250));const n=sahneResmi().src.length;if(n!=last){ch++;last=n}}
          inp.dispatchEvent(new Event('change',{bubbles:true}));await new Promise(r=>setTimeout(r,4000));return [ch,S.st.rotus.yumusatma]}""")
        print('UI yumusatma canlı', n, errs)
        await b.close()
asyncio.run(main())
