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
  const ust = h(`<div class="modul-ust"><b>${sirket}</b><span class="not" style="margin-left:12px">${M.tur === "polaroid" ? "Fotoğraflar kırpılmadan sığdırılır, boşluklar bulanık dolgu olur. Tek kalan foto için Hayal Medya çerçevesi eklenir." : "Her fotoğraf seçilen kağıt boyutunda ayrı baskı olur. Çift tıkla: gelişmiş düzenleme."}</span><span style="flex:1"></span><button class="btn kucuk" id="mEkle">+ Fotoğraf ekle</button><button class="btn kucuk" id="mKlasor">+ Klasör ekle</button><button class="ikon" id="mKapat" aria-label="Kapat">✕</button></div>`);
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
    kart.ondblclick = () => { M.sec = idx; M.gelismis = true; modulCiz(); };
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
    b.append(h(`<div class="modul-buyuk" id="mBuyuk"><img src="${secili.th || ""}" alt=""></div>`));
    const modSel = h(`<div class="alan"><label>Yerleşim</label><select><option value="sigdir" ${secili.p.mod === "sigdir" ? "selected" : ""}>Kırpmadan sığdır (bulanık dolgu)</option><option value="doldur" ${secili.p.mod === "doldur" ? "selected" : ""}>Alanı doldur (kırp)</option></select></div>`);
    $("select", modSel).onchange = (e) => { secili.p.mod = e.target.value; onizleYenile(secili, 0); };
    b.append(modSel);
    b.append(kaydirici("mz", "Yakınlaştırma", secili.p.zoom, 0.5, 3, 0.01, "×", set("zoom")));
    if (M.gelismis) {
      b.append(kaydirici("mx", "Yatay kaydır", secili.p.dx, -0.5, 0.5, 0.005, "", set("dx")));
      b.append(kaydirici("my", "Dikey kaydır", secili.p.dy, -0.5, 0.5, 0.005, "", set("dy")));
      b.append(kaydirici("mr", "Eğim", secili.p.rot, -15, 15, 0.1, "°", set("rot")));
      b.append(kaydirici("mp", "Pozlama (EV)", secili.p.poz, -1.5, 1.5, 0.05, "", set("poz")));
      b.append(kaydirici("mb", "Parlaklık", secili.p.parlaklik, -60, 60, 1, "", set("parlaklik")));
      b.append(kaydirici("mk", "Kontrast", secili.p.kontrast, -100, 100, 1, "", set("kontrast")));
      b.append(kaydirici("md", "Doygunluk", secili.p.doygunluk, -100, 100, 1, "", set("doygunluk")));
      b.append(kaydirici("ms", "Sıcaklık", secili.p.sicaklik, -100, 100, 1, "", set("sicaklik")));
      const sf = h(`<div class="satir"><button class="btn kucuk genis">Ayarları sıfırla</button></div>`);
      $("button", sf).onclick = () => { secili.p = {...VARS}; onizleYenile(secili, 0); modulCiz(); };
      b.append(sf);
    } else b.append(h(`<div class="not">Daha fazla ayar için fotoğrafa çift tıklayın.</div>`));
    sag.append(b);
  }
  // kayıt / yazdırma
  const kb = h(`<div class="bolum"><h3>KAYIT VE BASKI</h3>
    <div class="alan"><label>Kayıt klasörü ${M.tur === "serbest" ? "(boşsa: foto klasörü içinde “Baskıya Hazır”)" : ""}</label><div class="satir"><input type="text" id="mKl" value="${esc(M.klasor)}"><button class="btn kucuk" id="mSec">Seç</button></div></div>
    ${M.tur === "polaroid" ? `<div class="satir"><div class="alan"><label>Arşiv no</label><input type="text" id="mNo"></div><div class="alan"><label>Müşteri</label><input type="text" id="mAd"></div></div>` : ""}
    <div class="alan"><label>Yazıcı</label><select id="mYz">${M.yazicilar.map(x => `<option ${x === M.yazici ? "selected" : ""}>${esc(x)}</option>`).join("")}</select></div>
    ${M.tur === "polaroid" ? `<div class="alan"><label>Sayfa kopyası</label><input type="number" min="1" max="20" value="1" id="mKop"></div>` : ""}
    <div class="satir"><button class="btn genis" id="mKaydet">Sadece kaydet</button><button class="btn ana genis" id="mYazdir">Kaydet ve yazdır</button></div></div>`);
  $("#mSec", kb).onclick = async () => { const k = await api.pick_folder(M.klasor); if (k) { M.klasor = k; $("#mKl", kb).value = k; } };
  $("#mKl", kb).oninput = (e) => M.klasor = e.target.value;
  $("#mYz", kb).onchange = (e) => M.yazici = e.target.value;
  const git = async (yazdir) => {
    if (!M.items.length) { bildir("Önce fotoğraf ekleyin.", true); return; }
    if (M.tur === "polaroid" && !M.klasor) { bildir("Önce kayıt klasörünü seçin.", true); return; }
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
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && document.querySelector("#modul") && $("#modal").classList.contains("gizli")) modulKapat(); });
