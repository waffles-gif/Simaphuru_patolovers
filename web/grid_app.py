"""Vista de solo lectura del benchmark de escala (artifacts/grid_1000.json)."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

ARTIFACT = Path(__file__).resolve().parents[1] / "artifacts" / "grid_1000.json"
METHODS = {"base": "Base (todo 0)", "dp": "Programación dinámica",
           "qaoa_blocks": "QAOA por bloques", "local_search": "Búsqueda local"}


def render() -> None:
    st.title("Escalabilidad · grilla de 1000 variables (experimental)")
    st.info("40 corredores EW de 25 cruces, un bit por cruce. Los corredores no se acoplan entre "
            "sí porque el eje NS no tiene tramos en el motor actual. QAOA corre por bloques de 5 "
            "qubits en Statevector (simulador ideal, sin QPU). Datos sintéticos. La programación "
            "dinámica es exacta para el QUBO; el costo real se verifica en el simulador.")
    try:
        data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        totals, times = data["totals"], data["times_s"]
        base_real = totals["base"]["real"]
    except Exception:
        st.info("Benchmark de escala no disponible")
        return

    st.dataframe(pd.DataFrame([{
        "Método": label,
        "Costo real": totals[key]["real"],
        "Mejora vs base (%)": 100 * (base_real - totals[key]["real"]) / base_real,
        "Costo QUBO": totals[key]["qubo"],
        "Tiempo (s)": times[key],
    } for key, label in METHODS.items() if key in totals]), hide_index=True, width="stretch",
        column_config={c: st.column_config.NumberColumn(format="%.3f")
                       for c in ("Costo real", "Mejora vs base (%)", "Costo QUBO", "Tiempo (s)")})
    st.caption("El costo QUBO aproxima por pares y no coincide con el costo real; compare solo "
               "costos reales. Programación dinámica, QAOA por bloques y búsqueda local quedan a "
               "menos de 0,04 % entre sí en costo real: es un empate dentro del error de la "
               "aproximación. La programación dinámica es exacta para el QUBO y tarda "
               "milisegundos; QAOA tarda 49 s en simulador ideal.")

    blocks = data.get("qaoa_blocks") or {}
    cols = st.columns(4)
    cols[0].metric("Bloques QAOA aceptados", blocks.get("accepted_blocks", "—"))
    cols[1].metric("Bloques QAOA rechazados", blocks.get("rejected_blocks", "—"))
    cols[2].metric("Construir factores", f"{times.get('factors_s', 0):.2f} s")
    cols[3].metric("Verificar en simulador", f"{times.get('real_simulation_s', 0):.2f} s")

    st.subheader("Plan elegido por programación dinámica")
    plans = [row["methods"]["dp"]["plans"] for row in data.get("row_results", [])]
    if plans:
        fig, ax = plt.subplots(figsize=(8, 8 * len(plans) / max(len(plans[0]), 1) * 0.6))
        ax.imshow(plans, cmap="cividis", vmin=0, vmax=1, aspect="auto")
        ax.set_xlabel("Cruce del corredor EW")
        ax.set_ylabel("Corredor")
        st.pyplot(fig)
        plt.close(fig)
        st.caption("Oscuro: plan 0 (30/30 s) · claro: plan 1 (NS 40 / EW 20 s).")
