// Kueri Visual (/kueri/): menyusun SELECT dengan klik. Semua akses data lewat API resmi Superset,
// sehingga izin database, SQL Lab & RLS sama dengan SQL Lab.
//
// Status kueri (Q) -> fungsi susunSql() -> teks SQL -> /api/v1/sqllab/execute/
(function () {
  "use strict";
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const AGG = {"": "—", SUM: "Jumlah", AVG: "Rata-rata", COUNT: "Hitung", COUNT_DISTINCT: "Hitung unik", MIN: "Minimum", MAX: "Maksimum"};
  const OP = {"=": "sama dengan", "!=": "tidak sama", ">": "lebih dari", ">=": "≥", "<": "kurang dari", "<=": "≤",
              LIKE: "memuat teks", IN: "salah satu dari (pisah koma)", "IS NULL": "kosong", "IS NOT NULL": "tidak kosong"};
  // Kolom umum yang TIDAK dipakai untuk gabung otomatis (bernama sama di banyak tabel tapi bukan kunci).
  const UMUM = new Set(["id", "nama", "name", "keterangan", "description", "deskripsi", "status", "created_at", "updated_at",
    "created_by", "updated_by", "created_on", "changed_on", "tanggal", "tgl", "tahun", "bulan", "total", "jumlah", "nilai"]);
  const ANGKA = /INT|DEC|NUM|FLOAT|DOUBLE|REAL|MONEY|NUMBER/i;

  const Q = {db: null, skema: "", tabel: [], gabung: [], kolom: [], filter: [], urut: {kunci: "", arah: "ASC"}};
  let DB = [], TABEL = [];
  // Aturan nama per koneksi (/kueri/api/dialek/<id>): kutip, normalisasi huruf (Oracle/Snowflake/DB2), kata khusus.
  let DIALEK = {kutip_awal: '"', kutip_akhir: '"', normalisasi: false, kata_khusus: new Set()};

  // ---------- API Superset ----------
  async function api(url, data) {
    const r = await fetch(url, data === undefined ? {credentials: "same-origin"} : {
      method: "POST", credentials: "same-origin", body: JSON.stringify(data),
      headers: {"Content-Type": "application/json", "X-CSRFToken": window.SPS_CSRF}});
    const j = await r.json().catch(() => ({}));
    if (!r.ok) {
      const m = (j.errors && j.errors[0] && j.errors[0].message) || j.message || j.error || `Galat ${r.status}`;
      throw new Error(typeof m === "string" ? m : JSON.stringify(m));
    }
    return j;
  }
  const risonStr = s => "'" + String(s).replace(/!/g, "!!").replace(/'/g, "!'") + "'";
  function pesan(html, jenis = "") { $("#pesan").className = "pesan " + jenis; $("#pesan").innerHTML = html; }

  // ---------- SQL: kutip identitas sesuai jenis database ----------
  const kutip = n => DIALEK.kutip_awal + String(n).split(DIALEK.kutip_akhir).join(DIALEK.kutip_akhir + DIALEK.kutip_akhir) + DIALEK.kutip_akhir;
  // Nama tabel/skema/kolom. Oracle dkk.: nama huruf kecil dari Superset = nama HURUF BESAR di database,
  // jadi ditulis tanpa kutip (atau dikutip HURUF BESAR bila kata khusus/berkarakter aneh).
  function qi(n) {
    n = String(n);
    if (!DIALEK.normalisasi) return kutip(n);
    if (n === n.toLowerCase()) {
      return /^[a-z_][a-z0-9_$#]*$/.test(n) && !DIALEK.kata_khusus.has(n) ? n : kutip(n.toUpperCase());
    }
    return kutip(n);                                   // nama berhuruf besar-kecil campuran: persis apa adanya
  }
  const qa = n => kutip(n);                            // alias kolom hasil: selalu dikutip apa adanya
  // Dataset virtual (SQL tersimpan) dipakai sebagai subkueri: FROM (<sql>) t1
  const tabelRef = t => t.sql ? `(\n${t.sql.replace(/^/gm, "    ")}\n)` : (Q.skema ? qi(Q.skema) + "." : "") + qi(t.nama);
  const kol = (a, k) => `${a}.${qi(k)}`;
  const literal = (v, tipe) => (ANGKA.test(tipe || "") && /^-?\d+(\.\d+)?$/.test(String(v).trim()))
    ? String(v).trim() : "'" + String(v).replace(/'/g, "''") + "'";
  const tipeKolom = (a, k) => ((Q.tabel.find(t => t.alias === a) || {}).kolom || []).find(c => c.name === k)?.type || "";

  function namaHasil(c) {
    const ganda = Q.kolom.filter(x => x.k === c.k).length > 1;
    const dasar = ganda ? `${c.a}_${c.k}` : c.k;
    return c.agg ? `${{SUM: "jumlah", AVG: "rata2", COUNT: "hitung", COUNT_DISTINCT: "unik", MIN: "min", MAX: "maks"}[c.agg]}_${dasar}` : dasar;
  }
  function ekspresi(c) {
    const x = kol(c.a, c.k);
    if (!c.agg) return x;
    return c.agg === "COUNT_DISTINCT" ? `COUNT(DISTINCT ${x})` : `${c.agg}(${x})`;
  }

  function susunSql() {
    if (!Q.tabel.length) return "";
    const adaAgg = Q.kolom.some(c => c.agg);
    let pilih;
    const t1 = Q.tabel[0];
    if (Q.tabel.length === 1 && !adaAgg && Q.kolom.length === t1.kolom.length) pilih = ["t1.*"];
    else pilih = Q.kolom.map(c => {
      const e = ekspresi(c), n = namaHasil(c);
      return (c.agg || n !== c.k) ? `${e} AS ${qa(n)}` : e;
    });
    if (!pilih.length) pilih = ["t1.*"];
    let sql = "SELECT\n  " + pilih.join(",\n  ") + `\nFROM ${tabelRef(t1)} t1`;
    Q.tabel.slice(1).forEach(t => {
      const g = Q.gabung.filter(j => j.b === t.alias && j.ka && j.kb);
      const jenis = (Q.gabung.find(j => j.b === t.alias) || {}).jenis || "INNER";
      sql += g.length ? `\n${jenis} JOIN ${tabelRef(t)} ${t.alias} ON ` + g.map(j => `${kol(j.a, j.ka)} = ${kol(j.b, j.kb)}`).join(" AND ")
                      : `\nCROSS JOIN ${tabelRef(t)} ${t.alias}`;
    });
    const syarat = Q.filter.filter(f => f.a && f.k && (f.op.startsWith("IS") || String(f.v).trim() !== "")).map(f => {
      const x = kol(f.a, f.k), tp = tipeKolom(f.a, f.k);
      if (f.op.startsWith("IS")) return `${x} ${f.op}`;
      if (f.op === "LIKE") return `${x} LIKE '%${String(f.v).replace(/'/g, "''")}%'`;
      if (f.op === "IN") return `${x} IN (${String(f.v).split(",").map(v => literal(v.trim(), tp)).join(", ")})`;
      return `${x} ${f.op} ${literal(f.v, tp)}`;
    });
    if (syarat.length) sql += "\nWHERE " + syarat.join("\n  AND ");
    if (adaAgg) {
      const grup = Q.kolom.filter(c => !c.agg).map(ekspresi);
      if (grup.length) sql += "\nGROUP BY " + grup.join(", ");
    }
    if (Q.urut.kunci) {
      const c = Q.kolom.find(x => `${x.a}.${x.k}.${x.agg}` === Q.urut.kunci);
      if (c) sql += `\nORDER BY ${c.agg ? ekspresi(c) : kol(c.a, c.k)} ${Q.urut.arah}`;
    }
    return sql;
  }

  // ---------- Gabung otomatis ----------
  function cariGabung(baru) {
    const kunciMirip = n => /^(kd_|kode|id_|no_|nomor|npwp|nip|nik)|(_id|_kd|_kode|_code|_no)$/i.test(n);
    let terbaik = null;
    for (const lama of Q.tabel) {
      const kandidat = [];
      // 1. foreign key (dari metadata database)
      const kolomFk = fk => fk.column_names || fk.constrained_columns || [];
      for (const fk of baru.fk) if (fk.referred_table === lama.nama)
        kolomFk(fk).forEach((c, i) => kandidat.push({ka: fk.referred_columns[i], kb: c, skor: 100, asal: "foreign key"}));
      for (const fk of lama.fk) if (fk.referred_table === baru.nama)
        kolomFk(fk).forEach((c, i) => kandidat.push({ka: c, kb: fk.referred_columns[i], skor: 100, asal: "foreign key"}));
      // 2. <tabel>_id = id
      if (!kandidat.length) {
        const kb = baru.kolom.find(c => c.name.toLowerCase() === `${lama.nama.toLowerCase()}_id`);
        const ka = lama.kolom.find(c => c.name.toLowerCase() === "id");
        if (ka && kb) kandidat.push({ka: ka.name, kb: kb.name, skor: 80, asal: "pola nama"});
      }
      // 3. kolom bernama sama (selain kolom umum)
      if (!kandidat.length) for (const cb of baru.kolom) {
        const ca = lama.kolom.find(c => c.name.toLowerCase() === cb.name.toLowerCase());
        if (!ca || UMUM.has(cb.name.toLowerCase())) continue;
        kandidat.push({ka: ca.name, kb: cb.name, skor: kunciMirip(cb.name) ? 85 : 60, asal: "kolom bernama sama"});
      }
      if (!kandidat.length) continue;
      const maks = Math.max(...kandidat.map(k => k.skor));
      const pakai = kandidat.filter(k => k.skor === maks && (maks >= 80 || k === kandidat.find(x => x.skor === maks)));
      if (!terbaik || maks > terbaik.skor) terbaik = {lama, pakai, skor: maks};
    }
    return terbaik;
  }

  // ---------- Menambah / menghapus tabel ----------
  async function tambahTabel(nama, virtual) {
    let meta;
    if (virtual) meta = {columns: virtual.kolom, foreignKeys: []};
    else {
      pesan("Membaca kolom " + esc(nama) + "…");
      try {
        meta = await api(`/api/v1/database/${Q.db.id}/table_metadata/?name=${encodeURIComponent(nama)}` +
                         (Q.skema ? `&schema=${encodeURIComponent(Q.skema)}` : ""));
      } catch (e) { return pesan("Gagal membaca tabel: " + esc(e.message), "galat"); }
    }
    const t = {alias: "t" + (Math.max(0, ...Q.tabel.map(x => +x.alias.slice(1))) + 1), nama,
               kolom: (meta.columns || []).map(c => ({name: c.name, type: String(c.type || "")})), fk: meta.foreignKeys || []};
    if (virtual) Object.assign(t, {sql: virtual.sql, datasetId: virtual.id});
    let info = "";
    if (Q.tabel.length) {
      const g = cariGabung(t);
      if (g) {
        g.pakai.forEach(p => Q.gabung.push({a: g.lama.alias, ka: p.ka, b: t.alias, kb: p.kb, jenis: "INNER"}));
        info = `Digabung otomatis (${g.pakai[0].asal}): ` + g.pakai.map(p => `${g.lama.alias}.${esc(p.ka)} = ${t.alias}.${esc(p.kb)}`).join(", ") + ". Ubah di bawah bila kurang tepat.";
      } else {
        Q.gabung.push({a: Q.tabel[0].alias, ka: "", b: t.alias, kb: "", jenis: "INNER"});
        info = "Kolom penghubung tidak ditemukan otomatis. <b>Pilih kolom penghubung</b> di bagian Gabung.";
      }
    }
    const kunciGabung = new Set(Q.gabung.filter(j => j.b === t.alias).map(j => j.kb));
    Q.tabel.push(t);
    t.kolom.forEach(c => { if (!kunciGabung.has(c.name)) Q.kolom.push({a: t.alias, k: c.name, agg: ""}); });
    gambar();
    const gagal = info.includes("tidak ditemukan");
    $("#infoGabung").className = "pesan " + (gagal ? "galat" : "sukses");
    $("#infoGabung").innerHTML = info;
    pesan("");
    if (!gagal) jalankan();
  }
  function hapusTabel(alias) {
    Q.tabel = Q.tabel.filter(t => t.alias !== alias);
    $("#infoGabung").innerHTML = "";
    Q.kolom = Q.kolom.filter(c => c.a !== alias);
    Q.filter = Q.filter.filter(f => f.a !== alias);
    Q.gabung = Q.gabung.filter(j => j.a !== alias && j.b !== alias);
    gambar();
  }

  // ---------- Tampilan ----------
  function gambarTabel() {
    const cari = $("#cariTabel").value.toLowerCase();
    const dipakai = new Set(Q.tabel.map(t => t.nama));
    const isi = TABEL.filter(t => t.value.toLowerCase().includes(cari)).slice(0, 500);
    $("#daftarTabel").innerHTML = isi.length ? isi.map((t, i) =>
      `<div class="tabel ${dipakai.has(t.value) ? "dipakai" : ""}" data-i="${TABEL.indexOf(t)}" title="${t.virtual
        ? "Dataset virtual (SQL tersimpan), dipakai sebagai subkueri. Klik dua kali untuk memakai" : "Klik dua kali untuk memakai"}">${
        t.virtual ? "◇" : "▦"} <span class="nama" title="${esc(t.value)}">${esc(t.value)}</span><span class="jenis">${esc(t.type || "")}</span></div>`).join("")
      : `<div class="bantu">${cari ? `Tidak ada tabel berisi "${esc(cari)}" di skema <b>${esc(Q.skema)}</b>. Coba skema lain di atas.`
                                   : "Skema ini tidak berisi tabel/view yang boleh Anda baca."}</div>`;
    document.querySelectorAll("#daftarTabel .tabel").forEach(el => el.ondblclick = () => {
      const t = TABEL[+el.dataset.i];
      tambahTabel(t.value, t.virtual);
    });
  }

  function gambar() {
    gambarTabel();
    // Kanvas tabel
    $("#kanvas").innerHTML = Q.tabel.length ? Q.tabel.map(t => {
      const pilih = new Set(Q.kolom.filter(c => c.a === t.alias).map(c => c.k));
      return `<div class="kotak"><div class="kepala"><span class="alias">${t.alias}</span>${esc(t.nama)}<button title="Lepas tabel" data-hapus="${t.alias}">×</button></div>
        <div class="kolom">${t.kolom.map(c => `<label><input type="checkbox" data-a="${t.alias}" data-k="${esc(c.name)}" ${pilih.has(c.name) ? "checked" : ""}>${esc(c.name)}<small>${esc(c.type.split("(")[0])}</small></label>`).join("")}</div>
        <div class="semua"><a data-semua="${t.alias}">pilih semua</a><a data-tidak="${t.alias}">kosongkan</a></div></div>`;
    }).join("") : '<div class="kosong">Belum ada tabel. Pilih database &amp; skema di kiri, lalu klik dua kali sebuah tabel.</div>';
    document.querySelectorAll("[data-hapus]").forEach(b => b.onclick = () => hapusTabel(b.dataset.hapus));
    document.querySelectorAll("#kanvas input[type=checkbox]").forEach(c => c.onchange = () => {
      const {a, k} = c.dataset;
      if (c.checked) Q.kolom.push({a, k, agg: ""}); else Q.kolom = Q.kolom.filter(x => !(x.a === a && x.k === k));
      gambarRingkas();
    });
    document.querySelectorAll("[data-semua]").forEach(b => b.onclick = () => {
      const t = Q.tabel.find(x => x.alias === b.dataset.semua);
      t.kolom.forEach(c => { if (!Q.kolom.some(x => x.a === t.alias && x.k === c.name)) Q.kolom.push({a: t.alias, k: c.name, agg: ""}); });
      gambar();
    });
    document.querySelectorAll("[data-tidak]").forEach(b => b.onclick = () => { Q.kolom = Q.kolom.filter(x => x.a !== b.dataset.tidak); gambar(); });
    // Gabung
    const opsiKol = (alias, nilai) => '<option value="">(pilih kolom)</option>' + ((Q.tabel.find(t => t.alias === alias) || {}).kolom || [])
      .map(c => `<option ${c.name === nilai ? "selected" : ""}>${esc(c.name)}</option>`).join("");
    $("#daftarGabung").innerHTML = Q.gabung.length ? '<div class="judulPanel">Gabung (join)</div>' + Q.gabung.map((j, i) => `
      <div class="baris gabung">
        <select data-g="${i}" data-sisi="a">${Q.tabel.filter(t => t.alias !== j.b).map(t => `<option ${t.alias === j.a ? "selected" : ""}>${t.alias}</option>`).join("")}</select>
        <select data-g="${i}" data-sisi="ka">${opsiKol(j.a, j.ka)}</select> =
        <b>${j.b}</b> <select data-g="${i}" data-sisi="kb">${opsiKol(j.b, j.kb)}</select>
        <select data-g="${i}" data-sisi="jenis"><option value="INNER" ${j.jenis === "INNER" ? "selected" : ""}>hanya yang cocok (INNER)</option>
          <option value="LEFT" ${j.jenis === "LEFT" ? "selected" : ""}>semua dari kiri (LEFT)</option></select>
        <button class="kecil" data-tambahsyarat="${i}" title="Tambah kolom penghubung lain">+ kolom</button>
        <button class="kecil" data-buanggabung="${i}">hapus</button></div>`).join("") : "";
    document.querySelectorAll("[data-g]").forEach(s => s.onchange = () => {
      const j = Q.gabung[+s.dataset.g]; j[s.dataset.sisi] = s.value;
      if (s.dataset.sisi === "jenis") Q.gabung.filter(x => x.b === j.b).forEach(x => { x.jenis = s.value; });
      if (s.dataset.sisi === "a") j.ka = "";
      gambar();
    });
    document.querySelectorAll("[data-tambahsyarat]").forEach(b => b.onclick = () => {
      const j = Q.gabung[+b.dataset.tambahsyarat]; Q.gabung.push({a: j.a, ka: "", b: j.b, kb: "", jenis: j.jenis}); gambar();
    });
    document.querySelectorAll("[data-buanggabung]").forEach(b => b.onclick = () => { Q.gabung.splice(+b.dataset.buanggabung, 1); gambar(); });
    gambarRingkas();
  }

  function gambarRingkas() {
    $("#chipKolom").innerHTML = Q.kolom.length ? Q.kolom.map((c, i) => `<span class="chip">${c.a}.${esc(c.k)}
      <select data-agg="${i}" title="Ringkasan">${Object.entries(AGG).map(([k, v]) => `<option value="${k}" ${k === c.agg ? "selected" : ""}>${v}</option>`).join("")}</select>
      <button data-lepas="${i}" title="Lepas">×</button></span>`).join("") +
      (Q.kolom.some(c => c.agg) ? '<div class="bantu">Kolom tanpa ringkasan dipakai untuk <b>mengelompokkan</b> (GROUP BY).</div>' : "")
      : '<span class="bantu">Centang kolom pada tabel di atas.</span>';
    document.querySelectorAll("[data-agg]").forEach(s => s.onchange = () => { Q.kolom[+s.dataset.agg].agg = s.value; gambarRingkas(); });
    document.querySelectorAll("[data-lepas]").forEach(b => b.onclick = () => { Q.kolom.splice(+b.dataset.lepas, 1); gambar(); });
    // Filter
    const semuaKol = Q.tabel.flatMap(t => t.kolom.map(c => ({a: t.alias, k: c.name})));
    $("#daftarFilter").innerHTML = Q.filter.map((f, i) => `<div class="baris">
      <select data-f="${i}" data-x="kol">${semuaKol.map(c => `<option value="${c.a}|${esc(c.k)}" ${c.a === f.a && c.k === f.k ? "selected" : ""}>${c.a}.${esc(c.k)}</option>`).join("")}</select>
      <select data-f="${i}" data-x="op">${Object.entries(OP).map(([k, v]) => `<option value="${k}" ${k === f.op ? "selected" : ""}>${v}</option>`).join("")}</select>
      ${f.op.startsWith("IS") ? "" : `<input type="text" data-f="${i}" data-x="v" value="${esc(f.v)}" placeholder="nilai">`}
      <button class="kecil" data-buangfilter="${i}">hapus</button></div>`).join("");
    document.querySelectorAll("[data-f]").forEach(el => (el.tagName === "INPUT" ? el.oninput = ubahFilter : el.onchange = ubahFilter));
    document.querySelectorAll("[data-buangfilter]").forEach(b => b.onclick = () => { Q.filter.splice(+b.dataset.buangfilter, 1); gambarRingkas(); });
    // Urutan
    $("#urutKolom").innerHTML = '<option value="">(tanpa urutan)</option>' + Q.kolom.map(c =>
      `<option value="${c.a}.${esc(c.k)}.${c.agg}" ${`${c.a}.${c.k}.${c.agg}` === Q.urut.kunci ? "selected" : ""}>${c.agg ? AGG[c.agg] + " " : ""}${c.a}.${esc(c.k)}</option>`).join("");
    if (!$("#ubahManual").checked) $("#sql").value = susunSql();
  }
  function ubahFilter(ev) {
    const el = ev.target, f = Q.filter[+el.dataset.f];
    if (el.dataset.x === "kol") [f.a, f.k] = el.value.split("|");
    else f[el.dataset.x] = el.value;
    if (el.dataset.x === "op") gambarRingkas(); else if (!$("#ubahManual").checked) $("#sql").value = susunSql();
  }

  // ---------- Menjalankan ----------
  async function jalankan() {
    const sql = $("#sql").value.trim();
    if (!sql) return pesan("Belum ada kueri. Klik dua kali sebuah tabel.", "galat");
    $("#jalankan").disabled = true; pesan("Menjalankan…"); const mulai = performance.now();
    try {
      const j = await api("/api/v1/sqllab/execute/", {database_id: Q.db.id, sql, schema: Q.skema || null, runAsync: false,
        queryLimit: 1000, client_id: Math.random().toString(36).slice(2, 12), tab: "Kueri Visual", sql_editor_id: "kueri-visual"});
      if (j.status && j.status !== "success") {
        pesan(`Kueri berjalan di latar (database memakai mode async). Lihat hasilnya di <a href="/sqllab/history/">Riwayat kueri</a>.`);
        return;
      }
      const kolom = (j.columns || []).map(c => c.column_name || c.name);
      const baris = j.data || [];
      $("#hasil").className = "";
      $("#hasil").innerHTML = baris.length ? `<table class="data"><tr>${kolom.map(k => `<th>${esc(k)}</th>`).join("")}</tr>` +
        baris.map(b => "<tr>" + kolom.map(k => typeof b[k] === "number"
          ? `<td class="n">${b[k].toLocaleString("id-ID")}</td>` : `<td title="${esc(b[k])}">${esc(b[k])}</td>`).join("") + "</tr>").join("") + "</table>"
        : '<div class="kosong">Kueri berhasil, tetapi tidak ada baris.</div>';
      pesan(`${baris.length.toLocaleString("id-ID")} baris · ${((performance.now() - mulai) / 1000).toFixed(1)} detik` +
            (baris.length >= 1000 ? " (dibatasi 1.000 baris; simpan jadi dataset untuk semua data)" : ""), "sukses");
    } catch (e) { pesan(esc(e.message), "galat"); }
    finally { $("#jalankan").disabled = false; }
  }

  // Fisik: dataset virtual yang baru disimpan disalin jadi tabel ALDx Engine (mesin ekstrak, di backgrounder).
  async function buatFisik(datasetId, nama) {
    const pilih = $("#jadwalFisik").value;
    const jadwal = pilih === "harian" ? {jenis: "harian", jam: 2} : pilih === "jam" ? {jenis: "jam", setiap: 1} : {jenis: "manual"};
    let e;
    try { e = (await api("/kueri/api/fisik", {dataset_id: datasetId, jadwal})).ekstrak; }
    catch (err) { return pesan(`Dataset virtual <b>${esc(nama)}</b> tersimpan, tetapi tabel fisik gagal dibuat: ${esc(err.message)}`, "galat"); }
    pesan(`Menyalin hasil ke tabel <b>${esc(e.tabel)}</b> di ALDx Engine…`);
    for (let i = 0; i < 300; i++) {                       // maks ±10 menit; setelah itu cek di Pusat Kendali › Ekstrak
      await new Promise(r => setTimeout(r, 2000));
      try { e = await api(`/kueri/api/fisik/${e.id}`); } catch (err) { break; }
      if (e.status === "siap") {
        pesan(`Tabel fisik <b>${esc(e.tabel)}</b> siap (${Number(e.baris_total || 0).toLocaleString("id-ID")} baris). ` +
              `Dataset <b>${esc(e.tabel)}</b> = cepat (tabel), <b>${esc(nama)}</b> = virtual (selalu terbaru).`, "sukses");
        $("#lanjut").innerHTML = `<span class="bantu">Langkah berikutnya:</span>
          <a class="tombol" href="/studio/?dataset=${e.dataset_id}" target="_top">Buat chart dari tabel fisik</a>
          <a class="tombol" href="/pusat-kendali/?tab=ekstrak" target="_top">Atur jadwal di Pusat Kendali › Ekstrak</a>`;
        return;
      }
      if (e.status === "gagal") return pesan(`Penyalinan gagal: ${esc(e.pesan || "")}. Lihat Pusat Kendali › Ekstrak.`, "galat");
    }
    pesan("Penyalinan masih berjalan. Pantau di Pusat Kendali › Ekstrak.", "");
  }

  async function simpanDataset() {
    const nama = $("#namaDataset").value.trim(), sql = $("#sql").value.trim();
    if (!sql) return pesan("Belum ada kueri.", "galat");
    if (!/^[A-Za-z_][A-Za-z0-9_]{1,99}$/.test(nama)) return pesan("Nama dataset: huruf, angka, garis bawah; diawali huruf.", "galat");
    try {
      const j = await api("/api/v1/dataset/", {database: Q.db.id, schema: Q.skema || null, table_name: nama, sql});
      pesan(`Dataset <b>${esc(nama)}</b> tersimpan.`, "sukses");
      if ($("#jenisDataset").value === "fisik") return buatFisik(j.id, nama);
      $("#lanjut").innerHTML = `<span class="bantu">Langkah berikutnya:</span>
        <a href="/studio/?dataset=${j.id}"><button class="utama">Buat chart di Studio Visual</button></a>
        <a href="/studio/?tab=prep&dataset=${j.id}"><button>Persiapan data</button></a>
        <a href="/explore/?datasource_type=table&datasource_id=${j.id}"><button>Buka di Explore</button></a>`;
    } catch (e) {
      const izin = /forbidden|izin|permission|403/i.test(e.message);
      pesan("Gagal menyimpan dataset: " + esc(e.message) + (izin ? " (butuh izin Kelola dataset)" : " — jalankan kueri dulu sampai berhasil, lalu simpan."), "galat");
    }
  }

  // ---------- Memilih database & skema ----------
  async function muatDb() {
    const q = "(filters:!((col:expose_in_sqllab,opr:eq,value:!t)),order_column:database_name,order_direction:asc,page_size:100)";
    try { DB = (await api(`/api/v1/database/?q=${encodeURIComponent(q)}`)).result || []; }
    catch (e) { return pesan(esc(e.message), "galat"); }
    $("#pilihDb").innerHTML = DB.length ? DB.map(d => `<option value="${d.id}">${esc(d.database_name)}</option>`).join("")
      : '<option value="">(belum ada koneksi — Data › Hubungkan data)</option>';
    // Koneksi awal: ?db=, lalu yang terakhir dipakai, lalu koneksi pertama selain ALDx Engine (tabel internal).
    let terakhir = null;
    try { terakhir = localStorage.getItem("sps_kueri_db"); } catch (e) { /* mode privat */ }
    const ada = id => id && DB.some(d => String(d.id) === String(id));
    const bukanEngine = DB.find(d => !/ALDx Engine|SPS Engine/i.test(d.database_name));
    const awal = [new URLSearchParams(location.search).get("db"), terakhir, bukanEngine && bukanEngine.id].find(ada);
    if (awal) $("#pilihDb").value = String(awal);
    if (DB.length) gantiDb();
  }
  // Pesan galat koneksi yang mudah dipahami (pesan asli tetap disertakan untuk admin).
  const galatKoneksi = e => /connect|connection|timed? ?out|unreachable|refused|resolve/i.test(e.message)
    ? `Koneksi <b>${esc(Q.db.database_name)}</b> tidak bisa dihubungi saat ini. Pilih koneksi lain, atau minta admin memeriksanya di Data › Hubungkan data.<br><small>${esc(e.message)}</small>`
    : esc(e.message);
  async function gantiDb(skemaPilihan = null) {
    Q.db = DB.find(d => String(d.id) === $("#pilihDb").value);
    try { localStorage.setItem("sps_kueri_db", String(Q.db.id)); } catch (e) { /* mode privat */ }
    Object.assign(Q, {tabel: [], gabung: [], kolom: [], filter: []}); gambar();
    $("#pilihSkema").innerHTML = "<option>memuat…</option>";
    try {
      const [sk, d] = await Promise.all([
        api(`/api/v1/database/${Q.db.id}/schemas/`).then(j => j.result || []),
        api(`/kueri/api/dialek/${Q.db.id}`).catch(() => ({}))]);
      DIALEK = {kutip_awal: d.kutip_awal || '"', kutip_akhir: d.kutip_akhir || '"', normalisasi: !!d.normalisasi,
                kata_khusus: new Set(d.kata_khusus || [])};
      $("#pilihSkema").innerHTML = sk.map(s => `<option>${esc(s)}</option>`).join("");
      // Skema bawaan = skema yang dipilih di Hubungkan data (atau skema login koneksi).
      const cocok = n => n && sk.find(s => s.toLowerCase() === String(n).toLowerCase());
      const bawaan = cocok(d.skema_bawaan) || sk.find(s => /^(public|dbo|main|default)$/i.test(s)) || sk[0] || "";
      $("#pilihSkema").value = cocok(skemaPilihan) || bawaan; await gantiSkema();
    } catch (e) { $("#pilihSkema").innerHTML = ""; pesan(galatKoneksi(e), "galat"); }
  }
  async function gantiSkema() {
    if (Q.tabel.length && !confirm("Ganti skema akan mengosongkan kueri. Lanjut?")) { $("#pilihSkema").value = Q.skema; return; }
    Q.skema = $("#pilihSkema").value;
    Object.assign(Q, {tabel: [], gabung: [], kolom: [], filter: []}); gambar();
    $("#daftarTabel").innerHTML = '<div class="bantu">Memuat tabel…</div>';
    try {
      const q = `(schema_name:${risonStr(Q.skema)},force:!f)`;
      TABEL = (await api(`/api/v1/database/${Q.db.id}/tables/?q=${encodeURIComponent(q)}`)).result || [];
    } catch (e) { TABEL = []; pesan(galatKoneksi(e), "galat"); }
    // Dataset virtual di koneksi & skema ini: tampil di atas daftar, bertanda "virtual"
    try {
      const v = await api(`/kueri/api/virtual/${Q.db.id}` + (Q.skema ? `?skema=${encodeURIComponent(Q.skema)}` : ""));
      TABEL = [...v.map(d => ({value: d.nama, type: "virtual", virtual: d})), ...TABEL];
    } catch (e) { /* tanpa dataset virtual */ }
    gambarTabel();
  }

  // ---------- Kueri tersimpan (F6) ----------
  let TERSIMPAN = [];
  async function muatTersimpan() {
    try { TERSIMPAN = await api("/kueri/api/simpanan"); } catch (e) { TERSIMPAN = []; }
    $("#pilihTersimpan").innerHTML = `<option value="">Kueri tersimpan… (${TERSIMPAN.length})</option>` +
      TERSIMPAN.map(k => `<option value="${k.id}">${esc(k.nama)} · ${esc(k.diubah)}</option>`).join("");
  }
  async function simpanKueri() {
    if (!Q.tabel.length) return pesan("Belum ada kueri.", "galat");
    const nama = $("#namaKueri").value.trim();
    if (!nama) { $("#namaKueri").focus(); return pesan("Isi nama kueri (nama yang sama = ditimpa).", "galat"); }
    const isi = {db: Q.db.id, skema: Q.skema, tabel: Q.tabel, gabung: Q.gabung, kolom: Q.kolom, filter: Q.filter, urut: Q.urut,
                 manual: $("#ubahManual").checked, sql: $("#sql").value};
    try {
      const j = await api("/kueri/api/simpanan", {nama: nama.trim(), isi});
      pesan(`Kueri <b>${esc(nama)}</b> ${j.ditimpa ? "diperbarui" : "tersimpan"}. Buka lagi dari daftar Kueri tersimpan.`, "sukses");
      muatTersimpan();
    } catch (e) { pesan("Gagal menyimpan kueri: " + esc(e.message), "galat"); }
  }
  async function bukaTersimpan() {
    const k = TERSIMPAN.find(x => String(x.id) === $("#pilihTersimpan").value);
    if (!k) return;
    const isi = k.isi;
    if (!DB.some(d => d.id === isi.db)) return pesan("Koneksi kueri ini tidak ada atau tidak boleh Anda akses.", "galat");
    Object.assign(Q, {tabel: [], gabung: [], kolom: [], filter: []});
    $("#pilihDb").value = String(isi.db);
    await gantiDb(isi.skema);
    Object.assign(Q, {tabel: isi.tabel || [], gabung: isi.gabung || [], kolom: isi.kolom || [], filter: isi.filter || [],
                      urut: isi.urut || {kunci: "", arah: "ASC"}});
    gambar();
    $("#ubahManual").checked = !!isi.manual; $("#sql").readOnly = !isi.manual;
    $("#sql").value = isi.manual ? isi.sql : susunSql();
    $("#namaKueri").value = k.nama;
    pesan(`Kueri <b>${esc(k.nama)}</b> dibuka. Klik Jalankan.`, "sukses");
  }

  // ---------- Mulai ----------
  $("#pilihDb").onchange = gantiDb;
  $("#pilihSkema").onchange = gantiSkema;
  $("#cariTabel").oninput = gambarTabel;
  $("#tambahFilter").onclick = () => {
    const c = Q.kolom[0] || (Q.tabel[0] && {a: Q.tabel[0].alias, k: Q.tabel[0].kolom[0].name});
    if (!c) return pesan("Tambahkan tabel dulu.", "galat");
    Q.filter.push({a: c.a, k: c.k, op: "=", v: ""}); gambarRingkas();
  };
  $("#urutKolom").onchange = () => { Q.urut.kunci = $("#urutKolom").value; gambarRingkas(); };
  $("#urutArah").onchange = () => { Q.urut.arah = $("#urutArah").value; gambarRingkas(); };
  $("#ubahManual").onchange = () => { $("#sql").readOnly = !$("#ubahManual").checked; if (!$("#ubahManual").checked) $("#sql").value = susunSql(); };
  $("#jalankan").onclick = jalankan;
  $("#sql").addEventListener("keydown", e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) jalankan(); });
  // Buka di SQL Lab lewat tautan permanen (SQL panjang di alamat URL membuat gateway menolak: 502).
  $("#keSqlLab").onclick = async () => {
    const sql = $("#sql").value.trim(); if (!sql || !Q.db) return;
    try {
      const j = await api("/api/v1/sqllab/permalink", {dbId: Q.db.id, schema: Q.skema || null, sql, name: "Kueri Visual", autorun: false});
      const alamat = new URL(j.url, location.origin);
      if (window.parent !== window && window.parent.SPS && window.parent.SPS.buka) window.parent.SPS.buka(alamat.pathname);
      else location.href = alamat.pathname;
    } catch (e) { pesan("Gagal membuka SQL Lab: " + esc(e.message), "galat"); }
  };
  $("#simpanDataset").onclick = simpanDataset;
  $("#jenisDataset").onchange = () => { $("#jadwalFisik").hidden = $("#jenisDataset").value !== "fisik"; };
  $("#simpanKueri").onclick = simpanKueri;
  $("#pilihTersimpan").onchange = bukaTersimpan;
  muatDb(); muatTersimpan();
  window.SPS_KUERI = {Q, susunSql, cariGabung, gambar};      // untuk pengujian otomatis
})();
