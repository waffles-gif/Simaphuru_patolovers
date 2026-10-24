"""Aproximación cuadrática con auditoría completa de la tabla original."""

from dataclasses import dataclass

import numpy as np

from simaphuru.models import decision_vector


@dataclass
class Qubo:
    constant: float
    linear: list[float]
    pairs: list[tuple[int, int, float]]

    def evaluate(self, decision: tuple[int, ...]) -> float:
        return float(
            self.constant
            + sum(a * x for a, x in zip(self.linear, decision))
            + sum(b * decision[i] * decision[j] for i, j, b in self.pairs)
        )

    def energies(self) -> np.ndarray:
        return np.array(
            [
                self.evaluate(decision_vector(i, len(self.linear)))
                for i in range(2 ** len(self.linear))
            ]
        )

    def to_ising(self):
        from qiskit.quantum_info import SparsePauliOp

        size = len(self.linear)
        constant = self.constant + sum(self.linear) / 2 + sum(b for _, _, b in self.pairs) / 4
        z = [-a / 2 for a in self.linear]
        terms = [("I" * size, constant)]
        for i, j, b in self.pairs:
            z[i] -= b / 4
            z[j] -= b / 4
            label = ["I"] * size
            label[size - 1 - i] = label[size - 1 - j] = "Z"
            terms.append(("".join(label), b / 4))
        for i, coefficient in enumerate(z):
            label = ["I"] * size
            label[size - 1 - i] = "Z"
            terms.append(("".join(label), coefficient))
        return SparsePauliOp.from_list(terms).simplify()


def from_costs(costs: list[float]) -> Qubo:
    values = np.asarray(costs, dtype=float)
    size = (len(values) - 1).bit_length()
    if size < 1 or len(values) != 2**size or not np.all(np.isfinite(values)):
        raise ValueError("Se necesita una tabla finita de longitud 2**n")
    constant = float(values[0])
    linear = [float(values[1 << i] - constant) for i in range(size)]
    pairs = [
        (i, j, float(values[(1 << i) | (1 << j)] - values[1 << i] - values[1 << j] + constant))
        for i in range(size)
        for j in range(i + 1, size)
    ]
    return Qubo(constant, linear, pairs)


def audit(qubo: Qubo, costs: list[float]) -> dict:
    original, approximated = np.asarray(costs), qubo.energies()
    exact_index, qubo_index = int(np.argmin(original)), int(np.argmin(approximated))
    qubo_min = float(approximated[qubo_index])
    ties = np.flatnonzero(np.isclose(approximated, qubo_min, atol=1e-9, rtol=1e-9))
    return {
        "max_absolute_error": float(np.max(np.abs(original - approximated))),
        "exact_index": exact_index,
        "qubo_index": qubo_index,
        "decision_regret": float(original[qubo_index] - original[exact_index]),
        "qubo_tie_original_cost_range": [float(original[ties].min()), float(original[ties].max())],
        "exact_representation": bool(np.allclose(original, approximated, atol=1e-9, rtol=1e-9)),
        "original_costs": original.tolist(),
        "qubo_costs": approximated.tolist(),
    }
