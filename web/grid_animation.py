"""Varias avenidas EW de la grilla en un solo canvas, desde el historial del simulador.

Cada avenida reutiliza animation_payload de web/animation.py. Las calles NS cortan todas las
avenidas, pero el motor no tiene tramos NS: los autos NS salen hacia abajo y se desvanecen.
"""

import json

import streamlit as st

from model.traffic import simulate_chain
from web.animation import animation_payload

MAX_COLS = 10
BAND_PX = 230

HTML = """
<div id="wrap" style="font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#E5E7EB;background:#111827;
     border-radius:12px;padding:10px 12px 12px">
  <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:8px">
    <button id="play" style="background:#10B981;color:#fff;border:0;border-radius:8px;padding:6px 14px;
            font-weight:700;cursor:pointer">▶ Reproducir</button>
    <button id="restart" style="background:#374151;color:#fff;border:0;border-radius:8px;padding:6px 10px;
            cursor:pointer">↶ Inicio</button>
    <label style="font-size:13px">Velocidad
      <select id="speed" style="margin-left:4px;border-radius:6px;padding:2px 4px">
        <option value="1">1×</option><option value="5">5×</option>
        <option value="10" selected>10×</option><option value="20">20×</option>
      </select></label>
    <input id="scrub" aria-label="Instante de simulación" type="range" min="0" max="__MAX__" step="1" value="0" style="flex:1;min-width:120px">
    <span id="clock" style="font-variant-numeric:tabular-nums;font-size:13px;min-width:110px;text-align:right"></span>
  </div>
  <canvas id="cv" style="width:100%;height:__HEIGHT__px;display:block;border-radius:8px"></canvas>
  <div style="display:flex;gap:16px;flex-wrap:wrap;font-size:12px;opacity:.85;margin-top:8px">
    <span><b style="color:#60A5FA">■</b> carro NS</span>
    <span><b style="color:#F59E0B">■</b> carro EW</span>
    <span>● verde / rojo = semáforo de cada eje</span>
    <span>Los EW que salen de un cruce llegan al siguiente en __TRAVEL__ s</span>
    <span><b style="color:#9CA3AF">tramo x/K</b> = autos en el tramo EW (rojo = lleno)</span>
    <span>Los NS salen hacia abajo y desaparecen: no hay enlace NS entre avenidas</span>
  </div>
</div>
<script>
const D = __DATA__;
const R = D.rows.length, N = D.rows[0].ids.length, T = D.rows[0].history.length;
const TRAVEL = D.travel, K = D.storage;
const cv = document.getElementById('cv'), ctx = cv.getContext('2d');
const play = document.getElementById('play'), scrub = document.getElementById('scrub');
const speedSel = document.getElementById('speed'), clock = document.getElementById('clock');
const NS = '#60A5FA', EW = '#F59E0B', GREEN = '#22C55E', RED = '#EF4444';
const CAR_L = 14, CAR_W = 8, GAP = 4, ROAD = 30;

// Carros en movimiento por avenida, reconstruidos desde las salidas (misma regla que animation.py).
const moving = D.rows.map(row => {
  const list = [];
  row.history.forEach((s, t) => s.departures.forEach((d, i) => {
    for (let k = 0; k < d.NS; k++) list.push({kind: 'ns', i, t0: t + k * 0.3, dur: 2.5});
    for (let k = 0; k < d.EW; k++) {
      if (i < N - 1) list.push({kind: 'link', i, t0: t + k * 0.3, dur: TRAVEL});
      else list.push({kind: 'exit', i, t0: t + k * 0.3, dur: 2.5});
    }
  }));
  return list;
});

let W = 0, Hh = 0, tf = 0, playing = false, last = null, animationFrame = null;
function resize() {
  const r = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  W = r.width; Hh = r.height; cv.width = W * dpr; cv.height = Hh * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  draw();
}
const band = () => Hh / R;
const yRoad = r => band() * (r + 0.5);
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
function pill(x, y, text, bg) {
  ctx.font = 'bold 11px system-ui'; const w = ctx.measureText(text).width + 12;
  const cx = Math.min(Math.max(x, w / 2 + 2), W - w / 2 - 2);
  ctx.fillStyle = bg; ctx.beginPath(); ctx.roundRect(cx - w / 2, y - 9, w, 18, 9); ctx.fill();
  ctx.fillStyle = '#F9FAFB'; ctx.textAlign = 'center'; ctx.fillText(text, cx, y + 4);
}
function more(x, y, k) {
  if (k <= 0) return;
  ctx.fillStyle = '#F9FAFB'; ctx.font = 'bold 11px system-ui'; ctx.textAlign = 'center'; ctx.fillText('+' + k, x, y);
}
function ewTail(i, q) {
  const stop = xOf(i) - ROAD / 2 - 6, left = i === 0 ? 8 : xOf(i - 1) + ROAD / 2 + 8;
  const cap = Math.max(0, Math.floor((stop - left) / (CAR_L + GAP)));
  return {stop, left, cap, tail: stop - Math.min(q, cap) * (CAR_L + GAP)};
}

function drawRow(r, index) {
  const row = D.rows[r], s = row.history[index], y = yRoad(r), top = y - band() / 2;
  ctx.fillStyle = '#374151'; ctx.fillRect(0, y - ROAD / 2, W, ROAD);
  ctx.strokeStyle = 'rgba(255,255,255,.35)'; ctx.setLineDash([8, 8]); ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle = '#F9FAFB'; ctx.font = 'bold 12px system-ui'; ctx.textAlign = 'left';
  ctx.fillText(row.label, 8, y - ROAD / 2 - 6);
  for (let i = 0; i < N; i++) {
    const x = xOf(i), q = s.queues[i], ph = s.phases[i];
    ctx.fillStyle = '#4B5563'; ctx.fillRect(x - ROAD / 2, y - ROAD / 2, ROAD, ROAD);
    // cola NS arriba del cruce, dentro de la mitad superior de la banda
    const nsStop = y - ROAD / 2 - 6, nsCap = Math.max(0, Math.floor((nsStop - top - 18) / (CAR_L + GAP)));
    for (let k = 0; k < Math.min(q.NS, nsCap); k++) car(x - 7, nsStop - CAR_L / 2 - k * (CAR_L + GAP), false, NS);
    more(x - 24, top + 14, q.NS - nsCap);
    const e = ewTail(i, q.EW);
    for (let k = 0; k < Math.min(q.EW, e.cap); k++) car(e.stop - CAR_L / 2 - k * (CAR_L + GAP), y - 7, true, EW);
    more(e.left + 10, y - 18, q.EW - e.cap);
    const occ = s.occupancy ? s.occupancy[i] : null;
    if (occ !== null) pill((e.left + e.stop) / 2, y + ROAD / 2 + 14, occ + '/' + K, occ >= K ? RED : '#4B5563');
    if (s.blocked && s.blocked[i]) {
      ctx.strokeStyle = RED; ctx.lineWidth = 3; ctx.strokeRect(x - ROAD / 2 - 3, y - ROAD / 2 - 3, ROAD + 6, ROAD + 6);
    }
    light(x - ROAD / 2 - 14, y - ROAD / 2 - 14, ph === 'NS', 'NS');
    light(x - ROAD / 2 - 14, y + ROAD / 2 + 14, ph === 'EW', 'EW');
    ctx.fillStyle = '#D1D5DB'; ctx.font = '11px system-ui'; ctx.textAlign = 'center';
    ctx.fillText('plan ' + row.plans[i], x + ROAD / 2 + 18, y + ROAD / 2 + 14);
  }
  for (const m of moving[r]) {
    const p = (tf - m.t0) / m.dur;
    if (p < 0 || p >= 1) continue;
    const x = xOf(m.i);
    if (m.kind === 'ns') {
      // Cruza la avenida y se desvanece antes de la mitad de la banda inferior.
      ctx.globalAlpha = 1 - p;
      car(x - 7, y - ROAD / 2 + p * (band() * 0.45 + ROAD / 2), false, NS);
      ctx.globalAlpha = 1;
    } else if (m.kind === 'exit') car(x + p * (W - x), y - 7, true, EW);
    else {
      const end = ewTail(m.i + 1, s.queues[m.i + 1].EW).tail - CAR_L / 2, start = x + ROAD / 2;
      car(start + p * Math.max(0, end - start), y - 7, true, EW);
    }
  }
}

function draw() {
  if (!W) return;
  const index = Math.min(T - 1, Math.floor(tf));
  ctx.fillStyle = '#1C2A22'; ctx.fillRect(0, 0, W, Hh);
  ctx.fillStyle = '#374151';
  for (let i = 0; i < N; i++) ctx.fillRect(xOf(i) - ROAD / 2, 0, ROAD, Hh);
  ctx.strokeStyle = 'rgba(255,255,255,.35)'; ctx.setLineDash([8, 8]); ctx.lineWidth = 1.5;
  for (let i = 0; i < N; i++) { ctx.beginPath(); ctx.moveTo(xOf(i), 0); ctx.lineTo(xOf(i), Hh); ctx.stroke(); }
  ctx.setLineDash([]);
  // Etiqueta tenue entre avenidas: las calles NS no enlazan filas en el motor.
  ctx.fillStyle = 'rgba(229,231,235,.35)'; ctx.font = '10px system-ui'; ctx.textAlign = 'center';
  for (let r = 0; r < R - 1; r++) {
    const yMid = band() * (r + 1);
    for (let i = 0; i < N; i++) {
      ctx.save(); ctx.translate(xOf(i) + 3, yMid); ctx.rotate(-Math.PI / 2);
      ctx.fillText('sin enlace NS en el modelo', 0, 0); ctx.restore();
    }
  }
  for (let r = 0; r < R; r++) drawRow(r, index);
  clock.textContent = 't = ' + D.rows[0].history[index].t + ' / ' + D.rows[0].history[T - 1].t + ' s';
  scrub.value = index;
}

function frame(ts) {
  if (!playing) { animationFrame = null; return; }
  if (last !== null) tf += (ts - last) / 1000 * Number(speedSel.value);
  last = ts;
  if (tf >= T - 1) { tf = T - 1; setPlaying(false); draw(); return; }
  draw();
  animationFrame = requestAnimationFrame(frame);
}
function setPlaying(v) {
  if (animationFrame !== null) cancelAnimationFrame(animationFrame);
  animationFrame = null;
  playing = v; last = null;
  play.textContent = v ? '❚❚ Pausa' : '▶ Reproducir';
  play.setAttribute('aria-pressed', String(v));
  if (v) { if (tf >= T - 1) tf = 0; draw(); animationFrame = requestAnimationFrame(frame); }
}
play.onclick = () => setPlaying(!playing);
scrub.oninput = () => { setPlaying(false); tf = Number(scrub.value); draw(); };
document.getElementById('restart').onclick = () => { setPlaying(false); tf = 0; draw(); };
document.addEventListener('visibilitychange', () => { if (document.hidden) setPlaying(false); });
new ResizeObserver(resize).observe(cv);
</script>
"""


