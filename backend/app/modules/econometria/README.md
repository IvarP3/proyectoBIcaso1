# Econometría

Nombre técnico interno: `econometria`  
Nombre comercial: `Rentabilidad B2B (Econometría)`

## Estado actual

Submódulo operativo implementado: **Predicción + Simulación operativa de contratos**.

## Arquitectura

```
econometria/
├── controllers/econometria_controller.py
├── services/model_bundle_service.py
├── services/prediction_service.py
├── repositories/model_bundle_repository.py
├── schemas/econometria_schema.py
└── artifacts/models/
```

## Endpoints

- `GET /api/v1/econometria/resumen-ejecutivo`
- `GET /api/v1/econometria/analitica-descriptiva`
- `GET /api/v1/econometria/modelos-econometricos`
- `POST /api/v1/econometria/prediccion`
- `POST /api/v1/econometria/simulacion`
- `GET /api/v1/econometria/resumen-modelo`

## Contrato de predicción

Entrada (`POST /prediccion`):

- `peso_kg`
- `distancia_km`
- `altitud_msnm`
- `penalizacion_bs`
- `siniestros_bs`
- `nivel_sla` (`ESTÁNDAR`/`ESTANDAR`/`ORO`/`PLATINO`)
- `es_division_farma`
- `puntaje_chofer`

Salida:

- `margen_predicho_bs`
- `intervalo_confianza_95`
- `nivel_sla`
- `division`
- `alertas`
- `rentable`

## Bundle requerido

El servicio intenta cargar el bundle en este orden:

1. `app/modules/econometria/artifacts/models/transfreezer_modelo_econometrico_v1.pkl`
2. `app/modules/econometria/artifacts/models/transfreezer_modelo_econometrico_v1.plk`
3. `app/modules/forecast_operativo/artifacts/models/transfreezer_modelo_econometrico_v1.pkl`
4. `app/modules/forecast_operativo/artifacts/models/transfreezer_modelo_econometrico_v1.plk`
5. `app/modules/forecast_operativo/artifacts/models/transfreezer_modelo_ts.pkl` (fallback)

