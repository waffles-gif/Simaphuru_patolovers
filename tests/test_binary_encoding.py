import itertools

import numpy as np
import pytest
from qiskit.quantum_info import Statevector

from quantum.benchmark_encodings import run_benchmark
from quantum.qubo import (
    binary_index,
    build_binary,
    build_one_hot,
    decode_binary,
    factor_cost,
    one_hot_index,
)
from simaphuru.team import default_team_params, params_from_payload, run_team_experiment
from web.team_app import _benchmark_rows, _gap_percent, _uniform_optimal_probability


@pytest.mark.parametrize("n", [2, 3, 4, 5])
def test_binary_substitution_preserves_every_asymmetric_factor_cost_and_ising_energy(n):
    rng = np.random.default_rng(41 + n)
    local = rng.normal(size=(n, 2)).tolist()
    pairs = rng.normal(size=(n - 1, 2, 2)).tolist()
    binary, proof = build_binary(local, pairs)
    one_hot, _ = build_one_hot(local, pairs)
    hamiltonian = binary.to_ising()
    energies = binary.energies()
    for plans in itertools.product((0, 1), repeat=n):
        index = binary_index(plans)
        assert decode_binary(index, n) == list(plans)
        expected = factor_cost(local, pairs, plans)
        assert energies[index] == pytest.approx(expected)
        assert one_hot.evaluate(tuple(int(q == plan) for plan in plans for q in (0, 1))) == pytest.approx(expected)
        assert Statevector.from_int(index, 2**n).expectation_value(hamiltonian).real == pytest.approx(expected)
    assert proof["states_checked"] == 2**n
    assert proof["penalty"] == 0
    assert proof["feasible_identity_max_error"] < 1e-10


@pytest.mark.parametrize("n", [2, 3, 4, 5])
def test_encoding_change_preserves_physics_and_surrogate_error_but_changes_execution_id(n):
    params = default_team_params(n)
    original = run_team_experiment(params, qaoa=False)
    compact = run_team_experiment(params, qaoa=False, encoding="binary")
    assert compact["config_hash"] == original["config_hash"]
    assert compact["experiment_id"] != original["experiment_id"]
    assert compact["classical"]["optimal_cost"] == original["classical"]["optimal_cost"]
    assert compact["classical"]["optimal_plans"] == original["classical"]["optimal_plans"]
    assert compact["audit"]["max_absolute_error"] == original["audit"]["max_absolute_error"]
    assert compact["histories"] == original["histories"]
    assert compact["encoding"]["qubits"] == n
    assert original["encoding"]["qubits"] == 2 * n
    for before, after in zip(original["model"]["combinations"], compact["model"]["combinations"]):
        assert before["network"] == after["network"]
        assert before["metrics"] == after["metrics"]
        assert before["total_cost"] == after["total_cost"]
        assert after["decision_index"] == binary_index(tuple(after["plans"].values()))
        assert after["one_hot_index"] == one_hot_index(tuple(after["plans"].values()))
    imported, _ = params_from_payload(compact)
    assert imported == params


def test_binary_qaoa_probability_order_and_physical_expectation_are_audited():
    result = run_team_experiment(default_team_params(5), encoding="binary", max_evaluations=8)
    q = result["quantum"]
    p = q["probabilities_by_index"]
    assert len(p) == 32
    assert q["feasible_probability"] == pytest.approx(1)
    assert q["invalid_probability"] < 1e-12
    assert sum(p) == pytest.approx(1)
    physical = sum(p[c["decision_index"]] * c["total_cost"]
                   for c in result["model"]["combinations"])
    assert q["conditional_expected_original"] == pytest.approx(physical)
    for row in q["valid_probabilities"]:
        assert row["probability"] == p[binary_index(tuple(row["plans"].values()))]
    selected = max(q["valid_probabilities"], key=lambda row: row["probability"])
    assert q["representative_plans"] == selected["plans"]
    assert q["representative_original_cost"] == selected["original_cost"]


def test_zero_cost_and_tied_optima_do_not_invent_a_percentage_or_a_unique_optimum():
    params = default_team_params(2)
    params["weights"] = dict.fromkeys(params["weights"], 0.0)
    result = run_team_experiment(params, encoding="binary")
    assert _uniform_optimal_probability(result) == 1
    assert result["quantum"]["original_optimal_probability"] == pytest.approx(1)
    assert result["quantum"]["evaluations"] == 0
    assert all(row["Brecha %"] == 0 for row in _benchmark_rows(result))
    assert _gap_percent(1, 0) is None
    rows = _benchmark_rows(result)
    modal = next(row for row in rows if "más probable" in row["Método"])
    assert modal["P(óptimo)"] is None  # La moda no equivale a un muestreo del circuito.


def test_rejects_unknown_encoding_and_invalid_binary_factors():
    with pytest.raises(ValueError, match="Codificación"):
        run_team_experiment(default_team_params(2), encoding="other")
    with pytest.raises(ValueError, match="finitos"):
        build_binary([[0, np.nan], [1, 2]], [[[1, 2], [3, 4]]])
    with pytest.raises(ValueError, match="2..5"):
        build_binary([[0, 1]], [])
    with pytest.raises(ValueError, match="Índice"):
        decode_binary(4, 2)


def test_paired_benchmark_checks_shared_physics_and_records_budget():
    result = run_benchmark(ns=(2,), seeds=(11,), scenarios=("limited_storage",),
                           depth=1, max_evaluations=2)
    assert len(result["runs"]) == 2
    a, b = result["runs"]
    assert a["encoding"] != b["encoding"]
    assert a["config_hash"] == b["config_hash"]
    assert a["optimal_cost"] == b["optimal_cost"]
    assert a["pairwise_error_max"] == b["pairwise_error_max"]
    assert a["evaluations"] <= 6 and b["evaluations"] <= 6
    assert result["protocol"]["same_physics_verified"]
