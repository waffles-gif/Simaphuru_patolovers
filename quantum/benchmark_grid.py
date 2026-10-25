"""Escala la optimización a una grilla de filas independientes (cadenas EW)."""

import argparse
import json
from pathlib import Path

from simaphuru.grid import run_grid


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=40)
    parser.add_argument("--cols", type=int, default=25)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--no-qaoa", action="store_true", help="Omitir QAOA por bloques")
    parser.add_argument("--out", type=Path, default=Path("artifacts/grid_1000.json"))
    args = parser.parse_args()

    result = run_grid(args.rows, args.cols, qaoa=not args.no_qaoa, seed=args.seed)
    result["backend"] = "Statevector, bloques de 5 qubits"
    result["note"] = ("filas independientes: el eje NS no tiene acoplamiento en el motor actual; "
                      "datos sintéticos; sin QPU")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    for name, total in result["totals"].items():
        print(f"{name:13s} QUBO {total['qubo']:12.3f} | real {total['real']:12.3f} | "
              f"{result['times_s'][name]:.2f} s")
    print("Guardado en", args.out)


if __name__ == "__main__":
    main()
