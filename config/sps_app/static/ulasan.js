// ALDx App — Komentar & rating (tombol komentar di bilah atas, muncul saat dashboard / chart dibuka).
//
//   Data: /ulasan/api/<dashboard|chart>/<id>  (config/sps_ulasan). Hak akses objek dicek server.
//   Bila moderasi aktif, ulasan baru berstatus "menunggu" sampai disetujui Superadmin (Kelola › Moderasi ulasan).
//   Balasan (satu tingkat) & @sebut: ketik "@" lalu nama untuk memilih orang; ia mendapat pemberitahuan.
(function () {
  "use strict";
  const SPS = window.SPS, $ = s => document.querySelector(s);
  const {t} = SPS.i18n, ik = SPS.ikon, AWAL = window.SPS_AWAL;
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const tombol = $("#bukaUlasan");
  if (!tombol) return;
  tombol.innerHTML = ik("komentar", 18);

  const panel = document.createElement("div");
  panel.className = "panel-fg panel-ulasan"; panel.hidden = true;
  panel.setAttribute("role", "dialog"); panel.setAttribute("aria-label", t("Komentar & rating"));
  document.body.appendChild(panel);

  let objek = null, nilai = 0, induk = null;

  // Dashboard / chart yang sedang dibuka di bingkai.
  function kenali(alamat) {
    const u = new URL(alamat || "/", location.origin);
    let m = u.pathname.match(/^\/superset\/dashboard\/([^/]+)\/?$/);
    if (m) return {jenis: "dashboard", kunci: decodeURIComponent(m[1])};
    if (/^\/explore\/?$/.test(u.pathname) && /^\d+$/.test(u.searchParams.get("slice_id") || "")) return {jenis: "chart", kunci: u.searchParams.get("slice_id")};
    return null;
  }
  function perbarui(alamat) {
    objek = kenali(alamat);
    tombol.hidden = !objek;
    if (!objek) tutup();
  }

  const bintang = (n, besar) => [1, 2, 3, 4, 5].map(i =>
    `<span class="bintang${i <= Math.round(n || 0) ? " isi" : ""}${besar ? " besar" : ""}" data-nilai="${i}">★</span>`).join("");
  const STATUS = {menunggu: "menunggu persetujuan", ditolak: "ditolak"};

  async function buka() {
    if (!objek) return;
    panel.hidden = false;
    panel.innerHTML = `<p class="bantu-fg">${esc(t("Memuat..."))}</p>`;
    const r = await fetch(`/ulasan/api/${objek.jenis}/${encodeURIComponent(objek.kunci)}`, {credentials: "same-origin"});
    const d = await r.json().catch(() => ({}));
    if (!r.ok) { panel.innerHTML = `<p class="bantu-fg">${esc(d.error || t("Gagal memuat"))}</p>`; return; }
    nilai = 0; induk = null;
    panel.innerHTML = `<div class="kepala-fg"><b>${esc(t("Komentar & rating"))}</b>` +
      `<span class="rata-ulasan">${d.rata ? bintang(d.rata) + ` <b>${d.rata.toLocaleString("id-ID")}</b>` : ""} ` +
      `<small>${d.jumlah} ${esc(t("rating"))}</small></span></div>` +
      `<div class="tulis-ulasan"><div class="pilih-bintang" aria-label="${esc(t("Beri bintang"))}">${bintang(0, true)}</div>` +
      `<div class="membalas" hidden></div>` +
      `<textarea id="teksUlasan" rows="3" maxlength="2000" placeholder="${esc(t("Tulis komentar (opsional). Ketik @ untuk menyebut seseorang."))}"></textarea>` +
      `<div class="saran-sebut" hidden></div>` +
      `<div class="aksi-fg">${d.moderasi && !d.superadmin ? `<small class="bantu-fg">${esc(t("Tampil setelah disetujui Superadmin."))}</small>` : ""}` +
      `<button type="button" class="tombol utama" id="kirimUlasan">${esc(t("Kirim"))}</button></div></div>` +
      `<div class="daftar-ulasan">${susun(d).join("") || `<p class="bantu-fg">${esc(t("Belum ada komentar. Jadilah yang pertama."))}</p>`}</div>`;
  }

  // Komentar utama (terbaru dulu) dengan balasannya di bawahnya (terlama dulu).
  function susun(d) {
    const semua = d.ulasan || [], balasan = {};
    semua.filter(u => u.induk_id).forEach(u => (balasan[u.induk_id] = balasan[u.induk_id] || []).unshift(u));
    return semua.filter(u => !u.induk_id).map(u => kartu(u, d, false) +
      (balasan[u.id] || []).map(b => kartu(b, d, true)).join(""));
  }
  const sorotSebut = teks => esc(teks).replace(/(^|[^\w@])@([\w.\-]+(?:@[\w.\-]+\.\w+)?)/g, '$1<b class="sebut">@$2</b>');
  function kartu(u, d, balasan) {
    return `<div class="ulasan${balasan ? " balasan" : ""}" data-id="${u.id}" data-nama="${esc(u.nama || u.pengguna)}" data-pengguna="${esc(u.pengguna)}">` +
      `<div><b>${esc(u.nama || u.pengguna)}</b> ${u.nilai ? `<span class="kecil-bintang">${bintang(u.nilai)}</span>` : ""}` +
      `<small> · ${esc(new Date(u.dibuat + "Z").toLocaleDateString("id-ID"))}</small>` +
      (u.status !== "tampil" ? ` <span class="status-ulasan ${u.status}">${esc(t(STATUS[u.status]))}</span>` : "") +
      ((u.pengguna === d.saya || d.superadmin) ? ` <button type="button" class="hapus-ulasan" title="${esc(t("Hapus"))}">${ik("tutup", 14)}</button>` : "") +
      `</div>${u.teks ? `<p>${sorotSebut(u.teks)}</p>` : ""}${u.status === "ditolak" && u.alasan ? `<small class="bantu-fg">${esc(t("Alasan"))}: ${esc(u.alasan)}</small>` : ""}` +
      (!balasan && u.status === "tampil" ? `<button type="button" class="balas-ulasan">${esc(t("Balas"))}</button>` : "") + `</div>`;
  }

  // Saran @sebut saat mengetik.
  let tundaSebut = null;
  async function saranSebut(area) {
    const sebelum = area.value.slice(0, area.selectionStart), m = sebelum.match(/@([\w.\-]*)$/);
    const kotak = panel.querySelector(".saran-sebut");
    if (!m || !m[1]) { kotak.hidden = true; return; }
    const daftar = await (await fetch(`/ulasan/api/pengguna?q=${encodeURIComponent(m[1])}`, {credentials: "same-origin"})).json().catch(() => []);
    kotak.innerHTML = daftar.map(p => `<button type="button" data-username="${esc(p.username)}">${esc(p.nama || p.username)} <small>@${esc(p.username)}</small></button>`).join("");
    kotak.hidden = !daftar.length;
  }

  function tutup() { panel.hidden = true; }

  panel.addEventListener("click", async e => {
    const b = e.target.closest(".pilih-bintang .bintang");
    if (b) {
      nilai = Number(b.dataset.nilai);
      panel.querySelectorAll(".pilih-bintang .bintang").forEach(x => x.classList.toggle("isi", Number(x.dataset.nilai) <= nilai));
      return;
    }
    if (e.target.closest("#kirimUlasan")) {
      const teks = $("#teksUlasan").value.trim();
      if (!teks && !nilai) return SPS.notif ? SPS.notif(t("Tulis komentar atau beri bintang")) : null;
      const r = await fetch(`/ulasan/api/${objek.jenis}/${encodeURIComponent(objek.kunci)}`, {method: "POST", credentials: "same-origin",
        headers: {"Content-Type": "application/json", "X-CSRFToken": AWAL.csrf}, body: JSON.stringify({teks, nilai: nilai || null, induk_id: induk})});
      if (r.ok) buka();
      else if (SPS.notif) SPS.notif(((await r.json().catch(() => ({}))).error) || t("Gagal mengirim"));
      return;
    }
    const bl = e.target.closest(".balas-ulasan");
    if (bl) {
      const k = bl.closest(".ulasan"); induk = Number(k.dataset.id);
      const m = panel.querySelector(".membalas");
      m.innerHTML = `${esc(t("Membalas"))} <b>${esc(k.dataset.nama)}</b> <button type="button" class="batal-balas" aria-label="${esc(t("Batal"))}">${ik("tutup", 12)}</button>`;
      m.hidden = false;
      const area = $("#teksUlasan"); area.focus();
      return;
    }
    if (e.target.closest(".batal-balas")) { induk = null; panel.querySelector(".membalas").hidden = true; return; }
    const sb = e.target.closest(".saran-sebut [data-username]");
    if (sb) {
      const area = $("#teksUlasan"), pos = area.selectionStart;
      const sebelum = area.value.slice(0, pos).replace(/@([\w.\-]*)$/, "@" + sb.dataset.username + " ");
      area.value = sebelum + area.value.slice(pos); area.focus();
      area.selectionStart = area.selectionEnd = sebelum.length;
      panel.querySelector(".saran-sebut").hidden = true;
      return;
    }
    const h = e.target.closest(".hapus-ulasan");
    if (h) {
      const id = h.closest(".ulasan").dataset.id;
      const r = await fetch(`/ulasan/api/item/${id}`, {method: "DELETE", credentials: "same-origin", headers: {"X-CSRFToken": AWAL.csrf}});
      if (r.ok) buka();
    }
  });
  panel.addEventListener("input", e => {
    if (e.target.id === "teksUlasan") { clearTimeout(tundaSebut); tundaSebut = setTimeout(() => saranSebut(e.target), 200); }
  });
  tombol.addEventListener("click", () => (panel.hidden ? buka() : tutup()));
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !panel.hidden) tutup(); });
  document.addEventListener("click", e => { if (!panel.hidden && e.target.isConnected && !panel.contains(e.target) && !tombol.contains(e.target)) tutup(); });
  window.addEventListener("message", e => { if (e.origin === location.origin && e.data && e.data.sps === "rute") perbarui(e.data.alamat); });
  perbarui(SPS.halaman ? SPS.halaman().alamat : location.pathname);
})();
