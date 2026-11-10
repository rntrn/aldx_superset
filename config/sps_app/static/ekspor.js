/* ALDx Ekspor — tombol "Ekspor" untuk setiap tabel & grafik di halaman ALDx.
 *
 * Pemakaian di halaman:
 *   <div data-ekspor="Judul berkas"> ...tabel atau grafik... </div>
 *   SPS.ekspor.data(el, {kolom: [...], baris: [[...]]})   // opsional: data mentah (lebih akurat dari teks layar)
 *
 * Tombol muncul otomatis (juga untuk elemen yang dibuat belakangan). Format:
 *   Gambar PNG · PDF (lewat dialog cetak → "Simpan sebagai PDF") · Excel .xlsx (POST /app/api/ekspor)
 *   CSV · TXT (dipisah tab) · Salin ke clipboard
 * Elemen tanpa tabel/data hanya mendapat PNG & PDF.
 */
(function () {
  "use strict";
  const SPS = (window.SPS = window.SPS || {});
  if (SPS.ekspor) return;

  const t = s => (SPS.i18n ? SPS.i18n.t(s) : s);
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const PUSTAKA_GAMBAR = "/app/static/vendor/html-to-image.js";
  let menuTerbuka = null;

  // ---------- Gaya (satu kali per dokumen) ----------
  const gaya = document.createElement("style");
  gaya.textContent = `
[data-ekspor]{position:relative}
.sps-ekspor-tombol{position:absolute;top:6px;right:6px;z-index:5;display:inline-flex;align-items:center;gap:4px;
  font:500 12px/1 var(--sps-font,'Plus Jakarta Sans',system-ui,sans-serif);padding:5px 9px;border-radius:8px;cursor:pointer;
  background:rgba(255,255,255,.92);color:#334155;border:1px solid rgba(15,23,42,.12);box-shadow:0 1px 2px rgba(15,23,42,.06);
  opacity:.55;transition:opacity .16s,background .16s}
[data-ekspor]:hover>.sps-ekspor-tombol,.sps-ekspor-tombol:focus-visible,.sps-ekspor-tombol[aria-expanded=true]{opacity:1}
.sps-ekspor-tombol span{display:none}
[data-ekspor]:hover>.sps-ekspor-tombol span,.sps-ekspor-tombol:focus-visible span,.sps-ekspor-tombol[aria-expanded=true] span{display:inline}
.sps-ekspor-tombol:hover{background:#fff}
.sps-ekspor-menu{position:fixed;z-index:2147483000;min-width:200px;padding:6px;border-radius:12px;background:#fff;
  border:1px solid rgba(15,23,42,.1);box-shadow:0 12px 32px rgba(15,23,42,.18);font:13px/1.3 var(--sps-font,'Plus Jakarta Sans',system-ui,sans-serif);
  animation:spsEksporMuncul .16s cubic-bezier(.2,.8,.2,1)}
.sps-ekspor-menu button{display:flex;justify-content:space-between;gap:16px;width:100%;border:0;background:none;padding:8px 10px;
  border-radius:8px;cursor:pointer;color:#1e293b;font:inherit;text-align:left}
.sps-ekspor-menu button:hover,.sps-ekspor-menu button:focus-visible{background:#f1f5f9;outline:none}
.sps-ekspor-menu small{color:#94a3b8}
.sps-ekspor-notif{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:2147483000;background:#0f172a;color:#fff;
  padding:9px 16px;border-radius:10px;font:13px var(--sps-font,system-ui,sans-serif);box-shadow:0 8px 24px rgba(0,0,0,.25)}
@keyframes spsEksporMuncul{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){.sps-ekspor-menu{animation:none}}
@media print{.sps-ekspor-tombol{display:none}}
@media (hover:none){.sps-ekspor-tombol{opacity:1}}`;
  document.head.appendChild(gaya);

  function notif(teks) {
    const n = document.createElement("div");
    n.className = "sps-ekspor-notif"; n.textContent = teks; document.body.appendChild(n);
    setTimeout(() => n.remove(), 2600);
  }

  // ---------- Mengambil data dari elemen ----------
  function tabelDari(el) {
    if (el._spsData && el._spsData.kolom) return el._spsData;
    const tabel = el.matches("table") ? el : el.querySelector("table");
    if (!tabel) return null;
    const barisEl = [...tabel.rows].filter(r => r.offsetParent !== null || !tabel.offsetParent);
    if (!barisEl.length) return null;
    const teks = c => c.innerText.replace(/\s+/g, " ").trim();
    const kepala = tabel.tHead && tabel.tHead.rows.length ? tabel.tHead.rows[tabel.tHead.rows.length - 1]
      : (barisEl[0].querySelector("th") ? barisEl[0] : null);
    const kolom = kepala ? [...kepala.cells].map(teks) : [...barisEl[0].cells].map((_, i) => "Kolom " + (i + 1));
    const baris = barisEl.filter(r => r !== kepala && !(tabel.tHead && tabel.tHead.contains(r)))
      .map(r => [...r.cells].map(teks)).filter(b => b.some(Boolean));
    return {kolom, baris};
  }

  function judulDari(el) { return el.dataset.ekspor || document.title.split("·")[0].trim() || "data"; }
  function namaBerkas(judul, akhiran) {
    const d = new Date(), dua = n => String(n).padStart(2, "0");
    const cap = `${d.getFullYear()}${dua(d.getMonth() + 1)}${dua(d.getDate())}_${dua(d.getHours())}${dua(d.getMinutes())}`;
    return `${(judul.replace(/[^\w\- ]+/g, "").trim().replace(/\s+/g, "_") || "data").slice(0, 60)}_${cap}.${akhiran}`;
  }
  function unduh(isi, nama, jenis) {
    const url = isi instanceof Blob ? URL.createObjectURL(isi) : isi;
    const a = Object.assign(document.createElement("a"), {href: url, download: nama});
    document.body.appendChild(a); a.click(); a.remove();
    if (isi instanceof Blob) setTimeout(() => URL.revokeObjectURL(url), 4000);
  }

  // ---------- Format ----------
  const sel = v => { const s = String(v ?? ""); return /[",\n;]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  function csv(d) { return "﻿" + [d.kolom, ...d.baris].map(b => b.map(sel).join(",")).join("\r\n"); }
  function tsv(d) { return [d.kolom, ...d.baris].map(b => b.map(v => String(v ?? "").replace(/[\t\n]/g, " ")).join("\t")).join("\r\n"); }

  function muatPustaka() {
    if (window.htmlToImage) return Promise.resolve(window.htmlToImage);
    return new Promise((ok, gagal) => {
      const s = document.createElement("script");
      s.src = PUSTAKA_GAMBAR; s.onload = () => ok(window.htmlToImage); s.onerror = () => gagal(new Error("pustaka gambar gagal dimuat"));
      document.head.appendChild(s);
    });
  }
  async function png(el) {
    const lib = await muatPustaka();
    // Elemen bergulir (tabel panjang) difoto utuh, bukan hanya bagian yang terlihat.
    return lib.toPng(el, {pixelRatio: 2, backgroundColor: "#ffffff", cacheBust: true, skipFonts: true,
      width: el.scrollWidth, height: el.scrollHeight, style: {maxHeight: "none", height: el.scrollHeight + "px", overflow: "visible"},
      filter: n => !(n.classList && n.classList.contains("sps-ekspor-tombol"))});
  }

  function cetak(judul, isiHtml) {
    const f = document.createElement("iframe");
    f.style.cssText = "position:fixed;width:0;height:0;border:0;right:0;bottom:0";
    document.body.appendChild(f);
    const doc = f.contentDocument;
    doc.open();
    doc.write(`<!doctype html><html><head><meta charset="utf-8"><title>${esc(judul)}</title><style>
      body{font:12px/1.4 'Plus Jakarta Sans','Segoe UI',Arial,sans-serif;color:#0f172a;margin:24px}
      h1{font-size:18px;margin:0 0 2px}p.ket{color:#64748b;margin:0 0 14px}
      table{border-collapse:collapse;width:100%}th{background:#1e2a44;color:#fff;text-align:left}
      th,td{padding:5px 8px;border-bottom:1px solid #e2e8f0}tr{break-inside:avoid}img{max-width:100%}
      @page{margin:14mm}</style></head><body><h1>${esc(judul)}</h1>
      <p class="ket">${esc(t("Dicetak"))} ${new Date().toLocaleString()}</p>${isiHtml}</body></html>`);
    doc.close();
    const jalan = () => { f.contentWindow.focus(); f.contentWindow.print(); setTimeout(() => f.remove(), 60000); };
    const img = doc.querySelector("img");
    if (img && !img.complete) img.onload = jalan; else setTimeout(jalan, 50);
  }
  const tabelHtml = d => `<table><thead><tr>${d.kolom.map(k => `<th>${esc(k)}</th>`).join("")}</tr></thead><tbody>` +
    d.baris.map(b => `<tr>${b.map(v => `<td>${esc(v)}</td>`).join("")}</tr>`).join("") + "</tbody></table>";

  async function xlsx(judul, d) {
    const r = await fetch("/app/api/ekspor", {method: "POST", credentials: "same-origin",
      headers: {"Content-Type": "application/json"}, body: JSON.stringify({judul, ...d})});
    if (!r.ok) { const j = await r.json().catch(() => ({})); throw new Error(j.error || "Excel gagal dibuat (" + r.status + ")"); }
    return r.blob();
  }

  // ---------- Aksi ----------
  async function jalankan(aksi, el) {
    const judul = judulDari(el), d = tabelDari(el);
    try {
      if (aksi === "png") unduh(await png(el), namaBerkas(judul, "png"));
      if (aksi === "pdf") cetak(judul, d && !el.querySelector("canvas,svg:not(.ikon)") ? tabelHtml(d) : `<img src="${await png(el)}">`);
      if (aksi === "xlsx") { notif(t("Menyiapkan Excel…")); unduh(await xlsx(judul, d), namaBerkas(judul, "xlsx")); }
      if (aksi === "csv") unduh(new Blob([csv(d)], {type: "text/csv;charset=utf-8"}), namaBerkas(judul, "csv"));
      if (aksi === "txt") unduh(new Blob([judul + "\r\n\r\n" + tsv(d)], {type: "text/plain;charset=utf-8"}), namaBerkas(judul, "txt"));
      if (aksi === "salin") { await navigator.clipboard.writeText(tsv(d)); notif(t("Tersalin, tempel di Excel dengan Ctrl + V")); }
    } catch (e) {
      notif(t("Ekspor gagal") + ": " + e.message);
    }
  }

  const PILIHAN = [
    ["png", "Gambar", "PNG", false], ["pdf", "PDF / cetak", "PDF", false], ["xlsx", "Excel", "XLSX", true],
    ["csv", "CSV", "CSV", true], ["txt", "Teks", "TXT", true], ["salin", "Salin tabel", "Ctrl V", true],
  ];

  function tutupMenu() {
    if (!menuTerbuka) return;
    menuTerbuka.tombol.setAttribute("aria-expanded", "false"); menuTerbuka.menu.remove(); menuTerbuka = null;
  }
  function bukaMenu(tombol, el) {
    if (menuTerbuka && menuTerbuka.tombol === tombol) return tutupMenu();
    tutupMenu();
    const adaTabel = !!tabelDari(el);
    const menu = document.createElement("div");
    menu.className = "sps-ekspor-menu"; menu.setAttribute("role", "menu");
    menu.innerHTML = PILIHAN.filter(p => adaTabel || !p[3]).map(([k, label, ket]) =>
      `<button role="menuitem" data-aksi="${k}"><span>${esc(t(label))}</span><small>${esc(ket)}</small></button>`).join("");
    document.body.appendChild(menu);
    const r = tombol.getBoundingClientRect(), lebar = menu.offsetWidth, tinggi = menu.offsetHeight;
    menu.style.left = Math.max(8, Math.min(r.right - lebar, innerWidth - lebar - 8)) + "px";
    menu.style.top = (r.bottom + 6 + tinggi > innerHeight ? Math.max(8, r.top - tinggi - 6) : r.bottom + 6) + "px";
    menu.onclick = e => { const b = e.target.closest("[data-aksi]"); if (b) { tutupMenu(); jalankan(b.dataset.aksi, el); } };
    menu.onkeydown = e => {
      const tombolMenu = [...menu.querySelectorAll("button")], i = tombolMenu.indexOf(document.activeElement);
      if (e.key === "ArrowDown") { e.preventDefault(); tombolMenu[(i + 1) % tombolMenu.length].focus(); }
      if (e.key === "ArrowUp") { e.preventDefault(); tombolMenu[(i - 1 + tombolMenu.length) % tombolMenu.length].focus(); }
      if (e.key === "Escape") { tutupMenu(); tombol.focus(); }
    };
    tombol.setAttribute("aria-expanded", "true");
    menuTerbuka = {tombol, menu};
    menu.querySelector("button").focus();
  }

  function pasangSatu(el) {
    if ([...el.children].some(c => c.classList.contains("sps-ekspor-tombol"))) return;   // isi bisa diganti innerHTML
    const b = document.createElement("button");
    b.type = "button"; b.className = "sps-ekspor-tombol"; b.setAttribute("aria-haspopup", "menu");
    b.title = t("Ekspor: gambar, PDF, Excel, CSV, TXT");
    b.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v12M7 10l5 5 5-5M5 21h14"/></svg><span>${esc(t("Ekspor"))}</span>`;
    b.onclick = e => { e.stopPropagation(); bukaMenu(b, el); };
    el.appendChild(b);
  }
  function pasang(akar = document) {
    if (akar.matches && akar.matches("[data-ekspor]")) pasangSatu(akar);
    akar.querySelectorAll && akar.querySelectorAll("[data-ekspor]").forEach(pasangSatu);
  }

  document.addEventListener("click", e => { if (menuTerbuka && !menuTerbuka.menu.contains(e.target)) tutupMenu(); });
  addEventListener("scroll", tutupMenu, true);
  addEventListener("resize", tutupMenu);
  new MutationObserver(m => m.forEach(x => {
    x.addedNodes.forEach(n => n.nodeType === 1 && pasang(n));
    if (x.target.matches && x.target.matches("[data-ekspor]")) pasangSatu(x.target);
  }))
    .observe(document.documentElement, {childList: true, subtree: true});
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => pasang());
  else pasang();

  SPS.ekspor = {pasang, data: (el, d) => { el._spsData = d; }, jalankan};
})();
