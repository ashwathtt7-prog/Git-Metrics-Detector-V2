import { useEffect, useMemo, useRef, useState } from 'react';
import type { Job } from '../types';

interface Props {
  job: Job;
}

interface Stage {
  id: number;
  title: string;
  status: 'completed' | 'in_progress' | 'pending' | 'upcoming';
}

const Typewriter = ({ text, delay = 15, isDetail = false }: { text: string, delay?: number, isDetail?: boolean }) => {
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

  if (isDetail) {
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
  const [followLatest, setFollowLatest] = useState(true);
  const logContainers = useRef<Record<number, HTMLDivElement | null>>({});

  const stageTaggedLogs = useMemo(() => {
    const byStage: Record<number, string[]> = {};
    for (const line of logs) {
      const match = line.match(/\[S(\d+)/);
      const stageId = match ? Number(match[1]) : null;
      if (!stageId || Number.isNaN(stageId)) continue;
      if (!byStage[stageId]) byStage[stageId] = [];
      byStage[stageId].push(line);
    }
    return byStage;
  }, [logs]);

  const hasTaggedLogs = useMemo(() => logs.some(l => l.includes('[S')), [logs]);

  const legacyStageLogs = useMemo(() => {
    const byStage: Record<number, string[]> = { 1: [], 2: [], 3: [], 4: [], 5: [] };
    for (const l of logs) {
      if (l.includes('[S')) continue; // avoid double-display when mixed logs exist
      if (l.includes("git") || l.includes("Connecting") || l.includes("Found") || l.includes("structure") || l.includes("layout") || l.includes("I see")) byStage[1].push(l);
      else if (l.includes("Fetch") || l.includes("Streaming") || l.includes("buffered") || l.includes("logic files") || l.includes("architecture patterns") || l.includes("Prioritizing")) byStage[2].push(l);
      else if (l.includes("Pass 1") || l.includes("Pass 2") || l.includes("LLM") || l.includes("Reasoning") || l.includes("Intent") || l.includes("Insight") || l.includes("Domain") || l.includes("Batch") || l.includes("Feeding") || l.includes("Discovery")) byStage[3].push(l);
      else if (l.includes("Consolidating") || l.includes("deduplicating") || l.includes("distilled") || l.includes("Pass 3") || l.includes("Registry")) byStage[4].push(l);
      else if (l.includes("workspace") || l.includes("visualization") || l.includes("ready") || l.includes("Synthesis") || l.includes("Plan") || l.includes("data injected") || l.includes("Reports") || l.includes("Metabase") || l.includes("LIVE")) byStage[5].push(l);
    }
    return byStage;
  }, [logs]);

  useEffect(() => {
    if (!followLatest) return;
    const raf = window.requestAnimationFrame(() => {
      for (const key of Object.keys(logContainers.current)) {
        const stageId = Number(key);
        if (!showLogs[stageId]) continue;
        const el = logContainers.current[stageId];
        if (!el) continue;
        el.scrollTop = el.scrollHeight;
      }
    });

    return () => window.cancelAnimationFrame(raf);
  }, [followLatest, logs.length, showLogs]);

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
              {showLogs[stage.id] ? '▼ Hide LLM Details' : '▶ Show LLM Details'}
            </button>

            {showLogs[stage.id] && stage.status !== 'upcoming' && (
              <div className="log-viewer">
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '0.5rem' }}>
                  <button
                    className="thought-process-toggle"
                    onClick={() => setFollowLatest(v => !v)}
                    style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                  >
                    {followLatest ? 'Following latest' : 'Follow latest'}
                  </button>
                </div>

                <div
                  ref={(el) => { logContainers.current[stage.id] = el; }}
                  style={{ maxHeight: '320px', overflowY: 'auto' }}
                >
                  {((hasTaggedLogs ? (stageTaggedLogs[stage.id] || []) : (legacyStageLogs[stage.id] || []))).map((log, i) => {
                    const isDetail =
                      log.includes("/LLM]") ||
                      log.includes("/Evidence]") ||
                      log.includes("/Metric]") ||
                      log.includes("/Retry]") ||
                      log.includes("/Progress]") ||
                      log.includes("/Error]");
                    return (
                      <div key={i} className={`log-entry ${isDetail ? 'thought-block' : ''}`}>
                        <Typewriter text={log} isDetail={isDetail} delay={isDetail ? 5 : 20} />
                      </div>
                    );
                  })}
                  {stage.status === 'in_progress' && (
                    <div className="log-entry">
                      <span className="log-timestamp">...</span> {job.progress_message} <span className="thinking-dot" />
                    </div>
                  )}
                </div>
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
