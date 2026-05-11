from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

try:
    import snowflake.connector  # type: ignore

    _SNOWFLAKE_AVAILABLE = True
except Exception:
    snowflake = None  # type: ignore
    _SNOWFLAKE_AVAILABLE = False

from app.core.config import Settings
from app.modules.mineria.repositories.model_bundle_repository import ModelBundleRepository


RUTAS_REF = [
    {'nombre': 'SCZ → La Paz', 'distancia': 1350, 'altitud': 4150, 'complejidad': 4},
    {'nombre': 'SCZ → Cochabamba', 'distancia': 500, 'altitud': 2550, 'complejidad': 2},
    {'nombre': 'SCZ → Oruro', 'distancia': 820, 'altitud': 3706, 'complejidad': 3},
    {'nombre': 'SCZ → Trinidad', 'distancia': 610, 'altitud': 237, 'complejidad': 2},
    {'nombre': 'SCZ → Cobija', 'distancia': 1800, 'altitud': 300, 'complejidad': 4},
    {'nombre': 'LPZ → Oruro', 'distancia': 230, 'altitud': 3900, 'complejidad': 2},
    {'nombre': 'CBB → Sucre', 'distancia': 330, 'altitud': 2900, 'complejidad': 3},
    {'nombre': 'SCZ → Potosí', 'distancia': 900, 'altitud': 4090, 'complejidad': 4},
]

PLACAS_FLOTA = [
    'TF-001',
    'TF-002',
    'TF-003',
    'TF-004',
    'TF-005',
    'TF-006',
    'TF-007',
    'TF-008',
]

CONDUCTORES = [
    'Carlos Mamani',
    'Roberto Quispe',
    'Luis Flores',
    'Juan Condori',
    'Pedro Vargas',
    'Miguel Tapia',
    'Andrés Rojas',
    'Óscar Salinas',
]


def _parse_complejidad(raw: Any) -> int:
    value = str(raw).strip().upper()
    if 'BAJA' in value:
        return 1
    if 'MEDIA' in value:
        return 2
    if 'ALTA' in value:
        return 3
    if 'EXTREMA' in value or 'CRITICA' in value or 'MUY' in value:
        return 4
    try:
        return int(float(value))
    except Exception:
        return 2


def _risk_label(prob: float) -> str:
    if prob >= 0.80:
        return 'CRÍTICO'
    if prob >= 0.65:
        return 'URGENTE'
    if prob >= 0.40:
        return 'ALERTA'
    return 'NORMAL'


def _feature_value_map(data: dict[str, Any]) -> dict[str, float]:
    return {key: float(value) if value is not None else 0.0 for key, value in data.items()}


