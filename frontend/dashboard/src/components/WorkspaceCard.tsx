import { Link } from 'react-router-dom';
import type { Workspace } from '../types';

interface Props {
  workspace: Workspace;
  onDelete: (id: string) => void;
}

export default function WorkspaceCard({ workspace, onDelete }: Props) {
  const date = new Date(workspace.created_at).toLocaleDateString();

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
      <div className="workspace-footer">
        <span className="metric-count">{workspace.metric_count} metrics</span>
        <span className="workspace-date">{date}</span>
      </div>
    </div>
  );
}
