"""
Motor de trafico (R3) - Qiskit Fall Fest 2026.

Port a Python de `simulate` del core.js, extendido a cruces en cadena
conectados por el eje EW (A -> B -> C ...). Para el reto usamos 2 cruces (A -> B).

Modelo (v2, con almacenamiento finito y spillback):
- Paso de 1 s, horizonte 1360 s (20 ciclos), ciclo 68 s: verde NS, 4 s todo-rojo,
  verde EW, 4 s todo-rojo.
- Cada cruce tiene 2 ejes (NS, EW) con una cola FIFO por eje.
- Llegadas externas uniformes y deterministas (acumulador fraccional), en veh/min.
- Servicio 0.5 veh/s solo en verde. El credito fraccional se reinicia en rojo, con cola
  vacia o cuando el destino aguas abajo esta lleno.
- Conexion: los autos que salen del EW del cruce i llegan a la cola EW del cruce i+1
  despues de travel_time_s segundos (ademas de las llegadas externas de i+1).
- Almacenamiento finito: el tramo EW que entra a cada cruce i guarda como maximo
  K_e = storage_vehicles autos, contando cola EW de i + autos en transito hacia i.
- Spillback: el EW del cruce i solo despacha si el tramo de i+1 tiene espacio
  (K_e - cola - en transito > 0). El ultimo cruce despacha a la salida sin limite.
- Desborde externo: las llegadas externas EW que no caben en su tramo esperan en una
  cola externa (backlog) FIFO fuera de la red y entran cuando hay espacio. Cuentan como
  llegadas, suman demora y entran en la conservacion. Las llegadas NS no tienen limite.
- Prioridad del corredor: mientras el EW del cruce anterior (i-1) esta en verde con cola,
  le reserva 1 lugar en el tramo de i (servicio <= 1 veh/s); el backlog externo de i solo
  usa el espacio que sobra. Sin esa reserva el backlog ocupa cada lugar que se libera y el
  cruce anterior casi no despacha.

Orden dentro de cada segundo, para cada cruce en orden A -> B -> ...:
  (a) llegadas externas (EW al backlog) y del backlog al tramo segun el espacio que
      deja la reserva del corredor,
  (b) aterrizan los autos en transito hacia el cruce,
  (c) servicio, con chequeo de espacio aguas abajo para el EW,
  (d) se acumula la demora (cola + backlog).

Costo de un cruce:  C = wD*D/60 + wP*Qmax/30 + wR*R/30
  D    = demora media del cruce (veh-s en cola y backlog / llegadas a sus colas)
  Qmax = cola maxima de un solo eje del cruce (dentro de la red, sin backlog)
  R    = cola residual del cruce al final (NS + EW + backlog externo EW)
blocked_s (segundos con verde EW, cola no vacia y destino lleno) se reporta, no entra al costo.
Costo total de una combinacion = suma de los costos de cada cruce.

Los parametros son ilustrativos: no representan una avenida real.
"""

import copy

AXES = ("NS", "EW")

# Parametros por defecto. Se pueden copiar y modificar (ver default_params()).
DEFAULT_PARAMS = {
    "horizon_s": 1360,                # 20 ciclos de 68 s
    "cycle_s": 68,
    "all_red_s": 4,
    "service_rate_vps": 0.5,          # vehiculos por segundo en verde
    "travel_time_s": 20,              # tiempo de viaje entre cruces consecutivos
    "storage_vehicles": 12,           # K_e: capacidad del tramo EW que entra a cada cruce
    "weights": {"delay": 1.0, "peak_queue": 0.6, "residual": 1.0},
    "intersections": [
        {"id": "A", "name": "Cruce A", "arrival_rate_vpm": {"NS": 18, "EW": 12}},
        {"id": "B", "name": "Cruce B", "arrival_rate_vpm": {"NS": 15, "EW": 14}},
    ],
    "plans": [
        {"id": 0, "name": "Balanced", "green_s": {"NS": 30, "EW": 30}},
        {"id": 1, "name": "NS priority", "green_s": {"NS": 40, "EW": 20}},
    ],
}


def default_params():
    """Copia profunda de los defaults (para no modificarlos por accidente)."""
    return copy.deepcopy(DEFAULT_PARAMS)


def phase(t, green, cycle, all_red):
    """Fase del semaforo en el segundo t: 'NS', 'EW' o 'CLEAR' (todo-rojo)."""
    s = t % cycle
    if s < green["NS"]:
        return "NS"
    if s < green["NS"] + all_red:
        return "CLEAR"
    if s < green["NS"] + all_red + green["EW"]:
        return "EW"
    return "CLEAR"


def cost_from_metrics(mean_delay_s, peak_queue, residual, weights):
    """C = wD*D/60 + wP*Qmax/30 + wR*R/30"""
    return (weights["delay"] * mean_delay_s / 60
            + weights["peak_queue"] * peak_queue / 30
            + weights["residual"] * residual / 30)


