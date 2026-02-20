import type { Job, JobMetrics } from '../types';

const BASE = '/api/workflow';

export async function startAnalysis(repoUrl: string, githubToken?: string, force: boolean = false): Promise<Job> {
  const res = await fetch(`${BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      repo_url: repoUrl,
      github_token: githubToken,
      force: force
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to start analysis' }));
    if (res.status === 409) {
      // Create a persistent error object with extra fields
      const error = new Error(err.detail.message || 'Already analyzed') as any;
      error.status = 409;
      error.jobId = err.detail.job_id;
      error.workspaceId = err.detail.workspace_id;
      throw error;
    }
    throw new Error(err.detail || 'Failed to start analysis');
  }
  return res.json();
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(`${BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error('Job not found');
  return res.json();
}

export async function getJobMetrics(jobId: string): Promise<JobMetrics> {
  const res = await fetch(`${BASE}/jobs/${jobId}/metrics`);
  if (!res.ok) throw new Error('Failed to fetch metrics');
  return res.json();
}

export async function listJobs(): Promise<Job[]> {
  const res = await fetch(`${BASE}/jobs`);
  if (!res.ok) throw new Error('Failed to fetch jobs');
  return res.json();
}

export interface GitHubRepo {
  full_name: string;
  html_url: string;
  description: string;
  private: boolean;
  updated_at: string;
}

export async function listUserRepos(token: string): Promise<GitHubRepo[]> {
  const res = await fetch(`${BASE}/repos?token=${encodeURIComponent(token)}`);
  if (!res.ok) throw new Error('Failed to fetch repos');
  return res.json();
}
export async function generateMockData(workspaceId: string): Promise<any> {
  const res = await fetch(`${BASE}/workspaces/${workspaceId}/mock-data`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to generate mock data');
  return res.json();
}

export async function getMetabasePlan(workspaceId: string): Promise<any> {
  const res = await fetch(`${BASE}/workspaces/${workspaceId}/metabase-plan`);
  if (!res.ok) throw new Error('Failed to fetch Metabase plan');
  return res.json();
}
