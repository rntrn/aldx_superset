// ALDx App — Telusuri ke dashboard lain (drill-through, padanan Power BI).
//
//   Saat sebuah dashboard dibuka, tombol "Telusuri" di bilah atas membawa SEMUA filter yang sedang aktif
//   (bilah filter + klik-filter pada chart, mis. klik irisan "Elektronik") ke dashboard lain yang punya filter
//   di kolom bernama sama. Dashboard tujuan terbuka sudah tersaring; chip "Kembali" mengantar pulang.
//
//   Filter aktif dibaca dari halaman dashboard di dalam bingkai (window.__spsFilterAktif, bingkai.js).
//   Dashboard tujuan & nilai filternya dihitung server (/filter-global/api/sasaran): hak akses & RLS tetap berlaku,
//   pengguna hanya melihat dashboard yang memang boleh ia buka.
(function () {
  "use strict";
  const SPS = window.SPS, $ = s => document.querySelector(s);
  const {t} = SPS.i18n, ik = SPS.ikon;
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const tombol = $("#bukaTelusur");
  if (!tombol) return;
  tombol.innerHTML = ik("telusur", 18);

  const panel = document.createElement("div");
  panel.className = "panel-fg panel-telusur"; panel.hidden = true;
  panel.setAttribute("role", "dialog"); panel.setAttribute("aria-label", t("Telusuri ke dashboard lain"));
  document.body.appendChild(panel);
  let asal = null;                                       // {alamat, judul} dashboard sebelum menelusur

  function dashboardKini() {
    const h = SPS.halaman && SPS.halaman(), m = h && (h.alamat || "").match(/^\/superset\/dashboard\/([^/?#]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  }
  // Filter aktif di dashboard yang sedang tampil. {} bila tidak ada / tidak terbaca (fitur tetap aman dipakai).
  function filterAktif() {
    try {
      const w = document.getElementById("bingkai").contentWindow;
      return (w.__spsFilterAktif && w.__spsFilterAktif()) || {};
    } catch (e) { return {}; }
  }
  const ringkas = (k, v) => `${k === "__waktu__" ? t("Waktu") : k}: ` + (typeof v === "string" ? v
    : Array.isArray(v) ? (v.length > 3 ? `${v.slice(0, 3).join(", ")} +${v.length - 3}` : v.join(", "))
    : `${v.min ?? "…"} – ${v.max ?? "…"}`);

  function tutup() { panel.hidden = true; tombol.setAttribute("aria-expanded", "false"); }
  async function buka() {
    const d = dashboardKini(), filter = filterAktif(), kunci = Object.keys(filter);
    panel.innerHTML = `<div class="kepala-fg"><b>${esc(t("Telusuri ke dashboard lain"))}</b></div>` +
      (kunci.length ? `<p class="bantu-fg">${esc(t("Membawa filter yang sedang aktif:"))}</p><div class="bawa-telusur">${kunci.map(k =>
          `<span class="nilai-chip">${esc(ringkas(k, filter[k]))}</span>`).join("")}</div>`
        : `<p class="bantu-fg">${esc(t("Belum ada filter aktif. Klik batang/irisan pada chart atau pilih nilai di bilah filter, lalu buka panel ini lagi."))}</p>`) +
      `<div class="daftar-telusur" id="daftarTelusur"><p class="bantu-fg">${kunci.length ? esc(t("Mencari dashboard yang cocok…")) : ""}</p></div>`;
    panel.hidden = false; tombol.setAttribute("aria-expanded", "true");
    if (!kunci.length) return;
    let sasaran = [];
    try {
      const q = new URLSearchParams({asal: d, filter: JSON.stringify(filter)});
      sasaran = (await (await fetch("/filter-global/api/sasaran?" + q, {credentials: "same-origin"})).json()).sasaran || [];
    } catch (e) { /* tampil sebagai "tidak ada" */ }
    const el = $("#daftarTelusur");
    if (!el) return;
    el.innerHTML = sasaran.length ? sasaran.map((s, i) => `<button type="button" class="item-telusur" data-i="${i}">
        ${ik("dashboard", 18)}<span><b>${esc(s.judul)}</b><small>${esc(t("tersaring"))}: ${esc(s.berlaku.join(", "))}</small></span></button>`).join("")
      : `<p class="bantu-fg">${esc(t("Tidak ada dashboard lain yang punya filter di kolom itu. Tambahkan filter berkolom sama di dashboard tujuan (Studio › Susun dashboard › Tambah filter)."))}</p>`;
    el.querySelectorAll("[data-i]").forEach(b => b.onclick = () => {
      const s = sasaran[+b.dataset.i], h = SPS.halaman();
      asal = {alamat: h.alamat, judul: h.judul, tujuan: s.url, tiba: false};
      tutup();
      SPS.buka(`${s.url}?sps_fg=1&native_filters=${encodeURIComponent(s.native_filters)}`);
    });
  }

  // Chip "Kembali ke <asal>" selama berada di dashboard hasil telusur.
  const chip = document.createElement("button");
  chip.type = "button"; chip.className = "chip-fg lagi kembali-telusur hanya-lebar"; chip.hidden = true;
  tombol.before(chip);
  chip.onclick = () => { const a = asal; asal = null; chip.hidden = true; if (a) SPS.buka(a.alamat); };

  function segarkan() {
    const d = dashboardKini();
    tombol.hidden = !d;
    if (!d) { tutup(); asal = null; }
    // Chip tampil selama berada di dashboard tujuan. Peristiwa halaman bisa datang sebelum alamat baru tercatat,
    // jadi "sudah kembali ke asal" baru dihitung setelah tujuan benar-benar pernah tampil (asal.tiba).
    const jalur = ((SPS.halaman && SPS.halaman()) || {alamat: ""}).alamat.split("?")[0];
    if (asal) {
      const diAsal = jalur === asal.alamat.split("?")[0], diTujuan = jalur === asal.tujuan;
      if (diTujuan) asal.tiba = true;
      else if (!diAsal || asal.tiba) asal = null;            // pindah ke halaman lain, atau sudah pulang
    }
    chip.hidden = !(asal && asal.tiba);
    if (asal) { chip.textContent = `← ${asal.judul || t("Kembali")}`; chip.title = t("Kembali ke dashboard sebelum menelusur"); }
  }
  tombol.addEventListener("click", () => (panel.hidden ? buka() : tutup()));
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !panel.hidden) tutup(); });
  document.addEventListener("click", e => { if (!panel.hidden && e.target.isConnected && !panel.contains(e.target) && !tombol.contains(e.target)) tutup(); });
  window.addEventListener("sps:halaman", segarkan);
  segarkan();
})();
