*Nota posterior (24/10, noche): la interfaz ahora abre en binaria; la CLI sigue en one-hot.*

# Validación de la mejora para la final

Fecha: 24/10/2026. Base: `09ed6d0` más los cambios locales de la rama `rol2/final-codificacion-binaria`, paquete 0.3.0. Los JSON registran `git_dirty=true` y hashes SHA-256 de los módulos ejecutados; no atribuir estas cifras a la base sin cambios.

## Protocolo

- Mismo motor `team-ns-ew-v2`, catálogo, factores y tablas físicas, comprobados entre codificaciones.
- Tres escenarios sintéticos: predeterminado; tasas externas reducidas a la mitad; almacenamiento K=4. Dos tamaños: N=2 y N=5.
- Semillas de entrenamiento 3, 7 y 11. Tráfico determinista; estas semillas no representan días de tráfico independientes.
- QAOA p=3, tres reinicios, máximo 300 evaluaciones por reinicio, mismo optimizador Nelder–Mead. Presupuestos máximos iguales; se registra el número realmente utilizado.
- Probabilidades ideales calculadas con Statevector, sin hardware ni shots. Orden de codificaciones alternado entre semillas.
- 36 corridas, 18 comparaciones emparejadas. La binaria tuvo mayor P(óptimo físico) en las 18 comparaciones ensayadas. Tres semillas no prueban superioridad general.
- 60 pruebas locales pasaron. Incluyen energías binarias y one-hot con factores asimétricos, Ising, mismos costos e historiales, importación, invalidación de interfaz, escenario vacío y pesos cero. Ruff sin errores. Además se ejecutó una comprobación CLI binaria de cinco cruces.

## Caso predeterminado, semilla 7

| Cruces | Codificación | Qubits | P(óptimo físico) | P(programa válido) | E[C dado válido] | Plan más probable | Costo de ese plan |
|---|---|---:|---:|---:|---:|---|---:|
| 2 | one_hot | 4 | 28.3615% | 97.0694% | 21.786309 | 10 | 17.912639 |
| 2 | binary | 2 | 99.8965% | 100.0000% | 17.919105 | 10 | 17.912639 |
| 5 | one_hot | 10 | 3.4371% | 98.7935% | 55.373277 | 11001 | 52.933018 |
| 5 | binary | 5 | 10.0352% | 100.0000% | 51.813498 | 11001 | 52.933018 |

En dos cruces, ambos registros representan el costo físico exactamente hasta redondeo. En cinco, ambos mantienen el error máximo de aproximación 10,540358986 y pérdida de decisión de F de 4,302542457 (8,85%). El óptimo físico cuesta 48,630475554 y usa 11100; el óptimo por pares y el plan más probable de ambas codificaciones con semilla 7 usan 11001 y cuestan 52,933018011.

La binaria no recupera automáticamente el óptimo físico de cinco cruces como moda. Sí mejora en estos ensayos la probabilidad del óptimo físico y el costo físico esperado de la distribución.

## Dispersión de P(óptimo) entre semillas

| Escenario | Cruces | Codificación | Media | Mínimo–máximo | E[C dado válido] media |
|---|---:|---|---:|---|---:|
| default | 2 | one_hot | 24.67% | 21.09%–28.36% | 22.1889 |
| default | 2 | binary | 94.97% | 85.02%–99.99% | 18.0300 |
| default | 5 | one_hot | 3.07% | 2.89%–3.44% | 55.5496 |
| default | 5 | binary | 9.83% | 7.93%–11.52% | 51.7583 |
| half_demand | 2 | one_hot | 16.71% | 14.65%–19.67% | 1.5212 |
| half_demand | 2 | binary | 51.92% | 51.64%–52.46% | 1.4062 |
| half_demand | 5 | one_hot | 3.72% | 2.83%–4.40% | 20.9740 |
| half_demand | 5 | binary | 14.45% | 13.10%–15.16% | 20.7923 |
| limited_storage | 2 | one_hot | 23.77% | 22.45%–25.84% | 29.7571 |
| limited_storage | 2 | binary | 71.16% | 66.49%–78.89% | 25.8698 |
| limited_storage | 5 | one_hot | 3.04% | 2.88%–3.31% | 64.6096 |
| limited_storage | 5 | binary | 6.96% | 4.87%–9.39% | 58.1999 |

## Cómo reproducir

```sh
python -m pytest -q
python -m ruff check .
python -m quantum.run_qaoa --n 2 --encoding binary --out artifacts/binary_two.json
python -m quantum.benchmark_encodings --out artifacts/final_encodings.json
```

El último comando genera JSON y CSV. `artifacts/` permanece ignorado salvo las cuatro referencias históricas: este barrido no reemplaza esas referencias. La interfaz y la CLI siguen seleccionando one-hot por defecto para reproducirlas.

Para una pasada breve del protocolo:

```sh
python -m quantum.benchmark_encodings --n 2 --seeds 7 --scenarios default --max-evaluations 8 --out artifacts/smoke_encodings.json
```

## Lectura científica y límites

- La mejora principal es cambiar la representación: la binaria evita qubits redundantes y penalizaciones para exactamente dos programas. No cambia el tráfico ni elimina interacciones físicas omitidas por F.
- En el caso predeterminado de dos cruces, P(óptimo) binaria varía de 85,02% a 99,99% entre las tres semillas; el 99,90% de la demo no es una garantía para cualquier entrenamiento.
- Factibilidad binaria significa elegir exactamente un programa del catálogo por cruce, no satisfacer condiciones de un modelo urbano que todavía no representamos.
- No se compara ventaja cuántica: la enumeración física y la programación dinámica siguen resolviendo sus respectivos problemas exactamente.
- Los tiempos medidos pertenecen al simulador clásico de circuitos. La etapa QAOA excluye construir factores; el total incluye la enumeración para auditoría. No son un benchmark de rendimiento repetido ni una predicción de latencia en QPU.
- La esperanza física one-hot descarta estados inválidos. Se informa junto con su masa factible; no esconder los rechazos en una comparación de resultados prácticos.
- La selección híbrida de candidatos se añadió después y se documenta en `HYBRID_VALIDATION.md`. No se implementa warm-start del estado cuántico, demanda temporal ni buses.
