"""QUBO one-hot de locales y pares vecinos, compatible con el contrato de R3."""

import itertools

import numpy as np

from simaphuru.qubo import Qubo

# P = 1.5*(U-L) > U-L: misma garantia; en 2 cruces sube P(optimo) de QAOA p=3 (ver VALIDATION.md).
PENALTY_FACTOR = 1.5


def one_hot_index(plans: list[int] | tuple[int, ...]) -> int:
    """x_i0 y x_i1 ocupan los qubits 2*i y 2*i+1 (peso binario 2**q)."""
    return sum(1 << (2 * i + plan) for i, plan in enumerate(plans))


def decode_one_hot(index: int, size: int) -> list[int] | None:
    plans = []
    for i in range(size):
        bits = (index >> (2 * i)) & 3
        if bits not in (1, 2):
            return None
        plans.append(0 if bits == 1 else 1)
    return plans


def factor_cost(local: list, pairs: list, plans: list[int] | tuple[int, ...]) -> float:
    return float(
        sum(local[i][k] for i, k in enumerate(plans))
        + sum(pairs[i][plans[i]][plans[i + 1]] for i in range(len(pairs)))
    )


def build_one_hot(local: list, pairs: list) -> tuple[Qubo, dict]:
    """P = max(1, 1.5*(U-L)) > U-L: todo estado inválido cuesta más que un candidato factible U."""
    n = len(local)
    if not 2 <= n <= 5 or np.shape(local) != (n, 2) or np.shape(pairs) != (n - 1, 2, 2):
        raise ValueError("Se requieren 2..5 cruces, dos planes y pares vecinos 2x2")
    if not np.isfinite(local).all() or not np.isfinite(pairs).all():
        raise ValueError("Los costos deben ser finitos")
    linear = [float(c) for row in local for c in row]
    quadratic = [
        (2 * i + a, 2 * (i + 1) + b, float(pairs[i][a][b]))
        for i in range(n - 1) for a in range(2) for b in range(2)
    ]
    lower = sum(min(0.0, c) for c in linear) + sum(min(0.0, c) for _, _, c in quadratic)
    upper = factor_cost(local, pairs, [0] * n)
    penalty = max(1.0, PENALTY_FACTOR * (upper - lower))
    for i in range(n):
        linear[2 * i] -= penalty
        linear[2 * i + 1] -= penalty
        quadratic.append((2 * i, 2 * i + 1, 2 * penalty))
    qubo = Qubo(n * penalty, linear, quadratic)
    energies = qubo.energies()
    valid = [one_hot_index(p) for p in itertools.product((0, 1), repeat=n)]
    expected = [factor_cost(local, pairs, p) for p in itertools.product((0, 1), repeat=n)]
    invalid = sorted(set(range(len(energies))) - set(valid))
    mismatch = float(np.max(np.abs(energies[valid] - expected)))
    invalid_min, valid_min = float(energies[invalid].min()), float(energies[valid].min())
    if mismatch > 1e-8 or invalid_min <= valid_min:
        raise ValueError("La auditoría one-hot falló")
    return qubo, {
        "penalty": penalty,
        "unpenalized_lower_bound": lower,
        "feasible_upper_bound": upper,
        "proof": "P = max(1, 1.5(U-L)) > U-L; cualquier estado inválido tiene penalización >= P",
        "feasible_identity_max_error": mismatch,
        "invalid_minimum_energy": invalid_min,
        "feasible_minimum_energy": valid_min,
        "all_global_minimizers_feasible": True,
        "states_checked": len(energies),
    }


def dynamic_programming(local: list, pairs: list) -> tuple[list[int], float]:
    """Óptimo clásico del costo por pares en O(N*K²), sin afirmar exactitud física."""
    paths = [([k], float(local[0][k])) for k in (0, 1)]
    for i in range(1, len(local)):
        paths = [
            min(
                ((path + [k], cost + pairs[i - 1][path[-1]][k] + local[i][k])
                 for path, cost in paths),
                key=lambda item: item[1],
            )
            for k in (0, 1)
        ]
    plans, cost = min(paths, key=lambda item: item[1])
    return plans, float(cost)
