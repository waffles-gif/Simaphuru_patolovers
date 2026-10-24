"""
Enumeracion clasica (R3): corre las 4 combinaciones (A en {0,1}, B en {0,1}),
saca local_costs y pair_costs para el QUBO de R2, y el optimo por fuerza bruta.

Uso:
    python model/enumerate.py
    python model/enumerate.py --a-ns 18 --a-ew 12 --b-ns 15 --b-ew 14 --travel 25 \
        --w-delay 1 --w-peak 0.6 --w-res 1 --out data/model_output.json
"""

import argparse
import itertools
import json
import os
import time

try:
    from traffic import default_params, simulate_corridor, simulate_isolated
except ImportError:  # si se importa como paquete: from model.enumerate import ...
    from .traffic import default_params, simulate_corridor, simulate_isolated

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "..", "data", "model_output.json")


def build_params(args=None):
    """Arma el dict de parametros a partir de los defaults + linea de comandos."""
    p = default_params()
    if args is None:
        return p
    a, b = p["intersections"]
    a["arrival_rate_vpm"] = {"NS": args.a_ns, "EW": args.a_ew}
    b["arrival_rate_vpm"] = {"NS": args.b_ns, "EW": args.b_ew}
    p["travel_time_s"] = args.travel
    p["weights"] = {"delay": args.w_delay, "peak_queue": args.w_peak, "residual": args.w_res}
    return p


def one_hot(plan_a, plan_b):
    """Vector en el orden [x_A0, x_A1, x_B0, x_B1]."""
    x = [0, 0, 0, 0]
    x[plan_a] = 1
    x[2 + plan_b] = 1
    return x


def run(params):
    plan_ids = [pl["id"] for pl in params["plans"]]   # [0, 1]

    # 1) costos locales: cada cruce aislado (B sin trafico que viene de A)
    local = {"A": [], "B": []}
    for k in plan_ids:
        local["A"].append(simulate_isolated(0, k, params)["total_cost"])
        local["B"].append(simulate_isolated(1, k, params)["total_cost"])

    # 2) las 4 combinaciones con el corredor completo + fuerza bruta
    t0 = time.perf_counter()
    combos = []
    for pa, pb in itertools.product(plan_ids, plan_ids):
        r = simulate_corridor({"A": pa, "B": pb}, params)
        combos.append((pa, pb, r))
    best = min(combos, key=lambda c: c[2]["total_cost"])
    runtime_ms = (time.perf_counter() - t0) * 1000

    # 3) costo de par: lo que falta para que local + par = total exacto
    pair = [[0.0, 0.0], [0.0, 0.0]]
    for pa, pb, r in combos:
        pair[pa][pb] = r["total_cost"] - local["A"][pa] - local["B"][pb]

    r6 = lambda v: round(v, 6)
    combinations = []
    for pa, pb, r in combos:
        m = r["metrics"]
        combinations.append({
            "plans": {"A": pa, "B": pb},
            "total_cost": r6(r["total_cost"]),
            "metrics": {
                "mean_delay_s": round(m["mean_delay_s"], 3),
                "peak_queue": m["peak_queue"],
                "residual": m["residual"],
            },
            # extra (no rompe el formato): costo de cada cruce dentro del corredor
            "per_intersection_cost": {p["id"]: r6(p["cost"]) for p in r["per_intersection"]},
        })

    pa, pb, rb = best
    out = {
        "schema_version": "0.1",
        "example": False,
        "note": "Generado por R3 (model/enumerate.py). Parametros ilustrativos, no es una avenida real.",
        "inputs": {
            "horizon_s": params["horizon_s"],
            "cycle_s": params["cycle_s"],
            "weights": params["weights"],
            "intersections": params["intersections"],
            "plans": params["plans"],
            "link": {"from": "A", "to": "B", "travel_time_s": params["travel_time_s"]},
        },
        "_comment_model": "Lo llena R3 (motor de trafico): costos sacados del simulador.",
        "model": {
            "local_costs": {"A": [r6(v) for v in local["A"]], "B": [r6(v) for v in local["B"]]},
            "pair_costs": {
                "_comment": "pair_costs[planA][planB] = costo extra por la interaccion A->B "
                            "(total - local_A - local_B; local + par = total exacto)",
                "A-B": [[r6(v) for v in row] for row in pair],
            },
            "combinations": combinations,
        },
        "_comment_classical": "Lo llena R3: referencia exacta por enumeracion.",
        "classical": {
            "method": "brute_force",
            "optimal_plans": {"A": pa, "B": pb},
            "optimal_x": one_hot(pa, pb),
            "optimal_cost": r6(rb["total_cost"]),
            "runtime_ms": round(runtime_ms, 3),
        },
    }
    return out


def main():
    ap = argparse.ArgumentParser(description="Enumeracion clasica del corredor A->B")
    d = default_params()
    a, b = d["intersections"]
    ap.add_argument("--a-ns", type=float, default=a["arrival_rate_vpm"]["NS"])
    ap.add_argument("--a-ew", type=float, default=a["arrival_rate_vpm"]["EW"])
    ap.add_argument("--b-ns", type=float, default=b["arrival_rate_vpm"]["NS"])
    ap.add_argument("--b-ew", type=float, default=b["arrival_rate_vpm"]["EW"])
    ap.add_argument("--travel", type=int, default=d["travel_time_s"])
    ap.add_argument("--w-delay", type=float, default=d["weights"]["delay"])
    ap.add_argument("--w-peak", type=float, default=d["weights"]["peak_queue"])
    ap.add_argument("--w-res", type=float, default=d["weights"]["residual"])
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    out = run(build_params(args))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print("Guardado en", os.path.abspath(args.out))
    print("local_costs:", out["model"]["local_costs"])
    print("pair_costs A-B:", out["model"]["pair_costs"]["A-B"])
    for c in out["model"]["combinations"]:
        print("  A=%d B=%d  costo=%.4f  %s" % (c["plans"]["A"], c["plans"]["B"], c["total_cost"], c["metrics"]))
    print("Optimo:", out["classical"])


if __name__ == "__main__":
    main()
