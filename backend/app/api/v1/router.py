from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.modules.econometria.controllers.econometria_controller import router as econometria_router
from app.modules.forecast_operativo.controllers.forecast_controller import router as forecast_router
from app.modules.mineria.controllers.mineria_controller import router as mineria_router
from app.modules.asistente_inteligente.controllers.asistente_controller import router as asistente_router

api_router = APIRouter()

api_router.include_router(health_router, tags=['health'])
api_router.include_router(forecast_router, prefix='/forecast-operativo', tags=['forecast-operativo'])
api_router.include_router(econometria_router, prefix='/econometria', tags=['econometria'])
api_router.include_router(mineria_router, prefix='/torre-control-sio', tags=['torre-control-sio'])
api_router.include_router(asistente_router, prefix='/asistente-inteligente', tags=['asistente-inteligente'])

