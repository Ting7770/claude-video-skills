/* orbit-doc engine: one continuous camera over one illustrated world.
   Loaded by engine.html. Python calls:  await init(cfg)  then  frame(i) -> JPEG data URL.
   cfg = {W,H,fps,frames,base,world,beats,lines:[{t0,t1,text}],seed}
   Everything is deterministic in (frame index), so parallel workers render identical pixels. */
'use strict';
let CFG, W, H, MIN, FPS, NF, MAIN, mctx, TMP, tctx, SMALL, sctx, VIG, GRAIN = [];
const IM = {}, EL = {}, TL = {}; let ORDER = [], B = [], TX, TY, TR, SPD;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const lerp = (a, b, t) => a + (b - a) * t;
const eC = t => { t = clamp(t, 0, 1); return t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
const eS = t => { t = clamp(t, 0, 1); return .5 - .5 * Math.cos(Math.PI * t); };
const ease = t => .5 * eC(t) + .5 * eS(t);
const eOut = t => { t = clamp(t, 0, 1); return 1 - Math.pow(1 - t, 3); };
function rng(seed) { let s = (seed * 2654435761) >>> 0 || 1; return () => { s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; }; }
const FONT_HERO = "'Anton', Impact, sans-serif", FONT_UI = "'Avenir Next', 'Helvetica Neue', Arial, sans-serif", FONT_MONO = "Menlo, 'SF Mono', monospace";
const ACC = '#FFD23F';

// ---------- loading ----------
async function loadImg(name, max) {
  let im;
  for (let tries = 0; ; tries++) { // the local server can hiccup when several workers start at once: retry
    try { im = new Image(); im.src = CFG.base + 'img/' + encodeURIComponent(name) + (tries ? '?r=' + tries : ''); await im.decode(); break; }
    catch (err) { if (tries > 6) throw err; await new Promise(r => setTimeout(r, 400 * (tries + 1))); } }
  const k = Math.min(1, max / Math.max(im.naturalWidth, im.naturalHeight));
  IM[name] = await createImageBitmap(im, { resizeWidth: Math.round(im.naturalWidth * k), resizeHeight: Math.round(im.naturalHeight * k), resizeQuality: 'high' });
  IM[name].ar = im.naturalWidth / im.naturalHeight; im.src = '';
}

// ---------- timeline of element properties ----------
function prop(id, key, t) {
  const el = EL[id]; let v = el[key]; const segs = TL[id] && TL[id][key]; if (!segs) return v;
  for (const s of segs) {
    if (t < s.t0) break;
    if (t >= s.t1 || typeof s.to !== 'number') v = s.to;
    else v = lerp(s.from, s.to, s.lin ? (t - s.t0) / (s.t1 - s.t0) : ease((t - s.t0) / (s.t1 - s.t0)));
  }
  return v;
}
function addOp(id, key, to, t0, dur, lin) {
  if (!EL[id]) throw new Error('set: unknown element ' + id);
  TL[id] = TL[id] || {}; const L = (TL[id][key] = TL[id][key] || []);
  const from = prop(id, key, t0);
  L.push({ t0, t1: t0 + Math.max(dur, 1e-3), from: typeof from === 'number' ? from : 0, to, lin });
  L.sort((a, b) => a.t0 - b.t0);
}
function wordTime(k, word) {
  const b = B[k]; if (!word) return b.t0;
  const i = b.line.toLowerCase().indexOf(String(word).toLowerCase());
  if (i < 0) throw new Error(`beat ${k}: word "${word}" not in line`);
  return b.t0 + (b.t1 - b.t0) * (i / b.line.length) - 0.04;
}

// ---------- geometry ----------
function catmull(pts, k) { // k = float index along pts
  const n = pts.length - 1; k = clamp(k, 0, n); const i = Math.min(Math.floor(k), n - 1), u = k - i;
  const p0 = pts[Math.max(i - 1, 0)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(i + 2, n)];
  const u2 = u * u, u3 = u2 * u;
  const f = (a, b, c, d) => .5 * (2 * b + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u2 + (-a + 3 * b - 3 * c + d) * u3);
  return [f(p0[0], p1[0], p2[0], p3[0]), f(p0[1], p1[1], p2[1], p3[1])];
}
function dotPos(id, t) { const d = EL[id]; return catmull(EL[d.path].points, prop(id, 'k', t)); }
function bbox(id, t) { // {x,y,w,h} in world units
  const e = EL[id]; if (!e) throw new Error('unknown element ' + id);
  if (e.type === 'print' || e.type === 'card') { const s = sizeOf(e); return { x: e.x, y: e.y, w: s.w, h: s.h }; }
  if (e.type === 'planet' || e.type === 'sun') return { x: e.x, y: e.y, w: e.r * (e.ring ? 4.4 : 2.6), h: e.r * 2.6 };
  if (e.type === 'ring') return { x: e.cx, y: e.cy, w: e.rx * 2, h: e.ry * 2 };
  if (e.type === 'dot') { const p = dotPos(id, t); return { x: p[0], y: p[1], w: e.size * 4, h: e.size * 4 }; }
  if (e.type === 'path') { const xs = e.points.map(p => p[0]), ys = e.points.map(p => p[1]); const a = Math.min(...xs), b = Math.max(...xs), c = Math.min(...ys), d = Math.max(...ys); return { x: (a + b) / 2, y: (c + d) / 2, w: b - a, h: d - c }; }
  if (e.x !== undefined) return { x: e.x, y: e.y, w: e.w || 400, h: e.h || e.w || 400 };
  throw new Error('no bbox for ' + id);
}
function sizeOf(e) {
  if (e.type === 'card') return { w: e.w, h: e.h || e.w * 0.62 };
  const ar = IM[e.img] ? IM[e.img].ar : 1; const b = e.w * 0.035, bb = e.w * 0.085;
  return { w: e.w, h: (e.w - 2 * b) / ar + b + bb, b, bb };
}
function printPoint(id, fx, fy) { // world point at fractional image coords on a print
  const e = EL[id], s = sizeOf(e); const iw = e.w - 2 * s.b, ih = iw / IM[e.img].ar;
  const lx = -e.w / 2 + s.b + fx * iw, ly = -s.h / 2 + s.b + fy * ih, r = (e.rot || 0) * Math.PI / 180;
  return [e.x + lx * Math.cos(r) - ly * Math.sin(r), e.y + lx * Math.sin(r) + ly * Math.cos(r)];
}

// ---------- camera ----------
function shotAt(k, t) { // target {x,y,r} for beat k at time t; r = half of the visible span on the short side
  const b = B[k], c = b.cam; if (!c) return null;
  let x, y, r;
  if (c.on !== undefined) {
    const ids = [].concat(c.on);
    if (c.at) { [x, y] = printPoint(ids[0], c.at[0], c.at[1]); r = c.r; }
    else {
      let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
      for (const id of ids) { const q = bbox(id, t); x0 = Math.min(x0, q.x - q.w / 2); x1 = Math.max(x1, q.x + q.w / 2); y0 = Math.min(y0, q.y - q.h / 2); y1 = Math.max(y1, q.y + q.h / 2); }
      x = (x0 + x1) / 2; y = (y0 + y1) / 2;
      const fill = c.fill || (b.text ? .66 : .8);
      r = c.r || Math.max((y1 - y0) / (2 * fill) * MIN / H, (x1 - x0) / (2 * fill) * MIN / W);
      if (b.text) y += (0.07 * H) * (2 * r / MIN); // lift the subject so the caption sits under it
    }
  } else { x = c.x; y = c.y; r = c.r; }
  if (c.dx) x += c.dx * r; if (c.dy) y += c.dy * r;
  return { x, y, r };
}
function vwn(p0, p1) { // van Wijk & Nuij smooth zoom+pan, w = 2r
  const rho = 1.42, w0 = 2 * p0.r, w1 = 2 * p1.r, dx = p1.x - p0.x, dy = p1.y - p0.y, d = Math.hypot(dx, dy);
  if (d < 1e-4 * Math.max(w0, w1)) {
    const S = Math.abs(Math.log(w1 / w0)) / rho, k = Math.sign(Math.log(w1 / w0));
    return { S, f: s => ({ x: p0.x + dx * (S ? s / S : 1), y: p0.y + dy * (S ? s / S : 1), r: p0.r * Math.exp(k * rho * s) }) };
  }
  const b0 = (w1 * w1 - w0 * w0 + rho ** 4 * d * d) / (2 * w0 * rho * rho * d), b1 = (w1 * w1 - w0 * w0 - rho ** 4 * d * d) / (2 * w1 * rho * rho * d);
  const r0 = Math.log(Math.sqrt(b0 * b0 + 1) - b0), r1 = Math.log(Math.sqrt(b1 * b1 + 1) - b1), S = (r1 - r0) / rho;
  return { S, f: s => { const u = w0 / (rho * rho) * (Math.cosh(r0) * Math.tanh(rho * s + r0) - Math.sinh(r0)); return { x: p0.x + dx / d * u, y: p0.y + dy / d * u, r: p0.r * Math.cosh(r0) / Math.cosh(rho * s + r0) }; } };
}
function buildTrack() {
  TX = new Float64Array(NF); TY = new Float64Array(NF); TR = new Float64Array(NF);
  const st = B.map((b, k) => k === 0 ? 0 : b.t0 - (b.cam && b.cam.lead !== undefined ? b.cam.lead : 0.35));
  let cur = null, act = -1, tr = null, last = { x: 0, y: 0, r: 1 }, dir = [1, 0.25];
  for (let f = 0; f < NF; f++) {
    const t = f / FPS; let k = act;
    while (k + 1 < B.length && st[k + 1] <= t) k++;
    if (k !== act) { // new shot begins: plan the move from where we are
      act = k; const b = B[k];
      if (!b.cam || b.cam.same) { tr = tr ? { ...tr, keep: true } : null; }
      else {
        const from = cur || shotAt(k, t);
        const dur0 = b.cam.dur === 'beat' ? b.t1 + .3 - t : null;
        const arr = t + (dur0 || 1.6); const to = shotAt(k, arr);
        const P = vwn(from, to); const D = dur0 || b.cam.dur || clamp(0.75 + 0.48 * P.S, 0.9, 3.6);
        const mv = [to.x - from.x, to.y - from.y]; const ml = Math.hypot(...mv);
        if (ml > 0.3 * to.r) dir = [mv[0] / ml, mv[1] / ml];
        tr = { k, t0: t, D, P, to, follow: !!b.cam.follow, push: b.cam.push !== undefined ? b.cam.push : 0.014, drift: b.cam.drift !== undefined ? b.cam.drift : 0.006, dir: dir.slice() };
        if (k === 0) tr.D = 0.001;
      }
    }
    let p;
    if (!tr) p = cur;
    else if (t < tr.t0 + tr.D) p = tr.P.f(ease((t - tr.t0) / tr.D) * tr.P.S);
    else {
      const h = t - (tr.t0 + tr.D); let base = tr.to;
      if (tr.follow) { const q = shotAt(tr.k, t); base = { x: q.x, y: q.y, r: tr.to.r }; }
      const r = base.r * Math.exp(-tr.push * h);
      p = { x: base.x + tr.dir[0] * tr.drift * h * base.r, y: base.y + tr.dir[1] * tr.drift * h * base.r, r };
    }
    cur = p; TX[f] = p.x; TY[f] = p.y; TR[f] = Math.log(p.r);
  }
  // gaussian smoothing removes any corner in velocity; camera never stops dead (hold drift + push)
  const sig = 0.16 * FPS, R = Math.ceil(3 * sig), ker = []; let ks = 0;
  for (let i = -R; i <= R; i++) { const v = Math.exp(-i * i / (2 * sig * sig)); ker.push(v); ks += v; }
  for (const A of [TX, TY, TR]) {
    const src = A.slice();
    for (let f = 0; f < NF; f++) { let s = 0; for (let i = -R; i <= R; i++) s += src[clamp(f + i, 0, NF - 1)] * ker[i + R]; A[f] = s / ks; }
  }
  SPD = new Float64Array(NF);
  for (let f = 0; f < NF; f++) {
    const a = Math.max(f - 1, 0), b = Math.min(f + 1, NF - 1), s = MIN / (2 * Math.exp(TR[f]));
    SPD[f] = (Math.hypot(TX[b] - TX[a], TY[b] - TY[a]) * s + Math.abs(TR[b] - TR[a]) * MIN * 0.5) / Math.max(b - a, 1);
  }
}
function camAt(ff) {
  const f0 = clamp(Math.floor(ff), 0, NF - 1), f1 = Math.min(f0 + 1, NF - 1), u = clamp(ff - f0, 0, 1);
  return { x: lerp(TX[f0], TX[f1], u), y: lerp(TY[f0], TY[f1], u), r: Math.exp(lerp(TR[f0], TR[f1], u)) };
}

// ---------- scene ----------
let STARS, FAR;
function lw(c, worldW, minPx, s) { c.lineWidth = Math.max(worldW, minPx / s); }
function setWorld(c, cam, t) {
  const s = MIN / (2 * cam.r), hh = CFG.handheld === undefined ? 1 : CFG.handheld;
  const jx = hh * (2.2 * Math.sin(t * 0.83 + 1.3) + 1.3 * Math.sin(t * 1.91 + 0.2) + 0.6 * Math.sin(t * 3.7));
  const jy = hh * (1.8 * Math.sin(t * 0.71 + 2.1) + 1.2 * Math.sin(t * 2.33 + 0.9) + 0.5 * Math.sin(t * 4.1 + 1));
  const rot = hh * 0.0011 * Math.sin(t * 0.53 + 0.4);
  const cs = Math.cos(rot) * s, sn = Math.sin(rot) * s;
  c.setTransform(cs, sn, -sn, cs, W / 2 + jx - (cs * cam.x - sn * cam.y), H / 2 + jy - (sn * cam.x + cs * cam.y));
  return s;
}
function view(cam) { const hw = cam.r * W / MIN * 1.15, hh = cam.r * H / MIN * 1.15; return { x0: cam.x - hw, x1: cam.x + hw, y0: cam.y - hh, y1: cam.y + hh }; }
function inView(v, x, y, rad) { return x + rad > v.x0 && x - rad < v.x1 && y + rad > v.y0 && y - rad < v.y1; }

function drawEl(c, id, t, s, v, hero) {
  const e = EL[id], a = prop(id, 'a', t); if (!(a > 0.002)) return;
  c.save(); c.globalAlpha = clamp(a, 0, 1);
  try { DRAW[e.type](c, e, id, t, s, v, hero); } finally { c.restore(); }
}
const DRAW = {
  glow(c, e) { const g = c.createRadialGradient(e.x, e.y, 0, e.x, e.y, e.r); g.addColorStop(0, e.color); g.addColorStop(1, 'rgba(0,0,0,0)'); c.fillStyle = g; c.fillRect(e.x - e.r, e.y - e.r, 2 * e.r, 2 * e.r); },
  bubble(c, e, id, t, s) { // the heliosphere: warm interior wash + glowing edge
    c.save(); c.beginPath(); c.ellipse(e.cx, e.cy, e.rx, e.ry, 0, 0, Math.PI * 2);
    const g = c.createRadialGradient(e.cx, e.cy, 0, e.cx, e.cy, e.rx); g.addColorStop(0, 'rgba(255,170,80,0.10)'); g.addColorStop(.7, 'rgba(120,90,140,0.05)'); g.addColorStop(1, 'rgba(90,120,200,0.08)');
    c.save(); c.translate(e.cx, e.cy); c.scale(1, e.ry / e.rx); c.translate(-e.cx, -e.cy); c.fillStyle = g; c.fill(); c.restore();
    const gl = prop(id, 'glow', t) || 0;
    c.strokeStyle = `rgba(150,200,255,${0.35 + 0.6 * gl})`; lw(c, 26, 1.6 + 2 * gl, s); c.shadowColor = 'rgba(120,190,255,0.9)'; c.shadowBlur = 8 + 30 * gl; c.stroke(); c.restore();
  },
  ring(c, e, id, t, s) {
    const gl = prop(id, 'glow', t) || 0; c.beginPath(); c.ellipse(e.cx, e.cy, e.rx, e.ry, 0, 0, Math.PI * 2);
    if (e.dash) c.setLineDash(e.dash.map(d => Math.max(d, d * 3 / (s * 30)))); c.strokeStyle = e.color || 'rgba(200,220,255,.4)';
    lw(c, e.width || 12, 1.2 + 2 * gl, s); if (gl > 0) { c.shadowColor = e.color || '#fff'; c.shadowBlur = 25 * gl; } c.stroke(); c.setLineDash([]);
    if (e.label) { c.font = `${e.labelSize}px ${FONT_HERO}`; c.fillStyle = e.labelColor || '#fff'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.shadowColor = 'rgba(0,0,0,.6)'; c.shadowBlur = 12; c.fillText(e.label, e.labelAt[0], e.labelAt[1]); }
  },
  orbits(c, e, id, t, s) { c.strokeStyle = 'rgba(160,185,235,0.22)'; lw(c, 6, 1, s); for (const r of e.radii) { c.beginPath(); c.ellipse(e.cx, e.cy, r, r * e.flat, 0, 0, Math.PI * 2); c.stroke(); } },
  sun(c, e, id, t) {
    const R = e.r, pul = 1 + 0.03 * Math.sin(t * 1.3);
    let g = c.createRadialGradient(e.x, e.y, 0, e.x, e.y, R * 7 * pul); g.addColorStop(0, 'rgba(255,220,150,.55)'); g.addColorStop(.25, 'rgba(255,170,70,.18)'); g.addColorStop(1, 'rgba(255,140,40,0)');
    c.fillStyle = g; c.fillRect(e.x - R * 7, e.y - R * 7, R * 14, R * 14);
    g = c.createRadialGradient(e.x - R * .2, e.y - R * .2, 0, e.x, e.y, R); g.addColorStop(0, '#FFF8E0'); g.addColorStop(.6, '#FFD27A'); g.addColorStop(1, '#F59A2B');
    c.fillStyle = g; c.beginPath(); c.arc(e.x, e.y, R, 0, Math.PI * 2); c.fill();
  },
  planet(c, e, id, t, s, v) {
    if (!inView(v, e.x, e.y, e.r * 4)) return; const R = e.r, sx = EL.sun ? EL.sun.x : e.x - 1000;
    if (e.ring) { c.save(); c.beginPath(); c.ellipse(e.x, e.y, R * 2.1, R * .55, -0.18, Math.PI, Math.PI * 2); c.strokeStyle = e.ring; lw(c, R * .28, 1, s); c.stroke(); c.restore(); }
    if (e.haze) { const h = c.createRadialGradient(e.x, e.y, R * .8, e.x, e.y, R * 1.9); h.addColorStop(0, e.haze); h.addColorStop(1, 'rgba(0,0,0,0)'); c.fillStyle = h; c.beginPath(); c.arc(e.x, e.y, R * 1.9, 0, 7); c.fill(); }
    const g = c.createRadialGradient(e.x - R * .45 * Math.sign(e.x - sx || 1), e.y - R * .3, R * .1, e.x, e.y, R);
    g.addColorStop(0, e.color[0]); g.addColorStop(1, e.color[1]); c.fillStyle = g; c.beginPath(); c.arc(e.x, e.y, R, 0, Math.PI * 2); c.fill();
    if (e.bands) { c.save(); c.clip(); c.globalAlpha *= .35; for (let i = -4; i <= 4; i++) { c.fillStyle = i % 2 ? '#7a4a2a' : '#f3dcc0'; c.fillRect(e.x - R, e.y + i * R * .22 - R * .06, R * 2, R * .1); } c.restore(); }
    const sh = c.createLinearGradient(e.x - R, e.y, e.x + R, e.y); sh.addColorStop(0, 'rgba(0,0,0,0)'); sh.addColorStop(.3, 'rgba(0,0,0,0)'); sh.addColorStop(.7, 'rgba(2,4,12,.3)'); sh.addColorStop(1, 'rgba(2,4,12,.72)');
    c.fillStyle = sh; c.beginPath(); c.arc(e.x, e.y, R, 0, Math.PI * 2); c.fill();
    if (e.ring) { c.beginPath(); c.ellipse(e.x, e.y, R * 2.1, R * .55, -0.18, 0, Math.PI); c.strokeStyle = e.ring; lw(c, R * .28, 1, s); c.stroke(); }
  },
  path(c, e, id, t, s) {
    const dot = e.dot ? EL[e.dot] : null; const kmax = dot ? prop(e.dot, 'k', t) : (prop(id, 'reveal', t) ?? e.points.length - 1);
    const vis = dot ? prop(e.dot, 'vis', t) : 1; if (kmax <= 0.001 || vis <= 0.002) return;
    c.globalAlpha *= vis; c.beginPath(); const st = 0.04; let p = catmull(e.points, 0); c.moveTo(p[0], p[1]);
    for (let k = st; k < kmax; k += st) { p = catmull(e.points, k); c.lineTo(p[0], p[1]); } p = catmull(e.points, kmax); c.lineTo(p[0], p[1]);
    if (e.dash) c.setLineDash(e.dash.map(d => d / Math.min(1, s * 8)));
    c.strokeStyle = e.color; lw(c, e.width || 10, 2, s); c.shadowColor = e.color; c.shadowBlur = 10; c.lineCap = 'round'; c.stroke(); c.setLineDash([]);
  },
  dot(c, e, id, t, s) {
    const vis = prop(id, 'vis', t); if (vis <= 0.002) return; c.globalAlpha *= vis;
    const [x, y] = dotPos(id, t), gl = prop(id, 'glow', t) ?? 1, fl = prop(id, 'flash', t) || 0;
    const R = Math.max(e.size, 5 / s);
    let g = c.createRadialGradient(x, y, 0, x, y, R * 5); g.addColorStop(0, e.color); g.addColorStop(.25, e.color + '55'); g.addColorStop(1, e.color + '00');
    c.globalAlpha *= 0.25 + 0.75 * gl; c.fillStyle = g; c.beginPath(); c.arc(x, y, R * 5, 0, 7); c.fill();
    if (fl > 0.01 && fl < 0.99) { c.strokeStyle = `rgba(255,255,255,${1 - fl})`; lw(c, R * .2, 1.5, s); c.beginPath(); c.arc(x, y, R * (1 + 5 * fl), 0, 7); c.stroke(); }
    // craft silhouette when big enough
    const px = e.size * s; c.fillStyle = '#fff';
    if (px > 10) {
      c.save(); c.translate(x, y); c.rotate((prop(id, 'rot', t) || 0) * Math.PI / 180); const z = e.size;
      c.strokeStyle = '#EAF2FF'; lw(c, z * .05, 1, s);
      c.beginPath(); c.ellipse(0, 0, z * .55, z * .18, 0, 0, 7); c.fillStyle = '#DCE6F5'; c.fill(); c.stroke();
      c.beginPath(); c.moveTo(0, z * .1); c.lineTo(0, z * .35); c.moveTo(-z * .1, z * .3); c.lineTo(-z * 1.6, z * .7); c.moveTo(z * .1, z * .3); c.lineTo(z * 1.1, z * .65); c.stroke();
      c.fillStyle = '#9fb0c8'; c.fillRect(-z * .2, z * .28, z * .4, z * .18); c.restore();
    } else { c.beginPath(); c.arc(x, y, R * .6, 0, 7); c.fill(); }
    if (e.label && px > 6) { c.font = `600 ${e.size * .9}px ${FONT_UI}`; c.fillStyle = 'rgba(255,255,255,.85)'; c.fillText(e.label, x + e.size * 1.4, y - e.size * .8); }
  },
  thread(c, e, id, t, s) {
    const [x1, y1] = dotPos(e.to, t), x0 = EL[e.from].x, y0 = EL[e.from].y; const st = prop(id, 'static', t) || 0;
    const n = 160, dx = x1 - x0, dy = y1 - y0, L = Math.hypot(dx, dy), nx = -dy / L, ny = dx / L, r = rng(Math.floor(t * 30) + 7);
    c.beginPath(); for (let i = 0; i <= n; i++) { const u = i / n, j = st * (r() - .5) * 2 * Math.max(90, 26 / s) * Math.sin(Math.PI * u); c.lineTo(x0 + dx * u + nx * j, y0 + dy * u + ny * j); }
    c.strokeStyle = st > .5 ? `rgba(225,215,215,.9)` : 'rgba(170,225,255,.95)'; lw(c, 12, 3.2, s); c.shadowColor = '#7fd4ff'; c.shadowBlur = 16 * (1 - st); c.stroke();
    const p = prop(id, 'pulse', t); if (p >= 0 && p <= 1) {
      const px = x0 + dx * p, py = y0 + dy * p, R = Math.max(140, 26 / s); const g = c.createRadialGradient(px, py, 0, px, py, R);
      g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(.3, 'rgba(150,220,255,.6)'); g.addColorStop(1, 'rgba(150,220,255,0)'); c.fillStyle = g; c.beginPath(); c.arc(px, py, R, 0, 7); c.fill();
    }
  },
  wind(c, e, id, t, s, v) {
    const r = rng(5); c.strokeStyle = 'rgba(255,214,150,.55)'; lw(c, 10, 1.1, s); c.lineCap = 'round';
    for (let i = 0; i < e.n; i++) { const ang = r() * Math.PI * 2, sp = 900 + r() * 900, ph = r(); const d = e.r0 + ((t * sp / e.R + ph) % 1) * e.R; const L = 160 + r() * 260;
      const x = e.x + Math.cos(ang) * d, y = e.y + Math.sin(ang) * d * e.flat; if (!inView(v, x, y, L)) continue;
      c.globalAlpha = prop(id, 'a', t) * (1 - d / (e.r0 + e.R)) * .9; c.beginPath(); c.moveTo(x, y); c.lineTo(x + Math.cos(ang) * L, y + Math.sin(ang) * L * e.flat); c.stroke(); }
  },
  burst(c, e, id, t, s) {
    const p = prop(id, 'p', t); if (p <= 0.001 || p >= 0.999) return; const B2 = EL[e.of];
    c.beginPath(); c.ellipse(B2.cx, B2.cy, B2.rx * p * 1.05, B2.ry * p * 1.05, 0, 0, 7); c.strokeStyle = 'rgba(255,240,210,.95)'; lw(c, 60, 3, s); c.shadowColor = '#ffd27a'; c.shadowBlur = 30; c.stroke();
    c.globalAlpha *= .4; lw(c, 260, 10, s); c.stroke();
  },
  drape(c, e, id, t, s) {
    const B2 = EL[e.of]; c.strokeStyle = 'rgba(140,200,255,.55)'; lw(c, 14, 1.3, s); c.setLineDash([400, 260]); c.lineDashOffset = -t * 300;
    for (let i = 1; i <= e.n; i++) for (const sg of [-1, 1]) {
      const gap = i * e.gap; c.beginPath();
      for (let x = B2.cx - B2.rx * 1.6; x <= B2.cx + B2.rx * 1.9; x += 150) { const u = (x - B2.cx) / (B2.rx + gap); const h = Math.max(B2.ry + gap - 0.0 * i, 0) * Math.sqrt(Math.max(0, 1 - u * u)); const yy = B2.cy + sg * Math.max(h, (B2.ry + gap) * 0.25 + i * e.gap * .6); c.lineTo(x, yy); }
      c.stroke(); }
    c.setLineDash([]);
  },
  ripples(c, e, id, t, s) {
    const [x, y] = e.at ? e.at : dotPos(e.dot, t); for (let i = 0; i < 5; i++) { const u = ((t * .25 + i / 5) % 1); c.globalAlpha = prop(id, 'a', t) * (1 - u) * .6; c.strokeStyle = '#9fd0ff'; lw(c, 10, 1.2, s); c.beginPath(); c.arc(x, y, e.r * u, 0, 7); c.stroke(); }
  },
  print(c, e, id, t, s, v, hero) { const a = prop(id, 'a', t); drawPaper(c, e, s, a, () => { const S = sizeOf(e), iw = e.w - 2 * S.b; c.drawImage(IM[e.img], -e.w / 2 + S.b, -S.h / 2 + S.b, iw, iw / IM[e.img].ar); }, true); },
  card(c, e, id, t, s) { const a = prop(id, 'a', t); drawPaper(c, e, s, a, () => CARD[e.kind](c, e, id, t, s), false); },
  label(c, e) { c.font = `${e.size}px ${FONT_HERO}`; c.fillStyle = e.color || '#fff'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.letterSpacing = `${Math.round(e.size * .03)}px`; c.shadowColor = 'rgba(0,0,0,.7)'; c.shadowBlur = 20; c.fillText(e.text, e.x, e.y); c.letterSpacing = '0px'; },
  mark(c, e, id, t, s) { const [x, y] = printPoint(e.on, e.at[0], e.at[1]); c.strokeStyle = ACC; lw(c, e.r * .06, 2.5, s); c.shadowColor = ACC; c.shadowBlur = 10; c.beginPath(); c.arc(x, y, e.r, 0, 7); c.stroke(); },
};
function drawPaper(c, e, s, a, inner, isPrint) {
  const S = sizeOf(e), k = eOut(clamp(a, 0, 1)); const sc = lerp(1.16, 1, k) + 0.012 * Math.sin(Math.PI * clamp(a * 1.25, 0, 1)) * (1 - k);
  c.globalAlpha *= clamp(a * 2.4, 0, 1);
  c.translate(e.x, e.y - (1 - k) * S.h * .12); c.rotate(((e.rot || 0) + (1 - k) * 5) * Math.PI / 180); c.scale(sc, sc);
  const blur = clamp(e.w * 0.035 * s, 2, 70) * (1 + (1 - k) * 1.6);
  c.shadowColor = 'rgba(0,0,0,.6)'; c.shadowBlur = blur; c.shadowOffsetY = blur * .45;
  if (isPrint) { c.fillStyle = '#EEE8DA'; c.fillRect(-e.w / 2, -S.h / 2, e.w, S.h); }
  else { c.fillStyle = '#0A1222'; c.beginPath(); c.roundRect(-e.w / 2, -S.h / 2, e.w, S.h, e.w * .02); c.fill(); }
  c.shadowColor = 'transparent'; c.shadowBlur = 0; c.shadowOffsetY = 0;
  if (!isPrint) { c.strokeStyle = 'rgba(140,175,235,.55)'; lw(c, e.w * .004, 1, s); c.stroke(); }
  inner();
  if (isPrint && e.credit) { c.fillStyle = 'rgba(40,40,48,.75)'; c.font = `${S.bb * .3}px ${FONT_MONO}`; c.textAlign = 'right'; c.textBaseline = 'middle'; c.fillText(e.credit, e.w / 2 - S.b, S.h / 2 - S.bb / 2); }
  if (!isPrint && e.note) { const h = sizeOf(e).h; c.fillStyle = 'rgba(190,205,235,.8)'; c.font = `italic ${e.w * .028}px ${FONT_UI}`; c.textAlign = 'left'; c.textBaseline = 'alphabetic'; c.fillText(e.note, -e.w / 2 + e.w * .04, h / 2 - e.w * .035); }
}

// ---------- drawn diagrams (cards) ----------
function axes(c, e, s, x0, y0, x1, y1) { c.strokeStyle = 'rgba(160,185,230,.5)'; lw(c, e.w * .003, 1, s); c.beginPath(); c.moveTo(x0, y0); c.lineTo(x0, y1); c.lineTo(x1, y1); c.stroke(); }
function icon(c, kind, x, y, r) {
  if (kind === 'sun') { c.fillStyle = '#FFC857'; c.beginPath(); c.arc(x, y, r * .55, 0, 7); c.fill(); c.strokeStyle = '#FFC857'; c.lineWidth = r * .12; for (let i = 0; i < 8; i++) { const a = i * Math.PI / 4; c.beginPath(); c.moveTo(x + Math.cos(a) * r * .75, y + Math.sin(a) * r * .75); c.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r); c.stroke(); } }
  else { c.strokeStyle = '#8FD3FF'; c.lineWidth = r * .14; c.beginPath(); for (let a = 0; a < 9; a += .1) { const rr = r * a / 9; c.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr * .6); } c.stroke(); }
}
const CARD = {
  gauge(c, e, id, t, s) { // two particle counts: solar (falls) and galactic (rises)
    const w = e.w, h = sizeOf(e).h, x0 = -w * .38, x1 = w * .44, y0 = -h * .34, y1 = h * .28; axes(c, e, s, x0, y0, x1, y1);
    const p1 = prop(id, 'p1', t), p2 = prop(id, 'p2', t), xm = lerp(x0, x1, .55), r = rng(3);
    const line = (col, yA, yB, p, seed) => { const rr = rng(seed); c.strokeStyle = col; lw(c, w * .008, 2, s); c.beginPath(); const xe = lerp(x0, x1, .55 + .45 * p);
      for (let x = x0; x <= xe; x += w * .006) { const after = x > xm; const yy = (after ? yB : yA) + (rr() - .5) * h * .03; c.lineTo(x, yy); } c.stroke(); };
    line('#FFC857', lerp(y0, y1, .2), lerp(y0, y1, .93), p1, 4); line('#8FD3FF', lerp(y0, y1, .75), lerp(y0, y1, .08), p2, 9);
    c.strokeStyle = 'rgba(255,255,255,.35)'; c.setLineDash([w * .01, w * .01]); c.beginPath(); c.moveTo(xm, y0); c.lineTo(xm, y1); c.stroke(); c.setLineDash([]);
    icon(c, 'sun', x0 - w * .06, lerp(y0, y1, .2), w * .028); icon(c, 'gal', x0 - w * .06, lerp(y0, y1, .75), w * .03);
  },
  tone(c, e, id, t, s) { const w = e.w, h = sizeOf(e).h, x0 = -w * .4, x1 = w * .42, y0 = -h * .3, y1 = h * .26; axes(c, e, s, x0, y0, x1, y1);
    const p = prop(id, 'p', t), xe = lerp(x0, x1, p), rr = rng(11); c.strokeStyle = '#8FD3FF'; lw(c, w * .007, 2, s); c.shadowColor = '#8FD3FF'; c.shadowBlur = 8; c.beginPath();
    for (let x = x0; x <= xe; x += w * .005) { const u = (x - x0) / (x1 - x0); c.lineTo(x, lerp(y1 - h * .12, y0 + h * .2, u * .55) + Math.sin(u * 60) * h * .006 + (rr() - .5) * h * .012); } c.stroke(); },
  trace(c, e, id, t, s) { const w = e.w, h = sizeOf(e).h, x0 = -w * .4, x1 = w * .42, y0 = -h * .3, y1 = h * .26; axes(c, e, s, x0, y0, x1, y1);
    const p = prop(id, 'p', t), xe = lerp(x0, x1, p), xs = lerp(x0, x1, .5), rr = rng(21); const hi = prop(id, 'hi', t) || 0;
    c.strokeStyle = '#FFD23F'; lw(c, w * .007, 2, s); c.beginPath();
    for (let x = x0; x <= xe; x += w * .005) { const up = 1 / (1 + Math.exp(-(x - xs) / (w * .006))); c.lineTo(x, lerp(y1 - h * .15, y0 + h * .18, up) + (rr() - .5) * h * .035 + Math.sin(x * .02) * h * .01); } c.stroke();
    if (hi > 0) { c.globalAlpha *= hi; c.strokeStyle = 'rgba(255,210,63,.6)'; c.setLineDash([w * .012, w * .01]); c.beginPath(); c.moveTo(xs, y0 + h * .18); c.lineTo(x1, y0 + h * .18); c.stroke(); c.setLineDash([]); } },
  memory(c, e, id, t, s) { const w = e.w, h = sizeOf(e).h, cols = 28, rows = 14, cw = w * .86 / cols, ch = h * .74 / rows, ox = -w * .43, oy = -h * .42, rr = rng(31);
    const red = prop(id, 'red', t) || 0, chip = prop(id, 'chip', t) || 0, sc = prop(id, 'scatter', t) || 0; c.font = `${ch * .8}px ${FONT_MONO}`; c.textAlign = 'center'; c.textBaseline = 'middle';
    const bad = (i, j) => i >= 17 && i < 23 && j >= 5 && j < 7; // 12 cells of 392, about 3%
    const dest = [[3, 1], [9, 12], [25, 2], [14, 10], [6, 6], [21, 12], [1, 9], [11, 3], [26, 8], [18, 1], [4, 13], [23, 10]]; let q = 0;
    for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) { const ch1 = rr() < .5 ? '0' : '1'; let x = ox + (i + .5) * cw, y = oy + (j + .5) * ch;
      if (bad(i, j)) { c.fillStyle = `rgba(255,70,70,${red})`; c.fillRect(x - cw * .48, y - ch * .48, cw * .96, ch * .96); c.fillStyle = red > .5 ? '#fff' : 'rgba(180,200,235,.8)'; c.fillText(ch1, x, y);
        if (sc > 0) { const d = dest[q++ % dest.length], tx = ox + (d[0] + .5) * cw, ty = oy + (d[1] + .5) * ch; const u = ease(clamp(sc * 1.3 - q * .025, 0, 1)); c.fillStyle = '#5BE38C'; c.fillRect(lerp(x, tx, u) - cw * .42, lerp(y, ty, u) - ch * .42, cw * .84, ch * .84); } }
      else { c.fillStyle = 'rgba(180,200,235,.75)'; c.fillText(ch1, x, y); } }
    if (chip > 0) { c.strokeStyle = `rgba(255,210,63,${chip})`; lw(c, w * .006, 2, s); c.strokeRect(ox + 16.6 * cw, oy + 4.6 * ch, 6.8 * cw, 2.8 * ch); } },
  craft(c, e, id, t, s) { const w = e.w, h = sizeOf(e).h, z = w * .2; c.save(); c.translate(-w * .05, -h * .05);
    c.strokeStyle = '#DCE6F5'; lw(c, w * .004, 1, s); c.fillStyle = 'rgba(220,230,245,.12)'; c.beginPath(); c.ellipse(0, -z * .5, z * 1.15, z * .32, 0, 0, 7); c.fill(); c.stroke();
    c.beginPath(); c.moveTo(0, -z * .2); c.lineTo(0, z * .2); c.stroke(); c.strokeRect(-z * .35, z * .2, z * .7, z * .35);
    c.beginPath(); c.moveTo(z * .35, z * .4); c.lineTo(z * 1.9, z * .9); c.moveTo(-z * .35, z * .4); c.lineTo(-z * 1.6, z * 1.0); c.stroke();
    const gen = prop(id, 'gen', t) ?? 1; for (let i = 0; i < 3; i++) { const gx = -z * (.75 + i * .3), gy = z * (.62 + i * .13); c.fillStyle = `rgba(255,${150 + 60 * gen},60,${.25 + .75 * gen})`; c.shadowColor = '#ff9a3c'; c.shadowBlur = 25 * gen; c.fillRect(gx - z * .1, gy - z * .07, z * .2, z * .14); } c.shadowBlur = 0;
    const lit = prop(id, 'lit', t) ?? 10, pl = prop(id, 'plasma', t) ?? 1; for (let i = 0; i < 10; i++) { const lx = z * (.6 + i * .13), ly = z * (.52 + i * .043); const on = i === 0 ? pl > .5 && lit > i : lit > i; c.fillStyle = on ? '#5BE38C' : 'rgba(120,130,150,.6)'; c.shadowColor = '#5BE38C'; c.shadowBlur = on ? 14 : 0; c.beginPath(); c.arc(lx, ly, z * .045, 0, 7); c.fill(); } c.shadowBlur = 0;
    const hs = prop(id, 'heat', t) || 0; for (let i = 0; i < 6; i++) { const hx = -z * .3 + (i % 3) * z * .3, hy = z * .1 + Math.floor(i / 3) * z * .55; const sw = i % 2 === 0 ? hs : 0; c.fillStyle = sw > .5 ? '#8FD3FF' : '#FF9A3C'; c.globalAlpha *= 1; c.fillRect(hx - z * .05, hy - z * .05, z * .1, z * .1); }
    const th = prop(id, 'thr', t) || 0; for (let i = 0; i < 2; i++) { const tx = (i ? 1 : -1) * z * .45, ty = z * .58; const on = i === 0 ? 1 - th : th; c.fillStyle = `rgba(255,255,255,${.25 + .75 * on})`; c.beginPath(); c.moveTo(tx - z * .05, ty); c.lineTo(tx + z * .05, ty); c.lineTo(tx, ty + z * .12); c.fill(); if (on > .5) { c.fillStyle = 'rgba(143,211,255,.7)'; c.beginPath(); c.moveTo(tx - z * .03, ty + z * .12); c.lineTo(tx + z * .03, ty + z * .12); c.lineTo(tx, ty + z * .3); c.fill(); } }
    c.restore(); },
};

