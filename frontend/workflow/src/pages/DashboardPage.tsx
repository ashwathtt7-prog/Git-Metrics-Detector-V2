import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getDashboardData } from '../api/workflowApi';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts';

// Vibrant color palette
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

interface DashboardData {
  workspace: {
    id: string;
    name: string;
    repo_url: string;
    description: string;
  };
  summary: {
    total_metrics: number;
    total_entries: number;
    categories: Record<string, number>;
  };
  category_distribution: Array<{ name: string; value: number }>;
  charts: Array<{
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
  }>;
  metabase_url: string | null;
}

function StatCard({ icon, label, value, color, subtitle }: {
  icon: string; label: string; value: string | number; color: string; subtitle?: string;
}) {
  return (
    <div className="dash-stat-card" style={{ '--accent': color } as React.CSSProperties}>
      <div className="dash-stat-icon" style={{ background: `${color}15`, color }}>{icon}</div>
      <div className="dash-stat-info">
        <span className="dash-stat-value">{value}</span>
        <span className="dash-stat-label">{label}</span>
        {subtitle && <span className="dash-stat-subtitle">{subtitle}</span>}
      </div>
    </div>
  );
}

function MetricChart({ chart, index }: { chart: DashboardData['charts'][0]; index: number }) {
  const colorIdx = index % COLORS.length;
  const gradPair = GRADIENT_PAIRS[index % GRADIENT_PAIRS.length];
  const hasNumericData = chart.entries.length > 0 && typeof chart.entries[0].value === 'number';

  if (!hasNumericData || chart.entries.length === 0) {
    return (
      <div className="dash-chart-card">
        <div className="dash-chart-header">
          <div>
            <h3 className="dash-chart-title">{chart.name}</h3>
            <span className="dash-chart-category" style={{ background: `${COLORS[colorIdx]}15`, color: COLORS[colorIdx] }}>
              {chart.category}
            </span>
          </div>
          {chart.latest_value !== null && (
            <div className="dash-chart-latest">
              <span className="dash-latest-val">{String(chart.latest_value)}</span>
              <span className="dash-latest-label">Latest</span>
            </div>
          )}
        </div>
        <div className="dash-chart-empty">
          <p>{chart.description || 'No numeric data available for visualization'}</p>
        </div>
      </div>
    );
  }

  // Decide chart type based on entry count and category
  const chartType = chart.entries.length <= 5 ? 'bar' :
    chart.category === 'performance' ? 'area' : 'line';

  // Compute simple stats
  const values = chart.entries.map(e => e.value as number);
  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const trend = values.length >= 2 ? values[values.length - 1] - values[0] : 0;
  const trendPct = values[0] !== 0 ? ((trend / Math.abs(values[0])) * 100).toFixed(1) : '0';

  const gradientId = `grad-${index}`;

  return (
    <div className="dash-chart-card">
      <div className="dash-chart-header">
        <div>
          <h3 className="dash-chart-title">{chart.name}</h3>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginTop: '0.25rem' }}>
            <span className="dash-chart-category" style={{ background: `${COLORS[colorIdx]}15`, color: COLORS[colorIdx] }}>
              {chart.category}
            </span>
            {chart.platform && (
              <span className="dash-chart-platform">{chart.platform}</span>
            )}
          </div>
        </div>
        <div className="dash-chart-stats">
          <div className="dash-chart-latest">
            <span className="dash-latest-val">{typeof chart.latest_value === 'number' ? chart.latest_value.toLocaleString() : chart.latest_value}</span>
            <span className="dash-latest-label">Latest</span>
          </div>
          <div className={`dash-trend ${trend >= 0 ? 'dash-trend-up' : 'dash-trend-down'}`}>
            <span>{trend >= 0 ? '↑' : '↓'} {trendPct}%</span>
          </div>
        </div>
      </div>

      {/* Mini stats row */}
      <div className="dash-mini-stats">
        <div className="dash-mini-stat">
          <span className="dash-mini-label">Avg</span>
          <span className="dash-mini-value">{avg.toFixed(1)}</span>
        </div>
        <div className="dash-mini-stat">
          <span className="dash-mini-label">Max</span>
          <span className="dash-mini-value">{max.toLocaleString()}</span>
        </div>
        <div className="dash-mini-stat">
          <span className="dash-mini-label">Min</span>
          <span className="dash-mini-value">{min.toLocaleString()}</span>
        </div>
        <div className="dash-mini-stat">
          <span className="dash-mini-label">Points</span>
          <span className="dash-mini-value">{chart.entry_count}</span>
        </div>
      </div>

      <div className="dash-chart-body">
        <ResponsiveContainer width="100%" height={220}>
          {chartType === 'area' ? (
            <AreaChart data={chart.entries} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={gradPair[0]} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={gradPair[1]} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={{ stroke: '#e2e8f0' }} />
              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ background: '#fff', border: '1px solid #f1f5f9', borderRadius: 12, boxShadow: '0 10px 25px rgba(0,0,0,0.08)' }}
                labelStyle={{ fontWeight: 700, color: '#1e293b' }}
              />
              <Area type="monotone" dataKey="value" stroke={gradPair[0]} fill={`url(#${gradientId})`} strokeWidth={2.5} dot={{ r: 3, fill: gradPair[0] }} activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2 }} />
            </AreaChart>
          ) : chartType === 'bar' ? (
            <BarChart data={chart.entries} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={gradPair[0]} stopOpacity={0.9} />
                  <stop offset="100%" stopColor={gradPair[1]} stopOpacity={0.6} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={{ stroke: '#e2e8f0' }} />
              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ background: '#fff', border: '1px solid #f1f5f9', borderRadius: 12, boxShadow: '0 10px 25px rgba(0,0,0,0.08)' }}
                labelStyle={{ fontWeight: 700, color: '#1e293b' }}
              />
              <Bar dataKey="value" fill={`url(#${gradientId})`} radius={[6, 6, 0, 0]} />
            </BarChart>
          ) : (
            <LineChart data={chart.entries} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor={gradPair[0]} />
                  <stop offset="100%" stopColor={gradPair[1]} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={{ stroke: '#e2e8f0' }} />
              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ background: '#fff', border: '1px solid #f1f5f9', borderRadius: 12, boxShadow: '0 10px 25px rgba(0,0,0,0.08)' }}
                labelStyle={{ fontWeight: 700, color: '#1e293b' }}
              />
              <Line type="monotone" dataKey="value" stroke={`url(#${gradientId})`} strokeWidth={2.5} dot={{ r: 3, fill: COLORS[colorIdx], stroke: '#fff', strokeWidth: 2 }} activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2, fill: COLORS[colorIdx] }} />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>

      {chart.description && (
        <p className="dash-chart-desc">{chart.description}</p>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!workspaceId) {
      navigate('/');
      return;
    }
    setLoading(true);
    getDashboardData(workspaceId)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [workspaceId, navigate]);

  if (loading) {
    return (
      <div className="dash-loading-page">
        <div className="dash-loading-spinner" />
        <h2>Loading Dashboard</h2>
        <p>Preparing your analytics visualizations...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="dash-error-page">
        <h2>Dashboard Error</h2>
        <p>{error || 'Failed to load dashboard data'}</p>
        <button className="btn-analyze" onClick={() => navigate('/')}>Back to Home</button>
      </div>
    );
  }

  const { workspace, summary, category_distribution, charts } = data;

  // Build a combined timeline from all metrics for the overview area chart
  const timelineMap: Record<string, Record<string, number>> = {};
  charts.forEach((chart) => {
    chart.entries.forEach((e) => {
      if (typeof e.value === 'number') {
        if (!timelineMap[e.date]) timelineMap[e.date] = {};
        timelineMap[e.date][chart.name] = e.value;
      }
    });
  });

  const timelineDates = Object.keys(timelineMap).sort();
  const overviewData = timelineDates.map((date) => ({
    date,
    ...timelineMap[date],
  }));

  // Metrics with numeric data for radar chart (normalize to 0-100)
  const radarMetrics = charts
    .filter(c => c.entries.length > 0 && typeof c.latest_value === 'number')
    .slice(0, 8);

  const radarData = radarMetrics.map((m) => {
    const vals = m.entries.filter(e => typeof e.value === 'number').map(e => e.value as number);
    const maxVal = Math.max(...vals, 1);
    return {
      metric: m.name.length > 20 ? m.name.slice(0, 18) + '...' : m.name,
      value: Math.round(((m.latest_value as number) / maxVal) * 100),
      fullMark: 100,
    };
  });

  return (
    <div className="dash-page">
      {/* Hero Header */}
      <div className="dash-hero">
        <div className="dash-hero-bg" />
        <div className="dash-hero-content">
          <div className="dash-hero-text">
            <span className="dash-hero-badge">Analytics Dashboard</span>
            <h1 className="dash-hero-title">{workspace.name}</h1>
            {workspace.description && (
              <p className="dash-hero-desc">{workspace.description}</p>
            )}
          </div>
          <div className="dash-hero-actions">
            {data.metabase_url && (
              <a
                href={data.metabase_url}
                target="_blank"
                rel="noopener noreferrer"
                className="dash-btn dash-btn-metabase"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <line x1="3" y1="9" x2="21" y2="9" />
                  <line x1="9" y1="21" x2="9" y2="9" />
                </svg>
                Open in Metabase
              </a>
            )}
            <button className="dash-btn dash-btn-back" onClick={() => navigate('/')}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M19 12H5" /><path d="M12 19l-7-7 7-7" />
              </svg>
              Back
            </button>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="dash-stats-row">
        <StatCard icon="📊" label="Total Metrics" value={summary.total_metrics} color="#ef4444" />
        <StatCard icon="📈" label="Data Points" value={summary.total_entries.toLocaleString()} color="#3b82f6" />
        <StatCard icon="🏷️" label="Categories" value={Object.keys(summary.categories).length} color="#10b981" />
        <StatCard icon="⚡" label="Avg per Metric" value={summary.total_metrics > 0 ? Math.round(summary.total_entries / summary.total_metrics) : 0} color="#f59e0b" subtitle="data points" />
      </div>

      {/* Overview Section: Combined Timeline + Category Pie + Radar */}
      <div className="dash-overview-grid">
        {/* Combined Timeline */}
        {overviewData.length > 0 && (
          <div className="dash-overview-card dash-overview-wide">
            <h3 className="dash-section-title">
              <span className="dash-section-icon">📉</span>
              Metrics Timeline Overview
            </h3>
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={overviewData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
                <defs>
                  {charts.slice(0, 6).map((c, i) => (
                    <linearGradient key={c.id} id={`overview-${i}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0.2} />
                      <stop offset="95%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0} />
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ background: '#fff', border: '1px solid #f1f5f9', borderRadius: 12, boxShadow: '0 10px 25px rgba(0,0,0,0.08)', fontSize: 12 }}
                />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
                {charts.slice(0, 6).filter(c => c.entries.some(e => typeof e.value === 'number')).map((c, i) => (
                  <Area
                    key={c.id}
                    type="monotone"
                    dataKey={c.name}
                    stroke={COLORS[i % COLORS.length]}
                    fill={`url(#overview-${i})`}
                    strokeWidth={2}
                    dot={false}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Category Distribution Pie */}
        <div className="dash-overview-card">
          <h3 className="dash-section-title">
            <span className="dash-section-icon">🎯</span>
            Category Distribution
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={category_distribution}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={4}
                dataKey="value"
                stroke="none"
              >
                {category_distribution.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#fff', border: '1px solid #f1f5f9', borderRadius: 12, boxShadow: '0 10px 25px rgba(0,0,0,0.08)' }}
              />
              <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Radar Chart */}
        {radarData.length >= 3 && (
          <div className="dash-overview-card">
            <h3 className="dash-section-title">
              <span className="dash-section-icon">🕸️</span>
              Metric Health Radar
            </h3>
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={radarData} cx="50%" cy="50%" outerRadius={90}>
                <PolarGrid stroke="#e2e8f0" />
                <PolarAngleAxis dataKey="metric" tick={{ fontSize: 9, fill: '#64748b' }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 9 }} />
                <Radar name="Health Score" dataKey="value" stroke="#ef4444" fill="#ef4444" fillOpacity={0.15} strokeWidth={2} />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Individual Metric Charts */}
      <div className="dash-section-header">
        <h2>
          <span className="dash-section-icon">📊</span>
          Metric Deep Dive
        </h2>
        <p>Individual trend analysis for each discovered metric</p>
      </div>

      <div className="dash-charts-grid">
        {charts.map((chart, i) => (
          <MetricChart key={chart.id} chart={chart} index={i} />
        ))}
      </div>

      {/* Footer with Metabase link */}
      {data.metabase_url && (
        <div className="dash-footer-cta">
          <div className="dash-footer-content">
            <div>
              <h3>Want more advanced analytics?</h3>
              <p>Open in Metabase for SQL queries, custom filters, and interactive drill-downs</p>
            </div>
            <a
              href={data.metabase_url}
              target="_blank"
              rel="noopener noreferrer"
              className="dash-btn dash-btn-metabase-lg"
            >
              Open Metabase Dashboard
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                <path d="M7 17L17 7" />
                <path d="M7 7h10v10" />
              </svg>
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
