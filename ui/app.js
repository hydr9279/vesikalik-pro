/* Hayal Medya Vesikalık Pro — arayüz */
"use strict";

// ------------------------------------------------------------------ köprü
const api = new Proxy({}, {
  get: (_, name) => (...args) => {
    if (window.pywebview && window.pywebview.api) return window.pywebview.api[name](...args);
    return fetch("/api/" + name, {method: "POST", body: JSON.stringify(args)}).then(r => r.json());
  }
});
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const h = (html) => { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstElementChild; };
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
window.onerror = (m, s, l) => { try { api.log_js_error(`${m} @${l}`); } catch (e) {} };

const ADIMLAR = ["Başlangıç", "Arka Plan", "Rötuş", "Ölçekleme", "Baskı ve Kayıt"];
const S = {
  init: null, fmt: {}, fid: "bio56", adim: 0, isler: [], cur: null, st: null, gorunum: "sonuc", arac: "sam+",
  firca: 40, bilgi: {musteri: "", no: "", adet: 4}, ayar: {}, karsilastir: 50, lekeArac: false, sayfa: null, rArac: "k", sGuc: 60, rVal: 70, kHard: 40, kVal: 100, kSrc: null, rGor: "sonuc", seciliLeke: -1,
};

// ------------------------------------------------------------------ meşgul / ilerleme
let mesgul = 0, pollT = null;
async function cagir(name, ...args) {
  mesgul++;
  const showT = setTimeout(() => { if (mesgul) { $("#ilerleme").classList.remove("gizli"); } }, 350);
  if (!pollT) pollT = setInterval(async () => {
    const p = await api.progress();
    $("#ilMesaj").textContent = p.mesaj || "Çalışıyor…";
    $("#ilCubuk").style.width = Math.round((p.yuzde || 0.03) * 100) + "%";
    $("#ilYuzde").textContent = "%" + Math.round((p.yuzde || 0) * 100);
    $("#ilKalan").textContent = p.kalan ? `yaklaşık ${Math.ceil(p.kalan)} sn kaldı` : "";
  }, 300);
  try {
    const r = await api[name](...args);
    if (r && r.ok === false) { bildir(r.hata || "Bir hata oluştu", true); }
    return r;
  } catch (e) { bildir("Hata: " + e, true); return {ok: false}; }
  finally {
    clearTimeout(showT);
    mesgul--;
    if (!mesgul) { $("#ilerleme").classList.add("gizli"); clearInterval(pollT); pollT = null; }
  }
}
function bildir(msg, hata = false, eylem = null) {
  const b = $("#bildirim");
  b.className = "bildirim" + (hata ? " hata" : "");
  b.innerHTML = `<span>${esc(msg)}</span>`;
  if (eylem) { const k = h(`<button class="btn kucuk">${esc(eylem.ad)}</button>`); k.onclick = eylem.fn; b.append(k); }
  clearTimeout(b._t); b._t = setTimeout(() => b.classList.add("gizli"), hata ? 7000 : 5000);
}

// ------------------------------------------------------------------ başlat
let basladi = false;
async function baslat() {
  if (basladi) return; basladi = true;
  S.init = await api.init();
  try { const ml = await api.model_listesi(); S.modeller = ml.modeller || []; } catch (e) { S.modeller = []; }
  S.init.formatlar.forEach(f => S.fmt[f.id] = f);
  S.ayar = S.init.ayarlar;
  $("#surum").textContent = S.init.surum;
  temaUygula(S.ayar.tema || "koyu");
  S.fid = "bio56";
  ciz();
  kameraDurum();
  setInterval(kameraYokla, 3000);
}
window.addEventListener("pywebviewready", baslat);
// Geliştirme sunucusu (tarayıcı) için: pywebview yoksa doğrudan başla
window.addEventListener("load", () => setTimeout(() => { if (!window.pywebview && !basladi) baslat(); }, 1500));

function temaUygula(t) {
  document.documentElement.dataset.tema = t;
  $$(".simge").forEach(i => i.src = "assets/app_icon.png");
}

// ------------------------------------------------------------------ çizim
function ciz() { adimlarCiz(); siraCiz(); sahneCiz(); panelCiz(); altCiz(); }

function adimlarCiz() {
  const n = $("#adimlar"); n.innerHTML = "";
  ADIMLAR.forEach((a, i) => {
    const ok = S.st && i < S.adim;
    const b = h(`<button class="adim ${i === S.adim ? "aktif" : ""} ${ok ? "bitti" : ""}"><span class="no">${ok ? "✓" : i + 1}</span>${a}</button>`);
    b.disabled = !gidilebilir(i);
    b.onclick = () => adimaGit(i);
    n.append(b);
    if (i < ADIMLAR.length - 1) n.append(h(`<span class="adim-cizgi" style="${ok ? "background:var(--iyi)" : ""}"></span>`));
  });
}
function gidilebilir(i) {
  if (i === 0) return true;
  if (!S.cur || !S.st) return false;
  const j = isBul(S.cur);
  if (i === 1) return !!j.analizli;
  return !!j.maskeli;
}
function isBul(id) { return S.isler.find(x => x.id === id); }

function siraCiz() {
  const l = $("#siraListe"); l.innerHTML = "";
  $("#siraSay").textContent = S.isler.length;
  S.isler.forEach(j => {
    const durum = j.durum || "";
    const e = h(`<div class="sira-oge ${j.id === S.cur ? "secili" : ""}" title="${esc(j.ad)}"><img src="${j.kucuk}" alt=""><div><div class="ad">${esc(j.ad)}</div><div class="alt-y">${esc(j.not || "Bekliyor")}</div></div><span class="nokta ${durum}"></span><button class="sil" title="Sıradan çıkar">✕</button></div>`);
    e.onclick = (ev) => { if (ev.target.classList.contains("sil")) return; isSec(j.id); };
    $(".sil", e).onclick = async () => { await api.remove_job(j.id); S.isler = S.isler.filter(x => x !== j); if (S.cur === j.id) { S.cur = null; S.st = null; S.adim = 0; } ciz(); };
    l.append(e);
  });
}

function altCiz() {
  const geri = $("#btnGeri"), ileri = $("#btnIleri");
  geri.textContent = S.adim === 0 ? "Fotoğraf ekle" : "Geri";
  geri.onclick = S.adim === 0 ? dosyaEkle : () => adimaGit(S.adim - 1);
  const son = S.adim === 4;
  ileri.textContent = son ? "Sıradaki fotoğraf" : `İleri: ${ADIMLAR[S.adim + 1]}`;
  ileri.disabled = son ? !S.isler.some(x => x.id !== S.cur && !x.kaydedildi) : !S.cur;
  ileri.onclick = son ? siradaki : () => adimaGit(S.adim + 1);
  $("#donanim").textContent = "Donanım: " + (S.st?.donanim || "—");
  const j = S.cur && isBul(S.cur);
  $("#dosyaBilgi").textContent = j ? `${j.ad} · ${S.fmt[S.fid].ad}` : "";
}

// ------------------------------------------------------------------ dosyalar
async function dosyaEkle() {
  const yollar = await api.pick_files();
  if (yollar && yollar.length) await yollaEkle(yollar);
}
async function yollaEkle(yollar) {
  const r = await cagir("add_files", yollar);
  ekle(r);
}
function ekle(r) {
  if (!Array.isArray(r)) return;
  r.forEach(x => { if (x.hata) bildir(x.hata, true); else S.isler.push({...x, durum: "", not: "Bekliyor"}); });
  if (!S.cur && S.isler.length) isSec(S.isler[0].id); else ciz();
}
async function isSec(id) {
  S.cur = id; S.adim = 0; S.st = null; S.sayfa = null;
  ciz();
  await analiz();
}
async function analiz() {
  const j = isBul(S.cur);
  const r = await cagir("analyze", S.cur, S.fid);
  if (!r.ok) { j.durum = "kotu"; j.not = "Yüz bulunamadı"; ciz(); return; }
  S.st = r; j.analizli = true; j.orijinal = r.orijinal;
  if (!S.bilgi.no || S.bilgi._oto) { S.bilgi.no = String(r.arsiv_no); S.bilgi._oto = true; }
  durumGuncelle();
  ciz();
  if (S.ayar.hizli_mod && !r.uygunluk.some(c => c.durum === "bad")) await hizliMod();
}
function durumGuncelle() {
  const j = isBul(S.cur); if (!j || !S.st?.uygunluk) return;
  const bad = S.st.uygunluk.filter(c => c.durum === "bad").length, warn = S.st.uygunluk.filter(c => c.durum === "warn").length;
  j.durum = bad ? "kotu" : warn ? "uyari" : "iyi";
  j.not = bad ? `${bad} sorun` : warn ? `${warn} uyarı` : "Uygun";
}
async function hizliMod() {
  bildir("Hızlı mod: tüm adımlar otomatik uygulanıyor");
  if (!(await maskeHazirla())) return;
  await rotusUygula();
  S.adim = 4; ciz(); sayfaHazirla();
}

// ------------------------------------------------------------------ adım geçişleri
async function adimaGit(i) {
  if (i > 0 && !S.cur) return;
  if (i >= 1 && !isBul(S.cur).maskeli) { if (!(await maskeHazirla())) return; }
  if (i >= 2 && !isBul(S.cur).rotuslu) await rotusUygula();
  S.adim = i;
  if (i === 1 || i === 3) await gorunumYenile("sonuc");
  if (i === 4) { ciz(); return sayfaHazirla(); }
  ciz();
}
async function maskeHazirla(force = false) {
  const j = isBul(S.cur);
  const r = await cagir("matte", S.cur, S.fid, {model: S.ayar.model || "auto"}, force);
  if (!r.ok) return false;
  S.st = r; j.maskeli = true; durumGuncelle();
  return true;
}
async function rotusUygula(p = {}) {
  const j = isBul(S.cur);
  const r = await cagir("retouch", S.cur, S.fid, {...(S.st?.rotus || {}), ...p});
  if (r.ok) { S.st = r; j.rotuslu = true; durumGuncelle(); }
  return r;
}
async function gorunumYenile(mode) {
  S.gorunum = mode;
  if (mode === "sonuc") return;
  const r = await cagir("view", S.cur, S.fid, mode);
  if (r.ok) S.st.gorsel_alt = r.gorsel;
}
function siradaki() {
  const n = S.isler.find(x => x.id !== S.cur && !x.kaydedildi);
  if (n) { S.bilgi = {musteri: "", no: "", adet: S.bilgi.adet, _oto: true}; isSec(n.id); }
}

// ------------------------------------------------------------------ sahne
function sahneCiz() {
  const sh = $("#sahne"); sh.innerHTML = "";
  if (S.adim === 0) return girisCiz(sh);
  if (S.adim === 1) return tuvalCiz(sh, "arkaplan");
  if (S.adim === 2) return tuvalCiz(sh, "rotus");
  if (S.adim === 3) return tuvalCiz(sh, "olcek");
  if (S.adim === 4) return baskiCiz(sh);
}

function girisCiz(sh) {
  const g = h(`<div class="giris"></div>`);
  if (S.cur && S.st) {
    const j = isBul(S.cur);
    g.append(h(`<div class="satir" style="gap:24px;align-items:flex-start;height:100%">
      <img src="${S.st.orijinal}" style="max-height:100%;max-width:60%;border-radius:8px;box-shadow:0 10px 40px rgba(0,0,0,.4)">
      <div style="display:flex;flex-direction:column;gap:12px;min-width:260px">
        <h1 style="font-size:20px">${esc(j.ad)}</h1>
        <div class="not">Tür: <b>${esc(S.fmt[S.fid].ad)}</b> · Değiştirmek için aşağıdan seçin.</div>
        <div class="ciplar" id="turCip"></div>
        <div class="not">Sağdaki bilgileri doldurup <b>İleri</b> ile arka plan adımına geçin. Program arka planı en kaliteli modelle ayıracak.</div>
      </div></div>`));
    sh.append(g);
    const c = $("#turCip", g);
    S.init.formatlar.forEach(f => { const b = h(`<button class="cip ${f.id === S.fid ? "secili" : ""}">${esc(f.ad)}</button>`); b.onclick = () => turSec(f.id); c.append(b); });
    return;
  }
  g.append(h(`<div><h1>Yeni çekim</h1><div class="not" style="margin-top:6px;font-size:14px">Fotoğraf türünü seçin ve fotoğrafı bırakın. Kurallar ve ayarlar türe göre otomatik gelir.</div></div>`));
  const k = h(`<div class="kartlar"></div>`);
  const kart = (id, k1, k2, k3) => { const e = h(`<button class="kart ${S.fid === id ? "secili" : ""}"><span class="k1">${k1}</span><span class="k2">${k2}</span><span class="k3">${k3}</span></button>`); e.onclick = () => turSec(id); return e; };
  k.append(kart("bio56", "BİYOMETRİK", "5 × 6 cm", "Pasaport · Kimlik · Ehliyet"));
  k.append(kart("bio55", "BİYOMETRİK", "5 × 5 cm", "Kare biyometrik"));
  k.append(kart("ves45", "VESİKALIK", "4,5 × 6 cm", "Orijinal fon veya 12 degrade"));
  g.append(k);
  const vz = h(`<div><div class="not" style="font-weight:600;letter-spacing:.08em;margin-bottom:8px">VİZE ÖLÇÜLERİ</div><div class="ciplar"></div></div>`);
  S.init.formatlar.filter(f => f.grup === "vize").forEach(f => { const b = h(`<button class="cip ${S.fid === f.id ? "secili" : ""}">${esc(f.ad)}</button>`); b.onclick = () => turSec(f.id); $(".ciplar", vz).append(b); });
  g.append(vz);
  const mod = h(`<div class="kartlar"><button class="kart" id="kPol"><span class="k1">POLAROID</span><span class="k2" style="font-size:18px">Instax Square</span><span class="k3">10x15'e 2 kart · kırpmasız</span></button><button class="kart" id="kSer"><span class="k1">SERBEST BASKI</span><span class="k2" style="font-size:18px">10x15 · 13x18 · 15x21</span><span class="k3">Adet ve pozlama ayarlı</span></button></div>`);
  $("#kPol", mod).onclick = () => modulAc("polaroid");
  $("#kSer", mod).onclick = () => modulAc("serbest");
  g.append(mod);
  const b = h(`<div class="birak"><span class="daire"><svg viewBox="0 0 24 24"><path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3"/></svg></span><b style="color:var(--yazi);font-size:15px">Fotoğrafları buraya bırakın</b><span>JPG, PNG, HEIC, WebP, TIFF, RAW · Klasör de bırakabilirsiniz</span><div class="satir"><button class="btn kucuk" id="bDosya">Dosya seç</button><button class="btn kucuk" id="bKlasor">Klasör seç</button></div></div>`);
  $("#bDosya", b).onclick = dosyaEkle;
  $("#bKlasor", b).onclick = async () => { const k = await api.pick_folder(); if (k) yollaEkle([k]); };
  g.append(b);
  sh.append(g);
}
async function turSec(id) {
  S.fid = id;
  const f = S.fmt[id];
  if (!f.adetler.includes(S.bilgi.adet)) S.bilgi.adet = f.adetler[0];
  if (S.cur && S.st) {
    const r = await cagir("set_bg", S.cur, S.fid, {tip: "auto"});
    if (r.ok) Object.assign(S.st, r, {orijinal: S.st.orijinal});
    durumGuncelle();
  }
  ciz();
}

