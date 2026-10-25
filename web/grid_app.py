"""Grilla de avenidas EW independientes sobre el motor del equipo. No redefine sus ecuaciones."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from model.traffic import default_params, simulate_chain
from simaphuru.grid import BLOCK, EW_RANGE, NS_RANGE, grid_params, run_grid
from web.animation import render_animation

ARTIFACT = Path(__file__).resolve().parents[1] / "artifacts" / "grid_1000.json"
METHODS = {"base": "Base (todo 0)", "dp": "Programación dinámica",
           "qaoa_blocks": "QAOA por bloques", "local_search": "Búsqueda local"}
# Segundos por cruce medidos en el benchmark 40×25 (factores + verificación; QAOA aparte).
SECONDS_PER_CROSSING, QAOA_SECONDS_PER_CROSSING = 0.03, 0.05


@st.cache_data(show_spinner=False)
def _run(rows, cols, seed, qaoa, ns_range, ew_range, travel, storage, weights):
    return run_grid(rows, cols, qaoa=qaoa, seed=seed, ns_range=ns_range, ew_range=ew_range,
                    travel_time_s=travel, storage_vehicles=storage, weights=dict(weights))


def _load_artifact() -> dict | None:
    try:
        data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        data["totals"]["base"]["real"]
        return data
    except Exception:
        return None


def _improvement(totals: dict, key: str) -> float:
    base = totals["base"]["real"]
    return 100 * (base - totals[key]["real"]) / base if base else 0.0


def _render_traffic(result: dict, grid: list[dict]) -> None:
    cols = result["cols"]
    if cols > 10:
        st.info("La animación está disponible hasta 10 cruces por fila")
    else:
        rows = list(range(result["rows"]))
        st.caption(f"Se animan {min(2, len(rows))} de las {len(rows)} avenidas; elige cuáles.")
        left, right = st.columns(2)
        picked = [left.selectbox("Primera avenida", rows, index=0)]
        if len(rows) > 1:
            picked.append(right.selectbox("Segunda avenida", rows, index=1))
        for r in dict.fromkeys(picked):
            params = grid[r]
            plans = result["row_results"][r]["methods"]["dp"]["plans"]
            ids = [it["id"] for it in params["intersections"]]
            sim = simulate_chain(plans, params, keep_history=True)
            st.subheader(f"Avenida EW · fila {r}")
            st.caption(f"Plan DP: {' · '.join(f'{i}={k}' for i, k in zip(ids, plans))} · "
                       f"costo real {sim['total_cost']:.3f}")
            render_animation({"plans": dict(zip(ids, plans)), "history": sim["history"]}, params)
    st.caption("Las avenidas se simulan por separado: el eje NS no tiene tramos ni spillback en "
               "el motor actual.")


def _render_comparison(result: dict) -> None:
    totals, times = result["totals"], result["times_s"]
    blocks = result.get("qaoa_blocks") or {}
    st.dataframe(pd.DataFrame([{
        "Método": label,
        "Costo real": totals[key]["real"],
        "Mejora vs base (%)": _improvement(totals, key),
        "Costo QUBO": totals[key]["qubo"],
        "Tiempo (s)": times[key],
        "Bloques aceptados": str(blocks.get("accepted_blocks", "—")) if key == "qaoa_blocks" else "—",
        "Bloques rechazados": str(blocks.get("rejected_blocks", "—")) if key == "qaoa_blocks" else "—",
    } for key, label in METHODS.items() if key in totals]), hide_index=True, width="stretch",
        column_config={c: st.column_config.NumberColumn(format="%.3f")
                       for c in ("Costo real", "Mejora vs base (%)", "Costo QUBO", "Tiempo (s)")})
    solved = [k for k in ("dp", "qaoa_blocks", "local_search") if k in totals]
    reals = [totals[k]["real"] for k in solved]
    spread = 100 * (max(reals) - min(reals)) / min(reals) if min(reals) else 0.0
    short = {"dp": "programación dinámica", "qaoa_blocks": "QAOA por bloques",
             "local_search": "búsqueda local"}
    names = ", ".join(short[k] for k in solved[:-1]) + " y " + short[solved[-1]]
    names = names[0].upper() + names[1:]
    note = "El costo QUBO aproxima por pares y no coincide con el costo real; compare solo costos reales. "
    if spread < 0.04:
        note += (f"{names} quedan a menos de 0,04 % entre sí en costo real: es un empate dentro del "
                 "error de la aproximación. ")
    else:
        note += f"{names} quedan a {spread:.2f} % entre sí en costo real. ".replace(".", ",", 1)
    note += "La programación dinámica es exacta para el QUBO y tarda milisegundos"
    if "qaoa_blocks" in times:
        note += f"; QAOA tarda {times['qaoa_blocks']:.0f} s en simulador ideal"
    st.caption(note + ".")
    cols = st.columns(2)
    cols[0].metric("Construir factores", f"{times.get('factors_s', 0):.2f} s")
    cols[1].metric("Verificar en simulador", f"{times.get('real_simulation_s', 0):.2f} s")


def _render_plan(result: dict) -> None:
    plans = [row["methods"]["dp"]["plans"] for row in result["row_results"]]
    fig, ax = plt.subplots(figsize=(8, max(2.0, 8 * len(plans) / len(plans[0]) * 0.6)))
    ax.imshow(plans, cmap="cividis", vmin=0, vmax=1, aspect="auto")
    ax.set_xlabel("Cruce de la avenida EW")
    ax.set_ylabel("Avenida (fila)")
    st.pyplot(fig)
    plt.close(fig)
    st.caption("Oscuro: plan 0 (30/30 s) · claro: plan 1 (NS 40 / EW 20 s).")


def _render_limitations() -> None:
    st.markdown(
        "- **Sin spillback NS:** las avenidas EW no se acoplan; el eje NS no tiene tramos ni "
        "capacidad finita en el motor actual.\n"
        f"- **QAOA por bloques de {BLOCK} qubits** en `qiskit.quantum_info.Statevector` "
        "(simulador ideal, sin ruido, sin QPU). Un bloque se acepta solo si baja el costo QUBO.\n"
        "- **Datos sintéticos:** tasas enteras pseudoaleatorias por fila; no calibradas con "
        "aforos reales.\n"
        "- **La programación dinámica es exacta para el QUBO** por pares; el costo real de cada "
        "plan se verifica con el simulador completo de la fila.\n"
        "- **Sin ventaja cuántica:** los tiempos son de simulación local y no la demuestran.")


def render() -> None:
    st.title("Escalabilidad · grilla de 1000 variables (experimental)")
    st.write("Varias avenidas EW del motor del equipo, un bit por cruce, optimizadas por fila.")
    st.info("Parámetros ilustrativos, no calibrados. Las avenidas no se acoplan entre sí porque el eje "
            "NS no tiene tramos en el motor actual. QAOA corre por bloques de 5 qubits en "
            "Statevector (simulador ideal, sin QPU).")
    precomputed = st.sidebar.toggle("Ver benchmark 40×25 precalculado", value=False)
    base = default_params()
    rows = int(st.sidebar.number_input("Filas (avenidas EW)", min_value=1, max_value=10, value=2,
                                       step=1, disabled=precomputed))
    cols = st.sidebar.selectbox("Cruces por fila", [5, 10, 15, 20, 25], disabled=precomputed)
    seed = int(st.sidebar.number_input("Semilla de tasas", min_value=0, value=2026, step=1,
                                       disabled=precomputed))
    storage = st.sidebar.slider("Capacidad de cada tramo EW (K) · veh", 1, 40,
                                base["storage_vehicles"], disabled=precomputed)
    travel = st.sidebar.slider("Viaje entre cruces · s", 1, 90, base["travel_time_s"],
                               disabled=precomputed)
    with st.sidebar.expander("Llegadas externas · veh/min"):
        ns_range = st.slider("Rango NS", 0, 60, NS_RANGE, disabled=precomputed)
        ew_range = st.slider("Rango EW", 0, 60, EW_RANGE, disabled=precomputed)
    weights = {}
    with st.sidebar.expander("Pesos del costo"):
        for key, label in (("delay", "Demora"), ("peak_queue", "Cola máxima"), ("residual", "Residual")):
            weights[key] = st.number_input(label, min_value=0.0, max_value=10.0,
                                           value=base["weights"][key], step=0.1, disabled=precomputed)
    qaoa = st.sidebar.checkbox("Incluir QAOA por bloques", value=True, disabled=precomputed)

    if precomputed:
        result = _load_artifact()
        if result is None:
            st.info("Benchmark de escala no disponible")
            return
        grid = grid_params(result["rows"], result["cols"], result["seed"])
    else:
        key = (rows, cols, seed, qaoa, tuple(ns_range), tuple(ew_range), travel, storage,
               tuple(sorted(weights.items())))
        estimate = rows * cols * (SECONDS_PER_CROSSING + (QAOA_SECONDS_PER_CROSSING if qaoa else 0))
        if st.button("Ejecutar", type="primary"):
            with st.spinner(f"Simulando {rows}×{cols} cruces… tiempo estimado ~{estimate:.0f} s"):
                _run(*key)
            st.session_state["grid_key"] = key
        if st.session_state.get("grid_key") != key:
            st.write(f"Ejecuta para obtener resultados de esta configuración (~{estimate:.0f} s).")
            return
        result = _run(*key)
        grid = grid_params(rows, cols, seed, ns_range=tuple(ns_range), ew_range=tuple(ew_range),
                           travel_time_s=travel, storage_vehicles=storage, weights=weights)

    totals, times = result["totals"], result["times_s"]
    st.header("Resultados")
    m = st.columns(4)
    m[0].metric("Variables binarias", result["n_variables"])
    m[1].metric("Costo real · base", f"{totals['base']['real']:.3f}")
    m[2].metric("Costo real · DP", f"{totals['dp']['real']:.3f}",
                delta=f"{_improvement(totals, 'dp'):.2f} % mejor que base", delta_color="off")
    m[3].metric("Tiempo total", f"{sum(times.values()):.1f} s")

    tabs = st.tabs(["Tráfico", "Comparación", "Plan", "Limitaciones"])
    with tabs[0]:
        _render_traffic(result, grid)
    with tabs[1]:
        _render_comparison(result)
    with tabs[2]:
        _render_plan(result)
    with tabs[3]:
        _render_limitations()
