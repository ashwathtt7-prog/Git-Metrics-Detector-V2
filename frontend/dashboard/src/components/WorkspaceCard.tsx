import { Link } from 'react-router-dom';
import type { Workspace } from '../types';

interface Props {
  workspace: Workspace;
  onDelete: (id: string) => void;
  onGenerateMockData: (id: string) => void;
  generating: boolean;
}

export default function WorkspaceCard({ workspace, onDelete, onGenerateMockData, generating }: Props) {
  const date = new Date(workspace.created_at).toLocaleDateString();
  const hasMetabase = Boolean(workspace.metabase_url);
  const canOpenMetabase = Boolean(workspace.has_mock_data && workspace.metabase_url);

  return (
    <div className="workspace-card">
      <div className="workspace-card-header">
        <Link to={`/workspace/${workspace.id}`} className="workspace-name">
          {workspace.name}
        </Link>
        <button
          className="btn-delete"
          onClick={(e) => { e.preventDefault(); onDelete(workspace.id); }}
          title="Delete workspace"
        >
          &times;
        </button>
      </div>
      <p className="workspace-url">{workspace.repo_url}</p>
      {workspace.description && (
        <p className="workspace-desc">{workspace.description}</p>
      )}

      <div className="workspace-actions">
        {canOpenMetabase ? (
          <a className="btn-metabase" href={workspace.metabase_url} target="_blank" rel="noreferrer">
            Open in Metabase
          </a>
        ) : (
          <button
            className="btn-generate"
            type="button"
            onClick={() => onGenerateMockData(workspace.id)}
            disabled={generating}
            title={hasMetabase && !workspace.has_mock_data ? 'Mock data is not generated yet.' : undefined}
          >
            {generating ? 'Generating...' : 'Generate mock data'}
          </button>
        )}
        <Link className="btn-details" to={`/workspace/${workspace.id}`}>
          View details
        </Link>
      </div>

      <div className="workspace-footer">
        <span className="metric-count">{workspace.metric_count} metrics</span>
        <span className="workspace-date">{date}</span>
      </div>
    </div>
  );
}
