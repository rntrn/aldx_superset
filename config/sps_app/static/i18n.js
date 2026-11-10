// Bahasa ALDx: id (sumber) · en · ja. Dipakai cangkang /app/ dan halaman ALDx di dalam bingkai.
//
//   await SPS.i18n.siap        kamus bahasa aktif sudah dimuat
//   SPS.i18n.t("Beranda")      -> "Home" (en); teks yang belum ada di kamus tampil apa adanya
//   SPS.i18n.amati(elemen)     terjemahkan teks & atribut (placeholder, title, aria-label) di elemen itu,
//                              termasuk isi yang muncul belakangan (MutationObserver)
//
// Kamus: /app/static/bahasa/<kode>.json  { "teks Indonesia": "terjemahan", ... , "_pola": [[regex, ganti], ...] }
// Halaman bawaan Superset (teks sumber Inggris) memakai /app/static/bahasa/superset-id.json untuk id;
// en & ja memakai terjemahan Superset sendiri. Pilih dengan <script data-kamus="superset">.
// Bahasa disimpan di cookie sps_bahasa (dibaca juga oleh server & halaman di dalam bingkai).
(function () {
  "use strict";
  const BAHASA = {id: "Bahasa Indonesia", en: "English", ja: "日本語"};
  const cookie = (document.cookie.match(/(?:^|; )sps_bahasa=([a-z]{2})/) || [])[1];
  const aktif = BAHASA[cookie] ? cookie : "id";
  let kamus = {}, pola = [];
  const ATRIBUT = ["placeholder", "title", "aria-label"];
  const LEWATI = new Set(["SCRIPT", "STYLE", "TEXTAREA", "CODE", "PRE", "svg", "CANVAS"]);
  // Isi DATA (chart, tabel hasil, editor) tidak pernah diterjemahkan: nilai data harus tampil apa adanya.
  const LEWATI_SEL = ".slice_container,.chart-holder,.ace_editor,.ag-root,table.data,.tabelData," +
                     "#hasil,#grafik,.grafik,.mini,.tabel-ai,.teks-ai,.kode-ai,.pesan-ai.saya,[data-tanpa-terjemah]";
  const skrip = document.currentScript;
  const VERSI = (skrip && new URL(skrip.src).searchParams.get("v")) || "";
  const superset = !!(skrip && skrip.dataset.kamus === "superset");
  const perlu = superset ? aktif === "id" : aktif !== "id";
  const berkas = superset ? `superset-${aktif}` : aktif;

  const siap = !perlu ? Promise.resolve() :
    fetch(`/app/static/bahasa/${berkas}.json?v=${VERSI}`, {credentials: "same-origin"})
      .then(r => (r.ok ? r.json() : {})).catch(() => ({}))
      .then(k => { pola = (k._pola || []).map(([p, g]) => [new RegExp(p), g]); delete k._pola; kamus = k; });

  // Kunci kamus = teks dengan spasi/baris baru dirapatkan (teks HTML sering terpotong baris).
  const rapat = s => s.replace(/\s+/g, " ").trim();
  function t(teks) {
    if (!perlu || !teks) return teks;
    const k = rapat(teks);
    if (kamus[k] !== undefined) return kamus[k];
    for (const [p, g] of pola) if (p.test(k)) return k.replace(p, g);
    return teks;
  }

  function teksNode(n) {
    const asli = n.nodeValue, isi = asli.trim();
    if (!isi || isi.length > 600) return;
    const hasil = t(isi);
    if (hasil !== isi) n.nodeValue = asli.slice(0, asli.indexOf(isi)) + hasil + asli.slice(asli.indexOf(isi) + isi.length);
  }
  function terjemahkan(akar) {
    if (!perlu || !akar) return;
    if (akar.nodeType === 3) return teksNode(akar);
    if (akar.nodeType !== 1 || LEWATI.has(akar.tagName) || akar.closest(LEWATI_SEL)) return;
    const jalan = document.createTreeWalker(akar, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, {
      acceptNode: n => (n.nodeType === 1 && (LEWATI.has(n.tagName) || n.matches(LEWATI_SEL))
        ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT)});
    for (let n = jalan.currentNode; n; n = jalan.nextNode()) {
      if (n.nodeType === 3) teksNode(n);
      else for (const a of ATRIBUT) if (n.hasAttribute(a)) { const v = n.getAttribute(a), h = t(v); if (h !== v) n.setAttribute(a, h); }
    }
  }
  function amati(akar = document.body) {
    if (!perlu) return;
    siap.then(() => {
      terjemahkan(akar);
      document.title = t(document.title.split(" · ")[0]) + (document.title.includes(" · ") ? " · " + document.title.split(" · ").slice(1).join(" · ") : "");
      new MutationObserver(daftar => {
        for (const m of daftar) {
          if (m.type === "characterData") { if (!m.target.parentElement || !m.target.parentElement.closest(LEWATI_SEL)) teksNode(m.target); }
          else m.addedNodes.forEach(terjemahkan);
        }
      }).observe(akar, {childList: true, subtree: true, characterData: true});
    });
  }
  function ganti(kode) {
    document.cookie = `sps_bahasa=${kode}; path=/; max-age=31536000; SameSite=Lax`;
  }

  window.SPS = window.SPS || {};
  window.SPS.i18n = {aktif, BAHASA, siap, t, terjemahkan, amati, ganti};
})();
