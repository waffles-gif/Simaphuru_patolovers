from pathlib import Path

import pytest
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


def test_switching_encoding_invalidates_results_and_both_views_run():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
    assert app.sidebar.selectbox[2].value == "binary"  # La interfaz abre en binaria.
    app.checkbox[0].uncheck().run()
    app.button[0].click().run(timeout=30)
    assert app.session_state["team_experiment"]["encoding"]["qubits"] == 2
    app.sidebar.selectbox[2].set_value("one_hot").run()
    assert not app.exception
    assert len(app.metric) == 0
    app.button[0].click().run(timeout=30)
    assert not app.exception
    assert app.session_state["team_experiment"]["encoding"]["qubits"] == 4


@pytest.mark.parametrize("case", ["empty", "zero_weights"])
def test_binary_view_handles_zero_cost_and_counts_all_tied_optima(case):
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
    app.sidebar.selectbox[2].set_value("binary").run()
    for field in app.number_input:
        if ((case == "empty" and " · " in field.label)
                or (case == "zero_weights" and field.label in ("Demora", "Cola máxima", "Residual"))):
            field.set_value(0.0)
    app.run()
    app.button[0].click().run(timeout=30)
    assert not app.exception
    assert app.session_state["team_experiment"]["classical"]["optimal_cost"] == 0
    assert app.metric[2].delta == "+0.0 pp vs azar"


@pytest.mark.parametrize("n", [3, 4])
def test_intermediate_corridors_run_and_do_not_expose_a_second_clock(n):
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
    assert app.sidebar.selectbox[0].options == ["2", "3", "4", "5"]
    app.sidebar.selectbox[0].set_value(n).run()
    app.sidebar.selectbox[2].set_value("binary").run()
    app.checkbox[1].check().run()
    app.button[0].click().run(timeout=30)
    assert not app.exception
    result = app.session_state["team_experiment"]
    assert len(result["model"]["combinations"]) == 2**n
    assert result["encoding"]["qubits"] == n
    assert result["hybrid"] is not None
    assert not any("Instante" in slider.label for slider in app.slider)
    for history in result["histories"].values():
        assert len(history["history"][0]["blocked"]) == n
    # Otro programa recrea el reproductor sin recalcular ni mezclar la configuración física.
    inspector = next(box for box in app.selectbox if box.label == "Planes para inspeccionar")
    old_id = result["experiment_id"]
    inspector.set_value(inspector.options[-1]).run()
    assert not app.exception
    assert app.session_state["team_experiment"]["experiment_id"] == old_id
