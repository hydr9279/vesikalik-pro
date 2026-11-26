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
        await pg.keyboard.press('m'); await pg.wait_for_timeout(300)
        box=await pg.locator('#sahne .tuval-ic').bounding_box()
        x=box['x']+box['width']*0.2; y=box['y']+box['height']*0.85
        await pg.mouse.move(x,y); await pg.mouse.down()
        s0=await pg.evaluate("sahneResmi().src.length")
        ch=0; last=s0
        for i in range(25):
            await pg.mouse.move(x+i*6,y); await pg.wait_for_timeout(80)
            n=await pg.evaluate("sahneResmi().src.length")
            if n!=last: ch+=1; last=n
        await pg.screenshot(path=f'{OUT}/c2_surukle.png')
        await pg.mouse.up(); await pg.wait_for_timeout(3000)
        print('sürüklerken görüntü değişimi', ch, 'şekil sayısı', await pg.evaluate("S.st.sekil_sayisi"), errs)
        await b.close()
asyncio.run(main())