// ------------------------------------------------------------------ tuval (arka plan, rötuş, ölçek)
let V = {zoom: 1, panX: 0, panY: 0};
function tuvalCiz(sh, tur) {
  const f = S.fmt[S.fid];
  const asp = f.gen_mm / f.yuk_mm;
  const alan = h(`<div class="tuval-alan"></div>`);
  const ic = h(`<div class="tuval-ic ${tur === "arkaplan" ? "dama" : ""}"></div>`);
  const ana = h(`<img alt="Önizleme">`);
  let src = S.st.gorsel;
  if (tur === "arkaplan" && S.gorunum !== "sonuc" && S.st.gorsel_alt) src = S.st.gorsel_alt;
  ana.src = src;
  ic.append(ana);
  const kat = h(`<div class="ust-katman"></div>`);
  ic.append(kat);
  alan.append(ic);
  sh.append(alan);
  const yerlestir = () => {
    const r = alan.getBoundingClientRect();
    let H0 = r.height - 130, W0 = H0 * asp;
    if (W0 > r.width - 160) { W0 = r.width - 160; H0 = W0 / asp; }
    const H = H0 * V.zoom, W = W0 * V.zoom;
    ic.style.width = W + "px"; ic.style.height = H + "px";
    ic.style.transform = `translate(${-W / 2 + V.panX}px, ${-H / 2 + V.panY + 6}px)`;
    const z = $(".yakinlik span", sh); if (z) z.textContent = Math.round(V.zoom * 100) + "%";
  };
  requestAnimationFrame(yerlestir);
  window.onresize = yerlestir;
  // yakınlaştırma
  const yk = h(`<div class="yakinlik"><button class="ikon kucuk" aria-label="Uzaklaştır">−</button><span>100%</span><button class="ikon kucuk" aria-label="Yakınlaştır">+</button><button class="ikon kucuk" title="Sığdır" aria-label="Sığdır">⤢</button></div>`);
  const [bz1, bz2, bz3] = $$("button", yk);
  bz1.onclick = () => { V.zoom = Math.max(0.4, V.zoom / 1.2); yerlestir(); };
  bz2.onclick = () => { V.zoom = Math.min(6, V.zoom * 1.2); yerlestir(); };
  bz3.onclick = () => { V = {zoom: 1, panX: 0, panY: 0}; yerlestir(); };
  sh.append(yk);
  alan.addEventListener("wheel", (e) => {
    e.preventDefault();
    if (tur === "olcek" && !e.ctrlKey) { geomDegis({zoom: +(S.st.geom.zoom * (e.deltaY < 0 ? 1.01 : 0.99)).toFixed(4)}); return; }
    V.zoom = Math.min(6, Math.max(0.4, V.zoom * (e.deltaY < 0 ? 1.1 : 0.9))); yerlestir();
  }, {passive: false});
  // kaydırma (orta tuş / boşluk + sürükle / Kaydır aracı)
  let pan = null;
  alan.addEventListener("mousedown", (e) => {
    if (e.button === 1 || bosluk || S.arac === "kaydir") { pan = {x: e.clientX, y: e.clientY, px: V.panX, py: V.panY}; e.preventDefault(); }
  });
  window.onmousemove = (e) => { if (pan) { V.panX = pan.px + e.clientX - pan.x; V.panY = pan.py + e.clientY - pan.y; yerlestir(); } };
  window.onmouseup = () => { pan = null; };
  const norm = (e) => { const r = ic.getBoundingClientRect(); return [(e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height]; };

  if (tur === "arkaplan") arkaplanTuval(sh, alan, ic, kat, norm);
  if (tur === "rotus") rotusTuval(sh, alan, ic, kat, norm, ana);
  if (tur === "olcek") olcekTuval(sh, alan, ic, kat, norm);
}
let bosluk = false;

function arkaplanTuval(sh, alan, ic, kat, norm) {
  const ar = h(`<div class="araclar">
    <button class="arac" data-a="sam+" title="Akıllı seçim: kişiye ekle (A)">＋ Kişiye ekle</button>
    <button class="arac" data-a="sam-" title="Akıllı seçim: fondan say (S)">− Fon say</button>
    <button class="arac" data-a="firca+" title="Fırça: ekle (B)">Fırça ekle</button>
    <button class="arac" data-a="firca-" title="Fırça: sil (E)">Fırça sil</button>
    <button class="arac" data-a="kaydir" title="Kaydır (H / boşluk)">Kaydır</button>
    <span class="arac-ayrac"></span>
    <div class="seg" id="gor"><button data-g="sonuc">Sonuç</button><button data-g="maske">Maske</button><button data-g="once">Önce</button></div></div>`);
  $$(".arac", ar).forEach(b => { b.classList.toggle("secili", b.dataset.a === S.arac); b.onclick = () => { S.arac = b.dataset.a; sahneCiz(); }; });
  $$("#gor button", ar).forEach(b => { b.classList.toggle("secili", b.dataset.g === S.gorunum); b.onclick = async () => { await gorunumYenile(b.dataset.g); sahneCiz(); }; });
  sh.append(ar);
  sh.append(h(`<div class="efsane"><span>Sol tık: seçili araç · Fare tekerleği: yakınlaştır · Boşluk+sürükle: kaydır</span></div>`));
  (S.st.supheli || []).filter(b => b.w < 0.7 && b.h < 0.6).forEach(b => kat.append(h(`<div class="supheli" style="left:${b.x * 100}%;top:${b.y * 100}%;width:${b.w * 100}%;height:${b.h * 100}%"><span>${esc(b.ad)} · kontrol edin</span></div>`)));
  // fırça imleci
  const im = h(`<div class="firca-imlec"></div>`); alan.append(im);
  const svgNS = "http://www.w3.org/2000/svg";
  let cizim = null;
  alan.addEventListener("mousemove", (e) => {
    if (S.arac.startsWith("firca")) {
      const r = alan.getBoundingClientRect(); const d = S.firca;
      Object.assign(im.style, {display: "block", width: d + "px", height: d + "px", left: (e.clientX - r.left - d / 2) + "px", top: (e.clientY - r.top - d / 2) + "px"});
    } else im.style.display = "none";
    if (cizim) { cizim.pts.push(norm(e)); const [x, y] = cizim.pts.at(-1); cizim.path.setAttribute("d", cizim.path.getAttribute("d") + ` L${x * 1000} ${y * 1000}`); }
  });
  alan.addEventListener("mousedown", async (e) => {
    if (e.button !== 0 || bosluk || S.arac === "kaydir") return;
    if (S.arac.startsWith("sam")) {
      const [x, y] = norm(e); if (x < 0 || y < 0 || x > 1 || y > 1) return;
      const pos = S.arac === "sam+";
      kat.append(h(`<div class="isaret" style="left:${x * 100}%;top:${y * 100}%;background:${pos ? "var(--iyi)" : "var(--kotu)"}">${pos ? "+" : "−"}</div>`));
      const r = await cagir("edit", S.cur, S.fid, {t: "sam", x, y, pos});
      if (r.ok) { S.st = r; S.gorunum === "sonuc" || await gorunumYenile(S.gorunum); sahneCiz(); panelCiz(); }
    } else if (S.arac.startsWith("firca")) {
      const svg = document.createElementNS(svgNS, "svg"); svg.setAttribute("viewBox", "0 0 1000 1000"); svg.setAttribute("preserveAspectRatio", "none");
      Object.assign(svg.style, {position: "absolute", inset: 0, width: "100%", height: "100%", overflow: "visible"});
      const path = document.createElementNS(svgNS, "path"); const [x, y] = norm(e);
      path.setAttribute("d", `M${x * 1000} ${y * 1000}`);
      const rr = ic.getBoundingClientRect();
      path.setAttribute("stroke", S.arac === "firca+" ? "rgba(61,214,140,.6)" : "rgba(255,122,122,.6)");
      path.setAttribute("stroke-width", S.firca / rr.width * 1000); path.setAttribute("fill", "none"); path.setAttribute("stroke-linecap", "round"); path.setAttribute("stroke-linejoin", "round");
      path.setAttribute("vector-effect", "none");
      svg.append(path); kat.append(svg);
      cizim = {pts: [[x, y]], path, w: rr.width};
    }
  });
  alan.addEventListener("mouseup", async () => {
    if (!cizim) return;
    const c = cizim; cizim = null;
    const r = await cagir("edit", S.cur, S.fid, {t: "brush", pts: c.pts, r: S.firca / 2 / c.w, add: S.arac === "firca+", hard: 0.6});
    if (r.ok) { S.st = r; S.gorunum === "sonuc" || await gorunumYenile(S.gorunum); }
    sahneCiz(); panelCiz();
  });
}

function rotusTuval(sh, alan, ic, kat, norm, ana) {
  const svgNS = "http://www.w3.org/2000/svg";
  const A = S.rArac || "k";
  const T = (k, ad, ip) => `<button class="arac ${A === k ? "secili" : ""}" data-a="${k}" title="${ip}">${ad}</button>`;
  const fs = S.st.firca_sayisi || [0, 0];
  const ar = h(`<div class="araclar">${T("k", "Karşılaştır", "Önce / sonra sürgüsü: fotoğrafın önceki ve sonraki hâlini yan yana kaydırarak görün")}<span class="arac-ayrac"></span>${T("l", "Leke fırçası", "Tıklanan yeri leke olarak temizler (L)")}${T("g", "Geri al fırçası", "Rötuşu fırçayla yüzdelik olarak siler, orijinale döndürür (G)")}${T("p", "Koruma fırçası", "Fırçayla boyanan yer rötuştan korunur (P)")}<span class="arac-ayrac"></span>${T("n", "Klon damgası", "Alt + tıkla: kaynak seç, sonra boyayarak kopyala (S)")}${T("t", "Ten örneği", "Gelişmiş portre rötuşu için ten rengi örneği seç (T)")}<span class="arac-ayrac"></span>${T("m", "İt / çek", "Omuz ve giysi kenarını fırçayla it (M). Yüz kilitlidir")}${T("b", "Şişir", "Fırçanın altını büyüt (B). Yüz kilitlidir")}${T("z", "Küçült", "Fırçanın altını küçült (Z). Yüz kilitlidir")}<span class="arac-ayrac"></span><button class="arac ${S.lekeGoster ? "secili" : ""}" data-a="x" title="Bulunan lekeleri göster/gizle">Lekeleri göster</button><button class="arac ${S.rGor === "koruma" ? "secili" : ""}" data-a="v" title="Rötuşun dokunmadığı bölgeleri yeşil gösterir (K)">Koruma haritası</button><button class="arac" data-a="u" title="Son fırça darbesini geri al">↶ Fırça geri al</button><button class="arac" data-a="us" title="Son şekillendirme darbesini geri al">↶ Şekil geri al${S.st.sekil_sayisi ? " (" + S.st.sekil_sayisi + ")" : ""}</button><button class="arac" data-a="uk" title="Son klon darbesini geri al">↶ Klon geri al${S.st.klon_sayisi ? " (" + S.st.klon_sayisi + ")" : ""}</button></div>`);
  $$(".arac", ar).forEach(b => b.onclick = async () => {
    const a = b.dataset.a;
    if (a === "x") S.lekeGoster = !S.lekeGoster;
    else if (a === "v") { S.rGor = S.rGor === "koruma" ? "sonuc" : "koruma"; S.st.gorsel_koruma = null; }
    else if (a === "us") { const r = await cagir("sekil_geri_al", S.cur, S.fid); if (r.ok) { S.st = {...r, gorsel_once: S.st.gorsel_once}; } }
    else if (a === "uk") { const r = await cagir("klon_geri_al", S.cur, S.fid); if (r.ok) { S.st = {...r, gorsel_once: S.st.gorsel_once}; } }
    else if (a === "u") { const t = (S.rArac === "p") ? "koru" : "geri"; const r = await cagir("rotus_firca_geri_al", S.cur, S.fid, t); if (r.ok) { S.st = {...r, gorsel_once: S.st.gorsel_once}; } }
    else S.rArac = a;
    sahneCiz();
  });
  sh.append(ar);
  if (A === "g" || A === "p") {
    const ab = h(`<div class="araclar alt-y"><label>Fırça boyutu <input type="range" min="6" max="160" value="${S.firca}" id="rfb"> <b>${S.firca}</b></label>${A === "g" ? `<label>Geri alma gücü <input type="range" min="5" max="100" value="${S.rVal}" id="rfv"> <b>%${S.rVal}</b></label>` : ""}</div>`);
    $("#rfb", ab).oninput = (e) => { S.firca = +e.target.value; $("b", e.target.parentNode).textContent = S.firca; };
    if ($("#rfv", ab)) $("#rfv", ab).oninput = (e) => { S.rVal = +e.target.value; $("b", e.target.parentNode).textContent = "%" + S.rVal; };
    sh.append(ab);
  }
  if (A === "n") {
    const nb = h(`<div class="araclar alt-y"><label>Fırça boyutu <input type="range" min="6" max="200" value="${S.firca}" id="nfb"> <b>${S.firca}</b></label><label>Kenar yumuşaklığı <input type="range" min="0" max="100" value="${100 - S.kHard}" id="nfy"> <b>%${100 - S.kHard}</b></label><label>Opaklık <input type="range" min="5" max="100" value="${S.kVal}" id="nfo"> <b>%${S.kVal}</b></label><span class="not" style="margin:0">${S.kSrc ? "Kaynak seçili ✓" : "Önce <b>Alt + tıkla</b> ile kaynağı seçin"}</span></div>`);
    $("#nfb", nb).oninput = (e) => { S.firca = +e.target.value; $("b", e.target.parentNode).textContent = S.firca; };
    $("#nfy", nb).oninput = (e) => { S.kHard = 100 - +e.target.value; $("b", e.target.parentNode).textContent = "%" + e.target.value; };
    $("#nfo", nb).oninput = (e) => { S.kVal = +e.target.value; $("b", e.target.parentNode).textContent = "%" + S.kVal; };
    sh.append(nb);
  }
  if (A === "m" || A === "b" || A === "z") {
    const sb = h(`<div class="araclar alt-y"><label>Fırça boyutu <input type="range" min="20" max="260" value="${S.firca}" id="sfb"> <b>${S.firca}</b></label><label>Güç <input type="range" min="10" max="100" value="${S.sGuc}" id="sfg"> <b>%${S.sGuc}</b></label><span class="not" style="margin:0">${A === "m" ? "Omuz kenarından <b>içe/dışa sürükleyin</b>" : "Bölgenin üzerinde <b>tıklayıp basılı tutun</b> ya da gezdirin"}. Yüz kilitli.</span></div>`);
    $("#sfb", sb).oninput = (e) => { S.firca = +e.target.value; $("b", e.target.parentNode).textContent = S.firca; };
    $("#sfg", sb).oninput = (e) => { S.sGuc = +e.target.value; $("b", e.target.parentNode).textContent = "%" + S.sGuc; };
    sh.append(sb);
  }
  if (A === "t") sh.append(h(`<div class="araclar alt-y"><span class="not" style="margin:0">Yüzde <b>ten renginde</b> 1-4 noktaya tıklayın (yanak, alın). Gelişmiş yumuşatma yalnız bu renge benzeyen yerlere uygulanır.</span></div>`));
  (S.st.pro_ornekler || []).forEach(([x, y]) => kat.append(h(`<span class="ornek-isaret" style="left:${x * 100}%;top:${y * 100}%"></span>`)));
  if (S.rGor === "koruma") {
    if (!S.st.gorsel_koruma) cagir("view", S.cur, S.fid, "koruma").then(r => { if (r.ok) { S.st.gorsel_koruma = r.gorsel; sahneCiz(); } });
    else ana.src = S.st.gorsel_koruma;
  }
  if (!S.st.gorsel_once) cagir("view", S.cur, S.fid, "once").then(r => { if (r.ok) { S.st.gorsel_once = r.gorsel; sahneCiz(); } });
  if (S.st.gorsel_once && A === "k" && S.rGor !== "koruma") {
    const kap = h(`<div style="position:absolute;inset:0;overflow:hidden;width:${S.karsilastir}%"><img src="${S.st.gorsel_once}" style="width:${10000 / S.karsilastir}%;height:100%;max-width:none;box-shadow:none"></div>`);
    ic.insertBefore(kap, kat);
    const ay = h(`<div class="ayir" style="left:${S.karsilastir}%"></div>`);
    kat.append(ay, h(`<span class="etiket" style="left:10px">ÖNCE</span>`), h(`<span class="etiket" style="right:10px">SONRA</span>`));
    let sur = false;
    ay.onmousedown = (e) => { sur = true; e.stopPropagation(); };
    alan.addEventListener("mousemove", (e) => { if (!sur) return; const [x] = norm(e); S.karsilastir = Math.max(2, Math.min(98, x * 100)); kap.style.width = S.karsilastir + "%"; $("img", kap).style.width = (10000 / S.karsilastir) + "%"; ay.style.left = S.karsilastir + "%"; });
    window.addEventListener("mouseup", () => sur = false);
  }
  const guncelle = (r) => { S.st = {...r, gorsel_once: S.st.gorsel_once, gorsel_koruma: null}; sahneCiz(); panelCiz(); };
  const sil = async (i) => { S.seciliLeke = -1; const r = await cagir("leke_sil", S.cur, S.fid, i); if (r.ok) guncelle(r); };
  S.silLeke = () => { if (S.seciliLeke >= 0) sil(S.seciliLeke); };
  if (S.lekeGoster || A === "l") (S.st.lekeler || []).forEach(([x, y, t], i) => {
    const m = h(`<span class="leke-isaret ${t ? "elle" : ""} ${S.seciliLeke === i ? "sec" : ""}" style="left:${x * 100}%;top:${y * 100}%" title="Tıkla: seç · Delete / sağ tık: işareti sil"></span>`);
    m.onmousedown = (e) => { e.stopPropagation(); if (e.button === 2) return; if (A === "l") { sil(i); return; } S.seciliLeke = i; $$(".leke-isaret", kat).forEach(z => z.classList.remove("sec")); m.classList.add("sec"); };
    m.oncontextmenu = (e) => { e.preventDefault(); e.stopPropagation(); sil(i); };
    kat.append(m);
  });
  // leke ekleme (yalnızca Leke fırçası aracında, boş yere tıklayınca)
  if (A === "l") alan.addEventListener("mousedown", async (e) => {
    if (e.button !== 0 || bosluk) return;
    const [x, y] = norm(e);
    const r = await cagir("spot", S.cur, S.fid, x, y);
    if (r.ok) guncelle(r);
  });
  if (A === "t") alan.addEventListener("mousedown", async (e) => {
    if (e.button !== 0 || bosluk) return;
    const [x, y] = norm(e);
    const r = await cagir("pro_ornek", S.cur, S.fid, x, y);
    if (r.ok) guncelle(r);
  });
  // geri al / koruma / klon fırçaları
  if (A === "g" || A === "p" || A === "n" || A === "m" || A === "b" || A === "z") {
    let cizim = null;
    const im = h(`<div class="firca-imlec" style="display:none"></div>`); alan.append(im);
    alan.addEventListener("mousemove", (e) => {
      const r = alan.getBoundingClientRect(), d = S.firca;
      Object.assign(im.style, {display: "block", width: d + "px", height: d + "px", left: (e.clientX - r.left - d / 2) + "px", top: (e.clientY - r.top - d / 2) + "px"});
      if (cizim) { cizim.pts.push(norm(e)); const [x, y] = cizim.pts.at(-1); cizim.path.setAttribute("d", cizim.path.getAttribute("d") + ` L${x * 1000} ${y * 1000}`); }
    });
    alan.addEventListener("mousedown", (e) => {
      if (e.button !== 0 || bosluk) return;
      if (A === "n" && e.altKey) { S.kSrc = norm(e); S.kOfs = null; bildir("Klon kaynağı seçildi"); panelCiz(); sahneCiz(); return; }
      if (A === "n" && !S.kSrc) { bildir("Önce Alt + tıklayarak kaynağı seçin"); return; }
      const svg = document.createElementNS(svgNS, "svg"); svg.setAttribute("viewBox", "0 0 1000 1000"); svg.setAttribute("preserveAspectRatio", "none");
      Object.assign(svg.style, {position: "absolute", inset: 0, width: "100%", height: "100%", overflow: "visible", pointerEvents: "none"});
      const path = document.createElementNS(svgNS, "path"); const [x, y] = norm(e);
      path.setAttribute("d", `M${x * 1000} ${y * 1000}`);
      const rr = ic.getBoundingClientRect();
      path.setAttribute("stroke", A === "g" ? "rgba(255,190,80,.55)" : (A === "m" || A === "b" || A === "z") ? "rgba(255,120,200,.45)" : A === "n" ? "rgba(120,170,255,.5)" : "rgba(61,214,140,.55)");
      path.setAttribute("stroke-width", S.firca / rr.width * 1000); path.setAttribute("fill", "none"); path.setAttribute("stroke-linecap", "round"); path.setAttribute("stroke-linejoin", "round");
      svg.append(path); kat.append(svg);
      cizim = {pts: [[x, y]], path, w: rr.width};
    });
    alan.addEventListener("mouseup", async () => {
      if (!cizim) return;
      const c = cizim; cizim = null;
      if (A === "m" || A === "b" || A === "z") {
        const r = await cagir("sekil_firca", S.cur, S.fid, {tur: A === "m" ? "it" : A === "b" ? "sis" : "kuc", pts: c.pts, r: S.firca / 2 / c.w, guc: S.sGuc / 100});
        if (r.ok) guncelle(r);
        return;
      }
      if (A === "n") {
        if (!S.kOfs) S.kOfs = [S.kSrc[0] - c.pts[0][0], S.kSrc[1] - c.pts[0][1]];   // hizalı: kaynak–hedef farkı vuruşlar arasında sabit
        const k0 = [c.pts[0][0] + S.kOfs[0], c.pts[0][1] + S.kOfs[1]];
        const r = await cagir("klon_firca", S.cur, S.fid, {pts: c.pts, src: k0, r: S.firca / 2 / c.w, val: S.kVal / 100, hard: S.kHard / 100});
        if (r.ok) guncelle(r);
        return;
      }
      const r = await cagir("rotus_firca", S.cur, S.fid, {pts: c.pts, r: S.firca / 2 / c.w, val: A === "g" ? S.rVal / 100 : 1, tur: A === "g" ? "geri" : "koru", hard: 0.4});
      if (r.ok) guncelle(r);
    });
  }
  sh.append(h(`<div class="efsane"><span><span style="display:inline-block;width:10px;height:10px;border:2px solid var(--iyi);border-radius:5px"></span> Onarılan leke: ${(S.st.lekeler || []).length} · Geri al fırçası: ${fs[0]} · Koruma fırçası: ${fs[1]}</span></div>`));
}

function olcekTuval(sh, alan, ic, kat, norm) {
  const f = S.fmt[S.fid];
  const o = S.st.olcu || {};
  const mm = (v, ax) => (ax === "x" ? v / f.gen_mm : v / f.yuk_mm) * 100 + "%";
  const svgNS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNS, "svg");
  svg.setAttribute("viewBox", `0 0 ${f.gen_mm} ${f.yuk_mm}`); svg.setAttribute("preserveAspectRatio", "none");
  Object.assign(svg.style, {position: "absolute", inset: 0, width: "100%", height: "100%", overflow: "visible"});
  const headT = f.chin_mm - (f.chin_mm - f.eye_mm) * 2.05;
  const lw = 0.18;
  let s = "";
  if (S.ayar.sablon_goster !== false) {
    // şablon: baş oval + omuz hattı
    const hh = f.chin_mm - headT, hw = hh * 0.74, cx = f.gen_mm / 2, cy = headT + hh / 2;
    s += `<ellipse cx="${cx}" cy="${cy}" rx="${hw / 2}" ry="${hh / 2}" fill="rgba(90,160,255,.10)" stroke="rgba(90,160,255,.85)" stroke-width="${lw}" stroke-dasharray="1 .6"/>`;
    const sy = f.chin_mm + hh * 0.22;
    s += `<path d="M${cx - hw * 1.25} ${f.yuk_mm} C ${cx - hw * 1.25} ${sy + 3}, ${cx - hw * 0.6} ${sy}, ${cx - hw * 0.28} ${f.chin_mm + 1.2} M${cx + hw * 1.25} ${f.yuk_mm} C ${cx + hw * 1.25} ${sy + 3}, ${cx + hw * 0.6} ${sy}, ${cx + hw * 0.28} ${f.chin_mm + 1.2}" fill="none" stroke="rgba(90,160,255,.7)" stroke-width="${lw}" stroke-dasharray="1 .6"/>`;
  }
  // kılavuzlar: göz hattı, çene, baş aralığı, orta
  s += `<line x1="0" x2="${f.gen_mm}" y1="${f.eye_mm}" y2="${f.eye_mm}" stroke="#5AA0FF" stroke-width="${lw}" stroke-dasharray=".8 .5"/>`;
  s += `<line x1="0" x2="${f.gen_mm}" y1="${f.chin_mm}" y2="${f.chin_mm}" stroke="#FF6B6B" stroke-width="${lw}" stroke-dasharray=".8 .5"/>`;
  s += `<rect x="0" width="${f.gen_mm}" y="${f.chin_mm - f.head_max}" height="${Math.max(0.1, f.head_max - f.head_min)}" fill="rgba(255,107,107,.10)" stroke="none"/>`;
  s += `<line x1="${f.gen_mm / 2}" x2="${f.gen_mm / 2}" y1="0" y2="${f.yuk_mm}" stroke="#5AA0FF" stroke-width="${lw * 0.8}" stroke-dasharray=".3 .5"/>`;
  if (o.tepe_mm != null) {
    s += `<line x1="${f.gen_mm * 0.25}" x2="${f.gen_mm * 0.75}" y1="${o.tepe_mm}" y2="${o.tepe_mm}" stroke="#3DD68C" stroke-width="${lw * 2}"/>`;
    s += `<line x1="${f.gen_mm * 0.3}" x2="${f.gen_mm * 0.7}" y1="${o.cene_mm}" y2="${o.cene_mm}" stroke="#3DD68C" stroke-width="${lw * 2}"/>`;
  }
  svg.innerHTML = s;
  kat.append(svg);
  // cetvel etiketleri
  kat.append(h(`<span class="etiket" style="left:calc(100% + 8px);top:${mm(f.eye_mm)};transform:translateY(-50%);background:#5AA0FF">Göz ${f.eye_mm} mm</span>`));
  kat.append(h(`<span class="etiket" style="left:calc(100% + 8px);top:${mm(f.chin_mm)};transform:translateY(-50%);background:#FF6B6B">Çene ${f.chin_mm} mm</span>`));
  if (o.bas_mm != null) kat.append(h(`<span class="etiket" style="right:calc(100% + 8px);left:auto;top:${mm((o.tepe_mm + o.cene_mm) / 2)};transform:translateY(-50%);background:var(--iyi);color:#0E1014">Baş ${o.bas_mm} mm</span>`));
  const ar = h(`<div class="araclar"><button class="arac" data-k="-">Küçült</button><button class="arac" data-k="+">Büyüt</button><button class="arac" data-k="sol">↺ Eğim</button><button class="arac" data-k="sag">↻ Eğim</button><button class="arac secili" data-k="tasi">Sürükle: taşı</button><span class="arac-ayrac"></span><button class="arac" data-k="sifir">Sıfırla</button></div>`);
  $$(".arac", ar).forEach(b => b.onclick = () => {
    const g = S.st.geom;
    ({"-": () => geomDegis({zoom: +(g.zoom * 0.99).toFixed(4)}), "+": () => geomDegis({zoom: +(g.zoom * 1.01).toFixed(4)}),
      "sol": () => geomDegis({rot: +(g.rot - 0.5).toFixed(2)}), "sag": () => geomDegis({rot: +(g.rot + 0.5).toFixed(2)}),
      "sifir": async () => { const r = await cagir("reset_geom", S.cur, S.fid); if (r.ok) { S.st = r; ciz(); } }}[b.dataset.k] || (() => {}))();
  });
  sh.append(ar);
  sh.append(h(`<div class="efsane"><span>Sürükle: taşı · Tekerlek: ölçek · Ok tuşları: 0,1 mm · [ ]: eğim · Ctrl+tekerlek: ekran yakınlığı</span></div>`));
  let sur = null;
  alan.addEventListener("mousedown", (e) => {
    if (e.button !== 0 || bosluk) return;
    const r = ic.getBoundingClientRect();
    sur = {x: e.clientX, y: e.clientY, dx: S.st.geom.dx, dy: S.st.geom.dy, k: f.gen_mm / r.width};
  });
  alan.addEventListener("mousemove", (e) => {
    if (!sur) return;
    const nx = sur.dx + (e.clientX - sur.x) * sur.k, ny = sur.dy + (e.clientY - sur.y) * sur.k;
    ic.querySelector("img").style.transform = `translate(${(nx - S.st.geom.dx) / f.gen_mm * 100}%, ${(ny - S.st.geom.dy) / f.yuk_mm * 100}%)`;
    sur.nx = nx; sur.ny = ny;
  });
  window.addEventListener("mouseup", () => { if (sur && sur.nx != null) geomDegis({dx: +sur.nx.toFixed(2), dy: +sur.ny.toFixed(2)}); sur = null; }, {once: true});
}
let geomT = null, geomBekleyen = {};
function geomDegis(d) {
  Object.assign(S.st.geom, d); Object.assign(geomBekleyen, d);
  clearTimeout(geomT);
  geomT = setTimeout(async () => {
    const g = geomBekleyen; geomBekleyen = {};
    const r = await api.set_geom(S.cur, S.fid, g);
    if (r.ok) { S.st = r; durumGuncelle(); sahneCiz(); panelCiz(); siraCiz(); }
  }, 90);
  panelCiz();
}

