# Contratos de datos

## Integración predeterminada: motor del equipo, schema 0.2

`TeamParams` en `simaphuru/team.py` valida las entradas del motor R3: segundos, veh/min y veh/s, identificadores únicos, dos planes 0/1 y suma de verdes/despejes igual al ciclo. La opción de dos cruces usa cuatro variables one-hot: `x_A0,x_A1,x_B0,x_B1`. En cinco, son diez variables. La variable q corresponde al qubit q y al peso `2**q`; la impresión de kets Qiskit invierte ese orden visual. Ejemplo A=1,B=0: vector `[0,1,1,0]`, índice 6.

La salida 0.2 conserva los campos de integración `inputs`, `model.local_costs`, `model.pair_costs`, `model.combinations` y `classical` de 0.1, y añade parámetros completos sin redondear, huella, versión, auditoría, `quantum` e historiales. `quantum` es null si no se solicita QAOA. `example=false` significa resultado calculado; los parámetros siguen siendo sintéticos. No se convierte automáticamente a schema 1.0.

`config_hash` depende de TODOS los parámetros y de `team-ns-ew-v2`. La vista invalida resultados al cambiar también semilla del optimizador, profundidad o activación QAOA. El historial se regenera desde los mismos parámetros y planes. `upstream_commit` identifica la base auditada; la versión del paquete identifica la adaptación.

### Almacenamiento finito y spillback (`team-ns-ew-v2`)

- `storage_vehicles` (K_e, vehículos, default 12) es la capacidad del tramo EW que entra a cada cruce i. Ocupación = cola EW de i + autos en tránsito hacia i; nunca supera K_e.
- Spillback: el EW de i solo despacha si el tramo de i+1 tiene espacio (K_e − cola − tránsito > 0). El último cruce sale sin límite. Si el destino está lleno no sale nadie aunque haya verde, y el crédito fraccional de servicio se reinicia.
- Desborde externo: las llegadas externas EW que no caben esperan en un backlog FIFO fuera de la red. Cuentan en `arrived_external`, suman veh-s a la demora y entran al balance. NS no tiene límite.
- Orden por segundo y por cruce (A → B → …): llegadas externas y backlog → aterrizan los autos en tránsito → servicio con chequeo aguas abajo → demora (cola + backlog).
- El costo no cambia: C = wD·D/60 + wP·Qmax/30 + wR·R/30. `blocked_s` por cruce (segundos con verde EW, cola no vacía y destino lleno) es solo de reporte. Por cruce también se publican `backlog_end`, `in_transit_end` y `peak_occupancy`; `metrics.blocked_s` suma los cruces.
- Defaults de R1 (`parametros.csv`): horizonte 1360 s (20 ciclos), viaje 20 s, K_e = 12. Siguen siendo sintéticos.

Las probabilidades siguen el índice one-hot de 16/1024 estados, incluidos los inválidos. `feasible_probability` es la suma de estados con un plan por cruce; `original_optimal_probability` no está condicionada. `conditional_expected_original` promedia solo estados factibles y se publica junto a esa masa. No se define costo de tráfico para un estado inválido. `representative_plans` usa el candidato factible de mayor probabilidad, no una búsqueda oculta del óptimo clásico.

La CLI acepta el JSON 0.1 de R3 y comprueba sus combinaciones y factores frente al motor antes de ejecutar QAOA. Los campos ausentes `all_red_s=4` y `service_rate_vps=0.5` se heredan explícitamente del motor y se anotan en `import_notes`. Si `inputs.storage_vehicles` falta (JSON generado con v1), se hereda K_e = 12; como v1 no tenía almacenamiento finito, sus costos no se reproducen y el JSON se rechaza. Si no se reproducen los costos dentro de 1e-5, se rechaza la integración. La tolerancia cubre redondeo a seis decimales, no permite mezclar modelos físicos distintos. El archivo ficticio `example_result.json` se rechaza.

`network_pending` incluye colas, backlog externo y tránsito. `metrics.residual` = colas NS/EW + backlog externo EW al final (en v1 era solo colas). `metrics.peak_queue` sigue siendo la cola máxima de un eje dentro de la red, sin backlog. La demora original por llegada a colas no es tiempo de viaje global por vehículo único. No renombrar esas métricas como equivalentes.

## Vista experimental: schema 1.0

Los apartados siguientes se refieren exclusivamente al flujo anterior, de un bit por cruce y costo diferente. Sus claves `qaoa` y `scenario` no se intercambian con `quantum` e `inputs` de la integración 0.2.

## Borrador inicial del equipo

El archivo raíz `example_result.json` se conserva con schema 0.1, one-hot y valores expresamente ficticios. No se mezcla con schema 1.0 ni se interpreta como experimento real. El README original se conserva en `docs/TEAM_DRAFT.md`.

## Entradas

`Scenario` y `Blockage` en `simaphuru/models.py` son el contrato ejecutable. Las unidades están en los nombres: segundos, veh/min para llegadas y veh/s para servicio. El paso es fijo de un segundo. No introducir m/min o veh/h sin conversión y documentación.

Todo escenario incluye `schema_version`, `scenario_id` y `provenance`. Cada nuevo dato real debe añadir su fuente, fecha, unidad, ámbito y condición en un documento de datos. No quitar la etiqueta sintética hasta validar el conjunto.

`arrival_trace` devuelve un arreglo entero, no negativo e inmutable, con columnas: principal exterior y una transversal por cruce. Lo utilizan todas las decisiones sin volver a sortear llegadas.

## Decisiones

El vector `(x0,…,xn−1)` sigue C1…Cn. El índice de tabla es `Σ xi·2**i`. Ejemplo: vector `(1,0)` tiene índice 1, etiqueta humana `10` y ket Qiskit `01`. Usar `decision_vector` y `decision_label`; no interpretar strings con otra convención.

## Resultados

`run_experiment` produce JSON con:

- `schema_version`, `model_version`, `config_hash`, `seed`, `scenario`, `versions`.
- `evaluations`: todos los índices, decisiones, costos físicos y conteos.
- `qubo`: constante, lineales y pares `(i,j,valor)`; cada par aparece una vez.
- `audit`: error máximo, mínimos y pérdida de decisión sobre el costo original.
- `qaoa`: circuito, profundidad, ángulos alternados gamma/beta, configuración, probabilidades por índice y ambas expectativas. Es null si no se ejecutó Qiskit.
- `histories`: historial del programa base, óptimo físico, óptimo QUBO y candidato más probable, sin duplicados.
- `claims`: declara límites del escenario y de las conclusiones.

`config_hash` depende del escenario, semilla y versión del modelo. Si cambian unidades, costo o semántica, incrementar `MODEL_VERSION`. La configuración cuántica y la versión del paquete acompañan cada resultado. La interfaz invalida también resultados al cambiar profundidad o ejecución QAOA.

No mezclar históricos de un experimento con probabilidades de otro. Guardar resultados en `artifacts/`; subir solo fixtures pequeños y claramente identificados cuando hagan falta para pruebas.
