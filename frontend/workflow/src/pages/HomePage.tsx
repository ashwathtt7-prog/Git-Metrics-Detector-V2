import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { startAnalysis, listJobs } from '../api/workflowApi';
import type { Job } from '../types';

export default function HomePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [externalLink, setExternalLink] = useState('');
  const [selectedRepo, setSelectedRepo] = useState('');
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);

  useEffect(() => {
    listJobs().then(setRecentJobs).catch(console.error);
  }, []);

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
            <option value="">Select from your list...</option>
            {recentJobs.map(j => (
              <option key={j.id} value={j.repo_url}>{j.repo_owner}/{j.repo_name}</option>
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
