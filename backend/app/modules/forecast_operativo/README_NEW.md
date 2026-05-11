# Módulo: Proyección de Ingresos

**Nombre interno:** `forecast_operativo`  
**Nombre comercial:** `Proyección de Ingresos`

## Descripción

Sistema de pronóstico predictivo y prescriptivo basado en **análisis de series de tiempo (SARIMA)** que integra:

- **Analítica Descriptiva:** Visualización de ingresos, gastos y penalizaciones históricas
- **Analítica Diagnóstica:** Rentabilidad por ruta y cliente
- **Analítica Predictiva:** Pronóstico de 6 meses con intervalos de confianza al 90%
- **Analítica Prescriptiva:** Recomendaciones tácticas por nivel de demanda

## Arquitectura

### Backend

```
forecast_operativo/
├── controllers/forecast_controller.py     # Endpoints REST
├── services/forecast_service.py           # Lógica de negocio (carga pkl, expone datos)
├── repositories/model_repository.py       # I/O de archivos (.pkl)
├── schemas/forecast_schema.py             # Modelos Pydantic (request/response)
├── artifacts/models/
│   └── transfreezer_modelo_ts.pkl        # Modelo entrenado + metadatos + análisis
└── README.md                              # Este archivo
```

### Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/forecast-operativo` | GET | Pronóstico 6 meses (parámetro `horizon` opcional) |
| `/api/v1/forecast-operativo/metricas` | GET | Métricas de calidad del modelo (MAE, RMSE, MAPE, AIC) |
| `/api/v1/forecast-operativo/historicos` | GET | Estadísticas históricas (media, CV, ingresos, margen) |
| `/api/v1/forecast-operativo/serie` | GET | Serie histórica de 15 meses (para gráficos) |
| `/api/v1/forecast-operativo/ruta` | GET | Margen por ruta y eficiencia |
| `/api/v1/forecast-operativo/cliente` | GET | Margen por cliente y penalizaciones |
| `/api/v1/forecast-operativo/dashboard` | GET | **Agregado completo** para dashboard (recomendado) |

## Artefacto `.pkl`

El archivo `transfreezer_modelo_ts.pkl` contiene:

```python
{
    'metadata': {
        'fecha_entrenamiento': str,
        'empresa': 'Transfreezer',
        'modelo_nombre': 'SARIMA(1,1,0)x(1,1,0,4)',  # Tipo de modelo
        'n_meses_entrenamiento': 15,
        'periodo_entrenamiento': 'Enero 2025 – Marzo 2026',
        'horizonte_forecast_meses': 6,
        'nivel_confianza': 0.90
    },
    'modelo_fitted': <SARIMAX fitted model>,  # Objeto statsmodels
    'metricas': {
        'MAE_Bs': float,           # Error medio absoluto
        'RMSE_Bs': float,          # Raíz del error cuadrado medio
        'MAPE_pct': float,         # Error porcentual absoluto medio
        'AIC': float,              # Criterio de información de Akaike
        'cumple_umbral_25pct': bool
    },
    'forecast': [
        {
            'Mes': '2026-04',
            'Margen_Proyectado_Bs': 138400.0,
            'IC_Inferior_Bs': 128900.0,
            'IC_Superior_Bs': 147800.0,
            'Nivel_Demanda': 'MEDIO'
        },
        # ... 5 meses más
    ],
    'stats_historicos': { ... },
    'serie_historica': { ... },
    'analisis_ruta': [ ... ],
    'analisis_cliente': [ ... ],
    'reglas_prescriptivas': { ... },
    'umbrales': { ... }
}
```

## Flujo de Datos

1. **Backend (FastAPI)**
   - Carga el `.pkl` una sola vez en memoria (caching)
   - Expone endpoints que deserializan y sirven subconjuntos de datos
   - API responde con Pydantic models tipados

2. **Frontend (Next.js React)**
   - Llama a `/api/v1/forecast-operativo/dashboard` en `useEffect`
   - Recibe datos completos de forma estructurada
   - Renderiza dashboard con KPIs, gráficos dinámicos y recomendaciones

## Modelo Técnico

**Tipo:** SARIMA  
**Entrenamiento:** 12 meses (2025)  
**Validación:** 3 meses (2026 enero–marzo)  
**Predicción:** 6 meses (abril–septiembre 2026)  
**MAPE esperado:** 20–25%

## Instalación & Deployment

### Backend
```bash
cd backend
python -m uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install recharts  # Si no está instalado
npm run dev
```

### Acceder
- **Dashboard:** `http://localhost:3000/modules/forecast`
- **API Docs:** `http://127.0.0.1:8000/docs`

---

**Última actualización:** Abril 2026  
**Responsable:** Análisis Predictivo | Transfreezer
