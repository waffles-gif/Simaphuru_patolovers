# Demo y benchmark inicial

1. Seleccionar **Motor del equipo · NS/EW**, dos cruces. Explicar entradas externas en ambos cruces y conexión EW; parámetros ilustrativos.
2. Ejecutar Qiskit local. Mostrar base 24,088042, mínimo físico 17,912639 y representación exacta de cuatro decisiones. Plan 1 significa prioridad NS.
3. Inspeccionar historial de A=1,B=0. Explicar colas, transferencia y conservación global; pendientes incluyen tránsito y backlog externo. Cada tramo EW guarda hasta K_e = 12 vehículos: en la tabla, el óptimo tiene `blocked_s` = 0 y las otras tres combinaciones sí sufren spillback (43, 234 y 38 s en A).
4. Mostrar probabilidad factible, masa inválida, costo real condicionado y probabilidad del óptimo sin condicionar. No presentar el representante de mayor probabilidad como toda la distribución.
5. Mostrar cinco cruces: el sustituto de pares elige un plan con costo físico 8,85 % superior al óptimo. Separar esa pérdida de la debida al entrenamiento QAOA.
6. Descargar JSON 0.2. Reproducir con `python -m quantum.run_qaoa --input data/model_output.json --out artifacts/team_two.json`.
7. Si sobra tiempo, abrir la vista experimental como referencia conceptual anterior de almacenamiento finito. Aclarar que utiliza otro motor/costo y no comparar sus magnitudes directamente.

Antes del pitch: ejecutar pruebas, preparar video de respaldo, verificar enlaces y registrar versión. No prometer entrenamiento remoto en vivo.

## Benchmark del equipo

Casos de corrección: red vacía, vehículo único, enlace lleno, descarga bloqueada. Casos operativos a añadir: demanda moderada, pico temporal, incidente y sobresaturación.

Comparar base, óptimo físico enumerado, óptimo de pares por programación dinámica, selección uniforme factible y QAOA. Usar mismas llegadas, horizonte, estado inicial y alternativas. La demora original es por visita a colas; publicar también pendientes de red, tránsito y conteos por eje. Si se evalúa generalización del sustituto, separar escenarios/semillas de construcción y evaluación; el flujo actual audita la tabla completa de esta instancia. El enlace lleno y la descarga bloqueada ya están en el motor del equipo (v2); el bus solo está en la vista experimental.

La instalación de SUMO/RESCO y una validación empírica son pasos posteriores. No se ha ejecutado ni superado un benchmark externo con este scaffold.

## Próximos pendientes del MVP

- Fuentes y parámetros actuales del tramo real elegido.
- Representación de movimientos, entradas y desfases reales.
- Separación de parada de bus, obstrucción y maniobra de reincorporación.
- Selección periódica de planes, si se justifica y valida.
- Animación espacial y métricas peatonales/persona, si el alcance lo requiere.
- Pruebas de sensibilidad y evaluación reservada.
