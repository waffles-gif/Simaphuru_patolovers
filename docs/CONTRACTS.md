# Contratos de datos

## Extensión para la final: schema 0.3, codificación explícita

El motor físico sigue siendo `team-ns-ew-v2`: sus ecuaciones, parámetros, costos e historiales no cambian
al elegir una codificación. `run_team_experiment(..., encoding="one_hot" | "binary")` conserva one-hot
como valor predeterminado para reproducir las referencias anteriores. La CLI añade `--encoding` y la
interfaz permite elegir ambas. El paquete pasa a 0.3.0.

- `encoding.name`, `qubits`, `states`, `valid_states` y `penalty` describen el registro activo.
- One-hot: dos variables por cruce, índice `Σ 2**(2*i+plan_i)`, P conservadora como en 0.2.
- Binaria: `y_i=plan_i`, índice `Σ plan_i*2**i`, un qubit por cruce; todos los estados eligen un programa.
  No hay penalización one-hot. Esto no garantiza que el programa sea óptimo ni que el modelo sea calibrado.
- La sustitución `x_i0=1-y_i`, `x_i1=y_i` conserva exactamente F, el objetivo por pares vecinos.
  Para V(a,b), se usa V00+(V10−V00)a+(V01−V00)b+(V11−V10−V01+V00)ab.
  Se verifican exhaustivamente sus energías. La aproximación F≠C en cinco cruces permanece igual.
- `model.combinations[].decision_index` y `quantum.valid_probabilities[].decision_index` indexan las
  probabilidades del registro ACTIVO. `one_hot_index` se conserva solo como índice histórico one-hot;
  no usarlo para indexar un resultado binario.
- `classical.optimal_x` usa el registro activo. `bit_order` describe ese registro; el ket Qiskit sigue
  imprimiéndose en orden inverso al vector de decisiones humano A…E.
- `audit.encoding` contiene la prueba de identidad algebraica del registro activo; `audit.one_hot` se
  conserva con el contenido anterior para one-hot y vale null en binaria.
- `config_hash` identifica exclusivamente el tráfico y sigue siendo igual entre codificaciones.
  `experiment_id` añade codificación, activación QAOA, semilla, profundidad, presupuesto y versiones
  de Simaphuru/Qiskit. `execution` expone esos valores. No mezclar resultados usando solo config_hash.
- `factor_generation_ms` mide la construcción compartida de factores. Los tiempos de búsqueda QAOA/DP
  excluyen esa etapa; la enumeración física se hace para referencia/auditoría y no construye F.

El importador acepta schemas 0.1/0.2/0.3 y vuelve a comprobar costos y factores contra el motor.
El modo experimental schema 1.0 permanece separado. Los apartados históricos siguientes describen
la referencia one-hot 0.2, no una restricción de usar siempre dos qubits por cruce.

### Candidatos híbridos verificados

`run_team_experiment(..., hybrid=True)` requiere QAOA y añade `hybrid`; cuando está desactivado vale null.
La configuración se añade a `execution` y `experiment_id`, nunca a los parámetros físicos/config_hash.

- Inicio común: programa de DP para F. El módulo `simaphuru/hybrid.py` recibe solo parámetros, inicio
  y probabilidades, no la tabla exhaustiva ni el óptimo físico.
- Tres métodos: `qaoa_candidates`, `uniform_candidates`, `local_search`. El último explora vecinos
  no evaluados de uno y después dos bits del mejor programa conocido, con orden aleatorio reproducible.
- `candidate_proposals` limita las propuestas (default 32), `max_candidate_simulations` limita las
  simulaciones nuevas por método (default 8), incluida una simulación del programa inicial.
  `sampling_seed` (default 2026) es independiente de la semilla del entrenamiento.
- Cada método usa un caché independiente. Duplicados e inválidos consumen propuestas y no otra
  evaluación física. Al alcanzar el límite, las propuestas nuevas restantes se registran sin costo,
  con `status=not_evaluated_budget`; no se consulta su costo en la tabla exhaustiva.
- La búsqueda local puede terminar antes de agotar propuestas. Se informa trabajo efectivo: límites
  iguales no equivalen a igual tiempo o igual número efectivo de simulaciones.
- `selected_cost` se obtiene ejecutando `simulate_chain` y nunca supera `initial_cost` salvo redondeo.
  `selected_plans`/`initial_plans` son diccionarios por cruce en la salida integrada, listas en las trazas.
- `gap_to_exact` se añade después de seleccionar, para diagnóstico. No guía la generación ni selección.
- `sampling_kind=classical_sampling_from_ideal_qaoa_probabilities`: no son shots físicos ni ruido de QPU.
  `warm_start_quantum_state=false`: la solución clásica es referencia de aceptación, no estado inicial QAOA.
