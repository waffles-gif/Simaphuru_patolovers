"""Grilla de filas independientes: cada fila es una cadena EW del motor del equipo.

El eje NS no tiene acoplamiento en el motor actual, así que el costo de la grilla es la
suma de costos por fila. Datos sintéticos; QAOA por bloques de 5 qubits en Statevector.
"""

import random
from time import perf_counter

from model.chain import sub_params
from model.traffic import default_params, simulate_chain
from quantum.qubo import build_binary, decode_binary, dynamic_programming, factor_cost
from simaphuru.quantum import solve_qaoa

BLOCK = 5


def grid_params(rows: int, cols: int, seed: int = 2026) -> list[dict]:
    """Una cadena de `cols` cruces por fila; tasas en los rangos de CHAIN_RATES (veh/min)."""
    if rows < 1 or cols < 2:
        raise ValueError("Se requieren rows >= 1 y cols >= 2")
    grid = []
    for r in range(rows):
        rng = random.Random(seed + r)
        p = default_params()
        p["intersections"] = [
            {"id": f"F{r}C{c}", "name": f"Fila {r} cruce {c}",
             "arrival_rate_vpm": {"NS": rng.randint(12, 18), "EW": rng.randint(6, 14)}}
            for c in range(cols)
        ]
        grid.append(p)
    return grid


def row_factors(params: dict) -> tuple[list, list]:
    """Locales y pares vecinos como en model/chain.py."""
    n = len(params["intersections"])
    local = [[simulate_chain([k], sub_params(params, [i]))["total_cost"] for k in (0, 1)]
             for i in range(n)]
    pairs = []
    for i in range(n - 1):
        sp = sub_params(params, [i, i + 1])
        pairs.append([[simulate_chain([a, b], sp)["total_cost"] - local[i][a] - local[i + 1][b]
                       for b in (0, 1)] for a in (0, 1)])
    return local, pairs


def solve_row_dp(local: list, pairs: list) -> list[int]:
    return dynamic_programming(local, pairs)[0]


def solve_row_qaoa_blocks(local: list, pairs: list, block: int = BLOCK, sweeps: int = 2,
                          seed: int = 7, stats: dict | None = None) -> list[int]:
    """Barridos de bloques; los vecinos fuera del bloque quedan fijos en el plan actual.

    Un bloque de QAOA se acepta solo si baja factor_cost en más de 1e-9; `stats` cuenta
    bloques aceptados y rechazados.
    """
    n = len(local)
    if n % block or not 2 <= block <= 5:
        raise ValueError("cols debe ser múltiplo del bloque y el bloque de 2..5 cruces")
    plans = [0] * n
    for _ in range(sweeps):
        for s in range(0, n, block):
            e = s + block
            sub_local = [list(row) for row in local[s:e]]
            if s > 0:
                for k in (0, 1):
                    sub_local[0][k] += pairs[s - 1][plans[s - 1]][k]
            if e < n:
                for k in (0, 1):
                    sub_local[-1][k] += pairs[e - 1][k][plans[e]]
            qubo, _ = build_binary(sub_local, pairs[s:e - 1])
            result = solve_qaoa(qubo, None, depth=3, seed=seed, restarts=2, max_evaluations=60)
            candidate = plans[:s] + decode_binary(result["most_likely_index"], block) + plans[e:]
            accepted = factor_cost(local, pairs, candidate) < factor_cost(local, pairs, plans) - 1e-9
            if accepted:
                plans = candidate
            if stats is not None:
                key = "accepted_blocks" if accepted else "rejected_blocks"
                stats[key] = stats.get(key, 0) + 1
    return plans


def solve_row_local_search(local: list, pairs: list, start: list[int] | None = None) -> list[int]:
    """Flip de un bit con primera mejora, hasta que ningún flip mejore."""
    plans = list(start) if start is not None else [0] * len(local)
    cost = factor_cost(local, pairs, plans)
    improved = True
    while improved:
        improved = False
        for i in range(len(plans)):
            plans[i] ^= 1
            candidate = factor_cost(local, pairs, plans)
            if candidate < cost - 1e-12:
                cost, improved = candidate, True
            else:
                plans[i] ^= 1
    return plans


def run_grid(rows: int, cols: int, qaoa: bool = True, seed: int = 2026) -> dict:
    solvers = {
        "base": lambda local, pairs: [0] * len(local),
        "dp": solve_row_dp,
        "local_search": solve_row_local_search,
    }
    block_stats = {"accepted_blocks": 0, "rejected_blocks": 0}
    if qaoa:
        if cols % BLOCK:
            raise ValueError(f"Con QAOA, cols debe ser múltiplo de {BLOCK}")
        solvers["qaoa_blocks"] = lambda local, pairs: solve_row_qaoa_blocks(
            local, pairs, stats=block_stats)
    totals = {name: {"qubo": 0.0, "real": 0.0} for name in solvers}
    times = {name: 0.0 for name in solvers}
    times.update(factors_s=0.0, real_simulation_s=0.0)
    row_results = []
    for r, params in enumerate(grid_params(rows, cols, seed)):
        t = perf_counter()
        local, pairs = row_factors(params)
        times["factors_s"] += perf_counter() - t
        row = {"row": r, "methods": {}}
        for name, solve in solvers.items():
            t = perf_counter()
            plans = solve(local, pairs)
            times[name] += perf_counter() - t
            t = perf_counter()
            real = float(simulate_chain(plans, params)["total_cost"])
            times["real_simulation_s"] += perf_counter() - t
            qubo_cost = factor_cost(local, pairs, plans)
            totals[name]["qubo"] += qubo_cost
            totals[name]["real"] += real
            row["methods"][name] = {"plans": plans, "qubo_cost": qubo_cost, "real_cost": real}
        row_results.append(row)
    return {"rows": rows, "cols": cols, "seed": seed, "n_variables": rows * cols,
            "totals": totals, "times_s": times,
            "qaoa_blocks": block_stats if qaoa else None, "row_results": row_results}
