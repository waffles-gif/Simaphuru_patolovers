# Casos Manuales para Verificación del Motor de Simulación

**Instrucciones para Rol 1:** Lee cada estado inicial al Rol 3. Ejecuten el simulador por los segundos indicados y verifiquen que el resultado del programa coincida exactamente con la "Salida Física Esperada". Si no coincide, el motor tiene un error de conservación o lógica y los costos del QUBO serán erróneos.

### Caso 1: Flujo Libre (Validación de Descarga)

* **Objetivo:** Comprobar que los autos se mueven correctamente cuando hay espacio y luz verde.

* **Estado Inicial:**

  * Tramo 1 (Origen): 10 vehículos esperando.

  * Tramo 2 (Destino): 0 vehículos (Vacío).

  * Semáforo: VERDE para el flujo principal.

* **Acción:** Avanzar la simulación 10 segundos.

* **Salida Física Esperada:**

  * Con una tasa de 0.5 veh/s, en 10 segundos deben cruzar 5 vehículos.

  * Tramo 1 final: 5 vehículos.

  * Tramo 2 final: 5 vehículos.

* **Check de Rol 3:** \[ \] Validado en código.

### Caso 2: Bloqueo Aguas Arriba - Spillback (El Caso Crítico)

* **Objetivo:** Comprobar que el simulador respeta el límite físico de almacenamiento ($K_e = 12$) sin importar la luz del semáforo. Esto simula el problema central de Javier Prado.

* **Estado Inicial:**

  * Tramo 1 (Origen): 10 vehículos esperando.

  * Tramo 2 (Destino): 12 vehículos (LLENO, $K_e$ alcanzado).

  * Semáforo: VERDE para el flujo principal.

* **Acción:** Avanzar la simulación 10 segundos.

* **Salida Física Esperada:**

  * Como el destino no tiene espacio, la transferencia de autos debe ser CERO, a pesar del semáforo en verde.

  * Tramo 1 final: 10 vehículos.

  * Tramo 2 final: 12 vehículos.

* **Check de Rol 3:** \[ \] Validado en código.

### Caso 3: Despeje y Cambio de Fase

* **Objetivo:** Verificar que en los 4 segundos de despeje (ámbar/todo rojo) no haya movimiento de autos, evitando colisiones lógicas.

* **Estado Inicial:**

  * Tramo 1 (Origen): 5 vehículos.

  * Semáforo: Cambiando de Fase Principal a Fase Transversal (iniciando los 4s de despeje).

* **Acción:** Avanzar la simulación exactamente 4 segundos.

* **Salida Física Esperada:**

  * Transferencia de vehículos: 0.

  * Inventarios intactos (Tramo 1 final: 5 vehículos). El movimiento solo debe reanudarse al segundo 5 si la nueva fase tiene verde y destino libre.

* **Check de Rol 3:** \[ \] Validado en código.