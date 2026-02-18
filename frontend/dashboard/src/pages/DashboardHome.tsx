import { useEffect, useState } from 'react';
import WorkspaceList from '../components/WorkspaceList';
import { listWorkspaces, deleteWorkspace } from '../api/dashboardApi';
import type { Workspace } from '../types';

const SUPERSET_URL = 'http://localhost:8088';

export default function DashboardHome() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<'workspaces' | 'superset'>('workspaces');

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
        <h1>Dashboard</h1>
        <div className="header-actions">
          <a href="http://localhost:3000" className="btn-workflow-link">
            + Analyze New Repo
          </a>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="tab-nav">
        <button
          className={`tab-btn ${view === 'workspaces' ? 'active' : ''}`}
          onClick={() => setView('workspaces')}
        >
          📊 Workspaces
        </button>
        <button
          className={`tab-btn ${view === 'superset' ? 'active' : ''}`}
          onClick={() => setView('superset')}
        >
          📈 Superset Analytics
        </button>
        <a
          href={SUPERSET_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="tab-btn superset-external"
          title="Open Superset in new tab"
        >
          🔗 Open Superset ↗
        </a>
      </div>

      {view === 'workspaces' ? (
        loading ? (
          <div className="loading">Loading workspaces...</div>
        ) : error ? (
          <div className="error-message">{error}</div>
        ) : (
          <WorkspaceList workspaces={workspaces} onDelete={handleDelete} />
        )
      ) : (
        <div className="superset-container">
          <div className="superset-info">
            <h2>Apache Superset Analytics</h2>
            <p>
              Explore your Git metrics with interactive charts, dashboards, and SQL queries
              powered by Apache Superset.
            </p>
            <div className="superset-features">
              <div className="feature-card">
                <span className="feature-icon">📊</span>
                <h3>Interactive Charts</h3>
                <p>Create bar charts, line graphs, pie charts, and more from your metrics data.</p>
              </div>
              <div className="feature-card">
                <span className="feature-icon">🗂️</span>
                <h3>Custom Dashboards</h3>
                <p>Build and share dashboards that combine multiple visualizations.</p>
              </div>
              <div className="feature-card">
                <span className="feature-icon">🔍</span>
                <h3>SQL Lab</h3>
                <p>Write SQL queries directly against your metrics database for advanced analysis.</p>
              </div>
              <div className="feature-card">
                <span className="feature-icon">📤</span>
                <h3>Export & Share</h3>
                <p>Export charts as images, download data as CSV, or share dashboards.</p>
              </div>
            </div>
          </div>

          <div className="superset-embed-wrapper">
            <iframe
              src={SUPERSET_URL}
              className="superset-iframe"
              title="Apache Superset"
              allow="fullscreen"
            />
          </div>

          <div className="superset-help">
            <h3>Getting Started with Superset</h3>
            <ol>
              <li>Login with <strong>admin / admin</strong></li>
              <li>Go to <strong>Settings → Database Connections</strong></li>
              <li>Add a new <strong>SQLite</strong> database with your metrics.db path</li>
              <li>Create charts from the <strong>workspaces</strong>, <strong>metrics</strong>, and <strong>metric_entries</strong> tables</li>
              <li>Build dashboards by combining your charts</li>
            </ol>
          </div>
        </div>
      )}
    </div>
  );
}
