# Simaphuru · Patolovers

Base compartida del MVP de tráfico conectado y optimización QUBO/QAOA para Qiskit Fall Fest 2026.

**Stack:** Python 3.13 recomendado (compatibilidad declarada 3.11–3.13), Qiskit 2, Aer/Optimization, NumPy/SciPy, Pydantic, Streamlit, pytest y Ruff. Ejecuta QAOA localmente: no necesita cuenta IBM, token ni hardware remoto. Las dependencias resueltas se fijan en `requirements.lock`.

## Equipo y trabajo previo

| Rol | Integrante |
|---|---|
| R1 · Evidencia y modelo físico | Daniel |
| R2 · QUBO y Qiskit | Rafael |
| R3 · Motor de tráfico | Valentino |
| R4 · Interfaz e integración | Tamara |

Esta entrega se adaptó al [commit ee4eed5 del equipo](https://github.com/waffles-gif/Simaphuru_patolovers/tree/ee4eed52ba3438242aa213532c1eb5761ae5f70e). La opción predeterminada usa su motor `model/traffic.py`, sus llegadas NS/EW, sus costos y su codificación one-hot. Se añadieron QUBO/QAOA, auditoría y Streamlit sobre ese motor. Consultar la [comparación, resultados y mejoras priorizadas](docs/COMPARACION_Y_MEJORAS.md).

Se conservan el [borrador original del equipo](docs/TEAM_DRAFT.md), `data/model_output.json`, `data/chain_output.json` y `example_result.json`. El último tiene `example=true` y números ficticios; los otros dos son salidas del motor del equipo con parámetros ilustrativos. El flujo integrado exporta schema 0.2 con parámetros completos y campos compatibles con 0.1. El motor anterior de almacenamiento finito, schema 1.0 y un bit por cruce queda explícitamente separado como experimental.

## Empezar en cinco minutos

```sh
git clone https://github.com/waffles-gif/Simaphuru_patolovers.git
cd Simaphuru_patolovers
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest
python -m streamlit run app.py
```

En Windows, crear el entorno con `py -3.13 -m venv .venv` y activarlo con `.venv\Scripts\Activate.ps1`; los demás comandos `python -m ...` son iguales. En macOS/Linux, si `python3` apunta a otra versión compatible, puede utilizarse; el entorno comprobado inicialmente es Python 3.13. No instalar paquetes en el Python del sistema.

Abrir la dirección local indicada por Streamlit y pulsar **Ejecutar experimento**. La opción predeterminada es **Motor del equipo · NS/EW**. La instalación inicial requiere internet; los experimentos y la interfaz funcionan localmente después de instalar.

## Ejecutar sin interfaz

```sh
python model/enumerate.py --out data/model_output.json
python -m quantum.run_qaoa --input data/model_output.json --out artifacts/team_two.json
python -m quantum.run_qaoa --n 5 --out artifacts/team_five.json
python -m ruff check .
```

Los resultados locales quedan en `artifacts/`, ignorado por Git salvo los cuatro JSON de referencia incluidos para reproducir la verificación. `python -m quantum.run_qaoa --help` muestra opciones. La entrada 0.1 se verifica regenerando sus costos antes de usarla. `example_result.json` se rechaza como entrada real. La aplicación comparte el mismo motor que la línea de comandos.

## Qué incluye el proyecto

- Motor del equipo: corredor EW con colas NS/EW, entradas externas en cada cruce, viaje de 20 s, horizonte 1360 s, almacenamiento finito K_e = 12 por tramo EW y spillback (`team-ns-ew-v2`).
- Dos programas por cruce: NS/EW 30/30 o 40/20 s, ciclo 68 s y dos despejes de 4 s. El plan 1 favorece NS, no el eje EW del corredor.
- Enumeración de 4 o 32 decisiones y referencia clásica por programación dinámica del costo por pares vecinos.
- QUBO one-hot, penalización con cota demostrada y auditoría de 16 o 1024 estados binarios. Dos cruces reproducen los costos; cinco se auditan como aproximación.
- Circuitos QAOA implementados con Qiskit, vector de estado local y ajuste clásico de ángulos.
- Probabilidad factible, masa inválida, costo físico condicionado y probabilidad no condicionada del óptimo físico.
- Interfaz, exportación, pruebas originales del equipo y nuevas pruebas de integración; GitHub Actions preparado.
- Vista experimental separada que conserva la ampliación anterior de almacenamiento finito, demanda variable y obstrucción agregada.

La verificación local y sus resultados están en `docs/VALIDATION.md`. El estado de las comprobaciones remotas se consulta en la pestaña Actions de GitHub.

**No es una calibración de Javier Prado.** Con cinco cruces, la aproximación vecina elige un plan con costo real 3,55 % mayor que el óptimo en el caso predeterminado. Es una limitación de representación que persiste incluso resolviendo perfectamente ese QUBO. Enumerar los costos ya proporciona el óptimo clásico; no se demuestra ventaja cuántica. Las probabilidades son exactas del simulador cuántico, no conteos de hardware. Ver [resultados ejecutados](docs/VALIDATION.md).

## Organización para trabajar en paralelo

```text
model/                     Motor y enumeración del equipo (rol 3)
quantum/                   QUBO one-hot y entrada QAOA (rol 2)
web/                       Vista del equipo y vista experimental (rol 4)
app.py                     Entrada Streamlit y elección explícita de motor
simaphuru/
  team.py                  Contrato/adaptador del motor R3 y experimento integrado
  quantum.py               Circuitos y entrenamiento Qiskit compartidos
  qubo.py                  QUBO/Ising compartido y sustituto experimental
  models.py, simulation.py Motor experimental con almacenamiento finito
  experiment.py, cli.py     Flujo experimental anterior, identificado como tal
data/model_output.json      Salida original R3 para dos cruces
data/chain_output.json      Auditoría original R3 para cinco cruces
data/scenarios/             Plantillas de la vista experimental
tests/                      Pruebas físicas, matemáticas e integración
docs/                       Modelo, contratos, roles, fuentes y demo
artifacts/                  Referencias publicadas y resultados locales ignorados
.github/workflows/ci.yml    Comprobación automática
```

Consultar [comparación y mejoras](docs/COMPARACION_Y_MEJORAS.md), [roles](docs/ROLES.md), [contratos](docs/CONTRACTS.md) y [guion de demo](docs/DEMO.md). `docs/MODEL.md` describe exclusivamente el motor experimental anterior.

## Antes de compartir cambios

```sh
git switch -c rol3/nombre-del-cambio
python -m pytest
python -m ruff check .
git add <archivos>
git commit -m "Describe el cambio"
git push -u origin rol3/nombre-del-cambio
```

Abrir un pull request a `main` para integrar. No subir `.venv`, tokens, datos personales ni archivos de credenciales. No cambiar unidades, costo u orden de bits sin actualizar contratos, versión y pruebas. Ver [CONTRIBUTING.md](CONTRIBUTING.md).
