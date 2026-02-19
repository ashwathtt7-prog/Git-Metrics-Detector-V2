import type { Job } from '../types';

interface Props {
  job: Job;
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Initializing...',
  fetching: 'Fetching repository files...',
  analyzing: 'Analyzing codebase with AI...',
  completed: 'Analysis complete!',
  failed: 'Analysis failed',
};

export default function AnalysisProgress({ job }: Props) {
  const progress = job.total_files > 0
    ? Math.round((job.analyzed_files / job.total_files) * 100)
    : 0;

  const isFetching = job.status === 'fetching';
  const isAnalyzing = job.status === 'analyzing';
  const isComplete = job.status === 'completed';
  const isFailed = job.status === 'failed';

  return (
    <div className={`analysis-progress ${isFailed ? 'error' : ''}`}>
      <div className="progress-header">
        <span className={`status-badge ${job.status}`}>
          {STATUS_LABELS[job.status] || job.status}
        </span>
        <span className="repo-name">{job.repo_owner}/{job.repo_name}</span>
      </div>

      {(isFetching || isAnalyzing || isComplete) && job.total_files > 0 && (
        <div className="progress-bar-container">
          <div className="progress-bar" style={{ width: `${isComplete ? 100 : progress}%` }} />
          <span className="progress-text">
            {isFetching
              ? `${job.analyzed_files} / ${job.total_files} files fetched`
              : isAnalyzing
                ? `${job.total_files} files sent to AI for analysis`
                : `${job.total_files} files analyzed`
            }
          </span>
        </div>
      )}

      {isAnalyzing && job.progress_message && (
        <div className="llm-progress">
          <span className="llm-spinner" />
          <span className="llm-message">{job.progress_message}</span>
        </div>
      )}

      {isFailed && job.error_message && (
        <div className="error-message">{job.error_message}</div>
      )}
    </div>
  );
}