@dataclass
class TruckState:
    placa: str
    conductor: str
    ruta: str
    distancia_nominal_km: float
    altitud_maxima_msnm: float
    nivel_complejidad: int
    capacidad_max_kg: float
    horometro_frio_acumulado: float
    puntaje_eficiencia_termica: float
    peso_transportado_kg: float
    es_saboteado: bool = False
    temp_objetivo: float = field(default_factory=lambda: random.choice([-20, -18, -15, 4, 6]))
    progreso: float = 0.0
    estado_viaje: str = 'INICIANDO'
    ticks_en_estado: int = 0
    ticks_finalizado: int = 0
    apertura_puertas: int = 0
    motor_apagados: int = 0
    total_lecturas: int = 0
    falla_activa: bool = False
    drift_temp: float = 0.0
    sabotaje_activado: bool = False

    def _reset_viaje(self) -> None:
        self.progreso = 0.0
        self.estado_viaje = 'INICIANDO'
        self.ticks_en_estado = 0
        self.ticks_finalizado = 0
        self.apertura_puertas = 0
        self.motor_apagados = 0
        self.total_lecturas = random.randint(5, 20)
        self.drift_temp = 0.0
        self.sabotaje_activado = False
        self.falla_activa = self.es_saboteado or random.random() < 0.10

    def tick(self, es_lluvia: bool, es_feriado: bool) -> dict[str, Any]:
        self.ticks_en_estado += 1
        self.total_lecturas += 1

        if self.estado_viaje == 'INICIANDO':
            if self.ticks_en_estado >= random.randint(1, 2):
                self.estado_viaje = 'EN_RUTA'
                self.ticks_en_estado = 0
            mensaje_estado = '🚦 Saliendo de planta — Chequeo completado'

        elif self.estado_viaje == 'EN_RUTA':
            incremento = 0.045 + random.uniform(-0.01, 0.012)
            if es_lluvia:
                incremento += 0.004
            self.progreso = min(1.0, self.progreso + incremento)

            if self.es_saboteado and not self.sabotaje_activado and self.progreso >= 0.40:
                self.sabotaje_activado = True
                self.falla_activa = True
                self.drift_temp += random.uniform(8.0, 15.0)
                self.apertura_puertas += random.randint(6, 12)
                self.motor_apagados += random.randint(5, 8)

            if self.progreso >= 1.0:
                self.estado_viaje = 'FINALIZADO'
                self.ticks_en_estado = 0
                self.ticks_finalizado = 0

            pct_ruta = int(self.progreso * 100)
            if self.sabotaje_activado:
                mensaje_estado = f'🚨 ALERTA TÉRMICA — {pct_ruta}% de ruta completado'
            else:
                mensaje_estado = f'🚛 En tránsito — {pct_ruta}% completado'

        elif self.estado_viaje == 'FINALIZADO':
            self.ticks_finalizado += 1
            mensaje_estado = '✅ Llegada a destino confirmada — Descargando'
            if self.ticks_finalizado >= 4:
                self._reset_viaje()
                mensaje_estado = '🔄 Iniciando nuevo viaje...'
        else:
            self.estado_viaje = 'EN_RUTA'
            mensaje_estado = '🚛 En tránsito'

        altitud_actual = self.altitud_maxima_msnm * abs(math.sin(math.pi * self.progreso))
        temp_base = self.temp_objetivo
        if self.estado_viaje == 'FINALIZADO':
            self.drift_temp += random.uniform(0.5, 1.5)
        elif self.falla_activa and not self.es_saboteado:
            self.drift_temp += random.uniform(0.2, 0.8)
        elif self.sabotaje_activado:
            self.drift_temp += random.uniform(0.8, 1.8)

        ruido_temp = random.uniform(-1.1, 1.1)
        temp_actual = temp_base + self.drift_temp + ruido_temp + (0.6 if es_lluvia else 0.0) + (0.3 if es_feriado else 0.0)

        variacion_prom = abs(temp_actual - temp_base) + random.uniform(0.2, 1.0)
        variacion_max = variacion_prom + random.uniform(0.5, 1.8)
        diferencia_temp = max(0.0, variacion_max + random.uniform(1.0, 2.5))
        apertura_delta = random.randint(0, 2)
        motor_delta = random.randint(0, 1)
        if es_lluvia:
            apertura_delta += random.randint(0, 1)
        if es_feriado:
            motor_delta += random.randint(0, 1)
        self.apertura_puertas += apertura_delta
        self.motor_apagados += motor_delta

        velocidad = max(25.0, min(85.0, random.gauss(58.0, 11.0) - (8.0 if es_lluvia else 0.0)))
        humedad = max(25.0, min(99.0, random.gauss(60.0, 13.0) + (12.0 if es_lluvia else 0.0)))
        ocupacion = min(1.0, max(0.35, self.peso_transportado_kg / max(self.capacidad_max_kg, 1.0)))
        cond_adversa = int(bool(es_lluvia)) + int(bool(es_feriado))

        return {
            'DISTANCIA_NOMINAL_KM': float(self.distancia_nominal_km),
            'ALTITUD_MAXIMA_MSNM': float(altitud_actual),
            'NIVEL_COMPLEJIDAD': float(self.nivel_complejidad),
            'RIESGO_COMPLEJIDAD': float(self.nivel_complejidad),
            'EPOCA_LLUVIAS': int(bool(es_lluvia)),
            'ES_FIN_SEMANA': int(bool(es_feriado)),
            'ES_FERIADO_BOLIVIA': int(bool(es_feriado)),
            'CONDICION_ADVERSA': float(cond_adversa),
            'AVG_VARIACION_TERMICA': float(variacion_prom),
            'MAX_VARIACION_TERMICA': float(variacion_max),
            'DIFERENCIA_TEMP': float(diferencia_temp),
            'CONTEO_APERTURA_PUERTA': float(self.apertura_puertas),
            'CONTEO_MOTOR_APAGADO': float(self.motor_apagados),
            'RATIO_APERTURA_PUERTA': float(self.apertura_puertas / max(self.total_lecturas, 1)),
            'AVG_TEMP_INTERNA_C': float(temp_actual),
            'AVG_HUMEDAD_PCT': float(humedad),
            'AVG_VELOCIDAD_KMH': float(velocidad),
            'HOROMETRO_FRIO_ACUMULADO': float(self.horometro_frio_acumulado + self.ticks_en_estado * 4.5),
            'TASA_OCUPACION': float(ocupacion),
            'PUNTAJE_EFICIENCIA_TERMICA': float(self.puntaje_eficiencia_termica),
            'DURACION_REAL_HRS': float(max(2.0, (self.distancia_nominal_km / max(velocidad, 1.0)) + random.uniform(-0.8, 1.2))),
            'PESO_TRANSPORTADO_KG': float(self.peso_transportado_kg),
            'TOTAL_LECTURAS_IOT': float(self.total_lecturas),
            '_estado_viaje': self.estado_viaje,
            '_mensaje_estado': mensaje_estado,
            '_progreso_ruta': float(self.progreso),
            '_falla_activa': int(self.falla_activa),
            '_temp_actual': float(temp_actual),
        }

    def metadata(self) -> dict[str, Any]:
        return {
            'placa': self.placa,
            'conductor': self.conductor,
            'ruta': self.ruta,
            'estado_viaje': self.estado_viaje,
            'progreso': self.progreso,
            'falla_activa': self.falla_activa,
            'es_saboteado': self.es_saboteado,
        }


