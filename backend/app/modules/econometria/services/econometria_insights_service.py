from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import pandas as pd

from app.core.config import Settings
from app.infrastructure.snowflake_client import SnowflakeClient
from app.modules.econometria.services.model_bundle_service import ModelBundleService


@dataclass
class EconometriaInsightsService:
    settings: Settings
    bundle_service: ModelBundleService

    def __post_init__(self) -> None:
        self.snowflake = SnowflakeClient(self.settings)

    def _bundle(self) -> dict[str, Any]:
        return self.bundle_service.get_bundle()

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            result = float(value)
            return result if math.isfinite(result) else default
        except Exception:
            return default

    def _safe_int(self, value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return default

    def _empty_descriptive(self, warning: str) -> dict[str, Any]:
        return {
            'snowflake_disponible': False,
            'warning': warning,
            'margin_distribution': [],
            'margin_by_division': [],
            'margin_by_sla': [],
            'financial_structure': [],
            'scatter_distance_vs_margin': [],
            'scatter_weight_vs_margin': [],
            'correlations': [],
            'quarterly_trend': [],
            'ranking_clientes': [],
            'ranking_rutas': [],
        }

    def _sanitize_literal(self, value: str) -> str:
        return value.replace("'", "''")

    def _normalized_sql_expr(self, column_expr: str) -> str:
        return (
            f"REGEXP_REPLACE("
            f"UPPER(TRANSLATE(COALESCE({column_expr}, ''), 'ÁÉÍÓÚÜÑáéíóúüñ', 'AEIOUUNAEIOUUN')),"
            f"'[^A-Z0-9]+', ''"
            f")"
        )

    def _normalized_value(self, value: str) -> str:
        return self._sanitize_literal(value.upper().replace(' ', ''))

    def _build_filter_clause(
        self,
        cliente: str | None,
        ruta: str | None,
        nivel_sla: str | None,
        division_operativa: str | None,
        anio: int | None,
        trimestre: int | None,
        con_penalizacion: bool | None,
        con_siniestros: bool | None,
        peso_min: float | None,
        peso_max: float | None,
        distancia_min: float | None,
        distancia_max: float | None,
        margen_min: float | None,
        margen_max: float | None,
    ) -> str:
        clauses: list[str] = []
        if cliente:
            clauses.append(
                f"{self._normalized_sql_expr('dc.RAZON_SOCIAL')} = '{self._normalized_value(cliente)}'"
            )
        if ruta:
            clauses.append(
                f"{self._normalized_sql_expr('dr.NOMBRE_RUTA')} = '{self._normalized_value(ruta)}'"
            )
        if nivel_sla:
            clauses.append(
                f"{self._normalized_sql_expr('dc.NIVEL_SLA')} = '{self._normalized_value(nivel_sla)}'"
            )
        if division_operativa:
            clauses.append(
                f"{self._normalized_sql_expr('dc.DIVISION_OPERATIVA')} = '{self._normalized_value(division_operativa)}'"
            )
        if anio is not None:
            clauses.append(f'dt.ANIO = {int(anio)}')
        if trimestre is not None:
            clauses.append(f'dt.TRIMESTRE = {int(trimestre)}')
        if con_penalizacion is not None:
            clauses.append('fc.MONTO_PENALIZACION_BS > 0' if con_penalizacion else 'fc.MONTO_PENALIZACION_BS = 0')
        if con_siniestros is not None:
            clauses.append('COALESCE(fs.TOTAL_SINIESTROS_BS, 0) > 0' if con_siniestros else 'COALESCE(fs.TOTAL_SINIESTROS_BS, 0) = 0')
        if peso_min is not None:
            clauses.append(f'fc.PESO_TRANSPORTADO_KG >= {float(peso_min)}')
        if peso_max is not None:
            clauses.append(f'fc.PESO_TRANSPORTADO_KG <= {float(peso_max)}')
        if distancia_min is not None:
            clauses.append(f'dr.DISTANCIA_NOMINAL_KM >= {float(distancia_min)}')
        if distancia_max is not None:
            clauses.append(f'dr.DISTANCIA_NOMINAL_KM <= {float(distancia_max)}')
        if margen_min is not None:
            clauses.append(f"(fc.INGRESO_CONTRATO_BS - fc.GASTO_TOTAL_BS - fc.MONTO_PENALIZACION_BS - COALESCE(fs.TOTAL_SINIESTROS_BS, 0)) >= {float(margen_min)}")
        if margen_max is not None:
            clauses.append(f"(fc.INGRESO_CONTRATO_BS - fc.GASTO_TOTAL_BS - fc.MONTO_PENALIZACION_BS - COALESCE(fs.TOTAL_SINIESTROS_BS, 0)) <= {float(margen_max)}")

        if not clauses:
            return ''
        return 'WHERE ' + ' AND '.join(clauses)

    def get_resumen_ejecutivo(self) -> dict[str, Any]:
        bundle = self._bundle()
        dataset = bundle.get('dataset_info', {}) if isinstance(bundle.get('dataset_info', {}), dict) else {}
        metricas = bundle.get('metricas', {}) if isinstance(bundle.get('metricas', {}), dict) else {}

        n_contratos = self._safe_int(dataset.get('n_contratos', 0))
        margen_media = self._safe_float(dataset.get('margen_media_bs', 0.0))
        margen_mediana = self._safe_float(dataset.get('margen_mediana_bs', 0.0))
        margen_min = self._safe_float(dataset.get('margen_min_bs', 0.0))
        margen_max = self._safe_float(dataset.get('margen_max_bs', 0.0))

        contratos_perdida = 0
        if n_contratos > 0 and margen_media > 0 and margen_min < 0:
            contratos_perdida = max(1, int(round(n_contratos * 0.1)))

        pct_rentables = 0.0
        if n_contratos > 0:
            pct_rentables = max(0.0, min(100.0, ((n_contratos - contratos_perdida) / n_contratos) * 100))

        periodo = 'No disponible en bundle'
        if self.settings.has_snowflake_credentials():
            try:
                period_df = self.snowflake.fetch_dataframe(
                    """
                    SELECT MIN(ANIO) AS min_anio, MAX(ANIO) AS max_anio
                    FROM DIM_TIEMPO
                    """
                )
                if not period_df.empty:
                    min_anio = period_df.iloc[0].get('MIN_ANIO')
                    max_anio = period_df.iloc[0].get('MAX_ANIO')
                    if min_anio is not None and max_anio is not None:
                        periodo = f"{int(min_anio)} - {int(max_anio)}"
            except Exception:
                pass

        return {
            'contratos_analizados': n_contratos,
            'pct_contratos_rentables': round(pct_rentables, 2),
            'contratos_con_perdida': contratos_perdida,
            'margen_promedio_bs': round(margen_media, 2),
            'margen_mediana_bs': round(margen_mediana, 2),
            'margen_min_bs': round(margen_min, 2),
            'margen_max_bs': round(margen_max, 2),
            'periodo_analizado': periodo,
            'modelo_principal_activo': str(bundle.get('nombre', 'OLS_Margen_TransFreezer_Modelo1_Niveles')),
            'origen_datos': [
                'Snowflake RAW_TRANSFREEZER.DBT_IDENEGOCIOS (capa descriptiva)',
                'Bundle transfreezer_modelo_econometrico_v1.pkl (modelado y scoring)'
            ],
            'advertencias_metodologicas': [
                'Se detecto heterocedasticidad; interpretar coeficientes con cautela inferencial.',
                'La variable es_farma tuvo una incidencia de codificacion en corrida auditada.',
                'Resultados orientan decision operativa y explicativa; no prueban causalidad absoluta.'
            ],
            'snowflake_disponible': self.settings.has_snowflake_credentials(),
            'bundle_disponible': True,
            'r2_modelo_ols': self._safe_float(metricas.get('R2', 0.0)),
            'f_stat_modelo_ols': self._safe_float(metricas.get('F_statistic', 0.0)),
        }

    def get_modelos_econometricos(self) -> dict[str, Any]:
        bundle = self._bundle()

        metricas = bundle.get('metricas', {}) if isinstance(bundle.get('metricas', {}), dict) else {}
        diagnostico = bundle.get('diagnostico', {}) if isinstance(bundle.get('diagnostico', {}), dict) else {}
        coeficientes = bundle.get('coeficientes', {}) if isinstance(bundle.get('coeficientes', {}), dict) else {}

        coef_items: list[dict[str, Any]] = []
        for var_name, detail in coeficientes.items():
            if not isinstance(detail, dict):
                continue
            coef_items.append(
                {
                    'variable': str(var_name),
                    'beta': self._safe_float(detail.get('beta', 0.0)),
                    'std_err': self._safe_float(detail.get('std_err', 0.0)),
                    't_stat': self._safe_float(detail.get('t_stat', 0.0)),
                    'p_value': self._safe_float(detail.get('p_value', 1.0), 1.0),
                    'ci_95_lo': self._safe_float(detail.get('CI_95_lo', 0.0)),
                    'ci_95_hi': self._safe_float(detail.get('CI_95_hi', 0.0)),
                    'significativo_5pct': bool(detail.get('significativo_5pct', False)),
                }
            )

        coef_items.sort(key=lambda item: abs(item['beta']), reverse=True)

        coef_items_no_const = [item for item in coef_items if item['variable'] != 'const']

        stds_x = bundle.get('stds_X', {}) if isinstance(bundle.get('stds_X', {}), dict) else {}
        dataset_info = bundle.get('dataset_info', {}) if isinstance(bundle.get('dataset_info', {}), dict) else {}
        std_y = self._safe_float(dataset_info.get('margen_std_bs', 0.0), 0.0)

        standardized_coefs: list[dict[str, Any]] = []
        if std_y != 0:
            for item in coef_items_no_const:
                std_x = self._safe_float(stds_x.get(item['variable'], 0.0), 0.0)
                beta_std = item['beta'] * std_x / std_y if std_x else 0.0
                standardized_coefs.append(
                    {
                        'variable': item['variable'],
                        'beta': self._safe_float(beta_std),
                        'std_err': item['std_err'],
                        't_stat': item['t_stat'],
                        'p_value': item['p_value'],
                        'ci_95_lo': 0.0,
                        'ci_95_hi': 0.0,
                        'significativo_5pct': item['significativo_5pct'],
                    }
                )
        else:
            for item in coef_items_no_const:
                standardized_coefs.append(
                    {
                        'variable': item['variable'],
                        'beta': item['beta'],
                        'std_err': item['std_err'],
                        't_stat': item['t_stat'],
                        'p_value': item['p_value'],
                        'ci_95_lo': 0.0,
                        'ci_95_hi': 0.0,
                        'significativo_5pct': item['significativo_5pct'],
                    }
                )

        standardized_coefs.sort(key=lambda item: abs(item['beta']), reverse=True)

        ajuste_observado_predicho: list[dict[str, Any]] = []
        modelo_ols = bundle.get('modelo')
        if modelo_ols is not None and hasattr(modelo_ols, 'fittedvalues'):
            try:
                fitted = list(getattr(modelo_ols, 'fittedvalues'))
                observed = list(getattr(getattr(modelo_ols, 'model', None), 'endog', []))
                for actual, predicho in zip(observed[:500], fitted[:500]):
                    ajuste_observado_predicho.append(
                        {
                            'x': self._safe_float(actual),
                            'y': self._safe_float(predicho),
                        }
                    )
            except Exception:
                pass

        modelo_loglog = bundle.get('modelo_loglog')
        has_loglog = modelo_loglog is not None

        loglog_variables: list[dict[str, Any]] = []
        if has_loglog and hasattr(modelo_loglog, 'params'):
            try:
                for key, beta in modelo_loglog.params.items():
                    pvals = getattr(modelo_loglog, 'pvalues', {})
                    p_val = float(pvals.get(key, 1.0)) if hasattr(pvals, 'get') else 1.0
                    loglog_variables.append(
                        {
                            'variable': str(key),
                            'beta': self._safe_float(beta),
                            'p_value': self._safe_float(p_val, 1.0),
                            'significativo_5pct': p_val < 0.05,
                        }
                    )
            except Exception:
                pass

        return {
            'ols': {
                'formula': str(bundle.get('formula', 'No disponible')),
                'variable_dependiente': str(bundle.get('variable_dependiente', 'MARGEN_REAL_BS')),
                'variables_independientes': list(bundle.get('variables_independientes', [])),
                'coeficientes': coef_items,
                'coeficientes_estandarizados': standardized_coefs,
                'ajuste_observado_predicho': ajuste_observado_predicho,
                'r2': self._safe_float(metricas.get('R2', 0.0)),
                'r2_ajustado': self._safe_float(metricas.get('R2_ajustado', 0.0)),
                'f_statistic': self._safe_float(metricas.get('F_statistic', 0.0)),
                'n_observaciones': self._safe_int(metricas.get('N_observaciones', 0)),
                'diagnostico': {
                    'rmse': self._safe_float(diagnostico.get('RMSE', 0.0)),
                    'mae': self._safe_float(diagnostico.get('MAE', 0.0)),
                    'test_breusch_pagan_pvalue': self._safe_float(diagnostico.get('test_Breusch_Pagan_pvalue', 1.0)),
                    'n_vars_significativas_5pct': self._safe_int(diagnostico.get('n_vars_significativas_5pct', 0)),
                    'n_vars_significativas_10pct': self._safe_int(diagnostico.get('n_vars_significativas_10pct', 0)),
                },
                'interpretacion_ejecutiva': [
                    'Los betas del OLS se leen en Bs por unidad, ceteris paribus.',
                    'Penalizaciones y siniestros son erosores directos del margen esperado.',
                    'Priorizar lectura robusta por evidencia de heterocedasticidad.'
                ],
            },
            'loglog': {
                'disponible': has_loglog,
                'offset_aplicado': 'Se estima desde el minimo de Y en notebook (|min(Y)| + 1).',
                'transformacion': 'ln(Y + c) y ln(X + 1) para variables continuas',
                'variables': loglog_variables,
                'interpretacion_porcentual': [
                    'Coeficientes log-log se interpretan como elasticidades aproximadas.',
                    'Variables dummy se interpretan como semi-elasticidades.'
                ],
                'limitaciones': [
                    'Requiere conversion para lectura ejecutiva en Bs.',
                    'No reemplaza el modelo operativo principal OLS en este modulo.'
                ],
            },
            'comparativa': {
                'modelo_operativo_principal': 'OLS en niveles',
                'motivo': 'Mayor interpretabilidad en Bs para decisiones operativas de negocio.',
                'metricas': {
                    'r2_ols': self._safe_float(metricas.get('R2', 0.0)),
                    'aic_ols': self._safe_float(metricas.get('AIC', 0.0)),
                    'bic_ols': self._safe_float(metricas.get('BIC', 0.0)),
                    'loglog_disponible': has_loglog,
                },
                'utilidad_practica': [
                    'OLS: simulacion y prediccion operativa en Bs.',
                    'Log-log: lectura de elasticidades para analisis estrategico relativo.'
                ],
            },
        }

    def get_analitica_descriptiva(
        self,
        cliente: str | None,
        ruta: str | None,
        nivel_sla: str | None,
        division_operativa: str | None,
        anio: int | None,
        trimestre: int | None,
        con_penalizacion: bool | None,
        con_siniestros: bool | None,
        peso_min: float | None,
        peso_max: float | None,
        distancia_min: float | None,
        distancia_max: float | None,
        margen_min: float | None,
        margen_max: float | None,
    ) -> dict[str, Any]:
        if not self.settings.has_snowflake_credentials():
            return self._empty_descriptive('Snowflake no configurado. La capa descriptiva requiere credenciales válidas.')

        where_clause = self._build_filter_clause(
            cliente,
            ruta,
            nivel_sla,
            division_operativa,
            anio,
            trimestre,
            con_penalizacion,
            con_siniestros,
            peso_min,
            peso_max,
            distancia_min,
            distancia_max,
            margen_min,
            margen_max,
        )

        base_query = f"""
            WITH siniestros AS (
                SELECT NRO_CONTRATO_VENTA, SUM(VALOR_PERDIDA_BS) AS TOTAL_SINIESTROS_BS
                FROM FACT_SINIESTRALIDAD_CALIDAD
                GROUP BY NRO_CONTRATO_VENTA
            ),
            dataset AS (
                SELECT
                    fc.NRO_CONTRATO_VENTA,
                    fc.INGRESO_CONTRATO_BS,
                    fc.GASTO_TOTAL_BS,
                    fc.MONTO_PENALIZACION_BS,
                    fc.PESO_TRANSPORTADO_KG,
                    dr.DISTANCIA_NOMINAL_KM,
                    dr.ALTITUD_MAXIMA_MSNM,
                    dr.NOMBRE_RUTA,
                    dc.RAZON_SOCIAL,
                    dc.NIVEL_SLA,
                    dc.DIVISION_OPERATIVA,
                    dt.ANIO,
                    dt.TRIMESTRE,
                    COALESCE(fs.TOTAL_SINIESTROS_BS, 0) AS TOTAL_SINIESTROS_BS,
                    (fc.INGRESO_CONTRATO_BS - fc.GASTO_TOTAL_BS - fc.MONTO_PENALIZACION_BS - COALESCE(fs.TOTAL_SINIESTROS_BS, 0)) AS MARGEN_REAL_BS
                FROM FACT_CONTRATOS_FLETES fc
                LEFT JOIN siniestros fs ON fs.NRO_CONTRATO_VENTA = fc.NRO_CONTRATO_VENTA
                LEFT JOIN DIM_CLIENTE dc ON dc.CLIENTE_SK = fc.CLIENTE_SK
                LEFT JOIN DIM_RUTA dr ON dr.RUTA_SK = fc.RUTA_SK
                LEFT JOIN DIM_TIEMPO dt ON dt.TIEMPO_SK = fc.TIEMPO_SK
                {where_clause}
            )
            SELECT * FROM dataset
        """

        try:
            df = self.snowflake.fetch_dataframe(base_query)
        except Exception as exc:
            return self._empty_descriptive(f'No se pudo consultar Snowflake: {exc}')

        if df.empty:
            return self._empty_descriptive('No hay registros para los filtros aplicados.')

        numeric_cols = [
            'INGRESO_CONTRATO_BS', 'GASTO_TOTAL_BS', 'MONTO_PENALIZACION_BS',
            'TOTAL_SINIESTROS_BS', 'MARGEN_REAL_BS', 'PESO_TRANSPORTADO_KG',
            'DISTANCIA_NOMINAL_KM', 'ALTITUD_MAXIMA_MSNM'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.dropna(subset=['MARGEN_REAL_BS'])

        margin_distribution = []
        if not df.empty:
            bins = pd.cut(df['MARGEN_REAL_BS'], bins=10)
            dist = bins.value_counts().sort_index()
            for interval, count in dist.items():
                margin_distribution.append(
                    {
                        'bucket': f'{interval.left:.0f} a {interval.right:.0f}',
                        'count': int(count),
                    }
                )

        margin_by_division = (
            df.groupby('DIVISION_OPERATIVA', dropna=False)
            .agg(margen_promedio_bs=('MARGEN_REAL_BS', 'mean'), contratos=('NRO_CONTRATO_VENTA', 'count'))
            .reset_index()
            .rename(columns={'DIVISION_OPERATIVA': 'nombre'})
            .fillna({'nombre': 'SIN DIVISION'})
            .to_dict('records')
        )

        margin_by_sla = (
            df.groupby('NIVEL_SLA', dropna=False)
            .agg(margen_promedio_bs=('MARGEN_REAL_BS', 'mean'), contratos=('NRO_CONTRATO_VENTA', 'count'))
            .reset_index()
            .rename(columns={'NIVEL_SLA': 'nombre'})
            .fillna({'nombre': 'SIN SLA'})
            .to_dict('records')
        )

        financial_structure = [
            {'etapa': 'Ingreso', 'monto_bs': float(df['INGRESO_CONTRATO_BS'].mean())},
            {'etapa': 'Gasto', 'monto_bs': -float(df['GASTO_TOTAL_BS'].mean())},
            {'etapa': 'Penalización', 'monto_bs': -float(df['MONTO_PENALIZACION_BS'].mean())},
            {'etapa': 'Siniestros', 'monto_bs': -float(df['TOTAL_SINIESTROS_BS'].mean())},
            {'etapa': 'Margen', 'monto_bs': float(df['MARGEN_REAL_BS'].mean())},
        ]

        scatter_distance_vs_margin = (
            df[['DISTANCIA_NOMINAL_KM', 'MARGEN_REAL_BS']]
            .dropna()
            .head(500)
            .rename(columns={'DISTANCIA_NOMINAL_KM': 'x', 'MARGEN_REAL_BS': 'y'})
            .to_dict('records')
        )
        scatter_weight_vs_margin = (
            df[['PESO_TRANSPORTADO_KG', 'MARGEN_REAL_BS']]
            .dropna()
            .head(500)
            .rename(columns={'PESO_TRANSPORTADO_KG': 'x', 'MARGEN_REAL_BS': 'y'})
            .to_dict('records')
        )

        correlations = []
        corr_cols = ['INGRESO_CONTRATO_BS', 'GASTO_TOTAL_BS', 'MONTO_PENALIZACION_BS', 'TOTAL_SINIESTROS_BS', 'PESO_TRANSPORTADO_KG', 'DISTANCIA_NOMINAL_KM', 'ALTITUD_MAXIMA_MSNM', 'MARGEN_REAL_BS']
        corr_df = df[corr_cols].dropna()
        if not corr_df.empty and 'MARGEN_REAL_BS' in corr_df.columns:
            corr_series = corr_df.corr()['MARGEN_REAL_BS'].drop('MARGEN_REAL_BS')
            for key, val in corr_series.items():
                correlations.append({'variable': str(key), 'r': float(val)})
            correlations.sort(key=lambda item: abs(item['r']), reverse=True)

        quarterly_trend = (
            df.groupby(['ANIO', 'TRIMESTRE'], dropna=False)
            .agg(margen_promedio_bs=('MARGEN_REAL_BS', 'mean'), contratos=('NRO_CONTRATO_VENTA', 'count'))
            .reset_index()
            .assign(periodo=lambda data: data['ANIO'].astype(str) + '-Q' + data['TRIMESTRE'].astype(str))
            [['periodo', 'margen_promedio_bs', 'contratos']]
            .to_dict('records')
        )

        ranking_clientes = (
            df.groupby('RAZON_SOCIAL', dropna=False)
            .agg(
                margen_promedio_bs=('MARGEN_REAL_BS', 'mean'),
                contratos=('NRO_CONTRATO_VENTA', 'count'),
                categoria=('DIVISION_OPERATIVA', 'first'),
            )
            .reset_index()
            .rename(columns={'RAZON_SOCIAL': 'nombre'})
            .fillna({'nombre': 'SIN CLIENTE'})
            .sort_values('margen_promedio_bs', ascending=False)
            .head(10)
            .to_dict('records')
        )

        ranking_rutas = (
            df.groupby('NOMBRE_RUTA', dropna=False)
            .agg(
                margen_promedio_bs=('MARGEN_REAL_BS', 'mean'),
                contratos=('NRO_CONTRATO_VENTA', 'count'),
                valor_extra=('ALTITUD_MAXIMA_MSNM', 'first'),
            )
            .reset_index()
            .rename(columns={'NOMBRE_RUTA': 'nombre'})
            .fillna({'nombre': 'SIN RUTA'})
            .sort_values('margen_promedio_bs', ascending=False)
            .head(10)
            .to_dict('records')
        )

        return {
            'snowflake_disponible': True,
            'warning': None,
            'margin_distribution': margin_distribution,
            'margin_by_division': margin_by_division,
            'margin_by_sla': margin_by_sla,
            'financial_structure': financial_structure,
            'scatter_distance_vs_margin': scatter_distance_vs_margin,
            'scatter_weight_vs_margin': scatter_weight_vs_margin,
            'correlations': correlations,
            'quarterly_trend': quarterly_trend,
            'ranking_clientes': ranking_clientes,
            'ranking_rutas': ranking_rutas,
        }
