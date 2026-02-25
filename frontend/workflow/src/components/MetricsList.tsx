import { useState } from 'react';
import type { Metric } from '../types';
import MetricCard from './MetricCard';
import MetricDetailModal from './MetricDetailModal';

interface Props {
  metrics: Metric[];
}

export default function MetricsList({ metrics }: Props) {
  const [selectedMetric, setSelectedMetric] = useState<Metric | null>(null);

  if (metrics.length === 0) {
    return <p className="no-metrics">No metrics discovered.</p>;
  }

  return (
    <div className="metrics-section">
      <div className="metrics-grid">
        {metrics.map((m) => (
          <MetricCard
            key={m.id}
            metric={m}
            onClick={() => setSelectedMetric(m)}
          />
        ))}
      </div>

      {selectedMetric && (
        <MetricDetailModal
          metric={selectedMetric}
          onClose={() => setSelectedMetric(null)}
        />
      )}
    </div>
  );
}
