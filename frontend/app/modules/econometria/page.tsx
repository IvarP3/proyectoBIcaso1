'use client';

import { FormEvent, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  LabelList,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { BlockMath } from 'react-katex';
import './page.css';

type TabKey = 'resumen' | 'descriptiva' | 'modelos' | 'simulacion';
type NivelSla = 'ESTÁNDAR' | 'ESTANDAR' | 'ORO' | 'PLATINO';

type PredictionInput = {
  peso_kg: number;
  distancia_km: number;
  altitud_msnm: number;
  penalizacion_bs: number;
  siniestros_bs: number;
  nivel_sla: NivelSla;
  es_division_farma: boolean;
  puntaje_chofer: number;
};

type FormValues = {
  peso_kg: string;
  distancia_km: string;
  altitud_msnm: string;
  penalizacion_bs: string;
  siniestros_bs: string;
  nivel_sla: NivelSla;
  es_division_farma: boolean;
  puntaje_chofer: string;
};

type NumericFieldKey =
  | 'peso_kg'
  | 'distancia_km'
  | 'altitud_msnm'
  | 'penalizacion_bs'
  | 'siniestros_bs'
  | 'puntaje_chofer';

type PredictionOutput = {
  margen_predicho_bs: number;
  intervalo_confianza_95: [number, number] | number[];
  nivel_sla: string;
  division: string;
  alertas: string[];
  rentable: boolean;
};

type SimulationOutput = {
  margen_base_bs: number;
  margen_simulado_bs: number;
  diferencia_absoluta_bs: number;
  diferencia_porcentual: number;
  interpretacion_cambio: string;
  alertas_operativas: string[];
  rentable_ajustado: boolean;
};

type ExamplePreset = {
  key: string;
  name: string;
  values: PredictionInput;
};

type ExecutiveSummary = {
  contratos_analizados: number;
  pct_contratos_rentables: number;
  contratos_con_perdida: number;
  margen_promedio_bs: number;
  margen_mediana_bs: number;
  margen_min_bs: number;
  margen_max_bs: number;
  periodo_analizado: string;
  modelo_principal_activo: string;
  origen_datos: string[];
  advertencias_metodologicas: string[];
  snowflake_disponible: boolean;
  bundle_disponible: boolean;
  r2_modelo_ols: number;
  f_stat_modelo_ols: number;
};

type DescriptiveResponse = {
  snowflake_disponible: boolean;
  warning: string | null;
  margin_distribution: { bucket: string; count: number }[];
  margin_by_division: { nombre: string; margen_promedio_bs: number; contratos: number }[];
  margin_by_sla: { nombre: string; margen_promedio_bs: number; contratos: number }[];
  financial_structure: { etapa: string; monto_bs: number }[];
  scatter_distance_vs_margin: { x: number; y: number }[];
  scatter_weight_vs_margin: { x: number; y: number }[];
  correlations: { variable: string; r: number }[];
  quarterly_trend: { periodo: string; margen_promedio_bs: number; contratos: number }[];
  ranking_clientes: { nombre: string; margen_promedio_bs: number; contratos: number; categoria?: string | null; valor_extra?: number | null }[];
  ranking_rutas: { nombre: string; margen_promedio_bs: number; contratos: number; categoria?: string | null; valor_extra?: number | null }[];
};

type ModelsResponse = {
  ols: {
    formula: string;
    variable_dependiente: string;
    variables_independientes: string[];
    coeficientes: {
      variable: string;
      beta: number;
      std_err: number;
      t_stat: number;
      p_value: number;
      ci_95_lo: number;
      ci_95_hi: number;
      significativo_5pct: boolean;
    }[];
    coeficientes_estandarizados: {
      variable: string;
      beta: number;
      std_err: number;
      t_stat: number;
      p_value: number;
      ci_95_lo: number;
      ci_95_hi: number;
      significativo_5pct: boolean;
    }[];
    ajuste_observado_predicho: { x: number; y: number }[];
    r2: number;
    r2_ajustado: number;
    f_statistic: number;
    n_observaciones: number;
    diagnostico: Record<string, number>;
    interpretacion_ejecutiva: string[];
  };
  loglog: {
    disponible: boolean;
    offset_aplicado: string;
    transformacion: string;
    variables: { variable: string; beta: number; p_value: number; significativo_5pct: boolean }[];
    interpretacion_porcentual: string[];
    limitaciones: string[];
  };
  comparativa: {
    modelo_operativo_principal: string;
    motivo: string;
    metricas: Record<string, number | boolean>;
    utilidad_practica: string[];
  };
};

type DescriptiveFilters = {
  division_operativa: string;
  nivel_sla: string;
  anio: string;
  trimestre: string;
  con_penalizacion: string;
  con_siniestros: string;
};

const API_BASE_CANDIDATES = [
  process.env.NEXT_PUBLIC_API_BASE_URL,
  'http://localhost:8000/api/v1/econometria',
  'http://127.0.0.1:8000/api/v1/econometria',
  '/api/v1/econometria',
].filter((value): value is string => Boolean(value));
const TAB_ITEMS: { key: TabKey; label: string }[] = [
  { key: 'resumen', label: '1. Resumen ejecutivo' },
  { key: 'descriptiva', label: '2. Analítica descriptiva' },
  { key: 'modelos', label: '3. Modelos econométricos' },
  { key: 'simulacion', label: '4. Operativo (Predicción + Simulación)' },
];

const EXAMPLES: ExamplePreset[] = [
  {
    key: 'ejemplo-1',
    name: 'Contrato Farma · SCZ-La Paz · Platino',
    values: {
      peso_kg: 50,
      distancia_km: 860,
      altitud_msnm: 4200,
      penalizacion_bs: 0,
      siniestros_bs: 0,
      nivel_sla: 'PLATINO',
      es_division_farma: true,
      puntaje_chofer: 8.5,
    },
  },
  {
    key: 'ejemplo-2',
    name: 'Contrato Cárnico · SCZ-Cobija · Estándar (con penalización)',
    values: {
      peso_kg: 5000,
      distancia_km: 1300,
      altitud_msnm: 250,
      penalizacion_bs: 800,
      siniestros_bs: 200,
      nivel_sla: 'ESTÁNDAR',
      es_division_farma: false,
      puntaje_chofer: 6.9,
    },
  },
  {
    key: 'ejemplo-3',
    name: 'Contrato Alimentos · SCZ-Cbba · Estándar',
    values: {
      peso_kg: 2500,
      distancia_km: 480,
      altitud_msnm: 3500,
      penalizacion_bs: 0,
      siniestros_bs: 0,
      nivel_sla: 'ESTÁNDAR',
      es_division_farma: false,
      puntaje_chofer: 7.8,
    },
  },
];

function formatBs(value: number): string {
  return `Bs ${value.toLocaleString('es-BO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatBsAxis(value: number): string {
  const absValue = Math.abs(value);
  if (absValue >= 1_000_000) {
    return `Bs ${(value / 1_000_000).toFixed(1)}M`;
  }
  if (absValue >= 1_000) {
    return `Bs ${(value / 1_000).toFixed(1)}k`;
  }
  return `Bs ${value.toFixed(0)}`;
}

function formatModelVariable(variable: string): string {
  const labels: Record<string, string> = {
    PESO_TRANSPORTADO_KG: 'Peso transportado',
    DISTANCIA_NOMINAL_KM: 'Distancia nominal',
    ALTITUD_MAXIMA_MSNM: 'Altitud máxima',
    MONTO_PENALIZACION_BS: 'Penalización SLA',
    TOTAL_SINIESTROS_BS: 'Siniestros',
    sla_n: 'Nivel SLA',
    es_farma: 'División Fármacos',
    PUNTAJE_EFICIENCIA_TERMICA: 'Eficiencia térmica',
    const: 'Intercepto',
    ln_peso: 'ln(Peso + 1)',
    ln_distancia: 'ln(Distancia + 1)',
    ln_altitud: 'ln(Altitud + 1)',
    ln_penalizacion: 'ln(Penalización + 1)',
    ln_siniestros: 'ln(Siniestros + 1)',
  };

  return labels[variable] ?? variable.replaceAll('_', ' ');
}

function toFormValues(values: PredictionInput): FormValues {
  return {
    peso_kg: String(values.peso_kg),
    distancia_km: String(values.distancia_km),
    altitud_msnm: String(values.altitud_msnm),
    penalizacion_bs: String(values.penalizacion_bs),
    siniestros_bs: String(values.siniestros_bs),
    nivel_sla: values.nivel_sla,
    es_division_farma: values.es_division_farma,
    puntaje_chofer: String(values.puntaje_chofer),
  };
}

function toPredictionInput(values: FormValues): PredictionInput {
  const parse = (raw: string): number => {
    if (raw.trim() === '') {
      return 0;
    }
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : 0;
  };

  return {
    peso_kg: parse(values.peso_kg),
    distancia_km: parse(values.distancia_km),
    altitud_msnm: parse(values.altitud_msnm),
    penalizacion_bs: parse(values.penalizacion_bs),
    siniestros_bs: parse(values.siniestros_bs),
    nivel_sla: values.nivel_sla,
    es_division_farma: values.es_division_farma,
    puntaje_chofer: parse(values.puntaje_chofer),
  };
}

async function fetchJsonWithFallback(path: string, options?: RequestInit) {
  let lastError: unknown = null;

  for (const baseUrl of API_BASE_CANDIDATES) {
    try {
      const response = await fetch(`${baseUrl}${path}`, options);
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data?.detail ?? `HTTP ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError instanceof Error ? lastError : new Error('No se pudo conectar con el backend.');
}

export default function EconometriaPage() {
  const [activeTab, setActiveTab] = useState<TabKey>('simulacion');
  const [summary, setSummary] = useState<ExecutiveSummary | null>(null);
  const [descriptive, setDescriptive] = useState<DescriptiveResponse | null>(null);
  const [models, setModels] = useState<ModelsResponse | null>(null);
  const [loadingSection, setLoadingSection] = useState(false);
  const [sectionError, setSectionError] = useState<string | null>(null);

  const [filters, setFilters] = useState<DescriptiveFilters>({
    division_operativa: '',
    nivel_sla: '',
    anio: '',
    trimestre: '',
    con_penalizacion: '',
    con_siniestros: '',
  });

  const [selectedExample, setSelectedExample] = useState<string>(EXAMPLES[0].key);
  const [form, setForm] = useState<FormValues>(toFormValues(EXAMPLES[0].values));
  const [baseScenario, setBaseScenario] = useState<FormValues>(toFormValues(EXAMPLES[0].values));
  const [prediction, setPrediction] = useState<PredictionOutput | null>(null);
  const [simulation, setSimulation] = useState<SimulationOutput | null>(null);
  const [predictLoading, setPredictLoading] = useState(false);
  const [simulateLoading, setSimulateLoading] = useState(false);
  const [predictionError, setPredictionError] = useState<string | null>(null);
  const [simulationError, setSimulationError] = useState<string | null>(null);

  const activeExampleName = useMemo(
    () => EXAMPLES.find((item) => item.key === selectedExample)?.name ?? 'Caso personalizado',
    [selectedExample],
  );

  const descriptiveClientRanking = useMemo(
    () => (descriptive?.ranking_clientes ?? []).filter((item) => item.nombre),
    [descriptive],
  );
  const descriptiveRouteRanking = useMemo(
    () => (descriptive?.ranking_rutas ?? []).filter((item) => item.nombre),
    [descriptive],
  );
  const clientRankingAverage = useMemo(
    () => (descriptiveClientRanking.length > 0 ? descriptiveClientRanking.reduce((sum, item) => sum + item.margen_promedio_bs, 0) / descriptiveClientRanking.length : 0),
    [descriptiveClientRanking],
  );
  const routeRankingAverage = useMemo(
    () => (descriptiveRouteRanking.length > 0 ? descriptiveRouteRanking.reduce((sum, item) => sum + item.margen_promedio_bs, 0) / descriptiveRouteRanking.length : 0),
    [descriptiveRouteRanking],
  );
  const modelCoefficients = useMemo(
    () => (models?.ols.coeficientes ?? []).filter((item) => item.variable !== 'const'),
    [models],
  );
  const modelStandardizedCoefficients = useMemo(
    () => (models?.ols.coeficientes_estandarizados ?? []).filter((item) => item.variable !== 'const'),
    [models],
  );
  const observedPredictedPoints = models?.ols.ajuste_observado_predicho ?? [];
  const observedPredictedExtent = useMemo(() => {
    if (observedPredictedPoints.length === 0) return { min: 0, max: 0 };
    const values = observedPredictedPoints.flatMap((point) => [point.x, point.y]);
    return { min: Math.min(...values), max: Math.max(...values) };
  }, [observedPredictedPoints]);

  const loadTabData = async (tab: TabKey, forceReload: boolean = false) => {
    setActiveTab(tab);
    if (!forceReload) {
      if (tab === 'resumen' && summary) return;
      if (tab === 'descriptiva' && descriptive) return;
      if (tab === 'modelos' && models) {
        const hasStandardized = (models.ols.coeficientes_estandarizados?.length ?? 0) > 0;
        const hasObservedPredicted = (models.ols.ajuste_observado_predicho?.length ?? 0) > 0;
        if (hasStandardized && hasObservedPredicted) return;
      }
    }

    setLoadingSection(true);
    setSectionError(null);
    try {
      if (tab === 'resumen') {
        setSummary(await fetchJsonWithFallback('/resumen-ejecutivo'));
      }
      if (tab === 'descriptiva') {
        const params = new URLSearchParams();
        if (filters.division_operativa) params.set('division_operativa', filters.division_operativa);
        if (filters.nivel_sla) params.set('nivel_sla', filters.nivel_sla);
        if (filters.anio) params.set('anio', filters.anio);
        if (filters.trimestre) params.set('trimestre', filters.trimestre);
        if (filters.con_penalizacion) params.set('con_penalizacion', filters.con_penalizacion);
        if (filters.con_siniestros) params.set('con_siniestros', filters.con_siniestros);
        setDescriptive(await fetchJsonWithFallback(`/analitica-descriptiva?${params.toString()}`));
      }
      if (tab === 'modelos') {
        setModels(await fetchJsonWithFallback('/modelos-econometricos'));
      }
    } catch (err) {
      setSectionError(err instanceof Error ? err.message : 'Error inesperado al cargar sección.');
    } finally {
      setLoadingSection(false);
    }
  };

  const reloadDescriptive = async () => {
    setDescriptive(null);
    await loadTabData('descriptiva', true);
  };

  const handleLoadExample = () => {
    const preset = EXAMPLES.find((item) => item.key === selectedExample);
    if (!preset) return;
    setForm(toFormValues(preset.values));
    setBaseScenario(toFormValues(preset.values));
    setPrediction(null);
    setSimulation(null);
    setPredictionError(null);
    setSimulationError(null);
  };

  const handleNumber = (key: NumericFieldKey, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const submitPrediction = async (event: FormEvent) => {
    event.preventDefault();
    setPredictLoading(true);
    setPredictionError(null);
    try {
      const predictionResponse = await fetchJsonWithFallback('/prediccion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(toPredictionInput(form)),
      });
      setPrediction(predictionResponse);
    } catch (err) {
      setPredictionError(err instanceof Error ? err.message : 'Error inesperado en predicción.');
      setPrediction(null);
    } finally {
      setPredictLoading(false);
    }
  };

  const submitSimulation = async () => {
    setSimulateLoading(true);
    setSimulationError(null);
    try {
      const simulationResponse = await fetchJsonWithFallback('/simulacion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_input: toPredictionInput(baseScenario),
          adjusted_input: toPredictionInput(form),
        }),
      });
      setSimulation(simulationResponse);
    } catch (err) {
      setSimulationError(err instanceof Error ? err.message : 'Error inesperado en simulación.');
      setSimulation(null);
    } finally {
      setSimulateLoading(false);
    }
  };

  const renderForm = () => (
    <article className="panel-card">
      <h2>Entradas del contrato</h2>
      <p className="helper">Cargar ejemplo y luego editar todos los campos si lo necesitas.</p>

      <div className="example-row">
        <select value={selectedExample} onChange={(event) => setSelectedExample(event.target.value)}>
          {EXAMPLES.map((example) => (
            <option key={example.key} value={example.key}>
              {example.name}
            </option>
          ))}
        </select>
        <button type="button" onClick={handleLoadExample}>Cargar ejemplo</button>
      </div>

      <p className="active-example">Caso activo: {activeExampleName}</p>

      <form className="prediction-form" onSubmit={submitPrediction}>
        <label>Peso transportado (kg)
          <input type="number" min={0} step="0.01" value={form.peso_kg} onChange={(event) => handleNumber('peso_kg', event.target.value)} />
        </label>
        <label>Distancia nominal (km)
          <input type="number" min={0} step="0.01" value={form.distancia_km} onChange={(event) => handleNumber('distancia_km', event.target.value)} />
        </label>
        <label>Altitud máxima (msnm)
          <input type="number" min={0} step="0.01" value={form.altitud_msnm} onChange={(event) => handleNumber('altitud_msnm', event.target.value)} />
        </label>
        <label>Penalización estimada (Bs)
          <input type="number" min={0} step="0.01" value={form.penalizacion_bs} onChange={(event) => handleNumber('penalizacion_bs', event.target.value)} />
        </label>
        <label>Siniestros estimados (Bs)
          <input type="number" min={0} step="0.01" value={form.siniestros_bs} onChange={(event) => handleNumber('siniestros_bs', event.target.value)} />
        </label>
        <label>Nivel SLA
          <select value={form.nivel_sla} onChange={(event) => setForm((prev) => ({ ...prev, nivel_sla: event.target.value as NivelSla }))}>
            <option value="ESTÁNDAR">ESTÁNDAR</option>
            <option value="ESTANDAR">ESTANDAR</option>
            <option value="ORO">ORO</option>
            <option value="PLATINO">PLATINO</option>
          </select>
        </label>
        <label>División
          <select value={form.es_division_farma ? 'FARMACOS' : 'ALIMENTOS'} onChange={(event) => setForm((prev) => ({ ...prev, es_division_farma: event.target.value === 'FARMACOS' }))}>
            <option value="ALIMENTOS">ALIMENTOS</option>
            <option value="FARMACOS">FÁRMACOS</option>
          </select>
        </label>
        <label>Puntaje de eficiencia térmica del chofer
          <input type="number" min={0} max={10} step="0.1" value={form.puntaje_chofer} onChange={(event) => handleNumber('puntaje_chofer', event.target.value)} />
        </label>
        <button type="submit" disabled={predictLoading}>{predictLoading ? 'Calculando predicción...' : 'Ejecutar predicción'}</button>
        <button type="button" className="simulate-btn" disabled={simulateLoading} onClick={submitSimulation}>{simulateLoading ? 'Simulando escenario...' : 'Simular vs escenario base'}</button>
      </form>
    </article>
  );

  const predictionInterval = prediction?.intervalo_confianza_95 ?? [0, 0];

  return (
    <main className="econometria-page">
      <section className="hero-card">
        <p className="eyebrow">Rentabilidad B2B (Econometría)</p>
        <h1>Módulo econométrico con 4 submódulos</h1>
        <p>Explora resumen, descriptiva, modelos y una capa operativa unificada de predicción y simulación.</p>
      </section>

      <section className="tabs-shell">
        {TAB_ITEMS.map((tab) => (
          <button key={tab.key} className={`tab-btn ${activeTab === tab.key ? 'active' : ''}`} onClick={() => loadTabData(tab.key)}>
            {tab.label}
          </button>
        ))}
      </section>

      {loadingSection ? <div className="panel-card">Cargando sección...</div> : null}
      {sectionError ? <div className="panel-card error-message">{sectionError}</div> : null}

      {activeTab === 'resumen' && summary ? (
        <section className="panel-grid">
          <article className="panel-card">
            <h2>KPIs ejecutivos</h2>
            <div className="result-kpis">
              <div><span>Contratos analizados</span><strong>{summary.contratos_analizados}</strong></div>
              <div><span>Rentables (%)</span><strong>{summary.pct_contratos_rentables.toFixed(2)}%</strong></div>
              <div><span>Con pérdida</span><strong>{summary.contratos_con_perdida}</strong></div>
              <div><span>Margen promedio</span><strong>{formatBs(summary.margen_promedio_bs)}</strong></div>
              <div><span>Margen mediana</span><strong>{formatBs(summary.margen_mediana_bs)}</strong></div>
              <div><span>Margen min / max</span><strong>{`${formatBs(summary.margen_min_bs)} / ${formatBs(summary.margen_max_bs)}`}</strong></div>
              <div><span>Periodo</span><strong>{summary.periodo_analizado}</strong></div>
              <div><span>Modelo activo</span><strong>{summary.modelo_principal_activo}</strong></div>
            </div>
          </article>
          <article className="panel-card">
            <h2>Advertencias metodológicas</h2>
            <ul className="list-box">
              {summary.advertencias_metodologicas.map((item) => <li key={item}>{item}</li>)}
            </ul>
            <h2>Origen de datos</h2>
            <ul className="list-box">
              {summary.origen_datos.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </article>
        </section>
      ) : null}

      {activeTab === 'descriptiva' && (
        <>
          <section className="panel-card filters-card">
            <h2>Filtros globales</h2>
            <div className="filters-grid">
              <label>División
                <select value={filters.division_operativa} onChange={(e) => setFilters((p) => ({ ...p, division_operativa: e.target.value }))}>
                  <option value="">Todas</option>
                  <option value="ALIMENTOS">ALIMENTOS</option>
                  <option value="FARMACOS">FÁRMACOS</option>
                </select>
              </label>
              <label>Nivel SLA
                <select value={filters.nivel_sla} onChange={(e) => setFilters((p) => ({ ...p, nivel_sla: e.target.value }))}>
                  <option value="">Todos</option>
                  <option value="ESTÁNDAR">ESTÁNDAR</option>
                  <option value="ORO">ORO</option>
                  <option value="PLATINO">PLATINO</option>
                </select>
              </label>
              <label>Año
                <input value={filters.anio} onChange={(e) => setFilters((p) => ({ ...p, anio: e.target.value }))} placeholder="ej: 2025" />
              </label>
              <label>Trimestre
                <select value={filters.trimestre} onChange={(e) => setFilters((p) => ({ ...p, trimestre: e.target.value }))}>
                  <option value="">Todos</option>
                  <option value="1">Q1</option>
                  <option value="2">Q2</option>
                  <option value="3">Q3</option>
                  <option value="4">Q4</option>
                </select>
              </label>
              <label>Con penalización
                <select value={filters.con_penalizacion} onChange={(e) => setFilters((p) => ({ ...p, con_penalizacion: e.target.value }))}>
                  <option value="">Todos</option>
                  <option value="true">Sí</option>
                  <option value="false">No</option>
                </select>
              </label>
              <label>Con siniestros
                <select value={filters.con_siniestros} onChange={(e) => setFilters((p) => ({ ...p, con_siniestros: e.target.value }))}>
                  <option value="">Todos</option>
                  <option value="true">Sí</option>
                  <option value="false">No</option>
                </select>
              </label>
            </div>
            <button className="reload-btn" onClick={reloadDescriptive}>Aplicar filtros</button>
          </section>

          {descriptive ? (
            <section className="panel-grid">
              {descriptive.warning ? <article className="panel-card error-message">{descriptive.warning}</article> : null}

              <article className="panel-card chart-card">
                <h2>Distribución de margen real</h2>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={descriptive.margin_distribution}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
                    <XAxis dataKey="bucket" hide />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" fill="#2d84e2" />
                  </BarChart>
                </ResponsiveContainer>
              </article>

              <article className="panel-card chart-card">
                <h2>Margen por división</h2>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={descriptive.margin_by_division}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
                    <XAxis dataKey="nombre" />
                    <YAxis />
                    <Tooltip formatter={(v) => formatBs(Number(v))} />
                    <Bar dataKey="margen_promedio_bs" fill="#1faf86" />
                  </BarChart>
                </ResponsiveContainer>
              </article>

              <article className="panel-card chart-card">
                <h2>Margen por SLA</h2>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={descriptive.margin_by_sla}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
                    <XAxis dataKey="nombre" />
                    <YAxis />
                    <Tooltip formatter={(v) => formatBs(Number(v))} />
                    <Bar dataKey="margen_promedio_bs" fill="#c57d1f" />
                  </BarChart>
                </ResponsiveContainer>
              </article>

              <article className="panel-card chart-card">
                <h2>Estructura financiera promedio</h2>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={descriptive.financial_structure}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
                    <XAxis dataKey="etapa" />
                    <YAxis />
                    <Tooltip formatter={(v) => formatBs(Number(v))} />
                    <Bar dataKey="monto_bs" fill="#8e64e8" />
                  </BarChart>
                </ResponsiveContainer>
              </article>

              <article className="panel-card chart-card">
                <h2>Distancia vs margen</h2>
                <ResponsiveContainer width="100%" height={260}>
                  <ScatterChart>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
                    <XAxis type="number" dataKey="x" name="Distancia" />
                    <YAxis type="number" dataKey="y" name="Margen" />
                    <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                    <Scatter data={descriptive.scatter_distance_vs_margin} fill="#2d84e2" />
                  </ScatterChart>
                </ResponsiveContainer>
              </article>

              <article className="panel-card chart-card">
                <h2>Evolución trimestral del margen</h2>
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={descriptive.quarterly_trend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
                    <XAxis dataKey="periodo" />
                    <YAxis />
                    <Tooltip formatter={(v) => formatBs(Number(v))} />
                    <Legend />
                    <Line type="monotone" dataKey="margen_promedio_bs" stroke="#1faf86" />
                  </LineChart>
                </ResponsiveContainer>
              </article>

              <article className="panel-card chart-card">
                <h2>Correlaciones con margen</h2>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={descriptive.correlations.slice(0, 8)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
                    <XAxis dataKey="variable" />
                    <YAxis domain={[-1, 1]} />
                    <Tooltip formatter={(v) => Number(v).toFixed(3)} />
                    <Bar dataKey="r" fill="#8e64e8" />
                  </BarChart>
                </ResponsiveContainer>
              </article>

              <article className="panel-card chart-card notebook-chart-card">
                <h2>Rentabilidad por cliente</h2>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={[...descriptiveClientRanking.slice(0, 6)].reverse()} layout="vertical" margin={{ left: 10, right: 30 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
                    <XAxis type="number" tickFormatter={(value) => formatBs(Number(value))} />
                    <YAxis type="category" dataKey="nombre" width={170} />
                    <Tooltip formatter={(v, _name, payload) => [formatBs(Number(v)), `Contratos: ${payload?.payload?.contratos ?? 0}`]} />
                    <ReferenceLine x={clientRankingAverage} stroke="#ef6b5a" strokeDasharray="6 4" strokeWidth={2} />
                    <Bar dataKey="margen_promedio_bs" radius={[0, 10, 10, 0]}>
                      {[...descriptiveClientRanking.slice(0, 6)].reverse().map((item) => (
                        <Cell
                          key={item.nombre}
                          fill={item.categoria?.toUpperCase().includes('FARM') ? '#f5a623' : '#2d84e2'}
                        />
                      ))}
                      <LabelList dataKey="margen_promedio_bs" position="right" formatter={(value) => formatBs(Number(value ?? 0))} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <p className="helper">Línea punteada roja = promedio general de los clientes mostrados.</p>
              </article>

              <article className="panel-card chart-card notebook-chart-card">
                <h2>Rentabilidad por ruta</h2>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={[...descriptiveRouteRanking.slice(0, 6)].reverse()} layout="vertical" margin={{ left: 10, right: 30 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
                    <XAxis type="number" tickFormatter={(value) => formatBs(Number(value))} />
                    <YAxis type="category" dataKey="nombre" width={170} />
                    <Tooltip formatter={(v, _name, payload) => [formatBs(Number(v)), `Altitud: ${Math.round(Number(payload?.payload?.valor_extra ?? 0))} msnm`]} />
                    <ReferenceLine x={routeRankingAverage} stroke="#ef6b5a" strokeDasharray="6 4" strokeWidth={2} />
                    <Bar dataKey="margen_promedio_bs" radius={[0, 10, 10, 0]}>
                      {[...descriptiveRouteRanking.slice(0, 6)].reverse().map((item) => (
                        <Cell key={item.nombre} fill={(item.valor_extra ?? 0) > 3500 ? '#d15a4e' : '#4a92d8'} />
                      ))}
                      <LabelList dataKey="margen_promedio_bs" position="right" formatter={(value) => formatBs(Number(value ?? 0))} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <p className="helper">Rojo = rutas por encima de 3,500 msnm, azul = rutas por debajo del umbral.</p>
              </article>
            </section>
          ) : (
            <div className="panel-card">Selecciona esta pestaña o aplica filtros para cargar la capa descriptiva.</div>
          )}
        </>
      )}

      {activeTab === 'modelos' && models ? (
        <>
          <section className="panel-grid">
            <article className="panel-card formula-card">
              <h2>Modelo lineal múltiple</h2>
              <div className="formula-box">
                <BlockMath math={'Y_i = \\beta_0 + \\beta_1 X_{1i} + \\beta_2 X_{2i} + \\cdots + \\beta_k X_{ki} + \\varepsilon_i'} />
              </div>
              <p className="helper">Interpretación operativa: cada coeficiente cambia el margen esperado en Bs por unidad adicional de la variable.</p>
            </article>

            <article className="panel-card formula-card">
              <h2>Modelo log-log (elasticidades)</h2>
              <div className="formula-box">
                <BlockMath math={'\\ln(Y_i + c) = \\alpha + \\delta_1 \\ln(X_{1i}+1) + \\delta_2 \\ln(X_{2i}+1) + \\cdots + \\delta_k X_{ki} + \\varepsilon_i'} />
              </div>
              <p className="helper">Interpretación analítica: los coeficientes logarítmicos se leen como cambios porcentuales aproximados.</p>
            </article>

            <article className="panel-card chart-card">
              <h2>Modelo 1 - Betas estandarizados</h2>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={modelStandardizedCoefficients.slice(0, 8).reverse()} layout="vertical" margin={{ top: 10, right: 24, bottom: 10, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
                  <XAxis type="number" tick={{ fontSize: 15 }} tickCount={7} />
                  <YAxis type="category" dataKey="variable" width={175} tick={{ fontSize: 14 }} tickFormatter={formatModelVariable} />
                  <Tooltip formatter={(v) => Number(v).toFixed(4)} labelFormatter={(label) => formatModelVariable(String(label))} />
                  <ReferenceLine x={0} stroke="rgba(255,255,255,0.35)" strokeWidth={1.5} />
                  <Bar dataKey="beta" radius={[0, 10, 10, 0]}>
                    {modelStandardizedCoefficients.slice(0, 8).reverse().map((item) => (
                      <Cell key={item.variable} fill={item.beta >= 0 ? '#61d4bc' : '#ef6b5a'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </article>

            <article className="panel-card chart-card">
              <h2>Ajuste observado vs predicho</h2>
              <ResponsiveContainer width="100%" height={300}>
                <ScatterChart margin={{ top: 8, right: 16, bottom: 26, left: 22 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
                  <XAxis
                    type="number"
                    dataKey="x"
                    name="Observado"
                    tickFormatter={(v) => formatBsAxis(Number(v))}
                    tick={{ fontSize: 15 }}
                    height={36}
                    minTickGap={14}
                    tickMargin={8}
                  />
                  <YAxis
                    type="number"
                    dataKey="y"
                    name="Predicho"
                    tickFormatter={(v) => formatBsAxis(Number(v))}
                    tick={{ fontSize: 15 }}
                    width={126}
                    tickCount={6}
                    tickMargin={8}
                  />
                  <Tooltip cursor={{ strokeDasharray: '3 3' }} formatter={(value) => formatBs(Number(value))} labelFormatter={() => 'Contrato'} />
                  <ReferenceLine x={0} y={0} stroke="transparent" />
                  <ReferenceLine segment={[{ x: observedPredictedExtent.min, y: observedPredictedExtent.min }, { x: observedPredictedExtent.max, y: observedPredictedExtent.max }]} stroke="#ef6b5a" strokeWidth={2.5} strokeDasharray="6 4" />
                  <Scatter data={observedPredictedPoints} fill="#2d84e2" />
                </ScatterChart>
              </ResponsiveContainer>
            </article>
          </section>

          <section className="panel-grid">
            <article className="panel-card">
              <h2>Modelo OLS</h2>
              <p className="helper">{models.ols.formula}</p>
              <div className="result-kpis">
                <div><span>R²</span><strong>{models.ols.r2.toFixed(4)}</strong></div>
                <div><span>R² ajustado</span><strong>{models.ols.r2_ajustado.toFixed(4)}</strong></div>
                <div><span>F-statistic</span><strong>{models.ols.f_statistic.toFixed(2)}</strong></div>
                <div><span>Observaciones</span><strong>{models.ols.n_observaciones}</strong></div>
              </div>
              <h3 className="sub-title">Coeficientes con mayor impacto</h3>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={modelCoefficients.slice(0, 8).map((item) => ({ ...item, signed: item.beta }))} layout="vertical" margin={{ left: 18, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="variable" width={150} tickFormatter={formatModelVariable} />
                  <Tooltip formatter={(v) => Number(v).toFixed(4)} labelFormatter={(label) => formatModelVariable(String(label))} />
                  <ReferenceLine x={0} stroke="rgba(255,255,255,0.35)" strokeWidth={1.5} />
                  <Bar dataKey="signed" radius={[0, 10, 10, 0]}>
                    {modelCoefficients.slice(0, 8).map((item) => (
                      <Cell key={item.variable} fill={item.beta >= 0 ? '#61d4bc' : '#ef6b5a'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </article>

            <article className="panel-card">
              <h2>Diagnóstico OLS</h2>
              <div className="result-kpis">
                <div><span>RMSE</span><strong>{models.ols.diagnostico.rmse.toFixed(2)}</strong></div>
                <div><span>MAE</span><strong>{models.ols.diagnostico.mae.toFixed(2)}</strong></div>
                <div><span>BP p-value</span><strong>{models.ols.diagnostico.test_breusch_pagan_pvalue.toFixed(4)}</strong></div>
                <div><span>Sig. 5%</span><strong>{models.ols.diagnostico.n_vars_significativas_5pct}</strong></div>
              </div>
              <h3 className="sub-title">Coeficientes técnicos</h3>
              <div className="model-table-wrap">
                <table className="model-table">
                  <thead>
                    <tr>
                      <th>Variable</th>
                      <th>β</th>
                      <th>p-value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {modelCoefficients.slice(0, 8).map((item) => (
                      <tr key={item.variable}>
                        <td>{formatModelVariable(item.variable)}</td>
                        <td>{item.beta.toFixed(4)}</td>
                        <td className={item.significativo_5pct ? 'ok' : ''}>{item.p_value.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>

            <article className="panel-card">
              <h2>Modelo Log-Log</h2>
              <p className="helper">{models.loglog.transformacion}</p>
              <p className="helper">Offset: {models.loglog.offset_aplicado}</p>
              <div className="result-kpis">
                <div><span>Disponible</span><strong>{models.loglog.disponible ? 'Sí' : 'No'}</strong></div>
                <div><span>Variables</span><strong>{models.loglog.variables.length}</strong></div>
              </div>
              <h3 className="sub-title">Elasticidades</h3>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={models.loglog.variables.filter((item) => item.variable !== 'const').slice(0, 8)} layout="vertical" margin={{ left: 18, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="variable" width={150} tickFormatter={formatModelVariable} />
                  <Tooltip formatter={(v) => Number(v).toFixed(4)} labelFormatter={(label) => formatModelVariable(String(label))} />
                  <Bar dataKey="beta" radius={[0, 10, 10, 0]} fill="#c57d1f" />
                </BarChart>
              </ResponsiveContainer>
            </article>

            <article className="panel-card">
              <h2>Interpretación log-log</h2>
              <ul className="list-box">
                {models.loglog.interpretacion_porcentual.map((item) => <li key={item}>{item}</li>)}
              </ul>
              <h3 className="sub-title">Limitaciones</h3>
              <ul className="list-box">
                {models.loglog.limitaciones.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </article>

            <article className="panel-card chart-card">
              <h2>Comparativa de modelos</h2>
              <p className="helper">Modelo operativo principal: {models.comparativa.modelo_operativo_principal}</p>
              <p>{models.comparativa.motivo}</p>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart
                  data={[
                    { name: 'R² OLS', value: models.comparativa.metricas.r2_ols as number },
                    { name: 'AIC OLS', value: models.comparativa.metricas.aic_ols as number },
                    { name: 'BIC OLS', value: models.comparativa.metricas.bic_ols as number },
                  ]}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="value" stroke="#8e64e8" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
              <ul className="list-box">
                {models.comparativa.utilidad_practica.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </article>
          </section>

          <section className="panel-grid">
            <article className="panel-card chart-card">
              <h2>Coeficientes significativos</h2>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={modelCoefficients.filter((item) => item.significativo_5pct)} layout="vertical" margin={{ left: 18, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="variable" width={150} tickFormatter={formatModelVariable} />
                  <Tooltip formatter={(v) => Number(v).toFixed(4)} labelFormatter={(label) => formatModelVariable(String(label))} />
                  <Bar dataKey="beta" radius={[0, 10, 10, 0]} fill="#65d18e" />
                </BarChart>
              </ResponsiveContainer>
            </article>

            <article className="panel-card chart-card">
              <h2>Intervalos de confianza 95%</h2>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={modelCoefficients.slice(0, 8)} layout="vertical" margin={{ left: 18, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="variable" width={150} tickFormatter={formatModelVariable} />
                  <Tooltip formatter={(v) => Number(v).toFixed(4)} labelFormatter={(label) => formatModelVariable(String(label))} />
                  <Bar dataKey="ci_95_hi" fill="#1a78c2" radius={[0, 10, 10, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </article>
          </section>
        </>
      ) : null}

      {activeTab === 'simulacion' && (
        <section className="panel-grid">
          {renderForm()}
          <article className="panel-card result-card">
            <h2>Resultado operativo</h2>
            {predictionError ? <p className="error-message">{predictionError}</p> : null}
            {simulationError ? <p className="error-message">{simulationError}</p> : null}

            {!prediction ? (
              <div className="empty-state"><p>Ejecuta predicción para ver margen esperado e intervalo de confianza.</p></div>
            ) : (
              <>
                <div className="result-kpis">
                  <div><span>Margen predicho</span><strong>{formatBs(prediction.margen_predicho_bs)}</strong></div>
                  <div><span>Intervalo (95%)</span><strong>{`${formatBs(Number(predictionInterval[0] ?? 0))} a ${formatBs(Number(predictionInterval[1] ?? 0))}`}</strong></div>
                  <div><span>Rentable</span><strong className={prediction.rentable ? 'ok' : 'risk'}>{prediction.rentable ? 'Sí' : 'No'}</strong></div>
                  <div><span>Segmentación</span><strong>{`${prediction.division} · SLA ${prediction.nivel_sla}`}</strong></div>
                </div>
                <div className="alerts-box">
                  <h3>Alertas operativas</h3>
                  {prediction.alertas.length === 0 ? <p>Sin alertas críticas.</p> : <ul>{prediction.alertas.map((alerta) => <li key={alerta}>{alerta}</li>)}</ul>}
                </div>
              </>
            )}

            {!simulation ? (
              <div className="empty-state"><p>Ejecuta simulación para comparar escenario base vs ajustado.</p></div>
            ) : (
              <>
                <div className="result-kpis">
                  <div><span>Margen base</span><strong>{formatBs(simulation.margen_base_bs)}</strong></div>
                  <div><span>Margen simulado</span><strong>{formatBs(simulation.margen_simulado_bs)}</strong></div>
                  <div><span>Diferencia absoluta</span><strong>{formatBs(simulation.diferencia_absoluta_bs)}</strong></div>
                  <div><span>Diferencia %</span><strong>{simulation.diferencia_porcentual.toFixed(2)}%</strong></div>
                </div>
                <div className="interpretation-box"><p>{simulation.interpretacion_cambio}</p></div>
                <div className="alerts-box">
                  <h3>Alertas operativas del escenario ajustado</h3>
                  {simulation.alertas_operativas.length === 0 ? <p>Sin alertas críticas.</p> : <ul>{simulation.alertas_operativas.map((alerta) => <li key={alerta}>{alerta}</li>)}</ul>}
                </div>
              </>
            )}
          </article>
        </section>
      )}
    </main>
  );
}
