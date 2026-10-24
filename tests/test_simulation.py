import numpy as np
import pytest

from simaphuru.models import Blockage, Scenario, decision_vector
from simaphuru.simulation import arrival_trace, phase, simulate


def scenario(**kwargs):
    fields = {"scenario_id": "test", "provenance": "sintético", "junctions": 2, "horizon_s": 100}
    return Scenario(**(fields | kwargs))


@pytest.mark.parametrize("choice,main,side", [(0, 30, 30), (1, 40, 20)])
def test_feasible_phases(choice, main, side):
    phases = [phase(t, choice) for t in range(68)]
    assert phases.count("principal") == main
    assert phases.count("transversal") == side
    assert phases.count("despeje") == 8


def test_single_vehicle_has_travel_time_and_is_never_duplicated():
    s = scenario(horizon_s=12, travel_time_s=3)
    trace = np.zeros((12, 3), dtype=int)
    trace[0, 0] = 1
    result = simulate(s, (0, 0), trace, record_history=True)
    first = next(r["t"] for r in result.history if r["main_flow"][0])
    second = next(r["t"] for r in result.history if r["main_flow"][1])
    assert first == 1  # Crédito: 0,5 por segundo; primera salida al segundo paso.
    assert second >= first + 3
    assert result.arrivals == result.exited == 1
    assert result.residual == 0


def test_full_downstream_blocks_upstream_and_counts_external_demand():
    s = scenario(
        storage_vehicles=3,
        travel_time_s=2,
        main_veh_min=60,
        side_veh_min=0,
        service_veh_s=1,
        blockages=(Blockage(junction=1, start_s=0, duration_s=100, capacity_factor=0),),
    )
    result = simulate(s, (0, 0), arrival_trace(s, 7), record_history=True)
    assert result.exited == 0
    assert result.blocked_seconds[0] > 0
    assert result.history[-1]["external_queue"] > 0
    for row in result.history:
        assert max(row["main_occupancy"]) <= 3
        assert row["arrivals"] == (
            row["exited"]
            + sum(row["main_occupancy"])
            + sum(row["side_queue"])
            + row["external_queue"]
        )


def test_seeded_trace_and_all_five_crossing_decisions_conserve():
    s = scenario(junctions=5, arrival_mode="poisson")
    trace = arrival_trace(s, 42)
    np.testing.assert_array_equal(trace, arrival_trace(s, 42))
    assert not np.array_equal(trace, arrival_trace(s, 43))
    assert not trace.flags.writeable
    for i in range(32):
        result = simulate(s, decision_vector(i, 5), trace)
        assert result.arrivals == result.exited + result.residual
        assert result.cost >= 0


def test_no_traffic_is_zero_and_bad_decision_fails():
    s = scenario(main_veh_min=0, side_veh_min=0)
    trace = arrival_trace(s, 0)
    result = simulate(s, (0, 0), trace)
    assert result.cost == result.residual == result.arrivals == result.exited == 0
    with pytest.raises(ValueError):
        simulate(s, (0, 2), trace)
