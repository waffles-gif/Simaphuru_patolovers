"""Orquestación compartida por CLI y Streamlit, con huella de configuración."""

import platform
from dataclasses import asdict
from importlib.metadata import version
from time import perf_counter

import numpy as np

from simaphuru import __version__
from simaphuru.models import MODEL_VERSION, Scenario, decision_label, decision_vector
from simaphuru.qubo import audit, from_costs
from simaphuru.simulation import arrival_trace, simulate


def run_experiment(
    scenario: Scenario,
    *,
    seed: int = 7,
    qaoa: bool = False,
    depth: int = 1,
    max_evaluations: int = 60,
) -> dict:
    started = perf_counter()
    trace = arrival_trace(scenario, seed)
    evaluations = []
    for index in range(2**scenario.junctions):
        result = simulate(scenario, decision_vector(index, scenario.junctions), trace)
        evaluations.append(
            {
                "index": index,
                "decision_id": decision_label(index, scenario.junctions),
                **{k: v for k, v in result.to_dict().items() if k != "history"},
            }
        )
    costs = [r["cost"] for r in evaluations]
    qubo = from_costs(costs)
    audit_result = audit(qubo, costs)
    quantum_result = None
    if qaoa:
        from simaphuru.quantum import solve_qaoa

        quantum_result = solve_qaoa(
            qubo, costs, depth=depth, seed=seed, max_evaluations=max_evaluations
        )
    selected = {0, audit_result["exact_index"], audit_result["qubo_index"]}
    if quantum_result:
        selected.add(quantum_result["most_likely_index"])
    histories = {}
    for index in sorted(selected):
        result = simulate(
            scenario, decision_vector(index, scenario.junctions), trace, record_history=True
        )
        histories[decision_label(index, scenario.junctions)] = result.history
    true = np.asarray(costs)
    return {
        "schema_version": "1.0",
        "model_version": MODEL_VERSION,
        "config_hash": scenario.fingerprint(seed),
        "seed": seed,
        "scenario": scenario.model_dump(mode="json"),
        "versions": {
            "simaphuru": __version__,
            "python": platform.python_version(),
            "qiskit": version("qiskit"),
        },
        "bit_order": "decision_id=C1…Cn; Ci+1=qubit i=bit 2**i; inverse del ket Qiskit",
        "evaluations": evaluations,
        "qubo": asdict(qubo),
        "audit": audit_result,
        "qaoa": quantum_result,
        "histories": histories,
        "baseline_cost": float(true[0]),
        "exact_minimum": float(true.min()),
        "elapsed_s": perf_counter() - started,
        "claims": {
            "synthetic": True,
            "empirically_calibrated": False,
            "quantum_advantage_demonstrated": False,
        },
    }
