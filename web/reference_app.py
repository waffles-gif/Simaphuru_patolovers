"""Interfaz inicial. Toda la lógica científica vive en simaphuru."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from simaphuru.experiment import run_experiment
from simaphuru.models import decision_label, load_scenario


def render():
    st.title("🚦Simaphuru")
    st.write("Tráfico conectado, referencia clásica y QAOA con Qiskit.")
    st.info("Escenarios sintéticos de referencia: todavía no son una calibración de Javier Prado.")
    folder = Path(__file__).resolve().parents[1] / "data" / "scenarios"
    scenario_names = sorted(
        (p.name for p in folder.glob("*.json")), key=lambda name: (not name.startswith("two"), name)
    )
    scenario_name = st.sidebar.selectbox("Escenario", scenario_names)
    scenario = load_scenario(folder / scenario_name)
    seed = int(st.sidebar.number_input("Semilla", min_value=0, value=7, step=1))
    with_qaoa = st.sidebar.checkbox("Ejecutar QAOA en Qiskit local", value=True)
    depth = st.sidebar.selectbox("Capas QAOA", [1, 2])
    main_rate = st.sidebar.slider(
        "Llegadas principales · veh/min", 0.0, 30.0, float(scenario.main_veh_min), 1.0
    )
    side_rate = st.sidebar.slider(
        "Llegadas por transversal · veh/min", 0.0, 20.0, float(scenario.side_veh_min), 1.0
    )
    include_blockage = st.sidebar.checkbox("Incluir bloqueo temporal", value=True)
    scenario = scenario.model_copy(
        update={
            "main_veh_min": main_rate,
            "side_veh_min": side_rate,
            "blockages": scenario.blockages if include_blockage else (),
        }
    )
    st.sidebar.caption("No requiere credenciales IBM. Probabilidades exactas, sin hardware.")
    fingerprint = (scenario.fingerprint(seed), with_qaoa, depth)
    st.write(" → ".join(f"Cruce {i + 1}" for i in range(scenario.junctions)))
    st.caption(scenario.provenance)
    if st.button("Ejecutar experimento", type="primary"):
        with st.spinner("Evaluando las mismas llegadas para todas las decisiones…"):
            st.session_state["experiment"] = run_experiment(
                scenario, seed=seed, qaoa=with_qaoa, depth=depth
            )
            st.session_state["fingerprint"] = fingerprint
    if st.session_state.get("fingerprint") != fingerprint:
        st.write("Ejecuta el experimento para obtener resultados de esta configuración.")
        st.stop()
    result = st.session_state["experiment"]
    left, center, right = st.columns(3)
    left.metric("Costo del programa base", f"{result['baseline_cost']:.4f}")
    center.metric("Mínimo exacto del simulador", f"{result['exact_minimum']:.4f}")
    right.metric("Error máximo QUBO", f"{result['audit']['max_absolute_error']:.4f}")
    st.caption("Costo = tiempo total acumulado / (60 × demanda) + fracción pendiente.")
    if not result["audit"]["exact_representation"]:
        st.warning(
            "El QUBO es aproximado. Su energía y el costo real del tráfico se evalúan por separado."
        )
    table = pd.DataFrame(result["evaluations"])[
        ["index", "decision_id", "cost", "arrivals", "exited", "residual"]
    ]
    table["costo_qubo"] = result["audit"]["qubo_costs"]
    st.dataframe(table, hide_index=True, width="stretch")
    if result["qaoa"]:
        quantum = result["qaoa"]
        st.subheader("Resultado Qiskit")
        st.write(
            {
                "Esperanza del QUBO": quantum["expected_qubo"],
                "Esperanza del costo real": quantum["expected_original"],
                "Brecha real": quantum["original_gap"],
                "Probabilidad de óptimo real": quantum["original_optimal_probability"],
            }
        )
        probability_table = pd.DataFrame(
            {
                "decisión": [
                    decision_label(i, scenario.junctions)
                    for i in range(len(quantum["probabilities_by_index"]))
                ],
                "probabilidad": quantum["probabilities_by_index"],
            }
        ).set_index("decisión")
        st.bar_chart(probability_table)
        with st.expander("Circuito Qiskit y convención de bits"):
            st.code(quantum["circuit_text"], language="text")
            st.write(result["bit_order"])
    st.subheader("Evolución del corredor")
    selection = st.selectbox("Decisión para inspeccionar", list(result["histories"]))
    history = result["histories"][selection]
    instant = st.slider("Instante de inspección · segundos", 0, len(history) - 1, 0)
    snapshot = history[instant]
    columns = st.columns(scenario.junctions)
    for i, column in enumerate(columns):
        with column:
            st.markdown(f"**Cruce {i + 1}**")
            st.caption(f"Fase: {snapshot['phase'][i]}")
            occupancy = snapshot["main_occupancy"][i]
            st.progress(
                occupancy / scenario.storage_vehicles,
                text=f"Enlace: {occupancy}/{scenario.storage_vehicles} vehículos",
            )
            st.caption(
                f"Principal lista: {snapshot['main_waiting'][i]} · "
                f"Transversal: {snapshot['side_queue'][i]}"
            )
    st.caption(f"Cola externa: {snapshot['external_queue']} · Salidas acumuladas: {snapshot['exited']}")
    series = pd.DataFrame(
        {
            f"Ocupación C{i + 1}": [row["main_occupancy"][i] for row in history]
            for i in range(scenario.junctions)
        }
    )
    series["Cola externa"] = [row["external_queue"] for row in history]
    st.line_chart(series)
    st.caption("Ocupación incluye vehículos en tránsito y detenidos; no equivale a cola detenida.")
    st.download_button(
        "Descargar experimento JSON",
        json.dumps(result, ensure_ascii=False, indent=2),
        file_name="simaphuru-experiment.json",
        mime="application/json",
    )
    with st.expander("Configuración, procedencia y reproducibilidad"):
        st.json(
            {
                "config_hash": result["config_hash"],
                "scenario": result["scenario"],
                "versions": result["versions"],
                "claims": result["claims"],
            }
        )