// ---------- beats, heroes, text ----------
function activeBeat(t) { let k = 0; while (k + 1 < B.length && B[k + 1].t0 - 0.25 <= t) k++; return k; }
function heroesOf(k) { return k < 0 ? [] : [].concat(B[k].hero || []); }
function dimOf(k) { const b = B[k]; if (b.dim !== undefined) return b.dim; if (b.hero) return .58; if (b.text) return .6; return 0; }
function drawScene(c, t, cam) {
  c.setTransform(1, 0, 0, 1, 0, 0); c.globalAlpha = 1; c.globalCompositeOperation = 'source-over';
  c.fillStyle = CFG.world.bg || '#04060D'; c.fillRect(0, 0, W, H);
  const s0 = MIN / (2 * cam.r); // far stars: screen space with slight parallax
  for (const st of FAR) { const x = ((st[0] - cam.x * s0 * 0.015) % W + W) % W, y = ((st[1] - cam.y * s0 * 0.015) % H + H) % H; c.globalAlpha = st[2] * (.75 + .25 * Math.sin(t * st[3] + st[0])); c.fillStyle = '#cfe0ff'; c.fillRect(x, y, st[4], st[4]); }
  c.globalAlpha = 1; const s = setWorld(c, cam, t), v = view(cam);
  for (const st of STARS) { if (st[0] < v.x0 || st[0] > v.x1 || st[1] < v.y0 || st[1] > v.y1) continue; c.globalAlpha = st[2]; c.fillStyle = '#fff'; const z = clamp(st[3] * s * .12, 1.1, 2.6) / s; c.fillRect(st[0], st[1], z, z); }
  c.globalAlpha = 1;
  const k = activeBeat(t), b = B[k], pk = k - 1, u = clamp((t - (b.t0 - 0.25)) / 0.45, 0, 1);
  const hs = new Set([...heroesOf(k), ...(u < 1 ? heroesOf(pk) : [])]);
  for (const id of ORDER) if (!hs.has(id)) drawEl(c, id, t, s, v, false);
  const dim = lerp(pk >= 0 ? dimOf(pk) : 0, dimOf(k), ease(u));
  if (dim > 0.01) { c.save(); c.setTransform(1, 0, 0, 1, 0, 0); c.fillStyle = `rgba(2,3,9,${dim})`; c.fillRect(0, 0, W, H); c.restore(); }
  for (const id of ORDER) if (hs.has(id)) { // heroes over the veil; the outgoing hero sinks back under it
    const cur = heroesOf(k).includes(id); c.save(); setWorld(c, cam, t);
    if (!cur) c.globalAlpha = 1 - ease(u) * .6; drawEl(c, id, t, s, v, true); c.restore(); }
}
function wrap(c, text, maxW) { const words = text.split(' '), out = []; let line = '';
  for (const w of words) { const tr = line ? line + ' ' + w : w; if (c.measureText(tr).width > maxW && line) { out.push(line); line = w; } else line = tr; } if (line) out.push(line); return out; }
