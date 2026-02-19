import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer } from 'recharts';
import { CATEGORY_COLORS } from './colors';

interface Props {
  data: { metric: string; category: string; entries: number }[];
}

export default function MetricEntriesChart({ data }: Props) {
  if (!data.length) return <div className="no-data">No metrics</div>;

  return (
    <ResponsiveContainer width="100%" height={Math.max(250, data.length * 32)}>
      <BarChart data={data} layout="vertical" margin={{ left: 20 }}>
        <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 12 }} />
        <YAxis
          type="category"
          dataKey="metric"
          tick={{ fill: '#94a3b8', fontSize: 11 }}
          width={180}
        />
        <Tooltip
          contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0' }}
        />
        <Bar dataKey="entries" radius={[0, 4, 4, 0]}>
          {data.map((entry) => (
            <Cell
              key={entry.metric}
              fill={CATEGORY_COLORS[entry.category] || '#6b7280'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
