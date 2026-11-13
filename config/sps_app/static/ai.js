// ALDx App — panel Asisten AI di setiap halaman dengan peran ahli.
//
//   Buka: tombol ✦ di bilah atas, atau Ctrl + I. Peran dipilih dengan chip atau diketik: /hw-engineer ...
//   Peran & alatnya ditentukan server (/asisten/api/peran, sps_ai/peran.py); hanya peran yang boleh yang tampil.
//   Pertanyaan dikirim ke /asisten/api/chat bersama halaman yang sedang dibuka (konteks).
//   Belum ada model aktif -> layar "Sambungkan AI" (/asisten/api/sambungan): model lokal yang terdeteksi
//   otomatis + langkah memasangnya, dan isian key cloud gratis/berbayar (Admin, tersimpan terenkripsi).
//   Usulan perubahan (tema / pengaturan server) tampil sebagai kartu: baru berlaku setelah pengguna menekan
//   "Terapkan", lewat API biasa yang memeriksa hak aksesnya sendiri.
(function () {
  "use strict";
  const SPS = window.SPS, $ = s => document.querySelector(s);
  const {t} = SPS.i18n, ik = SPS.ikon, AWAL = window.SPS_AWAL;
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const fmt = new Intl.NumberFormat("id-ID", {maximumFractionDigits: 2});

  // Peran bawaan menurut halaman yang sedang dibuka (pertama yang tersedia dipakai).
  const PERAN_HALAMAN = [
    [/^\/pusat-kendali\/?(\?tab=(status|topologi|pengaturan|batas))?$/, ["hw-engineer"]],
    [/^\/pusat-kendali\/\?tab=identitas/, ["ahli-ui-ux"]],
    [/^\/(pusat-kendali\/\?tab=(hubungkan|ekstrak)|tablemodelview|databaseview|kueri|sqllab|studio\/\?tab=prep)/, ["data-engineer"]],
  ];

  let daftarPeran = [], model = [], peranAktif = "analis", peranDipilih = false, riwayat = [], sibuk = false, siap = null;

  // ---------------- Data awal ----------------
  async function muat() {
    if (siap) return siap;
    siap = fetch("/asisten/api/peran", {credentials: "same-origin"}).then(r => (r.ok ? r.json() : null)).then(j => {
      if (!j) return false;
      daftarPeran = j.peran; model = j.model;
      $("#modelAi").innerHTML = model.map(m => `<option value="${esc(m.id)}" ${m.id === j.bawaan ? "selected" : ""}>${esc(m.nama)}</option>`).join("");
      $("#modelAi").hidden = model.length < 2;
      infoModel();
      return true;
    }).catch(() => false);
    return siap;
  }
  function infoModel() {
    const m = model.find(x => x.id === $("#modelAi").value) || model[0];
    $("#privasiAi").textContent = !m ? t("Belum ada model AI yang aktif.") : m.kirim_data ? t("Data boleh dianalisis model")
      : t("Angka tidak dikirim ke model (privasi)");
  }
  const peran = id => daftarPeran.find(p => p.id === id);

  function peranUntukHalaman() {
    const h = SPS.halaman ? SPS.halaman().alamat : "";
    for (const [pola, calon] of PERAN_HALAMAN) {
      if (pola.test(h)) { const p = calon.find(peran); if (p) return p; }
    }
    return "analis";
  }

  // ---------------- Tampilan ----------------
  function gambarPeran() {
    $("#daftarPeran").innerHTML = daftarPeran.map(p =>
      `<button type="button" class="chip-peran ${p.id === peranAktif ? "aktif" : ""}" data-peran="${p.id}" title="${esc(t(p.ringkas))}">` +
      `${ik(p.ikon, 15)}<span>${esc(t(p.nama))}</span></button>`).join("");
    document.querySelectorAll("[data-peran]").forEach(b => b.onclick = () => { pilihPeran(b.dataset.peran, true); $("#masukanAi").focus(); });
    const p = peran(peranAktif);
    $("#peranAiNama").textContent = p ? `${p.perintah} · ${t(p.ringkas)}` : "";
    if (!riwayat.length) sapaan();
  }
  function pilihPeran(id, manual) {
    if (!peran(id)) return;
    peranAktif = id; peranDipilih = peranDipilih || manual;
    gambarPeran();
  }
  // Tombol cepat sesuai halaman: di dashboard, satu klik untuk ringkasan & hal yang janggal.
  function contohHalaman() {
    const h = SPS.halaman ? SPS.halaman().alamat : "";
    return /\/superset\/dashboard\//.test(h)
      ? ["Ringkas dashboard ini dalam 5 poin", "Apa yang janggal atau perlu ditindaklanjuti di dashboard ini?"] : [];
  }
  function sapaan() {
    const p = peran(peranAktif);
    if (!p) return;
    $("#obrolanAi").innerHTML = `<div class="sapa-ai"><div class="ikon-bulat">${ik(p.ikon, 22)}</div>
      <b>${esc(t(p.nama))}</b><p>${esc(t(p.ringkas))}</p>
      <div class="contoh-ai">${[...contohHalaman(), ...p.contoh].map(c => `<button type="button" data-contoh="${esc(c)}">${esc(t(c))}</button>`).join("")}</div>
      <small>${esc(t("Ketik / untuk berganti peran"))}: ${daftarPeran.map(x => `<code>${esc(x.perintah)}</code>`).join(" ")}</small></div>`;
    document.querySelectorAll("[data-contoh]").forEach(b => b.onclick = () => kirim(t(b.dataset.contoh)));
  }

  function md(teks) {
    // Markdown ringan: blok ```kode```, `kode`, **tebal**, daftar "- ", baris baru.
    const bagian = String(teks || "").split(/```(\w*)\n?([\s\S]*?)```/g);
    let html = "";
    for (let i = 0; i < bagian.length; i++) {
      if (i % 3 === 0) {
        html += esc(bagian[i]).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>")
          .replace(/^\s*[-*] (.*)$/gm, "• $1").replace(/\n/g, "<br>");
      } else if (i % 3 === 2) {
        html += `<div class="kode-ai" data-ekspor="${esc(bagian[i - 1] || "kode")}"><pre>${esc(bagian[i].trim())}</pre>` +
                `<button type="button" class="salin-kode">${esc(t("Salin"))}</button></div>`;
      }
    }
    return html;
  }
  function gelembung(kelas, html) {
    const d = document.createElement("div");
    d.className = "pesan-ai " + kelas; d.innerHTML = html;
    $("#obrolanAi").appendChild(d);
    d.querySelectorAll(".salin-kode").forEach(b => b.onclick = () => {
      navigator.clipboard.writeText(b.previousElementSibling.textContent).then(() => SPS.notif(t("Tersalin")));
    });
    $("#obrolanAi").scrollTop = 1e9;
    return d;
  }
  function tabel(p) {
    const kolom = p.kolom || [], baris = (p.baris || []).slice(0, 200);
    const sel = v => typeof v === "number" ? `<td class="n">${fmt.format(v)}</td>` : `<td>${esc(v)}</td>`;
    return `<div class="tabel-ai" data-ekspor="${esc(p.judul || "Hasil Asisten AI")}"><table><tr>${kolom.map(k => `<th>${esc(k)}</th>`).join("")}</tr>` +
      baris.map(b => "<tr>" + kolom.map(k => sel(Array.isArray(b) ? b[kolom.indexOf(k)] : b[k])).join("") + "</tr>").join("") + "</table></div>" +
      ((p.baris || []).length > 200 ? `<small>${esc(t("Menampilkan 200 baris pertama"))}</small>` : "");
  }
  const nilaiTampil = v => v === true ? t("Ya") : v === false ? t("Tidak") : Array.isArray(v) ? v.join(", ") : typeof v === "number" ? fmt.format(v) : String(v ?? "–");

  // WCAG: teks ≥ 4,5 : 1 (AA), teks besar ≥ 3 : 1; elemen non-teks (garis fokus, sorotan) ≥ 3 : 1.
  function kartuKontras(k) {
    const kelas = k.non_teks ? (k.AA_non_teks ? "lulus" : "gagal") : k.AA_teks_normal ? "lulus" : k.AA_teks_besar ? "sedang" : "gagal";
    const tanda = kelas === "lulus" ? "✓ AA" : kelas === "sedang" ? t("AA teks besar") : "✗ " + t("kurang kontras");
    return `<div class="kontras ${kelas}">${esc(t(k.pasangan))}: ${String(k.rasio).replace(".", ",")} : 1 ${esc(tanda)}</div>`;
  }
  function kartuUsulan(p) {
    const judul = p.jenis === "tema" ? t("Usulan perubahan tema") : t("Usulan perubahan pengaturan server");
    const warna = v => /^#[0-9A-F]{6}$/i.test(v) ? `<i class="cuplik" style="background:${v}"></i>` : "";
    const d = gelembung("usulan", `<b>${esc(judul)}</b>${p.alasan ? `<p>${esc(p.alasan)}</p>` : ""}
      <table>${p.rincian.map(r => `<tr><td>${esc(t(r.label))}</td><td>${warna(r.lama)}${esc(nilaiTampil(r.lama))}</td><td>→</td>
        <td><b>${warna(r.baru)}${esc(nilaiTampil(r.baru))}</b> ${r.satuan ? esc(r.satuan) : ""}${r.berlaku === "terapkan" ? ` <span class="lencana-ai">${esc(t("perlu diterapkan"))}</span>` : ""}</td></tr>`).join("")}</table>
      ${(p.kontras || []).map(kartuKontras).join("")}
      ${(p.galat || []).map(g => `<div class="galat-ai">${esc(g)}</div>`).join("")}
      <div class="aksi-usulan"><button type="button" class="tombol utama" data-terapkan ${(p.galat || []).length && p.jenis === "pengaturan" ? "disabled" : ""}>${ik("centang", 16)}${esc(t("Terapkan"))}</button>
      <button type="button" class="tombol" data-abaikan>${esc(t("Abaikan"))}</button></div>`);
    d.querySelector("[data-abaikan]").onclick = () => { d.classList.add("selesai"); d.querySelector(".aksi-usulan").innerHTML = `<small>${esc(t("Diabaikan"))}</small>`; };
    d.querySelector("[data-terapkan]").onclick = async e => {
      e.currentTarget.disabled = true;
      try {
        const r = await fetch(p.api, {method: "POST", credentials: "same-origin",
          headers: {"Content-Type": "application/json", "X-CSRFToken": AWAL.csrf}, body: JSON.stringify({perubahan: p.perubahan})});
        const j = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(j.error || j.message || r.status);
        let ket = t("Diterapkan.");
        if (p.jenis === "tema") { segarkanTema(); ket += " " + t("Tekan F5 bila ada bagian yang belum berubah."); }
        if (p.jenis === "pengaturan" && j.terapkan && j.terapkan.length) ket += " " + t("Sebagian perlu scripts\\terapkan-server.ps1 (restart).");
        d.classList.add("selesai"); d.querySelector(".aksi-usulan").innerHTML = `<span class="sukses-ai">${ik("centang", 16)} ${esc(ket)}</span>`;
        riwayat.push({role: "user", content: "(Usulan sudah diterapkan oleh pengguna.)"});
      } catch (err) {
        e.currentTarget.disabled = false;
        d.querySelector(".aksi-usulan").insertAdjacentHTML("beforeend", `<div class="galat-ai">${esc(t("Gagal menerapkan"))}: ${esc(err.message)}</div>`);
      }
    };
  }
  function segarkanTema() {
    const v = "?v=" + Date.now(), docs = [document];
    try { docs.push($("#bingkai").contentDocument); } catch (e) { /* abaikan */ }
    docs.forEach(d => d && d.querySelectorAll("link#sps-tema, link[href*='/identitas/tema.css']").forEach(l => { l.href = "/identitas/tema.css" + v; }));
  }

  function tampilPeristiwa(p, wadah) {
    if (p.tipe === "langkah") {
      let l = wadah.querySelector(".langkah-ai");
      if (!l) { l = document.createElement("div"); l.className = "langkah-ai"; wadah.appendChild(l); }
      l.insertAdjacentHTML("beforeend", `<span>${ik("centang", 13)}${esc(t(p.teks))}</span>`);
    }
    if (p.tipe === "tabel") wadah.insertAdjacentHTML("beforeend", tabel(p));
    if (p.tipe === "chart" || p.tipe === "dashboard" || p.tipe === "dataset") {
      const label = p.tipe === "dashboard" ? t("Dashboard") : p.tipe === "dataset" ? t("Dataset") : p.disimpan ? t("Chart") : t("Pratinjau chart");
      const a = document.createElement("a");
      a.className = "tautan-ai"; a.href = "/app/?p=" + encodeURIComponent(p.url);
      a.innerHTML = `${ik({dashboard: "dashboard", dataset: "tabel"}[p.tipe] || "chart", 16)}${esc(label)}: ${esc(p.judul)}`;
      a.onclick = e => { e.preventDefault(); SPS.buka(p.url); };
      wadah.appendChild(a);
      if (p.id && (p.tipe === "dashboard" || (p.tipe === "chart" && p.disimpan))) {        // simpan hasil AI sebagai berkas .ald/.aldx
        const b = document.createElement("a");
        const alamat = `/berkas/?jenis=${p.tipe}&id=${p.id}`;
        b.className = "tautan-ai"; b.href = "/app/?p=" + encodeURIComponent(alamat);
        b.innerHTML = `${ik("simpan", 16)}${esc(t("Simpan sebagai berkas .ald / .aldx"))}`;
        b.onclick = e => { e.preventDefault(); SPS.buka(alamat); };
        wadah.appendChild(b);
      }
    }
    if (p.tipe === "saran") wadah.insertAdjacentHTML("beforeend",
      `<div class="langkah-ai"><span>${esc(p.saran.length + " " + t("saran chart ditemukan (Asisten AI › Auto Chart)"))}</span></div>` +
      (p.wawasan || []).map(w => `<div class="wawasan-ai">${esc(w)}</div>`).join(""));
    if (p.tipe === "usulan") kartuUsulan(p);
  }

  // ---------------- Sambungkan AI ----------------
  const PANDUAN = "/panduan/28-sambungkan-asisten-ai";
  let tabSambung = "lokal";

  async function layarSambung(segarkan) {
    $("#panelAi").classList.add("mode-sambung");
    $("#obrolanAi").innerHTML = `<div class="pesan-ai memuat"><span class="titik"><i></i><i></i><i></i></span> ${esc(t("Memeriksa model AI…"))}</div>`;
    let d;
    try {
      const r = await fetch(`/asisten/api/sambungan${segarkan ? "?segarkan=1" : ""}`, {credentials: "same-origin"});
      d = await r.json();
      if (!r.ok) throw new Error(d.error || r.status);
    } catch (e) { $("#obrolanAi").innerHTML = `<div class="galat-ai">${esc(e.message)}</div>`; return; }

    const adaModel = d.model.length > 0;
    const hidup = d.lokal.filter(x => x.aktif);
    const kartuLokal = d.lokal.map(x => {
      const p = x.langkah ? x : null;
      const siapPakai = x.aktif && x.model.length;
      const status = !x.aktif ? `<span class="lencana">${esc(t("belum menyala"))}</span>`
        : x.model.length ? `<span class="lencana ok">${esc(t("siap"))} · ${x.model.length} model</span>`
        : `<span class="lencana peringatan">${esc(t("menyala, belum ada model"))}</span>`;
      const isi = siapPakai
        ? `<div class="model-temuan">${x.model.map(m => `<code>${esc(m)}</code>`).join("")}</div>`
        : p ? `<ol>${p.langkah.map(l => Array.isArray(l)
            ? `<li>${esc(t(l[0]))}<span class="perintah"><code>${esc(l[1])}</code><button type="button" data-salin="${esc(l[1])}">${esc(t("Salin"))}</button></span></li>`
            : `<li>${esc(t(l))}</li>`).join("")}</ol>` : "";
      const buka = (!hidup.length && x.nama === "Ollama") || (x.aktif && !x.model.length) || siapPakai;
      return `<details class="kartu-sambung" ${buka ? "open" : ""}>
        <summary><b>${esc(x.nama)}</b><small>port ${esc(x.port)}</small>${status}</summary>${isi}
        ${p && !siapPakai ? `<a class="tautan" href="${p.unduh}" target="_blank" rel="noopener">${esc(t("Unduh"))} ${esc(x.nama)} ↗</a>` : ""}</details>`;
    }).join("");

    const kartuCloud = kat => d.cloud.filter(c => c.kategori === kat).map(c => `
      <div class="kartu-sambung">
        <div class="kepala"><b>${esc(c.layanan)}</b>${c.terisi ? `<span class="lencana ok">${esc(t("tersambung"))}${c.samar ? ` · ${esc(c.samar)}` : ""}</span>` : ""}</div>
        <small class="redup">${c.model.map(esc).join(" · ")}</small>
        ${d.boleh_atur ? (c.sumber === "env" ? `<small class="redup">${esc(t("Diatur di berkas .env server."))}</small>` : `
        <form class="isi-key" data-env="${esc(c.env)}">
          <input type="password" autocomplete="off" spellcheck="false" placeholder="${esc(c.terisi ? t("Ganti key…") : t("Tempel key di sini"))}" aria-label="API key ${esc(c.layanan)}">
          <button class="tombol utama" type="submit">${esc(t("Simpan"))}</button>
          ${c.terisi ? `<button class="tombol" type="button" data-hapus="${esc(c.env)}">${esc(t("Hapus"))}</button>` : ""}
        </form>`) : ""}
        ${c.url_key && !c.terisi ? `<a class="tautan" href="${esc(c.url_key)}" target="_blank" rel="noopener">${esc(t("Buat key"))} ↗</a>` : ""}
      </div>`).join("");

    const tab = (id, label) => `<button type="button" role="tab" aria-selected="${tabSambung === id}" class="${tabSambung === id ? "aktif" : ""}" data-tab="${id}">${esc(t(label))}</button>`;
    const isiTab = {
      lokal: `<p class="redup">${esc(t("Gratis, data tidak keluar dari kantor. Pasang salah satu di komputer server ini; semua model yang sudah diunduh terdeteksi otomatis."))}</p>${kartuLokal}`,
      gratis: `<p class="redup">${esc(t("Kuota harian gratis, cukup daftar & buat key. Angka hasil query tidak dikirim ke layanan cloud."))}</p>${kartuCloud("gratis")}`,
      berbayar: `<p class="redup">${esc(t("Kualitas terbaik, dibayar per pemakaian. Isi saldo di penyedia, lalu tempel key-nya."))}</p>${kartuCloud("berbayar")}`,
    };
    $("#obrolanAi").innerHTML = `<div class="sambung-ai">
      <div class="sapa-ai rapat"><div class="ikon-bulat">${ik("sambung", 22)}</div>
        <b>${esc(adaModel ? t("Sambungan AI") : t("Sambungkan Asisten AI"))}</b>
        <p>${esc(adaModel ? `${d.model.length} ${t("model siap dipakai.")}` : d.boleh_atur
          ? t("Belum ada model AI. Pilih satu cara di bawah, bisa diganti kapan saja.")
          : t("Belum ada model AI. Admin dapat menyambungkannya; langkahnya ada di bawah."))}</p></div>
      <div class="tab-sambung" role="tablist">${tab("lokal", "Lokal")}${tab("gratis", "Cloud gratis")}${tab("berbayar", "Cloud berbayar")}</div>
      <div class="isi-sambung">${isiTab[tabSambung]}</div>
      <div class="aksi-sambung">
        <button class="tombol" type="button" id="periksaAi">${ik("segarkan", 16)} ${esc(t("Periksa lagi"))}</button>
        ${adaModel ? `<button class="tombol utama" type="button" id="mulaiAi">${esc(t("Mulai bertanya"))}</button>` : ""}
        <a class="tautan" href="${PANDUAN}" target="_blank" rel="noopener">${esc(t("Panduan lengkap"))} ↗</a>
        ${d.boleh_atur ? `<a class="tautan" href="/pusat-kendali/?tab=ai" target="_blank" rel="noopener">${esc(t("Pusat Kendali"))} ↗</a>` : ""}
      </div></div>`;

    const o = $("#obrolanAi");
    o.querySelectorAll("[data-tab]").forEach(b => b.onclick = () => { tabSambung = b.dataset.tab; layarSambung(); });
    o.querySelectorAll("[data-salin]").forEach(b => b.onclick = () => navigator.clipboard.writeText(b.dataset.salin).then(() => SPS.notif(t("Tersalin"))));
    $("#periksaAi").onclick = () => segarSambungan();
    if ($("#mulaiAi")) $("#mulaiAi").onclick = keluarSambung;
    o.querySelectorAll("form.isi-key").forEach(f => f.onsubmit = e => {
      e.preventDefault();
      const key = f.querySelector("input").value.trim();
      if (key) simpanKey(f.dataset.env, key, f.querySelector("button[type=submit]"));
    });
    o.querySelectorAll("[data-hapus]").forEach(b => b.onclick = () => simpanKey(b.dataset.hapus, "", b));
  }

  async function simpanKey(env, key, tombol) {
    tombol.disabled = true;
    const label = tombol.textContent;
    tombol.textContent = key ? t("Menguji…") : t("Menghapus…");
    try {
      const r = await fetch("/asisten/api/sambungan", {method: "POST", credentials: "same-origin",
        headers: {"Content-Type": "application/json", "X-CSRFToken": AWAL.csrf}, body: JSON.stringify({env, key})});
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j.error || r.status);
      SPS.notif(key ? t("Key tersimpan dan diterima penyedia.") : t("Key dihapus."));
      await segarSambungan();
    } catch (e) {
      SPS.notif(e.message);
      tombol.disabled = false; tombol.textContent = label;
    }
  }

  async function segarSambungan() {
    siap = null;
    const sebelum = model.length;
    await layarSambung(true);
    await muat();
    if (!sebelum && model.length) SPS.notif(t("Asisten AI tersambung."));
  }

  function keluarSambung() {
    $("#panelAi").classList.remove("mode-sambung");
    riwayat = [];
    gambarPeran();
    $("#masukanAi").focus();
  }

  // Halaman yang sedang dibuka: alamat, judul, dan teks yang tampil (dari bingkai, satu origin; maks 4.000 huruf).
  // Server hanya meneruskan teks ke model yang boleh menerima data (kirim_data).
  function konteksHalaman() {
    const k = SPS.halaman ? {...SPS.halaman()} : {};
    try {
      const f = document.querySelector("iframe#bingkai, .isi iframe");
      const dok = f && !f.hidden && f.contentDocument;
      const sumber = dok ? dok.body : document.querySelector("#beranda");
      if (sumber) k.teks = (sumber.innerText || "").replace(/\n{3,}/g, "\n\n").slice(0, 4000);
    } catch (e) { /* halaman lain origin: cukup alamat & judul */ }
    return k;
  }

  // ---------------- Kirim ----------------
  async function kirim(teks) {
    teks = String(teks || "").trim();
    if (!teks || sibuk) return;
    const m = teks.match(/^\/([\w-]+)\s*/);
    if (m && peran(m[1])) { pilihPeran(m[1], true); teks = teks.slice(m[0].length).trim(); if (!teks) return; }
    if (!model.length) { layarSambung(); return; }
    if (!riwayat.length) $("#obrolanAi").innerHTML = "";
    $("#masukanAi").value = ""; ukurMasukan(); tutupSaran();
    const p = peran(peranAktif);
    gelembung("saya", `${riwayat.length && riwayat.peranTerakhir === peranAktif ? "" : `<span class="label-peran">${esc(p.perintah)}</span>`}${esc(teks)}`);
    riwayat.peranTerakhir = peranAktif;
    riwayat.push({role: "user", content: teks});
    const tunggu = gelembung("ai memuat", `<span class="titik"><i></i><i></i><i></i></span> ${esc(t("Berpikir…"))}`);
    sibuk = true; $("#kirimAi").disabled = true;
    try {
      const r = await fetch("/asisten/api/chat", {method: "POST", credentials: "same-origin",
        headers: {"Content-Type": "application/json", "X-CSRFToken": AWAL.csrf},
        body: JSON.stringify({riwayat, model: $("#modelAi").value, peran: peranAktif, konteks: konteksHalaman()})});
      // Bukan JSON = permintaan diputus di tengah jalan (biasanya model terlalu lama, atau server dimulai ulang).
      const j = await r.json().catch(() => ({error: [502, 503, 504].includes(r.status)
        ? t("Server memutus permintaan karena model AI terlalu lama menjawab. Pakai model yang lebih cepat atau pecah permintaan menjadi langkah lebih kecil.")
        : `${t("Jawaban server tidak terbaca")} (HTTP ${r.status})`}));
      tunggu.remove();
      if (!r.ok) throw new Error(j.error || r.status);
      const wadah = gelembung("ai", "");
      (j.peristiwa || []).filter(x => x.tipe === "langkah").forEach(x => tampilPeristiwa(x, wadah));
      wadah.insertAdjacentHTML("beforeend", `<div class="teks-ai">${md(j.jawaban)}</div>`);
      (j.peristiwa || []).filter(x => x.tipe !== "langkah").forEach(x => tampilPeristiwa(x, wadah));
      wadah.querySelectorAll(".salin-kode").forEach(b => b.onclick = () => navigator.clipboard.writeText(b.previousElementSibling.textContent).then(() => SPS.notif(t("Tersalin"))));
      riwayat.push({role: "assistant", content: j.jawaban || ""});
    } catch (e) {
      tunggu.remove();
      gelembung("galat", esc(e.message));
      riwayat.pop();
    }
    sibuk = false; $("#kirimAi").disabled = false; $("#obrolanAi").scrollTop = 1e9;
  }

  // ---------------- Saran perintah "/" ----------------
  let sorot = 0;
  function saranTampil() {
    const v = $("#masukanAi").value;
    const m = v.match(/^\/([\w-]*)$/);
    if (!m) return tutupSaran();
    const cocok = daftarPeran.filter(p => p.id.startsWith(m[1].toLowerCase()) || t(p.nama).toLowerCase().includes(m[1].toLowerCase()));
    if (!cocok.length) return tutupSaran();
    sorot = Math.min(sorot, cocok.length - 1);
    const s = $("#saranPerintah");
    s.innerHTML = cocok.map((p, i) => `<button type="button" class="${i === sorot ? "sorot" : ""}" data-pilih="${p.id}">${ik(p.ikon, 16)}<b>${esc(p.perintah)}</b><span>${esc(t(p.nama))} · ${esc(t(p.ringkas))}</span></button>`).join("");
    s.classList.add("tampil");
    s.querySelectorAll("[data-pilih]").forEach(b => b.onmousedown = e => { e.preventDefault(); terimaSaran(b.dataset.pilih); });
  }
  function terimaSaran(id) { pilihPeran(id, true); $("#masukanAi").value = ""; tutupSaran(); $("#masukanAi").focus(); }
  function tutupSaran() { $("#saranPerintah").classList.remove("tampil"); sorot = 0; }
  function ukurMasukan() { const m = $("#masukanAi"); m.style.height = "auto"; m.style.height = Math.min(160, m.scrollHeight) + "px"; }

  // ---------------- Buka / tutup ----------------
  async function buka(pertanyaan) {
    document.body.classList.add("ai-buka");
    $("#panelAi").setAttribute("aria-hidden", "false");
    $("#bukaAi").classList.add("aktif");
    if (!(await muat())) { $("#obrolanAi").innerHTML = `<div class="galat-ai">${esc(t("Asisten AI belum bisa dihubungi."))}</div>`; return; }
    if (!riwayat.length && !peranDipilih) peranAktif = peranUntukHalaman();
    gambarPeran();
    if (!model.length) return layarSambung();
    if (pertanyaan) kirim(pertanyaan); else setTimeout(() => $("#masukanAi").focus(), 60);
  }
  function tutup() {
    document.body.classList.remove("ai-buka");
    $("#panelAi").setAttribute("aria-hidden", "true");
    $("#bukaAi").classList.remove("aktif");
  }
  const terbuka = () => document.body.classList.contains("ai-buka");
  function baru() { $("#panelAi").classList.remove("mode-sambung"); riwayat = []; peranDipilih = false; peranAktif = peranUntukHalaman(); gambarPeran(); $("#masukanAi").focus(); }

  function pasang() {
    $("#bukaAi").innerHTML = ik("ai");
    $("#bukaAi").hidden = false;
    $("#tutupAi").innerHTML = ik("tutup");
    $("#baruAi").innerHTML = ik("tambah");
    $("#sambungAi").innerHTML = ik("sambung");
    $("#sambungAi").onclick = () => ($("#panelAi").classList.contains("mode-sambung") && model.length ? keluarSambung() : layarSambung());
    $("#kirimAi").innerHTML = ik("kirim", 18);
    $("#ikonJudulAi").innerHTML = ik("ai", 18);
    $("#masukanAi").placeholder = t("Tanya, atau ketik / untuk memilih peran…");   // textarea dilewati penerjemah DOM
    $("#bukaAi").onclick = () => (terbuka() ? tutup() : buka());
    $("#tutupAi").onclick = tutup;
    $("#baruAi").onclick = baru;
    $("#modelAi").onchange = infoModel;
    $("#formAi").onsubmit = e => { e.preventDefault(); kirim($("#masukanAi").value); };
    const m = $("#masukanAi");
    m.addEventListener("input", () => { ukurMasukan(); saranTampil(); });
    m.addEventListener("keydown", e => {
      const s = $("#saranPerintah"), ada = s.classList.contains("tampil"), pilihan = [...s.querySelectorAll("[data-pilih]")];
      if (ada && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
        e.preventDefault(); sorot = (sorot + (e.key === "ArrowDown" ? 1 : -1) + pilihan.length) % pilihan.length; saranTampil(); return;
      }
      if (ada && (e.key === "Enter" || e.key === "Tab")) { e.preventDefault(); terimaSaran(pilihan[sorot].dataset.pilih); return; }
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); kirim(m.value); }
      if (e.key === "Escape") { e.stopPropagation(); ada ? tutupSaran() : tutup(); }
    });
  }

  SPS.ai = {buka, tutup, sambungkan: () => buka().then(() => layarSambung()), alih: () => (terbuka() ? tutup() : buka()), tanya: q => buka(q)};
  SPS.siapAi = () => { if (SPS.bisa("Asisten AI")) pasang(); };
})();
