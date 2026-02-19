interface Props {
  workspaces: number;
  metrics: number;
  entries: number;
}

export default function KpiCards({ workspaces, metrics, entries }: Props) {
  const cards = [
    { label: 'Workspaces', value: workspaces },
    { label: 'Metrics', value: metrics },
    { label: 'Data Entries', value: entries },
  ];

  return (
    <div className="kpi-row">
      {cards.map((c) => (
        <div key={c.label} className="kpi-card">
          <div className="kpi-value">{c.value.toLocaleString()}</div>
          <div className="kpi-label">{c.label}</div>
        </div>
      ))}
    </div>
  );
}
