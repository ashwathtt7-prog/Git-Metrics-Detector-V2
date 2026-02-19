import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

interface Props {
  data: { data_type: string; count: number }[];
}

export default function DataTypeBarChart({ data }: Props) {
  if (!data.length) return <div className="no-data">No data</div>;

  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={data} layout="vertical">
        <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 12 }} />
        <YAxis
          type="category"
          dataKey="data_type"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          width={100}
        />
        <Tooltip
          contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0' }}
        />
        <Bar dataKey="count" fill="#a78bfa" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
