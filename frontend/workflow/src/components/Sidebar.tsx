import React, { useEffect, useState } from 'react';
import { listJobs } from '../api/workflowApi';
import type { Job } from '../types';

export default function Sidebar() {
    const [token, setToken] = useState(localStorage.getItem('github_token') || '');
    const [recentJobs, setRecentJobs] = useState<Job[]>([]);

    useEffect(() => {
        localStorage.setItem('github_token', token);
        // Dispatch a custom event so HomePage can react immediately (StorageEvent doesn't fire in the same tab)
        window.dispatchEvent(new CustomEvent('github-token-changed'));
    }, [token]);

    useEffect(() => {
        listJobs().then(setRecentJobs).catch(console.error);
        const interval = setInterval(() => {
            listJobs().then(setRecentJobs).catch(console.error);
        }, 10000);
        return () => clearInterval(interval);
    }, []);

    return (
        <aside className="sidebar">
            <div className="sidebar-header">
                <div className="logo-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="8" y1="12" x2="8" y2="16"></line><line x1="12" y1="10" x2="12" y2="16"></line><line x1="16" y1="7" x2="16" y2="16"></line></svg>
                </div>
                <div className="logo-text">
                    <h1>Metrics Detector</h1>
                    <p>Github Analysis Suite</p>
                </div>
            </div>

            <div className="sidebar-section">
                <h3>GitHub Personal Access Token</h3>
                <div className="token-input-wrapper">
                    <input
                        type="password"
                        className="token-input"
                        placeholder="Enter your GitHub access token"
                        value={token}
                        onChange={(e) => setToken(e.target.value)}
                    />
                </div>
            </div>

            <div className="sidebar-section" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <h3>Analyzed Repos</h3>
                    <span style={{ fontSize: '0.65rem', color: '#64748b', fontWeight: 700 }}>{recentJobs.length} TOTAL</span>
                </div>

                <div className="analyzed-repos-list">
                    {recentJobs.map((job) => (
                        <div key={job.id} className="repo-item" onClick={() => window.location.href = `/analysis/${job.id}`}>
                            <div className="repo-item-header">
                                <div className="repo-avatar">
                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.28 1.15-.28 2.35 0 3.5-.73 1.02-1.08 2.25-1 3.5 0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"></path><path d="M9 18c-4.51 2-4.51-2-7-2"></path></svg>
                                </div>
                                <div className="repo-info">
                                    <h4>{job.repo_owner}/{job.repo_name}</h4>
                                    <p>{new Date(job.created_at).toLocaleDateString()}</p>
                                </div>
                            </div>
                        </div>
                    ))}
                    {recentJobs.length === 0 && <p style={{ fontSize: '0.8rem', color: '#64748b' }}>No recent analyses</p>}
                </div>
            </div>
        </aside>
    );
}
