from pydantic import BaseModel, Field, field_validator


class PredictionRequest(BaseModel):
    peso_kg: float = Field(ge=0)
    distancia_km: float = Field(ge=0)
    altitud_msnm: float = Field(ge=0)
    penalizacion_bs: float = Field(ge=0)
    siniestros_bs: float = Field(ge=0)
    nivel_sla: str
    es_division_farma: bool
    puntaje_chofer: float = Field(ge=0, le=10)

    @field_validator('nivel_sla')
    @classmethod
    def validate_nivel_sla(cls, value: str) -> str:
        normalized = value.upper().strip()
        valid_values = {'ESTANDAR', 'ESTÁNDAR', 'ORO', 'PLATINO'}
        if normalized not in valid_values:
            raise ValueError('nivel_sla debe ser ESTÁNDAR/ESTANDAR, ORO o PLATINO')
        return value


class PredictionResponse(BaseModel):
    margen_predicho_bs: float
    intervalo_confianza_95: list[float]
    nivel_sla: str
    division: str
    alertas: list[str]
    rentable: bool


class SimulationRequest(BaseModel):
    base_input: PredictionRequest
    adjusted_input: PredictionRequest


class SimulationResponse(BaseModel):
    margen_base_bs: float
    margen_simulado_bs: float
    diferencia_absoluta_bs: float
    diferencia_porcentual: float
    interpretacion_cambio: str
    alertas_operativas: list[str]
    rentable_ajustado: bool


class BundleSummaryResponse(BaseModel):
    nombre: str
    version: str
    fecha_entreno: str
    empresa: str
    variable_dependiente: str
    formula: str
    metodo: str
    variables_independientes: list[str]
    metricas: dict[str, float | int | bool]
    diagnostico: dict[str, float | int | bool]
    limitaciones_metodologicas: list[str]


class ExecutiveSummaryResponse(BaseModel):
    contratos_analizados: int
    pct_contratos_rentables: float
    contratos_con_perdida: int
    margen_promedio_bs: float
    margen_mediana_bs: float
    margen_min_bs: float
    margen_max_bs: float
    periodo_analizado: str
    modelo_principal_activo: str
    origen_datos: list[str]
    advertencias_metodologicas: list[str]
    snowflake_disponible: bool
    bundle_disponible: bool
    r2_modelo_ols: float
    f_stat_modelo_ols: float


class HistogramBin(BaseModel):
    bucket: str
    count: int


class GroupMarginItem(BaseModel):
    nombre: str
    margen_promedio_bs: float
    contratos: int
    categoria: str | None = None
    valor_extra: float | None = None


class FinancialStepItem(BaseModel):
    etapa: str
    monto_bs: float


class ScatterPointItem(BaseModel):
    x: float
    y: float


class CorrelationItem(BaseModel):
    variable: str
    r: float


class QuarterlyTrendItem(BaseModel):
    periodo: str
    margen_promedio_bs: float
    contratos: int


class DescriptiveAnalyticsResponse(BaseModel):
    snowflake_disponible: bool
    warning: str | None = None
    margin_distribution: list[HistogramBin]
    margin_by_division: list[GroupMarginItem]
    margin_by_sla: list[GroupMarginItem]
    financial_structure: list[FinancialStepItem]
    scatter_distance_vs_margin: list[ScatterPointItem]
    scatter_weight_vs_margin: list[ScatterPointItem]
    correlations: list[CorrelationItem]
    quarterly_trend: list[QuarterlyTrendItem]
    ranking_clientes: list[GroupMarginItem]
    ranking_rutas: list[GroupMarginItem]


class OlsCoefficientItem(BaseModel):
    variable: str
    beta: float
    std_err: float
    t_stat: float
    p_value: float
    ci_95_lo: float
    ci_95_hi: float
    significativo_5pct: bool


class OlsModelViewResponse(BaseModel):
    formula: str
    variable_dependiente: str
    variables_independientes: list[str]
    coeficientes: list[OlsCoefficientItem]
    coeficientes_estandarizados: list[OlsCoefficientItem]
    ajuste_observado_predicho: list[ScatterPointItem]
    r2: float
    r2_ajustado: float
    f_statistic: float
    n_observaciones: int
    diagnostico: dict[str, float | int]
    interpretacion_ejecutiva: list[str]


class LogLogVariableItem(BaseModel):
    variable: str
    beta: float
    p_value: float
    significativo_5pct: bool


class LogLogModelViewResponse(BaseModel):
    disponible: bool
    offset_aplicado: str
    transformacion: str
    variables: list[LogLogVariableItem]
    interpretacion_porcentual: list[str]
    limitaciones: list[str]


class ModelComparisonResponse(BaseModel):
    modelo_operativo_principal: str
    motivo: str
    metricas: dict[str, float | bool]
    utilidad_practica: list[str]


class EconometricModelsResponse(BaseModel):
    ols: OlsModelViewResponse
    loglog: LogLogModelViewResponse
    comparativa: ModelComparisonResponse
