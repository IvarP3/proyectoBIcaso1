from __future__ import annotations

import unicodedata

import pandas as pd

from app.modules.econometria.schemas.econometria_schema import (
    PredictionRequest,
    PredictionResponse,
    SimulationResponse,
)
from app.modules.econometria.services.model_bundle_service import ModelBundleService


class PredictionService:
    def __init__(self, bundle_service: ModelBundleService) -> None:
        self.bundle_service = bundle_service

    def _normalize_sla(self, nivel_sla: str) -> str:
        normalized = unicodedata.normalize('NFKD', nivel_sla).encode('ascii', 'ignore').decode('ascii')
        normalized = normalized.upper().strip()
        if normalized == 'ESTANDAR':
            return 'ESTANDAR'
        if normalized == 'ORO':
            return 'ORO'
        if normalized == 'PLATINO':
            return 'PLATINO'
        return 'ESTANDAR'

    def _map_sla_numeric(self, nivel_sla: str) -> int:
        sla_map = {
            'ESTANDAR': 1,
            'ORO': 2,
            'PLATINO': 3,
        }
        return sla_map.get(self._normalize_sla(nivel_sla), 1)

    def _canonical_sla_label(self, nivel_sla: str) -> str:
        normalized = self._normalize_sla(nivel_sla)
        if normalized == 'ESTANDAR':
            return 'ESTÁNDAR'
        return normalized

    def predict_contract_margin(self, payload: PredictionRequest) -> PredictionResponse:
        bundle = self.bundle_service.get_bundle()
        modelo = bundle['modelo']

        sla_n = self._map_sla_numeric(payload.nivel_sla)
        es_farma = int(payload.es_division_farma)

        x_nuevo = pd.DataFrame([
            {
                'const': 1,
                'PESO_TRANSPORTADO_KG': payload.peso_kg,
                'DISTANCIA_NOMINAL_KM': payload.distancia_km,
                'ALTITUD_MAXIMA_MSNM': payload.altitud_msnm,
                'MONTO_PENALIZACION_BS': payload.penalizacion_bs,
                'TOTAL_SINIESTROS_BS': payload.siniestros_bs,
                'sla_n': sla_n,
                'es_farma': es_farma,
                'PUNTAJE_EFICIENCIA_TERMICA': payload.puntaje_chofer,
            }
        ])

        prediccion = float(modelo.predict(x_nuevo)[0])
        diagnostico = bundle.get('diagnostico', {}) if isinstance(bundle.get('diagnostico', {}), dict) else {}
        rmse = float(diagnostico.get('RMSE', 0.0))

        ci_lo = prediccion - 1.96 * rmse
        ci_hi = prediccion + 1.96 * rmse

        alertas: list[str] = []
        if payload.penalizacion_bs > 500:
            alertas.append('Penalización SLA elevada')
        if payload.siniestros_bs > 0:
            alertas.append('Siniestro registrado en este contrato')
        if payload.altitud_msnm > 3500:
            alertas.append('Ruta de alta altitud: riesgo térmico elevado')
        if payload.puntaje_chofer < 7.0:
            alertas.append('Puntaje del chofer por debajo del umbral recomendado')
        if prediccion < 0:
            alertas.append('Contrato proyectado con pérdida')

        return PredictionResponse(
            margen_predicho_bs=round(prediccion, 2),
            intervalo_confianza_95=[round(ci_lo, 2), round(ci_hi, 2)],
            nivel_sla=self._canonical_sla_label(payload.nivel_sla),
            division='FÁRMACOS' if es_farma else 'ALIMENTOS',
            alertas=alertas,
            rentable=prediccion > 0,
        )

    def simulate_contract_scenario(
        self,
        base_input: PredictionRequest,
        adjusted_input: PredictionRequest,
    ) -> SimulationResponse:
        base = self.predict_contract_margin(base_input)
        adjusted = self.predict_contract_margin(adjusted_input)

        delta_abs = adjusted.margen_predicho_bs - base.margen_predicho_bs
        delta_pct = 0.0
        if base.margen_predicho_bs != 0:
            delta_pct = (delta_abs / abs(base.margen_predicho_bs)) * 100

        if delta_abs > 0:
            interpretation = 'El escenario ajustado mejora el margen esperado respecto al escenario base.'
        elif delta_abs < 0:
            interpretation = 'El escenario ajustado reduce el margen esperado respecto al escenario base.'
        else:
            interpretation = 'El escenario ajustado no cambia el margen esperado frente al escenario base.'

        return SimulationResponse(
            margen_base_bs=round(base.margen_predicho_bs, 2),
            margen_simulado_bs=round(adjusted.margen_predicho_bs, 2),
            diferencia_absoluta_bs=round(delta_abs, 2),
            diferencia_porcentual=round(delta_pct, 2),
            interpretacion_cambio=interpretation,
            alertas_operativas=adjusted.alertas,
            rentable_ajustado=adjusted.rentable,
        )
