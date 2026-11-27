import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
        pg=await b.new_page(viewport={'width':1440,'height':900})
        await pg.goto('http://127.0.0.1:8765/index.html'); await pg.wait_for_timeout(1500)
        await pg.evaluate("yollaEkle(['/home/claude/ornekler/orijinal/IMG_7923.JPG'])")
        await pg.wait_for_function("S.st && S.st.uygunluk", timeout=120000)
        await pg.evaluate("S.ayar.model='isnet'; adimaGit(2)")
        await pg.wait_for_function("S.adim===2 && !mesgul", timeout=500000)
        r=await pg.evaluate("cagir('spot_toplu', S.cur, S.fid, [[0.5,0.5,0.02,0.5],[0.55,0.6]]).then(r=>JSON.stringify({ok:r.ok,hata:r.hata,g:r.gecmis,n:(r.lekeler||[]).length}))")
        print(r)
        r=await pg.evaluate("cagir('genel_geri_al', S.cur, S.fid,'rotus').then(r=>JSON.stringify({ok:r.ok,hata:r.hata,g:r.gecmis,n:(r.lekeler||[]).length}))")
        print(r)
        r=await pg.evaluate("cagir('genel_ileri_al', S.cur, S.fid,'rotus').then(r=>JSON.stringify({ok:r.ok,hata:r.hata,g:r.gecmis,n:(r.lekeler||[]).length}))")
        print(r)
        await b.close()
asyncio.run(main())
