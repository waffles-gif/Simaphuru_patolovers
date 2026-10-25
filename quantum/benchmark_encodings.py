"""Comparación emparejada de codificaciones; no es una prueba de ventaja cuántica.

python -m quantum.benchmark_encodings --out artifacts/benchmark_encodings.json
"""

import argparse
import csv
import hashlib
import json
import platform
import subprocess
from pathlib import Path

from simaphuru.team import default_team_params, run_team_experiment

SCENARIOS = ("default", "half_demand", "limited_storage")


def _source_state() -> dict:
    root = Path(__file__).resolve().parents[1]
    files = ("quantum/qubo.py", "quantum/benchmark_encodings.py", "simaphuru/team.py",
             "quantum/benchmark_hybrid.py", "simaphuru/hybrid.py", "simaphuru/quantum.py",
             "simaphuru/qubo.py", "model/traffic.py", "model/chain.py")
    state = {"files_sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                              for name in files}}
    try:
        state["git_revision"] = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()
        state["git_dirty"] = bool(subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        state["git_revision"], state["git_dirty"] = None, None
    return state


def run_benchmark(*, ns=(2, 5), seeds=(3, 7, 11), scenarios=SCENARIOS,
                  depth=3, max_evaluations=300) -> dict:
    if not ns or not seeds or not scenarios or any(seed < 0 for seed in seeds):
        raise ValueError("Se requieren tamaños, escenarios y semillas no negativas")
    if any(name not in SCENARIOS for name in scenarios):
        raise ValueError("Escenario de benchmark desconocido")
    rows, costs = [], []
    for scenario in scenarios:
        for n in ns:
            params = default_team_params(n)
            if scenario == "half_demand":
                for intersection in params["intersections"]:
                    for axis in ("NS", "EW"):
                        intersection["arrival_rate_vpm"][axis] *= 0.5
            elif scenario == "limited_storage":
                params["storage_vehicles"] = 4
            physical_reference = None
            for run, seed in enumerate(seeds):
                # Alternar orden reduce el sesgo sistemático de ejecutar siempre una versión primero.
                order = ("one_hot", "binary") if run % 2 == 0 else ("binary", "one_hot")
                for encoding in order:
                    r = run_team_experiment(params, encoding=encoding, seed=seed,
                                            depth=depth, max_evaluations=max_evaluations)
                    physical = [{"plans": c["plans"], "cost": c["total_cost"],
                                 "approx_cost": c["approx_cost"], "network": c["network"]}
                                for c in r["model"]["combinations"]]
                    if physical_reference is None:
                        physical_reference = physical
                        costs.append({"scenario": scenario, "n": n, "config_hash": r["config_hash"],
                                      "inputs": r["inputs"]["params"], "costs": physical})
                    elif physical != physical_reference:
                        raise ValueError("Las codificaciones no están comparando el mismo tráfico")
                    q, best = r["quantum"], r["classical"]["optimal_cost"]
                    rows.append({
                        "scenario": scenario, "n": n, "seed": seed, "encoding": encoding,
                        "config_hash": r["config_hash"], "experiment_id": r["experiment_id"],
                        "qubits": r["encoding"]["qubits"], "depth": depth,
                        "restarts": q["restarts"], "max_evaluations_per_restart": max_evaluations,
                        "evaluations": q["evaluations"], "versions": r["versions"],
                        "backend": q["backend"], "optimal_cost": best,
                        "uniform_expected_cost": r["classical"]["uniform_feasible_expected_cost"],
                        "uniform_optimal_probability": sum(
                            abs(c["total_cost"] - best) < 1e-9
                            for c in r["model"]["combinations"]) / len(physical),
                        "feasible_probability": q["feasible_probability"],
                        "optimal_probability": q["original_optimal_probability"],
                        "expected_physical_given_feasible": q["conditional_expected_original"],
                        "expected_gap_given_feasible": q["conditional_original_gap"],
                        "representative_plans": q["representative_plans"],
                        "representative_cost": q["representative_original_cost"],
                        "pairwise_error_max": r["audit"]["max_absolute_error"],
                        "factor_generation_ms": r["factor_generation_ms"],
                        "qaoa_ms": q["runtime_ms"], "total_ms": 1000 * r["elapsed_s"],
                        "valid_probabilities": q["valid_probabilities"],
                    })
                    print(f"{scenario} · N={n} · semilla={seed} · {encoding}: "
                          f"P(óptimo)={q['original_optimal_probability']:.4f}", flush=True)
    return {
        "benchmark_version": "encoding-paired-v1", "source": _source_state(),
        "python": platform.python_version(),
        "protocol": {"seeds": list(seeds), "ns": list(ns), "scenarios": list(scenarios),
                     "depth": depth, "max_evaluations_per_restart": max_evaluations,
                     "same_physics_verified": True, "same_surrogate": True,
                     "timing": "QAOA ms excluye factores; total incluye enumeración de auditoría. "
                               "Una corrida por configuración: no es un benchmark estable de tiempos.",
                     "scope": "Semillas de entrenamiento sobre escenarios sintéticos deterministas; "
                              "sin validación empírica, shots ni ventaja cuántica demostrada."},
        "cost_tables": costs, "runs": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, choices=(2, 3, 4, 5), nargs="+", default=[2, 5])
    parser.add_argument("--seeds", type=int, nargs="+", default=[3, 7, 11])
    parser.add_argument("--scenarios", choices=SCENARIOS, nargs="+", default=list(SCENARIOS))
    parser.add_argument("--depth", type=int, choices=(1, 2, 3), default=3)
    parser.add_argument("--max-evaluations", type=int, default=300)
    parser.add_argument("--out", type=Path, default=Path("artifacts/benchmark_encodings.json"))
    args = parser.parse_args()
    result = run_benchmark(ns=args.n, seeds=args.seeds, scenarios=args.scenarios,
                           depth=args.depth, max_evaluations=args.max_evaluations)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    fields = [key for key in result["runs"][0]
              if key not in ("valid_probabilities", "versions", "representative_plans")]
    with args.out.with_suffix(".csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(result["runs"])
    print("Resultados:", args.out.resolve())


if __name__ == "__main__":
    main()
