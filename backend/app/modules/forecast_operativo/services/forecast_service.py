from app.core.config import Settings
from app.modules.forecast_operativo.repositories.model_repository import ModelRepository
from app.modules.forecast_operativo.schemas.forecast_schema import (
    ForecastItem,
    ForecastResponse,
    MetricasResponse,
    ModeloDiagnosticoResponse,
    PalancaPrescriptivaItem,
    TrazabilidadEjecutivaResponse,
    StatsHistoricosResponse,
    ValidacionPredictivaItem,
    ValidacionPredictivaResponse,
    SerieHistoricaResponse,
    AnalisisRutaItem,
    AnalisisClienteItem,
    DashboardResponse,
)

import numpy as np
import pandas as pd


class ForecastService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.repository = ModelRepository(settings)
        self._artifact = None

    def _load_artifact(self) -> dict:
        """Carga el artefacto pkl una sola vez y lo cachea en memoria."""
        if self._artifact is None:
            model_path = self.repository.resolve_model_path()
            artifact = self.repository.load_model(model_path)
            
            if artifact is None:
                raise ValueError(f'No se pudo cargar el modelo desde: {model_path}')
            
            if not isinstance(artifact, dict):
                raise ValueError(f'Modelo debe ser un diccionario, se recibió: {type(artifact).__name__}')
            
            # Validar que contenga al menos los campos principales
            required_keys = ['forecast', 'metricas', 'stats_historicos']
            missing = [k for k in required_keys if k not in artifact]
            if missing:
                raise ValueError(f'Artefacto incompleto. Faltan claves: {missing}')
            
            self._artifact = artifact
        return self._artifact

    def _get_metadata(self) -> dict:
        artifact = self._load_artifact()
        return artifact.get('metadata', {})

    def _get_serie_data(self) -> tuple[list[str], np.ndarray]:
        artifact = self._load_artifact()
        serie = artifact.get('serie_historica', {})
        meses = list(serie.get('meses', []))
        valores = np.asarray(serie.get('margen_neto_bs', []), dtype=float)
        return meses, valores

    def _get_confidence_level(self) -> float:
        metadata = self._get_metadata()
        try:
            return float(metadata.get('nivel_confianza', 0.90))
        except (TypeError, ValueError):
            return 0.90

    def _safe_expm1(self, values: np.ndarray) -> np.ndarray:
        clipped = np.clip(np.asarray(values, dtype=float), -50.0, 50.0)
        return np.expm1(clipped)

    def _get_status_modelo(self, mape_pct: float, umbral_mape_pct: float) -> str:
        if mape_pct <= umbral_mape_pct * 0.5:
            return 'SALUDABLE'
        if mape_pct <= umbral_mape_pct:
            return 'VIGILANCIA'
        return 'ALERTA'

    def _safe_str(self, value: object, default: str = 'N/A') -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text if text else default

    def _format_order(self, metadata: dict) -> str | None:
        orden = metadata.get('orden')
        if orden is None:
            return None
        return self._safe_str(orden)

    def _build_validation(self) -> tuple[ValidacionPredictivaResponse, list[ValidacionPredictivaItem]]:
        artifact = self._load_artifact()
        metadata = self._get_metadata()
        _, actual = self._get_serie_data()
        model = artifact.get('modelo_fitted')

        if actual.size == 0 or model is None or not hasattr(model, 'get_prediction'):
            empty = ValidacionPredictivaResponse(
                mae_bs=0.0,
                rmse_bs=0.0,
                mape_pct=0.0,
                cobertura_ic_pct=0.0,
                puntos=[]
            )
            return empty, []

        confidence = self._get_confidence_level()
        try:
            prediction = model.get_prediction(start=0, end=len(actual) - 1)
            pred_log = np.asarray(prediction.predicted_mean, dtype=float)
            predicho = self._safe_expm1(pred_log)
            conf_int = prediction.conf_int(alpha=1 - confidence)
            if isinstance(conf_int, pd.DataFrame):
                lower_log = np.asarray(conf_int.iloc[:, 0], dtype=float)
                upper_log = np.asarray(conf_int.iloc[:, 1], dtype=float)
            else:
                conf_arr = np.asarray(conf_int, dtype=float)
                lower_log = conf_arr[:, 0]
                upper_log = conf_arr[:, 1]
            lower = self._safe_expm1(lower_log)
            upper = self._safe_expm1(upper_log)
        except Exception:
            fitted = getattr(model, 'fittedvalues', None)
            if fitted is None:
                predicho = np.zeros_like(actual)
            else:
                predicho = self._safe_expm1(np.asarray(fitted, dtype=float))
            resid_std = float(np.std(actual - predicho)) if actual.size else 0.0
            lower = np.clip(predicho - 1.96 * resid_std, 0, None)
            upper = predicho + 1.96 * resid_std

        # ── Filtrar burn-in: el modelo SARIMA(2,1,2)x(1,1,0,3) con d=1,D=1
        # no puede estimar los primeros puntos (NaN → expm1 → 0 o valores
        # aberrantes). Solo mostramos puntos donde la predicción es válida:
        # pred > 0 y no es NaN y no supera 10x el máximo histórico.
        max_historico = float(actual.max()) if actual.size else 1e9
        valid_mask = (
            ~np.isnan(predicho)
            & (predicho > 0)
            & (predicho <= max_historico * 10)
        )

        meses, _ = self._get_serie_data()
        puntos: list[ValidacionPredictivaItem] = []
        valid_errors: list[float] = []
        valid_pcts: list[float] = []
        valid_ics: list[bool] = []

        for i, (mes, real, pred, ic_lo, ic_hi) in enumerate(
            zip(meses, actual, predicho, lower, upper)
        ):
            if not valid_mask[i]:
                continue
            err = float(real) - float(pred)
            err_abs = abs(err)
            err_pct = err_abs / float(real) * 100 if real != 0 else 0.0
            dentro = bool(real >= ic_lo and real <= ic_hi)

            valid_errors.append(err_abs)
            valid_pcts.append(err_pct)
            valid_ics.append(dentro)

            puntos.append(
                ValidacionPredictivaItem(
                    periodo=self._safe_str(mes),
                    real_bs=float(real),
                    predicho_bs=float(pred),
                    error_bs=float(err),
                    error_pct=float(err_pct),
                    dentro_ic=dentro
                )
            )

        if valid_errors:
            mae = float(np.mean(valid_errors))
            rmse = float(np.sqrt(np.mean(np.square(valid_errors))))
            mape = float(np.mean(valid_pcts))
            cob = float(np.mean(valid_ics) * 100)
        else:
            mae = rmse = mape = cob = 0.0

        response = ValidacionPredictivaResponse(
            mae_bs=mae,
            rmse_bs=rmse,
            mape_pct=mape,
            cobertura_ic_pct=cob,
            puntos=puntos
        )
        return response, puntos

    def get_modelo_diagnostico(self) -> ModeloDiagnosticoResponse:
        artifact = self._load_artifact()
        metadata = self._get_metadata()
        metricas = artifact.get('metricas', {})
        umbrales = artifact.get('umbrales', {})
        mape_pct = float(metricas.get('MAPE_pct', 0.0))
        umbral_mape = float(umbrales.get('mape_alerta_pct', 30.0))
        return ModeloDiagnosticoResponse(
            estado_modelo=self._get_status_modelo(mape_pct, umbral_mape),
            mae_bs=float(metricas.get('MAE_Bs', 0.0)),
            rmse_bs=float(metricas.get('RMSE_Bs', 0.0)),
            mape_pct=mape_pct,
            aic=float(metricas.get('AIC', 0.0)),
            cumple_umbral=bool(metricas.get('cumple_umbral_25pct', False)),
            umbral_mape_pct=umbral_mape,
            fecha_entrenamiento=self._safe_str(metadata.get('fecha_entrenamiento')),
            version=self._safe_str(metadata.get('version')),
            modelo_nombre=self._safe_str(metadata.get('modelo_nombre')),
            tipo=self._safe_str(metadata.get('tipo')),
            orden=self._format_order(metadata),
            nivel_confianza=float(metadata.get('nivel_confianza', 0.90)),
            periodo_entrenamiento=self._safe_str(metadata.get('periodo_entrenamiento')),
            n_meses_entrenamiento=int(metadata.get('n_meses_entrenamiento', 0) or 0),
            horizonte_forecast_meses=int(metadata.get('horizonte_forecast_meses', 0) or 0)
        )

    def get_validacion_predictiva(self) -> ValidacionPredictivaResponse:
        validation, _ = self._build_validation()
        return validation

    def get_trazabilidad_ejecutiva(self, horizon: int) -> TrazabilidadEjecutivaResponse:
        metadata = self._get_metadata()
        return TrazabilidadEjecutivaResponse(
            horizonte_activo_meses=horizon,
            periodo_entrenado=self._safe_str(metadata.get('periodo_entrenamiento')),
            ultimo_refresco=self._safe_str(metadata.get('fecha_entrenamiento')),
            modelo_nombre=self._safe_str(metadata.get('modelo_nombre')),
            tipo=self._safe_str(metadata.get('tipo')),
            version=self._safe_str(metadata.get('version'))
        )

    def get_palancas_prescriptivas(self) -> list[PalancaPrescriptivaItem]:
        # Extraídas del notebook, sin inventar valores nuevos.
        return [
            PalancaPrescriptivaItem(
                descripcion='Provisionar flota en meses altos (capturar demanda no atendida)',
                impacto_estimado_bs_anual=125_000.0,
                impacto_resumen='+100,000–150,000 Bs/año'
            ),
            PalancaPrescriptivaItem(
                descripcion='Reasignar 30% capacidad ruta baja margen → Cobija/Tarija',
                impacto_estimado_bs_anual=100_000.0,
                impacto_resumen='+80,000–120,000 Bs/año'
            ),
            PalancaPrescriptivaItem(
                descripcion='Campaña comercial proactiva en meses bajos (llenar capacidad)',
                impacto_estimado_bs_anual=50_000.0,
                impacto_resumen='+40,000–60,000 Bs/año'
            ),
            PalancaPrescriptivaItem(
                descripcion='Anticipar riesgo por mes/ruta/cliente → reducir penalizaciones',
                impacto_estimado_bs_anual=14_000.0,
                impacto_resumen='+13,000–15,000 Bs/año'
            ),
            PalancaPrescriptivaItem(
                descripcion='Renegociar contratos clientes de alto riesgo (SLA + cláusulas)',
                impacto_estimado_bs_anual=20_000.0,
                impacto_resumen='+15,000–25,000 Bs/año'
            ),
        ]

    def build_forecast(self, horizon: int) -> ForecastResponse:
        artifact = self._load_artifact()
        forecast_data = artifact.get('forecast', [])
        
        if not forecast_data:
            # Si no hay data, retornar respuesta vacía pero válida
            return ForecastResponse(
                module='Proyección de Ingresos',
                horizon_months=0,
                source_model='SARIMA',
                items=[]
            )
        
        items = []
        for f in forecast_data[:horizon]:
            try:
                nivel = f.get('Nivel_Demanda', 'MEDIO')
                items.append(
                    ForecastItem(
                        month=str(f.get('Mes', 'N/A')),
                        projected_income_bob=float(f.get('Margen_Proyectado_Bs', 0)),
                        lower_bound_bob=float(f.get('IC_Inferior_Bs', 0)),
                        upper_bound_bob=float(f.get('IC_Superior_Bs', 0)),
                        suggested_action=self._map_accion(nivel)
                    )
                )
            except (KeyError, ValueError, TypeError):
                continue
        
        meta = artifact.get('metadata', {})
        return ForecastResponse(
            module='Proyección de Ingresos',
            horizon_months=len(items),
            source_model=str(meta.get('modelo_nombre', 'SARIMA')),
            items=items
        )

    def get_metricas(self) -> MetricasResponse:
        artifact = self._load_artifact()
        metricas = artifact.get('metricas', {})
        return MetricasResponse(
            mae_bs=float(metricas.get('MAE_Bs', 0.0)),
            rmse_bs=float(metricas.get('RMSE_Bs', 0.0)),
            mape_pct=float(metricas.get('MAPE_pct', 0.0)),
            aic=float(metricas.get('AIC', 0.0)),
            cumple_umbral=bool(metricas.get('cumple_umbral_25pct', False))
        )

    def get_stats_historicos(self) -> StatsHistoricosResponse:
        artifact = self._load_artifact()
        stats = artifact.get('stats_historicos', {})
        return StatsHistoricosResponse(
            media_margen_bs=float(stats.get('media_margen_Bs', 0.0)),
            std_margen_bs=float(stats.get('std_margen_Bs', 0.0)),
            cv_pct=float(stats.get('cv_pct', 0.0)),
            ingreso_total_bs=float(stats.get('ingreso_total_Bs', 0.0)),
            margen_neto_total_bs=float(stats.get('margen_neto_total_Bs', 0.0)),
            pct_margen_global=float(stats.get('pct_margen_global', 0.0))
        )

    def get_serie_historica(self) -> SerieHistoricaResponse:
        artifact = self._load_artifact()
        serie = artifact.get('serie_historica', {})
        return SerieHistoricaResponse(
            meses=serie.get('meses', []),
            margen_neto_bs=serie.get('margen_neto_bs', []),
            ingreso_bs=serie.get('ingreso_bs', []),
            num_contratos=serie.get('num_contratos', [])
        )

    def get_analisis_ruta(self) -> list[AnalisisRutaItem]:
        artifact = self._load_artifact()
        rutas = artifact.get('analisis_ruta', [])
        if not rutas:
            return []
        return [
            AnalisisRutaItem(
                ruta=str(r.get('RUTA', 'N/A')),
                margen_neto_bs=float(r.get('MARGEN_NETO_BS', 0)),
                pct_margen=float(r.get('PCT_MARGEN', 0)),
                margen_por_kg=float(r.get('MARGEN_POR_KG', 0)),
                num_contratos=int(r.get('NUM_CONTRATOS', 0))
            )
            for r in rutas if r
        ]

    def get_analisis_cliente(self) -> list[AnalisisClienteItem]:
        artifact = self._load_artifact()
        clientes = artifact.get('analisis_cliente', [])
        if not clientes:
            return []
        return [
            AnalisisClienteItem(
                cliente=str(c.get('CLIENTE', 'N/A')),
                nivel_sla=c.get('NIVEL_SLA'),
                margen_neto_bs=float(c.get('MARGEN_NETO_BS', 0)),
                num_contratos=int(c.get('NUM_CONTRATOS', 0)),
                penalizacion_bs=float(c.get('PENALIZACION_BS', 0)),
                margen_por_contrato=float(c.get('MARGEN_POR_CONTRATO', 0)) if c.get('MARGEN_POR_CONTRATO') is not None else None
            )
            for c in clientes if c
        ]

    def get_dashboard_completo(self, horizon: int = 6) -> DashboardResponse:
        artifact = self._load_artifact()
        try:
            validation = self.get_validacion_predictiva()
            return DashboardResponse(
                forecast=self.build_forecast(horizon),
                metricas=self.get_metricas(),
                modelo=self.get_modelo_diagnostico(),
                validacion_predictiva=validation,
                trazabilidad=self.get_trazabilidad_ejecutiva(horizon),
                stats_historicos=self.get_stats_historicos(),
                serie_historica=self.get_serie_historica(),
                analisis_ruta=self.get_analisis_ruta(),
                analisis_cliente=self.get_analisis_cliente(),
                reglas_prescriptivas=artifact.get('reglas_prescriptivas', {}),
                umbrales=artifact.get('umbrales', {}),
                palancas_prescriptivas=self.get_palancas_prescriptivas()
            )
        except Exception as e:
            print(f"Error en get_dashboard_completo: {e}")
            raise

    def _map_accion(self, nivel: str) -> str:
        mapa = {
            'ALTO': 'Provisionar flota extra',
            'MEDIO': 'Mantener capacidad planificada',
            'BAJO': 'Buscar contratos proactivos'
        }
        return mapa.get(nivel, 'Mantener capacidad planificada')
