# Fuentes y procedencia

## Base actual del equipo

- [Commit ee4eed5](https://github.com/waffles-gif/Simaphuru_patolovers/tree/ee4eed52ba3438242aa213532c1eb5761ae5f70e): motor NS/EW y contrato que se adaptan.
- [Motor de tráfico](https://github.com/waffles-gif/Simaphuru_patolovers/blob/ee4eed52ba3438242aa213532c1eb5761ae5f70e/model/traffic.py): ecuaciones, entradas y costo existentes.
- [Enumeración de dos cruces](https://github.com/waffles-gif/Simaphuru_patolovers/blob/ee4eed52ba3438242aa213532c1eb5761ae5f70e/model/enumerate.py): tabla 0.1 y descomposición local/par.
- [Cadena y error de cinco cruces](https://github.com/waffles-gif/Simaphuru_patolovers/blob/ee4eed52ba3438242aa213532c1eb5761ae5f70e/model/chain.py): aproximación vecina que se mantiene y audita.

Las fuentes de contexto siguientes orientan investigación futura; esta adaptación no incorpora aforos nuevos ni verifica una calibración urbana.

## Escenarios incluidos

Son nuevos supuestos sintéticos, sin datos personales ni aforos reales. El nombre Javier Prado no se usa como identificador de una red calibrada. Las dos plantillas comparten la misma abstracción; cinco cruces son una prueba computacional, no cinco ubicaciones verificadas.

## Documentación técnica

- Qiskit Statevector: https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.quantum_info.Statevector
- QAOA, IBM: https://quantum.cloud.ibm.com/docs/en/tutorials/quantum-approximate-optimization-algorithm
- Streamlit: https://docs.streamlit.io/get-started/installation
- SUMO TripInfo, definiciones y vehículos inconclusos: https://eclipse.dev/sumo/docs/Simulation/Output/TripInfo.html
- RESCO, posible benchmark posterior: https://github.com/Pi-Star-Lab/RESCO

Usar documentación de la versión instalada. El tutorial IBM incluye hardware; el stack de este repositorio utiliza evaluación local.

## Evidencia de contexto para investigar Lima

- ATU, publicación del PMU 2025–2045: https://www.gob.pe/institucion/atu/normas-legales/7530942-395-2025-atu-pe . Parte del diagnóstico/modelo corresponde a 2023.
- LACCEI 2018, Javier Prado: https://www.laccei.org/LACCEI2018-Lima/full_papers/FP409.pdf . Videos de junio de 2014 entre Aviación y Evitamiento. Incluye principal, auxiliares y rampas. Cinco cámaras no equivalen a cinco cruces semaforizados.
- ATU, control territorial y detenciones de buses, abril de 2026: https://www.gob.pe/institucion/atu/noticias/1385134-atu-implementa-control-territorial-para-recuperar-el-orden-y-reducir-la-congestion-en-el-centro-de-lima . Contexto del mecanismo, no tiempos de parada de nuestra red.

No se han incorporado aforos de estas fuentes al código. Para hacerlo: registrar tabla/página, fecha de observación, ámbito, unidades, incertidumbre y transformación realizada.

## Antecedente del equipo

El repositorio anterior https://github.com/rafaelchamayo/patolovers-mvp (commit a3c75eafcac84bad28a6f377adacadb08d2dbc50) contiene un laboratorio JavaScript de un cruce y dos qubits. Sirvió como antecedente de alcance; no se han copiado sus archivos al repositorio Python. Registrar herramientas y contribuciones según las bases de la hackathon.
