from pydantic import BaseModel, Field
from typing import Any


class ForecastItem(BaseModel):
    month: str
    projected_income_bob: float = Field(ge=0)
    lower_bound_bob: float = Field(ge=0)
    upper_bound_bob: float = Field(ge=0)
    suggested_action: str


class ForecastResponse(BaseModel):
    module: str
    horizon_months: int
    source_model: str
    items: list[ForecastItem]


class MetricasResponse(BaseModel):
    mae_bs: float
    rmse_bs: float
    mape_pct: float
    aic: float
    cumple_umbral: bool


class StatsHistoricosResponse(BaseModel):
    media_margen_bs: float
    std_margen_bs: float
    cv_pct: float
    ingreso_total_bs: float
    margen_neto_total_bs: float
    pct_margen_global: float


class SerieHistoricaResponse(BaseModel):
    meses: list[str]
    margen_neto_bs: list[float]
    ingreso_bs: list[float]
    num_contratos: list[int]


class AnalisisRutaItem(BaseModel):
    ruta: str
    margen_neto_bs: float
    pct_margen: float
    margen_por_kg: float
    num_contratos: int


class AnalisisClienteItem(BaseModel):
    cliente: str
    nivel_sla: str | None = None
    margen_neto_bs: float
    num_contratos: int
    penalizacion_bs: float
    margen_por_contrato: float | None = None


class ModeloDiagnosticoResponse(BaseModel):
    estado_modelo: str
    mae_bs: float
    rmse_bs: float
    mape_pct: float
    aic: float
    cumple_umbral: bool
    umbral_mape_pct: float
    fecha_entrenamiento: str
    version: str
    modelo_nombre: str
    tipo: str
    orden: str | None = None
    nivel_confianza: float
    periodo_entrenamiento: str
    n_meses_entrenamiento: int
    horizonte_forecast_meses: int


class ValidacionPredictivaItem(BaseModel):
    periodo: str
    real_bs: float
    predicho_bs: float
    error_bs: float
    error_pct: float
    dentro_ic: bool


class ValidacionPredictivaResponse(BaseModel):
    mae_bs: float
    rmse_bs: float
    mape_pct: float
    cobertura_ic_pct: float
    puntos: list[ValidacionPredictivaItem]


class TrazabilidadEjecutivaResponse(BaseModel):
    horizonte_activo_meses: int
    periodo_entrenado: str
    ultimo_refresco: str
    modelo_nombre: str
    tipo: str
    version: str


class PalancaPrescriptivaItem(BaseModel):
    descripcion: str
    impacto_estimado_bs_anual: float
    impacto_resumen: str


class DashboardResponse(BaseModel):
    forecast: ForecastResponse
    metricas: MetricasResponse
    modelo: ModeloDiagnosticoResponse
    validacion_predictiva: ValidacionPredictivaResponse
    trazabilidad: TrazabilidadEjecutivaResponse
    stats_historicos: StatsHistoricosResponse
    serie_historica: SerieHistoricaResponse
    analisis_ruta: list[AnalisisRutaItem]
    analisis_cliente: list[AnalisisClienteItem]
    reglas_prescriptivas: dict[str, str]
    umbrales: dict[str, Any]
    palancas_prescriptivas: list[PalancaPrescriptivaItem]
