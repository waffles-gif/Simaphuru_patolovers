"""Interfaz sobre el motor existente del equipo. No redefine sus ecuaciones."""

import json

import altair as alt
import pandas as pd
import streamlit as st

from simaphuru.team import default_team_params, run_team_experiment, team_fingerprint
from web.animation import render_animation
from web.explainer import render_explainer

PLAN_LABEL = {0: "30/30", 1: "40/20"}
ENCODING_LABEL = {"one_hot": "Dos qubits por cruce · one-hot",
                  "binary": "Un qubit por cruce · binaria"}


def _plans(plans: dict) -> str:
    """{'A': 1, 'B': 0} -> 'A=1 · B=0'."""
    return " · ".join(f"{k}={v}" for k, v in plans.items())


def _gap_percent(cost: float, best: float) -> float | None:
    """El porcentaje no está definido si el óptimo es cero y existe una brecha."""
    if abs(cost - best) < 1e-9:
        return 0.0
    return 100 * (cost - best) / best if abs(best) > 1e-12 else None


def _uniform_optimal_probability(result: dict) -> float:
    combos = result["model"]["combinations"]
    best = result["classical"]["optimal_cost"]
    return sum(abs(c["total_cost"] - best) < 1e-9 for c in combos) / len(combos)


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
                "Brecha vs óptimo": cost - best, "Brecha %": _gap_percent(cost, best),
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
                q["representative_original_cost"], None,
                None, f"{q['evaluations']} evaluaciones del circuito, {result['encoding']['qubits']} qubits",
                q["runtime_ms"]),
            row(f"QAOA p={q['depth']} · distribución válida", "Cuántico", "esperanza condicionada",
                q["conditional_expected_original"], q["original_optimal_probability"],
                q["feasible_probability"], "costo esperado entre soluciones válidas", None),
        ]
    if result.get("hybrid"):
        labels = {"qaoa_candidates": ("Híbrido · QAOA + verificación", "Híbrido"),
                  "uniform_candidates": ("Búsqueda clásica · candidatos uniformes", "Clásico heurístico"),
                  "local_search": ("Búsqueda clásica · vecinos", "Clásico heurístico")}
        for key, method in result["hybrid"]["methods"].items():
            label, kind = labels[key]
            rows.append(row(label, kind, _plans(method["selected_plans"]), method["selected_cost"],
                            None, 1.0, f"{method['simulator_evaluations']} simulaciones nuevas "
                            f"(incluye inicial); {method['proposal_attempts']} propuestas",
                            method["runtime_ms"]))
    rows += [
        row("Al azar", "Referencia", "uniforme", classical["uniform_feasible_expected_cost"],
            n_opt / n_states, 1.0, "ninguno", None),
        row("Programa base", "Referencia", _plans({i: 0 for i in ids}), classical["baseline_cost"],
            float(abs(classical["baseline_cost"] - best) < 1e-9), 1.0, "1 simulación", None),
    ]
    return rows


TYPE_COLORS = {"Clásico exacto": "#5B9BE6", "Clásico aproximado": "#8DB9EE",
               "Cuántico": "#3DBE80", "Híbrido": "#D6B35A",
               "Clásico heurístico": "#A79BDD", "Referencia": "#6B7682"}


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
               "que el óptimo exacto. P(óptimo) se refiere a un muestreo del circuito, no a seleccionar su moda. "
               "La fila de distribución descarta estados inválidos para calcular el costo esperado; su P(óptimo) "
               "no está condicionada. Si el costo óptimo es cero, una brecha porcentual no definida se deja vacía.")
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
    st.caption(f"Preparación compartida de factores locales/pares: {result['factor_generation_ms']:.1f} ms. "
               "Los tiempos de búsqueda de QAOA y programación dinámica excluyen esa preparación. La enumeración "
               "evalúa el simulador completo y sirve para auditar; no es necesaria para construir esos factores. "
               "Son etapas distintas, no una prueba de aceleración. QAOA usa simulación ideal local.")


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
        st.success("En esta configuración, el modelo por pares reproduce el costo del simulador.")
    else:
        st.warning(f"Con {len(ids)} cruces el modelo por pares es una aproximación: error máximo "
                   f"{audit['max_absolute_error']:.3f}. Su mejor plan cuesta "
                   f"{audit['decision_regret']:.3f} unidades más que el óptimo real, "
                   "aunque se resuelva perfectamente.")


