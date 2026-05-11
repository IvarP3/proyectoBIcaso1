# Torre de Control SIO

Nombre técnico interno (`mineria`) para el módulo operativo de analítica comercial y machine learning.

## Propósito

- Explorar patrones de clientes, rutas, contratos y alertas operativas.
- Segmentar viajes por riesgo y condición logística.
- Sugerir prioridades de atención y escalamiento.

## Estado

- Implementado como módulo FastAPI bajo `/api/v1/torre-control-sio`.
- Consume `best_model.pkl` desde `app/modules/mineria/artifacts/models`.
- Mantiene el nombre interno `mineria` para no romper la arquitectura.

## Nombre comercial visible

El módulo se muestra al usuario final como `Torre de Control SIO (Minería de Datos)`.

