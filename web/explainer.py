"""Explicación visual paso a paso del flujo: corredor → planes → simulación → QUBO → QAOA → resultado.

Solo dibuja; no calcula nada nuevo. Usa los parámetros y, si existe, el resultado del experimento.
"""

import streamlit as st

NS, EW, RED, OK, MUTED = "#3B82F6", "#F59E0B", "#9CA3AF", "#10B981", "rgba(128,128,128,.35)"

CSS = f"""
<style>
.sx {{ font-family: inherit; color: inherit; }}
.sx-strip {{ display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin:4px 0 18px; }}
.sx-chip {{ display:flex; align-items:center; gap:8px; padding:6px 12px; border-radius:999px;
           border:1px solid {MUTED}; font-size:14px; white-space:nowrap; }}
.sx-num {{ width:22px; height:22px; border-radius:50%; background:{NS}; color:#fff; font-weight:700;
          display:flex; align-items:center; justify-content:center; font-size:12px; }}
.sx-arrow {{ opacity:.5; }}
.sx-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(340px,1fr)); gap:14px; }}
.sx-card {{ border:1px solid {MUTED}; border-radius:12px; padding:14px 16px; background:rgba(128,128,128,.06); }}
.sx-card h4 {{ margin:0 0 4px; font-size:16px; display:flex; gap:8px; align-items:center; }}
.sx-card p {{ margin:4px 0 10px; font-size:13.5px; opacity:.85; line-height:1.45; }}
.sx-bar {{ display:flex; height:26px; border-radius:6px; overflow:hidden; margin:4px 0 2px; font-size:12px;
          color:#fff; font-weight:600; }}
.sx-bar div {{ display:flex; align-items:center; justify-content:center; }}
.sx-lbl {{ font-size:12.5px; opacity:.8; margin-top:8px; }}
.sx-combos {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(92px,1fr)); gap:6px; }}
.sx-combo {{ border:1px solid {MUTED}; border-radius:8px; padding:6px 8px; font-size:12px; }}
.sx-combo b {{ font-family:ui-monospace,Menlo,monospace; font-size:13px; letter-spacing:1px; }}
.sx-combo .m {{ height:4px; border-radius:2px; background:{RED}; margin-top:4px; }}
.sx-combo.best {{ border:2px solid {OK}; }}
.sx-combo.best .m {{ background:{OK}; }}
.sx-q {{ display:inline-flex; flex-direction:column; align-items:center; margin:2px 3px; font-size:11px; }}
.sx-q span {{ width:30px; height:30px; border-radius:6px; border:2px solid {MUTED}; display:flex;
             align-items:center; justify-content:center; font-weight:700; font-family:ui-monospace,Menlo,monospace; }}
.sx-q.on span {{ background:{NS}; border-color:{NS}; color:#fff; }}
.sx-q.bad span {{ background:#EF4444; border-color:#EF4444; color:#fff; }}
.sx-group {{ display:inline-block; padding:4px 6px; border-radius:8px; border:1px dashed {MUTED}; margin:2px 4px 2px 0; }}
.sx-prob {{ display:grid; grid-template-columns:72px 1fr 54px; gap:6px; align-items:center; font-size:12px; margin:2px 0; }}
.sx-prob .track {{ height:14px; background:rgba(128,128,128,.15); border-radius:4px; overflow:hidden; }}
.sx-prob .fill {{ height:100%; background:{NS}; }}
.sx-prob.best .fill {{ background:{OK}; }}
.sx-prob.bad .fill {{ background:#EF4444; }}
.sx-mono {{ font-family:ui-monospace,Menlo,monospace; }}
.sx-note {{ font-size:12.5px; opacity:.75; margin-top:8px; }}
.sx-road {{ display:flex; align-items:center; margin-top:6px; overflow-x:auto; padding:4px 2px 8px; }}
.sx-end {{ font-size:12px; opacity:.75; text-align:center; padding:0 6px; }}
.sx-x {{ display:flex; flex-direction:column; align-items:center; }}
.sx-ns {{ color:{NS}; font-size:12px; font-weight:700; border-left:4px solid {NS}; padding:4px 0 4px 6px; }}
.sx-box {{ width:44px; height:44px; border-radius:8px; background:#1F2937; color:#fff; font-weight:700;
          font-size:18px; display:flex; align-items:center; justify-content:center;
          box-shadow:0 0 0 4px {EW}; }}
.sx-ew {{ flex:1; min-width:28px; height:5px; background:{EW}; position:relative; margin:0 4px; }}
.sx-ew span {{ position:absolute; top:10px; left:0; right:0; text-align:center; font-size:11.5px; opacity:.8;
              white-space:nowrap; }}
.sx-circ {{ display:flex; align-items:flex-start; margin-top:6px; }}
.sx-g {{ display:flex; flex-direction:column; align-items:center; width:64px; text-align:center; }}
.sx-g div {{ width:48px; height:42px; border-radius:8px; color:#fff; font-weight:700; font-size:18px;
            display:flex; align-items:center; justify-content:center; }}
.sx-g span {{ font-size:11px; opacity:.8; margin-top:4px; line-height:1.25; }}
.sx-wire {{ flex:1; height:2px; background:rgba(128,128,128,.6); margin-top:20px; min-width:8px; }}
.sx-loop {{ font-size:12.5px; margin-top:10px; padding:6px 10px; border:1px dashed {MUTED}; border-radius:8px;
           display:inline-block; }}
</style>
"""


