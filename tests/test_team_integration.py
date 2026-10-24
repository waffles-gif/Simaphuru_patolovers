import copy
import itertools
import json
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError
from qiskit.quantum_info import Statevector

from model.chain import run as original_chain_run
from quantum.qubo import (
    build_one_hot,
    decode_one_hot,
    dynamic_programming,
    factor_cost,
    one_hot_index,
)
from simaphuru.team import (
    TeamParams,
    default_team_params,
    params_from_payload,
    run_team_experiment,
    verify_imported_payload,
)

ROOT = Path(__file__).resolve().parents[1]


def test_asymmetric_one_hot_costs_penalty_and_qiskit_bits():
    local, pairs = [[2, -1], [4, 0]], [[[-3, 2], [5, -7]]]
    qubo, proof = build_one_hot(local, pairs)
    energies = qubo.energies()
    hamiltonian = qubo.to_ising()
    for index in range(16):
        expected = float(Statevector.from_int(index, 16).expectation_value(hamiltonian).real)
        assert expected == pytest.approx(energies[index])
        plans = decode_one_hot(index, 2)
        if plans is not None:
            assert energies[index] == pytest.approx(factor_cost(local, pairs, plans))
    assert one_hot_index([1, 0]) == 6
    assert decode_one_hot(6, 2) == [1, 0]
    assert decode_one_hot(0, 2) is None
    assert decode_one_hot(int(np.argmin(energies)), 2) is not None
    assert proof["penalty"] > proof["feasible_upper_bound"] - proof["unpenalized_lower_bound"]


def test_dynamic_programming_matches_full_search_with_negative_interactions():
    rng = np.random.default_rng(4)
    local, pairs = rng.normal(size=(5, 2)).tolist(), rng.normal(size=(4, 2, 2)).tolist()
    plans, cost = dynamic_programming(local, pairs)
    brute_force = min(factor_cost(local, pairs, p) for p in itertools.product((0, 1), repeat=5))
    assert cost == pytest.approx(brute_force)
    assert cost == pytest.approx(factor_cost(local, pairs, plans))


def test_import_existing_r3_json_and_reject_incompatible_figures():
    payload = json.loads((ROOT / "data/model_output.json").read_text())
    params, notes = params_from_payload(payload)
    assert notes  # El contrato antiguo omite servicio y despeje: se declara la herencia.
    result = run_team_experiment(params, qaoa=False)
    verify_imported_payload(payload, result)
    assert result["audit"]["exact_representation"]
    assert len(result["model"]["combinations"]) == 4
    changed = copy.deepcopy(payload)
    changed["model"]["combinations"][0]["total_cost"] += 1
    with pytest.raises(ValueError, match="no reproduce"):
        verify_imported_payload(changed, result)
    payload["example"] = True
    with pytest.raises(ValueError, match="salida real"):
        params_from_payload(payload)


def test_five_crossings_matches_existing_chain_and_counts_unique_vehicles():
    original = original_chain_run(5)
    result = run_team_experiment(default_team_params(5), qaoa=False)
    assert len(result["model"]["combinations"]) == 32
    assert result["audit"]["max_absolute_error"] == pytest.approx(original["error"]["max_abs"])
    assert result["classical"]["optimal_cost"] == pytest.approx(original["best_exact"]["exact"])
    assert not result["audit"]["exact_representation"]
    for c in result["model"]["combinations"]:
        net = c["network"]
        assert net["external_demand"] == net["network_exited"] + net["network_pending"]
        assert net["network_pending"] == net["queued_end"] + net["in_transit_end"]
    assert result["audit"]["one_hot"]["states_checked"] == 1024


def test_qaoa_reports_invalid_mass_and_conditional_cost_without_inventing_traffic_cost():
    result = run_team_experiment(default_team_params(2), qaoa=True, max_evaluations=8)
    q = result["quantum"]
    valid = q["valid_probabilities"]
    assert sum(r["probability"] for r in valid) + q["invalid_probability"] == pytest.approx(1)
    assert q["expected_original"] is None
    assert q["conditional_expected_original"] == pytest.approx(
        sum(r["probability"] * r["original_cost"] for r in valid) / q["feasible_probability"]
    )
    assert q["original_optimal_probability"] <= q["feasible_probability"] + 1e-12
    assert len(q["probabilities_by_index"]) == 16
    json.dumps(result)


def test_contract_rejects_cycle_errors_and_duplicate_identifiers():
    params = default_team_params(2)
    params["cycle_s"] += 1
    with pytest.raises(ValidationError):
        TeamParams.model_validate(params)
    params = default_team_params(2)
    params["intersections"][1]["id"] = "A"
    with pytest.raises(ValidationError):
        TeamParams.model_validate(params)
