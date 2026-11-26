import asyncio
from playwright.async_api import async_playwright
OUT='/home/claude/vp/test/shots'
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
        pg=await b.new_page(viewport={'width':1440,'height':900})
        errs=[]; pg.on('pageerror',lambda e: errs.append(str(e))); pg.on('console',lambda m: errs.append('console:'+m.text) if m.type=='error' else None)
        await pg.goto('http://127.0.0.1:8765/index.html'); await pg.wait_for_timeout(1500)
        await pg.evaluate("yollaEkle(['/home/claude/ornekler/orijinal/IMG_7923.JPG'])")
        await pg.wait_for_function("S.st && S.st.uygunluk", timeout=120000)
        # ana menü
        await pg.click('#btnAna'); await pg.wait_for_timeout(500)
        print('ana kartlar', await pg.locator('.kartlar .kart').count())
        await pg.screenshot(path=f'{OUT}/p1_ana.png')
        await pg.evaluate("S.ayar.model='isnet'; adimaGit(3)")
        await pg.wait_for_function("S.adim===3 && !mesgul", timeout=300000); await pg.wait_for_timeout(1500)
        # ölçekleme sürükleme: iki kez sürükle, ortada başka bir tıklama
        box=await pg.locator('.tuval-alan').bounding_box(); cx,cy=box['x']+box['width']/2, box['y']+box['height']/2
        await pg.mouse.click(60,500)
        dx0=await pg.evaluate("S.st.geom.dx")
        await pg.mouse.move(cx,cy); await pg.mouse.down(); await pg.mouse.move(cx+60,cy+20,steps=5); await pg.mouse.up(); await pg.wait_for_timeout(900)
        dx1=await pg.evaluate("S.st.geom.dx")
        await pg.mouse.move(cx,cy); await pg.mouse.down(); await pg.mouse.move(cx-30,cy-10,steps=5); await pg.mouse.up(); await pg.wait_for_timeout(900)
        dx2=await pg.evaluate("S.st.geom.dx")
        await pg.mouse.move(cx+200,cy); await pg.mouse.move(cx+250,cy+30)   # bırakıldıktan sonra takip etmemeli
        await pg.wait_for_timeout(300)
        print('dx',dx0,dx1,dx2,'sur',await pg.evaluate("document.querySelector('.tuval-ic img').style.transform"))
        # rötuş ekranı
        await pg.evaluate("adimaGit(2)"); await pg.wait_for_function("S.adim===2 && !mesgul", timeout=300000); await pg.wait_for_timeout(2500)
        await pg.screenshot(path=f'{OUT}/p2_rotus.png')
        await pg.click('.arac-d[data-a="l"]'); await pg.wait_for_timeout(300)
        box=await pg.locator('.tuval-alan').bounding_box()
        for dx in (-30,10,50): await pg.mouse.click(box['x']+box['width']/2+dx, box['y']+box['height']*0.5)
        print('bekleyen', await pg.evaluate("(S.bLeke[S.cur]||[]).length"))
        await pg.screenshot(path=f'{OUT}/p3_leke.png')
        await pg.click('#lUygula'); await pg.wait_for_function("!mesgul", timeout=120000); await pg.wait_for_timeout(1500)
        print('bekleyen sonra', await pg.evaluate("(S.bLeke[S.cur]||[]).length"), 'elle', await pg.evaluate("(S.st.lekeler||[]).filter(x=>x[2]).length"))
        # geri al fırçası
        await pg.click('.arac-d[data-a="g"]'); await pg.wait_for_timeout(300)
        await pg.mouse.move(box['x']+box['width']/2, box['y']+box['height']*0.5); await pg.mouse.down(); await pg.mouse.move(box['x']+box['width']/2+60, box['y']+box['height']*0.5+10, steps=5); await pg.mouse.up()
        await pg.wait_for_function("!mesgul", timeout=120000); await pg.wait_for_timeout(800)
        print('firca sayisi', await pg.evaluate("S.st.firca_sayisi"))
        await pg.screenshot(path=f'{OUT}/p4_geriAl.png')
        # modüller + düzenleme
        await pg.click('#btnAna'); await pg.wait_for_timeout(300)
        await pg.click('#kPol'); await pg.wait_for_timeout(500)
        await pg.evaluate("modulEkle(['/home/claude/ornekler/orijinal/IMG_7923.JPG','/home/claude/ornekler/orijinal/IMG_7920.JPG'])"); await pg.wait_for_timeout(3000)
        await pg.screenshot(path=f'{OUT}/p5_modul.png')
        await pg.locator('.modul-kart').first.dblclick(); await pg.wait_for_selector('#duzen .dz-fg', timeout=20000); await pg.wait_for_timeout(1000)
        box=await pg.locator('#dzAlan').bounding_box(); cx,cy=box['x']+box['width']/2, box['y']+box['height']/2
        await pg.mouse.move(cx,cy); await pg.mouse.down(); await pg.mouse.move(cx+50,cy+30,steps=5); await pg.mouse.up()
        await pg.mouse.wheel(0,-300); await pg.wait_for_timeout(300)
        print('p', await pg.evaluate("JSON.stringify(M.items[0].p)"))
        await pg.screenshot(path=f'{OUT}/p6_duzen.png')
        await pg.click('#dzSifir'); print('sifir', await pg.evaluate("M.items[0].p.zoom"))
        await pg.click('#dzTamam'); await pg.wait_for_timeout(500)
        print('modul acik', await pg.locator('#modul').count(), 'duzen', await pg.locator('#duzen').count())
        await pg.click('#mKapat'); await pg.wait_for_timeout(300); print('modul kapandi', await pg.locator('#modul').count()==0)
        await pg.evaluate("ayarlar('modeller')"); await pg.wait_for_timeout(1200)
        await pg.screenshot(path=f'{OUT}/p7_modeller.png')
        print('ERR',errs[:6]); await b.close()
asyncio.run(main())
