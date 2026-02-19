import { useEffect, useState, Suspense, lazy } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAnalyticsOverview, getWorkspaceAnalytics, listWorkspaces, getWorkspace } from '../api/dashboardApi';
import type { AnalyticsOverview, WorkspaceAnalytics } from '../api/dashboardApi';
import type { Workspace, WorkspaceDetail } from '../types';
import KpiCards from '../components/charts/KpiCards';
import CategoryPieChart from '../components/charts/CategoryPieChart';
import WorkspaceBarChart from '../components/charts/WorkspaceBarChart';
import EntryTrendChart from '../components/charts/EntryTrendChart';
import DataTypeBarChart from '../components/charts/DataTypeBarChart';
import MetricEntriesChart from '../components/charts/MetricEntriesChart';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

// 1. Import all dashboard files dynamically
const dashboardModules = import.meta.glob('../dashboards/Workspace_*.tsx');

type Tab = 'overview' | 'workspace';

export default function AnalyticsPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>('overview');
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWsId, setSelectedWsId] = useState('');
  const [selectedWsDetail, setSelectedWsDetail] = useState<WorkspaceDetail | null>(null);
  const [wsAnalytics, setWsAnalytics] = useState<WorkspaceAnalytics | null>(null);
  const [loading, setLoading] = useState(true);

  // 2. State for the dynamically loaded component
  const [CustomDashboard, setCustomDashboard] = useState<React.ComponentType<{ metrics: any[] }> | null>(null);

  useEffect(() => {
    Promise.all([getAnalyticsOverview(), listWorkspaces()])
      .then(([ov, ws]) => {
        setOverview(ov);
        setWorkspaces(ws);
        if (ws.length > 0) setSelectedWsId(ws[0].id);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selectedWsId) {
      // Fetch both detail and analytics
      Promise.all([
        getWorkspace(selectedWsId),
        getWorkspaceAnalytics(selectedWsId)
      ]).then(([detail, analytics]) => {
        setSelectedWsDetail(detail);
        setWsAnalytics(analytics);

        // 3. Try to load custom dashboard
        const path = `../dashboards/Workspace_${selectedWsId}.tsx`;
        if (dashboardModules[path]) {
          dashboardModules[path]().then((mod: any) => {
            setCustomDashboard(() => mod.default);
          }).catch(err => {
            console.error("Failed to load custom dashboard component:", err);
            setCustomDashboard(null);
          });
        } else {
          setCustomDashboard(null);
        }
      });
    }
  }, [selectedWsId]);

  if (loading) return <div className="loading">Loading analytics...</div>;
  if (!overview) return <div className="error-banner">Failed to load analytics</div>;

  return (
    <div className="analytics-page">
      <div className="dashboard-header">
        <h1>Analytics</h1>
        <div className="header-actions">
          <button onClick={() => navigate('/')} className="btn-back">
            &larr; Dashboard
          </button>
        </div>
      </div>

      <KpiCards
        workspaces={overview.totals.workspaces}
        metrics={overview.totals.metrics}
        entries={overview.totals.entries}
      />

      <div className="tab-nav">
        <button
          className={`tab-btn ${tab === 'overview' ? 'active' : ''}`}
          onClick={() => setTab('overview')}
        >
          Overview
        </button>
        <button
          className={`tab-btn ${tab === 'workspace' ? 'active' : ''}`}
          onClick={() => setTab('workspace')}
        >
          Workspace Drill-Down
        </button>
      </div>

      {tab === 'overview' && (
        <div>
          <div className="chart-row">
            <div className="chart-card">
              <h3>Metrics by Category</h3>
              <CategoryPieChart data={overview.category_distribution} />
            </div>
            <div className="chart-card">
              <h3>Data Types</h3>
              <DataTypeBarChart data={overview.datatype_distribution} />
            </div>
          </div>

          <div className="chart-row">
            <div className="chart-card chart-full-width">
              <h3>Metrics per Workspace</h3>
              <WorkspaceBarChart data={overview.workspace_metrics} />
            </div>
          </div>

          <div className="chart-row">
            <div className="chart-card chart-full-width">
              <h3>Entry Activity Over Time</h3>
              <EntryTrendChart data={overview.entry_trends} />
            </div>
          </div>
        </div>
      )}

      {tab === 'workspace' && (
        <div>
          <div className="filter-bar">
            <label>Workspace:</label>
            <select
              value={selectedWsId}
              onChange={(e) => setSelectedWsId(e.target.value)}
            >
              {workspaces.map((ws) => (
                <option key={ws.id} value={ws.id}>
                  {ws.name}
                </option>
              ))}
            </select>
          </div>

          {wsAnalytics && (
            <div className="workspace-content">
              {/* If custom dashboard component exists, render it with fallback to default view */}
              {CustomDashboard ? (
                <Suspense fallback={<div>Loading custom dashboard...</div>}>
                  <CustomDashboard metrics={wsAnalytics.metric_values} />
                </Suspense>
              ) : (
                /* Default/Fallback View */
                <>
                  <div className="chart-row">
                    <div className="chart-card">
                      <h3>Category Distribution</h3>
                      <CategoryPieChart data={wsAnalytics.category_distribution} />
                    </div>
                    <div className="chart-card">
                      <h3>Data Types</h3>
                      <DataTypeBarChart data={wsAnalytics.datatype_distribution} />
                    </div>
                  </div>
                  <div className="chart-row">
                    <div className="chart-card chart-full-width">
                      <h3>Metric Values</h3>
                      <MetricEntriesChart data={wsAnalytics.metric_values} />
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
