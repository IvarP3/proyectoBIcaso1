import pickle
import os

pkl_path = 'app/modules/forecast_operativo/artifacts/models/transfreezer_modelo_ts.pkl'

if os.path.exists(pkl_path):
    try:
        with open(pkl_path, 'rb') as f:
            artifact = pickle.load(f)
        
        print(f"Tipo de contenido: {type(artifact)}")
        print(f"Es diccionario: {isinstance(artifact, dict)}")
        
        if isinstance(artifact, dict):
            print(f"Claves: {list(artifact.keys())}")
        else:
            print(f"Contenido: {dir(artifact)}")
            # Si es un modelo SARIMA
            if hasattr(artifact, 'fittedvalues'):
                print("✓ Es un modelo statsmodels (SARIMAX)")
            
    except Exception as e:
        print(f"Error al cargar: {e}")
else:
    print(f"Archivo no encontrado en: {pkl_path}")
    print(f"Cwd: {os.getcwd()}")
    print(f"Archivos en artifacts/models/:")
    try:
        for f in os.listdir('app/modules/forecast_operativo/artifacts/models/'):
            print(f"  - {f}")
    except:
        print("  (No se puede listar el directorio)")
