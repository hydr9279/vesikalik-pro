import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
        pg=await b.new_page(viewport={'width':1440,'height':900})
        errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
        await pg.goto('http://127.0.0.1:8765/index.html'); await pg.wait_for_timeout(1500)
        await pg.evaluate("yollaEkle(['/tmp/kesik.jpg','/home/claude/ornekler/orijinal/IMG_7923.JPG'])")
        await pg.wait_for_function("S.st && S.st.uygunluk", timeout=120000); await pg.wait_for_timeout(1500)
        print('kadraj', await pg.evaluate("JSON.stringify(S.st.kadraj)"))
        await pg.screenshot(path='test/shots/x0.png')
        await pg.evaluate("document.querySelector('#kdYak') && document.querySelector('#kdYak').click()")
        await pg.wait_for_function("!mesgul", timeout=120000); await pg.wait_for_timeout(1500)
        print('sonra', await pg.evaluate("JSON.stringify([S.st.kadraj, S.st.geom])"))
        await pg.evaluate("S.ayar.model='isnet'; adimaGit(3)")
        await pg.wait_for_function("S.adim===3 && !mesgul", timeout=600000); await pg.wait_for_timeout(2500)
        for m in ('uzat','yumusat','doldur'):
            await pg.evaluate(f"cagir('update_settings',{{kenar_modu:'{m}'}}).then(()=>geomDegis({{zoom:S.st.geom.zoom*0.999}}))")
            await pg.wait_for_function("!mesgul", timeout=60000); await pg.wait_for_timeout(2500)
            await pg.screenshot(path=f'test/shots/x_{m}.png')
        # devam: 2. fotoğrafa geç, geri dön
        await pg.evaluate("kayitAl(); anaMenu()"); await pg.wait_for_timeout(500)
        ids=await pg.evaluate("S.isler.map(j=>j.id)")
        await pg.evaluate(f"isSec('{ids[1]}')"); await pg.wait_for_timeout(1500)
        print('2. foto adım', await pg.evaluate("S.adim"))
        await pg.evaluate(f"isSec('{ids[0]}')"); await pg.wait_for_function("!mesgul", timeout=60000); await pg.wait_for_timeout(2000)
        print('geri dönünce adım', await pg.evaluate("S.adim"), await pg.evaluate("JSON.stringify(S.st.geom)"), errs)
        await pg.screenshot(path='test/shots/x_devam.png')
        await b.close()
asyncio.run(main())
