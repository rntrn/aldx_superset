// ALDx App — Filter global (tombol corong di bilah atas).
//
//   Pengguna memilih kolom (dari filter native dashboard yang boleh ia lihat) & nilainya, mis. Cabang = Cabang Bandung,
//   rentang angka (mis. Tahun 2023–2025) atau rentang waktu (mis. 30 hari terakhir).
//   Disimpan per akun di server (/filter-global/api/milik) + salinan di browser (localStorage "sps_filter_global",
//   dibaca bingkai.js tanpa menunggu server). Setiap dashboard yang punya filter native di
//   kolom yang sama dibuka dengan nilai itu (bingkai.js -> /filter-global/api/terapkan), juga dashboard di Story.
//   Hak akses & RLS tetap berlaku: filter hanya mempersempit data.
(function () {
  "use strict";
  const SPS = window.SPS, $ = s => document.querySelector(s);
  const {t} = SPS.i18n, ik = SPS.ikon;
  const KUNCI = "sps_filter_global";
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));

  const baca = () => { try { return JSON.parse(localStorage.getItem(KUNCI) || "null") || {aktif: true, filter: {}}; } catch (e) { return {aktif: true, filter: {}}; } };
  const simpanLokal = fg => { try { localStorage.setItem(KUNCI, JSON.stringify(fg)); } catch (e) { /* mode privat: abaikan */ } };
  const simpan = fg => {
    simpanLokal(fg);
    fetch("/filter-global/api/milik", {method: "POST", credentials: "same-origin",
      headers: {"Content-Type": "application/json", "X-CSRFToken": (window.SPS_AWAL || {}).csrf || ""}, body: JSON.stringify(fg)}).catch(() => {});
  };
  const jumlah = fg => (fg.aktif ? Object.keys(fg.filter || {}).length : 0);
  SPS.filterGlobal = {baca, simpan};

  let kolom = null;
  const tombol = $("#bukaFilter");
  if (!tombol) return;
  tombol.innerHTML = ik("corong", 18) + '<span class="lencana-fg" hidden></span>';

  const panel = document.createElement("div");
  panel.className = "panel-fg"; panel.hidden = true;
  panel.setAttribute("role", "dialog"); panel.setAttribute("aria-label", t("Filter global"));
  document.body.appendChild(panel);

  function lencana() {
    const n = jumlah(baca()), l = tombol.querySelector(".lencana-fg");
    l.hidden = !n; l.textContent = n; tombol.classList.toggle("aktif", n > 0);
  }

  async function muatKolom() {
    if (kolom) return kolom;
    try { kolom = (await (await fetch("/filter-global/api/kolom", {credentials: "same-origin"})).json()).kolom || []; }
    catch (e) { kolom = []; }
    return kolom;
  }

  // Isian nilai menurut jenis kolom (F2): pilihan = daftar nilai, rentang = min–maks angka, waktu = rentang waktu.
  const WAKTU = [["Last day", "Kemarin"], ["Last week", "7 hari terakhir"], ["Last month", "30 hari terakhir"],
                 ["Last quarter", "3 bulan terakhir"], ["Last year", "1 tahun terakhir"], ["", "Tanggal tertentu…"]];
  const jenisKolom = k => ((kolom || []).find(x => x.kolom === k) || {}).jenis || "pilihan";
  function isianNilai(k, nilai) {
    const j = jenisKolom(k);
    if (j === "rentang") {
      const v = nilai && !Array.isArray(nilai) ? nilai : {};
      return `<span class="rentang-fg"><input type="number" class="min" value="${esc(v.min ?? "")}" placeholder="${esc(t("dari"))}">` +
             `<input type="number" class="max" value="${esc(v.max ?? "")}" placeholder="${esc(t("sampai"))}"></span>`;
    }
    if (j === "waktu") {
      const v = typeof nilai === "string" ? nilai : "Last month", preset = WAKTU.some(([x]) => x === v);
      return `<span class="waktu-fg"><select class="preset">${WAKTU.map(([x, l]) =>
        `<option value="${esc(x)}" ${(preset ? x === v : !x) ? "selected" : ""}>${esc(t(l))}</option>`).join("")}</select>` +
        `<input type="text" class="khusus" value="${esc(preset ? "" : v)}" placeholder="2025-01-01 : 2025-12-31" ${preset ? "hidden" : ""}></span>`;
    }
    return `<input type="text" class="nilai" value="${esc((Array.isArray(nilai) ? nilai : []).join(", "))}" placeholder="${esc(t("nilai, pisahkan dengan koma"))}">`;
  }
  function baris(k = "", nilai = []) {
    const opsi = `<option value="">${esc(t("— pilih kolom —"))}</option>` + kolom.map(x =>
      `<option value="${esc(x.kolom)}" ${x.kolom === k ? "selected" : ""}>${esc(t(x.label))}${x.jenis === "waktu" ? "" : ` (${esc(x.kolom)})`} · ${x.dashboard} ${esc(t("dashboard"))}</option>`).join("");
    return `<div class="baris-fg"><select class="kolom">${opsi}</select><span class="isi-fg">${isianNilai(k, nilai)}</span>` +
      `<button type="button" class="tombol-ikon hapus-fg" aria-label="${esc(t("Hapus"))}">${ik("tutup", 16)}</button></div>`;
  }

  async function buka() {
    await muatKolom();
    const fg = baca();
    panel.innerHTML = `<div class="kepala-fg"><b>${esc(t("Filter global"))}</b>` +
      `<label><input type="checkbox" id="aktifFg" ${fg.aktif ? "checked" : ""}> ${esc(t("Aktif"))}</label></div>` +
      `<p class="bantu-fg">${esc(t("Berlaku di semua dashboard & Story yang punya filter di kolom yang sama. Hak akses tetap berlaku."))}</p>` +
      (kolom.length ? "" : `<p class="bantu-fg">${esc(t("Belum ada dashboard dengan filter pilihan. Tambahkan filter di dashboard dulu."))}</p>`) +
      `<div id="barisFg">${Object.entries(fg.filter || {}).map(([k, v]) => baris(k, v)).join("") || baris()}</div>` +
      `<div class="aksi-fg"><button type="button" class="tombol" id="tambahFg">${ik("tambah", 16)}${esc(t("Tambah"))}</button>` +
      `<button type="button" class="tombol" id="kosongFg">${esc(t("Hapus semua"))}</button>` +
      `<button type="button" class="tombol utama" id="terapkanFg">${esc(t("Terapkan"))}</button></div>`;
    panel.hidden = false;
    tombol.setAttribute("aria-expanded", "true");
  }

  function tutup() { panel.hidden = true; tombol.setAttribute("aria-expanded", "false"); }

  function ambil() {
    const filter = {};
    panel.querySelectorAll(".baris-fg").forEach(b => {
      const k = b.querySelector("select.kolom").value, j = jenisKolom(k);
      if (!k) return;
      if (j === "rentang") {
        const min = b.querySelector(".min").value, max = b.querySelector(".max").value;
        if (min !== "" || max !== "") filter[k] = {min: min === "" ? null : Number(min), max: max === "" ? null : Number(max)};
      } else if (j === "waktu") {
        const v = b.querySelector(".preset").value || b.querySelector(".khusus").value.trim();
        if (v) filter[k] = v;
      } else {
        const v = b.querySelector(".nilai").value.split(",").map(x => x.trim()).filter(Boolean);
        if (v.length) filter[k] = [...new Set([...(filter[k] || []), ...v])];
      }
    });
    return {aktif: $("#aktifFg").checked, filter};
  }

  // Muat ulang dashboard yang sedang dibuka tanpa filter lama agar filter global baru dipakai.
  function muatUlang() {
    const h = SPS.halaman && SPS.halaman();
    if (!h || !/^\/superset\/dashboard\//.test(h.alamat)) return;
    const u = new URL(h.alamat, location.origin);
    ["native_filters", "native_filters_key", "sps_fg"].forEach(k => u.searchParams.delete(k));
    SPS.buka(u.pathname + u.search + u.hash);
  }

  tombol.addEventListener("click", () => (panel.hidden ? buka() : tutup()));
  panel.addEventListener("change", e => {
    if (e.target.matches("select.kolom")) e.target.closest(".baris-fg").querySelector(".isi-fg").innerHTML = isianNilai(e.target.value, null);
    if (e.target.matches("select.preset")) e.target.parentElement.querySelector(".khusus").hidden = !!e.target.value;
  });
  panel.addEventListener("click", e => {
    if (e.target.closest("#tambahFg")) $("#barisFg").insertAdjacentHTML("beforeend", baris());
    else if (e.target.closest(".hapus-fg")) e.target.closest(".baris-fg").remove();
    else if (e.target.closest("#kosongFg")) { simpan({aktif: true, filter: {}}); lencana(); tutup(); muatUlang(); }
    else if (e.target.closest("#terapkanFg")) { simpan(ambil()); lencana(); tutup(); muatUlang(); }
  });
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !panel.hidden) tutup(); });
  document.addEventListener("click", e => { if (!panel.hidden && e.target.isConnected && !panel.contains(e.target) && !tombol.contains(e.target)) tutup(); });
  lencana();
  // Ambil versi di akun (mis. diatur dari komputer lain) dan jadikan salinan browser.
  fetch("/filter-global/api/milik", {credentials: "same-origin"}).then(r => (r.ok ? r.json() : null)).then(fg => {
    if (fg && JSON.stringify(fg) !== JSON.stringify(baca())) { simpanLokal(fg); lencana(); }
  }).catch(() => {});
})();
