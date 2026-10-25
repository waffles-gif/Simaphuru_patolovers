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
    parser = argparse.ArgumentParser(description="Motor R3, QUBO auditable y QAOA Qiskit")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input", type=Path, help="Salida R3 schema 0.1/0.2/0.3; se verifica contra el motor")
    source.add_argument("--params", type=Path, help="Parámetros completos del motor en JSON")
    parser.add_argument("--n", type=int, choices=(2, 3, 4, 5), default=2)
    parser.add_argument("--depth", type=int, choices=(1, 2, 3), default=3)
    parser.add_argument("--encoding", choices=("one_hot", "binary"), default="one_hot",
                        help="Mismo costo por pares; binaria usa un qubit por cruce")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-evaluations", type=int, default=300, help="Por reinicio, tres reinicios")
    parser.add_argument("--no-qaoa", action="store_true")
    parser.add_argument("--hybrid", action="store_true", help="Comparar candidatos verificados con búsquedas clásicas")
    parser.add_argument("--candidate-proposals", type=int, default=32)
    parser.add_argument("--max-candidate-simulations", type=int, default=8,
                        help="Por método, incluida la evaluación del programa inicial")
    parser.add_argument("--sampling-seed", type=int, default=2026)
    parser.add_argument("--out", type=Path, default=Path("artifacts/team_result.json"))
    args = parser.parse_args()
    if args.hybrid and args.no_qaoa:
        parser.error("--hybrid requiere QAOA; no combinar con --no-qaoa")
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
                                 seed=args.seed, max_evaluations=args.max_evaluations,
                                 encoding=args.encoding, hybrid=args.hybrid,
                                 candidate_proposals=args.candidate_proposals,
                                 max_candidate_simulations=args.max_candidate_simulations,
                                 sampling_seed=args.sampling_seed)
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
