import pickle

try:
    with open('app/modules/forecast_operativo/artifacts/models/transfreezer_modelo_ts.pkl', 'rb') as f:
        artifact = pickle.load(f)
    
    print('✓ Modelo cargado correctamente')
    print(f'  Metadata modelo: {artifact["metadata"]["modelo_nombre"]}')
    print(f'  Forecast items: {len(artifact["forecast"])} meses')
    print(f'  Series históricas: {len(artifact["serie_historica"]["meses"])} meses')
    print(f'  Rutas analizadas: {len(artifact["analisis_ruta"])}')
    print(f'  Clientes: {len(artifact["analisis_cliente"])}')
    print(f'  MAPE: {artifact["metricas"]["MAPE_pct"]:.1f}%')
    print(f'  MAE: {artifact["metricas"]["MAE_Bs"]:,.0f} Bs')
    print(f'  Cumple umbral (MAPE<25%): {artifact["metricas"]["cumple_umbral_25pct"]}')
    print('')
    print('✓ Todos los datos listos para el dashboard')
except Exception as e:
    print(f'✗ Error: {e}')
