import { useState } from 'react';

interface Props {
  onSubmit: (repoUrl: string) => void;
  loading: boolean;
}

export default function RepoInputForm({ onSubmit, loading }: Props) {
  const [repoUrl, setRepoUrl] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;
    onSubmit(repoUrl.trim());
  };

  return (
    <form onSubmit={handleSubmit} className="repo-form">
      <div className="form-group">
        <label htmlFor="repo-url">GitHub Repository URL</label>
        <input
          id="repo-url"
          type="url"
          placeholder="https://github.com/owner/repo"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          required
          disabled={loading}
        />
      </div>

      <button type="submit" disabled={loading || !repoUrl.trim()}>
        {loading ? 'Starting...' : 'Analyze Repository'}
      </button>
    </form>
  );
}