// ------------------------------------------------------------------ baskı
async function sayfaHazirla() {
  const r = await cagir("sheet", S.cur, S.fid, S.bilgi.adet);
  if (r.ok) { S.sayfa = r; sahneCiz(); }
}
function baskiCiz(sh) {
  if (!S.sayfa) { sh.append(h(`<div class="bos">Baskı sayfası hazırlanıyor…</div>`)); return; }
  sh.append(h(`<div class="sayfa-on"><img src="${S.sayfa.sayfa}" alt="10x15 baskı önizlemesi"><div style="display:flex;flex-direction:column;gap:10px;align-items:center"><img src="${S.sayfa.tekli}" style="max-height:260px;max-width:200px;box-shadow:0 8px 24px rgba(0,0,0,.4)"><span class="not">Tekli · ${esc(S.fmt[S.fid].ad)} · 300 DPI</span><button class="btn kucuk" id="tamBoy">Gerçek boyutlu önizleme</button></div></div>`));
  const tb = $("#tamBoy", sh); if (tb) tb.onclick = () => { const px = 100 / 25.4 * 96; modal("Gerçek boyutlu önizleme (10×15 cm)", h(`<div class="modal-ic"><div class="not">Ekranınızda yaklaşık gerçek ölçüdedir (96 DPI varsayımıyla). Cetvelle ekranı ölçerek kontrol edebilirsiniz.</div><div style="overflow:auto;max-height:70vh;text-align:center"><img src="${S.sayfa.sayfa}" style="width:${px}px;background:#fff;box-shadow:0 4px 20px rgba(0,0,0,.4)"></div></div>`), true); };
}

