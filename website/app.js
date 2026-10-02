let D = window.PRODUCTS || [];
const $ = (id) => document.getElementById(id);
const charts = {};

const avg = (a) => (a.length ? a.reduce((s, x) => s + x, 0) / a.length : 0);
const median = (a) => {
  if (!a.length) return 0;
  const s = [...a].sort((x, y) => x - y), m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};
const quantile = (a, q) => {
  const s = [...a].sort((x, y) => x - y);
  return s.length ? s[Math.min(s.length - 1, Math.floor(q * s.length))] : 0;
};
const fmt = (v, d = 2) => (v == null || isNaN(v) ? '-' : Number(v).toLocaleString(undefined, { maximumFractionDigits: d }));
const esc = (s) => String(s ?? '-').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const uniq = (k) => [...new Set(D.map((r) => r[k]).filter((v) => v != null))].sort();

const METRICS = {
  'Product count': (r) => r.length,
  'Average rating': (r) => avg(r.map((x) => x.rating_score_imputed)),
  'Average discount': (r) => avg(r.map((x) => x.discount_pct_filled)),
  'Median price': (r) => median(r.map((x) => x.price_current)),
  'Average engagement': (r) => avg(r.map((x) => x.engagement_score)),
};
const GROUPS = ['brand', 'category', 'source', 'availability', 'price_tier_within_currency', 'cluster'];

const COLS = [
  ['title', 'Title'], ['brand', 'Brand'], ['source', 'Source'], ['category', 'Category'],
  ['currency', 'Cur'], ['price_current', 'Price'], ['rating_score_imputed', 'Rating'],
  ['reviews_count', 'Reviews'], ['discount_pct_filled', 'Disc %'], ['availability', 'Stock'],
  ['engagement_score', 'Engagement'],
];

function fillSelect(id, values, withAll = true) {
  $(id).innerHTML = (withAll ? ['All', ...values] : values).map((v) => `<option>${esc(v)}</option>`).join('');
}

function filtered() {
  const f = { source: $('f-source').value, category: $('f-category').value, currency: $('f-currency').value, availability: $('f-availability').value };
  const minRev = +$('f-reviews').value || 0, minRat = +$('f-rating').value || 0;
  const q = $('f-search').value.trim().toLowerCase();
  return D.filter((r) =>
    Object.keys(f).every((k) => f[k] === 'All' || r[k] === f[k]) &&
    r.reviews_count >= minRev && r.rating_score_imputed >= minRat &&
    (!q || `${r.title} ${r.brand}`.toLowerCase().includes(q)));
}

function drawChart(id, config) {
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart($(id), config);
}
const countBy = (rows, key) => {
  const m = new Map();
  rows.forEach((r) => m.set(String(r[key]), (m.get(String(r[key])) || 0) + 1));
  return m;
};

function renderKpis(rows) {
  const k = [
    ['Rows', fmt(rows.length, 0)],
    ['Unique brands', fmt(new Set(rows.map((r) => r.brand)).size, 0)],
    ['Median price', fmt(median(rows.map((r) => r.price_current)))],
    ['Average rating', fmt(avg(rows.map((r) => r.rating_score_imputed)))],
    ['Discounted %', fmt(avg(rows.map((r) => (r.discount_pct_filled > 0 ? 100 : 0))), 1)],
    ['In stock %', fmt(avg(rows.map((r) => (r.availability === 'in_stock' ? 100 : 0))), 1)],
  ];
  $('kpis').innerHTML = k.map(([l, v]) => `<div class="kpi"><span>${l}</span><b>${v}</b></div>`).join('');
}

