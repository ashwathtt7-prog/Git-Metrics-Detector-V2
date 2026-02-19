SELECT
    id,
    repo_url,
    repo_owner,
    repo_name,
    status,
    error_message,
    total_files,
    analyzed_files,
    created_at,
    completed_at
FROM analysis_jobs
ORDER BY created_at DESC
