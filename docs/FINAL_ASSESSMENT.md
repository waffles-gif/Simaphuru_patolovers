*Nota posterior (24/10, noche): la interfaz ahora abre en binaria; la CLI sigue en one-hot.*

# Assessment y plan de cierre para la final

Actualizado el 24/10/2026 por la noche. Final comunicada por Rafael: **25/10/2026, 10:00, Lima**.
No hubo comentarios específicos del jurado ni cambios de rúbrica o entregables. Base revisada:
`09ed6d0`, que ya incorpora la vista comparativa del equipo. Este assessment no asigna una nota
inventada ni representa una evaluación oficial del jurado.

## Decisión de alcance

El producto ya funciona. Para la final conviene fortalecer la formulación, el benchmark y la explicación
antes de incorporar un modelo vial completamente nuevo. Una mejora pequeña, auditada y visible tiene
mejor relación impacto/riesgo que aumentar cruces o depender de acceso remoto a una QPU.

Compromiso de esta primera iteración: conservar la física y las referencias históricas, añadir una
codificación compacta del mismo objetivo y comprobar que su beneficio no dependa de una sola semilla.
QAOA sigue siendo híbrido en su entrenamiento. Tras la selección de Rafael, una segunda iteración
añadió búsqueda híbrida de candidatos con validación física y dos controles clásicos; ver
`HYBRID_VALIDATION.md`. Warm-start del estado cuántico permanece fuera de alcance.

## Assessment según la rúbrica

Las bases originales están en `/Users/rafaelchamayo/Downloads/BASES DE PARTICIPACIÓN.pdf`, páginas 4–7.
Para Algoritmos y aplicaciones se combinan los criterios comunes con el específico de la categoría:

| Criterio | Peso | Evidencia actual | Qué reforzar para la final |
|---|---:|---|---|
| Innovación, validación y potencial | 25% | Spillback y comparación de programas conectados | Mecanismo físico explicado con un caso controlado; distinguir aplicación potencial de validación de Lima |
| Uso de Qiskit y claridad | 25% | Circuitos reales Qiskit simulados; interfaz y gráficos | Explicar qué decide el circuito y mostrar una mejora auditada; ensayo de 2:30–3 minutos |
| Formulación y optimización | 20% | QUBO exacto para dos cruces, aproximación auditada para cinco; enumeración y DP | Comparar codificaciones sin cambiar el problema; separar error algebraico, físico y del algoritmo |
| Rigor y reproducibilidad | 15% | Contratos, tests y escenarios sintéticos identificados | Semillas múltiples, evidencia descargable y presupuesto de entrenamiento explícito |
| Calidad y arquitectura | 15% | Motor compartido por interfaz/CLI y separación de modelos | Casos límite sin fallos, metadatos claros y demo reproducible |

Las bases piden GitHub, descripción, integrantes, PPT y demo o video cuando corresponda. El pitch es
el principal medio de evaluación en la final, dura 2:30–3 minutos y puede incluir preguntas. **No exigen
ventaja cuántica**. Puntúan pertinencia, justificación y gestión de limitaciones.

## Prioridades por impacto, esfuerzo y riesgo

| Orden | Mejora | Impacto | Esfuerzo orientativo | Riesgo | Decisión |
|---|---|---|---|---|---|
| 1 | Codificación binaria, identidad energética y barrido emparejado | Alto en formulación y Qiskit | 45–90 min con verificación | Bajo/medio | Implementada en esta iteración |
| 2 | Resolver cero costo/empates y distinguir moda de muestreo | Alto en rigor de la demo | 20–40 min | Bajo | Implementada en esta iteración |
| 3 | Híbrido: semilla clásica, candidatos QAOA y selección física | Alto como experimento | 60–120 min | Medio | Implementado por elección de Rafael, con controles clásicos y presupuestos explícitos |
| 4 | Reproductor sincronizado y eventos de bloqueo registrados | Alto en claridad visual | 45–90 min | Medio | Implementado después: un reloj para canvas y tarjetas, con eventos reales de bloqueo |
| 5 | Demanda variable y obstrucción de descarga por bus | Alto en realismo | 2–4 h más recalcular benchmark | Alto esta noche | Solo tras congelar una versión estable y si queda tiempo |
| 6 | Hardware remoto o una red mucho mayor | Incierto para esta final | Variable | Alto | No convertirlo en dependencia del pitch |

Los esfuerzos son estimaciones de trabajo, no promesas de ejecución ni disponibilidad del equipo.

## Qué se implementó y qué prueba su aceptación

