(function () {
const sum = (a) => a.reduce((s, x) => s + x, 0), mean = (a) => (a.length ? sum(a) / a.length : 0);
const std = (a) => { const m = mean(a); return Math.sqrt(mean(a.map((x) => (x - m) ** 2))); };
const col = (r, k) => r.map((x) => x[k]);
const keys = (r, k) => [...new Set(col(r, k))].filter((v) => v != null).sort();
const by = (r, k) => { const m = {}; r.forEach((x) => (m[x[k]] ??= []).push(x)); return m; };
const cnt = (r, k) => { const m = by(r, k); return Object.keys(m).sort().map((a) => [a, m[a].length]); };
const top = (e, n) => [...e].sort((a, b) => b[1] - a[1]).slice(0, n);
const srt = (a) => [...a].sort((x, y) => x - y);
const ppf = (p) => { const t = Math.sqrt(-2 * Math.log(p < 0.5 ? p : 1 - p)); const v = t - (2.515517 + 0.802853 * t + 0.010328 * t * t) / (1 + 1.432788 * t + 0.189269 * t * t + 0.001308 * t ** 3); return p < 0.5 ? -v : v; };
const TIERS = ['Budget', 'Mid-range', 'Premium', 'Luxury'], H = [...Array(24).keys()], DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const RT = 'rating_score_imputed', ENG = 'engagement_score';
const hasT = (r) => r.some((x) => x.scrape_hour != null);
const ml = () => window.ML || null;
const bars = (e, o = {}) => [{ type: 'bar', x: e.map((v) => v[0]), y: e.map((v) => v[1]), ...o }];
const NUM = { rating: RT, 'log price': 'lp', 'log reviews': 'lr', discount: 'discount_pct_filled', engagement: ENG };

const CH = [];
const add = (g, t, f) => CH.push([g, t, f]);

// ---------- Basic ----------
add('Basic charts', 'Bar: top brands', (r) => { const e = top(cnt(r, 'brand'), 10).reverse(); return { data: [{ type: 'bar', orientation: 'h', x: e.map((v) => v[1]), y: e.map((v) => v[0]) }] }; });
add('Basic charts', 'Column: products by category', (r) => ({ data: bars(cnt(r, 'category')) }));
add('Basic charts', 'Line: avg rating by price tier', (r) => ({ data: [{ type: 'scatter', mode: 'lines+markers', x: TIERS, y: TIERS.map((t) => mean(col(r.filter((x) => x.price_tier_within_currency === t), RT))) }] }));
add('Basic charts', 'Area: products by price tier', (r) => ({ data: [{ type: 'scatter', fill: 'tozeroy', x: TIERS, y: TIERS.map((t) => r.filter((x) => x.price_tier_within_currency === t).length) }] }));
add('Basic charts', 'Pie: availability', (r) => { const e = cnt(r, 'availability'); return { data: [{ type: 'pie', labels: e.map((v) => v[0]), values: e.map((v) => v[1]) }] }; });
add('Basic charts', 'Donut: source share', (r) => { const e = cnt(r, 'source'); return { data: [{ type: 'pie', hole: 0.5, labels: e.map((v) => v[0]), values: e.map((v) => v[1]) }] }; });
add('Basic charts', 'Histogram: rating', (r) => ({ data: [{ type: 'histogram', x: col(r, RT), nbinsx: 20 }] }));
const sc = (r, bubble) => { const cur = keys(r, 'currency')[0], s = r.filter((x) => x.currency === cur); return { data: [{ type: 'scatter', mode: 'markers', x: col(s, 'price_current'), y: col(s, RT), text: col(s, 'title'), marker: { size: bubble ? s.map((x) => Math.max(5, Math.min(30, Math.sqrt(x.reviews_count) / 1.5))) : 7, opacity: 0.6 } }], layout: { xaxis: { type: 'log', title: 'price (' + cur + ')' }, yaxis: { title: 'rating' } } }; };
add('Basic charts', 'Scatter: price vs rating', (r) => sc(r, false));
add('Basic charts', 'Bubble: price vs rating (size = reviews)', (r) => sc(r, true));
add('Basic charts', 'Missingness by column (%)', () => { const m = window.MISSING; return m ? { data: [{ type: 'bar', x: m.cols, y: m.pct }] } : null; });

// ---------- Comparison / trend ----------
const stackAvail = (r, norm) => { const s = keys(r, 'source'); return { data: keys(r, 'availability').map((a) => ({ type: 'bar', name: a, x: s, y: s.map((v) => r.filter((x) => x.source === v && x.availability === a).length) })), layout: { barmode: 'stack', barnorm: norm ? 'percent' : '' } }; };
add('Comparison and trend', 'Grouped bar: avg rating, category x source', (r) => ({ data: keys(r, 'source').map((s) => ({ type: 'bar', name: s, x: keys(r, 'category'), y: keys(r, 'category').map((c) => mean(col(r.filter((x) => x.source === s && x.category === c), RT))) })), layout: { barmode: 'group' } }));
add('Comparison and trend', 'Stacked bar: availability by source', (r) => stackAvail(r, false));
add('Comparison and trend', '100% stacked bar: availability by source', (r) => stackAvail(r, true));
const hourLines = (r, stack) => hasT(r) ? { data: keys(r, 'source').map((s) => ({ type: 'scatter', mode: 'lines', name: s, stackgroup: stack ? 'a' : undefined, x: H, y: H.map((h) => r.filter((x) => x.source === s && x.scrape_hour === h).length) })), layout: { xaxis: { title: 'scrape hour' } } } : null;
add('Comparison and trend', 'Multi-line: scrapes per hour by source', (r) => hourLines(r, false));
add('Comparison and trend', 'Stacked area: scrapes per hour by source', (r) => hourLines(r, true));
add('Comparison and trend', 'Combo + dual-axis: count (bars) and avg rating (line)', (r) => { const c = keys(r, 'category'); return { data: [{ type: 'bar', name: 'products', x: c, y: c.map((v) => r.filter((x) => x.category === v).length) }, { type: 'scatter', mode: 'lines+markers', name: 'avg rating', yaxis: 'y2', x: c, y: c.map((v) => mean(col(r.filter((x) => x.category === v), RT))) }], layout: { yaxis2: { overlaying: 'y', side: 'right', range: [2.4, 5] } } }; });

// ---------- Statistical ----------
add('Statistical', 'Box plot: rating by source', (r) => ({ data: keys(r, 'source').map((s) => ({ type: 'box', name: s, y: col(r.filter((x) => x.source === s), RT) })) }));
add('Statistical', 'Violin plot: rating by source', (r) => ({ data: keys(r, 'source').map((s) => ({ type: 'violin', name: s, box: { visible: true }, y: col(r.filter((x) => x.source === s), RT) })) }));
add('Statistical', 'Strip / swarm plot: engagement by category', (r) => ({ data: keys(r, 'category').map((c) => ({ type: 'box', name: c, boxpoints: 'all', jitter: 0.6, pointpos: 0, fillcolor: 'rgba(0,0,0,0)', line: { width: 0 }, y: col(r.filter((x) => x.category === c), ENG) })) }));
add('Statistical', 'Error bars: avg rating +/- std error by category', (r) => { const c = keys(r, 'category'), g = c.map((v) => col(r.filter((x) => x.category === v), RT)); return { data: [{ type: 'scatter', mode: 'markers', x: c, y: g.map(mean), error_y: { type: 'data', array: g.map((a) => std(a) / Math.sqrt(a.length || 1)) } }] }; });
add('Statistical', 'Density (KDE): rating', (r) => { const a = col(r, RT), n = a.length, h = 1.06 * std(a) * n ** -0.2 || 0.1, lo = Math.min(...a) - 0.5, hi = Math.max(...a) + 0.5, xs = [...Array(80)].map((_, i) => lo + (i * (hi - lo)) / 79); return { data: [{ type: 'scatter', fill: 'tozeroy', x: xs, y: xs.map((x) => sum(a.map((v) => Math.exp(-0.5 * ((x - v) / h) ** 2))) / (n * h * Math.sqrt(2 * Math.PI))) }] }; });
add('Statistical', 'ECDF (step): rating', (r) => { const a = srt(col(r, RT)); return { data: [{ type: 'scatter', mode: 'lines', line: { shape: 'hv' }, x: a, y: a.map((_, i) => (i + 1) / a.length) }] }; });
add('Statistical', 'QQ plot: rating vs normal', (r) => { const a = srt(col(r, RT)), n = a.length, m = mean(a), s = std(a); const t = a.map((_, i) => m + s * ppf((i + 0.5) / n)); return { data: [{ type: 'scatter', mode: 'markers', x: t, y: a, name: 'data' }, { type: 'scatter', mode: 'lines', x: [a[0], a[n - 1]], y: [a[0], a[n - 1]], name: 'y = x' }] }; });

// ---------- Relationship ----------
add('Relationship', 'Heatmap: avg engagement, category x source', (r) => { const c = keys(r, 'category'), s = keys(r, 'source'); return { data: [{ type: 'heatmap', x: s, y: c, colorscale: 'Viridis', z: c.map((a) => s.map((b) => { const q = r.filter((x) => x.category === a && x.source === b); return q.length ? mean(col(q, ENG)) : null; })) }] }; });
const lr = (r) => r.map((x) => ({ ...x, lp: Math.log1p(x.price_current), lr: Math.log1p(x.reviews_count) }));
add('Relationship', 'Correlation matrix', (r) => { const d = lr(r), k = Object.keys(NUM), z = k.map((a) => k.map((b) => { const x = col(d, NUM[a]), y = col(d, NUM[b]), mx = mean(x), my = mean(y); return sum(x.map((v, i) => (v - mx) * (y[i] - my))) / (Math.sqrt(sum(x.map((v) => (v - mx) ** 2)) * sum(y.map((v) => (v - my) ** 2))) || 1); })); return { data: [{ type: 'heatmap', x: k, y: k, z, zmin: -1, zmax: 1, colorscale: 'RdBu', text: z.map((q) => q.map((v) => v.toFixed(2))), texttemplate: '%{text}' }] }; });
add('Relationship', 'Scatter matrix (pair plot)', (r) => { const d = lr(r); return { data: [{ type: 'splom', dimensions: Object.keys(NUM).map((k) => ({ label: k, values: col(d, NUM[k]) })), marker: { size: 3, color: d.map((x) => +x.cluster), colorscale: 'Viridis' }, diagonal: { visible: false } }], layout: { height: 520 } }; });
add('Relationship', 'Parallel coordinates', (r) => { const d = lr(r); return { data: [{ type: 'parcoords', line: { color: d.map((x) => +x.cluster), colorscale: 'Viridis' }, dimensions: Object.keys(NUM).map((k) => ({ label: k, values: col(d, NUM[k]) })) }], layout: { margin: { t: 60, l: 60, r: 40, b: 30 } } }; });
add('Relationship', 'PCA cluster map', (r) => r.some((x) => x.pc1 != null) ? { data: keys(r, 'cluster').map((c) => { const s = r.filter((x) => x.cluster === c); return { type: 'scatter', mode: 'markers', name: 'Cluster ' + c, x: col(s, 'pc1'), y: col(s, 'pc2'), text: col(s, 'title'), marker: { size: 6, opacity: 0.7 } }; }) } : null);

// ---------- Specialized ----------
add('Specialized', 'Radar: cluster profile', (r) => { const cl = keys(r, 'cluster'), m = { rating: (a) => mean(col(a, RT)), reviews: (a) => mean(col(a, 'reviews_count')), discount: (a) => mean(col(a, 'discount_pct_filled')), 'in stock': (a) => mean(a.map((x) => +(x.availability === 'in_stock'))), engagement: (a) => mean(col(a, ENG)) }, k = Object.keys(m), v = cl.map((c) => k.map((n) => m[n](r.filter((x) => x.cluster === c)))), mx = k.map((_, j) => Math.max(...v.map((q) => q[j])) || 1); return { data: cl.map((c, i) => ({ type: 'scatterpolar', fill: 'toself', name: 'Cluster ' + c, theta: [...k, k[0]], r: [...v[i].map((x, j) => x / mx[j]), v[i][0] / mx[0]] })) }; });
const stages = (r) => { const med = srt(col(r, RT))[r.length >> 1] || 0, a = r.filter((x) => x.availability === 'in_stock'), b = a.filter((x) => x[RT] >= med), c = b.filter((x) => x.anomaly_flag !== 'Anomalous'), d = c.filter((x) => x.reviews_count <= 50); return [['All products', r.length], ['In stock', a.length], ['Rating >= median', b.length], ['Not anomalous', c.length], ['Reviews <= 50', d.length]]; };
add('Specialized', 'Funnel: opportunity filters', (r) => { const s = stages(r); return { data: [{ type: 'funnel', y: s.map((v) => v[0]), x: s.map((v) => v[1]) }], layout: { margin: { l: 130 } } }; });
add('Specialized', 'Waterfall: products dropped at each filter', (r) => { const s = stages(r); return { data: [{ type: 'waterfall', x: s.map((v) => v[0]), measure: s.map((_, i) => (i === 0 ? 'absolute' : 'relative')), y: s.map((v, i) => (i === 0 ? v[1] : v[1] - s[i - 1][1])) }] }; });
const pctOf = (r, f) => (r.length ? (100 * r.filter(f).length) / r.length : 0);
add('Specialized', 'Gauge: in-stock share %', (r) => ({ data: [{ type: 'indicator', mode: 'gauge+number', value: pctOf(r, (x) => x.availability === 'in_stock'), gauge: { axis: { range: [0, 100] } } }] }));
add('Specialized', 'Bullet: discounted share % vs 50% target', (r) => ({ data: [{ type: 'indicator', mode: 'number+gauge', value: pctOf(r, (x) => x.discount_pct_filled > 0), gauge: { shape: 'bullet', axis: { range: [0, 100] }, threshold: { value: 50, line: { width: 3 } } } }], layout: { margin: { l: 90, t: 50 } } }));
const tree = (r, type) => { const ids = [], lab = [], par = [], val = [], clr = []; keys(r, 'source').forEach((s) => { ids.push(s); lab.push(s); par.push(''); val.push(0); clr.push(0); keys(r.filter((x) => x.source === s), 'category').forEach((c) => { const q = r.filter((x) => x.source === s && x.category === c); ids.push(s + '|' + c); lab.push(c); par.push(s); val.push(q.length); clr.push(mean(col(q, RT))); }); }); return { data: [{ type, ids, labels: lab, parents: par, values: val, marker: { colors: clr, colorscale: 'Viridis' }, branchvalues: 'remainder' }] }; };
add('Specialized', 'Treemap: source > category', (r) => tree(r, 'treemap'));
add('Specialized', 'Sunburst: source > category', (r) => tree(r, 'sunburst'));
add('Specialized', 'Sankey: source > category > availability', (r) => { const S = keys(r, 'source'), C = keys(r, 'category'), A = keys(r, 'availability'), n = [...S, ...C, ...A], ix = (v) => n.indexOf(v), s = [], t = [], v = []; const link = (k1, k2) => cnt(r.map((x) => ({ k: x[k1] + '\u0001' + x[k2] })), 'k').forEach(([k, c]) => { const [a, b] = k.split('\u0001'); s.push(ix(a)); t.push(ix(b)); v.push(c); }); link('source', 'category'); link('category', 'availability'); return { data: [{ type: 'sankey', node: { label: n, pad: 12 }, link: { source: s, target: t, value: v } }], layout: { height: 420 } }; });

// ---------- Time / quality ----------
add('Time and freshness', 'Time-series line: scrapes per hour', (r) => hasT(r) ? { data: [{ type: 'scatter', mode: 'lines+markers', x: H, y: H.map((h) => r.filter((x) => x.scrape_hour === h).length) }] } : null);
add('Time and freshness', 'Calendar-style heatmap: scrape day x hour', (r) => hasT(r) ? { data: [{ type: 'heatmap', x: H, y: DAYS, colorscale: 'YlGnBu', z: DAYS.map((d) => H.map((h) => r.filter((x) => x.scrape_day === d && x.scrape_hour === h).length)) }] } : null);
add('Time and freshness', 'Freshness: days since latest scrape by source', (r) => r.some((x) => x.days_since_latest_scrape != null) ? { data: keys(r, 'source').map((s) => ({ type: 'box', name: s, y: col(r.filter((x) => x.source === s), 'days_since_latest_scrape') })) } : null);

// ---------- Business ----------
add('Business', 'Pareto: brands by total reviews', (r) => { const m = by(r, 'brand'), e = top(Object.keys(m).map((b) => [b, sum(col(m[b], 'reviews_count'))]), 15), tot = sum(e.map((v) => v[1])) || 1; let c = 0; return { data: [{ type: 'bar', name: 'reviews', x: e.map((v) => v[0]), y: e.map((v) => v[1]) }, { type: 'scatter', mode: 'lines+markers', name: 'cumulative %', yaxis: 'y2', x: e.map((v) => v[0]), y: e.map((v) => (c += v[1], (100 * c) / tot)) }], layout: { yaxis2: { overlaying: 'y', side: 'right', range: [0, 100] } } }; });
add('Business', 'Progress bars: share of products (%)', (r) => { const k = [['In stock', (x) => x.availability === 'in_stock'], ['Discounted', (x) => x.discount_pct_filled > 0], ['Rating >= 4', (x) => x[RT] >= 4], ['Anomalous', (x) => x.anomaly_flag === 'Anomalous']]; return { data: [{ type: 'bar', orientation: 'h', y: k.map((v) => v[0]), x: k.map((v) => pctOf(r, v[1])) }], layout: { xaxis: { range: [0, 100] } } }; });

// ---------- Machine learning ----------
add('Machine learning', 'Confusion matrix (holdout)', () => { const m = ml(); if (!m) return null; return { data: [{ type: 'heatmap', z: m.confusion, x: ['Pred low', 'Pred high'], y: ['Actual low', 'Actual high'], colorscale: 'YlGnBu', text: m.confusion, texttemplate: '%{text}' }] }; });
add('Machine learning', 'Feature importance', () => { const m = ml(); return m ? { data: [{ type: 'bar', orientation: 'h', x: m.importance.importance, y: m.importance.feature }], layout: { margin: { l: 170 } } } : null; });
const curve = () => { const m = ml(); if (!m) return null; const o = m.y_proba.map((p, i) => [p, m.y_test[i]]).sort((a, b) => b[0] - a[0]), P = sum(m.y_test), N = o.length - P; let tp = 0, fp = 0; const pts = [{ fpr: 0, tpr: 0, prec: 1, rec: 0 }]; o.forEach((v) => { v[1] ? tp++ : fp++; pts.push({ fpr: fp / (N || 1), tpr: tp / (P || 1), prec: tp / (tp + fp), rec: tp / (P || 1) }); }); return pts; };
add('Machine learning', 'ROC curve', () => { const p = curve(); return p ? { data: [{ type: 'scatter', mode: 'lines', name: 'model', x: p.map((v) => v.fpr), y: p.map((v) => v.tpr) }, { type: 'scatter', mode: 'lines', name: 'random', line: { dash: 'dot' }, x: [0, 1], y: [0, 1] }], layout: { xaxis: { title: 'FPR' }, yaxis: { title: 'TPR' } } } : null; });
add('Machine learning', 'Precision-recall curve', () => { const p = curve(); return p ? { data: [{ type: 'scatter', mode: 'lines', x: p.map((v) => v.rec), y: p.map((v) => v.prec) }], layout: { xaxis: { title: 'Recall' }, yaxis: { title: 'Precision', range: [0, 1.05] } } } : null; });
add('Machine learning', 'Calibration curve', () => { const m = ml(); if (!m) return null; const bx = [], by_ = []; for (let b = 0; b < 10; b++) { const s = m.y_proba.map((p, i) => [p, m.y_test[i]]).filter((v) => v[0] >= b / 10 && v[0] < (b + 1) / 10 + (b === 9 ? 1e-9 : 0)); if (s.length) { bx.push(mean(s.map((v) => v[0]))); by_.push(mean(s.map((v) => v[1]))); } } return { data: [{ type: 'scatter', mode: 'lines+markers', name: 'model', x: bx, y: by_ }, { type: 'scatter', mode: 'lines', name: 'perfect', line: { dash: 'dot' }, x: [0, 1], y: [0, 1] }], layout: { xaxis: { title: 'Predicted' }, yaxis: { title: 'Actual rate' } } }; });
add('Machine learning', 'Predicted propensity vs actual reviews', (r) => ({ data: [{ type: 'scatter', mode: 'markers', x: col(r, 'high_review_propensity'), y: col(r, 'reviews_count'), text: col(r, 'title'), marker: { size: 6, opacity: 0.6 } }], layout: { yaxis: { type: 'log', title: 'reviews' }, xaxis: { title: 'propensity' } } }));
add('Machine learning', 'Silhouette score by k', () => { const m = ml(); return m && m.silhouette.length ? { data: [{ type: 'bar', x: m.silhouette.map((v) => 'k=' + v.k), y: m.silhouette.map((v) => v.silhouette_score) }] } : null; });

window.drawGallery = function (rows) {
  const root = document.getElementById('gallery');
  if (typeof Plotly === 'undefined') { root.innerHTML = '<p style="padding:12px">Plotly library load nahi hui (internet ya CDN block). F12 > Network/Console check karo.</p>'; return; }
  if (!rows.length) { root.innerHTML = '<p>No products match the current filters.</p>'; return; }
  if (!root.dataset.built) {
    let html = '', g = '';
    CH.forEach(([grp], i) => { if (grp !== g) { if (g) html += '</div>'; html += `<h2 class="gh">${grp}</h2><div class="gal">`; g = grp; } html += `<div id="g${i}"></div>`; });
    root.innerHTML = html + '</div>';
    root.dataset.built = 1;
  }
  const fg = getComputedStyle(document.body).color;
  CH.forEach(([, title, fn], i) => {
    const el = document.getElementById('g' + i);
    let res = null;
    try { res = fn(rows); } catch (e) { console.warn(title, e); }
    if (!res) { el.innerHTML = `<small style="color:var(--muted)">${title}: data not available</small>`; return; }
    const lay = { title: { text: title, font: { size: 13 } }, height: 330, margin: { l: 50, r: 20, t: 40, b: 50 }, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: { color: fg, size: 11 }, ...res.layout };
    try { Plotly.react(el, res.data, lay, { responsive: true, displaylogo: false }); } catch (e) { console.warn(title, e); el.innerHTML = `<small style="color:var(--muted)">${title}: chart error (console dekho)</small>`; }
  });
};
})();