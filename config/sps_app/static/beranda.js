// Beranda: titik mulai yang efisien.
//   0. Siapkan ALDx         (Admin) daftar periksa sesudah instalasi: AI, data, pengguna, identitas, cadangan;
//                            hilang sendiri bila semua selesai, bisa disembunyikan
//   1. Tanya / cari          ketik nama dashboard/chart/dataset, atau pertanyaan untuk Asisten AI
//   2. Bangun laporan        5 langkah berurutan: data -> siapkan -> chart -> dashboard -> story,
//                            dengan jumlah milik sistem & sorotan "langkah berikutnya"
//   3. Lanjutkan             yang terakhir Anda buka (log aktivitas Superset)
//   4. Dashboard             favorit & terbaru
(function () {
  "use strict";
  const $ = s => document.querySelector(s);
  const {t} = SPS.i18n;
  const ik = SPS.ikon;
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const ambil = url => fetch(url, {credentials: "same-origin"}).then(r => (r.ok ? r.json() : null)).catch(() => null);
  const angka = n => (n == null ? "–" : Number(n).toLocaleString(SPS.i18n.aktif === "id" ? "id-ID" : SPS.i18n.aktif));
  let sudahDigambar = false;

  // Waktu relatif dari Superset ("2 hours ago") ke bahasa aktif (Indonesia); bahasa lain apa adanya.
  const WAKTU = [[/^a few seconds ago$/, "baru saja"], [/^a minute ago$/, "1 menit lalu"], [/^(\d+) minutes ago$/, "$1 menit lalu"],
    [/^an hour ago$/, "1 jam lalu"], [/^(\d+) hours ago$/, "$1 jam lalu"], [/^a day ago$/, "1 hari lalu"], [/^(\d+) days ago$/, "$1 hari lalu"],
    [/^a month ago$/, "1 bulan lalu"], [/^(\d+) months ago$/, "$1 bulan lalu"], [/^a year ago$/, "1 tahun lalu"], [/^(\d+) years ago$/, "$1 tahun lalu"]];
  const waktu = s => {
    if (SPS.i18n.aktif !== "id") return s || "";
    const w = WAKTU.find(([pola]) => pola.test(s || ""));
    return w ? String(s).replace(w[0], w[1]) : (s || "");
  };

  // ---------------- Siapkan ALDx (Admin) ----------------
  const PERSIAPAN = {
    ai: {judul: "Sambungkan Asisten AI", ket: "Model lokal (Ollama, LM Studio) terdeteksi otomatis, atau tempel key cloud gratis.",
         ikon: "ai", aksi: () => SPS.ai.sambungkan()},
    data: {judul: "Hubungkan data kantor", ket: "Database, data warehouse, atau berkas Excel/Access/CSV.",
           ikon: "sambung", aksi: () => SPS.buka("/pusat-kendali/?tab=hubungkan")},
    pengguna: {judul: "Tambahkan pengguna", ket: "Akun rekan kerja dan perannya (Pengguna, Analis, Admin).",
               ikon: "pengguna", aksi: () => SPS.buka("/users/")},
    identitas: {judul: "Pasang nama & logo", ket: "Nama perusahaan, logo, dan warna tampil di semua halaman.",
                ikon: "studio", aksi: () => SPS.buka("/pusat-kendali/?tab=identitas")},
    cadangan: {judul: "Jadwalkan cadangan", ket: "Sekali saja: scripts\\jadwal-cadangan.ps1 (Run as administrator).",
               ikon: "simpan", aksi: () => SPS.buka("/panduan/19-runbook-faq-admin")},
  };
  const KUNCI_SEMBUNYI = "sps_persiapan_sembunyi";
  async function isiPersiapan() {
    const wadah = $("#persiapan");
    if (!wadah) return;
    let sembunyi = false;
    try { sembunyi = localStorage.getItem(KUNCI_SEMBUNYI) === "1"; } catch (e) { /* mode privat */ }
    const j = await ambil("/app/api/persiapan");
    if (!j || !j.total || j.selesai === j.total || sembunyi) { wadah.hidden = true; return; }
    const persen = Math.round(j.selesai / j.total * 100), keliling = 2 * Math.PI * 22;
    const berikut = j.langkah.find(x => !x.selesai);
    wadah.hidden = false;
    wadah.innerHTML = `<div class="kepala-siap">
        <svg class="cincin" viewBox="0 0 52 52" aria-hidden="true"><circle cx="26" cy="26" r="22"/><circle class="isi" cx="26" cy="26" r="22"
          stroke-dasharray="${keliling}" stroke-dashoffset="${keliling * (1 - j.selesai / j.total)}"/></svg>
        <span class="persen">${persen}%</span>
        <div><h2>${esc(t("Siapkan ALDx"))}</h2><small>${j.selesai} ${esc(t("dari"))} ${j.total} ${esc(t("langkah selesai. Bisa dikerjakan kapan saja."))}</small></div>
        <button class="tombol-ikon" type="button" id="sembunyiSiap" title="${esc(t("Sembunyikan"))}" aria-label="${esc(t("Sembunyikan"))}">${ik("tutup", 18)}</button>
      </div>
      <div class="daftar-siap">${j.langkah.map(x => { const p = PERSIAPAN[x.id]; return `
        <button type="button" class="langkah-siap ${x.selesai ? "selesai" : ""} ${x === berikut ? "berikut" : ""}" data-siap="${x.id}">
          <span class="tanda">${x.selesai ? ik("centang", 14) : ik(p.ikon, 16)}</span>
          <span class="teks"><b>${esc(t(p.judul))}</b><small>${esc(t(p.ket))}</small></span>
          <span class="aksi">${x.selesai ? esc(t("Selesai")) : esc(t("Mulai")) + " →"}</span></button>`; }).join("")}</div>`;
    wadah.querySelectorAll("[data-siap]").forEach(b => b.onclick = () => PERSIAPAN[b.dataset.siap].aksi());
    $("#sembunyiSiap").onclick = () => { try { localStorage.setItem(KUNCI_SEMBUNYI, "1"); } catch (e) { /* abaikan */ } wadah.hidden = true; };
  }

  function sapaan() {
    const j = new Date().getHours();
    return j < 11 ? t("Selamat pagi") : j < 15 ? t("Selamat siang") : j < 18 ? t("Selamat sore") : t("Selamat malam");
  }
  const LANGKAH = [
    {no: 1, izin: "Hubungkan data", ikon: "sambung", judul: "Sambungkan data", ket: "Hubungkan database atau unggah Excel/CSV, lalu jadikan dataset.",
     alamat: () => (SPS.bisa("Hubungkan data") ? "/pusat-kendali/?tab=hubungkan" : "/tablemodelview/list/"), hitung: "dataset", satuan: "dataset"},
    {no: 2, izin: "Persiapan data", ikon: "siapkan", judul: "Siapkan data", ket: "Bersihkan, gabung, dan hitung kolom baru tanpa SQL.",
     alamat: () => "/studio/?tab=prep", hitung: null, satuan: ""},
    {no: 3, izin: "Studio Visual", ikon: "studio", judul: "Buat chart", ket: "Seret kolom di Studio Visual; grafik langsung jadi.",
     alamat: () => "/studio/", hitung: "chart", satuan: "chart"},
    {no: 4, izin: "Studio Visual", ikon: "dashboard", judul: "Susun dashboard", ket: "Gabungkan chart dan filter menjadi satu halaman.",
     alamat: () => "/studio/?tab=dasbor", hitung: "dashboard", satuan: "dashboard"},
    {no: 5, izin: "Story", ikon: "story", judul: "Ceritakan dengan story", ket: "Rangkai beberapa dashboard menjadi presentasi berurutan.",
     alamat: () => "/asisten/?tab=story", hitung: "story", satuan: "story"},
  ];

  // Hanya langkah yang boleh dikerjakan pengguna ini (pengguna baca-saja tidak melihat bagian ini).
  const langkahSaya = () => LANGKAH.filter(l => SPS.bisa(l.izin));

  function kerangka() {
    const p = window.SPS_AWAL.pengguna;
    const langkah = langkahSaya();
    const ai = SPS.bisa("Asisten AI");
    $("#beranda").innerHTML = `<div class="lebar">
      <div class="sapa"><h1>${esc(sapaan())}, ${esc((p.nama || "").split(" ")[0])}</h1>
        <p>${esc(t("Mau mulai dari mana hari ini?"))}</p></div>
      <form class="tanya" id="formTanya">${ik("cari")}
        <input id="masukanTanya" autocomplete="off" placeholder="${esc(ai ? t("Cari data, chart, dashboard… atau tanya AI") : t("Cari dashboard, chart, dataset…"))}">
        ${ai ? `<button class="tombol" type="button" id="tombolAi">${ik("ai", 18)}${esc(t("Tanya AI"))}</button>` : ""}
        <button class="tombol utama besar" type="submit">${esc(t("Cari"))}</button></form>
      ${p.admin ? `<section class="kartu-siap" id="persiapan" hidden></section>` : ""}
      ${langkah.length ? `<section><div class="judul-bagian"><h2>${esc(t("Bangun laporan, langkah demi langkah"))}</h2></div>
        <div class="alur" id="alur" style="--jumlah-langkah:${langkah.length}">${langkah.map(l => `
          <a class="langkah-kartu" href="#" data-no="${l.no}">
            <span class="no">${l.no}</span><span class="ikon-bulat">${ik(l.ikon)}</span>
            <b>${esc(t(l.judul))}</b><small>${esc(t(l.ket))}</small>
            <span class="angka" data-hitung="${l.hitung || ""}">${l.hitung ? "…" : ""}</span></a>`).join("")}</div></section>` : ""}
      <div class="dua-kolom">
        <section><div class="judul-bagian"><h2>${esc(t("Lanjutkan"))}</h2></div>
          <div class="daftar" id="terakhir"><div class="kerangka-muat"></div><div class="kerangka-muat"></div><div class="kerangka-muat"></div></div></section>
        <section><div class="judul-bagian"><h2>${esc(t("Dashboard"))}</h2><a href="#" id="semuaDashboard">${esc(t("Lihat semua"))} →</a></div>
          <div class="daftar" id="dashboardBeranda"><div class="kerangka-muat"></div><div class="kerangka-muat"></div></div></section>
      </div></div>`;
    $("#formTanya").onsubmit = e => { e.preventDefault(); cari($("#masukanTanya").value); };
    if (ai) $("#tombolAi").onclick = () => SPS.ai.tanya($("#masukanTanya").value.trim());
    $("#semuaDashboard").onclick = e => { e.preventDefault(); SPS.buka("/dashboard/list/"); };
    document.querySelectorAll(".langkah-kartu").forEach(a => a.onclick = e => {
      e.preventDefault(); SPS.buka(LANGKAH.find(l => l.no === +a.dataset.no).alamat());
    });
  }
  function cari(q) {
    q = q.trim();
    document.dispatchEvent(new KeyboardEvent("keydown", {key: "k", ctrlKey: true}));   // buka palet
    const m = document.querySelector("#masukanPalet");
    m.value = q; m.dispatchEvent(new Event("input"));
  }

  async function isiAngka() {
    const jumlah = async api => { const j = await ambil(`/api/v1/${api}/?q=(page_size:1,columns:!(id))`); return j ? j.count : null; };
    const story = ambil("/asisten/api/story").then(j => (Array.isArray(j) ? j.length : (j && j.story ? j.story.length : null)));
    const [ds, ch, db, st] = await Promise.all([jumlah("dataset"), jumlah("chart"), jumlah("dashboard"), story]);
    const nilai = {dataset: ds, chart: ch, dashboard: db, story: st};
    let berikutnya = null;
    for (const l of langkahSaya()) {
      const el = document.querySelector(`.langkah-kartu[data-no="${l.no}"]`);
      if (l.hitung) el.querySelector(".angka").innerHTML = `${angka(nilai[l.hitung])}<small>${esc(t(l.satuan))}</small>`;
      if (!berikutnya && l.hitung && nilai[l.hitung] === 0) berikutnya = el;
    }
    if (berikutnya) { berikutnya.classList.add("berikutnya"); berikutnya.dataset.saran = t("Langkah berikutnya"); }
  }

  const IKON_JENIS = {dashboard: "dashboard", slice: "chart", chart: "chart", table: "tabel", dataset: "tabel"};
  async function isiTerakhir() {
    const j = await ambil("/api/v1/log/recent_activity/?q=(page_size:6)");
    const daftar = (j && j.result) || [];
    $("#terakhir").innerHTML = daftar.length ? daftar.map(x => `
      <a href="#" data-alamat="${esc(x.item_url)}"><span class="ikon-bulat">${ik(IKON_JENIS[x.item_type] || "chart", 18)}</span>
        <span class="teks"><b>${esc(x.item_title)}</b><small>${esc(t(x.item_type === "dashboard" ? "Dashboard" : "Chart"))} · ${esc(waktu(x.time_delta_humanized))}</small></span></a>`).join("")
      : `<div class="kosong">${esc(t("Belum ada yang dibuka. Mulai dari langkah 1 di atas."))}</div>`;
    pasangTautan("#terakhir");
  }
  async function isiDashboard() {
    const kolom = "columns:!(id,dashboard_title,url,changed_on_delta_humanized,published,certified_by,certification_details)";
    const [fav, baru] = await Promise.all([
      ambil(`/api/v1/dashboard/?q=(filters:!((col:id,opr:dashboard_is_favorite,value:!t)),page_size:5,${kolom})`),
      ambil(`/api/v1/dashboard/?q=(order_column:changed_on_delta_humanized,order_direction:desc,page_size:6,${kolom})`)]);
    const lihat = new Set(), daftar = [];
    for (const [sumber, bintang] of [[fav, true], [baru, false]]) for (const d of (sumber && sumber.result) || [])
      if (!lihat.has(d.id) && daftar.length < 6) { lihat.add(d.id); daftar.push({...d, bintang}); }
    $("#dashboardBeranda").innerHTML = daftar.length ? daftar.map(d => `
      <a href="#" data-alamat="${esc(d.url || `/superset/dashboard/${d.id}/`)}"><span class="ikon-bulat">${ik(d.bintang ? "bintang" : "dashboard", 18)}</span>
        <span class="teks"><b>${esc(d.dashboard_title)}${SPS.lencanaResmi(d)}</b><small>${esc(d.published ? t("Terbit") : t("Draf"))} · ${esc(waktu(d.changed_on_delta_humanized))}</small></span></a>`).join("")
      : `<div class="kosong">${esc(t("Belum ada dashboard."))}</div>`;
    pasangTautan("#dashboardBeranda");
  }
  function pasangTautan(sel) {
    document.querySelectorAll(`${sel} [data-alamat]`).forEach(a => a.onclick = e => { e.preventDefault(); SPS.buka(a.dataset.alamat); });
  }

  SPS.beranda = {
    tampil() {
      if (!sudahDigambar) { kerangka(); sudahDigambar = true; }
      isiPersiapan(); isiAngka(); isiTerakhir(); isiDashboard();
    },
  };
})();
