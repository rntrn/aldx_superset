/* =============================================================================
   Studio Visual — PERSIAPAN DATA
     Data asal -> langkah-langkah -> pratinjau (sesuai hak akses) -> simpan dataset baru
   ============================================================================= */
"use strict";

(() => {
  const JENIS = {pilih: "Pilih kolom", ganti_nama: "Ganti nama", ubah_tipe: "Ubah tipe", bersihkan: "Bersihkan",
                 filter: "Filter baris", hitung: "Kolom hitung", agregasi: "Agregasi", gabung: "Gabung data"};
  const TIPE_GABUNG = {left: "Semua baris kiri (left join)", inner: "Hanya yang cocok di kedua sisi (inner join)"};
  const namaDataset = id => Studio.awal.dataset.find(d => d.id === Number(id))?.nama || `dataset ${id}`;
  const OP = ["==", "!=", ">", "<", ">=", "<=", "IN", "NOT IN", "LIKE", "KOSONG", "TIDAK KOSONG"];
  const AKSI = {trim: "Hapus spasi tepi", besar: "HURUF BESAR", kecil: "huruf kecil", isi_kosong: "Isi nilai kosong"};
  const AGG = ["SUM", "AVG", "MIN", "MAX", "COUNT"];
  const P = {ds: null, langkah: [], aktif: null, hasil: null, kolomAsal: []};

  const ringkas = l => ({
    pilih: () => `${l.kolom.length} kolom`, ganti_nama: () => `${l.dari} → ${l.ke}`,
    ubah_tipe: () => `${l.kolom}: ${l.tipe}`, bersihkan: () => `${l.kolom}: ${AKSI[l.aksi] || l.aksi}`,
    filter: () => `${l.kolom} ${l.op} ${Array.isArray(l.nilai) ? l.nilai.join(", ") : (l.nilai ?? "")}`,
    hitung: () => `${l.nama} = ${l.rumus}`, agregasi: () => `per ${l.kelompok.join(", ") || "semua"}`,
    gabung: () => l.dataset_id ? `dengan ${namaDataset(l.dataset_id)} (${l.tipe})` : "pilih dataset",
  }[l.jenis] || (() => ""))();

  /* ---------- Alur ---------- */
  function renderAlur(galatDi = null) {
    const nama = Studio.awal.dataset.find(d => d.id === P.ds)?.nama || "–";
    let h = `<div class="simpul asal">Asal<span class="ket">${esc(nama)}</span></div>`;
    P.langkah.forEach((l, i) => {
      h += `<div class="sambung"></div><div class="simpul ${P.aktif === i ? "aktif" : ""} ${galatDi === i ? "galat" : ""}" data-i="${i}">
        ${i + 1}. ${esc(JENIS[l.jenis])}<span class="ket">${esc(ringkas(l))}</span></div>`;
    });
    h += `<div class="sambung"></div><button class="kedua" id="tambahLangkah">Tambah langkah</button>`;
    $("#alur").innerHTML = h;
    $$("#alur [data-i]").forEach(el => el.onclick = () => bukaEditor(Number(el.dataset.i)));
    $("#tambahLangkah").onclick = e => Studio.menu(e.clientX, e.clientY,
      Object.entries(JENIS).map(([k, v]) => ({label: v, aksi: () => tambah({jenis: k})})));
  }

  function tambah(l) {
    const isi = {pilih: {kolom: []}, ganti_nama: {dari: "", ke: ""}, ubah_tipe: {kolom: "", tipe: "teks"},
                 bersihkan: {kolom: "", aksi: "trim"}, filter: {kolom: "", op: "==", nilai: ""},
                 hitung: {nama: "", rumus: ""}, agregasi: {kelompok: [], ukuran: []},
                 gabung: {dataset_id: null, tipe: "left", kunci: [], kolom: []}}[l.jenis];
    P.langkah.push({...isi, ...l});
    bukaEditor(P.langkah.length - 1);
  }

  /* ---------- Editor langkah ---------- */
  async function kolomSebelum(i) {
    if (i === 0) return P.kolomAsal;
    const h = await Studio.api("/studio/api/prep/pratinjau", {dataset_id: P.ds, langkah: P.langkah.slice(0, i)});
    return h.kolom;
  }
  const opsi = (daftar, pilih) => daftar.map(k => `<option ${k === pilih ? "selected" : ""}>${esc(k)}</option>`).join("");
  const centang = (daftar, pilih, nama) => `<div class="opsiKolom" style="display:flex;flex-wrap:wrap;gap:4px 14px">` +
    daftar.map(k => `<label><input type="checkbox" name="${nama}" value="${esc(k)}" ${pilih.includes(k) ? "checked" : ""}> ${esc(k)}</label>`).join("") + "</div>";

  async function bukaEditor(i) {
    P.aktif = i; renderAlur();
    const l = P.langkah[i], ed = $("#editorLangkah");
    let kolom;
    try { kolom = await kolomSebelum(i); } catch (e) { Studio.notif(esc(e.message), true); return; }
    const baris = (lbl, isi) => `<div class="baris"><label>${lbl}</label><div>${isi}</div></div>`;
    const form = {
      pilih: () => baris("Kolom dipakai", centang(kolom, l.kolom.length ? l.kolom : kolom, "kolom")),
      ganti_nama: () => baris("Kolom", `<select id="eDari">${opsi(kolom, l.dari)}</select>`) + baris("Nama baru", `<input type="text" id="eKe" value="${esc(l.ke)}">`),
      ubah_tipe: () => baris("Kolom", `<select id="eKolom">${opsi(kolom, l.kolom)}</select>`) + baris("Tipe", `<select id="eTipe">${opsi(["teks", "angka", "tanggal"], l.tipe)}</select>`),
      bersihkan: () => baris("Kolom", `<select id="eKolom">${opsi(kolom, l.kolom)}</select>`) +
        baris("Aksi", `<select id="eAksi">${Object.entries(AKSI).map(([k, v]) => `<option value="${k}" ${k === l.aksi ? "selected" : ""}>${v}</option>`).join("")}</select>`) +
        baris("Nilai pengganti", `<input type="text" id="eNilai" value="${esc(l.nilai ?? "")}" placeholder="hanya untuk 'Isi nilai kosong'">`),
      filter: () => baris("Kolom", `<select id="eKolom">${opsi(kolom, l.kolom)}</select>`) + baris("Operator", `<select id="eOp">${opsi(OP, l.op)}</select>`) +
        baris("Nilai", `<input type="text" id="eNilai" value="${esc(Array.isArray(l.nilai) ? l.nilai.join(", ") : (l.nilai ?? ""))}" placeholder="untuk IN: pisahkan dengan koma">`),
      hitung: () => baris("Nama kolom", `<input type="text" id="eNama" value="${esc(l.nama)}" placeholder="mis. rasio_per_wp">`) +
        baris("Rumus", `<textarea id="eRumus" rows="2" placeholder="mis. total / NULLIF(jumlah_wp, 0)">${esc(l.rumus)}</textarea>
          <div class="ket" style="margin-top:4px">Klik kolom untuk menyisipkan: ${kolom.map(k => `<button class="kecil" data-sisip="${esc(k)}">${esc(k)}</button>`).join(" ")}<br>
          Fungsi umum: ROUND, ABS, COALESCE, NULLIF, UPPER, LOWER, TRIM, SUBSTR, CASE WHEN … THEN … ELSE … END</div>`),
      gabung: () => {
        const asal = Studio.awal.dataset.find(d => d.id === P.ds);
        const pilihan = Studio.awal.dataset.filter(d => d.database_id === asal?.database_id);
        return baris("Gabung dengan", `<select id="eKanan"><option value="">Pilih dataset…</option>${pilihan.map(d =>
            `<option value="${d.id}" ${d.id === Number(l.dataset_id) ? "selected" : ""}>${esc(d.nama)}</option>`).join("")}</select>`) +
          baris("Cara gabung", `<select id="eTipe">${Object.entries(TIPE_GABUNG).map(([k, v]) => `<option value="${k}" ${k === l.tipe ? "selected" : ""}>${v}</option>`).join("")}</select>`) +
          `<div id="eKananIsi"></div><p class="ket">Hak akses kedua dataset tetap berlaku pada hasilnya. Hanya dataset di database yang sama yang bisa digabung.</p>`;
      },
      agregasi: () => baris("Kelompokkan per", centang(kolom, l.kelompok, "kelompok")) +
        baris("Ukuran", `<div id="eUkuran">${(l.ukuran.length ? l.ukuran : [{kolom: kolom[0], agg: "SUM"}]).map(u => barisUkuran(kolom, u)).join("")}</div>
          <button class="kecil" id="eTambahUk">Tambah ukuran</button>`),
    }[l.jenis];
    ed.innerHTML = `<b>${i + 1}. ${esc(JENIS[l.jenis])}</b><div style="margin-top:10px">${form()}</div>
      <div class="alat"><button class="utama" id="eTerapkan">Terapkan</button><button class="teks" id="eHapus">Hapus langkah</button>
      <button class="teks" id="eTutup">Tutup</button><span class="ket" id="eGalat" style="color:var(--merah)"></span></div>`;
    ed.classList.add("tampil");
    $$("[data-sisip]", ed).forEach(b => b.onclick = () => { $("#eRumus").value += (/\s$|^$/.test($("#eRumus").value) ? "" : " ") + b.dataset.sisip; });
    $("#eTambahUk")?.addEventListener("click", () => $("#eUkuran").insertAdjacentHTML("beforeend", barisUkuran(kolom, {kolom: kolom[0], agg: "SUM"})));
    if (l.jenis === "gabung") {
      $("#eKanan").onchange = () => isiGabung(l, kolom, Number($("#eKanan").value), true);
      if (l.dataset_id) isiGabung(l, kolom, Number(l.dataset_id), false);
    }
    $("#eTerapkan").onclick = () => { bacaEditor(l); pratinjau(); };
    $("#eHapus").onclick = () => { P.langkah.splice(i, 1); tutupEditor(); pratinjau(); };
    $("#eTutup").onclick = tutupEditor;
  }
  /* Bagian editor gabung yang bergantung pada dataset kanan */
  async function isiGabung(l, kolom, idKanan, baru) {
    const wadah = $("#eKananIsi");
    if (!idKanan) { wadah.innerHTML = ""; return; }
    let b;
    try { b = await Studio.api(`/studio/api/bidang/${idKanan}`); } catch (e) { wadah.innerHTML = `<p class="galat">${esc(e.message)}</p>`; return; }
    const kanan = [...b.dimensi, ...b.ukuran].filter(x => !x.metrik && x.field !== "__baris__").map(x => x.field);
    const sama = kolom.filter(k => kanan.some(x => x.toLowerCase() === k.toLowerCase()));
    const kunci = !baru && l.kunci.length ? l.kunci : (sama.length ? [{kiri: sama[0], kanan: kanan.find(x => x.toLowerCase() === sama[0].toLowerCase())}] : [{kiri: kolom[0], kanan: kanan[0]}]);
    const ambil = !baru && l.kolom.length ? l.kolom : kanan.filter(k => !kunci.some(x => x.kanan === k));
    const barisKunci = k => `<div class="eKunci" style="display:flex;gap:6px;align-items:center;margin-bottom:4px">
      <select class="kiri">${opsi(kolom, k.kiri)}</select><span>=</span><select class="kanan">${opsi(kanan, k.kanan)}</select></div>`;
    wadah.innerHTML = `<div class="baris"><label>Kolom kunci</label><div><div id="eKunciDaftar">${kunci.map(barisKunci).join("")}</div>
        <button class="kecil" id="eTambahKunci">Tambah kunci</button></div></div>
      <div class="baris"><label>Kolom diambil</label><div>${centang(kanan, ambil, "kanan")}</div></div>`;
    $("#eTambahKunci").onclick = () => $("#eKunciDaftar").insertAdjacentHTML("beforeend", barisKunci({kiri: kolom[0], kanan: kanan[0]}));
  }

  const barisUkuran = (kolom, u) => `<div class="eUk" style="display:flex;gap:6px;margin-bottom:4px">
    <select class="ukAgg" style="width:100px">${opsi(AGG, u.agg)}</select><select class="ukKolom">${opsi(kolom, u.kolom)}</select></div>`;

  function nilaiKetik(v) {
    const t = String(v ?? "").trim();
    return t !== "" && !isNaN(Number(t)) ? Number(t) : t;
  }
  function bacaEditor(l) {
    const v = id => $(id)?.value;
    const dicentang = nama => $$(`#editorLangkah input[name=${nama}]:checked`).map(c => c.value);
    ({
      pilih: () => { l.kolom = dicentang("kolom"); },
      ganti_nama: () => Object.assign(l, {dari: v("#eDari"), ke: v("#eKe").trim()}),
      ubah_tipe: () => Object.assign(l, {kolom: v("#eKolom"), tipe: v("#eTipe")}),
      bersihkan: () => Object.assign(l, {kolom: v("#eKolom"), aksi: v("#eAksi"), nilai: v("#eNilai")}),
      filter: () => {
        const op = v("#eOp"), raw = v("#eNilai");
        l.kolom = v("#eKolom"); l.op = op;
        l.nilai = op === "IN" || op === "NOT IN" ? raw.split(",").map(nilaiKetik).filter(x => x !== "") : nilaiKetik(raw);
      },
      hitung: () => Object.assign(l, {nama: v("#eNama").trim(), rumus: v("#eRumus").trim()}),
      gabung: () => Object.assign(l, {
        dataset_id: Number(v("#eKanan")) || null, tipe: v("#eTipe"),
        kunci: $$("#eKunciDaftar .eKunci").map(r => ({kiri: $(".kiri", r).value, kanan: $(".kanan", r).value})),
        kolom: dicentang("kanan")}),
      agregasi: () => {
        l.kelompok = dicentang("kelompok");
        l.ukuran = $$("#eUkuran .eUk").map(r => ({kolom: $(".ukKolom", r).value, agg: $(".ukAgg", r).value}));
      },
    })[l.jenis]();
  }
  function tutupEditor() { P.aktif = null; $("#editorLangkah").classList.remove("tampil"); renderAlur(); }

  /* ---------- Pratinjau & profil ---------- */
  const pratinjau = Studio.tunda(async () => {
    $("#prepInfo").textContent = "Memproses…";
    try {
      P.hasil = await Studio.api("/studio/api/prep/pratinjau", {dataset_id: P.ds, langkah: P.langkah});
      if (!P.langkah.length) P.kolomAsal = P.hasil.kolom;
      $("#eGalat") && ($("#eGalat").textContent = "");
      renderAlur(); renderProfil();
      $("#prepTabel").innerHTML = Studio.tabelHtml(P.hasil.kolom, P.hasil.baris, 200);
      if (window.SPS && SPS.ekspor) SPS.ekspor.data($("#prepTabel"), {kolom: P.hasil.kolom, baris: P.hasil.baris.map(b => P.hasil.kolom.map(k => b[k]))});
      $("#sqlbox").textContent = P.hasil.sql;
      $("#prepInfo").textContent = `${P.hasil.kolom.length} kolom · ${fmtPenuh.format(P.hasil.baris.length)} baris contoh (sesuai hak akses Anda)`;
    } catch (e) {
      const m = /Langkah (\d+)/.exec(e.message);
      renderAlur(m ? Number(m[1]) - 1 : null);
      $("#prepInfo").textContent = "";
      if ($("#eGalat")) $("#eGalat").textContent = e.message; else Studio.notif(esc(e.message), true);
    }
  }, 150);

  function renderProfil() {
    const {kolom, baris} = P.hasil;
    $("#profil").innerHTML = kolom.map(k => {
      const nilai = baris.map(b => b[k]);
      const kosong = nilai.filter(v => v === null || v === "").length;
      const isi = nilai.filter(v => v !== null && v !== "");
      const unik = new Set(isi.map(String));
      const semuaAngka = isi.length && isi.every(angka);
      let tubuh;
      if (semuaAngka && unik.size > 12) {
        const min = Math.min(...isi), max = Math.max(...isi), lebarBin = (max - min) / 8 || 1;
        const bin = Array(8).fill(0); isi.forEach(v => { bin[Math.min(7, Math.floor((v - min) / lebarBin))] += 1; });
        const puncak = Math.max(...bin);
        tubuh = `<div class="ket">min ${fmtRingkas.format(min)} · maks ${fmtRingkas.format(max)}</div>` +
          `<div style="display:flex;align-items:flex-end;gap:2px;height:60px;margin-top:6px">${bin.map(n =>
            `<div title="${n} baris" style="flex:1;background:var(--navy2);border-radius:2px 2px 0 0;height:${Math.max(2, n / puncak * 100)}%"></div>`).join("")}</div>`;
      } else {
        const hitung = {}; isi.forEach(v => { hitung[v] = (hitung[v] || 0) + 1; });
        const atas = Object.entries(hitung).sort((a, b) => b[1] - a[1]).slice(0, 8), puncak = atas[0]?.[1] || 1;
        tubuh = atas.map(([v, n]) => `<div class="v" data-k="${esc(k)}" data-v="${esc(v)}" title="Klik untuk menyaring">
          <span class="b" style="width:${Math.max(3, n / puncak * 70)}px"></span><span class="t">${esc(v)}</span><span class="ket">${n}</span></div>`).join("");
      }
      return `<div class="pkartu"><div class="nama"><span title="${esc(k)}">${esc(k)}</span><button class="kecil" data-menu="${esc(k)}">Aksi</button></div>
        <div class="ket">${unik.size} nilai unik${kosong ? ` · ${kosong} kosong` : ""}</div><div style="margin-top:6px">${tubuh}</div></div>`;
    }).join("");
    $$("#profil [data-menu]").forEach(b => b.onclick = e => menuKolom(e, b.dataset.menu));
    $$("#profil .v").forEach(el => el.onclick = e => {
      const k = el.dataset.k, v = nilaiKetik(el.dataset.v);
      Studio.menu(e.clientX, e.clientY, [
        {label: "Hanya nilai ini", aksi: () => { P.langkah.push({jenis: "filter", kolom: k, op: "==", nilai: v}); pratinjau(); }},
        {label: "Kecualikan nilai ini", aksi: () => { P.langkah.push({jenis: "filter", kolom: k, op: "!=", nilai: v}); pratinjau(); }}]);
    });
  }

  function menuKolom(e, k) {
    const cepat = l => () => { P.langkah.push(l); pratinjau(); };
    Studio.menu(e.clientX, e.clientY, [
      {label: "Ganti nama…", aksi: () => tambah({jenis: "ganti_nama", dari: k, ke: ""})},
      {label: "Buang kolom", aksi: cepat({jenis: "pilih", kolom: P.hasil.kolom.filter(x => x !== k)})}, "-",
      {label: "Jadikan teks", aksi: cepat({jenis: "ubah_tipe", kolom: k, tipe: "teks"})},
      {label: "Jadikan angka", aksi: cepat({jenis: "ubah_tipe", kolom: k, tipe: "angka"})},
      {label: "Jadikan tanggal", aksi: cepat({jenis: "ubah_tipe", kolom: k, tipe: "tanggal"})}, "-",
      ...Object.entries(AKSI).filter(([a]) => a !== "isi_kosong").map(([a, t]) => ({label: t, aksi: cepat({jenis: "bersihkan", kolom: k, aksi: a})})),
      {label: "Isi nilai kosong…", aksi: () => tambah({jenis: "bersihkan", kolom: k, aksi: "isi_kosong", nilai: ""})},
      {label: "Saring kolom ini…", aksi: () => tambah({jenis: "filter", kolom: k, op: "==", nilai: ""})},
    ]);
  }

  /* ---------- Simpan ---------- */
  async function simpan() {
    const nama = $("#prepNama").value.trim();
    if (!nama) { Studio.notif("Isi nama dataset baru (huruf kecil, angka, garis bawah).", true); return; }
    try {
      const j = await Studio.api("/studio/api/prep/simpan", {dataset_id: P.ds, langkah: P.langkah, nama});
      Studio.notif(`Dataset <b>${esc(j.nama)}</b> tersimpan (${j.kolom} kolom). Hak akses: <code>${esc(j.hak_akses)}</code>.
        <a href="#" id="bukaLembarBaru">Buat grafik dari dataset ini</a>`);
      await Studio.muatAwal(); isiDataset();
      $("#bukaLembarBaru").onclick = ev => {
        ev.preventDefault(); $('nav.tab button[data-tab="lembar"]').click();
        $("#pilihDataset").innerHTML = Studio.awal.dataset.map(d => `<option value="${d.id}">${esc(d.nama)}</option>`).join("");
        Studio.lembar.gantiDataset(j.id);
      };
    } catch (e) { Studio.notif(esc(e.message), true); }
  }

  function isiDataset() {
    $("#prepDataset").innerHTML = Studio.awal.dataset.map(d => `<option value="${d.id}" ${d.id === P.ds ? "selected" : ""}>${esc(d.nama)}</option>`).join("");
  }
  function gantiAsal(id) {
    Object.assign(P, {ds: Number(id), langkah: [], aktif: null, kolomAsal: []});
    $("#editorLangkah").classList.remove("tampil");
    pratinjau();
  }

  Studio.saatMulai.push(() => {
    isiDataset();
    $("#prepDataset").onchange = () => gantiAsal($("#prepDataset").value);
    $("#prepSimpan").onclick = simpan;
    $("#prepSimpan").disabled = !Studio.awal.izin.dataset;
    if (!Studio.awal.izin.dataset) $("#prepSimpan").title = "Butuh kemampuan 'Kelola dataset' (Pusat Kendali → Hak akses)";
    $("#lihatSql").onclick = () => { $("#sqlbox").classList.toggle("tampil"); $("#lihatSql").textContent = $("#sqlbox").classList.contains("tampil") ? "Sembunyikan SQL" : "Lihat SQL"; };
    let dimuat = false;
    window.addEventListener("tab", e => {                     // pratinjau pertama saat tab dibuka
      if (e.detail !== "prep" || dimuat || !Studio.awal.dataset.length) return;
      dimuat = true;
      const minta = Number(new URLSearchParams(location.search).get("dataset"));
      const ds = Studio.awal.dataset.find(d => d.id === minta) || Studio.awal.dataset[0];
      isiDataset(); $("#prepDataset").value = ds.id; gantiAsal(ds.id);
    });
    // Dibuka langsung lewat /studio/?tab=prep (tab sudah aktif sebelum data awal termuat)
    if ($('nav.tab button[data-tab="prep"]').classList.contains("aktif")) window.dispatchEvent(new CustomEvent("tab", {detail: "prep"}));
  });
})();