// ------------------------------------------------------------------ panel
function kaydirici(ad, etiket, deger, min, max, adim, birim, degisti, bilgi = "") {
  const e = h(`<div class="kaydirici" title="${esc(bilgi)}"><div class="ust-s"><label for="k_${ad}">${etiket}</label><span class="deger">${deger}${birim}</span></div><div class="cubuk"><button type="button" class="ok" aria-label="Azalt">◄</button><input id="k_${ad}" type="range" min="${min}" max="${max}" step="${adim}" value="${deger}"><button type="button" class="ok" aria-label="Artır">►</button></div></div>`);
  const inp = $("input", e), [sol, sag] = $$("button.ok", e);
  const nd = (adim + "").includes(".") ? (adim + "").split(".")[1].length : 0;
  inp.oninput = () => $(".deger", e).textContent = inp.value + birim;
  inp.onchange = () => degisti(+inp.value);
  // ok düğmeleri: tek tık = bir adım, basılı tutunca tekrar, Shift = 10 adım; art arda basışlar tek işleme birleşir
  let bekle = null;
  const git = (yon, ev) => {
    const kat = ev && ev.shiftKey ? 10 : 1;
    let v = +inp.value + yon * adim * kat;
    v = Math.min(+max, Math.max(+min, +v.toFixed(nd)));
    inp.value = v; $(".deger", e).textContent = inp.value + birim;
    clearTimeout(bekle); bekle = setTimeout(() => degisti(+inp.value), 350);
  };
  [[sol, -1], [sag, 1]].forEach(([b, yon]) => {
    let t1 = null, t2 = null;
    const dur = () => { clearTimeout(t1); clearInterval(t2); };
    b.onpointerdown = (ev) => { ev.preventDefault(); git(yon, ev); t1 = setTimeout(() => { t2 = setInterval(() => git(yon, ev), 70); }, 400); };
    b.onpointerup = b.onpointerleave = b.onpointercancel = dur;
    b.onkeydown = (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); git(yon, ev); } };
  });
  return e;
}
function bolum(baslik, sag = "") { return h(`<section class="bolum"><h3>${baslik}${sag}</h3></section>`); }
function secim(ad, etiket, deger, degisti, bilgi = "") {
  const e = h(`<label class="secim" title="${esc(bilgi)}">${etiket}<input type="checkbox" ${deger ? "checked" : ""}></label>`);
  $("input", e).onchange = (ev) => degisti(ev.target.checked);
  return e;
}

function panelCiz() {
  const p = $("#panel"); p.innerHTML = "";
  if (S.adim === 0) return panelBaslangic(p);
  if (S.adim === 1) return panelArkaplan(p);
  if (S.adim === 2) return panelRotus(p);
  if (S.adim === 3) return panelOlcek(p);
  if (S.adim === 4) return panelBaski(p);
}

function uygunlukListe(liste) {
  const ul = h(`<ul class="uyg"></ul>`);
  (liste || []).forEach(c => ul.append(h(`<li><span class="d ${c.durum}">${c.durum === "ok" ? "✓" : "!"}</span><span class="a">${esc(c.ad)}</span><span class="v">${esc(c.deger)}</span></li>`)));
  return ul;
}
function uygunlukOzet(liste) {
  const bad = (liste || []).filter(c => c.durum === "bad").length, warn = (liste || []).filter(c => c.durum === "warn").length;
  const renk = bad ? "var(--kotu)" : warn ? "var(--uyari)" : "var(--iyi)";
  const yazi = bad ? `${bad} sorun var` : warn ? `Uygun · ${warn} uyarı` : "Uygun";
  return h(`<div class="ozet"><span class="b" style="background:${renk}">${bad ? "!" : "✓"}</span><div><div style="font-weight:700">${yazi}</div><div class="not">${(liste || []).length} kontrol</div></div></div>`);
}

function panelBaslangic(p) {
  const f = S.fmt[S.fid];
  const b = bolum("BİLGİLER");
  b.append(h(`<div class="alan"><label for="mAd">Müşteri adı (isteğe bağlı)</label><input type="text" id="mAd" value="${esc(S.bilgi.musteri)}" placeholder="Ad Soyad"></div>`));
  b.append(h(`<div class="alan"><label for="mNo">Arşiv numarası</label><input type="text" id="mNo" value="${esc(S.bilgi.no)}"></div>`));
  const ad = h(`<div class="alan"><label>Tür ve adet</label><div class="satir"><span class="cip secili" style="display:inline-flex;align-items:center">${esc(f.ad)}</span><div class="seg" id="adetSeg"></div></div></div>`);
  f.adetler.forEach(n => { const k = h(`<button class="${S.bilgi.adet === n ? "secili" : ""}">${n} adet</button>`); k.onclick = () => { S.bilgi.adet = n; panelCiz(); }; $("#adetSeg", ad).append(k); });
  b.append(ad);
  b.append(h(`<div class="not">Dosya adı: <b id="dAd"></b></div>`));
  p.append(b);
  const guncelAd = () => { const m = $("#mAd").value.trim(); S.bilgi.musteri = m; S.bilgi.no = $("#mNo").value.trim(); S.bilgi._oto = false;
    $("#dAd").textContent = `${S.bilgi.no || "?"} ${S.bilgi.adet}_${f.kisa}${m ? "_" + m : ""}_….jpg`; };
  $("#mAd").oninput = guncelAd; $("#mNo").oninput = guncelAd;
  $("#mAd").onchange = async () => {
    const ad = $("#mAd").value.trim(); if (!ad || !S.cur) return;
    const r = await api.musteri_ayar(S.cur, S.fid, ad, false);
    if (r && r.bulundu) bildir(`${ad} için önceki ayarlar bulundu`, false, {ad: "Uygula", fn: async () => { const x = await cagir("musteri_ayar", S.cur, S.fid, ad, true); if (x.ok && x.bulundu) { S.st = x; isBul(S.cur).rotuslu = true; ciz(); bildir("Önceki rötuş, fon ve saç ayarları uygulandı"); } }});
  };
  if (S.isler.length > 1) {
    const tb = h(`<div class="satir"><button class="btn kucuk genis">Sıradaki tüm fotoğrafları otomatik işle (toplu)</button></div>`);
    $("button", tb).onclick = async () => {
      const ids = S.isler.filter(x => !x.rotuslu).map(x => x.id);
      const r = await cagir("toplu_isle", ids, S.fid);
      if (!r.ok) return;
      r.sonuc.forEach(o => { const j = isBul(o.id); if (!j) return; if (o.ok) { j.analizli = j.maskeli = j.rotuslu = true; j.durum = o.sorun ? "kotu" : "iyi"; j.not = o.sorun ? `${o.sorun} sorun` : "İşlendi"; } else { j.durum = "kotu"; j.not = "Hata"; } });
      siraCiz(); bildir(`Toplu işlem bitti: ${r.sonuc.filter(o => o.ok && !o.sorun).length} uygun, ${r.sonuc.filter(o => !o.ok || o.sorun).length} kontrol gerekli`);
    };
    p.append(tb);
  }
  setTimeout(() => { const m = S.bilgi.musteri; $("#dAd").textContent = `${S.bilgi.no || "?"} ${S.bilgi.adet}_${f.kisa}${m ? "_" + m : ""}_….jpg`; });
  if (S.st?.uygunluk) {
    const k = bolum("HIZLI ÖN KONTROL");
    k.append(uygunlukOzet(S.st.uygunluk));
    k.append(h(`<div class="not">Sorun varsa müşteri hâlâ buradayken yeniden çekebilirsiniz.</div>`));
    k.append(uygunlukListe(S.st.uygunluk.filter(c => ["Tek yüz", "Gözler açık", "Ağız kapalı", "Baş dönüklüğü", "Gözlük", "Işık dengesi", "Netlik"].includes(c.ad))));
    p.append(k);
  }
  const o = bolum("OTOMATİK");
  o.append(secim("hm", "Hızlı mod (sorun yoksa tüm adımlar otomatik)", S.ayar.hizli_mod, async v => { S.ayar.hizli_mod = v; await api.update_settings({hizli_mod: v}); }));
  o.append(h(`<div class="not">Kamera klasörü: ${esc(S.ayar.kamera_klasoru || "seçilmedi")} — Ayarlar'dan değiştirilir.</div>`));
  p.append(o);
}

function panelArkaplan(p) {
  const st = S.st, m = st.matte, f = S.fmt[S.fid];
  const b1 = bolum("YAPAY ZEKA MODELİ");
  const ML = (S.modeller || []).filter(x => x.var && !x.kapali && x.key !== "vitmatte");
  const modeller = [["auto", "Otomatik (en kaliteli)"], ...(ML.length ? ML : [{key: "birefnet", ad: "BiRefNet Portre"}, {key: "isnet", ad: "ISNet"}, {key: "u2net", ad: "U²-Net"}]).map(x => [x.key, x.ad + (x.ticari === false ? " · ticari değil" : "")])];
  const sel = h(`<select aria-label="Model"></select>`);
  modeller.forEach(([k, a]) => sel.append(h(`<option value="${k}" ${(m.model || "auto") === k ? "selected" : ""}>${a}</option>`)));
  sel.onchange = async () => { const r = await cagir("matte", S.cur, S.fid, {model: sel.value}, true); if (r.ok) { S.st = r; ciz(); } };
  b1.append(sel);
  const lab = h(`<button class="btn kucuk genis ana">Model Laboratuvarı · modelleri karşılaştır…</button>`);
  lab.onclick = modelLab;
  const mdk = h(`<button class="btn kucuk genis" title="Saç ve kenarı fırçayla elle düzeltin: her dokunuş anında görünür, otomatik işlem yoktur">✎ Manuel dekupe · saç düzenle${st.manuel_var && st.manuel_var[1] ? " ●" : ""}</button>`);
  mdk.onclick = () => manuelAc("dekupe");
  b1.append(lab, mdk);
  if ((S.modeller || []).some(x => x.key === "vitmatte" && x.var && !x.kapali))
    b1.append(secim("vm", "ViTMatte ile kenar rafine et (ticari değil)", !!m.vitmatte, async v => { const r = await cagir("matte", S.cur, S.fid, {vitmatte: v}, true); if (r.ok) { S.st = r; ciz(); } }, "Saç kenarındaki belirsiz bandı ince ayarlar; yavaştır"));
  b1.append(h(`<div class="not">Kullanılan: <b>${esc(((S.modeller || []).find(x => x.key === st.model) || {}).ad || st.model)}</b> · ${esc(st.donanim)}</div>`));
  const yb = h(`<div class="satir"><button class="btn kucuk genis" id="bYen">Yeniden hesapla</button><button class="btn kucuk genis" id="bGeri">Son düzeltmeyi geri al</button></div>`);
  $("#bYen", yb).onclick = async () => { const r = await cagir("matte", S.cur, S.fid, null, true); if (r.ok) { S.st = r; ciz(); } };
  $("#bGeri", yb).onclick = geriAl;
  $("#bGeri", yb).disabled = !st.duzeltme_sayisi;
  b1.append(yb);
  p.append(b1);
  if ((st.supheli || []).length) {
    const b = bolum("KONTROL EDİLMESİ GEREKENLER");
    b.append(h(`<div class="not">Sarı kesikli alanlara bakın. Hatalı yerde <b>＋ Kişiye ekle</b> veya <b>− Fon say</b> ile tıklayın; ince ayar için fırçayı kullanın.</div>`));
    st.supheli.forEach(x => b.append(h(`<div class="satir" style="font-size:13px"><span style="color:var(--uyari)">▲</span>${esc(x.ad)}</div>`)));
    p.append(b);
  }
  const bh = bolum("SAÇ TİPİ");
  const modlar = {otomatik: "Otomatik", kivircik: "Kıvırcık / çok saçlı", dalgali: "Dalgalı", duz: "Düz / ince saç", az: "Kısa / az saç / kel", ortulu: "Örtülü (başörtüsü, şapka)"};
  const hs = h(`<select aria-label="Saç tipi">${Object.entries(modlar).map(([k, v]) => `<option value="${k}" ${m.sac_modu === k ? "selected" : ""}>${v}</option>`).join("")}</select>`);
  hs.onchange = async () => { const r = await cagir("sac_modu", S.cur, S.fid, hs.value); if (r.ok) { S.st = r; sahneCiz(); panelCiz(); } };
  bh.append(hs);
  const yk2 = h(`<div class="satir"><button class="btn kucuk genis">Saça yakınlaş (kenarı fırçayla düzelt)</button></div>`);
  $("button", yk2).onclick = () => { V.zoom = 3; V.panX = 0; V.panY = 260; sahneCiz(); };
  bh.append(yk2);
  bh.append(h(`<div class="not">Saç tipi, kenar ince ayarlarını o saç yapısına göre hazırlar. Sonra aşağıdan değiştirebilirsiniz.</div>`));
  p.append(bh);
  const b2 = bolum("KENAR İNCE AYARI", `<a id="oner">Önerilene dön</a>`);
  const mset = (k) => async (v) => { const r = await cagir("set_matte", S.cur, S.fid, {[k]: v}); if (r.ok) { S.st = r; sahneCiz(); } };
  b2.append(kaydirici("fa", "Gri hale temizliği", m.fon_ayikla, 0, 100, 1, "", mset("fon_ayikla"), "Saç kenarında kalan eski fon rengini temizler"));
  b2.append(kaydirici("sd", "Saç detayı", m.sac_detay, 0, 100, 1, "", mset("sac_detay")));
  b2.append(kaydirici("yu", "Kenar yumuşaklığı", m.yumusaklik, 0, 100, 1, "", mset("yumusaklik")));
  b2.append(kaydirici("da", "Kenar daraltma", m.daraltma, 0, 4, 1, " px", mset("daraltma")));
  b2.append(kaydirici("ta", "Renk taşması temizleme", m.tasma, 0, 100, 1, "", mset("tasma")));
  b2.append(kaydirici("st", "Uçuşan saç temizleme", m.sac_temizle, 0, 100, 1, "", mset("sac_temizle"), "Fona taşan tek tek saç tellerini siler"));
  b2.append(kaydirici("fb", "Fırça boyutu", S.firca, 6, 160, 1, " px", v => { S.firca = v; }));
  p.append(b2);
  $("#oner", b2).onclick = async () => { const d = S.init.varsayilanlar.matte; const r = await cagir("set_matte", S.cur, S.fid, {...d, model: m.model}); if (r.ok) { S.st = r; ciz(); } };
  p.append(fonPaneli(f));
}

