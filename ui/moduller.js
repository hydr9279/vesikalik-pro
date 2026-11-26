// Polaroid ve Serbest Baskı modülleri (yüz tanıma yok: kırpmasız + bulanık dolgu)
const M = {tur: null, items: [], sec: 0, sayfa: 0, kagit: "10x15", gelismis: false, yazicilar: [], yazici: "", klasor: ""};
const VARS = {zoom: 1, dx: 0, dy: 0, rot: 0, mod: "sigdir", poz: 0, parlaklik: 0, kontrast: 0, doygunluk: 0, sicaklik: 0};

function modulAc(tur) {
  M.tur = tur; M.items = []; M.sec = 0; M.sayfa = 0; M.gelismis = false; M.klasor = "";
  document.querySelector("#modul")?.remove();
  const ek = h(`<div id="modul" class="modul-ekran"></div>`);
  document.body.append(ek);
  modulCiz();
  if (tur === "serbest") api.serbest_yazicilar().then(r => { M.yazicilar = r.yazicilar || []; M.yazici = r.varsayilan || ""; modulCiz(); });
  else { M.yazicilar = (S.init.yazicilar || []); M.yazici = S.ayar.varsayilan_yazici || M.yazicilar[0] || ""; }
}
function modulKapat() { document.querySelector("#modul")?.remove(); }

const mAdet = (i) => (M.tur === "serbest" ? i.adet : 1);
async function modulEkle(yollar) {
  const r = await api.modul_dosyalar(yollar);
  r.forEach(x => M.items.push({yol: x.yol, ad: x.ad, adet: 1, p: {...VARS}, th: null}));
  modulCiz();
}
let mZaman = {};
function onizleYenile(i, gecik = 120) {
  clearTimeout(mZaman[i.yol]);
  mZaman[i.yol] = setTimeout(async () => {
    const r = await api.modul_onizle(M.tur, i.yol, i.p, M.kagit);
    if (r && r.gorsel) { i.th = r.gorsel; const im = document.querySelector(`[data-yol="${CSS.escape(i.yol)}"] img`); if (im) im.src = i.th; if (M.items[M.sec] === i) { const b = document.querySelector("#mBuyuk img"); if (b) b.src = i.th; } }
  }, gecik);
}

