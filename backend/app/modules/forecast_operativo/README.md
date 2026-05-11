# Forecast Operativo

Nombre técnico interno del módulo de pronóstico mensual. Su función es cargar el modelo entrenado y devolver proyecciones de ingresos o margen para los siguientes meses.

## Qué hace este módulo

- Recibe la solicitud desde la API.
- Busca el modelo en disco.
- Ejecuta la predicción con el horizonte solicitado.
- Devuelve la respuesta lista para que el frontend la pinte en tabla o gráfico.

## Qué no hace este módulo

- No entrena el modelo desde cero.
- No obtiene datos desde Snowflake por sí solo.
- No dibuja gráficos ni tablas.

## Dónde copiar el modelo

Copiar aquí los archivos entrenados:

- `app/modules/forecast_operativo/artifacts/models/`

Nombres recomendados:

- `forecast_model.pkl`
- `forecast_model.joblib`
- `forecast_metadata.json`

Si quieres apuntar a otro archivo, define `MODEL_FILE` en el entorno.

## Nombre comercial visible

Este módulo se mostrará al usuario final como `Margen de Contratos (Series de tiempo)`.

