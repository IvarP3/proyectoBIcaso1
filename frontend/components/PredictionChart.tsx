import {
  Area,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid
} from 'recharts';

type SerieHistorica = {
  meses: string[];
  margen_neto_bs: number[];
};

type ForecastItemRaw = {
  month: string;
  projected_income_bob: number;
  lower_bound_bob: number;
  upper_bound_bob: number;
};

type ForecastRaw = {
  items: ForecastItemRaw[];
};

type PredictionChartProps = {
  serie: SerieHistorica;
  forecast: ForecastRaw;
};

export default function PredictionChart({ serie, forecast }: PredictionChartProps) {
  const CHART_RESIZE_DEBOUNCE_MS = 160;
  const forecastItems = Array.isArray(forecast?.items) ? forecast.items : [];

  const historyData = serie.meses.map((mes: string, idx: number) => ({
    mes,
    valor: Number(serie.margen_neto_bs[idx] ?? 0) / 1000,
    isHistorico: true,
    inferior: null,
    superior: null
  }));

  const forecastData = forecastItems.map((item: ForecastItemRaw) => ({
    mes: item.month,
    valor: Number(item.projected_income_bob) / 1000,
    inferior: Number(item.lower_bound_bob) / 1000,
    superior: Number(item.upper_bound_bob) / 1000,
    isHistorico: false
  }));

  const allData = [...historyData, ...forecastData];
  const splitLabel = serie.meses[serie.meses.length - 1];

  return (
    <div className="prediction-chart-wrapper">
      <ResponsiveContainer width="100%" height={400} debounce={CHART_RESIZE_DEBOUNCE_MS}>
        <ComposedChart data={allData} margin={{ top: 20, right: 24, left: 0, bottom: 20 }}>
          <defs>
            <linearGradient id="forecastBand" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#C0392B" stopOpacity={0.28} />
              <stop offset="95%" stopColor="#C0392B" stopOpacity={0.02} />
            </linearGradient>
          </defs>

          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
          <XAxis dataKey="mes" stroke="#AED6F1" angle={-45} textAnchor="end" height={80} />
          <YAxis
            stroke="#AED6F1"
            label={{ value: 'Miles de Bs', angle: -90, position: 'insideLeft' }}
          />

          {splitLabel ? (
            <ReferenceLine
              x={splitLabel}
              stroke="rgba(174, 214, 241, 0.55)"
              strokeDasharray="6 4"
              label={{ value: 'Inicio forecast', position: 'top', fill: '#AED6F1', fontSize: 11 }}
            />
          ) : null}

          <Tooltip
            contentStyle={{ backgroundColor: '#10243a', border: '1px solid #2c5d87', borderRadius: 8 }}
            formatter={(value, name) => {
              if (name === 'IC 90%') return null;
              const isMain = name === 'Histórico + Forecast';
              const styledValue = (
                <span style={{ fontWeight: isMain ? 700 : 400, color: isMain ? '#ffffff' : 'rgba(174,214,241,0.45)' }}>
                  {`${Number(value).toFixed(1)}K Bs`}
                </span>
              );
              return [styledValue, name] as any;
            }}
          />
          <Legend />

          <Area
            type="monotone"
            dataKey="superior"
            stroke="none"
            fill="none"
            name="IC superior"
            isAnimationActive={false}
          />
          <Area
            type="monotone"
            dataKey="inferior"
            stroke="none"
            fill="url(#forecastBand)"
            name="IC 90%"
            isAnimationActive={false}
          />

          <Line
            type="monotone"
            dataKey="valor"
            stroke="#1B4F72"
            strokeWidth={2.4}
            name="Histórico + Forecast"
            isAnimationActive={false}
            dot={({ cx, cy, payload }) => (
              <circle
                cx={cx}
                cy={cy}
                r={payload?.isHistorico ? 3.5 : 5}
                fill={payload?.isHistorico ? '#1B4F72' : '#C0392B'}
                stroke="#FFFFFF"
                strokeWidth={1.5}
              />
            )}
          />
          <Line
            type="monotone"
            dataKey="inferior"
            stroke="rgba(127, 140, 141, 0.45)"
            strokeDasharray="4 3"
            dot={false}
            name="IC inferior"
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="superior"
            stroke="rgba(127, 140, 141, 0.45)"
            strokeDasharray="4 3"
            dot={false}
            name="IC superior"
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>

      <style jsx>{`
        .prediction-chart-wrapper {
          width: 100%;
          background: rgba(27, 79, 114, 0.08);
          border-radius: 12px;
          padding: 18px;
          border: 1px solid rgba(41, 128, 185, 0.28);
        }
      `}</style>
    </div>
  );
}
