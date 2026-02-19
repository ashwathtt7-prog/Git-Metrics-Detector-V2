import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import WorkspaceList from '../components/WorkspaceList';
import { listWorkspaces, deleteWorkspace } from '../api/dashboardApi';
import type { Workspace } from '../types';

export default function DashboardHome() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchWorkspaces = async () => {
    try {
      const data = await listWorkspaces();
      setWorkspaces(data);
    } catch {
      // ignore
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
    } catch {
      // ignore
    }
  };

  return (
    <div className="dashboard-home">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <div className="header-actions">
          <Link to="/analytics" className="btn-analytics-link">
            Analytics
          </Link>
          <a href="http://localhost:3000" className="btn-workflow-link">
            + Analyze New Repo
          </a>
        </div>
      </div>

      {loading ? (
        <div className="loading">Loading workspaces...</div>
      ) : (
        <WorkspaceList workspaces={workspaces} onDelete={handleDelete} />
      )}
    </div>
  );
}
