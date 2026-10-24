"""Adaptador explícito: motor R3 -> contrato compatible -> one-hot -> Qiskit."""

import copy
import hashlib
import itertools
import json
import platform
from dataclasses import asdict
from importlib.metadata import version
from time import perf_counter
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from model.chain import chain_params
from model.traffic import simulate_chain
from quantum.qubo import (
    build_one_hot,
    decode_one_hot,
    dynamic_programming,
    factor_cost,
    one_hot_index,
)
from simaphuru import __version__

UPSTREAM_COMMIT = "ee4eed52ba3438242aa213532c1eb5761ae5f70e"
TEAM_MODEL_VERSION = "team-ns-ew-v2"


class Rates(BaseModel):
    model_config = ConfigDict(extra="forbid")
    NS: float = Field(ge=0, le=120)
    EW: float = Field(ge=0, le=120)


class Intersection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    name: str
    arrival_rate_vpm: Rates


class Weights(BaseModel):
    model_config = ConfigDict(extra="forbid")
    delay: float = Field(ge=0, le=100)
    peak_queue: float = Field(ge=0, le=100)
    residual: float = Field(ge=0, le=100)


class Greens(BaseModel):
    model_config = ConfigDict(extra="forbid")
    NS: int = Field(ge=1)
    EW: int = Field(ge=1)


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Literal[0, 1]
    name: str
    green_s: Greens


class TeamParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    horizon_s: int = Field(ge=1, le=3600)
    cycle_s: int = Field(ge=4, le=300)
    all_red_s: int = Field(ge=1)
    service_rate_vps: float = Field(gt=0, le=1)
    travel_time_s: int = Field(ge=1, le=300)
    storage_vehicles: int = Field(ge=1, le=500)
    weights: Weights
    intersections: list[Intersection] = Field(min_length=2, max_length=5)
    plans: list[Plan] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def consistent(self):
        ids = [i.id for i in self.intersections]
        if len(set(ids)) != len(ids):
            raise ValueError("Identificadores de cruce duplicados")
        if [p.id for p in self.plans] != [0, 1]:
            raise ValueError("Orden de planes requerido: 0, 1")
        if any(p.green_s.NS + p.green_s.EW + 2 * self.all_red_s != self.cycle_s
               for p in self.plans):
            raise ValueError("Los verdes y despejes deben sumar el ciclo")
        return self


def default_team_params(n: int = 2) -> dict:
    if n not in (2, 3, 4, 5):
        raise ValueError("El adaptador admite de dos a cinco cruces")
    return TeamParams.model_validate(chain_params(n)).model_dump()


def team_fingerprint(params: dict) -> str:
    validated = TeamParams.model_validate(params).model_dump()
    payload = {"params": validated, "model_version": TEAM_MODEL_VERSION}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def params_from_payload(payload: dict) -> tuple[dict, list[str]]:
    """El JSON antiguo omite dos parámetros: se declaran y verifican, nunca se ocultan."""
    if payload.get("example") is not False or payload.get("schema_version") not in ("0.1", "0.2"):
        raise ValueError("Se requiere una salida real del motor con schema 0.1 o 0.2")
    inputs = payload["inputs"]
    if "params" in inputs:
        return TeamParams.model_validate(inputs["params"]).model_dump(), []
    params = default_team_params(2)
    for key in ("horizon_s", "cycle_s", "weights", "intersections", "plans"):
        params[key] = inputs[key]
    params["travel_time_s"] = inputs["link"]["travel_time_s"]
    params["storage_vehicles"] = inputs.get("storage_vehicles", params["storage_vehicles"])
    notes = ["schema 0.1 omite all_red_s y service_rate_vps: se heredan 4 s y 0.5 veh/s "
             "de model/traffic.py; todos los costos deben reproducirse antes de integrarlo"]
    return TeamParams.model_validate(params).model_dump(), notes


