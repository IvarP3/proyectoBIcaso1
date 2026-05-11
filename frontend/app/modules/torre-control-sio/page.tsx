'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import './page.css';

type Summary = {
  total_viajes: number;
  tasa_siniestro_pct: number;
  perdida_promedio_bs: number;
  rutas_activas: number;
  camiones_activos: number;
  camiones_en_riesgo: number;
  riesgo_promedio_pct: number;
  alertas_totales: number;
  alertas_criticas: number;
  last_update: string;
  cycle: number;
};

type FleetItem = {
  placa: string;
  conductor: string;
  ruta: string;
  prob: number;
  cluster: number;
  prescripcion: string;
  nivel: string;
  telemetry: Record<string, any>;
  metadata: Record<string, any>;
};

type AlertItem = {
  timestamp: string;
  fecha: string;
  placa: string;
  conductor: string;
  ruta: string;
  prob_pct: number;
  nivel: string;
  emoji: string;
  cluster: number;
  prescripcion: string;
};

type HistoryItem = {
  cycle: number;
  avg_risk_pct: number;
  critical_count: number;
  alert_count: number;
};

type DashboardResponse = {
  summary: Summary;
  fleet: FleetItem[];
  alerts: AlertItem[];
  history: HistoryItem[];
  bundle: {
    nombre: string;
    version: string;
    training_date: string;
    model_name: string;
    feature_count: number;
    cluster_feature_count: number;
    umbrales: Record<string, number>;
    metrics: Record<string, number>;
  };
};

const API_BASE_CANDIDATES = [
  process.env.NEXT_PUBLIC_API_BASE_URL,
  'http://127.0.0.1:8000/api/v1/torre-control-sio',
  'http://localhost:8000/api/v1/torre-control-sio',
  '/api/v1/torre-control-sio',
].filter((value): value is string => Boolean(value));

function pickApiBase(): string {
  return API_BASE_CANDIDATES[0] ?? '/api/v1/torre-control-sio';
}

function formatPct(value: number): string {
  return `${value.toFixed(1)}%`;
}

function formatBs(value: number): string {
  return `Bs ${value.toLocaleString('es-BO', { maximumFractionDigits: 0 })}`;
}

function riskColor(prob: number): string {
  if (prob >= 0.8) return '#DA1E28';
  if (prob >= 0.65) return '#E85D3F';
  if (prob >= 0.4) return '#D29922';
  return '#2EA043';
}

function riskTone(prob: number): 'critical' | 'urgent' | 'warning' | 'normal' {
  if (prob >= 0.8) return 'critical';
  if (prob >= 0.65) return 'urgent';
  if (prob >= 0.4) return 'warning';
  return 'normal';
}

function formatShortDate(dateText: string): string {
  if (!dateText || dateText === '—') return '—';
  return dateText.length > 10 ? dateText.slice(0, 10) : dateText;
}

type TabKey = 'fleet' | 'alerts' | 'prediction';

const TAB_ITEMS: { key: TabKey; label: string; icon: string }[] = [
  { key: 'fleet', label: 'Vista de Flota', icon: '🚛' },
  { key: 'alerts', label: 'Registro de Alertas', icon: '📋' },
  { key: 'prediction', label: 'Detalle de Predicción', icon: '🔬' },
];

