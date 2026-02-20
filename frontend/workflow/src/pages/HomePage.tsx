import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { startAnalysis, listUserRepos } from '../api/workflowApi';
import type { GitHubRepo } from '../api/workflowApi';

export default function HomePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [externalLink, setExternalLink] = useState('');
  const [selectedRepo, setSelectedRepo] = useState('');
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [reposLoading, setReposLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchRepos = useCallback(() => {
    const token = localStorage.getItem('github_token') || '';
    if (token) {
      setReposLoading(true);
      listUserRepos(token)
        .then(setRepos)
        .catch(console.error)
        .finally(() => setReposLoading(false));
    } else {
      setRepos([]);
    }
  }, []);

  useEffect(() => {
    fetchRepos();
    // Debounced listener for token changes from the Sidebar (fires on every keystroke)
    const onTokenChanged = () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(fetchRepos, 800);
    };
    window.addEventListener('github-token-changed', onTokenChanged);
    // Also listen for cross-tab changes
    const onStorage = (e: StorageEvent) => {
      if (e.key === 'github_token') fetchRepos();
    };
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener('github-token-changed', onTokenChanged);
      window.removeEventListener('storage', onStorage);
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [fetchRepos]);

  const handleAnalyze = async () => {
    const url = externalLink || selectedRepo;
    if (!url) {
      setError('Please provide a repository URL or select one.');
      return;
    }

    setLoading(true);
    setError('');

    // Get token from local storage (managed by Sidebar)
    const token = localStorage.getItem('github_token') || undefined;

    try {
      const job = await startAnalysis(url, token);
      navigate(`/analysis/${job.id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to start analysis');
    } finally {
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
          <label>Choose Repository</label>
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
          onClick={handleAnalyze}
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
    </div>
  );
}
