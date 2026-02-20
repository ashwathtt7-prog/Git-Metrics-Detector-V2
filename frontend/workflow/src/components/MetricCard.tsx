import type { Metric } from '../types';

interface Props {
  metric: Metric;
}

const CATEGORY_COLORS: Record<string, string> = {
  business: '#2563eb',
  engagement: '#7c3aed',
  content: '#059669',
  performance: '#d97706',
  growth: '#dc2626',
};

export default function MetricCard({ metric }: Props) {
  const color = CATEGORY_COLORS[metric.category || ''] || '#6b7280';

  return (
    <div className="metric-card">
      <div className="metric-card-header">
        <h3>{metric.name}</h3>
        {metric.category && (
          <span className="category-badge" style={{ backgroundColor: color }}>
            {metric.category}
          </span>
        )}
      </div>
      {metric.description && (
        <p className="metric-description">{metric.description}</p>
      )}
      <div className="metric-meta">
        <span className="data-type">Type: {metric.data_type}</span>
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
    </div>
  );
}
