import { useEffect, useState } from 'react';
import WorkspaceList from '../components/WorkspaceList';
import { listWorkspaces, deleteWorkspace, generateMockData } from '../api/dashboardApi';
import type { Workspace } from '../types';

export default function DashboardHome() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [generatingId, setGeneratingId] = useState<string | null>(null);

  const fetchWorkspaces = async () => {
    try {
      setError(null);
      setNotice(null);
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

  const handleGenerateMockData = async (id: string) => {
    setGeneratingId(id);
    setNotice(null);
    try {
      const res = await generateMockData(id);
      await fetchWorkspaces();
      if (res?.metabase_error && !res?.metabase_url) {
        setNotice(`Mock data generated, but Metabase setup failed: ${res.metabase_error}`);
      } else {
        setNotice('Mock data generated successfully.');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate mock data');
    } finally {
      setGeneratingId(null);
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

      {notice && <div className="notice-message">{notice}</div>}
      {loading ? (
        <div className="loading">Loading workspaces...</div>
      ) : error ? (
        <div className="error-message">{error}</div>
      ) : (
        <WorkspaceList
          workspaces={workspaces}
          onDelete={handleDelete}
          onGenerateMockData={handleGenerateMockData}
          isGenerating={(id) => generatingId === id}
        />
      )}
    </div>
  );
}
