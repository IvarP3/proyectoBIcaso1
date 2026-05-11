"""
diagnose_scale.py — Diagnóstico de escala: Real vs. Predicho
Ejecutar desde: backend/
  cd backend && .venv\Scripts\python diagnose_scale.py
"""

import pickle
import numpy as np

PKL = "app/modules/forecast_operativo/artifacts/models/transfreezer_modelo_ts.pkl"

with open(PKL, "rb") as f:
    artifact = pickle.load(f)

# ── Datos reales (escala original) ─────────────────────────────────────────────
serie = artifact.get("serie_historica", {})
meses   = list(serie.get("meses", []))
actual  = np.asarray(serie.get("margen_neto_bs", []), dtype=float)

print("=" * 70)
print("SERIE HISTÓRICA (escala original, en Bs)")
print("=" * 70)
for m, v in zip(meses, actual):
    print(f"  {m}: {v:>12,.0f} Bs")

print(f"\n  Mín: {actual.min():,.0f} Bs")
print(f"  Máx: {actual.max():,.0f} Bs")
print(f"  Media: {actual.mean():,.0f} Bs")

# ── Modelo fitted ─────────────────────────────────────────────────────────────
model = artifact.get("modelo_fitted")
if model is None:
    print("\n⚠️  No hay 'modelo_fitted' en el artefacto.")
else:
    print("\n" + "=" * 70)
    print("PREDICCIONES IN-SAMPLE (con modelo_fitted)")
    print("=" * 70)

    # Método 1: fittedvalues
    fitted = getattr(model, "fittedvalues", None)
    if fitted is not None:
        fitted_arr = np.asarray(fitted, dtype=float)
        print(f"\n  fittedvalues (sin expm1) — primeros 3 valores:")
        print(f"    {fitted_arr[:3].tolist()}")
        print(f"    Rango: [{fitted_arr.min():.4f}, {fitted_arr.max():.4f}]")

        fitted_orig = np.expm1(np.clip(fitted_arr, -50, 50))
        print(f"\n  fittedvalues (CON expm1) — primeros 3 valores:")
        print(f"    {fitted_orig[:3].tolist()}")
        print(f"    Rango: [{fitted_orig.min():,.0f}, {fitted_orig.max():,.0f}] Bs")

    # Método 2: get_prediction
    try:
        pred = model.get_prediction(start=0, end=len(actual) - 1)
        pm_log = np.asarray(pred.predicted_mean, dtype=float)
        print(f"\n  get_prediction (sin expm1) — primeros 3 valores:")
        print(f"    {pm_log[:3].tolist()}")

        pm_orig = np.expm1(np.clip(pm_log, -50, 50))
        print(f"\n  get_prediction (CON expm1) — primeros 3 valores:")
        print(f"    {pm_orig[:3].tolist()}")
        print(f"    Rango: [{pm_orig.min():,.0f}, {pm_orig.max():,.0f}] Bs")

        # Comparación real vs. predicho
        print("\n" + "=" * 70)
        print("COMPARACIÓN: Real vs. Predicho (get_prediction + expm1)")
        print("=" * 70)
        n = min(len(meses), len(pm_orig))
        for i in range(n):
            err = actual[i] - pm_orig[i]
            pct = abs(err) / actual[i] * 100 if actual[i] != 0 else 0
            print(f"  {meses[i]}  real={actual[i]:>10,.0f}  pred={pm_orig[i]:>10,.0f}  err={err:>+10,.0f}  ({pct:.1f}%)")

        mae  = np.mean(np.abs(actual[:n] - pm_orig[:n]))
        mape = np.mean(np.abs((actual[:n] - pm_orig[:n]) / actual[:n]) * 100)
        print(f"\n  MAE  = {mae:,.0f} Bs")
        print(f"  MAPE = {mape:.2f}%")

    except Exception as e:
        print(f"\n  ⚠️  get_prediction falló: {e}")

# ── Forecast (ya en escala original) ────────────────────────────────────────
fc = artifact.get("forecast", [])
print("\n" + "=" * 70)
print("FORECAST (artefacto — ya en escala original)")
print("=" * 70)
for row in fc:
    print(f"  {row.get('Mes','?')}  proyectado={row.get('Margen_Proyectado_Bs',0):>10,.0f} Bs  "
          f"  IC=[{row.get('IC_Inferior_Bs',0):>10,.0f}, {row.get('IC_Superior_Bs',0):>10,.0f}]")
