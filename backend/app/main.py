from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.modules.asistente_inteligente.services.asistente_service import get_asistente_service
from app.modules.econometria.services.model_bundle_service import get_model_bundle_service
from app.modules.mineria.services.torre_control_service import get_torre_control_service


def create_app() -> FastAPI:
    app = FastAPI(
        title='Transfreezer Insight Suite API',
        version='0.1.0',
        description='API modular para pronóstico operativo y futuras líneas de analítica.'
    )

    resolved_cors_origins = list(settings.cors_origins)
    if 'http://localhost:3000' not in resolved_cors_origins:
        resolved_cors_origins.append('http://localhost:3000')
    if 'http://127.0.0.1:3000' not in resolved_cors_origins:
        resolved_cors_origins.append('http://127.0.0.1:3000')

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_cors_origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*']
    )

    app.include_router(api_router, prefix='/api/v1')

    @app.on_event('startup')
    def preload_asistente_inteligente() -> None:
        try:
            get_asistente_service(settings).preload()
        except Exception as exc:
            print(f'[asistente-inteligente] warning: no se pudo precargar el pipeline: {exc}')

    @app.on_event('startup')
    def preload_econometria_bundle() -> None:
        try:
            get_model_bundle_service(settings).preload()
        except Exception as exc:
            print(f'[econometria] warning: no se pudo precargar el modelo: {exc}')

    @app.on_event('startup')
    def preload_torre_control_bundle() -> None:
        try:
            get_torre_control_service(settings).preload()
        except Exception as exc:
            print(f'[torre-control-sio] warning: no se pudo precargar el modelo: {exc}')

    return app


app = create_app()
