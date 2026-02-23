import type { Workspace, WorkspaceDetail, MetricEntry } from '../types';

const BASE = '/api/dashboard';
const WORKFLOW_BASE = '/api/workflow';

// --- Analytics Types ---

export interface AnalyticsOverview {
  totals: { workspaces: number; metrics: number; entries: number };
  category_distribution: { category: string; count: number }[];
  datatype_distribution: { data_type: string; count: number }[];
  workspace_metrics: { workspace: string; category: string; count: number }[];
  entry_trends: { date: string; count: number }[];
  job_stats: { status: string; count: number }[];
}

export interface WorkspaceAnalytics {
  category_distribution: { category: string; count: number }[];
  datatype_distribution: { data_type: string; count: number }[];
  metric_values: {
    metric: string;
    category: string;
    value: number;
    display_value: string;
  }[];
}

export async function getAnalyticsOverview(): Promise<AnalyticsOverview> {
  const res = await fetch(`${BASE}/analytics/overview`);
  if (!res.ok) throw new Error('Failed to fetch analytics');
  return res.json();
}

export async function getWorkspaceAnalytics(id: string): Promise<WorkspaceAnalytics> {
  const res = await fetch(`${BASE}/analytics/workspace/${id}`);
  if (!res.ok) throw new Error('Failed to fetch workspace analytics');
  return res.json();
}

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

export async function generateMockData(workspaceId: string): Promise<any> {
  const res = await fetch(`${WORKFLOW_BASE}/workspaces/${workspaceId}/mock-data`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to generate mock data');
  return res.json();
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
