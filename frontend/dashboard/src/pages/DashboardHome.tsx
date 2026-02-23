import { useEffect, useState } from 'react';
import WorkspaceList from '../components/WorkspaceList';
import { listWorkspaces, deleteWorkspace } from '../api/dashboardApi';
import type { Workspace } from '../types';

export default function DashboardHome() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchWorkspaces = async () => {
    try {
      setError(null);
      const data = await listWorkspaces();
      setWorkspaces(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load workspaces');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchWorkspaces(); }, []);

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this workspace and all its metrics?')) return;
    try {
      await deleteWorkspace(id);
      setWorkspaces(workspaces.filter((w) => w.id !== id));
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to delete workspace');
    }
  };

  return (
    <div className="dashboard-home">
      <div className="dashboard-header">
        <h1>Workspaces</h1>
        <div className="header-actions">
          <a href="http://localhost:3001" className="btn-workflow-link">
            + Analyze New Repo
          </a>
        </div>
      </div>

      {loading ? (
        <div className="loading">Loading workspaces...</div>
      ) : error ? (
        <div className="error-message">{error}</div>
      ) : (
        <WorkspaceList workspaces={workspaces} onDelete={handleDelete} />
      )}
    </div>
  );
}
