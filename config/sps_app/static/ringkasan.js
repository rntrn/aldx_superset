// ALDx App — Ringkasan AI otomatis saat dashboard dibuka (server: sps_ai/ringkasan.py).
//
//   Chip "✦ Ringkasan AI" di bilah atas: berdenyut saat dibuat, lalu klik = kartu 3-5 poin berangka
//   + "Perlu perhatian". Tombol: Perbarui (buat ulang), Tanya lanjut (panel Asisten AI).
//   ai.yaml ringkasan_dashboard: otomatis (dibuat saat dibuka) | klik (dibuat saat chip diklik) | mati (chip tidak tampil).
//   Chip hanya tampil bagi pengguna yang boleh memakai Asisten AI (tombol ✦ tampil).
(function () {
  "use strict";
  const SPS = window.SPS, tombol = document.getElementById("bukaTelusur");
  if (!tombol) return;
  const {t} = SPS.i18n;
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const JEDA_MS = 4000, MAKS_TANYA = 150;                  // tanya status tiap 4 detik, paling lama ±10 menit

  const chip = document.createElement("button");
  chip.type = "button"; chip.className = "chip-fg chip-ringkas hanya-lebar"; chip.hidden = true;
  chip.title = t("Ringkasan AI dashboard ini");
  tombol.before(chip);
  const kartu = document.createElement("div");
  kartu.className = "kartu-ringkas"; kartu.hidden = true; kartu.setAttribute("role", "dialog");
  document.body.append(kartu);

  let nomor = 0, tanya = 0, kunci = null, keadaan = {status: "klik"}, pengatur = null;

  const aktifAi = () => { const b = document.getElementById("bukaAi"); return b && !b.hidden; };
  function gambarChip() {
    const s = keadaan.status;
    chip.classList.toggle("sibuk", s === "jalan");
    chip.classList.toggle("siap", s === "selesai");
    chip.textContent = "✦ " + (s === "jalan" ? t("Meringkas…") : t("Ringkasan AI"));
  }
  function gambarKartu() {
    const s = keadaan;
    const isi = s.status === "selesai"
      ? `<ul>${s.poin.map(p => `<li class="${/^perlu perhatian/i.test(p) ? "perhatian" : ""}">${esc(p)}</li>`).join("")}</ul>
         <div class="ket-ringkas">${esc(s.model)} · ${esc(s.dibuat)} · ${esc(t("angka mengikuti hak akses Anda, tanpa filter dashboard"))}</div>`
      : s.status === "jalan" ? `<p class="ket-ringkas">${esc(t("AI sedang membaca angka tiap chart…"))}</p>`
      : s.status === "gagal" ? `<p class="galat-ringkas">${esc(t(s.galat || "Ringkasan gagal dibuat."))}</p>`
      : `<p class="ket-ringkas">${esc(t("Klik Buat ringkasan untuk meminta AI meringkas dashboard ini."))}</p>`;
    kartu.innerHTML = `<div class="judul-ringkas"><b>✦ ${esc(t("Ringkasan AI"))}</b><button type="button" class="tutup-ringkas" aria-label="${esc(t("Tutup"))}">×</button></div>${isi}
      <div class="aksi-ringkas">
        <button type="button" class="tombol" data-aksi="segar" ${s.status === "jalan" ? "disabled" : ""}>${esc(t(s.status === "klik" ? "Buat ringkasan" : "Perbarui"))}</button>
        <button type="button" class="tombol" data-aksi="tanya">${esc(t("Tanya lanjut"))}</button></div>`;
    kartu.querySelector(".tutup-ringkas").onclick = () => { kartu.hidden = true; };
    kartu.querySelector('[data-aksi="segar"]').onclick = () => ambil(s.status === "klik" ? "" : "segar=1");
    kartu.querySelector('[data-aksi="tanya"]').onclick = () => {
      kartu.hidden = true;
      if (SPS.ai) SPS.ai.tanya(t("Apa yang janggal atau perlu ditindaklanjuti di dashboard ini?"));
    };
  }
  function letakkanKartu() {
    const r = chip.getBoundingClientRect();
    kartu.style.top = `${r.bottom + 8}px`;
    kartu.style.right = `${Math.max(12, innerWidth - r.right)}px`;
  }
  async function ambil(param) {
    const urutan = nomor;
    clearTimeout(pengatur);
    if (param) tanya = 0;
    let j;
    try {
      const r = await fetch(`/asisten/api/ringkasan/${encodeURIComponent(kunci)}?${param}`, {credentials: "same-origin"});
      j = await r.json();
      if (!r.ok) j = {status: r.status === 403 ? "mati" : "gagal", galat: j.error};
    } catch (e) { j = {status: "gagal", galat: "Ringkasan tidak bisa diambil (jaringan)."}; }
    if (urutan !== nomor) return;                          // pengguna sudah pindah dashboard
    keadaan = j;
    if (j.status === "mati") { chip.hidden = true; kartu.hidden = true; return; }
    chip.hidden = false; gambarChip();
    if (!kartu.hidden) gambarKartu();
    if (j.status === "jalan" && ++tanya < MAKS_TANYA) pengatur = setTimeout(() => ambil(""), JEDA_MS);
  }
  chip.onclick = () => {
    if (!kartu.hidden) { kartu.hidden = true; return; }
    gambarKartu(); letakkanKartu(); kartu.hidden = false;
  };
  document.addEventListener("keydown", e => { if (e.key === "Escape") kartu.hidden = true; });
  document.addEventListener("click", e => { if (!kartu.hidden && !kartu.contains(e.target) && e.target !== chip) kartu.hidden = true; });

  function halamanBerubah() {
    const h = SPS.halaman && SPS.halaman(), m = h && (h.alamat || "").match(/^\/superset\/dashboard\/([^/?#]+)/);
    nomor++; clearTimeout(pengatur); kartu.hidden = true;
    if (!m || !aktifAi()) { chip.hidden = true; kunci = null; return; }
    kunci = decodeURIComponent(m[1]); keadaan = {status: "klik"};
    ambil("auto=1");
  }
  window.addEventListener("sps:halaman", halamanBerubah);
  // tombol ✦ baru tampil setelah hak akses AI diketahui: tunggu sebentar sebelum keputusan pertama
  setTimeout(halamanBerubah, 1200);
})();
