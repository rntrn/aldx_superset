// ALDx App — Ekspor dashboard ke PowerPoint (tombol di bilah atas saat sebuah dashboard dibuka).
//
//   1. setiap chart pada tab yang sedang tampil dipotret (html-to-image, sama dengan Ekspor PNG), berurutan dari atas
//   2. judul dashboard + filter aktif menjadi slide sampul
//   3. server menyusun berkas .pptx (POST /pptx/api/buat, config/sps_pptx.py) -> diunduh
//   Chart di tab lain tidak ikut: buka tab itu lalu ekspor lagi.
(function () {
  "use strict";
  const SPS = window.SPS, tombol = document.getElementById("eksporPptx");
  if (!tombol) return;
  const {t} = SPS.i18n;
  tombol.innerHTML = SPS.ikon("presentasi", 18);
  const PUSTAKA = "/app/static/vendor/html-to-image.js";
  const tunggu = ms => new Promise(r => setTimeout(r, ms));
  let sibuk = false;

  const muatPustaka = () => window.htmlToImage ? Promise.resolve(window.htmlToImage) : new Promise((ok, gagal) => {
    const s = document.createElement("script");
    s.src = PUSTAKA; s.onload = () => ok(window.htmlToImage); s.onerror = () => gagal(new Error(t("Pustaka gambar gagal dimuat")));
    document.head.appendChild(s);
  });
  const dashboardKini = () => /^\/superset\/dashboard\//.test(((SPS.halaman && SPS.halaman()) || {}).alamat || "");

  // Chart sudah selesai digambar? (kanvas/svg/tabel/teks angka muncul, tidak ada pemuat)
  async function tungguSiap(h) {
    for (let i = 0; i < 25; i++) {
      const isi = h.querySelector('[data-test="chart-container"]');
      if (isi && !isi.querySelector(".loading, [aria-label='loading']") && isi.querySelector("canvas, svg, table, .header-line, .big_number, .superset-legacy-chart-big-number")) return;
      await tunggu(200);
    }
  }
  function ringkasFilter(w) {
    let f = {};
    try { f = (w.__spsFilterAktif && w.__spsFilterAktif()) || {}; } catch (e) { /* tanpa filter */ }
    return Object.entries(f).map(([k, v]) => `${k === "__waktu__" ? t("Waktu") : k}: ` +
      (typeof v === "string" ? v : Array.isArray(v) ? v.join(", ") : `${v.min ?? "…"} – ${v.max ?? "…"}`)).join(" · ");
  }

  async function ekspor() {
    if (sibuk) return;
    const bingkai = document.getElementById("bingkai"), w = bingkai.contentWindow, dok = bingkai.contentDocument;
    const kotak = [...dok.querySelectorAll(".dashboard-component-chart-holder")]
      .filter(h => h.querySelector('[data-test="chart-container"]') && h.getClientRects().length);   // tab yang tampil saja
    if (!kotak.length) { SPS.notif(t("Tidak ada chart yang tampil untuk diekspor.")); return; }
    sibuk = true; tombol.disabled = true;
    try {
      const lib = await muatPustaka(), slide = [];
      for (const [i, h] of kotak.entries()) {
        SPS.notif(`${t("Menyiapkan PowerPoint")}: ${i + 1}/${kotak.length}`);
        h.scrollIntoView({block: "center"}); await tungguSiap(h); await tunggu(150);
        const judul = (h.querySelector('[data-test="editable-title"]') || {}).innerText || "";
        const png = await lib.toPng(h, {pixelRatio: 1.5, backgroundColor: "#ffffff", cacheBust: true, skipFonts: true,
          filter: n => !(n.dataset && ["slice-header", "ellipsis", "slice-header-controls"].includes(n.dataset.test))});   // judul jadi judul slide
        slide.push({judul: judul.trim(), png});
      }
      w.scrollTo(0, 0);
      const h = SPS.halaman() || {}, judul = (h.judul || "Dashboard").replace(/\s*·.*$/, "");
      const r = await fetch("/pptx/api/buat", {method: "POST", credentials: "same-origin",
        headers: {"Content-Type": "application/json", "X-CSRFToken": (window.SPS_AWAL || {}).csrf || ""},
        body: JSON.stringify({judul, keterangan: ringkasFilter(w), slide})});
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `HTTP ${r.status}`);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(await r.blob());
      a.download = ((r.headers.get("Content-Disposition") || "").match(/filename="([^"]+)"/) || [])[1] || "dashboard.pptx";
      document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
      SPS.notif(`${t("PowerPoint siap")}: ${slide.length + 1} slide`);
    } catch (e) {
      SPS.notif(`${t("Ekspor PowerPoint gagal")}: ${e.message}`);
    } finally { sibuk = false; tombol.disabled = false; }
  }
  tombol.addEventListener("click", ekspor);
  const segarkan = () => { tombol.hidden = !dashboardKini(); };
  window.addEventListener("sps:halaman", segarkan);
  segarkan();
})();
