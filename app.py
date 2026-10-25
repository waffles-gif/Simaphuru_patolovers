"""Entrada Streamlit: motor del equipo y ampliación experimental separados."""

import streamlit as st

st.set_page_config(page_title="Simaphuru", page_icon="🚦", layout="wide")
mode = st.sidebar.radio("Modelo", ["Motor del equipo · NS/EW", "Experimental · almacenamiento limitado",
                                  "Escalabilidad · grilla (experimental)"])
if mode == "Motor del equipo · NS/EW":
    from web.team_app import render
elif mode == "Escalabilidad · grilla (experimental)":
    from web.grid_app import render
else:
    from web.reference_app import render

render()
