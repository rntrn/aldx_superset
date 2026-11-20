// Skrip di SETIAP halaman Superset & ALDx (disisipkan sps_app.tampilan). Hanya bekerja bila halaman tampil
// di dalam cangkang /app/:
//   - sembunyikan navbar Superset & kepala halaman ALDx (judul & menu sudah ada di cangkang)
//   - laporkan alamat & judul ke cangkang (termasuk perpindahan halaman SPA Superset)
//   - teruskan pintasan cangkang (Ctrl+K, Ctrl+I, ?, g lalu huruf, Esc, Ctrl+\) agar tetap jalan saat fokus di halaman
//   - tab yang punya item menu sendiri (MANDIRI) tampil sebagai halaman tersendiri; ?tab=<nama> membuka tab
//   - terjemahan: halaman ALDx memakai kamus ALDx; halaman Superset memakai kamus "superset" (Indonesia)
//   - filter global: dashboard dibuka dengan filter global pengguna (tombol corong di cangkang)
//   - petunjuk singkat di halaman Superset yang membingungkan (buat dataset, buat chart, Explore) + jalan pintas
//     ke Studio Visual yang menyarankan dimensi & ukuran otomatis
(function () {
  "use strict";
  // ---- Filter global (sps_filter_global.py): juga di luar cangkang, mis. dashboard di halaman Story ----
  const KUNCI_FG = "sps_filter_global";
  window.__spsFilterGlobal = function () {
    const m = location.pathname.match(/^\/superset\/dashboard\/([^/]+)\/?$/);
    if (!m || window.__spsFgTerakhir === location.pathname) return;
    window.__spsFgTerakhir = location.pathname;
    const p = new URLSearchParams(location.search);
    if (p.has("native_filters") || p.has("native_filters_key") || p.has("sps_fg")) return;   // sudah / diatur pengguna
    let fg = null;
    try { fg = JSON.parse(localStorage.getItem(KUNCI_FG) || "null"); } catch (e) { return; }
    if (!fg || !fg.aktif || !Object.keys(fg.filter || {}).length) return;
    const q = new URLSearchParams({dashboard: decodeURIComponent(m[1]), filter: JSON.stringify(fg.filter),
                                   kecuali: JSON.stringify(fg.kecuali || [])});
    fetch("/filter-global/api/terapkan?" + q, {credentials: "same-origin"}).then(r => (r.ok ? r.json() : null)).then(j => {
      if (!j || !j.native_filters) return;
      p.set("native_filters", j.native_filters);
      p.set("sps_fg", "1");
      location.replace(location.pathname + "?" + p + location.hash);
    }).catch(() => {});
  };
  window.__spsFilterGlobal();

  // ---- Telusuri ke dashboard lain (telusur.js): filter yang sedang aktif di dashboard ini ----
  // Dibaca dari state halaman (dataMask Superset): filter di bilah filter + klik-filter pada chart.
  // Hasil: {kolom: [nilai] | {min, max}, "__waktu__": "Last month"}; {} bila tidak ada / struktur Superset berubah.
  window.__spsFilterAktif = function () {
    try {
      const akar = document.getElementById("app");
      const kunci = akar && Object.keys(akar).find(k => k.startsWith("__reactContainer"));
      if (!kunci) return {};
      const antre = [akar[kunci]];
      let toko = null, n = 0;
      while (antre.length && n < 4000 && !toko) {             // cari Provider redux di pohon React (dangkal)
        const x = antre.shift(); n++;
        if (!x) continue;
        const p = x.memoizedProps;
        if (p && p.store && typeof p.store.getState === "function") toko = p.store;
        if (x.child) antre.push(x.child);
        if (x.sibling) antre.push(x.sibling);
      }
      const hasil = {};
      Object.values((toko && toko.getState().dataMask) || {}).forEach(m => {
        const e = (m && m.extraFormData) || {};
        (e.filters || []).forEach(f => {
          if (typeof f.col !== "string") return;               // kolom rumus (adhoc) tidak dibawa
          const k = f.col.toLowerCase();
          if (f.op === "IN" && Array.isArray(f.val)) hasil[k] = [...new Set([...(Array.isArray(hasil[k]) ? hasil[k] : []), ...f.val])];
          else if (f.op === "==" || f.op === "=") hasil[k] = [f.val];
          else if (f.op === ">=" || f.op === "<=") {
            const r = hasil[k] && !Array.isArray(hasil[k]) ? hasil[k] : {min: null, max: null};
            r[f.op === ">=" ? "min" : "max"] = f.val; hasil[k] = r;
          }
        });
        if (e.time_range && e.time_range !== "No filter") hasil.__waktu__ = e.time_range;
      });
      return hasil;
    } catch (e) { return {}; }
  };

  let induk;
  try { induk = window.parent !== window && window.parent.location.pathname.startsWith("/app") ? window.parent : null; }
  catch (e) { induk = null; }
  if (!induk || window.__spsBingkai) return;
  window.__spsBingkai = true;

  // ---- Klik kanan chart di dashboard -> "Telusuri ke dashboard lain…" ----
  // Butir ditambahkan ke menu klik kanan bawaan chart. Saat dipilih: nilai yang diklik dijadikan klik-filter
  // (bila chart mendukung), lalu panel Telusuri di cangkang dibuka dengan filter itu (telusur.js).
  if (location.pathname.startsWith("/superset/dashboard/")) {
    const TEKS = {id: "Telusuri ke dashboard lain…", en: "Drill through to another dashboard…", ja: "別のダッシュボードへドリルスルー…"};
    const sisipkan = menu => {
      const daftar = menu.querySelector("ul.ant-dropdown-menu");
      if (!daftar || daftar.querySelector("[data-sps-telusur]")) return;
      const butir = document.createElement("li");
      butir.className = "ant-dropdown-menu-item ant-dropdown-menu-item-only-child"; butir.setAttribute("role", "menuitem");
      butir.dataset.spsTelusur = "1";
      butir.innerHTML = '<span class="ant-dropdown-menu-title-content"></span>';
      butir.firstChild.textContent = TEKS[(document.documentElement.lang || "id").slice(0, 2)] || TEKS.id;
      butir.onmouseenter = () => butir.classList.add("ant-dropdown-menu-item-active");
      butir.onmouseleave = () => butir.classList.remove("ant-dropdown-menu-item-active");
      butir.onclick = () => {
        const silang = daftar.querySelector('[data-menu-id$="cross-filtering-menu-item"]');
        const bisa = silang && !silang.classList.contains("ant-dropdown-menu-item-disabled") && !/hapus|remove|解除|削除/i.test(silang.textContent);
        if (bisa) silang.click();                              // menu menutup sendiri
        else daftar.dispatchEvent(new KeyboardEvent("keydown", {key: "Escape", keyCode: 27, which: 27, bubbles: true}));   // tutup menu
        setTimeout(() => induk.postMessage({sps: "telusur"}, location.origin), bisa ? 600 : 0);   // tunggu klik-filter tercatat
      };
      daftar.appendChild(butir);
    };
    new MutationObserver(() => document.querySelectorAll('[data-test="chart-context-menu"]').forEach(sisipkan))
      .observe(document.body, {childList: true, subtree: true});
  }
  const VERSI = new URL(document.currentScript.src).searchParams.get("v") || "";
  const halamanSps = !document.getElementById("app");
  document.documentElement.classList.add("sps-bingkai");

  // ---- Studio Visual = satu-satunya tempat membangun & mengedit chart ----
  //   /chart/add, /chart/list            -> Studio (chart baru / daftar chart ada di Studio)
  //   /explore/ dari dataset (chart baru) -> Studio dengan dataset itu
  //   /explore/?slice_id=N               -> Studio bila chart N buatan Studio; chart lain tetap di Explore
  //   ...&lanjutan=1                     -> Mode lanjutan: tetap di Explore (diingat per chart selama sesi)
  (function arahkanKeStudio() {
    if (halamanSps) return;
    const p = location.pathname, q = new URLSearchParams(location.search);
    const kunciLanjutan = id => "sps_lanjutan_" + id;
    if (/^\/chart\/(add|list)/.test(p)) {
      const ds = q.get("dataset") || q.get("datasource_id");
      location.replace("/studio/" + (/^\d+$/.test(ds || "") ? "?dataset=" + ds : ""));
      return;
    }
    if (!/^\/explore\/?$/.test(p)) return;
    const slice = q.get("slice_id");
    if (q.get("lanjutan") === "1") {
      if (slice) try { sessionStorage.setItem(kunciLanjutan(slice), "1"); } catch (e) { /* mode privat */ }
      return;
    }
    if (/^\d+$/.test(slice || "")) {
      try { if (sessionStorage.getItem(kunciLanjutan(slice))) return; } catch (e) { /* mode privat */ }
      fetch(`/studio/api/lembar/${slice}`, {credentials: "same-origin"})
        .then(r => { if (r.ok) location.replace(`/studio/?chart=${slice}`); }).catch(() => {});
      return;
    }
    const ds = q.get("datasource_id") || (q.get("datasource") || "").split("__")[0];
    if (!q.get("form_data_key") && !q.get("form_data") && /^\d+$/.test(ds)) location.replace(`/studio/?dataset=${ds}`);
  })();

  const gaya = document.createElement("style");
  gaya.textContent = `
    html.sps-bingkai #main-menu, html.sps-bingkai header.sps-hiasan, html.sps-bingkai .spsNav,
    html.sps-bingkai body > .navbar.navbar-inverse{display:none!important}
    html.sps-bingkai body > .container, html.sps-bingkai body > .container-fluid{padding-top:12px}
    html.sps-bingkai body::before{display:none!important}
    html.sps-bingkai, html.sps-bingkai body{background:var(--sps-latar,#F4F4F5)}
    /* Tombol sekunder Superset (Pilih banyak, Ubah dashboard): garis tepi, bukan abu gelap yang tampak nonaktif */
    html.sps-bingkai .superset-button-secondary:not(:disabled){background:#fff!important;color:var(--sps-utama,#18181B)!important;
      border:1px solid var(--sps-utama,#18181B)!important}
    html.sps-bingkai .superset-button-secondary:not(:disabled):hover{background:var(--sps-utama-muda,#E8E8E8)!important}
    /* Tombol tambahan ALDx di kepala dashboard (Riwayat versi, Tata ponsel): ukuran sama dengan tombol Superset */
    html.sps-bingkai .sps-versi, html.sps-bingkai .sps-ponsel-atur, html.sps-bingkai .sps-filter-tambah{height:32px;padding:0 14px;border-radius:var(--sps-sudut,8px);
      font:600 13px/30px var(--sps-font,inherit);cursor:pointer;white-space:nowrap}
    /* Judul dashboard memakai ruang yang ada (tidak terpotong lebih awal) */
    html.sps-bingkai .title-panel > div:first-child{flex:0 1 auto!important;max-width:none!important;min-width:120px}
    html.sps-bingkai .title-panel input.ant-input{field-sizing:content;width:auto!important;max-width:100%!important;text-overflow:ellipsis}
    html.sps-bingkai .title-panel > div:nth-child(2){flex:0 1 auto;min-width:0;overflow:hidden}
    /* Tata letak ponsel yang diatur pemilik: semua chart jadi satu daftar berurutan (urutan via style.order) */
    html.sps-tata-ponsel .grid-content{display:flex!important;flex-direction:column}
    html.sps-tata-ponsel .grid-content .dragdroppable-row,html.sps-tata-ponsel .grid-content .dragdroppable-row > .with-popover-menu,
    html.sps-tata-ponsel .grid-content .grid-row{display:contents!important}
    /* Explore (editor chart) punya lebar minimum 300 + 320 + 512 px: di bingkai yang lebih sempit (layar kecil, panel AI
       terbuka) chart terdorong keluar & terpotong di kanan. Sedang: panel kiri dipersempit. Sempit: chart di atas, lalu
       sumber data & kontrol bertumpuk di bawahnya (digulir). */
    @media (min-width:901px) and (max-width:1180px){
      html.sps-bingkai .explore-column.data-source-selection{min-width:220px!important;width:220px!important;flex:0 0 220px!important}
      html.sps-bingkai .explore-column.controls-column{min-width:280px!important;width:280px!important;flex:0 0 280px!important}
      html.sps-bingkai .main-explore-content{min-width:0!important}
    }
    @media (max-width:900px){
      html.sps-bingkai div:has(> .main-explore-content){flex-direction:column!important;overflow-y:auto!important;overflow-x:hidden!important}
      html.sps-bingkai div:has(> .main-explore-content) > *{width:100%!important;min-width:0!important;max-width:100%!important;flex:none!important}
      html.sps-bingkai .main-explore-content{order:-1;height:62vh;min-height:340px}
      html.sps-bingkai .explore-column.controls-column{height:auto!important;min-height:70vh}
      html.sps-bingkai .explore-column.data-source-selection{height:50vh!important}
    }
    @media (max-width:760px){                      /* ponsel: kotak dashboard bertumpuk satu kolom */
      html.sps-bingkai .sps-versi,html.sps-bingkai .sps-ponsel-atur,html.sps-bingkai .sps-filter-tambah{display:none!important}
      html.sps-bingkai .dashboard .grid-row{flex-direction:column!important;flex-wrap:nowrap!important}
      html.sps-bingkai .dashboard .grid-row > *{width:100%!important;max-width:100%!important;margin-right:0!important}
      html.sps-bingkai .dashboard .grid-row .resizable-container{width:100%!important;max-width:100%!important}
    }`;
  document.head.appendChild(gaya);

  // ---- Lapor alamat & judul ----
  let ruteTerakhir = "";
  const lapor = () => {
    induk.postMessage({sps: "rute", alamat: location.pathname + location.search + location.hash, judul: document.title}, location.origin);
    if (!halamanSps && location.pathname !== ruteTerakhir) {
      ruteTerakhir = location.pathname; setTimeout(petunjuk, 600); window.__spsFilterGlobal(); lipatFilterPonsel(); tabSqlOtomatis();
      tombolVersi(); tataPonsel(); notifFilterBaru();
    }
  };
  for (const f of ["pushState", "replaceState"]) {
    const asli = history[f];
    history[f] = function () { const h = asli.apply(this, arguments); setTimeout(lapor); return h; };
  }
  window.addEventListener("popstate", () => setTimeout(lapor));
  new MutationObserver(() => lapor()).observe(document.querySelector("title") || document.head, {childList: true, characterData: true, subtree: true});

  // ---- Pintasan diteruskan ke cangkang ----
  const mengetik = el => el && (/^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName) || el.isContentEditable || !!el.closest(".ace_editor, .monaco-editor"));
  document.addEventListener("keydown", e => {
    const mod = e.ctrlKey || e.metaKey, k = e.key;
    const milikCangkang = (mod && (k.toLowerCase() === "k" || k.toLowerCase() === "i" || k === "\\")) || (!mod && !e.altKey && ["?", "g", "Escape", "h", "d", "c", "s", "k", "q", "t", "y"].includes(k));
    if (!milikCangkang) return;
    induk.postMessage({sps: "tombol", key: k, ctrlKey: e.ctrlKey, metaKey: e.metaKey, altKey: e.altKey, mengetik: mengetik(document.activeElement)}, location.origin);
    if (mod) e.preventDefault();
  }, true);

  // ---- Tab mandiri & ?tab= (halaman ALDx) ----
  const MANDIRI = {hubungkan: "Hubungkan data", ekstrak: "Ekstrak ke ALDx Engine", prep: "Persiapan data", story: "Story"};
  // Satu pintu Asisten AI (U23): di cangkang, tanya-jawab memakai panel ✦ (Ctrl + I); halaman /asisten/ hanya Auto chart.
  const TERSEMBUNYI = location.pathname.startsWith("/asisten") ? {tanya: true} : {};
  function aturTab() {
    const baris = document.querySelector("nav.tab");
    if (!baris) return;
    const aktif = baris.querySelector("button.aktif"), mandiri = aktif && MANDIRI[aktif.dataset.tab];
    baris.querySelectorAll("button").forEach(b => {
      b.style.display = (!mandiri && MANDIRI[b.dataset.tab]) || TERSEMBUNYI[b.dataset.tab] ? "none" : "";
    });
    const tampak = [...baris.querySelectorAll("button")].filter(b => b.style.display !== "none").length;
    baris.style.display = mandiri || tampak <= 1 ? "none" : "";
  }
  function pasangTab() {
    const baris = document.querySelector("nav.tab");
    if (!baris) return;
    baris.querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
      setTimeout(aturTab);
      // Tab biasa: alamat ikut berubah agar Muat ulang / Buka di tab baru membuka tab yang sama.
      const u = new URL(location.href); u.searchParams.set("tab", b.dataset.tab); history.replaceState(null, "", u);
    }));
    const minta = new URLSearchParams(location.search).get("tab");
    const tombol = minta && baris.querySelector(`button[data-tab="${CSS.escape(minta)}"]`);
    if (tombol) tombol.click();
    else if (MANDIRI[(baris.querySelector("button.aktif") || {}).dataset?.tab] ||
             TERSEMBUNYI[(baris.querySelector("button.aktif") || {}).dataset?.tab]) {
      const pertama = [...baris.querySelectorAll("button")].find(b => !MANDIRI[b.dataset.tab] && !TERSEMBUNYI[b.dataset.tab]);
      pertama && pertama.click();
    }
    aturTab();
    if (TERSEMBUNYI.tanya && document.getElementById("auto") && !document.getElementById("spsPintuAi")) {
      const k = document.createElement("div");
      k.id = "spsPintuAi"; k.className = "kartu";
      k.style.cssText = "display:flex;gap:12px;align-items:center;flex-wrap:wrap";
      k.innerHTML = `<span>${BHS === "en" ? "To ask questions about your data, use the ✦ Assistant panel (Ctrl + I)." :
        BHS === "ja" ? "データについて質問するには ✦ アシスタントパネル（Ctrl + I）を使います。" :
        "Untuk bertanya tentang data, pakai panel ✦ Asisten di kanan atas (Ctrl + I)."}</span>` +
        `<button type="button" class="kecil">${BHS === "en" ? "Open Assistant" : BHS === "ja" ? "アシスタントを開く" : "Buka Asisten"}</button>`;
      k.querySelector("button").onclick = () => induk.postMessage({sps: "tombol", key: "i", ctrlKey: true, metaKey: false,
        altKey: false, mengetik: false}, location.origin);
      document.getElementById("auto").prepend(k);
    }
  }

  // ---- Tombol "Riwayat versi" di kepala dashboard (F8) ----
  function tombolVersi(coba = 0) {
    const m = location.pathname.match(/^\/superset\/dashboard\/([^/]+)\/?$/);
    if (!m) return;
    const panel = document.querySelector(".right-button-panel");
    if (!panel) { if (coba < 20) setTimeout(() => tombolVersi(coba + 1), 500); return; }
    if (panel.querySelector(".sps-versi")) return;
    fetch(`/api/v1/dashboard/${m[1]}`, {credentials: "same-origin"}).then(r => (r.ok ? r.json() : null)).then(j => {
      if (!j || panel.querySelector(".sps-versi")) return;
      const b = document.createElement("button");
      b.type = "button"; b.className = "ant-btn superset-button superset-button-secondary sps-versi";
      b.style.marginRight = "8px"; b.style.whiteSpace = "nowrap";   // satu baris, sejajar tombol Superset
      b.textContent = BHS === "en" ? "Version history" : BHS === "ja" ? "バージョン履歴" : "Riwayat versi";
      b.onclick = () => induk.SPS.buka(`/versi-dashboard/?id=${j.result.id}`);
      panel.prepend(b);
      const saya = ((induk.SPS_AWAL || {}).pengguna || {});
      const pemilik = (j.result.owners || []).some(o => o.username === saya.username || o.id === saya.id);
      if (saya.admin || pemilik) {                    // F7: pemilik/Admin mengatur tata letak ponsel
        const t2 = b.cloneNode(); t2.classList.remove("sps-versi"); t2.classList.add("sps-ponsel-atur");
        t2.textContent = BHS === "en" ? "Phone layout" : BHS === "ja" ? "スマホ表示" : "Tata ponsel";
        t2.onclick = () => induk.SPS.buka(`/ponsel-dashboard/?id=${j.result.id}`);
        b.after(t2);
        const t3 = b.cloneNode(); t3.classList.remove("sps-versi"); t3.classList.add("sps-filter-tambah");
        t3.textContent = BHS === "en" ? "Add filter" : BHS === "ja" ? "フィルター追加" : "Tambah filter";
        t3.title = BHS === "en" ? "Add a dashboard filter that applies to every chart with that column" : "Filter dashboard yang berlaku di semua chart yang punya kolomnya";
        t3.onclick = () => dialogFilter(j.result.id);
        t2.after(t3);
      }
    }).catch(() => {});
  }

  // ---- D5: "Tambah filter" langsung di dashboard (pemilik/Admin) ----
  // Lewat ALDx Rencana (/filter-global/api/tambah): pilih kolom -> pratinjau "berlaku di N dari M chart" -> Simpan ->
  // dashboard dimuat ulang + notifikasi berisi Urungkan.
  const escH = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const sebarisH = s => escH(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`(.+?)`/g, "<code>$1</code>");
  const kirimF = (url, data) => fetch(url, {method: "POST", credentials: "same-origin",
    headers: {"Content-Type": "application/json", "X-CSRFToken": ((induk.SPS_AWAL || {}).csrf || "")}, body: JSON.stringify(data || {})})
    .then(async r => { const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.error || r.status); return j; });
  const GAYA_KARTU = "background:#fff;border-radius:14px;box-shadow:0 20px 50px rgba(15,23,42,.25);padding:18px;width:min(460px,92vw);" +
    "max-height:86vh;overflow:auto;font:13px/1.5 var(--sps-font,'Plus Jakarta Sans',system-ui,sans-serif);color:#1e293b";
  const GAYA_TOMBOL = "border-radius:8px;padding:6px 14px;cursor:pointer;font:inherit;font-weight:600;";
  async function dialogFilter(idDash) {
    document.getElementById("spsDlgFilter")?.remove();
    const latar = document.createElement("div");
    latar.id = "spsDlgFilter";
    latar.style.cssText = "position:fixed;inset:0;z-index:2000;background:rgba(15,23,42,.35);display:flex;align-items:center;justify-content:center";
    latar.innerHTML = `<div role="dialog" aria-modal="true" aria-label="Tambah filter dashboard" style="${GAYA_KARTU}">
      <b style="font-size:15px">Tambah filter dashboard</b>
      <p style="margin:4px 0 10px;color:#64748b">Filter berlaku di semua chart yang datasetnya punya kolom itu; chart lain dikecualikan otomatis.</p>
      <div data-isi>Memuat kolom…</div></div>`;
    latar.onclick = e => { if (e.target === latar) latar.remove(); };
    document.addEventListener("keydown", function esc(e) { if (e.key === "Escape") { latar.remove(); document.removeEventListener("keydown", esc); } });
    document.body.appendChild(latar);
    const isi = latar.querySelector("[data-isi]");
    let data;
    try { data = await fetch(`/filter-global/api/kolom-dashboard?dashboard=${idDash}`, {credentials: "same-origin"}).then(r => r.json()); }
    catch (e) { isi.textContent = "Gagal memuat kolom."; return; }
    if (!data.kolom || !data.kolom.length) { isi.textContent = data.error || "Chart di dashboard ini belum punya kolom yang bisa difilter."; return; }
    isi.innerHTML = `<div style="max-height:40vh;overflow:auto;border:1px solid #e2e8f0;border-radius:10px">${data.kolom.map((k, i) =>
        `<label style="display:flex;gap:8px;align-items:center;padding:7px 10px;border-bottom:1px solid #f1f5f9;cursor:pointer;${k.sudah ? "opacity:.5" : ""}">
          <input type="radio" name="spsKolom" value="${escH(k.kolom)}" ${i === 0 && !k.sudah ? "checked" : ""} ${k.sudah ? "disabled" : ""}>
          <span style="flex:1"><b>${escH(k.label)}</b> <code style="color:#64748b">${escH(k.kolom)}</code></span>
          <span style="color:#64748b;white-space:nowrap">${k.sudah ? "sudah ada" : `${k.chart} dari ${k.total} chart`}</span></label>`).join("")}</div>
      <label style="display:block;margin-top:10px">Jenis
        <select data-jenis style="margin-left:6px;padding:4px;border-radius:6px"><option value="">Otomatis</option>
          <option value="pilihan">Pilihan nilai</option><option value="rentang">Rentang angka</option><option value="waktu">Rentang waktu</option></select></label>
      <div data-pratinjau style="margin-top:10px"></div>
      <div data-aksi style="display:flex;gap:8px;justify-content:flex-end;margin-top:12px">
        <button type="button" data-batal style="${GAYA_TOMBOL}border:1px solid #cbd5e1;background:#fff">Batal</button>
        <button type="button" data-lanjut style="${GAYA_TOMBOL}border:0;color:#fff;background:var(--sps-utama,#1E2A44)">Pratinjau</button></div>`;
    const pratinjau = isi.querySelector("[data-pratinjau]");
    isi.querySelector("[data-batal]").onclick = () => latar.remove();
    let rencana = null;
    isi.querySelectorAll('input[name="spsKolom"], [data-jenis]').forEach(x => x.onchange = () => {   // pilihan berubah: pratinjau ulang
      if (rencana) kirimF(`/filter-global/api/rencana/${rencana.id}/batal`).catch(() => {});
      rencana = null; pratinjau.innerHTML = ""; isi.querySelector("[data-lanjut]").textContent = "Pratinjau";
    });
    isi.querySelector("[data-lanjut]").onclick = async e => {
      const tombol = e.currentTarget;
      tombol.disabled = true;
      try {
        if (!rencana) {
          const kolom = (isi.querySelector('input[name="spsKolom"]:checked') || {}).value;
          if (!kolom) throw new Error("Pilih kolom dulu.");
          rencana = await kirimF("/filter-global/api/tambah", {dashboard: idDash, kolom, jenis: isi.querySelector("[data-jenis]").value});
          pratinjau.innerHTML = `<div style="background:#f8fafc;border-radius:10px;padding:8px 10px">${rencana.baris.map(sebarisH).join("<br>")}</div>` +
            (rencana.peringatan || []).map(w => `<div style="margin-top:6px;background:#FFFAEB;color:#B54708;border-radius:8px;padding:6px 9px">${sebarisH(w)}</div>`).join("");
          tombol.textContent = "Simpan";
        } else {
          await kirimF(`/filter-global/api/rencana/${rencana.id}/simpan`);
          try { sessionStorage.setItem("sps_filter_baru", JSON.stringify({id: rencana.id, teks: rencana.baris[0], dash: String(idDash)})); } catch (x) { /* mode privat */ }
          location.reload();
          return;
        }
      } catch (err) {
        pratinjau.innerHTML = `<div style="background:#FEF3F2;color:#B42318;border-radius:8px;padding:6px 9px">${escH(err.message)}</div>`;
        rencana = null; tombol.textContent = "Pratinjau";
      }
      tombol.disabled = false;
    };
  }
  // Setelah Simpan: notifikasi + Urungkan (sekali, di dashboard yang sama)
  function notifFilterBaru() {
    let info = null;
    try { info = JSON.parse(sessionStorage.getItem("sps_filter_baru") || "null"); sessionStorage.removeItem("sps_filter_baru"); } catch (e) { /* abaikan */ }
    const m = location.pathname.match(/^\/superset\/dashboard\/([^/]+)\/?$/);
    if (!info || !m) return;
    const k = document.createElement("div");
    k.style.cssText = "position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:2000;background:#1e293b;color:#fff;border-radius:12px;" +
      "padding:10px 14px;display:flex;gap:12px;align-items:center;box-shadow:0 12px 32px rgba(15,23,42,.3);font:13px/1.4 var(--sps-font,system-ui,sans-serif);max-width:92vw";
    k.innerHTML = `<span>✓ ${sebarisH(info.teks)}. Buka panel filter (ikon corong) untuk memakainya.</span>
      <button type="button" style="${GAYA_TOMBOL}border:1px solid #fff;background:none;color:#fff">Urungkan</button>
      <button type="button" aria-label="Tutup" style="border:0;background:none;color:#fff;font-size:18px;cursor:pointer">×</button>`;
    const [urung, tutup] = k.querySelectorAll("button");
    tutup.onclick = () => k.remove();
    urung.onclick = async () => {
      urung.disabled = true;
      try { await kirimF(`/filter-global/api/rencana/${info.id}/urungkan`); location.reload(); }
      catch (e) { k.querySelector("span").textContent = "Gagal mengurungkan: " + e.message; urung.disabled = false; }
    };
    document.body.appendChild(k);
    setTimeout(() => k.isConnected && k.remove(), 20000);
  }

  // ---- Tata letak ponsel per dashboard (F7): urutan & chart tersembunyi, hanya layar sempit ----
  const SEMPIT = window.matchMedia("(max-width: 760px)");
  let TATA = null;
  function tataPonsel(coba = 0) {
    const m = location.pathname.match(/^\/superset\/dashboard\/([^/]+)\/?$/);
    document.documentElement.classList.remove("sps-tata-ponsel");
    if (!m || !SEMPIT.matches) return;
    const terap = () => {
      const kotak = c => c && (c.closest(".dragdroppable-column") || c.closest(".dashboard-component-chart-holder"));
      let ada = 0;
      TATA.urutan.forEach((id, n) => {
        const k = kotak(document.querySelector(`.dashboard-chart-id-${id}`));
        if (!k) return;
        ada++; k.style.order = String(n); k.style.display = TATA.sembunyi.includes(id) ? "none" : "";
      });
      if (ada) document.documentElement.classList.add("sps-tata-ponsel");
      if (ada < TATA.urutan.length && coba < 20) setTimeout(() => tataPonsel(coba + 1), 700);   // chart belum dirender
    };
    if (TATA && TATA.kunci === m[1]) return terap();
    fetch(`/ponsel-dashboard/api/${m[1]}`, {credentials: "same-origin"}).then(r => (r.ok ? r.json() : null)).then(j => {
      if (!j || !j.diatur) return;
      TATA = {kunci: m[1], urutan: j.urutan, sembunyi: j.sembunyi}; terap();
    }).catch(() => {});
  }
  SEMPIT.addEventListener("change", () => tataPonsel());

  // ---- Petunjuk di halaman Superset ----
  const BHS = (document.cookie.match(/(?:^|; )sps_bahasa=([a-z]{2})/) || [])[1] || "id";
  const PETUNJUK = [
    {pola: /^\/dataset\/add/, kunci: "dataset", teks: {
      id: "Buat dataset: pilih Database → Skema (hanya skema terpilih di Hubungkan data) → klik tabel/view → Buat & jelajahi dataset. Untuk langsung membuat chart, Studio Visual lebih mudah.",
      en: "Create a dataset: choose Database → Schema (only schemas chosen in Connect data) → click a table/view → Create dataset. To build a chart right away, Visual Studio is easier.",
      ja: "データセット作成：データベース → スキーマ（データ接続で選んだもののみ）→ テーブル/ビューを選択 → Create dataset。すぐにチャートを作るならビジュアルスタジオが簡単です。"}},
    {pola: /^\/chart\/add/, kunci: "chart", teks: {
      id: "Pilih dataset dan jenis chart, lalu Create new chart. Belum yakin jenis chart? Di Studio Visual cukup seret kolom: dimensi & ukuran dikenali otomatis dan jenis chart disarankan.",
      en: "Choose a dataset and chart type, then Create new chart. Not sure which chart? In Visual Studio just drag columns: dimensions & measures are detected and a chart type is suggested.",
      ja: "データセットとチャート種類を選び Create new chart。迷ったらビジュアルスタジオで列をドラッグするだけ：ディメンションとメジャーを自動判別しチャートを提案します。"}},
    {pola: /^\/explore/, kunci: "explore", teks: {
      id: "Isi minimal: Metrik = angka yang dihitung (mis. SUM kolom nilai), Dimensi = dikelompokkan per apa (mis. cabang atau wilayah), Filter bila perlu, lalu Perbarui chart. Mulai dengan Batas baris 1000; chart pohon/jaringan otomatis dibatasi agar tidak macet.",
      en: "Minimum: METRICS = numbers to calculate (e.g. SUM of a value column), DIMENSIONS = group by (e.g. region), FILTERS if needed, then Update chart. Start with Row limit 1000; tree/network charts are capped so the browser does not freeze.",
      ja: "最低限：METRICS＝計算する数値（例：値列の SUM）、DIMENSIONS＝グループ化（例：地域）、必要なら FILTERS、そして Update chart。Row limit は 1000 から。ツリー/ネットワーク図はフリーズ防止のため上限あり。"}},
  ];
  const TOMBOL = {id: "Buka di Studio Visual", en: "Open in Visual Studio", ja: "ビジュアルスタジオで開く"};
  let idDatasetAwal = new URLSearchParams(location.search).get("datasource_id") || new URLSearchParams(location.search).get("dataset");
  function petunjuk() {
    const lama = document.getElementById("spsPetunjuk"); if (lama) lama.remove();
    const p = PETUNJUK.find(x => x.pola.test(location.pathname));
    if (!p) return;
    try { if (localStorage.getItem("sps_petunjuk_" + p.kunci) === "tutup") return; } catch (e) { /* mode privat */ }
    const id = /^\d+$/.test(idDatasetAwal || "") ? idDatasetAwal : "";
    const k = document.createElement("div");
    k.id = "spsPetunjuk"; k.setAttribute("role", "note");
    k.style.cssText = "position:fixed;right:16px;top:64px;z-index:1000;max-width:380px;background:#fff;border:1px solid rgba(15,23,42,.12);" +
      "border-left:4px solid var(--sps-aksen,#4F7CF7);border-radius:12px;box-shadow:0 12px 32px rgba(15,23,42,.16);padding:10px 34px 10px 12px;" +
      "font:12.5px/1.5 var(--sps-font,'Plus Jakarta Sans',system-ui,sans-serif);color:#1e293b;transition:opacity .2s";
    const JUDUL = {id: "Petunjuk", en: "Tips", ja: "ヒント"};
    k.innerHTML = `<div data-isi>${(p.teks[BHS] || p.teks.id).replace(/[&<>]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;"}[c]))}
      <br><button type="button" data-studio style="margin-top:8px;border:0;border-radius:8px;padding:5px 10px;cursor:pointer;color:#fff;background:var(--sps-utama,#1E2A44);font:inherit;font-weight:600">${TOMBOL[BHS] || TOMBOL.id}</button></div>
      <button type="button" data-ciut hidden style="border:0;background:none;cursor:pointer;font:inherit;font-weight:600;color:var(--sps-utama,#1E2A44);padding:0">💡 ${JUDUL[BHS] || JUDUL.id}</button>
      <button type="button" data-tutup aria-label="Tutup" title="Jangan tampilkan lagi" style="position:absolute;top:4px;right:6px;border:0;background:none;font-size:18px;cursor:pointer;color:#64748b">×</button>`;
    const ciut = c => {
      k.querySelector("[data-isi]").hidden = c; k.querySelector("[data-ciut]").hidden = !c;
      k.style.padding = c ? "6px 30px 6px 10px" : "10px 34px 10px 12px";
    };
    k.querySelector("[data-ciut]").onclick = () => ciut(false);
    k.querySelector("[data-studio]").onclick = () => induk.postMessage({sps: "buka", alamat: "/studio/" + (id ? "?dataset=" + id : "")}, location.origin);
    k.querySelector("[data-tutup]").onclick = () => { k.remove(); try { localStorage.setItem("sps_petunjuk_" + p.kunci, "tutup"); } catch (e) { /* abaikan */ } };
    setTimeout(() => k.isConnected && ciut(true), 12000);      // menciut sendiri agar tidak menutupi kontrol
    document.body.appendChild(k);
  }

  // ---- Bahasa ----
  function muatI18n() {
    const s = document.createElement("script");
    s.src = `/app/static/i18n.js?v=${VERSI}`;
    s.dataset.kamus = halamanSps ? "" : "superset";
    s.onload = () => window.SPS.i18n.amati(document.body);
    document.head.appendChild(s);
  }

  // ---- Ponsel: panel filter dashboard dilipat agar chart langsung terlihat (tombol corong membukanya) ----
  function lipatFilterPonsel() {
    if (window.innerWidth >= 760 || !/^\/superset\/dashboard\//.test(location.pathname)) return;
    let coba = 0;
    const t = setInterval(() => {
      const tombol = document.querySelector('[data-test="filter-bar__collapse-button"]');
      const panel = document.querySelector('[data-test="filter-bar"]');
      if (tombol && tombol.offsetWidth > 0 && panel && panel.offsetWidth > 100) {
        tombol.click(); clearInterval(t);
        setTimeout(() => window.dispatchEvent(new Event("resize")), 400);   // chart menyesuaikan lebar baru
      }
      else if (++coba > 40) clearInterval(t);               // 10 detik: panel tidak ada / sudah terlipat
    }, 250);
  }

  // ---- SQL Lab tanpa tab: buka satu tab editor otomatis (pengguna baru tidak bingung) ----
  function tabSqlOtomatis() {
    if (!/^\/sqllab\/?$/.test(location.pathname)) return;
    let coba = 0;
    const t = setInterval(() => {
      const tab = document.querySelectorAll('[data-test="sql-editor-tabs"] .ant-tabs-tab');
      const tambah = document.querySelector('[data-test="add-tab-icon"]');
      if (tab.length === 1 && tambah) { tambah.click(); clearInterval(t); }
      else if (tab.length > 1 || ++coba > 40) clearInterval(t);
    }, 250);
  }

  // ---- SQL Lab: tabel diseret/diklik dari pohon kiri ke editor ----
  // Superset menyisipkan kueri lengkap "SELECT ... FROM <tabel> LIMIT 100" di posisi kursor. Bila pengguna
  // sudah mengetik "SELECT * FROM ", hasilnya dua SELECT dan database menolak (ClickHouse code 62, ORA-00936, ...).
  // Bila sisipan jatuh tepat setelah FROM / JOIN, ganti dengan nama tabelnya saja.
  const POLA_SELECT = /^\s*select\s[\s\S]*?\sfrom\s+([\s\S]+?)(?:\s+limit\s+\d+)?\s*;?\s*$/i;
  function rapikanSisipan(editor, d) {
    if (d.action !== "insert") return;
    const sisip = d.lines.join("\n"), m = sisip.match(POLA_SELECT);
    if (!m || d.lines.length < 2 && !/\blimit\b/i.test(sisip)) return;      // bukan sisipan kueri tabel
    const sesi = editor.getSession();
    const sebelum = sesi.getTextRange({start: {row: 0, column: 0}, end: d.start});
    if (!/\b(from|join)\s*$/i.test(sebelum)) return;
    const tabel = (/\s$/.test(sebelum) ? "" : " ") + m[1].trim();
    setTimeout(() => sesi.replace({start: d.start, end: d.end}, tabel), 0);  // jangan ubah di dalam event change
  }
  function sqlLabRapi() {
    if (!/^\/sqllab/.test(location.pathname)) return;
    setInterval(() => document.querySelectorAll(".ace_editor").forEach(el => {
      const ed = el.env && el.env.editor;
      if (!ed || ed.__spsRapi) return;
      ed.__spsRapi = true;
      ed.getSession().on("change", d => rapikanSisipan(ed, d));
    }), 1000);
  }

  // ---- Mode gelap untuk halaman ALDx di bingkai (Pusat Kendali, Kueri Visual, Studio, Asisten, Berkas) ----
  // Halaman-halaman ini memakai warna tetap; cangkang menyimpan pilihan tema di <html data-tema>. Bila gelap, halaman
  // dibalik warnanya dengan rona dipertahankan (invert + hue-rotate); gambar, video & peta dibalik lagi ke warna asli.
  // Panduan punya mode gelap sendiri; halaman Superset memakai tema Superset sendiri.
  function gelapBingkai() {
    if (!halamanSps || location.pathname.startsWith("/panduan")) return;
    const gaya = document.createElement("style");
    gaya.textContent = "html.sps-gelap{filter:invert(.92) hue-rotate(180deg);background:#fff}" +
      "html.sps-gelap img,html.sps-gelap video,html.sps-gelap picture,html.sps-gelap .leaflet-tile-pane," +
      "html.sps-gelap [style*='background-image']{filter:invert(1) hue-rotate(180deg)}";
    document.head.appendChild(gaya);
    const atur = () => {
      let gelap = false;
      try { gelap = induk.document.documentElement.dataset.tema === "gelap"; } catch (e) { /* lain origin */ }
      document.documentElement.classList.toggle("sps-gelap", gelap);
    };
    atur();
    try { new MutationObserver(atur).observe(induk.document.documentElement, {attributes: true, attributeFilter: ["data-tema"]}); }
    catch (e) { /* abaikan */ }
  }

  function mulai() {
    gelapBingkai();
    sqlLabRapi();
    if (halamanSps) pasangTab();
    muatI18n();
    lapor();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mulai); else mulai();
})();
