interface Props {
  workspaceId: string;
}

export default function DashboardLink({ workspaceId }: Props) {
  const dashboardUrl = `http://localhost:3001/workspace/${workspaceId}`;

  return (
    <div className="dashboard-link">
      <div className="workspace-created">Workspace created successfully!</div>
      <a href={dashboardUrl} className="btn-dashboard" target="_blank" rel="noopener noreferrer">
        Go to Dashboard
      </a>
    </div>
  );
}
