// ALDx App — cangkang: navigasi, bingkai, palet perintah (Ctrl+K), pintasan, bantuan, bahasa, akun.
// Panel Asisten AI ada di ai.js (Ctrl+I), tombol Ekspor di ekspor.js.
//
// Alur singkat:
//   mulai() -> muat kamus bahasa + daftar menu yang boleh (/api/v1/menu/) -> gambar sidebar -> buka rute awal
//   buka(alamat)   "beranda" = Beranda (beranda.js); selain itu alamat halaman di dalam <iframe id="bingkai">
//   Halaman di bingkai melapor lewat postMessage (bingkai.js): alamat & judul baru, pintasan keyboard.
(function () {
  "use strict";
  const $ = s => document.querySelector(s);
  const {t, BAHASA} = SPS.i18n;
  const ik = SPS.ikon;
  const AWAL = window.SPS_AWAL;
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const ambil = url => fetch(url, {credentials: "same-origin"}).then(r => (r.ok ? r.json() : null)).catch(() => null);
  const simpanLokal = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* mode privat */ } };
  const bacaLokal = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };

  // ---------------- Daftar halaman (urutan = urutan membuat laporan) ----------------
  // izin = nama menu Superset/sps_menu yang harus boleh dibuka; cocok = pola alamat yang termasuk halaman ini.
  const NAV = [
    {id: "beranda", grup: "", label: "Beranda", ikon: "rumah", alamat: "beranda"},
    {id: "hubungkan", grup: "Data", label: "Hubungkan data", ikon: "sambung", alamat: "/pusat-kendali/?tab=hubungkan", izin: "Hubungkan data", langkah: 1, admin: true, cocok: /^\/(pusat-kendali\/\?tab=hubungkan|databaseview)/},
    {id: "dataset", grup: "Data", label: "Dataset", ikon: "tabel", alamat: "/tablemodelview/list/", izin: "Datasets", langkah: 1, cocok: /^\/tablemodelview/},
    {id: "prep", grup: "Data", label: "Persiapan data", ikon: "siapkan", alamat: "/studio/?tab=prep", izin: "Persiapan data", langkah: 2},
    {id: "ekstrak", grup: "Data", label: "Ekstrak ke ALDx Engine", ikon: "ekstrak", alamat: "/pusat-kendali/?tab=ekstrak", izin: "Ekstrak data", admin: true},
    {id: "kueri", grup: "Kueri", label: "Kueri Visual", ikon: "kueri", alamat: "/kueri/", izin: "Kueri Visual", cocok: /^\/kueri/},
    {id: "sqllab", grup: "Kueri", label: "SQL Lab", ikon: "sql", alamat: "/sqllab/", izin: "SQL Editor", cocok: /^\/sqllab\/?$|^\/sqllab\/\?/},
    {id: "tersimpan", grup: "Kueri", label: "Kueri tersimpan", ikon: "simpan", alamat: "/savedqueryview/list/", izin: "Saved Queries", cocok: /^\/savedqueryview/},
    {id: "studio", grup: "Visual", label: "Studio Visual", ikon: "studio", alamat: "/studio/", izin: "Studio Visual", langkah: 3},
    {id: "chart", grup: "Visual", label: "Daftar chart", ikon: "chart", alamat: "/chart/list/", izin: "Charts", cocok: /^\/(chart|explore)/},
    {id: "dashboard", grup: "Dashboard & Story", label: "Daftar dashboard", ikon: "dashboard", alamat: "/dashboard/list/", izin: "Dashboards",
     langkah: 4, cocok: /^\/(dashboard\/list|superset\/dashboard)/},
    {id: "story", grup: "Dashboard & Story", label: "Story", ikon: "story", alamat: "/asisten/?tab=story", izin: "Story", langkah: 5},
    {id: "langganan", grup: "Dashboard & Story", label: "Langganan laporan", ikon: "riwayat", alamat: "/report/list/", izin: "Alerts & Report",
     cocok: /^\/report\//},
    {id: "peringatan", grup: "Dashboard & Story", label: "Peringatan data", ikon: "riwayat", alamat: "/alert/list/", izin: "Alerts & Report",
     cocok: /^\/alert\//},
    {id: "berkas", grup: "Dashboard & Story", label: "Berkas .ald / .aldx", ikon: "simpan", alamat: "/berkas/", izin: "Berkas ALDx", cocok: /^\/berkas/},
    {id: "sematkan", grup: "Dashboard & Story", label: "Sematkan ke web lain", ikon: "sambung", alamat: "/sematkan/", izin: "Sematkan", admin: true, cocok: /^\/sematkan\/?$/},
    // Tanya-jawab AI ada di panel ✦ (Ctrl + I) di setiap halaman; menu ini untuk membuat chart & dashboard otomatis.
    {id: "asisten", grup: "Asisten", label: "Auto chart & dashboard", ikon: "ai", alamat: "/asisten/?tab=auto", izin: "Asisten AI", cocok: /^\/asisten\/?(\?tab=(auto|tanya))?$/},
    {id: "panduan", grup: "Asisten", label: "Panduan", ikon: "bantuan", alamat: "/panduan/", cocok: /^\/panduan/},
    {id: "sambungai", grup: "Kelola", label: "Asisten AI", ikon: "ai", alamat: "/pusat-kendali/?tab=ai", izin: "Pusat Kendali Server", admin: true,
     cocok: /^\/pusat-kendali\/\?tab=ai/},
    {id: "pusat", grup: "Kelola", label: "Pusat Kendali", ikon: "server", alamat: "/pusat-kendali/", izin: "Pusat Kendali Server", admin: true},
    {id: "pengguna", grup: "Kelola", label: "Pengguna", ikon: "pengguna", alamat: "/users/", izin: "List Users", cocok: /^\/users/},
    {id: "role", grup: "Kelola", label: "Role", ikon: "kunci", alamat: "/roles/", izin: "List Roles", cocok: /^\/roles/},
    {id: "lihatsebagai", grup: "Kelola", label: "Lihat sebagai…", ikon: "pengguna", alamat: "/lihat-sebagai/", izin: "Pusat Kendali Server", admin: true,
     cocok: /^\/lihat-sebagai/},
    {id: "rls", grup: "Kelola", label: "Hak akses data (RLS)", ikon: "kunci", alamat: "/rowlevelsecurity/list/", izin: "Row Level Security", cocok: /^\/rowlevelsecurity/},
    // Koneksi database (lanjutan) TIDAK jadi menu sendiri: dibuka dari Data › Hubungkan data › Koneksi tersimpan.
    {id: "riwayat", grup: "Kelola", label: "Riwayat kueri", ikon: "riwayat", alamat: "/sqllab/history/", izin: "Query Search", cocok: /^\/sqllab\/history/},
    {id: "moderasi", grup: "Kelola", label: "Moderasi ulasan", ikon: "komentar", alamat: "/ulasan/moderasi/", izin: "Pusat Kendali Server", superadmin: true, cocok: /^\/ulasan\/moderasi/},
    // Log aktivitas versi terbaca = jejak audit (Pusat Kendali › Riwayat); log mentah Superset tetap di /actionlog/list.
    {id: "log", grup: "Kelola", label: "Jejak audit", ikon: "riwayat", alamat: "/pusat-kendali/?tab=riwayat", izin: "Pusat Kendali Server", admin: true,
     cocok: /^\/(actionlog|pusat-kendali\/\?tab=riwayat)/},
  ];
  const TAB_BAWAH = ["beranda", "dataset", "studio", "dashboard"];
  const LABEL_PENDEK = {studio: "Studio", dashboard: "Dashboard"};
  let boleh = new Set(["beranda"]), urlMenu = {}, ruteAktif = null, bantuan = null;

  // ---------------- Hak akses dari menu Superset ----------------
  function kumpulkanMenu(daftar) {
    for (const m of daftar || []) {
      if (m === "-") continue;
      boleh.add(m.name);
      if (m.url) urlMenu[m.name] = m.url;
      kumpulkanMenu(m.childs);
    }
  }
  const terlihat = () => NAV.filter(n => (!n.izin || boleh.has(n.izin)) && (!n.admin || AWAL.pengguna.admin) && (!n.superadmin || AWAL.pengguna.superadmin));

  // ---------------- Sidebar & tab bawah ----------------
  // Grup yang bisa dilipat (isi jarang dipakai harian). Status lipat disimpan per browser.
  const GRUP_LIPAT = {Kelola: true};
  function gambarNav() {
    let grup = null, html = "";
    for (const n of terlihat()) {
      if (n.grup !== grup) {
        if (grup && GRUP_LIPAT[grup] !== undefined) html += "</div>";
        grup = n.grup;
        if (grup && GRUP_LIPAT[grup] !== undefined) {
          const lipat = (bacaLokal("sps_lipat_" + grup) ?? (GRUP_LIPAT[grup] ? "1" : "0")) === "1";
          html += `<h6 class="${lipat ? "terlipat" : ""}"><button type="button" class="grup-lipat" data-grup="${esc(grup)}">${esc(t(grup))}${ik("lipat", 14)}</button></h6><div class="isi-grup">`;
        } else if (grup) html += `<h6>${esc(t(grup))}</h6>`;
      }
      html += `<a href="${esc(tautan(n))}" data-rute="${n.id}" title="${esc(t(n.label))}">${ik(n.ikon)}<span class="label">${esc(t(n.label))}</span>` +
              (n.langkah ? `<span class="langkah" title="${esc(t("Langkah ke-") + n.langkah)}">${n.langkah}</span>` : "") + "</a>";
    }
    if (grup && GRUP_LIPAT[grup] !== undefined) html += "</div>";
    $("#nav").innerHTML = html;
    document.querySelectorAll(".grup-lipat").forEach(b => b.onclick = () => {
      const h = b.parentElement; h.classList.toggle("terlipat");
      simpanLokal("sps_lipat_" + b.dataset.grup, h.classList.contains("terlipat") ? "1" : "0");
    });
    $("#tabBawah").innerHTML = terlihat().filter(n => TAB_BAWAH.includes(n.id)).map(n =>
      `<a href="${esc(tautan(n))}" data-rute="${n.id}">${ik(n.ikon, 22)}<span>${esc(t(LABEL_PENDEK[n.id] || n.label))}</span></a>`).join("") +
      `<button type="button" id="tabLainnya">${ik("menu", 22)}<span>${esc(t("Lainnya"))}</span></button>`;
    $("#tabLainnya").onclick = () => document.body.classList.add("laci-nav");
    document.querySelectorAll("[data-rute]").forEach(a => a.addEventListener("click", e => {
      if (e.ctrlKey || e.metaKey || e.shiftKey || e.button === 1) return;      // buka di tab baru: biarkan
      e.preventDefault();
      const n = NAV.find(x => x.id === a.dataset.rute);
      buka(n.alamat === "beranda" ? "beranda" : (urlMenu[n.izin] && !n.alamat.includes("?") ? urlMenu[n.izin] : n.alamat));
      document.body.classList.remove("laci-nav");
    }));
  }
  const tautan = n => (n.alamat === "beranda" ? "/app/" : "/app/?p=" + encodeURIComponent(n.alamat));

  function ruteDari(alamat) {
    if (alamat === "beranda") return NAV[0];
    const u = new URL(alamat, location.origin), tab = u.searchParams.get("tab") || "";
    const cocok = NAV.filter(n => n.alamat !== "beranda" && (n.cocok ? n.cocok.test(u.pathname + u.search)
      : new URL(n.alamat, location.origin).pathname === u.pathname && (new URL(n.alamat, location.origin).searchParams.get("tab") || "") === tab));
    return cocok[0] || null;
  }
  function tandaiAktif(n) {
    ruteAktif = n;
    const a = n && document.querySelector(`.nav [data-rute="${n.id}"]`);
    const isi = a && a.closest(".isi-grup");
    if (isi) isi.previousElementSibling.classList.remove("terlipat");
    document.querySelectorAll("[data-rute]").forEach(a => a.classList.toggle("aktif", !!n && a.dataset.rute === n.id && !a.classList.contains("merek")));
  }

  // ---------------- Bingkai ----------------
  const bingkai = $("#bingkai"), beranda = $("#beranda"), bilah = $("#bilahMuat");
  let alamatBingkai = "";

  function setJejak(n, judulHalaman) {
    const grup = n && n.grup ? `<span>${esc(t(n.grup))}</span>${ik("kanan", 14)}` : "";
    const judul = judulHalaman || (n ? t(n.label) : "");
    $("#jejak").innerHTML = grup + `<b>${esc(judul)}</b>`;
    document.title = (judul ? judul + " · " : "") + AWAL.app;
    window.dispatchEvent(new Event("sps:halaman"));        // mis. chip filter global menyesuaikan dashboard yang dibuka
  }
  function buka(alamat, {dorong = true} = {}) {
    if (alamat.startsWith("/app")) { const p = new URL(alamat, location.origin).searchParams.get("p"); alamat = p || "beranda"; }
    const n = ruteDari(alamat);
    tandaiAktif(n);
    if (alamat === "beranda") {
      bingkai.hidden = true; beranda.hidden = false;
      setJejak(NAV[0], t("Beranda"));
      if (dorong) history.pushState({p: "beranda"}, "", "/app/");
      SPS.beranda && SPS.beranda.tampil();
      return;
    }
    beranda.hidden = true; bingkai.hidden = false;
    setJejak(n, null);
    if (alamat !== alamatBingkai) {
      alamatBingkai = alamat;
      bilah.className = "bilah-muat"; void bilah.offsetWidth; bilah.classList.add("jalan");
      bingkai.src = alamat;
    }
    if (dorong) history.pushState({p: alamat}, "", "/app/?p=" + encodeURIComponent(alamat));
  }
  function laporAlamat(alamat, judul) {
    // Pindah halaman di dalam bingkai (klik tautan / navigasi SPA Superset).
    if (alamat.startsWith("/login")) { location.href = "/login/?next=" + encodeURIComponent("/app/?p=" + encodeURIComponent(alamatBingkai)); return; }
    if (alamat.startsWith("/app")) { buka(alamat); return; }
    alamatBingkai = alamat;
    const n = ruteDari(alamat);
    tandaiAktif(n);
    const judulBersih = judul && !/^(Superset|SPS|ALDx)/.test(judul) ? judul.split(" · ")[0].split(" | ")[0] : null;
    setJejak(n, n && !/dashboard\/(?!list)|explore/.test(alamat) ? t(n.label) : judulBersih || (n ? t(n.label) : ""));
    const kini = "/app/?p=" + encodeURIComponent(alamat);
    if (location.pathname + location.search !== kini) history.replaceState({p: alamat}, "", kini);
  }
  bingkai.addEventListener("load", () => {
    bilah.classList.add("selesai");
    try {
      const w = bingkai.contentWindow;
      laporAlamat(w.location.pathname + w.location.search + w.location.hash, w.document.title);
    } catch (e) { /* lain asal: abaikan */ }
  });
  window.addEventListener("popstate", e => buka((e.state && e.state.p) || awalDariUrl(), {dorong: false}));
  const awalDariUrl = () => new URLSearchParams(location.search).get("p") || "beranda";

  // ---------------- Pesan dari bingkai (bingkai.js) ----------------
  window.addEventListener("message", e => {
    if (e.origin !== location.origin || !e.data || !e.data.sps) return;
    const d = e.data;
    if (d.sps === "rute") laporAlamat(d.alamat, d.judul);
    else if (d.sps === "tombol") tanganiTombol(d);
    else if (d.sps === "buka") buka(d.alamat);
  });

  // ---------------- Lapisan (tirai, palet, laci, menu) ----------------
  const tirai = $("#tirai");
  function tutupSemua() {
    ["#palet", "#laci", "#menuMengambang"].forEach(s => $(s).classList.remove("tampil"));
    tirai.classList.remove("tampil", "bening"); document.body.classList.remove("laci-nav");
  }
  tirai.onclick = tutupSemua;

  function menuMengambang(tombol, html) {
    const m = $("#menuMengambang");
    m.className = "menu-mengambang";
    m.innerHTML = html;
    const r = tombol.getBoundingClientRect();
    if (r.top < innerHeight / 2) {             // tombol di bilah atas: menu turun, rata kanan tombol
      m.style.left = "auto"; m.style.right = Math.max(8, innerWidth - r.right) + "px";
      m.style.bottom = "auto"; m.style.top = (r.bottom + 8) + "px";
    } else {
      m.style.right = "auto"; m.style.left = Math.min(r.left, innerWidth - 240) + "px";
      m.style.top = "auto"; m.style.bottom = (innerHeight - r.top + 8) + "px";
    }
    m.classList.add("tampil"); tirai.classList.add("tampil", "bening");      // menu kecil: latar tidak diburamkan
    setTimeout(() => { tirai.addEventListener("click", () => tirai.classList.remove("bening"), {once: true}); });
    return m;
  }
  async function gantiBahasa(kode) {
    SPS.i18n.ganti(kode);
    // Halaman bawaan Superset hanya punya Inggris & Jepang; Indonesia diterjemahkan oleh kamus SPS.
    await fetch("/lang/" + (kode === "ja" ? "ja" : "en"), {credentials: "same-origin", redirect: "manual"}).catch(() => null);
    location.reload();
  }
  // ---------------- Tampilan terang / gelap (U25) ----------------
  // Pilihan disimpan di browser. Halaman Superset membaca "superset-theme-mode" (default | dark | system) dari
  // penyimpanan yang sama (satu origin), jadi dashboard & chart ikut berganti tanpa pengaturan lain.
  const TEMA = {terang: "Terang", gelap: "Gelap", sistem: "Ikuti sistem"};
  const temaAktif = () => (TEMA[bacaLokal("sps_tema")] ? bacaLokal("sps_tema") : "terang");
  const gelapSistem = window.matchMedia("(prefers-color-scheme: dark)");
  function terapkanTema(muatUlangIsi = false) {
    const pilih = temaAktif(), gelap = pilih === "gelap" || (pilih === "sistem" && gelapSistem.matches);
    document.documentElement.dataset.tema = gelap ? "gelap" : "terang";
    const logo = document.querySelector(".merek img");          // logo versi putih di latar gelap
    if (logo) logo.src = logo.src.replace(/\/berkas\/logo(_putih)?\?/, gelap ? "/berkas/logo_putih?" : "/berkas/logo?");
    const mode = {terang: "default", gelap: "dark", sistem: "system"}[pilih];
    if (bacaLokal("superset-theme-mode") !== mode) {
      simpanLokal("superset-theme-mode", mode);
      const f = document.querySelector("iframe#bingkai, .isi iframe");
      if (muatUlangIsi && f) f.contentWindow.location.reload();
    }
  }
  gelapSistem.addEventListener("change", () => terapkanTema());
  terapkanTema();

  const inisial = nama => String(nama || "?").trim().split(/\s+/).slice(0, 2).map(x => x[0]).join("").toUpperCase();
  // Menu akun (avatar di kanan bilah atas): profil, bahasa, pintasan, keluar.
  function menuAkun(tombol) {
    const p = AWAL.pengguna, peran = p.superadmin ? "Superadmin" : p.admin ? "Admin" : "";
    menuMengambang(tombol, `<div class="profil-menu"><span class="avatar besar">${esc(inisial(p.nama))}</span>
        <div><b>${esc(p.nama)}</b><small>${esc(p.username)}</small>${peran ? `<span class="peran-menu">${esc(t(peran))}</span>` : ""}</div></div>
      <div class="pilih-bahasa" role="group" aria-label="${esc(t("Bahasa"))}">${ik("bahasa", 16)}${Object.entries(BAHASA).map(([k, v]) =>
        `<button type="button" data-bahasa="${k}" class="${k === SPS.i18n.aktif ? "aktif" : ""}" aria-pressed="${k === SPS.i18n.aktif}" title="${esc(v)}">${esc(k === "id" ? "Indonesia" : v)}</button>`).join("")}</div>
      <div class="pilih-bahasa" role="group" aria-label="${esc(t("Tampilan"))}">${ik("bulan", 16)}${Object.entries(TEMA).map(([k, v]) =>
        `<button type="button" data-tema="${k}" class="${k === temaAktif() ? "aktif" : ""}" aria-pressed="${k === temaAktif()}">${esc(t(v))}</button>`).join("")}</div>
      ${NOTIF.daftar.length ? `<hr><div class="notif-menu" aria-label="${esc(t("Pemberitahuan"))}">${NOTIF.daftar.slice(0, 8).map(x =>
        `<a href="/app/?p=${encodeURIComponent(x.alamat)}" data-notif="${esc(x.alamat)}" class="${x.dibaca ? "" : "baru"}">${esc(x.teks)}<br><small>${esc(new Date(x.dibuat + "Z").toLocaleString("id-ID"))}</small></a>`).join("")}</div>` : ""}
      <hr><a href="/app/?p=${encodeURIComponent("/user_info/")}" data-buka="/user_info/">${ik("pengguna", 18)}${esc(t("Info pengguna"))}</a>
      <button type="button" data-aksi="pintasan">${ik("pintasan", 18)}${esc(t("Pintasan keyboard"))}</button>
      <hr><a href="/logout/">${ik("keluar", 18)}${esc(t("Keluar"))}</a>`);
    const m = $("#menuMengambang");
    m.classList.add("menu-akun");
    m.querySelectorAll("[data-bahasa]").forEach(b => b.onclick = () => gantiBahasa(b.dataset.bahasa));
    m.querySelectorAll("[data-notif]").forEach(x => x.onclick = e => { e.preventDefault(); tutupSemua(); buka(x.dataset.notif); });
    if (NOTIF.belum_dibaca) {                                   // menu dibuka = pemberitahuan dianggap dibaca
      fetch("/ulasan/api/notifikasi/baca", {method: "POST", credentials: "same-origin", headers: {"X-CSRFToken": AWAL.csrf}})
        .then(() => { NOTIF.belum_dibaca = 0; tandaAvatar(); }).catch(() => {});
    }
    m.querySelectorAll("[data-tema]").forEach(b => b.onclick = () => { simpanLokal("sps_tema", b.dataset.tema); terapkanTema(true); tutupSemua(); });
    m.querySelector("[data-buka]").onclick = e => { e.preventDefault(); tutupSemua(); buka("/user_info/"); };
    m.querySelector('[data-aksi="pintasan"]').onclick = () => { tutupSemua(); bukaBantuan("pintasan"); };
  }

  // ---------------- Palet perintah (Ctrl+K) ----------------
  const palet = $("#palet"), masukan = $("#masukanPalet"), hasil = $("#hasilPalet");
  let pilihan = [], sorot = 0, nomorCari = 0;
  const rison = s => "'" + String(s).replace(/!/g, "!!").replace(/'/g, "!'") + "'";

  function bukaPalet(teks = "") {
    tutupSemua();
    palet.classList.add("tampil"); tirai.classList.add("tampil");
    masukan.value = teks; isiPalet(); setTimeout(() => masukan.focus(), 20);
  }
  function perintahDasar() {
    const halaman = terlihat().map(n => ({kelompok: t("Halaman"), ikon: n.ikon, label: t(n.label), ket: n.grup ? t(n.grup) : "", jalan: () => buka(n.alamat)}));
    const aksi = [
      {kelompok: t("Perintah"), ikon: "bantuan", label: t("Cara pakai halaman ini"), ket: "?", jalan: () => bukaBantuan()},
      {kelompok: t("Perintah"), ikon: "pintasan", label: t("Pintasan keyboard"), ket: "", jalan: () => bukaBantuan("pintasan")},
      {kelompok: t("Perintah"), ikon: "lipat", label: t("Ringkas / lebarkan menu samping"), ket: "Ctrl \\", jalan: () => ringkas()},
      ...Object.entries(BAHASA).map(([k, v]) => ({kelompok: t("Perintah"), ikon: "bahasa", label: t("Bahasa") + ": " + v, ket: "", jalan: () => gantiBahasa(k)})),
      {kelompok: t("Perintah"), ikon: "keluar", label: t("Keluar"), ket: "", jalan: () => { location.href = "/logout/"; }},
    ];
    return [...halaman, ...aksi];
  }
  function cocokTeks(item, q) { return !q || (item.label + " " + item.ket).toLowerCase().includes(q); }
  async function isiPalet() {
    const q = masukan.value.trim().toLowerCase(), nomor = ++nomorCari;
    pilihan = perintahDasar().filter(i => cocokTeks(i, q));
    sorot = 0; gambarPalet();
    if (q.length < 2) return;
    const f = (kol, nilai) => `(filters:!((col:${kol},opr:ct,value:${rison(nilai)})),page_size:5,order_column:changed_on_delta_humanized,order_direction:desc)`;
    // Hasil yang disertifikasi ("Resmi") diurutkan lebih dulu (F5).
    const [d, c, s] = await Promise.all([
      ambil(`/api/v1/dashboard/?q=${encodeURIComponent(f("dashboard_title", q))}`),
      ambil(`/api/v1/chart/?q=${encodeURIComponent(f("slice_name", q))}`),
      ambil(`/api/v1/dataset/?q=${encodeURIComponent(f("table_name", q))}`)]);
    if (nomor !== nomorCari) return;                                             // hasil lama: abaikan
    const tambah = (j, kelompok, ikon, label, alamat) => (j && j.result || [])
      .sort((a, b) => !!b.certified_by - !!a.certified_by).forEach(x =>
        pilihan.push({kelompok, ikon, label: label(x), ket: x.certified_by ? t("Resmi") : "", jalan: () => buka(alamat(x))}));
    tambah(d, t("Dashboard"), "dashboard", x => x.dashboard_title, x => x.url || `/superset/dashboard/${x.id}/`);
    tambah(c, t("Chart"), "chart", x => x.slice_name, x => `/explore/?slice_id=${x.id}`);
    if (s && s.result) s.result = s.result.filter(x => !/^ramalan__/.test(x.table_name));   // dataset sistem (U17)
    tambah(s, t("Dataset"), "tabel", x => x.table_name, x => `/explore/?datasource_type=table&datasource_id=${x.id}`);
    gambarPalet();
  }
  function gambarPalet() {
    let kelompok = null, html = "";
    pilihan.forEach((p, i) => {
      if (p.kelompok !== kelompok) { kelompok = p.kelompok; html += `<li class="kepala">${esc(kelompok)}</li>`; }
      html += `<li class="pilihan ${i === sorot ? "sorot" : ""}" data-i="${i}">${ik(p.ikon, 18)}<span>${esc(p.label)}</span><small>${esc(p.ket)}</small></li>`;
    });
    hasil.innerHTML = html || `<li class="kosong">${esc(t("Tidak ditemukan"))}</li>`;
    hasil.querySelectorAll(".pilihan").forEach(li => {
      li.onmouseenter = () => { sorot = +li.dataset.i; tandaiSorot(); };
      li.onclick = () => jalankanPilihan(+li.dataset.i);
    });
  }
  function tandaiSorot() {
    hasil.querySelectorAll(".pilihan").forEach(li => li.classList.toggle("sorot", +li.dataset.i === sorot));
    const el = hasil.querySelector(".sorot"); el && el.scrollIntoView({block: "nearest"});
  }
  function jalankanPilihan(i) { const p = pilihan[i]; if (!p) return; tutupSemua(); p.jalan(); }
  let tundaPalet;
  masukan.addEventListener("input", () => { clearTimeout(tundaPalet); tundaPalet = setTimeout(isiPalet, 160); });
  masukan.addEventListener("keydown", e => {
    if (e.key === "ArrowDown") { sorot = Math.min(pilihan.length - 1, sorot + 1); tandaiSorot(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { sorot = Math.max(0, sorot - 1); tandaiSorot(); e.preventDefault(); }
    else if (e.key === "Enter") { jalankanPilihan(sorot); e.preventDefault(); }
  });

  // ---------------- Bantuan (cara pakai + pintasan) ----------------
  async function muatBantuan() {
    if (bantuan) return bantuan;
    const kode = SPS.i18n.aktif;
    bantuan = await ambil(`/app/static/bantuan/${kode}.json?v=${AWAL.versi}`) || await ambil(`/app/static/bantuan/id.json?v=${AWAL.versi}`) || {};
    return bantuan;
  }
  function topikHalaman() {
    if (!ruteAktif) return /\/superset\/dashboard\//.test(alamatBingkai) ? "lihat-dashboard" : "beranda";
    if (ruteAktif.id === "chart" && /^\/explore/.test(alamatBingkai)) return "explore";
    if (ruteAktif.id === "dashboard" && /\/superset\/dashboard\//.test(alamatBingkai)) return "lihat-dashboard";
    return ruteAktif.id;
  }
  async function bukaBantuan(topik) {
    const b = await muatBantuan(), id = topik || topikHalaman();
    const isi = b[id] || b.umum || {judul: t("Cara pakai"), ringkas: ""};
    const pintas = id === "pintasan" ? [] : (isi.pintasan || []);
    const umum = (b.pintasan && b.pintasan.pintasan) || [];
    // "Ctrl + K" = tekan bersamaan; "g → h" = tekan berurutan
    const tombol = k => k.split(" → ").map(u => u.split(" + ").map(x => `<kbd>${esc(x)}</kbd>`).join(" + ")).join(" → ");
    const baris = daftar => daftar.map(([k, v]) => `<span>${tombol(k)}</span><span>${esc(v)}</span>`).join("");
    $("#judulLaci").textContent = isi.judul || t("Cara pakai");
    $("#badanLaci").innerHTML =
      (isi.ringkas ? `<p>${esc(isi.ringkas)}</p>` : "") +
      (isi.langkah && isi.langkah.length ? `<section><h4>${esc(t("Langkah"))}</h4><ol>${isi.langkah.map(l => `<li>${esc(l)}</li>`).join("")}</ol></section>` : "") +
      (isi.tips && isi.tips.length ? isi.tips.map(x => `<div class="tip">💡 ${esc(x)}</div>`).join("") : "") +
      (pintas.length ? `<section><h4>${esc(t("Pintasan di halaman ini"))}</h4><div class="pintas">${baris(pintas)}</div></section>` : "") +
      `<section><h4>${esc(t("Pintasan di semua halaman"))}</h4><div class="pintas">${baris(umum)}</div></section>`;
    tutupSemua();
    $("#laci").classList.add("tampil"); tirai.classList.add("tampil");
    $("#tutupLaci").focus();
  }

  // ---------------- Pintasan keyboard ----------------
  const LOMPAT = {h: "beranda", d: "dashboard", c: "chart", s: "studio", k: "kueri", q: "sqllab", t: "dataset", y: "story"};
  let tungguG = 0;
  const sedangMengetik = el => el && (/^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName) || el.isContentEditable);
  function tanganiTombol(e) {
    const mod = e.ctrlKey || e.metaKey;
    if (mod && e.key.toLowerCase() === "k") { bukaPalet(); return true; }
    if (mod && e.key === "\\") { ringkas(); return true; }
    if (mod && e.key.toLowerCase() === "i" && SPS.ai && !$("#bukaAi").hidden) { SPS.ai.alih(); return true; }
    if (e.key === "Escape") { tutupSemua(); return true; }
    if (e.mengetik || mod || e.altKey) return false;
    if (e.key === "?") { bukaBantuan(); return true; }
    if (e.key === "g") { tungguG = Date.now(); return true; }
    if (Date.now() - tungguG < 1200 && LOMPAT[e.key]) {
      tungguG = 0;
      const n = NAV.find(x => x.id === LOMPAT[e.key]);
      if (n && (!n.izin || boleh.has(n.izin))) buka(n.alamat);
      return true;
    }
    return false;
  }
  document.addEventListener("keydown", e => {
    const ditangani = tanganiTombol({key: e.key, ctrlKey: e.ctrlKey, metaKey: e.metaKey, altKey: e.altKey,
                                     mengetik: sedangMengetik(document.activeElement)});
    if (ditangani && (e.ctrlKey || e.metaKey || e.key === "?")) e.preventDefault();
  });

  // ---------------- Lain-lain ----------------
  function ringkas() {
    document.body.classList.toggle("ringkas");
    simpanLokal("sps_ringkas", document.body.classList.contains("ringkas") ? "1" : "0");
  }
  SPS.notif = (teks) => {
    const n = $("#notif"); n.textContent = teks; n.classList.add("tampil");
    clearTimeout(SPS.notif.t); SPS.notif.t = setTimeout(() => n.classList.remove("tampil"), 2600);
  };
  SPS.buka = alamat => buka(alamat);
  SPS.halaman = () => ({alamat: bingkai.hidden ? "/app/" : alamatBingkai, judul: ($("#jejak b") || {}).textContent || "",
                        rute: ruteAktif ? ruteAktif.id : ""});
  SPS.bisa = izin => boleh.has(izin);
  SPS.nav = NAV;
  // Lencana "Resmi" (F5): dashboard/chart/dataset yang disertifikasi (Ubah properti › Sertifikasi).
  SPS.lencanaResmi = x => (x && x.certified_by ? ` <span class="lencana-resmi" title="${esc(t("Disertifikasi oleh") + " " + x.certified_by +
    (x.certification_details ? ": " + x.certification_details : ""))}">${ik("centang", 12)}${esc(t("Resmi"))}</span>` : "");

  async function mulai() {
    if (bacaLokal("sps_ringkas") === "1") document.body.classList.add("ringkas");
    await SPS.i18n.siap;
    SPS.i18n.amati(document.body);
    const p = AWAL.pengguna;
    $("#tombolRingkas").innerHTML = ik("lipat", 18);
    $("#tombolRingkas").title = t("Ringkas / lebarkan menu samping") + " (Ctrl + \\)";
    $("#tombolRingkas").setAttribute("aria-label", t("Ringkas menu"));
    $("#tombolAkun").innerHTML = `<span class="avatar">${esc(inisial(p.nama))}</span>`;
    $("#tombolAkun").title = p.nama;
    $("#tombolAkun").setAttribute("aria-label", t("Akun") + ": " + p.nama);
    $("#bukaNav").innerHTML = ik("menu");
    $("#bukaBantuan").innerHTML = ik("bantuan");
    $("#bukaTab").innerHTML = ik("bukaTab", 18);
    $("#bukaLainnya").innerHTML = ik("lainnya");
    $("#bukaLainnya").onclick = () => {                // ponsel: isi menu = tombol bilah atas yang sedang tersedia
      const item = [["bukaUlasan", "komentar", "Komentar & rating"], ["bukaTelusur", "telusur", "Telusuri ke dashboard lain"],
                    ["bukaFilter", "corong", "Filter global"],
                    ["bukaAi", "ai", "Asisten AI"], ["bukaBantuan", "bantuan", "Cara pakai halaman ini"]]
        .filter(([id]) => !$("#" + id).hidden);
      const m = menuMengambang($("#bukaLainnya"), item.map(([id, ikon, label]) =>
        `<button type="button" data-tombol="${id}">${ik(ikon, 18)}<span>${esc(t(label))}</span></button>`).join(""));
      m.querySelectorAll("[data-tombol]").forEach(b => b.onclick = () => {
        m.classList.remove("tampil"); tirai.classList.remove("tampil", "bening"); $("#" + b.dataset.tombol).click();
      });
    };
    $("#ikonCari").innerHTML = ik("cari");
    $("#bukaPalet").insertAdjacentHTML("afterbegin", ik("cari", 18));
    $("#tutupLaci").innerHTML = ik("tutup");
    $("#teksCari").textContent = t("Cari atau jalankan perintah…");
    $("#bukaPalet").querySelector("kbd").textContent = /Mac|iPhone|iPad/.test(navigator.platform) ? "⌘ K" : "Ctrl K";
    $("#bukaPalet").onclick = () => bukaPalet();
    $("#bukaBantuan").onclick = () => bukaBantuan();
    $("#tutupLaci").onclick = tutupSemua;
    $("#tombolAkun").onclick = e => menuAkun(e.currentTarget);
    $("#tombolRingkas").onclick = ringkas;
    $("#bukaNav").onclick = () => { document.body.classList.add("laci-nav"); tirai.classList.add("tampil"); };
    $("#bukaTab").onclick = () => window.open(bingkai.hidden ? "/app/" : "/app/?p=" + encodeURIComponent(alamatBingkai), "_blank");
    document.querySelector(".merek").onclick = e => { e.preventDefault(); buka("beranda"); };

    const menu = await ambil("/api/v1/menu/");
    kumpulkanMenu(menu && menu.result);
    gambarNav();
    SPS.siapAi && SPS.siapAi();
    buka(awalDariUrl(), {dorong: false});
    history.replaceState({p: awalDariUrl()}, "", location.pathname + location.search);
  }
  // Pemberitahuan (@sebut & balasan komentar) + lencana komentar menunggu moderasi (Superadmin).
  // Titik di avatar = ada yang belum dibaca / ditinjau. Diperbarui tiap 2 menit.
  let NOTIF = {belum_dibaca: 0, daftar: []}, MENUNGGU = 0;
  const tandaAvatar = () => $("#tombolAkun").classList.toggle("ada-tugas", NOTIF.belum_dibaca > 0 || MENUNGGU > 0);
  async function lencanaModerasi() {
    NOTIF = (await ambil("/ulasan/api/notifikasi")) || NOTIF;
    tandaAvatar();
    if (!AWAL.pengguna.superadmin) return;
    const j = await ambil("/ulasan/api/menunggu");
    const n = (j && j.menunggu) || 0, a = document.querySelector('.nav [data-rute="moderasi"]');
    if (a) {
      let l = a.querySelector(".lencana-nav");
      if (!l) { l = document.createElement("span"); l.className = "lencana-nav"; a.appendChild(l); }
      l.textContent = n > 99 ? "99+" : n; l.hidden = !n;
      l.title = t("Komentar menunggu moderasi");
    }
    MENUNGGU = n; tandaAvatar();
  }

  mulai().then(() => { lencanaModerasi(); setInterval(lencanaModerasi, 120000); });
})();
