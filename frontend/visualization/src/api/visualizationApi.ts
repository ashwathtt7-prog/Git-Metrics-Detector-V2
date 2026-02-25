const BASE = '/api/workflow';

export async function getDashboardData(workspaceId: string): Promise<any> {
  const res = await fetch(`${BASE}/workspaces/${workspaceId}/dashboard-data`);
  if (!res.ok) throw new Error('Failed to fetch dashboard data');
  return res.json();
}
