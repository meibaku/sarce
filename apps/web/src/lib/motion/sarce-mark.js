/* eslint-disable */
// From the v1.0 design handoff (sarce-private: design/handoff-v1/design/sarce-mark.js), unchanged.
// A dependency-free web component; loaded in the browser only, through components/ui/mascot.tsx.
// <sarce-mark state="trace" size="96" speed="1" progress="0.4" reduced loop="false">
// States: static trace tip ring brilliant sound checkin uncalibrated error offline empty quiet pull
// Mascot: idle nod shake look think bow cheer droop sleep  (eyes="false" hides the eyes)
(() => {
  const D = "M8 6h7v5h5.5V6h7v5H33V6h7v12q0 3-3 4l-2 1v18l5 5q2 2 2 4v6q0 2-2 2H8q-2 0-2-2v-6q0-2 2-4l5-5V23l-2-1q-3-1-3-4z";
  const C = { ink: '#1a1f26', mute: '#69717d', line: '#d8dce1', acc: '#2f5f9e', sound: '#2f7a55', check: '#9a6420' };
  const cl = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const seg = (t, a, b) => cl((t - a) / (b - a));
  const out = x => 1 - Math.pow(1 - x, 3);
  const io = x => x < .5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2;
  const back = x => { const c = 1.4; return x <= 0 ? 0 : 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
  const fade = (t, p) => 1 - seg(t, p - .4, p);
  // Each state: (t seconds, progress|null) -> frame. Loop length in LOOP; REST = reduced-motion still.
  const S = {
    static: () => ({ lift: 1 }),
    trace: t => { t %= 2.8; return { draw: io(seg(t, 0, 1)), lift: back(seg(t, 1, 1.45)), dash: io(seg(t, 2, 2.6)) }; },
    tip: t => { t %= 3.2; const l = back(seg(t, 0, .5)) * (1 - io(seg(t, 2.7, 3.2))), x = seg(t, .5, 2.7);
      return { lift: l, tilt: 8 * l + 9 * Math.sin(x * Math.PI * 4) * Math.sin(x * Math.PI) }; },
    ring: (t, p) => ({ lift: 1, ring: p != null ? p : io(seg(t % 3.6, .2, 3)) }),
    brilliant: (t, p, loop) => { if (loop) t %= 3.6; const dip = Math.sin(seg(t, .15, .45) * Math.PI);
      return { lift: back(seg(t, .45, 1)), dip, badge: ['!!', C.acc, back(seg(t, .9, 1.3))], op: loop ? fade(t, 3.6) : 1 }; },
    sound: (t, p, loop) => { if (loop) t %= 3.2; return { lift: 1, badge: ['✓', C.sound, out(seg(t, .2, .6))], op: loop ? fade(t, 3.2) : 1 }; },
    checkin: (t, p, loop) => { if (loop) t %= 3.2; return { lift: 1, badge: ['?!', C.check, out(seg(t, .2, .6))], op: loop ? fade(t, 3.2) : 1 }; },
    uncalibrated: () => ({ lift: 1, color: C.mute, badge: ['~', C.check, 1, true] }),
    error: (t, p, loop) => { if (loop) t %= 3.2; const f = out(seg(t, .2, .8));
      return { lift: 1 - .75 * f, tilt: 8 - 18 * f, color: C.mute, badge: ['↻', C.mute, out(seg(t, .7, 1.1))], op: loop ? fade(t, 3.2) : 1 }; },
    offline: () => ({ lift: 1, color: C.mute, dashed: 'both' }),
    empty: () => ({ lift: 1, color: C.mute, dashed: 'top' }),
    quiet: () => ({ lift: 1, color: C.mute }),
    pull: (t, p) => { const v = p != null ? p : io(Math.abs(((t % 3) / 1.5) - 1)); return { lift: v, tilt: 8 * v, op: .35 + .65 * v }; },
  };
  // Mascot: the break is the neck. Head pivots at (24,25); eyes optional.
  const REST0 = {};
  const wv = (t, p) => (1 - Math.cos((t % p) / p * Math.PI * 2)) / 2;
  const blink = t => { const b = t % 3.6; return b > 3.4 ? Math.abs(Math.cos((b - 3.4) / .2 * Math.PI)) : 1; };
  const M = o => ({ lift: 1, pv: 1, eyes: 1, ...o });
  Object.assign(S, {
    idle: t => M({ hy: -0.8 * wv(t, 2.4), blink: blink(t) }),
    nod: t => { t %= 2.4; const x = seg(t, .2, 1.4); return M({ tilt: 8 + 12 * Math.abs(Math.sin(x * Math.PI * 2)), ey: 1.2 * Math.sin(x * Math.PI), blink: blink(t + 1) }); },
    shake: t => { t %= 2.4; const x = seg(t, .2, 1.4); return M({ tilt: 8 + 3 * Math.sin(x * Math.PI * 4) * Math.sin(x * Math.PI), hx: 2.4 * Math.sin(x * Math.PI * 4) * Math.sin(x * Math.PI), ex: -1.2 * Math.sin(x * Math.PI * 4), blink: 1 }); },
    look: t => { t %= 4; const l = io(seg(t, .3, .6)) - io(seg(t, 1.6, 2.1)) * 2 + io(seg(t, 3.2, 3.6)); return M({ ex: -1.6 * l, tilt: 8 - 4 * l, blink: blink(t + 2) }); },
    think: t => M({ tilt: 2 - 2 * wv(t, 3.2), hy: -0.6 * wv(t, 3.2), ey: -1.4, ex: 1.2, blink: blink(t) }),
    bow: t => { t %= 3.2; const d = io(seg(t, .2, .9)) - io(seg(t, 1.8, 2.6)); return M({ tilt: 8 + 26 * d, lift: 1 - .3 * d, ey: 1.2 * d, blink: blink(t) }); },
    cheer: (t, p, loop) => { if (loop) t %= 3.6; const j = Math.sin(seg(t, .3, .9) * Math.PI); return M({ hy: -7 * j, tilt: 8 - 10 * j, dip: Math.sin(seg(t, .1, .35) * Math.PI), ey: -0.8 * j, badge: ['!!', C.acc, back(seg(t, .8, 1.2))], op: loop ? fade(t, 3.6) : 1, blink: 1 }); },
    droop: (t, p, loop) => { if (loop) t %= 3.2; const f = out(seg(t, .2, 1)); return M({ tilt: 8 + 22 * f, lift: 1 - .5 * f, ey: 1.4 * f, color: C.mute, badge: ['\u21bb', C.mute, out(seg(t, .9, 1.3))], op: loop ? fade(t, 3.2) : 1, blink: 1 }); },
    sleep: t => M({ tilt: 14, lift: .7, hy: .8 * wv(t, 3.6), color: C.mute, blink: 0.12 }),
    hello: t => { t %= 2.6; const a = Math.abs(Math.sin(seg(t, .2, 1.2) * Math.PI * 2)); return M({ hy: -5 * a, tilt: 8 - 8 * a, ey: -.6 * a, blink: blink(t + 1) }); },
    hop: t => { t %= 1.8; const j = sn(seg(t, .25, .75)); return M({ by: -10 * j, sq: .12 * sn(seg(t, .05, .25)) + .1 * sn(seg(t, .75, .95)) - .05 * j, hy: 1.5 * sn(seg(t, .3, .8)), tilt: 8 + 4 * sn(seg(t, .3, .9)), blink: blink(t + 2) }); },
    curious: t => { t %= 3.6; const d = io(seg(t, .2, .8)) - io(seg(t, 2.6, 3.2)); return M({ tilt: 8 - 18 * d, hx: -1.5 * d, brot: -4 * d, ex: -1.2 * d, ey: -.6 * d, blink: blink(t) }); },
    stretch: t => { t %= 3.4; const d = io(seg(t, .2, 1)) - io(seg(t, 2.2, 3)); return M({ hy: -8 * d, sq: -.07 * d, tilt: 8 - 8 * d, blink: 1 - .85 * sn(seg(t, 1, 2.2)) }); },
    wink: t => { t %= 3; const w = sn(seg(t, .4, 1.3)); return M({ tilt: 8 + 8 * w, hx: .8 * w, wr: 1 - .9 * sn(seg(t, .6, 1.1)), blink: 1 }); },
    startle: t => { t %= 3; const j = back(seg(t, .2, .45)) * (1 - io(seg(t, 1.4, 2.2))); return M({ hy: -12 * j, tilt: 8 - 12 * j, sq: -.08 * sn(seg(t, .15, .4)), es: 1 + .6 * j, blink: 1 }); },
    shy: t => { t %= 3.6; const d = io(seg(t, .2, .8)) - io(seg(t, 2.6, 3.2)); return M({ tilt: 8 + 16 * d, lift: 1 - .4 * d, brot: 4 * d, ex: 1.6 * d, ey: 1 * d, blink: blink(t + 1) }); },
    proud: t => { t %= 3.6; const d = io(seg(t, .2, .9)) - io(seg(t, 2.6, 3.3)); return M({ sq: -.05 * d, tilt: 8 - 14 * d, hy: -2 * d, blink: 1 - .85 * d }); },
    castle: t => { t %= 3.6; const o = sn(seg(t, .3, 1.1)), b = sn(seg(t, 2.1, 2.9)); return M({ bx: 14 * io(seg(t, .3, 1.1)) - 14 * io(seg(t, 2.1, 2.9)), brot: -4 * o + 4 * b, tilt: 8 + 8 * o - 8 * b, ex: 1.4 * (sn(seg(t, .1, 1.2)) - sn(seg(t, 1.9, 3))), blink: blink(t + 1) }); },
    sacrifice: t => { t %= 4.6; const r = out(seg(t, .3, 1)) * (1 - io(seg(t, 2.6, 3.4))), j = sn(seg(t, 3.4, 3.9)); return M({ brot: 78 * r, bpx: 40, bx: -16 * r, by: 4 * r - 5 * j, tilt: 8 + 18 * r, blink: 1 - .85 * r, badge: ['!!', C.acc, back(seg(t, 3.6, 4)) * (1 - seg(t, 4.3, 4.6))] }); },
    wobble: t => { t %= 2.6; const x = seg(t, .1, 2.2), w = Math.sin(x * Math.PI * 5) * (1 - x); return M({ brot: 10 * w, tilt: 8 - 6 * w, ex: -1 * w, blink: 1 }); },
    dizzy: t => { t %= 3.6; const x = seg(t, .1, 3.3), m = sn(x), a = x * Math.PI * 6; return M({ hx: 2.5 * m * Math.cos(a), hy: -1.5 * m * Math.sin(a), tilt: 8 + 10 * m * Math.sin(a), ex: 1.2 * m * Math.cos(a + 1), ey: 1.2 * m * Math.sin(a + 1), brot: 3 * m * Math.sin(a / 2), blink: 1 }); },
    shiver: t => M({ hx: .5 * Math.sin(t * 60), bx: .4 * Math.sin(t * 53 + 1), tilt: 12, hy: 1, lift: .8, color: C.mute, blink: blink(t) }),
    relief: t => { t %= 3.6; const e = sn(seg(t, .3, 1.5)); return M({ sq: .1 * e, hy: 2.5 * e, tilt: 8 + 6 * e, blink: 1 - .85 * sn(seg(t, .3, 1.7)) }); },
    yawn: t => { t %= 4.4; const d = io(seg(t, .2, 1.2)) - io(seg(t, 2.4, 3.4)); return M({ tilt: 8 - 18 * d, hy: -4 * d, sq: -.04 * d, blink: 1 - .88 * d, color: C.mute }); },
    doze: t => { t %= 5; const k = 1 - io(seg(t, 3.2, 3.45)), s = io(seg(t, .2, 3)) * k, w = sn(seg(t, 3.2, 3.9)); return M({ tilt: 8 + 18 * s - 6 * w, hy: 2 * s - 2 * w, blink: t < 3.2 ? 1 - .88 * seg(t, .2, 1.5) : 1, es: 1 + .4 * w, color: C.mute }); },
    peek: t => { t %= 3.6; const u = out(seg(t, .2, .9)) - io(seg(t, 2.6, 3.2)); return M({ by: 20 * (1 - u), op: u, ex: 1.4 * Math.sin(seg(t, 1, 2.4) * Math.PI * 2), blink: blink(t + 1) }); },
    sway: t => { const s = Math.sin(t * Math.PI * 2 / 1.6); return M({ brot: 5 * s, tilt: 8 - 6 * s, ex: -.8 * s, blink: blink(t) }); },
    patrol: t => { const p = Math.sin(t * Math.PI * 2 / 3.2); return M({ bx: 12 * p, by: -2.5 * Math.abs(Math.sin(t * Math.PI * 2 / .8)), ex: 1.4 * Math.cos(t * Math.PI * 2 / 3.2), blink: blink(t) }); },
    giggle: t => { t %= 2.4; const x = seg(t, .2, 1.4), g = Math.abs(Math.sin(x * Math.PI * 6)) * sn(x); return M({ hy: -2.5 * g, tilt: 8 - 4 * g, blink: 1 - .8 * sn(x) }); },
    squint: t => { t %= 3.6; const d = io(seg(t, .2, .8)) - io(seg(t, 2.6, 3.2)); return M({ brot: -6 * d, hx: -1 * d, tilt: 8 - 4 * d, blink: 1 - .6 * d }); },
    huh: t => { t %= 3.2; const d = io(seg(t, .2, .7)) - io(seg(t, 2.2, 2.8)); return M({ tilt: 8 - 16 * d, wl: 1 + .5 * d, wr: 1 - .4 * d, ey: -.6 * d, blink: 1 }); },
    gasp: t => { t %= 3; const j = back(seg(t, .2, .4)) * (1 - io(seg(t, 1.8, 2.6))); return M({ hy: -6 * j, es: 1 + .5 * j, sq: -.05 * j, tilt: 8 - 8 * j, blink: 1 }); },
    headdown: t => { t %= 3.2; const d = out(seg(t, .2, .5)) * (1 - io(seg(t, 2, 2.8))); return M({ lift: 1 - d, tilt: 8 * (1 - d), hy: 1.5 * d, sq: .06 * sn(seg(t, .4, .7)), blink: 1 - .88 * d }); },
    rooklift: t => { t %= 3.6; const u = io(seg(t, .2, 1)) - io(seg(t, 2.4, 3.2)); return M({ by: -14 * u, ey: 1.2 * u, tilt: 8 + 6 * u, sq: .08 * sn(seg(t, .9, 1.2)) + .08 * sn(seg(t, 3.1, 3.4)), blink: blink(t) }); },
    check: t => { t %= 2.6; const l = back(seg(t, .2, .5)) * (1 - io(seg(t, 1.4, 2))); return M({ tilt: 8 + 14 * l, hx: 3 * l, ex: 1.6 * l, es: 1 + .2 * l, blink: 1, badge: ['+', C.acc, out(seg(t, .4, .7)) * (1 - seg(t, 2, 2.4))] }); },
    tick: t => { const k = (t * 5) % 1, s = Math.floor(t * 5) % 2 ? 1 : -1, v = -s + 2 * s * out(Math.min(1, k * 4)); return M({ tilt: 8 + 7 * v, ex: 1.2 * v, es: 1.15, blink: 1 }); },
    zwischenzug: t => { t %= 3.6; const a = io(seg(t, .2, .6)) * (1 - io(seg(t, 1.3, 1.5))), b = back(seg(t, 1.4, 1.8)) * (1 - io(seg(t, 2.8, 3.3))); return M({ tilt: 8 + 14 * a - 10 * b, hy: -5 * b, ex: 1.6 * b, ey: .8 * a, es: 1 + .3 * sn(seg(t, 1.2, 1.6)), blink: 1 }); },
    resign: t => { t %= 4.4; const d = io(seg(t, .3, 1.6)) * (1 - io(seg(t, 3.4, 4))); return M({ brot: -80 * d, bpx: 8, bx: 16 * d, by: 4 * d, tilt: 8 + 10 * d, color: C.mute, blink: 1 - .88 * d }); },
    sigh: t => { t %= 3.4; const i = sn(seg(t, .2, 1)), e = sn(seg(t, 1, 2.6)); return M({ sq: -.05 * i + .08 * e, hy: -2 * i + 2 * e, tilt: 8 + 10 * e, blink: 1 - .7 * e, color: C.mute }); },
    melt: t => { t %= 4; const d = io(seg(t, .2, 1.6)) - io(seg(t, 2.6, 3.6)); return M({ sq: .35 * d, hy: 3 * d, tilt: 8 + 10 * d, blink: 1 - .5 * d, color: C.mute }); },
    breathe: t => { const b = (1 - Math.cos((t % 8) / 8 * Math.PI * 2)) / 2; return M({ sq: -.06 * b, hy: -3 * b, tilt: 8 - 6 * b, blink: .12 }); },
  });
  const sn = x => Math.sin(x * Math.PI);
  Object.assign(REST0, { peek: 1.5, sway: 0, patrol: 0, giggle: .8, squint: 1.5, huh: 1.5, gasp: 1, headdown: 1.2, rooklift: 1.6, check: 1, tick: 0, zwischenzug: 2, resign: 2.5, sigh: 1.8, melt: 2, breathe: 2, hello: .5, hop: 0, curious: 1.2, stretch: 1.6, wink: .85, startle: .9, shy: 1.2, proud: 1.5, castle: 1.4, sacrifice: 1.5, wobble: 2.4, dizzy: 0, shiver: 0, relief: .9, yawn: 1.8, doze: 2.5 });
  const REST = { ...REST0, idle: 0, nod: .5, shake: .5, look: .8, bow: 1.2, cheer: 2, droop: 2, trace: 1.8, tip: .6, ring: 2.4, brilliant: 2, sound: 2, checkin: 2, error: 2, pull: 0 };
  let uid = 0;
  const NS = 'http://www.w3.org/2000/svg';
  const el = (n, a, p) => { const e = document.createElementNS(NS, n); for (const k in a) e.setAttribute(k, a[k]); p && p.appendChild(e); return e; };

  class SarceMark extends HTMLElement {
    static get observedAttributes() { return ['state', 'size', 'progress', 'reduced']; }
    connectedCallback() {
      if (this.svg) return this.start();
      const id = 'sm' + (++uid);
      this.style.display = 'inline-block'; this.style.lineHeight = '0';
      const s = this.svg = el('svg', { viewBox: '-14 -18 76 84', overflow: 'visible' }, this);
      const d = el('defs', {}, s);
      el('polygon', { points: '-20,80 -20,36 0,34 48,22 68,17 68,80' }, el('clipPath', { id: id + 'l' }, d));
      el('polygon', { points: '-20,-30 68,-30 68,14 48,19 0,31 -20,36' }, el('clipPath', { id: id + 'u' }, d));
      const pa = { d: D, fill: 'none', 'stroke-width': 3, 'stroke-linejoin': 'round', 'stroke-linecap': 'round', pathLength: 1 };
      this.ringBg = el('circle', { cx: 24, cy: 30, r: 37, fill: 'none', 'stroke-width': 2, stroke: C.line }, s);
      this.ringFg = el('circle', { cx: 24, cy: 30, r: 37, fill: 'none', 'stroke-width': 2, stroke: C.acc, 'stroke-linecap': 'round', pathLength: 1, 'stroke-dasharray': 1, transform: 'rotate(-90 24 30)' }, s);
      this.body = el('g', {}, s);
      this.lo = el('path', { ...pa, 'clip-path': `url(#${id}l)` }, this.body);
      this.topG = el('g', {}, this.body);
      this.hi = el('path', { ...pa, 'clip-path': `url(#${id}u)` }, this.topG);
      this.eyes = el('g', {}, this.topG);
      this.eL = el('ellipse', { cx: 19, cy: 16, rx: 1.6, ry: 1.6 }, this.eyes);
      this.eR = el('ellipse', { cx: 29, cy: 16, rx: 1.6, ry: 1.6 }, this.eyes);
      this.bG = el('g', {}, s);
      this.bC = el('circle', { cx: 0, cy: 0, r: 9, fill: '#fff', 'stroke-width': 1.6 }, this.bG);
      this.bT = el('text', { x: 0, y: 3.4, 'text-anchor': 'middle', 'font-size': 9.5, 'font-weight': 600, 'font-family': "'IBM Plex Sans', sans-serif" }, this.bG);
      this.size(); this.paint(0); this.start();
    }
    disconnectedCallback() { cancelAnimationFrame(this.raf); this.raf = 0; }
    attributeChangedCallback(n) { if (!this.svg) return; if (n === 'size') this.size(); else { this.t0 = performance.now(); this.paint(0); } }
    size() { const h = +(this.getAttribute('size') || 96); this.svg.setAttribute('height', h); this.svg.setAttribute('width', h * 76 / 84); }
    start() { this.t0 = performance.now(); const tick = now => { this.paint((now - this.t0) / 1000 * +(this.getAttribute('speed') || 1)); this.raf = requestAnimationFrame(tick); }; if (!this.raf) this.raf = requestAnimationFrame(tick); }
    paint(t) {
      const st = this.getAttribute('state') || 'static', fn = S[st] || S.static;
      const pAttr = this.getAttribute('progress'), p = pAttr == null || pAttr === '' ? null : cl(+pAttr);
      const reduced = this.hasAttribute('reduced') && this.getAttribute('reduced') !== 'false';
      const loop = this.getAttribute('loop') !== 'false';
      const f = { draw: 1, dash: 0, lift: 0, tilt: null, dip: 0, op: 1, color: C.ink, ...fn(reduced ? (REST[st] || 0) : t, p, reduced ? false : loop) };
      const tilt = f.tilt == null ? 8 * f.lift : f.tilt;
      for (const [path, dashed] of [[this.lo, f.dashed === 'both'], [this.hi, !!f.dashed]]) {
        path.setAttribute('stroke', f.color);
        path.setAttribute('stroke-dasharray', dashed ? '0.035 0.03' : '1 1');
        path.setAttribute('stroke-dashoffset', dashed ? 0 : 1 - f.draw - f.dash);
      }
      const sq = f.sq || 0;
      this.body.setAttribute('transform', `translate(${f.bx || 0} ${(f.by || 0) + 2 * f.dip}) rotate(${f.brot || 0} ${f.bpx || 24} 58) translate(24 58) scale(${1 + sq * .6} ${1 - sq}) translate(-24 -58)`);
      const [px, py] = f.pv ? [24, 25] : [24, 20];
      this.topG.setAttribute('transform', `translate(${5 * f.lift + (f.hx || 0)} ${-4 * f.lift + (f.hy || 0)}) rotate(${tilt} ${px} ${py})`);
      const eyesOn = f.eyes && this.getAttribute('eyes') !== 'false';
      this.eyes.style.display = eyesOn ? '' : 'none';
      if (eyesOn) { const es = f.es || 1, bk = f.blink == null ? 1 : f.blink; for (const [e, x, w] of [[this.eL, 19, f.wl], [this.eR, 29, f.wr]]) { e.setAttribute('cx', x + (f.ex || 0)); e.setAttribute('cy', 16 + (f.ey || 0)); e.setAttribute('rx', 1.6 * es); e.setAttribute('ry', Math.max(.25, 1.6 * es * bk * (w == null ? 1 : w))); e.setAttribute('fill', f.color); } }
      this.svg.style.opacity = f.op;
      const on = f.ring != null;
      this.ringBg.style.display = this.ringFg.style.display = on ? '' : 'none';
      if (on) this.ringFg.setAttribute('stroke-dashoffset', 1 - f.ring);
      const b = f.badge;
      this.bG.style.display = b && b[2] > 0 ? '' : 'none';
      if (b) {
        this.bG.setAttribute('transform', `translate(50 -4) scale(${b[2]})`);
        this.bC.setAttribute('stroke', b[1]); this.bC.setAttribute('stroke-dasharray', b[3] ? '2 1.6' : 'none');
        this.bT.setAttribute('fill', b[1]); this.bT.textContent = b[0];
      }
    }
  }
  if (!customElements.get('sarce-mark')) customElements.define('sarce-mark', SarceMark);
})();

export {}; // a module, so it can be loaded on demand; defining the element is its only effect
