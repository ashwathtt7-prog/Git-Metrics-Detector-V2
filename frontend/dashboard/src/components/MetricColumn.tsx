import { useState, useEffect } from 'react';
import type { Metric, MetricEntry } from '../types';
import { getMetricEntries } from '../api/dashboardApi';

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

export default function MetricColumn({ metric }: Props) {
  const [entries, setEntries] = useState<MetricEntry[]>(metric.entries || []);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!metric.entries || metric.entries.length === 0) {
      getMetricEntries(metric.id).then(setEntries).catch((e) => {
        setError(e instanceof Error ? e.message : 'Failed to load entries');
      });
    } else {
      setEntries(metric.entries);
    }
  }, [metric.id, metric.entries]);

  const color = CATEGORY_COLORS[metric.category || ''] || '#6b7280';

  return (
    <div className="metric-column">
      <div className="column-header">
        <h3 className="column-title">{metric.name}</h3>
        {metric.category && (
          <span className="col-category" style={{ backgroundColor: color }}>
            {metric.category}
          </span>
        )}
      </div>

      {metric.description && (
        <p className="column-desc">{metric.description}</p>
      )}

      <div className="column-meta">
        {metric.suggested_source && (
          <p className="col-source">Source: {metric.suggested_source}</p>
        )}
      </div>

      {error && <div className="error-message" style={{ color: '#dc2626', fontSize: '0.85rem', margin: '0.5rem 0' }}>{error}</div>}

      <div className="column-entries">
        {entries.length > 0 ? (
          <div className="latest-entry-highlight" style={{ marginTop: '1rem', borderTop: '1px solid #f1f5f9', paddingTop: '1rem' }}>
            <div style={{ fontSize: '1rem', fontWeight: 700, color: '#1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <span>{entries[0].value}</span>
              <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 500 }}>
                {new Date(entries[0].recorded_at).toLocaleDateString()}
              </span>
            </div>
            <p style={{ fontSize: '0.75rem', fontStyle: 'italic', color: '#64748b', marginTop: '0.2rem' }}>
              Initial analysis estimate
            </p>
          </div>
        ) : (
          !error && <p className="no-entries">No data yet</p>
        )}
      </div>
    </div>
  );
}
