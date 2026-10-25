from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

import simaphuru.hybrid as hybrid_module
from model.traffic import simulate_chain
from simaphuru.hybrid import compare_candidate_searches
from simaphuru.team import default_team_params, run_team_experiment


def test_hybrid_physically_evaluates_candidates_without_an_exhaustive_cost_table(monkeypatch):
    params = default_team_params(2)
    calls = []

    def counted(plans, inputs):
        calls.append(tuple(plans))
        return simulate_chain(plans, inputs)

    monkeypatch.setattr(hybrid_module, "simulate_chain", counted)
    result = compare_candidate_searches(params, [0, 0], [0, 1, 0, 0],
                                        encoding="binary", proposals=5, max_simulations=3)
    q = result["methods"]["qaoa_candidates"]
    assert q["selected_plans"] == [1, 0]
    assert q["selected_cost"] == pytest.approx(17.912638629067644)
    assert q["initial_cost"] == pytest.approx(24.08804241261722)
    assert q["simulator_evaluations"] == 2
    assert q["duplicates"] == 4
    assert len(calls) == sum(m["simulator_evaluations"] for m in result["methods"].values())
    assert not result["selection_uses_exact_reference"]
    assert not result["warm_start_quantum_state"]


def test_worse_candidates_do_not_replace_classical_initial_solution():
    result = compare_candidate_searches(default_team_params(2), [1, 0], [0, 0, 1, 0],
                                        encoding="binary", proposals=4, max_simulations=2)
    q = result["methods"]["qaoa_candidates"]
    assert q["selected_plans"] == [1, 0]
    assert q["selected_cost"] == q["initial_cost"]
    assert q["improvement"] == 0
    assert q["trace"][1]["cost"] > q["initial_cost"]


def test_invalid_one_hot_samples_consume_proposals_but_no_extra_simulations():
    p = [1.0] + [0.0] * 15  # 0000 no elige un programa por cruce.
    result = compare_candidate_searches(default_team_params(2), [0, 0], p,
                                        encoding="one_hot", proposals=5, max_simulations=2)
    q = result["methods"]["qaoa_candidates"]
    assert q["invalid_samples"] == 5
    assert q["proposal_attempts"] == 5
    assert q["simulator_evaluations"] == 1
    assert q["selected_plans"] == [0, 0]


def test_same_budget_caps_initial_accounting_and_sampling_reproducibility():
    arguments = dict(encoding="binary", proposals=12, max_simulations=3, sampling_seed=11)
    a = compare_candidate_searches(default_team_params(2), [0, 0], [0.25] * 4, **arguments)
    b = compare_candidate_searches(default_team_params(2), [0, 0], [0.25] * 4, **arguments)
    for name, method in a["methods"].items():
        assert method["simulator_evaluations"] <= 3
        assert method["proposal_attempts"] <= 12
        assert method["trace"][0]["source"] == "classical_initial"
        assert method["trace"] == b["methods"][name]["trace"]
        assert method["selected_cost"] <= method["initial_cost"]
    only_initial = compare_candidate_searches(default_team_params(2), [0, 0], [0.25] * 4,
                                              encoding="binary", proposals=4, max_simulations=1)
    assert all(m["simulator_evaluations"] == 1 for m in only_initial["methods"].values())


@pytest.mark.parametrize("p", [[0.25] * 3, [0] * 4, [np.nan] * 4, [-1, 1, 1, 0]])
def test_incompatible_quantum_distribution_is_rejected(p):
    with pytest.raises(ValueError, match="Distribución"):
        compare_candidate_searches(default_team_params(2), [0, 0], p, encoding="binary")


def test_team_integrates_verified_results_and_histories_without_changing_physics():
    params = default_team_params(5)
    base = run_team_experiment(params, encoding="binary", max_evaluations=4)
    result = run_team_experiment(params, encoding="binary", max_evaluations=4, hybrid=True,
                                 candidate_proposals=10, max_candidate_simulations=5)
    assert result["experiment_id"] != base["experiment_id"]
    assert result["config_hash"] == base["config_hash"]
    assert result["classical"]["optimal_cost"] == base["classical"]["optimal_cost"]
    assert result["quantum"]["probabilities_by_index"] == base["quantum"]["probabilities_by_index"]
    for method in result["hybrid"]["methods"].values():
        plans = list(method["selected_plans"].values())
        independent = simulate_chain(plans, params)
        assert method["selected_cost"] == independent["total_cost"]
        assert method["gap_to_exact"] == pytest.approx(
            method["selected_cost"] - result["classical"]["optimal_cost"])
        assert any(history["plans"] == method["selected_plans"]
                   for history in result["histories"].values())
    with pytest.raises(ValueError, match="requiere"):
        run_team_experiment(params, qaoa=False, hybrid=True)


def test_hybrid_streamlit_view_runs_five_crossings_and_invalidates_sampling_budget():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
    app.sidebar.selectbox[0].set_value(5).run()
    app.sidebar.selectbox[2].set_value("binary").run()
    app.checkbox[1].check().run()
    app.button[0].click().run(timeout=30)
    assert not app.exception
    assert app.session_state["team_experiment"]["hybrid"] is not None
    next(field for field in app.number_input if field.label == "Máximo de propuestas").set_value(16).run()
    assert not app.exception
    assert len(app.metric) == 0
