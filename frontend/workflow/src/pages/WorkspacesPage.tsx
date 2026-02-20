
import React, { useEffect, useState } from 'react';
import { listJobs } from '../api/workflowApi';
import type { Job } from '../types';
import { useNavigate } from 'react-router-dom';

export default function WorkspacesPage() {
    const [jobs, setJobs] = useState<Job[]>([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        listJobs()
            .then(setJobs)
            .finally(() => setLoading(false));
    }, []);

    return (
        <div className="content" style={{ maxWidth: '1000px', margin: '0 auto' }}>
            <header className="content-header" style={{ textAlign: 'left', width: '100%', marginBottom: '2rem' }}>
                <h1>All Workspaces</h1>
                <p>Browse all your previously analyzed repositories and their metrics.</p>
            </header>

            {loading ? (
                <div style={{ textAlign: 'center', padding: '4rem' }}>Loading workspaces...</div>
            ) : (
                <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', width: '100%' }}>
                    {jobs.map((job) => (
                        <div
                            key={job.id}
                            className="metric-card"
                            style={{ cursor: 'pointer', display: 'flex', flexDirection: 'column' }}
                            onClick={() => navigate(`/analysis/${job.id}?view=dashboard`)}
                        >
                            <div className="metric-card-header">
                                <h3>{job.repo_owner}/{job.repo_name}</h3>
                                <span className={`status-label ${job.status}`}>
                                    {job.status}
                                </span>
                            </div>
                            <p className="metric-description" style={{ flex: 1 }}>
                                {job.repo_url}
                            </p>
                            <div className="metric-meta" style={{ marginTop: '1rem', borderTop: '1px solid #f1f5f9', paddingTop: '1rem' }}>
                                Analyzed on {new Date(job.created_at).toLocaleDateString()}
                            </div>
                        </div>
                    ))}
                    {jobs.length === 0 && <div style={{ textAlign: 'center', gridColumn: '1/-1' }}>No workspace found.</div>}
                </div>
            )}
        </div>
    );
}