function modulCiz() {
  const ek = document.querySelector("#modul"); if (!ek) return;
  const sirket = M.tur === "polaroid" ? "POLAROID · Instax Square" : "SERBEST BASKI";
  const per = M.tur === "serbest" ? 6 : 6;
  const sayfaSay = Math.max(1, Math.ceil(M.items.length / per));
  M.sayfa = Math.min(M.sayfa, sayfaSay - 1);
  const goster = M.items.slice(M.sayfa * per, M.sayfa * per + per);
  const secili = M.items[M.sec];
  ek.innerHTML = "";
  const ust = h(`<div class="modul-ust"><b>${sirket}</b><span class="not" style="margin-left:12px">${M.tur === "polaroid" ? "Fotoğraflar kırpılmadan sığdırılır, boşluklar bulanık dolgu olur. Tek kalan foto için Hayal Medya çerçevesi eklenir." : "Her fotoğraf seçilen kağıt boyutunda ayrı baskı olur. Çift tıkla: gelişmiş düzenleme sayfası."}</span><span style="flex:1"></span><button class="btn kucuk" id="mEkle">+ Fotoğraf ekle</button><button class="btn kucuk" id="mKlasor">+ Klasör ekle</button><button class="btn kucuk" id="mKapat" title="Ana menüye dön (Esc)">⌂ Ana menüye dön</button></div>`);
  $("#mEkle", ust).onclick = async () => { const y = await api.pick_files(); if (y?.length) modulEkle(y); };
  $("#mKlasor", ust).onclick = async () => { const k = await api.pick_folder(); if (k) modulEkle([k]); };
  $("#mKapat", ust).onclick = modulKapat;
  ek.append(ust);
  const govde = h(`<div class="modul-govde"></div>`);
  // sol: ızgara
  const sol = h(`<div class="modul-sol"></div>`);
  if (!M.items.length) sol.append(h(`<div class="birak" style="margin:40px"><b style="color:var(--yazi)">Fotoğraf ekleyin</b><span>Dosya veya klasör seçin, ya da buraya bırakın</span></div>`));
  const izgara = h(`<div class="modul-izgara"></div>`);
  goster.forEach((it, k) => {
    const idx = M.sayfa * per + k;
    const kart = h(`<div class="modul-kart ${idx === M.sec ? "secili" : ""}" data-yol="${esc(it.yol)}"><div class="modul-th ${M.tur === "polaroid" ? "kare" : ""}"><img alt="${esc(it.ad)}" src="${it.th || ""}"></div><div class="modul-alt"><span class="ad" title="${esc(it.ad)}">${esc(it.ad)}</span>${M.tur === "serbest" ? `<span class="adet"><button data-d="-">−</button><b>${it.adet}</b><button data-d="+">+</button></span>` : ""}<span class="poz"><button data-p="-" title="Koyulaştır">☾</button><button data-p="+" title="Aydınlat">☀</button></span><button class="sil" title="Listeden çıkar">✕</button></div></div>`);
    kart.onclick = (e) => { if (e.target.closest("button")) return; M.sec = idx; modulCiz(); };
    kart.ondblclick = () => { M.sec = idx; duzenAc(idx); };
    $$("button[data-d]", kart).forEach(b => b.onclick = () => { it.adet = Math.max(1, Math.min(99, it.adet + (b.dataset.d === "+" ? 1 : -1))); modulCiz(); });
    $$("button[data-p]", kart).forEach(b => b.onclick = () => { it.p.poz = Math.max(-1.5, Math.min(1.5, +(it.p.poz + (b.dataset.p === "+" ? 0.15 : -0.15)).toFixed(2))); onizleYenile(it, 0); modulCiz(); });
    $(".sil", kart).onclick = () => { M.items.splice(idx, 1); M.sec = Math.max(0, Math.min(M.sec, M.items.length - 1)); modulCiz(); };
    izgara.append(kart);
    if (!it.th) onizleYenile(it, 30 + k * 40);
  });
  sol.append(izgara);
  if (sayfaSay > 1) {
    const sn = h(`<div class="satir" style="justify-content:center;padding:10px"><button class="btn kucuk" id="mOnce">‹ Önceki</button><span>Sayfa ${M.sayfa + 1} / ${sayfaSay}</span><button class="btn kucuk" id="mSonra">Sonraki ›</button></div>`);
    $("#mOnce", sn).onclick = () => { M.sayfa = Math.max(0, M.sayfa - 1); modulCiz(); };
    $("#mSonra", sn).onclick = () => { M.sayfa = Math.min(sayfaSay - 1, M.sayfa + 1); modulCiz(); };
    sol.append(sn);
  }
  govde.append(sol);
  // sağ: ayarlar
  const sag = h(`<div class="modul-sag"></div>`);
  if (M.tur === "serbest") {
    const k = h(`<div class="alan"><label>Kağıt boyutu</label><select id="mKagit">${["10x15", "13x18", "15x21"].map(x => `<option ${M.kagit === x ? "selected" : ""}>${x}</option>`).join("")}</select></div>`);
    $("select", k).onchange = (e) => { M.kagit = e.target.value; M.items.forEach(i => { i.th = null; }); modulCiz(); };
    sag.append(k);
  }
  if (secili) {
    const b = h(`<div class="bolum"><h3>${esc(secili.ad)}</h3></div>`);
    const set = (k) => (v) => { secili.p[k] = v; onizleYenile(secili, 80); };
    b.append(h(`<div class="modul-buyuk" id="mBuyuk" style="cursor:pointer" title="Tıklayın: gelişmiş düzenleme sayfası"><img src="${secili.th || ""}" alt=""></div>`));
    const modSel = h(`<div class="alan"><label>Yerleşim</label><select><option value="sigdir" ${secili.p.mod === "sigdir" ? "selected" : ""}>Kırpmadan sığdır (bulanık dolgu)</option><option value="doldur" ${secili.p.mod === "doldur" ? "selected" : ""}>Alanı doldur (kırp)</option></select></div>`);
    $("select", modSel).onchange = (e) => { secili.p.mod = e.target.value; onizleYenile(secili, 0); };
    b.append(modSel);
    b.append(kaydirici("mz", "Yakınlaştırma", secili.p.zoom, 0.5, 3, 0.01, "×", set("zoom")));
    const dz = h(`<button class="btn genis ana" style="height:44px;font-size:14px" title="Büyük ekranda kaydır, yakınlaştır, renk ayarla">✎ Gelişmiş düzenleme sayfası</button>`);
    dz.onclick = () => duzenAc(M.sec);
    b.append(dz);
    sag.append(b);
  }
  // kayıt / yazdırma
  const kb = h(`<div class="bolum"><h3>KAYIT VE BASKI</h3>
    <div class="alan"><label>Kayıt klasörü <span class="not">(boşsa kaydederken sorulur)</span></label><div class="satir"><input type="text" id="mKl" value="${esc(M.klasor)}"><button class="btn kucuk" id="mSec">Seç</button></div></div>
    ${M.tur === "polaroid" ? `<div class="satir"><div class="alan"><label>Arşiv no</label><input type="text" id="mNo"></div><div class="alan"><label>Müşteri</label><input type="text" id="mAd"></div></div>` : ""}
    <div class="alan"><label>Yazıcı</label><select id="mYz">${M.yazicilar.map(x => `<option ${x === M.yazici ? "selected" : ""}>${esc(x)}</option>`).join("")}</select></div>
    ${M.tur === "polaroid" ? `<div class="alan"><label>Sayfa kopyası</label><input type="number" min="1" max="20" value="1" id="mKop"></div>` : ""}
    <div class="satir"><button class="btn genis" id="mKaydet">Sadece kaydet</button><button class="btn ana genis" id="mYazdir">Kaydet ve yazdır</button></div></div>`);
  $("#mSec", kb).onclick = async () => { const k = await api.pick_folder(M.klasor); if (k) { M.klasor = k; $("#mKl", kb).value = k; } };
  $("#mKl", kb).oninput = (e) => M.klasor = e.target.value;
  $("#mYz", kb).onchange = (e) => M.yazici = e.target.value;
  const git = async (yazdir) => {
    if (!M.items.length) { bildir("Önce fotoğraf ekleyin.", true); return; }
    if (!M.klasor) {   // uyarı yerine doğrudan klasör seçtir
      const k = await api.pick_folder(M.klasor); if (!k) return;
      M.klasor = k; const inp = document.querySelector("#mKl"); if (inp) inp.value = k;
    }
    if (yazdir && !M.yazici) { bildir("Yazıcı seçilmedi.", true); return; }
    let r;
    if (M.tur === "polaroid") r = await cagir("polaroid_kaydet", M.items.map(i => ({yol: i.yol, p: i.p})), {klasor: M.klasor, no: $("#mNo", kb).value, musteri: $("#mAd", kb).value, yazdir, yazici: M.yazici, kopya: +($("#mKop", kb)?.value || 1)});
    else r = await cagir("serbest_kaydet", M.items.map(i => ({yol: i.yol, adet: i.adet, p: i.p})), M.kagit, {klasor: M.klasor, yazdir, yazici: M.yazici});
    if (r.ok) { const kl = r.klasor || M.klasor; bildir(`${r.dosyalar.length} dosya kaydedildi${yazdir ? " ve yazıcıya gönderildi" : ""}`, false, {ad: "Klasörü aç", fn: () => api.open_folder(kl || (r.dosyalar[0] || ""))}); }
  };
  $("#mKaydet", kb).onclick = () => git(false);
  $("#mYazdir", kb).onclick = () => git(true);
  sag.append(kb);
  govde.append(sag);
  ek.append(govde);
  if (M.tur === "polaroid" && M.items.length) {
    const ps = h(`<div class="modul-sayfa-onizleme"><span class="not">Baskı sayfası önizlemesi (10x15, iki kart)</span><div id="mSayfalar"></div></div>`);
    ek.append(ps);
    clearTimeout(M._pt);
    M._pt = setTimeout(async () => { const r = await api.polaroid_sayfalar(M.items.map(i => ({yol: i.yol, p: i.p}))); const c = document.querySelector("#mSayfalar"); if (c && r.sayfalar) c.innerHTML = r.sayfalar.map(s => `<img src="${s}" alt="sayfa">`).join(""); }, 400);
  }
}
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && document.querySelector("#modul") && !document.querySelector("#duzen") && $("#modal").classList.contains("gizli")) modulKapat(); });


