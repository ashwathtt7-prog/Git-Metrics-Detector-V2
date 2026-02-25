import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getDashboardData } from '../api/visualizationApi';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ComposedChart, ReferenceLine, Scatter, ScatterChart,
} from 'recharts';

const COLORS = [
  '#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6',
  '#ec4899', '#06b6d4', '#f97316', '#6366f1', '#14b8a6',
  '#e11d48', '#84cc16',
];

const GRADIENT_PAIRS = [
  ['#ef4444', '#f97316'],
  ['#3b82f6', '#06b6d4'],
  ['#10b981', '#84cc16'],
  ['#f59e0b', '#f97316'],
  ['#8b5cf6', '#ec4899'],
  ['#ec4899', '#f43f5e'],
  ['#06b6d4', '#3b82f6'],
  ['#6366f1', '#8b5cf6'],
];

interface ChartData {
  id: string;
  name: string;
  description: string;
  category: string;
  data_type: string;
  platform: string;
  source: string;
  entries: Array<{ date: string; value: number | string; notes: string }>;
  entry_count: number;
  insights: any;
  latest_value: number | string | null;
}

interface DashboardData {
  workspace: { id: string; name: string; repo_url: string; description: string };
  summary: { total_metrics: number; total_entries: number; categories: Record<string, number> };
  category_distribution: Array<{ name: string; value: number }>;
  charts: ChartData[];
  metabase_url: string | null;
}

/* ---------- Analysis Helpers ---------- */

function analyzeDataPattern(values: number[]): {
  trend: 'rising' | 'falling' | 'stable' | 'volatile';
  volatility: number;
  hasSpikes: boolean;
  anomalies: number[];
  movingAvg: number[];
  trendPct: number;
  bestChartType: 'area' | 'line' | 'bar' | 'composed';
} {
  if (values.length < 2) return { trend: 'stable', volatility: 0, hasSpikes: false, anomalies: [], movingAvg: values, trendPct: 0, bestChartType: 'bar' };

  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((a, b) => a + (b - avg) ** 2, 0) / values.length;
  const stddev = Math.sqrt(variance);
  const cv = avg !== 0 ? (stddev / Math.abs(avg)) * 100 : 0;

  // Trend detection via linear regression
  const n = values.length;
  const xBar = (n - 1) / 2;
  const yBar = avg;
  let num = 0, den = 0;
  for (let i = 0; i < n; i++) {
    num += (i - xBar) * (values[i] - yBar);
    den += (i - xBar) ** 2;
  }
  const slope = den !== 0 ? num / den : 0;
  const trendPct = avg !== 0 ? (slope * n / Math.abs(avg)) * 100 : 0;

  // Anomalies: values beyond 2 standard deviations
  const anomalies: number[] = [];
  values.forEach((v, i) => {
    if (Math.abs(v - avg) > 2 * stddev) anomalies.push(i);
  });

  // Moving average (window=5)
  const window = Math.min(5, Math.floor(values.length / 3));
  const movingAvg: number[] = [];
  for (let i = 0; i < values.length; i++) {
    const start = Math.max(0, i - Math.floor(window / 2));
    const end = Math.min(values.length, start + window);
    const slice = values.slice(start, end);
    movingAvg.push(slice.reduce((a, b) => a + b, 0) / slice.length);
  }

  const trend: 'rising' | 'falling' | 'stable' | 'volatile' =
    cv > 40 ? 'volatile' :
      trendPct > 10 ? 'rising' :
        trendPct < -10 ? 'falling' : 'stable';

  // Smart chart selection
  let bestChartType: 'area' | 'line' | 'bar' | 'composed' = 'line';
  if (values.length <= 7) bestChartType = 'bar';
  else if (anomalies.length > 0 || cv > 30) bestChartType = 'composed';
  else if (trend === 'rising' || trend === 'falling') bestChartType = 'area';

  return { trend, volatility: cv, hasSpikes: anomalies.length > 0, anomalies, movingAvg, trendPct, bestChartType };
}

