// ALDx App — label kesegaran data di bilah atas saat sebuah dashboard dibuka.
//
//   "Data: 2 jam lalu"  = data di ALDx Engine (ekstrak/impor) yang paling lama diperbarui 2 jam lalu
//   "Data langsung"     = semua chart membaca database sumber langsung (selalu terbaru)
//   Arahkan kursor ke label untuk rincian per dataset; klik membuka halaman Jejak data.
//   Dihitung server (/jejak-data/api/segar, sps_jejak.kesegaran): hanya dataset yang boleh diakses pengguna.
(function () {
  "use strict";
  const SPS = window.SPS, tombol = document.getElementById("bukaTelusur");
  if (!tombol) return;
  const {t} = SPS.i18n;
  const SEHARI = 86400;

  const chip = document.createElement("button");
  chip.type = "button"; chip.className = "chip-fg chip-segar hanya-lebar"; chip.hidden = true;
  tombol.before(chip);
  chip.onclick = () => SPS.buka("/jejak-data/");

  function usia(detik) {
    if (detik < 90) return t("baru saja");
    if (detik < 5400) return `${Math.round(detik / 60)} ${t("menit lalu")}`;
    if (detik < 2 * SEHARI) return `${Math.round(detik / 3600)} ${t("jam lalu")}`;
    return `${Math.round(detik / SEHARI)} ${t("hari lalu")}`;
  }
  function rincian(r) {
    if (r.jenis === "langsung") return `${r.dataset}: ${t("langsung dari sumber (selalu terbaru)")}`;
    if (r.jenis === "engine" && !r.selesai) return `${r.dataset}: ${t("tabel ALDx Engine (tanpa jadwal penyegaran)")}`;
    return `${r.dataset}: ${t("diperbarui")} ${r.selesai}` + (r.berikutnya ? `, ${t("berikutnya")} ${r.berikutnya}` : "") +
      (r.status === "gagal" ? ` (${t("penyegaran terakhir GAGAL")})` : "");
  }

  let nomor = 0;
  async function segarkan() {
    const h = SPS.halaman && SPS.halaman(), m = h && (h.alamat || "").match(/^\/superset\/dashboard\/([^/?#]+)/);
    const urutan = ++nomor;
    if (!m) { chip.hidden = true; return; }
    let j = null;
    try { j = await (await fetch("/jejak-data/api/segar?dashboard=" + encodeURIComponent(decodeURIComponent(m[1])), {credentials: "same-origin"})).json(); }
    catch (e) { /* tanpa label */ }
    if (urutan !== nomor) return;                          // pengguna sudah pindah halaman
    if (!j || j.error || !j.rincian.length) { chip.hidden = true; return; }
    chip.textContent = j.usia_detik == null ? t("Data langsung") : `${t("Data")}: ${usia(j.usia_detik)}`;
    chip.classList.toggle("lama", j.gagal || (j.usia_detik || 0) > 2 * SEHARI);
    chip.title = j.rincian.map(rincian).join("\n");
    chip.hidden = false;
  }
  window.addEventListener("sps:halaman", segarkan);
  segarkan();
})();
