import React from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';
import { formatDataAge, humanizeRuntimeReason, normalizeRuntimeStatus, RUNTIME_STATUS_TOKENS } from '../runtimeStatus';

export function PageHeader({ eyebrow, title, description, actions }) {
  return <header className="page-heading"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{description && <p>{description}</p>}</div>{actions && <div className="page-actions">{actions}</div>}</header>;
}

export function MetricCard({ icon, label, value, detail, tone = 'blue' }) {
  return <article className={`metric-card metric-${tone}`}><div className="metric-card-top"><span>{label}</span><span className="metric-icon">{icon}</span></div><strong>{value}</strong>{detail && <small>{detail}</small>}</article>;
}

export function Panel({ title, subtitle, action, className = '', children }) {
  return <section className={`panel ${className}`}>{(title || action) && <div className="panel-heading"><div>{title && <h2>{title}</h2>}{subtitle && <p>{subtitle}</p>}</div>{action}</div>}{children}</section>;
}

export function StateMessage({ type = 'empty', children }) {
  return <div className={`state-message state-${type}`} role={type === 'error' ? 'alert' : 'status'}>{type === 'loading' ? <Loader2 className="spin" size={20} /> : type === 'error' ? <AlertCircle size={20} /> : null}<span>{children}</span></div>;
}

export function Badge({ children, tone = 'neutral' }) { return <span className={`ui-badge badge-${tone}`}>{children}</span>; }
export function RuntimeStatus({ status, ageSeconds, lastSuccessAt, reason, detail, compact = false }) {
  const normalized = normalizeRuntimeStatus(status);
  const token = RUNTIME_STATUS_TOKENS[normalized];
  const age = formatDataAge(ageSeconds);
  const timestamp = lastSuccessAt ? new Date(lastSuccessAt).toLocaleString('vi-VN') : null;
  const explanation = humanizeRuntimeReason(reason);
  const aria = [token.label, detail, timestamp ? `last success ${timestamp}` : null, age !== 'Not observed' ? age : null, explanation].filter(Boolean).join(', ');
  return <span className={`runtime-status runtime-status-${normalized}${compact ? ' runtime-status-compact' : ''}`} role="status" aria-label={aria} data-runtime-status={normalized}>
    <span className="runtime-status-badge"><i aria-hidden="true" />{token.label}</span>
    {!compact && <span className="runtime-status-detail">{detail && <strong>{detail}</strong>}{timestamp && <span>Last success {timestamp}</span>}<span>Age {age}</span>{explanation && <span>Reason {explanation}</span>}</span>}
  </span>;
}
export function formatNumber(value, digits = 0) { return value === null || value === undefined || Number.isNaN(Number(value)) ? '—' : Number(value).toLocaleString('vi-VN', { maximumFractionDigits: digits }); }
export function formatPercent(value, digits = 2) { return value === null || value === undefined || Number.isNaN(Number(value)) ? '—' : `${(Number(value) * 100).toLocaleString('vi-VN', { maximumFractionDigits: digits })}%`; }
