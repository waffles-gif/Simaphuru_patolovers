"""
Checks simples del motor de trafico. Correr con:
    python model/test_traffic.py        (o)    python -m pytest model/test_traffic.py
"""

import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from traffic import AXES, default_params, simulate_corridor, phase  # noqa: E402
from enumerate import run  # noqa: E402

COMBOS = [{"A": a, "B": b} for a, b in itertools.product([0, 1], [0, 1])]


def test_conservation():
    """Por cada cola: llegados (externos + desde A) = servidos + en cola."""
    p = default_params()
    for plans in COMBOS:
        r = simulate_corridor(plans, p)
        for inter in r["per_intersection"]:
            for a in AXES:
                llegados = inter["arrived_external"][a]
                if a == "EW":
                    llegados += inter["arrived_from_link"]
                assert llegados == inter["served"][a] + inter["queue_end"][a], (plans, inter["id"], a)
        # lo que sale del EW de A = lo que llego a B por el enlace + lo que sigue en viaje
        A, B = r["per_intersection"]
        assert A["served"]["EW"] == B["arrived_from_link"] + r["in_transit_end"]


def test_queues_never_negative():
    p = default_params()
    for plans in COMBOS:
        r = simulate_corridor(plans, p, keep_history=True)
        for inter in r["per_intersection"]:
            assert all(v >= 0 for v in inter["min_queue"].values())
        for step in r["history"]:
            for q in step["queues"]:
                assert q["NS"] >= 0 and q["EW"] >= 0


def test_no_service_in_red():
    """Un eje solo puede despachar autos cuando la fase es su verde."""
    p = default_params()
    for plans in COMBOS:
        r = simulate_corridor(plans, p, keep_history=True)
        for step in r["history"]:
            for ph, dep in zip(step["phases"], step["departures"]):
                for a in AXES:
                    if ph != a:
                        assert dep[a] == 0, (plans, step["t"], ph, a)


def test_phase_layout():
    """Plan 0: 30 NS + 4 rojo + 30 EW + 4 rojo = 68 s."""
    g = {"NS": 30, "EW": 30}
    fases = [phase(t, g, 68, 4) for t in range(68)]
    assert fases.count("NS") == 30 and fases.count("EW") == 30 and fases.count("CLEAR") == 8


def test_deterministic():
    p = default_params()
    for plans in COMBOS:
        r1 = simulate_corridor(plans, p, keep_history=True)
        r2 = simulate_corridor(plans, p, keep_history=True)
        assert r1 == r2


def test_local_plus_pair_equals_total():
    out = run(default_params())
    local = out["model"]["local_costs"]
    pair = out["model"]["pair_costs"]["A-B"]
    for c in out["model"]["combinations"]:
        a, b = c["plans"]["A"], c["plans"]["B"]
        assert abs(local["A"][a] + local["B"][b] + pair[a][b] - c["total_cost"]) < 1e-5


def test_classical_is_min():
    out = run(default_params())
    best = min(c["total_cost"] for c in out["model"]["combinations"])
    assert abs(out["classical"]["optimal_cost"] - best) < 1e-9
    x = out["classical"]["optimal_x"]
    assert sum(x[:2]) == 1 and sum(x[2:]) == 1


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("OK ", t.__name__)
    print("Todos los tests pasaron (%d)" % len(tests))
