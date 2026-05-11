import pickle
import json
from datetime import datetime

# Simulamos la estructura que espera el frontend
pkl_path = 'app/modules/forecast_operativo/artifacts/models/transfreezer_modelo_ts.pkl'

with open(pkl_path, 'rb') as f:
    artifact = pickle.load(f)

# Construir la respuesta del dashboard (como lo haría el backend)
dashboard_response = {
    "forecast": {
        "module": "Proyección de Ingresos",
        "horizon_months": 6,
        "source_model": artifact.get('metadata', {}).get('modelo_nombre', 'SARIMA'),
        "items": artifact.get('forecast', [])[:6]
    },
    "metricas": {
        "mae_bs": artifact.get('metricas', {}).get('MAE_Bs', 0),
        "rmse_bs": artifact.get('metricas', {}).get('RMSE_Bs', 0),
        "mape_pct": artifact.get('metricas', {}).get('MAPE_pct', 0),
        "aic": artifact.get('metricas', {}).get('AIC', 0),
        "cumple_umbral": artifact.get('metricas', {}).get('cumple_umbral_25pct', False)
    },
    "stats_historicos": artifact.get('stats_historicos', {}),
    "serie_historica": artifact.get('serie_historica', {}),
    "analisis_ruta": artifact.get('analisis_ruta', []),
    "analisis_cliente": artifact.get('analisis_cliente', []),
    "reglas_prescriptivas": artifact.get('reglas_prescriptivas', {}),
    "umbrales": artifact.get('umbrales', {})
}

print("✅ Respuesta del dashboard simulada:")
print(f"  Forecast items: {len(dashboard_response['forecast']['items'])}")
print(f"  Rutas analizadas: {len(dashboard_response['analisis_ruta'])}")
print(f"  Clientes analizados: {len(dashboard_response['analisis_cliente'])}")
print(f"  Meses históricos: {len(dashboard_response['serie_historica'].get('meses', []))}")
print(f"  MAPE del modelo: {dashboard_response['metricas']['mape_pct']:.1f}%")
print("\n✨ El dashboard está listo. Recarga la página en el navegador.")
