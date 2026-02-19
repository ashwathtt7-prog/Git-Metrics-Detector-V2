import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer } from 'recharts';
import { CATEGORY_COLORS } from './colors';

interface Props {
  data: { metric: string; category: string; value: number; display_value: string }[];
}

export default function MetricEntriesChart({ data }: Props) {
  // Filter out any entries with invalid values
  const validData = (data || []).map(d => ({
    ...d,
    value: typeof d.value === 'number' && !isNaN(d.value) ? d.value : 0
  })).filter(d => d.metric);

  if (!validData.length) return <div className="no-data">No metrics data available</div>;

  return (
    <ResponsiveContainer width="100%" height={Math.max(250, validData.length * 40)}>
      <BarChart data={validData} layout="vertical" margin={{ left: 20, right: 30 }}>
        <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 12 }} hide={false} />
        <YAxis
          type="category"
          dataKey="metric"
          tick={{ fill: '#94a3b8', fontSize: 11 }}
          width={180}
        />
        <Tooltip
          contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0' }}
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={24}>
          {validData.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={CATEGORY_COLORS[entry.category] || '#6b7280'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
