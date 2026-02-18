import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import AnalysisProgress from '../components/AnalysisProgress';
import MetricsList from '../components/MetricsList';
import DashboardLink from '../components/DashboardLink';
import { getJob, getJobMetrics } from '../api/workflowApi';
import type { Job, Metric } from '../types';

export default function AnalysisPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<Job | null>(null);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [error, setError] = useState('');

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
          timeoutId = setTimeout(poll, 2000);
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

  if (error) {
    return (
      <div className="analysis-page">
        <div className="error-banner">{error}</div>
        <button onClick={() => navigate('/')} className="btn-back">Back to Home</button>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="analysis-page">
        <div className="loading">Loading...</div>
      </div>
    );
  }

  return (
    <div className="analysis-page">
      <button onClick={() => navigate('/')} className="btn-back">
        &larr; New Analysis
      </button>

      <AnalysisProgress job={job} />

      {job.status === 'completed' && (
        <>
          {job.workspace_id && <DashboardLink workspaceId={job.workspace_id} />}
          <MetricsList metrics={metrics} />
        </>
      )}

      {job.status === 'failed' && (
        <button onClick={() => navigate('/')} className="btn-retry">
          Try Again
        </button>
      )}
    </div>
  );
}
