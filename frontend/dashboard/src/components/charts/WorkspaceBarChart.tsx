import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { CATEGORY_COLORS, CATEGORY_LIST } from './colors';

interface Props {
  data: { workspace: string; category: string; count: number }[];
}

export default function WorkspaceBarChart({ data }: Props) {
  if (!data.length) return <div className="no-data">No data</div>;

  // Pivot data: group by workspace, stack by category
  const workspaceMap = new Map<string, Record<string, number>>();
  for (const row of data) {
    if (!workspaceMap.has(row.workspace)) {
      workspaceMap.set(row.workspace, { workspace: row.workspace } as any);
    }
    const entry = workspaceMap.get(row.workspace)!;
    entry[row.category] = row.count;
  }
  const pivoted = Array.from(workspaceMap.values());

  // Determine which categories are present
  const cats = CATEGORY_LIST.filter((c) =>
    data.some((d) => d.category === c)
  );

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={pivoted}>
        <XAxis
          dataKey="workspace"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          angle={-20}
          textAnchor="end"
          height={60}
        />
        <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
        <Tooltip
          contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0' }}
        />
        <Legend />
        {cats.map((cat) => (
          <Bar
            key={cat}
            dataKey={cat}
            stackId="a"
            fill={CATEGORY_COLORS[cat]}
            name={cat}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
