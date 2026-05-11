import pickle
import sys

pkl_path = 'app/modules/forecast_operativo/artifacts/models/transfreezer_modelo_ts.pkl'

try:
    print("🔍 Cargando pickle con método mejorado...")
    with open(pkl_path, 'rb') as f:
        artifact = pickle.load(f)
    
    print("✓ Modelo cargado correctamente")
    print(f"  Tipo: {type(artifact).__name__}")
    print(f"  Claves principales: {list(artifact.keys())}")
    
    # Validar estructura
    required = ['forecast', 'metricas', 'stats_historicos']
    for key in required:
        if key in artifact:
            print(f"  ✓ {key}: presente")
        else:
            print(f"  ✗ {key}: FALTANTE")
            sys.exit(1)
    
    # Detalles del forecast
    forecast = artifact.get('forecast', [])
    print(f"\n📊 Forecast:")
    print(f"  Items: {len(forecast)}")
    if forecast:
        print(f"  Primer mes: {forecast[0].get('Mes', 'N/A')}")
        print(f"  Margen: {forecast[0].get('Margen_Proyectado_Bs', 'N/A')}")
    
    # Metricas
    metricas = artifact.get('metricas', {})
    print(f"\n📈 Métricas:")
    print(f"  MAPE: {metricas.get('MAPE_pct', 'N/A')}%")
    print(f"  MAE: {metricas.get('MAE_Bs', 'N/A')} Bs")
    
    # Stats
    stats = artifact.get('stats_historicos', {})
    print(f"\n📉 Estadísticas:")
    print(f"  Media margen: {stats.get('media_margen_Bs', 'N/A')} Bs")
    print(f"  Serie histórica: {len(stats.get('meses', []))} meses")
    
    print("\n✅ Artefacto validado correctamente. Dashboard listo para usar.")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
