import type { Workspace, WorkspaceDetail, MetricEntry } from '../types';

const BASE = '/api/dashboard';

export async function listWorkspaces(): Promise<Workspace[]> {
  const res = await fetch(`${BASE}/workspaces`);
  if (!res.ok) throw new Error('Failed to fetch workspaces');
  return res.json();
}

export async function getWorkspace(id: string): Promise<WorkspaceDetail> {
  const res = await fetch(`${BASE}/workspaces/${id}`);
  if (!res.ok) throw new Error('Workspace not found');
  return res.json();
}

export async function deleteWorkspace(id: string): Promise<void> {
  const res = await fetch(`${BASE}/workspaces/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete workspace');
}

export async function getMetricEntries(metricId: string): Promise<MetricEntry[]> {
  const res = await fetch(`${BASE}/metrics/${metricId}/entries`);
  if (!res.ok) throw new Error('Failed to fetch entries');
  return res.json();
}

export async function addMetricEntry(
  metricId: string,
  value: string,
  notes?: string
): Promise<MetricEntry> {
  const res = await fetch(`${BASE}/metrics/${metricId}/entries`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value, notes: notes || null }),
  });
  if (!res.ok) throw new Error('Failed to add entry');
  return res.json();
}
