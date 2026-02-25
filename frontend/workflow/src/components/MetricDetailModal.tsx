import { useEffect, useState } from 'react';
import type { Metric } from '../types';
import { getMetricInsights } from '../api/workflowApi';

interface Props {
  metric: Metric;
  onClose: () => void;
  onInsightsLoaded?: (metricId: string, insights: string) => void;
}

interface InsightData {
  metric_name?: string;
  context_title?: string;
  context_description?: string;
  impact_analysis?: string;
  recommended_targets?: {
    healthy?: string;
    warning?: string;
    critical?: string;
  };
  correlations?: string[];
  improvement_strategies?: string[];
  stakeholders?: string[];
  risk_signals?: string;
  technical_intel?: string;
  // Legacy fields
  business_context?: string;
  why_it_matters?: string;
  codebase_inferred_insights?: string;
}

export default function MetricDetailModal({ metric, onClose, onInsightsLoaded }: Props) {
  const [insights, setInsights] = useState<InsightData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Parse existing insights or fetch them
  useEffect(() => {
    if (metric.insights) {
      try {
        setInsights(jsonParse(metric.insights));
      } catch {
        setInsights(null);
      }
      return;
    }

    // Fetch insights on-demand
    setLoading(true);
    setError(null);
    getMetricInsights(metric.id)
      .then((res) => {
        if (res.insights) {
          setInsights(res.insights);
          onInsightsLoaded?.(metric.id, JSON.stringify(res.insights));
        } else {
          setError('No insights generated');
        }
      })
      .catch((err) => setError(err.message || 'Failed to load insights'))
      .finally(() => setLoading(false));
  }, [metric.id, metric.insights, onInsightsLoaded]);

  // Utility to parse JSON safely (handles double encoding if present)
  function jsonParse(str: string) {
    try {
      const first = JSON.parse(str);
      if (typeof first === 'string') return JSON.parse(first);
      return first;
    } catch {
      return null;
    }
  }

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onClose]);

  return (
    <div className="mdm-overlay" onClick={onClose}>
      <div className="mdm-container" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="mdm-header">
          <div className="mdm-header-left">
            <h2 className="mdm-title">{metric.name}</h2>
            <div className="mdm-badges">
              {metric.category && (
                <span className="mdm-badge mdm-badge-category">{metric.category}</span>
              )}
              <span className="mdm-badge mdm-badge-type">{metric.data_type}</span>
            </div>
          </div>
          <button className="mdm-close-btn" onClick={onClose}>&times;</button>
        </div>

        <div className="mdm-content">
          {/* Description */}
          {metric.description && (
            <div className="mdm-desc-box">
              <p>{metric.description}</p>
            </div>
          )}

          {/* Source Info Row */}
          <div className="mdm-info-row">
            {metric.suggested_source && (
              <div className="mdm-info-chip">
                <span className="mdm-chip-label">Source</span>
                <span className="mdm-chip-value">{metric.suggested_source}</span>
              </div>
            )}
            {metric.source_platform && (
              <div className="mdm-info-chip">
                <span className="mdm-chip-label">Platform</span>
                <span className="mdm-chip-value">{metric.source_platform}</span>
              </div>
            )}
            {metric.source_table && (
              <div className="mdm-info-chip">
                <span className="mdm-chip-label">Reference</span>
                <span className="mdm-chip-value mdm-mono">{metric.source_table}</span>
              </div>
            )}
          </div>

          {/* Latest Value */}
          {metric.entries && metric.entries.length > 0 && (
            <div className="mdm-latest-strip">
              <div className="mdm-latest-item">
                <span className="mdm-latest-label">Current Value</span>
                <span className="mdm-latest-value">{metric.entries[0].value}</span>
              </div>
              <div className="mdm-latest-item">
                <span className="mdm-latest-label">Last Recorded</span>
                <span className="mdm-latest-date">
                  {new Date(metric.entries[0].recorded_at).toLocaleDateString(undefined, {
                    month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit'
                  })}
                </span>
              </div>
            </div>
          )}

          {/* Divider */}
          <div className="mdm-divider">
            <span>AI Strategic Analytics</span>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="mdm-loading">
              <div className="mdm-spinner" />
              <p>Performing deep codebase analysis...</p>
              <p className="mdm-loading-sub">Inferring architectural constraints and business impact</p>
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div className="mdm-error-box">
              <p>{error}</p>
            </div>
          )}

          {/* Insights Content */}
          {insights && !loading && (
            <div className="mdm-insights">

              {/* Technical Intel / Codebase Inferred */}
              {(insights.technical_intel || insights.codebase_inferred_insights) && (
                <div className="mdm-card mdm-card-code">
                  <div className="mdm-card-header">
                    <span className="mdm-card-icon">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <polyline points="16 18 22 12 16 6"></polyline>
                        <polyline points="8 6 2 12 8 18"></polyline>
                      </svg>
                    </span>
                    <h3>Architectural Intel</h3>
                  </div>
                  <div className="mdm-code-insight">
                    {insights.technical_intel || insights.codebase_inferred_insights}
                  </div>
                </div>
              )}

              {/* Context Description */}
              {(insights.context_description || insights.business_context) && (
                <div className="mdm-card">
                  <div className="mdm-card-header">
                    <span className="mdm-card-icon">&#9670;</span>
                    <h3>{insights.context_title || 'Strategic Context'}</h3>
                  </div>
                  <p>{insights.context_description || insights.business_context}</p>
                </div>
              )}

              {/* Impact Analysis */}
              {(insights.impact_analysis || insights.why_it_matters) && (
                <div className="mdm-card mdm-card-accent">
                  <div className="mdm-card-header">
                    <span className="mdm-card-icon">&#9888;</span>
                    <h3>Domain Impact Assessment</h3>
                  </div>
                  <p>{insights.impact_analysis || insights.why_it_matters}</p>
                </div>
              )}

              {/* Recommended Targets */}
              {insights.recommended_targets && (
                <div className="mdm-card">
                  <div className="mdm-card-header">
                    <span className="mdm-card-icon">&#9678;</span>
                    <h3>Performance Thresholds</h3>
                  </div>
                  <div className="mdm-thresholds">
                    <div className="mdm-threshold mdm-threshold-healthy">
                      <div className="mdm-threshold-dot" />
                      <div>
                        <strong>Healthy</strong>
                        <p>{insights.recommended_targets.healthy}</p>
                      </div>
                    </div>
                    <div className="mdm-threshold mdm-threshold-warning">
                      <div className="mdm-threshold-dot" />
                      <div>
                        <strong>Warning</strong>
                        <p>{insights.recommended_targets.warning}</p>
                      </div>
                    </div>
                    <div className="mdm-threshold mdm-threshold-critical">
                      <div className="mdm-threshold-dot" />
                      <div>
                        <strong>Critical</strong>
                        <p>{insights.recommended_targets.critical}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Correlations */}
              {insights.correlations && insights.correlations.length > 0 && (
                <div className="mdm-card">
                  <div className="mdm-card-header">
                    <span className="mdm-card-icon">&#8644;</span>
                    <h3>Inter-Metric Correlations</h3>
                  </div>
                  <ul className="mdm-bullet-list">
                    {insights.correlations.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Improvement Strategies */}
              {insights.improvement_strategies && insights.improvement_strategies.length > 0 && (
                <div className="mdm-card">
                  <div className="mdm-card-header">
                    <span className="mdm-card-icon">&#10148;</span>
                    <h3>Strategic Improvement Plan</h3>
                  </div>
                  <div className="mdm-strategies">
                    {insights.improvement_strategies.map((s, i) => (
                      <div key={i} className="mdm-strategy-item">
                        <span className="mdm-strategy-num">{i + 1}</span>
                        <p>{s}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Risk Signals */}
              {insights.risk_signals && (
                <div className="mdm-card mdm-card-risk">
                  <div className="mdm-card-header">
                    <span className="mdm-card-icon">&#9888;</span>
                    <h3>Critical Risk Signals</h3>
                  </div>
                  <p>{insights.risk_signals}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
