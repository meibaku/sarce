/* eslint-disable */
// From the v1.0 design handoff (sarce-private: design/handoff-v1/design/sarce-skits.js), unchanged.
// A dependency-free web component; loaded in the browser only, through components/ui/mascot.tsx.
// <sarce-skit name="resign" speed="1" reduced>  Multi-rook comic skits, same 7a rook.
// Names: resign doubled leapfrog blunder brilliant timetrouble balloon draw stalemate nap
(() => {
  const D = "M8 6h7v5h5.5V6h7v5H33V6h7v12q0 3-3 4l-2 1v18l5 5q2 2 2 4v6q0 2-2 2H8q-2 0-2-2v-6q0-2 2-4l5-5V23l-2-1q-3-1-3-4z";
  const INK = '#1a1f26', MUTE = '#8a919b', ACC = '#2f5f9e', CHK = '#9a6420', LINE = '#e2e5e9';
  const G = 92, F = "'IBM Plex Sans',sans-serif";
  const cl = v => Math.min(1, Math.max(0, v)), seg = (t, a, b) => cl((t - a) / (b - a));
  const io = x => x < .5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2, out = x => 1 - Math.pow(1 - x, 3);
  const back = x => x <= 0 ? 0 : 1 + 2.4 * Math.pow(x - 1, 3) + 1.4 * Math.pow(x - 1, 2);
  const sn = x => Math.sin(x * Math.PI), wv = (t, p) => (1 - Math.cos((t % p) / p * Math.PI * 2)) / 2;
  const bl = t => { const b = t % 3.4; return b > 3.2 ? Math.abs(Math.cos((b - 3.2) / .2 * Math.PI)) : 1; };

  function eyes(r, c) {
    const ex = r.ex || 0, ey = r.ey || 0;
    if (r.eyes === 'x') return [19, 29].map(x => { const a = x + ex, b = 16 + ey; return `<path d="M${a - 1.8} ${b - 1.8}l3.6 3.6M${a + 1.8} ${b - 1.8}l-3.6 3.6" stroke="${c}" stroke-width="1.4" stroke-linecap="round"/>`; }).join('');
    const es = r.es || 1, b = r.blink == null ? 1 : r.blink;
    return [19, 29].map(x => `<ellipse cx="${x + ex}" cy="${16 + ey}" rx="${1.6 * es}" ry="${Math.max(.25, 1.6 * es * b)}" fill="${c}"/>`).join('');
  }
  function rook(r, id) {
    const s = r.s || 1, c = r.color || INK, sq = r.sq || 0, lift = r.lift == null ? 1 : r.lift, hp = r.hp || [24, 25], rpx = r.rpx == null ? 24 : r.rpx;
    const P = k => `<path d="${D}" fill="#fff" stroke="${c}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"${r.dash ? ' stroke-dasharray="3 2.5"' : ''} clip-path="url(#${id}${k})"/>`;
    const core = `<g transform="translate(${5 * lift} ${-4 * lift}) rotate(${r.ht == null ? 8 * lift : r.ht} ${hp[0]} ${hp[1]})">${P('u')}${eyes(r, c)}</g>`;
    const bodyT = `translate(0 ${r.by || 0}) rotate(${r.rot || 0} ${rpx} 58) translate(24 58) scale(${1 + sq * .6} ${1 - sq}) translate(-24 -58)`;
    const inner = r.free
      ? `<g transform="${bodyT}">${r.headOnly ? '' : P('l')}</g><g transform="translate(${r.hx || 0} ${r.hy || 0}) rotate(${r.hr || 0} ${rpx} 58)">${core}</g>`
      : `<g transform="${bodyT}">${r.headOnly ? '' : P('l')}<g transform="translate(${r.hx || 0} ${r.hy || 0})">${core}</g></g>`;
    return `<g opacity="${r.op == null ? 1 : r.op}" transform="translate(${r.x - 24 * s} ${G - 58 * s + (r.y || 0)}) scale(${s})"><g transform="${r.flip ? 'translate(48 0) scale(-1 1)' : ''}">${inner}</g></g>`;
  }
  const txt = (x, y, s, size, c, op = 1, sc = 1) => op <= 0 || sc <= 0 ? '' : `<text x="${x}" y="${y}" text-anchor="middle" font-family="${F}" font-weight="600" font-size="${size}" fill="${c}" opacity="${op}" transform="translate(${x} ${y}) scale(${sc}) translate(${-x} ${-y})">${s}</text>`;
  const ln = (d, op, c = INK, w = 1.6) => op <= 0 ? '' : `<path d="${d}" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" opacity="${op}"/>`;
  const badge = (x, y, s, sc, c) => sc <= 0 ? '' : `<g transform="translate(${x} ${y}) scale(${sc})"><circle r="10" fill="#fff" stroke="${c}" stroke-width="1.8"/><text y="3.8" text-anchor="middle" font-family="${F}" font-weight="600" font-size="10.5" fill="${c}">${s}</text></g>`;
  const drop = (x, y, op) => op <= 0 ? '' : `<path d="M${x} ${y - 3.5}q2.6 3.2 0 5q-2.6-1.8 0-5z" fill="none" stroke="${ACC}" stroke-width="1.3" opacity="${op}"/>`;
  const fadeLoop = (t, L) => seg(t, 0, .2) * (1 - seg(t, L - .4, L));

  const SK = {
    resign: { L: 5, rest: 2.2, f: t => {
      const op = fadeLoop(t, 5), fall = Math.pow(seg(t, .4, 1.1), 2), snap = t >= 1.1, roll = out(seg(t, 1.1, 2.3));
      const A = { x: 90, rpx: 44, free: true, rot: 90 * fall, hr: 90 * fall, hp: [24, 16], op,
        ht: 8 + 200 * roll, hx: 46 * roll, hy: -10 * sn(seg(t, 1.1, 1.45)) + 6 * out(seg(t, 1.3, 1.6)),
        eyes: snap ? 'x' : null, es: 1 + .4 * seg(t, .3, .6), ex: snap ? 0 : 1 };
      const j = back(seg(t, 1.15, 1.35)) * (1 - io(seg(t, 1.9, 2.3))), hide = io(seg(t, 2.3, 3));
      const B = { x: 40 - 26 * hide, s: .72, color: MUTE, op, y: -16 * j, hy: -8 * j, es: 1 + .8 * j, sq: -.06 * j,
        ex: 1.3, ht: 8 + 10 * hide, lift: 1 - .4 * hide, hx: t > 2.3 ? .7 * Math.sin(t * 60) : 0, blink: t < 1.1 ? bl(t) : 1 };
      const d = sn(seg(t, 1.1, 1.5));
      return { rooks: [B, A], props: ln(`M104 ${G - 2}l-8-5M104 ${G - 8}l-9-1M172 ${G - 2}l8-5`, d * op) + txt(40 - 26 * hide, 30 - 14 * j, '!', 16, CHK, op * seg(t, 1.15, 1.25) * (1 - seg(t, 2.4, 2.7))) + drop(52 - 26 * hide, 58, op * sn(seg(t, 2.4, 3.6))) };
    } },
    doubled: { L: 4, rest: 1.8, f: t => {
      const op = fadeLoop(t, 4), p = Math.pow(seg(t, .2, 1), 2), hit = sn(seg(t, 1, 1.4)), g = io(seg(t, 1.6, 2.1)) * (1 - io(seg(t, 3, 3.4))), shy = io(seg(t, 1.7, 2.2));
      const A = { x: 150 + 10 * out(seg(t, 1, 1.3)), op, hy: -8 * hit, es: 1 + .6 * hit, ex: -1.7 * g, ht: 8 - 12 * g, blink: t > 1.6 ? 1 - .5 * g : bl(t) };
      const B = { x: 112 * (t < 1 ? 1 : 1) - 122 * (1 - p) - 14 * io(seg(t, 2.4, 3.4)), op, rot: t < 1 ? 7 * seg(t, .3, .6) : 7 * (1 - seg(t, 1, 1.15)), sq: .12 * sn(seg(t, 1, 1.2)),
        hx: 5 * sn(seg(t, 1, 1.3)), hy: -4 * sn(seg(t, 1, 1.3)), ht: 8 + 16 * shy, ex: -1.2 * shy, ey: 1 * shy, lift: 1 - .2 * shy, es: 1 + .5 * hit };
      return { rooks: [A, B], props: ln(`M131 ${G - 58}v-7M125 ${G - 54}l-5-4M137 ${G - 54}l5-4`, hit * op) + ln(`M${B.x - 34} ${G - 34}h-14M${B.x - 30} ${G - 24}h-18M${B.x - 34} ${G - 14}h-12`, sn(seg(t, .5, 1)) * op, MUTE) };
    } },
    leapfrog: { L: 3.4, rest: 1.05, f: t => {
      const op = fadeLoop(t, 3.4), duck = io(seg(t, .5, .8)) - io(seg(t, 1.5, 1.9)), p = seg(t, .6, 1.5), done = seg(t, 1.9, 2.3);
      const B = { x: 130, op, sq: .22 * duck, lift: 1 - .8 * duck, blink: 1 - .88 * duck, ex: 1.5 * done };
      const A = { x: 60 + 140 * io(p), y: -46 * sn(p), op, sq: .15 * io(seg(t, .2, .55)) * (1 - seg(t, .55, .65)) + .14 * sn(seg(t, 1.5, 1.75)),
        rot: -10 * sn(p), ht: 8 - 14 * sn(p), es: 1 + .3 * sn(p), ex: -1.4 * done, blink: t > 2 ? 1 - .85 * done : 1 };
      return { rooks: [B, A], props: ln(`M${A.x - 26} ${G - 20 + A.y}l-10 4M${A.x - 24} ${G - 32 + A.y}l-12 0`, sn(p) * op, MUTE) };
    } },
    blunder: { L: 4, rest: 1.4, f: t => {
      const op = fadeLoop(t, 4), w = seg(t, .1, 1), trip = out(seg(t, 1, 1.2)) * (1 - io(seg(t, 1.6, 2.1))), fly = seg(t, 1, 1.7);
      const ht = 8 + 180 * io(fly) + 180 * io(seg(t, 2.5, 2.9));
      const A = { x: 40 + 72 * w, by: t < 1 ? -2.5 * Math.abs(Math.sin(t * 9)) : 0, rot: 28 * trip, rpx: 44, op,
        hy: -30 * sn(fly), hp: [24, 16], ht, es: t > 1 && t < 1.8 ? 1.5 : 1, blink: t > 2 && t < 2.5 ? bl(t + 1.2) : 1, sq: .08 * sn(seg(t, 1.7, 1.9)) };
      return { rooks: [A], props: `<rect x="133" y="${G - 9}" width="11" height="9" fill="none" stroke="${MUTE}" stroke-width="1.6"/>` + txt(150, 30, '?!', 15, CHK, op * seg(t, 1.8, 1.9) * (1 - seg(t, 3, 3.4)), back(seg(t, 1.8, 2.1))) };
    } },
    brilliant: { L: 4, rest: 2.2, f: t => {
      const op = fadeLoop(t, 4), up = out(seg(t, .55, 1.1)), dn = Math.pow(seg(t, 1.5, 2), 2);
      const hy = t < 1.5 ? -80 * up : -80 * (1 - dn) - 6 * sn(seg(t, 2, 2.2));
      const hx = t < 1.5 ? 0 : 14 * (1 - io(seg(t, 2.3, 2.8)));
      const A = { x: 120, op, sq: .18 * io(seg(t, .2, .5)) * (1 - seg(t, .5, .58)) + .1 * sn(seg(t, 2, 2.2)), hy, hx, hp: [24, 16],
        ht: 8 + 360 * io(seg(t, 1.4, 2)), es: t > .5 && t < 2.3 ? 1.4 : 1, blink: t > 2.8 ? 1 - .85 * sn(seg(t, 2.8, 3.6)) : 1 };
      return { rooks: [A], props: ln(`M114 ${44 + hy * .4}v14M126 ${44 + hy * .4}v14M120 ${48 + hy * .4}v16`, sn(seg(t, .6, 1.05)) * op, MUTE) + badge(120, 22, '!!', back(seg(t, 1, 1.4)) * (1 - seg(t, 3.2, 3.6)), ACC) };
    } },
    timetrouble: { L: 2.4, rest: .4, f: (t, T) => {
      let p = '';
      for (let i = 0; i < 4; i++) { const ph = ((T * 1.4) + i / 4) % 1, sd = i % 2 ? 1 : -1; p += drop(120 + sd * (16 + 18 * ph), 44 - 10 * sn(ph) + 18 * ph * ph, 1 - ph); }
      const a = (T * 720) % 360 * Math.PI / 180;
      p += `<circle cx="190" cy="68" r="13" fill="none" stroke="${INK}" stroke-width="1.6"/>` + ln(`M190 68l${9 * Math.sin(a)} ${-9 * Math.cos(a)}`, 1, ACC, 1.8) + ln('M190 52v-3M186 49h8', 1);
      return { rooks: [{ x: 120 + .8 * Math.sin(T * 50), hp: [24, 17], ht: 8 + (T * 540) % 360, es: 1.5 }], props: p };
    } },
    balloon: { L: 4.6, rest: 1.8, f: t => {
      const op = fadeLoop(t, 4.6), u = io(seg(t, .3, 1.6)) * (1 - Math.pow(seg(t, 3, 3.25), 2));
      const hy = -34 * u, hx = 10 * Math.sin(t * 2.2) * u, by = t > 1.6 && t < 3 ? -8 * Math.abs(Math.sin((t - 1.6) * Math.PI / .5)) : 0;
      const A = { x: 120, op, free: true, hx, hy, ht: 8 + 8 * Math.sin(t * 2) * u, ey: 1.4 * u, ex: -hx * .08, by, sq: .2 * sn(seg(t, 3.25, 3.5)), blink: t > 3.25 && t < 3.6 ? .2 : 1 };
      return { rooks: [A], props: ln(`M120 ${59 + by}Q${124 + hx * .3} ${57 + hy * .5} ${125 + hx} ${55 + hy}`, u > .05 ? op : 0, MUTE, 1.2) };
    } },
    draw: { L: 4.4, rest: 2.4, f: t => {
      const op = fadeLoop(t, 4.4), lean = io(seg(t, 1.6, 2.1)) * (1 - io(seg(t, 3.3, 3.8))), bow = sn(seg(t, 2.5, 3.2));
      const n1 = Math.abs(Math.sin(seg(t, .3, .9) * Math.PI * 2)), n2 = Math.abs(Math.sin(seg(t, .9, 1.5) * Math.PI * 2));
      const base = { op, ex: 1.4, rot: 8 * lean };
      return { rooks: [{ ...base, x: 82, ht: 8 + 12 * n1 + 24 * bow, blink: bl(t) }, { ...base, x: 158, flip: true, ht: 8 + 12 * n2 + 24 * bow, blink: bl(t + 1.4) }],
        props: txt(120, 30, '½', 18, ACC, op * (1 - seg(t, 3.6, 4)), back(seg(t, 2, 2.4))) };
    } },
    stalemate: { L: 4.6, rest: 3.2, f: t => {
      const op = fadeLoop(t, 4.6), m = io(seg(t, .2, .8)), hop = sn(seg(t, 1.1, 1.5)), lean = sn(seg(t, 1.8, 2.4)), look = io(seg(t, 2.6, 2.9)) * (1 - io(seg(t, 3.9, 4.2)));
      const st = { op, y: -8 * hop, rot: -8 * lean, ex: 1.4 * (1 - look), ey: .8 * look, es: 1 + .3 * hop, sq: .08 * sn(seg(t, 3.6, 4)), blink: t > 2.6 ? bl(t) : 1 };
      return { rooks: [{ ...st, x: 70 + 24 * m }, { ...st, x: 170 - 24 * m, flip: true }], props: txt(100, 30, '…', 16, MUTE, op * sn(seg(t, 2.8, 3.9))) + txt(140, 30, '…', 16, MUTE, op * sn(seg(t, 2.9, 4))) };
    } },
    nap: { L: 5.6, rest: 2.8, f: (t, T) => {
      const w = t - Math.min(Math.max(t - 2.4, 0), .8), fr = t > 2.4 && t < 3.2 ? 1 : 0, snore = sn(seg(t, 2.35, 2.9));
      const bx = -20 + 280 * w / 4.8;
      let z = '';
      for (let i = 0; i < 3; i++) { const ph = ((T / 1.8) + i / 3) % 1; z += txt(176 + 10 * ph, 38 - 22 * ph, 'z', 8 + 5 * ph + 6 * snore, MUTE, sn(ph)); }
      const A = { x: 160, ht: 22, lift: .7, hy: 2 + wv(T, 3.6) - 2 * snore, blink: .12, color: INK };
      const B = { x: bx, s: .8, by: fr ? 0 : -4 * Math.abs(Math.sin(w * Math.PI * 2.2)), rot: fr ? 10 : 5, ex: bx < 160 ? 1.6 : -1.6, es: fr ? 1.7 : 1.2, sq: fr ? -.04 : 0 };
      return { rooks: [B, A], props: z };
    } },
    flag: { L: 4.4, rest: 2, f: t => {
      const op = fadeLoop(t, 4.4), up = io(seg(t, .2, .8)) * (1 - io(seg(t, 3.4, 3.9))), f = out(seg(t, .6, 1.2)) * (1 - io(seg(t, 3.1, 3.5)));
      const A = { x: 104, op, hy: -10 * up, hx: -6 * up, ht: 8 - 16 * up, ex: 1.4 * up, ey: .6 * up, blink: bl(t) };
      const top = G - 8 - 56 * f, w = Math.sin(t * 9) * 2;
      return { rooks: [A], props: f > .01 ? ln('M132 ' + G + 'V' + top, op) + '<path d="M132 ' + top + 'q6 ' + (-2 + w) + ' 12 0t12 0v10q-6 ' + (-2 + w) + ' -12 0t-12 0z" fill="#fff" stroke="' + INK + '" stroke-width="1.6" stroke-linejoin="round" opacity="' + op + '"/>' : '' };
    } },
    ghost: { L: 5, rest: 2.6, f: t => {
      const op = fadeLoop(t, 5), u = out(seg(t, 1.4, 3.4)), gop = op * seg(t, 1.4, 1.8) * (1 - seg(t, 3.6, 4.2));
      const A = { x: 90, rpx: 44, rot: 90 * Math.pow(seg(t, .3, 1.1), 2), eyes: t > 1.1 ? 'x' : null, es: 1 + .4 * seg(t, .2, .5), op };
      const Gh = { x: 147, y: 26 - 50 * u, headOnly: true, dash: true, color: MUTE, op: gop, hx: 4 * Math.sin(t * 3), ey: 1.2 * seg(t, 2.6, 3), blink: bl(t) };
      return { rooks: [A, Gh], props: ln('M104 ' + (G - 2) + 'l-8-5M172 ' + (G - 2) + 'l8-5', op * sn(seg(t, 1.1, 1.5))) };
    } },
    sink: { L: 5, rest: 2.2, clipG: true, f: t => {
      const op = fadeLoop(t, 5), d = io(seg(t, .4, 2.6)), struggling = t > .4 && t < 2.6;
      const A = { x: 120, op, y: 64 * d - 26 * sn(seg(t, 3.6, 4.4)), hy: -6 * d, ey: -1.2 * d, es: 1 + .3 * d, hx: struggling ? .7 * Math.sin(t * 20) : 0, blink: bl(t) };
      let b = '';
      for (let i = 0; i < 3; i++) { const ph = seg(t, 2.6 + i * .25, 3.4 + i * .25); if (ph > 0 && ph < 1) b += '<circle cx="' + (116 + i * 5) + '" cy="' + (G - 2 - 14 * ph) + '" r="' + (1.5 + ph) + '" fill="none" stroke="' + MUTE + '" stroke-width="1.2" opacity="' + sn(ph) * op + '"/>'; }
      return { rooks: [A], props: b + ln('M94 ' + (G + 1.5) + 'q4-3 8 0M138 ' + (G + 1.5) + 'q4-3 8 0', op * (struggling ? 1 : 0), MUTE) };
    } },
    domino: { L: 5, rest: 2.2, f: t => {
      const op = fadeLoop(t, 5), a = 38 * Math.pow(seg(t, .3, .75), 2), b = 38 * Math.pow(seg(t, .75, 1.15), 2), c = 90 * Math.pow(seg(t, 1.15, 1.65), 2);
      const snap = t >= 1.65, roll = out(seg(t, 1.65, 2.6));
      const Rk = (x, rot, i) => ({ x, rot, rpx: 44, op, es: 1 + .5 * seg(t, .3 + i * .45, .5 + i * .45), blink: t > 2.4 ? .12 : 1 });
      const C = { x: 134, rpx: 44, free: true, rot: c, hr: c, hp: [24, 16], op, ht: 8 + 150 * roll, hx: 28 * roll, hy: -10 * sn(seg(t, 1.65, 2)) + 6 * out(seg(t, 1.85, 2.1)), eyes: snap ? 'x' : null, es: 1.4 };
      return { rooks: [C, Rk(92, b, 1), Rk(50, a, 0)], props: ln('M150 ' + (G - 2) + 'l-6-5M214 ' + (G - 2) + 'l8-5', op * sn(seg(t, 1.65, 2))) };
    } },
    comfort: { L: 5.4, rest: 3, f: t => {
      const op = fadeLoop(t, 5.4), w = seg(t, .3, 1.6), lean = io(seg(t, 1.9, 2.4)) * (1 - io(seg(t, 4.2, 4.7))), s2 = sn(seg(t, 2.6, 3.6)), up = io(seg(t, 3.6, 4.2));
      const A = { x: 150, op, ht: 30 - 16 * up, lift: .55 + .3 * up, ey: 1.2 * (1 - up), blink: up > .5 ? bl(t) : .6, sq: .06 * s2 };
      const B = { x: -20 + 122 * io(w), op, by: w > 0 && w < 1 ? -3 * Math.abs(Math.sin(t * 10)) : 0, rot: 9 * lean, ht: 8 + 14 * lean, hx: 3 * lean, ex: 1.4, blink: lean > .5 ? 1 - .85 * lean : bl(t), sq: .06 * s2 };
      return { rooks: [A, B], props: '' };
    } },
    catch: { L: 4.8, rest: 2, f: t => {
      const op = fadeLoop(t, 4.8), fall = 90 * Math.pow(seg(t, .3, .9), 2), p = seg(t, .9, 1.6), land = t > 1.6;
      const k = land ? Math.sin((t - 1.6) * 9) * (1 - seg(t, 1.6, 3)) : 0;
      const A = { x: 70, rpx: 44, free: true, rot: fall, hr: fall, hp: [24, 16], op, ht: 8 - 90 * io(p), hx: 29 * io(p) + 2.5 * k, hy: -56 * io(p) - 25 * sn(p), eyes: t > .9 && t < 2.4 ? 'x' : null, blink: bl(t) };
      const B = { x: 205 - 45 * out(seg(t, .9, 1.5)) + k, op, rot: land ? 3 * k : -6 * sn(seg(t, .9, 1.5)), es: t > .9 && t < 3 ? 1.5 : 1, ey: -1.4 * seg(t, 1.3, 1.6), blink: t > 3 ? bl(t) : 1 };
      return { rooks: [B, A], props: '' };
    } },
    premove: { L: 3.8, rest: 1.1, f: t => {
      const op = fadeLoop(t, 3.8), h = io(seg(t, .3, .75)), w = seg(t, 1, 1.8), bx = 60 + 90 * io(w), wait = t > .75 && t < 1.8;
      const A = { x: bx, op, free: true, hx: 90 * h - (bx - 60), hy: -4 * sn(seg(t, .3, .75)) - (wait ? 1.5 * Math.abs(Math.sin(t * 12)) : 0), ex: wait ? -1.6 : 1, by: w > 0 && w < 1 ? -3 * Math.abs(Math.sin(t * 14)) : 0, sq: .1 * sn(seg(t, 1.8, 2)), es: t < .3 ? 1.3 : 1, blink: t > 2 ? bl(t) : 1 };
      return { rooks: [A], props: ln('M' + (bx - 30) + ' 60h-10M' + (bx - 30) + ' 72h-14', op * sn(w), MUTE) };
    } },
    seventh: { L: 4.4, rest: 1.6, f: t => {
      const op = seg(t, 0, .3) * (1 - seg(t, 4, 4.4)), st = Math.sin(t * Math.PI * 2.5);
      const A = { x: 20 + 200 * (t / 4.4), op, by: -5 * Math.abs(st), rot: 4 * st, ht: -4, ey: -.6, blink: .25 };
      return { rooks: [A], props: '<path d="M0 ' + (G + 1.5) + 'H240" stroke="' + ACC + '" stroke-width="1.5" stroke-dasharray="5 5"/>' + txt(12, G - 6, '7', 12, ACC, 1) };
    } },
    offer: { L: 5.2, rest: 2.4, f: t => {
      const op = fadeLoop(t, 5.2), p = io(seg(t, .4, 1.4)), q = io(seg(t, 3.2, 4)), k = p * (1 - q), arc = sn(seg(t, .4, 1.4)) + sn(seg(t, 3.2, 4));
      const A = { x: 84, op, free: true, hx: 38 * k, hy: 31 * k - 16 * arc, ht: 8 - 8 * k, rot: 14 * sn(seg(t, 1.2, 2.4)), ex: 1.2 * k, blink: bl(t) };
      return { rooks: [A], props: txt(132, 40, '!?', 14, CHK, op * seg(t, 1.6, 1.8) * (1 - seg(t, 3, 3.2)), back(seg(t, 1.6, 1.9))) };
    } },
    disagree: { L: 5.6, rest: 2.9, f: t => {
      const op = fadeLoop(t, 5.6), nod = x => Math.abs(Math.sin(x * Math.PI * 2)), sh = x => Math.sin(x * Math.PI * 4) * sn(x);
      const a1 = seg(t, .3, 1.1), b1 = seg(t, .6, 1.4), a2 = seg(t, 1.5, 2), p = io(seg(t, 2.4, 3.2)), ps = seg(t, 2.4, 3.2), after = t > 3.2;
      const A = { x: 85, op, free: true, ht: 8 + 12 * nod(a1) + 12 * nod(a2), hx: 60 * p, hy: -30 * sn(ps), ex: after ? -1.4 : 1.4, es: after ? 1.4 : 1, blink: bl(t) };
      const B = { x: 155, flip: true, op, free: true, hx: 60 * p + 2.4 * (sh(b1) + sh(a2)), hy: -10 * sn(ps), ex: after ? -1.4 : 1.4, es: after ? 1.4 : 1, blink: bl(t + 1) };
      return { rooks: [A, B], props: txt(85, 24, '\u2713', 13, '#2f7a55', op * (sn(a1) + sn(a2))) + txt(155, 24, '\u2715', 13, MUTE, op * (sn(b1) + sn(a2))) };
    } },
    comeback: { L: 4.6, rest: 2.6, f: t => {
      const op = fadeLoop(t, 4.6), r = 1 - out(seg(t, .3, 1.7)), hop = seg(t, 1.9, 2.4);
      const A = { x: 110, op, free: true, hp: [24, 16], hx: 120 * r, hy: t < 1.9 ? 31 : 31 * (1 - io(hop)) - 18 * sn(hop), ht: 8 + 330 * r, sq: .12 * sn(seg(t, 2.4, 2.65)), es: t > 2.4 && t < 3 ? 1.3 : 1, blink: t > 3 ? 1 - .85 * sn(seg(t, 3, 3.8)) : 1 };
      return { rooks: [A], props: '' };
    } },
    backrank: { L: 5.6, rest: 3.1, f: (t, T) => {
      const op = fadeLoop(t, 5.6), cy = -40 + 132 * Math.pow(seg(t, 1.2, 1.9), 2), wake = back(seg(t, 2.1, 2.35)) * (1 - io(seg(t, 2.8, 3.3))), slump = io(seg(t, 3, 3.6));
      const A = { x: 110, op, ht: 22 - 30 * wake, lift: .7 + .3 * wake, hy: (t < 2.1 ? 2 + wv(T, 3.6) : 0) - 8 * wake, blink: t < 2.1 ? .12 : 1 - .5 * slump, es: 1 + .8 * wake, ey: 1.2 * slump, sq: .04 * sn(seg(t, 1.9, 2.1)) };
      const cx = 168, y0 = Math.min(cy, G);
      let z = '';
      if (t < 2.1) for (let i = 0; i < 3; i++) { const ph = ((T / 1.8) + i / 3) % 1; z += txt(128 + 10 * ph, 38 - 22 * ph, 'z', 8 + 5 * ph, MUTE, sn(ph) * op); }
      const crown = '<path d="M' + (cx - 11) + ' ' + y0 + 'l-2-14 7 6 6-10 6 10 7-6-2 14z" fill="#fff" stroke="' + INK + '" stroke-width="1.8" stroke-linejoin="round" opacity="' + op + '"/>';
      return { rooks: [A], props: z + crown + ln('M' + (cx - 18) + ' ' + (G - 1) + 'l-6-3M' + (cx + 18) + ' ' + (G - 1) + 'l6-3', op * sn(seg(t, 1.9, 2.3))) + txt(140, 26, '#', 18, CHK, op * seg(t, 3, 3.2), back(seg(t, 3, 3.3))) };
    } },
    pin: { L: 4, rest: 1.6, f: t => {
      const op = fadeLoop(t, 4), st = io(seg(t, .4, 1.8)) * (t < 1.8 ? 1 : 0), sn2 = out(seg(t, 1.8, 2.05)), jit = t > .6 && t < 1.8 ? .7 * Math.sin(t * 50) : 0;
      const hx = t < 1.8 ? 14 * st + jit : 14 * (1 - sn2) - 3 * sn(seg(t, 2, 2.4));
      const A = { x: 120, op, free: true, hx, hy: -2 * st, rot: 3 * st, ex: 1.6 * st, es: 1 + .5 * sn(seg(t, 1.8, 2.4)), sq: .08 * sn(seg(t, 1.9, 2.2)), blink: t > 2.6 ? bl(t) : 1 };
      return { rooks: [A], props: '<path d="M0 ' + (G - 36) + 'H94" stroke="' + ACC + '" stroke-width="1.6" stroke-dasharray="4 4" opacity="' + op + '"/>' + ln('M94 ' + (G - 42) + 'v12', op, ACC) };
    } },
    zugzwang: { L: 4.4, rest: 2.3, f: t => {
      const op = fadeLoop(t, 4.4), tip = io(seg(t, .3, .8)) * (1 - io(seg(t, 3.4, 3.9))), wob = Math.sin(t * 7) * tip * (t < 2.2 ? 1 : 0), shut = t > 2.1 && t < 2.8;
      const A = { x: 120 + 8 * io(seg(t, 2.2, 2.6)) - 8 * io(seg(t, 3.6, 4.2)), op, sq: -.07 * tip, rot: 4 * wob, ht: 8 - 6 * wob, es: shut ? 1 : 1.25, blink: shut ? .15 : 1, ex: -1 * wob };
      return { rooks: [A], props: drop(A.x + 20, 44, sn(seg(t, 1, 2.2)) * op) };
    } },
    skewer: { L: 4, rest: 1.4, f: t => {
      const op = fadeLoop(t, 4), tip = 240 - 230 * io(seg(t, .4, 1.1)), aop = op * (1 - seg(t, 1.6, 2));
      const pa = back(seg(t, .72, .9)) * (1 - io(seg(t, 2.6, 3.2))), pb = back(seg(t, .92, 1.1)) * (1 - io(seg(t, 2.8, 3.4)));
      const A = { x: 156, op, hy: -12 * pa, es: 1 + .6 * pa, ex: 1.4 * pa, blink: 1 }, B = { x: 84, op, s: .9, hy: -20 * pb, es: 1 + .6 * pb, ex: 1.4 * pb, blink: 1 };
      return { rooks: [B, A], props: ln('M240 44H' + tip + 'M' + (tip + 6) + ' 39l-6 5 6 5', aop, ACC, 1.8) };
    } },
    rookendgame: { L: 5.2, rest: 4, f: t => {
      const op = fadeLoop(t, 5.2), y = d => ({ ht: 8 - 18 * d, hy: -4 * d, sq: -.04 * d, blink: 1 - .88 * d });
      const d1 = io(seg(t, .4, 1.2)) - io(seg(t, 2, 2.6)), d2 = io(seg(t, 1.4, 2.2)) - io(seg(t, 3, 3.6));
      return { rooks: [{ x: 80, op, ex: 1.2, ...y(d1) }, { x: 160, flip: true, op, ex: 1.2, ...y(d2) }], props: txt(120, 34, '\u00bd', 18, MUTE, op * seg(t, 3.6, 4.2)) };
    } },
    perpetual: { L: 4, rest: .5, f: t => {
      const ph = t / 4 * Math.PI * 2, xb = 120 + 70 * Math.sin(ph), xa = 120 + 70 * Math.sin(ph - .8), hop = k => -3 * Math.abs(Math.sin((t + k) * Math.PI * 3)), c = (t % 1);
      const B = { x: xb, flip: Math.cos(ph) < 0, by: hop(0), es: 1.4, ex: -1, blink: 1 }, A = { x: xa, flip: Math.cos(ph - .8) < 0, by: hop(.15), es: 1.15, ex: 1.4, ht: -2, blink: bl(t) };
      return { rooks: [A, B], props: txt(xb, 28 - 6 * c, '+', 15, ACC, sn(c)) };
    } },
    connected: { L: 4.4, rest: 1.7, f: t => {
      const op = fadeLoop(t, 4.4), m = io(seg(t, .2, 1.1)), l = sn(seg(t, 1.3, 1.9)), happy = sn(seg(t, 2, 3.2));
      const hopb = m > 0 && m < 1 ? -3 * Math.abs(Math.sin(t * 12)) : 0;
      const R = x => ({ x, op, by: hopb, hx: 6 * l, hy: -10 * l, ht: 8 - 14 * l, ex: 1.4, blink: 1 - .85 * happy });
      return { rooks: [R(40 + 58 * m), { ...R(200 - 58 * m), flip: true }], props: ln('M120 22v-6M113 25l-5-4M127 25l5-4', op * sn(seg(t, 1.55, 2)), ACC) };
    } },
    juggle: { L: 2.4, rest: .6, f: t => {
      const ph = (t % 1.2) / 1.2, h = sn(ph);
      const A = { x: 120, free: true, hy: -40 * h, hx: 4 * Math.sin(ph * Math.PI * 2), hp: [24, 16], ht: 8 + 360 * ph, sq: .1 * Math.pow(Math.cos(ph * Math.PI), 10), ey: -.6, blink: 1 };
      return { rooks: [A], props: '' };
    } },
    streak: { L: 3.6, rest: .62, f: t => {
      const op = fadeLoop(t, 3.6);
      return { rooks: [60, 120, 180].map((x, i) => { const j = sn(seg(t, .3 + i * .2, .8 + i * .2)) + sn(seg(t, 1.7 + i * .2, 2.2 + i * .2)); return { x, s: .85, op, y: -14 * j, hy: -3 * j, sq: -.05 * j, blink: 1 - .8 * j, ht: 8 - 8 * j }; }), props: '' };
    } },
    opening: { L: 5.2, rest: 1, f: t => {
      const op = fadeLoop(t, 5.2), doze = io(seg(t, 2.8, 3.6)) * (1 - out(seg(t, 4, 4.2))), jerk = sn(seg(t, 4, 4.5));
      const A = { x: 104, op, ht: 18 + 14 * doze - 18 * jerk, ey: 1.4, ex: 1.6, hy: 2 * doze - 5 * jerk, blink: doze > .5 ? .12 : 1, es: 1 + .6 * jerk };
      const p1 = seg(t, 1, 1.4), p2 = seg(t, 2, 2.4), pg = p => p > 0 && p < 1 ? ln('M152 64q' + (8 - 16 * p) + ' ' + (-6 * sn(p)) + ' ' + (14 - 28 * p) + ' 0', op, INK, 1.4) : '';
      return { rooks: [A], props: '<path d="M138 64q7-4 14 0q7-4 14 0v16q-7-4-14 0q-7-4-14 0z" fill="#fff" stroke="' + INK + '" stroke-width="1.6" stroke-linejoin="round" opacity="' + op + '"/>' + ln('M152 64v16', op, INK, 1.2) + pg(p1) + pg(p2) + txt(132, 30, 'z', 10, MUTE, op * doze) };
    } },
    twin: { L: 5, rest: 2.8, f: t => {
      const op = fadeLoop(t, 5), gop = op * seg(t, .3, .9);
      const M = tt => { const w = sn(seg(tt, 1, 1.6)), j = sn(seg(tt, 1.9, 2.4)), lk = io(seg(tt, 2.7, 3.1)) * (1 - io(seg(tt, 4, 4.4))); return { ht: 8 - 18 * w, hx: -2 * w, y: -12 * j, sq: .08 * sn(seg(tt, 2.35, 2.55)), ex: 1.6 * lk, es: 1 + .4 * lk, blink: tt > 3.4 && tt < 3.9 ? 1 - .85 * sn(seg(tt, 3.4, 3.9)) : 1 }; };
      return { rooks: [{ x: 80, op, ...M(t) }, { x: 160, flip: true, dash: true, color: MUTE, op: gop, ...M(t - .18) }], props: '' };
    } },
  };

  let uid = 0;
  class SarceSkit extends HTMLElement {
    static get observedAttributes() { return ['name']; }
    connectedCallback() { if (!this.id_) { this.id_ = 'sk' + (++uid); this.style.display = 'block'; } this.t0 = performance.now(); const sk = SK[this.getAttribute('name')] || SK.resign; this.paintAt(sk.rest); this.go(); }
    disconnectedCallback() { cancelAnimationFrame(this.raf); this.raf = 0; }
    attributeChangedCallback() { if (this.id_) { this.t0 = performance.now(); const sk = SK[this.getAttribute('name')] || SK.resign; this.paintAt(sk.rest); } }
    go() { const k = n => { this.paint((n - this.t0) / 1000 * +(this.getAttribute('speed') || 1)); this.raf = requestAnimationFrame(k); }; if (!this.raf) this.raf = requestAnimationFrame(k); }
    paintAt(r) { this.paint(r, true); }
    paint(T, still) {
      const sk = SK[this.getAttribute('name')] || SK.resign, red = this.hasAttribute('reduced') && this.getAttribute('reduced') !== 'false';
      const t = red ? sk.rest : still ? T : T % sk.L, TT = red ? sk.rest : T;
      const { rooks, props } = sk.f(t, TT), id = this.id_;
      this.innerHTML = `<svg viewBox="0 -30 240 140" width="100%" style="display:block;overflow:hidden"><defs><clipPath id="${id}l"><polygon points="-20,80 -20,36 0,34 48,22 68,17 68,80"/></clipPath><clipPath id="${id}u"><polygon points="-20,-30 68,-30 68,14 48,19 0,31 -20,36"/></clipPath><clipPath id="${id}g"><rect x="-100" y="-100" width="440" height="${G + 101.5}"/></clipPath></defs>${ln(`M0 ${G + 1.5}H240`, 1, LINE, 1.5)}<g${sk.clipG ? ` clip-path="url(#${id}g)"` : ''}>${rooks.map(r => rook(r, id)).join('')}</g>${props}</svg>`;
    }
  }
  if (!customElements.get('sarce-skit')) customElements.define('sarce-skit', SarceSkit);
})();

export {}; // a module, so it can be loaded on demand; defining the element is its only effect
