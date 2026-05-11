from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AlertItem(BaseModel):
    timestamp: str
    fecha: str
    placa: str
    conductor: str
    ruta: str
    prob_pct: float
    nivel: str
    emoji: str
    cluster: int
    prescripcion: str


class TruckItem(BaseModel):
    placa: str
    conductor: str
    ruta: str
    prob: float = Field(ge=0.0, le=0.99)
    cluster: int
    prescripcion: str
    nivel: str
    telemetry: dict[str, Any]
    metadata: dict[str, Any]


class HistoryItem(BaseModel):
    cycle: int
    avg_risk_pct: float
    critical_count: int
    alert_count: int


class DashboardSummary(BaseModel):
    total_viajes: int
    tasa_siniestro_pct: float
    perdida_promedio_bs: float
    rutas_activas: int
    camiones_activos: int
    camiones_en_riesgo: int
    riesgo_promedio_pct: float
    alertas_totales: int
    alertas_criticas: int
    last_update: str
    cycle: int


class BundleSummary(BaseModel):
    nombre: str
    version: str
    training_date: str
    model_name: str
    feature_count: int
    cluster_feature_count: int
    umbrales: dict[str, float]
    metrics: dict[str, float]


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    fleet: list[TruckItem]
    alerts: list[AlertItem]
    history: list[HistoryItem]
    bundle: BundleSummary
