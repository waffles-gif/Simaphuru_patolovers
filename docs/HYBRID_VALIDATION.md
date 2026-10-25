# Validación del híbrido con candidatos verificados

24/10/2026. Paquete/schema 0.3, motor físico `team-ns-ew-v2`. Esta capa se añadió tras la elección de Rafael y se ejecutó sobre la misma base local de la final.

## Qué hace y qué no hace

Parte del programa obtenido por programación dinámica del costo por pares. El selector recibe ese programa, parámetros y probabilidades QAOA; **no recibe la tabla exhaustiva ni el óptimo físico**. Muestrea candidatos y evalúa cada programa nuevo con `simulate_chain`. Conserva siempre el inicial si no hay mejora. La tabla exhaustiva solo permite medir después la distancia al óptimo. La aplicación completa todavía la calcula para auditoría; no es un flujo de producción que haya eliminado ese costo.

Esta es selección híbrida verificada, no warm-start del circuito. El estado QAOA sigue empezando desde la superposición uniforme. El muestreo posterior es clásico sobre probabilidades ideales, no mediciones en una QPU.

## Protocolo

- Tres escenarios sintéticos: predeterminado, media demanda y almacenamiento K=4; N=2 y N=5.
- QAOA binaria p=3, semilla de entrenamiento 7, tres reinicios y hasta 300 evaluaciones por reinicio. Entrenada una vez por escenario/tamaño.
- Semillas de muestreo 3,7,11,2026. No cambian la demanda ni constituyen observaciones empíricas independientes.
- Por método, hasta 32 propuestas y 8 simulaciones físicas, incluida la inicial. Cachés independientes. Propuestas duplicadas/one-hot inválidas consumen intentos, sin otra simulación.
- Controles: candidatos uniformes y búsqueda local de uno/dos bits desde el mismo inicio. La búsqueda local usa costos ya evaluados y puede terminar antes.
- Límites iguales no significan igual tiempo total ni igual número efectivo de evaluaciones. El híbrido requiere además entrenamiento QAOA; preparar los factores y obtener el inicio clásico también tiene costo.
- 24 casos escenario/tamaño/muestreo, 72 búsquedas verificadas, más seis entrenamientos compartidos para generar las distribuciones.

## Caso predeterminado de cinco cruces, muestreo 2026

Inicio por pares: **11001**, costo **52,933018011**. Óptimo exhaustivo: **11100**, costo **48,630475554**.

| Método | Programa final | Costo físico | Mejora desde inicio | Simulaciones físicas | Propuestas |
|---|---|---:|---:|---:|---:|
| qaoa_candidates | 11100 | 48.630476 | 4.302542 | 8 | 32 |
| uniform_candidates | 11100 | 48.630476 | 4.302542 | 8 | 32 |
| local_search | 11100 | 48.630476 | 4.302542 | 8 | 7 |

Los tres métodos encuentran el óptimo en este caso. El descenso de costo desde 52,9330 es **8,13%** respecto de ese inicio. No confundirlo con la pérdida de 8,85% del inicio respecto del óptimo: usan denominadores diferentes. **No se atribuye esta mejora exclusivamente al componente cuántico.**

## Resultados de cinco cruces entre cuatro semillas de muestreo

| Escenario | Método | Costo inicial | Costo final medio | Óptimo encontrado | Simulaciones efectivas medias |
|---|---|---:|---:|---:|---:|
| default | qaoa_candidates | 52.933018 | 48.630476 | 4/4 | 7.50 |
| default | uniform_candidates | 52.933018 | 49.578775 | 2/4 | 8.00 |
| default | local_search | 52.933018 | 48.630476 | 4/4 | 8.00 |
| half_demand | qaoa_candidates | 23.527184 | 16.827048 | 4/4 | 7.75 |
| half_demand | uniform_candidates | 23.527184 | 17.106684 | 1/4 | 8.00 |
| half_demand | local_search | 23.527184 | 16.827048 | 4/4 | 8.00 |
| limited_storage | qaoa_candidates | 56.341200 | 56.167976 | 4/4 | 7.25 |
| limited_storage | uniform_candidates | 56.341200 | 56.254588 | 2/4 | 8.00 |
| limited_storage | local_search | 56.341200 | 56.167976 | 4/4 | 8.00 |

En los doce casos de cinco cruces: híbrido **12/12**, búsqueda local **12/12**, uniforme **5/12**. La búsqueda local iguala la calidad del híbrido sin entrenar QAOA. El resultado demuestra la utilidad de verificar propuestas en el simulador completo y la mejora sobre el inicio por pares; no demuestra ventaja cuántica ni que la búsqueda clásica local falle.

En dos cruces el inicio DP ya es óptimo en los escenarios ensayados; ningún método puede mejorarlo bajo el mismo objetivo. Incluir esos casos aumenta artificialmente una cifra global de éxito, por lo que el análisis principal anterior separa cinco cruces.

## Pruebas y reproducción

60 pruebas locales pasaron y Ruff pasó. La capa híbrida se prueba con candidatos peores, duplicados, estados one-hot inválidos, distribuciones incompatibles, límite de una sola simulación inicial, reproducibilidad, correspondencia de costos e historiales y control de presupuesto en Streamlit. Se cuenta cada llamada nueva a la física para evitar usar silenciosamente la tabla exhaustiva.

```sh
python -m pytest -q
python -m quantum.run_qaoa --n 5 --encoding binary --hybrid --out artifacts/hybrid_five.json
python -m quantum.benchmark_hybrid --out artifacts/final_hybrid.json
```

La CLI admite `--candidate-proposals`, `--max-candidate-simulations` y `--sampling-seed`. En Streamlit: cinco cruces, binaria, activar «Comparar búsqueda híbrida», ejecutar y abrir «Híbrido verificado». JSON/CSV incluyen trazas, presupuesto, versiones y hashes de fuente.

## Límites

No hay calibración de Lima, demanda temporal, buses, hardware cuántico ni validación de generalización. El presupuesto limita la búsqueda de candidatos, no toda la preparación del experimento. Reducir el costo compuesto no garantiza disminuir cada cola o cada segundo de bloqueo. Los tiempos del selector excluyen el entrenamiento y no deben presentarse como tiempos totales comparables.
