import React from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';

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
export function formatNumber(value, digits = 0) { return value === null || value === undefined || Number.isNaN(Number(value)) ? '—' : Number(value).toLocaleString('vi-VN', { maximumFractionDigits: digits }); }
export function formatPercent(value, digits = 2) { return value === null || value === undefined || Number.isNaN(Number(value)) ? '—' : `${(Number(value) * 100).toLocaleString('vi-VN', { maximumFractionDigits: digits })}%`; }
