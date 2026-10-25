"""Búsqueda de candidatos: no recibe la tabla exhaustiva ni conoce el óptimo físico.

La distribución QAOA se muestrea clásicamente; no son shots ejecutados en una QPU.
Cada método vuelve a evaluar sus candidatos con la misma física y un caché independiente.
"""

from itertools import combinations
from time import perf_counter

import numpy as np

from model.traffic import simulate_chain
from quantum.qubo import decode_binary, decode_one_hot


def _search(params, initial, propose, *, proposals, max_simulations):
    started = perf_counter()
    cache, log = {}, []
    best, best_cost = tuple(initial), float("inf")

    def evaluate(plans, source):
        nonlocal best, best_cost
        result = simulate_chain(list(plans), params)
        cost = float(result["total_cost"])
        cache[plans] = {"cost": cost, "metrics": result["metrics"]}
        improved = cost < best_cost - 1e-9
        if improved:
            best, best_cost = plans, cost
        log.append({"plans": list(plans), "status": "simulated", "source": source,
                    "cost": cost, "improved": improved})

    evaluate(best, "classical_initial")
    stop_reason = "proposal_limit"
    for attempt in range(proposals):
        # Los generadores clásicos locales pueden usar únicamente costos ya evaluados.
        try:
            plans = propose(attempt, best, cache)
        except StopIteration:
            stop_reason = "simulation_limit_or_local_neighborhood_exhausted"
            break
        if plans is None:
            log.append({"plans": None, "status": "invalid"})
        elif plans in cache:
            log.append({"plans": list(plans), "status": "duplicate", "cost": cache[plans]["cost"]})
        elif len(cache) >= max_simulations:
            log.append({"plans": list(plans), "status": "not_evaluated_budget"})
        else:
            evaluate(plans, "candidate")
    initial_cost = cache[tuple(initial)]["cost"]
    return {"initial_plans": list(initial), "initial_cost": initial_cost,
            "selected_plans": list(best), "selected_cost": best_cost,
            "improvement": initial_cost - best_cost, "metrics": cache[best]["metrics"],
            "simulator_evaluations": len(cache), "proposal_attempts": len(log) - 1,
            "duplicates": sum(row["status"] == "duplicate" for row in log),
            "invalid_samples": sum(row["status"] == "invalid" for row in log),
            "not_evaluated_budget": sum(row["status"] == "not_evaluated_budget" for row in log),
            "stop_reason": stop_reason,
            "runtime_ms": (perf_counter() - started) * 1000, "trace": log}


def compare_candidate_searches(params: dict, initial_plans: list[int],
                              quantum_probabilities: list[float], *, encoding: str,
                              proposals: int = 32, max_simulations: int = 8,
                              sampling_seed: int = 2026) -> dict:
    """Mismos límites de propuestas y evaluaciones físicas; no igual tiempo total.

    Una evaluación física inicial cuenta en max_simulations. Duplicados y estados
    inválidos consumen propuestas pero no otra simulación. No se completan presupuestos
    con soluciones elegidas desde la tabla exacta. El mejor inicial siempre se conserva.
    """
    n = len(params["intersections"])
    if (encoding not in ("one_hot", "binary") or proposals < 1 or max_simulations < 1
            or sampling_seed < 0 or len(initial_plans) != n
            or any(plan not in (0, 1) for plan in initial_plans)):
        raise ValueError("Configuración de búsqueda híbrida inválida")
    size = n if encoding == "binary" else 2 * n
    p = np.asarray(quantum_probabilities, dtype=float)
    if (p.shape != (2**size,) or not np.isfinite(p).all() or np.any(p < 0)
            or not np.isclose(p.sum(), 1, atol=1e-9, rtol=1e-9)):
        raise ValueError("Distribución QAOA incompatible con la codificación")
    p = p / p.sum()
    quantum_rng = np.random.default_rng(sampling_seed)
    uniform_rng = np.random.default_rng(sampling_seed)
    local_rng = np.random.default_rng(sampling_seed)
    samples = quantum_rng.choice(len(p), size=proposals, p=p)
    random_plans = uniform_rng.integers(0, 2, size=(proposals, n))
    decode = decode_binary if encoding == "binary" else decode_one_hot

    def quantum(attempt, best, cache):
        decoded = decode(int(samples[attempt]), n)
        return None if decoded is None else tuple(decoded)

    def uniform(attempt, best, cache):
        return tuple(int(x) for x in random_plans[attempt])

    def local(attempt, best, cache):
        if len(cache) >= max_simulations:
            raise StopIteration
        # Buscar vecinos no evaluados de un bit; si se agotan, ampliar a dos bits.
        for distance in (1, 2):
            neighbors = []
            for positions in combinations(range(n), distance):
                candidate = list(best)
                for pos in positions:
                    candidate[pos] ^= 1
                candidate = tuple(candidate)
                if candidate not in cache:
                    neighbors.append(candidate)
            if neighbors:
                return neighbors[int(local_rng.integers(len(neighbors)))]
        raise StopIteration

    methods = {name: _search(params, initial_plans, proposer, proposals=proposals,
                              max_simulations=max_simulations)
               for name, proposer in (("qaoa_candidates", quantum),
                                      ("uniform_candidates", uniform), ("local_search", local))}
    if any(row["selected_cost"] > row["initial_cost"] + 1e-9 for row in methods.values()):
        raise ValueError("La selección no puede empeorar la solución inicial")
    return {
        "method": "classical_seed_and_verified_candidates_v1",
        "initial_source": "dynamic_programming_pairwise",
        "sampling_kind": "classical_sampling_from_ideal_qaoa_probabilities",
        "sampling_seed": sampling_seed,
        "budget": {"proposals": proposals, "max_simulator_evaluations": max_simulations,
                   "initial_evaluation_included": True},
        "selection_uses_exact_reference": False,
        "warm_start_quantum_state": False,
        "timing_scope": "Solo propuestas y evaluación física; excluye factores, DP y entrenamiento QAOA.",
        "methods": methods,
    }
