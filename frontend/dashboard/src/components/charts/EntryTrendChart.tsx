import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

interface Props {
  data: { date: string; count: number }[];
}

export default function EntryTrendChart({ data }: Props) {
  if (!data.length) return <div className="no-data">No entries recorded yet</div>;

  return (
    <ResponsiveContainer width="100%" height={250}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="entryGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#60a5fa" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} />
        <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
        <Tooltip
          contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0' }}
        />
        <Area
          type="monotone"
          dataKey="count"
          stroke="#60a5fa"
          fill="url(#entryGradient)"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
