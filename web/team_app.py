"""Interfaz sobre el motor existente del equipo. No redefine sus ecuaciones."""

import json

import pandas as pd
import streamlit as st

from simaphuru.team import default_team_params, run_team_experiment, team_fingerprint


def render():
    st.title("🚦 Simaphuru · Motor del equipo")
    st.write("Cruces NS/EW conectados por EW, QUBO one-hot y QAOA en Qiskit.")
    st.info("Parámetros ilustrativos. Este motor aún usa colas sin límite; no simula spillback ni paradas de bus.")
    n = st.sidebar.selectbox("Cruces conectados", [2, 5])
    params = default_team_params(n)
    with_qaoa = st.sidebar.checkbox("Ejecutar QAOA en Qiskit local", value=True)
    seed = int(st.sidebar.number_input("Semilla del optimizador", min_value=0, value=7, step=1))
    depth = st.sidebar.selectbox("Capas QAOA", [1, 2])
    params["travel_time_s"] = st.sidebar.slider("Viaje entre cruces · s", 1, 90, 25)
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
    if st.session_state.get("team_fingerprint") != fingerprint:
        st.write("Ejecuta el experimento para obtener resultados de esta configuración.")
        return
    result = st.session_state["team_experiment"]
    classical, audit = result["classical"], result["audit"]
    left, middle, right = st.columns(3)
    left.metric("Costo del programa base", f"{classical['baseline_cost']:.4f}")
    middle.metric("Mínimo exacto del simulador", f"{classical['optimal_cost']:.4f}")
    right.metric("Error máximo locales + pares", f"{audit['max_absolute_error']:.4f}")
    st.caption("Costo por cruce: wD·D/60 + wP·Qmax/30 + wR·R/30. Total: suma por cruces.")
    if not audit["exact_representation"]:
        st.warning("Con cinco cruces, locales y pares vecinos aproximan el costo físico. Se informa su error y pérdida de decisión.")
    rows = []
    for c in result["model"]["combinations"]:
        rows.append({"planes": str(c["plans"]), "costo_simulador": c["total_cost"],
                     "costo_pares": c["approx_cost"], **c["metrics"], **c["network"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.write("Óptimo físico:", classical["optimal_plans"])
    st.write("Referencia clásica por pares (programación dinámica):", result["pairwise_classical"])
    st.write("Referencia uniforme entre planes factibles:", {
        "costo esperado": classical["uniform_feasible_expected_cost"],
        "probabilidad factible": 1.0,
        "probabilidad de óptimo físico": sum(
            abs(c["total_cost"] - classical["optimal_cost"]) < 1e-9
            for c in result["model"]["combinations"]
        ) / len(result["model"]["combinations"]),
    })
    st.caption("mean_delay_s es demora por llegada a colas (visitas); no es tiempo de viaje por vehículo único. Los pendientes de red incluyen vehículos en tránsito.")
    if result["quantum"]:
        q = result["quantum"]
        st.subheader("Qiskit · distribución one-hot")
        st.write({"qubits": 2 * n, "Probabilidad factible": q["feasible_probability"],
                  "Probabilidad del óptimo físico (sin condicionar)": q["original_optimal_probability"],
                  "Costo real esperado condicionado a factibilidad": q["conditional_expected_original"],
                  "Brecha real condicionada": q["conditional_original_gap"]})
        probabilities = {str(row["plans"]): row["probability"] for row in q["valid_probabilities"]}
        probabilities["ESTADOS INVÁLIDOS (total)"] = q["invalid_probability"]
        st.bar_chart(pd.DataFrame({"probabilidad": probabilities}))
        st.write("Representante factible de mayor probabilidad:", q["representative_plans"])
        st.caption("Se muestra toda la masa inválida. La esperanza condicionada descarta fallos y debe leerse junto a la probabilidad factible.")
        with st.expander("Circuito, penalización y tiempos"):
            st.code(q["circuit_text"], language="text")
            st.json({"penalización": audit["one_hot"], "bits": result["bit_order"],
                     "tiempo_QAOA_ms": q["runtime_ms"], "tiempo_enumeración_ms": classical["runtime_ms"]})
    st.subheader("Evolución del mismo experimento")
    label = st.selectbox("Planes para inspeccionar", list(result["histories"]))
    selected = result["histories"][label]
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
    st.download_button("Descargar experimento JSON", json.dumps(result, indent=2, ensure_ascii=False),
                       file_name="simaphuru-team-result.json", mime="application/json")
    with st.expander("Contrato, parámetros y procedencia"):
        st.json({k: result[k] for k in ("schema_version", "model_version", "upstream_commit",
                                       "config_hash", "inputs", "versions", "claims")})