def _bits(plans: dict, ids: list) -> str:
    return "".join(str(plans[i]) for i in ids)


def _corridor(ids: list, travel_s: int) -> str:
    """Corredor dibujado con HTML/CSS (st.html elimina <svg> e imágenes data:)."""
    road = f'<div class="sx-ew"><span>{travel_s} s</span></div>'
    cells = road.join(
        f'<div class="sx-x"><div class="sx-ns">NS ↓</div><div class="sx-box">{cid}</div>'
        f'<div class="sx-ns">↓</div></div>' for cid in ids
    )
    return (f'<div class="sx-road" role="img" aria-label="Corredor de {len(ids)} cruces conectados por EW">'
            f'<div class="sx-end">entran<br>EW →</div>{cells}<div class="sx-end">→ salen</div></div>')


def _plan_bar(plan: dict, cycle: int, all_red: int) -> str:
    g_ns, g_ew = plan["green_s"]["NS"], plan["green_s"]["EW"]
    seg = [(g_ns, NS, f"NS {g_ns}s"), (all_red, RED, ""), (g_ew, EW, f"EW {g_ew}s"), (all_red, RED, "")]
    cells = "".join(f'<div style="width:{100 * s / cycle:.2f}%;background:{c}">{t}</div>' for s, c, t in seg)
    return (f'<div class="sx-lbl">Plan {plan["id"]} · {plan.get("name", "")}</div>'
            f'<div class="sx-bar">{cells}</div>')