function getHealthScore(chart: ChartData): number {
  const values = chart.entries.filter(e => typeof e.value === 'number').map(e => e.value as number);
  if (values.length < 2) return 50;
  const analysis = analyzeDataPattern(values);
  const name = chart.name.toLowerCase();

  // Context-aware scoring
  const isErrorMetric = /error|fail|crash|timeout|exception|bug|defect/.test(name);
  const isRateMetric = /rate|percentage|ratio|coverage|uptime|availability/.test(name);
  const isLatencyMetric = /latency|response.*time|duration|ttfb|load.*time/.test(name);

  let score = 70; // baseline

  if (isErrorMetric) {
    // For error metrics, lower is better, stable is great
    if (analysis.trend === 'falling') score += 20;
    else if (analysis.trend === 'rising') score -= 30;
    if (analysis.volatility < 15) score += 10;
    if (analysis.hasSpikes) score -= 15;
  } else if (isLatencyMetric) {
    // For latency, lower and stable is better
    if (analysis.trend === 'falling') score += 15;
    else if (analysis.trend === 'rising') score -= 20;
    if (analysis.volatility > 30) score -= 15;
  } else if (isRateMetric) {
    // For rates/coverage, higher and stable is better
    if (analysis.trend === 'rising') score += 15;
    else if (analysis.trend === 'falling') score -= 20;
    if (analysis.volatility < 20) score += 10;
  } else {
    // Generic: stability is good, growth is usually good
    if (analysis.trend === 'stable') score += 10;
    if (analysis.volatility < 25) score += 5;
    if (analysis.trend === 'rising') score += 5;
  }

  return Math.max(0, Math.min(100, score));
}

function getTrendLabel(analysis: ReturnType<typeof analyzeDataPattern>): { text: string; emoji: string; color: string } {
  switch (analysis.trend) {
    case 'rising': return { text: 'Upward Trend', emoji: '📈', color: '#10b981' };
    case 'falling': return { text: 'Downward Trend', emoji: '📉', color: '#ef4444' };
    case 'volatile': return { text: 'High Volatility', emoji: '⚡', color: '#f59e0b' };
    default: return { text: 'Stable', emoji: '✅', color: '#3b82f6' };
  }
}

/* ---------- Stat Card ---------- */
function StatCard({ icon, label, value, color, subtitle }: {
  icon: string; label: string; value: string | number; color: string; subtitle?: string;
}) {
  return (
    <div className="stat-card" style={{ '--accent': color } as React.CSSProperties}>
      <div className="stat-icon" style={{ background: `${color}18`, color }}>{icon}</div>
      <div className="stat-info">
        <span className="stat-value">{value}</span>
        <span className="stat-label">{label}</span>
        {subtitle && <span className="stat-sub">{subtitle}</span>}
      </div>
    </div>
  );
}

/* ---------- Custom Tooltip ---------- */
function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="custom-tooltip">
      <p className="tooltip-label">{label}</p>
      {payload.map((p: any, i: number) => (
        <p key={i} className="tooltip-row">
          <span className="tooltip-dot" style={{ background: p.color }} />
          <span className="tooltip-name">{p.name || p.dataKey}:</span>
          <span className="tooltip-val">{typeof p.value === 'number' ? p.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : p.value}</span>
        </p>
      ))}
    </div>
  );
}

