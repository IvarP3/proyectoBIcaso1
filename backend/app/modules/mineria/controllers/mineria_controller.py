from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.modules.mineria.schemas.mineria_schema import DashboardResponse
from app.modules.mineria.services.torre_control_service import get_torre_control_service

router = APIRouter()


def get_service(settings: Settings = Depends(get_settings)):
    service = get_torre_control_service(settings)
    service.preload()
    return service


@router.get('/dashboard', response_model=DashboardResponse)
def get_dashboard(service=Depends(get_service)) -> DashboardResponse:
    return DashboardResponse(**service.get_dashboard())


@router.post('/tick', response_model=DashboardResponse)
def advance_tick(
    es_lluvia: bool = False,
    es_feriado: bool = False,
    service=Depends(get_service),
) -> DashboardResponse:
    return DashboardResponse(**service.tick(es_lluvia=es_lluvia, es_feriado=es_feriado))


@router.get('/fleet')
def get_fleet(service=Depends(get_service)):
    return service.get_fleet()


@router.get('/alerts')
def get_alerts(service=Depends(get_service)):
    return service.get_alerts()


@router.post('/alerts/clear')
def clear_alerts(service=Depends(get_service)):
    service.clear_alerts()
    return {'ok': True}


@router.get('/bundle')
def get_bundle(service=Depends(get_service)):
    return service.get_dashboard()['bundle']