def render_explainer(params: dict, result: dict | None) -> None:
    ids = [it["id"] for it in params["intersections"]]
    n = len(ids)
    cycle = params["cycle_s"]
    all_red = params["all_red_s"]
    travel = params["travel_time_s"]
    storage = params["storage_vehicles"]
    plans = params["plans"]

    steps = ["Corredor", "Elegir plan", "Simular todo", "QUBO → qubits", "QAOA en Qiskit", "Comparar"]
    strip = '<span class="sx-arrow">→</span>'.join(
        f'<div class="sx-chip"><div class="sx-num">{i}</div>{s}</div>' for i, s in enumerate(steps, 1)
    )

    # 1 · corredor
    c1 = (f'<div class="sx-card"><h4><span class="sx-num">1</span>El corredor</h4>'
          f'<p>{n} cruces en cadena. Los autos que salen por EW de un cruce llegan al siguiente '
          f'{travel} s después (el número sobre cada tramo). Cada tramo EW guarda como máximo '
          f'<b>{storage} autos</b>: si está lleno, el cruce anterior no puede despachar aunque tenga verde.</p>'
          f'{_corridor(ids, travel)}</div>')

    # 2 · planes
    bars = "".join(_plan_bar(p, cycle, all_red) for p in plans)
    c2 = (f'<div class="sx-card"><h4><span class="sx-num">2</span>Cada cruce elige un plan</h4>'
          f'<p>Un ciclo dura {cycle} s. Cada cruce elige cómo repartir el verde entre NS y EW '
          f'(gris = despeje en rojo). Esa es la única decisión.</p>{bars}'
          f'<div class="sx-note">Con {n} cruces y {len(plans)} planes hay '
          f'<b>{len(plans) ** n} combinaciones</b> posibles.</div></div>')

    # 3 · simulación
    if result:
        combos = result["model"]["combinations"]
        costs = [c["total_cost"] for c in combos]
        lo, hi = min(costs), max(costs)
        best = _bits(result["classical"]["optimal_plans"], ids)
        cards = []
        for c in combos:
            b = _bits(c["plans"], ids)
            frac = 1 - (c["total_cost"] - lo) / (hi - lo) if hi > lo else 1
            cards.append(f'<div class="sx-combo{" best" if b == best else ""}"><b>{b}</b><br>'
                         f'{c["total_cost"]:.2f}<div class="m" style="width:{8 + 92 * frac:.0f}%"></div></div>')
        body3 = (f'<div class="sx-combos">{"".join(cards)}</div>'
                 f'<div class="sx-note">Cada bit es el plan de un cruce ({", ".join(ids)}). '
                 f'Barra más larga = más barato. <span style="color:{OK}">■</span> óptimo exacto '
                 f'<b class="sx-mono">{best}</b> = {result["classical"]["optimal_cost"]:.2f} '
                 f'(base {"0" * n} = {result["classical"]["baseline_cost"]:.2f}).</div>')
    else:
        body3 = '<div class="sx-note">Ejecuta el experimento para ver el costo de cada combinación.</div>'
    c3 = (f'<div class="sx-card"><h4><span class="sx-num">3</span>Simulamos todas las combinaciones</h4>'
          f'<p>El simulador corre cada combinación y le pone un costo (demora + cola máxima + autos '
          f'pendientes). Así conocemos la <b>respuesta exacta</b> para comparar.</p>{body3}</div>')

    # 4 · QUBO one-hot
    example = (result["classical"]["optimal_plans"] if result else {i: 0 for i in ids})
    groups_ok = "".join(
        '<span class="sx-group">' + "".join(
            f'<span class="sx-q{" on" if example[i] == k else ""}"><span>{1 if example[i] == k else 0}</span>'
            f'x<sub>{i}{k}</sub></span>' for k in range(len(plans))) + "</span>"
        for i in ids)
    bad_first = ids[0]
    groups_bad = "".join(
        '<span class="sx-group">' + "".join(
            f'<span class="sx-q{" bad" if i == bad_first else (" on" if example[i] == k else "")}">'
            f'<span>{1 if (i == bad_first or example[i] == k) else 0}</span>x<sub>{i}{k}</sub></span>'
            for k in range(len(plans))) + "</span>"
        for i in ids)
    penalty = f'{result["audit"]["one_hot"]["penalty"]:.2f}' if result else "P"
    c4 = (f'<div class="sx-card"><h4><span class="sx-num">4</span>De costos a qubits (QUBO one-hot)</h4>'
          f'<p>Cada cruce usa {len(plans)} qubits, uno por plan: <b>{len(plans) * n} qubits</b>. '
          f'Debe haber exactamente un 1 por cruce; si no, se suma una penalización de {penalty}.</p>'
          f'<div class="sx-lbl">✅ Válido: un plan por cruce</div>{groups_ok}'
          f'<div class="sx-lbl">❌ Inválido: el cruce {bad_first} tiene dos planes encendidos</div>{groups_bad}'
          f'<div class="sx-note">El costo de cada cruce y de cada par vecino se vuelven los pesos del QUBO.</div></div>')

    # 5 · QAOA
    q = result["quantum"] if result else None
    depth = q["depth"] if q else "p"
    optimizer = q["optimizer"] if q else "optimizador clásico"
    boxes = [("|0⟩", "#6B7280", "inicio"), ("H", NS, "todas las combinaciones"),
             ("γ", EW, "aplica el costo"), ("β", OK, "mezcla"), ("M", "#374151", "medir")]
    gates = '<span class="sx-wire"></span>'.join(
        f'<div class="sx-g"><div style="background:{col}">{t}</div><span>{sub}</span></div>'
        for t, col, sub in boxes)
    c5 = (f'<div class="sx-card"><h4><span class="sx-num">5</span>QAOA en Qiskit</h4>'
          f'<p>El circuito pone todas las combinaciones a la vez, aplica el costo (γ) y mezcla (β), '
          f'{depth} capa(s). Un optimizador clásico repite y ajusta los ángulos para que las '
          f'combinaciones baratas salgan más seguido al medir.</p>'
          f'<div class="sx-circ" role="img" aria-label="Circuito QAOA: inicio, H, costo, mezcla, medir">'
          f'{gates}</div><div class="sx-loop">↻ {optimizer} ajusta γ y β y vuelve a correr el circuito</div></div>')

    # 6 · comparación
    if q:
        best = _bits(result["classical"]["optimal_plans"], ids)
        rows = sorted(q["valid_probabilities"], key=lambda r: -r["probability"])
        top = max([r["probability"] for r in rows] + [q["invalid_probability"]]) or 1
        lines = []
        for r in rows[:8]:
            b = _bits(r["plans"], ids)
            lines.append(f'<div class="sx-prob{" best" if b == best else ""}"><span class="sx-mono">{b}</span>'
                         f'<div class="track"><div class="fill" style="width:{100 * r["probability"] / top:.1f}%">'
                         f'</div></div><span>{r["probability"]:.1%}</span></div>')
        lines.append(f'<div class="sx-prob bad"><span>inválidos</span><div class="track"><div class="fill" '
                     f'style="width:{100 * q["invalid_probability"] / top:.1f}%"></div></div>'
                     f'<span>{q["invalid_probability"]:.1%}</span></div>')
        body6 = ("".join(lines) +
                 f'<div class="sx-note"><span style="color:{OK}">■</span> óptimo exacto <b class="sx-mono">'
                 f'{best}</b>: QAOA lo devuelve con probabilidad <b>{q["original_optimal_probability"]:.1%}</b>. '
                 f'Sale un estado válido el {q["feasible_probability"]:.1%} de las veces. '
                 f'{"Se muestran las 8 más probables. " if len(rows) > 8 else ""}</div>')
    else:
        body6 = '<div class="sx-note">Ejecuta el experimento con QAOA activado para ver la distribución.</div>'
    c6 = (f'<div class="sx-card"><h4><span class="sx-num">6</span>Comparamos con la respuesta exacta</h4>'
          f'<p>Medimos el circuito y vemos con qué probabilidad sale cada combinación. '
          f'Lo ideal: que la más probable sea el óptimo del paso 3.</p>{body6}</div>')

    st.html(f'{CSS}<div class="sx"><div class="sx-strip">{strip}</div>'
            f'<div class="sx-grid">{c1}{c2}{c3}{c4}{c5}{c6}</div></div>')