class TorreControlService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.repository = ModelBundleRepository(settings)
        self._bundle: dict[str, Any] | None = None
        self._catalog: pd.DataFrame | None = None
        self._fleet: dict[str, TruckState] = {}
        self._alerts: list[dict[str, Any]] = []
        self._history: list[dict[str, Any]] = []
        self._cycle = 0
        self._last_update = '—'
        self._latest_snapshot: dict[str, Any] | None = None

    def preload(self) -> None:
        self._ensure_initialized()
        self._ensure_bundle()

    def _ensure_initialized(self) -> None:
        if self._catalog is not None and self._fleet:
            return
        self._catalog = self._load_fleet_catalog()
        self._fleet = self._build_fleet(self._catalog)

    def _ensure_bundle(self) -> dict[str, Any]:
        if self._bundle is not None:
            return self._bundle
        model_path = self.repository.resolve_model_path()
        bundle = self.repository.load_bundle(model_path)
        if bundle is None:
            raise ValueError(f'No se pudo cargar el bundle desde: {model_path}')
        self._bundle = bundle
        return bundle

    def _load_fleet_catalog(self) -> pd.DataFrame:
        if _SNOWFLAKE_AVAILABLE and self.settings.has_snowflake_credentials():
            try:
                conn = snowflake.connector.connect(
                    account=self.settings.snowflake_account,
                    user=self.settings.snowflake_user,
                    password=self.settings.snowflake_password,
                    warehouse=self.settings.snowflake_warehouse,
                    database=self.settings.snowflake_database,
                    schema=self.settings.snowflake_schema,
                    role=self.settings.snowflake_role,
                )
                sql = """
                SELECT
                    dv.PLACA_CIRCULACION AS PLACA,
                    dch.NOMBRE_COMPLETO AS CONDUCTOR,
                    dr.NOMBRE_RUTA,
                    dr.DISTANCIA_NOMINAL_KM,
                    dr.ALTITUD_MAXIMA_MSNM,
                    dr.NIVEL_COMPLEJIDAD,
                    dv.CAPACIDAD_MAX_KG,
                    dv.HOROMETRO_FRIO_ACUMULADO,
                    dch.PUNTAJE_EFICIENCIA_TERMICA,
                    fc.PESO_TRANSPORTADO_KG
                FROM RAW_TRANSFREEZER.DBT_IDENEGOCIOS.FACT_CONTRATOS_FLETES fc
                JOIN RAW_TRANSFREEZER.DBT_IDENEGOCIOS.DIM_VEHICULO dv ON fc.VEHICULO_SK = dv.VEHICULO_SK
                JOIN RAW_TRANSFREEZER.DBT_IDENEGOCIOS.DIM_CHOFER dch ON fc.CHOFER_SK = dch.CHOFER_SK
                JOIN RAW_TRANSFREEZER.DBT_IDENEGOCIOS.DIM_RUTA dr ON fc.RUTA_SK = dr.RUTA_SK
                QUALIFY ROW_NUMBER() OVER(PARTITION BY dv.PLACA_CIRCULACION ORDER BY fc.TIEMPO_SK DESC) = 1
                LIMIT 8
                """
                cur = conn.cursor()
                cur.execute(sql)
                df = cur.fetch_pandas_all()
                cur.close()
                conn.close()
                if not df.empty:
                    df.columns = [col.upper() for col in df.columns]
                    return df
            except Exception:
                pass

        records: list[dict[str, Any]] = []
        random.seed(42)
        for idx, placa in enumerate(PLACAS_FLOTA):
            ruta = RUTAS_REF[idx % len(RUTAS_REF)]
            records.append(
                {
                    'PLACA': placa,
                    'CONDUCTOR': CONDUCTORES[idx],
                    'NOMBRE_RUTA': ruta['nombre'],
                    'DISTANCIA_NOMINAL_KM': ruta['distancia'],
                    'ALTITUD_MAXIMA_MSNM': ruta['altitud'],
                    'NIVEL_COMPLEJIDAD': ruta['complejidad'],
                    'CAPACIDAD_MAX_KG': random.choice([15000, 18000, 20000]),
                    'HOROMETRO_FRIO_ACUMULADO': random.randint(1000, 14000),
                    'PUNTAJE_EFICIENCIA_TERMICA': random.randint(55, 95),
                    'PESO_TRANSPORTADO_KG': random.randint(10000, 19000),
                }
            )
        return pd.DataFrame(records)

    def _build_fleet(self, catalog: pd.DataFrame) -> dict[str, TruckState]:
        fleet: dict[str, TruckState] = {}
        for idx, row in catalog.reset_index(drop=True).iterrows():
            placa = str(row.get('PLACA', f'TF-{idx + 1:03d}'))
            fleet[placa] = TruckState(
                placa=placa,
                conductor=str(row.get('CONDUCTOR', 'Sin asignar')),
                ruta=str(row.get('NOMBRE_RUTA', 'Desconocida')),
                distancia_nominal_km=float(row.get('DISTANCIA_NOMINAL_KM', 500)),
                altitud_maxima_msnm=float(row.get('ALTITUD_MAXIMA_MSNM', 2500)),
                nivel_complejidad=_parse_complejidad(row.get('NIVEL_COMPLEJIDAD', 2)),
                capacidad_max_kg=float(row.get('CAPACIDAD_MAX_KG', 18000)),
                horometro_frio_acumulado=float(row.get('HOROMETRO_FRIO_ACUMULADO', 5000)),
                puntaje_eficiencia_termica=float(row.get('PUNTAJE_EFICIENCIA_TERMICA', 75)),
                peso_transportado_kg=float(row.get('PESO_TRANSPORTADO_KG', 14000)),
                es_saboteado=(idx < 2),
            )
            if idx < 2:
                fleet[placa].estado_viaje = 'EN_RUTA'
                fleet[placa].progreso = 0.32 * (idx + 1)
        return fleet

    def _get_bundle_summary(self) -> dict[str, Any]:
        bundle = self._ensure_bundle()
        return {
            'nombre': str(bundle.get('name', bundle.get('nombre', 'Torre de Control SIO'))),
            'version': str(bundle.get('version', '1.0')),
            'training_date': str(bundle.get('training_date', bundle.get('fecha_entreno', 'N/A'))),
            'model_name': str(bundle.get('name', bundle.get('modelo', 'best_model'))),
            'feature_count': len(bundle.get('features', [])),
            'cluster_feature_count': len(bundle.get('cluster_features', bundle.get('features', []))),
            'umbrales': {k: float(v) for k, v in bundle.get('umbrales', {}).items()} if isinstance(bundle.get('umbrales', {}), dict) else {},
            'metrics': {k: float(v) for k, v in bundle.get('metrics', {}).items()} if isinstance(bundle.get('metrics', {}), dict) else {},
        }

    def _predict_riesgo(self, raw_data: dict[str, Any]) -> tuple[float, int, str, dict[str, float]]:
        bundle = self._ensure_bundle()
        model = bundle['model']
        scaler = bundle['scaler']
        cluster_model = bundle['cluster_model']
        cluster_scaler = bundle['cluster_scaler']
        features = list(bundle.get('features', []))
        cluster_features = list(bundle.get('cluster_features', features))

        cluster_dict = {feature: raw_data.get(feature, 0.0) for feature in cluster_features}
        x_cluster = pd.DataFrame([cluster_dict])
        x_cluster_scaled = cluster_scaler.transform(x_cluster)
        cluster = int(cluster_model.predict(x_cluster_scaled)[0])

        enriched = dict(raw_data)
        enriched['CLUSTER_RIESGO'] = cluster
        model_dict = {feature: enriched.get(feature, 0.0) for feature in features}
        x_model = pd.DataFrame([model_dict])
        x_model_scaled = scaler.transform(x_model)
        prob = min(float(model.predict_proba(x_model_scaled)[0][1]), 0.99)

        try:
            importances = getattr(model, 'feature_importances_', None)
            if importances is None:
                raise AttributeError
            values_scaled = x_model_scaled[0]
            contributions = {
                features[idx]: float(importances[idx] * abs(values_scaled[idx]))
                for idx in range(len(features))
            }
            contributions.pop('CLUSTER_RIESGO', None)
        except Exception:
            contributions = {}

        top_feature = max(contributions, key=lambda key: abs(contributions[key])) if contributions else None
        if top_feature == 'AVG_VARIACION_TERMICA':
            base = '⚠️ Variación térmica elevada: verificar aislamiento del furgón y ajustar set-point del motor Thermo King.'
        elif top_feature == 'MAX_VARIACION_TERMICA':
            base = '🚨 Pico térmico crítico detectado: riesgo inminente de ruptura de cadena de frío. Contactar supervisor de inmediato.'
        elif top_feature == 'DIFERENCIA_TEMP':
            base = '🌡️ Amplitud térmica excesiva: producto en zona de riesgo sanitario. Detener y verificar carga.'
        elif top_feature == 'CONTEO_APERTURA_PUERTA':
            base = '🚪 Exceso de apertura de puertas: llamar al chofer y verificar paradas no autorizadas en ruta.'
        elif top_feature == 'CONTEO_MOTOR_APAGADO':
            base = '🔧 Motor frigorífico apagado en ruta: falla crítica inminente. Detener vehículo y solicitar apoyo técnico.'
        elif top_feature == 'ALTITUD_MAXIMA_MSNM':
            base = '⛰️ Ruta altiplánica de alta exigencia: activar protocolo de monitoreo reforzado cada 15 min.'
        elif top_feature == 'HOROMETRO_FRIO_ACUMULADO':
            base = '🔩 Motor Thermo King supera horómetro de servicio. Programar mantenimiento preventivo urgente.'
        elif top_feature == 'CONDICION_ADVERSA':
            base = '🌧️ Condiciones climáticas adversas + feriado: incrementar frecuencia de check-in con el conductor.'
        elif top_feature == 'PUNTAJE_EFICIENCIA_TERMICA':
            base = '👤 Conductor con bajo puntaje de eficiencia: asignar supervisor o reasignar a conductor de mayor experiencia.'
        elif top_feature == 'AVG_HUMEDAD_PCT':
            base = '💧 Humedad interna elevada: revisar sellado del furgón y posible condensación sobre la carga.'
        elif top_feature == 'AVG_TEMP_INTERNA_C':
            base = '🌡️ Temperatura interna fuera de rango objetivo: recalibrar el termostato del equipo de frío.'
        else:
            base = '⚠️ Múltiples indicadores fuera de rango. Activar protocolo de revisión integral antes del próximo punto de control.'

        if prob >= 0.80:
            prefix = '🔴 CRÍTICO — '
        elif prob >= 0.65:
            prefix = '🟠 URGENTE — '
        elif prob >= 0.40:
            prefix = '🟡 PREVENTIVO — '
        else:
            prefix = '🟢 INFO — '

        return prob, cluster, prefix + base, contributions

    def _calibrate_business_probability(
        self,
        truck: TruckState,
        telemetry: dict[str, Any],
        model_prob: float,
    ) -> float:
        def _clip(value: float, upper: float) -> float:
            return max(0.0, min(value, upper))

        variacion = float(telemetry.get('AVG_VARIACION_TERMICA', 0.0))
        variacion_max = float(telemetry.get('MAX_VARIACION_TERMICA', 0.0))
        diferencia_temp = float(telemetry.get('DIFERENCIA_TEMP', 0.0))
        aperturas = float(telemetry.get('CONTEO_APERTURA_PUERTA', 0.0))
        motor_apagado = float(telemetry.get('CONTEO_MOTOR_APAGADO', 0.0))
        humedad = float(telemetry.get('AVG_HUMEDAD_PCT', 0.0))
        eficiencia = float(telemetry.get('PUNTAJE_EFICIENCIA_TERMICA', truck.puntaje_eficiencia_termica))
        altitud = float(telemetry.get('ALTITUD_MAXIMA_MSNM', truck.altitud_maxima_msnm))
        complejidad = float(telemetry.get('RIESGO_COMPLEJIDAD', truck.nivel_complejidad))

        score = 0.0
        score += _clip(variacion / 8.0, 1.0) * 0.24
        score += _clip(variacion_max / 12.0, 1.0) * 0.12
        score += _clip(diferencia_temp / 15.0, 1.0) * 0.10
        score += _clip(aperturas / 10.0, 1.0) * 0.14
        score += _clip(motor_apagado / 8.0, 1.0) * 0.14
        score += _clip(max(0.0, humedad - 60.0) / 35.0, 1.0) * 0.05
        score += _clip(max(0.0, 85.0 - eficiencia) / 35.0, 1.0) * 0.07
        score += _clip(max(0.0, altitud - 2400.0) / 1800.0, 1.0) * 0.04
        score += _clip(complejidad / 4.0, 1.0) * 0.04

        if truck.es_saboteado:
            score += 0.22

        if truck.estado_viaje == 'EN_RUTA':
            score += 0.03
        elif truck.estado_viaje == 'FINALIZADO':
            score *= 0.6

        calibrated = max(model_prob, score)
        return min(calibrated, 0.99)

    def _register_alert(
        self,
        placa: str,
        conductor: str,
        ruta: str,
        prob: float,
        prescripcion: str,
        cluster: int,
    ) -> None:
        if prob < 0.65:
            return

        nivel = 'CRÍTICO' if prob >= 0.80 else 'URGENTE'
        emoji = '🔴' if nivel == 'CRÍTICO' else '🟠'
        entry = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'fecha': datetime.now().strftime('%d/%m/%Y'),
            'placa': placa,
            'conductor': conductor,
            'ruta': ruta,
            'prob_pct': round(prob * 100, 1),
            'nivel': nivel,
            'emoji': emoji,
            'cluster': cluster,
            'prescripcion': prescripcion,
        }
        if self._alerts and self._alerts[-1]['placa'] == placa and self._alerts[-1]['timestamp'] == entry['timestamp']:
            return
        self._alerts.append(entry)
        self._alerts = self._alerts[-200:]

    def _build_snapshot(self, es_lluvia: bool, es_feriado: bool) -> dict[str, Any]:
        self._ensure_initialized()
        self._ensure_bundle()

        fleet_items: list[dict[str, Any]] = []
        for placa, truck in self._fleet.items():
            telemetry = truck.tick(es_lluvia=es_lluvia, es_feriado=es_feriado)
            raw = _feature_value_map({key: value for key, value in telemetry.items() if not key.startswith('_')})
            prob, cluster, prescripcion, _ = self._predict_riesgo(raw)
            business_prob = self._calibrate_business_probability(truck, telemetry, prob)

            self._register_alert(
                placa=placa,
                conductor=truck.conductor,
                ruta=truck.ruta,
                prob=business_prob,
                prescripcion=prescripcion,
                cluster=cluster,
            )

            fleet_items.append(
                {
                    'placa': placa,
                    'conductor': truck.conductor,
                    'ruta': truck.ruta,
                    'prob': business_prob,
                    'prob_model': prob,
                    'cluster': cluster,
                    'prescripcion': prescripcion,
                    'nivel': _risk_label(business_prob),
                    'telemetry': telemetry,
                    'metadata': truck.metadata(),
                }
            )

        avg_risk = float(sum(item['prob'] for item in fleet_items) / max(len(fleet_items), 1))
        critical_count = sum(1 for item in fleet_items if item['prob'] >= 0.80)
        self._cycle += 1
        self._last_update = datetime.now().strftime('%H:%M:%S')
        self._history.append(
            {
                'cycle': self._cycle,
                'avg_risk_pct': round(avg_risk * 100, 2),
                'critical_count': critical_count,
                'alert_count': len(self._alerts),
            }
        )
        self._history = self._history[-30:]

        summary = {
            'total_viajes': 1440,
            'tasa_siniestro_pct': 12.4,
            'perdida_promedio_bs': 85000.0,
            'rutas_activas': len(self._catalog) if self._catalog is not None else len(self._fleet),
            'camiones_activos': len(fleet_items),
            'camiones_en_riesgo': sum(1 for item in fleet_items if item['prob'] >= 0.65),
            'riesgo_promedio_pct': round(avg_risk * 100, 2),
            'alertas_totales': len(self._alerts),
            'alertas_criticas': sum(1 for item in self._alerts if item['nivel'] == 'CRÍTICO'),
            'last_update': self._last_update,
            'cycle': self._cycle,
        }

        self._latest_snapshot = {
            'summary': summary,
            'fleet': fleet_items,
            'alerts': list(reversed(self._alerts)),
            'history': list(self._history),
            'bundle': self._get_bundle_summary(),
        }
        return self._latest_snapshot

    def get_dashboard(self) -> dict[str, Any]:
        if self._latest_snapshot is None:
            return self._build_snapshot(es_lluvia=False, es_feriado=False)
        return self._latest_snapshot

    def tick(self, es_lluvia: bool = False, es_feriado: bool = False) -> dict[str, Any]:
        return self._build_snapshot(es_lluvia=es_lluvia, es_feriado=es_feriado)

    def get_fleet(self) -> list[dict[str, Any]]:
        return list(self.get_dashboard()['fleet'])

    def get_alerts(self) -> list[dict[str, Any]]:
        return list(self.get_dashboard()['alerts'])

    def clear_alerts(self) -> None:
        self._alerts = []
        self._history = []
        self._latest_snapshot = None
        self._cycle = 0
        self._last_update = '—'

    def get_history(self) -> list[dict[str, Any]]:
        return list(self.get_dashboard()['history'])


_service: TorreControlService | None = None


def get_torre_control_service(settings: Settings) -> TorreControlService:
    global _service
    if _service is None:
        _service = TorreControlService(settings)
    return _service
