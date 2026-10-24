# Verificación de la entrega adaptada

Fecha: 24 de octubre de 2026. Base GitHub original: `ee4eed52ba3438242aa213532c1eb5761ae5f70e`. Resultados regenerados con el motor `team-ns-ew-v2` (almacenamiento finito K_e = 12 por tramo EW, spillback, horizonte 1360 s, viaje 20 s).

## Entorno y pruebas

- Python 3.14.0 local (único disponible; dependencias instaladas con `--ignore-requires-python`); paquete simaphuru 0.2.0. El CI comprueba 3.11 y 3.13.
- Qiskit 2.6.1, Aer 0.18.0, Optimization 0.7.0, NumPy 2.3.5, SciPy 1.16.3, Streamlit 1.66.1, Pydantic 2.14.1.
- **38 pruebas locales pasaron**: las originales del equipo, los tres casos manuales de R1 (flujo libre, destino lleno, despeje), conservación con backlog, ocupación ≤ K_e, prioridad del corredor, física del motor experimental, contratos, auditoría one-hot/Ising, suficiencia de P, programación dinámica, importación de JSON real/rechazo de cifras incompatibles, conservación de vehículos únicos, Qiskit e interfaz.
- Ruff: sin errores. `python -m streamlit run app.py` arranca sin errores (health check `ok`).
- Se construyó el paquete distribuible 0.2.0 y se importaron sus cuatro paquetes desde una extracción separada; el experimento de dos cruces reprodujo A=1,B=0.
- La interfaz se probó con AppTest con QAOA habilitado: la tabla muestra `blocked_s` por cruce. Se comprobó invalidación al cambiar de corredor y separación del motor experimental.
- `model/traffic.py` ya no coincide con el commit original: desde `team-ns-ew-v2` agrega K_e, spillback y backlog externo (ver `docs/CONTRACTS.md`). `data/model_output.json` y `data/chain_output.json` se regeneraron con ese motor.
- Compatible por declaración con Python 3.11–3.13. La ejecución local fue en 3.13; consultar la pestaña Actions de GitHub para el estado de la comprobación remota en 3.11/3.13.

## Resultados calculados sobre el motor del equipo

QAOA p=3, penalización P = 1,5·(U−L), semilla del optimizador 7, tres reinicios de Nelder–Mead y hasta 300 evaluaciones por reinicio (configuración por defecto). Datos de tráfico uniformes y deterministas. No se utilizaron hardware ni shots.

| Cruces | Mínimo físico | Error máximo de pares | Pérdida real al minimizar pares | P(factible) QAOA | P(óptimo físico), sin condicionar | E[costo físico dado factible] |
|---|---:|---:|---:|---:|---:|---:|
| 2 | 17.912638629 | 0.000000000 | 0.000000000 | 0.970694 | 0.283615 | 21.786308766 |
| 5 | 48.630475554 | 10.540358986 | 4.302542457 | 0.987935 | 0.034371 | 55.373277337 |

Óptimos físicos: dos cruces A=1,B=0 (0 s bloqueados); cinco cruces A=1,B=1,C=1,D=0,E=0. Plan factible más probable de QAOA: A=1,B=0 en dos cruces (coincide con el óptimo) y A=1,B=1,C=0,D=0,E=1 en cinco (el óptimo del sustituto de pares, costo real 52.933018). P = 36,132064 en dos cruces y 78,768811 en cinco. Tiempo QAOA: ≈2,2 s y ≈14 s. Programa base: 24.088042 y 61.302960; media uniforme entre factibles: 22.242612 y 55.618418.

Archivos: `artifacts/team_two.json` y `artifacts/team_five.json`. El primero verifica/importa `data/model_output.json` schema 0.1; se declaran parámetros físicos heredados ausentes en ese contrato. Los nuevos resultados completos usan schema 0.2 y se pueden volver a ejecutar con `quantum/run_qaoa.py` como módulo.

Con cinco cruces, el mejor plan del sustituto (A=1,B=1,C=0,D=0,E=1) tiene costo real 52.933018011 frente a 48.630475554 del óptimo: pérdida ≈8.85 %. No es un fallo numérico del solver; es una discrepancia de representación. El reporte QAOA separa esta cuestión del entrenamiento.

La selección uniforme entre planes factibles tiene P(óptimo)=1/4 en dos cruces y 1/32 en cinco para estos casos, con factibilidad 1. Con la configuración por defecto, la P(óptimo) sin condicionar de QAOA es 0,284 y 0,034: ligeramente mayor que esas referencias. Su costo físico esperado condicionado también es ligeramente menor que la media uniforme. La ventaja es pequeña, sobre una sola instancia y semilla, y con cinco cruces el plan más probable es el óptimo del sustituto, no el físico. **No se afirma que esta configuración QAOA supere globalmente a la selección uniforme ni a las referencias clásicas.** Son métricas distintas y se deben publicar juntas.

### Barrido de configuración QAOA (dos cruces, semilla 7, tres reinicios)

Misma formulación one-hot; solo cambian capas p, penalización P y evaluaciones por reinicio. U−L = 24,088042. El objetivo entrenado es la energía esperada del QUBO, no P(óptimo).

| p | P | Evaluaciones | P(óptimo) | P(factible) |
|---:|---|---:|---:|---:|
| 1 | U−L+1 = 25,088 (anterior) | 60 | 0,1487 | 0,5375 |
| 1 | U−L+1e-6 = 24,088 (mínimo) | 300 | 0,1451 | 0,5220 |
| 1 | 1,5·(U−L) = 36,132 | 300 | 0,1799 | 0,6750 |
| 2 | U−L+1 | 300 | 0,2289 | 0,8705 |
| 2 | mínimo | 300 | 0,2253 | 0,8535 |
| 2 | 1,5·(U−L) | 300 | 0,2447 | 0,9501 |
| 3 | U−L+1 | 300 | 0,2553 | 0,8784 |
| 3 | mínimo | 300 | 0,2521 | 0,8623 |
| **3** | **1,5·(U−L)** | **300** | **0,2836** | **0,9707** |

Con 60 evaluaciones ninguna configuración superó 0,25. Se adopta la última fila por defecto.

## Referencias experimentales anteriores

`artifacts/reference_two.json` y `artifacts/reference_five.json` conservan resultados del motor experimental schema 1.0, regenerados con `python -m simaphuru.cli --scenario data/scenarios/two_crossings.json --qaoa --seed 7 --output artifacts/reference_two.json` (y `five_crossings.json` para cinco). Ese motor no cambió. Sus costos no son comparables numéricamente con el motor NS/EW del equipo.

## Límites

El motor principal tiene almacenamiento finito por tramo EW y spillback (v2), pero no buses, demanda variable, giros ni desfases optimizados. Las llegadas NS siguen sin límite. El motor experimental ilustra además reducciones de descarga, con otras ecuaciones/entradas/costo.

Los parámetros de ambas vistas son sintéticos. No hay calibración de Javier Prado, validación de campo, benchmark externo SUMO/RESCO ejecutado ni ventaja cuántica demostrada. La presentación final y los datos reales siguen pendientes.

![Experimento ejecutado en navegador](demo_verificada.png)
