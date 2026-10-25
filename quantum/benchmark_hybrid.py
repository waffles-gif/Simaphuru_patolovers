"""Ablación del aporte de candidatos QAOA con el mismo inicio y límites de búsqueda."""

import argparse
import csv
import json
from pathlib import Path

from quantum.benchmark_encodings import SCENARIOS, _source_state
from simaphuru.hybrid import compare_candidate_searches
from simaphuru.team import default_team_params, run_team_experiment


def run_benchmark(*, ns=(2, 5), seeds=(3, 7, 11, 2026), scenarios=SCENARIOS,
                  depth=3, optimizer_seed=7, max_evaluations=300,
                  proposals=32, max_simulations=8) -> dict:
    cases, training, rows = [], [], []
    if not ns or not seeds or not scenarios or any(name not in SCENARIOS for name in scenarios):
        raise ValueError("Se requieren escenarios, tamaños y semillas de muestreo")
    for scenario in scenarios:
        for n in ns:
            params = default_team_params(n)
            if scenario == "half_demand":
                for intersection in params["intersections"]:
                    for axis in ("NS", "EW"):
                        intersection["arrival_rate_vpm"][axis] *= 0.5
            elif scenario == "limited_storage":
                params["storage_vehicles"] = 4
            # Entrenar una vez por escenario; las semillas posteriores cambian solo el muestreo.
            reference = run_team_experiment(params, encoding="binary", depth=depth,
                                            seed=optimizer_seed, max_evaluations=max_evaluations)
            q = reference["quantum"]
            training.append({"scenario": scenario, "n": n, "config_hash": reference["config_hash"],
                             "experiment_id": reference["experiment_id"], "versions": reference["versions"],
                             "params": params, "quantum": q,
                             "initial_plans": reference["pairwise_classical"]["optimal_plans"],
                             "optimal_cost_reference_only": reference["classical"]["optimal_cost"]})
            for seed in seeds:
                result = compare_candidate_searches(
                    params, list(reference["pairwise_classical"]["optimal_plans"].values()),
                    q["probabilities_by_index"], encoding="binary", proposals=proposals,
                    max_simulations=max_simulations, sampling_seed=seed)
                cases.append({"scenario": scenario, "n": n, "result": result})
                for name, method in result["methods"].items():
                    best = reference["classical"]["optimal_cost"]
                    rows.append({"scenario": scenario, "n": n, "sampling_seed": seed,
                                 "method": name, "initial_cost": method["initial_cost"],
                                 "selected_cost": method["selected_cost"],
                                 "improvement": method["improvement"],
                                 "gap_to_exact": method["selected_cost"] - best,
                                 "found_optimum": abs(method["selected_cost"] - best) < 1e-9,
                                 "simulator_evaluations": method["simulator_evaluations"],
                                 "proposal_attempts": method["proposal_attempts"],
                                 "runtime_ms_selection_only": method["runtime_ms"]})
                print(f"{scenario} · N={n} · muestreo={seed}: " + ", ".join(
                    f"{key}={value['selected_cost']:.4f}" for key, value in result["methods"].items()),
                    flush=True)
    return {"benchmark_version": "verified-candidates-ablation-v1", "source": _source_state(),
            "protocol": {"optimizer_seed": optimizer_seed, "sampling_seeds": list(seeds),
                         "ns": list(ns), "scenarios": list(scenarios), "depth": depth,
                         "max_evaluations_per_restart": max_evaluations,
                         "proposals_limit": proposals, "simulator_evaluations_limit": max_simulations,
                         "initial_included": True,
                         "scope": "Mismos límites de búsqueda, no igual tiempo total. Entrenamiento QAOA "
                                  "adicional registrado; muestreo clásico ideal, sin hardware ni ventaja cuántica."},
            "training": training, "cases": cases, "runs": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, choices=(2, 3, 4, 5), nargs="+", default=[2, 5])
    parser.add_argument("--seeds", type=int, nargs="+", default=[3, 7, 11, 2026])
    parser.add_argument("--scenarios", choices=SCENARIOS, nargs="+", default=list(SCENARIOS))
    parser.add_argument("--max-evaluations", type=int, default=300)
    parser.add_argument("--candidate-proposals", type=int, default=32)
    parser.add_argument("--max-candidate-simulations", type=int, default=8)
    parser.add_argument("--out", type=Path, default=Path("artifacts/final_hybrid.json"))
    args = parser.parse_args()
    result = run_benchmark(ns=args.n, seeds=args.seeds, scenarios=args.scenarios,
                           max_evaluations=args.max_evaluations,
                           proposals=args.candidate_proposals,
                           max_simulations=args.max_candidate_simulations)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    with args.out.with_suffix(".csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(result["runs"][0]))
        writer.writeheader()
        writer.writerows(result["runs"])
    print("Resultados:", args.out.resolve())


if __name__ == "__main__":
    main()
