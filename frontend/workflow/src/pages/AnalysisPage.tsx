import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import AnalysisProgress from '../components/AnalysisProgress';
import MetricsList from '../components/MetricsList';
import { getJob, getJobMetrics, startAnalysis, listUserRepos, generateMockData, getMetabasePlan } from '../api/workflowApi';
import type { Job, Metric, GitHubRepo } from '../types';

export default function AnalysisPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<Job | null>(null);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [error, setError] = useState('');
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [hasMockData, setHasMockData] = useState(false);
  const metricsLoadedRef = useRef(false);

  const queryParams = new URLSearchParams(window.location.search);
  const viewDashboard = queryParams.get('view') === 'dashboard';

  // States for the form at the top
  const [loadingNew, setLoadingNew] = useState(false);
  const [externalLink, setExternalLink] = useState('');
  const [mockLoading, setMockLoading] = useState(false);
  const [metabasePlan, setMetabasePlan] = useState<any | null>(null);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [showErrorModal, setShowErrorModal] = useState(false);
  const [showOverwriteModal, setShowOverwriteModal] = useState<{ msg: string, forceAction: () => void } | null>(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [metabaseUrl, setMetabaseUrl] = useState<string | null>(null);

  useEffect(() => {
    metricsLoadedRef.current = false;
    setHasMockData(false);
    const cached = localStorage.getItem('github_repos_cache');
    if (cached) {
      try {
        setRepos(JSON.parse(cached));
      } catch (e) {
        console.error('Failed to parse cached repos');
      }
    }

    const token = localStorage.getItem('github_token');
    if (token) {
      listUserRepos(token).then(data => {
        setRepos(data);
        localStorage.setItem('github_repos_cache', JSON.stringify(data));
      }).catch(console.error);
    }



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

        if (jobData.status === 'completed' && !metricsLoadedRef.current) {
          const result = await getJobMetrics(jobId);
          if (active) {
            setMetrics(result.metrics);
            setHasMockData(result.metrics.some(m => (m.entries || []).length > 0));
            metricsLoadedRef.current = true;
          }
        }

        if (jobData.status !== 'failed') {
          timeoutId = setTimeout(poll, jobData.status === 'completed' ? 1500 : 800);
        }
      } catch (err) {
        if (!active) return;
        const msg = err instanceof Error ? err.message : 'Failed to fetch job status';
        // If the URL contains an invalid/non-existent job id (e.g. /analysis/job_name),
        // go back to Home instead of leaving the user stranded on a broken page.
        if (String(msg).toLowerCase().includes('job not found')) {
          navigate('/');
          return;
        }
        setError(msg);
      }
    };

    poll();
    return () => {
      active = false;
      clearTimeout(timeoutId);
    };
  }, [jobId, navigate]);

  const handleAnalyzeNew = async (force: boolean = false) => {
    if (!externalLink) return;
    setLoadingNew(true);
    try {
      const token = localStorage.getItem('github_token') || undefined;
      const newJob = await startAnalysis(externalLink, token, force);
      navigate(`/analysis/${newJob.id}`);
    } catch (err: any) {
      if (err.status === 409) {
        setShowOverwriteModal({
          msg: `${err.message}\n\nDo you want to analyze it again and overwrite the current instance in the database?`,
          forceAction: () => handleAnalyzeNew(true),
        });
      } else {
        alert(err.message || 'Failed to start analysis');
      }
    } finally {
      setLoadingNew(false);
    }
  };

  const handleGenerateMock = async () => {
    if (!job?.workspace_id) return;
    setMockLoading(true);
    try {
      const res = await generateMockData(job.workspace_id);
      // Re-fetch metrics to show the new data
      const result = await getJobMetrics(jobId!);
      setMetrics(result.metrics);
      setHasMockData(result.metrics.some(m => (m.entries || []).length > 0) || (res?.entries_added ?? 0) > 0);
      if (res?.metabase_url) {
        setMetabaseUrl(res.metabase_url);
      }
      // Automatically fetch plan if we don't have it
      if (!metabasePlan) {
        handleMetabasePlan();
      }
      if (res?.metabase_error && !res?.metabase_url) {
        setErrorMessage(`Mock data generated, but Metabase setup failed: ${res.metabase_error}\n\nTip: restart the backend so it loads backend/.env (METABASE_USERNAME/METABASE_PASSWORD), then click "Continue to Dashboard" again.`);
        setShowErrorModal(true);
      } else {
        setShowSuccessModal(true);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to generate mock data. The LLM might have returned invalid data format.');
      setShowErrorModal(true);
    } finally {
      setMockLoading(false);
    }
  };

  const handleMetabasePlan = async (): Promise<string | null> => {
    if (!job?.workspace_id) return null;
    try {
      const plan = await getMetabasePlan(job.workspace_id);
      let url: string | null = null;
      if (typeof plan === 'string') {
        try {
          const parsed = JSON.parse(plan);
          if (parsed.metabase_url) { url = parsed.metabase_url; setMetabaseUrl(url); }
          if (parsed.metabase_error) {
            setErrorMessage(parsed.metabase_error);
            setShowErrorModal(true);
          }
          setMetabasePlan(parsed.plan || parsed);
        } catch (e) {
          setMetabasePlan(plan);
        }
      } else {
        if (plan.metabase_url) { url = plan.metabase_url; setMetabaseUrl(url); }
        if (plan.metabase_error) {
          setErrorMessage(plan.metabase_error);
          setShowErrorModal(true);
        }
        setMetabasePlan(plan.plan || plan);
      }
      return url;
    } catch (err: any) {
      console.error("Metabase plan fetch failed", err);
      setErrorMessage("Could not generate the Metabase dashboard plan. Please try again.");
      setShowErrorModal(true);
      return null;
    }
  };

  const handleMetabaseClick = async () => {
    if (!hasMockData) {
      setErrorMessage("Not sufficient data. Please generate mock data first.");
      setShowErrorModal(true);
      return;
    }

    // Open a window immediately to avoid popup blockers, then navigate it once URL is known.
    const popup = window.open('about:blank', '_blank');

    const directUrl = metabaseUrl;
    if (directUrl) {
      if (popup) popup.location.href = directUrl;
      else window.open(directUrl, '_blank');
      return;
    }

    const url = await handleMetabasePlan();
    if (url) {
      if (popup) popup.location.href = url;
      else window.open(url, '_blank');
      return;
    }

    if (popup) popup.close();
    setErrorMessage("Metabase URL was not returned. Ensure Metabase is running on your configured METABASE_URL and try again.");
    setShowErrorModal(true);
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
    <div className="analysis-page-container" style={{ width: '100%', maxWidth: '800px', position: 'relative' }}>
      {/* Workspaces Shortcut */}
      <div style={{ position: 'absolute', top: '2rem', right: '0rem', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.5rem' }}>
        <div
          style={{
            cursor: 'pointer',
            color: '#ef4444',
            transition: 'color 0.2s'
          }}
          title="View all workspaces"
          onClick={() => window.open('http://localhost:3000', '_blank')}
        >
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="7" y1="17" x2="17" y2="7"></line>
            <polyline points="7 7 17 7 17 17"></polyline>
          </svg>
        </div>
        <button
          type="button"
          className="thought-process-toggle"
          style={{ fontSize: '0.75rem', padding: '0.35rem 0.6rem' }}
          onClick={() => window.open('http://localhost:3000', '_blank')}
        >
          Workspaces
        </button>
      </div>
      {/* Form at the top (as seen in wireframe) */}
      <header className="content-header">
        <h1>New Repository Analysis</h1>
        <p>Select a local repository or provide an external URL to begin deep metrics detection.</p>
      </header>

      <div className="analysis-form-row">
        <div className="form-group">
          <label>Choose Repository ({repos.length})</label>
          <select
            className="input-control"
            onChange={(e) => {
              if (e.target.value) {
                // If user selects a repo, auto-fill it into the input or handle navigation
                setExternalLink(e.target.value);
              }
            }}
          >
            <option value="">Select from your list...</option>
            {repos.map(r => (
              <option key={r.full_name} value={r.html_url}>
                {r.full_name}{r.private ? ' (private)' : ''}
              </option>
            ))}
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
          onClick={() => handleAnalyzeNew(false)}
          disabled={loadingNew}
        >
          {loadingNew ? 'Starting...' : 'Analyze Repo'}
        </button>
      </div>

      {!viewDashboard && job && <AnalysisProgress job={job} />}

      {job?.status === 'completed' && (
        <div style={{ marginTop: '2rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2>Discovered Metrics ({metrics.length})</h2>
            <button
              className="btn-analyze"
              style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }}
              onClick={handleGenerateMock}
              disabled={mockLoading}
            >
              {mockLoading ? 'Generating...' : 'Generate Mock Data'}
            </button>
          </div>
          <MetricsList metrics={metrics} />
        </div>
      )}

      {job?.status === 'failed' && (
        <button onClick={() => navigate('/')} className="btn-retry" style={{ marginTop: '2rem' }}>
          Try Another Repo
        </button>
      )}

      {/* Custom Success Modal */}
      {showSuccessModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(15, 23, 42, 0.75)', backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10000, padding: '1rem'
        }}>
          <div style={{
            background: '#ffffff', width: '100%', maxWidth: '450px', borderRadius: '24px',
            padding: '2.5rem', textAlign: 'center', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
          }}>
            <div style={{
              width: '64px', height: '64px', background: '#dcfce7', color: '#22c55e',
              borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 1.5rem',
            }}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#1e293b', marginBottom: '0.5rem' }}>History Injected</h2>
            <p style={{ color: '#64748b', marginBottom: '2rem' }}>
              Synthetic metrics have been successfully generated and mapped to your registry. You can now view the visual trends.
            </p>
            <button
              className="btn-analyze"
              style={{ width: '100%' }}
              onClick={async () => {
                setShowSuccessModal(false);
                await handleMetabaseClick();
              }}
            >
              Continue to Dashboard
            </button>
          </div>
        </div>
      )}

      {/* Overwrite Confirm Modal */}
      {showOverwriteModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(15, 23, 42, 0.75)', backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10000, padding: '1rem'
        }}>
          <div style={{
            background: '#ffffff', width: '100%', maxWidth: '520px', borderRadius: '24px',
            padding: '2.5rem', textAlign: 'left', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
            border: '2px solid #fee2e2'
          }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#1e293b', marginBottom: '0.75rem' }}>
              Overwrite Existing Analysis?
            </h2>
            <p style={{ color: '#64748b', marginBottom: '1.5rem', whiteSpace: 'pre-wrap' }}>
              {showOverwriteModal.msg}
            </p>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button
                className="btn-analyze"
                style={{ flex: 1, background: '#ef4444' }}
                onClick={() => {
                  const action = showOverwriteModal.forceAction;
                  setShowOverwriteModal(null);
                  action();
                }}
              >
                Overwrite & Reanalyze
              </button>
              <button
                className="btn-analyze"
                style={{ flex: 1, background: '#ffffff', color: '#1e293b', border: '1px solid #e2e8f0' }}
                onClick={() => setShowOverwriteModal(null)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}


      {showErrorModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(15, 23, 42, 0.75)', backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10000, padding: '1rem'
        }}>
          <div style={{
            background: '#ffffff', width: '100%', maxWidth: '450px', borderRadius: '24px',
            padding: '2.5rem', textAlign: 'center', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
            border: '2px solid #fee2e2'
          }}>
            <div style={{
              width: '64px', height: '64px', background: '#fee2e2', color: '#ef4444',
              borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 1.5rem',
            }}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#1e293b', marginBottom: '0.5rem' }}>Generation Failed</h2>
            <p style={{ color: '#64748b', marginBottom: '2rem', fontSize: '0.9rem', lineHeight: '1.5' }}>
              {errorMessage}
            </p>
            <button
              className="btn-analyze"
              style={{ width: '100%', background: '#1e293b' }}
              onClick={() => setShowErrorModal(false)}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
