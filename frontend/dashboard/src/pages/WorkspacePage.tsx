import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import MetricColumn from '../components/MetricColumn';
import { getWorkspace } from '../api/dashboardApi';
import type { WorkspaceDetail } from '../types';

export default function WorkspacePage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const [workspace, setWorkspace] = useState<WorkspaceDetail | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!workspaceId) {
      navigate('/');
      return;
    }
    getWorkspace(workspaceId)
      .then(setWorkspace)
      .catch(() => setError('Workspace not found'));
  }, [workspaceId, navigate]);

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

      <div className="metrics-columns">
        {workspace.metrics.map((m) => (
          <MetricColumn key={m.id} metric={m} />
        ))}
      </div>
    </div>
  );
}