function fonPaneli(f) {
  const bg = S.st.bg;
  const b = bolum("FON");
  const tip = bg.tip === "auto" ? (f.fon === "original" ? "original" : "solid") : bg.tip;
  const set = async (d) => { const r = await cagir("set_bg", S.cur, S.fid, d); if (r.ok) { S.st = r; sahneCiz(); panelCiz(); } };
  if (f.grup !== "vesikalik") {
    b.append(h(`<div class="not">${f.grup === "biyometrik" ? "Biyometrikte" : "Vizede"} fon kurala göre: <b>${f.fon === "lightgray" ? "açık gri" : "beyaz"}</b>.</div>`));
    const s = h(`<div class="seg"><button data-r="#FFFFFF">Beyaz</button><button data-r="#EEEEEE">Açık gri</button><button data-r="#F6F4EF">Kırık beyaz</button></div>`);
    $$("button", s).forEach(k => { k.classList.toggle("secili", (bg.tip === "auto" && k.dataset.r === (f.fon === "lightgray" ? "#EEEEEE" : "#FFFFFF")) || (bg.tip === "solid" && bg.renk === k.dataset.r)); k.onclick = () => set({tip: "solid", renk: k.dataset.r}); });
    b.append(s);
    return b;
  }
  const seg = h(`<div class="seg"><button data-t="original">Orijinal fon</button><button data-t="gradient">Degrade</button><button data-t="solid">Düz renk</button></div>`);
  $$("button", seg).forEach(k => { k.classList.toggle("secili", tip === k.dataset.t); k.onclick = () => set({tip: k.dataset.t}); });
  b.append(seg);
  if (tip === "original") {
    b.append(h(`<div class="not">Kişi kesilmez; stüdyo fonu korunur.</div>`));
    b.append(kaydirici("fa2", "Fonu aydınlat", bg.fon_aydinlat, 0, 100, 1, "", v => set({fon_aydinlat: v})));
    b.append(kaydirici("ft", "Fon lekelerini temizle", bg.fon_temizle, 0, 100, 1, "", v => set({fon_temizle: v})));
  } else if (tip === "gradient") {
    const g = h(`<div class="fonlar"></div>`);
    S.init.degradeler.forEach(d => { const k = h(`<button class="fon ${+bg.degrade === d.no ? "secili" : ""}" title="${d.no}. ${esc(d.ad)}" style="background-image:url(assets/degrade_${d.no}.png)"><span>${d.no}</span></button>`); k.onclick = () => set({degrade: d.no, ic: null, dis: null}); g.append(k); });
    b.append(g);
    const cur = S.init.degradeler.find(d => d.no === +bg.degrade) || S.init.degradeler[0];
    b.append(h(`<div class="not"><b>${cur.no}. ${esc(cur.ad)}</b></div>`));
    b.append(kaydirici("mx", "Işık merkezi (yatay)", Math.round(bg.merkez_x * 100), 0, 100, 1, "%", v => set({merkez_x: v / 100})));
    b.append(kaydirici("my", "Işık merkezi (dikey)", Math.round(bg.merkez_y * 100), 0, 100, 1, "%", v => set({merkez_y: v / 100})));
    b.append(kaydirici("ya", "Yayılma", Math.round(bg.yayilma * 100), 20, 150, 1, "%", v => set({yayilma: v / 100})));
    b.append(kaydirici("se", "Kenar koyuluğu (sertlik)", Math.round(bg.sertlik * 10) / 10, 0.5, 3, 0.1, "", v => set({sertlik: v})));
    const rk = h(`<div class="satir"><div class="alan" style="flex:1"><label>İç renk</label><input type="color" class="renk-sec" value="${bg.ic || cur.ic}"></div><div class="alan" style="flex:1"><label>Dış renk</label><input type="color" class="renk-sec" value="${bg.dis || cur.dis}"></div></div>`);
    const [ri, rd] = $$("input", rk);
    ri.onchange = () => set({ic: ri.value}); rd.onchange = () => set({dis: rd.value});
    const tk = h(`<button type="button" class="takas" title="İç ve dış rengi değiştir" aria-label="İç ve dış rengi değiştir">⇄</button>`);
    tk.onclick = () => { const a = ri.value; ri.value = rd.value; rd.value = a; set({ic: ri.value, dis: rd.value}); };
    rk.insertBefore(tk, rk.children[1]);
    b.append(rk);
  } else {
    const rk = h(`<div class="satir"><input type="color" class="renk-sec" value="${bg.renk || "#FFFFFF"}" aria-label="Fon rengi"></div>`);
    $("input", rk).onchange = (e) => set({tip: "solid", renk: e.target.value});
    b.append(rk);
  }
  return b;
}

function panelRotus(p) {
  const r = S.st.rotus, f = S.fmt[S.fid];
  const set = (k) => async (v) => { const x = await rotusUygula({[k]: v}); if (x.ok) { S.st.gorsel_once = S.st.gorsel_once; sahneCiz(); panelCiz(); } };
  const pr = bolum("PROFİL");
  const profiller = S.ayar.rotus_profilleri || {};
  const sel = h(`<select aria-label="Rötuş profili"><option value="">— Profil seç —</option><option value="__dogal">Biyometrik · Doğal (önerilen)</option><option value="__belirgin">Vesikalık · Belirgin</option>${Object.keys(profiller).map(k => `<option value="${esc(k)}">${esc(k)}</option>`).join("")}</select>`);
  sel.onchange = async () => {
    const hazir = {__dogal: {leke: 55, yumusatma: 25, doku: 70, parlama: 40, gozalti: 15, goz_beyaz: 0, dis_beyaz: 0},
      __belirgin: {leke: 70, yumusatma: 45, doku: 60, parlama: 55, gozalti: 30, goz_beyaz: 30, dis_beyaz: 20}};
    const v = hazir[sel.value] || profiller[sel.value]; if (!v) return;
    const x = await rotusUygula(v); if (x.ok) { sahneCiz(); panelCiz(); }
  };
  pr.append(sel);
  const mrt = h(`<button class="btn kucuk genis ana" title="Photoshop benzeri klon damgası, yama ve nokta iyileştirme: her vuruş anında etki eder">✎ Manuel rötuş ekranı${S.st.manuel_var && S.st.manuel_var[0] ? " ●" : ""}</button>`);
  mrt.onclick = () => manuelAc("rotus");
  pr.append(mrt);
  const pb = h(`<div class="satir"><button class="btn kucuk genis">Profili kaydet</button></div>`);
  $("button", pb).onclick = () => metinSor("Profil adı", "", async (ad) => { if (!ad) return; profiller[ad] = {...r}; S.ayar.rotus_profilleri = profiller; await api.update_settings({rotus_profilleri: profiller}); bildir("Profil kaydedildi"); panelCiz(); });
  pr.append(pb);
  p.append(pr);
  const l = bolum("LEKE VE SİVİLCE · LaMa");
  l.append(kaydirici("le", "Hassasiyet (0 = kapalı)", r.leke, 0, 100, 1, "", set("leke")));
  l.append(h(`<div class="not">${(S.st.lekeler || []).length} leke bulundu. <b>Leke fırçası</b> ile tıklayarak ekleyin veya bulunanı geri alın.</div>`));
  l.append(kaydirici("go", "Gözlük yansıması temizleme", r.gozluk, 0, 100, 1, "", set("gozluk"), "Camdaki flaş parlaması ve renkli yansımayı onarır"));
  p.append(l);
  const c = bolum("CİLT");
  c.append(kaydirici("yu2", "Yumuşatma", r.yumusatma, 0, 100, 1, "", set("yumusatma")));
  c.append(kaydirici("do", "Doku koruma", r.doku, 0, 100, 1, "", set("doku")));
  c.append(kaydirici("pa", "Parlama azaltma", r.parlama, 0, 100, 1, "", set("parlama")));
  c.append(kaydirici("ga", "Göz altı aydınlatma", r.gozalti, 0, 100, 1, "", set("gozalti")));
  p.append(c);
  const sp = (k) => async (v) => { const x = await rotusUygula({pro: {...(S.st.rotus.pro || {}), [k]: v}}); if (x.ok) { sahneCiz(); panelCiz(); } };
  const pro = r.pro || {};
  const gp = bolum("GELİŞMİŞ PORTRE RÖTUŞU");
  gp.append(secim("pa1", "Açık (ten örneğine göre profesyonel yumuşatma)", !!pro.acik, sp("acik"), "Imagenomic benzeri 3 ölçekli yumuşatma"));
  if (pro.acik) {
    gp.append(kaydirici("pm", "Genel miktar", pro.miktar ?? 60, 0, 100, 1, "", sp("miktar")));
    gp.append(kaydirici("pi", "İnce gözenek", pro.ince ?? 4, 0, 10, 1, "", sp("ince")));
    gp.append(kaydirici("po2", "Orta leke ve düzensizlik", pro.orta ?? 5, 0, 10, 1, "", sp("orta")));
    gp.append(kaydirici("pk", "Kaba ton geçişi", pro.kaba ?? 3, 0, 10, 1, "", sp("kaba")));
    gp.append(kaydirici("pe", "Detay koruma eşiği", pro.esik ?? 55, 10, 100, 1, "", sp("esik"), "Yüksek: belirgin çizgiler (kırışık, kaş) korunur"));
    gp.append(kaydirici("pt", "Ten benzerliği toleransı", pro.tolerans ?? 24, 8, 60, 1, "", sp("tolerans"), "Seçilen ten örneğine ne kadar benzeyen yerler etkilensin"));
    gp.append(kaydirici("py", "Etki alanı", pro.yayilma ?? 100, 0, 100, 1, "%", sp("yayilma")));
    const gb = h(`<div class="satir"><button class="btn kucuk">Ten örneği seç</button><button class="btn kucuk">Örnekleri temizle (${(S.st.pro_ornekler || []).length})</button></div>`);
    const [b1, b2] = $$("button", gb);
    b1.onclick = () => { S.rArac = "t"; sahneCiz(); };
    b2.onclick = async () => { const x = await cagir("pro_ornek", S.cur, S.fid, null, null, true); if (x.ok) { S.st = {...x, gorsel_once: S.st.gorsel_once}; sahneCiz(); panelCiz(); } };
    gp.append(gb);
  }
  p.append(gp);
  const ks = r.keskin || {};
  const sk = (k) => async (v) => { const x = await rotusUygula({keskin: {...(S.st.rotus.keskin || {}), [k]: v}}); if (x.ok) { sahneCiz(); panelCiz(); } };
  const gk = bolum("KESKİNLEŞTİRME (Unsharp Mask)");
  gk.append(kaydirici("km", "Miktar", ks.miktar ?? 50, 0, 150, 1, "%", sk("miktar")));
  gk.append(kaydirici("kya", "Yarıçap", ks.yaricap ?? 1.0, 0.3, 5, 0.1, " px", sk("yaricap")));
  gk.append(kaydirici("ke", "Eşik", ks.esik ?? 0, 0, 20, 1, "", sk("esik"), "Düşük kontrastlı yerleri (gürültü, cilt) keskinleştirme"));
  gk.append(secim("kc", "Cildi koru (yüzde daha az keskinlik)", ks.cilt_koru !== false, sk("cilt_koru")));
  p.append(gk);
  const gs = bolum("ŞEKİLLENDİR (omuz ve duruş)");
  gs.append(kaydirici("om", "Otomatik omuz hizalama", Math.round((S.st.omuz || 0) * 100), 0, 100, 1, "%", async v => { const x = await cagir("sekil_omuz", S.cur, S.fid, v / 100); if (x.ok) { S.st = {...x, gorsel_once: S.st.gorsel_once}; sahneCiz(); panelCiz(); } }, "Omuz hattı farkını (yüzü değiştirmeden) giderir"));
  gs.append(h(`<div class="not">${S.st.omuz_fark == null ? "Omuz farkı ölçülemedi." : Math.abs(S.st.omuz_fark) < 6 ? "Omuzlar zaten dengeli." : `Ölçülen omuz farkı: <b>${Math.abs(S.st.omuz_fark).toFixed(0)} px</b> (${S.st.omuz_fark > 0 ? "sol" : "sağ"} omuz daha aşağıda).`} Elle düzeltmek için araç çubuğundan <b>İt / çek</b>, <b>Şişir</b>, <b>Küçült</b>. Yüz bölgesi kilitlidir.</div>`));
  const gsb = h(`<button class="btn kucuk">Şekillendirmeyi sıfırla</button>`);
  gsb.onclick = async () => { const x = await cagir("sekil_geri_al", S.cur, S.fid, true); if (x.ok) { S.st = {...x, gorsel_once: S.st.gorsel_once}; sahneCiz(); panelCiz(); } };
  gs.append(gsb);
  p.append(gs);
  const kb = bolum("DETAY KORUMA");
  kb.append(kaydirici("kr", "Koruma gücü (kirpik, kaş, bıyık, sakal, burun delikleri)", r.koruma, 0, 100, 1, "", set("koruma"), "Bu bölgelere rötuş dokunmaz. Yeşil harita için K tuşu"));
  kb.append(secim("gv", "Güvenli sınır (kişiye ait kırışık/ben/sakal korunur)", r.guvenli, set("guvenli")));
  kb.append(h(`<div class="not">Fırçalar: <b>G</b> geri al (yüzdelik), <b>P</b> koru, <b>L</b> leke, <b>S</b> klon, <b>T</b> ten örneği. Leke işaretini silmek için tıklayıp <b>Delete</b> veya sağ tık.</div>`));
  p.append(kb);
  const gd = bolum("GÖZ VE DİŞ");
  if (f.grup === "vesikalik") {
    gd.append(kaydirici("gb", "Göz beyazlatma", r.goz_beyaz, 0, 100, 1, "", set("goz_beyaz")));
    gd.append(kaydirici("db", "Diş beyazlatma", r.dis_beyaz, 0, 100, 1, "", set("dis_beyaz")));
  } else gd.append(h(`<div class="not">Biyometrik ve vize fotoğraflarında kapalıdır (yüz hatları değiştirilmez).</div>`));
  p.append(gd);
  const t = bolum("IŞIK VE RENK");
  t.append(secim("ob", "Otomatik beyaz dengesi (fona göre)", r.oto_beyaz, set("oto_beyaz")));
  t.append(kaydirici("po", "Pozlama", r.pozlama, -100, 100, 1, "", set("pozlama")));
  t.append(kaydirici("ko", "Kontrast", r.kontrast, -100, 100, 1, "", set("kontrast")));
  t.append(kaydirici("si", "Sıcaklık", r.sicaklik, -100, 100, 1, "", set("sicaklik")));
  p.append(t);
  const s = bolum("STİL (Hayal Medya görünümü)");
  const ss = h(`<select aria-label="Stil"><option value="">Kapalı</option>${(S.init.stiller || []).map(x => `<option ${r.stil === x ? "selected" : ""}>${esc(x)}</option>`).join("")}</select>`);
  ss.onchange = () => set("stil")(ss.value);
  s.append(ss);
  if (r.stil) s.append(kaydirici("sg", "Stil gücü", r.stil_guc, 0, 100, 1, "%", set("stil_guc")));
  const so = h(`<button class="btn kucuk">Öncesi/sonrası çiftlerinden stil öğren…</button>`);
  so.onclick = stilOgren;
  s.append(so);
  p.append(s);
}

function panelOlcek(p) {
  const f = S.fmt[S.fid], g = S.st.geom, o = S.st.olcu || {};
  const b = bolum("STANDART");
  b.append(h(`<div><div style="font-size:19px;font-weight:700">${esc(f.ad)}</div><div class="not">${f.gen_mm} × ${f.yuk_mm} mm · 300 DPI · göz ${f.eye_mm} mm · çene ${f.chin_mm} mm</div></div>`));
  b.append(secim("sb", "Şablonu göster", S.ayar.sablon_goster !== false, async v => { S.ayar.sablon_goster = v; await api.update_settings({sablon_goster: v}); sahneCiz(); }));
  p.append(b);
  const i = bolum("İNCE AYAR");
  i.append(kaydirici("zo", "Ölçek", Math.round(g.zoom * 1000) / 10, 70, 140, 0.5, " %", v => geomDegis({zoom: v / 100})));
  i.append(kaydirici("ro", "Eğim", g.rot, -15, 15, 0.1, "°", v => geomDegis({rot: v})));
  i.append(kaydirici("dx", "Yatay kaydırma", g.dx, -15, 15, 0.1, " mm", v => geomDegis({dx: v})));
  i.append(kaydirici("dy", "Dikey kaydırma", g.dy, -15, 15, 0.1, " mm", v => geomDegis({dy: v})));
  i.append(secim("du", "Başı otomatik düzleştir", g.duzlestir, v => geomDegis({duzlestir: v})));
  i.append(h(`<div class="not">Ölçülen: tepe ${o.tepe_mm ?? "–"} mm · göz ${o.goz_mm ?? "–"} mm · çene ${o.cene_mm ?? "–"} mm · baş ${o.bas_mm ?? "–"} mm</div>`));
  p.append(i);
  const u = bolum("UYGUNLUK RAPORU");
  u.append(uygunlukOzet(S.st.uygunluk));
  u.append(uygunlukListe(S.st.uygunluk));
  p.append(u);
}

