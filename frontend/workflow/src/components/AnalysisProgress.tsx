import { useState, useEffect } from 'react';
import type { Job } from '../types';

interface Props {
  job: Job;
}

interface Stage {
  id: number;
  title: string;
  status: 'completed' | 'in_progress' | 'pending' | 'upcoming';
}

const Typewriter = ({ text, delay = 15, isThought = false }: { text: string, delay?: number, isThought?: boolean }) => {
  const [currentText, setCurrentText] = useState('');

  useEffect(() => {
    let active = true;
    let i = 0;
    setCurrentText('');

    const tick = () => {
      if (!active) return;
      if (i < text.length) {
        setCurrentText(text.slice(0, i + 1));
        i++;
        setTimeout(tick, delay);
      }
    };
    tick();

    return () => { active = false; };
  }, [text, delay]);

  if (isThought) {
    return (
      <div className="thought-content">
        <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: '#6366f1', fontSize: '0.8rem', fontStyle: 'italic' }}>
          {currentText}
        </pre>
      </div>
    );
  }

  return <>{currentText}</>;
};

export default function AnalysisProgress({ job }: Props) {
  const [showLogs, setShowLogs] = useState<Record<number, boolean>>({
    1: false,
    2: true,
    3: true,
    4: true,
    5: true,
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
    { id: 4, title: 'Consolidating', status: getStageStatus(4) },
    { id: 5, title: 'Workspace Creation', status: getStageStatus(5) },
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
                  if (stage.id === 1) return l.includes("git") || l.includes("Connecting") || l.includes("Found") || l.includes("structure") || l.includes("layout") || l.includes("I see");
                  if (stage.id === 2) return l.includes("Fetch") || l.includes("Streaming") || l.includes("buffered") || l.includes("logic files") || l.includes("architecture patterns") || l.includes("Prioritizing");
                  if (stage.id === 3) return l.includes("Pass 1") || l.includes("Pass 2") || l.includes("LLM") || l.includes("Reasoning") || l.includes("Intent") || l.includes("Insight") || l.includes("Domain") || l.includes("Batch") || l.includes("Feeding") || l.includes("Discovery");
                  if (stage.id === 4) return l.includes("Consolidating") || l.includes("deduplicating") || l.includes("distilled") || l.includes("Pass 3") || l.includes("Registry");
                  if (stage.id === 5) return l.includes("workspace") || l.includes("visualization") || l.includes("ready") || l.includes("Synthesis") || l.includes("Plan") || l.includes("data injected") || l.includes("Reports") || l.includes("Metabase") || l.includes("LIVE");
                  return false;
                }).map((log, i) => {
                  const isThought = log.includes("LLM Thought Process");
                  return (
                    <div key={i} className={`log-entry ${isThought ? 'thought-block' : ''}`}>
                      <Typewriter text={log} isThought={isThought} delay={isThought ? 5 : 20} />
                    </div>
                  );
                })}
                {stage.status === 'in_progress' && (
                  <div className="log-entry">
                    <span className="log-timestamp">...</span> {job.progress_message} <span className="thinking-dot" />
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