// ------------------------------------------------------------------ Gelişmiş düzenleme sayfası (Polaroid / Serbest)
// Kaydırma, yakınlaştırma ve renk ayarları tarayıcıda anında çalışır; asıl baskı çıktısı motorda tam hesaplanır.
const DZ = {};
async function duzenAc(idx) {
  const it = M.items[idx]; if (!it) return;
  document.querySelector("#duzen")?.remove();
  M.sec = idx;
  const r = await cagir("modul_resim", M.tur, it.yol, M.kagit);
  if (!r.ok) return;
  const kok = h(`<div id="duzen" class="duzen">
    <div class="duzen-ust"><b id="dzAd"></b><span class="not" id="dzSay"></span><span style="flex:1"></span>
      <button class="btn kucuk" id="dzOnce" title="Önceki fotoğraf">‹ Önceki</button><button class="btn kucuk" id="dzSonra" title="Sonraki fotoğraf">Sonraki ›</button>
      <button class="btn kucuk ana" id="dzTamam" title="Değişiklikler korunur, listeye dön (Esc)">✓ Tamam</button></div>
    <div class="duzen-govde"><div class="duzen-alan" id="dzAlan"><div class="duzen-cerceve" id="dzCerceve"><div class="dz-bg"></div><img class="dz-fg" alt="" draggable="false"></div></div>
      <div class="duzen-sag" id="dzSag"></div></div>
    <div class="duzen-alt"><span>Sürükle: fotoğrafı kaydır · Tekerlek: yakınlaştır · [ ]: eğim · Ok tuşları: ince kaydırma</span><span id="dzDurum"></span></div>
    <svg width="0" height="0" style="position:absolute"><filter id="dzF" color-interpolation-filters="sRGB"><feComponentTransfer><feFuncR id="dzR" type="linear" slope="1" intercept="0"/><feFuncG id="dzG" type="linear" slope="1" intercept="0"/><feFuncB id="dzB" type="linear" slope="1" intercept="0"/></feComponentTransfer></filter></svg></div>`);
  document.body.append(kok);
  const alan = $("#dzAlan", kok), cer = $("#dzCerceve", kok), fg = $(".dz-fg", kok), bg = $(".dz-bg", kok);
  fg.src = r.gorsel; bg.style.backgroundImage = `url(${r.gorsel})`;
  const D = DZ.d = {idx, cw: r.cw, ch: r.ch, iw: r.iw, ih: r.ih};

  const yerlestir = () => {
    const ar = alan.getBoundingClientRect(), k = Math.min((ar.width - 40) / D.cw, (ar.height - 40) / D.ch);
    const W = Math.round(D.cw * k), H = Math.round(D.ch * k);
    Object.assign(cer.style, {width: W + "px", height: H + "px"});
    const p = M.items[D.idx].p, doldur = p.mod === "doldur";
    const s = (doldur ? Math.max(W / D.iw, H / D.ih) : Math.min(W / D.iw, H / D.ih)) * (+p.zoom || 1);
    Object.assign(fg.style, {width: D.iw + "px", height: D.ih + "px", left: "0px", top: "0px", transformOrigin: "50% 50%",
      transform: `translate(${W / 2 - D.iw / 2 + p.dx * W}px, ${H / 2 - D.ih / 2 + p.dy * H}px) rotate(${p.rot}deg) scale(${s})`});
    // renk: pozlama/parlaklık/sıcaklık (SVG), kontrast/doygunluk (CSS)
    const ev = Math.pow(2, +p.poz || 0), t = (+p.sicaklik || 0) / 100, ic = (+p.parlaklik || 0) * 1.2 / 255;
    $("#dzR", kok).setAttribute("slope", ev * (1 + 0.08 * t)); $("#dzG", kok).setAttribute("slope", ev); $("#dzB", kok).setAttribute("slope", ev * (1 - 0.08 * t));
    ["dzR", "dzG", "dzB"].forEach(i => $("#" + i, kok).setAttribute("intercept", ic));
    const filtre = `url(#dzF) contrast(${1 + (+p.kontrast || 0) / 100 * 0.6}) saturate(${1 + (+p.doygunluk || 0) / 100})`;
    fg.style.filter = filtre; bg.style.filter = `${filtre} blur(18px) brightness(.92)`;
    $("#dzDurum", kok).textContent = `Yakınlaştırma ×${(+p.zoom).toFixed(2)} · Eğim ${(+p.rot).toFixed(1)}°`;
  };
  const sag = $("#dzSag", kok);
  const yaz = () => { $("#dzAd", kok).textContent = M.items[D.idx].ad; $("#dzSay", kok).textContent = `${D.idx + 1} / ${M.items.length}`; yerlestir(); };
  const panel = () => {
    const it2 = M.items[D.idx], p = it2.p; sag.innerHTML = "";
    const set = (k) => (v) => { p[k] = v; yerlestir(); };
    const kay = (ad, et, d, mn, mx, ad2, br, k) => kaydirici(ad, et, d, mn, mx, ad2, br, set(k), "", set(k));   // anlik: sürüklerken canlı
    const modSel = h(`<div class="alan"><label>Yerleşim</label><select><option value="sigdir" ${p.mod === "sigdir" ? "selected" : ""}>Kırpmadan sığdır (bulanık dolgu)</option><option value="doldur" ${p.mod === "doldur" ? "selected" : ""}>Alanı doldur (kırp)</option></select></div>`);
    $("select", modSel).onchange = (e) => { p.mod = e.target.value; yerlestir(); };
    sag.append(h(`<div class="bolum"><h3>KONUM</h3></div>`));
    const b1 = $(".bolum", sag); b1.append(modSel);
    b1.append(kaydirici("dz1", "Yakınlaştırma", p.zoom, 0.5, 3, 0.01, "×", set("zoom"), "", set("zoom")));
    b1.append(kaydirici("dz2", "Yatay kaydır", p.dx, -0.5, 0.5, 0.005, "", set("dx"), "", set("dx")));
    b1.append(kaydirici("dz3", "Dikey kaydır", p.dy, -0.5, 0.5, 0.005, "", set("dy"), "", set("dy")));
    b1.append(kaydirici("dz4", "Eğim", p.rot, -15, 15, 0.1, "°", set("rot"), "", set("rot")));
    const b2 = h(`<div class="bolum"><h3>RENK</h3></div>`);
    b2.append(kaydirici("dz5", "Pozlama (EV)", p.poz, -1.5, 1.5, 0.05, "", set("poz"), "", set("poz")));
    b2.append(kaydirici("dz6", "Parlaklık", p.parlaklik, -60, 60, 1, "", set("parlaklik"), "", set("parlaklik")));
    b2.append(kaydirici("dz7", "Kontrast", p.kontrast, -100, 100, 1, "", set("kontrast"), "", set("kontrast")));
    b2.append(kaydirici("dz8", "Doygunluk", p.doygunluk, -100, 100, 1, "", set("doygunluk"), "", set("doygunluk")));
    b2.append(kaydirici("dz9", "Sıcaklık", p.sicaklik, -100, 100, 1, "", set("sicaklik"), "", set("sicaklik")));
    sag.append(b2);
    const sf = h(`<div class="bolum"><div class="satir"><button class="btn genis" id="dzSifir" title="Bu fotoğrafın tüm ayarlarını başa döndürür">↺ Ayarları sıfırla</button></div><div class="not" style="margin-top:8px">Önizleme yaklaşıktır; baskı çıktısı program tarafından tam hesaplanır.</div></div>`);
    $("#dzSifir", sf).onclick = () => { it2.p = {...VARS}; panel(); yerlestir(); };
    sag.append(sf);
  };
  const git = (yeni) => { if (yeni < 0 || yeni >= M.items.length) return; onizleYenile(M.items[D.idx], 0); duzenKapat(true); duzenAc(yeni); };
  const duzenKapat = (sessiz) => { document.removeEventListener("keydown", tus); window.removeEventListener("resize", yerlestir); kok.remove(); DZ.d = null; if (!sessiz) { onizleYenile(M.items[D.idx], 0); modulCiz(); } };
  $("#dzTamam", kok).onclick = () => duzenKapat(false);
  $("#dzOnce", kok).onclick = () => git(D.idx - 1); $("#dzSonra", kok).onclick = () => git(D.idx + 1);

  // fare: kaydır (pointer capture) + tekerlek yakınlaştır
  let tut = null;
  alan.addEventListener("pointerdown", (e) => { if (e.button !== 0) return; const c = cer.getBoundingClientRect(), p = M.items[D.idx].p; tut = {x: e.clientX, y: e.clientY, dx: p.dx, dy: p.dy, w: c.width, h: c.height}; alan.setPointerCapture(e.pointerId); alan.style.cursor = "grabbing"; });
  alan.addEventListener("pointermove", (e) => {
    if (!tut) return; if (e.buttons === 0) { tut = null; alan.style.cursor = ""; return; }
    const p = M.items[D.idx].p; p.dx = +Math.max(-0.5, Math.min(0.5, tut.dx + (e.clientX - tut.x) / tut.w)).toFixed(4); p.dy = +Math.max(-0.5, Math.min(0.5, tut.dy + (e.clientY - tut.y) / tut.h)).toFixed(4); yerlestir();
  });
  const birak = () => { if (tut) { tut = null; alan.style.cursor = ""; panel(); } };
  alan.addEventListener("pointerup", birak); alan.addEventListener("pointercancel", birak); alan.addEventListener("lostpointercapture", birak);
  alan.addEventListener("wheel", (e) => { e.preventDefault(); const p = M.items[D.idx].p; p.zoom = +Math.max(0.5, Math.min(3, p.zoom * (e.deltaY < 0 ? 1.05 : 1 / 1.05))).toFixed(3); yerlestir(); clearTimeout(D._pt); D._pt = setTimeout(panel, 150); }, {passive: false});
  const tus = (e) => {
    if (e.target.tagName === "INPUT" && e.target.type === "text") return;
    const p = M.items[D.idx].p, adim = e.shiftKey ? 0.02 : 0.004;
    if (e.key === "Escape") { e.preventDefault(); duzenKapat(false); return; }
    if (e.key === "[") p.rot = +Math.max(-15, p.rot - 0.5).toFixed(1); else if (e.key === "]") p.rot = +Math.min(15, p.rot + 0.5).toFixed(1);
    else if (e.key === "ArrowLeft") p.dx = +(p.dx - adim).toFixed(4); else if (e.key === "ArrowRight") p.dx = +(p.dx + adim).toFixed(4);
    else if (e.key === "ArrowUp") p.dy = +(p.dy - adim).toFixed(4); else if (e.key === "ArrowDown") p.dy = +(p.dy + adim).toFixed(4); else return;
    e.preventDefault(); yerlestir(); panel();
  };
  document.addEventListener("keydown", tus); window.addEventListener("resize", yerlestir);
  panel(); yaz();
}
