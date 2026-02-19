import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import MetricColumn from '../components/MetricColumn';
import { getWorkspace, getWorkspaceAnalytics } from '../api/dashboardApi';
import type { WorkspaceDetail } from '../types';
import type { WorkspaceAnalytics } from '../api/dashboardApi';
import CategoryPieChart from '../components/charts/CategoryPieChart';
import DataTypeBarChart from '../components/charts/DataTypeBarChart';
import MetricEntriesChart from '../components/charts/MetricEntriesChart';

type Tab = 'metrics' | 'charts';

export default function WorkspacePage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const [workspace, setWorkspace] = useState<WorkspaceDetail | null>(null);
  const [analytics, setAnalytics] = useState<WorkspaceAnalytics | null>(null);
  const [tab, setTab] = useState<Tab>('metrics');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!workspaceId) return;
    getWorkspace(workspaceId)
      .then(setWorkspace)
      .catch(() => setError('Workspace not found'));
    getWorkspaceAnalytics(workspaceId)
      .then(setAnalytics)
      .catch(() => {});
  }, [workspaceId]);

  if (error) {
    return (
      <div className="workspace-page">
        <div className="error-banner">{error}</div>
        <button onClick={() => navigate('/')} className="btn-back">Back to Dashboard</button>
      </div>
    );
  }

  if (!workspace) {
    return <div className="loading">Loading workspace...</div>;
  }

  return (
    <div className="workspace-page">
      <button onClick={() => navigate('/')} className="btn-back">
        &larr; All Workspaces
      </button>

      <div className="workspace-header">
        <h1>{workspace.name}</h1>
        <a href={workspace.repo_url} target="_blank" rel="noopener noreferrer" className="repo-link">
          View Repository
        </a>
      </div>

      {workspace.description && (
        <p className="workspace-description">{workspace.description}</p>
      )}

      <div className="metrics-count">
        {workspace.metrics.length} metric{workspace.metrics.length !== 1 ? 's' : ''} discovered
      </div>

      <div className="tab-nav">
        <button
          className={`tab-btn ${tab === 'metrics' ? 'active' : ''}`}
          onClick={() => setTab('metrics')}
        >
          Metrics
        </button>
        <button
          className={`tab-btn ${tab === 'charts' ? 'active' : ''}`}
          onClick={() => setTab('charts')}
        >
          Charts
        </button>
      </div>

      {tab === 'metrics' && (
        <div className="metrics-columns">
          {workspace.metrics.map((m) => (
            <MetricColumn key={m.id} metric={m} />
          ))}
        </div>
      )}

      {tab === 'charts' && analytics && (
        <div>
          <div className="chart-row">
            <div className="chart-card">
              <h3>Category Distribution</h3>
              <CategoryPieChart data={analytics.category_distribution} />
            </div>
            <div className="chart-card">
              <h3>Data Types</h3>
              <DataTypeBarChart data={analytics.datatype_distribution} />
            </div>
          </div>
          <div className="chart-row">
            <div className="chart-card chart-full-width">
              <h3>Entries per Metric</h3>
              <MetricEntriesChart data={analytics.metric_entry_counts} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
