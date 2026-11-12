/* =============================================================================
   Studio Visual — fungsi bersama (dipakai lembar.js, dasbor.js, prep.js)
   Semua modul menempel pada objek global Studio.
   ============================================================================= */
"use strict";

const Studio = {
  awal: null,            // data /api/awal: dataset, aturan tanda, warna, izin, daftar lembar & dashboard
  saatMulai: [],         // fungsi tiap modul yang dipanggil setelah data awal siap
  csrf: document.body.dataset.csrf,
};

/* ---------- Utilitas DOM & teks ---------- */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const fmtPenuh = new Intl.NumberFormat("id-ID", {maximumFractionDigits: 2});
const fmtRingkas = new Intl.NumberFormat("id-ID", {notation: "compact", maximumFractionDigits: 1});
const angka = v => typeof v === "number" && isFinite(v);
const tampilNilai = v => angka(v) ? fmtPenuh.format(v) : (v ?? "–");

Studio.tunda = (fungsi, ms = 250) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fungsi(...a), ms); }; };

/* ---------- API (CSRF otomatis) ---------- */
Studio.api = async (url, data) => {
  const opsi = data === undefined ? {} : {method: "POST", body: JSON.stringify(data),
    headers: {"Content-Type": "application/json", "X-CSRFToken": Studio.csrf}};
  const r = await fetch(url, opsi);
  const j = await r.json().catch(() => ({error: `Jawaban server tidak terbaca (${r.status})`}));
  if (!r.ok) throw new Error(j.error || `Error ${r.status}`);
  return j;
};

/* ---------- Notifikasi ---------- */
Studio.notif = (html, galat = false) => {
  const n = $("#notif");
  n.innerHTML = html; n.className = "notif" + (galat ? " galat" : ""); n.style.display = "block";
  clearTimeout(Studio._notifT);
  Studio._notifT = setTimeout(() => { n.style.display = "none"; }, galat ? 7000 : 5000);
};

/* ---------- Menu kecil (klik pil) ---------- */
Studio.menu = (x, y, item) => {
  Studio.tutupMenu();
  const m = document.createElement("div");
  m.className = "menu"; m.id = "menuAktif";
  item.forEach(i => {
    if (i === "-") { m.appendChild(document.createElement("hr")); return; }
    const b = document.createElement("button");
    b.textContent = i.label; if (i.pilih) b.className = "pilih";
    b.onclick = () => { Studio.tutupMenu(); i.aksi(); };
    m.appendChild(b);
  });
  document.body.appendChild(m);
  m.style.left = Math.min(x, innerWidth - m.offsetWidth - 8) + "px";
  m.style.top = Math.min(y, innerHeight - m.offsetHeight - 8) + "px";
  setTimeout(() => document.addEventListener("click", Studio.tutupMenu, {once: true}), 0);
};
Studio.tutupMenu = () => $("#menuAktif")?.remove();

/* ---------- Dialog ---------- */
Studio.dialog = ({judul, isi, ok = "Terapkan", padaOk}) => {
  $("#dialog").innerHTML = `<h3>${esc(judul)}</h3><div class="isi">${isi}</div>
    <div class="kaki"><button class="kedua" id="dlgBatal">Batal</button><button class="utama" id="dlgOk">${esc(ok)}</button></div>`;
  $("#latar").classList.add("tampil");
  $("#dlgBatal").onclick = Studio.tutupDialog;
  $("#dlgOk").onclick = () => { if (padaOk() !== false) Studio.tutupDialog(); };
};
Studio.tutupDialog = () => $("#latar").classList.remove("tampil");
$("#latar").addEventListener("click", e => { if (e.target.id === "latar") Studio.tutupDialog(); });
document.addEventListener("keydown", e => { if (e.key === "Escape") { Studio.tutupDialog(); Studio.tutupMenu(); } });

/* ---------- Tabel data sederhana ---------- */
// skala = daftar kolom ukuran yang selnya diberi latar makin pekat untuk nilai makin besar (skala warna tabel).
Studio.tabelHtml = (kolom, baris, maks = 500, skala = null) => {
  const tampil = baris.slice(0, maks), rentang = {};
  (skala || []).forEach(k => {
    const v = tampil.map(b => b[k]).filter(angka);
    if (v.length) rentang[k] = [Math.min(...v), Math.max(...v)];
  });
  const latar = (k, v) => {
    const r = rentang[k];
    if (!r || !angka(v)) return "";
    const a = r[1] === r[0] ? 0.4 : 0.06 + 0.5 * (v - r[0]) / (r[1] - r[0]);
    return ` style="background:rgba(225,29,116,${a.toFixed(3)})"`;
  };
  return `<table class="data"><tr>${kolom.map(k => `<th>${esc(k)}</th>`).join("")}</tr>` +
    tampil.map(b => "<tr>" + kolom.map(k => angka(b[k])
      ? `<td class="n"${latar(k, b[k])}>${fmtPenuh.format(b[k])}</td>` : `<td>${esc(b[k])}</td>`).join("") + "</tr>").join("") + "</table>";
};

/* ---------- Tab ---------- */
$$("nav.tab button").forEach(b => b.onclick = () => {
  $$("nav.tab button, section").forEach(x => x.classList.remove("aktif"));
  b.classList.add("aktif"); $("#" + b.dataset.tab).classList.add("aktif");
  window.dispatchEvent(new CustomEvent("tab", {detail: b.dataset.tab}));
  window.dispatchEvent(new Event("resize"));            // grafik menyesuaikan ukuran
});

/* ---------- Mulai ---------- */
Studio.muatAwal = async () => { Studio.awal = await Studio.api("/studio/api/awal"); return Studio.awal; };

// Dataset baru (mis. dataset virtual dari Kueri Visual / SQL Lab) langsung muncul tanpa memuat ulang:
// saat halaman kembali dibuka/difokuskan, daftar dataset diambil ulang dan pilihan dataset diperbarui.
Studio.segarkanDataset = async () => {
  if (!Studio.awal) return;
  let baru;
  try { baru = (await Studio.api("/studio/api/awal")).dataset; } catch (e) { return; }
  const lama = Studio.awal.dataset.map(d => d.id).join(), kini = baru.map(d => d.id).join();
  if (lama === kini) return;
  Studio.awal.dataset = baru;
  document.querySelectorAll("#pilihDataset, #prepDataset").forEach(sel => {
    const nilai = sel.value;
    sel.innerHTML = baru.map(d => `<option value="${d.id}">${String(d.nama).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]))}</option>`).join("");
    if (baru.some(d => String(d.id) === nilai)) sel.value = nilai;
  });
};
window.addEventListener("focus", () => Studio.segarkanDataset());
document.addEventListener("visibilitychange", () => { if (!document.hidden) Studio.segarkanDataset(); });
window.addEventListener("load", async () => {
  try { await Studio.muatAwal(); } catch (e) { Studio.notif(esc(e.message), true); return; }
  Studio.saatMulai.forEach(f => f());
});