function panelBaski(p) {
  const f = S.fmt[S.fid];
  const k = bolum("KAĞIT");
  k.append(h(`<div class="ozet"><span class="b" style="background:var(--vurgu)">▭</span><div><div style="font-weight:700">10 × 15 cm</div><div class="not">300 DPI · beyaz zemin · ${f.dizim === "cerceveli" ? "ayrık kutular, ince koyu gri çerçeve" : "bitişik, aralarında ince gri kesim çizgisi"}</div></div></div>`));
  const ad = h(`<div class="seg"></div>`);
  f.adetler.forEach(n => { const b = h(`<button class="${S.bilgi.adet === n ? "secili" : ""}">${n} adet</button>`); b.onclick = async () => { S.bilgi.adet = n; panelCiz(); await sayfaHazirla(); }; ad.append(b); });
  k.append(ad);
  if (f.dizim !== "ortali" && S.bilgi.adet === 8) k.append(h(`<div class="not">8 adet = aynı sayfadan 2 baskı.</div>`));
  if (["abd", "hindistan"].includes(S.fid)) k.append(h(`<div class="not">5,08 cm fotoğraflar 10 cm kağıda yan yana tam sığmadığı için her birinden 0,4 mm kırpılır.</div>`));
  p.append(k);
  const kb = bolum("KAYIT");
  kb.append(h(`<div class="alan"><label for="sNo">Arşiv numarası</label><input type="text" id="sNo" value="${esc(S.bilgi.no)}"></div>`));
  kb.append(h(`<div class="alan"><label for="sAd">Müşteri adı</label><input type="text" id="sAd" value="${esc(S.bilgi.musteri)}"></div>`));
  kb.append(h(`<div class="alan"><label>Kayıt yeri</label><div class="satir"><input type="text" id="sKl" value="${esc(S.kayitKlasor || S.ayar.varsayilan_klasor || "")}" placeholder="Klasör seçin"><button class="btn kucuk" id="bKl">Seç…</button></div></div>`));
  kb.append(secim("tk", "Tekli JPG de kaydet (başvuru ölçüsü)", S.ayar.tekli_jpg !== false, v => { S.ayar.tekli_jpg = v; api.update_settings({tekli_jpg: v}); }));
  kb.append(secim("on", "Online başvuru çıktısı (600 px, ≤240 KB)", !!S.online, v => { S.online = v; }));
  kb.append(h(`<div class="not">JPEG kalite 100 · 4:4:4 · sRGB · 300 DPI</div>`));
  p.append(kb);
  $("#bKl", kb).onclick = async () => { const k2 = await api.pick_folder(S.kayitKlasor || S.ayar.varsayilan_klasor || ""); if (k2) { S.kayitKlasor = k2; $("#sKl").value = k2; } };
  const y = bolum("YAZICI");
  const ys = h(`<select id="sYz" aria-label="Yazıcı"></select>`);
  (S.init.yazicilar || []).forEach(n => ys.append(h(`<option ${n === S.ayar.varsayilan_yazici ? "selected" : ""}>${esc(n)}</option>`)));
  if (!(S.init.yazicilar || []).length) ys.append(h(`<option value="">Yazıcı bulunamadı</option>`));
  y.append(ys);
  p.append(y);
  const btn = bolum("ONAY");
  const b1 = h(`<button class="btn ana">Kaydet ve Yazdır</button>`), b2 = h(`<button class="btn">Sadece Kaydet</button>`);
  b1.onclick = () => kaydet(true); b2.onclick = () => kaydet(false);
  b1.disabled = !(S.init.yazicilar || []).length;
  btn.append(b1, b2);
  p.append(btn);
}
function sonKontrol(onay) {
  const ad = $("#sAd")?.value.trim(), yz = $("#sYz")?.value, sayfa = (+S.bilgi.adet || 4) / 4;
  const uyg = (S.st?.uygunluk || []).filter(c => c.durum !== "ok");
  const sat = [
    [!!ad, "Müşteri adı", ad || "Girilmemiş (dosya adında boş kalır)"],
    [true, "Adet", `${S.bilgi.adet} fotoğraf · ${sayfa} sayfa baskı`],
    [!!yz, "Yazıcı", yz || "Seçilmemiş"],
    [!uyg.length, "Uygunluk", uyg.length ? uyg.map(c => c.ad).join(", ") : "Tüm kurallar uygun"],
  ];
  const ic = h(`<div class="modal-ic"><div style="display:flex;gap:16px;align-items:flex-start"><img src="${S.sayfa?.sayfa || ""}" style="max-height:340px;max-width:46%;border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.35)" alt="Baskı önizlemesi"><ul class="uyg" style="flex:1"></ul></div>
    <label class="secim">Bir daha gösterme<input type="checkbox" id="skSorma"></label>
    <div class="satir" style="justify-content:flex-end"><button class="btn">Geri dön</button><button class="btn ana">Yazdır</button></div></div>`);
  sat.forEach(([ok, a, v]) => $("ul", ic).append(h(`<li><span class="d ${ok ? "ok" : "uyari"}">${ok ? "✓" : "!"}</span><span class="a">${esc(a)}</span><span class="v">${esc(v)}</span></li>`)));
  const [g, y] = $$("button", ic);
  g.onclick = kapat;
  y.onclick = async () => { if ($("#skSorma", ic).checked) { S.ayar.son_kontrol = false; await api.update_settings({son_kontrol: false}); } kapat(); onay(); };
  modal("Baskı öncesi son kontrol", ic, true);
}

async function kaydet(yazdir, kontrolsuz = false) {
  const klasor = $("#sKl").value.trim();
  if (!klasor) { bildir("Önce kayıt klasörünü seçin.", true); return; }
  if (yazdir && !kontrolsuz && S.ayar.son_kontrol !== false) { sonKontrol(() => kaydet(yazdir, true)); return; }
  S.bilgi.no = $("#sNo").value.trim(); S.bilgi.musteri = $("#sAd").value.trim(); S.kayitKlasor = klasor;
  const r = await cagir("save", S.cur, S.fid, {klasor, no: S.bilgi.no, adet: S.bilgi.adet, musteri: S.bilgi.musteri, tekli: S.ayar.tekli_jpg !== false,
    online: !!S.online, yazdir, yazici: $("#sYz")?.value, kopya: 1});
  if (!r.ok) return;
  const j = isBul(S.cur); j.kaydedildi = true; j.not = "Kaydedildi" + (r.yazdirildi ? " · basıldı" : ""); j.durum = "iyi";
  S.bilgi.no = String(r.sonraki_no); S.bilgi._oto = true;
  siraCiz(); altCiz(); panelCiz();
  bildir(`Kaydedildi${r.yazdirildi ? " ve yazıcıya gönderildi" : ""}: ${Object.keys(r.dosyalar).length} dosya`, false, {ad: "Klasörü aç", fn: () => api.open_folder(klasor)});
}

// ------------------------------------------------------------------ geri al
async function geriAl() {
  if (S.adim === 1 && S.st?.duzeltme_sayisi) { const r = await cagir("undo_edit", S.cur, S.fid); if (r.ok) { S.st = r; ciz(); } }
  else if (S.adim === 3) { const r = await cagir("reset_geom", S.cur, S.fid); if (r.ok) { S.st = r; ciz(); } }
}

// ------------------------------------------------------------------ modallar
function modal(baslik, icerik, genis = false) {
  const m = $("#modal"), k = $("#modalKutu");
  k.innerHTML = ""; k.style.width = genis ? "min(980px,94vw)" : "";
  const bas = h(`<div class="modal-bas"><h2>${baslik}</h2><button class="ikon" aria-label="Kapat">✕</button></div>`);
  $("button", bas).onclick = kapat;
  k.append(bas, icerik);
  m.classList.remove("gizli");
  m.onclick = (e) => { if (e.target === m) kapat(); };
}
function kapat() { $("#modal").classList.add("gizli"); }
function metinSor(baslik, deger, ok, sifre = false) {
  const ic = h(`<div class="modal-ic"><input type="${sifre ? "password" : "text"}" value="${esc(deger)}"><div class="satir" style="justify-content:flex-end"><button class="btn">Vazgeç</button><button class="btn ana">Tamam</button></div></div>`);
  const [v, t] = $$("button", ic);
  v.onclick = kapat; t.onclick = () => { const x = $("input", ic).value; kapat(); ok(x); };
  $("input", ic).onkeydown = (e) => { if (e.key === "Enter") t.click(); };
  modal(baslik, ic);
  setTimeout(() => $("input", ic).focus(), 50);
}

async function stilOgren() {
  const ic = h(`<div class="modal-ic"><div class="not">Rötuşsuz ve rötuşlu (sizin elinizden çıkmış) aynı fotoğrafın çiftlerini ekleyin. Program renk ve ton tarzınızı öğrenir ve tek tıkla uygular. En az 2–3 çift önerilir.</div><div id="ciftler"></div><div class="satir"><button class="btn kucuk" id="cEkle">Çift ekle (önce rötuşsuz, sonra rötuşlu)</button></div><div class="alan"><label>Stil adı</label><input type="text" id="stAd" value="Hayal Medya"></div><div class="satir" style="justify-content:flex-end"><button class="btn ana" id="stOgr">Öğren</button></div></div>`);
  const ciftler = [];
  $("#cEkle", ic).onclick = async () => {
    const a = await api.pick_files(); if (!a?.length) return;
    const b = await api.pick_files(); if (!b?.length) return;
    ciftler.push([a[0], b[0]]);
    $("#ciftler", ic).append(h(`<div class="not">${ciftler.length}. ${esc(a[0].split(/[\\/]/).pop())} → ${esc(b[0].split(/[\\/]/).pop())}</div>`));
  };
  $("#stOgr", ic).onclick = async () => {
    if (!ciftler.length) return bildir("En az bir çift ekleyin.", true);
    const r = await cagir("learn_style", $("#stAd", ic).value || "Stil", ciftler);
    if (r.ok) { S.init.stiller = r.stiller; kapat(); bildir("Stil öğrenildi"); panelCiz(); }
  };
  modal("Stil öğren", ic);
}

async function modelLab() {
  const ml = ((await api.model_listesi()).modeller || []).filter(x => x.var && !x.kapali && x.key !== "vitmatte");
  S.modeller = (await api.model_listesi()).modeller || S.modeller;
  const sec = new Set(ml.filter(x => !x.agir).map(x => x.key));
  const ic = h(`<div class="modal-ic"><div class="not">Aynı fotoğraf seçtiğiniz modellerle ayrı ayrı ayrıştırılır ve beyaz, koyu, renkli zeminde yan yana gösterilir. Saç kenarındaki halelere, kopuk tellere ve kaybolan saça bakın. <b>Bunu kullan</b> ile seçtiğiniz model uygulanır.</div>
    <div class="lab-sec"></div>
    <div class="satir" style="justify-content:space-between"><label class="secim">Zeminler: <span class="zem"><span style="background:#fff"></span><span style="background:#23272F"></span><span style="background:#2E7D5B"></span></span></label><button class="btn ana" id="labCalis">Karşılaştır</button></div>
    <div class="lab-sonuc"></div></div>`);
  const kutu = $(".lab-sec", ic);
  ml.forEach(x => {
    const l = h(`<label class="secim lab-m" title="${esc(x.not)}"><span><b>${esc(x.ad)}</b> <small>${esc(x.lisans)}${x.ticari ? "" : " · ticari değil"}${x.agir ? " · ağır" : ""}</small></span><input type="checkbox" ${sec.has(x.key) ? "checked" : ""}></label>`);
    $("input", l).onchange = (e) => e.target.checked ? sec.add(x.key) : sec.delete(x.key);
    kutu.append(l);
  });
  if (ml.length < 2) kutu.append(h(`<div class="not">Karşılaştırmak için en az iki model gerekir. Ayarlar → Modeller bölümünden ek modelleri içe aktarın.</div>`));
  $("#labCalis", ic).onclick = async () => {
    if (!sec.size) { bildir("En az bir model seçin", true); return; }
    const so = $(".lab-sonuc", ic); so.innerHTML = `<div class="not">Hesaplanıyor… (model başına birkaç saniye; ağır modeller daha uzun sürer)</div>`;
    const r = await cagir("model_karsilastir", S.cur, S.fid, [...sec]);
    so.innerHTML = "";
    if (!r.ok) return;
    r.sonuclar.forEach(x => {
      const k = h(`<div class="lab-kart ${r.oneri === x.key ? "oneri" : ""}"><div class="lab-b"><b>${esc(x.ad)}</b>${r.oneri === x.key ? `<span class="rozet">Önerilen (uzlaşı)</span>` : ""}${x.ticari === false ? `<span class="rozet gri">Ticari değil</span>` : ""}</div></div>`);
      if (x.hata) { k.append(h(`<div class="not">Çalışmadı: ${esc(x.hata)}</div>`)); so.append(k); return; }
      const sr = h(`<div class="lab-resim"></div>`); x.gorseller.forEach(g => sr.append(h(`<img src="${g}" alt="${esc(x.ad)}">`))); k.append(sr);
      k.append(h(`<div class="not">${x.sure} sn · belirsiz kenar %${x.belirsiz}</div>`));
      const b = h(`<button class="btn kucuk">Bunu kullan</button>`);
      b.onclick = async () => { kapat(); const q = await cagir("matte", S.cur, S.fid, {model: x.key}, true); if (q.ok) { S.st = q; ciz(); } };
      k.append(b); so.append(k);
    });
    if (r.oneri) so.prepend(h(`<div class="not">Öneri, modellerin birbirine en yakın (uzlaşı) sonucuna göre verilir; mutlaka kendi gözünüzle de bakın.</div>`));
  };
  modal("Model Laboratuvarı", ic, true);
}

