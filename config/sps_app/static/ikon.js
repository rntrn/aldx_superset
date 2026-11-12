// Ikon garis 24x24 buatan sendiri (stroke = currentColor). Pakai: SPS.ikon("rumah")
(function () {
  "use strict";
  const P = {
    rumah: "M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z",
    telusur: "M4 4h7v7H4zM13 13h7v7h-7zM11 7.5h4.5a2 2 0 0 1 2 2V13M15 10.5l2.5 2.5 2.5-2.5",
    sambung: "M9 7H7a5 5 0 0 0 0 10h2M15 7h2a5 5 0 0 1 0 10h-2M8 12h8",
    tabel: "M3 5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM3 9h18M3 15h18M9 9v12",
    siapkan: "M4 6h10M4 12h16M4 18h7M17 4v4M14 6h6M14 16l2 2 4-4",
    ekstrak: "M12 3v12m0 0-4-4m4 4 4-4M5 21h14",
    kueri: "M4 5h16M4 10h10M4 15h7M16 15l2 2 3-4",
    sql: "M8 8 4 12l4 4M16 8l4 4-4 4M13.5 5l-3 14",
    simpan: "M6 3h10l4 4v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zM8 3v5h7M8 21v-7h8v7",
    studio: "M3 21V10M9 21V4M15 21v-8M21 21V8",
    chart: "M4 20V10m6 10V4m6 16v-7m4 7H2",
    dashboard: "M3 3h8v10H3zM13 3h8v6h-8zM13 11h8v10h-8zM3 15h8v6H3z",
    story: "M4 5h16v11H4zM8 20h8M12 16v4M10 8.5v4l3.5-2z",
    ai: "M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8zM19 15l.9 2.1 2.1.9-2.1.9L19 21l-.9-2.1L16 18l2.1-.9z",
    kelola: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z",
    pengguna: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8",
    kunci: "M5 11h14v10H5zM8 11V7a4 4 0 0 1 8 0v4",
    riwayat: "M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5M12 7v5l3 2",
    server: "M4 4h16v6H4zM4 14h16v6H4zM8 7h.01M8 17h.01",
    cari: "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3",
    bantuan: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01",
    bahasa: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18",
    keluar: "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9",
    tutup: "M18 6 6 18M6 6l12 12",
    menu: "M4 6h16M4 12h16M4 18h16",
    lipat: "M15 18l-6-6 6-6",
    kanan: "M9 18l6-6-6-6",
    bukaTab: "M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6",
    segarkan: "M21 12a9 9 0 1 1-2.6-6.4L21 8M21 3v5h-5",
    tambah: "M12 5v14M5 12h14",
    corong: "M3 4h18l-7 8.5V19l-4 2v-8.5z",
    komentar: "M4 5h16v11H9l-5 4z",
    bulan: "M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z",
    bintang: "M12 3l2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3 6.4 20.2l1.1-6.2L3 9.6l6.2-.9z",
    pintasan: "M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM7 9h.01M11 9h.01M15 9h.01M7 13h.01M17 13h.01M9 15h6",
    lainnya: "M5 12h.01M12 12h.01M19 12h.01",
    kirim: "M22 2 11 13M22 2l-7 20-4-9-9-4z",
    centang: "M5 12l5 5L20 7",
  };
  window.SPS = window.SPS || {};
  window.SPS.ikon = (nama, ukuran = 20) =>
    `<svg class="ikon" width="${ukuran}" height="${ukuran}" viewBox="0 0 24 24" fill="none" stroke="currentColor" ` +
    `stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${P[nama] || P.lainnya}"/></svg>`;
})();
