from time import perf_counter

import pytest

from quantum.qubo import factor_cost
from simaphuru.grid import grid_params, row_factors, run_grid


def test_grid_2x10_dp_bounds_qaoa_blocks_and_runs_fast():
    start = perf_counter()
    result = run_grid(2, 10)
    assert perf_counter() - start < 30
    assert result["n_variables"] == 20
    stats = result["qaoa_blocks"]
    assert stats["accepted_blocks"] + stats["rejected_blocks"] == 2 * 2 * 2  # filas*bloques*barridos
    for row, params in zip(result["row_results"], grid_params(2, 10)):
        local, pairs = row_factors(params)
        dp, qaoa = row["methods"]["dp"], row["methods"]["qaoa_blocks"]
        assert dp["qubo_cost"] == pytest.approx(factor_cost(local, pairs, dp["plans"]))
        assert dp["qubo_cost"] <= qaoa["qubo_cost"] + 1e-9
        assert qaoa["qubo_cost"] <= row["methods"]["base"]["qubo_cost"] + 1e-9
        assert dp["qubo_cost"] <= row["methods"]["local_search"]["qubo_cost"] + 1e-9


def test_grid_rates_are_deterministic_and_in_range():
    a, b = grid_params(3, 5), grid_params(3, 5)
    assert a == b
    for params in a:
        for it in params["intersections"]:
            assert 12 <= it["arrival_rate_vpm"]["NS"] <= 18
            assert 6 <= it["arrival_rate_vpm"]["EW"] <= 14
