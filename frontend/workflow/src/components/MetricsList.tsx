import type { Metric } from '../types';
import MetricCard from './MetricCard';

interface Props {
  metrics: Metric[];
}

export default function MetricsList({ metrics }: Props) {
  if (metrics.length === 0) {
    return <p className="no-metrics">No metrics discovered.</p>;
  }

  return (
    <div className="metrics-section">

      <div className="metrics-grid">
        {metrics.map((m) => (
          <MetricCard key={m.id} metric={m} />
        ))}
      </div>
    </div>
  );
}
