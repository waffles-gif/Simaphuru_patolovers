"""Interfaz sobre el motor existente del equipo. No redefine sus ecuaciones."""

import json

import altair as alt
import pandas as pd
import streamlit as st

from simaphuru.team import default_team_params, run_team_experiment, team_fingerprint
from web.animation import render_animation
from web.explainer import render_explainer

PLAN_LABEL = {0: "30/30", 1: "40/20"}


def _plans(plans: dict) -> str:
    """{'A': 1, 'B': 0} -> 'A=1 · B=0'."""
    return " · ".join(f"{k}={v}" for k, v in plans.items())


def _benchmark_rows(result: dict) -> list[dict]:
    """Una fila por método, todas medidas con el mismo simulador y el mismo óptimo exacto."""
    classical, pairwise, q = result["classical"], result["pairwise_classical"], result["quantum"]
    combos = result["model"]["combinations"]
    n_states = len(combos)
    best = classical["optimal_cost"]
    n_opt = sum(abs(c["total_cost"] - best) < 1e-9 for c in combos)
    ids = list(classical["optimal_plans"])

    def row(method, kind, plans, cost, p_opt, valid, work, ms):
        return {"Método": method, "Tipo": kind, "Plan elegido": plans, "Costo real": cost,
                "Brecha vs óptimo": cost - best, "Brecha %": 100 * (cost - best) / best,
                "P(óptimo)": p_opt, "Soluciones válidas": valid, "Trabajo": work,
                "Tiempo": "—" if ms is None else f"{ms:.1f} ms"}

    rows = [
        row("Enumeración", "Clásico exacto", _plans(classical["optimal_plans"]), best,
            1.0, 1.0, f"{n_states} simulaciones del corredor", classical["runtime_ms"]),
        row("Prog. dinámica (pares)", "Clásico aproximado", _plans(pairwise["optimal_plans"]),
            pairwise["original_cost"], float(pairwise["original_regret"] < 1e-9), 1.0,
            f"{len(ids) - 1} {'par' if len(ids) == 2 else 'pares'} × 4 combinaciones", pairwise["runtime_ms"]),
    ]
    if q:
        rows += [
            row(f"QAOA p={q['depth']} · más probable", "Cuántico", _plans(q["representative_plans"]),
                q["representative_original_cost"], q["original_optimal_probability"],
                q["feasible_probability"], f"{q['evaluations']} evaluaciones del circuito, {2 * len(ids)} qubits",
                q["runtime_ms"]),
            row(f"QAOA p={q['depth']} · una medición", "Cuántico", "según distribución",
                q["conditional_expected_original"], q["original_optimal_probability"],
                q["feasible_probability"], "costo esperado entre soluciones válidas", None),
        ]
    rows += [
        row("Al azar", "Referencia", "uniforme", classical["uniform_feasible_expected_cost"],
            n_opt / n_states, 1.0, "ninguno", None),
        row("Programa base", "Referencia", _plans({i: 0 for i in ids}), classical["baseline_cost"],
            float(abs(classical["baseline_cost"] - best) < 1e-9), 1.0, "1 simulación", None),
    ]
    return rows


TYPE_COLORS = {"Clásico exacto": "#5B9BE6", "Clásico aproximado": "#8DB9EE",
               "Cuántico": "#3DBE80", "Referencia": "#6B7682"}


