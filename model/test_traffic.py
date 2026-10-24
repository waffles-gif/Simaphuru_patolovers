"""
Checks simples del motor de trafico. Correr con:
    python model/test_traffic.py        (o)    python -m pytest model/test_traffic.py
"""

import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from traffic import AXES, default_params, simulate_chain, simulate_corridor, phase  # noqa: E402
from enumerate import run  # noqa: E402
from chain import chain_params  # noqa: E402

COMBOS = [{"A": a, "B": b} for a, b in itertools.product([0, 1], [0, 1])]


def test_conservation():
    """Por cada cola: llegados (externos + desde A) = servidos + en cola (+ backlog en EW)."""
    p = default_params()
    for plans in COMBOS:
        r = simulate_corridor(plans, p)
        for inter in r["per_intersection"]:
            for a in AXES:
                llegados = inter["arrived_external"][a]
                quedan = inter["queue_end"][a]
                if a == "EW":
                    llegados += inter["arrived_from_link"]
                    quedan += inter["backlog_end"]
                assert llegados == inter["served"][a] + quedan, (plans, inter["id"], a)
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


# ---- almacenamiento finito (K_e) y spillback: casos_manuales.md ----

def _manual_params(horizon):
    """Corredor A -> B sin llegadas externas, para ver solo el inventario inicial."""
    p = default_params()
    p["horizon_s"] = horizon
    for it in p["intersections"]:
        it["arrival_rate_vpm"] = {"NS": 0, "EW": 0}
    return p


def _occupancy(inter):
    """Ocupacion del tramo EW que entra al cruce: cola EW + autos en transito hacia el."""
    return inter["queue_end"]["EW"] + inter["in_transit_end"]


# A con plan 0 tiene verde EW en s = 34..63 del ciclo; B con plan 1 recien en 44..63,
# asi que entre t = 34 y 43 B no descarga y su tramo solo cambia por lo que manda A.

def test_caso1_flujo_libre():
    """Origen 10, destino vacio, verde: en 10 s a 0.5 veh/s pasan 5."""
    r = simulate_chain([0, 1], _manual_params(10),
                       initial_state={"t0": 34, "queues": [{"EW": 10}, {"EW": 0}]})
    A, B = r["per_intersection"]
    assert A["served"]["EW"] == 5
    assert A["queue_end"]["EW"] == 5
    assert _occupancy(B) == 5
    assert A["blocked_s"] == 0


def test_caso2_spillback_destino_lleno():
    """Origen 10, destino con K_e = 12 autos, verde: transferencia cero."""
    r = simulate_chain([0, 1], _manual_params(10),
                       initial_state={"t0": 34, "queues": [{"EW": 10}, {"EW": 12}]})
    A, B = r["per_intersection"]
    assert A["served"]["EW"] == 0
    assert A["queue_end"]["EW"] == 10
    assert _occupancy(B) == 12
    assert A["blocked_s"] == 10


def test_caso3_despeje_sin_movimiento():
    """Origen 5 al iniciar el despeje de 4 s (s = 64..67 tras el verde EW): nada se mueve."""
    r = simulate_chain([0, 1], _manual_params(4),
                       initial_state={"t0": 64, "queues": [{"EW": 5}, {"EW": 0}]})
    A, B = r["per_intersection"]
    assert sum(A["served"].values()) == 0 and sum(B["served"].values()) == 0
    assert A["queue_end"]["EW"] == 5
    assert _occupancy(B) == 0


def test_network_conservation_with_backlog():
    """Llegadas externas = salidas de la red + colas + en transito + backlog (5 cruces)."""
    p = chain_params(5)
    hubo_backlog = False
    for x in itertools.product([0, 1], repeat=5):
        r = simulate_chain(list(x), p)
        per = r["per_intersection"]
        externas = sum(sum(q["arrived_external"].values()) for q in per)
        salidas = sum(q["served"]["NS"] for q in per) + per[-1]["served"]["EW"]
        colas = sum(sum(q["queue_end"].values()) for q in per)
        backlog = sum(q["backlog_end"] for q in per)
        assert externas == salidas + colas + r["in_transit_end"] + backlog, x
        assert r["metrics"]["residual"] == colas + backlog
        hubo_backlog |= backlog > 0
    assert hubo_backlog, "el caso no ejercita el desborde externo"


def test_storage_never_exceeds_ke():
    p = chain_params(5)
    K = p["storage_vehicles"]
    hubo_spillback = False
    for x in itertools.product([0, 1], repeat=5):
        r = simulate_chain(list(x), p, keep_history=True)
        for step in r["history"]:
            assert all(occ <= K for occ in step["occupancy"]), (x, step["t"])
        assert all(q["peak_occupancy"] <= K for q in r["per_intersection"])
        hubo_spillback |= r["metrics"]["blocked_s"] > 0
    assert hubo_spillback, "con los defaults deberia ocurrir spillback"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("OK ", t.__name__)
    print("Todos los tests pasaron (%d)" % len(tests))