function renderCharts(rows) {
  const g = $('g-group').value, metric = $('g-metric').value, top = +$('g-top').value;
  const groups = new Map();
  rows.forEach((r) => { const key = String(r[g]); (groups.get(key) || groups.set(key, []).get(key)).push(r); });
  const ranked = [...groups].map(([k, v]) => [k, METRICS[metric](v)]).sort((a, b) => b[1] - a[1]).slice(0, top);
  drawChart('c-rank', { type: 'bar', data: { labels: ranked.map((x) => x[0]), datasets: [{ label: metric, data: ranked.map((x) => +x[1].toFixed(2)), backgroundColor: '#4c78a8' }] }, options: { indexAxis: 'y', plugins: { legend: { display: false } } } });

  const av = countBy(rows, 'availability');
  drawChart('c-avail', { type: 'doughnut', data: { labels: [...av.keys()], datasets: [{ data: [...av.values()], backgroundColor: ['#4c78a8', '#f58518', '#54a24b', '#b279a2'] }] } });

  const bins = [0, 0, 0, 0, 0];
  rows.forEach((r) => { bins[Math.min(4, Math.max(0, Math.floor(r.rating_score_imputed) - 1))]++; });
  drawChart('c-rating', { type: 'bar', data: { labels: ['1-2', '2-3', '3-4', '4-5', '5'], datasets: [{ label: 'Products', data: bins, backgroundColor: '#54a24b' }] }, options: { plugins: { legend: { display: false } } } });

  const cl = [...countBy(rows, 'cluster')].sort((a, b) => a[0] - b[0]);
  drawChart('c-cluster', { type: 'bar', data: { labels: cl.map((x) => 'Cluster ' + x[0]), datasets: [{ label: 'Products', data: cl.map((x) => x[1]), backgroundColor: '#e45756' }] }, options: { plugins: { legend: { display: false } } } });
}

function renderMore(rows) {
  const grp = (k) => {
    const m = new Map();
    rows.forEach((r) => (m.get(r[k]) || m.set(r[k], []).get(r[k])).push(r));
    return [...m].sort((a, b) => String(a[0]).localeCompare(String(b[0])));
  };
  const bar = (id, k, f, label, color, horiz) => {
    const g = grp(k);
    drawChart(id, { type: 'bar', data: { labels: g.map((x) => x[0]), datasets: [{ label, data: g.map((x) => +f(x[1]).toFixed(2)), backgroundColor: color }] }, options: { indexAxis: horiz ? 'y' : 'x', plugins: { legend: { display: false } } } });
  };
  const pct = (fn) => (r) => avg(r.map((x) => (fn(x) ? 100 : 0)));
  bar('c-cat', 'category', (r) => r.length, 'Products', '#4c78a8');
  bar('c-catrate', 'category', (r) => avg(r.map((x) => x.rating_score_imputed)), 'Avg rating', '#54a24b', true);
  bar('c-disc', 'source', pct((x) => x.discount_pct_filled > 0), 'Discounted %', '#f58518');
  bar('c-anom', 'source', pct((x) => x.anomaly_flag === 'Anomalous'), 'Anomaly %', '#e45756');
  bar('c-opps', 'source', (r) => avg(r.map((x) => x.opportunity_score)), 'Opportunity', '#72b7b2');

  const src = grp('source');
  drawChart('c-src', { type: 'doughnut', data: { labels: src.map((x) => x[0]), datasets: [{ data: src.map((x) => x[1].length), backgroundColor: PAL }] } });

  const cl = grp('cluster');
  const mets = {
    Rating: (r) => avg(r.map((x) => x.rating_score_imputed)),
    Reviews: (r) => avg(r.map((x) => x.reviews_count)),
    Discount: (r) => avg(r.map((x) => x.discount_pct_filled)),
    'In stock': (r) => avg(r.map((x) => (x.availability === 'in_stock' ? 1 : 0))),
    Engagement: (r) => avg(r.map((x) => x.engagement_score)),
  };
  const names = Object.keys(mets);
  const vals = cl.map(([, r]) => names.map((n) => mets[n](r)));
  const mx = names.map((_, j) => Math.max(...vals.map((v) => v[j])) || 1);
  drawChart('c-radar', { type: 'radar', data: { labels: names, datasets: cl.map(([c], i) => ({ label: 'Cluster ' + c, data: vals[i].map((v, j) => +(v / mx[j]).toFixed(2)), borderColor: PAL[i % PAL.length], backgroundColor: PAL[i % PAL.length] + '33' })) } });

  const cat = grp('category');
  drawChart('c-combo', { type: 'bar', data: { labels: cat.map((x) => x[0]), datasets: [
    { type: 'bar', label: 'Products', data: cat.map((x) => x[1].length), backgroundColor: '#4c78a8', yAxisID: 'y' },
    { type: 'line', label: 'Avg rating', data: cat.map((x) => +avg(x[1].map((r) => r.rating_score_imputed)).toFixed(2)), borderColor: '#e45756', yAxisID: 'y2' },
  ] }, options: { scales: { y2: { position: 'right', min: 2.4, max: 5, grid: { drawOnChartArea: false } } } } });
}

function table(el, rows, cols = COLS, limit = 50) {
  const head = cols.map((c) => `<th>${c[1]}</th>`).join('');
  const body = rows.slice(0, limit).map((r) => `<tr>${cols.map((c) => `<td>${typeof r[c[0]] === 'number' ? fmt(r[c[0]]) : esc(r[c[0]])}</td>`).join('')}</tr>`).join('');
  $(el).innerHTML = rows.length ? `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>` : '<p>No products match the current filters.</p>';
}