def verify_imported_payload(payload: dict, result: dict) -> None:
    """Rechaza figuras que no correspondan a la simulación mostrada en la interfaz."""
    old = {tuple(sorted(c["plans"].items())): c["total_cost"]
           for c in payload["model"]["combinations"]}
    new = {tuple(sorted(c["plans"].items())): c["total_cost"]
           for c in result["model"]["combinations"]}
    if old.keys() != new.keys() or any(abs(old[k] - new[k]) > 1e-5 for k in old):
        raise ValueError("El JSON importado no reproduce los costos del motor actual; no se mezcla con su historial")
    ids = [i["id"] for i in result["inputs"]["intersections"]]
    for c in result["model"]["combinations"]:
        plans = c["plans"]
        factor = sum(payload["model"]["local_costs"][i][plans[i]] for i in ids)
        factor += sum(payload["model"]["pair_costs"][f"{a}-{b}"][plans[a]][plans[b]]
                      for a, b in zip(ids, ids[1:]))
        if abs(factor - c["approx_cost"]) > 1e-5:
            raise ValueError("Los factores locales/pares importados no corresponden al escenario")


def network_counts(result: dict) -> dict:
    per = result["per_intersection"]
    external = sum(sum(p["arrived_external"].values()) for p in per)
    exited = sum(p["served"]["NS"] for p in per) + per[-1]["served"]["EW"]
    queued = sum(p["residual"] for p in per)
    transit = result["in_transit_end"]
    if external != exited + queued + transit:
        raise ValueError("El motor no conserva vehículos a nivel de red")
    return {"external_demand": external, "network_exited": exited,
            "queued_end": queued, "in_transit_end": transit,
            "network_pending": queued + transit, "conservation_error": 0}


def _subset(params: dict, indices: list[int]) -> dict:
    subset = copy.deepcopy(params)
    subset["intersections"] = [subset["intersections"][i] for i in indices]
    return subset