function drawText(c, t) {
  c.setTransform(1, 0, 0, 1, 0, 0);
  for (let k = 0; k < B.length; k++) { const b = B[k]; if (!b.text) continue;
    const ta = b._tw, tb = Math.min(b.t1 + 0.35, k + 1 < B.length ? B[k + 1].t0 + 0.1 : 1e9) + (b.textHold || 0);
    if (t < ta - .01 || t > tb + .3) continue; const a = clamp((t - ta) / .28, 0, 1) * clamp((tb + .3 - t) / .3, 0, 1); if (a <= 0) continue;
    const cap = b.hero && !b.textBig; const size = Math.round(MIN * (cap ? 0.078 : (b.textSize || 0.135)));
    c.font = `${size}px ${FONT_HERO}`; c.textAlign = 'center'; c.textBaseline = 'alphabetic'; c.letterSpacing = `${Math.round(size * .03)}px`;
    const lines = wrap(c, b.text, W * .86), lh = size * 1.08, rise = (1 - eOut(a)) * size * .12;
    let y = cap ? H - MIN * 0.075 - (lines.length - 1) * lh : H / 2 + size * .36 - (lines.length - 1) * lh / 2 + (b.textY || 0) * H;
    c.globalAlpha = a; c.shadowColor = 'rgba(0,0,0,.75)'; c.shadowBlur = size * .25;
    lines.forEach((ln, i) => { c.fillStyle = (b.accent ? ACC : '#FFFFFF'); c.fillText(ln, W / 2, y + i * lh + rise); });
    c.shadowBlur = 0; c.letterSpacing = '0px'; }
  // series mark
  for (const b of B) if (b.brand && t >= b.t0 && t <= b.t1 + .3) { const a = clamp((t - b.t0) / .4, 0, 1) * clamp((b.t1 + .3 - t) / .4, 0, 1);
    c.globalAlpha = a * .92; const sz = Math.round(MIN * .032); c.font = `600 ${sz}px ${FONT_UI}`; c.letterSpacing = `${Math.round(sz * .25)}px`; c.fillStyle = '#fff'; c.textAlign = 'left';
    c.fillText(CFG.brand || "ORBIT'S LOGBOOK", MIN * .07, MIN * .1); c.letterSpacing = '0px'; }
  c.globalAlpha = 1;
}
function post(t) {
  const c = mctx; c.setTransform(1, 0, 0, 1, 0, 0); c.globalAlpha = 1;
  sctx.globalCompositeOperation = 'copy'; sctx.filter = 'blur(6px) brightness(0.85) contrast(1.9)'; sctx.drawImage(MAIN, 0, 0, SMALL.width, SMALL.height); sctx.filter = 'none';
  c.globalCompositeOperation = 'screen'; c.globalAlpha = .5; c.drawImage(SMALL, 0, 0, W, H);
  c.globalCompositeOperation = 'source-over'; c.globalAlpha = 1; c.drawImage(VIG, 0, 0);
  drawText(c, t);
  const g = GRAIN[Math.floor(t * FPS) % GRAIN.length]; c.globalCompositeOperation = 'overlay'; c.globalAlpha = .1; c.fillStyle = g; c.fillRect(0, 0, W, H);
  c.globalCompositeOperation = 'source-over'; c.globalAlpha = 1;
  const T0 = CFG.range ? CFG.range[0] : 0, T1 = CFG.range ? CFG.range[1] : NF / FPS, fade = Math.min(clamp((t - T0) / (CFG.range ? .3 : .6), 0, 1), clamp((T1 - t) / .5, 0, 1));
  if (fade < 1) { c.fillStyle = `rgba(0,0,0,${1 - fade})`; c.fillRect(0, 0, W, H); }
}