- Los tiempos por método cubren propuestas y evaluaciones físicas. Factores, DP y entrenamiento QAOA se
  informan aparte. La app completa todavía enumera para auditoría; no se afirma aceleración ni escalabilidad.
- Los programas finales de los tres métodos se incluyen en `histories`, regenerados desde el mismo
  escenario. Conservar la identidad del experimento al animarlos o exportarlos.

### Historial y reproductor sincronizado

El historial de `model/traffic.py` añade `blocked`, una lista booleana por cruce y paso. Se registra
exactamente en la misma condición que incrementa `blocked_s`. No cambia ninguna ecuación, costo,
demanda, capacidad o decisión; el modelo físico conserva la versión v2 y su config_hash.

- `phases`, `queues`, `occupancy`, `backlog` y `t` describen el registro del paso. `blocked[i]` es el
  evento ocurrido al intentar despachar, antes del servicio posterior del receptor en ese segundo.
  Por ello puede valer true aunque la ocupación del receptor al final del paso sea menor que K.
- La suma temporal de `blocked[i]` coincide con `per_intersection[i].blocked_s`.
- Reloj, semáforos, colas y tarjetas del reproductor usan el mismo `history[floor(tf)]`.
  Solo los sprites de coches se interpolan entre segundos; no se vuelve a simular tráfico al reproducir.
- El deslizador pausa y selecciona un paso común; Inicio vuelve al primero; cambiar programa recrea
  el reproductor en el primer paso. No hay un segundo deslizador de inspección estática en Streamlit.
- Las tarjetas incluyen fase, colas NS/EW, ocupación EW, tránsito, espera externa y evento de bloqueo.
  Historiales antiguos sin `blocked` muestran «sin registro»; no se reconstruye un evento ficticio.
- El gráfico de colas muestra el horizonte completo y los conteos finales se rotulan como tales;
  no se presentan como si fueran indicadores del instante reproducido.

La interfaz permite N=2,3,4,5; el adaptador y la CLI ya admitían esos tamaños. Las codificaciones
usan N qubits binarios o 2N one-hot. Se auditan siempre las 2**N decisiones físicas y no se asume
que el objetivo por pares sea exacto para tres o cuatro cruces.

## Integración predeterminada: motor del equipo, schema 0.2

`TeamParams` en `simaphuru/team.py` valida las entradas del motor R3: segundos, veh/min y veh/s, identificadores únicos, dos planes 0/1 y suma de verdes/despejes igual al ciclo. La opción de dos cruces usa cuatro variables one-hot: `x_A0,x_A1,x_B0,x_B1`. En cinco, son diez variables. La variable q corresponde al qubit q y al peso `2**q`; la impresión de kets Qiskit invierte ese orden visual. Ejemplo A=1,B=0: vector `[0,1,1,0]`, índice 6.

La salida 0.2 conserva los campos de integración `inputs`, `model.local_costs`, `model.pair_costs`, `model.combinations` y `classical` de 0.1, y añade parámetros completos sin redondear, huella, versión, auditoría, `quantum` e historiales. `quantum` es null si no se solicita QAOA. `example=false` significa resultado calculado; los parámetros siguen siendo sintéticos. No se convierte automáticamente a schema 1.0.

`config_hash` depende de TODOS los parámetros y de `team-ns-ew-v2`. La vista invalida resultados al cambiar también semilla del optimizador, profundidad o activación QAOA. El historial se regenera desde los mismos parámetros y planes. `upstream_commit` identifica la base auditada; la versión del paquete identifica la adaptación.

### Almacenamiento finito y spillback (`team-ns-ew-v2`)

- `storage_vehicles` (K_e, vehículos, default 12) es la capacidad del tramo EW que entra a cada cruce i. Ocupación = cola EW de i + autos en tránsito hacia i; nunca supera K_e.
- Spillback: el EW de i solo despacha si el tramo de i+1 tiene espacio (K_e − cola − tránsito > 0). El último cruce sale sin límite. Si el destino está lleno no sale nadie aunque haya verde, y el crédito fraccional de servicio se reinicia.
- Desborde externo: las llegadas externas EW que no caben esperan en un backlog FIFO fuera de la red. Cuentan en `arrived_external`, suman veh-s a la demora y entran al balance. NS no tiene límite.
- Prioridad del corredor: mientras el EW de i-1 está en verde con cola, reserva 1 lugar en el tramo de i; el backlog externo de i solo usa el espacio restante.
- Orden por segundo y por cruce (A → B → …): llegadas externas y backlog (respetando la reserva) → aterrizan los autos en tránsito → servicio con chequeo aguas abajo → demora (cola + backlog).
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
