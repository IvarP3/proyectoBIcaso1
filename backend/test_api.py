"""
Simula la llamada API que hace el frontend al backend
"""
import pickle
import sys

sys.path.insert(0, '.')

from app.core.config import Settings
from app.modules.forecast_operativo.services.forecast_service import ForecastService
from pathlib import Path

print("🔧 Simulando llamada API al dashboard...\n")

try:
    # Crear settings
    settings = Settings()
    
    # Crear servicio
    service = ForecastService(settings)
    
    # Llamar al dashboard (como lo haría el endpoint)
    print("📡 Llamando a get_dashboard_completo()...")
    dashboard = service.get_dashboard_completo()
    
    print("✅ Dashboard obtenido correctamente:\n")
    print(f"  Forecast: {dashboard.forecast.horizon_months} meses")
    print(f"  Primer mes: {dashboard.forecast.items[0].month if dashboard.forecast.items else 'N/A'}")
    print(f"  Margen primer mes: {dashboard.forecast.items[0].projected_income_bob:,.0f} Bs" if dashboard.forecast.items else "N/A")
    
    print(f"\n  Métricas MAPE: {dashboard.metricas.mape_pct:.1f}%")
    print(f"  Cumple umbral: {dashboard.metricas.cumple_umbral}")
    
    print(f"\n  Media histórica: {dashboard.stats_historicos.media_margen_bs:,.0f} Bs")
    print(f"  Volatilidad (CV): {dashboard.stats_historicos.cv_pct:.1f}%")
    
    print(f"\n  Meses históricos: {len(dashboard.serie_historica.meses)}")
    print(f"  Rutas: {len(dashboard.analisis_ruta)}")
    print(f"  Clientes: {len(dashboard.analisis_cliente)}")
    
    print(f"\n  Reglas prescriptivas: {len(dashboard.reglas_prescriptivas)}")
    print(f"  Umbrales: {len(dashboard.umbrales)}")
    
    print("\n" + "="*60)
    print("✨ El backend está listo y sirviendo datos correctamente")
    print("="*60)
    print("\n⚠️  Si el frontend sigue mostrando error:")
    print("   1. Asegúrate de que ambos servidores estén corriendo")
    print("   2. Recarga la página (Ctrl+F5 para limpiar cache)")
    print("   3. Abre la consola del navegador (F12) para ver logs")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
