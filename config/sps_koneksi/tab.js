// Tab "Hubungkan data" di Pusat Kendali (/pusat-kendali/). Dimuat oleh sps_server/halaman.html.
// Memakai helper halaman itu: $, esc, api, CSRF.
// Alur: 1 Pilih sumber -> 2 Isi detail (atau unggah berkas) -> 3 Uji -> 4 Simpan / impor.
(function () {
  "use strict";
  let KATALOG = null, JENIS = null, BERKAS = null, LULUS = false, ambilSkema = () => [];
  const el = () => $("#hubungkan");

  const langkah = n => `<div class="hbLangkah">${["Pilih sumber", "Isi detail", "Uji koneksi", "Simpan"]
    .map((t, i) => `<span class="${i + 1 === n ? "aktif" : ""}">${i + 1}. ${t}</span>`).join("")}</div>`;
  const hasil = (ok, html) => `<div class="hbHasil ${ok ? "ok" : "gagal"}">${html}</div>`;

  // --- Langkah 1: pilih sumber --------------------------------------------------------------
  function pilihSumber() {
    JENIS = BERKAS = null;
    // Driver tidak ada di image: kartu nonaktif + cara memasang (U21).
    const kartu = j => `<button class="hbJenis" data-jenis="${j.id}" ${j.driver_ada ? "" : `disabled title="${esc(
      j.opsional ||
      `Paket Python '${j.paket}' belum ada di image ini. Admin server: taruh berkas .whl-nya di docker\\wheels, tambahkan ` +
      `namanya ke docker\\wheels\\paket.txt, lalu jalankan scripts\\init.ps1 (lihat docs 06 §4).`)}"`}>
      <b>${esc(j.nama)}</b><span class="ket">${esc(j.driver_ada ? j.keterangan || " " : `Driver belum terpasang (paket ${j.paket}). Arahkan kursor untuk cara memasang.`)}</span></button>`;
    const kelompok = Object.entries(KATALOG.kelompok).map(([k, label]) => {
      const isi = KATALOG.jenis.filter(j => j.kelompok === k);
      return isi.length ? `<h2>${esc(label)}</h2><div class="hbGrid">${isi.map(kartu).join("")}</div>` : "";
    }).join("");
    const jenisBerkas = [...new Set(Object.values(KATALOG.berkas))].join(", ");
    el().innerHTML = `${langkah(1)}
      <div class="kartu ket">Hubungkan sumber data kantor dalam 4 langkah. Koneksi selalu <b>hanya-baca</b> (data sumber tidak bisa diubah)
        dan password disimpan terenkripsi. Setelah tersimpan, sumber muncul di SQL Lab, Dataset &amp; Studio Visual.</div>
      <h2>Berkas</h2>
      <div class="hbGrid"><button class="hbJenis" data-jenis="berkas"><b>Berkas (Access, Excel, CSV, …)</b>
        <span class="ket">${esc(jenisBerkas)} — disalin ke ALDx Engine</span></button></div>
      ${kelompok}
      <h2>Koneksi tersimpan</h2><div id="hbDaftar" class="kartu ket">Memuat…</div>`;
    el().querySelectorAll("[data-jenis]").forEach(b => b.onclick = () =>
      b.dataset.jenis === "berkas" ? formBerkas() : formDatabase(KATALOG.jenis.find(j => j.id === b.dataset.jenis)));
    daftarKoneksi();
  }

  async function daftarKoneksi() {
    try {
      const d = await api("/hubungkan/api/koneksi");
      $("#hbDaftar").innerHTML = d.length ? `<table><tr><th>Nama</th><th>Jenis</th><th>Akses</th><th>Skema yang ditampilkan</th><th></th></tr>${d.map(k =>
        `<tr><td>${esc(k.nama)}</td><td>${esc(k.dialek)}</td><td>${k.dml ? "baca-tulis" : "hanya-baca"}</td>
         <td>${k.skema.length ? k.skema.map(esc).join(", ") : '<span class="ket">semua</span>'}</td>
         <td><button class="kecil" data-skema="${k.id}" data-nama="${esc(k.nama)}">Atur skema</button></td></tr>`).join("")}</table>
        <div id="hbAturSkema"></div>
        <p class="ket">Ganti alamat/password atau hapus koneksi: <a href="/databaseview/list/">pengaturan koneksi lanjutan</a>.</p>` : "Belum ada koneksi.";
      $("#hbDaftar").querySelectorAll("[data-skema]").forEach(b => b.onclick = () => aturSkema(+b.dataset.skema, b.dataset.nama));
    } catch (e) { $("#hbDaftar").innerHTML = `<span class="galat">${esc(e.message)}</span>`; }
  }

  // --- Pilihan skema: hanya skema ini yang tampil di Dataset, SQL Lab, Kueri Visual, Studio ------------
  function pemilihSkema(wadah, semua, pilih, login) {
    const terpilih = new Set(pilih && pilih.length ? pilih : (login && semua.includes(login) ? [login] : []));
    wadah.innerHTML = `<div class="hbSkema"><b>Skema yang ditampilkan</b>
      <span class="ket">Hanya skema tercentang yang muncul di Dataset, SQL Lab, Kueri Visual &amp; Studio. Kosong = semua skema.</span>
      <div class="aksi" style="margin:8px 0"><input type="text" class="hbCariSkema" placeholder="Cari skema…">
        <button class="kecil" data-aksi="login">Hanya skema login${login ? ` (${esc(login)})` : ""}</button>
        <button class="kecil" data-aksi="kosong">Kosongkan</button></div>
      <div class="hbDaftarSkema" style="max-height:240px;overflow:auto;columns:3 180px;border:1px solid var(--garis);border-radius:8px;padding:8px">
        ${semua.map(s => `<label style="display:block"><input type="checkbox" value="${esc(s)}" ${terpilih.has(s) ? "checked" : ""}> ${esc(s)}</label>`).join("")}</div>
      <span class="ket hbJumlahSkema"></span></div>`;
    const kotak = () => [...wadah.querySelectorAll(".hbDaftarSkema input")];
    const hitung = () => { const n = kotak().filter(x => x.checked).length;
      wadah.querySelector(".hbJumlahSkema").textContent = n ? `${n} skema dipilih` : `Semua ${semua.length} skema akan tampil`; };
    wadah.querySelector(".hbCariSkema").oninput = e => { const q = e.target.value.toLowerCase();
      kotak().forEach(x => { x.parentElement.style.display = x.value.toLowerCase().includes(q) ? "" : "none"; }); };
    wadah.querySelector('[data-aksi="login"]').onclick = () => { kotak().forEach(x => { x.checked = x.value === login; }); hitung(); };
    wadah.querySelector('[data-aksi="kosong"]').onclick = () => { kotak().forEach(x => { x.checked = false; }); hitung(); };
    wadah.querySelector(".hbDaftarSkema").onchange = hitung; hitung();
    return () => kotak().filter(x => x.checked).map(x => x.value);
  }

  async function aturSkema(id, nama) {
    const w = $("#hbAturSkema");
    w.innerHTML = `<div class="kartu ket">Membaca skema ${esc(nama)}…</div>`;
    try {
      const d = await api(`/hubungkan/api/koneksi/${id}/skema`);
      w.innerHTML = `<div class="kartu"><b>${esc(nama)}</b><div id="hbPilihSkema"></div>
        <div class="aksi" style="margin-top:8px"><button class="utama" id="hbSimpanSkema">Simpan skema</button>
        <button class="kedua" id="hbBatalSkema">Batal</button></div></div>`;
      const ambilPilihan = pemilihSkema($("#hbPilihSkema"), d.semua, d.pilih, d.skema_login);
      $("#hbBatalSkema").onclick = () => { w.innerHTML = ""; };
      $("#hbSimpanSkema").onclick = async () => {
        await api(`/hubungkan/api/koneksi/${id}/skema`, {skema: ambilPilihan()});
        daftarKoneksi();
      };
    } catch (e) { w.innerHTML = `<div class="kartu galat">${esc(e.message)}</div>`; }
  }

  // --- Langkah 2-4: database ----------------------------------------------------------------
  function kontrol(i) {
    const atr = `data-kunci="${i.kunci}" ${i.wajib && i.jenis !== "ya_tidak" ? "required" : ""}`;
    if (i.jenis === "ya_tidak") return `<label><span><input type="checkbox" ${atr}> ${esc(i.label)}</span></label>`;
    const judul = `${esc(i.label)}${i.wajib ? " *" : ""}`, bantu = i.bantu ? `<span class="ket">${esc(i.bantu)}</span>` : "";
    if (i.jenis === "panjang") return `<label class="lebar">${judul}<textarea ${atr}></textarea>${bantu}</label>`;
    const tipe = i.jenis === "rahasia" ? "password" : i.jenis === "angka" ? "number" : "text";
    return `<label>${judul}<input type="${tipe}" ${atr} value="${esc(i.bawaan)}" autocomplete="off">${bantu}</label>`;
  }

  function isian() {
    const n = {};
    el().querySelectorAll("[data-kunci]").forEach(x => { n[x.dataset.kunci] = x.type === "checkbox" ? x.checked : x.value.trim(); });
    return n;
  }

  function formDatabase(j) {
    JENIS = j; LULUS = false;
    el().innerHTML = `${langkah(2)}
      <div class="kartu"><b>${esc(j.nama)}</b> <span class="ket">${esc(j.keterangan)}</span>
        <div class="hbForm" style="margin-top:12px">${j.isian.map(kontrol).join("")}
          <label class="lebar">Nama koneksi (tampil di Superset) *<input type="text" id="hbNama" value="${esc(j.nama)}" maxlength="120"></label></div>
        <div id="hbHasil"></div>
        <div class="aksi" style="margin-top:12px"><button class="kedua" id="hbKembali">← Kembali</button>
          <button class="utama" id="hbUji">Uji koneksi</button><button class="utama" id="hbSimpan" disabled>Simpan</button></div></div>`;
    el().querySelectorAll("[data-kunci]").forEach(x => x.oninput = () => { LULUS = false; $("#hbSimpan").disabled = true; });
    $("#hbKembali").onclick = pilihSumber;
    $("#hbUji").onclick = uji;
    $("#hbSimpan").onclick = simpan;
  }

  async function uji() {
    const b = $("#hbUji"); b.disabled = true; b.textContent = "Menguji…";
    el().querySelector(".hbLangkah").outerHTML = langkah(3);
    try {
      const r = await api("/hubungkan/api/uji", {jenis: JENIS.id, isian: isian()});
      LULUS = true; $("#hbSimpan").disabled = false;
      $("#hbHasil").innerHTML = hasil(true, `<b>Berhasil tersambung</b> dalam ${r.ms} ms · versi server ${esc(r.versi)}` +
        `<br>Pilih skema yang berisi data Anda, lalu klik <b>Simpan</b>.`) + '<div id="hbPilihSkema"></div>';
      ambilSkema = r.skema.length ? pemilihSkema($("#hbPilihSkema"), r.skema, [], r.skema_login) : () => [];
    } catch (e) {
      $("#hbHasil").innerHTML = hasil(false, `<b>Belum tersambung.</b> ${esc(e.message)}
        <br><span class="ket">Periksa alamat, port, nama pengguna &amp; password, serta firewall antara server ini dan database.</span>`);
    } finally { b.disabled = false; b.textContent = "Uji koneksi"; }
  }

  async function simpan() {
    if (!LULUS) return;
    const b = $("#hbSimpan"); b.disabled = true;
    try {
      const r = await api("/hubungkan/api/simpan", {jenis: JENIS.id, isian: isian(), nama: $("#hbNama").value, skema: ambilSkema()});
      el().innerHTML = `${langkah(4)}<div class="kartu">${hasil(true, `<b>Koneksi "${esc(r.nama)}" tersimpan.</b>`)}
        <p>Langkah berikutnya:</p><ul>
          <li><a href="/sqllab/?dbid=${r.id}">Coba query di SQL Lab</a></li>
          <li><a href="/dataset/add/">Buat dataset</a> dari tabel di koneksi ini</li>
          <li>Buka <a href="/studio/">Studio Visual</a> untuk membuat chart</li></ul>
        <button class="kedua" id="hbLagi">Hubungkan sumber lain</button></div>`;
      $("#hbLagi").onclick = pilihSumber;
    } catch (e) { $("#hbHasil").innerHTML = hasil(false, esc(e.message)); b.disabled = false; }
  }

  // --- Langkah 2-4: berkas ------------------------------------------------------------------
  function formBerkas() {
    const akhiran = Object.keys(KATALOG.berkas).join(",");
    el().innerHTML = `${langkah(2)}
      <div class="kartu"><b>Berkas</b> <span class="ket">${KATALOG.maks_mb ? "Maks " + KATALOG.maks_mb.toLocaleString("id-ID") + " MB." : "Tanpa batas ukuran."} Isi berkas disalin ke ALDx Engine,
        lalu tiap tabel menjadi dataset siap dibuat chart. Mengimpor ulang dengan nama sama = isi diganti.</span>
        <div class="hbForm" style="margin-top:12px"><label class="lebar">Pilih berkas
          <input type="file" id="hbBerkas" accept="${akhiran}"></label></div>
        <div id="hbHasil"></div>
        <div class="aksi" style="margin-top:12px"><button class="kedua" id="hbKembali">← Kembali</button></div></div>`;
    $("#hbKembali").onclick = pilihSumber;
    $("#hbBerkas").onchange = unggah;
  }

  async function unggah() {
    const f = $("#hbBerkas").files[0]; if (!f) return;
    $("#hbHasil").innerHTML = `<p class="ket">Mengunggah &amp; membaca ${esc(f.name)}…</p>`;
    const fd = new FormData(); fd.append("berkas", f);
    const r = await fetch("/hubungkan/api/berkas", {method: "POST", headers: {"X-CSRFToken": CSRF}, body: fd});
    const j = await r.json().catch(() => ({error: "Gagal (" + r.status + ")"}));
    if (!r.ok) return $("#hbHasil").innerHTML = hasil(false, esc(j.error));
    BERKAS = j; pilihTabel();
  }

  function pilihTabel() {
    const b = BERKAS;
    el().innerHTML = `${langkah(3)}
      <div class="kartu"><b>${esc(b.nama)}</b> <span class="ket">${esc(b.jenis)} · ${b.tabel.length} tabel</span>
        <div class="hbTabel" style="margin-top:10px"><table><tr><th></th><th>Tabel</th><th>Kolom &amp; contoh isi</th></tr>
        ${b.tabel.map((t, i) => `<tr><td><input type="checkbox" data-tabel="${i}" ${t.galat ? "disabled" : "checked"}></td>
          <td>${esc(t.nama)}</td><td>${t.galat ? `<span class="galat">${esc(t.galat)}</span>` :
          `${t.kolom.map(esc).join(", ")}<div class="hbContoh">${(t.contoh[0] || []).map(esc).join(" | ")}</div>`}</td></tr>`).join("")}
        </table></div>
        <div class="hbForm" style="margin-top:12px"><label>Awalan nama tabel di engine
          <input type="text" id="hbAwalan" value="${esc(b.awalan)}" maxlength="30"><span class="ket">Contoh hasil: ${esc((b.awalan + "_" + (b.tabel[0]?.nama || "tabel")).toLowerCase())} · kolom foto/lampiran tidak ikut diimpor</span></label></div>
        <div id="hbHasil"></div>
        <div class="aksi" style="margin-top:12px"><button class="kedua" id="hbKembali">← Kembali</button>
          <button class="utama" id="hbImpor">Impor ke ALDx Engine</button></div></div>`;
    $("#hbKembali").onclick = formBerkas;
    $("#hbImpor").onclick = imporBerkas;
  }

  async function imporBerkas() {
    const tabel = [...el().querySelectorAll("[data-tabel]:checked")].map(x => BERKAS.tabel[+x.dataset.tabel].nama);
    if (!tabel.length) return $("#hbHasil").innerHTML = hasil(false, "Pilih minimal satu tabel.");
    const b = $("#hbImpor"); b.disabled = true; b.textContent = "Mengimpor…";
    try {
      const r = await api(`/hubungkan/api/berkas/${BERKAS.token}`, {tabel, awalan: $("#hbAwalan").value, nama_asli: BERKAS.nama});
      el().innerHTML = `${langkah(4)}<div class="kartu">${hasil(true, `<b>${r.hasil.length} tabel diimpor.</b>`)}
        <table><tr><th>Tabel asal</th><th>Dataset</th><th class="n">Baris</th><th></th></tr>${r.hasil.map(h =>
          `<tr><td>${esc(h.tabel)}</td><td>${esc(h.dataset)}</td><td class="n">${fmt.format(h.baris)}</td>
           <td><a href="/explore/?datasource_type=table&datasource_id=${h.dataset_id}">Buat chart</a></td></tr>`).join("")}</table>
        <button class="kedua" id="hbLagi" style="margin-top:10px">Hubungkan sumber lain</button></div>`;
      $("#hbLagi").onclick = pilihSumber;
    } catch (e) { $("#hbHasil").innerHTML = hasil(false, esc(e.message)); b.disabled = false; b.textContent = "Impor ke ALDx Engine"; }
  }

  window.muatHubungkan = async function () {
    try { KATALOG = KATALOG || await api("/hubungkan/api/katalog"); pilihSumber(); }
    catch (e) { el().innerHTML = `<div class="kartu galat">${esc(e.message)}</div>`; }
  };
})();
