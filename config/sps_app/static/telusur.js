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
      `<div class="daftar-telusur" id="daftarTelusur"><p class="bantu-fg">${kunci.length ? esc(t("Mencari dashboard yang cocok…")) : ""}</p></div>` +
      `<div class="kepala-fg" style="margin-top:12px"><b>${esc(t("Tampilan tersimpan"))}</b></div>` +
      (kunci.length ? `<form class="simpan-tampilan" id="formTampilan"><input id="namaTampilan" maxlength="80" autocomplete="off"
          placeholder="${esc(t("Nama tampilan, mis. Elektronik Jawa"))}"><button class="tombol" type="submit">${esc(t("Simpan tampilan ini"))}</button></form>` : "") +
      `<div class="daftar-telusur" id="daftarTampilan"></div>`;
    panel.hidden = false; tombol.setAttribute("aria-expanded", "true");
    tampilan(d, filter);
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

  // Tampilan tersimpan (bookmark): keadaan filter dashboard ini disimpan dengan nama, per akun.
  // Klik = dashboard yang sama dibuka dengan filter itu terpasang. Disimpan di server (/filter-global/api/tampilan).
  const kirim = (alamat, isi) => fetch(alamat, {method: "POST", credentials: "same-origin",
    headers: {"Content-Type": "application/json", "X-CSRFToken": (window.SPS_AWAL || {}).csrf || ""}, body: JSON.stringify(isi)}).then(r => r.json());
  async function tampilan(d, filter) {
    const el = $("#daftarTampilan");
    const gambar = (daftar, url) => {
      el.innerHTML = daftar.length ? daftar.map((s, i) => `<div class="baris-tampilan"><button type="button" class="item-telusur" data-t="${i}">
          ${ik("corong", 18)}<span><b>${esc(s.nama)}</b><small>${esc(Object.keys(s.filter).map(k => ringkas(k, s.filter[k])).join(" · "))}</small></span></button>
          <button type="button" class="hapus-tampilan" data-h="${s.id}" title="${esc(t("Hapus tampilan"))}" aria-label="${esc(t("Hapus tampilan"))}">×</button></div>`).join("")
        : `<p class="bantu-fg">${esc(t("Belum ada. Atur filter di dashboard ini, lalu simpan dengan nama agar bisa dibuka lagi dengan satu klik."))}</p>`;
      el.querySelectorAll("[data-t]").forEach(b => b.onclick = () => {
        const s = daftar[+b.dataset.t];
        tutup();
        SPS.buka(s.native_filters ? `${url}?sps_fg=1&native_filters=${encodeURIComponent(s.native_filters)}` : url);
      });
      el.querySelectorAll("[data-h]").forEach(b => b.onclick = async () => {
        await kirim("/filter-global/api/tampilan/hapus", {id: +b.dataset.h}).catch(() => 0);
        tampilan(d, filter);
      });
    };
    let url = "";
    try {
      const j = await (await fetch("/filter-global/api/tampilan?dashboard=" + encodeURIComponent(d), {credentials: "same-origin"})).json();
      url = j.url; gambar(j.tampilan || [], url);
    } catch (e) { el.innerHTML = ""; }
    const form = $("#formTampilan");
    if (form) form.onsubmit = async e => {
      e.preventDefault();
      const j = await kirim("/filter-global/api/tampilan", {dashboard: d, nama: $("#namaTampilan").value, filter}).catch(() => ({error: t("Gagal menyimpan")}));
      if (j.error) { SPS.notif ? SPS.notif(j.error, true) : alert(j.error); return; }
      $("#namaTampilan").value = ""; gambar(j.tampilan || [], url);
    };
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
  // Menu klik kanan chart di dashboard (bingkai.js) meminta panel ini dibuka.
  window.addEventListener("message", e => { if (e.origin === location.origin && e.data && e.data.sps === "telusur" && dashboardKini()) buka(); });
  window.addEventListener("sps:halaman", segarkan);
  segarkan();
})();