/* ---------- Insight Panel ---------- */
function InsightPanel({ insights, metricName }: { insights: any; metricName: string }) {
  if (!insights) return null;

  const title = insights.context_title || insights.business_context;
  const description = insights.context_description || insights.why_it_matters;
  const targets = insights.recommended_targets;
  const strategies = insights.improvement_strategies;
  const riskSignals = insights.risk_signals;
  const correlations = insights.correlations;

  if (!title && !description) return null;

  return (
    <div className="insight-panel">
      {title && <h4 className="insight-title">💡 {title}</h4>}
      {description && <p className="insight-desc">{typeof description === 'string' ? description.slice(0, 300) : ''}</p>}

      {targets && (
        <div className="insight-targets">
          <span className="target-label">Targets:</span>
          <div className="target-items">
            {targets.healthy && <span className="target healthy" title={targets.healthy}>🟢 Healthy</span>}
            {targets.warning && <span className="target warning" title={targets.warning}>🟡 Warning</span>}
            {targets.critical && <span className="target critical" title={targets.critical}>🔴 Critical</span>}
          </div>
        </div>
      )}

      {correlations && Array.isArray(correlations) && correlations.length > 0 && (
        <div className="insight-correlations">
          <span className="corr-label">🔗 Linked metrics:</span>
          <p className="corr-text">{correlations[0]}</p>
        </div>
      )}

      {strategies && Array.isArray(strategies) && strategies.length > 0 && (
        <details className="insight-strategies">
          <summary>🛠️ {strategies.length} improvement {strategies.length === 1 ? 'strategy' : 'strategies'}</summary>
          <ul>
            {strategies.slice(0, 3).map((s: string, i: number) => <li key={i}>{s}</li>)}
          </ul>
        </details>
      )}

      {riskSignals && typeof riskSignals === 'string' && (
        <details className="insight-risk">
          <summary>⚠️ Risk signal</summary>
          <p>{riskSignals}</p>
        </details>
      )}
    </div>
  );
}

