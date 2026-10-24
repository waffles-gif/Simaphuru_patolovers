from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_runs_a_real_baseline_and_invalidates_changed_configuration():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run(timeout=30)
    assert not app.exception
    app.checkbox[0].uncheck().run()
    app.button[0].click().run(timeout=30)
    assert not app.exception
    assert len(app.metric) == 3
    app.number_input[0].set_value(8).run()
    assert not app.exception
    assert len(app.metric) == 0  # No reutilizar resultados de otra configuración.


def test_experimental_model_remains_separate_and_runnable():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run(timeout=30)
    app.radio[0].set_value("Experimental · almacenamiento limitado").run()
    app.checkbox[0].uncheck().run()
    app.button[0].click().run(timeout=30)
    assert not app.exception
    assert len(app.metric) == 3
    assert app.session_state["experiment"]["model_version"] == "queue-network-v1"
    assert app.session_state["experiment"]["schema_version"] == "1.0"


def test_team_view_executes_qiskit_and_invalidates_another_corridor():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run(timeout=30)
    app.button[0].click().run(timeout=30)
    assert not app.exception
    result = app.session_state["team_experiment"]
    assert result["quantum"]["feasible_probability"] > 0
    assert result["model_version"] == "team-ns-ew-v2"
    app.sidebar.selectbox[0].set_value(5).run(timeout=30)
    assert not app.exception
    assert len(app.metric) == 0