async function ayarlar(sekme = "genel") {
  S.ayar = await api.settings();
  const ic = h(`<div></div>`);
  const sek = h(`<div class="sekmeler"></div>`);
  [["genel", "Genel"], ["yazici", "Yazıcılar"], ["yonetici", "Yönetici"], ["modeller", "Modeller"], ["tasima", "Ayar taşıma"], ["kayit", "Hata kaydı"]].forEach(([k, a]) => {
    const b = h(`<button class="sekme ${k === sekme ? "secili" : ""}">${a}</button>`); b.onclick = () => ayarlar(k); sek.append(b);
  });
  ic.append(sek);
  const g = h(`<div class="modal-ic"></div>`);
  ic.append(g);
  const kaydetA = async (d, pw = "") => { const r = await cagir("update_settings", d, pw); if (r.ok) { S.ayar = r.ayarlar; } return r; };
  if (sekme === "genel") {
    g.append(h(`<div class="alan"><label>Varsayılan kayıt klasörü (boşsa her seferinde sorulur)</label><div class="satir"><input type="text" id="aKl" value="${esc(S.ayar.varsayilan_klasor)}"><button class="btn kucuk" id="aKlS">Seç…</button><button class="btn kucuk" id="aKlT">Temizle</button></div></div>`));
    g.append(h(`<div class="alan"><label>Kamera klasörü (yeni çekimler otomatik sıraya eklenir)</label><div class="satir"><input type="text" id="aKam" value="${esc(S.ayar.kamera_klasoru)}"><button class="btn kucuk" id="aKamS">Seç…</button></div></div>`));
    g.append(secim("ki", "Kamera klasörünü izle", S.ayar.kamera_izle, async v => { await kaydetA({kamera_izle: v}); kameraDurum(); }));
    g.append(secim("hm2", "Hızlı mod", S.ayar.hizli_mod, v => kaydetA({hizli_mod: v})));
    const gd = await api.gpu_durum();
    const gk = h(`<div class="bolum" style="border:1px solid var(--cizgi);border-radius:12px;padding:10px 12px"><h3>EKRAN KARTI</h3><div class="not" id="gpuYazi"></div></div>`);
    const gyaz = (d) => { $("#gpuYazi", gk).innerHTML = `Şu an kullanılan: <b>${esc(d.ad)}</b>. ${d.gpu_acik ? "Ekran kartı açık: uygun kart varsa (NVIDIA CUDA / DirectML) işlemler kartla yapılır." : "Ekran kartı KAPALI: tüm işlemler yalnızca işlemci (CPU) ile yapılır. Daha yavaştır ama sürücü sorunlarından etkilenmez."} Değişiklikte modeller yeniden yüklenir.`; };
    gyaz(gd);
    gk.append(secim("gpu1", "Ekran kartını kullan", gd.gpu_acik, async v => { const r = await cagir("gpu_ayarla", v); if (r.ad) { gyaz(r); S.ayar.gpu_kullan = v; bildir(v ? "Ekran kartı açıldı" : "Yalnızca işlemci modu"); } }));
    g.append(gk);
    g.append(secim("sb2", "Ölçeklemede şablonu göster", S.ayar.sablon_goster !== false, v => kaydetA({sablon_goster: v})));
    const ms = h(`<div class="alan"><label>Arka plan modeli</label><select><option value="auto">Otomatik</option><option value="birefnet">BiRefNet Portre</option><option value="isnet">ISNet</option><option value="u2net">U²-Net</option></select></div>`);
    $("select", ms).value = S.ayar.model || "auto"; $("select", ms).onchange = (e) => kaydetA({model: e.target.value});
    g.append(ms);
    $("#aKlS", g).onclick = async () => { const k = await api.pick_folder(S.ayar.varsayilan_klasor); if (k) { await kaydetA({varsayilan_klasor: k}); $("#aKl", g).value = k; } };
    $("#aKlT", g).onclick = async () => { await kaydetA({varsayilan_klasor: ""}); $("#aKl", g).value = ""; };
    $("#aKamS", g).onclick = async () => { const k = await api.pick_folder(S.ayar.kamera_klasoru); if (k) { await kaydetA({kamera_klasoru: k}); $("#aKam", g).value = k; kameraDurum(); } };
  } else if (sekme === "yazici") {
    const r = await api.printers();
    if (!r.yazicilar.length) g.append(h(`<div class="not">Yazıcı bulunamadı. Yazıcılar yalnızca Windows'ta listelenir.</div>`));
    g.append(h(`<div class="not"><b>Kurulum adımları:</b> 1) Sürücü ayarları → kağıt 10x15 / 6x4, kenarsız açık (Epson: genişletme en az). 2) Test sayfası yazdırın. 3) Cetvelleri gerçek cetvelle ölçüp aşağıya yazın: program ölçeği düzeltir. 4) Test sayfasını tekrar basıp kontrol edin.</div>`));
    r.yazicilar.forEach(y => {
      const pr = y.profil;
      const kart = h(`<div class="bolum" style="border:1px solid var(--cizgi);border-radius:12px"><h3>${esc(y.ad)} ${r.varsayilan === y.ad ? "<span style='color:var(--iyi)'>VARSAYILAN</span>" : ""}</h3>
        <div class="not">${esc(pr.not || "")}</div>
        <div class="satir"><button class="btn kucuk" data-k="v">Varsayılan yap</button><button class="btn kucuk" data-k="s">Sürücü ayarları…</button><button class="btn kucuk" data-k="t">Test sayfası yazdır</button><button class="btn kucuk" data-k="o">Test sayfasını gör</button></div>
        <div class="satir"><div class="alan" style="flex:1"><label>Yatay cetvel ölçümü (80 mm olmalı)</label><input type="number" step="0.1" placeholder="80"></div><div class="alan" style="flex:1"><label>Dikey cetvel ölçümü (120 mm olmalı)</label><input type="number" step="0.1" placeholder="120"></div><button class="btn kucuk" data-k="k" style="align-self:flex-end">Düzelt</button></div>
        <div class="not">Ölçek: yatay ${pr.olcek_x} · dikey ${pr.olcek_y} ${pr.serbest === false ? "· Serbest baskıda kullanılmaz" : ""}</div></div>`);
      const [ix, iy] = $$("input", kart);
      $$("button", kart).forEach(b => b.onclick = async () => {
        const k = b.dataset.k;
        if (k === "v") { await cagir("save_printer", y.ad, {}, true); S.ayar = await api.settings(); ayarlar("yazici"); }
        if (k === "s") { await cagir("printer_props", y.ad); }
        if (k === "t") { const x = await cagir("test_print", y.ad); if (x.ok) bildir("Test sayfası gönderildi"); }
        if (k === "o") { const x = await api.test_page_preview(); modal("Test sayfası", h(`<div class="modal-ic"><img src="${x.gorsel}" style="max-width:100%;background:#fff"></div>`)); }
        if (k === "k") { const x = await cagir("calibrate", y.ad, +ix.value || 0, +iy.value || 0); if (x.ok) { bildir("Ölçek düzeltildi"); ayarlar("yazici"); } }
      });
      g.append(kart);
    });
  } else if (sekme === "yonetici") {
    g.append(h(`<div class="not">Yönetici: <b>${esc(S.ayar.yonetici?.ad || "HAYDAR")}</b>. Bu bölümdeki ayarlar şifre ister.</div>`));
    g.append(h(`<div class="alan"><label>Güncel arşiv numarası</label><input type="number" id="yNo" value="${S.ayar.arsiv_no}"></div>`));
    g.append(h(`<div class="alan"><label>Yeni şifre (değiştirmek istemiyorsanız boş bırakın)</label><input type="password" id="yYeni"></div>`));
    g.append(h(`<div class="alan"><label>Yönetici şifresi</label><input type="password" id="yPw"></div>`));
    const b = h(`<div class="satir" style="justify-content:flex-end"><button class="btn ana">Kaydet</button></div>`);
    $("button", b).onclick = async () => {
      const d = {arsiv_no: +$("#yNo", g).value};
      if ($("#yYeni", g).value) d.yeni_sifre = $("#yYeni", g).value;
      const r = await kaydetA(d, $("#yPw", g).value);
      if (r.ok) { bildir("Yönetici ayarları kaydedildi"); S.bilgi.no = String(S.ayar.arsiv_no); S.bilgi._oto = true; kapat(); panelCiz(); }
    };
    g.append(b);
  } else if (sekme === "modeller") {
    const ml = (await api.model_listesi()).modeller || [];
    g.append(h(`<div class="not">Yapay zeka modelleri bu bilgisayarda çalışır, internet gerekmez. "Ek model paketi"ndeki .onnx dosyalarını <b>İçe aktar</b> ile ekleyin. Ticari olmayan lisanslı modellerin sorumluluğu kullanıcıya aittir.</div>`));
    const t = h(`<table class="liste"><thead><tr><th>Model</th><th>Lisans</th><th>Boyut</th><th>Durum</th><th></th></tr></thead><tbody></tbody></table>`);
    ml.forEach(x => {
      const tr = h(`<tr><td><b>${esc(x.ad)}</b><div class="not" style="margin:0">${esc(x.not)}</div></td><td>${esc(x.lisans)}${x.ticari ? "" : ` <span class="rozet gri">Ticari değil</span>`}</td><td>${x.var ? x.mb + " MB" : "—"}</td><td>${x.var ? (x.kapali ? "Kapalı" : "Hazır") : "Yüklü değil"}</td><td style="white-space:nowrap"></td></tr>`);
      const td = tr.lastElementChild;
      if (x.var) { const b = h(`<button class="btn kucuk">${x.kapali ? "Aç" : "Kapat"}</button>`); b.onclick = async () => { await api.model_kapat(x.key, !x.kapali); ayarlar("modeller"); }; td.append(b); }
      if (x.kaldirilabilir) { const b = h(`<button class="btn kucuk tehlike">Kaldır</button>`); b.onclick = async () => { await api.model_kaldir(x.key); ayarlar("modeller"); }; td.append(b); }
      $("tbody", t).append(tr);
    });
    g.append(t);
    const ib = h(`<div class="satir"><button class="btn ana">Model içe aktar (.onnx)…</button></div>`);
    $("button", ib).onclick = async () => { const r = await cagir("model_ice_aktar"); if (r.ok) { bildir(r.eklenen?.length ? "Eklendi: " + r.eklenen.join(", ") : "Dosya eklenmedi" + (r.taninmayan?.length ? " (tanınmadı: " + r.taninmayan.join(", ") + ")" : "")); ayarlar("modeller"); } };
    g.append(ib);
  } else if (sekme === "tasima") {
    g.append(h(`<div class="not">Profilleri, stilleri, yazıcı ve diğer ayarları tek dosyayla diğer bilgisayarlara taşıyın. Arşiv numarası taşınmaz.</div>`));
    const b = h(`<div class="satir"><button class="btn">Dışa aktar…</button><button class="btn">İçe aktar…</button></div>`);
    const [d, i] = $$("button", b);
    d.onclick = async () => { const r = await cagir("export_settings"); if (r.yol) bildir("Kaydedildi: " + r.yol); };
    i.onclick = () => metinSor("Yönetici şifresi", "", async (pw) => { const r = await cagir("import_settings", pw); if (r.ok && !r.iptal) { bildir("Ayarlar içe aktarıldı"); S.ayar = r.ayarlar; } }, true);
    g.append(b);
  } else {
    g.append(h(`<div class="not">Bir sorun olursa program günlük hata kaydı tutar. Klasörü açıp ilgili günün dosyasını gönderin; sorunun nedeni hızla bulunur.</div>`));
    const b = h(`<div class="satir"><button class="btn">Hata kayıtları klasörünü aç</button><button class="btn ana">Sorun bildir (rapor oluştur)</button></div>`);
    const [b1, b2] = $$("button", b);
    b1.onclick = () => api.open_logs();
    b2.onclick = async () => { const r = await cagir("sorun_bildir"); if (r.ok) bildir("Rapor masaüstüne kaydedildi: " + r.yol.split(/[\\/]/).pop()); };
    g.append(b);
    g.append(h(`<div class="not">Rapor; hata kayıtlarını, ayarları (şifresiz) ve ekran kartı bilgisini içerir. <b>Müşteri fotoğrafı içermez.</b> Oluşan zip dosyasını bana gönderin.</div>`));
  }
  modal("Ayarlar", ic);
}

async function arsiv(sekme = "arsiv", q = "") {
  const ic = h(`<div></div>`);
  const sek = h(`<div class="sekmeler"></div>`);
  [["arsiv", "Müşteri arşivi"], ["rapor", "Günlük rapor"]].forEach(([k, a]) => { const b = h(`<button class="sekme ${k === sekme ? "secili" : ""}">${a}</button>`); b.onclick = () => arsiv(k); sek.append(b); });
  ic.append(sek);
  const g = h(`<div class="modal-ic"></div>`); ic.append(g);
  if (sekme === "arsiv") {
    const ara = h(`<input type="text" placeholder="Arşiv no veya müşteri adı ile ara" value="${esc(q)}">`);
    ara.onkeydown = (e) => { if (e.key === "Enter") arsiv("arsiv", ara.value); };
    g.append(ara);
    const r = await api.archive(q);
    const t = h(`<table class="liste"><thead><tr><th>No</th><th>Müşteri</th><th>Tür</th><th>Adet</th><th>Tarih</th><th></th></tr></thead><tbody></tbody></table>`);
    r.kayitlar.forEach(k => {
      const tr = h(`<tr><td>${esc(k.no)}</td><td>${esc(k.musteri || "—")}</td><td>${esc(k.tur)}</td><td>${k.adet}</td><td>${esc((k.tarih || "").replace("T", " ").slice(0, 16))}</td><td style="white-space:nowrap"><button class="btn kucuk">Klasör</button> <button class="btn kucuk">Yeniden bas</button></td></tr>`);
      const [kl, yb] = $$("button", tr);
      kl.onclick = () => api.open_folder(k.klasor);
      yb.onclick = async () => { const x = await cagir("reprint", k._i); if (x.ok) bildir("Yazıcıya gönderildi"); };
      $("tbody", t).append(tr);
    });
    if (!r.kayitlar.length) g.append(h(`<div class="not">Kayıt bulunamadı.</div>`)); else g.append(t);
  } else {
    const r = await api.report("");
    g.append(h(`<div class="ozet"><span class="b" style="background:var(--vurgu)">${r.toplam_is}</span><div><div style="font-weight:700">${esc(r.gun)} · ${r.toplam_is} iş · ${r.toplam_adet} fotoğraf</div><div class="not">Bugün kaydedilen işler</div></div></div>`));
    const t = h(`<table class="liste"><thead><tr><th>Tür</th><th>İş</th><th>Fotoğraf</th><th>Basılan</th></tr></thead><tbody></tbody></table>`);
    Object.entries(r.turler).forEach(([k, v]) => $("tbody", t).append(h(`<tr><td>${esc(k)}</td><td>${v.is}</td><td>${v.adet}</td><td>${v.baski}</td></tr>`)));
    g.append(t);
  }
  const alt = h(`<div class="satir" style="justify-content:flex-end;margin-top:12px"><button class="btn tehlike">Arşivi ve raporu sıfırla…</button></div>`);
  $("button", alt).onclick = () => arsivSifirla();
  ic.append(alt);
  modal("Arşiv ve rapor", ic, true);
}

function arsivSifirla() {
  const ic = h(`<div class="modal-ic"><div class="not">Müşteri arşivi ve günlük rapor kayıtları <b>silinir</b>. Güvenlik için silmeden önce bilgisayarda yedek dosyası alınır. Arşiv numarası kaldığı yerden devam eder. Devam etmek için yönetici adı ve şifresi gerekir.</div>
    <div class="alan"><label>Yönetici adı</label><input type="text" id="sAd" autocomplete="off"></div>
    <div class="alan"><label>Yönetici şifresi</label><input type="password" id="sPw" autocomplete="off"></div>
    <div class="not" id="sHata" style="color:#ff8a80"></div>
    <div class="satir" style="justify-content:flex-end"><button class="btn">Vazgeç</button><button class="btn tehlike">Sıfırla</button></div></div>`);
  const [v, t] = $$("button", ic);
  v.onclick = () => arsiv();
  t.onclick = async () => {
    const r = await api.arsiv_sifirla($("#sAd", ic).value, $("#sPw", ic).value);
    if (r.ok) { kapat(); bildir(r.silinen ? `${r.silinen} kayıt silindi (yedek alındı)` : "Silinecek kayıt yoktu"); }
    else $("#sHata", ic).textContent = r.hata || "İşlem yapılamadı";
  };
  $("#sPw", ic).onkeydown = (e) => { if (e.key === "Enter") t.click(); };
  modal("Arşivi sıfırla", ic);
  setTimeout(() => $("#sAd", ic).focus(), 50);
}

