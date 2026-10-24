# Simaphuru · Equipo patolovers

> Qiskit Fall Fest 2026 · Categoría: Algoritmos y aplicaciones

**[Una frase que diga qué hace el proyecto. Ej.: "Elegimos el plan de semáforos de dos cruces conectados con QAOA en Qiskit y lo comparamos con la solución exacta."]**

## Equipo

| Rol | Nombre | Qué hizo |
|---|---|---|
| R1 · Evidencia y modelo físico | Rafael Chamayo | [completar] |
| R2 · QUBO y Qiskit | [nombre] | [completar] |
| R3 · Motor de tráfico | [nombre] | [completar] |
| R4 · Interfaz e integración | [nombre] | [completar] |

## Problema

[2–3 líneas. Qué pasa en el tráfico real y por qué elegir bien los tiempos de verde importa. Si citan un dato, pongan la fuente.]

## Solución

[2–3 líneas. Qué decide el sistema, cómo lo convierte en un QUBO y cómo lo resuelve.]

Funcionalidades:
- [ej.: ajustar llegadas por cruce y pesos del costo]
- [ej.: ver la simulación de colas de cada plan]
- [ej.: comparar QAOA contra la solución exacta]

## Formulación

- **Variables:** `x_{c,k} = 1` si el cruce `c` usa el plan `k` (one-hot).
- **Restricción:** cada cruce usa exactamente un plan: `Σ_k x_{c,k} = 1`.
- **Costo:** costo local de cada cruce + costo de interacción entre cruces vecinos.
- **QUBO:** `costo + P · Σ_c (Σ_k x_{c,k} − 1)²`, con `P = [valor]` elegido porque [razón].
- **Qubits:** [número] · **Capas QAOA (p):** [valor] · **Optimizador:** [nombre]

## Resultados

| Método | Mejor costo | ¿Cumple restricciones? | Prob. del óptimo | Tiempo |
|---|---|---|---|---|
| Exacto (fuerza bruta) | [ ] | Sí | — | [ ] |
| QAOA p=1 | [ ] | [ % factibles ] | [ ] | [ ] |
| QAOA p=2 | [ ] | [ % factibles ] | [ ] | [ ] |

[Gráfico de comparación: `docs/results.png`]

## Limitaciones

- Es un modelo pequeño y simplificado; los parámetros son ilustrativos, no calibrados con datos reales.
- A este tamaño, el método clásico es más rápido. No afirmamos ventaja cuántica.
- [Otra limitación que encuentren: ruido, número de qubits, etc.]

## Cómo correrlo

```bash
pip install -r requirements.txt
python quantum/run_qaoa.py        # [ajustar al nombre real]
# Interfaz: abrir web/index.html en el navegador
```

## Estructura

```
model/     motor de tráfico y enumeración clásica (R3)
quantum/   QUBO y QAOA en Qiskit (R2)
web/       interfaz y demo (R4)
docs/      fuentes, parámetros, resultados y PPT (R1)
data/      JSON que se pasan entre módulos (ver data/example_result.json)
```

## Demo

- Video: [link]
- Presentación: [link]

## Siguientes pasos

- [ej.: escalar a 5 cruces]
- [ej.: correr en hardware real de IBM]
