import numpy as np
import pytest
from qiskit.quantum_info import Statevector

from simaphuru.models import decision_label, decision_vector
from simaphuru.quantum import probabilities, solve_qaoa
from simaphuru.qubo import audit, from_costs


def test_asymmetric_two_bit_table_matches_qubo_and_ising_order():
    costs = [3, 1, 4, 0]  # Índice binario: q0 tiene peso 1.
    qubo = from_costs(costs)
    np.testing.assert_allclose(qubo.energies(), costs)
    hamiltonian = qubo.to_ising()
    for index, expected in enumerate(costs):
        state = Statevector.from_int(index, 4)
        assert float(state.expectation_value(hamiltonian).real) == pytest.approx(expected)
    assert decision_vector(1, 2) == (1, 0)
    assert decision_label(1, 2) == "10"
    assert audit(qubo, costs)["exact_representation"]


def test_cubic_interaction_is_reported_not_mislabeled_as_exact():
    costs = [0] * 7 + [1]
    result = audit(from_costs(costs), costs)
    assert not result["exact_representation"]
    assert result["max_absolute_error"] == 1


def test_analytic_qaoa_interference_and_normalization():
    qubo = from_costs([0, 1, 0, 1])
    probs = probabilities(qubo, [np.pi / 2, -np.pi / 4])
    assert probs.sum() == pytest.approx(1)
    assert probs[0] + probs[2] == pytest.approx(1)


def test_optimizer_returns_real_distribution_and_original_objective():
    costs = [3, 1, 4, 0]
    result = solve_qaoa(from_costs(costs), costs, restarts=1, max_evaluations=25)
    probs = np.asarray(result["probabilities_by_index"])
    assert probs.sum() == pytest.approx(1)
    assert 0 <= result["expected_original"] <= np.mean(costs) + 1e-9
    assert result["expected_original"] == pytest.approx(probs @ costs)
    assert result["backend"] == "qiskit.quantum_info.Statevector"


def test_constant_qubo_stays_uniform_without_fake_success():
    result = solve_qaoa(from_costs([7, 7, 7, 7]), [7, 7, 7, 7])
    np.testing.assert_allclose(result["probabilities_by_index"], [0.25] * 4)
    assert result["evaluations"] == 0
    assert result["original_optimal_probability"] == pytest.approx(1)