def grid_animation_html(rows_results: list[dict], params_by_row: list[dict]) -> str:
    """rows_results: entradas de run_grid()["row_results"]; anima el plan DP de cada una."""
    if not rows_results or len(rows_results) != len(params_by_row):
        raise ValueError("Se requiere al menos una avenida y sus parámetros")
    rows = []
    for row, params in zip(rows_results, params_by_row):
        plans = row["methods"]["dp"]["plans"]
        ids = [it["id"] for it in params["intersections"]]
        sim = simulate_chain(plans, params, keep_history=True)
        payload = animation_payload({"plans": dict(zip(ids, plans)), "history": sim["history"]}, params)
        payload["label"] = f"Avenida EW · fila {row['row']}"
        rows.append(payload)
    data = {"rows": rows, "travel": rows[0]["travel"], "storage": rows[0]["storage"]}
    serialized = json.dumps(data, separators=(",", ":")).replace("<", "\\u003c")
    return (HTML.replace("__MAX__", str(len(rows[0]["history"]) - 1))
                .replace("__HEIGHT__", str(BAND_PX * len(rows)))
                .replace("__TRAVEL__", str(data["travel"]))
                .replace("__DATA__", serialized))


def render_grid_animation(rows_results: list[dict], params_by_row: list[dict]) -> None:
    if len(params_by_row[0]["intersections"]) > MAX_COLS:
        st.info(f"La animación está disponible hasta {MAX_COLS} cruces por fila")
        return
    st.iframe(grid_animation_html(rows_results, params_by_row),
              height=BAND_PX * len(rows_results) + 150)
