// Manuel düzenleme ekranları (Photoshop benzeri, anlık): Rötuş (klon / yama / nokta iyileştirme / yumuşatma)
// ve Dekupe-Saç (saç fırçası / ekle / sil / yumuşat / keskin / daralt / genişlet).
// Ekrana girerken veri BİR KEZ yüklenir; sonrası tamamen tarayıcıda çalışır, her vuruş anında görünür.
// "Uygula" sonucu motora tek seferde gönderir; "İptal" hiçbir şeyi değiştirmez.

const MV = {};

function mvResim(src) {
  return new Promise((ok, hata) => { const im = new Image(); im.onload = () => ok(im); im.onerror = hata; im.src = src; });
}
const mvKelep = (v, a, b) => v < a ? a : v > b ? b : v;
const mvSmooth = (e0, e1, x) => { const t = mvKelep((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t); };

async function manuelAc(mod) {
  if (!S.cur || MV.acik) return;
  const r = await cagir("manuel_ac", S.cur, S.fid, mod);
  if (!r.ok) return;
  const img = await mvResim(r.gorsel);
  const W = r.w, H = r.h;
  const M = MV.m = {mod, W, H, zoom: 1, tx: 0, ty: 0, arac: mod === "rotus" ? "klon" : "sac", boyut: Math.max(20, Math.round(W / 60)),
    sert: 50, guc: mod === "rotus" ? 100 : 60, doku: 35, hizali: true, akis: 100, yMod: "kaynak", yay: 3, kaynak: null, ofs: null, gecmis: [], ileri: [], onceMi: false,
    gorunum: "beyaz", tasma: 80, bosluk: false, sel: null, kirli: false};
  MV.acik = true;

  // ---- DOM
  const kok = h(`<div class="mv" id="mv">
    <div class="mv-ust"><b class="mv-baslik">${mod === "rotus" ? "Manuel rötuş" : "Manuel dekupe · saç"}</b><div class="mv-ayarlar" id="mvAyar"></div>
      <div class="mv-btnler"><button class="btn" id="mvIptal" title="Yaptıklarınızı atıp çık">İptal</button><button class="btn ana" id="mvUygula" title="Düzenlemeleri fotoğrafa uygula ve çık">Uygula</button></div></div>
    <div class="mv-govde"><div class="mv-sol" id="mvSol"></div>
      <div class="mv-alan" id="mvAlan"><div class="mv-sahne" id="mvSahne"></div><div class="mv-imlec" id="mvImlec"></div><svg class="mv-sel" id="mvSel"></svg></div>
      <div class="mv-sag" id="mvSag"></div></div>
    <div class="mv-alt"><span id="mvDurum"></span><span id="mvIpucu"></span></div></div>`);
  document.body.appendChild(kok);
  const alan = $("#mvAlan", kok), sahne = $("#mvSahne", kok), imlec = $("#mvImlec", kok), selSvg = $("#mvSel", kok);

  // ---- tuvaller
  const cv = document.createElement("canvas"); cv.width = W; cv.height = H; sahne.appendChild(cv);
  const cx = cv.getContext("2d", {willReadFrequently: true});
  const tmp = document.createElement("canvas"); tmp.width = W; tmp.height = H;
  tmp.getContext("2d").drawImage(img, 0, 0);
  const orig = tmp.getContext("2d", {willReadFrequently: true}).getImageData(0, 0, W, H);   // rötuş: Wr; dekupe: W
  const wd = new ImageData(new Uint8ClampedArray(orig.data), W, H);                        // üzerinde çalışılan
  let A = null, A0 = null, plB = null, plF = null;
  if (mod === "dekupe") {
    const ai = await mvResim(r.alfa);
    const ac = document.createElement("canvas"); ac.width = W; ac.height = H; const actx = ac.getContext("2d", {willReadFrequently: true}); actx.drawImage(ai, 0, 0);
    const ad = actx.getImageData(0, 0, W, H).data; A = new Uint8Array(W * H); for (let i = 0; i < W * H; i++) A[i] = ad[i * 4];
    A0 = new Uint8Array(A);
    const plaka = async (src) => { const pi = await mvResim(src); const c = document.createElement("canvas"); c.width = W; c.height = H; const x = c.getContext("2d", {willReadFrequently: true}); x.imageSmoothingEnabled = true; x.imageSmoothingQuality = "high"; x.drawImage(pi, 0, 0, W, H); return x.getImageData(0, 0, W, H).data; };
    plB = await plaka(r.plaka_b); plF = await plaka(r.plaka_f);
  }
  let bulanik = null, bulanikB = null;
  if (mod === "rotus") {   // cilt yumuşatma fırçası için bir kez hesaplanan alçak geçirgen kopya
    const bc = document.createElement("canvas"); bc.width = W; bc.height = H; const bx = bc.getContext("2d", {willReadFrequently: true});
    bx.filter = `blur(${Math.max(3, Math.round(W / 420))}px)`; bx.drawImage(tmp, 0, 0); bx.filter = "none";
    bulanik = bx.getImageData(0, 0, W, H).data;
    const b2 = document.createElement("canvas"); b2.width = W; b2.height = H; const b2x = b2.getContext("2d", {willReadFrequently: true});
    b2x.filter = `blur(${Math.max(6, Math.round(W / 180))}px)`; b2x.drawImage(tmp, 0, 0); b2x.filter = "none";
    bulanikB = b2x.getImageData(0, 0, W, H).data;
  }
  const cov = new Float32Array(W * H);

  // ---- görünüm (yakınlaştırma / kaydırma)
  const uygula = () => { sahne.style.transform = `translate(${M.tx}px,${M.ty}px) scale(${M.zoom})`; $("#mvDurum", kok).textContent = `%${Math.round(M.zoom * 100)} · ${W}×${H}px`; selCiz(); haritaCiz(); };
  const sigdir = () => { const ar = alan.getBoundingClientRect(); M.zoom = Math.min(ar.width / W, ar.height / H) * 0.96; M.tx = (ar.width - W * M.zoom) / 2; M.ty = (ar.height - H * M.zoom) / 2; uygula(); };
  const noktaya = (e) => { const ar = alan.getBoundingClientRect(); return [(e.clientX - ar.left - M.tx) / M.zoom, (e.clientY - ar.top - M.ty) / M.zoom]; };
  alan.addEventListener("wheel", (e) => {
    e.preventDefault();
    const ar = alan.getBoundingClientRect(), mx = e.clientX - ar.left, my = e.clientY - ar.top;
    const z = mvKelep(M.zoom * (e.deltaY < 0 ? 1.15 : 1 / 1.15), 0.05, 12);
    M.tx = mx - (mx - M.tx) * z / M.zoom; M.ty = my - (my - M.ty) * z / M.zoom; M.zoom = z; uygula();
  }, {passive: false});

  // ---- çizim yardımcıları
  const goster = (x0, y0, w, h) => { x0 = Math.max(0, x0 | 0); y0 = Math.max(0, y0 | 0); w = Math.min(W - x0, w | 0); h = Math.min(H - y0, h | 0); if (w > 0 && h > 0) cx.putImageData(M.onceMi ? orig : wd, 0, 0, x0, y0, w, h); };
  const fircaA = (d, r, sert) => { if (d >= r) return 0; const ic = r * sert / 100; if (d <= ic) return 1; return mvSmooth(0, 1, 1 - (d - ic) / Math.max(0.001, r - ic)); };

  // dekupe: bölge yeniden boyama
  const arkaRenk = () => ({beyaz: [255, 255, 255], koyu: [35, 39, 47], renkli: [46, 125, 91]}[M.gorunum] || [255, 255, 255]);
  const boyaDekupe = (x0, y0, w, h) => {
    x0 = Math.max(0, x0 | 0); y0 = Math.max(0, y0 | 0); w = Math.min(W - x0, w | 0); h = Math.min(H - y0, h | 0);
    const d = wd.data, o = orig.data, bg = arkaRenk(), k = M.tasma / 100, mod_ = M.gorunum;
    for (let y = y0; y < y0 + h; y++) for (let x = x0; x < x0 + w; x++) {
      const i = y * W + x, p = i * 4, a = A[i] / 255;
      if (M.onceMi || mod_ === "once") { d[p] = o[p]; d[p + 1] = o[p + 1]; d[p + 2] = o[p + 2]; d[p + 3] = 255; continue; }
      if (mod_ === "maske") { d[p] = d[p + 1] = d[p + 2] = A[i]; d[p + 3] = 255; continue; }
      if (mod_ === "kirmizi") { const f = 0.55 * (1 - a); d[p] = o[p] * (1 - f) + 255 * f; d[p + 1] = o[p + 1] * (1 - f); d[p + 2] = o[p + 2] * (1 - f); d[p + 3] = 255; continue; }
      let fr = o[p], fg = o[p + 1], fb = o[p + 2];
      if (a > 0.02 && a < 0.995 && k > 0) {   // kenar rengi: eski fon payını çıkar
        const ia = 1 / a, ib = 1 - a;
        const cr = mvKelep((fr - ib * plB[p]) * ia, 0, 255), cg = mvKelep((fg - ib * plB[p + 1]) * ia, 0, 255), cb = mvKelep((fb - ib * plB[p + 2]) * ia, 0, 255);
        fr += (cr - fr) * k; fg += (cg - fg) * k; fb += (cb - fb) * k;
      }
      d[p] = fr * a + bg[0] * (1 - a); d[p + 1] = fg * a + bg[1] * (1 - a); d[p + 2] = fb * a + bg[2] * (1 - a); d[p + 3] = 255;
    }
  };
  const tumuBoya = () => { if (mod === "dekupe") boyaDekupe(0, 0, W, H); cx.putImageData(M.onceMi && mod === "rotus" ? orig : wd, 0, 0); };
  tumuBoya();

  // ---- geçmiş
  let snap = null, kirli = null;
  const dikdortgenGenislet = (x, y, w, h) => { if (!kirli) kirli = [x, y, x + w, y + h]; else { kirli[0] = Math.min(kirli[0], x); kirli[1] = Math.min(kirli[1], y); kirli[2] = Math.max(kirli[2], x + w); kirli[3] = Math.max(kirli[3], y + h); } };
  const darbeBasla = () => {
    kirli = null;
    snap = mod === "rotus" ? new Uint8ClampedArray(wd.data) : new Uint8Array(A);
  };
  const darbeBitir = () => {
    if (!kirli) { snap = null; return; }
    const [a, b, c, d] = kirli.map((v, i) => Math.max(0, Math.min(i % 2 ? H : W, v | 0)));
    const w = c - a, hh = d - b; if (w <= 0 || hh <= 0) { snap = null; return; }
    const once = mod === "rotus" ? new Uint8ClampedArray(w * hh * 4) : new Uint8Array(w * hh), sonra = mod === "rotus" ? new Uint8ClampedArray(w * hh * 4) : new Uint8Array(w * hh);
    for (let y = 0; y < hh; y++) {
      if (mod === "rotus") { once.set(snap.subarray(((b + y) * W + a) * 4, ((b + y) * W + a + w) * 4), y * w * 4); sonra.set(wd.data.subarray(((b + y) * W + a) * 4, ((b + y) * W + a + w) * 4), y * w * 4); }
      else { once.set(snap.subarray((b + y) * W + a, (b + y) * W + a + w), y * w); sonra.set(A.subarray((b + y) * W + a, (b + y) * W + a + w), y * w); }
    }
    M.gecmis.push({x: a, y: b, w, h: hh, once, sonra}); if (M.gecmis.length > 60) M.gecmis.shift();
    M.ileri = []; M.kirli = true; snap = null; kirli = null;
    for (let y = b; y < d; y++) cov.fill(0, y * W + a, y * W + c);
    gecmisCiz(); haritaCiz();
  };
  const kaydirGecmis = (g, ileri) => {
    const veri = ileri ? g.sonra : g.once;
    for (let y = 0; y < g.h; y++) {
      if (mod === "rotus") wd.data.set(veri.subarray(y * g.w * 4, (y + 1) * g.w * 4), ((g.y + y) * W + g.x) * 4);
      else A.set(veri.subarray(y * g.w, (y + 1) * g.w), (g.y + y) * W + g.x);
    }
    if (mod === "dekupe") boyaDekupe(g.x, g.y, g.w, g.h);
    goster(g.x, g.y, g.w, g.h);
  };
  const geriAl = () => { const g = M.gecmis.pop(); if (!g) return; kaydirGecmis(g, false); M.ileri.push(g); gecmisCiz(); };
  const ileriAl = () => { const g = M.ileri.pop(); if (!g) return; kaydirGecmis(g, true); M.gecmis.push(g); gecmisCiz(); };

  // ---- araçlar (rötuş)
  const klonNokta = (px, py) => {
    const r = M.boyut / 2, d = wd.data, s = snap, op = M.guc / 100;
    const x0 = Math.max(0, Math.floor(px - r)), x1 = Math.min(W, Math.ceil(px + r) + 1), y0 = Math.max(0, Math.floor(py - r)), y1 = Math.min(H, Math.ceil(py + r) + 1);
    const ox = M.ofs[0], oy = M.ofs[1];
    for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
      const a = fircaA(Math.hypot(x - px, y - py), r, M.sert); if (a <= 0) continue;
      const i = y * W + x; cov[i] += (1 - cov[i]) * a * (M.akis / 100);
      const sx = Math.round(x + ox), sy = Math.round(y + oy); if (sx < 0 || sy < 0 || sx >= W || sy >= H) continue;
      const e = cov[i] * op, p = i * 4, q = (sy * W + sx) * 4;
      d[p] = s[p] * (1 - e) + s[q] * e; d[p + 1] = s[p + 1] * (1 - e) + s[q + 1] * e; d[p + 2] = s[p + 2] * (1 - e) + s[q + 2] * e;
    }
    dikdortgenGenislet(x0, y0, x1 - x0, y1 - y0); goster(x0, y0, x1 - x0, y1 - y0);
  };
  // genel fırça darbesi: akış (flow) birikimi + opaklık tavanı
  const darbe = (px, py, fn) => {
    const r = M.boyut / 2, d = wd.data, op = M.guc / 100, ak = M.akis / 100;
    const x0 = Math.max(0, Math.floor(px - r)), x1 = Math.min(W, Math.ceil(px + r) + 1), y0 = Math.max(0, Math.floor(py - r)), y1 = Math.min(H, Math.ceil(py + r) + 1);
    for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
      const a = fircaA(Math.hypot(x - px, y - py), r, M.sert); if (a <= 0) continue;
      const i = y * W + x; cov[i] += (1 - cov[i]) * a * ak;
      fn(i, i * 4, cov[i] * op, x, y, d);
    }
    dikdortgenGenislet(x0, y0, x1 - x0, y1 - y0); goster(x0, y0, x1 - x0, y1 - y0);
  };
  const parla = (c) => 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2];
  // İyileştirme fırçası: kaynağın dokusunu alır, rengi/ışığı hedefin çevresine uydurur
  const iyilestirNokta = (px, py) => {
    const s = snap, ox = M.ofs[0], oy = M.ofs[1];
    darbe(px, py, (i, p, e, x, y, d) => {
      const sx = Math.round(x + ox), sy = Math.round(y + oy); if (sx < 0 || sy < 0 || sx >= W || sy >= H) return;
      const q = (sy * W + sx) * 4;
      for (let c = 0; c < 3; c++) { const yeni = s[q + c] + (bulanikB[p + c] - bulanikB[q + c]); d[p + c] = s[p + c] * (1 - e) + mvKelep(yeni, 0, 255) * e; }
    });
  };
  // Orijinale döndür: ekran açıldığındaki hale geri getirir
  const geriNokta = (px, py) => { const o = orig.data, s = snap; darbe(px, py, (i, p, e, x, y, d) => { for (let c = 0; c < 3; c++) d[p + c] = s[p + c] * (1 - e) + o[p + c] * e; }); };
  // Parlama gider: yerel ortalamanın üstüne çıkan parlak fazlalığı azaltır, dokuyu korur
  const parlamaNokta = (px, py) => {
    const s = snap;
    darbe(px, py, (i, p, e, x, y, d) => {
      const L = 0.299 * s[p] + 0.587 * s[p + 1] + 0.114 * s[p + 2], Ll = 0.299 * bulanikB[p] + 0.587 * bulanikB[p + 1] + 0.114 * bulanikB[p + 2];
      const fazla = L - Ll + 4; if (fazla <= 0) return;
      const yeniL = Math.max(1, L - fazla * 0.9 * mvKelep(fazla / 24, 0, 1)), k = yeniL / Math.max(1, L);
      for (let c = 0; c < 3; c++) d[p + c] = s[p + c] * (1 - e) + mvKelep(s[p + c] * k, 0, 255) * e;
    });
  };
  // Aydınlat / Karart (Dodge / Burn)
  const pozlamaNokta = (px, py, aydinlat) => {
    const s = snap;
    darbe(px, py, (i, p, e, x, y, d) => {
      const k = aydinlat ? 1 + 0.45 * e : 1 - 0.45 * e;
      for (let c = 0; c < 3; c++) d[p + c] = mvKelep(s[p + c] * k + (aydinlat ? (255 - s[p + c]) * 0.05 * e : 0), 0, 255);
    });
  };
  // Göz / diş beyazlat: beyaza yakın bölgede rengi azaltır ve hafifçe açar
  const beyazlatNokta = (px, py) => {
    const s = snap;
    darbe(px, py, (i, p, e, x, y, d) => {
      const r_ = s[p], g_ = s[p + 1], b_ = s[p + 2], mx = Math.max(r_, g_, b_), mn = Math.min(r_, g_, b_), L = 0.299 * r_ + 0.587 * g_ + 0.114 * b_;
      const doy = mx ? (mx - mn) / mx : 0, w = e * mvSmooth(50, 130, L) * (1 - mvSmooth(0.35, 0.7, doy));
      if (w <= 0) return;
      const t = 0.7 * w, ac = 1 + 0.10 * w;
      d[p] = mvKelep((s[p] * (1 - t) + L * t) * ac, 0, 255); d[p + 1] = mvKelep((s[p + 1] * (1 - t) + L * t) * ac, 0, 255); d[p + 2] = mvKelep((s[p + 2] * (1 - t) + L * t) * ac, 0, 255);
    });
  };
  const yumusatNokta = (px, py) => {
    const r = M.boyut / 2, d = wd.data, s = snap, op = M.guc / 100, t = M.doku / 100;
    const x0 = Math.max(0, Math.floor(px - r)), x1 = Math.min(W, Math.ceil(px + r) + 1), y0 = Math.max(0, Math.floor(py - r)), y1 = Math.min(H, Math.ceil(py + r) + 1);
    for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
      const a = fircaA(Math.hypot(x - px, y - py), r, M.sert); if (a <= 0) continue;
      const i = y * W + x; if (a > cov[i]) cov[i] = a;
      const e = cov[i] * op, p = i * 4;
      for (let c = 0; c < 3; c++) { const lp = bulanik[p + c], hedef = lp + (s[p + c] - lp) * t; d[p + c] = s[p + c] * (1 - e) + hedef * e; }
    }
    dikdortgenGenislet(x0, y0, x1 - x0, y1 - y0); goster(x0, y0, x1 - x0, y1 - y0);
  };
  const halka = (px, py, r) => {   // çevre örnekleri (24 açı × 2 yarıçap)
    const out = []; for (let k = 0; k < 24; k++) for (const m of [1.15, 1.45]) {
      const x = Math.round(px + Math.cos(k * Math.PI / 12) * r * m), y = Math.round(py + Math.sin(k * Math.PI / 12) * r * m);
      if (x < 0 || y < 0 || x >= W || y >= H) return null; const p = (y * W + x) * 4; out.push(wd.data[p], wd.data[p + 1], wd.data[p + 2]);
    } return out;
  };
  const noktaIyilestir = (px, py) => {
    const r = M.boyut / 2, hedef = halka(px, py, r); if (!hedef) return;
    let en = 1e18, ed = null;
    for (const m of [2.5, 3.4]) for (let k = 0; k < 24; k++) {
      const dx = Math.cos(k * Math.PI / 12) * r * m, dy = Math.sin(k * Math.PI / 12) * r * m;
      const aday = halka(px + dx, py + dy, r); if (!aday) continue;
      let ssd = 0; for (let i = 0; i < hedef.length; i++) { const f = hedef[i] - aday[i]; ssd += f * f; }
      if (ssd < en) { en = ssd; ed = [dx, dy, aday]; }
    }
    if (!ed) return;
    const dm = [0, 0, 0], am = [0, 0, 0]; for (let i = 0; i < hedef.length; i += 3) for (let c = 0; c < 3; c++) { dm[c] += hedef[i + c]; am[c] += ed[2][i + c]; }
    const n = hedef.length / 3, dl = [(dm[0] - am[0]) / n, (dm[1] - am[1]) / n, (dm[2] - am[2]) / n];
    const R = r * 1.1, d = wd.data, s = new Uint8ClampedArray(wd.data), op = M.guc / 100;
    const x0 = Math.max(0, Math.floor(px - R)), x1 = Math.min(W, Math.ceil(px + R) + 1), y0 = Math.max(0, Math.floor(py - R)), y1 = Math.min(H, Math.ceil(py + R) + 1);
    for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
      const a = fircaA(Math.hypot(x - px, y - py), R, Math.min(60, M.sert)) * op; if (a <= 0) continue;
      const sx = Math.round(x + ed[0]), sy = Math.round(y + ed[1]); if (sx < 0 || sy < 0 || sx >= W || sy >= H) continue;
      const p = (y * W + x) * 4, q = (sy * W + sx) * 4;
      for (let c = 0; c < 3; c++) d[p + c] = s[p + c] * (1 - a) + (s[q + c] + dl[c]) * a;
    }
    dikdortgenGenislet(x0, y0, x1 - x0, y1 - y0); goster(x0, y0, x1 - x0, y1 - y0);
  };

  // ---- yama (lasso → kaynağa sürükle)
  let lasso = null, yama = null;
  const selCiz = () => {
    selSvg.innerHTML = "";
    const yol = lasso || (M.sel && M.sel.pts);
    if (!yol || yol.length < 2) return;
    const dx = yama ? yama.dx : 0, dy = yama ? yama.dy : 0;
    const pts = yol.map(([x, y]) => `${(M.tx + (x + dx) * M.zoom).toFixed(1)},${(M.ty + (y + dy) * M.zoom).toFixed(1)}`).join(" ");
    if (lasso) {   // çizerken: ince koyu serbest çizgi (Photoshop'taki gibi)
      selSvg.innerHTML = `<polyline points="${pts}" fill="none" stroke="#fff" stroke-width="3" stroke-opacity=".55" stroke-linejoin="round"/><polyline points="${pts}" fill="none" stroke="#111" stroke-width="1.2" stroke-linejoin="round"/>`;
    } else {       // seçili: yürüyen karıncalar (siyah-beyaz kesik çizgi)
      selSvg.innerHTML = `<polygon points="${pts}" fill="rgba(0,0,0,.06)" stroke="#fff" stroke-width="1.3"/><polygon points="${pts}" fill="none" stroke="#111" stroke-width="1.3" stroke-dasharray="5 5" class="mv-karinca"/>`;
    }
  };
  const yamaUygula = (pts0, dx0, dy0) => {
    const hedefMod = M.yMod === "hedef";
    const pts = hedefMod ? pts0.map(([x, y]) => [x + dx0, y + dy0]) : pts0, dx = hedefMod ? -dx0 : dx0, dy = hedefMod ? -dy0 : dy0;
    let x0 = 1e9, y0 = 1e9, x1 = -1, y1 = -1; pts.forEach(([x, y]) => { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); });
    const pad = 8; x0 = Math.max(0, Math.floor(x0 - pad)); y0 = Math.max(0, Math.floor(y0 - pad)); x1 = Math.min(W, Math.ceil(x1 + pad)); y1 = Math.min(H, Math.ceil(y1 + pad));
    const w = x1 - x0, hh = y1 - y0; if (w < 2 || hh < 2) return;
    // seçim maskesi (kenar yumuşatmalı)
    const mc = document.createElement("canvas"); mc.width = w; mc.height = hh; const mx = mc.getContext("2d", {willReadFrequently: true});
    mx.filter = `blur(${(0.6 + M.yay * 1.1).toFixed(1)}px)`; mx.fillStyle = "#fff"; mx.beginPath(); pts.forEach(([x, y], i) => i ? mx.lineTo(x - x0, y - y0) : mx.moveTo(x - x0, y - y0)); mx.closePath(); mx.fill();
    const md = mx.getImageData(0, 0, w, hh).data;
    // hedef ve kaynak bölgesi, alçak geçiren farkı (ışık/renk uyumu)
    const bolge = (sx, sy) => { const c = document.createElement("canvas"); c.width = w; c.height = hh; const x = c.getContext("2d", {willReadFrequently: true}); x.putImageData(new ImageData(new Uint8ClampedArray(orig.data.length ? subBolge(snap, sx, sy, w, hh) : 0), w, hh), 0, 0); return c; };
    const subBolge = (kaynak, sx, sy, ww, hh2) => { const o = new Uint8ClampedArray(ww * hh2 * 4); for (let y = 0; y < hh2; y++) for (let x = 0; x < ww; x++) { const X = mvKelep(sx + x, 0, W - 1), Y = mvKelep(sy + y, 0, H - 1), p = (Y * W + X) * 4, q = (y * ww + x) * 4; o[q] = kaynak[p]; o[q + 1] = kaynak[p + 1]; o[q + 2] = kaynak[p + 2]; o[q + 3] = 255; } return o; };
    const hc = bolge(x0, y0), sc = bolge(Math.round(x0 + dx), Math.round(y0 + dy));
    const rb = Math.max(2, Math.round(Math.sqrt(w * hh) * 0.18));
    const blur = (c) => { const b = document.createElement("canvas"); b.width = w; b.height = hh; const x = b.getContext("2d", {willReadFrequently: true}); x.filter = `blur(${rb}px)`; x.drawImage(c, 0, 0); return x.getImageData(0, 0, w, hh).data; };
    const hb = blur(hc), sb = blur(sc), sd = sc.getContext("2d").getImageData(0, 0, w, hh).data, hd = hc.getContext("2d").getImageData(0, 0, w, hh).data;
    const dif = M.guc / 100, d = wd.data;
    for (let y = 0; y < hh; y++) for (let x = 0; x < w; x++) {
      const a = md[(y * w + x) * 4 + 3] / 255; if (a <= 0.004) continue;
      const q = (y * w + x) * 4, p = ((y0 + y) * W + (x0 + x)) * 4;
      for (let c = 0; c < 3; c++) { const yeni = sd[q + c] + (hb[q + c] - sb[q + c]) * dif; d[p + c] = hd[q + c] * (1 - a) + yeni * a; }
    }
    dikdortgenGenislet(x0, y0, w, hh); goster(x0, y0, w, hh);
  };

  // ---- araçlar (dekupe)
  const dekupeNokta = (px, py) => {
    const r = M.boyut / 2, op = M.guc / 100, tur = M.arac, o = orig.data;
    const x0 = Math.max(0, Math.floor(px - r)), x1 = Math.min(W, Math.ceil(px + r) + 1), y0 = Math.max(0, Math.floor(py - r)), y1 = Math.min(H, Math.ceil(py + r) + 1);
    const bw = x1 - x0, bh = y1 - y0, loc = (tur === "yumusat" || tur === "daralt" || tur === "genislet") ? new Uint8Array(bw * bh) : null;
    if (loc) for (let y = 0; y < bh; y++) loc.set(A.subarray((y0 + y) * W + x0, (y0 + y) * W + x0 + bw), y * bw);
    const goruntu = (x, y) => loc[mvKelep(y - y0, 0, bh - 1) * bw + mvKelep(x - x0, 0, bw - 1)];
    for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
      const w = fircaA(Math.hypot(x - px, y - py), r, M.sert) * op; if (w <= 0) continue;
      const i = y * W + x, p = i * 4, a = A[i]; let hedef = a;
      if (tur === "sac") {
        if (a > 242) continue;   // kişinin içi: dokunma (yalnız kenar bölgesi iyileştirilir)
        const bR = plB[p], bG = plB[p + 1], bB = plB[p + 2], fR = plF[p], fG = plF[p + 1], fB = plF[p + 2];
        const vx = fR - bR, vy = fG - bG, vz = fB - bB, n2 = vx * vx + vy * vy + vz * vz;
        if (n2 < 400) { hedef = a; }   // saç rengi fon rengine çok yakınsa güvenilmez
        else { const t = ((o[p] - bR) * vx + (o[p + 1] - bG) * vy + (o[p + 2] - bB) * vz) / n2; hedef = 255 * mvSmooth(0.12, 0.85, t); }
      } else if (tur === "ekle") hedef = 255;
      else if (tur === "sil") hedef = 0;
      else if (tur === "keskin") hedef = 255 * mvSmooth(0.32, 0.68, a / 255);
      else { // yumuşat / daralt / genişlet: 5×5
        let mn = 255, mx = 0, top = 0, n = 0;
        for (let yy = -2; yy <= 2; yy++) for (let xx = -2; xx <= 2; xx++) { const v = goruntu(x + xx, y + yy); if (v < mn) mn = v; if (v > mx) mx = v; top += v; n++; }
        hedef = tur === "daralt" ? mn : tur === "genislet" ? mx : top / n;
      }
      A[i] = a + (hedef - a) * w;
    }
    dikdortgenGenislet(x0, y0, bw, bh); boyaDekupe(x0, y0, bw, bh); goster(x0, y0, bw, bh);
  };

  // ---- fare
  let cizim = null, son = null, bosluk = false, tut = null;
  const arac = () => M.arac;
  const KAYNAKLI = (a) => a === "klon" || a === "iyilestir";
  const noktaKalan = (e) => { const [x, y] = noktaya(e); return [x, y]; };
  const dabCalistir = (x, y) => {
    const a = arac();
    if (mod === "rotus") { if (a === "klon") klonNokta(x, y); else if (a === "iyilestir") iyilestirNokta(x, y); else if (a === "geri") geriNokta(x, y); else if (a === "parlama") parlamaNokta(x, y);
      else if (a === "aydinlat") pozlamaNokta(x, y, true); else if (a === "karart") pozlamaNokta(x, y, false); else if (a === "beyazlat") beyazlatNokta(x, y); else if (a === "yumusat") yumusatNokta(x, y); else if (a === "nokta") noktaIyilestir(x, y); }
    else dekupeNokta(x, y);
  };
  alan.addEventListener("pointerdown", (e) => {
    if (e.button === 1 || (e.button === 0 && M.bosluk)) { tut = {x: e.clientX, y: e.clientY, tx: M.tx, ty: M.ty}; alan.setPointerCapture(e.pointerId); e.preventDefault(); return; }
    if (e.button !== 0) return;
    const [x, y] = noktaKalan(e);
    if (KAYNAKLI(arac()) && e.altKey) { M.kaynak = [x, y]; M.ofs = null; arayuzGuncelle(); durumIpucu("Klon kaynağı seçildi: boyamaya başlayın"); return; }
    if (KAYNAKLI(arac())) {
      if (!M.kaynak) { durumIpucu("Önce Alt + tıklayarak kaynak noktasını seçin"); return; }
      if (!M.ofs || !M.hizali) M.ofs = [M.kaynak[0] - x, M.kaynak[1] - y];
    }
    if (arac() === "yama") {
      if (M.sel && M.sel.pts && pointInPoly(x, y, M.sel.pts)) { darbeBasla(); yama = {bx: x, by: y, dx: 0, dy: 0}; alan.setPointerCapture(e.pointerId); return; }
      M.sel = null; lasso = [[x, y]]; alan.setPointerCapture(e.pointerId); selCiz(); return;
    }
    darbeBasla(); cizim = true; son = [x, y]; alan.setPointerCapture(e.pointerId);
    dabCalistir(x, y);
  });
  alan.addEventListener("pointermove", (e) => {
    const ar = alan.getBoundingClientRect(), d = M.boyut * M.zoom;
    if (FIRCALI.includes(arac())) {
      Object.assign(imlec.style, {display: "block", width: d + "px", height: d + "px", left: (e.clientX - ar.left - d / 2) + "px", top: (e.clientY - ar.top - d / 2) + "px"});
      alan.style.cursor = "none";
    } else { imlec.style.display = "none"; alan.style.cursor = "crosshair"; }
    if (M.bosluk || tut) alan.style.cursor = "grab";
    if (tut) { M.tx = tut.tx + e.clientX - tut.x; M.ty = tut.ty + e.clientY - tut.y; uygula(); return; }
    const [x, y] = noktaKalan(e);
    if (lasso) { lasso.push([x, y]); selCiz(); return; }
    if (yama) { yama.dx = x - yama.bx; yama.dy = y - yama.by; for (let i = 0; i < wd.data.length; i++) wd.data[i] = snap[i]; yamaUygula(M.sel.pts, yama.dx, yama.dy); selCiz(); return; }
    if (cizim && son) {
      const r = Math.max(1, M.boyut / 2), aralik = arac() === "nokta" ? r * 1.4 : Math.max(1, r * (mod === "dekupe" ? 0.18 : 0.22));
      const mesafe = Math.hypot(x - son[0], y - son[1]); const n = Math.floor(mesafe / aralik);
      for (let k = 1; k <= n; k++) dabCalistir(son[0] + (x - son[0]) * k / n, son[1] + (y - son[1]) * k / n);
      if (n > 0) son = [son[0] + (x - son[0]) * n * aralik / mesafe, son[1] + (y - son[1]) * n * aralik / mesafe];
    }
  });
  const birak = (e) => {
    tut = null;
    if (lasso) { if (lasso.length > 3) M.sel = {pts: lasso}; lasso = null; selCiz(); durumIpucu(M.sel ? "Seçimin içinden tutup temiz bir alana sürükleyin, bırakınca uygulanır · Esc: seçimi kaldır" : ""); return; }
    if (yama) { const fark = Math.hypot(yama.dx, yama.dy); const pts = M.sel.pts; yama = null; if (fark < 2) { for (let i = 0; i < wd.data.length; i++) wd.data[i] = snap[i]; snap = null; goster(0, 0, W, H); } else { M.sel = null; darbeBitir(); } selCiz(); return; }
    if (cizim) { cizim = false; son = null; darbeBitir(); }
  };
  alan.addEventListener("pointerup", birak); alan.addEventListener("pointercancel", birak);
  alan.addEventListener("pointerleave", () => { imlec.style.display = "none"; });
  const FIRCALI = ["klon", "iyilestir", "geri", "parlama", "aydinlat", "karart", "beyazlat", "yumusat", "nokta", "sac", "ekle", "sil", "keskin", "daralt", "genislet"];
  let popup = null;
  const popupKapat = () => { if (popup) { popup.remove(); popup = null; document.removeEventListener("pointerdown", disTik, true); } };
  const disTik = (e) => { if (popup && !popup.contains(e.target)) popupKapat(); };
  const fircaPopup = (cx_, cy_) => {
    popupKapat();
    const mx_ = Math.round(W / 6);
    popup = h(`<div class="mv-pop"><div class="mv-pop-onizle"><canvas width="96" height="96"></canvas></div>
      <label><span>Boyut</span><input type="range" min="1" max="${mx_}" value="${M.boyut}"><input type="number" min="1" max="${mx_}" value="${M.boyut}" class="sayi"><i>px</i></label>
      <label><span>Sertlik</span><input type="range" min="0" max="100" value="${M.sert}"><input type="number" min="0" max="100" value="${M.sert}" class="sayi"><i>%</i></label></div>`);
    kok.appendChild(popup);
    const ar = kok.getBoundingClientRect(), pw = 270, ph = 190;
    popup.style.left = mvKelep(cx_ - ar.left - pw / 2, 8, ar.width - pw - 8) + "px"; popup.style.top = mvKelep(cy_ - ar.top + 14, 8, ar.height - ph - 8) + "px";
    const pc = $("canvas", popup), px = pc.getContext("2d");
    const onizle = () => {
      px.clearRect(0, 0, 96, 96); const R = 42 * Math.min(1, 0.25 + M.boyut / Math.max(40, mx_ * 0.35)) , ic = M.sert / 100;
      const g = px.createRadialGradient(48, 48, R * ic, 48, 48, R); g.addColorStop(0, "rgba(255,255,255,.95)"); g.addColorStop(1, "rgba(255,255,255,0)");
      px.fillStyle = g; px.beginPath(); px.arc(48, 48, R, 0, 7); px.fill();
      px.strokeStyle = "rgba(0,0,0,.5)"; px.lineWidth = 1; px.beginPath(); px.arc(48, 48, R, 0, 7); px.stroke();
    };
    const [sB, nB, sS, nS] = $$("input", popup);
    const sinirla = (v, a, b) => mvKelep(Math.round(+v || 0), a, b);
    const yaz = () => { onizle(); ayarCiz(); };
    sB.oninput = () => { M.boyut = sinirla(sB.value, 1, mx_); nB.value = M.boyut; yaz(); };
    nB.oninput = () => { M.boyut = sinirla(nB.value, 1, mx_); sB.value = M.boyut; yaz(); };
    sS.oninput = () => { M.sert = sinirla(sS.value, 0, 100); nS.value = M.sert; yaz(); };
    nS.oninput = () => { M.sert = sinirla(nS.value, 0, 100); sS.value = M.sert; yaz(); };
    onizle(); document.addEventListener("pointerdown", disTik, true);
  };
  MV.popupKapat = popupKapat;
  alan.addEventListener("contextmenu", (e) => { e.preventDefault(); if (FIRCALI.includes(M.arac)) fircaPopup(e.clientX, e.clientY); });

  function pointInPoly(x, y, pts) { let ic = false; for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) { const [xi, yi] = pts[i], [xj, yj] = pts[j]; if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) ic = !ic; } return ic; }
  const durumIpucu = (t) => { $("#mvIpucu", kok).textContent = t || ""; };

  // ---- arayüz: sol araç sütunu, üst ayar çubuğu, sağ panel
  const ARACLAR = mod === "rotus"
    ? [["klon", "Klon damgası", "Alt + tıkla: kaynağı seç, sonra boyayarak kopyala (S)", "◎"], ["yama", "Yama", "Lekenin çevresini elle çizerek seçin, sonra seçimi temiz bir alana sürükleyin (J)", "⬚"],
       ["iyilestir", "İyileştirme fırçası", "Alt + tıkla kaynağı seç; dokuyu kopyalar, rengi ve ışığı çevreye uydurur (H)", "✚"],
       ["nokta", "Nokta iyileştirme", "Lekenin üzerine tıklayın: çevreden en uygun dokuyla otomatik doldurur (Q)", "✦"], ["yumusat", "Cilt yumuşat", "Fırçayla ten düzensizliğini yumuşatır, dokuyu korur (W)", "◌"],
       ["parlama", "Parlama gider", "Alın, burun, yanaktaki yağ parlamasını siler; dokuyu korur (P)", "☀"], ["aydinlat", "Aydınlat", "Gölge ve göz altı morluğunu yerel olarak açar (L)", "◑"], ["karart", "Karart", "Fazla parlak bölgeyi yerel olarak koyulaştırır (B)", "◐"],
       ["beyazlat", "Göz / diş beyazlat", "Göz akı ve dişlerde sararmayı giderir, ten rengine etki etmez (T)", "◇"], ["geri", "Orijinale döndür", "Fırçayla geçtiğiniz yeri bu ekran açıldığındaki haline geri getirir (O)", "↺"]]
    : [["sac", "Saç fırçası", "Kenarı iyileştir: saç tellerini renk farkına göre geri getirir, gri haleyi siler (S)", "≋"], ["ekle", "Ekle", "Fırçanın altını kişiye ekler (A)", "＋"], ["sil", "Sil", "Fırçanın altını fon olarak siler (E)", "−"],
       ["yumusat", "Yumuşat", "Maske kenarını yumuşatır (U)", "◌"], ["keskin", "Keskinleştir", "Maske kenarını netleştirir (K)", "◆"], ["daralt", "Daralt", "Kenarı içe doğru kaydırır (D)", "⇥"], ["genislet", "Genişlet", "Kenarı dışa doğru kaydırır (G)", "⇤"]];
  const sol = $("#mvSol", kok);
  const solCiz = () => { sol.innerHTML = ""; ARACLAR.forEach(([k, ad, ip, ik]) => { const b = h(`<button class="mv-arac ${M.arac === k ? "secili" : ""}" title="${esc(ad + " — " + ip)}"><span>${ik}</span><small>${esc(ad)}</small></button>`); b.onclick = () => { popupKapat(); M.kaynak = KAYNAKLI(k) && KAYNAKLI(M.arac) ? M.kaynak : null; M.ofs = null; M.arac = k; M.sel = null; selCiz(); arayuzGuncelle(); }; sol.append(b); }); };
  const ayarEl = $("#mvAyar", kok);
  const slider = (etiket, ip, min, max, deger, birim, cb) => {
    const e = h(`<label class="mv-s" title="${esc(ip)}"><span>${etiket}</span><button type="button" class="ok">◄</button><input type="range" min="${min}" max="${max}" value="${deger}"><button type="button" class="ok">►</button><b>${deger}${birim}</b></label>`);
    const inp = $("input", e), [sl, sg] = $$("button", e), lab = $("b", e);
    const ayarla = (v) => { v = mvKelep(v, +min, +max); inp.value = v; lab.textContent = v + birim; cb(v); };
    inp.oninput = () => ayarla(+inp.value); sl.onclick = () => ayarla(+inp.value - 1); sg.onclick = () => ayarla(+inp.value + 1); return e;
  };
  const secimEl = (etiket, ip, deger, cb) => { const e = h(`<label class="mv-c" title="${esc(ip)}"><input type="checkbox" ${deger ? "checked" : ""}><span>${etiket}</span></label>`); $("input", e).onchange = (ev) => cb(ev.target.checked); return e; };
  const ayarCiz = () => {
    ayarEl.innerHTML = "";
    if (FIRCALI.includes(M.arac)) {
      const chip = h(`<button type="button" class="mv-chip" title="Fırça boyutu ve sertliği: fotoğraf üzerinde sağ tıklayın (veya buraya tıklayın). Kısayol: [ ] boyut, Shift+[ ] sertlik">◯ ${M.boyut}px · %${M.sert}</button>`);
      chip.onclick = () => { const r = chip.getBoundingClientRect(); fircaPopup(r.left + r.width / 2, r.bottom); };
      ayarEl.append(chip);
    }
    if (M.arac === "yama") {
      const g = h(`<div class="mv-seg" title="Kaynak: seçili lekeyi, sürüklediğiniz temiz alanla doldurur. Hedef: seçili temiz alanı sürüklediğiniz yere kopyalar"><span>Yama</span><button type="button" class="${M.yMod === "kaynak" ? "ac" : ""}">Kaynak</button><button type="button" class="${M.yMod === "hedef" ? "ac" : ""}">Hedef</button></div>`);
      const [bk, bh] = $$("button", g); bk.onclick = () => { M.yMod = "kaynak"; ayarCiz(); }; bh.onclick = () => { M.yMod = "hedef"; ayarCiz(); };
      ayarEl.append(g);
      ayarEl.append(slider("Yayılım", "Yama kenarının çevreye karışma miktarı (Photoshop'taki Diffusion)", 1, 7, M.yay, "", v => M.yay = v));
      ayarEl.append(slider("Uyum", "Yamanın çevre ışığına ve rengine uyumu", 1, 100, M.guc, "%", v => M.guc = v));
    } else {
      const gucAd = {klon: "Opaklık", iyilestir: "Opaklık", geri: "Opaklık", parlama: "Güç", aydinlat: "Pozlama", karart: "Pozlama", beyazlat: "Güç", nokta: "Güç", yumusat: "Güç", sac: "Güç", ekle: "Güç", sil: "Güç", keskin: "Güç", daralt: "Güç", genislet: "Güç"}[M.arac];
      const gucIp = {klon: "Kopyalanan dokunun en fazla şeffaflığı (Photoshop'taki Opacity)"}[M.arac] || "Fırça etkisinin gücü";
      ayarEl.append(slider(gucAd, gucIp, 1, 100, M.guc, "%", v => M.guc = v));
      if (["klon", "iyilestir", "geri", "parlama", "aydinlat", "karart", "beyazlat"].includes(M.arac)) ayarEl.append(slider("Akış", "Aynı yere tekrar boyadıkça etkinin birikme hızı (Photoshop'taki Flow)", 1, 100, M.akis, "%", v => M.akis = v));
    }
    if (M.arac === "yumusat" && mod === "rotus") ayarEl.append(slider("Doku", "Yumuşatırken korunan ince doku miktarı", 0, 100, M.doku, "%", v => M.doku = v));
    if (KAYNAKLI(M.arac)) ayarEl.append(secimEl("Hizalı", "Açık: kaynak ile hedef arasındaki fark vuruşlar arasında sabit kalır (Photoshop'taki Aligned)", M.hizali, v => { M.hizali = v; M.ofs = null; }));
    if (mod === "dekupe") ayarEl.append(slider("Renk taşması", "Kenardaki eski fon rengini temizleme miktarı (önizleme ve sonuç)", 0, 100, M.tasma, "%", v => { M.tasma = v; tumuBoya(); }));
  };
  const sag = $("#mvSag", kok);
  const gecmisCiz = () => { const g = $("#mvGecmis", kok); if (g) g.textContent = `${M.gecmis.length} işlem`; $("#mvGeri", kok) && ($("#mvGeri", kok).disabled = !M.gecmis.length); $("#mvIleri", kok) && ($("#mvIleri", kok).disabled = !M.ileri.length); };
  const sagCiz = () => {
    sag.innerHTML = `<div class="mv-bolum"><h4>Görünüm</h4><div class="mv-gor"></div></div>
      <div class="mv-bolum"><h4>Harita</h4><canvas id="mvHarita" class="mv-harita" title="Tıklayın veya sürükleyin: görünümü o noktaya taşır"></canvas></div>
      <div class="mv-bolum"><h4>Geçmiş</h4><div class="satir"><button class="btn kucuk" id="mvGeri" title="Son işlemi geri al (Ctrl+Z)">↶ Geri al</button><button class="btn kucuk" id="mvIleri" title="Geri alınanı yinele (Ctrl+Y)">↷ İleri</button></div><div class="not" id="mvGecmis"></div></div>
      <div class="mv-bolum"><h4>Yakınlaştırma</h4><div class="satir"><button class="btn kucuk" id="mvSigdir" title="Tüm fotoğrafı sığdır (0)">Sığdır</button><button class="btn kucuk" id="mv100" title="%100 boyut (1)">%100</button></div><div class="not">Fare tekerleği: yakınlaştır · Boşluk + sürükle: kaydır</div></div>
      <div class="mv-bolum"><h4>Karşılaştır</h4><button class="btn kucuk genis" id="mvOnce" title="Basılı tutarken orijinal görünür (\\ tuşu)">Önce / Sonra (basılı tut)</button></div>`;
    const gor = $(".mv-gor", sag);
    const modlar = mod === "rotus" ? [["sonuc", "Sonuç"]] : [["beyaz", "Beyaz"], ["koyu", "Koyu"], ["renkli", "Renkli"], ["maske", "Maske"], ["kirmizi", "Kırmızı kaplama"], ["once", "Orijinal"]];
    modlar.forEach(([k, a]) => { const b = h(`<button class="btn kucuk ${M.gorunum === k ? "ana" : ""}" title="Görünüm: ${esc(a)}">${a}</button>`); b.onclick = () => { M.gorunum = k; tumuBoya(); sagCiz(); }; gor.append(b); });
    if (mod === "rotus") gor.append(h(`<div class="not">Düzenlemeler bu fotoğraf üzerinde yapılır; kenarları etkileyen otomatik işlem yoktur.</div>`));
    $("#mvGeri", sag).onclick = geriAl; $("#mvIleri", sag).onclick = ileriAl; $("#mvSigdir", sag).onclick = sigdir;
    $("#mv100", sag).onclick = () => { const ar = alan.getBoundingClientRect(); M.zoom = 1; M.tx = (ar.width - W) / 2; M.ty = (ar.height - H) / 2; uygula(); };
    const ob = $("#mvOnce", sag), ac = (v) => { M.onceMi = v; if (mod === "dekupe") boyaDekupe(0, 0, W, H); cx.putImageData(v ? orig : wd, 0, 0); };
    ob.onpointerdown = () => ac(true); ob.onpointerup = ob.onpointerleave = () => { if (M.onceMi) ac(false); };
    gecmisCiz(); haritaKur();
  };
  const haritaCiz = () => {
    const hc = $("#mvHarita", kok); if (!hc || !hc.width) return;
    const x = hc.getContext("2d"); x.clearRect(0, 0, hc.width, hc.height); x.drawImage(cv, 0, 0, hc.width, hc.height);
    const ar = alan.getBoundingClientRect(), k = hc.width / W;
    const vx = mvKelep(-M.tx / M.zoom, 0, W), vy = mvKelep(-M.ty / M.zoom, 0, H), vw = Math.min(W - vx, ar.width / M.zoom), vh = Math.min(H - vy, ar.height / M.zoom);
    x.fillStyle = "rgba(0,0,0,.35)"; x.beginPath(); x.rect(0, 0, hc.width, hc.height); x.rect(vx * k, vy * k, vw * k, vh * k); x.fill("evenodd");
    x.strokeStyle = "#fff"; x.lineWidth = 1.5; x.strokeRect(vx * k, vy * k, vw * k, vh * k);
  };
  const haritaKur = () => {
    const hc = $("#mvHarita", kok); if (!hc) return;
    const gen = 190; hc.width = gen; hc.height = Math.max(40, Math.round(gen * H / W)); hc.style.width = gen + "px"; hc.style.height = hc.height + "px";
    const tasi = (e) => { const r = hc.getBoundingClientRect(), ar = alan.getBoundingClientRect(); const ix = (e.clientX - r.left) / r.width * W, iy = (e.clientY - r.top) / r.height * H; M.tx = ar.width / 2 - ix * M.zoom; M.ty = ar.height / 2 - iy * M.zoom; uygula(); };
    let tut_ = false; hc.onpointerdown = (e) => { tut_ = true; hc.setPointerCapture(e.pointerId); tasi(e); }; hc.onpointermove = (e) => { if (tut_) tasi(e); }; hc.onpointerup = () => { tut_ = false; };
    haritaCiz();
  };
  MV.haritaCiz = haritaCiz;
  const arayuzGuncelle = () => { solCiz(); ayarCiz(); sagCiz(); };
  arayuzGuncelle();

  // ---- klavye
  const tusIndir = (e) => {
    if (e.target.tagName === "INPUT" && e.target.type === "text") return;
    const k = e.key.toLowerCase();
    if (e.type === "keydown") {
      if (e.code === "Space") { M.bosluk = true; alan.style.cursor = "grab"; e.preventDefault(); return; }
      if (e.ctrlKey && k === "z") { e.preventDefault(); e.shiftKey ? ileriAl() : geriAl(); return; }
      if (e.ctrlKey && k === "y") { e.preventDefault(); ileriAl(); return; }
      if (e.shiftKey && (e.key === "{" || e.key === "}")) { M.sert = mvKelep(M.sert + (e.key === "{" ? -10 : 10), 0, 100); ayarCiz(); return; }
      if (e.key === "[") { M.boyut = Math.max(4, Math.round(M.boyut * 0.85)); ayarCiz(); return; }
      if (e.key === "]") { M.boyut = Math.min(Math.round(W / 6), Math.round(M.boyut * 1.18)); ayarCiz(); return; }
      if (e.key === "\\") { if (!M.onceMi) { M.onceMi = true; if (mod === "dekupe") boyaDekupe(0, 0, W, H); cx.putImageData(orig, 0, 0); } return; }
      if (e.key === "0") { sigdir(); return; }
      if ((e.key === "Escape" || e.key === "Enter") && popup) { popupKapat(); return; }
      if (e.key === "Escape") { if (M.sel) { M.sel = null; selCiz(); } else iptal(); return; }
      const eslesme = mod === "rotus" ? {s: "klon", j: "yama", q: "nokta", w: "yumusat", h: "iyilestir", o: "geri", p: "parlama", l: "aydinlat", b: "karart", t: "beyazlat"} : {s: "sac", a: "ekle", e: "sil", u: "yumusat", k: "keskin", d: "daralt", g: "genislet"};
      if (!e.ctrlKey && eslesme[k]) { M.arac = eslesme[k]; M.sel = null; arayuzGuncelle(); }
    } else {
      if (e.code === "Space") { M.bosluk = false; alan.style.cursor = ""; }
      if (e.key === "\\" && M.onceMi) { M.onceMi = false; if (mod === "dekupe") boyaDekupe(0, 0, W, H); cx.putImageData(wd, 0, 0); }
    }
  };
  document.addEventListener("keydown", tusIndir); document.addEventListener("keyup", tusIndir);
  const kapatMV = () => { popupKapat(); document.removeEventListener("keydown", tusIndir); document.removeEventListener("keyup", tusIndir); window.removeEventListener("resize", sigdir); kok.remove(); MV.acik = false; MV.m = null; };
  const iptal = () => { if (M.kirli && !confirm("Yaptığınız düzenlemeler atılsın mı?")) return; kapatMV(); };
  $("#mvIptal", kok).onclick = iptal;

  // ---- uygula: yalnız değişen kısım motora gönderilir
  $("#mvUygula", kok).onclick = async () => {
    if (!M.kirli) { kapatMV(); return; }
    if (mod === "rotus") {
      const d = wd.data, o = orig.data; let x0 = W, y0 = H, x1 = -1, y1 = -1;
      for (let y = 0; y < H; y++) { const sat = y * W; for (let x = 0; x < W; x++) { const p = (sat + x) * 4; if (d[p] !== o[p] || d[p + 1] !== o[p + 1] || d[p + 2] !== o[p + 2]) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; } } }
      if (x1 < 0) { kapatMV(); return; }
      const w = x1 - x0 + 1, hh = y1 - y0 + 1, yama_ = new ImageData(w, hh);
      for (let y = 0; y < hh; y++) for (let x = 0; x < w; x++) { const p = ((y0 + y) * W + x0 + x) * 4, q = (y * w + x) * 4; const fark = d[p] !== o[p] || d[p + 1] !== o[p + 1] || d[p + 2] !== o[p + 2]; yama_.data[q] = d[p]; yama_.data[q + 1] = d[p + 1]; yama_.data[q + 2] = d[p + 2]; yama_.data[q + 3] = fark ? 255 : 0; }
      const c = document.createElement("canvas"); c.width = w; c.height = hh; c.getContext("2d").putImageData(yama_, 0, 0);
      kapatMV();
      const q = await cagir("manuel_uygula_rotus", S.cur, S.fid, x0, y0, c.toDataURL("image/png"));
      if (q.ok) { S.st = {...q, gorsel_once: S.st.gorsel_once}; ciz(); bildir("Manuel rötuş uygulandı"); }
    } else {
      const ac = document.createElement("canvas"); ac.width = W; ac.height = H; const ax = ac.getContext("2d"), mc = document.createElement("canvas"); mc.width = W; mc.height = H; const mx = mc.getContext("2d");
      const ai = new ImageData(W, H), mi = new ImageData(W, H);
      for (let i = 0; i < W * H; i++) { const p = i * 4, v = A[i]; ai.data[p] = ai.data[p + 1] = ai.data[p + 2] = v; ai.data[p + 3] = 255; const m = v !== A0[i] ? 255 : 0; mi.data[p] = mi.data[p + 1] = mi.data[p + 2] = m; mi.data[p + 3] = 255; }
      ax.putImageData(ai, 0, 0); mx.putImageData(mi, 0, 0);
      kapatMV();
      const q = await cagir("manuel_uygula_dekupe", S.cur, S.fid, ac.toDataURL("image/png"), mc.toDataURL("image/png"));
      if (q.ok) { S.st = {...q, gorsel_once: S.st.gorsel_once}; ciz(); bildir("Manuel dekupe uygulandı"); }
    }
  };
  window.addEventListener("resize", sigdir);
  sigdir();
  durumIpucu(mod === "rotus" ? "Klon damgası: Alt + tıkla kaynağı seç · Fare tekerleği: yakınlaştır · Boşluk + sürükle: kaydır" : "Saç fırçasıyla saç ucunun üstünden geçin · Koyu zeminde hale daha net görünür");
}
