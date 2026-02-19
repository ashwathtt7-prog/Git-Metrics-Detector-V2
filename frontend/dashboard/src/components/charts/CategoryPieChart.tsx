import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { CATEGORY_COLORS } from './colors';

interface Props {
  data: { category: string; count: number }[];
}

export default function CategoryPieChart({ data }: Props) {
  if (!data.length) return <div className="no-data">No data</div>;

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={100}
          dataKey="count"
          nameKey="category"
          paddingAngle={2}
          label={({ category, count }) => `${category}: ${count}`}
        >
          {data.map((entry) => (
            <Cell
              key={entry.category}
              fill={CATEGORY_COLORS[entry.category] || '#6b7280'}
            />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0' }}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
