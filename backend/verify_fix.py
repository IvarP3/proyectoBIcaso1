"""
verify_fix.py — Verifica que el fix de burn-in funciona correctamente.
Ejecutar desde: backend/
  .venv\Scripts\python verify_fix.py
"""

import pickle
import numpy as np

PKL = "app/modules/forecast_operativo/artifacts/models/transfreezer_modelo_ts.pkl"

with open(PKL, "rb") as f:
    artifact = pickle.load(f)

serie = artifact.get("serie_historica", {})
meses  = list(serie.get("meses", []))
actual = np.asarray(serie.get("margen_neto_bs", []), dtype=float)
model  = artifact.get("modelo_fitted")

def safe_expm1(values):
    return np.expm1(np.clip(np.asarray(values, dtype=float), -50, 50))

# Simular el _build_validation con el fix
prediction = model.get_prediction(start=0, end=len(actual) - 1)
pred_log = np.asarray(prediction.predicted_mean, dtype=float)
predicho = safe_expm1(pred_log)

conf_int = prediction.conf_int(alpha=0.10)
lower = safe_expm1(np.asarray(conf_int.iloc[:, 0], dtype=float))
upper = safe_expm1(np.asarray(conf_int.iloc[:, 1], dtype=float))

max_historico = float(actual.max())
valid_mask = (
    ~np.isnan(predicho)
    & (predicho > 0)
    & (predicho <= max_historico * 10)
)

print("=" * 70)
print("VALIDACION CON FIX (burn-in filtrado)")
print("=" * 70)
print(f"\nPuntos totales:  {len(actual)}")
print(f"Puntos válidos:  {valid_mask.sum()}")
print(f"Puntos filtrados: {(~valid_mask).sum()}")

valid_errors = []
valid_pcts   = []
valid_ics    = []

for i, (mes, real, pred, ic_lo, ic_hi) in enumerate(
    zip(meses, actual, predicho, lower, upper)
):
    tag = "✓" if valid_mask[i] else "⚠ FILTRADO"
    if not valid_mask[i]:
        print(f"\n  [{tag}] {mes}  real={real:>10,.0f}  pred={pred:>10,.2f}")
        continue

    err = real - pred
    err_abs = abs(err)
    err_pct = err_abs / real * 100 if real != 0 else 0.0
    dentro = real >= ic_lo and real <= ic_hi

    valid_errors.append(err_abs)
    valid_pcts.append(err_pct)
    valid_ics.append(dentro)

    ic_sym = "✓" if dentro else "✗"
    print(f"  {mes}  real={real:>10,.0f}  pred={pred:>10,.0f}  err={err:>+10,.0f}  ({err_pct:.1f}%)  IC:{ic_sym}")

if valid_errors:
    print(f"\n  MAE  = {np.mean(valid_errors):,.0f} Bs")
    print(f"  MAPE = {np.mean(valid_pcts):.2f}%")
    print(f"  Cobertura IC = {np.mean(valid_ics)*100:.1f}%")

print("\n" + "=" * 70)
print("FORECAST (escala original — sin cambios)")
print("=" * 70)
for row in artifact.get("forecast", []):
    print(f"  {row.get('Mes','?')}  {row.get('Margen_Proyectado_Bs',0):>10,.0f} Bs")