def _render_comparison(result: dict) -> None:
    rows = _benchmark_rows(result)
    df = pd.DataFrame(rows)
    st.markdown("**Calidad de la solución**: todos los planes se evalúan con el mismo simulador.")
    st.dataframe(
        df[["Tipo", "Método", "Plan elegido", "Costo real", "Brecha %", "P(óptimo)", "Soluciones válidas"]],
        hide_index=True, width="stretch",
        column_config={
            "Costo real": st.column_config.NumberColumn(format="%.3f"),
            "Brecha %": st.column_config.NumberColumn(format="%+.2f %%"),
            "P(óptimo)": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
            "Soluciones válidas": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
        },
    )
    st.caption("Costo real = costo del simulador para el plan elegido (menor es mejor). Brecha % = cuánto más caro "
               "que el óptimo exacto. P(óptimo) = probabilidad de obtener el plan óptimo en una ejecución.")
    best = result["classical"]["optimal_cost"]
    bars = alt.Chart(df).mark_bar(cornerRadiusEnd=3).encode(
        x=alt.X("Costo real:Q", title="Costo real (menor es mejor)"),
        y=alt.Y("Método:N", sort=alt.EncodingSortField("Costo real", order="ascending"), title=None,
                axis=alt.Axis(labelLimit=320)),
        color=alt.Color("Tipo:N", scale=alt.Scale(domain=list(TYPE_COLORS), range=list(TYPE_COLORS.values())),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["Método", "Plan elegido", alt.Tooltip("Costo real:Q", format=".3f"),
                 alt.Tooltip("Brecha %:Q", format="+.2f")],
    )
    optimum = alt.Chart(pd.DataFrame({"x": [best]})).mark_rule(strokeDash=[4, 4], color="#E9E6DF").encode(x="x:Q")
    st.altair_chart((bars + optimum).properties(height=48 * len(rows)), width="stretch")
    st.caption("La línea punteada marca el óptimo exacto.")
    st.markdown("**Costo de cómputo**")
    st.dataframe(df[["Tipo", "Método", "Trabajo", "Tiempo"]], hide_index=True, width="stretch")
    st.caption("Los tiempos no son comparables entre sí: QAOA y la programación dinámica parten de la tabla de "
               "costos que ya calculó la enumeración. QAOA corre en un simulador de vector de estado, no en "
               "hardware.")


def _render_classical(result: dict, ids: list[str]) -> None:
    classical, pairwise, audit = result["classical"], result["pairwise_classical"], result["audit"]
    probs = {}
    if result["quantum"]:
        probs = {_plans(r["plans"]): r["probability"] for r in result["quantum"]["valid_probabilities"]}
    rows = []
    for c in sorted(result["model"]["combinations"], key=lambda c: c["total_cost"]):
        label = _plans(c["plans"])
        rows.append({
            "Planes": label,
            "Óptimo": "★" if abs(c["total_cost"] - classical["optimal_cost"]) < 1e-9 else "",
            "Costo real": c["total_cost"], "Costo QUBO (pares)": c["approx_cost"],
            "Demora media s": c["metrics"]["mean_delay_s"], "Cola máx": c["metrics"]["peak_queue"],
            "Residual": c["metrics"]["residual"],
            **{f"Bloqueo {k} s": v for k, v in c["blocked_s"].items()},
            **({"P(QAOA)": probs.get(label, 0.0)} if probs else {}),
        })
    st.markdown("**Enumeración exhaustiva**: se simulan todas las combinaciones y se toma la más barata. "
                "Es la referencia exacta contra la que se mide todo lo demás.")
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                 column_config={
                     "Costo real": st.column_config.NumberColumn(format="%.3f"),
                     "Costo QUBO (pares)": st.column_config.NumberColumn(format="%.3f"),
                     "Demora media s": st.column_config.NumberColumn(format="%.1f"),
                     "P(QAOA)": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
                 })
    st.caption("Bloqueo = segundos con verde EW, cola y tramo siguiente lleno (spillback); se reporta, no entra al "
               "costo. Demora media es por llegada a colas, no tiempo de viaje por vehículo único.")
    st.markdown("**Programación dinámica por pares**: minimiza la suma de costos locales y de pares vecinos "
                "(el mismo modelo que recibe QAOA) en O(N·K²).")
    st.write(f"Plan: {_plans(pairwise['optimal_plans'])} · costo del modelo por pares "
             f"{pairwise['optimal_approx_cost']:.3f} · costo real {pairwise['original_cost']:.3f} · "
             f"pérdida {pairwise['original_regret']:.3f}")
    if audit["exact_representation"]:
        st.success("Con 2 cruces el modelo por pares reproduce exactamente el costo del simulador.")
    else:
        st.warning(f"Con {len(ids)} cruces el modelo por pares es una aproximación: error máximo "
                   f"{audit['max_absolute_error']:.3f}. Su mejor plan cuesta "
                   f"{100 * audit['decision_regret'] / classical['optimal_cost']:.2f} % más que el óptimo real, "
                   "aunque se resuelva perfectamente.")


