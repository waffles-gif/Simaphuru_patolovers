"""QAOA real en circuitos Qiskit; evaluación local de vector de estado."""

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from scipy.optimize import minimize

from simaphuru.qubo import Qubo


def circuit(qubo: Qubo, angles: list[float]) -> QuantumCircuit:
    if not angles or len(angles) % 2:
        raise ValueError("Se necesitan pares gamma, beta")
    size = len(qubo.linear)
    span = float(np.ptp(qubo.energies()))
    qc = QuantumCircuit(size)
    qc.h(range(size))
    z = [-a / 2 for a in qubo.linear]
    for i, j, b in qubo.pairs:
        z[i] -= b / 4
        z[j] -= b / 4
    for gamma, beta in zip(angles[::2], angles[1::2]):
        if span > 1e-12:
            for i, value in enumerate(z):
                qc.rz(2 * gamma * value / span, i)
            for i, j, b in qubo.pairs:
                qc.rzz(2 * gamma * (b / 4) / span, i, j)
        qc.rx(2 * beta, range(size))
    return qc


def probabilities(qubo: Qubo, angles: list[float]) -> np.ndarray:
    return Statevector.from_instruction(circuit(qubo, angles)).probabilities()


def solve_qaoa(
    qubo: Qubo,
    original_costs: list[float] | None,
    *,
    depth: int = 1,
    seed: int = 7,
    restarts: int = 3,
    max_evaluations: int = 60,
) -> dict:
    if depth not in (1, 2) or restarts < 1 or max_evaluations < 1:
        raise ValueError("Configuración de entrenamiento inválida")
    energies = qubo.energies()
    if original_costs is not None and len(original_costs) != len(energies):
        raise ValueError("La tabla original y el QUBO deben coincidir")
    rng = np.random.default_rng(seed)
    # Incluimos |+> como candidato inicial: el mejor resultado nunca empeora su esperanza.
    best_angles = np.zeros(2 * depth)
    best_expected = float(energies.mean())
    history, evaluations = [], 0

    def objective(angles):
        nonlocal best_angles, best_expected, evaluations
        value = float(probabilities(qubo, angles.tolist()) @ energies)
        evaluations += 1
        if value < best_expected:
            best_expected, best_angles = value, angles.copy()
        history.append(best_expected)
        return value

    if float(np.ptp(energies)) > 1e-12:
        for _ in range(restarts):
            minimize(
                objective,
                rng.uniform(-np.pi, np.pi, 2 * depth),
                method="Nelder-Mead",
                options={"maxfev": max_evaluations},
            )
    angles = best_angles.tolist()
    probs = probabilities(qubo, angles)
    true = None if original_costs is None else np.asarray(original_costs)
    return {
        "backend": "qiskit.quantum_info.Statevector",
        "depth": depth,
        "seed": seed,
        "restarts": restarts,
        "evaluations": evaluations,
        "optimizer": "Nelder-Mead",
        "max_evaluations_per_restart": max_evaluations,
        "angles_gamma_beta": angles,
        "probabilities_by_index": probs.tolist(),
        "expected_qubo": float(probs @ energies),
        "expected_original": None if true is None else float(probs @ true),
        "qubo_gap": float(probs @ energies - energies.min()),
        "original_gap": None if true is None else float(probs @ true - true.min()),
        "original_optimal_probability": None if true is None else float(
            probs[np.isclose(true, true.min(), atol=1e-9, rtol=1e-9)].sum()
        ),
        "most_likely_index": int(np.argmax(probs)),
        "best_expectation_trace": history,
        "circuit_text": str(circuit(qubo, angles).draw(output="text")),
        "execution_kind": "local_exact_probabilities_no_hardware_no_shots",
    }
