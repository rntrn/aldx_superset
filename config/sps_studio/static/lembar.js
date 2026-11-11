/* =============================================================================
   Studio Visual — LEMBAR KERJA
     Panel Data -> seret ke rak Kolom / Baris / Filter / Warna / Ukuran
     "Tampilkan saya" memilih jenis grafik; "Otomatis" = rekomendasi
   ============================================================================= */
"use strict";

(() => {
  const AGG = {SUM: "Jumlah", AVG: "Rata-rata", COUNT: "Hitung", COUNT_DISTINCT: "Hitung unik", MIN: "Minimum", MAX: "Maksimum"};
  const RAK_BANYAK = ["kolom", "baris"], RAK_SATU = ["warna", "ukuran"];
  const URUT = {"": "Urutkan", turun: "Urut: terbesar dulu", naik: "Urut: terkecil dulu"};
  const BATAS_PRATINJAU = 2000;

  const L = {ds: null, bidang: null, kolom: [], baris: [], warna: null, ukuran: null, filter: [],
             tanda: "otomatis", label: false, urut: "", chartId: null, hasil: null, nomorKueri: 0,
             analitik: {}};
  const TANDA_ANALITIK = ["garis", "area", "batang"];

  /* ---------- Pil ---------- */
  const labelPil = p => p.peran === "dimensi" || p.metrik ? (p.label || p.field)
    : p.field === "__baris__" ? "Jumlah baris" : `${p.agg}(${p.field})`;
  const salin = p => ({field: p.field, peran: p.peran, agg: p.agg || "SUM", metrik: !!p.metrik,
                       label: p.label, waktu: !!p.waktu, geo: p.geo || "", dttm: !!p.dttm});
  const keSpec = p => p && {field: p.field, peran: p.peran, agg: p.agg, metrik: p.metrik};

  function dimensi() {
    const d = [...L.kolom, ...L.baris].filter(p => p.peran === "dimensi");
    if (L.warna?.peran === "dimensi") d.push(L.warna);
    return [...new Map(d.map(p => [labelPil(p), p])).values()];
  }
  function ukuran() {
    const u = [...L.kolom, ...L.baris].filter(p => p.peran === "ukuran");
    [L.ukuran, L.warna].forEach(p => { if (p?.peran === "ukuran") u.push(p); });
    return [...new Map(u.map(p => [labelPil(p), p])).values()];
  }

  /* ---------- Tampilkan saya ---------- */
  const punyaGeo = (d, peran) => d.some(p => p.geo === peran);
  const sah = (t, nd, nu) => {
    const a = Studio.awal.aturan[t], d = dimensi();
    if (!(nd >= a.dim[0] && nd <= a.dim[1] && nu >= a.ukuran[0] && nu <= a.ukuran[1] && nd + nu > 0)) return false;
    if (a.geo === "titik" && !(punyaGeo(d, "lintang") && punyaGeo(d, "bujur"))) return false;
    if (a.waktu && !d.some(p => p.waktu)) return false;
    return true;
  };
  function rekomendasi() {
    const d = dimensi(), nd = d.length, nu = ukuran().length;
    if (nd + nu === 0) return null;
    if (nd === 0) return nu === 1 ? "angka" : "tabel";
    const ukKolom = L.kolom.some(p => p.peran === "ukuran"), ukBaris = L.baris.some(p => p.peran === "ukuran");
    const dimKolom = L.kolom.some(p => p.peran === "dimensi"), dimBaris = L.baris.some(p => p.peran === "dimensi");
    // kolom geografis -> peta (lintang/bujur langsung jadi peta)
    if (sah("peta_titik", nd, nu)) return "peta_titik";
    if (nd === 1 && nu === 1 && punyaGeo(d, "wilayah")) return "peta_wilayah";
    if (nd === 1 && nu >= 2 && ukKolom && ukBaris && sah("sebar", nd, nu)) return "sebar";
    // dimensi di Kolom & Baris, ukuran hanya di Warna/Ukuran -> tabel sorot (peta panas)
    if (nd === 2 && nu === 1 && dimKolom && dimBaris && !ukKolom && !ukBaris) return "peta_panas";
    if (nd >= 3 && dimKolom && dimBaris && sah("tabel_pivot", nd, nu)) return "tabel_pivot";
    if (d.some(p => p.waktu) && nu >= 1 && sah("garis", nd, nu)) return "garis";
    if (sah("batang", nd, nu)) return "batang";
    if (sah("tabel_pivot", nd, nu)) return "tabel_pivot";
    return "tabel";
  }
  const tandaEfektif = () => L.tanda === "otomatis" ? rekomendasi() : L.tanda;
  const kebutuhan = t => {
    const a = Studio.awal.aturan[t];
    const r = (x, n) => x[0] === x[1] ? `${x[0]} ${n}` : `${x[0]}–${x[1]} ${n}`;
    const tambahan = a.geo === "titik" ? " (termasuk lintang & bujur)" : a.waktu ? " (termasuk tanggal)" : "";
    return `${a.label}: ${r(a.dim, "dimensi")}${tambahan}, ${r(a.ukuran, "ukuran")}`;
  };

  function renderShowMe() {
    const nd = dimensi().length, nu = ukuran().length, rek = rekomendasi(), efektif = tandaEfektif();
    const grup = {};
    Object.entries(Studio.awal.aturan).forEach(([t, a]) => (grup[a.grup] ??= []).push(t));
    $("#showme").innerHTML = Object.entries(grup).map(([g, daftar]) => `<div class="grupJenis">${esc(g)}</div>` +
      daftar.map(t => `<button class="jenis ${t === rek ? "saran" : ""} ${t === efektif ? "aktif" : ""}" data-t="${t}"
        ${sah(t, nd, nu) ? "" : "disabled"} title="${esc(kebutuhan(t))}">
        <svg viewBox="0 0 40 26" style="color:var(--navy2)">${Studio.ikonTanda[t]}</svg>${esc(Studio.awal.aturan[t].label)}</button>`).join("")).join("");
    $$("#showme .jenis").forEach(b => {
      b.onclick = () => { L.tanda = b.dataset.t; $("#pilihTanda").value = L.tanda; perbarui(); };
      b.onmouseenter = () => { $("#butuh").textContent = kebutuhan(b.dataset.t); };
      b.onmouseleave = tulisButuh;
    });
    tulisButuh();
  }
  function tulisButuh() {
    const rek = rekomendasi();
    $("#butuh").innerHTML = rek ? `Bingkai emas = rekomendasi (<b>${esc(Studio.awal.aturan[rek].label)}</b>). Arahkan ke jenis lain untuk melihat kebutuhannya.`
      : "Seret kolom ke rak untuk melihat jenis grafik yang cocok.";
  }

  /* ---------- Panel Data ---------- */
  async function gantiDataset(id, spec = null) {
    L.ds = Number(id);
    L.bidang = await Studio.api(`/studio/api/bidang/${L.ds}`);
    $("#pilihDataset").value = L.ds;
    if (spec) terapkanSpec(spec); else bersihkan(false);
    renderBidang(); muatSaran();
  }

  function renderBidang() {
    const cari = $("#cariBidang").value.trim().toLowerCase();
    const tag = b => b.jenis === "geo" ? "Geo" : b.jenis === "tanggal" ? "Tgl" : b.jenis === "metrik" ? "f(x)" : b.jenis === "angka" ? "#" : "Abc";
    const isi = daftar => daftar.filter(b => !cari || (b.label || b.field).toLowerCase().includes(cari)).map(b =>
      `<div class="bidang ${b.peran}" draggable="true" data-f="${esc(b.field)}" data-p="${b.peran}" title="${esc(b.keterangan || b.field)}">
        <span class="tag">${tag(b)}</span>${esc(b.label || b.field)}</div>`).join("") || '<div class="ket">–</div>';
    $("#daftarDimensi").innerHTML = isi(L.bidang.dimensi);
    $("#daftarUkuran").innerHTML = isi(L.bidang.ukuran);
    $$("#panelData .bidang").forEach(el => {
      const b = cariBidang(el.dataset.f, el.dataset.p);
      el.ondragstart = e => e.dataTransfer.setData("text/plain", JSON.stringify({sumber: "panel", pil: salin(b)}));
      el.ondblclick = () => { (b.peran === "dimensi" ? L.kolom : L.baris).push(salin(b)); perbarui(); };
    });
  }
  const cariBidang = (f, peran) => L.bidang[peran].find(b => b.field === f);

  /* ---------- Rak ---------- */
  function renderRak() {
    $$(".rak").forEach(z => {
      const rak = z.dataset.rak;
      const isi = rak === "filter" ? L.filter.map(f => f.pil) : RAK_SATU.includes(rak) ? [L[rak]].filter(Boolean) : L[rak];
      z.innerHTML = "";
      isi.forEach((p, i) => z.appendChild(elPil(p, rak, i)));
      z.classList.toggle("kosong", !isi.length);
    });
  }

  function elPil(p, rak, i) {
    const el = document.createElement("div");
    el.className = `pil ${p.peran}`; el.draggable = true;
    const f = rak === "filter" ? L.filter[i] : null;
    const teks = f ? `${labelPil(p)}${f.nilai ? ` (${f.nilai.length})` : ""}` : labelPil(p);
    el.innerHTML = `<span>${esc(teks)}</span><button class="x" title="Buang">×</button>`;
    el.ondragstart = e => e.dataTransfer.setData("text/plain", JSON.stringify({sumber: rak, idx: i}));
    $(".x", el).onclick = e => { e.stopPropagation(); buang(rak, i); perbarui(); };
    el.onclick = e => menuPil(e, p, rak, i);
    return el;
  }

  function menuPil(e, p, rak, i) {
    const item = [];
    if (rak === "filter") item.push({label: "Ubah filter…", aksi: () => bukaFilter(p, i)});
    else {
      if (p.peran === "ukuran" && !p.metrik && p.field !== "__baris__")
        Object.entries(AGG).forEach(([k, v]) => item.push({label: `${v} (${k})`, pilih: p.agg === k, aksi: () => { p.agg = k; perbarui(); }}));
      if (item.length) item.push("-");
      item.push({label: "Saring dengan kolom ini…", aksi: () => bukaFilter(salin(p))});
    }
    item.push({label: "Buang", aksi: () => { buang(rak, i); perbarui(); }});
    Studio.menu(e.clientX, e.clientY, item);
  }

  function ambil(sumber, idx) {
    if (sumber === "filter") return L.filter[idx].pil;
    return RAK_SATU.includes(sumber) ? L[sumber] : L[sumber][idx];
  }
  function buang(rak, i) {
    if (rak === "filter") L.filter.splice(i, 1);
    else if (RAK_SATU.includes(rak)) L[rak] = null;
    else L[rak].splice(i, 1);
  }

  function terima(rak, d) {
    const pindah = d.sumber !== "panel";
    const pil = pindah ? ambil(d.sumber, d.idx) : d.pil;
    if (!pil) return;
    if (rak === "filter") { bukaFilter(salin(pil)); return; }     // filter = salinan, rak asal tetap
    if (pindah) buang(d.sumber, d.idx);
    if (RAK_SATU.includes(rak)) L[rak] = pil;
    else if (!L[rak].some(p => labelPil(p) === labelPil(pil))) L[rak].push(pil);
    perbarui();
  }

  function pasangSeret() {
    $$(".rak").forEach(z => {
      z.ondragover = e => { e.preventDefault(); z.classList.add("over"); };
      z.ondragleave = () => z.classList.remove("over");
      z.ondrop = e => { e.preventDefault(); z.classList.remove("over"); terima(z.dataset.rak, JSON.parse(e.dataTransfer.getData("text/plain"))); };
    });
    const pd = $("#panelData");                 // seret pil kembali ke panel Data = buang
    pd.ondragover = e => { e.preventDefault(); pd.classList.add("over"); };
    pd.ondragleave = () => pd.classList.remove("over");
    pd.ondrop = e => {
      e.preventDefault(); pd.classList.remove("over");
      const d = JSON.parse(e.dataTransfer.getData("text/plain"));
      if (d.sumber !== "panel") { buang(d.sumber, d.idx); perbarui(); }
    };
  }

  /* ---------- Filter ---------- */
  async function bukaFilter(pil, idx = null) {
    const lama = idx !== null ? L.filter[idx] : null;
    if (pil.peran === "dimensi") {
      let nilai;
      try { nilai = await Studio.api(`/studio/api/nilai/${L.ds}?kolom=${encodeURIComponent(pil.field)}`); }
      catch (e) { Studio.notif(esc(e.message), true); return; }
      const dipilih = new Set((lama?.nilai || nilai).map(String));
      Studio.dialog({judul: `Filter: ${labelPil(pil)}`, isi: `
        <input type="text" id="fCari" placeholder="Cari nilai">
        <div style="margin:8px 0"><button class="kecil" id="fSemua">Semua</button> <button class="kecil" id="fKosong">Tidak ada</button></div>
        <div class="nilaiList" id="fNilai">${nilai.map(v => `<label><input type="checkbox" value="${esc(v)}" ${dipilih.has(String(v)) ? "checked" : ""}> ${esc(v ?? "(kosong)")}</label>`).join("")}</div>`,
        padaOk: () => {
          const pilih = $$("#fNilai input:checked").map(c => nilai.find(v => String(v) === c.value));
          if (!pilih.length) { Studio.notif("Pilih minimal satu nilai.", true); return false; }
          simpanFilter(idx, {pil, nilai: pilih});
        }});
      $("#fCari").oninput = () => $$("#fNilai label").forEach(l => { l.style.display = l.textContent.toLowerCase().includes($("#fCari").value.toLowerCase()) ? "" : "none"; });
      $("#fSemua").onclick = () => $$("#fNilai input").forEach(c => { c.checked = true; });
      $("#fKosong").onclick = () => $$("#fNilai input").forEach(c => { c.checked = false; });
    } else {
      Studio.dialog({judul: `Filter: ${pil.field}`, isi: `
        <p class="ket">Menyaring baris data sebelum dijumlahkan. Kosongkan untuk tanpa batas.</p>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
          <label>Minimal<input type="number" id="fMin" value="${lama?.min ?? ""}"></label>
          <label>Maksimal<input type="number" id="fMaks" value="${lama?.max ?? ""}"></label></div>`,
        padaOk: () => {
          const min = $("#fMin").value === "" ? null : Number($("#fMin").value);
          const max = $("#fMaks").value === "" ? null : Number($("#fMaks").value);
          if (min === null && max === null) { Studio.notif("Isi minimal atau maksimal.", true); return false; }
          simpanFilter(idx, {pil, min, max});
        }});
    }
  }
  function simpanFilter(idx, f) {
    if (idx === null) L.filter.push(f); else L.filter[idx] = f;
    perbarui();
  }
  const filterSpec = () => L.filter.flatMap(f => f.nilai ? [{field: f.pil.field, op: "IN", nilai: f.nilai}]
    : [f.min !== null && {field: f.pil.field, op: ">=", nilai: f.min}, f.max !== null && {field: f.pil.field, op: "<=", nilai: f.max}].filter(Boolean));

  /* ---------- Spesifikasi & query ---------- */
  const spec = () => ({dataset_id: L.ds, judul: $("#judulLembar").value.trim(), tanda: tandaEfektif(),
    kolom: L.kolom.map(keSpec), baris: L.baris.map(keSpec), warna: keSpec(L.warna), ukuran: keSpec(L.ukuran),
    label: L.label, filter: filterSpec(), urut: L.urut, batas: BATAS_PRATINJAU, analitik: L.analitik});
  const horizontal = () => L.baris.some(p => p.peran === "dimensi") && !L.kolom.some(p => p.peran === "dimensi");

  const kueri = Studio.tunda(async () => {
    const nd = dimensi().length, nu = ukuran().length, t = tandaEfektif();
    const pesan = $("#pesanKanvas");
    if (!L.ds || nd + nu === 0) { tampilPesan("Seret <b>&nbsp;Dimensi&nbsp;</b> ke rak Kolom dan <b>&nbsp;Ukuran&nbsp;</b> ke rak Baris."); return; }
    if (!sah(t, nd, nu)) { tampilPesan(`${esc(kebutuhan(t))}.<br>Sekarang: ${nd} dimensi, ${nu} ukuran. Pilih jenis lain di "Tampilkan saya".`); return; }
    const mulai = performance.now(), nomor = ++L.nomorKueri;
    try {
      const hasil = await Studio.api("/studio/api/kueri", spec());
      if (nomor !== L.nomorKueri) return;                      // ada permintaan lebih baru
      L.hasil = hasil;
      const dataEkspor = {kolom: hasil.kolom, baris: hasil.baris.map(b => hasil.kolom.map(k => b[k]))};
      if (window.SPS && SPS.ekspor) ["#tabelData"].concat(".lukis").forEach(s => SPS.ekspor.data($(s), dataEkspor));
      pesan.style.display = "none";
      const info = Studio.gambar($("#grafik"), L.hasil, t, {horizontal: horizontal(), label: L.label}) || {};
      $("#statusLembar").innerHTML = `<span>${fmtPenuh.format(L.hasil.baris.length)} baris</span><span>${esc(Studio.awal.aturan[t].label)}</span>
        <span>${Math.round(performance.now() - mulai)} ms</span>${L.hasil.baris.length >= BATAS_PRATINJAU ? "<span>Dibatasi " + BATAS_PRATINJAU + " baris</span>" : ""}
        ${info.catatan ? `<span class="peringatan">${esc(info.catatan)}</span>` : ""}`;
      renderAnalitik();
      if ($("#tabelData").classList.contains("tampil")) $("#tabelData").innerHTML = Studio.tabelHtml(L.hasil.kolom, L.hasil.baris);
    } catch (e) { if (nomor === L.nomorKueri) tampilPesan(`<span style="color:var(--merah)">${esc(e.message)}</span>`); }
  }, 300);

  function tampilPesan(html) {
    Studio.hapusGrafik($("#grafik"));
    $("#grafik").innerHTML = "";
    $("#pesanKanvas").innerHTML = html; $("#pesanKanvas").style.display = "flex";
    $("#statusLembar").innerHTML = "";
  }

  /* ---------- Panel Analitik (ramalan, tren, anomali) ---------- */
  const bacaAnalitik = () => {
    const a = {ramalan: $("#anRamalan").checked ? Math.max(1, Math.min(36, +$("#anPeriode").value || 6)) : 0,
               tren: $("#anTren").checked, anomali: $("#anAnomali").checked};
    L.analitik = a.ramalan || a.tren || a.anomali ? a : {};
  };
  function renderAnalitik() {
    const bisa = TANDA_ANALITIK.includes(tandaEfektif()) && dimensi().length === 1 && L.warna?.peran !== "dimensi";
    $("#panelAnalitik").classList.toggle("mati", !bisa);
    $$("#panelAnalitik input").forEach(i => { i.disabled = !bisa; });
    const a = L.analitik;
    $("#anRamalan").checked = !!a.ramalan; if (a.ramalan) $("#anPeriode").value = a.ramalan;
    $("#anTren").checked = !!a.tren; $("#anAnomali").checked = !!a.anomali;
    const r = Object.values(L.hasil?.analitik?.seri || {}).find(x => x.ramalan)?.ramalan;
    $("#anKet").innerHTML = !bisa ? "Untuk Garis, Area, atau Batang dengan satu dimensi berurutan (mis. bulan)."
      : r ? `Metode: ${esc(r.metode)}. Pita = keyakinan 80% &amp; 95%.` + (L.hasil.analitik.catatan.length ? `<br>${esc(L.hasil.analitik.catatan.join(" "))}` : "")
      : (L.hasil?.analitik?.catatan || []).map(esc).join("<br>") || "Ramalan memakai pola tren &amp; musiman data.";
  }

  function perbarui() {
    renderRak(); renderShowMe(); renderAnalitik();
    $("#urut").textContent = URUT[L.urut];
    kueri();
  }

  /* ---------- Simpan / buka ---------- */
  async function simpan(baru) {
    if (!L.ds) return;
    try {
      const j = await Studio.api("/studio/api/lembar", {spec: spec(), chart_id: baru ? null : L.chartId});
      if (j.disimpan) {
        L.chartId = j.id;
        Studio.notif(`Tersimpan sebagai chart Superset. ${j.catatan ? esc(j.catatan) + " " : ""}<a href="${esc(j.url)}" target="_blank">Buka di Explore</a>`);
        await Studio.muatAwal(); renderDaftar(); window.dispatchEvent(new Event("lembar-berubah"));
      } else Studio.notif(`${esc(j.catatan)} <a href="${esc(j.url)}" target="_blank">Buka</a>`);
    } catch (e) { Studio.notif(esc(e.message), true); }
  }

  function terapkanSpec(s) {
    const pil = d => {
      if (!d) return null;
      const b = cariBidang(d.field, d.peran) || {};
      return {...salin({...b, ...d}), agg: d.agg || b.agg || "SUM"};
    };
    L.kolom = (s.kolom || []).map(pil); L.baris = (s.baris || []).map(pil);
    L.warna = pil(s.warna); L.ukuran = pil(s.ukuran); L.label = !!s.label; L.urut = s.urut || "";
    L.filter = [];
    const kelompok = {};
    (s.filter || []).forEach(f => {
      const b = cariBidang(f.field, "dimensi") || cariBidang(f.field, "ukuran");
      if (f.op === "IN") L.filter.push({pil: salin(b || {field: f.field, peran: "dimensi"}), nilai: f.nilai});
      else { const k = (kelompok[f.field] ??= {pil: salin(b || {field: f.field, peran: "ukuran"}), min: null, max: null});
             if (f.op === ">=") k.min = f.nilai; else k.max = f.nilai; }
    });
    L.filter.push(...Object.values(kelompok));
    L.tanda = s.tanda || "otomatis"; L.chartId = s.chart_id || null; L.analitik = s.analitik || {};
    $("#judulLembar").value = s.judul || ""; $("#pakaiLabel").checked = L.label; $("#pilihTanda").value = L.tanda;
    perbarui();
  }

  function renderDaftar() {
    const daftar = Studio.awal.lembar;
    $("#daftarLembar").innerHTML = daftar.map(l => `<div data-id="${l.id}"><b>${esc(l.judul)}</b><span class="ket">${esc(Studio.awal.aturan[l.tanda]?.label || "")} · ${esc(l.diubah)}</span></div>`).join("")
      || '<div class="ket">Belum ada. Simpan lembar kerja pertama Anda.</div>';
    $$("#daftarLembar [data-id]").forEach(el => el.onclick = async () => {
      try { const s = await Studio.api(`/studio/api/lembar/${el.dataset.id}`); await gantiDataset(s.dataset_id, s); }
      catch (e) { Studio.notif(esc(e.message), true); }
    });
  }

  /* ---------- Saran dari data (auto chart ML ringan) ---------- */
  async function muatSaran() {
    const ds = L.ds;
    $("#saranData").innerHTML = '<div class="ket">Mempelajari data…</div>';
    try {
      const h = await Studio.api(`/studio/api/saran/${ds}`);
      if (ds !== L.ds) return;                                 // dataset sudah diganti: abaikan jawaban lama
      const label = h.label_jenis || {};
      $("#saranData").innerHTML = h.saran.map((s, i) => `<div data-i="${i}"><b>${esc(s.judul)}</b>
        <span class="ket"><span class="lencanaJenis">${esc(label[s.jenis] || s.jenis)}</span> ${esc(s.alasan)}</span></div>`).join("")
        || '<div class="ket">Tidak ada saran.</div>';
      $$("#saranData [data-i]").forEach(el => el.onclick = () => terapkanSaran(h.saran[el.dataset.i]));
    } catch (e) { if (ds === L.ds) $("#saranData").innerHTML = `<div class="ket">${esc(e.message)}</div>`; }
  }
  function terapkanSaran(s) {
    if (s.spec && s.jenis in Studio.awal.aturan) {
      return terapkanSpec({kolom: s.spec.kolom || [], baris: s.spec.baris || [], warna: s.spec.warna || null,
                           ukuran: s.spec.ukuran || null, tanda: s.jenis, judul: s.judul});
    }
    const uk = s.metrik.map(m => {
      const c = /^(\w+)\((.+)\)$/.exec(m);
      return c ? {field: c[2], peran: "ukuran", agg: c[1].toUpperCase()} : {field: m, peran: "ukuran", metrik: true};
    });
    const [d1, d2] = s.kelompok.map(k => ({field: k, peran: "dimensi"}));
    terapkanSpec({kolom: d1 ? [d1] : [], baris: uk, warna: d2 || null, tanda: s.jenis in Studio.awal.aturan ? s.jenis : "otomatis", judul: s.judul});
  }

  /* ---------- Tombol ---------- */
  function bersihkan(render = true) {
    Object.assign(L, {kolom: [], baris: [], warna: null, ukuran: null, filter: [], tanda: "otomatis", label: false, urut: "",
                      chartId: null, analitik: {}});
    $("#judulLembar").value = ""; $("#pakaiLabel").checked = false; $("#pilihTanda").value = "otomatis";
    if (render) perbarui(); else { renderRak(); renderShowMe(); renderAnalitik(); tampilPesan("Seret <b>&nbsp;Dimensi&nbsp;</b> ke rak Kolom dan <b>&nbsp;Ukuran&nbsp;</b> ke rak Baris."); }
  }

  Studio.saatMulai.push(() => {
    const ds = Studio.awal.dataset;
    $("#pilihDataset").innerHTML = ds.map(d => `<option value="${d.id}">${esc(d.nama)}</option>`).join("");
    $("#pilihTanda").innerHTML = '<option value="otomatis">Otomatis</option>' +
      Object.entries(Studio.awal.aturan).map(([k, a]) => `<option value="${k}">${esc(a.label)}</option>`).join("");
    $("#pilihDataset").onchange = () => gantiDataset($("#pilihDataset").value);
    $("#cariBidang").oninput = renderBidang;
    $("#pilihTanda").onchange = () => { L.tanda = $("#pilihTanda").value; perbarui(); };
    $("#pakaiLabel").onchange = () => { L.label = $("#pakaiLabel").checked; perbarui(); };
    ["anRamalan", "anTren", "anAnomali", "anPeriode"].forEach(id => { $("#" + id).onchange = () => { bacaAnalitik(); perbarui(); }; });
    $("#tukar").onclick = () => { [L.kolom, L.baris] = [L.baris, L.kolom]; perbarui(); };
    $("#urut").onclick = () => { L.urut = {"": "turun", turun: "naik", naik: ""}[L.urut]; perbarui(); };
    $("#lihatData").onclick = () => {
      const t = $("#tabelData"); t.classList.toggle("tampil");
      $("#lihatData").textContent = t.classList.contains("tampil") ? "Sembunyikan data" : "Lihat data";
      if (L.hasil) t.innerHTML = Studio.tabelHtml(L.hasil.kolom, L.hasil.baris);
      window.dispatchEvent(new Event("resize"));
    };
    $("#bersihkan").onclick = () => bersihkan();
    $("#simpanLembar").onclick = () => simpan(false);
    $("#simpanBaru").onclick = () => simpan(true);
    pasangSeret(); renderDaftar();
    // ?dataset=ID (mis. dari Kueri Visual) memilih dataset itu; selain itu dataset pertama.
    const minta = Number(new URLSearchParams(location.search).get("dataset"));
    const awalDs = ds.find(d => d.id === minta) || ds[0];
    if (awalDs) gantiDataset(awalDs.id); else tampilPesan("Belum ada dataset yang boleh Anda akses.");
  });
  Studio.lembar = {gantiDataset};
})();
