// Berkas ALDx: ekspor & impor .ald / .aldx (halaman /berkas/).
// Daftar objek diambil dari API Superset (otomatis hanya yang boleh dilihat pengguna).
// Ekspor/impor lewat /berkas/api/* (izin & enkripsi dicek di server: config/sps_berkas/paket.py).
(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const nilai = (nama) => document.querySelector(`input[name=${nama}]:checked`).value;
  const rison = (s) => "'" + String(s).replace(/!/g, "!!").replace(/'/g, "!'") + "'";
  const JENIS = {
    dashboard: {api: "dashboard", nama: "dashboard_title"},
    chart: {api: "chart", nama: "slice_name"},
    dataset: {api: "dataset", nama: "table_name"},
  };
  const pesan = (el, teks, jenis = "") => { el.className = "pesan " + jenis; el.textContent = teks; };
  const buka = (alamat) => (window.parent !== window && window.parent.SPS?.buka) ? window.parent.SPS.buka(alamat) : (location.href = alamat);

  // ---------------- Ekspor ----------------
  const awal = new URLSearchParams(location.search);
  let terpilih = new Set(awal.get("id") ? [Number(awal.get("id"))] : []);
  if (awal.get("jenis") && JENIS[awal.get("jenis")]) document.querySelector(`input[name=jenis][value=${awal.get("jenis")}]`).checked = true;

  let tunda;
  async function muatDaftar() {
    const j = JENIS[nilai("jenis")], cari = $("#cari").value.trim();
    const saring = cari ? `,filters:!((col:${j.nama},opr:ct,value:${rison(cari)}))` : "";
    const q = `(columns:!(id,${j.nama}),order_column:changed_on_delta_humanized,order_direction:desc,page_size:100${saring})`;
    $("#daftar").innerHTML = '<div class="kosong">Memuat...</div>';
    try {
      const r = await fetch(`/api/v1/${j.api}/?q=${encodeURIComponent(q)}`);
      if (!r.ok) throw new Error(r.status === 403 ? "Anda tidak berhak melihat daftar ini." : "Gagal memuat daftar.");
      const hasil = (await r.json()).result || [];
      $("#daftar").innerHTML = hasil.length ? hasil.map((o) =>
        `<label><input type="checkbox" value="${o.id}" ${terpilih.has(o.id) ? "checked" : ""}> ${esc(o[j.nama])}</label>`).join("")
        : '<div class="kosong">Tidak ada. Buat dulu, atau ubah kata pencarian.</div>';
    } catch (e) {
      $("#daftar").innerHTML = `<div class="kosong galat">${esc(e.message)}</div>`;
    }
    perbarui();
  }

  function perbarui() {
    const aldx = nilai("format") === "aldx", sandi = nilai("kunci") === "sandi";
    $("#baris-data").hidden = !aldx;
    if (!aldx) $("#data").checked = false;
    $("#isi-sandi").hidden = !sandi;
    $("#unduh").disabled = terpilih.size === 0;
  }

  $("#daftar").addEventListener("change", (e) => {
    const id = Number(e.target.value);
    e.target.checked ? terpilih.add(id) : terpilih.delete(id);
    perbarui();
  });
  document.querySelectorAll("input[name=jenis]").forEach((r) => r.addEventListener("change", () => { terpilih = new Set(); muatDaftar(); }));
  document.querySelectorAll("input[name=format],input[name=kunci]").forEach((r) => r.addEventListener("change", perbarui));
  $("#cari").addEventListener("input", () => { clearTimeout(tunda); tunda = setTimeout(muatDaftar, 300); });

  $("#unduh").addEventListener("click", async () => {
    const el = $("#pesan-ekspor"), pakaiSandi = nilai("kunci") === "sandi";
    if (pakaiSandi && $("#sandi1").value.length < 8) return pesan(el, "Kata sandi minimal 8 karakter.", "galat");
    if (pakaiSandi && $("#sandi1").value !== $("#sandi2").value) return pesan(el, "Kedua kata sandi tidak sama.", "galat");
    $("#unduh").disabled = true;
    pesan(el, $("#data").checked ? "Menyiapkan berkas & menyalin data... (bisa beberapa menit)" : "Menyiapkan berkas...");
    try {
      const r = await fetch("/berkas/api/ekspor", {method: "POST",
        headers: {"Content-Type": "application/json", "X-CSRFToken": window.SPS_CSRF},
        body: JSON.stringify({jenis: nilai("jenis"), ids: [...terpilih], format: nilai("format"), data: $("#data").checked,
                              sandi: pakaiSandi ? $("#sandi1").value : null, catatan: $("#catatan").value})});
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `Gagal (${r.status})`);
      if (r.status === 202) {                       // dikerjakan backgrounder: pantau di "Ekspor terakhir"
        pesan(el, "Berkas disiapkan di latar belakang. Anda boleh meninggalkan halaman ini; " +
                  "unduh dari bagian Ekspor terakhir setelah siap.", "sukses");
        muatTugas();
        return;
      }
      const nama = r.headers.get("X-Nama-Berkas") || "berkas." + nilai("format");
      const a = Object.assign(document.createElement("a"), {href: URL.createObjectURL(await r.blob()), download: nama});
      document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 30000);
      pesan(el, `Berkas ${nama} diunduh.`, "sukses");
    } catch (e) {
      pesan(el, e.message, "galat");
    } finally {
      $("#unduh").disabled = terpilih.size === 0;
    }
  });

  // ---------------- Ekspor latar (berkas .aldx berisi data) ----------------
  let pantau = null;
  const LABEL_TUGAS = {antre: "menunggu", jalan: "sedang dibuat", siap: "siap", gagal: "gagal"};
  async function muatTugas() {
    let daftar = [];
    try { daftar = await (await fetch("/berkas/api/tugas", {credentials: "same-origin"})).json(); } catch (e) { return; }
    const kotak = $("#ekspor-latar");
    kotak.hidden = !daftar.length;
    $("#daftar-tugas").innerHTML = daftar.map((t) =>
      `<tr><td>${esc(t.dibuat)}</td><td>${esc(t.nama || "–")}</td>` +
      `<td><span class="lencana ${t.status === "siap" ? "ok" : t.status === "gagal" ? "awas" : ""}">${esc(LABEL_TUGAS[t.status] || t.status)}</span>` +
      `${t.status === "gagal" ? `<br><small>${esc(t.pesan)}</small>` : ""}</td>` +
      `<td>${t.status === "siap" ? `<a class="tombol" href="/berkas/api/tugas/${esc(t.id)}/unduh">Unduh</a>` : ""}</td></tr>`).join("");
    clearTimeout(pantau);
    if (daftar.some((t) => t.status === "antre" || t.status === "jalan")) pantau = setTimeout(muatTugas, 3000);
  }
  muatTugas();

  // ---------------- Impor ----------------
  let periksa = null;

  function formulir() {
    const fd = new FormData();
    fd.append("berkas", $("#berkas").files[0]);
    if ($("#sandi-impor").value) fd.append("sandi", $("#sandi-impor").value);
    return fd;
  }

  async function kirim(alamat, fd) {
    const r = await fetch(alamat, {method: "POST", headers: {"X-CSRFToken": window.SPS_CSRF}, body: fd});
    const d = await r.json().catch(() => ({error: `Gagal (${r.status})`}));
    if (!r.ok) throw Object.assign(new Error(d.error || `Gagal (${r.status})`), {data: d});
    return d;
  }

  async function bukaBerkas() {
    const el = $("#pesan-impor");
    $("#hasil-periksa").hidden = true;
    $("#hasil-impor").innerHTML = "";
    if (!$("#berkas").files.length) return;
    pesan(el, "Membuka berkas...");
    try {
      periksa = await kirim("/berkas/api/periksa", formulir());
      tampilkanPeriksa();
      pesan(el, "");
    } catch (e) {
      if (e.data && e.data.perlu_sandi) $("#isi-sandi-impor").hidden = false;
      pesan(el, e.message, "galat");
    }
  }

  function tampilkanPeriksa() {
    const m = periksa.manifest, isi = m.isi || {};
    const jumlah = [["dashboard", "dashboard"], ["chart", "chart"], ["dataset", "dataset"]]
      .filter(([k]) => isi[k]).map(([k, l]) => `${isi[k]} ${l}`).join(" · ");
    const baris = (m.dataset || []).filter((d) => d.data).reduce((a, d) => a + (d.baris || 0), 0);
    $("#ringkas").innerHTML = `<b>${esc(m.judul)}</b> <span class="lencana ${periksa.terverifikasi ? "ok" : "awas"}">${
      periksa.terverifikasi ? "terverifikasi" : "dari server lain"}</span><br>` +
      `.${esc(m.format)} · ${esc(jumlah)}${periksa.punya_data ? ` · data ${baris.toLocaleString("id-ID")} baris` : ""}<br>` +
      `Dibuat oleh <b>${esc(m.dibuat_oleh)}</b>, ${esc(new Date(m.dibuat).toLocaleString("id-ID"))}` +
      (m.catatan ? `<br><i>${esc(m.catatan)}</i>` : "") +
      (periksa.sudah_ada ? `<br>${periksa.sudah_ada} objek sudah ada di server ini.` : "");
    $("#baris-pakai-data").hidden = !periksa.punya_data;
    // Peran yang tidak boleh memuat data (Pengaturan berkas.peran_muat_data): impor definisinya saja.
    const cek = $("#pakai-data"), ket = $("#ket-pakai-data");
    cek.disabled = !periksa.boleh_muat_data;
    if (!periksa.boleh_muat_data) cek.checked = false;
    ket.textContent = !periksa.punya_data ? "" : periksa.boleh_muat_data
      ? "Data hanya terlihat oleh Anda & Admin sampai Admin membagikannya."
      : "Peran Anda tidak boleh memuat data dari berkas. Hanya definisi yang diimpor; pilih koneksi tujuan di bawah.";
    $("#jalankan-impor").disabled = !periksa.boleh_impor;
    if (!periksa.boleh_impor) pesan($("#pesan-impor"), "Anda tidak punya izin membuat objek ini. Hubungi admin.", "galat");
    tampilkanPeta();
    $("#hasil-periksa").hidden = false;
  }

  function tampilkanPeta() {
    const m = periksa.manifest, pakaiData = periksa.punya_data && $("#pakai-data").checked;
    const perlu = new Set((m.dataset || []).filter((d) => !(pakaiData && d.data)).map((d) => d.koneksi_uuid));
    const koneksi = (m.koneksi || []).filter((k) => perlu.has(k.uuid));
    $("#isi-peta").hidden = koneksi.length === 0;
    const opsi = (k) => '<option value="">— pilih —</option>' + periksa.koneksi_tujuan.map((d) =>
      `<option value="${d.id}" ${d.id === k.saran ? "selected" : ""}>${esc(d.nama)}</option>`).join("");
    $("#peta").innerHTML = koneksi.map((k) =>
      `<tr><td style="width:45%">${esc(k.nama)} <small class="bantu">(${esc(k.jenis)})</small></td><td>→</td>` +
      `<td><select data-uuid="${esc(k.uuid)}">${opsi(k)}</select></td></tr>`).join("");
    const timpa = document.querySelector("input[name=mode][value=timpa]");
    timpa.disabled = pakaiData;
    if (pakaiData || !periksa.sudah_ada) document.querySelector("input[name=mode][value=salinan]").checked = true;
  }

  $("#berkas").addEventListener("change", () => {
    $("#namaBerkas").textContent = $("#berkas").files[0] ? $("#berkas").files[0].name : "";
    $("#sandi-impor").value = ""; $("#isi-sandi-impor").hidden = true; bukaBerkas();
  });
  // Seret-lepas (U16): berkas yang dijatuhkan dimasukkan ke input file yang sama.
  const zona = $("#zona");
  ["dragenter", "dragover"].forEach((ev) => zona.addEventListener(ev, (e) => { e.preventDefault(); zona.classList.add("aktif"); }));
  ["dragleave", "drop"].forEach((ev) => zona.addEventListener(ev, () => zona.classList.remove("aktif")));
  zona.addEventListener("drop", (e) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (!f) return;
    if (!/\.aldx?$/i.test(f.name)) return pesan($("#pesan-impor"), "Pilih berkas berakhiran .ald atau .aldx.", "galat");
    const dt = new DataTransfer(); dt.items.add(f); $("#berkas").files = dt.files;
    $("#berkas").dispatchEvent(new Event("change"));
  });
  $("#buka").addEventListener("click", bukaBerkas);
  $("#pakai-data").addEventListener("change", tampilkanPeta);

  $("#jalankan-impor").addEventListener("click", async () => {
    const el = $("#pesan-impor"), peta = {};
    for (const s of document.querySelectorAll("#peta select")) {
      if (!s.value) return pesan(el, "Pilih koneksi tujuan untuk setiap koneksi.", "galat");
      peta[s.dataset.uuid] = Number(s.value);
    }
    const fd = formulir();
    fd.append("peta", JSON.stringify(peta));
    fd.append("mode", nilai("mode"));
    fd.append("data", periksa.punya_data && $("#pakai-data").checked ? "1" : "0");
    $("#jalankan-impor").disabled = true;
    pesan(el, "Mengimpor...");
    try {
      const h = await kirim("/berkas/api/impor", fd);
      pesan(el, `Selesai: ${h.objek.length} ${h.jenis} diimpor${h.tabel_data ? `, ${h.tabel_data} tabel data dimuat` : ""}${
        h.dataset_dipakai ? `, ${h.dataset_dipakai} dataset sudah ada & dipakai apa adanya` : ""}.${
        h.dikunci_pengimpor ? " Data hanya terlihat oleh Anda & Admin sampai Admin membagikannya." : ""}`, "sukses");
      $("#hasil-impor").innerHTML = h.objek.map((o) => `<div><a href="${esc(o.alamat)}" data-buka="${esc(o.alamat)}">${esc(o.nama)}</a>${o.baru ? "" : " (diperbarui)"}</div>`).join("");
      $("#hasil-periksa").hidden = true;
    } catch (e) {
      pesan(el, e.message, "galat");
    } finally {
      $("#jalankan-impor").disabled = false;
    }
  });
  $("#hasil-impor").addEventListener("click", (e) => {
    const a = e.target.closest("a[data-buka]");
    if (a) { e.preventDefault(); buka(a.dataset.buka); }
  });

  muatDaftar();
})();
