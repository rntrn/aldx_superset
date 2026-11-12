/* =============================================================================
   Studio Visual — PENYUSUN DASHBOARD
     Seret lembar kerja ke kanvas; tiap baris maksimal 12 kolom (¼ ⅓ ½ ⅔ penuh).
     Objek desain (padanan "Objects" Tableau/Power BI): Teks (huruf, ukuran, warna, latar, rata),
     Gambar (unggah ke server) dan Garis pemisah. Validasi & render akhir di server: sps_studio/objek.py.
   ============================================================================= */
"use strict";

(() => {
  const LEBAR = {3: "¼", 4: "⅓", 6: "½", 8: "⅔", 12: "Penuh"};
  const D = {id: null, baris: [], filter: []};  // baris: [[{chart_id, lebar, judul} | objek]] atau [{jenis: "garis"}]
  // filter: [{nama, dataset_id, kolom, jenis: "pilihan"|"rentang", nilai, min, max}] (nilai/min/max = pratinjau)
  const cacheHasil = new Map();                  // chart_id -> hasil query (dengan filter aktif)
  const cacheBidang = new Map();                 // dataset_id -> daftar nama kolom (huruf kecil)

  const lembarById = id => Studio.awal.lembar.find(l => l.id === Number(id));
  const totalLebar = row => row.reduce((s, k) => s + (k.lebar || 0), 0);
  const barisGaris = row => row[0]?.jenis === "garis";
  const TINGGI = {6: "Pendek (±50 px)", 10: "Sedang (±80 px)", 16: "Tinggi (±130 px)", 26: "Besar (±210 px)",
                  40: "Sangat besar (±320 px)", 52: "Setinggi chart (±420 px)"};
  const OBJEK_BARU = {
    teks: () => ({jenis: "teks", lebar: 12, tinggi: 10, teks: "Judul bagian", huruf: "bawaan", ukuran: 24, tebal: true,
                  miring: false, warna: "#111827", latar: "", rata: "left", tegak: "center"}),
    gambar: () => ({jenis: "gambar", lebar: 3, tinggi: 10, gambar: "", alt: "", rata: "center", pas: "contain"}),
  };
  const keluargaHuruf = k => (Studio.awal.huruf || []).find(h => h.kunci === k)?.keluarga || "inherit";

  // Cermin html_objek() di objek.py untuk pratinjau di kanvas (hasil akhir tetap dirender server).
  function htmlObjek(o) {
    if (o.jenis === "teks") {
      const tegak = {start: "flex-start", center: "center", end: "flex-end"}[o.tegak] || "center";
      return `<div style="display:flex;flex-direction:column;justify-content:${tegak};height:100%;box-sizing:border-box;
        padding:6px 14px;border-radius:10px;line-height:1.25;font-family:${keluargaHuruf(o.huruf)};font-size:${o.ukuran}px;
        font-weight:${o.tebal ? 700 : 400};font-style:${o.miring ? "italic" : "normal"};color:${o.warna};text-align:${o.rata};
        background:${o.latar || "transparent"}"><div>${esc(o.teks).replace(/\n/g, "<br>")}</div></div>`;
    }
    if (!o.gambar) return '<div class="kosongBesar ket">Belum ada gambar. Klik Atur.</div>';
    const rata = {left: "flex-start", center: "center", right: "flex-end"}[o.rata];
    const ukuran = o.pas === "cover" ? "width:100%;height:100%" : "max-width:100%;max-height:100%";
    return `<div style="display:flex;align-items:center;justify-content:${rata};height:100%">
      <img src="/studio/gambar/${esc(o.gambar)}" alt="${esc(o.alt)}" style="${ukuran};object-fit:${o.pas};border-radius:8px"></div>`;
  }

  function renderDaftar() {
    const cari = $("#cariLembarD").value.trim().toLowerCase();
    const dipakai = new Set(D.baris.flat().map(k => k.chart_id));
    $("#daftarLembarD").innerHTML = Studio.awal.lembar.filter(l => !cari || l.judul.toLowerCase().includes(cari)).map(l =>
      `<div class="bidang dimensi" draggable="true" data-id="${l.id}" style="color:var(--teks);${dipakai.has(l.id) ? "opacity:.45" : ""}">
        <span class="tag">${esc((Studio.awal.aturan[l.tanda]?.label || "").slice(0, 4))}</span>${esc(l.judul)}</div>`).join("")
      || '<div class="ket">Belum ada lembar kerja tersimpan. Buat di tab Lembar kerja.</div>';
    $$("#daftarLembarD [data-id]").forEach(el => {
      el.ondragstart = e => e.dataTransfer.setData("text/plain", JSON.stringify({baru: Number(el.dataset.id)}));
    });
  }

  function renderKanvas() {
    const k = $("#kanvasDasbor");
    k.innerHTML = "";
    D.baris.forEach((row, r) => k.appendChild(elBaris(row, r)));
    const baru = document.createElement("div");
    baru.className = "drow baru"; baru.textContent = "Seret lembar kerja ke sini untuk baris baru";
    zonaJatuh(baru, D.baris.length);
    k.appendChild(baru);
    renderDaftar();
  }

  function elBaris(row, r) {
    const el = document.createElement("div");
    if (barisGaris(row)) {
      el.className = "drow garis"; el.draggable = true;
      el.innerHTML = '<hr><span>Garis pemisah</span><button class="kecil">Hapus</button>';
      el.ondragstart = e => e.dataTransfer.setData("text/plain", JSON.stringify({garisDari: r}));
      $("button", el).onclick = () => { D.baris.splice(r, 1); renderKanvas(); };
      zonaJatuh(el, r);
      return el;
    }
    el.className = "drow" + (totalLebar(row) > 12 ? " penuh" : "");
    row.forEach((kotak, i) => el.appendChild(elKotak(kotak, r, i)));
    zonaJatuh(el, r);
    return el;
  }

  function elKotak(kotak, r, i) {
    const el = document.createElement("div"), objek = !!kotak.jenis;
    el.className = "dtile" + (objek ? " objek" : ""); el.draggable = true;
    el.style.flex = `0 0 calc(${kotak.lebar / 12 * 100}% - ${10 * (1 - kotak.lebar / 12)}px)`;
    const judul = objek ? (kotak.jenis === "teks" ? "Teks" : "Gambar") : kotak.judul;
    el.innerHTML = `<div class="kepala"><span title="${esc(judul)}">${esc(judul)}</span>
      <select title="Lebar">${Object.entries(LEBAR).map(([v, t]) => `<option value="${v}" ${Number(v) === kotak.lebar ? "selected" : ""}>${t}</option>`).join("")}</select>
      ${objek ? '<button class="kecil" data-atur>Atur</button>' : ""}<button class="kecil" data-hapus>Hapus</button></div><div class="mini"></div>`;
    el.ondragstart = e => { e.stopPropagation(); e.dataTransfer.setData("text/plain", JSON.stringify({r, i})); };
    $("select", el).onchange = e => { kotak.lebar = Number(e.target.value); renderKanvas(); };
    $("[data-hapus]", el).onclick = () => { D.baris[r].splice(i, 1); D.baris = D.baris.filter(b => b.length); renderKanvas(); };
    if (objek) {
      $("[data-atur]", el).onclick = () => aturObjek(kotak);
      const mini = $(".mini", el);
      mini.style.height = `${Math.min(kotak.tinggi * 8, 420)}px`;
      mini.innerHTML = htmlObjek(kotak);
    } else requestAnimationFrame(() => gambarMini($(".mini", el), kotak.chart_id));
    return el;
  }

  async function gambarMini(el, chartId) {
    const l = lembarById(chartId);
    if (!l || !l.spec?.tanda) { el.innerHTML = '<div class="kosongBesar ket">Pratinjau tidak tersedia</div>'; return; }
    try {
      if (!cacheHasil.has(chartId)) {
        const tambahan = await filterUntuk(l.spec.dataset_id);
        cacheHasil.set(chartId, await Studio.api("/studio/api/kueri", {...l.spec, batas: 500, filter: [...(l.spec.filter || []), ...tambahan]}));
      }
      const s = l.spec, horizontal = (s.baris || []).some(p => p.peran === "dimensi") && !(s.kolom || []).some(p => p.peran === "dimensi");
      Studio.gambar(el, cacheHasil.get(chartId), s.tanda, {mini: true, horizontal, label: false});
    } catch (e) { el.innerHTML = `<div class="kosongBesar ket">${esc(e.message)}</div>`; }
  }

  function zonaJatuh(el, r) {
    el.ondragover = e => { e.preventDefault(); el.classList.add("over"); };
    el.ondragleave = () => el.classList.remove("over");
    el.ondrop = e => {
      e.preventDefault(); el.classList.remove("over");
      const d = JSON.parse(e.dataTransfer.getData("text/plain"));
      // Garis pemisah selalu satu baris sendiri, diletakkan sebelum baris tujuan (atau di akhir).
      if (d.objek === "garis" || d.garisDari !== undefined) {
        if (d.garisDari !== undefined) { D.baris.splice(d.garisDari, 1); if (d.garisDari < r) r -= 1; }
        D.baris.splice(Math.min(r, D.baris.length), 0, [{jenis: "garis"}]);
        renderKanvas(); return;
      }
      if (D.baris[r] && barisGaris(D.baris[r])) r += 1;     // jatuh di garis -> baris baru setelahnya
      let kotak, aturSetelah = false;
      if (d.objek) { kotak = OBJEK_BARU[d.objek](); aturSetelah = true; }
      else if (d.baru) {
        if (D.baris.flat().some(k => k.chart_id === d.baru)) { Studio.notif("Lembar kerja ini sudah ada di dashboard.", true); return; }
        const l = lembarById(d.baru);
        kotak = {chart_id: d.baru, judul: l.judul, lebar: l.tanda === "angka" ? 3 : 6};
      } else {
        kotak = D.baris[d.r].splice(d.i, 1)[0];
        if (d.r < r && !D.baris[d.r].length) r -= 1;          // baris asal kosong ikut hilang
        D.baris = D.baris.filter(b => b.length);
      }
      const tujuan = D.baris[r];
      if (!tujuan || barisGaris(tujuan)) D.baris.splice(r, 0, [kotak]);
      else {
        const sisa = 12 - totalLebar(tujuan);
        if (sisa < 3) { Studio.notif("Baris ini sudah penuh. Kecilkan lebar kotak lain atau seret ke baris baru.", true); D.baris.push([kotak]); }
        else { kotak.lebar = Math.min(kotak.lebar, Math.max(...Object.keys(LEBAR).map(Number).filter(v => v <= sisa))); tujuan.push(kotak); }
      }
      renderKanvas();
      if (aturSetelah) aturObjek(kotak);
    };
  }

  /* ---------- Filter dashboard (filter tampil di dashboard) ---------- */
  async function kolomDataset(id) {
    if (!cacheBidang.has(id)) {
      const b = await Studio.api(`/studio/api/bidang/${id}`);
      cacheBidang.set(id, [...b.dimensi, ...b.ukuran].filter(x => !x.metrik && x.field !== "__baris__"));
    }
    return cacheBidang.get(id);
  }
  // Seperti Superset: filter berlaku untuk dataset yang punya kolom bernama sama.
  async function filterUntuk(datasetId) {
    const kolom = (await kolomDataset(datasetId)).map(x => x.field);
    return D.filter.flatMap(f => {
      const nama = kolom.find(k => k.toLowerCase() === f.kolom.toLowerCase());
      if (!nama) return [];
      if (f.jenis === "waktu") return [];                    // rentang waktu hanya diatur di dashboard jadi
      if (f.jenis === "pilihan") return f.nilai?.length ? [{field: nama, op: "IN", nilai: f.nilai}] : [];
      return [f.min != null && {field: nama, op: ">=", nilai: f.min}, f.max != null && {field: nama, op: "<=", nilai: f.max}].filter(Boolean);
    });
  }
  const ringkasFilter = f => f.jenis === "pilihan" ? (f.nilai?.length ? f.nilai.join(", ") : "semua")
    : [f.min != null && `≥ ${fmtPenuh.format(f.min)}`, f.max != null && `≤ ${fmtPenuh.format(f.max)}`].filter(Boolean).join(" · ") || "semua";

  function renderFilter() {
    const el = $("#filterDasbor");
    el.innerHTML = `<span class="label">Filter</span>` + D.filter.map((f, i) =>
      `<div class="fchip ${(f.nilai?.length || f.min != null || f.max != null) ? "aktif" : ""}"><b>${esc(f.nama)}</b>
        <span class="nilai" title="${esc(ringkasFilter(f))}">${esc(ringkasFilter(f))}</span>
        <button class="kecil" data-atur="${i}">Pilih</button><button class="kecil" data-hapus="${i}">Hapus</button></div>`).join("") +
      `<button class="kedua" id="tambahFilter">Tambah filter</button>
       <span class="ket">Klik chart di dashboard juga menyaring chart lain (cross filter).</span>`;
    $("#tambahFilter").onclick = dialogTambahFilter;
    $$("[data-atur]", el).forEach(b => b.onclick = () => aturFilter(D.filter[b.dataset.atur]));
    $$("[data-hapus]", el).forEach(b => b.onclick = () => { D.filter.splice(Number(b.dataset.hapus), 1); segarkanTile(); });
  }
  function segarkanTile() { cacheHasil.clear(); renderFilter(); renderKanvas(); }

  async function dialogTambahFilter() {
    const dipakai = [...new Set(D.baris.flat().map(k => lembarById(k.chart_id)?.spec?.dataset_id).filter(Boolean))];
    const pilihan = dipakai.length ? Studio.awal.dataset.filter(d => dipakai.includes(d.id)) : Studio.awal.dataset;
    Studio.dialog({judul: "Tambah filter dashboard", ok: "Tambah", isi: `
      <label>Dataset<select id="fdDs">${pilihan.map(d => `<option value="${d.id}">${esc(d.nama)}</option>`).join("")}</select></label>
      <label style="display:block;margin-top:8px">Kolom<select id="fdKolom"></select></label>
      <label style="display:block;margin-top:8px">Nama di dashboard<input type="text" id="fdNama" placeholder="mis. Cabang"></label>
      <label style="display:block;margin-top:8px">Jenis<select id="fdJenis"><option value="pilihan">Pilihan nilai (dropdown)</option><option value="rentang">Rentang angka</option><option value="waktu">Rentang waktu (tanggal)</option></select></label>
      <p class="ket">Filter berlaku untuk semua chart yang datanya punya kolom dengan nama sama.</p>`,
      padaOk: () => {
        const kolom = $("#fdKolom").value;
        if (!kolom) return false;
        D.filter.push({nama: $("#fdNama").value.trim() || kolom, dataset_id: Number($("#fdDs").value), kolom, jenis: $("#fdJenis").value});
        segarkanTile();
      }});
    const isiKolom = async () => {
      const k = await kolomDataset(Number($("#fdDs").value));
      const jenis = $("#fdJenis").value;
      $("#fdKolom").innerHTML = k.filter(x => jenis === "rentang" ? (x.peran === "ukuran" || x.jenis === "angka")
          : jenis === "waktu" ? (x.waktu || x.dttm) : x.peran === "dimensi")
        .map(x => `<option>${esc(x.field)}</option>`).join("");
    };
    $("#fdDs").onchange = isiKolom; $("#fdJenis").onchange = isiKolom;
    isiKolom();
  }

  async function aturFilter(f) {
    if (f.jenis === "waktu") { Studio.notif("Rentang waktu dipilih pengguna di dashboard (mis. 30 hari terakhir); tidak ada pratinjau di Studio."); return; }
    if (f.jenis === "rentang") {
      Studio.dialog({judul: `Filter: ${f.nama}`, isi: `<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
        <label>Minimal<input type="number" id="fdMin" value="${f.min ?? ""}"></label><label>Maksimal<input type="number" id="fdMaks" value="${f.max ?? ""}"></label></div>
        <p class="ket">Hanya untuk pratinjau di Studio; di dashboard pengguna mengatur sendiri.</p>`,
        padaOk: () => { f.min = $("#fdMin").value === "" ? null : Number($("#fdMin").value);
                        f.max = $("#fdMaks").value === "" ? null : Number($("#fdMaks").value); segarkanTile(); }});
      return;
    }
    let nilai;
    try { nilai = await Studio.api(`/studio/api/nilai/${f.dataset_id}?kolom=${encodeURIComponent(f.kolom)}`); }
    catch (e) { Studio.notif(esc(e.message), true); return; }
    const dipilih = new Set((f.nilai || []).map(String));
    Studio.dialog({judul: `Filter: ${f.nama}`, isi: `<p class="ket">Kosongkan semua = tanpa filter. Hanya untuk pratinjau di Studio.</p>
      <div class="nilaiList" id="fdNilai">${nilai.map(v => `<label><input type="checkbox" value="${esc(v)}" ${dipilih.has(String(v)) ? "checked" : ""}> ${esc(v ?? "(kosong)")}</label>`).join("")}</div>`,
      padaOk: () => { f.nilai = $$("#fdNilai input:checked").map(c => nilai.find(v => String(v) === c.value)); segarkanTile(); }});
  }

  /* ---------- Objek: dialog Atur ---------- */
  const opsi = (daftar, pilih) => Object.entries(daftar).map(([v, t]) => `<option value="${v}" ${String(v) === String(pilih) ? "selected" : ""}>${esc(t)}</option>`).join("");
  const RATA = {left: "Kiri", center: "Tengah", right: "Kanan"};
  const swatch = sasaran => `<div class="swatch">${["#111827", "#6B7280", "#FFFFFF", ...(Studio.awal.warna || [])].map(w =>
    `<button type="button" style="background:${w}" title="${w}" data-sasaran="${sasaran}" data-w="${w}"></button>`).join("")}</div>`;

  function aturObjek(o) {
    const s = {...o};                                    // salinan: Batal tidak mengubah apa pun
    const isi = o.jenis === "teks" ? `<div class="dlgObjek">
        <label class="penuh">Teks (Enter = baris baru)<textarea id="oTeks">${esc(s.teks)}</textarea></label>
        <label>Huruf<select id="oHuruf">${opsi(Object.fromEntries((Studio.awal.huruf || []).map(h => [h.kunci, h.label])), s.huruf)}</select></label>
        <label>Ukuran (px)<input type="number" id="oUkuran" min="10" max="96" value="${s.ukuran}"></label>
        <label class="cek"><input type="checkbox" id="oTebal" ${s.tebal ? "checked" : ""}> Tebal</label>
        <label class="cek"><input type="checkbox" id="oMiring" ${s.miring ? "checked" : ""}> Miring</label>
        <label>Warna teks<input type="color" id="oWarna" value="${s.warna}">${swatch("oWarna")}</label>
        <label>Latar<input type="color" id="oLatar" value="${s.latar || "#FFFFFF"}">${swatch("oLatar")}
          <span class="cek" style="display:flex;gap:6px;align-items:center"><input type="checkbox" id="oTanpaLatar" ${s.latar ? "" : "checked"}> Tanpa latar</span></label>
        <label>Rata<select id="oRata">${opsi(RATA, s.rata)}</select></label>
        <label>Posisi tegak<select id="oTegak">${opsi({start: "Atas", center: "Tengah", end: "Bawah"}, s.tegak)}</select></label>
        <label class="penuh">Tinggi kotak<select id="oTinggi">${opsi(TINGGI, s.tinggi)}</select></label>
        <div class="penuh contohObjek" id="oContoh"></div></div>`
      : `<div class="dlgObjek">
        <label class="penuh">Berkas gambar (PNG, JPEG, WebP, GIF; maks. 3 MB)<input type="file" id="oBerkas" accept="image/png,image/jpeg,image/webp,image/gif"></label>
        <label class="penuh">Teks alternatif (dibaca pembaca layar)<input type="text" id="oAlt" value="${esc(s.alt)}" placeholder="mis. Logo perusahaan"></label>
        <label>Rata<select id="oRata">${opsi(RATA, s.rata)}</select></label>
        <label>Ukuran gambar<select id="oPas">${opsi({contain: "Utuh (tidak terpotong)", cover: "Penuhi kotak (bisa terpotong)"}, s.pas)}</select></label>
        <label class="penuh">Tinggi kotak<select id="oTinggi">${opsi(TINGGI, s.tinggi)}</select></label>
        <div class="penuh contohObjek" id="oContoh"></div></div>`;
    Studio.dialog({judul: o.jenis === "teks" ? "Atur teks" : "Atur gambar", isi, padaOk: () => {
      baca();
      if (o.jenis === "teks" && !s.teks.trim()) { Studio.notif("Teks masih kosong.", true); return false; }
      if (o.jenis === "gambar" && !s.gambar) { Studio.notif("Pilih berkas gambar dulu.", true); return false; }
      Object.assign(o, s); renderKanvas();
    }});
    const nilai = id => $("#" + id)?.value;
    function baca() {
      Object.assign(s, {rata: nilai("oRata"), tinggi: Number(nilai("oTinggi"))});
      if (o.jenis === "teks") Object.assign(s, {teks: nilai("oTeks"), huruf: nilai("oHuruf"),
        ukuran: Math.min(Math.max(Number(nilai("oUkuran")) || 16, 10), 96), tebal: $("#oTebal").checked, miring: $("#oMiring").checked,
        warna: nilai("oWarna"), latar: $("#oTanpaLatar").checked ? "" : nilai("oLatar"), tegak: nilai("oTegak")});
      else Object.assign(s, {alt: nilai("oAlt"), pas: nilai("oPas")});
      const c = $("#oContoh");
      c.style.height = `${Math.min(s.tinggi * 8, 220)}px`; c.innerHTML = htmlObjek(s);
    }
    const wadah = $("#dialog .isi");                      // dibuat ulang tiap dialog: handler tidak bocor ke dialog lain
    wadah.oninput = wadah.onchange = e => { if (e.target.id !== "oBerkas") baca(); };
    wadah.onclick = e => {
      const b = e.target.closest("[data-sasaran]");
      if (!b) return;
      $("#" + b.dataset.sasaran).value = b.dataset.w;
      if (b.dataset.sasaran === "oLatar") $("#oTanpaLatar").checked = false;
      baca();
    };
    const berkas = $("#oBerkas");
    if (berkas) berkas.onchange = () => {
      const f = berkas.files[0];
      if (!f) return;
      if (f.size > 3 * 1024 * 1024) { Studio.notif("Gambar lebih dari 3 MB.", true); berkas.value = ""; return; }
      const r = new FileReader();
      r.onload = async () => {
        try { s.gambar = (await Studio.api("/studio/api/gambar", {data: r.result})).id; if (!$("#oAlt").value) $("#oAlt").value = f.name.replace(/\.[^.]+$/, ""); baca(); }
        catch (err) { Studio.notif(esc(err.message), true); }
      };
      r.readAsDataURL(f);
    };
    baca();
  }

  /* ---------- Simpan & buka ---------- */
  async function simpan() {
    try {
      const j = await Studio.api("/studio/api/dashboard", {id: D.id, judul: $("#judulDasbor").value, keterangan: $("#ketDasbor").value,
                                                         baris: D.baris.map(row => row.map(k => (k.jenis ? k : {chart_id: k.chart_id, lebar: k.lebar}))),
                                                         filter: D.filter.map(f => ({nama: f.nama, dataset_id: f.dataset_id, kolom: f.kolom, jenis: f.jenis}))});
      D.id = j.id;
      $("#tautanDasbor").innerHTML = `<a href="${esc(j.url)}" target="_blank">Buka dashboard</a>`;
      Studio.notif(`Dashboard tersimpan. <a href="${esc(j.url)}" target="_blank">Buka</a>`);
      await Studio.muatAwal(); isiPilihan();
    } catch (e) { Studio.notif(esc(e.message), true); }
  }

  async function buka(id) {
    if (!id) return baru();
    try {
      const d = await Studio.api(`/studio/api/dashboard/${id}`);
      Object.assign(D, {id: d.id, baris: d.baris, filter: d.filter || []});
      cacheHasil.clear(); renderFilter();
      $("#judulDasbor").value = d.judul; $("#ketDasbor").value = d.keterangan || "";
      $("#tautanDasbor").innerHTML = `<a href="/superset/dashboard/${d.id}/" target="_blank">Buka dashboard</a>`;
      renderKanvas();
    } catch (e) { Studio.notif(esc(e.message), true); }
  }
  function baru() {
    Object.assign(D, {id: null, baris: [], filter: []});
    cacheHasil.clear(); renderFilter();
    $("#judulDasbor").value = ""; $("#ketDasbor").value = ""; $("#tautanDasbor").innerHTML = ""; $("#bukaDasbor").value = "";
    renderKanvas();
  }
  function isiPilihan() {
    $("#bukaDasbor").innerHTML = '<option value="">Buka dashboard Studio…</option>' +
      Studio.awal.dashboard.map(d => `<option value="${d.id}" ${d.id === D.id ? "selected" : ""}>${esc(d.judul)}</option>`).join("");
  }

  Studio.saatMulai.push(() => {
    $("#cariLembarD").oninput = renderDaftar;
    $$("#daftarObjek [data-objek]").forEach(el => {
      el.ondragstart = e => e.dataTransfer.setData("text/plain", JSON.stringify({objek: el.dataset.objek}));
      // Klik (tanpa seret) = tambahkan di baris baru paling bawah.
      el.onclick = () => {
        const j = el.dataset.objek;
        if (j === "garis") { D.baris.push([{jenis: "garis"}]); renderKanvas(); return; }
        const o = OBJEK_BARU[j](); D.baris.push([o]); renderKanvas(); aturObjek(o);
      };
    });
    $("#bukaDasbor").onchange = () => buka($("#bukaDasbor").value);
    $("#dasborBaru").onclick = baru;
    $("#simpanDasbor").onclick = simpan;
    $("#simpanDasbor").disabled = !Studio.awal.izin.dashboard;
    if (!Studio.awal.izin.dashboard) $("#simpanDasbor").title = "Anda belum punya izin membuat dashboard";
    isiPilihan(); renderFilter(); renderKanvas();
  });
  window.addEventListener("lembar-berubah", () => { cacheHasil.clear(); renderDaftar(); });
})();
