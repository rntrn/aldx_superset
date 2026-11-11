// ALDx App — Filter global (tombol corong di bilah atas).
//
//   Pengguna memilih kolom (dari filter native dashboard yang boleh ia lihat) & nilainya, mis. Cabang = Cabang Bandung,
//   rentang angka (mis. Tahun 2023–2025) atau rentang waktu (mis. 30 hari terakhir).
//   - Nilai kolom pilihan dipilih dari daftar yang bisa dicari (/filter-global/api/nilai, RLS berlaku) atau diketik.
//   - Filter aktif tampil sebagai chip di bilah atas; × pada chip mencabut filter itu.
//   - "Kecualikan dashboard ini": dashboard yang sedang dibuka tidak diberi filter global (daftar `kecuali`).
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
  const KOSONG = () => ({aktif: true, filter: {}, kecuali: []});

  const baca = () => { try { return {...KOSONG(), ...(JSON.parse(localStorage.getItem(KUNCI) || "null") || {})}; } catch (e) { return KOSONG(); } };
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

  // Chip filter aktif di bilah atas (layar lebar saja; di ponsel cukup lencana angka).
  const bilahChip = document.createElement("div");
  bilahChip.className = "chip-fg-bar hanya-lebar";
  tombol.before(bilahChip);

  const panel = document.createElement("div");
  panel.className = "panel-fg"; panel.hidden = true;
  panel.setAttribute("role", "dialog"); panel.setAttribute("aria-label", t("Filter global"));
  document.body.appendChild(panel);

  async function muatKolom() {
    if (kolom) return kolom;
    try { kolom = (await (await fetch("/filter-global/api/kolom", {credentials: "same-origin"})).json()).kolom || []; }
    catch (e) { kolom = []; }
    return kolom;
  }
  const infoKolom = k => (kolom || []).find(x => x.kolom === k) || {};
  const jenisKolom = k => infoKolom(k).jenis || "pilihan";

  // ---- Ringkasan teks satu filter (untuk chip) ----
  const WAKTU = [["Last day", "Kemarin"], ["Last week", "7 hari terakhir"], ["Last month", "30 hari terakhir"],
                 ["Last quarter", "3 bulan terakhir"], ["Last year", "1 tahun terakhir"], ["", "Tanggal tertentu…"]];
  function ringkas(k, v) {
    const label = k === "__waktu__" ? t("Waktu") : t(infoKolom(k).label || k);
    let isi;
    if (typeof v === "string") isi = t((WAKTU.find(([x]) => x === v) || [, v])[1]);
    else if (Array.isArray(v)) isi = v.length > 2 ? `${v.slice(0, 2).join(", ")} +${v.length - 2}` : v.join(", ");
    else isi = `${v.min ?? "…"} – ${v.max ?? "…"}`;
    return {label, isi};
  }

  // Dashboard yang sedang dibuka di cangkang (id/slug dari alamat), atau null.
  function dashboardKini() {
    const h = SPS.halaman && SPS.halaman(), m = h && (h.alamat || "").match(/^\/superset\/dashboard\/([^/?#]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  }

  function perbaruiBilah() {
    const fg = baca(), n = jumlah(fg), l = tombol.querySelector(".lencana-fg");
    l.hidden = !n; l.textContent = n; tombol.classList.toggle("aktif", n > 0);
    const d = dashboardKini(), kecuali = d && (fg.kecuali || []).includes(d);
    const daftar = fg.aktif ? Object.entries(fg.filter || {}) : [];
    // Ringkas agar judul halaman tetap terbaca: chip berisi nilai saja (nama kolom di tooltip), maks. 2 chip + "+n".
    bilahChip.innerHTML = daftar.slice(0, 2).map(([k, v]) => {
      const r = ringkas(k, v);
      return `<span class="chip-fg${kecuali ? " redup" : ""}" title="${esc(r.label)}: ${esc(r.isi)}">` +
        `<button type="button" class="isi-chip" data-buka>${esc(r.isi)}</button>` +
        `<button type="button" class="cabut-chip" data-cabut="${esc(k)}" aria-label="${esc(t("Hapus"))}">${ik("tutup", 12)}</button></span>`;
    }).join("") + (daftar.length > 2 ? `<button type="button" class="chip-fg lagi" data-buka>+${daftar.length - 2}</button>` : "") +
      (kecuali && daftar.length ? `<span class="catatan-chip">${esc(t("dikecualikan"))}</span>` : "");
  }

  // ---- Isian nilai menurut jenis kolom: pilihan = chip + cari, rentang = min–maks angka, waktu = rentang waktu ----
  let nomorDaftar = 0;
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
    const id = `dlFg${++nomorDaftar}`;
    return `<span class="pilih-fg">${(Array.isArray(nilai) ? nilai : []).map(chipNilai).join("")}` +
      `<input type="text" class="cari-nilai" list="${id}" placeholder="${esc(t("cari atau ketik nilai…"))}" autocomplete="off">` +
      `<datalist id="${id}"></datalist></span>`;
  }
  const chipNilai = v => `<span class="nilai-chip" data-v="${esc(v)}">${esc(v)}<button type="button" class="cabut-nilai" aria-label="${esc(t("Hapus"))}">×</button></span>`;

  function tambahNilai(input) {
    const wadah = input.closest(".pilih-fg"), ada = new Set([...wadah.querySelectorAll(".nilai-chip")].map(c => c.dataset.v));
    input.value.split(",").map(x => x.trim()).filter(x => x && !ada.has(x)).forEach(v => input.insertAdjacentHTML("beforebegin", chipNilai(v)));
    input.value = "";
  }

  // Daftar nilai dari server (dicari saat mengetik, ditunda 250 ms agar tidak membanjiri server).
  let tundaCari = null;
  function muatNilai(input) {
    const k = input.closest(".baris-fg").querySelector("select.kolom").value;
    if (!k || jenisKolom(k) !== "pilihan") return;
    clearTimeout(tundaCari);
    tundaCari = setTimeout(async () => {
      try {
        const q = new URLSearchParams({kolom: k, cari: input.value.trim()});
        const j = await (await fetch("/filter-global/api/nilai?" + q, {credentials: "same-origin"})).json();
        input.nextElementSibling.innerHTML = (j.nilai || []).map(v => `<option value="${esc(v)}"></option>`).join("");
      } catch (e) { /* tetap bisa diketik manual */ }
    }, 250);
  }

  function baris(k = "", nilai = []) {
    const opsi = `<option value="">${esc(t("— pilih kolom —"))}</option>` + kolom.map(x =>
      `<option value="${esc(x.kolom)}" ${x.kolom === k ? "selected" : ""}>${esc(t(x.label))}${x.jenis === "waktu" ? "" : ` (${esc(x.kolom)})`} · ${x.dashboard} ${esc(t("dashboard"))}</option>`).join("");
    return `<div class="baris-fg"><select class="kolom">${opsi}</select><span class="isi-fg">${isianNilai(k, nilai)}</span>` +
      `<button type="button" class="tombol-ikon hapus-fg" aria-label="${esc(t("Hapus"))}">${ik("tutup", 16)}</button></div>`;
  }

  async function buka() {
    await muatKolom();
    const fg = baca(), d = dashboardKini();
    panel.innerHTML = `<div class="kepala-fg"><b>${esc(t("Filter global"))}</b>` +
      `<label><input type="checkbox" id="aktifFg" ${fg.aktif ? "checked" : ""}> ${esc(t("Aktif"))}</label></div>` +
      `<p class="bantu-fg">${esc(t("Berlaku di semua dashboard & Story yang punya filter di kolom yang sama. Hak akses tetap berlaku."))}</p>` +
      (kolom.length ? "" : `<p class="bantu-fg">${esc(t("Belum ada dashboard dengan filter pilihan. Tambahkan filter di dashboard dulu."))}</p>`) +
      `<div id="barisFg">${Object.entries(fg.filter || {}).map(([k, v]) => baris(k, v)).join("") || baris()}</div>` +
      (d ? `<label class="kecuali-fg"><input type="checkbox" id="kecualiFg" ${(fg.kecuali || []).includes(d) ? "checked" : ""}> ` +
           `${esc(t("Kecualikan dashboard ini (jangan terapkan filter global di sini)"))}</label>` : "") +
      `<div class="aksi-fg"><button type="button" class="tombol" id="tambahFg">${ik("tambah", 16)}${esc(t("Tambah"))}</button>` +
      `<button type="button" class="tombol" id="kosongFg">${esc(t("Hapus semua"))}</button>` +
      `<button type="button" class="tombol utama" id="terapkanFg">${esc(t("Terapkan"))}</button></div>`;
    panel.hidden = false;
    tombol.setAttribute("aria-expanded", "true");
  }

  function tutup() { panel.hidden = true; tombol.setAttribute("aria-expanded", "false"); }

  function ambil() {
    const lama = baca(), filter = {};
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
        const cari = b.querySelector(".cari-nilai");
        if (cari.value.trim()) tambahNilai(cari);                 // teks yang belum di-Enter ikut dipakai
        const v = [...b.querySelectorAll(".nilai-chip")].map(c => c.dataset.v);
        if (v.length) filter[k] = [...new Set([...(filter[k] || []), ...v])];
      }
    });
    let kecuali = (lama.kecuali || []).slice();
    const d = dashboardKini(), cek = $("#kecualiFg");
    if (d && cek) kecuali = cek.checked ? [...new Set([...kecuali, d])] : kecuali.filter(x => x !== d);
    return {aktif: $("#aktifFg").checked, filter, kecuali};
  }

  // Muat ulang dashboard yang sedang dibuka tanpa filter lama agar filter global baru dipakai.
  function muatUlang() {
    const h = SPS.halaman && SPS.halaman();
    if (!h || !/^\/superset\/dashboard\//.test(h.alamat)) return;
    const u = new URL(h.alamat, location.origin);
    ["native_filters", "native_filters_key", "sps_fg"].forEach(k => u.searchParams.delete(k));
    SPS.buka(u.pathname + u.search + u.hash);
  }
  const terapkan = fg => { simpan(fg); perbaruiBilah(); tutup(); muatUlang(); };

  tombol.addEventListener("click", () => (panel.hidden ? buka() : tutup()));
  bilahChip.addEventListener("click", e => {
    const cabut = e.target.closest("[data-cabut]");
    if (cabut) {
      const fg = baca();
      delete fg.filter[cabut.dataset.cabut];
      terapkan(fg);
    } else if (e.target.closest("[data-buka]")) buka();
  });
  panel.addEventListener("change", e => {
    if (e.target.matches("select.kolom")) e.target.closest(".baris-fg").querySelector(".isi-fg").innerHTML = isianNilai(e.target.value, null);
    if (e.target.matches("select.preset")) e.target.parentElement.querySelector(".khusus").hidden = !!e.target.value;
  });
  panel.addEventListener("input", e => {
    if (!e.target.matches(".cari-nilai")) return;
    // Memilih dari datalist memicu "input" dengan nilai persis salah satu opsi -> langsung jadi chip.
    const opsi = [...e.target.nextElementSibling.options].map(o => o.value);
    if (e.inputType === "insertReplacementText" || (!e.inputType && opsi.includes(e.target.value))) tambahNilai(e.target);
    else muatNilai(e.target);
  });
  panel.addEventListener("focusin", e => { if (e.target.matches(".cari-nilai")) muatNilai(e.target); });
  panel.addEventListener("keydown", e => {
    if (!e.target.matches(".cari-nilai")) return;
    if (e.key === "Enter" || e.key === ",") { e.preventDefault(); tambahNilai(e.target); }
    else if (e.key === "Backspace" && !e.target.value) {
      const chips = e.target.closest(".pilih-fg").querySelectorAll(".nilai-chip");
      if (chips.length) chips[chips.length - 1].remove();
    }
  });
  panel.addEventListener("click", e => {
    if (e.target.closest(".cabut-nilai")) e.target.closest(".nilai-chip").remove();
    else if (e.target.closest(".pilih-fg")) e.target.closest(".pilih-fg").querySelector(".cari-nilai").focus();
    else if (e.target.closest("#tambahFg")) $("#barisFg").insertAdjacentHTML("beforeend", baris());
    else if (e.target.closest(".hapus-fg")) e.target.closest(".baris-fg").remove();
    else if (e.target.closest("#kosongFg")) terapkan({...KOSONG(), kecuali: baca().kecuali || []});
    else if (e.target.closest("#terapkanFg")) terapkan(ambil());
  });
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !panel.hidden) tutup(); });
  document.addEventListener("click", e => { if (!panel.hidden && e.target.isConnected && !panel.contains(e.target) && !tombol.contains(e.target) && !bilahChip.contains(e.target)) tutup(); });
  // Chip perlu tahu dashboard yang sedang dibuka (catatan "tidak berlaku di sini"): perbarui saat halaman berganti.
  window.addEventListener("sps:halaman", perbaruiBilah);
  muatKolom().then(perbaruiBilah);
  perbaruiBilah();
  // Ambil versi di akun (mis. diatur dari komputer lain) dan jadikan salinan browser.
  fetch("/filter-global/api/milik", {credentials: "same-origin"}).then(r => (r.ok ? r.json() : null)).then(fg => {
    if (fg && JSON.stringify(fg) !== JSON.stringify(baca())) { simpanLokal({...KOSONG(), ...fg}); perbaruiBilah(); }
  }).catch(() => {});
})();
