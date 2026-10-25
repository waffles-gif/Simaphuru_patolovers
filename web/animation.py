"""Animación de los carros a partir del historial del simulador (no simula nada nuevo).

Cada segundo del historial trae fase, colas y salidas por cruce. Los carros que salen por EW
de un cruce viajan travel_time_s hasta el siguiente; eso se reconstruye para dibujarlos en el tramo.
"""

import json

import streamlit.components.v1 as components

HTML = """
<style>
  #cards { display:grid;grid-template-columns:repeat(__N__,minmax(0,1fr));gap:8px;margin-top:10px; }
  .state-card { background:#1F2937;border:1px solid #4B5563;border-radius:8px;padding:9px;min-width:0; }
  .state-card h3 { font-size:13px;margin:0 0 5px; }
  .state-card .phase { font-weight:700;font-size:12px;color:#22C55E; }
  .state-card .snapshot { font-size:11px;color:#D1D5DB;margin:3px 0; }
  .state-card dl { display:grid;grid-template-columns:minmax(0,1fr) auto;gap:3px 5px;margin:5px 0 0;font-size:12px; }
  .state-card dt { color:#D1D5DB; } .state-card dd { margin:0;font-variant-numeric:tabular-nums; }
  @media (max-width:380px) { #cards { grid-template-columns:repeat(2,minmax(0,1fr)); } }
</style>
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
    <span id="phases" style="font-size:12px;opacity:.85;width:100%"></span>
  </div>
  <canvas id="cv" style="width:100%;height:280px;display:block;border-radius:8px"></canvas>
  <section id="cards" aria-label="Tarjetas sincronizadas de los cruces"></section>
  <div style="display:flex;gap:16px;flex-wrap:wrap;font-size:12px;opacity:.85;margin-top:8px">
    <span><b style="color:#60A5FA">■</b> carro NS</span>
    <span><b style="color:#F59E0B">■</b> carro EW</span>
    <span>● verde / rojo = semáforo de cada eje</span>
    <span>Los EW que salen de un cruce llegan al siguiente en __TRAVEL__ s</span>
    <span><b style="color:#9CA3AF">tramo x/K</b> = autos en el tramo EW (rojo = lleno)</span>
    <span><b style="color:#EF4444">BLOQUEO</b> = evento registrado al intentar despachar en ese paso</span>
    <span><b style="color:#9CA3AF">esperan fuera</b> = llegadas que no caben en el tramo</span>
  </div>
</div>
<script>
const D = __DATA__;
const H = D.history, N = D.ids.length, T = H.length, TRAVEL = D.travel, K = D.storage;
const cv = document.getElementById('cv'), ctx = cv.getContext('2d');
const play = document.getElementById('play'), scrub = document.getElementById('scrub');
const speedSel = document.getElementById('speed'), clock = document.getElementById('clock');
const phases = document.getElementById('phases');
const NS = '#60A5FA', EW = '#F59E0B', GREEN = '#22C55E', RED = '#EF4444';
const CAR_L = 14, CAR_W = 8, GAP = 4, ROAD = 30;

// Canvas, tarjetas, reloj y deslizador leen el mismo registro H[floor(tf)].
const cards = D.ids.map((id, i) => {
  const card = document.createElement('article');
  card.className = 'state-card'; card.dataset.junction = id;
  const heading = document.createElement('h3'); heading.textContent = 'Cruce ' + id + ' · plan ' + D.plans[i];
  const phase = document.createElement('div'); phase.className = 'phase';
  const snapshot = document.createElement('div'); snapshot.className = 'snapshot';
  const fields = document.createElement('dl');
  const values = {};
  for (const label of ['Cola NS', 'Cola EW', 'Tramo', 'Viajan', 'Fuera', 'Bloqueo']) {
    const dt = document.createElement('dt'), dd = document.createElement('dd');
    dt.textContent = label; values[label] = dd; fields.append(dt, dd);
  }
  card.append(heading, phase, snapshot, fields);
  document.getElementById('cards').append(card);
  return {card, phase, snapshot, values};
});
function renderCards(s, index) {
  cards.forEach((c, i) => {
    c.card.dataset.snapshotIndex = String(index);
    c.phase.textContent = s.phases[i] === 'CLEAR' ? 'Despeje' : 'Verde ' + s.phases[i];
    c.phase.title = s.phases[i] === 'CLEAR' ? 'Ambos ejes en rojo' : 'Eje con luz verde';
    c.phase.style.color = s.phases[i] === 'CLEAR' ? RED : GREEN;
    c.snapshot.textContent = 't = ' + s.t + ' s';
    c.values['Cola NS'].textContent = s.queues[i].NS;
    c.values['Cola EW'].textContent = s.queues[i].EW;
    const occupancy = s.occupancy ? s.occupancy[i] : null;
    c.values['Tramo'].textContent = occupancy === null ? '—' : occupancy + '/' + K;
    c.values['Viajan'].textContent = occupancy === null ? '—' : occupancy - s.queues[i].EW;
    c.values['Fuera'].textContent = s.backlog ? s.backlog[i] : '—';
    const blocked = s.blocked ? s.blocked[i] : null;
    c.values['Bloqueo'].textContent = blocked === null ? 'sin registro' : (blocked ? 'Sí' : 'No');
    c.values['Bloqueo'].style.color = blocked ? RED : '#E5E7EB';
    c.card.style.borderColor = blocked ? RED : '#4B5563';
  });
}

// Carros en movimiento reconstruidos desde las salidas: tramo i -> i+1, o salida del sistema.
const moving = [];
H.forEach((s, t) => s.departures.forEach((d, i) => {
  for (let k = 0; k < d.NS; k++) moving.push({kind: 'ns', i, t0: t + k * 0.3, dur: 2.5});
  for (let k = 0; k < d.EW; k++) {
    if (i < N - 1) moving.push({kind: 'link', i, t0: t + k * 0.3, dur: TRAVEL});
    else moving.push({kind: 'exit', i, t0: t + k * 0.3, dur: 2.5});
  }
}));

let W = 0, Hh = 0, tf = 0, playing = false, last = null, animationFrame = null;
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
// Extremo de la cola EW del cruce i (donde se detiene un carro que llega).
function ewTail(i, q) {
  const stop = xOf(i) - ROAD / 2 - 6, left = i === 0 ? 8 : xOf(i - 1) + ROAD / 2 + 8;
  const cap = Math.max(0, Math.floor((stop - left) / (CAR_L + GAP)));
  return {stop, left, cap, tail: stop - Math.min(q, cap) * (CAR_L + GAP)};
}

function draw() {
  if (!W) return;
  const index = Math.min(T - 1, Math.floor(tf)), s = H[index], y = yRoad();
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
    // ocupación del tramo EW que entra a este cruce y autos que esperan fuera de la red
    const mid = (e.left + e.stop) / 2, occ = s.occupancy ? s.occupancy[i] : null;
    if (occ !== null) {
      const full = occ >= K;
      pill(mid, y + ROAD / 2 + 56, 'tramo ' + occ + '/' + K, full ? RED : '#4B5563');
    }
    const back = s.backlog ? s.backlog[i] : 0;
    if (back > 0) pill(mid, y - ROAD / 2 - 70, back + ' esperan fuera', '#6B7280');
    // Reproducir el evento del motor, no inferirlo de la ocupación posterior al servicio.
    if (s.blocked && s.blocked[i]) {
      ctx.strokeStyle = RED; ctx.lineWidth = 3; ctx.strokeRect(x - ROAD / 2 - 3, y - ROAD / 2 - 3, ROAD + 6, ROAD + 6);
      pill(x + ROAD, y - ROAD / 2 - 100, 'BLOQUEO hacia ' + D.ids[i + 1], RED);
    }
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
  clock.textContent = 't = ' + s.t + ' / ' + H[T - 1].t + ' s';
  phases.textContent = 'Fases: ' + phaseTxt;
  scrub.value = index;
  renderCards(s, index);
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


def animation_payload(selected: dict, params: dict) -> dict:
    """Una sola fuente para todas las vistas del reproductor; no modifica la historia."""
    ids = [it["id"] for it in params["intersections"]]
    if not selected["history"] or set(selected["plans"]) != set(ids):
        raise ValueError("El historial debe incluir los mismos cruces y al menos un paso")
    for step in selected["history"]:
        if any(len(step[key]) != len(ids) for key in ("phases", "queues", "departures")):
            raise ValueError("El paso del historial no corresponde al número de cruces")
        if any(step.get(key) is not None and len(step[key]) != len(ids)
               for key in ("occupancy", "backlog", "blocked")):
            raise ValueError("Los estados del historial deben incluir todos los cruces")
    return {
        "ids": ids,
        "plans": [selected["plans"][i] for i in ids],
        "travel": params["travel_time_s"],
        "storage": params["storage_vehicles"],
        "history": [{"t": h["t"], "phases": h["phases"], "queues": h["queues"],
                     "departures": h["departures"], "occupancy": h.get("occupancy"),
                     "backlog": h.get("backlog"), "blocked": h.get("blocked")}
                    for h in selected["history"]],
    }


def animation_html(selected: dict, params: dict) -> str:
    data = animation_payload(selected, params)
    # Un identificador importado no debe poder cerrar el elemento script del documento.
    serialized = json.dumps(data, separators=(",", ":")).replace("<", "\\u003c")
    return (HTML.replace("__MAX__", str(len(selected["history"]) - 1))
                .replace("__N__", str(len(data["ids"])))
                .replace("__TRAVEL__", str(params["travel_time_s"]))
                .replace("__DATA__", serialized))


def render_animation(selected: dict, params: dict) -> None:
    components.html(animation_html(selected, params), height=750, scrolling=True)
