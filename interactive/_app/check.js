// Check the built interactive without a browser.
//
//     node interactive/_app/check.js
//
// Reads ../_hairy-app.html, checks the markup, then runs the page's own script
// against a small fake DOM and compares what it decoded with data/*.csv. The
// fake DOM returns null for any id that is not really in the markup, as a
// browser would, so a missing element fails here rather than silently killing
// the script on a phone.

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = path.join(__dirname, '..', '_hairy-app.html');
const DATA = path.join(__dirname, '..', '..', 'data');
if (!fs.existsSync(FILE)) { console.error('check.js: run build.py first'); process.exit(1); }
const html = fs.readFileSync(FILE, 'utf8');

let failures = 0, passes = 0;
const check = (ok, label, detail) => {
  if (ok) passes++; else failures++;
  if (!ok || process.argv.includes('-v')) console.log(`${ok ? 'ok  ' : 'FAIL'}  ${label}${detail ? '  (' + detail + ')' : ''}`);
};

// ---------------------------------------------------------------- markup
const opens = (html.match(/<script>/g) || []).length, closes = (html.match(/<\/script>/g) || []).length;
check(opens === 1 && closes === 1, 'exactly one script block', `${opens}/${closes}`);
const markup = html.slice(0, html.indexOf('<script>'));
const script = html.slice(html.indexOf('<script>') + 8, html.lastIndexOf('</script>'));
check(!/__[A-Z_]+__/.test(html), 'no unfilled placeholders');

const ids = new Set([...markup.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]));
for (const id of new Set([...script.matchAll(/\$\('([^']+)'\)|getElementById\('([^']+)'\)/g)].map(m => m[1] || m[2]))) {
  check(ids.has(id), `#${id} exists in the markup`);
}

const prose = markup.replace(/<style>[\s\S]*?<\/style>/, '').replace(/<[^>]+>/g, ' ');
check(!/—|&mdash;/.test(prose), 'no em-dashes in the text');
check(!/\bbands?\b/i.test(prose), 'no mention of a target range band');
check(/href="\.\.\/r\/"/.test(markup) && /href="\.\.\/python\/"/.test(markup), 'notes link both notebooks');
check(/<details class="ha-notes">/.test(markup) && !/<details class="ha-notes" open/.test(markup), 'notes start collapsed');
// iOS: everything tappable is a real button, and nothing hidden can catch taps.
check(!/<div[^>]*\bonclick=/.test(markup), 'no click handlers on divs');
check(/\.ha-tip\{[^}]*pointer-events:none/.test(html) && /\.ha-brush\{[^}]*pointer-events:none/.test(html),
      'tooltip and brush never take pointer events');
check(/touch-action:pan-y/.test(html), 'plot lets vertical swipes scroll the page');

const chipKeys = [...markup.matchAll(/<button type="button" class="ha-chip" data-s="([^"]+)"/g)].map(m => m[1]);
const DATA_JSON = JSON.parse(script.slice(script.indexOf('const DATA = ') + 13, script.indexOf(';\nconst root')));
const seriesKeys = DATA_JSON.series.map(s => s.key);
check(JSON.stringify(chipKeys) === JSON.stringify(seriesKeys), 'one legend button per series, in order', chipKeys.join(', '));
for (const k of seriesKeys.concat('target', 'recessions')) {
  check(markup.includes(`class="ha-callout" data-series="${k}"`), `notes have a callout for ${k}`);
}
// A ::: left out of text.qmd doesn't fail the build: pandoc nests every later
// callout inside the open one. Walk the notes' divs and count any callout that
// opens while another is still open.
{
  const start = markup.indexOf('<details class="ha-notes">');
  const notes = markup.slice(start, markup.indexOf('</details>', start));
  let depth = 0, nested = 0;
  const open = [];  // the depth each open callout started at
  for (const [tag] of notes.matchAll(/<div\b[^>]*>|<\/div>/g)) {
    if (tag.startsWith('</')) {
      depth--;
      if (open.length && open[open.length - 1] === depth) open.pop();
    } else {
      if (/class="ha-callout"/.test(tag)) { if (open.length) nested++; open.push(depth); }
      depth++;
    }
  }
  check(nested === 0 && depth === 0, 'no note is nested inside another', `${nested} nested`);
}
check(/href="\.\.\/"/.test(markup), 'notes link the blog post');
check(markup.indexOf('class="ha-key"') < markup.indexOf('class="ha-chip"'), 'target rate is listed first');
check(/<button type="button" class="ha-chip" data-rec aria-pressed="false">/.test(markup), 'recessions button is there, and off');
check(markup.lastIndexOf('class="ha-chip" data-s=') < markup.indexOf('class="ha-chip" data-rec'), 'recessions come last');
check(/<summary>Notes and Sources<\/summary>/.test(markup), 'notes panel is labeled "Notes and Sources"');

