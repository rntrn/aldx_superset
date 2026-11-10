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
    const q = new URLSearchParams({dashboard: decodeURIComponent(m[1]), filter: JSON.stringify(fg.filter)});
    fetch("/filter-global/api/terapkan?" + q, {credentials: "same-origin"}).then(r => (r.ok ? r.json() : null)).then(j => {
      if (!j || !j.native_filters) return;
      p.set("native_filters", j.native_filters);
      p.set("sps_fg", "1");
      location.replace(location.pathname + "?" + p + location.hash);
    }).catch(() => {});
  };
  window.__spsFilterGlobal();

  let induk;
  try { induk = window.parent !== window && window.parent.location.pathname.startsWith("/app") ? window.parent : null; }
  catch (e) { induk = null; }
  if (!induk || window.__spsBingkai) return;
  window.__spsBingkai = true;
  const VERSI = new URL(document.currentScript.src).searchParams.get("v") || "";
  const halamanSps = !document.getElementById("app");
  document.documentElement.classList.add("sps-bingkai");

  const gaya = document.createElement("style");
  gaya.textContent = `
    html.sps-bingkai #main-menu, html.sps-bingkai header.sps-hiasan, html.sps-bingkai .spsNav,
    html.sps-bingkai body > .navbar.navbar-inverse{display:none!important}
    html.sps-bingkai body > .container, html.sps-bingkai body > .container-fluid{padding-top:12px}
    html.sps-bingkai body::before{display:none!important}
    html.sps-bingkai, html.sps-bingkai body{background:var(--sps-latar,#F5F6F8)}
    /* Tombol sekunder Superset (Pilih banyak, Ubah dashboard): garis tepi, bukan abu gelap yang tampak nonaktif */
    html.sps-bingkai .superset-button-secondary:not(:disabled){background:#fff!important;color:var(--sps-utama,#1F4E79)!important;
      border:1px solid var(--sps-utama,#1F4E79)!important}
    html.sps-bingkai .superset-button-secondary:not(:disabled):hover{background:var(--sps-muda,#EAF1FB)!important}
    /* Judul dashboard memakai ruang yang ada (tidak terpotong lebih awal) */
    html.sps-bingkai .title-panel > div:first-child{flex:0 1 auto!important;max-width:none!important;min-width:120px}
    html.sps-bingkai .title-panel input.ant-input{field-sizing:content;width:auto!important;max-width:100%!important;text-overflow:ellipsis}
    html.sps-bingkai .title-panel > div:nth-child(2){flex:0 1 auto;min-width:0;overflow:hidden}
    /* Tata letak ponsel yang diatur pemilik: semua chart jadi satu daftar berurutan (urutan via style.order) */
    html.sps-tata-ponsel .grid-content{display:flex!important;flex-direction:column}
    html.sps-tata-ponsel .grid-content .dragdroppable-row,html.sps-tata-ponsel .grid-content .dragdroppable-row > .with-popover-menu,
    html.sps-tata-ponsel .grid-content .grid-row{display:contents!important}
    @media (max-width:760px){                      /* ponsel: kotak dashboard bertumpuk satu kolom */
      html.sps-bingkai .sps-versi,html.sps-bingkai .sps-ponsel-atur{display:none!important}
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
      tombolVersi(); tataPonsel();
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
      b.style.marginRight = "8px";
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
      }
    }).catch(() => {});
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
