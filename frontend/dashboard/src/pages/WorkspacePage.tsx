import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import MetricColumn from '../components/MetricColumn';
import { getWorkspace, generateMockData } from '../api/dashboardApi';
import type { WorkspaceDetail } from '../types';

export default function WorkspacePage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const [workspace, setWorkspace] = useState<WorkspaceDetail | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);

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

  let metabaseUrl: string | null = workspace.metabase_url || null;
  if (workspace.dashboard_config) {
    try {
      const parsed = JSON.parse(workspace.dashboard_config);
      if (parsed?.metabase_url) metabaseUrl = parsed.metabase_url;
      if (!metabaseUrl && parsed?.plan?.metabase_url) metabaseUrl = parsed.plan.metabase_url;
    } catch {}
  }

  const handleGenerate = async () => {
    if (!workspaceId) return;
    setGenerating(true);
    setNotice(null);
    try {
      const res = await generateMockData(workspaceId);
      const updated = await getWorkspace(workspaceId);
      setWorkspace(updated);
      if (res?.metabase_error && !res?.metabase_url) {
        setNotice(`Mock data generated, but Metabase setup failed: ${res.metabase_error}`);
      } else {
        setNotice('Mock data generated successfully.');
      }
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Failed to generate mock data');
    } finally {
      setGenerating(false);
    }
  };

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

      {notice && <div className="notice-message">{notice}</div>}

      {!workspace.has_mock_data ? (
        <div style={{ margin: '0.75rem 0 1rem' }}>
          <div style={{ marginBottom: '0.5rem', color: '#64748b' }}>
            Mock data has not been generated for this workspace yet.
          </div>
          <button className="btn-generate" type="button" onClick={handleGenerate} disabled={generating}>
            {generating ? 'Generating...' : 'Generate mock data'}
          </button>
        </div>
      ) : metabaseUrl ? (
        <div style={{ margin: '0.75rem 0 1rem' }}>
          <a className="btn-metabase" href={metabaseUrl} target="_blank" rel="noreferrer">
            Open in Metabase
          </a>
        </div>
      ) : null}

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
