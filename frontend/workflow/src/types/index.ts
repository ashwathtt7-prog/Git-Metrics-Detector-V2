export interface Job {
  id: string;
  repo_url: string;
  repo_owner: string;
  repo_name: string;
  status: 'pending' | 'fetching' | 'analyzing' | 'completed' | 'failed';
  error_message?: string;
  total_files: number;
  analyzed_files: number;
  created_at: string;
  completed_at?: string;
  workspace_id?: string;
  progress_message?: string;
  current_stage: number;
  logs?: string;
}

export interface Metric {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  category?: string;
  data_type: string;
  suggested_source?: string;
  source_table?: string;
  source_platform?: string;
  display_order: number;
  created_at: string;
  entries?: MetricEntry[];
}

export interface MetricEntry {
  id: string;
  metric_id: string;
  value: string;
  recorded_at: string;
  notes?: string;
}

export interface JobMetrics {
  job: Job;
  metrics: Metric[];
  workspace_id?: string;
}

export interface GitHubRepo {
  full_name: string;
  html_url: string;
  description: string;
  private: boolean;
  updated_at: string;
}