/* ---------- Individual Metric Chart ---------- */
function MetricChart({ chart, index }: { chart: ChartData; index: number }) {
  const colorIdx = index % COLORS.length;
  const gradPair = GRADIENT_PAIRS[index % GRADIENT_PAIRS.length];
  const numericEntries = chart.entries.filter(e => typeof e.value === 'number');
  const hasNumericData = numericEntries.length > 0;

  if (!hasNumericData || chart.entries.length === 0) {
    return (
      <div className="chart-card">
        <div className="chart-head">
          <div>
            <h3 className="chart-title">{chart.name}</h3>
            <span className="chart-cat" style={{ background: `${COLORS[colorIdx]}15`, color: COLORS[colorIdx] }}>
              {chart.category}
            </span>
          </div>
        </div>
        <div className="chart-empty">
          <p>{chart.description || 'No numeric data available for visualization'}</p>
        </div>
        <InsightPanel insights={chart.insights} metricName={chart.name} />
      </div>
    );
  }

  const values = numericEntries.map(e => e.value as number);
  const analysis = analyzeDataPattern(values);
  const trendInfo = getTrendLabel(analysis);
  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const gradientId = `grad-${index}`;
  const maGradientId = `ma-grad-${index}`;

  // Build enriched chart data with moving average
  const enrichedData = chart.entries.map((e, i) => ({
    ...e,
    movingAvg: typeof e.value === 'number' ? +analysis.movingAvg[i]?.toFixed(2) : undefined,
    isAnomaly: analysis.anomalies.includes(i),
  }));

  // Smart chart rendering based on data analysis
  const renderChart = () => {
    if (analysis.bestChartType === 'composed' || analysis.hasSpikes) {
      // Composed chart: show actual values + moving average + anomaly markers
      return (
        <ComposedChart data={enrichedData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={gradPair[0]} stopOpacity={0.2} />
              <stop offset="95%" stopColor={gradPair[1]} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={{ stroke: '#e2e8f0' }} />
          <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
          <Tooltip content={<ChartTooltip />} />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
          <ReferenceLine y={avg} stroke="#94a3b8" strokeDasharray="5 5" label={{ value: `Avg: ${avg.toFixed(1)}`, fill: '#94a3b8', fontSize: 10 }} />
          <Area type="monotone" dataKey="value" name="Value" stroke={gradPair[0]} fill={`url(#${gradientId})`} strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="movingAvg" name="Trend" stroke={gradPair[1]} strokeWidth={2} strokeDasharray="4 4" dot={false} />
          {analysis.anomalies.length > 0 && (
            <Scatter name="Anomaly" dataKey="value" fill="#ef4444">
              {enrichedData.map((entry, i) => (
                <Cell key={i} fill={entry.isAnomaly ? '#ef4444' : 'transparent'} r={entry.isAnomaly ? 6 : 0} />
              ))}
            </Scatter>
          )}
        </ComposedChart>
      );
    }

    if (analysis.bestChartType === 'area') {
      return (
        <AreaChart data={enrichedData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={gradPair[0]} stopOpacity={0.3} />
              <stop offset="95%" stopColor={gradPair[1]} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={{ stroke: '#e2e8f0' }} />
          <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
          <Tooltip content={<ChartTooltip />} />
          <ReferenceLine y={avg} stroke="#94a3b8" strokeDasharray="5 5" label={{ value: `Avg: ${avg.toFixed(1)}`, fill: '#94a3b8', fontSize: 10 }} />
          <Area type="monotone" dataKey="value" stroke={gradPair[0]} fill={`url(#${gradientId})`} strokeWidth={2.5} dot={{ r: 2, fill: gradPair[0] }} activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2 }} />
          <Line type="monotone" dataKey="movingAvg" name="Trend" stroke={gradPair[1]} strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
        </AreaChart>
      );
    }

    if (analysis.bestChartType === 'bar') {
      return (
        <BarChart data={chart.entries} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={gradPair[0]} stopOpacity={0.9} />
              <stop offset="100%" stopColor={gradPair[1]} stopOpacity={0.6} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={{ stroke: '#e2e8f0' }} />
          <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
          <Tooltip content={<ChartTooltip />} />
          <ReferenceLine y={avg} stroke="#94a3b8" strokeDasharray="5 5" label={{ value: `Avg: ${avg.toFixed(1)}`, fill: '#94a3b8', fontSize: 10 }} />
          <Bar dataKey="value" fill={`url(#${gradientId})`} radius={[8, 8, 0, 0]} />
        </BarChart>
      );
    }

    // Default: line with trend
    return (
      <LineChart data={enrichedData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor={gradPair[0]} />
            <stop offset="100%" stopColor={gradPair[1]} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={{ stroke: '#e2e8f0' }} />
        <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
        <Tooltip content={<ChartTooltip />} />
        <ReferenceLine y={avg} stroke="#94a3b8" strokeDasharray="5 5" label={{ value: `Avg: ${avg.toFixed(1)}`, fill: '#94a3b8', fontSize: 10 }} />
        <Line type="monotone" dataKey="value" stroke={`url(#${gradientId})`} strokeWidth={2.5} dot={{ r: 2, fill: COLORS[colorIdx], stroke: '#fff', strokeWidth: 1 }} activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2, fill: COLORS[colorIdx] }} />
        <Line type="monotone" dataKey="movingAvg" name="Trend" stroke={COLORS[(colorIdx + 3) % COLORS.length]} strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
      </LineChart>
    );
  };

  return (
    <div className="chart-card">
      <div className="chart-head">
        <div>
          <h3 className="chart-title">{chart.name}</h3>
          <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', marginTop: '0.2rem', flexWrap: 'wrap' }}>
            <span className="chart-cat" style={{ background: `${COLORS[colorIdx]}15`, color: COLORS[colorIdx] }}>
              {chart.category}
            </span>
            {chart.platform && <span className="chart-platform">{chart.platform}</span>}
            <span className="trend-pill" style={{ background: `${trendInfo.color}15`, color: trendInfo.color }}>
              {trendInfo.emoji} {trendInfo.text}
            </span>
          </div>
        </div>
        <div className="chart-stats-right">
          <div className="chart-latest">
            <span className="latest-val">{typeof chart.latest_value === 'number' ? chart.latest_value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : chart.latest_value}</span>
            <span className="latest-lbl">Latest</span>
          </div>
          <div className={`trend-badge ${analysis.trendPct >= 0 ? 'trend-up' : 'trend-down'}`}>
            {analysis.trendPct >= 0 ? '↑' : '↓'} {Math.abs(analysis.trendPct).toFixed(1)}%
          </div>
        </div>
      </div>

      <div className="mini-stats">
        <div className="mini-stat"><span className="mini-lbl">Avg</span><span className="mini-val">{avg.toFixed(1)}</span></div>
        <div className="mini-stat"><span className="mini-lbl">Max</span><span className="mini-val">{max.toLocaleString()}</span></div>
        <div className="mini-stat"><span className="mini-lbl">Min</span><span className="mini-val">{min.toLocaleString()}</span></div>
        <div className="mini-stat"><span className="mini-lbl">Volatility</span><span className="mini-val">{analysis.volatility.toFixed(0)}%</span></div>
        {analysis.anomalies.length > 0 && (
          <div className="mini-stat anomaly-stat"><span className="mini-lbl">Anomalies</span><span className="mini-val">{analysis.anomalies.length}</span></div>
        )}
      </div>

      <div className="chart-body">
        <ResponsiveContainer width="100%" height={220}>
          {renderChart()}
        </ResponsiveContainer>
      </div>

      {chart.description && <p className="chart-desc">{chart.description}</p>}
      <InsightPanel insights={chart.insights} metricName={chart.name} />
    </div>
  );
}

