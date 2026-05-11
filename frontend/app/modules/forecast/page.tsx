'use client';

import { useEffect, useState } from 'react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell
} from 'recharts';
import PredictionChart from '@/components/PredictionChart';
import './dashboard.css';

interface KPI {
  label: string;
  value: string;
  subtext: string;
  color: string;
}

interface DashboardData {
  forecast: any;
  metricas: any;
  modelo: {
    estado_modelo: string;
    mae_bs: number;
    rmse_bs: number;
    mape_pct: number;
    aic: number;
    cumple_umbral: boolean;
    umbral_mape_pct: number;
    fecha_entrenamiento: string;
    version: string;
    modelo_nombre: string;
    tipo: string;
    orden?: string | null;
    nivel_confianza: number;
    periodo_entrenamiento: string;
    n_meses_entrenamiento: number;
    horizonte_forecast_meses: number;
  };
  validacion_predictiva: {
    mae_bs: number;
    rmse_bs: number;
    mape_pct: number;
    cobertura_ic_pct: number;
    puntos: {
      periodo: string;
      real_bs: number;
      predicho_bs: number;
      error_bs: number;
      error_pct: number;
      dentro_ic: boolean;
    }[];
  };
  trazabilidad: {
    horizonte_activo_meses: number;
    periodo_entrenado: string;
    ultimo_refresco: string;
    modelo_nombre: string;
    tipo: string;
    version: string;
  };
  stats_historicos: any;
  serie_historica: any;
  analisis_ruta: any[];
  analisis_cliente: any[];
  reglas_prescriptivas: Record<string, string>;
  umbrales: Record<string, any>;
  palancas_prescriptivas: {
    descripcion: string;
    impacto_estimado_bs_anual: number;
    impacto_resumen: string;
  }[];
}

const COLORS = ['#1B4F72', '#2980B9', '#1E8449', '#D4AC0D', '#C0392B'];
const CHART_RESIZE_DEBOUNCE_MS = 160;

