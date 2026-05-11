from fastapi import APIRouter, Depends, Query

from app.core.config import Settings, get_settings
from app.modules.forecast_operativo.schemas.forecast_schema import (
    ForecastResponse,
    MetricasResponse,
    StatsHistoricosResponse,
    SerieHistoricaResponse,
    AnalisisRutaItem,
    AnalisisClienteItem,
    DashboardResponse,
)
from app.modules.forecast_operativo.services.forecast_service import ForecastService

router = APIRouter()


def get_service(settings: Settings = Depends(get_settings)) -> ForecastService:
    return ForecastService(settings)


@router.get('', response_model=ForecastResponse)
def get_forecast(
    horizon: int = Query(default=6, ge=0, le=6),
    service: ForecastService = Depends(get_service)
) -> ForecastResponse:
    return service.build_forecast(horizon=horizon)


@router.get('/metricas', response_model=MetricasResponse)
def get_metricas(service: ForecastService = Depends(get_service)) -> MetricasResponse:
    return service.get_metricas()


@router.get('/historicos', response_model=StatsHistoricosResponse)
def get_stats_historicos(service: ForecastService = Depends(get_service)) -> StatsHistoricosResponse:
    return service.get_stats_historicos()


@router.get('/serie', response_model=SerieHistoricaResponse)
def get_serie_historica(service: ForecastService = Depends(get_service)) -> SerieHistoricaResponse:
    return service.get_serie_historica()


@router.get('/ruta', response_model=list[AnalisisRutaItem])
def get_analisis_ruta(service: ForecastService = Depends(get_service)) -> list[AnalisisRutaItem]:
    return service.get_analisis_ruta()


@router.get('/cliente', response_model=list[AnalisisClienteItem])
def get_analisis_cliente(service: ForecastService = Depends(get_service)) -> list[AnalisisClienteItem]:
    return service.get_analisis_cliente()


@router.get('/dashboard', response_model=DashboardResponse)
def get_dashboard_completo(
    horizon: int = Query(default=6, ge=0, le=6),
    service: ForecastService = Depends(get_service)
) -> DashboardResponse:
    return service.get_dashboard_completo(horizon=horizon)