/* ========== MAIN DASHBOARD ========== */
export default function DashboardPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!workspaceId) return;
    setLoading(true);
    getDashboardData(workspaceId)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [workspaceId]);

  if (loading) {
    return (
      <div className="page-center">
        <div className="spinner" />
        <h2>Loading Analytics</h2>
        <p>Analyzing data patterns and generating insights...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="page-center">
        <div className="error-icon">!</div>
        <h2>Dashboard Error</h2>
        <p>{error || 'Failed to load dashboard data'}</p>
        <a href="http://localhost:3001" className="btn-primary">Back to Workflow</a>
      </div>
    );
  }

  const { workspace, summary, category_distribution, charts } = data;

  // Combined timeline for overview (top 6 metrics only for readability)
  const timelineMap: Record<string, Record<string, number>> = {};
  charts.slice(0, 6).forEach((chart) => {
    chart.entries.forEach((e) => {
      if (typeof e.value === 'number') {
        if (!timelineMap[e.date]) timelineMap[e.date] = {};
        timelineMap[e.date][chart.name] = e.value;
      }
    });
  });
  const timelineDates = Object.keys(timelineMap).sort();
  const overviewData = timelineDates.map((date) => ({ date, ...timelineMap[date] }));

  // Health Radar — uses pattern-aware scoring instead of raw normalization
  const healthData = charts
    .filter(c => c.entries.length > 0 && typeof c.latest_value === 'number')
    .slice(0, 8)
    .map((m) => ({
      metric: m.name.length > 18 ? m.name.slice(0, 16) + '…' : m.name,
      health: getHealthScore(m),
      fullMark: 100,
    }));

  // Volatility comparison — which metrics fluctuate most?
  const volatilityData = charts
    .filter(c => c.entries.filter(e => typeof e.value === 'number').length >= 3)
    .map((c, i) => {
      const vals = c.entries.filter(e => typeof e.value === 'number').map(e => e.value as number);
      const analysis = analyzeDataPattern(vals);
      return {
        name: c.name.length > 18 ? c.name.slice(0, 16) + '…' : c.name,
        volatility: +analysis.volatility.toFixed(1),
        anomalies: analysis.anomalies.length,
        fill: COLORS[i % COLORS.length],
      };
    })
    .sort((a, b) => b.volatility - a.volatility)
    .slice(0, 10);

  // Category health — average health per category
  const categoryHealth: Record<string, { total: number; count: number }> = {};
  charts.forEach(c => {
    const score = getHealthScore(c);
    if (!categoryHealth[c.category]) categoryHealth[c.category] = { total: 0, count: 0 };
    categoryHealth[c.category].total += score;
    categoryHealth[c.category].count += 1;
  });
  const categoryHealthData = Object.entries(categoryHealth).map(([name, { total, count }], i) => ({
    name,
    health: Math.round(total / count),
    fill: COLORS[i % COLORS.length],
  }));

  // Count anomalies and volatile metrics
  const anomalyCount = charts.reduce((acc, c) => {
    const vals = c.entries.filter(e => typeof e.value === 'number').map(e => e.value as number);
    if (vals.length < 2) return acc;
    return acc + analyzeDataPattern(vals).anomalies.length;
  }, 0);

  const volatileCount = charts.filter(c => {
    const vals = c.entries.filter(e => typeof e.value === 'number').map(e => e.value as number);
    if (vals.length < 3) return false;
    return analyzeDataPattern(vals).volatility > 30;
  }).length;

  return (
    <div className="dashboard">
      {/* ===== HERO ===== */}
      <header className="hero">
        <div className="hero-glow" />
        <div className="hero-content">
          <div className="hero-text">
            <span className="hero-badge">Analytics Intelligence</span>
            <h1 className="hero-title">{workspace.name}</h1>
            {workspace.description && <p className="hero-desc">{workspace.description}</p>}
            <a href={workspace.repo_url} target="_blank" rel="noopener noreferrer" className="hero-repo">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" /></svg>
              {workspace.repo_url.replace('https://github.com/', '')}
            </a>
          </div>
          <div className="hero-actions">
            {data.metabase_url && (
              <a href={data.metabase_url} target="_blank" rel="noopener noreferrer" className="btn-metabase">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><rect x="3" y="3" width="18" height="18" rx="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" /></svg>
                Open in Metabase
              </a>
            )}
            <a href="http://localhost:3001" className="btn-ghost">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M19 12H5" /><path d="M12 19l-7-7 7-7" /></svg>
              Workflow
            </a>
          </div>
        </div>
      </header>

      {/* ===== STAT CARDS ===== */}
      <section className="stats-row">
        <StatCard icon="📊" label="Total Metrics" value={summary.total_metrics} color="#ef4444" />
        <StatCard icon="📈" label="Data Points" value={summary.total_entries.toLocaleString()} color="#3b82f6" />
        <StatCard icon="🏷️" label="Categories" value={Object.keys(summary.categories).length} color="#10b981" />
        <StatCard icon="⚡" label="Volatile Metrics" value={volatileCount} color="#f59e0b" subtitle={`${anomalyCount} anomalies detected`} />
      </section>

      {/* ===== OVERVIEW ROW ===== */}
      <section className="overview-grid">
        {/* Timeline */}
        {overviewData.length > 0 && (
          <div className="overview-card overview-wide">
            <h3 className="section-title"><span className="section-icon">📉</span> Metrics Timeline <span className="section-sub">(top {Math.min(6, charts.length)} by activity)</span></h3>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={overviewData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
                <defs>
                  {charts.slice(0, 6).map((c, i) => (
                    <linearGradient key={c.id} id={`ov-${i}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0.2} />
                      <stop offset="95%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0} />
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
                <Tooltip content={<ChartTooltip />} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
                {charts.slice(0, 6).filter(c => c.entries.some(e => typeof e.value === 'number')).map((c, i) => (
                  <Area key={c.id} type="monotone" dataKey={c.name} stroke={COLORS[i % COLORS.length]} fill={`url(#ov-${i})`} strokeWidth={2} dot={false} />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Category Distribution */}
        <div className="overview-card">
          <h3 className="section-title"><span className="section-icon">🎯</span> Metric Categories</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={category_distribution} cx="50%" cy="50%" innerRadius={55} outerRadius={95} paddingAngle={4} dataKey="value" stroke="none">
                {category_distribution.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip content={<ChartTooltip />} />
              <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Health Radar */}
        {healthData.length >= 3 && (
          <div className="overview-card">
            <h3 className="section-title"><span className="section-icon">🕸️</span> Health Score Radar</h3>
            <p className="section-sub-detail">Higher = healthier trend pattern</p>
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={healthData} cx="50%" cy="50%" outerRadius={85}>
                <PolarGrid stroke="#e2e8f0" />
                <PolarAngleAxis dataKey="metric" tick={{ fontSize: 9, fill: '#64748b' }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 9 }} />
                <Radar name="Health" dataKey="health" stroke="#10b981" fill="#10b981" fillOpacity={0.15} strokeWidth={2} />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Volatility Ranking */}
        {volatilityData.length > 0 && (
          <div className="overview-card overview-wide">
            <h3 className="section-title"><span className="section-icon">⚡</span> Stability Analysis <span className="section-sub">Lower volatility = more predictable</span></h3>
            <ResponsiveContainer width="100%" height={250}>
              <ComposedChart data={volatilityData} margin={{ top: 10, right: 20, left: 0, bottom: 30 }} layout="horizontal">
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false} angle={-25} textAnchor="end" />
                <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false} label={{ value: 'Volatility %', angle: -90, position: 'insideLeft', style: { fontSize: 10, fill: '#94a3b8' } }} />
                <Tooltip content={<ChartTooltip />} />
                <ReferenceLine y={20} stroke="#10b981" strokeDasharray="5 5" label={{ value: "Stable (<20%)", fill: '#10b981', fontSize: 10 }} />
                <ReferenceLine y={40} stroke="#f59e0b" strokeDasharray="5 5" label={{ value: "Volatile (>40%)", fill: '#f59e0b', fontSize: 10 }} />
                <Bar dataKey="volatility" name="Volatility %" radius={[8, 8, 0, 0]}>
                  {volatilityData.map((d, i) => (
                    <Cell key={i} fill={d.volatility > 40 ? '#ef4444' : d.volatility > 20 ? '#f59e0b' : '#10b981'} />
                  ))}
                </Bar>
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Category Health */}
        {categoryHealthData.length > 1 && (
          <div className="overview-card">
            <h3 className="section-title"><span className="section-icon">🏥</span> Category Health</h3>
            <p className="section-sub-detail">Average health score per category</p>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={categoryHealthData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
                <Tooltip content={<ChartTooltip />} />
                <ReferenceLine y={70} stroke="#10b981" strokeDasharray="3 3" label={{ value: "Good", fill: '#10b981', fontSize: 10 }} />
                <Bar dataKey="health" name="Health Score" radius={[8, 8, 0, 0]}>
                  {categoryHealthData.map((d, i) => (
                    <Cell key={i} fill={d.health >= 70 ? '#10b981' : d.health >= 50 ? '#f59e0b' : '#ef4444'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      {/* ===== INDIVIDUAL CHARTS ===== */}
      <section>
        <div className="section-header">
          <h2><span className="section-icon">🔬</span> Metric Deep Dive</h2>
          <p>Pattern analysis with trend detection, moving averages, and anomaly highlighting</p>
        </div>
        <div className="charts-grid">
          {charts.map((chart, i) => <MetricChart key={chart.id} chart={chart} index={i} />)}
        </div>
      </section>

      {/* ===== METABASE CTA ===== */}
      {data.metabase_url && (
        <footer className="footer-cta">
          <div className="footer-inner">
            <div>
              <h3>Need more advanced analytics?</h3>
              <p>Open in Metabase for SQL queries, custom filters, and interactive drill-downs</p>
            </div>
            <a href={data.metabase_url} target="_blank" rel="noopener noreferrer" className="btn-metabase-lg">
              Open Metabase Dashboard
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><path d="M7 17L17 7" /><path d="M7 7h10v10" /></svg>
            </a>
          </div>
        </footer>
      )}
    </div>
  );
}
