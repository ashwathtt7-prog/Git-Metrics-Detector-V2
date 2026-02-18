export interface Workspace {
  id: string;
  name: string;
  repo_url: string;
  description?: string;
  created_at: string;
  updated_at: string;
  metric_count: number;
}

export interface Metric {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  category?: string;
  data_type: string;
  suggested_source?: string;
  display_order: number;
  created_at: string;
}

export interface WorkspaceDetail {
  id: string;
  name: string;
  repo_url: string;
  description?: string;
  created_at: string;
  updated_at: string;
  metrics: Metric[];
}

export interface MetricEntry {
  id: string;
  metric_id: string;
  value?: string;
  recorded_at: string;
  notes?: string;
}
