"""Referencia discreta: corredor unidireccional y transversal agregada por cruce."""

from collections import deque
from dataclasses import asdict, dataclass

import numpy as np

from simaphuru.models import Scenario

CYCLE_S = 68
CLEARANCE_S = 4
MAIN_GREENS = (30, 40)


def phase(t: int, choice: int) -> str:
    position = t % CYCLE_S
    green = MAIN_GREENS[choice]
    if position < green:
        return "principal"
    if green + CLEARANCE_S <= position < 60 + CLEARANCE_S:
        return "transversal"
    return "despeje"


def arrival_trace(scenario: Scenario, seed: int) -> np.ndarray:
    """Traza externa inmutable compartida entre todas las decisiones."""
    rng = np.random.default_rng(seed)
    counts = np.zeros((scenario.horizon_s, scenario.junctions + 1), dtype=int)
    accumulators = np.zeros(scenario.junctions + 1)
    for t in range(scenario.horizon_s):
        factor = scenario.peak_factor if scenario.peak_start_s <= t < scenario.peak_end_s else 1
        rates = np.array([scenario.main_veh_min] + [scenario.side_veh_min] * scenario.junctions)
        rates = rates * factor / 60
        if scenario.arrival_mode == "poisson":
            counts[t] = rng.poisson(rates)
        else:
            accumulators += rates
            counts[t] = np.floor(accumulators + 1e-10).astype(int)
            accumulators -= counts[t]
    counts.setflags(write=False)
    return counts


@dataclass
class SimulationResult:
    decision: tuple[int, ...]
    cost: float
    arrivals: int
    exited: int
    residual: int
    total_time_veh_s: int
    peak_waiting: list[int]
    blocked_seconds: list[int]
    history: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


def simulate(
    scenario: Scenario,
    decision: tuple[int, ...],
    trace: np.ndarray,
    *,
    record_history: bool = False,
) -> SimulationResult:
    if len(decision) != scenario.junctions or any(x not in (0, 1) for x in decision):
        raise ValueError("Se necesita una decisión binaria por cruce")
    if trace.shape != (scenario.horizon_s, scenario.junctions + 1):
        raise ValueError("La traza no coincide con el escenario")
    if np.any(trace < 0) or not np.all(np.isfinite(trace)) or not np.all(trace == np.floor(trace)):
        raise ValueError("Las llegadas deben ser enteros no negativos")
    n = scenario.junctions
    # Cada elemento es el instante mínimo de salida del enlace; incluye tránsito y espera.
    main = [deque() for _ in range(n)]
    side = [0] * n
    main_credit, side_credit = [0.0] * n, [0.0] * n
    external = arrivals = exited = total_time = 0
    peak, blocked, history = [0] * n, [0] * n, []
    for t, incoming in enumerate(trace):
        arrivals += int(incoming.sum())
        external += int(incoming[0])
        for i in range(n):
            side[i] += int(incoming[i + 1])
        admitted = min(external, scenario.storage_vehicles - len(main[0]))
        main[0].extend([t] * admitted)  # Entrada en la línea del primer cruce.
        external -= admitted
        phases = [phase(t, x) for x in decision]
        flows, side_flows = [0] * n, [0] * n
        for i in range(n):
            ready = sum(time <= t for time in main[i])
            room = scenario.storage_vehicles - len(main[i + 1]) if i + 1 < n else 1
            factor = 1.0
            for event in scenario.blockages:
                if event.junction == i and event.start_s <= t < event.start_s + event.duration_s:
                    factor = min(factor, event.capacity_factor)
            if phases[i] == "principal" and ready and room and factor:
                main_credit[i] += scenario.service_veh_s * factor
                flows[i] = min(int(main_credit[i] + 1e-10), ready, room)
                main_credit[i] -= flows[i]
            else:
                main_credit[i] = 0
            if phases[i] == "principal" and ready and (room == 0 or factor == 0):
                blocked[i] += 1
            if phases[i] == "transversal" and side[i]:
                side_credit[i] += scenario.service_veh_s
                side_flows[i] = min(int(side_credit[i] + 1e-10), side[i])
                side_credit[i] -= side_flows[i]
            else:
                side_credit[i] = 0
        # Todas las transferencias usan la misma fotografía del estado anterior.
        for i, flow in enumerate(flows):
            for _ in range(flow):
                main[i].popleft()
            side[i] -= side_flows[i]
            exited += side_flows[i]
        for i, flow in enumerate(flows):
            if i + 1 < n:
                main[i + 1].extend([t + scenario.travel_time_s] * flow)
            else:
                exited += flow
        for i in range(n):
            if not main[i]:
                main_credit[i] = 0
            if not side[i]:
                side_credit[i] = 0
        occupancy = [len(q) for q in main]
        waiting = [sum(time <= t for time in q) for q in main]
        residual = sum(occupancy) + sum(side) + external
        if arrivals != exited + residual:
            raise AssertionError("Violación de conservación global")
        if any(value > scenario.storage_vehicles for value in occupancy):
            raise AssertionError("Almacenamiento excedido")
        total_time += residual
        peak = [max(peak[i], waiting[i] + side[i]) for i in range(n)]
        if record_history:
            history.append(
                {
                    "t": t,
                    "phase": phases,
                    "main_occupancy": occupancy,
                    "main_waiting": waiting,
                    "side_queue": side.copy(),
                    "external_queue": external,
                    "arrivals": arrivals,
                    "exited": exited,
                    "main_flow": flows,
                    "side_flow": side_flows,
                }
            )
    divisor = max(1, arrivals)
    return SimulationResult(
        decision,
        total_time / (60 * divisor) + residual / divisor,
        arrivals,
        exited,
        residual,
        total_time,
        peak,
        blocked,
        history,
    )
