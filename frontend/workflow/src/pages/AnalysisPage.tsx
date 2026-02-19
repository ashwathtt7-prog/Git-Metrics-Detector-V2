import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import AnalysisProgress from '../components/AnalysisProgress';
import MetricsList from '../components/MetricsList';
import DashboardLink from '../components/DashboardLink';
import { getJob, getJobMetrics, startAnalysis } from '../api/workflowApi';
import type { Job, Metric } from '../types';

export default function AnalysisPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<Job | null>(null);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [error, setError] = useState('');

  // States for the form at the top
  const [loadingNew, setLoadingNew] = useState(false);
  const [externalLink, setExternalLink] = useState('');

  useEffect(() => {
    if (!jobId) {
      navigate('/');
      return;
    }

    let active = true;
    let timeoutId: ReturnType<typeof setTimeout>;

    const poll = async () => {
      try {
        const jobData = await getJob(jobId);
        if (!active) return;
        setJob(jobData);

        if (jobData.status === 'completed') {
          const result = await getJobMetrics(jobId);
          if (active) setMetrics(result.metrics);
        } else if (jobData.status !== 'failed') {
          timeoutId = setTimeout(poll, 1500); // Poll slightly faster for real-time feel
        }
      } catch (err: any) {
        if (active) setError(err.message || 'Failed to fetch job status');
      }
    };

    poll();
    return () => {
      active = false;
      clearTimeout(timeoutId);
    };
  }, [jobId, navigate]);

  const handleAnalyzeNew = async () => {
    if (!externalLink) return;
    setLoadingNew(true);
    try {
      const token = localStorage.getItem('github_token') || undefined;
      const newJob = await startAnalysis(externalLink, token);
      navigate(`/analysis/${newJob.id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to start analysis');
    } finally {
      setLoadingNew(false);
    }
  };

  if (error && !job) {
    return (
      <div className="analysis-page-container" style={{ width: '100%', maxWidth: '800px' }}>
        <div className="error-banner">{error}</div>
        <button onClick={() => navigate('/')} className="btn-back">Back to Home</button>
      </div>
    );
  }

  return (
    <div className="analysis-page-container" style={{ width: '100%', maxWidth: '800px' }}>
      {/* Form at the top (as seen in wireframe) */}
      <header className="content-header">
        <h1>New Repository Analysis</h1>
        <p>Select a local repository or provide an external URL to begin deep metrics detection.</p>
      </header>

      <div className="analysis-form-row">
        <div className="form-group">
          <label>Choose Repository</label>
          <select className="input-control">
            <option>{job ? `${job.repo_owner}/${job.repo_name}` : 'Select from your list...'}</option>
          </select>
        </div>

        <div className="form-group">
          <label>External GitHub Link</label>
          <div style={{ position: 'relative' }}>
            <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
            </span>
            <input
              type="url"
              className="input-control"
              style={{ paddingLeft: '2.5rem' }}
              placeholder={job?.repo_url || "https://github.com/user/repo"}
              value={externalLink}
              onChange={(e) => setExternalLink(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div style={{ textAlign: 'center' }}>
        <button
          className="btn-analyze"
          onClick={handleAnalyzeNew}
          disabled={loadingNew}
        >
          {loadingNew ? 'Starting...' : 'Analyze Repo'}
        </button>
      </div>

      {job && <AnalysisProgress job={job} />}

      {job?.status === 'completed' && (
        <div style={{ marginTop: '2rem' }}>
          {job.workspace_id && <DashboardLink workspaceId={job.workspace_id} />}
          <MetricsList metrics={metrics} />
        </div>
      )}

      {job?.status === 'failed' && (
        <button onClick={() => navigate('/')} className="btn-retry" style={{ marginTop: '2rem' }}>
          Try Another Repo
        </button>
      )}
    </div>
  );
}
