# Abrir esta entrega

Esta carpeta contiene el código y documentación del repositorio https://github.com/waffles-gif/Simaphuru_patolovers . No incluye el entorno virtual ni credenciales.

1. Instalar Python 3.13 (recomendado).
2. Abrir una terminal dentro de esta carpeta.
3. Crear y activar el entorno e instalar:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Windows: usar `py -3.13 -m venv .venv` y `.venv\Scripts\Activate.ps1` para los dos primeros pasos; después los comandos `python -m ...` son iguales.

La opción predeterminada **Motor del equipo · NS/EW** utiliza los archivos actuales del equipo en `model/`. Ajustar cruces, llegadas y viaje; pulsar **Ejecutar experimento**. Compara las decisiones y ejecuta QAOA local. No depende de IBM Cloud. Los parámetros son ilustrativos.

La opción **Experimental · almacenamiento limitado** conserva el motor de la entrega anterior, con otros supuestos y otro costo. No mezclar sus cifras con las del motor del equipo. Si ya habías instalado la versión anterior, vuelve a ejecutar `python -m pip install -r requirements.txt` antes de abrirla.

En macOS, si aparece un error de certificados al instalar, utilizar `PIP_CERT=/etc/ssl/cert.pem python -m pip install -r requirements.txt`.

Para trabajar: `docs/ROLES.md`. Para conocer las diferencias y siguientes pasos: `docs/COMPARACION_Y_MEJORAS.md`. Para comprobar resultados ejecutados: `docs/VALIDATION.md`. El README contiene el árbol del proyecto y comandos de pruebas.
