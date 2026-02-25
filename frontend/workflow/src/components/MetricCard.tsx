import type { Metric } from '../types';

interface Props {
  metric: Metric;
  onClick?: () => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  business: '#2563eb',
  engagement: '#7c3aed',
  content: '#059669',
  performance: '#d97706',
  growth: '#dc2626',
};

export default function MetricCard({ metric, onClick }: Props) {
  const color = CATEGORY_COLORS[metric.category || ''] || '#6b7280';

  return (
    <div className="metric-card" onClick={onClick} title="Click for detailed insights">
      <div className="metric-card-header">
        <h3>{metric.name}</h3>
        <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
          {metric.category && (
            <span className="category-badge" style={{ backgroundColor: color }}>
              {metric.category}
            </span>
          )}
        </div>
      </div>
      {metric.description && (
        <p className="metric-description">{metric.description}</p>
      )}
      <div className="metric-meta">
        {metric.suggested_source && (
          <p className="suggested-source">
            <strong>Source:</strong> {metric.suggested_source}
          </p>
        )}
        {(metric.source_table || metric.source_platform) && (
          <div className="source-details">
            {metric.source_platform && (
              <span className="source-platform-badge">
                {metric.source_platform}
              </span>
            )}
            {metric.source_table && (
              <span className="source-table-badge">
                {metric.source_table}
              </span>
            )}
          </div>
        )}
      </div>

      {metric.entries && metric.entries.length > 0 && (
        <div style={{ marginTop: '1.5rem', borderTop: '1px solid #f1f5f9', paddingTop: '1rem' }}>
          <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <span style={{ fontSize: '1rem' }}>{metric.entries[0].value}</span>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 500 }}>
              {new Date(metric.entries[0].recorded_at).toLocaleDateString()}
            </span>
          </div>
          <p style={{ fontSize: '0.75rem', fontStyle: 'italic', color: '#64748b', marginTop: '0.2rem' }}>
            Initial analysis estimate
          </p>
        </div>
      )}
    </div>
  );
}
