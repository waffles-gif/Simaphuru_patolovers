# Colaboración

1. Leer `docs/ROLES.md`, `docs/MODEL.md` y `docs/CONTRACTS.md`.
2. Crear rama: `rol1/datos`, `rol2/qubo`, `rol3/simulacion` o `rol4/interfaz`.
3. Mantener los cambios en el módulo propio. Acordar cambios de contratos antes de implementarlos.
4. Añadir o ajustar pruebas significativas del comportamiento que cambió.
5. Ejecutar `python -m pytest` y `python -m ruff check .`.
6. Abrir un pull request pequeño con problema, comportamiento resultante y validación.

No modificar `requirements.lock` a mano: se regenera desde un entorno limpio y se comprueba la instalación. No subir entornos virtuales, credenciales ni resultados pesados. Las versiones Python del CI son la referencia de compatibilidad.

No afirmar que un escenario es empírico sin fuente, fecha, unidad y ámbito. No etiquetar un QUBO aproximado como exacto. Registrar el uso y procedencia de herramientas y materiales según las bases de la hackathon.

El repositorio no establece todavía una licencia de distribución: el propietario/equipo debe decidirla. La adaptación incorpora el motor del equipo desde el commit indicado en `docs/COMPARACION_Y_MEJORAS.md`; el antecedente JavaScript no se copió. Las fuentes conceptuales se citan en `docs/SOURCES.md`.