def simulate_chain(plan_ids, params, keep_history=False, initial_state=None):
    """
    Simula una cadena de cruces conectados por EW, en el orden de params['intersections'].

    plan_ids: lista con el id de plan de cada cruce (mismo orden que intersections).
    initial_state: solo para tests. Dict opcional con
        "t0": segundo de inicio (la simulacion corre de t0 a t0 + horizon_s),
        "queues": [{"NS": n, "EW": n}, ...] autos ya en cola en cada cruce,
        "in_transit": [{segundo_de_llegada: cantidad}, ...] autos viajando hacia cada cruce.
      Los autos iniciales no cuentan como llegadas.
    Devuelve un dict con metricas por cruce, metricas agregadas y costo total.
    """
    inters = params["intersections"]
    n = len(inters)
    assert len(plan_ids) == n, "un plan por cruce"
    plans_by_id = {p["id"]: p for p in params["plans"]}
    greens = [plans_by_id[pid]["green_s"] for pid in plan_ids]

    H = params["horizon_s"]
    cycle = params["cycle_s"]
    all_red = params["all_red_s"]
    mu = params["service_rate_vps"]
    tt = params["travel_time_s"]
    K = params["storage_vehicles"]
    w = params["weights"]

    # Chequeo: verde NS + rojo + verde EW + rojo debe dar el ciclo
    for g in greens:
        assert g["NS"] + g["EW"] + 2 * all_red == cycle, "el plan no cuadra con el ciclo"
    assert tt >= 1, "travel_time_s debe ser >= 1"
    assert K >= 1, "storage_vehicles debe ser >= 1"

    # Estado por cruce y eje. Las colas guardan el segundo de llegada de cada auto.
    queues = [{a: [] for a in AXES} for _ in range(n)]
    acc = [{a: 0.0 for a in AXES} for _ in range(n)]       # acumulador de llegadas
    credit = [{a: 0.0 for a in AXES} for _ in range(n)]    # credito de servicio
    rates = [{a: inters[i]["arrival_rate_vpm"][a] / 60 for a in AXES} for i in range(n)]

    arrived_ext = [{a: 0 for a in AXES} for _ in range(n)]   # llegadas externas
    arrived_link = [0] * n                                   # llegadas desde el cruce anterior (EW)
    served = [{a: 0 for a in AXES} for _ in range(n)]
    delay = [{a: 0 for a in AXES} for _ in range(n)]         # veh-s en cola (+ backlog en EW)
    peak = [{a: 0 for a in AXES} for _ in range(n)]
    min_queue = [{a: 0 for a in AXES} for _ in range(n)]     # para el test de no-negativos
    peak_occupancy = [0] * n                                 # max(cola EW + en transito) del tramo
    blocked = [0] * n                                        # segundos con spillback (solo reporte)

    # in_transit[i] = {segundo_de_llegada: cantidad} de autos viajando hacia el cruce i
    in_transit = [dict() for _ in range(n)]
    transit_n = [0] * n                                      # total en transito hacia el cruce i
    backlog = [[] for _ in range(n)]                         # cola externa EW fuera de la red (FIFO)

    t0 = 0
    if initial_state:
        t0 = initial_state.get("t0", 0)
        for i, qs in enumerate(initial_state.get("queues", [])):
            for a in AXES:
                queues[i][a] = [t0] * qs.get(a, 0)
        for i, tr in enumerate(initial_state.get("in_transit", [])):
            in_transit[i] = {int(s): k for s, k in tr.items()}
            transit_n[i] = sum(in_transit[i].values())

    def space(i):
        """Lugares libres en el tramo EW que entra al cruce i."""
        return K - len(queues[i]["EW"]) - transit_n[i]

    def corridor_reserve(i, t):
        """Lugares del tramo de i reservados al flujo que viene del EW de i-1."""
        if i == 0 or not queues[i - 1]["EW"]:
            return 0
        return 1 if phase(t, greens[i - 1], cycle, all_red) == "EW" else 0

    def downstream_full(i):
        """True si el EW del cruce i no puede despachar (el ultimo sale sin limite)."""
        return i + 1 < n and space(i + 1) <= 0

    history = []

    for t in range(t0, t0 + H):
        step = ({"t": t, "phases": [], "queues": [], "departures": [], "occupancy": [], "backlog": []}
                if keep_history else None)

        for i in range(n):
            ph = phase(t, greens[i], cycle, all_red)
            dep = {a: 0 for a in AXES}   # salidas en este segundo (para el test de "sin servicio en rojo")
            for a in AXES:
                q = queues[i][a]

                # (a) llegadas externas (acumulador fraccional, igual que core.js).
                #     Las EW pasan por el backlog y entran al tramo solo con el espacio
                #     que no esta reservado al corredor.
                acc[i][a] += rates[i][a]
                while acc[i][a] >= 1 - 1e-10:
                    acc[i][a] -= 1
                    (backlog[i] if a == "EW" else q).append(t)
                    arrived_ext[i][a] += 1
                if a == "EW":
                    while backlog[i] and space(i) > corridor_reserve(i, t):
                        q.append(backlog[i].pop(0))

                    # (b) aterrizan los autos en transito desde el cruce anterior
                    k = in_transit[i].pop(t, 0)
                    q.extend([t] * k)
                    transit_n[i] -= k
                    arrived_link[i] += k
                    peak_occupancy[i] = max(peak_occupancy[i], len(q) + transit_n[i])

                peak[i][a] = max(peak[i][a], len(q))

                # (c) servicio: solo si este eje tiene verde y, en EW, hay espacio aguas abajo
                if ph == a:
                    if a == "EW" and q and downstream_full(i):
                        blocked[i] += 1
                    credit[i][a] += mu
                    while credit[i][a] >= 1 and q and not (a == "EW" and downstream_full(i)):
                        credit[i][a] -= 1
                        q.pop(0)
                        served[i][a] += 1
                        dep[a] += 1
                        # el auto que sale del EW va al siguiente cruce
                        if a == "EW" and i + 1 < n:
                            arr_t = t + tt
                            in_transit[i + 1][arr_t] = in_transit[i + 1].get(arr_t, 0) + 1
                            transit_n[i + 1] += 1
                    if not q or (a == "EW" and downstream_full(i)):
                        credit[i][a] = 0.0
                else:
                    credit[i][a] = 0.0

                min_queue[i][a] = min(min_queue[i][a], len(q))
                # (d) demora: cada auto en cola (o en backlog EW) suma 1 s
                delay[i][a] += len(q) + (len(backlog[i]) if a == "EW" else 0)

            if keep_history:
                step["phases"].append(ph)
                step["queues"].append({a: len(queues[i][a]) for a in AXES})
                step["departures"].append(dep)
                step["occupancy"].append(len(queues[i]["EW"]) + transit_n[i])
                step["backlog"].append(len(backlog[i]))
        if keep_history:
            history.append(step)

    # ---- metricas por cruce ----
    per = []
    for i in range(n):
        arrivals_i = sum(arrived_ext[i].values()) + arrived_link[i]
        delay_i = sum(delay[i].values())
        mean_delay_i = delay_i / max(1, arrivals_i)
        peak_i = max(peak[i].values())
        resid_i = sum(len(queues[i][a]) for a in AXES) + len(backlog[i])
        per.append({
            "id": inters[i]["id"],
            "plan": plan_ids[i],
            "arrived_external": dict(arrived_ext[i]),
            "arrived_from_link": arrived_link[i],
            "served": dict(served[i]),
            "queue_end": {a: len(queues[i][a]) for a in AXES},
            "backlog_end": len(backlog[i]),
            "in_transit_end": transit_n[i],
            "min_queue": dict(min_queue[i]),
            "peak_by_axis": dict(peak[i]),
            "peak_occupancy": peak_occupancy[i],
            "blocked_s": blocked[i],
            "vehicle_seconds": delay_i,
            "mean_delay_s": mean_delay_i,
            "peak_queue": peak_i,
            "residual": resid_i,
            "cost": cost_from_metrics(mean_delay_i, peak_i, resid_i, w),
        })

    # ---- metricas agregadas de la combinacion (para mostrar) ----
    total_arrivals = sum(sum(p["arrived_external"].values()) + p["arrived_from_link"] for p in per)
    total_delay = sum(p["vehicle_seconds"] for p in per)

    return {
        "plans": list(plan_ids),
        "per_intersection": per,
        "metrics": {
            "mean_delay_s": total_delay / max(1, total_arrivals),
            "peak_queue": max(p["peak_queue"] for p in per),
            "residual": sum(p["residual"] for p in per),
            "blocked_s": sum(p["blocked_s"] for p in per),
        },
        "in_transit_end": sum(transit_n),
        "total_cost": sum(p["cost"] for p in per),
        "history": history if keep_history else None,
    }


def simulate_corridor(plans, params=None, keep_history=False):
    """
    Interfaz del reto (2 cruces A -> B).

    plans: dict como {"A": 0, "B": 1}
    params: dict de parametros (si es None se usan los defaults)
    """
    params = params or default_params()
    ids = [it["id"] for it in params["intersections"]]
    return simulate_chain([plans[i] for i in ids], params, keep_history)


def simulate_isolated(inter_index, plan_id, params=None):
    """Un cruce solo, sin trafico de entrada desde el anterior (para local_costs)."""
    params = copy.deepcopy(params or default_params())
    params["intersections"] = [params["intersections"][inter_index]]
    return simulate_chain([plan_id], params)


if __name__ == "__main__":
    r = simulate_corridor({"A": 0, "B": 0})
    for p in r["per_intersection"]:
        print(p["id"], "plan", p["plan"], "costo %.4f" % p["cost"],
              "D=%.2f Qmax=%d R=%d bloqueado=%ds"
              % (p["mean_delay_s"], p["peak_queue"], p["residual"], p["blocked_s"]))
    print("total", round(r["total_cost"], 4), r["metrics"])
