"""Ejecutar: python -m quantum.run_qaoa --input data/model_output.json."""

import argparse
import json
from pathlib import Path

from simaphuru.team import (
    default_team_params,
    params_from_payload,
    run_team_experiment,
    verify_imported_payload,
)


def main():
    parser = argparse.ArgumentParser(description="Motor R3, QUBO one-hot y QAOA Qiskit")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input", type=Path, help="Salida R3 schema 0.1/0.2; se verifica contra el motor")
    source.add_argument("--params", type=Path, help="Parámetros completos del motor en JSON")
    parser.add_argument("--n", type=int, choices=(2, 3, 4, 5), default=2)
    parser.add_argument("--depth", type=int, choices=(1, 2, 3), default=3)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-evaluations", type=int, default=300, help="Por reinicio, tres reinicios")
    parser.add_argument("--no-qaoa", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("artifacts/team_result.json"))
    args = parser.parse_args()
    payload, notes = None, []
    if args.input:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        params, notes = params_from_payload(payload)
    elif args.params:
        params = json.loads(args.params.read_text(encoding="utf-8"))
    else:
        params = default_team_params(args.n)
    if payload:
        # Verificar antes de entrenar QAOA sobre una entrada que podría ser incompatible.
        checked = run_team_experiment(params, qaoa=False)
        verify_imported_payload(payload, checked)
    result = run_team_experiment(params, qaoa=not args.no_qaoa, depth=args.depth,
                                 seed=args.seed, max_evaluations=args.max_evaluations)
    result["import_notes"] = notes
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Resultado:", args.out.resolve())
    print("Óptimo del simulador:", result["classical"]["optimal_plans"],
          result["classical"]["optimal_cost"])
    print("Error máximo locales + pares:", result["audit"]["max_absolute_error"])
    if result["quantum"]:
        print("Probabilidad factible:", result["quantum"]["feasible_probability"])


if __name__ == "__main__":
    main()
