import React from 'react';

export default function StatusFooter() {
    return (
        <footer className="status-footer">
            <div className="status-left">
                <span><span className="status-dot"></span> API Status: <strong style={{ color: '#10b981' }}>Healthy</strong></span>
                <span>DB Latency: <strong>14ms</strong></span>
            </div>
            <div className="status-right">
                <span>Version 2.5.0-stable</span>
                <button style={{ background: 'none', border: 'none', color: '#64748b', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>Clear Logs</button>
            </div>
        </footer>
    );
}