// ---------------------------------------------------------------- CSV truth
function readCSV(file) {
  const [head, ...rows] = fs.readFileSync(path.join(DATA, file), 'utf8').trim().split(/\r?\n/);
  const cols = head.split(',');
  return rows.map(r => { const v = r.split(','); const o = {}; cols.forEach((c, i) => { o[c] = v[i]; }); return o; });
}
const dayOf = s => Math.round(Date.parse(s + 'T00:00:00Z') / 864e5);
const ffr = readCSV('fed_funds_rate.csv');
const midOn = new Map(ffr.map(r => [dayOf(r.date), +r.target_mid]));
const truth = {};
for (const r of readCSV('hairs.csv')) {
  const s = (truth[r.source] = truth[r.source] || new Map());
  const d = dayOf(r.as_of);
  if (!s.has(d)) s.set(d, []);
  s.get(d).push([dayOf(r.target_date), +r.rate_pct]);
}

// ---------------------------------------------------------------- run it
function el(id) {
  const e = {
    id, style: {}, dataset: {}, hidden: false, _l: {}, _cls: new Set(), title: '',
    clientWidth: 760, offsetWidth: 220, offsetHeight: 120, textContent: '', innerHTML: '',
    classList: { add: c => e._cls.add(c), remove: c => e._cls.delete(c), contains: c => e._cls.has(c) },
    addEventListener(t, f) { (this._l[t] = this._l[t] || []).push(f); },
    setAttribute(k, v) { this['attr:' + k] = v; }, getAttribute(k) { return this['attr:' + k] ?? null; },
    getBoundingClientRect: () => ({left: 0, top: 0, width: 760, height: 441}),
    setPointerCapture() {}, releasePointerCapture() {},
    getContext: () => new Proxy({}, { get: (t, k) => k === 'measureText' ? (s => ({width: String(s).length * 6.5})) : (k in t ? t[k] : () => {}), set: (t, k, v) => { t[k] = v; return true; } }),
  };
  return e;
}
const nodes = {};
for (const id of ids) nodes[id] = el(id);
const chips = chipKeys.map(k => { const c = el(''); c.dataset.s = k; return c; });
if (/class="ha-chip" data-rec/.test(markup)) { const c = el(''); c.dataset.rec = ''; chips.push(c); }
nodes['hairy-app'].querySelectorAll = sel => (sel === '.ha-chip' ? chips : []);
const docListeners = {};
const window = {
  devicePixelRatio: 2,
  matchMedia: q => ({matches: /reduce/.test(q)}),      // no animation: views apply at once
  getComputedStyle: () => ({fontFamily: 'sans-serif'}),
  addEventListener() {},
  HAIRY_TEST: {},
};
const context = {
  window, console, performance: {now: () => Date.now()},
  requestAnimationFrame: f => setTimeout(() => f(Date.now()), 0), cancelAnimationFrame: () => {},
  getComputedStyle: window.getComputedStyle,
  document: {
    getElementById: id => nodes[id] || null,
    createElement: () => el('offscreen'),
    addEventListener: (t, f) => { (docListeners[t] = docListeners[t] || []).push(f); },
  },
};
context.window.document = context.document;
vm.createContext(context);
try {
  vm.runInContext(script, context, {filename: 'hairy-app.js'});
  check(true, 'script runs to the end');
} catch (e) {
  check(false, 'script runs to the end', e.stack.split('\n').slice(0, 3).join(' / '));
  process.exit(1);
}
const api = window.HAIRY_TEST.api;
check(!!api, 'test hook is exposed');
const {SERIES, R} = api;

// Decoded hairs match the CSV exactly: every hair, every point, to the basis point.
for (const s of SERIES) {
  const t = truth[s.key];
  check(s.hairs.length === t.size, `${s.key}: hair count`, `${s.hairs.length} vs ${t.size}`);
  let bad = 0, anchorsBad = 0, n = 0;
  for (const h of s.hairs) {
    const want = (t.get(h.asOf) || []).slice().sort((a, b) => a[0] - b[0]);
    if (want.length !== h.px.length) { bad++; continue; }
    want.forEach(([d, v], k) => { n++; if (d !== h.px[k] || Math.abs(v - h.py[k]) > 0.005 + 1e-9) bad++; });
    const anchor = midOn.get(h.asOf + 1);
    if (anchor === undefined ? h.ri !== -1 : Math.abs(h.vy[0] - anchor) > 1e-9 || h.vx[0] !== h.asOf) anchorsBad++;
  }
  check(bad === 0, `${s.key}: every point decodes to the CSV value`, `${n} points, ${bad} off`);
  check(anchorsBad === 0, `${s.key}: hairs start on the target a day after their forecast date`);
}

