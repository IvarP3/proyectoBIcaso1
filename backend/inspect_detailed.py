import pickle

pkl_path = 'app/modules/forecast_operativo/artifacts/models/transfreezer_modelo_ts.pkl'

with open(pkl_path, 'rb') as f:
    artifact = pickle.load(f)

print("🔍 Estructura detallada del pickle:\n")

# Forecast
print("📊 FORECAST (primeros 2):")
forecast = artifact.get('forecast', [])
for i, item in enumerate(forecast[:2]):
    print(f"  Item {i}: {item}")

# Serie histórica
print("\n📉 SERIE_HISTORICA:")
serie = artifact.get('serie_historica', {})
if serie:
    print(f"  Claves: {list(serie.keys())}")
    for key in serie:
        val = serie[key]
        if isinstance(val, list):
            print(f"  {key}: {len(val)} items")
            if val:
                print(f"    Primero: {val[0]}")
else:
    print("  (vacío)")

# Análisis ruta
print("\n🗺️  ANALISIS_RUTA (primeros 2):")
rutas = artifact.get('analisis_ruta', [])
for i, item in enumerate(rutas[:2]):
    print(f"  Item {i}: {item}")

# Análisis cliente
print("\n👥 ANALISIS_CLIENTE (primeros 2):")
clientes = artifact.get('analisis_cliente', [])
for i, item in enumerate(clientes[:2]):
    print(f"  Item {i}: {item}")

# Reglas prescriptivas
print("\n💼 REGLAS_PRESCRIPTIVAS:")
rules = artifact.get('reglas_prescriptivas', {})
for key, val in rules.items():
    print(f"  {key}: {val[:50]}...")