- Opción binaria: un qubit por cruce; one-hot permanece seleccionable y predeterminado.
- Sustitución exacta `x_i0=1-y_i`, `x_i1=y_i`; igualdad con F para todos los programas de prueba,
  incluidos factores aleatorios asimétricos y negativos. Se comprueba también la energía Ising.
- Mismo motor, demanda, costos físicos, conteos e historiales al cambiar codificación.
- Error F−C de cinco cruces inalterado: no se presenta como una corrección del modelo físico.
- Identificadores separados para escenario físico y ejecución; invalidación al cambiar codificación.
- UI sin división por cero y referencia uniforme que cuenta todos los óptimos en casos empatados.
- La probabilidad de una medición no se atribuye a la selección determinista del plan modal.
- CLI y barrido reproducibles; resultados completos en JSON/CSV, con presupuesto y hashes del código.

Ver `FINAL_VALIDATION.md` para resultados, alcance y comandos de reproducción.

## Segundo incremento implementado: híbrido verificado

1. Un método clásico barato obtiene un programa inicial; no usar el óptimo exacto como supuesto logro
   del híbrido. DP es óptima para F, pero su programa puede mejorarse bajo C.
2. QAOA propone un conjunto limitado de programas mediante muestreo con semilla y presupuesto explícitos.
3. El mismo simulador completo evalúa cada programa distinto, con idénticas entradas.
4. Conservar el mejor incluyendo el inicial; registrar intentos, duplicados, simulaciones nuevas y costos.
5. Repetir sustituyendo QAOA por búsqueda clásica local o muestreo uniforme con presupuesto comparable.
6. Mostrar cuánto añadió cada etapa. Si la contribución cuántica no mejora el clásico, reportarlo.

Los seis pasos anteriores ya están implementados y se prueban sin pasar la tabla exacta al selector.
La regla de aceptación asegura no empeorar C respecto del inicial en el escenario evaluado, no cada
métrica individual ni el tráfico real. El entrenamiento y las simulaciones para construir F también se
contabilizan. Warm-start puede estudiarse después de tener esta ablación clara.

## Organización antes de las 10:00

Propuesta de trabajo con límites, dejando descanso y evitando cambios estructurales por la mañana:

- Esta noche: cerrar y revisar codificación e híbrido, ya implementados. Priorizar ahora una demo
  coherente y el ensayo antes de añadir otra familia de ecuaciones. Registrar versión estable antes de seguir.
- Antes de dormir: ejecutar la demo completa, guardar resultados/capturas y grabar respaldo. Ninguna
  funcionalidad nueva se incluye en el pitch sin pruebas y cifras reproducidas.
- Mañana 08:30–09:00: comprobar instalación, enlaces, PPT, repositorio y respaldo desde el equipo que
  presentará. Conservar margen para traslado y logística según ubicación del equipo.
- 09:00–09:30: dos ensayos cronometrados; todos deben explicar programa, objetivo, QUBO y probabilidades.
- Desde 09:30: congelar cambios de comportamiento; solo corregir bloqueos de la demo.
- Antes de 10:00: equipo y materiales listos según instrucciones oficiales de la organización.

Si el equipo está disponible, tareas independientes: Rafael revisa formulación y resultados; Daniel
prepara evidencia y límites de Lima; Valentino verifica el caso físico y conservación; Tamara ensaya
la demo, PPT y respaldo. La presentación no depende de ejecutar el barrido completo en vivo.

## Mensaje técnico defendible

“Nuestro simulador representa bloqueo entre cruces conectados. Construimos y verificamos la
formulación, comparamos QAOA con referencias clásicas y encontramos que una codificación más compacta
mejora nuestro QAOA. Mostramos además cuándo una aproximación por pares pierde fidelidad física.”

No afirmar calibración de Javier Prado, ventaja cuántica, menor tiempo de viaje real, funcionamiento
de buses individuales ni que el plan más probable se obtiene en todas las mediciones.

## Checklist de salida

- [x] Mantener referencias clásicas y versión previa reproducible.
- [x] Física inalterada entre codificaciones; identidad energética auditada.
- [x] Evaluar tres escenarios, dos tamaños y tres semillas para cada codificación.
- [x] Tests y Ruff locales; casos de demanda vacía y pesos cero.
- [x] Híbrido con verificación del simulador completo, límites y dos controles clásicos.
- [x] Reproductor sincronizado y casos intermedios N=3/4 evaluados y habilitados.
- [ ] Revisar el diff en equipo y publicar la versión que decidan presentar.
- [ ] Ensayar 2:30–3 minutos con una única configuración y cifras identificadas.
- [ ] PPT, demo/video de respaldo y enlaces accesibles para el jurado.
- [ ] Confirmar que cada integrante entiende los resultados y sus límites.