function hakkinda() {
  const logo = document.documentElement.dataset.tema === "acik" ? "assets/logo_black.png" : "assets/logo_white.png";
  const ic = h(`<div><div class="hakkinda-logo"><img src="${logo}" alt="Hayal Medya"><div style="font-size:24px;font-weight:700">Vesikalık Pro <span style="font-size:13px;background:var(--vurgu);color:var(--vurgu-yazi);padding:3px 9px;border-radius:7px;vertical-align:middle">Sürüm ${esc(S.init.surum)}</span></div>
    <div style="font-weight:700;letter-spacing:.03em">HAYDAR ALTINSABAN yapımıdır · Tüm hakları saklıdır</div>
    <div class="not">HAYAL MEDYA · 0312 264 0 888 &nbsp;·&nbsp; Haydar Altınsaban · 0554 990 49 59</div></div>
    <div class="modal-ic">
    <h3 style="margin:0;font-size:13px;color:var(--soluk);letter-spacing:.08em">SÜRÜM NOTLARI · 1.4</h3>
    <ul class="not" style="margin:0;padding-left:18px;line-height:1.7;color:var(--yazi)">
      <li><b>Yeni (1.4):</b> Açılış animasyonu ve tek pencere kilidi: çift tıklayınca hemen yükleniyor penceresi görünür, tekrar tıklamak gerekmez, uygulama bir kez açılır.</li>
      <li><b>Yeni (1.4):</b> Manuel rötuş ekranı (klon damgası, yama, nokta iyileştirme, cilt yumuşatma) ve manuel dekupe · saç ekranı (saç fırçası, ekle, sil, yumuşat, keskinleştir, daralt, genişlet). Her vuruş anında görünür.</li>
      <li><b>Yeni (1.4):</b> Sade, yana kaydırılabilir araç çubukları ve fareyle ipucu balonları; vesikalık baskıda "Sayfa kopyası" kaldırıldı.</li>
      <li><b>Yeni (1.3):</b> Model Laboratuvarı: arka plan modellerini (BiRefNet Portre/Matting/HR Matting/Genel, BEN2, isteğe bağlı RMBG-2.0 ve ViTMatte) aynı fotoğrafta beyaz, koyu ve renkli zeminde yan yana karşılaştırın; "uzlaşı" önerisi; Ayarlar → Modeller (içe aktar, kapat, kaldır, lisans etiketi).</li>
      <li><b>Yeni (1.3):</b> Gelişmiş portre rötuşu (ten örneğine göre 3 ölçekli yumuşatma), klon damgası, keskinleştirme (Unsharp Mask), Şekillendir (it/çek, şişir, küçült, otomatik omuz hizalama; yüz kilitli).</li>
      <li><b>Yeni (1.3):</b> HEIC, AVIF, WebP, TIFF, şeffaf PNG ve kamera RAW (NEF, DNG, CR2, ARW…) girdileri; ayar çubuklarında ◄ ► hassas ok düğmeleri; degrade renk takas düğmesi; arşiv ve raporu sıfırlama (yönetici adı + şifre, yedekli); Sorun bildir; baskı öncesi son kontrol.</li>
      <li><b>Yeni (1.2):</b> saç tipi modları (kıvırcık, dalgalı, düz, kısa, örtülü) ve saça yakınlaşma; rötuşta kirpik, kaş, bıyık, sakal, burun delikleri koruması, koruma haritası, yüzdelik “geri al” fırçası, koruma fırçası, güvenli rötuş sınırı; leke işaretlerini silme (Delete / sağ tık).</li>
      <li><b>Yeni (1.2):</b> Polaroid (Instax Square) ve Serbest Baskı modülleri aktif; toplu işlem; müşteri ayar belleği; gerçek boyutlu baskı önizlemesi; ayarlarda ekran kartı aç/kapat (yalnız işlemci modu).</li>
      <li><b>Arka plan silme:</b> BiRefNet ile saç tellerine kadar ayırma, gri hale temizliği, tıklayarak düzeltme (Segment Anything) ve fırçalar.</li>
      <li><b>Fonlar:</b> biyometrik/vize için kurala uygun beyaz; vesikalıkta orijinal fon, 12 degrade fon ve degrade ayarları.</li>
      <li><b>Yüz temizleme:</b> yüz bölgeleme ile yalnız cilde rötuş, LaMa ile doğal leke onarımı, gözlük yansıması temizleme, göz altı, göz-diş beyazlatma, stil öğrenme, profiller.</li>
      <li><b>Ölçekleme:</b> Hayal Medya örneklerinden ölçülmüş şablonlar, kılavuz çizgileri, şablon görseli, elle ölçek-eğim-kaydırma.</li>
      <li><b>Uygunluk raporu:</b> göz, ağız, baş dönüklüğü ve eğikliği, baş ölçüsü, ışık dengesi, pozlama, netlik, kırmızı göz, gözlük.</li>
      <li><b>Baskı:</b> 10x15 referans dizimleri, yazıcı profilleri, test sayfası ve ölçek düzeltme, Kaydet ve Yazdır.</li>
      <li><b>Arşiv:</b> arşiv numaralı dosya adları, müşteri arşivi ve yeniden baskı, günlük rapor, online başvuru çıktısı.</li>
      <li><b>Yönetim:</b> yönetici kilidi, hızlı mod, kamera klasörü izleme, ayar taşıma, hata kaydı, kısayol rehberi.</li>
    </ul>
    <h3 style="margin:0;font-size:13px;color:var(--soluk);letter-spacing:.08em">YAPAY ZEKA MODELLERİ · BİLGİSAYARDA, İNTERNETSİZ</h3>
    <table class="liste"><tbody>
      <tr><td><b>BiRefNet Portre</b></td><td>Arka plan</td><td>MIT</td></tr><tr><td><b>ISNet / U²-Net</b></td><td>Arka plan (yedek)</td><td>Apache 2.0</td></tr>
      <tr><td><b>EfficientSAM</b></td><td>Tıkla-düzelt</td><td>Apache 2.0</td></tr><tr><td><b>LaMa</b></td><td>Leke ve yansıma onarımı</td><td>Apache 2.0</td></tr>
      <tr><td><b>Yüz bölgeleme (BiSeNet)</b></td><td>Cilt, göz, dudak, saç</td><td>MIT</td></tr><tr><td><b>YuNet</b></td><td>Yüz bulma</td><td>MIT</td></tr></tbody></table>
    <div class="not">Donanım: ${esc(S.st?.donanim || "ilk işlemde belirlenir")}</div></div></div>`);
  modal("Hakkında", ic);
}

function kisayollar() {
  const satir = (k, a) => `<tr><td style="white-space:nowrap">${k}</td><td>${a}</td></tr>`;
  const ic = h(`<div class="modal-ic"><div class="not">Programı hızlı kullanmak için kısayollar ve ne işe yaradıkları:</div><table class="liste"><tbody>
    ${satir("<kbd>Ctrl</kbd>+<kbd>O</kbd>", "Fotoğraf ekle. Klasör de seçilebilir; fotoğraflar sıraya girer.")}
    ${satir("<kbd>Enter</kbd> / <kbd>→</kbd> (adım çubuğu)", "Sonraki adıma geç. Arka plan, rötuş ve ölçek otomatik hazırlanır.")}
    ${satir("<kbd>Ctrl</kbd>+<kbd>Z</kbd>", "Arka planda son düzeltmeyi, ölçeklemede kadrajı geri alır.")}
    ${satir("<kbd>A</kbd>", "Arka plan · Akıllı seçim: tıkladığınız bölgeyi kişiye ekler.")}
    ${satir("<kbd>S</kbd>", "Arka plan · Akıllı seçim: tıkladığınız bölgeyi fon sayar (siler).")}
    ${satir("<kbd>B</kbd> / <kbd>E</kbd>", "Arka plan · Fırça ile ekle / sil. <kbd>[</kbd> <kbd>]</kbd> fırça boyutu.")}
    ${satir("<kbd>M</kbd>", "Arka plan · Sonuç ↔ maske görünümü.")}
    ${satir("<kbd>Boşluk</kbd> + sürükle", "Görüntüyü kaydır. Fare tekerleği: yakınlaştır.")}
    ${satir("<kbd>L</kbd>", "Rötuş · Leke fırçası: tıklanan yeri temizler, bulunmuş lekeye tıklarsanız işareti kaldırır.")}
    ${satir("<kbd>G</kbd> / <kbd>P</kbd>", "Rötuş · Geri al fırçası (yüzdelik) / Koruma fırçası. <kbd>[</kbd> <kbd>]</kbd> fırça boyutu.")}
    ${satir("<kbd>K</kbd>", "Rötuş · Koruma haritasını göster (kirpik, kaş, bıyık, burun delikleri yeşil).")}
    ${satir("<kbd>Delete</kbd> / sağ tık", "Rötuş · Seçili leke işaretini sil (işarete tıklayıp seçin).")}
    ${satir("<kbd>↑</kbd><kbd>↓</kbd><kbd>←</kbd><kbd>→</kbd>", "Ölçekleme · Fotoğrafı 0,1 mm kaydır (Shift ile 1 mm).")}
    ${satir("<kbd>+</kbd> / <kbd>-</kbd>", "Ölçekleme · Büyüt / küçült (%1).")}
    ${satir("<kbd>[</kbd> / <kbd>]</kbd>", "Ölçekleme · Eğim ver (0,5°).")}
    ${satir("<kbd>T</kbd>", "Ölçekleme · Şablonu göster / gizle.")}
    ${satir("<kbd>Ctrl</kbd>+<kbd>S</kbd>", "Baskı · Sadece kaydet. <kbd>Ctrl</kbd>+<kbd>P</kbd>: Kaydet ve yazdır.")}
    ${satir("<kbd>F1</kbd> <kbd>F2</kbd> <kbd>F3</kbd>", "Bu rehber · Ayarlar · Arşiv ve rapor.")}
    </tbody></table></div>`);
  modal("Kısayol rehberi", ic, true);
}

// ------------------------------------------------------------------ kamera klasörü
function kameraDurum() {
  const on = S.ayar.kamera_izle && S.ayar.kamera_klasoru;
  $("#kameraDurum .nokta").className = "nokta " + (on ? "iyi" : "");
  $("#kameraYazi").textContent = on ? "Kamera klasörü izleniyor" : "Kamera klasörü kapalı";
}
async function kameraYokla() {
  if (!S.ayar.kamera_izle || !S.ayar.kamera_klasoru || mesgul) return;
  const r = await api.poll_camera();
  if (r && r.yeni && r.yeni.length) { ekle(r.yeni); bildir(`${r.yeni.length} yeni çekim sıraya eklendi`); }
}

// ------------------------------------------------------------------ olaylar
$("#btnEkle").onclick = dosyaEkle;
$("#btnAyar").onclick = () => ayarlar();
$("#btnArsiv").onclick = () => arsiv();
$("#btnHakkinda").onclick = hakkinda;
$("#btnKisayol").onclick = kisayollar;
$("#btnGeriAl").onclick = geriAl;
$("#btnTema").onclick = async () => { const t = document.documentElement.dataset.tema === "koyu" ? "acik" : "koyu"; temaUygula(t); S.ayar.tema = t; await api.update_settings({tema: t}); };

document.addEventListener("dragover", (e) => { e.preventDefault(); $(".birak")?.classList.add("ustunde"); });
document.addEventListener("dragleave", () => $(".birak")?.classList.remove("ustunde"));
document.addEventListener("drop", async (e) => {
  e.preventDefault(); $(".birak")?.classList.remove("ustunde");
  const files = [...e.dataTransfer.files];
  const yollar = files.map(f => f.pywebviewFullPath).filter(Boolean);
  if (yollar.length) return yollaEkle(yollar);
  for (const f of files) {
    const data = await new Promise(res => { const r = new FileReader(); r.onload = () => res(r.result); r.readAsDataURL(f); });
    ekle(await cagir("add_upload", f.name, data));
  }
});

document.addEventListener("keydown", (e) => {
  if (e.target.matches("input,select,textarea")) return;
  if (e.code === "Space") { bosluk = true; e.preventDefault(); }
  const k = e.key;
  if (k === "F1") { e.preventDefault(); kisayollar(); }
  if (k === "F2") { e.preventDefault(); ayarlar(); }
  if (k === "F3") { e.preventDefault(); arsiv(); }
  if (k === "Escape") kapat();
  if (e.ctrlKey && k.toLowerCase() === "o") { e.preventDefault(); dosyaEkle(); }
  if (e.ctrlKey && k.toLowerCase() === "z") { e.preventDefault(); geriAl(); }
  if (mesgul || !$("#modal").classList.contains("gizli")) return;
  if (k === "Enter" && S.adim < 4) adimaGit(S.adim + 1);
  if (S.adim === 1) {
    const m = {a: "sam+", s: "sam-", b: "firca+", e: "firca-", h: "kaydir"}[k.toLowerCase()];
    if (m) { S.arac = m; sahneCiz(); }
    if (k === "[") { S.firca = Math.max(6, S.firca - 6); } if (k === "]") { S.firca = Math.min(160, S.firca + 6); }
    if (k.toLowerCase() === "m") { gorunumYenile(S.gorunum === "maske" ? "sonuc" : "maske").then(sahneCiz); }
  }
  if (S.adim === 2) {
    const kk = k.toLowerCase();
    const m = {l: "l", g: "g", p: "p", c: "k", s: "n", t: "t", m: "m", b: "b", z: "z"}[kk];
    if (m) { S.rArac = (S.rArac === m && m !== "k") ? "k" : m; sahneCiz(); }
    if (kk === "k") { S.rGor = S.rGor === "koruma" ? "sonuc" : "koruma"; S.st.gorsel_koruma = null; sahneCiz(); }
    if (k === "Delete" || k === "Backspace") { e.preventDefault(); S.silLeke && S.silLeke(); }
    if (k === "[") { S.firca = Math.max(6, S.firca - 6); sahneCiz(); } if (k === "]") { S.firca = Math.min(160, S.firca + 6); sahneCiz(); }
  }
  if (S.adim === 3) {
    const g = S.st.geom, st = e.shiftKey ? 1 : 0.1;
    const d = {ArrowLeft: {dx: +(g.dx - st).toFixed(2)}, ArrowRight: {dx: +(g.dx + st).toFixed(2)}, ArrowUp: {dy: +(g.dy - st).toFixed(2)}, ArrowDown: {dy: +(g.dy + st).toFixed(2)},
      "+": {zoom: +(g.zoom * 1.01).toFixed(4)}, "-": {zoom: +(g.zoom * 0.99).toFixed(4)}, "[": {rot: +(g.rot - 0.5).toFixed(2)}, "]": {rot: +(g.rot + 0.5).toFixed(2)}}[k];
    if (d) { e.preventDefault(); geomDegis(d); }
    if (k.toLowerCase() === "t") { S.ayar.sablon_goster = S.ayar.sablon_goster === false; api.update_settings({sablon_goster: S.ayar.sablon_goster}); sahneCiz(); panelCiz(); }
  }
  if (S.adim === 4 && e.ctrlKey && k.toLowerCase() === "s") { e.preventDefault(); kaydet(false); }
  if (S.adim === 4 && e.ctrlKey && k.toLowerCase() === "p") { e.preventDefault(); kaydet(true); }
});
document.addEventListener("keyup", (e) => { if (e.code === "Space") bosluk = false; });


// ------------------------------------------------------------------ ipucu balonu (tüm düğmelerde) ve araç çubuğu kaydırma
(function () {
  const ip = document.createElement("div"); ip.className = "ipucu"; document.body.appendChild(ip);
  let t = null, hedef = null;
  const gizle = () => { clearTimeout(t); hedef = null; ip.classList.remove("acik"); };
  document.addEventListener("mouseover", (e) => {
    const el = e.target.closest && e.target.closest("[title],[data-ip]");
    if (!el || el === hedef) return;
    if (el.hasAttribute("title")) { el.dataset.ip = el.getAttribute("title"); el.removeAttribute("title"); }
    if (!el.dataset.ip) return;
    gizle(); hedef = el;
    t = setTimeout(() => {
      ip.textContent = el.dataset.ip; ip.classList.add("acik");
      const r = el.getBoundingClientRect(), w = ip.offsetWidth, h = ip.offsetHeight;
      let x = Math.min(window.innerWidth - w - 8, Math.max(8, r.left + r.width / 2 - w / 2));
      let y = r.bottom + 10; if (y + h > window.innerHeight - 8) y = r.top - h - 10;
      ip.style.left = x + "px"; ip.style.top = y + "px";
    }, 280);
  });
  document.addEventListener("mouseout", (e) => { if (hedef && !(e.relatedTarget && hedef.contains(e.relatedTarget))) gizle(); });
  document.addEventListener("mousedown", gizle, true);
  document.addEventListener("wheel", (e) => {
    const bar = e.target.closest && e.target.closest(".araclar");
    if (bar && bar.scrollWidth > bar.clientWidth && Math.abs(e.deltaY) > Math.abs(e.deltaX)) { bar.scrollLeft += e.deltaY; e.preventDefault(); e.stopPropagation(); }
  }, {passive: false, capture: true});
})();
