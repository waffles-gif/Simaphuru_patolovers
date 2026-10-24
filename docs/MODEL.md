# Modelo de referencia y límites

**Este documento describe exclusivamente la vista experimental del ZIP anterior, schema 1.0.** La opción predeterminada actual usa `model/traffic.py` del equipo: ver `docs/COMPARACION_Y_MEJORAS.md`. Sus movimientos, costo y codificación son diferentes; no intercambiar resultados.

## Dominio

Corredor abstracto unidireccional de 2 a 5 cruces. Cada cruce tiene un movimiento principal y una transversal agregada que sale del sistema al ser atendida. El flujo principal ingresa solo por el primer cruce y atraviesa el corredor. No hay giros, cambios de carril, peatones individuales ni otras entradas a la corriente principal.

Todas las dimensiones, llegadas, tiempos y eventos iniciales son supuestos educativos. No son aforos ni fases reales de Javier Prado. Los despejes no constituyen un diseño vial certificado.

## Paso y conservación

Paso fijo de un segundo. Al comienzo del paso llegan los vehículos externos. La entrada principal admite hasta el espacio disponible en su primer enlace; el resto espera fuera. Enlaces internos guardan vehículos en tránsito y detenidos y su tiempo mínimo de cruce. El primero comienza en la línea de parada, sin un tramo previo de aproximación.

Para cada enlace: `n(t+1)=n(t)+entradas−salidas`, con `0≤n≤K`. Las transferencias se calculan desde una fotografía común: no se aprovecha en ese mismo paso el espacio que liberará otro movimiento. Es una regla conservadora de un segundo, no una resolución continua de propagación de ondas.

Las colas transversales son agregadas y sin almacenamiento físico finito; representan también espera exterior. La espera principal exterior permanece contabilizada. No interpretar la geometría de esas colas como una réplica urbana.

Identidad global en cada paso: `demanda externa acumulada = salidas del sistema + inventario principal + colas transversales + cola externa principal`. Las transferencias entre cruces no cuentan como demanda nueva.

Las llegadas se aplican antes del servicio. Con capacidad 0,5 veh/s, se acumula crédito y se sirve un vehículo al segundo paso de verde si hay cola y espacio. El crédito se pierde en rojo, bloqueo o cola vacía; no se acumula capacidad durante una obstrucción. Un vehículo que pasa Ci en t no está listo en Ci+1 hasta t+travel_time_s.

## Programas y eventos

Un bit por cruce selecciona A=30/30 o B=40/20 s principal/transversal. Ciclo de 68 s: verde principal, 4 s de despeje, verde transversal y 4 s de despeje. Todas las señales empiezan con la principal y desfase cero. No hay optimización de desfases todavía.

Un evento reduce la capacidad del movimiento principal de un cruce durante `[inicio,inicio+duración)`. Si un enlace se llena, impide transferencias desde el anterior y propaga el bloqueo. Esto representa una reducción agregada de descarga; no distingue todavía una parada de bus antes/después de la línea ni maniobras específicas. Eventos superpuestos aplican el menor factor de capacidad.

## Métricas y costo

`TTS = suma por paso del inventario pendiente`, medido después del servicio, en veh·s. Incluye vehículos en tránsito y espera exterior; no llamarlo únicamente demora detenida.

`C = TTS/(60·max(1,A)) + R/max(1,A)`.

A es demanda externa total y R inventario pendiente al terminar. Los dos pesos son preferencias de demostración fijadas en 1. El máximo de espera por cruce suma cola principal lista y transversal al final del paso; no es longitud física en metros. Bloqueo cuenta segundos de verde principal con vehículos listos y receptor lleno o factor de descarga cero. No incluye una reducción parcial que aún permite servicio.

Todos los planes reciben idéntica traza exógena y horizonte. Se empieza vacío; hay efectos de arranque y truncamiento. Las esperas de vehículos pendientes son incompletas y no se eliminan del denominador.

## QUBO e Ising

Orden numérico: `index = Σ xi·2**i`, Ci+1 es qubit i. `decision_id` escribe C1…Cn y por tanto invierte el ket Qiskit habitual.

Para la tabla C:

- `c=C(0)`.
- `ai=C(ei)−C(0)`.
- `bij=C(ei+ej)−C(ei)−C(ej)+C(0)`.
- `Q2(x)=c+Σ ai xi+Σ(i<j) bij xi xj`.

Dos bits: representación exacta de cualquier tabla de cuatro costos. Más bits: puede haber términos de orden superior. Se auditan TODOS los estados, con error máximo y pérdida `C(argmin Q2)−min C`. En empates se selecciona el primer índice numérico y se informa también el rango de costos reales entre minimizadores QUBO.

La conversión Ising usa `xi=(1−Zi)/2`. Se conservan constante, términos Z y ZZ. QAOA utiliza el rango de energías para escalar la fase, manteniendo costos reportados en las unidades originales. No se usa softmax para fabricar probabilidades.

Como ya se calculó toda la tabla, el óptimo clásico es conocido. Esto no acelera la simulación ni prueba ventaja cuántica. Los resultados Qiskit son vector de estado exacto local, sin hardware ni ruido de shots.

## Qué validar después

Geometría y movimientos reales, parámetros de descarga, aforos por movimiento, fases observadas, desfases, almacenamiento y recorridos. Distinguir calibración de parámetros, validación en datos reservados y reproducibilidad computacional. Una coincidencia con otro simulador no sustituye validación empírica.
