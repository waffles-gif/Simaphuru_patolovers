# Comparación con GitHub, adaptación y próximos pasos

Revisión del 24/10/2026. Base consultada: [commit ee4eed5](https://github.com/waffles-gif/Simaphuru_patolovers/tree/ee4eed52ba3438242aa213532c1eb5761ae5f70e), publicado a las 12:20, hora de Lima. La adaptación se preparó y verificó localmente antes de su publicación autorizada en el repositorio. Esta comparación describe esa base verificable; otros integrantes pueden publicar cambios posteriores.

## Qué existía y qué se adaptó

| Aspecto | GitHub consultado | ZIP anterior | Entrega adaptada |
|---|---|---|---|
| Motor | `model/traffic.py`: colas NS/EW y conexión EW | `simaphuru/simulation.py`: principal/transversal | El motor del equipo es la opción predeterminada; el otro queda en una vista experimental |
| Llegadas | Externas uniformes a NS y EW de cada cruce | Principal solo en primer cruce; transversal en todos; uniformes/Poisson | Se conservan las entradas del equipo, ajustables por cruce y eje |
| Programa 1 | NS=40, EW=20 s; perjudica el verde del corredor EW | Principal=40, transversal=20 s | Se respeta NS/EW y se muestra el significado del plan |
| Ciclo y servicio | 68 s, dos despejes de 4 s, 0,5 veh/s | Mismos valores ilustrativos | Se conservan los del equipo |
| Viaje entre cruces | 25 s por defecto | 20 s | 20 s desde v2 (parámetros de R1); ajustable |
| Almacenamiento | Colas y enlaces sin límite; no hay bloqueo hacia atrás | Capacidad finita en el eje principal | Desde `team-ns-ew-v2`: K_e = 12 por tramo EW, spillback y backlog externo en el motor del equipo (ver `docs/CONTRACTS.md`) |
| Costo | Suma por cruce de demora, cola máxima y residual | Tiempo total de inventario más residual global normalizados | Se conserva exactamente el costo del equipo, sin comparar magnitudes entre ambos motores |
| Codificación | README propone one-hot; aún no contiene implementación cuántica | Un bit por cruce | One-hot de 4 o 10 qubits para 2 o 5 cruces; flujo anterior preservado aparte |
| Dos cruces | Enumera cuatro planes y obtiene locales/pares | QUBO de dos bits por diferencias | Locales/pares del motor del equipo → QUBO one-hot → Ising → QAOA real |
| Cinco cruces | `model/chain.py` ya mide error de pares vecinos | Aproximación de todos los pares por diferencias | Se usa la aproximación vecina del equipo y se verifica contra sus 32 decisiones completas |
| Interfaz | No hay archivos `web/` ejecutables | Streamlit funcional | `web/team_app.py` usa el motor del equipo; `web/reference_app.py` conserva la vista experimental |
| Contrato | JSON 0.1, costos redondeados a seis decimales; faltan parámetros físicos | JSON 1.0 incompatible | JSON 0.2 amplía los campos 0.1; importación 0.1 verificada, sin mezclarlo con 1.0 |
| Pruebas | Siete pruebas de tráfico | Dieciséis pruebas | Pruebas originales más integración, conservación global, one-hot e interfaz |

Se incorporaron los archivos del motor y sus JSON originales. Desde `team-ns-ew-v2`, `model/traffic.py`, `model/enumerate.py`, `model/test_traffic.py` y los JSON cambian respecto al commit consultado para incorporar almacenamiento finito. En `model/chain.py` solo se adapta la importación para permitir tanto ejecución directa como importación de paquete. Los `.pyc` publicados por el equipo se excluyen de la entrega y de futuras incorporaciones: son cachés dependientes del entorno, no código fuente.

## Qué resultado cambia una decisión de alcance

Resultados con el motor `team-ns-ew-v2` y los parámetros de R1 (horizonte 1360 s, viaje 20 s, K_e = 12) y comienzo vacío:

| Cruces | Óptimo del simulador | Costo físico óptimo | Plan elegido por locales/pares | Costo real de ese plan | Error máximo de costos |
|---|---|---:|---|---:|---:|
| 2 | A=1, B=0 | 17,912639 | A=1, B=0 | 17,912639 | ≈ 0, dentro del redondeo numérico |
| 5 | A=1, B=1, C=1, D=0, E=0 | 48,630476 | A=1, B=1, C=0, D=0, E=1 | 52,933018 | 10,540359 |

La pérdida de decisión para cinco cruces es 4,302542, aproximadamente **8,85 %** del óptimo físico. Es un error de la representación por pares; puede persistir aunque un algoritmo resuelva perfectamente ese QUBO. No se corrige automáticamente añadiendo capas QAOA.

Comprometer la demo principal de **dos cruces**. Presentar cinco como experimento que expone y mide una limitación. Ambos son corredores abstractos, no una calibración de Javier Prado.

## Qué debemos entender del tráfico actual

**Estado:** colas FIFO NS/EW, vehículos en tránsito, acumuladores de llegadas y créditos de servicio. **Decisión:** un plan fijo 0 o 1 por cruce para todo el horizonte. **Algoritmo:** enumeración, programación dinámica del costo por pares o QAOA. Cambiar el algoritmo no añade realismo a las colas.

En cada paso de un segundo entran vehículos externos, llegan transferencias que completaron su viaje y se atiende el eje verde. Las transferencias EW desde un cruce se suman a las llegadas EW externas del siguiente. Todos los vehículos EW siguen al cruce siguiente, salvo en el último; no hay porcentajes de giro ni salida intermedia. NS representa una cola agregada y sale del sistema tras ser atendida. No son dos sentidos ni todos los movimientos de una intersección real.

Para el eje `a` del cruce `i`:

`q_i,a(t+1) = q_i,a(t) + llegadas_externas + transferencias_recibidas - servicio`.

La conservación global debe contar vehículos únicos:

`demanda externa = salidas definitivas + colas finales + vehículos en tránsito`.

Sumar las llegadas de todas las colas cuenta varias visitas del mismo vehículo EW. El motor calcula su demora media agregada con ese denominador: es demora por visita a colas, no tiempo de viaje por vehículo único. La integración informa además conteos globales y pendientes incluyendo tránsito. Mantiene el costo existente sin cambiar silenciosamente su significado.

El costo es una **preferencia de evaluación**, no una ley física:

`C_i = wD·D_i/60 + wP·Qmax_i/30 + wR·R_i/30`, y `C = Σ_i C_i`.

`D_i` es tiempo acumulado en colas dividido entre llegadas a esas colas, `Qmax_i` es el máximo de un solo eje y `R_i` suma las colas finales. El residual del costo original no penaliza los vehículos todavía en viaje. Despachar hacia un enlace durante el final del horizonte puede alterar esta comparación; revisar sensibilidad al horizonte, informar pendientes en tránsito y acordar un costo terminal antes de cambiar el objetivo. No eliminar vehículos pendientes ni reportar solo los completados.

## Qué debemos entender del QUBO

Para dos cruces se obtienen costos aislados `L_A(k)`, `L_B(l)` y costo del corredor `C(k,l)`. Se define por construcción:

`V_AB(k,l) = C(k,l) - L_A(k) - L_B(l)`.

Por eso `L_A + L_B + V_AB` reproduce los cuatro costos, incluso si el simulador original tiene máximos y dinámicas no lineales. La exactitud proviene de esta tabla finita de **dos decisiones**, no de suponer que las ecuaciones del tráfico son cuadráticas.

Con `x_i,k=1` si se elige el plan k:

`F(x)=Σ_i,k L_i(k)x_i,k + Σ_(i,i+1),k,l V_i(k,l)x_i,k x_(i+1),l`.

`Q(x)=F(x)+P Σ_i(x_i,0+x_i,1−1)²`.

La ampliación de la penalización añade una constante `P` por cruce, un término lineal `−P` para cada variable y un término `2P·x_i,0·x_i,1`. No se omite la constante al comparar energías. El objetivo Ising usa `x=(1−Z)/2` y se verifica el orden de bits con tablas asimétricas.

La penalización se justifica mediante una cota: `L` suma los coeficientes negativos de F, por lo que F(x)≥L en todo estado binario; `U=F` de un plan factible conocido. Se elige `P=max(1, 1,5·(U−L))`, que sigue cumpliendo P > U−L. Todo estado inválido tiene al menos una violación, así que `Q(x)≥L+P>U`. Esto garantiza que el mínimo global del QUBO sea factible; **no** garantiza que el circuito QAOA produzca solo estados factibles. Una P conservadora puede dificultar el entrenamiento al dominar la escala del objetivo.

Con cinco cruces, los pares se calculan simulando subcorredores aislados de dos cruces. Un cruce lejano recibe una corriente afectada por varios planes anteriores; por eso las sumas vecinas pueden omitir efectos. La auditoría informa error máximo y medio y `C(argmin F)−min C`. El clásico por programación dinámica resuelve F exactamente en O(N·K²), pero F puede aproximar C.

El circuito QAOA usa puertas Qiskit y probabilidades exactas de vector de estado, con p=3 capas, tres reinicios de Nelder–Mead y hasta 300 evaluaciones por reinicio. La semilla controla el entrenamiento; el tráfico actual es determinista. Se informa:

- Probabilidad factible y masa inválida, sin ocultar fallos.
- Probabilidad sin condicionar de alcanzar el óptimo del simulador.
- Costo real esperado **condicionado** a factibilidad, acompañado por la probabilidad factible.
- Un plan factible de mayor probabilidad como representante. No equivale a garantizar el mejor plan.

No existe costo físico definido para un estado que elige cero o dos planes por cruce. No se le inventa uno: su energía penalizada sigue en el QUBO, pero su costo físico se deja indefinido. Estos resultados no demuestran ventaja cuántica.

## Mejoras priorizadas y criterios de aceptación

| Prioridad | Mejora propuesta | Responsable inicial | Concepto que debe comprender | Prueba de aceptación |
|---|---|---|---|---|
| P0 | Acordar denominadores, pendientes y costo terminal | Daniel + Valentino; Rafael revisa el efecto QUBO | Diferencia entre vehículos únicos, visitas, demora y tiempo en el sistema | Conservación por paso; sensibilidad a 600/680/1200 s; publicar conteos incluso sin completar viajes |
| P0 | Mantener contrato 0.2 completo y misma huella entre costos, QAOA e historial | Tamara + Rafael | Procedencia, orden de bits y versionado | Cambiar un costo importado o parámetro invalida la integración; no reutilizar otro historial |
| P1 | Almacenamiento finito y bloqueo aguas arriba en el motor del equipo (hecho en `team-ns-ew-v2`) | Valentino | Oferta de envío, capacidad de recepción y ocupación de enlace | Enlace lleno impide transferencia; conservar vehículo en origen; al liberar espacio se reanuda |
| P1 | Demanda variable compartida entre candidatos | Daniel define casos; Valentino implementa trazas | Llegadas por movimiento, pelotones y aleatoriedad exógena | Misma traza para todos los planes; resultados por varias semillas; reservar semillas para evaluación |
| P2 | Parada de bus como reducción temporal de descarga, con ubicación explícita | Daniel + Valentino | Capacidad efectiva, duración y localización de la obstrucción | Fuera de la ventana no cambia capacidad; con factor cero no descarga; no se acumula crédito de servicio |
| P2 | Revisar calidad del sustituto de cinco cruces | Rafael | Error de representación frente a error del optimizador | Error por estado y pérdida sobre simulador completo; separar conjunto de construcción y evaluación si se ajusta un sustituto |
| P2 | Comparar one-hot con un bit por cruce o un mezclador que preserve factibilidad | Rafael | Subespacio factible, penalizaciones y muestreo | Mantener el mismo costo físico y catálogo; comparar probabilidad de óptimo sin condicionar y recursos, sin ocultar estados inválidos |
| P2 | Desfases como parte del catálogo de planes seguros | Rafael + Valentino | Coordinación de señales, viaje y fases permitidas | Cambiar desfase conserva verdes/despejes; no permite movimientos incompatibles |
| P3 | Visualización espacial del mismo historial y replay | Tamara | Diferencia entre animación y simulación | Fotogramas y contadores proceden del mismo hash y tiempo; distinguir cola de vehículos en tránsito |
| P3 | Calibrar una ubicación real y validar en otro período | Daniel coordina con todo el equipo | Observación, estimación, calibración y validación reservada | Fuente/fecha/unidad por parámetro; error sobre aforos y colas no usados para ajustar |

### Cómo ampliar físicamente sin romper la coherencia

**Almacenamiento.** Sea `n_i=q_i+v_i` la ocupación EW total, incluidos vehículos en tránsito, y `K_i` la capacidad. El envío debe respetar `f_i(t)≤min(q_i,listos(t), s_i(t), K_(i+1)−n_(i+1)(t))`, además del verde. Aquí `s_i` es el cupo entero derivado del crédito de servicio del paso. Las tasas originales son fraccionales: no redondear siempre 0,5 a cero. Calcular transferencias desde un estado común evita que un vehículo salte varios enlaces en el mismo segundo. Las entradas externas EW a un receptor lleno deben esperar en un depósito exterior contabilizado. Definir una regla para repartir recepción escasa entre entrada lateral y flujo precedente. Versionar el motor y recalcular todas las tablas: el QUBO anterior ya no corresponde.

**Demanda variable.** Usar una traza fija por experimento `a_i,a(t)`, primero con picos deterministas y luego, si se justifica, `a∼Poisson(λ_i,a(t)·Δt)` con λ en veh/s. Poisson es un supuesto, no un hecho demostrado de Lima. Cerca de señales puede ser necesario representar pelotones. Guardar la traza o su huella y semillas; comparar planes sobre los mismos eventos.

**Buses.** Una primera extensión agregada es `μ_i,EW(t)=μ0_i·[1−ρ_i·B_i(t)]`, donde B vale 1 durante una parada exógena y ρ es pérdida de capacidad entre 0 y 1. Es una obstrucción agregada, no un modelo de comportamiento del bus. Una parada antes de la señal, después de ella o en bahía necesita mecanismos distintos. Sin mediciones de frecuencia/duración, presentar análisis de sensibilidad. No atribuir beneficio a pasajeros si solo se cuenta vehículos.

**Coordinación.** Introducir un desfase φ mediante `fase_i(t−φ_i)` y elegir entre programas predefinidos completos. Ampliar de dos a K alternativas cambia la cantidad de variables one-hot y de combinaciones; no reutilizar automáticamente las funciones actuales limitadas a dos planes. Mantener como restricciones duras los movimientos permitidos y despejes; preferencias como favorecer un eje pertenecen al objetivo.

**Cinco cruces.** Antes de aumentar capas QAOA, revisar si conviene aprender factores adicionales, incluir estados/flujo en una formulación mayor o reducir el alcance. Una función arbitraria de cinco decisiones puede tener términos de orden tres a cinco. Hacerla exactamente cuadrática puede requerir variables auxiliares y más penalizaciones. Se deben explicar sus relaciones y verificar también los estados auxiliares. Para una demo, una aproximación con error medido es más defendible que llamarla exacta sin prueba.

## Benchmark y comprensión del equipo

**Ya ejecutable:** programa base, enumeración del costo físico, programación dinámica de locales/pares, expectativa de selección uniforme entre planes factibles y QAOA. Todos comparten parámetros, horizonte vacío inicial y alternativas. El costo del simulador y la energía aproximada se muestran separados. Los tiempos distinguen preparación de tablas, búsqueda clásica y entrenamiento; no comparar como aceleración un entrenamiento que usa una tabla previamente enumerada.

**Por añadir:** escenario vacío, demanda moderada, sobresaturación, pico temporal, bloqueo receptor y bus, con ablaciones que cambien un solo mecanismo. El motor principal ya permite variación de tasas constantes; picos, almacenamiento y buses deben implementarse allí antes de atribuirle esos escenarios. La vista experimental puede servir como ejemplo conceptual, pero sus costos no son comparables directamente.

Para cada mecanismo: un caso manual pequeño, una prueba física y un experimento de sensibilidad. Para demanda aleatoria: definir antes del ensayo un conjunto de semillas de construcción y otro reservado; publicar dispersión además de promedios. Reproducir una semilla prueba reproducibilidad computacional. Validar Lima requiere observaciones independientes: geometría/movimientos, verde real, descarga, aforos por movimiento, ocupación y tiempos de parada. La evidencia histórica orienta hipótesis; no sustituye aforos actuales.

### Asignación para continuar sin bloquear a los demás

| Integrante | Puede empezar ahora | Entrega mínima |
|---|---|---|
| Daniel | Ficha de cada parámetro y revisión del objetivo/denominadores | `docs/parametros.md`: observado/histórico/supuesto, fuente y unidad; caso manual de receptor lleno |
| Rafael | Explicar y auditar cuatro estados válidos y doce inválidos; contrastar DP con QAOA | Tabla de energías, prueba de P, masa factible, pérdida de representación y brecha del algoritmo separadas |
| Valentino | Diseñar almacenamiento como una extensión versionada de `model/traffic.py` | Balance por enlace y global, pruebas de cola llena y viajes, resultados antes/después con mismo escenario |
| Tamara | Ensayar la vista predeterminada y descarga/replay con contrato 0.2 | Demo reproducible, hash visible y vídeo de respaldo; visualización sin cambiar ecuaciones |

Punto conjunto breve: acordar qué significa cada métrica, conservar el caso de dos cruces que funciona y fijar un contrato antes de integrar nuevas ecuaciones. El modelo físico y la formulación deben poder explicarse a mano con dos cruces antes de presentar cinco o hardware real.
