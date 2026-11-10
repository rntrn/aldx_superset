// Tab "Identitas & Tema" di Pusat Kendali (/pusat-kendali/). Dimuat oleh sps_server/halaman.html.
// Memakai helper halaman itu: $, esc, api, CSRF. Semua perubahan berlaku tanpa restart.
(function () {
  "use strict";
  let DATA = null, UBAH = {};

  // --- Warna (sama dengan sps_identitas/tema.py) ---------------------------------------------
  const rgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
  const hex = a => "#" + a.map(v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0")).join("").toUpperCase();
  const campur = (a, b, p) => hex(rgb(a).map((x, i) => x + (rgb(b)[i] - x) * p));
  const terang = h => { const k = v => (v /= 255) <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4;
    const [r, g, b] = rgb(h).map(k); return .2126 * r + .7152 * g + .0722 * b; };
  const sah = h => /^#[0-9A-Fa-f]{6}$/.test(h);

  const nilai = () => ({...DATA.nilai, ...UBAH});

  function pratinjau() {
    const n = nilai(), el = $("#idnPratinjau");
    if (!el || !sah(n.warna_utama) || !sah(n.warna_aksen)) return;
    const u = n.warna_utama, a = n.warna_aksen;
    Object.entries({"--sps-utama": u, "--sps-utama-gelap": campur(u, "#000000", .25), "--sps-utama-terang": campur(u, "#FFFFFF", .22),
      "--sps-utama-muda": campur(u, "#FFFFFF", .9), "--sps-aksen": a, "--sps-latar": n.warna_latar,
      "--sps-teks-utama": terang(u) < .42 ? "#FFFFFF" : "#111827"}).forEach(([k, v]) => el.style.setProperty(k, v));
    $("#idnPNama").textContent = n.nama_aplikasi; $("#idnPPerusahaan").textContent = n.nama_perusahaan;
    $("#idnPSlogan").textContent = n.slogan;
    el.dataset.hiasan = n.hiasan;
  }

  function kontrol(i, v) {
    const id = `idn_${i.kunci}`, data = `data-kunci="${i.kunci}"`;
    if (i.jenis === "warna") return `<div class="idnWarna"><input type="color" id="${id}" ${data} value="${esc(v)}">
      <input type="text" ${data} data-pasangan="${id}" value="${esc(v)}" maxlength="7"></div>`;
    if (i.jenis === "pilihan") return `<select id="${id}" ${data}>${i.opsi.map(o => `<option ${o === v ? "selected" : ""}>${esc(o)}</option>`).join("")}</select>`;
    if (i.jenis === "ya_tidak") return `<label class="idnCek"><input type="checkbox" id="${id}" ${data} ${v ? "checked" : ""}> aktif</label>`;
    if (i.jenis === "berkas") {
      const ket = v === "unggah" ? "diunggah" : v.startsWith("statis:") ? "bawaan: " + v.slice(7) : "otomatis";
      const gelap = i.kunci === "logo_putih" ? " gelap" : "";
      return `<div class="idnBerkas"><span class="idnGambar${gelap}"><img src="/identitas/berkas/${i.kunci}?v=${DATA.versi}" alt=""></span>
        <span class="ket">${esc(ket)}</span>
        <label class="kecil tombolBerkas">Unggah…<input type="file" accept="image/*" data-unggah="${i.kunci}" hidden></label>
        ${v ? `<button class="kecil" data-kosongkan="${i.kunci}">Pakai otomatis</button>` : ""}</div>`;
    }
    return `<input type="text" id="${id}" ${data} value="${esc(v)}">`;
  }

  function gambar() {
    const n = nilai();
    const grup = DATA.grup.map(([g, label]) => `<div class="kartu"><b>${esc(label)}</b>` +
      DATA.isian.filter(i => i.grup === g).map(i => `<div class="atur${i.kunci in UBAH ? " ubah" : ""}">
        <div><div class="nama">${esc(i.label)}</div></div><div style="grid-column:2/-1">${kontrol(i, n[i.kunci])}</div>
        ${i.bantu ? `<div class="bantu">${esc(i.bantu)}</div>` : ""}</div>`).join("") + "</div>").join("");
    $("#identitas").innerHTML = `
      <div class="kartu ket">Nama, logo, warna &amp; animasi untuk <b>semua</b> halaman: login, dashboard, Studio, Asisten AI.
        Berlaku tanpa restart (pengguna lain melihatnya dalam ±1 menit, cukup muat ulang halaman).</div>
      <h2>Preset cepat</h2>
      <div class="idnPreset">${DATA.preset.map(p => `<button class="kedua" data-preset="${p.nama}">
        <span class="idnChip" style="background:${p.utama}"></span><span class="idnChip" style="background:${p.aksen}"></span>${esc(p.label)}</button>`).join("")}</div>
      <div class="idnTata"><div>${grup}</div>
        <div class="idnSamping"><h2 style="margin-top:0">Pratinjau</h2>
          <div id="idnPratinjau" class="idnP">
            <div class="idnPBar"><span class="idnPLogo"></span><b id="idnPNama"></b><span class="idnPMenu">Dashboard · Chart · SQL</span></div>
            <div class="idnPIsi"><div class="idnPLogin"><div class="idnPPerusahaan" id="idnPPerusahaan"></div><div id="idnPSlogan" class="ket"></div>
              <div class="idnPInput"></div><div class="idnPInput"></div><div class="idnPTombol">Masuk</div></div>
              <div class="idnPKartu"><div class="idnPJudul"></div><div class="idnPBatang"><i></i><i></i><i></i><i></i><i></i></div></div></div>
          </div>
          <div style="margin-top:12px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            <button class="utama" id="idnSimpan" ${Object.keys(UBAH).length ? "" : "disabled"}>Simpan identitas</button>
            <button class="kedua" id="idnBatal" ${Object.keys(UBAH).length ? "" : "disabled"}>Batalkan</button>
            <a href="/login/" target="_blank" style="color:var(--navy);font-size:13px">Lihat halaman login ↗</a></div>
          <div id="idnPesan" style="margin-top:8px"></div></div></div>`;
    pasangAcara(); pratinjau();
  }

  function ubah(kunci, v) {
    if (JSON.stringify(v) === JSON.stringify(DATA.nilai[kunci])) delete UBAH[kunci]; else UBAH[kunci] = v;
    const ada = Object.keys(UBAH).length;
    $("#idnSimpan").disabled = $("#idnBatal").disabled = !ada;
    document.querySelector(`[data-kunci="${kunci}"]`)?.closest(".atur")?.classList.toggle("ubah", kunci in UBAH);
    pratinjau();
  }

  function pesan(html) { $("#idnPesan").innerHTML = html; }

  function terapkanCss(versi) {   // halaman ini langsung ikut berubah
    document.querySelectorAll("link#sps-tema").forEach(l => l.href = `/identitas/tema.css?v=${versi}`);
    document.querySelectorAll('img[src^="/identitas/berkas/"]').forEach(img => img.src = img.src.replace(/(\?v=.*)?$/, `?v=${versi}`));
    document.querySelectorAll('link[rel="icon"]').forEach(l => l.href = `/identitas/berkas/favicon?v=${versi}`);
  }

  async function selesai(r, teks) {
    DATA.nilai = r.nilai; DATA.versi = r.versi; UBAH = {};
    gambar(); terapkanCss(r.versi); pesan(`<span class="sukses">${esc(teks)}</span>`);
  }

  function pasangAcara() {
    document.querySelectorAll("#identitas [data-kunci]").forEach(el => el.oninput = el.onchange = () => {
      const k = el.dataset.kunci;
      const v = el.type === "checkbox" ? el.checked : el.value.trim();
      if (el.type === "color") document.querySelector(`[data-pasangan="${el.id}"]`).value = v.toUpperCase();
      if (el.dataset.pasangan && sah(v)) $("#" + el.dataset.pasangan).value = v;
      ubah(k, el.type === "color" ? v.toUpperCase() : v);
    });
    document.querySelectorAll("[data-preset]").forEach(b => b.onclick = async () => {
      if (Object.keys(UBAH).length && !confirm("Perubahan yang belum disimpan akan hilang. Lanjut?")) return;
      try { await selesai(await api("/identitas/api/preset", {nama: b.dataset.preset}), "Preset diterapkan & disimpan."); }
      catch (e) { pesan(`<span class="galat">${esc(e.message)}</span>`); }
    });
    document.querySelectorAll("[data-unggah]").forEach(inp => inp.onchange = async () => {
      const f = inp.files[0]; if (!f) return;
      const fd = new FormData(); fd.append("berkas", f);
      const r = await fetch(`/identitas/api/berkas/${inp.dataset.unggah}`, {method: "POST", headers: {"X-CSRFToken": CSRF}, body: fd});
      const j = await r.json().catch(() => ({error: "Gagal (" + r.status + ")"}));
      if (!r.ok) return pesan(`<span class="galat">${esc(j.error)}</span>`);
      selesai(j, "Berkas diunggah & dipakai.");
    });
    document.querySelectorAll("[data-kosongkan]").forEach(b => b.onclick = async () => {
      try { await selesai(await api("/identitas/api", {perubahan: {[b.dataset.kosongkan]: ""}}), "Kembali ke logo otomatis."); }
      catch (e) { pesan(`<span class="galat">${esc(e.message)}</span>`); }
    });
    $("#idnBatal").onclick = () => { UBAH = {}; gambar(); };
    $("#idnSimpan").onclick = async () => {
      $("#idnSimpan").disabled = true;
      try { await selesai(await api("/identitas/api", {perubahan: UBAH}), "Tersimpan. Sudah berlaku di semua halaman."); }
      catch (e) { pesan(`<span class="galat">${esc(e.message)}</span>`); $("#idnSimpan").disabled = false; }
    };
  }

  window.muatIdentitas = async function () {
    try { DATA = await api("/identitas/api"); UBAH = {}; gambar(); }
    catch (e) { $("#identitas").innerHTML = `<div class="kartu galat">${esc(e.message)}</div>`; }
  };
})();
