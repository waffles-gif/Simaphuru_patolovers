# Guion del pitch (2:45 min)

## 1. Problema (0:00–0:30, 30 s)

En Javier Prado, en hora punta, un tramo de 3,5 km puede tomar hasta dos horas. Una causa es el spillback: la cola de un cruce llena el tramo hasta el siguiente y bloquea el cruce anterior, aunque tenga luz verde.

Si cada semáforo se programa por separado, ese efecto no se ve. Un plan que mejora un cruce puede empeorar el corredor. Y las combinaciones crecen como 2^N: con 5 cruces y dos planes por cruce ya son 32.

## 2. Solución (0:30–1:15, 45 s)

Construimos un simulador de tráfico que avanza segundo a segundo. Cada cruce tiene colas norte-sur y este-oeste. Cada tramo este-oeste guarda como máximo 12 autos, contando la cola y los que van en camino. Si el tramo siguiente está lleno, el cruce no deja salir a nadie aunque tenga verde.

Cada cruce elige entre dos planes: 30/30 o 40/20 segundos de verde. El simulador calcula el costo de cada combinación con la demora, la cola máxima y la cola que queda al final.

Esos costos se convierten en un QUBO: cada cruce usa dos qubits, uno por plan, y una penalización obliga a elegir exactamente un plan por cruce. QAOA en Qiskit resuelve ese QUBO, y comparamos el resultado con el óptimo exacto que obtenemos enumerando todas las combinaciones.

## 3. Demo (1:15–2:15, 60 s)

En Streamlit, motor del equipo, 2 cruces.

1. Pulsar **Ejecutar experimento**.
2. Mostrar la tabla de combinaciones. Señalar la columna `blocked_s`: en el óptimo (A=1, B=0) es 0 segundos. En las otras tres combinaciones el cruce A queda bloqueado 43, 234 y 38 segundos. El plan óptimo es el que evita el spillback.
3. Bajar a la sección de Qiskit. Mostrar que el 97 % de la probabilidad cae en soluciones válidas, con un plan por cruce, y que QAOA encuentra el óptimo el 28,4 % de las veces. Al azar sería 25 %.
4. Si hay tiempo, mostrar la animación del corredor para el plan óptimo.

## 4. Resultados y limitaciones (2:15–2:45, 30 s)

Con 2 cruces, QAOA respeta la restricción casi siempre y encuentra el óptimo un poco más que al azar. Con 5 cruces el QUBO usa una aproximación por pares de cruces vecinos, y su mejor plan cuesta 8,85 % más que el óptimo real. Los parámetros son sintéticos y usamos una sola semilla.

Cierre: medimos todo contra el óptimo exacto. QAOA ya respeta las restricciones; encontrar el óptimo depende de más capas y de mejores modelos.

## Preguntas probables del jurado

**¿Por qué cuántico si lo clásico gana?**
Con 4 o 32 combinaciones lo clásico gana, y lo decimos. Usamos ese óptimo exacto como referencia para medir a QAOA con honestidad. El interés está en corredores grandes, donde enumerar ya no es posible; no afirmamos ventaja cuántica.

**¿Dónde corrió QAOA?**
En una simulación exacta de vector de estado en Qiskit (`Statevector`), en una laptop. No usamos hardware ni shots, así que las probabilidades son exactas.

**¿Cómo eligieron P?**
P tiene que ser mayor que U−L, la diferencia entre el costo de un plan válido y la cota inferior del costo. Así ningún estado inválido puede ser el mínimo. Probamos el mínimo, U−L+1 y 1,5·(U−L), con p = 1, 2 y 3. La mejor combinación fue 1,5·(U−L) con p = 3 y 300 evaluaciones.

**¿Por qué 5 cruces es aproximado?**
Un QUBO solo tiene términos de a pares. El costo de un cruce lejano depende de los planes de todos los cruces anteriores. Con 2 cruces la representación es exacta; con 5 la aproximamos con pares de cruces vecinos y medimos el error contra el simulador completo.

**¿Los datos son reales?**
No. Los parámetros son sintéticos: ciclo de 68 s, 12 autos por tramo, 20 s de viaje y llegadas constantes. Las cifras de Javier Prado motivan el problema, pero el modelo no está calibrado con aforos reales.