function renderTables(rows) {
  const sort = $('p-sort').value;
  table('t-products', [...rows].sort((a, b) => (b[sort] ?? 0) - (a[sort] ?? 0)));

  const rCut = quantile(D.map((r) => r.rating_score_imputed), 0.85);
  const vCut = quantile(D.map((r) => r.reviews_count), 0.35);
  const rMed = median(D.map((r) => r.rating_score_imputed));
  const inStock = rows.filter((r) => r.availability === 'in_stock');

  const extra = (key, label) => [...COLS.slice(0, 5), COLS[5], COLS[6], COLS[7], [key, label]];
  table('t-opp', inStock.filter((r) => r.rating_score_imputed >= rMed).sort((a, b) => b.opportunity_score - a.opportunity_score), extra('opportunity_score', 'Opp. score'), 15);
  table('t-gems', inStock.filter((r) => r.rating_score_imputed >= rCut && r.reviews_count <= vCut).sort((a, b) => b.rating_score_imputed - a.rating_score_imputed || a.reviews_count - b.reviews_count), COLS, 15);
  table('t-anom', rows.filter((r) => r.anomaly_flag === 'Anomalous').sort((a, b) => b.anomaly_score - a.anomaly_score), extra('anomaly_score', 'Anomaly'), 15);
}

const PAL = ['#4c78a8', '#f58518', '#54a24b', '#e45756', '#b279a2', '#72b7b2', '#eeca3b'];
const pct = (f) => (r) => avg(r.map((x) => (f(x) ? 100 : 0)));
const HEAT = {
  'Avg engagement': (r) => avg(r.map((x) => x.engagement_score)),
  'Avg rating': (r) => avg(r.map((x) => x.rating_score_imputed)),
  'Product count': (r) => r.length,
  'Discounted %': pct((x) => x.discount_pct_filled > 0),
  'In stock %': pct((x) => x.availability === 'in_stock'),
  'Anomaly %': pct((x) => x.anomaly_flag === 'Anomalous'),
  'Avg opportunity': (r) => avg(r.map((x) => x.opportunity_score)),
};

function renderAnalysis(rows) {
  const cur = $('a-cur').value;
  const tip = (unit) => ({ callbacks: { label: (c) => `${String(c.raw.t).slice(0, 60)} | ${fmt(c.raw.x)} ${unit}, y=${fmt(c.raw.y)}` } });

  const clusters = [...new Set(rows.map((r) => r.cluster))].sort();
  const sub = rows.filter((r) => r.currency === cur);
  drawChart('c-bubble', { type: 'bubble', data: { datasets: clusters.map((c, i) => ({
    label: 'Cluster ' + c, backgroundColor: PAL[i % PAL.length] + '99',
    data: sub.filter((r) => r.cluster === c).map((r) => ({ x: r.price_current, y: r.rating_score_imputed, r: Math.max(3, Math.min(18, Math.sqrt(r.reviews_count) / 2)), t: r.title })),
  })) }, options: { scales: { x: { type: 'logarithmic', title: { display: true, text: 'Price (' + cur + ')' } }, y: { min: 2.4, max: 5.1, title: { display: true, text: 'Rating' } } }, plugins: { tooltip: tip(cur) } } });

  const m = HEAT[$('a-metric').value];
  const cats = [...new Set(rows.map((r) => r.category))].sort(), srcs = [...new Set(rows.map((r) => r.source))].sort();
  const cell = {};
  let lo = Infinity, hi = -Infinity;
  cats.forEach((c) => srcs.forEach((s) => {
    const sel = rows.filter((r) => r.category === c && r.source === s);
    if (sel.length) { const v = m(sel); cell[c + '|' + s] = v; lo = Math.min(lo, v); hi = Math.max(hi, v); }
  }));
  $('heat').innerHTML = `<table class="heat"><thead><tr><th>Category</th>${srcs.map((s) => `<th>${esc(s)}</th>`).join('')}</tr></thead><tbody>` +
    cats.map((c) => `<tr><td>${esc(c)}</td>${srcs.map((s) => {
      const v = cell[c + '|' + s];
      if (v == null) return '<td>-</td>';
      const t = (v - lo) / (hi - lo || 1);
      return `<td style="background:rgba(76,120,168,${(0.12 + 0.85 * t).toFixed(2)});color:${t > 0.55 ? '#fff' : 'inherit'}">${fmt(v)}</td>`;
    }).join('')}</tr>`).join('') + '</tbody></table>';

  const tiers = ['Budget', 'Mid-range', 'Premium', 'Luxury'], sources = srcs;
  drawChart('c-tier', { type: 'bar', data: { labels: sources, datasets: tiers.map((t, i) => ({ label: t, backgroundColor: PAL[i], data: sources.map((s) => rows.filter((r) => r.source === s && r.price_tier_within_currency === t).length) })) }, options: { scales: { x: { stacked: true }, y: { stacked: true } } } });

  const pt = (r) => ({ x: r.high_review_propensity, y: r.engagement_score, t: r.title });
  drawChart('c-opp', { type: 'scatter', data: { datasets: [
    { label: 'Typical', backgroundColor: '#2a9d8f88', data: rows.filter((r) => r.anomaly_flag !== 'Anomalous').map(pt) },
    { label: 'Anomalous', backgroundColor: '#e76f51', data: rows.filter((r) => r.anomaly_flag === 'Anomalous').map(pt) },
  ] }, options: { scales: { x: { title: { display: true, text: 'Review propensity' } }, y: { title: { display: true, text: 'Engagement score' } } }, plugins: { tooltip: tip('propensity') } } });
}