def _render_quantum(result: dict, ids: list[str]) -> None:
    q, audit = result["quantum"], result["audit"]
    if not q:
        st.info("QAOA no se ejecutó en esta configuración. Actívalo en la barra lateral y vuelve a ejecutar.")
        return
    proof = audit["one_hot"]
    n_states = len(result["model"]["combinations"])
    st.markdown(f"**QAOA p={q['depth']}** sobre {2 * len(ids)} qubits ({2 ** (2 * len(ids))} estados, "
                f"{n_states} válidos). Optimizador {q['optimizer']}, {q['restarts']} reinicios, hasta "
                f"{q['max_evaluations_per_restart']} evaluaciones por reinicio, semilla {q['seed']}. "
                f"Penalización P = {proof['penalty']:.3f}. Probabilidades exactas de vector de estado, sin shots ni "
                "hardware.")
    best = result["classical"]["optimal_cost"]
    ordered = sorted(q["valid_probabilities"], key=lambda r: r["original_cost"])
    # Con más de 2 cruces se usa el código corto de planes (A…E en orden) para que las etiquetas quepan.
    label = _plans if len(ids) == 2 else (lambda plans: "".join(str(v) for v in plans.values()))
    order = [label(r["plans"]) for r in ordered] + ["inválidos"]
    rows = [{"Planes": label(r["plans"]), "Fuente": f, "Probabilidad": v}
            for r in ordered for f, v in (("QAOA", r["probability"]), ("Azar", 1 / n_states))]
    rows.append({"Planes": "inválidos", "Fuente": "QAOA", "Probabilidad": q["invalid_probability"]})
    chart = alt.Chart(pd.DataFrame(rows)).mark_bar(cornerRadiusEnd=2).encode(
        x=alt.X("Planes:N", sort=order, title=None, axis=alt.Axis(labelAngle=-90 if len(order) > 6 else 0, labelOverlap=False)),
        xOffset=alt.XOffset("Fuente:N", sort=["QAOA", "Azar"]),
        y=alt.Y("Probabilidad:Q", axis=alt.Axis(format="%")),
        color=alt.Color("Fuente:N", sort=["QAOA", "Azar"],
                        scale=alt.Scale(domain=["QAOA", "Azar"], range=["#3DBE80", "#6B7682"]),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["Planes", "Fuente", alt.Tooltip("Probabilidad:Q", format=".2%")],
    )
    st.altair_chart(chart.properties(height=320), width="stretch")
    code = "" if len(ids) == 2 else f" Código de planes en orden {', '.join(ids)}: 11100 = " + ", ".join(
        f"{i}={v}" for i, v in zip(ids, "11100")) + "."
    st.caption(f"Planes ordenados de menor a mayor costo real: el primero es el óptimo ({best:.3f}).{code} "
               "QAOA mejora al azar si su barra verde supera a la gris en el óptimo.")
    st.dataframe(pd.DataFrame([{
        "Soluciones válidas": q["feasible_probability"], "P(óptimo)": q["original_optimal_probability"],
        "P(óptimo) al azar": 1 / n_states,
        "Costo esperado (válidas)": q["conditional_expected_original"],
        "Brecha esperada": q["conditional_original_gap"],
        "Plan más probable": _plans(q["representative_plans"]),
    }]), hide_index=True, width="stretch", column_config={
        "Soluciones válidas": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
        "P(óptimo)": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
        "P(óptimo) al azar": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
        "Costo esperado (válidas)": st.column_config.NumberColumn(format="%.3f"),
        "Brecha esperada": st.column_config.NumberColumn(format="%+.3f"),
    })
    with st.expander("Circuito y ángulos"):
        st.code(q["circuit_text"], language="text")
        st.json({"ángulos γ, β": q["angles_gamma_beta"], "bits": result["bit_order"],
                 "tiempo QAOA ms": q["runtime_ms"]})


def _render_variables(result: dict, params: dict, ids: list[str]) -> None:
    local, pair_costs, qubo = result["model"]["local_costs"], result["model"]["pair_costs"], result["qubo"]
    proof = result["audit"]["one_hot"]
    st.markdown("**Variables de decisión**: una variable binaria por cruce y plan; x = 1 si ese cruce usa ese "
                "plan. Cada variable es un qubit.")
    rows = []
    for i, cid in enumerate(ids):
        for k in (0, 1):
            q_index = 2 * i + k
            rows.append({"Variable": f"x_{cid}{k}", "Qubit": q_index, "Cruce": cid,
                         "Plan": f"{k} · NS/EW {PLAN_LABEL[k]} s", "Costo local L": local[cid][k],
                         "Coeficiente lineal QUBO": qubo["linear"][q_index]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config={
        "Costo local L": st.column_config.NumberColumn(format="%.3f"),
        "Coeficiente lineal QUBO": st.column_config.NumberColumn(format="%.3f"),
    })
    st.markdown("**Costos de pares vecinos V**: costo extra por la interacción entre dos cruces consecutivos "
                "(filas: plan del primero; columnas: plan del segundo).")
    cols = st.columns(min(len(pair_costs), 4))
    for idx, (link, matrix) in enumerate(pair_costs.items()):
        a, b = link.split("-")
        with cols[idx % len(cols)]:
            st.caption(link)
            st.dataframe(pd.DataFrame(matrix, index=[f"{a}={k}" for k in (0, 1)],
                                      columns=[f"{b}={k}" for k in (0, 1)]).round(3), width="stretch")
    st.markdown("**Función objetivo**")
    st.latex(r"Q(x) = \sum_{i,k} L_i(k)\,x_{i,k} + \sum_{i,k,l} V_{i,i+1}(k,l)\,x_{i,k}\,x_{i+1,l}"
             r" + P \sum_i (x_{i,0} + x_{i,1} - 1)^2")
    st.write(f"P = {proof['penalty']:.3f} > U − L = {proof['feasible_upper_bound'] - proof['unpenalized_lower_bound']:.3f}"
             f" (U = {proof['feasible_upper_bound']:.3f}, L = {proof['unpenalized_lower_bound']:.3f}). Así ningún "
             "estado inválido puede ser el mínimo.")
    st.markdown("**Costo del simulador por cruce**")
    st.latex(r"C_i = w_D\,\frac{D_i}{60} + w_P\,\frac{Q^{max}_i}{30} + w_R\,\frac{R_i}{30}, \qquad C = \sum_i C_i")
    w = params["weights"]
    st.dataframe(pd.DataFrame([
        {"Parámetro": "Horizonte", "Valor": f"{params['horizon_s']} s"},
        {"Parámetro": "Ciclo / despeje", "Valor": f"{params['cycle_s']} s / {params['all_red_s']} s ×2"},
        {"Parámetro": "Descarga en verde", "Valor": f"{params['service_rate_vps']} veh/s"},
        {"Parámetro": "Viaje entre cruces", "Valor": f"{params['travel_time_s']} s"},
        {"Parámetro": "Capacidad por tramo EW (K)", "Valor": f"{params['storage_vehicles']} veh"},
        {"Parámetro": "Pesos wD / wP / wR", "Valor": f"{w['delay']} / {w['peak_queue']} / {w['residual']}"},
        *({"Parámetro": f"Llegadas {it['id']} NS / EW",
           "Valor": f"{it['arrival_rate_vpm']['NS']:g} / {it['arrival_rate_vpm']['EW']:g} veh/min"}
          for it in params["intersections"]),
    ]), hide_index=True, width="stretch")


def _render_evolution(result: dict, params: dict, n: int) -> None:
    label = st.selectbox("Planes para inspeccionar", list(result["histories"]))
    selected = result["histories"][label]
    render_animation(selected, params)
    history = selected["history"]
    instant = st.slider("Instante · segundos", 0, len(history) - 1, 0)
    snapshot = history[instant]
    columns = st.columns(n)
    for i, col in enumerate(columns):
        with col:
            st.markdown(f"**Cruce {params['intersections'][i]['id']}**")
            st.caption(f"Plan {list(selected['plans'].values())[i]} · fase {snapshot['phases'][i]}")
            st.write(f"Cola NS: {snapshot['queues'][i]['NS']}")
            st.write(f"Cola EW: {snapshot['queues'][i]['EW']}")
    series = {f"{params['intersections'][i]['id']} {a}": [h["queues"][i][a] for h in history]
              for i in range(n) for a in ("NS", "EW")}
    st.line_chart(pd.DataFrame(series))
    st.write("Conteo final de red:", selected["network"])


def render():
    st.title("🚦Simaphuru")
    st.write("Cruces NS/EW conectados por EW, QUBO one-hot y QAOA en Qiskit.")
    st.info("Parámetros ilustrativos, no calibrados. Cada tramo EW guarda como máximo K autos: si el tramo "
            "siguiente está lleno, el cruce no despacha aunque tenga verde (spillback). No simula paradas de bus.")
    n = st.sidebar.selectbox("Cruces conectados", [2, 5])
    params = default_team_params(n)
    with_qaoa = st.sidebar.checkbox("Ejecutar QAOA en Qiskit local", value=True)
    seed = int(st.sidebar.number_input("Semilla del optimizador", min_value=0, value=7, step=1))
    depth = st.sidebar.selectbox("Capas QAOA", [1, 2, 3], index=2)
    params["travel_time_s"] = st.sidebar.slider("Viaje entre cruces · s", 1, 90, params["travel_time_s"])
    params["storage_vehicles"] = st.sidebar.slider("Capacidad de cada tramo EW (K) · veh", 1, 40,
                                                   params["storage_vehicles"])
    with st.sidebar.expander("Llegadas externas por cruce · veh/min"):
        for inter in params["intersections"]:
            for axis in ("NS", "EW"):
                inter["arrival_rate_vpm"][axis] = st.number_input(
                    f"{inter['id']} · {axis}", min_value=0.0, max_value=60.0,
                    value=float(inter["arrival_rate_vpm"][axis]), step=1.0,
                )
    with st.sidebar.expander("Pesos del costo"):
        for key, label in (("delay", "Demora"), ("peak_queue", "Cola máxima"), ("residual", "Residual")):
            params["weights"][key] = st.number_input(
                label, min_value=0.0, max_value=10.0, value=params["weights"][key], step=0.1
            )
    fingerprint = (team_fingerprint(params), with_qaoa, depth, seed)
    st.caption("Plan 0: NS/EW 30/30 s · Plan 1: NS/EW 40/20 s · ciclo 68 s · dos despejes de 4 s.")
    st.caption("Llegadas uniformes deterministas. La semilla cambia el entrenamiento QAOA, no el tráfico.")
    if st.button("Ejecutar experimento", type="primary"):
        with st.spinner("Simulando el corredor del equipo y comprobando la formulación…"):
            st.session_state["team_experiment"] = run_team_experiment(
                params, qaoa=with_qaoa, depth=depth, seed=seed
            )
            st.session_state["team_fingerprint"] = fingerprint
    current = st.session_state.get("team_experiment") if st.session_state.get("team_fingerprint") == fingerprint else None
    with st.expander("🧭 ¿Cómo funciona? Paso a paso", expanded=current is None):
        render_explainer(params, current)
    if current is None:
        st.write("Ejecuta el experimento para obtener resultados de esta configuración.")
        return
    result = current
    ids = [it["id"] for it in params["intersections"]]
    classical, q = result["classical"], result["quantum"]

    st.header("Resultados")
    left, middle, right = st.columns(3)
    left.metric("Óptimo exacto · clásico", f"{classical['optimal_cost']:.3f}",
                help=f"{_plans(classical['optimal_plans'])}. Base (todos plan 0): {classical['baseline_cost']:.3f}")
    if q:
        gap = q["representative_original_cost"] - classical["optimal_cost"]
        exact = abs(gap) < 1e-9
        middle.metric("Plan más probable · QAOA", f"{q['representative_original_cost']:.3f}",
                      delta="igual al óptimo" if exact else f"{gap:+.3f} vs óptimo",
                      delta_color="off" if exact else "inverse",
                      delta_arrow="off" if exact else "auto",
                      help=_plans(q["representative_plans"]))
        n_states = len(result["model"]["combinations"])
        right.metric("P(óptimo) · QAOA", f"{100 * q['original_optimal_probability']:.1f} %",
                     delta=f"{100 * (q['original_optimal_probability'] - 1 / n_states):+.1f} pp vs azar",
                     help=f"Al azar: {100 / n_states:.1f} %. Soluciones válidas: "
                          f"{100 * q['feasible_probability']:.1f} %")
    else:
        middle.metric("Plan más probable · QAOA", "sin ejecutar")
        right.metric("P(óptimo) · QAOA", "sin ejecutar")

    tabs = st.tabs(["Comparación", "Clásico", "Cuántico (QAOA)", "Variables y costos", "Evolución del tráfico"])
    with tabs[0]:
        _render_comparison(result)
    with tabs[1]:
        _render_classical(result, ids)
    with tabs[2]:
        _render_quantum(result, ids)
    with tabs[3]:
        _render_variables(result, params, ids)
    with tabs[4]:
        _render_evolution(result, params, n)

    st.download_button("Descargar experimento JSON", json.dumps(result, indent=2, ensure_ascii=False),
                       file_name="simaphuru-team-result.json", mime="application/json")
    with st.expander("Contrato, parámetros y procedencia"):
        st.json({k: result[k] for k in ("schema_version", "model_version", "upstream_commit",
                                       "config_hash", "inputs", "versions", "claims")})