export default function ForecastDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [horizon, setHorizon] = useState(6);

  useEffect(() => {
    const fetchDashboard = async () => {
      setLoading(true);
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/v1/forecast-operativo/dashboard?horizon=${horizon}`);
        if (!res.ok) throw new Error('Error cargando dashboard');
        const json = await res.json();
        setData(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error desconocido');
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, [horizon]);

  if (loading) return <div className="dashboard loading">Cargando dashboard...</div>;
  if (error) return <div className="dashboard error">Error: {error}</div>;
  if (!data) return <div className="dashboard error">Sin datos disponibles</div>;

  const kpis: KPI[] = [
    {
      label: 'Media histórica',
      value: `${(data.stats_historicos.media_margen_bs / 1000).toFixed(1)}K`,
      subtext: 'Bs/mes',
      color: '#1B4F72'
    },
    {
      label: 'MAPE del modelo',
      value: `${data.metricas.mape_pct.toFixed(1)}%`,
      subtext: `${data.metricas.cumple_umbral ? '✓ Aceptable' : 'Normal'}`,
      color: data.metricas.cumple_umbral ? '#1E8449' : '#D4AC0D'
    },
    {
      label: 'CV histórico',
      value: `${data.stats_historicos.cv_pct.toFixed(1)}%`,
      subtext: 'Volatilidad',
      color: '#2980B9'
    },
    {
      label: 'Total ingresos',
      value: `${(data.stats_historicos.ingreso_total_bs / 1000000).toFixed(1)}M`,
      subtext: 'Bs (15 meses)',
      color: '#1E8449'
    }
  ];

  const validationData = data.validacion_predictiva.puntos.map((item) => ({
    periodo: item.periodo,
    real: item.real_bs,
    predicho: item.predicho_bs,
    error: item.error_bs,
    dentro_ic: item.dentro_ic,
  }));

  const impactCards = data.palancas_prescriptivas;

  // Preparar datos para gráfico de serie histórica
  const serieData = data.serie_historica.meses.map((mes: string, idx: number) => ({
    mes,
    margen: data.serie_historica.margen_neto_bs[idx],
    ingreso: data.serie_historica.ingreso_bs[idx]
  }));

  // Preparar datos para gráfico de forecast
  const forecastData = data.forecast.items.map((item: any) => ({
    mes: item.month,
    proyectado: item.projected_income_bob,
    inferior: item.lower_bound_bob,
    superior: item.upper_bound_bob,
    accion: item.suggested_action
  }));

  // Preparar datos para análisis por ruta (top 8)
  const rutasData = data.analisis_ruta
    .sort((a: any, b: any) => b.margen_neto_bs - a.margen_neto_bs)
    .slice(0, 8)
    .map((r: any) => ({
      ruta: r.ruta.substring(0, 20),
      margen: r.margen_neto_bs,
      pct_margen: r.pct_margen
    }));

  // Análisis por cliente (top 5)
  const clientesTop = data.analisis_cliente
    .sort((a: any, b: any) => b.margen_neto_bs - a.margen_neto_bs)
    .slice(0, 5);

  // Mapear nivel demanda a color
  const getNivelColor = (nivel: string) => {
    switch(nivel) {
      case 'ALTO': return '#1E8449';
      case 'MEDIO': return '#D4AC0D';
      case 'BAJO': return '#C0392B';
      default: return '#7F8C8D';
    }
  };

  const mapAccionToNivel = (accion: string): string => {
    if (accion.includes('extra') || accion.includes('Provisionar')) return 'ALTO';
    if (accion.includes('Buscar') || accion.includes('proactivo')) return 'BAJO';
    return 'MEDIO';
  };

  return (
    <main className="dashboard">
      <header className="dashboard-header">
        <div>
          <h1>Margen de Contratos</h1>
          <p>Sistema de pronóstico predictivo de margen neto | Transfreezer</p>
        </div>
        <div className="horizon-control">
          <label htmlFor="horizonMonths">Horizonte de predicción</label>
          <div className="horizon-input-row">
            <input
              id="horizonMonths"
              type="range"
              min={0}
              max={6}
              step={1}
              value={horizon}
              onChange={(e) => setHorizon(Number(e.target.value))}
            />
            <span>{horizon} mes{horizon === 1 ? '' : 'es'}</span>
          </div>
        </div>
      </header>

      {/* KPIs */}
      <section className="kpi-section">
        {kpis.map((kpi, idx) => (
          <article key={idx} className="kpi-card">
            <div className="kpi-indicator" style={{ backgroundColor: kpi.color }}></div>
            <div className="kpi-content">
              <p className="kpi-label">{kpi.label}</p>
              <p className="kpi-value">{kpi.value}</p>
              <p className="kpi-subtext">{kpi.subtext}</p>
            </div>
          </article>
        ))}
      </section>

      {/* Gráfico predictivo principal (como notebook) */}
      <section id="forecast" className="chart-section prediction-section">
        <h2>Pronóstico de Margen Neto: Serie Histórica + {horizon} Meses (IC 90%)</h2>
        <PredictionChart serie={data.serie_historica} forecast={data.forecast} />
      </section>

      {/* Diagnóstico del modelo */}
      <section className="chart-section">
        <h2>Diagnóstico del Modelo</h2>
        <div className="info-grid">
          <article>
            <span className="label">Estado</span>
            <span className="value">{data.modelo.estado_modelo}</span>
          </article>
          <article>
            <span className="label">MAPE</span>
            <span className="value">{data.modelo.mape_pct.toFixed(1)}%</span>
          </article>
          <article>
            <span className="label">MAE</span>
            <span className="value">{(data.modelo.mae_bs / 1000).toFixed(1)}K Bs</span>
          </article>
          <article>
            <span className="label">RMSE</span>
            <span className="value">{(data.modelo.rmse_bs / 1000).toFixed(1)}K Bs</span>
          </article>
          <article>
            <span className="label">AIC</span>
            <span className="value">{data.modelo.aic.toFixed(2)}</span>
          </article>
          <article>
            <span className="label">Umbral MAPE</span>
            <span className="value">{data.modelo.umbral_mape_pct.toFixed(1)}%</span>
          </article>
          <article>
            <span className="label">Fecha entrenamiento</span>
            <span className="value">{data.modelo.fecha_entrenamiento.slice(0, 19).replace('T', ' ')}</span>
          </article>
          <article>
            <span className="label">Versión</span>
            <span className="value">{data.modelo.version}</span>
          </article>
        </div>
      </section>

      {/* Trazabilidad ejecutiva */}
      <section className="chart-section">
        <h2>Trazabilidad Ejecutiva</h2>
        <div className="info-grid">
          <article>
            <span className="label">Horizonte activo</span>
            <span className="value">{data.trazabilidad.horizonte_activo_meses} meses</span>
          </article>
          <article>
            <span className="label">Periodo entrenado</span>
            <span className="value">{data.trazabilidad.periodo_entrenado}</span>
          </article>
          <article>
            <span className="label">Último refresco</span>
            <span className="value">{data.trazabilidad.ultimo_refresco.slice(0, 19).replace('T', ' ')}</span>
          </article>
          <article>
            <span className="label">Modelo</span>
            <span className="value">{data.trazabilidad.modelo_nombre}</span>
          </article>
          <article>
            <span className="label">Tipo</span>
            <span className="value">{data.trazabilidad.tipo}</span>
          </article>
          <article>
            <span className="label">Versión</span>
            <span className="value">{data.trazabilidad.version}</span>
          </article>
        </div>
      </section>

      {/* Serie histórica */}
      <section className="chart-section">
        <h2>Serie Histórica de Margen Neto</h2>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={300} debounce={CHART_RESIZE_DEBOUNCE_MS}>
            <LineChart data={serieData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="mes" stroke="#AED6F1" />
              <YAxis stroke="#AED6F1" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1B4F72', border: '1px solid #2980B9' }}
                labelStyle={{ color: '#fff' }}
                formatter={(value: any) => `${(Number(value ?? 0) / 1000).toFixed(1)}K Bs`}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="margen"
                stroke="#1E8449"
                strokeWidth={2}
                dot={{ fill: '#1E8449', r: 4 }}
                activeDot={{ r: 6 }}
                name="Margen Neto"
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* Forecast con intervalos de confianza */}
      <section className="chart-section">
        <h2>Pronóstico {horizon} Meses con Intervalos de Confianza (90%)</h2>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={350} debounce={CHART_RESIZE_DEBOUNCE_MS}>
            <AreaChart data={forecastData}>
              <defs>
                <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2980B9" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#2980B9" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="mes" stroke="#AED6F1" />
              <YAxis stroke="#AED6F1" />
              <Tooltip
                contentStyle={{ backgroundColor: '#1B4F72', border: '1px solid #2980B9' }}
                labelStyle={{ color: '#fff' }}
                formatter={(value: any) => `${(Number(value ?? 0) / 1000).toFixed(1)}K Bs`}
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="custom-tooltip">
                        <p className="label">{data.mes}</p>
                        <p style={{ color: '#2980B9' }}>Proyectado: {(data.proyectado / 1000).toFixed(1)}K Bs</p>
                        <p style={{ color: '#7F8C8D' }}>Rango: {(data.inferior / 1000).toFixed(1)}K – {(data.superior / 1000).toFixed(1)}K</p>
                        <p style={{ color: '#D4AC0D' }}>Acción: {data.accion}</p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Area
                type="monotone"
                dataKey="proyectado"
                stroke="#2980B9"
                fillOpacity={1}
                fill="url(#colorForecast)"
                strokeWidth={2}
                name="Pronóstico"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="forecast-table">
          <table>
            <thead>
              <tr>
                <th>Mes</th>
                <th>Margen Proyectado</th>
                <th>IC Inferior</th>
                <th>IC Superior</th>
                <th>Acción Recomendada</th>
              </tr>
            </thead>
            <tbody>
              {forecastData.length === 0 ? (
                <tr>
                  <td colSpan={5}>Sin meses seleccionados para pronóstico.</td>
                </tr>
              ) : forecastData.map((row: any, idx: number) => {
                const nivel = mapAccionToNivel(row.accion);
                return (
                  <tr key={idx} style={{ borderLeftColor: getNivelColor(nivel), borderLeftWidth: '4px' }}>
                    <td>{row.mes}</td>
                    <td><strong>{(row.proyectado / 1000).toFixed(1)}K</strong></td>
                    <td>{(row.inferior / 1000).toFixed(1)}K</td>
                    <td>{(row.superior / 1000).toFixed(1)}K</td>
                    <td>
                      <span className={`action-badge action-${nivel.toLowerCase()}`}>
                        {row.accion}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Análisis por ruta */}
      <section id="rutas" className="chart-section">
        <h2>Margen Neto por Ruta (Top 8)</h2>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={300} debounce={CHART_RESIZE_DEBOUNCE_MS}>
            <BarChart data={rutasData} layout="vertical" margin={{ top: 5, right: 30, left: 200, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis type="number" stroke="#AED6F1" />
              <YAxis dataKey="ruta" type="category" stroke="#AED6F1" width={190} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1B4F72', border: '1px solid #2980B9' }}
                labelStyle={{ color: '#fff' }}
                formatter={(value: any) => `${(Number(value ?? 0) / 1000).toFixed(1)}K Bs`}
              />
              <Bar dataKey="margen" fill="#1B4F72" radius={[0, 8, 8, 0]} isAnimationActive={false}>
                {rutasData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* Análisis por cliente (top 5) */}
      <section id="clientes" className="chart-section">
        <h2>Clientes con Mayor Margen (Top 5)</h2>
        <div className="clientes-table">
          <table>
            <thead>
              <tr>
                <th>Cliente</th>
                <th>Margen Total</th>
                <th>Contratos</th>
                <th>Margen/Contrato</th>
                <th>Penalizaciones</th>
              </tr>
            </thead>
            <tbody>
              {clientesTop.map((c: any, idx: number) => (
                <tr key={idx}>
                  <td><strong>{c.cliente.substring(0, 30)}</strong></td>
                  <td>{(c.margen_neto_bs / 1000).toFixed(1)}K Bs</td>
                  <td>{c.num_contratos}</td>
                  <td>{(c.margen_por_contrato / 1000).toFixed(1)}K Bs</td>
                  <td style={{ color: c.penalizacion_bs > 10000 ? '#C0392B' : '#1E8449' }}>
                    {(c.penalizacion_bs / 1000).toFixed(1)}K Bs
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Recomendaciones prescriptivas */}
      <section className="chart-section prescriptive">
        <h2>Recomendaciones Prescriptivas (Por Nivel de Demanda)</h2>
        <div className="prescriptive-grid">
          <article className="prescriptive-card prescriptive-alto">
            <h3>Demanda ALTA (≥150K Bs)</h3>
            <p>{data.reglas_prescriptivas.ALTO || 'Provisionar flota completa'}</p>
          </article>
          <article className="prescriptive-card prescriptive-medio">
            <h3>Demanda MEDIA (100–150K Bs)</h3>
            <p>{data.reglas_prescriptivas.MEDIO || 'Mantener operación estándar'}</p>
          </article>
          <article className="prescriptive-card prescriptive-bajo">
            <h3>Demanda BAJA (&lt;100K Bs)</h3>
            <p>{data.reglas_prescriptivas.BAJO || 'Activar campaña comercial'}</p>
          </article>
        </div>
      </section>

      <section className="chart-section">
        <h2>Impacto de Palancas Prescriptivas</h2>
        <div className="prescriptive-grid">
          {impactCards.map((item) => (
            <article key={item.descripcion} className="prescriptive-card">
              <h3>{item.descripcion}</h3>
              <p><strong>{item.impacto_resumen}</strong></p>
              <p>Impacto estimado: {(item.impacto_estimado_bs_anual / 1000).toFixed(0)}K Bs/año</p>
            </article>
          ))}
        </div>
      </section>

      {/* Validación predictiva */}
      <section className="chart-section">
        <h2>Validación Predictiva: Real vs Predicho</h2>
        <div className="kpi-section validation-summary">
          <article className="kpi-card">
            <div className="kpi-indicator" style={{ backgroundColor: '#1B4F72' }}></div>
            <div className="kpi-content">
              <p className="kpi-label">MAPE validación</p>
              <p className="kpi-value">{data.validacion_predictiva.mape_pct.toFixed(1)}%</p>
              <p className="kpi-subtext">Serie histórica validada</p>
            </div>
          </article>
          <article className="kpi-card">
            <div className="kpi-indicator" style={{ backgroundColor: '#1E8449' }}></div>
            <div className="kpi-content">
              <p className="kpi-label">Cobertura IC</p>
              <p className="kpi-value">{data.validacion_predictiva.cobertura_ic_pct.toFixed(1)}%</p>
              <p className="kpi-subtext">Intervalo de confianza</p>
            </div>
          </article>
          <article className="kpi-card">
            <div className="kpi-indicator" style={{ backgroundColor: '#D4AC0D' }}></div>
            <div className="kpi-content">
              <p className="kpi-label">MAE validación</p>
              <p className="kpi-value">{(data.validacion_predictiva.mae_bs / 1000).toFixed(1)}K</p>
              <p className="kpi-subtext">Error medio absoluto</p>
            </div>
          </article>
        </div>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={320} debounce={CHART_RESIZE_DEBOUNCE_MS}>
            <LineChart data={validationData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="periodo" stroke="#AED6F1" />
              <YAxis stroke="#AED6F1" />
              <Tooltip
                contentStyle={{ backgroundColor: '#1B4F72', border: '1px solid #2980B9' }}
                labelStyle={{ color: '#fff' }}
                formatter={(value: any) => `${(Number(value ?? 0) / 1000).toFixed(1)}K Bs`}
              />
              <Legend />
              <Line type="monotone" dataKey="real" stroke="#1E8449" strokeWidth={2} dot={{ r: 3 }} name="Real" isAnimationActive={false} />
              <Line type="monotone" dataKey="predicho" stroke="#C0392B" strokeWidth={2} strokeDasharray="6 4" dot={{ r: 3 }} name="Predicho" isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="chart-section">
        <h2>Backtesting Visible</h2>
        <div className="forecast-table">
          <table>
            <thead>
              <tr>
                <th>Periodo</th>
                <th>Real</th>
                <th>Predicho</th>
                <th>Error</th>
                <th>% Error</th>
                <th>IC</th>
              </tr>
            </thead>
            <tbody>
              {data.validacion_predictiva.puntos.slice(-6).map((row) => (
                <tr key={row.periodo}>
                  <td>{row.periodo}</td>
                  <td>{(row.real_bs / 1000).toFixed(1)}K</td>
                  <td>{(row.predicho_bs / 1000).toFixed(1)}K</td>
                  <td>{(row.error_bs / 1000).toFixed(1)}K</td>
                  <td>{row.error_pct.toFixed(1)}%</td>
                  <td>{row.dentro_ic ? 'Dentro' : 'Fuera'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Información de modelo */}
      <section className="model-info">
        <h2>Información del Modelo</h2>
        <div className="info-grid">
          <article>
            <span className="label">Tipo de modelo</span>
            <span className="value">{data.modelo.modelo_nombre}</span>
          </article>
          <article>
            <span className="label">MAE (error promedio)</span>
            <span className="value">{(data.modelo.mae_bs / 1000).toFixed(1)}K Bs</span>
          </article>
          <article>
            <span className="label">RMSE (raíz error cuad.)</span>
            <span className="value">{(data.modelo.rmse_bs / 1000).toFixed(1)}K Bs</span>
          </article>
          <article>
            <span className="label">AIC (criterio info)</span>
            <span className="value">{data.modelo.aic.toFixed(2)}</span>
          </article>
          <article>
            <span className="label">Cobertura IC</span>
            <span className="value">{data.validacion_predictiva.cobertura_ic_pct.toFixed(1)}%</span>
          </article>
          <article>
            <span className="label">Periodo entrenado</span>
            <span className="value">{data.trazabilidad.periodo_entrenado}</span>
          </article>
          <article>
            <span className="label">Último refresco</span>
            <span className="value">{data.trazabilidad.ultimo_refresco.slice(0, 19).replace('T', ' ')}</span>
          </article>
        </div>
      </section>
    </main>
  );
}