export default function TorreControlSioPage() {
  const apiBase = useMemo(() => pickApiBase(), []);
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [esLluvia, setEsLluvia] = useState(false);
  const [esFeriado, setEsFeriado] = useState(false);
  const [selectedPlaca, setSelectedPlaca] = useState<string>('');
  const [activeTab, setActiveTab] = useState<TabKey>('fleet');

  async function loadSnapshot() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiBase}/dashboard`, { cache: 'no-store' });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const payload = (await response.json()) as DashboardResponse;
      setData(payload);
      if (!selectedPlaca && payload.fleet.length > 0) {
        setSelectedPlaca(payload.fleet[0].placa);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo cargar el dashboard');
    } finally {
      setLoading(false);
    }
  }

  async function advanceTick() {
    setRefreshing(true);
    setError(null);
    try {
      const response = await fetch(`${apiBase}/tick?es_lluvia=${esLluvia}&es_feriado=${esFeriado}`, {
        method: 'POST',
        cache: 'no-store'
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const payload = (await response.json()) as DashboardResponse;
      setData(payload);
      if (!selectedPlaca && payload.fleet.length > 0) {
        setSelectedPlaca(payload.fleet[0].placa);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo avanzar el ciclo');
    } finally {
      setRefreshing(false);
    }
  }

  async function clearAlerts() {
    try {
      await fetch(`${apiBase}/alerts/clear`, { method: 'POST' });
      await loadSnapshot();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudieron limpiar las alertas');
    }
  }

  useEffect(() => {
    void loadSnapshot();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return undefined;
    const timer = window.setInterval(() => {
      void advanceTick();
    }, 30000);
    return () => window.clearInterval(timer);
  }, [autoRefresh, esLluvia, esFeriado]);

  const fleet = data?.fleet ?? [];
  const sortedFleet = fleet.slice().sort((left, right) => right.prob - left.prob);
  const selectedTruck = fleet.find((item) => item.placa === selectedPlaca) ?? sortedFleet[0] ?? null;
  const history = data?.history ?? [];
  const alerts = data?.alerts ?? [];
  const criticalAlerts = alerts.filter((item) => item.nivel === 'CRÍTICO');
  const fleetAlertSource = sortedFleet
    .filter((item) => item.prob >= 0.65)
    .map((item) => ({
      timestamp: data?.summary.last_update ?? '—',
      fecha: data?.summary.last_update ?? '—',
      placa: item.placa,
      conductor: item.conductor,
      ruta: item.ruta,
      prob_pct: Number((item.prob * 100).toFixed(1)),
      nivel: item.nivel,
      emoji: item.prob >= 0.8 ? '🔴' : '🟠',
      cluster: item.cluster,
      prescripcion: item.prescripcion,
    }));
  const fleetBanner = fleetAlertSource.length > 0 ? fleetAlertSource[0] : null;
  const fleetBannerTone = fleetBanner ? (fleetBanner.nivel === 'CRÍTICO' ? 'critical' : 'urgent') : 'normal';
  const fleetBannerPlates = fleetAlertSource.slice(0, 4).map((item) => item.placa).join(', ');
  const trendData = history.map((item) => ({
    ciclo: item.cycle,
    riesgo: item.avg_risk_pct,
    criticos: item.critical_count,
    alertas: item.alert_count,
  }));
  const historicalKpis = [
    { label: 'Viajes históricos', value: String(data?.summary.total_viajes ?? 0), subtext: 'Acumulado del modelo' },
    { label: 'Tasa siniestro', value: formatPct(data?.summary.tasa_siniestro_pct ?? 0), subtext: 'Promedio histórico' },
    { label: 'Pérdida promedio', value: formatBs(data?.summary.perdida_promedio_bs ?? 0), subtext: 'Costo por evento' },
  ];
  const cycleKpis = [
    { label: 'CAMIONES ACTIVOS', value: String(data?.summary.camiones_activos ?? 0), color: '#2B8AE2' },
    {
      label: 'EN RIESGO (≥65%)',
      value: String(data?.summary.camiones_en_riesgo ?? 0),
      color: (data?.summary.camiones_en_riesgo ?? 0) > 0 ? '#DA1E28' : '#2EA043',
    },
    {
      label: 'RIESGO PROMEDIO',
      value: formatPct(data?.summary.riesgo_promedio_pct ?? 0),
      color: riskColor((data?.summary.riesgo_promedio_pct ?? 0) / 100),
    },
    {
      label: 'ALERTAS TOTALES',
      value: String(data?.summary.alertas_totales ?? 0),
      color: (data?.summary.alertas_totales ?? 0) > 0 ? '#D29922' : '#8B949E',
    },
    {
      label: 'ALERTAS CRÍTICAS',
      value: String(data?.summary.alertas_criticas ?? 0),
      color: (data?.summary.alertas_criticas ?? 0) > 0 ? '#DA1E28' : '#8B949E',
    },
  ];
  const riskLegend = [
    { label: 'NORMAL', range: '< 40%', color: '#2EA043' },
    { label: 'ALERTA', range: '40 – 64%', color: '#D29922' },
    { label: 'URGENTE', range: '65 – 79%', color: '#E85D3F' },
    { label: 'CRÍTICO', range: '≥ 80%', color: '#DA1E28' },
  ];
  const journeyPhases = [
    { label: 'SALIENDO', description: 'Chequeo de salida en planta', icon: '⏳' },
    { label: 'EN RUTA', description: 'Transporte activo en carretera', icon: '🚛' },
    { label: 'DESTINO', description: 'Llegó — descargando carga', icon: '✅' },
  ];
  const cycleLabel = `#${String(data?.summary.cycle ?? 0).padStart(4, '0')}`;

  if (loading && !data) {
    return <main className="sio-page sio-loading">Cargando Torre de Control SIO...</main>;
  }

  return (
    <main className="sio-page">
      <section className="sio-hero">
        <div className="sio-hero-copy">
          <div className="sio-brand-bar">
            <span className="sio-brand-icon" aria-hidden="true">🧊</span>
            <div className="sio-brand-text">
              <h1 className="sio-brand-title">TORRE DE CONTROL SIO</h1>
            </div>
          </div>
          <p className="sio-brand-meta sio-brand-meta--hero">
            TransFreezer Bolivia S.R.L. <span>|</span> Sistema Inmunológico Operativo <span>|</span> Ciclo {cycleLabel} <span>|</span> Última actualización: {data?.summary.last_update ?? '—'}
          </p>
        </div>
        <div className="sio-actions">
          <label><input type="checkbox" checked={esLluvia} onChange={(event) => setEsLluvia(event.target.checked)} /> Lluvia</label>
          <label><input type="checkbox" checked={esFeriado} onChange={(event) => setEsFeriado(event.target.checked)} /> Feriado</label>
          <label><input type="checkbox" checked={autoRefresh} onChange={(event) => setAutoRefresh(event.target.checked)} /> Auto-refresh</label>
          <button onClick={() => void advanceTick()} disabled={refreshing}>{refreshing ? 'Actualizando...' : 'Actualizar ahora'}</button>
          <button className="secondary" onClick={() => void clearAlerts()}>Limpiar alertas</button>
        </div>
      </section>

      {error ? <div className="sio-banner sio-banner--error">{error}</div> : null}

      <div className="sio-workspace">
        <section className="sio-main-column">
          <section className="sio-cycle-strip">
            <div className="sio-kpis sio-kpis--cycle-row">
              {cycleKpis.map((kpi) => (
                <article key={kpi.label} className="sio-kpi sio-kpi--cycle" style={{ borderColor: `${kpi.color}55` }}>
                  <span style={{ color: kpi.color }}>{kpi.label}</span>
                  <strong style={{ color: kpi.color }}>{kpi.value}</strong>
                </article>
              ))}
            </div>
          </section>
          <nav className="sio-tabs" aria-label="Submódulos de torre de control">
            {TAB_ITEMS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                className={`sio-tab ${activeTab === tab.key ? 'sio-tab--active' : ''}`}
                onClick={() => setActiveTab(tab.key)}
              >
                <span>{tab.icon}</span>
                <strong>{tab.label}</strong>
              </button>
            ))}
          </nav>

          {activeTab === 'fleet' ? (
            <section className="sio-submodule">
              {fleetBanner ? (
                <div className={`fleet-alert-banner fleet-alert-banner--${fleetBannerTone}`}>
                  <strong>{fleetBanner.nivel === 'CRÍTICO' ? 'ALERTA CRÍTICA' : 'ALERTA URGENTE'}</strong>
                  <span>
                    {fleetBanner.nivel === 'CRÍTICO'
                      ? ` ${fleetAlertSource.length} camión(es) requieren intervención inmediata: ${fleetBannerPlates}`
                      : ` ${fleetAlertSource.length} camión(es) fuera de rango: ${fleetBannerPlates}`}
                  </span>
                </div>
              ) : null}

              <article className="sio-panel sio-panel--wide">
                <div className="panel-head">
                  <h2>Vista de Flota</h2>
                  <p>Selecciona un camión para revisar telemetría, estado del viaje y prescripción.</p>
                </div>
                <div className="fleet-grid">
                  {sortedFleet.map((item) => {
                    const isSelected = item.placa === selectedPlaca;
                    const tone = riskTone(item.prob);
                    const progress = Number(item.telemetry._progreso_ruta ?? item.metadata.progreso ?? 0);
                    return (
                      <button
                        key={item.placa}
                        className={`fleet-card ${isSelected ? 'fleet-card--selected' : ''}`}
                        onClick={() => setSelectedPlaca(item.placa)}
                        style={{ borderColor: `${riskColor(item.prob)}55` }}
                      >
                        <div className="fleet-card__header">
                          <div>
                            <strong>{item.placa}</strong>
                            <p>{item.conductor}</p>
                            <small>{item.ruta}</small>
                          </div>
                          <div className="fleet-card__score" style={{ color: riskColor(item.prob) }}>
                            <span>{formatPct(item.prob * 100)}</span>
                            <small className={`fleet-card__badge fleet-card__badge--${tone}`}>{item.nivel}</small>
                          </div>
                        </div>

                        <div className="fleet-card__status" style={{ borderColor: `${riskColor(item.prob)}55`, color: riskColor(item.prob) }}>
                          {item.telemetry._mensaje_estado ?? item.metadata.estado_viaje ?? 'Sin estado'}
                        </div>

                        <div className="risk-bar risk-bar--thick">
                          <span style={{ width: `${Math.min(item.prob * 100, 100)}%`, background: riskColor(item.prob) }} />
                        </div>

                        <div className="fleet-card__metrics">
                          <div>
                            <span>Temp.</span>
                            <strong>{Number(item.telemetry._temp_actual ?? 0).toFixed(1)}°C</strong>
                          </div>
                          <div>
                            <span>Δ térmica</span>
                            <strong>{Number(item.telemetry.AVG_VARIACION_TERMICA ?? 0).toFixed(1)}°C</strong>
                          </div>
                          <div>
                            <span>Puertas</span>
                            <strong>{String(item.telemetry.CONTEO_APERTURA_PUERTA ?? 0)}x</strong>
                          </div>
                          <div>
                            <span>Motor</span>
                            <strong>{String(item.telemetry.CONTEO_MOTOR_APAGADO ?? 0)}x</strong>
                          </div>
                        </div>

                        <div className="fleet-route">
                          <span>Origen</span>
                          <strong>{Math.round(progress * 100)}%</strong>
                          <span>Destino</span>
                        </div>

                        <div className="risk-bar">
                          <span style={{ width: `${Math.min(progress * 100, 100)}%`, background: '#2B8AE2' }} />
                        </div>

                        <p className="fleet-card__note">{item.prescripcion}</p>
                      </button>
                    );
                  })}
                </div>
              </article>

          <article className="sio-panel sio-panel--wide">
            <div className="panel-head">
              <h2>Riesgo promedio por ciclo</h2>
              <p>Histórico de la simulación y eventos acumulados.</p>
            </div>
            <div className="chart-box">
              <ResponsiveContainer width="100%" height={320}>
                <ComposedChart data={trendData} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                  <XAxis dataKey="ciclo" stroke="#AED6F1" />
                  <YAxis stroke="#AED6F1" unit="%" />
                  <Tooltip contentStyle={{ backgroundColor: '#10243a', border: '1px solid #2c5d87', borderRadius: 10 }} />
                  <Legend />
                  <Line type="monotone" dataKey="riesgo" stroke="#1B4F72" strokeWidth={2.5} dot={{ r: 3 }} name="Riesgo promedio %" />
                  <Line type="monotone" dataKey="criticos" stroke="#E85D3F" strokeWidth={2} dot={{ r: 2 }} name="Críticos" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="sio-panel">
            <div className="panel-head">
              <h2>Detalle rápido</h2>
              <p>{selectedTruck ? selectedTruck.ruta : 'Sin selección'}</p>
            </div>
            {selectedTruck ? (
              <div className="detail-box">
                <div className="detail-row"><span>Conductor</span><strong>{selectedTruck.conductor}</strong></div>
                <div className="detail-row"><span>Nivel</span><strong style={{ color: riskColor(selectedTruck.prob) }}>{selectedTruck.nivel}</strong></div>
                <div className="detail-row"><span>Temperatura</span><strong>{Number(selectedTruck.telemetry._temp_actual ?? 0).toFixed(1)}°C</strong></div>
                <div className="detail-row"><span>Humedad</span><strong>{Number(selectedTruck.telemetry.AVG_HUMEDAD_PCT ?? 0).toFixed(0)}%</strong></div>
                <div className="detail-row"><span>Prescripción</span><strong>{selectedTruck.prescripcion}</strong></div>
              </div>
            ) : (
              <p className="muted">No hay camión seleccionado.</p>
            )}
          </article>
            </section>
          ) : null}

          {activeTab === 'alerts' ? (
            <section className="sio-submodule sio-submodule--alerts">
              <article className="sio-panel sio-panel--wide">
            <div className="panel-head">
              <h2>Registro de Alertas</h2>
              <p>Historial persistente de eventos urgentes y críticos, ordenado por aparición.</p>
            </div>
            <div className="alerts-summary">
              <div className="alerts-summary__item">
                <span>Total</span>
                <strong>{alerts.length}</strong>
              </div>
              <div className="alerts-summary__item">
                <span>Críticas</span>
                <strong>{criticalAlerts.length}</strong>
              </div>
              <div className="alerts-summary__item">
                <span>Última actualización</span>
                <strong>{data?.summary.last_update ?? '—'}</strong>
              </div>
            </div>

            <div className="alerts-list">
              {alerts.length > 0 ? alerts.map((alert) => (
                <article key={`${alert.placa}-${alert.timestamp}`} className={`alert-row alert-row--${alert.nivel.toLowerCase()}`}>
                  <div className="alert-row__top">
                    <span className="alert-row__time">{alert.timestamp}</span>
                    <strong>{alert.emoji} {alert.placa}</strong>
                    <span className="alert-row__level" style={{ color: riskColor(alert.prob_pct / 100) }}>{alert.nivel}</span>
                    <span className="alert-row__risk">{formatPct(alert.prob_pct)}</span>
                  </div>
                  <div className="alert-row__meta">
                    <span>{alert.conductor}</span>
                    <span>{alert.ruta}</span>
                    <span>{formatShortDate(alert.fecha)}</span>
                    <span>{alert.emoji}</span>
                  </div>
                  <p>{alert.prescripcion}</p>
                </article>
              )) : <p className="muted">Sin alertas registradas en este ciclo.</p>}
            </div>
              </article>
            </section>
          ) : null}

          {activeTab === 'prediction' ? (
            <section className="sio-submodule sio-submodule--prediction">
              <article className="sio-panel sio-panel--wide">
            <div className="panel-head">
              <h2>Detalle de Predicción</h2>
              <p>Vista del camión seleccionado, con telemetría, explicación y vector de entrada del modelo.</p>
            </div>
            {selectedTruck ? (
              <div className="prediction-layout">
                <div className="prediction-card prediction-card--hero">
                  <div className="prediction-card__header">
                    <div>
                      <strong>{selectedTruck.placa}</strong>
                      <p>{selectedTruck.conductor} | {selectedTruck.ruta}</p>
                    </div>
                    <div className="prediction-score" style={{ color: riskColor(selectedTruck.prob) }}>
                      {formatPct(selectedTruck.prob * 100)}
                    </div>
                  </div>
                  <div className="prediction-card__notice">
                    <span>{selectedTruck.nivel}</span>
                    <p>{selectedTruck.prescripcion}</p>
                  </div>
                </div>

                <div className="prediction-grid">
                  <article className="prediction-card">
                    <h3>Telemetría clave</h3>
                    <div className="prediction-stats">
                      <div><span>Temp. interna</span><strong>{Number(selectedTruck.telemetry._temp_actual ?? 0).toFixed(1)}°C</strong></div>
                      <div><span>Var. térmica Avg</span><strong>{Number(selectedTruck.telemetry.AVG_VARIACION_TERMICA ?? 0).toFixed(2)}°C</strong></div>
                      <div><span>Var. térmica Max</span><strong>{Number(selectedTruck.telemetry.MAX_VARIACION_TERMICA ?? 0).toFixed(2)}°C</strong></div>
                      <div><span>Aperturas puerta</span><strong>{String(selectedTruck.telemetry.CONTEO_APERTURA_PUERTA ?? 0)}x</strong></div>
                      <div><span>Motor apagado</span><strong>{String(selectedTruck.telemetry.CONTEO_MOTOR_APAGADO ?? 0)}x</strong></div>
                      <div><span>Velocidad</span><strong>{Number(selectedTruck.telemetry.AVG_VELOCIDAD_KMH ?? 0).toFixed(0)} km/h</strong></div>
                      <div><span>Humedad interna</span><strong>{Number(selectedTruck.telemetry.AVG_HUMEDAD_PCT ?? 0).toFixed(0)}%</strong></div>
                      <div><span>Ocupación</span><strong>{Number(selectedTruck.telemetry.TASA_OCUPACION ?? 0).toFixed(0)}%</strong></div>
                      <div><span>Estado</span><strong>{String(selectedTruck.telemetry._estado_viaje ?? selectedTruck.metadata.estado_viaje ?? '—')}</strong></div>
                    </div>
                  </article>

                  <article className="prediction-card">
                    <h3>Vectores del modelo</h3>
                    <div className="feature-table">
                      {Object.entries(selectedTruck.telemetry)
                        .filter(([key]) => !key.startsWith('_'))
                        .slice(0, 10)
                        .map(([key, value]) => (
                          <div key={key} className="feature-row">
                            <span>{key}</span>
                            <strong>{typeof value === 'number' ? value.toFixed(3) : String(value)}</strong>
                          </div>
                        ))}
                    </div>
                  </article>
                </div>

                <article className="prediction-card">
                  <h3>Bundle y contexto</h3>
                  <div className="prediction-meta-grid">
                    <div><span>Bundle</span><strong>{data?.bundle.nombre ?? '—'}</strong></div>
                    <div><span>Modelo</span><strong>{data?.bundle.model_name ?? '—'}</strong></div>
                    <div><span>Features</span><strong>{data?.bundle.feature_count ?? 0}</strong></div>
                    <div><span>Último ciclo</span><strong>{data?.summary.cycle ?? 0}</strong></div>
                    <div><span>Actualizado</span><strong>{data?.summary.last_update ?? '—'}</strong></div>
                    <div><span>Alertas totales</span><strong>{data?.summary.alertas_totales ?? 0}</strong></div>
                  </div>
                </article>
              </div>
            ) : (
              <p className="muted">No hay camión seleccionado.</p>
            )}
              </article>
            </section>
          ) : null}
        </section>

        <aside className="sio-side-column">
          <article className="info-card info-card--sticky">
            <h2>KPIs históricos</h2>
            <p className="info-card__lead">Resumen del comportamiento acumulado del modelo.</p>
            <div className="history-kpis">
              {historicalKpis.map((item) => (
                <div key={item.label} className="history-kpi">
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                  <small>{item.subtext}</small>
                </div>
              ))}
            </div>
          </article>

          <article className="info-card info-card--sticky">
            <h2>Leyenda de riesgo</h2>
            <div className="legend-list">
              {riskLegend.map((item) => (
                <div key={item.label} className="legend-item">
                  <span className="legend-item__dot" style={{ background: item.color }} />
                  <strong>{item.label}</strong>
                  <span>{item.range}</span>
                </div>
              ))}
            </div>
          </article>

          <article className="info-card info-card--sticky">
            <h2>Fases del viaje</h2>
            <div className="phase-list">
              {journeyPhases.map((phase) => (
                <div key={phase.label} className="phase-item">
                  <strong>{phase.icon} {phase.label}</strong>
                  <span>{phase.description}</span>
                </div>
              ))}
            </div>
          </article>

          <article className="info-card info-card--sticky">
            <h2>Bundle ML</h2>
            <div className="bundle-metrics bundle-metrics--compact">
              <div><span>Modelo</span><strong>{data?.bundle.model_name ?? '—'}</strong></div>
              <div><span>Features</span><strong>{data?.bundle.feature_count ?? 0}</strong></div>
                <div><span>Variables auxiliares</span><strong>{data?.bundle.cluster_feature_count ?? 0}</strong></div>
              <div><span>Fecha</span><strong>{formatShortDate(data?.bundle.training_date ?? '—')}</strong></div>
            </div>
          </article>
        </aside>
      </div>
    </main>
  );
}