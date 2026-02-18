import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import RepoInputForm from '../components/RepoInputForm';
import { startAnalysis } from '../api/workflowApi';

export default function HomePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (repoUrl: string) => {
    setLoading(true);
    setError('');
    try {
      const job = await startAnalysis(repoUrl);
      navigate(`/analysis/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start analysis');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="home-page">
      <div className="hero">
        <h1>Git Metrics Detector</h1>
        <p>Analyze any GitHub repository to discover trackable metrics using AI</p>
      </div>

      <RepoInputForm onSubmit={handleSubmit} loading={loading} />

      {error && <div className="error-banner">{error}</div>}

      <div className="how-it-works">
        <h2>How it works</h2>
        <div className="steps">
          <div className="step">
            <div className="step-number">1</div>
            <h3>Enter Repository URL</h3>
            <p>Paste a public or private GitHub repository link</p>
          </div>
          <div className="step">
            <div className="step-number">2</div>
            <h3>AI Analysis</h3>
            <p>AI analyzes every file to understand the project</p>
          </div>
          <div className="step">
            <div className="step-number">3</div>
            <h3>Get Metrics</h3>
            <p>Receive a list of project-specific trackable metrics</p>
          </div>
          <div className="step">
            <div className="step-number">4</div>
            <h3>Dashboard</h3>
            <p>A workspace is auto-created with all metrics as columns</p>
          </div>
        </div>
      </div>
    </div>
  );
}
