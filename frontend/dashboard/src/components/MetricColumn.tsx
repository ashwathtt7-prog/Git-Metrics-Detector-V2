import { useState, useEffect } from 'react';
import type { Metric, MetricEntry } from '../types';
import { getMetricEntries, addMetricEntry } from '../api/dashboardApi';

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
  const [entries, setEntries] = useState<MetricEntry[]>([]);
  const [newValue, setNewValue] = useState('');
  const [newNotes, setNewNotes] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getMetricEntries(metric.id).then(setEntries).catch(() => {});
  }, [metric.id]);

  const handleAdd = async () => {
    if (!newValue.trim()) return;
    setLoading(true);
    try {
      const entry = await addMetricEntry(metric.id, newValue.trim(), newNotes.trim() || undefined);
      setEntries([entry, ...entries]);
      setNewValue('');
      setNewNotes('');
      setShowAdd(false);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

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
        <span className="col-type">Type: {metric.data_type}</span>
        {metric.suggested_source && (
          <p className="col-source">Source: {metric.suggested_source}</p>
        )}
      </div>

      <div className="column-entries">
        {entries.length === 0 && !showAdd && (
          <p className="no-entries">No data yet</p>
        )}
        {entries.map((e) => (
          <div key={e.id} className="entry-item">
            <span className="entry-value">{e.value}</span>
            <span className="entry-date">
              {new Date(e.recorded_at).toLocaleDateString()}
            </span>
            {e.notes && <span className="entry-notes">{e.notes}</span>}
          </div>
        ))}
      </div>

      {showAdd ? (
        <div className="add-entry-form">
          <input
            type="text"
            placeholder="Value"
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            disabled={loading}
          />
          <input
            type="text"
            placeholder="Notes (optional)"
            value={newNotes}
            onChange={(e) => setNewNotes(e.target.value)}
            disabled={loading}
          />
          <div className="add-entry-actions">
            <button onClick={handleAdd} disabled={loading || !newValue.trim()} className="btn-save">
              {loading ? '...' : 'Save'}
            </button>
            <button onClick={() => setShowAdd(false)} className="btn-cancel">Cancel</button>
          </div>
        </div>
      ) : (
        <button className="btn-add-entry" onClick={() => setShowAdd(true)}>
          + Add Entry
        </button>
      )}
    </div>
  );
}
