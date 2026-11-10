// Tab "Asisten AI" di Pusat Kendali (/pusat-kendali/?tab=ai). Dimuat oleh sps_server/halaman.html.
// Memakai helper halaman itu: $, esc, api, CSRF. Data dari /asisten/api/sambungan (sama dengan panel ✦).
//   - Ringkasan: model aktif, aplikasi lokal yang menyala, key cloud terisi, model bawaan
//   - Model aktif: Uji (waktu jawab) & Jadikan bawaan untuk semua pengguna
//   - Model lokal: Ollama / LM Studio / Jan / llama.cpp terdeteksi otomatis + cara memasang
//   - Cloud gratis & berbayar: tempel key -> diuji ke penyedia -> disimpan terenkripsi (tanpa restart)
(function () {
  "use strict";
  const el = () => $("#ai");
  const PANDUAN = "/panduan/28-sambungkan-asisten-ai";
  const lencana = (kelas, teks) => `<span class="st ${kelas}">${esc(teks)}</span>`;

  function langkah(x) {
    if (!x.langkah) return "";
    return `<details><summary class="ket" style="cursor:pointer">Cara memasang</summary><ol class="ket" style="margin:6px 0 0;padding-left:18px">${
      x.langkah.map(l => Array.isArray(l) ? `<li>${esc(l[0])} <code>${esc(l[1])}</code></li>` : `<li>${esc(l)}</li>`).join("")}</ol>
      ${x.unduh ? `<a href="${esc(x.unduh)}" target="_blank" rel="noopener" class="ket">Unduh ${esc(x.nama)} ↗</a>` : ""}</details>`;
  }

  function tabelCloud(d, kat) {
    const baris = d.cloud.filter(c => c.kategori === kat).map(c => `<tr>
      <td><b>${esc(c.layanan)}</b><div class="ket">${c.model.map(esc).join(" · ")}</div></td>
      <td>${c.terisi ? lencana("siap", `tersambung ${c.samar || ""}`) : lencana("baru", "belum diisi")}</td>
      <td style="min-width:320px">${c.sumber === "env" ? `<span class="ket">Diatur di berkas .env server</span>` : `
        <form class="aiKey" data-env="${esc(c.env)}" style="display:flex;gap:6px">
          <input type="text" autocomplete="off" spellcheck="false" placeholder="${c.terisi ? "Ganti key…" : "Tempel key di sini"}"
                 style="font-family:ui-monospace,Consolas,monospace;-webkit-text-security:disc" aria-label="API key ${esc(c.layanan)}">
          <button class="utama" type="submit">Simpan</button>
          ${c.terisi ? `<button class="kedua" type="button" data-hapus="${esc(c.env)}">Hapus</button>` : ""}
        </form>`}</td>
      <td>${c.url_key ? `<a href="${esc(c.url_key)}" target="_blank" rel="noopener">Buat key ↗</a>` : ""}</td></tr>`).join("");
    return `<table><tr><th>Layanan</th><th>Status</th><th>API key</th><th></th></tr>${baris}</table>`;
  }

  async function gambar(segarkan) {
    el().innerHTML = `<div class="kartu ket">Memeriksa model AI…</div>`;
    let d;
    try { d = await api("/asisten/api/sambungan" + (segarkan ? "?segarkan=1" : "")); }
    catch (e) { el().innerHTML = `<div class="kartu galat">${esc(e.message)}</div>`; return; }
    const hidup = d.lokal.filter(x => x.aktif).length, terisi = d.cloud.filter(c => c.terisi).length;
    const bawaan = d.model.find(m => m.id === d.bawaan);

    el().innerHTML = `
      <div class="kartu ket">Asisten AI butuh minimal satu model. <b>Lokal</b> = gratis & data tidak keluar kantor (dipasang di
        Windows komputer server, terdeteksi otomatis). <b>Cloud</b> = cukup tempel key; angka hasil query tidak dikirim.
        Semua perubahan berlaku tanpa restart. Panduan: <a href="${PANDUAN}">Menyambungkan Asisten AI</a>.</div>
      <div class="kpi">
        ${kpi("Model aktif", d.model.length, d.model.length ? "siap dipakai pengguna" : "belum ada: pilih jalur di bawah")}
        ${kpi("Aplikasi lokal menyala", `${hidup} / ${d.lokal.length}`, "Ollama, LM Studio, Jan, llama.cpp")}
        ${kpi("Key cloud terisi", `${terisi} / ${d.cloud.length}`, "gratis & berbayar")}
        ${kpi("Model bawaan", bawaan ? `<span style="font-size:15px;line-height:1.3;display:block;overflow-wrap:anywhere" title="${esc(bawaan.nama)}">${esc(bawaan.nama.split(" — ")[0])}</span>` : "–", bawaan ? (bawaan.jalur === "lokal" ? "lokal" : "cloud") : "")}
      </div>
      <div style="display:flex;gap:8px;margin-bottom:6px"><button class="kedua" id="aiPeriksa" type="button">Periksa lagi</button>
        <span class="ket" id="aiPesan" style="align-self:center"></span></div>

      <h2>Model aktif</h2>
      <div class="kartu" style="overflow:auto">${d.model.length ? `<table><tr><th>Model</th><th>Jalur</th><th>Data ke model</th><th>Uji</th><th></th></tr>${
        d.model.map(m => `<tr><td><b>${esc(m.nama)}</b>${m.id === d.bawaan ? ` ${lencana("baru", "bawaan")}` : ""}</td>
          <td>${m.jalur === "lokal" ? "Lokal" : "Cloud"}</td>
          <td class="ket">${m.kirim_data ? "angka boleh dianalisis" : "hanya nama kolom (privasi)"}</td>
          <td><button class="kecil" data-uji="${esc(m.id)}" type="button">Uji</button> <span class="ket" data-hasil="${esc(m.id)}"></span></td>
          <td>${m.id !== d.bawaan && d.boleh_atur ? `<button class="kecil" data-bawaan="${esc(m.id)}" type="button">Jadikan bawaan</button>` : ""}</td></tr>`).join("")}</table>`
        : `<span class="ket">Belum ada model aktif. Pasang model lokal atau isi key cloud di bawah.</span>`}</div>

      <h2>Model lokal (terdeteksi otomatis)</h2>
      <div class="kartu" style="overflow:auto"><table><tr><th>Aplikasi</th><th>Status</th><th>Model yang sudah diunduh</th><th></th></tr>${
        d.lokal.map(x => `<tr><td><b>${esc(x.nama)}</b><div class="ket">port ${esc(x.port)}</div></td>
          <td>${!x.aktif ? lencana("baru", "belum menyala") : x.model.length ? lencana("siap", "siap") : lencana("berjalan", "menyala, belum ada model")}</td>
          <td>${x.model.length ? x.model.map(m => `<code>${esc(m)}</code>`).join(" ") : "<span class='ket'>–</span>"}</td>
          <td>${x.aktif && x.model.length ? "" : langkah(x)}</td></tr>`).join("")}</table></div>

      <h2>Cloud gratis <span class="ket">kuota harian</span></h2>
      <div class="kartu" style="overflow:auto">${tabelCloud(d, "gratis")}</div>
      <h2>Cloud berbayar <span class="ket">per pemakaian</span></h2>
      <div class="kartu" style="overflow:auto">${tabelCloud(d, "berbayar")}</div>`;

    const pesan = (t, ok) => { const p = $("#aiPesan"); p.textContent = t; p.className = ok ? "sukses" : "galat"; };
    $("#aiPeriksa").onclick = () => gambar(true);
    el().querySelectorAll("[data-uji]").forEach(b => b.onclick = async () => {
      const h = el().querySelector(`[data-hasil="${CSS.escape(b.dataset.uji)}"]`);
      b.disabled = true; h.textContent = "menunggu jawaban…"; h.className = "ket";
      try { const j = await api("/asisten/api/uji", {model: b.dataset.uji}); h.textContent = `✓ ${j.detik.toLocaleString("id-ID")} dtk`; h.className = "sukses"; }
      catch (e) { h.textContent = e.message; h.className = "galat"; }
      b.disabled = false;
    });
    el().querySelectorAll("[data-bawaan]").forEach(b => b.onclick = async () => {
      try { await api("/asisten/api/bawaan", {model: b.dataset.bawaan}); gambar(); }
      catch (e) { pesan(e.message, false); }
    });
    el().querySelectorAll("form.aiKey").forEach(f => f.onsubmit = async e => {
      e.preventDefault();
      const key = f.querySelector("input").value.trim(), tombol = f.querySelector("button[type=submit]");
      if (!key) return;
      tombol.disabled = true; tombol.textContent = "Menguji…";
      try { await api("/asisten/api/sambungan", {env: f.dataset.env, key}); await gambar(true); pesan("Key tersimpan dan diterima penyedia.", true); }
      catch (err) { pesan(err.message, false); tombol.disabled = false; tombol.textContent = "Simpan"; }
    });
    el().querySelectorAll("[data-hapus]").forEach(b => b.onclick = async () => {
      if (!confirm("Hapus key ini? Model dari layanan ini tidak bisa dipakai lagi.")) return;
      try { await api("/asisten/api/sambungan", {env: b.dataset.hapus, key: ""}); await gambar(true); pesan("Key dihapus.", true); }
      catch (err) { pesan(err.message, false); }
    });
  }

  window.muatAi = () => gambar();
})();