// The target line: every day's midpoint is recoverable from the change points.
let rateBad = 0;
for (const [d, mid] of midOn) { const i = api.rateIndex(d); if (i < 0 || Math.abs(R.mid[i] - mid) > 1e-9) rateBad++; }
check(rateBad === 0, 'target line matches every day of fed_funds_rate.csv', `${midOn.size} days`);

// Forecaster hairs are steps across calendar quarters, as in the notebooks.
{
  const spf = SERIES.find(s => s.step);
  const h = spf.hairs[spf.hairs.length - 1];
  const q = api.quarterStart, nq = api.nextQuarterStart;
  // The notebooks' rows: the anchor, each value at its quarter start (the
  // first clipped to the forecast date), then the last value at its quarter's
  // end. Drawn horizontal-then-vertical, so every row after the anchor adds
  // two vertices at its date.
  const rows = h.px.map(d => Math.max(q(d), h.asOf)).concat(nq(h.px[h.px.length - 1]));
  const xs = [h.asOf];
  for (const x of rows) xs.push(x, x);
  check(JSON.stringify(h.vx) === JSON.stringify(xs), 'forecaster hair steps at quarter starts');
  check(h.vy.slice(-1)[0] === h.py.slice(-1)[0], 'forecaster hair holds its last value to the quarter end');
}

// Ranges: the full view holds every point; hiding series and zooming refit it.
{
  const [x0, x1] = api.fullX(), [y0, y1] = api.fitY(x0, x1);
  let lo = Infinity, hi = -Infinity, first = Infinity, last = -Infinity;
  for (const s of SERIES) for (const h of s.hairs) {
    for (const v of h.vy) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
    first = Math.min(first, h.vx[0]); last = Math.max(last, h.vx[h.vx.length - 1]);
  }
  check(x0 < first && x1 > last, 'full view spans every hair');
  check(y0 < lo && y1 > hi, 'full view fits every value', `${y0.toFixed(2)} to ${y1.toFixed(2)}`);

  api.toggle(SERIES.find(s => s.key === 'spf_median'), false);
  check(api.fullX()[0] > dayOf('1993-01-01'), 'hiding the forecasters moves the start to the Treasury hairs');
  check(!nodes['ha-sources'].textContent.includes('Philadelphia'), 'hiding a series drops its source');
  check(nodes['ha-showall'].hidden === false, '"Show all" appears once a series is hidden');
  api.toggle(SERIES.find(s => s.key === 'spf_median'), true);
  check(nodes['ha-showall'].hidden === true, '"Show all" goes away when all are shown');
  check(/^Sources: .*Philadelphia.*FRED \(target rate\)\.$/.test(nodes['ha-sources'].textContent), 'sources line lists the series, then the target');

  const z0 = dayOf('2015-01-01'), z1 = dayOf('2019-12-31');
  api.zoomTo(z0, z1);
  check(api.state.zoomed && api.state.goal.x[0] === z0 && api.state.goal.x[1] === z1, 'zoom sets the date range');
  check(nodes['ha-zoomed'].hidden === false && nodes['ha-idle'].hidden === true, 'zoom bar offers a reset when zoomed');
  const zy = api.state.goal.y;
  check(zy[1] < 6 && zy[0] > -1, 'zoomed y axis fits the window', `${zy[0].toFixed(2)} to ${zy[1].toFixed(2)}`);
  api.toggle(SERIES.find(s => s.key === 'treasury_forward'), false);
  check(api.state.goal.x[0] === z0, 'hiding a series while zoomed keeps the date range');
  api.toggle(SERIES.find(s => s.key === 'treasury_forward'), true);
  api.resetZoom();
  check(!api.state.zoomed && api.state.goal.x[0] === api.fullX()[0], 'reset returns to the full range');
}