def _render_quantum(result: dict, ids: list[str]) -> None:
    q, audit = result["quantum"], result["audit"]
    if not q:
        st.info("QAOA no se ejecutó en esta configuración. Actívalo en la barra lateral y vuelve a ejecutar.")
        return
    proof, encoding = audit["encoding"], result["encoding"]
    n_states = len(result["model"]["combinations"])
    constraint = (f"Penalización P = {proof['penalty']:.3f}. " if encoding["name"] == "one_hot"
                  else "Todos los estados eligen un programa por cruce; sin penalización one-hot. ")
    st.markdown(f"**QAOA p={q['depth']}** sobre {encoding['qubits']} qubits ({encoding['states']} estados, "
                f"{n_states} válidos). Optimizador {q['optimizer']}, {q['restarts']} reinicios, hasta "
                f"{q['max_evaluations_per_restart']} evaluaciones por reinicio, semilla {q['seed']}. "
                f"{constraint}Probabilidades exactas de vector de estado, sin shots ni "
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
    example_code = "".join("1" if i < 3 else "0" for i in range(len(ids)))
    code = "" if len(ids) == 2 else f" Código de planes en orden {', '.join(ids)}: {example_code} = " + ", ".join(
        f"{i}={v}" for i, v in zip(ids, example_code)) + "."
    st.caption(f"Planes ordenados de menor a mayor costo real: el primero es el óptimo ({best:.3f}).{code} "
               "La calidad media, la probabilidad total de óptimo y el costo del plan más probable son métricas distintas.")
    st.dataframe(pd.DataFrame([{
        "Soluciones válidas": q["feasible_probability"], "P(óptimo)": q["original_optimal_probability"],
        "P(óptimo) al azar": _uniform_optimal_probability(result),
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
    proof = result["audit"]["encoding"]
    binary = result["encoding"]["name"] == "binary"
    st.markdown("**Variables de decisión**: " + (
        "un bit por cruce: y=0 elige 30/30 s; y=1 elige 40/20 s. Todos los estados eligen un programa."
        if binary else "una variable por cruce y plan; x=1 activa ese programa. Se exige exactamente uno por cruce."))
    rows = []
    for i, cid in enumerate(ids):
        if binary:
            rows.append({"Variable": f"y_{cid}", "Qubit": i, "Cruce": cid,
                         "Plan": "0 → 30/30; 1 → 40/20",
                         "L(0)": local[cid][0], "L(1)": local[cid][1],
                         "Coeficiente lineal QUBO": qubo["linear"][i]})
            continue
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
    if binary:
        st.latex(r"x_{i,0}=1-y_i,\quad x_{i,1}=y_i,\qquad Q(y)=c+\sum_i a_i y_i+\sum_i b_i y_i y_{i+1}")
        st.write("La sustitución conserva exactamente el objetivo por pares; no elimina su posible error físico. "
                 f"Error algebraico máximo auditado: {proof['feasible_identity_max_error']:.2e}.")
    else:
        st.latex(r"Q(x) = \sum_{i,k} L_i(k)\,x_{i,k} + \sum_{i,k,l} V_{i,i+1}(k,l)\,x_{i,k}\,x_{i+1,l}"
                 r" + P \sum_i (x_{i,0} + x_{i,1} - 1)^2")
        st.write(f"P = {proof['penalty']:.3f} > U − L = {proof['feasible_upper_bound'] - proof['unpenalized_lower_bound']:.3f}"
                 f" (U = {proof['feasible_upper_bound']:.3f}, L = {proof['unpenalized_lower_bound']:.3f}). Así ningún "
                 "estado inválido puede ser el mínimo global; QAOA aún puede producir estados inválidos.")
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


def _render_hybrid(result: dict) -> None:
    hybrid = result.get("hybrid")
    if not hybrid:
        st.info("Activa «Comparar búsqueda híbrida» en la barra lateral y vuelve a ejecutar.")
        return
    st.markdown("**El clásico propone un inicio; QAOA propone alternativas; el simulador completo decide.** "
                "Se conserva siempre el programa inicial si ningún candidato reduce su costo físico.")
    budget = hybrid["budget"]
    st.write(f"Mismos límites por método: hasta {budget['proposals']} propuestas y "
             f"{budget['max_simulator_evaluations']} simulaciones del corredor, incluida la inicial. "
             f"Semilla de muestreo {hybrid['sampling_seed']}.")
    labels = {"qaoa_candidates": "Híbrido · candidatos QAOA",
              "uniform_candidates": "Clásico · candidatos uniformes",
              "local_search": "Clásico · búsqueda local de uno/dos bits"}
    methods = hybrid["methods"]
    initial = methods["qaoa_candidates"]
    st.write(f"Inicio común por programación dinámica de pares: {_plans(initial['initial_plans'])}. "
             f"Costo verificado: {initial['initial_cost']:.4f}. "
             f"Óptimo exhaustivo de referencia: {result['classical']['optimal_cost']:.4f}.")
    st.dataframe(pd.DataFrame([{
        "Método": labels[key], "Programa seleccionado": _plans(method["selected_plans"]),
        "Costo físico": method["selected_cost"], "Mejora desde inicio": method["improvement"],
        "Brecha al óptimo": method["gap_to_exact"],
        "Simulaciones físicas": method["simulator_evaluations"],
        "Propuestas": method["proposal_attempts"], "Duplicadas": method["duplicates"],
        "Inválidas": method["invalid_samples"], "Sin evaluar por límite": method["not_evaluated_budget"],
        "Evaluación física y propuestas · ms": method["runtime_ms"],
    } for key, method in methods.items()]), hide_index=True, width="stretch")
    st.caption("QAOA se muestrea desde sus probabilidades ideales usando el generador clásico: no son shots "
               "de hardware. Los duplicados e inválidos consumen propuestas; no otra simulación física. "
               "La búsqueda local puede terminar antes de consumir todas las propuestas. Se informan límites "
               "iguales y trabajo real, no igualdad de tiempo total.")
    st.write(f"Trabajo previo adicional de QAOA: entrenamiento {hybrid['quantum_training_ms']:.1f} ms. "
             f"Preparación compartida de factores: {hybrid['factor_generation_ms']:.1f} ms; "
             f"búsqueda de la semilla clásica: {hybrid['classical_seed_search_ms']:.3f} ms.")
    st.caption("El selector no recibe la tabla exhaustiva: esta sirve solo para medir la brecha. "
               "La aplicación completa todavía la calcula para auditoría; no es una prueba de escalabilidad. "
               "Esta variante no implementa warm-start del estado cuántico. Una mejora del costo compuesto "
               "no garantiza mejorar cada indicador físico.")
    with st.expander("Trazabilidad de los candidatos"):
        for key, method in methods.items():
            st.markdown(f"**{labels[key]}**")
            st.dataframe(pd.DataFrame(method["trace"]), hide_index=True, width="stretch")


def _render_evolution(result: dict, params: dict, n: int) -> None:
    label = st.selectbox("Planes para inspeccionar", list(result["histories"]))
    selected = result["histories"][label]
    st.caption("Un único reloj controla semáforos, vehículos y tarjetas. Moverlo pausa la reproducción; "
               "al cambiar de programa, el reproductor comienza en el primer paso.")
    render_animation(selected, params)
    history = selected["history"]
    series = {f"{params['intersections'][i]['id']} {a}": [h["queues"][i][a] for h in history]
              for i in range(n) for a in ("NS", "EW")}
    with st.expander("Historial completo de colas"):
        st.line_chart(pd.DataFrame(series))
    st.write("Conteo al final del horizonte:", selected["network"])


def render():
    st.title("🚦Simaphuru")
    st.write("Cruces conectados, dos codificaciones del mismo problema y QAOA en Qiskit.")
    st.info("Parámetros ilustrativos, no calibrados. Cada tramo EW guarda como máximo K autos: si el tramo "
            "siguiente está lleno, el cruce no despacha aunque tenga verde (spillback). No simula paradas de bus.")
    n = st.sidebar.selectbox("Cruces conectados", [2, 3, 4, 5])
    params = default_team_params(n)
    with_qaoa = st.sidebar.checkbox("Ejecutar QAOA en Qiskit local", value=True)
    seed = int(st.sidebar.number_input("Semilla del optimizador", min_value=0, value=7, step=1))
    depth = st.sidebar.selectbox("Capas QAOA", [1, 2, 3], index=2)
    encoding = st.sidebar.selectbox("Representación de programas", list(ENCODING_LABEL),
                                    index=list(ENCODING_LABEL).index("binary"),
                                    format_func=ENCODING_LABEL.get)
    with_hybrid = st.sidebar.checkbox("Comparar búsqueda híbrida", value=False, disabled=not with_qaoa)
    with st.sidebar.expander("Presupuesto de candidatos"):
        candidate_proposals = int(st.number_input("Máximo de propuestas", min_value=1, max_value=256,
                                                  value=32, step=1))
        max_simulations = int(st.number_input("Máximo de simulaciones por método", min_value=1, max_value=32,
                                              value=8, step=1))
        sampling_seed = int(st.number_input("Semilla del muestreo", min_value=0, value=2026, step=1))
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
    do_hybrid = with_hybrid and with_qaoa
    fingerprint = (team_fingerprint(params), with_qaoa, depth, seed, encoding, do_hybrid,
                   candidate_proposals, max_simulations, sampling_seed)
    st.caption("Plan 0: NS/EW 30/30 s · Plan 1: NS/EW 40/20 s · ciclo 68 s · dos despejes de 4 s.")
    st.caption("Llegadas uniformes deterministas. La semilla cambia el entrenamiento QAOA, no el tráfico.")
    if st.button("Ejecutar experimento", type="primary"):
        with st.spinner("Simulando el corredor del equipo y comprobando la formulación…"):
            st.session_state["team_experiment"] = run_team_experiment(
                params, qaoa=with_qaoa, depth=depth, seed=seed, encoding=encoding,
                hybrid=do_hybrid, candidate_proposals=candidate_proposals,
                max_candidate_simulations=max_simulations, sampling_seed=sampling_seed
            )
            st.session_state["team_fingerprint"] = fingerprint
    current = st.session_state.get("team_experiment") if st.session_state.get("team_fingerprint") == fingerprint else None
    with st.expander("🧭 ¿Cómo funciona? Paso a paso", expanded=current is None):
        render_explainer(params, current, encoding=encoding)
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
        uniform_optimal = _uniform_optimal_probability(result)
        delta_pp = 100 * (q["original_optimal_probability"] - uniform_optimal)
        if abs(delta_pp) < 0.05:
            delta_pp = 0.0  # Evitar presentar redondeo numérico como una pérdida de -0.0 pp.
        right.metric("P(óptimo) · QAOA", f"{100 * q['original_optimal_probability']:.1f} %",
                     delta=f"{delta_pp:+.1f} pp vs azar",
                     help=f"Al azar: {100 * uniform_optimal:.1f} %. Soluciones válidas: "
                          f"{100 * q['feasible_probability']:.1f} %")
    else:
        middle.metric("Plan más probable · QAOA", "sin ejecutar")
        right.metric("P(óptimo) · QAOA", "sin ejecutar")

    tabs = st.tabs(["Comparación", "Clásico", "Cuántico (QAOA)", "Híbrido verificado",
                    "Variables y costos", "Evolución del tráfico"])
    with tabs[0]:
        _render_comparison(result)
    with tabs[1]:
        _render_classical(result, ids)
    with tabs[2]:
        _render_quantum(result, ids)
    with tabs[3]:
        _render_hybrid(result)
    with tabs[4]:
        _render_variables(result, params, ids)
    with tabs[5]:
        _render_evolution(result, params, n)

    st.download_button("Descargar experimento JSON", json.dumps(result, indent=2, ensure_ascii=False),
                       file_name="simaphuru-team-result.json", mime="application/json")
    with st.expander("Contrato, parámetros y procedencia"):
        st.json({k: result[k] for k in ("schema_version", "model_version", "upstream_commit",
                                       "config_hash", "experiment_id", "encoding", "execution",
                                       "inputs", "versions", "claims")})
