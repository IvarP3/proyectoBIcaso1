from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.modules.econometria.repositories.model_bundle_repository import ModelBundleRepository


class ModelBundleService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.repository = ModelBundleRepository(settings)
        self._bundle: dict[str, Any] | None = None
        self._bundle_path: Path | None = None

    def preload(self) -> None:
        self.get_bundle()

    def get_bundle(self) -> dict[str, Any]:
        if self._bundle is not None:
            return self._bundle

        model_path = self.repository.resolve_model_path()
        bundle = self.repository.load_bundle(model_path)

        if bundle is None:
            raise ValueError(f'No se pudo cargar el bundle econometrico desde: {model_path}')
        if not isinstance(bundle, dict):
            raise ValueError(f'Bundle econometrico invalido: {type(bundle).__name__}')
        if 'modelo' not in bundle:
            raise ValueError('Bundle econometrico incompleto: falta clave "modelo"')

        self._bundle = bundle
        self._bundle_path = model_path
        return bundle

    def get_bundle_path(self) -> str | None:
        if self._bundle_path is None:
            return None
        return str(self._bundle_path)

    def get_summary(self) -> dict[str, Any]:
        bundle = self.get_bundle()
        metricas = bundle.get('metricas', {})
        diagnostico = bundle.get('diagnostico', {})
        return {
            'nombre': str(bundle.get('nombre', 'N/A')),
            'version': str(bundle.get('version', 'N/A')),
            'fecha_entreno': str(bundle.get('fecha_entreno', 'N/A')),
            'empresa': str(bundle.get('empresa', 'N/A')),
            'variable_dependiente': str(bundle.get('variable_dependiente', 'N/A')),
            'formula': str(bundle.get('formula', 'N/A')),
            'metodo': str(bundle.get('metodo', 'N/A')),
            'variables_independientes': list(bundle.get('variables_independientes', [])),
            'metricas': metricas if isinstance(metricas, dict) else {},
            'diagnostico': diagnostico if isinstance(diagnostico, dict) else {},
            'limitaciones_metodologicas': [
                'Se detecto heterocedasticidad en el analisis original; priorizar lectura con errores robustos.',
                'La variable es_farma presento un problema de codificacion en la corrida auditada; usar con cautela inferencial.',
                'El modelo es explicativo-operativo y no prueba causalidad absoluta por si solo.'
            ],
        }


_bundle_service: ModelBundleService | None = None


def get_model_bundle_service(settings: Settings) -> ModelBundleService:
    global _bundle_service
    if _bundle_service is None:
        _bundle_service = ModelBundleService(settings)
    return _bundle_service