function download() {
  const rows = filtered(), keys = Object.keys(D[0]);
  const csv = [keys.join(',')].concat(rows.map((r) => keys.map((k) => JSON.stringify(r[k] ?? '')).join(','))).join('\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  a.download = 'filtered_products.csv';
  a.click();
}

function render() {
  const rows = filtered();
  $('status').textContent = rows.length ? `Showing ${rows.length.toLocaleString()} of ${D.length.toLocaleString()} products.` : 'No products match the current filters.';
  renderKpis(rows);
  renderCharts(rows);
  renderMore(rows);
  renderTables(rows);
  renderAnalysis(rows);
  if (window.drawGallery && !$('tab-gallery').classList.contains('hidden')) window.drawGallery(rows);
}

function init() {
  if (!D.length) { $('status').textContent = 'Koi data nahi hai. Upar "Upload CSV" se apni CSV upload karo (python server.py chalna chahiye).'; return; }
  fillSelect('f-source', uniq('source'));
  fillSelect('f-category', uniq('category'));
  fillSelect('f-currency', uniq('currency'));
  fillSelect('f-availability', uniq('availability'));
  fillSelect('g-group', GROUPS, false);
  fillSelect('a-cur', uniq('currency'), false);
  fillSelect('a-metric', Object.keys(HEAT), false);
  $('dl').onclick = download;
  fillSelect('g-metric', Object.keys(METRICS), false);
  fillSelect('p-sort', ['engagement_score', 'reviews_count', 'rating_score_imputed', 'price_current', 'discount_pct_filled'], false);

  if (!window.__bound) {
  window.__bound = true;
  document.querySelectorAll('.filters select, .filters input, .card-head select').forEach((el) => el.addEventListener('input', render));
  $('reset').onclick = () => {
    ['f-source', 'f-category', 'f-currency', 'f-availability'].forEach((id) => ($(id).value = 'All'));
    $('f-reviews').value = 0; $('f-rating').value = 0; $('f-search').value = '';
    render();
  };
  document.querySelectorAll('.tab').forEach((btn) => btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach((b) => b.classList.toggle('active', b === btn));
    document.querySelectorAll('.panel').forEach((p) => p.classList.toggle('hidden', p.id !== 'tab-' + btn.dataset.tab));
    render();
  }));
  }
  render();
}

function bindUpload() {
  $('csv').addEventListener('change', async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    $('status').textContent = 'Uploading and analysing ' + f.name + ' ... (models train ho rahe hain, 10-60 sec)';
    const fd = new FormData();
    fd.append('file', f);
    try {
      const res = await fetch('/api/upload', { method: 'POST', body: fd });
      const j = await res.json();
      if (!res.ok) throw new Error(j.error || res.statusText);
      D = j.products; window.ML = j.ml; window.MISSING = j.missing;
      $('f-reviews').value = 0; $('f-rating').value = 0; $('f-search').value = '';
      init();
    } catch (err) {
      $('status').textContent = 'Upload failed: ' + err.message + ' (python server.py chal raha hai? URL http://127.0.0.1:5000 hona chahiye)';
    }
    e.target.value = '';
  });
}

bindUpload();
init();