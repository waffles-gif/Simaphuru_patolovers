import argparse
import json
from pathlib import Path

from simaphuru.experiment import run_experiment
from simaphuru.models import load_scenario


def main():
    parser = argparse.ArgumentParser(description="Simaphuru: tráfico, QUBO y QAOA local")
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--qaoa", action="store_true")
    parser.add_argument("--depth", type=int, choices=[1, 2], default=1)
    parser.add_argument("--output", type=Path, default=Path("artifacts/experiment.json"))
    args = parser.parse_args()
    result = run_experiment(
        load_scenario(args.scenario), seed=args.seed, qaoa=args.qaoa, depth=args.depth
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "config_hash": result["config_hash"],
                "exact_minimum": result["exact_minimum"],
                "max_qubo_error": result["audit"]["max_absolute_error"],
                "qaoa_original_gap": result["qaoa"]["original_gap"] if result["qaoa"] else None,
                "elapsed_s": result["elapsed_s"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
