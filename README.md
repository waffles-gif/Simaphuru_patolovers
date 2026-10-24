# Simaphuru · Patolovers

Simaphuru simula un corredor de semáforos conectados y elige el plan de cada cruce: primero por enumeración clásica exacta y después con QAOA en Qiskit. Proyecto para Qiskit Fall Fest 2026.

## Problema / Solución

**Problema.** En avenidas congestionadas como Javier Prado, la cola de un cruce llena el tramo hasta el siguiente y bloquea a los autos que vienen detrás (spillback). Programar cada semáforo por separado ignora ese efecto: un plan que mejora un cruce puede empeorar el corredor. El número de combinaciones crece como 2^N con N cruces.

**Solución.** Un simulador de tráfico paso a paso (1 s) con colas NS/EW, capacidad finita K_e por tramo y spillback calcula el costo de cada combinación de planes (demora, cola máxima y cola residual). Esos costos se convierten en un QUBO one-hot, que QAOA resuelve en Qiskit. La interfaz Streamlit compara el resultado con el óptimo clásico exacto, muestra los segundos de bloqueo por cruce y anima el corredor.

## Resultados

| | 2 cruces | 5 cruces |
|---|---|---|
| Óptimo exacto | A=1,B=0 · 17.913 | 1,1,1,0,0 · 48.630 |
| Plan más probable de QAOA | el óptimo | 1,1,0,0,1 · 52.933 (óptimo del modelo por pares) |
| Prob. del óptimo | 28.4 % (azar 25 %) | 3.44 % (azar 3.125 %) |
| Soluciones válidas | 97.1 % | 98.8 % |
| Spillback en el óptimo | 0 s | 150 s |

Configuración: QAOA p=3, P=1.5·(U−L), 300 evaluaciones por reinicio (3 reinicios de Nelder–Mead), semilla 7, vector de estado exacto local (`qiskit.quantum_info.Statevector`), sin hardware ni shots. Plan 0 = NS/EW 30/30 s; plan 1 = 40/20 s. Costos en las unidades del modelo (`C = wD·D/60 + wP·Qmax/30 + wR·R/30`, suma por cruce). Fuentes: `artifacts/team_two.json`, `artifacts/team_five.json` y [docs/VALIDATION.md](docs/VALIDATION.md), que incluye el barrido de p, P y evaluaciones.

## Limitaciones

- Los parámetros son sintéticos (ciclo 68 s, K_e = 12, viaje 20 s, llegadas constantes). No es un gemelo digital de Javier Prado ni está calibrado con aforos reales.
- Una sola instancia de tráfico y una sola semilla del optimizador. La mejora de QAOA sobre elegir al azar es pequeña (28.4 % vs 25 %; 3.44 % vs 3.125 %) y no se ha probado con otras semillas.
- Con 5 cruces el QUBO usa una aproximación por pares de cruces vecinos. Su mejor plan cuesta 8.85 % más que el óptimo real, aunque se resuelva perfectamente; por eso QAOA prefiere ese plan.
- No hay ventaja cuántica: con 4 o 32 combinaciones la enumeración clásica ya da el óptimo exacto en milisegundos. Las probabilidades salen de una simulación exacta, no de hardware.

## Cómo correrlo

Requiere Python 3.11–3.13 (recomendado 3.13). QAOA corre localmente: no necesita cuenta IBM ni token.

```sh
git clone https://github.com/waffles-gif/Simaphuru_patolovers.git
cd Simaphuru_patolovers
python3 -m venv .venv
source .venv/bin/activate            # Windows: py -3.13 -m venv .venv ; .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

python -m pytest                     # pruebas
python -m ruff check .               # estilo
python -m streamlit run app.py       # interfaz: pulsar "Ejecutar experimento"
```

Línea de comandos (mismo motor que la interfaz):

```sh
python model/enumerate.py --out data/model_output.json                                  # costos de 2 cruces
python -m quantum.run_qaoa --input data/model_output.json --out artifacts/team_two.json  # QAOA 2 cruces
python -m quantum.run_qaoa --n 5 --out artifacts/team_five.json                         # QAOA 5 cruces
python model/chain.py                                                                   # error de la aproximación por pares
```

`python -m quantum.run_qaoa --help` muestra las opciones (`--depth`, `--seed`, `--max-evaluations`, `--no-qaoa`). Los resultados locales quedan en `artifacts/`, ignorado por Git salvo los cuatro JSON de referencia.

## Equipo

| Rol | Integrante |
|---|---|
| R1 · Evidencia | Daniel |
| R2 · QUBO y Qiskit | Rafael |
| R3 · Motor de tráfico | Valentino |
| R4 · Interfaz y entrega | Tamara |

Esta entrega parte del [commit ee4eed5 del equipo](https://github.com/waffles-gif/Simaphuru_patolovers/tree/ee4eed52ba3438242aa213532c1eb5761ae5f70e). Ver la [comparación y mejoras priorizadas](docs/COMPARACION_Y_MEJORAS.md). Se conservan el [borrador original](docs/TEAM_DRAFT.md) y `example_result.json` (`example=true`, números ficticios). La vista **Experimental · almacenamiento limitado** es un motor anterior con otras ecuaciones y otro costo (schema 1.0); sus cifras no se comparan con las del motor del equipo.

## Qué incluye el proyecto

- Motor del equipo: corredor EW con colas NS/EW, entradas externas en cada cruce, viaje de 20 s, horizonte 1360 s, almacenamiento finito K_e = 12 por tramo EW y spillback (`team-ns-ew-v2`).
- Dos programas por cruce: NS/EW 30/30 o 40/20 s, ciclo 68 s y dos despejes de 4 s. El plan 1 favorece NS, no el eje EW del corredor.
- Enumeración de 4 o 32 decisiones y referencia clásica por programación dinámica del costo por pares vecinos.
- QUBO one-hot, penalización con cota demostrada y auditoría de 16 o 1024 estados binarios. Dos cruces reproducen los costos; cinco se auditan como aproximación.
- Circuitos QAOA implementados con Qiskit, vector de estado local y ajuste clásico de ángulos.
- Probabilidad factible, masa inválida, costo físico condicionado y probabilidad no condicionada del óptimo físico.
- Interfaz con animación del corredor, exportación JSON, pruebas del motor (incluidos los casos manuales de spillback) e integración; GitHub Actions en Python 3.11 y 3.13.

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

Abrir un pull request a `main` para integrar (durante el hackathon se permite push directo a `main`). No subir `.venv`, tokens, datos personales ni archivos de credenciales. No cambiar unidades, costo u orden de bits sin actualizar contratos, versión y pruebas. Ver [CONTRIBUTING.md](CONTRIBUTING.md).
