/* =============================================================================
   Studio Visual — perender grafik (ECharts lokal)

   Studio.gambar(el, hasil, tanda, opsi)
     hasil : {kolom, baris, dimensi: [nama], ukuran: [label]}  dari /studio/api/kueri
     tanda : kunci ATURAN_TANDA (lembar.py), mis. batang, treemap, peta_titik
     opsi  : {horizontal, label, mini}
     kembali: {catatan} bila ada yang perlu diberitahukan (mis. provinsi tak dikenal)

   Peta memakai GeoJSON provinsi Indonesia lokal (static/indonesia.geojson): tanpa internet.

   Aturan visual: warna dibagikan menurut urutan kemunculan (sama seperti Superset, jadi
   pratinjau = hasil di dashboard), slot tetap & tidak diputar; seri ke-9 dst. abu-abu;
   satu sumbu nilai; garis tipis; legenda bila >= 2 seri.
   ============================================================================= */
"use strict";

(() => {
  const ABU = "#9AA5B1", TEKS = "#5F6B7A", GARIS = "#E6EBF1", SUMBU = "#D5DCE4";
  const RUNTUN = ["#EAF1FB", "#7FA3DE", "#2a5bb8", "#1F2F5F"];        // = skema djpBiru di Superset
  const instans = new Set();
  window.addEventListener("resize", Studio.tunda(() => instans.forEach(c => c.resize()), 120));

  const warna = (nama, semua) => {
    const urut = [...new Set(semua.map(String))];
    const i = urut.indexOf(String(nama));
    return i >= 0 && i < Studio.awal.warna.length ? Studio.awal.warna[i] : ABU;
  };
  const unik = arr => [...new Set(arr)];
  const urutNilai = (a, b) => (angka(a) && angka(b)) ? a - b : String(a).localeCompare(String(b), "id", {numeric: true});

  const dasar = mini => ({
    animationDuration: 250,
    textStyle: {fontFamily: "'Plus Jakarta Sans','Segoe UI',Arial,sans-serif", color: TEKS, fontSize: mini ? 10 : 12},
    grid: {left: 8, right: 16, top: mini ? 10 : 34, bottom: 8, containLabel: true},
    tooltip: {confine: true, valueFormatter: v => tampilNilai(v),
              backgroundColor: "#fff", borderColor: SUMBU, textStyle: {color: "#1F2933"}},
  });
  const sumbuNilai = () => ({type: "value", axisLabel: {formatter: v => fmtRingkas.format(v)},
                             splitLine: {lineStyle: {color: GARIS}}, axisLine: {show: false}});
  const sumbuKategori = data => ({type: "category", data, axisLine: {lineStyle: {color: SUMBU}},
                                  axisTick: {show: false}, axisLabel: {hideOverlap: true}});
  const legenda = (n, mini) => n >= 2 ? {type: "scroll", top: 0, icon: "roundRect", itemWidth: 12, itemHeight: 8,
                                          show: !mini || n <= 4} : {show: false};

  function pakaiEcharts(el, option) {
    let c = echarts.getInstanceByDom(el);
    if (!c) {                      // isi lama (pesan/tabel) dibersihkan HANYA sebelum ECharts dipasang
      el.innerHTML = "";
      c = echarts.init(el, null, {renderer: "svg"}); instans.add(c);
    }
    c.setOption(option, true);
    return c;
  }
  Studio.hapusGrafik = el => hapusEcharts(el);
  function hapusEcharts(el) {
    const c = echarts.getInstanceByDom(el);
    if (c) { instans.delete(c); c.dispose(); }
  }

  /* ---------- Batang / garis / area ---------- */
  function seri(hasil, tanda, opsi) {
    const [dx, dw] = hasil.dimensi, uk = hasil.ukuran;
    const an = !dw && hasil.analitik ? hasil.analitik : null;      // ramalan/tren/anomali (prediksi.py)
    let kategori = unik(hasil.baris.map(b => b[dx]));
    if (an) kategori = [...an.x];
    else if (tanda !== "batang") kategori = kategori.sort(urutNilai);
    const posisi = new Map(kategori.map((k, i) => [k, i]));
    const kosong = () => kategori.map(() => null);
    const seriData = {};
    if (dw) {                                                  // warna = dimensi kedua -> seri per nilai
      hasil.baris.forEach(b => {
        const s = (seriData[b[dw]] ??= kosong());
        s[posisi.get(b[dx])] = (s[posisi.get(b[dx])] || 0) + (b[uk[0]] ?? 0);
      });
    } else {
      uk.forEach(u => { seriData[u] = kosong(); });
      hasil.baris.forEach(b => uk.forEach(u => { seriData[u][posisi.get(b[dx])] = b[u]; }));
    }
    const nama = Object.keys(seriData);
    const persen = opsi.persen;
    if (persen) {                                              // batang 100%: tiap kategori dijumlah = 100
      kategori.forEach((_, i) => {
        const total = nama.reduce((a, n) => a + (seriData[n][i] || 0), 0) || 1;
        nama.forEach(n => { if (seriData[n][i] != null) seriData[n][i] = seriData[n][i] / total * 100; });
      });
    }
    const tumpuk = Boolean(dw) && tanda !== "garis";
    const series = nama.map(n => {
      const s = {name: n, data: seriData[n], itemStyle: {color: warna(n, nama)},
                 label: {show: opsi.label, formatter: p => persen ? Math.round(p.value) + "%" : fmtRingkas.format(p.value),
                         position: tumpuk ? "inside" : (opsi.horizontal ? "right" : "top"), fontSize: 10}};
      if (tanda === "batang") {
        Object.assign(s, {type: "bar", barMaxWidth: 44, barGap: "8%", stack: tumpuk ? "t" : undefined});
        s.itemStyle.borderRadius = tumpuk ? 0 : (opsi.horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]);
        if (tumpuk) Object.assign(s.itemStyle, {borderColor: "#fff", borderWidth: 1});
      } else {
        Object.assign(s, {type: "line", lineStyle: {width: 2}, symbol: "circle", symbolSize: 7,
                          showSymbol: kategori.length <= 24, stack: tumpuk ? "t" : undefined});
        if (tanda === "area") s.areaStyle = {opacity: tumpuk ? 0.85 : 0.25};
      }
      return s;
    });
    if (an) tambahAnalitik(series, an, kategori.length, nama, opsi);
    const sumbuK = sumbuKategori([...kategori, ...(an ? an.x_ramalan : [])].map(String)), sumbuN = sumbuNilai();
    if (persen) Object.assign(sumbuN, {max: 100, axisLabel: {formatter: v => v + "%"}});
    const tampak = series.filter(x => !x.name.startsWith("_")).map(x => x.name);
    const o = {...dasar(opsi.mini), legend: {...legenda(tampak.length, opsi.mini), data: tampak}, series,
               tooltip: {...dasar().tooltip, trigger: "axis", axisPointer: {type: tanda === "batang" ? "shadow" : "line"},
                         ...(persen ? {valueFormatter: v => v == null ? "–" : fmtPenuh.format(v) + "%"} : {}),
                         ...(an ? {formatter: ps => tooltipAnalitik(ps, an, kategori.length)} : {})}};
    if (opsi.horizontal && tanda === "batang") { sumbuK.inverse = true; o.yAxis = sumbuK; o.xAxis = sumbuN; }
    else { o.xAxis = sumbuK; o.yAxis = sumbuN; }
    if (kategori.length > 40 && !opsi.mini) {
      o.dataZoom = [{type: "inside", [opsi.horizontal ? "yAxisIndex" : "xAxisIndex"]: 0}];
    }
    return o;
  }

  /* ---------- Analitik: ramalan + pita keyakinan, garis tren, anomali ----------
     Seri bantu bernama "_..." (pita) disembunyikan dari legenda & tooltip. */
  const MERAH = "#e34948";
  function tambahAnalitik(series, an, n, nama, opsi) {
    const h = an.x_ramalan.length, pad = Array(h).fill(null);
    series.forEach(s => { s.data = [...s.data, ...pad]; });
    nama.forEach(u => {
      const a = an.seri[u] || {}, w = warna(u, nama), asli = series.find(x => x.name === u).data;
      const akhir = asli[n - 1];
      if (a.ramalan) {
        const r = a.ramalan, depan = Array(n - 1).fill(null);
        const pita = (bawah, atas, kode, op) => [
          {name: `_${kode}b ${u}`, type: "line", data: [...depan, akhir, ...bawah], stack: `${kode}${u}`, symbol: "none",
           lineStyle: {opacity: 0}, silent: true, z: 1},
          {name: `_${kode}a ${u}`, type: "line", data: [...depan, 0, ...atas.map((v, i) => v - bawah[i])], stack: `${kode}${u}`,
           symbol: "none", lineStyle: {opacity: 0}, areaStyle: {color: w, opacity: op}, silent: true, z: 1}];
        series.push(...pita(r.bawah95, r.atas95, "p95", 0.10), ...pita(r.bawah80, r.atas80, "p80", 0.16),
          {name: `Ramalan ${u}`, type: "line", data: [...depan, akhir, ...r.nilai], symbol: "circle", symbolSize: 5,
           itemStyle: {color: w}, lineStyle: {width: 2, type: "dashed", color: w}, z: 3});
      }
      if (a.tren) {
        series.push({name: `Tren ${u}`, type: "line", data: [...a.tren.nilai, ...pad], symbol: "none", z: 2,
                     itemStyle: {color: w}, lineStyle: {width: 1.5, type: "dotted", color: w, opacity: 0.9}});
      }
      if (a.anomali?.length) {
        const titik = Array(n + h).fill(null);
        a.anomali.forEach(x => { titik[x.i] = x.nilai; });
        series.push({name: `Anomali ${u}`, type: "scatter", data: titik, symbolSize: opsi.mini ? 7 : 11, z: 4,
                     itemStyle: {color: MERAH, borderColor: "#fff", borderWidth: 1.5}});
      }
    });
  }
  function tooltipAnalitik(ps, an, n) {
    const i = ps[0].dataIndex, ramalan = i >= n;
    let html = `<b>${esc(ps[0].axisValueLabel)}</b>${ramalan ? ' <span style="color:#8A6D00">ramalan</span>' : ""}`;
    ps.filter(p => !p.seriesName.startsWith("_") && p.value != null && !(ramalan && !p.seriesName.startsWith("Ramalan"))).forEach(p => {
      html += `<br>${p.marker}${esc(p.seriesName)}: <b>${tampilNilai(p.value)}</b>`;
      const u = p.seriesName.replace(/^Ramalan /, ""), r = an.seri[u]?.ramalan;
      if (ramalan && r) html += `<br><span style="color:#5F6B7A">80%: ${tampilNilai(r.bawah80[i - n])} – ${tampilNilai(r.atas80[i - n])}` +
        `<br>95%: ${tampilNilai(r.bawah95[i - n])} – ${tampilNilai(r.atas95[i - n])}</span>`;
    });
    return html;
  }

  /* ---------- Pie ---------- */
  function pie(hasil, opsi) {
    const [d] = hasil.dimensi, [u] = hasil.ukuran;
    let data = hasil.baris.map(b => ({name: String(b[d]), value: b[u]})).sort((a, b) => b.value - a.value);
    if (data.length > 8) {
      const lain = data.slice(7).reduce((s, x) => s + (x.value || 0), 0);
      data = [...data.slice(0, 7), {name: "Lainnya", value: lain}];
    }
    const nama = data.map(x => x.name);
    data.forEach(x => { x.itemStyle = {color: x.name === "Lainnya" ? ABU : warna(x.name, nama.filter(n => n !== "Lainnya"))}; });
    return {...dasar(opsi.mini), tooltip: {...dasar().tooltip, trigger: "item"},
            legend: {...legenda(data.length, opsi.mini), orient: "vertical", right: 0, top: "middle"},
            series: [{type: "pie", radius: ["45%", "72%"], center: ["40%", "52%"], data,
                      itemStyle: {borderColor: "#fff", borderWidth: 2},
                      label: {show: !opsi.mini, formatter: "{b}\n{d}%", fontSize: 11}}]};
  }

  /* ---------- Sebar ---------- */
  function sebar(hasil, opsi) {
    const [d] = hasil.dimensi, [ux, uy, us] = hasil.ukuran;
    const besar = us ? Math.max(...hasil.baris.map(b => b[us] || 0)) || 1 : 1;
    return {...dasar(opsi.mini),
      tooltip: {...dasar().tooltip, trigger: "item",
                formatter: p => `<b>${esc(p.data[3])}</b><br>${esc(ux)}: ${tampilNilai(p.data[0])}<br>${esc(uy)}: ${tampilNilai(p.data[1])}` +
                                (us ? `<br>${esc(us)}: ${tampilNilai(p.data[2])}` : "")},
      xAxis: {...sumbuNilai(), name: ux, nameLocation: "middle", nameGap: 26, scale: true},
      yAxis: {...sumbuNilai(), name: uy, scale: true},
      series: [{type: "scatter", data: hasil.baris.map(b => [b[ux], b[uy], us ? b[us] : null, b[d]]),
                symbolSize: v => us ? 8 + 30 * Math.sqrt((v[2] || 0) / besar) : 10,
                itemStyle: {color: Studio.awal.warna[0], opacity: 0.8, borderColor: "#fff", borderWidth: 2},
                label: {show: opsi.label, formatter: p => p.data[3], position: "right", fontSize: 10}}]};
  }

  /* ---------- Peta panas ---------- */
  function petaPanas(hasil, opsi) {
    const [dx, dy] = hasil.dimensi, [u] = hasil.ukuran;
    const xs = unik(hasil.baris.map(b => b[dx])).sort(urutNilai), ys = unik(hasil.baris.map(b => b[dy])).sort(urutNilai);
    const nilai = hasil.baris.map(b => b[u]).filter(angka);
    return {...dasar(opsi.mini), grid: {...dasar(opsi.mini).grid, bottom: opsi.mini ? 8 : 48},
      tooltip: {...dasar().tooltip, trigger: "item",
                formatter: p => `${esc(xs[p.data[0]])} · ${esc(ys[p.data[1]])}<br><b>${tampilNilai(p.data[2])}</b>`},
      xAxis: sumbuKategori(xs.map(String)), yAxis: sumbuKategori(ys.map(String)),
      visualMap: {min: Math.min(...nilai), max: Math.max(...nilai), calculable: false, orient: "horizontal",
                  left: "center", bottom: 0, show: !opsi.mini, itemHeight: 120, itemWidth: 10,
                  inRange: {color: RUNTUN}, formatter: v => fmtRingkas.format(v)},
      series: [{type: "heatmap", data: hasil.baris.map(b => [xs.indexOf(b[dx]), ys.indexOf(b[dy]), b[u]]),
                itemStyle: {borderColor: "#fff", borderWidth: 2, borderRadius: 3},
                label: {show: opsi.label, formatter: p => fmtRingkas.format(p.data[2]), fontSize: 10}}]};
  }

  /* ---------- Angka + tren (garis kecil) ---------- */
  function angkaTren(el, hasil, opsi) {
    const [d] = hasil.dimensi, [u] = hasil.ukuran;
    const titik = hasil.baris.filter(b => b[d] != null).sort((a, b) => urutNilai(a[d], b[d]));
    const akhir = titik.at(-1)?.[u] ?? 0, sebelum = titik.at(-2)?.[u];
    const ubah = angka(sebelum) && sebelum !== 0 ? (akhir - sebelum) / Math.abs(sebelum) : null;
    hapusSemua(el);
    el.innerHTML = `<div class="angkaBesar tren"><div class="nilai" style="${opsi.mini ? "font-size:30px" : ""}"
      title="${esc(tampilNilai(akhir))}">${esc(fmtRingkas.format(akhir))}</div>
      <div class="lbl">${esc(u)} · ${esc(titik.at(-1)?.[d] ?? "")}${ubah == null ? "" :
        ` · <span class="${ubah >= 0 ? "naik" : "turun"}">${ubah >= 0 ? "+" : ""}${(ubah * 100).toLocaleString("id-ID", {maximumFractionDigits: 1})}%</span>`}</div>
      <div class="spark"></div></div>`;
    const c = echarts.init($(".spark", el), null, {renderer: "svg"}); instans.add(c); el._anak = c;
    c.setOption({...dasar(true), grid: {left: 0, right: 0, top: 4, bottom: 0},
      xAxis: {type: "category", show: false, data: titik.map(b => String(b[d]))}, yAxis: {type: "value", show: false, scale: true},
      tooltip: {...dasar().tooltip, trigger: "axis"},
      series: [{type: "line", data: titik.map(b => b[u]), showSymbol: false, lineStyle: {width: 2, color: Studio.awal.warna[0]},
                areaStyle: {color: Studio.awal.warna[0], opacity: 0.12}}]});
  }

  /* ---------- Gauge ---------- */
  const bulatAtas = v => { if (!(v > 0)) return 1; const p = 10 ** Math.floor(Math.log10(v)); return Math.ceil(v / p) * p; };
  function gauge(hasil, opsi) {
    const u = hasil.ukuran[0], v = hasil.baris[0][u] ?? 0;
    return {...dasar(opsi.mini), series: [{type: "gauge", min: 0, max: bulatAtas(v * 1.2), startAngle: 225, endAngle: -45,
      progress: {show: true, width: 14, itemStyle: {color: Studio.awal.warna[0]}}, axisLine: {lineStyle: {width: 14, color: [[1, GARIS]]}},
      pointer: {length: "55%", width: 4, itemStyle: {color: "#1F2F5F"}}, splitLine: {length: 8, lineStyle: {color: SUMBU}},
      axisTick: {show: false}, axisLabel: {formatter: x => fmtRingkas.format(x), color: TEKS, fontSize: 10, distance: 18},
      title: {offsetCenter: [0, "72%"], fontSize: 12, color: TEKS},
      detail: {valueAnimation: true, offsetCenter: [0, "38%"], fontSize: opsi.mini ? 18 : 26, fontWeight: 700, color: "#1F2F5F",
               formatter: x => fmtRingkas.format(x)},
      data: [{value: v, name: u}]}]};
  }

  /* ---------- Tabel pivot ---------- */
  function pivotHtml(hasil) {
    const dimB = hasil.dim_baris?.length ? hasil.dim_baris : hasil.dimensi.slice(0, 1);
    const dimK = hasil.dimensi.filter(d => !dimB.includes(d)), uk = hasil.ukuran;
    const kunci = (b, ds) => ds.map(d => b[d] ?? "–").join(" · ");
    const barisK = unik(hasil.baris.map(b => kunci(b, dimB))).sort(urutNilai).slice(0, 300);
    const kolomK = unik(hasil.baris.map(b => kunci(b, dimK))).sort(urutNilai).slice(0, 40);
    const sel = new Map(), totB = new Map(), totK = new Map(), totAll = {};
    hasil.baris.forEach(b => {
      const rb = kunci(b, dimB), rk = kunci(b, dimK);
      uk.forEach(u => {
        const v = angka(b[u]) ? b[u] : 0, tambah = (m, k) => m.set(k, (m.get(k) || 0) + v);
        tambah(sel, `${rb}|${rk}|${u}`); tambah(totB, `${rb}|${u}`); tambah(totK, `${rk}|${u}`);
        totAll[u] = (totAll[u] || 0) + v;
      });
    });
    const judulK = kolomK.flatMap(k => uk.map(u => `<th class="n">${esc(dimK.length ? k : "")}${uk.length > 1 || !dimK.length ? `<div class="ket">${esc(u)}</div>` : ""}</th>`)).join("");
    const isi = barisK.map(rb => `<tr><td><b>${esc(rb)}</b></td>${kolomK.flatMap(rk => uk.map(u => {
      const v = sel.get(`${rb}|${rk}|${u}`); return `<td class="n">${v == null ? "" : esc(fmtPenuh.format(v))}</td>`; })).join("")}
      ${dimK.length ? uk.map(u => `<td class="n tot">${esc(fmtPenuh.format(totB.get(`${rb}|${u}`) || 0))}</td>`).join("") : ""}</tr>`).join("");
    const kaki = `<tr class="tot"><td>Total</td>${kolomK.flatMap(rk => uk.map(u => `<td class="n">${esc(fmtPenuh.format(totK.get(`${rk}|${u}`) || 0))}</td>`)).join("")}
      ${dimK.length ? uk.map(u => `<td class="n">${esc(fmtPenuh.format(totAll[u] || 0))}</td>`).join("") : ""}</tr>`;
    return `<table class="data pivot"><thead><tr><th>${esc(dimB.join(" · "))}${dimK.length ? `<div class="ket">${esc(dimK.join(" · "))} →</div>` : ""}</th>${judulK}
      ${dimK.length ? uk.map(u => `<th class="n">Total${uk.length > 1 ? `<div class="ket">${esc(u)}</div>` : ""}</th>`).join("") : ""}</tr></thead><tbody>${isi}${kaki}</tbody></table>`;
  }

  /* ---------- Waterfall ---------- */
  function waterfall(hasil, opsi) {
    const [d] = hasil.dimensi, [u] = hasil.ukuran;
    const baris = [...hasil.baris].sort((a, b) => urutNilai(a[d], b[d]));
    let jalan = 0;
    const dasarN = [], naik = [], turun = [];
    baris.forEach(b => {
      const v = b[u] || 0, awal = jalan; jalan += v;
      dasarN.push(Math.min(awal, jalan)); naik.push(v >= 0 ? v : null); turun.push(v < 0 ? -v : null);
    });
    const kat = [...baris.map(b => String(b[d])), "Total"];
    dasarN.push(0); naik.push(null); turun.push(null);
    const total = kat.map((_, i) => i === kat.length - 1 ? jalan : null);
    const bar = (name, data, color) => ({name, type: "bar", stack: "w", data, barMaxWidth: 44, itemStyle: {color},
      label: {show: opsi.label, position: "top", fontSize: 10, formatter: p => p.value == null ? "" : fmtRingkas.format(p.value)}});
    return {...dasar(opsi.mini), legend: {show: false}, xAxis: sumbuKategori(kat), yAxis: sumbuNilai(),
      tooltip: {...dasar().tooltip, trigger: "axis", axisPointer: {type: "shadow"},
                formatter: ps => { const i = ps[0].dataIndex; const v = i === kat.length - 1 ? jalan : baris[i][u];
                  return `<b>${esc(kat[i])}</b><br>${esc(u)}: ${tampilNilai(v)}`; }},
      series: [{type: "bar", stack: "w", data: dasarN, itemStyle: {color: "transparent"}, emphasis: {disabled: true}, tooltip: {show: false}},
               bar("Naik", naik, "#1baf7a"), bar("Turun", turun, "#e34948"), bar("Total", total, Studio.awal.warna[0])]};
  }

  /* ---------- Radar ---------- */
  function radar(hasil, opsi) {
    const [d] = hasil.dimensi, uk = hasil.ukuran, baris = hasil.baris.slice(0, 8);
    const nama = baris.map(b => String(b[d]));
    return {...dasar(opsi.mini), legend: legenda(nama.length, opsi.mini), tooltip: {...dasar().tooltip, trigger: "item"},
      radar: {indicator: uk.map(u => ({name: u, max: bulatAtas(Math.max(...hasil.baris.map(b => b[u] || 0)))})),
              radius: opsi.mini ? "62%" : "66%", center: ["50%", "56%"], axisName: {color: TEKS, fontSize: 11},
              splitLine: {lineStyle: {color: GARIS}}, splitArea: {show: false}, axisLine: {lineStyle: {color: GARIS}}},
      series: [{type: "radar", symbolSize: 4, data: baris.map((b, i) => ({name: nama[i], value: uk.map(u => b[u]),
        itemStyle: {color: warna(nama[i], nama)}, lineStyle: {width: 2}, areaStyle: {opacity: baris.length <= 3 ? 0.12 : 0}}))}]};
  }

  /* ---------- Treemap & sunburst (hierarki) ---------- */
  function pohon(hasil) {
    const dims = hasil.dimensi, [u] = hasil.ukuran, akar = new Map();
    hasil.baris.forEach(b => {
      let level = akar;
      dims.forEach((d, i) => {
        const k = String(b[d] ?? "–");
        if (!level.has(k)) level.set(k, {name: k, value: 0, anak: new Map()});
        const n = level.get(k); n.value += b[u] || 0; level = n.anak;
      });
    });
    const keArray = m => [...m.values()].sort((a, b) => b.value - a.value)
      .map(n => n.anak.size ? {name: n.name, value: n.value, children: keArray(n.anak)} : {name: n.name, value: n.value});
    const data = keArray(akar), atas = data.map(n => n.name);
    data.forEach(n => { n.itemStyle = {color: warna(n.name, atas)}; });
    return data;
  }
  function treemap(hasil, opsi) {
    return {...dasar(opsi.mini), tooltip: {...dasar().tooltip, trigger: "item"},
      series: [{type: "treemap", data: pohon(hasil), roam: false, nodeClick: false, breadcrumb: {show: false},
        top: 4, left: 4, right: 4, bottom: 4, leafDepth: hasil.dimensi.length > 1 && !opsi.mini ? 2 : null,
        label: {show: true, formatter: p => `${p.name}\n${fmtRingkas.format(p.value)}`, fontSize: 11},
        upperLabel: {show: hasil.dimensi.length > 1, height: 18, color: "#fff", fontSize: 11},
        itemStyle: {borderColor: "#fff", borderWidth: 1, gapWidth: 2},
        levels: [{itemStyle: {borderWidth: 0, gapWidth: 3}}, {colorSaturation: [0.35, 0.6], itemStyle: {gapWidth: 1, borderColorSaturation: 0.7}}]}]};
  }
  function sunburst(hasil, opsi) {
    return {...dasar(opsi.mini), tooltip: {...dasar().tooltip, trigger: "item"},
      series: [{type: "sunburst", data: pohon(hasil), radius: ["12%", "92%"], sort: null,
        itemStyle: {borderColor: "#fff", borderWidth: 1.5},
        label: {show: !opsi.mini, rotate: "radial", fontSize: 10, minAngle: 8},
        levels: [{}, {}, {itemStyle: {opacity: 0.8}}, {itemStyle: {opacity: 0.65}}]}]};
  }

  /* ---------- Corong ---------- */
  function corong(hasil, opsi) {
    const [d] = hasil.dimensi, [u] = hasil.ukuran;
    const data = hasil.baris.map(b => ({name: String(b[d]), value: b[u] || 0})).sort((a, b) => b.value - a.value).slice(0, 12);
    const maks = data[0]?.value || 1, nama = data.map(x => x.name);
    return {...dasar(opsi.mini), tooltip: {...dasar().tooltip, trigger: "item"},
      series: [{type: "funnel", data: data.map(x => ({...x, itemStyle: {color: warna(x.name, nama)}})), sort: "descending",
        left: "10%", width: "80%", top: 8, bottom: 8, gap: 2, minSize: "8%",
        label: {show: true, position: "inside", fontSize: 11, color: "#fff",
                formatter: p => `${p.name}  ${fmtRingkas.format(p.value)} (${Math.round(p.value / maks * 100)}%)`},
        itemStyle: {borderColor: "#fff", borderWidth: 1}}]};
  }

  /* ---------- Awan kata (HTML, tanpa pustaka tambahan) ---------- */
  function awanKata(hasil, opsi) {
    const [d] = hasil.dimensi, [u] = hasil.ukuran;
    const data = hasil.baris.filter(b => b[d] != null).sort((a, b) => (b[u] || 0) - (a[u] || 0)).slice(0, 120);
    const maks = Math.sqrt(data[0]?.[u] || 1), [kecil, besar] = opsi.mini ? [9, 26] : [12, 56];
    const nama = data.slice(0, Studio.awal.warna.length).map(b => String(b[d]));
    const acak = [...data].sort((a, b) => ((String(a[d]).length * 7919) % 13) - ((String(b[d]).length * 7919) % 13));
    return `<div class="awanKata">${acak.map(b => {
      const k = String(b[d]), ukuranH = kecil + (besar - kecil) * Math.sqrt(Math.max(0, b[u] || 0)) / maks;
      return `<span style="font-size:${ukuranH.toFixed(1)}px;color:${nama.includes(k) ? warna(k, nama) : ABU}"
        title="${esc(k)}: ${esc(tampilNilai(b[u]))}">${esc(k)}</span>`; }).join(" ")}</div>`;
  }

  /* ---------- Box plot (Tukey, sama seperti Superset) ---------- */
  const kuantil = (urut, q) => { const pos = (urut.length - 1) * q, b = Math.floor(pos);
    return urut[b + 1] !== undefined ? urut[b] + (pos - b) * (urut[b + 1] - urut[b]) : urut[b]; };
  function boxPlot(hasil, opsi) {
    const [dx] = hasil.dimensi, [u] = hasil.ukuran, grup = new Map();
    hasil.baris.forEach(b => { if (angka(b[u])) (grup.get(b[dx]) ?? grup.set(b[dx], []).get(b[dx])).push(b[u]); });
    const kat = [...grup.keys()].sort(urutNilai), kotak = [], pencilan = [];
    kat.forEach((k, i) => {
      const v = grup.get(k).sort((a, b) => a - b), q1 = kuantil(v, 0.25), q2 = kuantil(v, 0.5), q3 = kuantil(v, 0.75), iqr = q3 - q1;
      const dalam = v.filter(x => x >= q1 - 1.5 * iqr && x <= q3 + 1.5 * iqr);
      kotak.push([dalam[0], q1, q2, q3, dalam.at(-1)]);
      v.filter(x => !dalam.includes(x)).forEach(x => pencilan.push([i, x]));
    });
    return {...dasar(opsi.mini), xAxis: sumbuKategori(kat.map(String)), yAxis: {...sumbuNilai(), scale: true},
      tooltip: {...dasar().tooltip, trigger: "item", formatter: p => p.seriesType === "boxplot"
        ? `<b>${esc(p.name)}</b><br>Maks: ${tampilNilai(p.data[5])}<br>Q3: ${tampilNilai(p.data[4])}<br>Median: ${tampilNilai(p.data[3])}<br>Q1: ${tampilNilai(p.data[2])}<br>Min: ${tampilNilai(p.data[1])}`
        : `<b>${esc(kat[p.data[0]])}</b><br>Pencilan: ${tampilNilai(p.data[1])}`},
      series: [{type: "boxplot", data: kotak, itemStyle: {color: "#EAF1FB", borderColor: Studio.awal.warna[0], borderWidth: 1.5}},
               {type: "scatter", data: pencilan, symbolSize: 6, itemStyle: {color: Studio.awal.warna[3], opacity: 0.8}}]};
  }

  /* ---------- Sankey ---------- */
  function sankey(hasil, opsi) {
    const [ds, dt] = hasil.dimensi, [u] = hasil.ukuran;
    const sumber = unik(hasil.baris.map(b => String(b[ds]))), tujuan = unik(hasil.baris.map(b => String(b[dt])));
    const namaT = t => sumber.includes(t) ? t + "​" : t;      // nama sama di dua sisi tetap dua simpul
    const urut = [...sumber, ...tujuan.map(namaT)];
    return {...dasar(opsi.mini), tooltip: {...dasar().tooltip, trigger: "item"},
      series: [{type: "sankey", left: 8, right: 90, top: 8, bottom: 8, nodeGap: 6, emphasis: {focus: "adjacency"},
        data: urut.map(n => ({name: n, itemStyle: {color: warna(n.replace("​", ""), urut.map(x => x.replace("​", "")))}})),
        links: hasil.baris.filter(b => (b[u] || 0) > 0).map(b => ({source: String(b[ds]), target: namaT(String(b[dt])), value: b[u]})),
        lineStyle: {color: "gradient", opacity: 0.35, curveness: 0.5}, label: {fontSize: 11, color: TEKS}}]};
  }

  /* ---------- Peta (GeoJSON provinsi lokal) ---------- */
  let PROVINSI = null;                  // {kunci huruf kecil (ISO / nama) -> NAME_1}
  const petaSiap = fetch("/studio/static/indonesia.geojson").then(r => r.json()).then(geo => {
    echarts.registerMap("indonesia", geo);
    PROVINSI = {};
    geo.features.forEach(f => {
      const nama = f.properties.NAME_1;
      [f.properties.ISO, nama, f.properties.ISO.replace("ID-", ""), nama.replace(/^(DKI|DI|D\.I\.)\s*/i, "")]
        .forEach(k => { PROVINSI[k.toLowerCase()] = nama; });
    });
  });
  const geoDasar = mini => ({map: "indonesia", roam: !mini, zoom: 1.15, center: [118, -2.5],
    itemStyle: {areaColor: "#F1F4F8", borderColor: "#C9D3DE", borderWidth: 0.6},
    emphasis: {itemStyle: {areaColor: "#E3EAF3"}, label: {show: false}}, label: {show: false}, select: {disabled: true}});

  function petaWilayah(hasil, opsi) {
    const [d] = hasil.dimensi, [u] = hasil.ukuran;
    let lewatNama = 0, tidakDikenal = [];
    const data = hasil.baris.map(b => {
      const k = String(b[d] ?? "").trim().toLowerCase(), nama = PROVINSI[k];
      if (!nama) tidakDikenal.push(b[d]); else if (!/^id-/.test(k)) lewatNama++;
      return nama && {name: nama, value: b[u], asli: b[d]};
    }).filter(Boolean);
    const nilai = data.map(x => x.value).filter(angka);
    const catatan = [tidakDikenal.length && `${tidakDikenal.length} wilayah tidak dikenali`,
      lewatNama && "dicocokkan lewat nama; di Superset pakai kode ISO (mis. ID-JK)"].filter(Boolean).join(" · ");
    return [{...dasar(opsi.mini), tooltip: {...dasar().tooltip, trigger: "item",
        formatter: p => `<b>${esc(p.name)}</b><br>${esc(u)}: ${tampilNilai(p.value)}`},
      visualMap: {min: Math.min(...nilai), max: Math.max(...nilai), left: 8, bottom: 8, show: !opsi.mini, itemHeight: 100, itemWidth: 10,
                  inRange: {color: RUNTUN}, calculable: false, textStyle: {color: TEKS, fontSize: 11},
                  text: [fmtRingkas.format(Math.max(...nilai)), fmtRingkas.format(Math.min(...nilai))]},
      series: [{type: "map", ...geoDasar(opsi.mini), data, nameProperty: "NAME_1"}]}, catatan];
  }

  function petaTitik(hasil, tanda, opsi) {
    const g = hasil.geo || {}, lat = Object.keys(g).find(k => g[k] === "lintang"), lon = Object.keys(g).find(k => g[k] === "bujur");
    const lain = hasil.dimensi.find(x => x !== lat && x !== lon), [u] = hasil.ukuran;
    const titik = hasil.baris.filter(b => angka(+b[lat]) && angka(+b[lon]) && Math.abs(b[lat]) <= 90 && Math.abs(b[lon]) <= 180);
    const o = {...dasar(opsi.mini), geo: geoDasar(opsi.mini), tooltip: {...dasar().tooltip, trigger: "item"}};
    if (tanda === "peta_kepadatan") {
      const nilai = titik.map(b => u ? b[u] || 0 : 1);
      // titik saling menumpuk (intensitas dijumlah), jadi batas atas = beberapa kali nilai rata-rata
      const rata = nilai.reduce((a, b) => a + b, 0) / Math.max(1, nilai.length);
      return [{...o, visualMap: {min: 0, max: rata * Math.max(4, Math.sqrt(nilai.length) / 2), show: false,
                                 inRange: {color: ["rgba(127,163,222,0)", "#7FA3DE", "#2a5bb8", "#1F2F5F"]}},
        series: [{type: "heatmap", coordinateSystem: "geo", pointSize: opsi.mini ? 8 : 14, blurSize: opsi.mini ? 10 : 22,
                  data: titik.map((b, i) => [+b[lon], +b[lat], nilai[i]])}]}, ""];
    }
    const besar = u ? Math.max(...titik.map(b => b[u] || 0)) || 1 : 1;
    const kat = lain ? unik(titik.map(b => String(b[lain]))) : [];
    const kelompok = lain ? kat.slice(0, 9) : ["Titik"];
    const series = kelompok.map(k => ({name: k, type: "scatter", coordinateSystem: "geo",
      data: titik.filter(b => !lain || String(b[lain]) === k || (k === kelompok.at(-1) && kat.indexOf(String(b[lain])) >= 9))
        .map(b => ({value: [+b[lon], +b[lat], u ? b[u] : null], nama: lain ? b[lain] : ""})),
      symbolSize: v => u ? 4 + 22 * Math.sqrt(Math.max(0, v[2] || 0) / besar) : (opsi.mini ? 4 : 6),
      itemStyle: {color: lain ? warna(k, kat) : Studio.awal.warna[0], opacity: 0.75, borderColor: "#fff", borderWidth: 0.6},
      tooltip: {formatter: p => `${p.data.nama ? `<b>${esc(p.data.nama)}</b><br>` : ""}${(+p.value[1]).toFixed(4)}, ${(+p.value[0]).toFixed(4)}` +
                (u ? `<br>${esc(u)}: ${tampilNilai(p.value[2])}` : "")}}));
    const dibuang = hasil.baris.length - titik.length;
    return [{...o, series, legend: legenda(lain ? kelompok.length : 0, opsi.mini)}, dibuang ? `${dibuang} baris tanpa koordinat sah dilewati` : ""];
  }

  /* ---------- Titik masuk ---------- */
  function hapusSemua(el) {
    hapusEcharts(el);
    if (el._anak) { instans.delete(el._anak); el._anak.dispose(); el._anak = null; }
  }
  const HTML = {                                             // jenis yang digambar sebagai HTML biasa
    tabel: h => `<div style="position:absolute;inset:0;overflow:auto">${Studio.tabelHtml(h.kolom, h.baris)}</div>`,
    tabel_pivot: h => `<div style="position:absolute;inset:0;overflow:auto">${pivotHtml(h)}</div>`,
    awan_kata: (h, o) => awanKata(h, o),
  };
  const ECHARTS = {
    batang: (h, o) => seri(h, "batang", o), garis: (h, o) => seri(h, "garis", o), area: (h, o) => seri(h, "area", o),
    batang_100: (h, o) => seri(h, "batang", {...o, persen: true}),
    pie, sebar, peta_panas: petaPanas, gauge, waterfall, radar, treemap, sunburst, funnel: corong,
    box_plot: boxPlot, sankey,
  };
  const PETA = {peta_wilayah: petaWilayah, peta_titik: (h, o) => petaTitik(h, "peta_titik", o),
                peta_kepadatan: (h, o) => petaTitik(h, "peta_kepadatan", o)};

  Studio.gambar = (el, hasil, tanda, opsi = {}) => {
    if (!hasil || !hasil.baris.length) {
      hapusSemua(el);
      el.innerHTML = `<div class="kosongBesar">Tidak ada data untuk pilihan dan filter ini.</div>`;
      return {};
    }
    if (tanda === "angka") {
      hapusSemua(el);
      const u = hasil.ukuran[0];
      el.innerHTML = `<div class="angkaBesar"><div class="nilai" style="${opsi.mini ? "font-size:32px" : ""}"
        title="${esc(tampilNilai(hasil.baris[0][u]))}">${esc(fmtRingkas.format(hasil.baris[0][u] ?? 0))}</div><div class="lbl">${esc(u)}</div></div>`;
      return {};
    }
    if (tanda === "angka_tren") { angkaTren(el, hasil, opsi); return {}; }
    if (HTML[tanda]) { hapusSemua(el); el.innerHTML = HTML[tanda](hasil, opsi); return {}; }
    if (PETA[tanda]) {
      if (!PROVINSI) {                                        // GeoJSON belum termuat: gambar setelah siap
        hapusSemua(el); el.innerHTML = `<div class="kosongBesar">Memuat peta…</div>`;
        petaSiap.then(() => Studio.gambar(el, hasil, tanda, opsi));
        return {};
      }
      if (el._anak) hapusSemua(el);
      const [option, catatan] = PETA[tanda](hasil, opsi);
      pakaiEcharts(el, option);
      return {catatan};
    }
    if (el._anak) hapusSemua(el);
    pakaiEcharts(el, (ECHARTS[tanda] || ECHARTS.batang)(hasil, opsi));
    return {};
  };

  /* Gambar kecil "Tampilkan Saya" (garis tipis, satu warna) */
  Studio.ikonTanda = {
    angka: '<text x="20" y="19" text-anchor="middle" font-size="15" font-weight="700" fill="currentColor">123</text>',
    tabel: '<path d="M6 5h28M6 11h28M6 17h28M6 23h28M16 5v18" stroke="currentColor" stroke-width="1.6" fill="none"/>',
    batang: '<path d="M8 24V14M16 24V6M24 24V11M32 24V17" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>',
    garis: '<path d="M5 21l8-7 7 4 8-10 7 3" stroke="currentColor" stroke-width="2" fill="none" stroke-linejoin="round"/>',
    area: '<path d="M5 24V19l8-6 7 3 8-9 7 3v14z" fill="currentColor" opacity=".55"/>',
    pie: '<circle cx="20" cy="13" r="10" fill="none" stroke="currentColor" stroke-width="5" stroke-dasharray="40 63" opacity=".9"/><circle cx="20" cy="13" r="10" fill="none" stroke="currentColor" stroke-width="5" stroke-dasharray="20 63" stroke-dashoffset="-42" opacity=".45"/>',
    sebar: '<circle cx="10" cy="18" r="2.5" fill="currentColor"/><circle cx="17" cy="11" r="3.5" fill="currentColor"/><circle cx="26" cy="15" r="2.5" fill="currentColor"/><circle cx="31" cy="7" r="4" fill="currentColor"/>',
    angka_tren: '<text x="4" y="12" font-size="10" font-weight="700" fill="currentColor">123</text><path d="M4 22l7-4 6 2 8-7 10-3" stroke="currentColor" stroke-width="1.8" fill="none"/>',
    gauge: '<path d="M7 22a13 13 0 0 1 26 0" stroke="currentColor" stroke-width="4" fill="none" opacity=".3"/><path d="M7 22a13 13 0 0 1 20-11" stroke="currentColor" stroke-width="4" fill="none"/><path d="M20 22l6-8" stroke="currentColor" stroke-width="2"/>',
    tabel_pivot: '<path d="M6 5h28v18H6zM6 11h28M15 5v18M25 5v18" stroke="currentColor" stroke-width="1.5" fill="none"/><rect x="6" y="5" width="9" height="6" fill="currentColor" opacity=".35"/>',
    batang_100: '<path d="M8 24V4M16 24V4M24 24V4M32 24V4" stroke="currentColor" stroke-width="5" opacity=".35"/><path d="M8 24V12M16 24V16M24 24V9M32 24V14" stroke="currentColor" stroke-width="5"/>',
    waterfall: '<path d="M7 24V14M15 14V8M23 8V12M31 24V9" stroke="currentColor" stroke-width="5"/>',
    radar: '<path d="M20 3l14 9-5 12H11L6 12z" stroke="currentColor" stroke-width="1.2" fill="none" opacity=".5"/><path d="M20 8l9 5-4 7h-9l-3-8z" fill="currentColor" opacity=".6"/>',
    treemap: '<rect x="5" y="3" width="17" height="20" fill="currentColor" opacity=".85"/><rect x="23" y="3" width="12" height="11" fill="currentColor" opacity=".55"/><rect x="23" y="15" width="12" height="8" fill="currentColor" opacity=".35"/>',
    sunburst: '<circle cx="20" cy="13" r="4" fill="currentColor"/><circle cx="20" cy="13" r="8" fill="none" stroke="currentColor" stroke-width="3.5" opacity=".55"/><circle cx="20" cy="13" r="11.5" fill="none" stroke="currentColor" stroke-width="2.5" stroke-dasharray="14 4" opacity=".3"/>',
    funnel: '<path d="M6 4h28l-4 6H10zM11 11h18l-3 6H14zM15 18h10l-2 5h-6z" fill="currentColor" opacity=".75"/>',
    awan_kata: '<text x="3" y="12" font-size="9" font-weight="700" fill="currentColor">Abc</text><text x="20" y="10" font-size="6" fill="currentColor" opacity=".6">de</text><text x="10" y="22" font-size="11" font-weight="700" fill="currentColor" opacity=".8">fgh</text><text x="31" y="20" font-size="6" fill="currentColor" opacity=".5">ij</text>',
    box_plot: '<path d="M10 4v4M10 18v5M30 6v4M30 16v6M6 4h8M6 23h8M26 6h8M26 22h8" stroke="currentColor" stroke-width="1.4"/><rect x="5" y="8" width="10" height="10" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M5 13h10M25 13h10" stroke="currentColor" stroke-width="1.6"/><rect x="25" y="10" width="10" height="6" fill="none" stroke="currentColor" stroke-width="1.6"/>',
    sankey: '<rect x="4" y="3" width="3" height="10" fill="currentColor"/><rect x="4" y="15" width="3" height="8" fill="currentColor"/><rect x="33" y="3" width="3" height="7" fill="currentColor"/><rect x="33" y="12" width="3" height="11" fill="currentColor"/><path d="M7 8C20 8 20 6 33 6M7 19C20 19 20 17 33 17M7 11C20 11 20 20 33 20" stroke="currentColor" stroke-width="3" fill="none" opacity=".4"/>',
    peta_wilayah: '<path d="M4 9l5-3 4 3-2 4 3 3-4 3-5-2zM16 6l6-2 3 4-3 3 2 5-5 2-3-4zM27 9l5-1 4 5-3 5-5-1-2-4z" fill="currentColor" opacity=".7"/>',
    peta_titik: '<path d="M3 16c6-4 11 3 17-1s11-6 17-2" stroke="currentColor" stroke-width="1" fill="none" opacity=".35"/><circle cx="9" cy="10" r="2.6" fill="currentColor"/><circle cx="21" cy="15" r="4" fill="currentColor" opacity=".75"/><circle cx="31" cy="8" r="2" fill="currentColor"/><circle cx="28" cy="19" r="2.8" fill="currentColor" opacity=".6"/>',
    peta_kepadatan: '<path d="M10 4l5 3v6l-5 3-5-3V7zM21 9l5 3v6l-5 3-5-3v-6zM32 4l5 3v6l-5 3-5-3V7z" fill="currentColor"/><path d="M21 9l5 3v6l-5 3-5-3v-6z" opacity=".4" fill="currentColor"/>',
    peta_panas: '<rect x="6" y="3" width="9" height="9" fill="currentColor" opacity=".3"/><rect x="16" y="3" width="9" height="9" fill="currentColor" opacity=".8"/><rect x="26" y="3" width="9" height="9" fill="currentColor" opacity=".5"/><rect x="6" y="13" width="9" height="9" fill="currentColor" opacity=".9"/><rect x="16" y="13" width="9" height="9" fill="currentColor" opacity=".4"/><rect x="26" y="13" width="9" height="9" fill="currentColor" opacity=".7"/>',
  };
})();