// ---------- public API ----------
async function init(cfg) {
  CFG = cfg; W = cfg.W; H = cfg.H; MIN = Math.min(W, H); FPS = cfg.fps; NF = cfg.frames;
  MAIN = document.getElementById('c'); MAIN.width = W; MAIN.height = H; mctx = MAIN.getContext('2d');
  TMP = new OffscreenCanvas(W, H); tctx = TMP.getContext('2d'); SMALL = new OffscreenCanvas(Math.round(W / 4), Math.round(H / 4)); sctx = SMALL.getContext('2d');
  VIG = new OffscreenCanvas(W, H); const vc = VIG.getContext('2d'); const g = vc.createRadialGradient(W / 2, H / 2, MIN * .35, W / 2, H / 2, Math.hypot(W, H) * .55); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,.6)'); vc.fillStyle = g; vc.fillRect(0, 0, W, H);
  for (let i = 0; i < 6; i++) { const n = new OffscreenCanvas(256, 256), nc = n.getContext('2d'), d = nc.createImageData(256, 256), r = rng(100 + i); for (let p = 0; p < d.data.length; p += 4) { const v = 128 + (r() - .5) * 150; d.data[p] = d.data[p + 1] = d.data[p + 2] = v; d.data[p + 3] = 255; } nc.putImageData(d, 0, 0); GRAIN.push(mctx.createPattern(n, 'repeat')); }
  await document.fonts.load(`40px Anton`); await document.fonts.ready;
  const wd = cfg.world; for (const e of wd.elements) { EL[e.id] = { a: 1, ...e }; ORDER.push(e.id); }
  const need = new Set(wd.elements.filter(e => e.img).map(e => e.img)); await Promise.all([...need].map(n => loadImg(n, (EL[wd.elements.find(e => e.img === n).id].hires ? 3200 : 2000))));
  const r = rng(cfg.seed || 1), [WW, WH] = wd.size; STARS = []; for (let i = 0; i < (wd.stars || 4000); i++) STARS.push([r() * WW, r() * WH, .25 + r() * .75, r() < .9 ? 8 : 20]);
  FAR = []; for (let i = 0; i < 700; i++) FAR.push([r() * W, r() * H, .15 + r() * .45, .5 + r() * 2, r() < .85 ? 1 : 2]);
  B = cfg.beats.map((b, k) => ({ ...b, t0: cfg.lines[k].t0, t1: cfg.lines[k].t1, line: cfg.lines[k].text, text: b.text || null }));
  for (let k = 0; k < B.length; k++) B[k]._tw = B[k]._hit = wordTime(k, B[k].on);
  const ops = []; // property ops, timed on the spoken line
  for (const e of wd.elements) if (e.drop !== undefined) { EL[e.id].a = 0; const td = wordTime(e.drop, e.dropOn) - 0.12; B[e.drop]._hit = Math.max(B[e.drop]._hit, td + .6); ops.push([e.id, 'a', 1, td, e.dropDur || 0.6, false]); }
  for (let k = 0; k < B.length; k++) for (const o of (B[k].set || [])) { const [key, val, dur, on, lin] = o; const [id, pr] = key.split('.'); const b = B[k];
    const t0 = wordTime(k, on); const d = dur === 'beat' ? Math.max(b.t1 - t0, .3) : dur === 'next' ? Math.max((k + 1 < B.length ? B[k + 1].t0 : b.t1) - t0, .3) : (dur === undefined || dur === null ? .8 : dur);
    ops.push([id, pr, val, t0, d, !!lin]); }
  ops.sort((a, b) => a[3] - b[3]); for (const o of ops) addOp(o[0], o[1], o[2], o[3], o[4], o[5]);
  buildTrack();
  return { frames: NF, maxSpeed: Math.max(...SPD) };
}
function render(f) {
  const t = f / FPS, sp = SPD[clamp(f, 0, NF - 1)], n = sp > 10 ? Math.min(6, 2 + Math.floor((sp - 10) / 12)) : 1;
  if (n === 1) drawScene(mctx, t, camAt(f));
  else { for (let i = 0; i < n; i++) { const ff = f + (i / (n - 1) - .5) * .5; drawScene(tctx, ff / FPS, camAt(ff)); mctx.setTransform(1, 0, 0, 1, 0, 0); mctx.globalCompositeOperation = 'source-over'; mctx.globalAlpha = i === 0 ? 1 : 1 / (i + 1); mctx.drawImage(TMP, 0, 0); } mctx.globalAlpha = 1; }
  post(t);
}
function frame(f, q) { render(f); return MAIN.toDataURL('image/jpeg', q || 0.93); }
function stats() { // camera motion report for the checker
  const acc = []; for (let f = 1; f < NF - 1; f++) acc.push(Math.abs(SPD[f + 1] - SPD[f - 1]) / 2);
  const slow = []; for (let f = 0; f < NF; f++) if (SPD[f] < 0.02) slow.push(f);
  const fast = []; for (let f = 0; f < NF; f++) if (SPD[f] > 10) fast.push(f);
  return { maxSpeed: Math.max(...SPD), maxAccel: Math.max(...acc), deadFrames: slow.length, deadSample: slow.slice(0, 20), blurFrames: fast.length,
    speed: Array.from(SPD, v => Math.round(v * 100) / 100), beats: B.map(b => ({ t0: b.t0, t1: b.t1, tw: b._tw, hit: b._hit })) };
}
window.init = init; window.frame = frame; window.stats = stats;
