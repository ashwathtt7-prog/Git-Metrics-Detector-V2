import type { Workspace } from '../types';
import WorkspaceCard from './WorkspaceCard';

interface Props {
  workspaces: Workspace[];
  onDelete: (id: string) => void;
}

export default function WorkspaceList({ workspaces, onDelete }: Props) {
  if (workspaces.length === 0) {
    return (
      <div className="empty-state">
        <h2>No workspaces yet</h2>
        <p>Analyze a GitHub repository to create your first workspace.</p>
        <a href="http://localhost:3000" className="btn-workflow">
          Go to Workflow App
        </a>
      </div>
    );
  }

  return (
    <div className="workspace-grid">
      {workspaces.map((ws) => (
        <WorkspaceCard key={ws.id} workspace={ws} onDelete={onDelete} />
      ))}
    </div>
  );
}
