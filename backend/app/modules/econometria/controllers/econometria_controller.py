from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.modules.econometria.schemas.econometria_schema import (
    BundleSummaryResponse,
    DescriptiveAnalyticsResponse,
    EconometricModelsResponse,
    ExecutiveSummaryResponse,
    PredictionRequest,
    PredictionResponse,
    SimulationRequest,
    SimulationResponse,
)
from app.modules.econometria.services.econometria_insights_service import EconometriaInsightsService
from app.modules.econometria.services.model_bundle_service import get_model_bundle_service
from app.modules.econometria.services.prediction_service import PredictionService

router = APIRouter()


def get_prediction_service(settings: Settings = Depends(get_settings)) -> PredictionService:
    bundle_service = get_model_bundle_service(settings)
    return PredictionService(bundle_service)


def get_insights_service(settings: Settings = Depends(get_settings)) -> EconometriaInsightsService:
    bundle_service = get_model_bundle_service(settings)
    return EconometriaInsightsService(settings, bundle_service)


@router.get('/resumen-modelo', response_model=BundleSummaryResponse)
def get_bundle_summary(settings: Settings = Depends(get_settings)) -> BundleSummaryResponse:
    bundle_service = get_model_bundle_service(settings)
    try:
        summary = bundle_service.get_summary()
        return BundleSummaryResponse(**summary)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f'Bundle econometrico no disponible: {exc}') from exc


@router.get('/resumen-ejecutivo', response_model=ExecutiveSummaryResponse)
def get_executive_summary(service: EconometriaInsightsService = Depends(get_insights_service)) -> ExecutiveSummaryResponse:
    try:
        return ExecutiveSummaryResponse(**service.get_resumen_ejecutivo())
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f'Error obteniendo resumen ejecutivo: {exc}') from exc


@router.get('/analitica-descriptiva', response_model=DescriptiveAnalyticsResponse)
def get_descriptive_analytics(
    cliente: str | None = Query(default=None),
    ruta: str | None = Query(default=None),
    nivel_sla: str | None = Query(default=None),
    division_operativa: str | None = Query(default=None),
    anio: int | None = Query(default=None),
    trimestre: int | None = Query(default=None, ge=1, le=4),
    con_penalizacion: bool | None = Query(default=None),
    con_siniestros: bool | None = Query(default=None),
    peso_min: float | None = Query(default=None, ge=0),
    peso_max: float | None = Query(default=None, ge=0),
    distancia_min: float | None = Query(default=None, ge=0),
    distancia_max: float | None = Query(default=None, ge=0),
    margen_min: float | None = Query(default=None),
    margen_max: float | None = Query(default=None),
    service: EconometriaInsightsService = Depends(get_insights_service),
) -> DescriptiveAnalyticsResponse:
    try:
        payload = service.get_analitica_descriptiva(
            cliente=cliente,
            ruta=ruta,
            nivel_sla=nivel_sla,
            division_operativa=division_operativa,
            anio=anio,
            trimestre=trimestre,
            con_penalizacion=con_penalizacion,
            con_siniestros=con_siniestros,
            peso_min=peso_min,
            peso_max=peso_max,
            distancia_min=distancia_min,
            distancia_max=distancia_max,
            margen_min=margen_min,
            margen_max=margen_max,
        )
        return DescriptiveAnalyticsResponse(**payload)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f'Error obteniendo analitica descriptiva: {exc}') from exc


@router.get('/modelos-econometricos', response_model=EconometricModelsResponse)
def get_econometric_models(service: EconometriaInsightsService = Depends(get_insights_service)) -> EconometricModelsResponse:
    try:
        payload = service.get_modelos_econometricos()
        return JSONResponse(content=jsonable_encoder(EconometricModelsResponse(**payload)))
    except Exception as exc:
        fallback = EconometricModelsResponse(
            ols={
                'formula': 'No disponible temporalmente',
                'variable_dependiente': 'MARGEN_REAL_BS',
                'variables_independientes': [],
                'coeficientes': [],
                'r2': 0.0,
                'r2_ajustado': 0.0,
                'f_statistic': 0.0,
                'n_observaciones': 0,
                'diagnostico': {
                    'rmse': 0.0,
                    'mae': 0.0,
                    'test_breusch_pagan_pvalue': 1.0,
                    'n_vars_significativas_5pct': 0,
                    'n_vars_significativas_10pct': 0,
                },
                'interpretacion_ejecutiva': [
                    f'Vista de modelos en degradacion controlada: {exc}',
                    'El bundle sera reutilizado automaticamente cuando quede disponible.',
                ],
            },
            loglog={
                'disponible': False,
                'offset_aplicado': 'No disponible temporalmente.',
                'transformacion': 'No disponible temporalmente.',
                'variables': [],
                'interpretacion_porcentual': [
                    'No se pudo recuperar el bundle del modelo log-log en esta ejecucion.',
                ],
                'limitaciones': [
                    'La vista quedo degradada sin romper el resto del modulo.',
                ],
            },
            comparativa={
                'modelo_operativo_principal': 'OLS en niveles',
                'motivo': 'No fue posible cargar el bundle de modelos en esta ejecucion.',
                'metricas': {
                    'r2_ols': 0.0,
                    'aic_ols': 0.0,
                    'bic_ols': 0.0,
                    'loglog_disponible': False,
                },
                'utilidad_practica': [
                    'Recarga la pestaña para reintentar la carga del bundle.',
                    'El resto del modulo econometrico sigue disponible.',
                ],
            },
        )
        return JSONResponse(content=jsonable_encoder(fallback))


@router.post('/prediccion', response_model=PredictionResponse)
def predict_contract_margin(
    payload: PredictionRequest,
    service: PredictionService = Depends(get_prediction_service),
) -> PredictionResponse:
    try:
        return service.predict_contract_margin(payload)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f'Error al predecir margen: {exc}') from exc


@router.post('/simulacion', response_model=SimulationResponse)
def simulate_contract_scenario(
    payload: SimulationRequest,
    service: PredictionService = Depends(get_prediction_service),
) -> SimulationResponse:
    try:
        return service.simulate_contract_scenario(payload.base_input, payload.adjusted_input)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f'Error al simular escenario: {exc}') from exc
