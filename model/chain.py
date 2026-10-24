"""
Opcional: cadena de N cruces (por defecto 5) conectados por EW.

Con N > 2 el costo de un cruce depende de TODOS los planes de los cruces anteriores
(el trafico se va filtrando), asi que "locales + pares vecinos" ya no es exacto.
Este script mide el error de esa aproximacion contra la simulacion completa.

Aproximacion:
  local_i[k]        = costo del cruce i aislado con plan k
  pair_i[a][b]      = costo(sub-corredor i -> i+1 con planes a,b) - local_i[a] - local_{i+1}[b]
  costo_aprox(x)    = sum_i local_i[x_i] + sum_i pair_i[x_i][x_{i+1}]

Uso:
    python model/chain.py               (5 cruces)
    python model/chain.py --n 4 --out data/chain_output.json
"""

import argparse
import copy
import itertools
import json
import os
import time

from traffic import default_params, simulate_chain

HERE = os.path.dirname(os.path.abspath(__file__))

# Tasas ilustrativas para una cadena de hasta 6 cruces (veh/min). A y B iguales al reto.
CHAIN_RATES = [
    {"NS": 18, "EW": 12},
    {"NS": 15, "EW": 14},
    {"NS": 16, "EW": 8},
    {"NS": 12, "EW": 10},
    {"NS": 17, "EW": 6},
    {"NS": 14, "EW": 9},
]


def chain_params(n):
    p = default_params()
    p["intersections"] = [
        {"id": chr(ord("A") + i), "name": "Cruce " + chr(ord("A") + i),
         "arrival_rate_vpm": dict(CHAIN_RATES[i])}
        for i in range(n)
    ]
    return p


def sub_params(params, idxs):
    q = copy.deepcopy(params)
    q["intersections"] = [params["intersections"][i] for i in idxs]
    return q


def run(n=5):
    params = chain_params(n)
    K = [pl["id"] for pl in params["plans"]]

    # locales y pares (solo con simulaciones de 1 y 2 cruces)
    local = [[simulate_chain([k], sub_params(params, [i]))["total_cost"] for k in K] for i in range(n)]
    pair = []
    for i in range(n - 1):
        sp = sub_params(params, [i, i + 1])
        m = [[simulate_chain([a, b], sp)["total_cost"] - local[i][a] - local[i + 1][b] for b in K] for a in K]
        pair.append(m)

    # simulacion completa de las 2^n combinaciones
    t0 = time.perf_counter()
    rows = []
    for x in itertools.product(K, repeat=n):
        exact = simulate_chain(list(x), params)["total_cost"]
        approx = sum(local[i][x[i]] for i in range(n)) + sum(pair[i][x[i]][x[i + 1]] for i in range(n - 1))
        rows.append({"plans": list(x), "exact": exact, "approx": approx, "error": approx - exact})
    runtime_ms = (time.perf_counter() - t0) * 1000

    best_exact = min(rows, key=lambda r: r["exact"])
    best_approx = min(rows, key=lambda r: r["approx"])
    abs_err = [abs(r["error"]) for r in rows]
    rel_err = [abs(r["error"]) / r["exact"] for r in rows]

    return {
        "n_intersections": n,
        "n_combinations": len(rows),
        "rates_vpm": [it["arrival_rate_vpm"] for it in params["intersections"]],
        "local_costs": local,
        "pair_costs": pair,
        "error": {
            "max_abs": max(abs_err),
            "mean_abs": sum(abs_err) / len(abs_err),
            "max_rel": max(rel_err),
            "mean_rel": sum(rel_err) / len(rel_err),
        },
        "best_exact": best_exact,
        "best_approx": best_approx,
        "approx_picks_true_optimum": best_approx["plans"] == best_exact["plans"],
        "approx_choice_real_cost": best_approx["exact"],
        "runtime_ms_full_enumeration": runtime_ms,
        "combinations": rows,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--out", default=os.path.join(HERE, "..", "data", "chain_output.json"))
    args = ap.parse_args()
    assert 2 <= args.n <= len(CHAIN_RATES)

    out = run(args.n)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    e = out["error"]
    print("N=%d, %d combinaciones" % (out["n_intersections"], out["n_combinations"]))
    print("Error aprox (local + pares): max abs %.4f | medio abs %.4f | max rel %.2f%% | medio rel %.2f%%"
          % (e["max_abs"], e["mean_abs"], 100 * e["max_rel"], 100 * e["mean_rel"]))
    print("Optimo exacto :", out["best_exact"]["plans"], "costo %.4f" % out["best_exact"]["exact"])
    print("Optimo aprox  :", out["best_approx"]["plans"], "costo real %.4f" % out["approx_choice_real_cost"])
    print("La aproximacion acierta el optimo:", out["approx_picks_true_optimum"])
    print("Guardado en", os.path.abspath(args.out))


if __name__ == "__main__":
    main()
