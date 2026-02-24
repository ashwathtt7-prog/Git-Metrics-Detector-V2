import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { startAnalysis, listUserRepos, listJobs } from '../api/workflowApi';
import type { GitHubRepo, Job } from '../types';

export default function HomePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [externalLink, setExternalLink] = useState('');
  const [selectedRepo, setSelectedRepo] = useState('');
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [reposLoading, setReposLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [showOverwriteModal, setShowOverwriteModal] = useState<{ existingJob: Job, repoUrl: string } | null>(null);
  const [pendingForceUrl, setPendingForceUrl] = useState<string | null>(null);

  const fetchRepos = useCallback(() => {
    const token = localStorage.getItem('github_token') || '';
    console.log('[HomePage] Fetching repos with token:', token ? '***' : 'missing');
    if (token) {
      setReposLoading(true);
      listUserRepos(token)
        .then((data) => {
          console.log('[HomePage] Repos fetched:', data.length);
          localStorage.setItem('github_repos_cache', JSON.stringify(data));
          setRepos(data);
        })
        .catch((err) => {
          console.error('[HomePage] Repo fetch error:', err);
          setError('Failed to load repositories');
        })
        .finally(() => setReposLoading(false));
    } else {
      setRepos([]);
    }
  }, []);

  const [jobs, setJobs] = useState<any[]>([]);

  useEffect(() => {
    fetchRepos();
    // Also fetch analyzed jobs to check for duplicates proactively
    listJobs().then(setJobs).catch(console.error);

    const onTokenChanged = (_e: Event) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(fetchRepos, 800);
    };

    window.addEventListener('github-token-changed', onTokenChanged);
    return () => {
      window.removeEventListener('github-token-changed', onTokenChanged);
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [fetchRepos]);

  const normalizeUrl = (url: string) => {
    return url.replace(/\/$/, '').toLowerCase().trim();
  };

  const handleAnalyze = async (force: boolean = false) => {
    // Use pending URL if force reanalyzing, otherwise use form inputs
    const rawUrl = force && pendingForceUrl ? pendingForceUrl : (externalLink || selectedRepo).trim();
    if (!rawUrl) {
      setError('Please provide a repository URL or select one.');
      return;
    }

    const normalizedTarget = normalizeUrl(rawUrl);

    // Proactive check: if not already forcing, check if it's in our jobs list
    if (!force) {
      const existingJob = jobs.find(j =>
        normalizeUrl(j.repo_url) === normalizedTarget &&
        (j.status === 'completed' || j.status === 'analyzing' || j.status === 'pending')
      );

      if (existingJob) {
        // Show modal asking user what they want to do
        setShowOverwriteModal({ existingJob, repoUrl: rawUrl });
        return;
      }
    }

    setLoading(true);
    setError('');
    setPendingForceUrl(rawUrl); // Store for potential force reanalyze

    const token = localStorage.getItem('github_token') || undefined;

    try {
      const job = await startAnalysis(rawUrl, token, force);
      // Navigate immediately to the analysis page
      setPendingForceUrl(null); // Clear pending URL on success
      navigate(`/analysis/${job.id}`);
    } catch (err: any) {
      if (err.status === 409) {
        // Repo already analyzed: take the user to the existing analysis page.
        if (err.jobId) {
          navigate(`/analysis/${err.jobId}`);
          return;
        }
      }
      setError(err.message || 'Failed to start analysis');
      setLoading(false);
    }
  };

  return (
    <div className="home-page-container" style={{ width: '100%', maxWidth: '800px' }}>
      <header className="content-header">
        <h1>New Repository Analysis</h1>
        <p>Select a local repository or provide an external URL to begin deep metrics detection.</p>
      </header>

      <div className="analysis-form-row">
        <div className="form-group">
          <label>Choose Repository ({repos.length})</label>
          <select
            className="input-control"
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
          >
            <option value="">{reposLoading ? 'Loading repos...' : 'Select a repository...'}</option>
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
              placeholder="https://github.com/user/repo"
              value={externalLink}
              onChange={(e) => setExternalLink(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div style={{ textAlign: 'center' }}>
        <button
          className="btn-analyze"
          onClick={() => handleAnalyze(false)}
          disabled={loading}
        >
          {loading ? 'Starting...' : 'Analyze Repo'}
        </button>
      </div>



      {error && <div className="error-banner" style={{ marginTop: '2rem' }}>{error}</div>}

      {/* Placeholder for results or history if needed */}
      {!loading && !error && (
        <div style={{
          marginTop: '4rem',
          background: '#33415511',
          height: '150px',
          borderRadius: '16px',
          border: '2px dashed #33415533',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#64748b',
          fontSize: '0.9rem'
        }}>
          Repository analysis status will appear here
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
            border: '2px solid #fbbf24'
          }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#1e293b', marginBottom: '0.75rem' }}>
              Repository Already Analyzed
            </h2>
            <p style={{ color: '#64748b', marginBottom: '1.5rem', whiteSpace: 'pre-wrap' }}>
              This repository has already been analyzed (status: {showOverwriteModal.existingJob.status}).
              Would you like to view the existing analysis or overwrite it with a new one?
            </p>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button
                className="btn-analyze"
                style={{ flex: 1, background: '#ef4444' }}
                onClick={() => {
                  navigate(`/analysis/${showOverwriteModal.existingJob.id}`);
                  setShowOverwriteModal(null);
                }}
              >
                View Existing
              </button>
              <button
                className="btn-analyze"
                style={{ flex: 1, background: '#ef4444' }}
                onClick={() => {
                  const repoUrl = showOverwriteModal.repoUrl;
                  setShowOverwriteModal(null);
                  setPendingForceUrl(repoUrl);
                  // Use setTimeout to ensure state is updated before calling handleAnalyze
                  setTimeout(() => {
                    handleAnalyze(true);
                  }, 0);
                }}
              >
                Overwrite & Reanalyze
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
