import { useState } from 'react';
import type { Job } from '../types';

interface Props {
  job: Job;
}

interface Stage {
  id: number;
  title: string;
  status: 'completed' | 'in_progress' | 'pending' | 'upcoming';
}

export default function AnalysisProgress({ job }: Props) {
  const [showLogs, setShowLogs] = useState<Record<number, boolean>>({
    1: false,
    2: true,
    3: true,
    4: true,
  });

  const logs: string[] = job.logs ? JSON.parse(job.logs) : [];

  const getStageStatus = (stageId: number): Stage['status'] => {
    if (job.status === 'failed') return 'pending'; // Or handle error state
    if (job.status === 'completed') return 'completed';

    if (job.current_stage > stageId) return 'completed';
    if (job.current_stage === stageId) return 'in_progress';
    return 'upcoming';
  };

  const stages: Stage[] = [
    { id: 1, title: 'Validation', status: getStageStatus(1) },
    { id: 2, title: 'Fetching Data', status: getStageStatus(2) },
    { id: 3, title: 'Processing', status: getStageStatus(3) },
    { id: 4, title: 'Reporting', status: getStageStatus(4) },
  ];

  const toggleLogs = (id: number) => {
    setShowLogs(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const renderLogs = (stageId: number) => {
    // Basic logic to filter logs by stage if needed, 
    // but for now let's just show them in the active stage or based on simple heuristics
    if (job.current_stage !== stageId && getStageStatus(stageId) !== 'completed') return null;

    // For now, let's just show all logs in the current stage's box for simplicity
    // or distribute them if we had markers. Let's just show them in the current active stage.
    return (
      <div className="log-viewer">
        {logs.map((log, i) => (
          <div key={i} className="log-entry">
            {log}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="timeline-container">
      <div className="timeline-line" />

      {stages.map((stage) => (
        <div key={stage.id} className="stage-wrapper">
          <div className={`stage-node ${stage.status}`}>
            {stage.status === 'completed' && '✓'}
            {stage.status === 'in_progress' && '●'}
          </div>

          <div className={`stage-card ${stage.status}`}>
            <div className="stage-header">
              <div className="stage-title">
                <h2>Stage {stage.id}: {stage.title}</h2>
              </div>
              <span className={`status-label ${stage.status}`}>
                {stage.status.replace('_', ' ')}
              </span>
            </div>

            <button
              className="thought-process-toggle"
              onClick={() => toggleLogs(stage.id)}
            >
              {showLogs[stage.id] ? '▼ Hide LLM Thought Process' : '▶ Show LLM Thought Process'}
            </button>

            {showLogs[stage.id] && stage.status !== 'upcoming' && (
              <div className="log-viewer">
                {/* Simple filtering: show validation logs in stage 1, etc. */}
                {logs.filter(l => {
                  if (stage.id === 1) return l.includes("git") || l.includes("Validation") || l.includes("Found");
                  if (stage.id === 2) return l.includes("Fetch") || l.includes("Streaming") || l.includes("buffered");
                  if (stage.id === 3) return l.includes("Pass") || l.includes("LLM") || l.includes("Metrics discovered");
                  if (stage.id === 4) return l.includes("workspace") || l.includes("visualization") || l.includes("ready");
                  return false;
                }).map((log, i) => (
                  <div key={i} className="log-entry">
                    {log}
                  </div>
                ))}
                {stage.status === 'in_progress' && (
                  <div className="log-entry">
                    <span className="log-timestamp">...</span> {job.progress_message}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      ))}

      {job.status === 'failed' && (
        <div className="error-message">
          <strong>Analysis Failed:</strong> {job.error_message}
        </div>
      )}
    </div>
  );
}