def run_team_experiment(params: dict, *, qaoa: bool = True, depth: int = 1,
                        seed: int = 7, max_evaluations: int = 60) -> dict:
    started = perf_counter()
    params = TeamParams.model_validate(params).model_dump()
    n = len(params["intersections"])
    ids = [i["id"] for i in params["intersections"]]
    local = [[simulate_chain([k], _subset(params, [i]))["total_cost"]
              for k in (0, 1)] for i in range(n)]
    pairs = [
        [[simulate_chain([a, b], _subset(params, [i, i + 1]))["total_cost"]
          - local[i][a] - local[i + 1][b] for b in (0, 1)] for a in (0, 1)]
        for i in range(n - 1)
    ]
    model_started = perf_counter()
    combinations = []
    raw = {}
    for plans in itertools.product((0, 1), repeat=n):
        r = simulate_chain(list(plans), params)
        raw[plans] = r
        cost = float(r["total_cost"])
        combinations.append({
            "plans": dict(zip(ids, plans)), "total_cost": cost,
            "approx_cost": factor_cost(local, pairs, plans),
            "metrics": r["metrics"], "network": network_counts(r),
            "per_intersection_cost": {p["id"]: p["cost"] for p in r["per_intersection"]},
            "blocked_s": {p["id"]: p["blocked_s"] for p in r["per_intersection"]},
            "one_hot_index": one_hot_index(plans),
        })
    enumeration_ms = (perf_counter() - model_started) * 1000
    costs = np.array([c["total_cost"] for c in combinations])
    approx = np.array([c["approx_cost"] for c in combinations])
    best = int(np.argmin(costs))
    qubo, proof = build_one_hot(local, pairs)
    dp_started = perf_counter()
    dp_plans, dp_cost = dynamic_programming(local, pairs)
    dp_ms = (perf_counter() - dp_started) * 1000
    dp_real = raw[tuple(dp_plans)]["total_cost"]
    selected = {(0,) * n, tuple(combinations[best]["plans"].values()), tuple(dp_plans)}
    quantum = None
    if qaoa:
        from simaphuru.quantum import solve_qaoa

        quantum_started = perf_counter()
        quantum = solve_qaoa(qubo, None, depth=depth, seed=seed, max_evaluations=max_evaluations)
        quantum["runtime_ms"] = (perf_counter() - quantum_started) * 1000
        probs = np.array(quantum["probabilities_by_index"])
        valid_indices = [c["one_hot_index"] for c in combinations]
        valid_probs = probs[valid_indices]
        feasible_probability = float(valid_probs.sum())
        choice = int(np.argmax(valid_probs))
        chosen_plans = list(combinations[choice]["plans"].values())
        selected.add(tuple(chosen_plans))
        quantum.update({
            "feasible_probability": feasible_probability,
            "invalid_probability": max(0.0, 1 - feasible_probability),
            "conditional_expected_original": float(valid_probs @ costs / feasible_probability)
                if feasible_probability > 1e-12 else None,
            "conditional_original_gap": float(valid_probs @ costs / feasible_probability - costs.min())
                if feasible_probability > 1e-12 else None,
            "original_optimal_probability": float(valid_probs[np.isclose(
                costs, costs.min(), rtol=1e-9, atol=1e-9)].sum()),
            "most_likely_plans": decode_one_hot(quantum["most_likely_index"], n),
            "representative_rule": "plan factible de mayor probabilidad; no es garantía de óptimo",
            "representative_plans": dict(zip(ids, chosen_plans)),
            "representative_original_cost": float(costs[choice]),
            "valid_probabilities": [
                {"plans": c["plans"], "probability": float(p),
                 "original_cost": c["total_cost"], "one_hot_index": c["one_hot_index"]}
                for c, p in zip(combinations, valid_probs)
            ],
        })
    histories = {}
    for plans in sorted(selected):
        r = simulate_chain(list(plans), params, keep_history=True)
        network_counts(r)
        label = " · ".join(f"{i}={k}" for i, k in zip(ids, plans))
        histories[label] = {"plans": dict(zip(ids, plans)), "total_cost": r["total_cost"],
                            "history": r["history"], "network": network_counts(r)}
    return {
        "schema_version": "0.2", "compatible_fields": "0.1 locales/pares/combinations/classical",
        "example": False, "model_version": TEAM_MODEL_VERSION,
        "upstream_commit": UPSTREAM_COMMIT, "config_hash": team_fingerprint(params),
        "inputs": {**params, "params": params, "arrival_mode": "uniform_deterministic",
                   "links": [{"from": ids[i], "to": ids[i + 1],
                              "travel_time_s": params["travel_time_s"]} for i in range(n - 1)]},
        "model": {"local_costs": dict(zip(ids, local)),
                  "pair_costs": {f"{ids[i]}-{ids[i+1]}": pairs[i] for i in range(n - 1)},
                  "combinations": combinations},
        "classical": {"method": "brute_force_full_simulator", "optimal_plans": combinations[best]["plans"],
                      "optimal_x": [(one_hot_index(tuple(combinations[best]["plans"].values())) >> q) & 1
                                    for q in range(2 * n)],
                      "optimal_cost": float(costs[best]), "runtime_ms": enumeration_ms,
                      "baseline_cost": float(costs[0]), "uniform_feasible_expected_cost": float(costs.mean())},
        "pairwise_classical": {"method": "dynamic_programming", "optimal_plans": dict(zip(ids, dp_plans)),
                               "optimal_approx_cost": dp_cost, "original_cost": dp_real,
                               "original_regret": float(dp_real - costs.min()), "runtime_ms": dp_ms},
        "audit": {"max_absolute_error": float(np.max(np.abs(costs - approx))),
                  "mean_absolute_error": float(np.mean(np.abs(costs - approx))),
                  "exact_representation": bool(np.allclose(costs, approx, rtol=1e-9, atol=1e-9)),
                  "decision_regret": float(dp_real - costs.min()), "one_hot": proof},
        "quantum": quantum, "qubo": asdict(qubo), "histories": histories,
        "bit_order": "x_A0,x_A1,x_B0,x_B1,…; variable q = qubit q = peso 2**q; ket Qiskit invertido",
        "versions": {"simaphuru": __version__, "qiskit": version("qiskit"), "python": platform.python_version()},
        "optimizer_seed": seed, "elapsed_s": perf_counter() - started,
        "claims": {"synthetic": True, "empirically_calibrated": False,
                   "finite_storage": True, "spillback": True,
                   "quantum_advantage_demonstrated": False},
    }
