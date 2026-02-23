import { Link } from 'react-router-dom';
import type { Workspace } from '../types';

interface Props {
  workspace: Workspace;
  onDelete: (id: string) => void;
}

export default function WorkspaceCard({ workspace, onDelete }: Props) {
  const date = new Date(workspace.created_at).toLocaleDateString();
  const hasMetabase = Boolean(workspace.metabase_url);

  return (
    <div
      className={`workspace-card ${hasMetabase ? 'workspace-card-clickable' : ''}`}
      role={hasMetabase ? 'button' : undefined}
      tabIndex={hasMetabase ? 0 : undefined}
      onClick={() => { if (workspace.metabase_url) window.open(workspace.metabase_url, '_blank'); }}
      onKeyDown={(e) => {
        if (!hasMetabase) return;
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          if (workspace.metabase_url) window.open(workspace.metabase_url, '_blank');
        }
      }}
    >
      <div className="workspace-card-header">
        <Link to={`/workspace/${workspace.id}`} className="workspace-name" onClick={(e) => e.stopPropagation()}>
          {workspace.name}
        </Link>
        <button
          className="btn-delete"
          onClick={(e) => { e.preventDefault(); e.stopPropagation(); onDelete(workspace.id); }}
          title="Delete workspace"
        >
          &times;
        </button>
      </div>
      <p className="workspace-url">{workspace.repo_url}</p>
      {workspace.description && (
        <p className="workspace-desc">{workspace.description}</p>
      )}
      {workspace.metabase_url && (
        <div className="workspace-actions" onClick={(e) => e.stopPropagation()}>
          <a className="btn-metabase" href={workspace.metabase_url} target="_blank" rel="noreferrer">
            Open in Metabase ↗
          </a>
          <Link className="btn-details" to={`/workspace/${workspace.id}`}>
            View details
          </Link>
        </div>
      )}
      <div className="workspace-footer">
        <span className="metric-count">{workspace.metric_count} metrics</span>
        <span className="workspace-date">{date}</span>
      </div>
    </div>
  );
}
