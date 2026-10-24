"""Animación de los carros a partir del historial del simulador (no simula nada nuevo).

Cada segundo del historial trae fase, colas y salidas por cruce. Los carros que salen por EW
de un cruce viajan travel_time_s hasta el siguiente; eso se reconstruye para dibujarlos en el tramo.
"""

import json

import streamlit.components.v1 as components

HTML = """
<div id="wrap" style="font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#E5E7EB;background:#111827;
     border-radius:12px;padding:10px 12px 12px">
  <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:8px">
    <button id="play" style="background:#10B981;color:#fff;border:0;border-radius:8px;padding:6px 14px;
            font-weight:700;cursor:pointer">▶ Reproducir</button>
    <label style="font-size:13px">Velocidad
      <select id="speed" style="margin-left:4px;border-radius:6px;padding:2px 4px">
        <option value="1">1×</option><option value="5">5×</option>
        <option value="10" selected>10×</option><option value="20">20×</option>
      </select></label>
    <input id="scrub" type="range" min="0" max="__MAX__" step="1" value="0" style="flex:1;min-width:120px">
    <span id="clock" style="font-variant-numeric:tabular-nums;font-size:13px;min-width:110px;text-align:right"></span>
    <span id="phases" style="font-size:12px;opacity:.85;width:100%"></span>
  </div>
  <canvas id="cv" style="width:100%;height:330px;display:block;border-radius:8px"></canvas>
  <div style="display:flex;gap:16px;flex-wrap:wrap;font-size:12px;opacity:.85;margin-top:8px">
    <span><b style="color:#60A5FA">■</b> carro NS</span>
    <span><b style="color:#F59E0B">■</b> carro EW</span>
    <span>● verde / rojo = semáforo de cada eje</span>
    <span>Los EW que salen de un cruce llegan al siguiente en __TRAVEL__ s</span>
  </div>
</div>
<script>
const D = __DATA__;
const H = D.history, N = D.ids.length, T = H.length, TRAVEL = D.travel;
const cv = document.getElementById('cv'), ctx = cv.getContext('2d');
const play = document.getElementById('play'), scrub = document.getElementById('scrub');
const speedSel = document.getElementById('speed'), clock = document.getElementById('clock');
const phases = document.getElementById('phases');
const NS = '#60A5FA', EW = '#F59E0B', GREEN = '#22C55E', RED = '#EF4444';
const CAR_L = 14, CAR_W = 8, GAP = 4, ROAD = 30;

// Carros en movimiento reconstruidos desde las salidas: tramo i -> i+1, o salida del sistema.
const moving = [];
H.forEach((s, t) => s.departures.forEach((d, i) => {
  for (let k = 0; k < d.NS; k++) moving.push({kind: 'ns', i, t0: t + k * 0.3, dur: 2.5});
  for (let k = 0; k < d.EW; k++) {
    if (i < N - 1) moving.push({kind: 'link', i, t0: t + k * 0.3, dur: TRAVEL});
    else moving.push({kind: 'exit', i, t0: t + k * 0.3, dur: 2.5});
  }
}));

let W = 0, Hh = 0, tf = 0, playing = false, last = null;
function resize() {
  const r = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  W = r.width; Hh = r.height; cv.width = W * dpr; cv.height = Hh * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  draw();
}
const yRoad = () => Hh * 0.52;
const xOf = i => W * (i + 1) / (N + 1);

function car(x, y, horizontal, color) {
  ctx.fillStyle = color;
  const w = horizontal ? CAR_L : CAR_W, h = horizontal ? CAR_W : CAR_L;
  ctx.beginPath(); ctx.roundRect(x - w / 2, y - h / 2, w, h, 2.5); ctx.fill();
}
function light(x, y, on, label) {
  ctx.fillStyle = '#0B0F17'; ctx.beginPath(); ctx.roundRect(x - 9, y - 9, 18, 18, 5); ctx.fill();
  ctx.fillStyle = on ? GREEN : RED; ctx.beginPath(); ctx.arc(x, y, 6, 0, 7); ctx.fill();
  ctx.fillStyle = '#9CA3AF'; ctx.font = '10px system-ui'; ctx.textAlign = 'center'; ctx.fillText(label, x, y - 13);
}
function more(x, y, k) {
  if (k <= 0) return;
  ctx.fillStyle = '#F9FAFB'; ctx.font = 'bold 11px system-ui'; ctx.textAlign = 'center'; ctx.fillText('+' + k, x, y);
}
// Extremo de la cola EW del cruce i (donde se detiene un carro que llega).
function ewTail(i, q) {
  const stop = xOf(i) - ROAD / 2 - 6, left = i === 0 ? 8 : xOf(i - 1) + ROAD / 2 + 8;
  const cap = Math.max(0, Math.floor((stop - left) / (CAR_L + GAP)));
  return {stop, left, cap, tail: stop - Math.min(q, cap) * (CAR_L + GAP)};
}

function draw() {
  if (!W) return;
  const s = H[Math.min(T - 1, Math.floor(tf))], y = yRoad();
  ctx.fillStyle = '#1C2A22'; ctx.fillRect(0, 0, W, Hh);
  // calles
  ctx.fillStyle = '#374151'; ctx.fillRect(0, y - ROAD / 2, W, ROAD);
  for (let i = 0; i < N; i++) ctx.fillRect(xOf(i) - ROAD / 2, 0, ROAD, Hh);
  ctx.strokeStyle = 'rgba(255,255,255,.35)'; ctx.setLineDash([8, 8]); ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
  for (let i = 0; i < N; i++) { ctx.beginPath(); ctx.moveTo(xOf(i), 0); ctx.lineTo(xOf(i), Hh); ctx.stroke(); }
  ctx.setLineDash([]);

  for (let i = 0; i < N; i++) {
    const x = xOf(i), q = s.queues[i], ph = s.phases[i];
    ctx.fillStyle = '#4B5563'; ctx.fillRect(x - ROAD / 2, y - ROAD / 2, ROAD, ROAD);
    // cola NS: carros detenidos arriba del cruce
    const nsStop = y - ROAD / 2 - 6, nsCap = Math.floor((nsStop - 14) / (CAR_L + GAP));
    for (let k = 0; k < Math.min(q.NS, nsCap); k++) car(x - 7, nsStop - CAR_L / 2 - k * (CAR_L + GAP), false, NS);
    more(x - 24, 12, q.NS - nsCap);
    // cola EW: carros detenidos a la izquierda del cruce
    const e = ewTail(i, q.EW);
    for (let k = 0; k < Math.min(q.EW, e.cap); k++) car(e.stop - CAR_L / 2 - k * (CAR_L + GAP), y - 7, true, EW);
    more(e.left + 10, y - 18, q.EW - e.cap);
    // semáforos y etiquetas
    light(x - ROAD / 2 - 14, y - ROAD / 2 - 14, ph === 'NS', 'NS');
    light(x - ROAD / 2 - 14, y + ROAD / 2 + 14, ph === 'EW', 'EW');
    ctx.fillStyle = '#F9FAFB'; ctx.font = 'bold 15px system-ui'; ctx.textAlign = 'center';
    ctx.fillText(D.ids[i], x + ROAD / 2 + 14, y + ROAD / 2 + 20);
    ctx.font = '11px system-ui'; ctx.fillStyle = '#D1D5DB';
    ctx.fillText('plan ' + D.plans[i], x + ROAD / 2 + 14, y + ROAD / 2 + 34);
    ctx.fillText('cola NS ' + q.NS + ' · EW ' + q.EW, x, Hh - 8);
  }
  // carros en movimiento
  for (const m of moving) {
    const p = (tf - m.t0) / m.dur;
    if (p < 0 || p >= 1) continue;
    const x = xOf(m.i);
    if (m.kind === 'ns') car(x - 7, y - ROAD / 2 + p * (Hh - y + ROAD / 2), false, NS);
    else if (m.kind === 'exit') car(x + p * (W - x), y - 7, true, EW);
    else {
      const nxt = H[Math.min(T - 1, Math.floor(tf))].queues[m.i + 1].EW;
      const end = ewTail(m.i + 1, nxt).tail - CAR_L / 2;
      const start = x + ROAD / 2;
      car(start + p * Math.max(0, end - start), y - 7, true, EW);
    }
  }
  const phaseTxt = s.phases.map((p, i) => D.ids[i] + ' ' + (p === 'CLEAR' ? 'rojo' : p)).join(' · ');
  clock.textContent = 't = ' + Math.floor(tf) + ' / ' + (T - 1) + ' s';
  phases.textContent = 'Verde: ' + phaseTxt;
  scrub.value = Math.floor(tf);
}

function frame(ts) {
  if (!playing) return;
  if (last !== null) tf += (ts - last) / 1000 * Number(speedSel.value);
  last = ts;
  if (tf >= T - 1) { tf = T - 1; setPlaying(false); }
  draw();
  requestAnimationFrame(frame);
}
function setPlaying(v) {
  playing = v; last = null;
  play.textContent = v ? '❚❚ Pausa' : '▶ Reproducir';
  if (v) { if (tf >= T - 1) tf = 0; requestAnimationFrame(frame); }
}
play.onclick = () => setPlaying(!playing);
scrub.oninput = () => { tf = Number(scrub.value); draw(); };
new ResizeObserver(resize).observe(cv);
</script>
"""


def render_animation(selected: dict, params: dict) -> None:
    ids = [it["id"] for it in params["intersections"]]
    data = {
        "ids": ids,
        "plans": [selected["plans"][i] for i in ids],
        "travel": params["travel_time_s"],
        "history": [{"phases": h["phases"], "queues": h["queues"], "departures": h["departures"]}
                    for h in selected["history"]],
    }
    html = (HTML.replace("__DATA__", json.dumps(data, separators=(",", ":")))
                .replace("__MAX__", str(len(selected["history"]) - 1))
                .replace("__TRAVEL__", str(params["travel_time_s"])))
    components.html(html, height=455)
