/* =============================================================================
   Studio Visual — PENYUSUN DASHBOARD
     Seret lembar kerja ke kanvas; tiap baris maksimal 12 kolom (¼ ⅓ ½ ⅔ penuh).
   ============================================================================= */
"use strict";

(() => {
  const LEBAR = {3: "¼", 4: "⅓", 6: "½", 8: "⅔", 12: "Penuh"};
  const D = {id: null, baris: [], filter: []};  // baris: [[{chart_id, lebar, judul}]]
  // filter: [{nama, dataset_id, kolom, jenis: "pilihan"|"rentang", nilai, min, max}] (nilai/min/max = pratinjau)
  const cacheHasil = new Map();                  // chart_id -> hasil query (dengan filter aktif)
  const cacheBidang = new Map();                 // dataset_id -> daftar nama kolom (huruf kecil)

  const lembarById = id => Studio.awal.lembar.find(l => l.id === Number(id));
  const totalLebar = row => row.reduce((s, k) => s + k.lebar, 0);

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
    el.className = "drow" + (totalLebar(row) > 12 ? " penuh" : "");
    row.forEach((kotak, i) => el.appendChild(elKotak(kotak, r, i)));
    zonaJatuh(el, r);
    return el;
  }

  function elKotak(kotak, r, i) {
    const el = document.createElement("div");
    el.className = "dtile"; el.draggable = true;
    el.style.flex = `0 0 calc(${kotak.lebar / 12 * 100}% - ${10 * (1 - kotak.lebar / 12)}px)`;
    el.innerHTML = `<div class="kepala"><span title="${esc(kotak.judul)}">${esc(kotak.judul)}</span>
      <select title="Lebar">${Object.entries(LEBAR).map(([v, t]) => `<option value="${v}" ${Number(v) === kotak.lebar ? "selected" : ""}>${t}</option>`).join("")}</select>
      <button class="kecil">Hapus</button></div><div class="mini"></div>`;
    el.ondragstart = e => { e.stopPropagation(); e.dataTransfer.setData("text/plain", JSON.stringify({r, i})); };
    $("select", el).onchange = e => { kotak.lebar = Number(e.target.value); renderKanvas(); };
    $("button", el).onclick = () => { D.baris[r].splice(i, 1); D.baris = D.baris.filter(b => b.length); renderKanvas(); };
    requestAnimationFrame(() => gambarMini($(".mini", el), kotak.chart_id));
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
      let kotak;
      if (d.baru) {
        if (D.baris.flat().some(k => k.chart_id === d.baru)) { Studio.notif("Lembar kerja ini sudah ada di dashboard.", true); return; }
        const l = lembarById(d.baru);
        kotak = {chart_id: d.baru, judul: l.judul, lebar: l.tanda === "angka" ? 3 : 6};
      } else {
        kotak = D.baris[d.r].splice(d.i, 1)[0];
        if (d.r < r && !D.baris[d.r].length) r -= 1;          // baris asal kosong ikut hilang
        D.baris = D.baris.filter(b => b.length);
      }
      const tujuan = D.baris[r];
      if (!tujuan) { D.baris.push([kotak]); renderKanvas(); return; }
      const sisa = 12 - totalLebar(tujuan);
      if (sisa < 3) { Studio.notif("Baris ini sudah penuh. Kecilkan lebar kotak lain atau seret ke baris baru.", true); D.baris.push([kotak]); }
      else { kotak.lebar = Math.min(kotak.lebar, Math.max(...Object.keys(LEBAR).map(Number).filter(v => v <= sisa))); tujuan.push(kotak); }
      renderKanvas();
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
      <label style="display:block;margin-top:8px">Jenis<select id="fdJenis"><option value="pilihan">Pilihan nilai (dropdown)</option><option value="rentang">Rentang angka</option></select></label>
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
      $("#fdKolom").innerHTML = k.filter(x => jenis === "rentang" ? x.peran === "ukuran" : x.peran === "dimensi")
        .map(x => `<option>${esc(x.field)}</option>`).join("");
    };
    $("#fdDs").onchange = isiKolom; $("#fdJenis").onchange = isiKolom;
    isiKolom();
  }

  async function aturFilter(f) {
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

  /* ---------- Simpan & buka ---------- */
  async function simpan() {
    try {
      const j = await Studio.api("/studio/api/dashboard", {id: D.id, judul: $("#judulDasbor").value, keterangan: $("#ketDasbor").value,
                                                         baris: D.baris.map(row => row.map(k => ({chart_id: k.chart_id, lebar: k.lebar}))),
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
    $("#bukaDasbor").onchange = () => buka($("#bukaDasbor").value);
    $("#dasborBaru").onclick = baru;
    $("#simpanDasbor").onclick = simpan;
    $("#simpanDasbor").disabled = !Studio.awal.izin.dashboard;
    if (!Studio.awal.izin.dashboard) $("#simpanDasbor").title = "Anda belum punya izin membuat dashboard";
    isiPilihan(); renderFilter(); renderKanvas();
  });
  window.addEventListener("lembar-berubah", () => { cacheHasil.clear(); renderDaftar(); });
})();