// Hit testing finds a hair at its own drawn position, and nothing far away.
{
  api.draw();
  const g = api.geo();
  check(!!g && g.hits.length > 1000, 'every hair in view is hit-testable', g && `${g.hits.length}`);
  const e = g.hits.find(x => x.h.s.key === 'sep_median');
  const j = Math.floor(e.xs.length / 2);
  const mx = (e.xs[j - 1] + e.xs[j]) / 2, my = (e.ys[j - 1] + e.ys[j]) / 2;
  const got = api.nearest(mx, my, 9);
  check(!!got, 'a point on a hair finds a hair');
  check(api.nearest(g.ml + g.pw / 2, g.mt - 40, 9) === null, 'a point outside the plot finds nothing');
  const html2 = api.tipHTML(e.h);
  check(html2.includes('FOMC Median Projection') && html2.includes('Made ') && /End \d{4}/.test(html2), 'tooltip names the series, the date and the projections');
}

// Recessions: the right dates, off at first, and their source only when shown.
{
  const want = readCSV('nber_recessions.csv').map(r => [dayOf(r.peak), dayOf(r.trough)]);
  check(JSON.stringify(api.RECS) === JSON.stringify(want), 'recession dates match nber_recessions.csv', `${want.length} recessions`);
  check(api.state.rec === false && !nodes['ha-sources'].textContent.includes('National Bureau'), 'recessions start hidden');
  api.toggleRec(true);
  check(/; National Bureau of Economic Research via the St\. Louis Fed's FRED \(recessions\)\.$/.test(nodes['ha-sources'].textContent),
        'showing recessions adds their source, last');
  check(nodes['ha-showall'].hidden === true, '"Show all" ignores recessions');
  api.toggleRec(false);
  check(!nodes['ha-sources'].textContent.includes('National Bureau'), 'hiding recessions drops their source');
}

// Click to keep a hair's window open, through the canvas's own handlers.
{
  api.draw();
  const g = api.geo(), cv = nodes['ha-canvas'];
  const fire = (type, x, y, pointerType = 'mouse', id = 1) => (cv._l[type] || [])
    .forEach(f => f({type, pointerId: id, pointerType, button: 0, clientX: x, clientY: y, target: cv, preventDefault() {}}));
  const e = g.hits.find(x => x.h.s.key === 'sep_median');
  const j = Math.floor(e.xs.length / 2);
  const mx = (e.xs[j - 1] + e.xs[j]) / 2, my = (e.ys[j - 1] + e.ys[j]) / 2;
  const empty = [g.ml + g.pw - 3, g.mt + 3];          // top right: no hair reaches 12% in 2029
  fire('pointerdown', mx, my); fire('pointerup', mx, my);
  const kept = api.state.pin;
  check(!!kept, 'a click on a hair keeps it');
  check(nodes['ha-tip'].innerHTML.includes('Click the plot to close'), 'a kept window says how to close it');
  fire('pointermove', empty[0], empty[1]);
  check(api.state.pin === kept, 'moving the mouse away leaves it kept');
  fire('pointerdown', empty[0], empty[1]); fire('pointerup', empty[0], empty[1]);
  check(api.state.pin === null, 'the next click on the plot lets go');
  fire('pointerdown', mx, my, 'touch', 2); fire('pointerup', mx, my, 'touch', 2);
  check(!!api.state.pin, 'a tap on a hair keeps it');
  fire('pointerdown', empty[0], empty[1], 'touch', 3); fire('pointerup', empty[0], empty[1], 'touch', 3);
  check(api.state.pin === null, 'a tap on empty plot lets go');
  fire('pointerdown', mx, my); fire('pointerup', mx, my);
  (docListeners.pointerdown || []).forEach(f => f({target: {}, pointerType: 'mouse'}));
  check(api.state.pin === null, 'a click off the plot lets go');
}

// Ticks stay inside the window and read sensibly.
{
  const t = api.xTicks(dayOf('1982-01-01'), dayOf('2030-01-01'), 700);
  check(t.major.length >= 5 && t.major.every(m => /^\d{4}$/.test(m.label)), 'full range labels whole years', t.major.map(m => m.label).join(' '));
  const z = api.xTicks(dayOf('2024-01-15'), dayOf('2025-06-01'), 700);
  check(z.major.some(m => /^[A-Z][a-z]{2}$/.test(m.label)), 'a short range labels months', z.major.map(m => m.label).join(' '));
  const y = api.yTicks(-0.4, 12.3, 400);
  check(y.length >= 4 && y.length <= 10 && y.every(v => v.label.endsWith('%')), 'y ticks are percents', y.map(v => v.label).join(' '));
}

console.log(`${failures ? 'FAILED' : 'passed'}: ${passes} checks passed, ${failures} failed`);
process.exit(failures ? 1 : 0);
