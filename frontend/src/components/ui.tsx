/** Primitives d'interface partagees par les ecrans. */
import type { ReactNode } from "react";

import { IconAlert } from "./Icons";
import { errorMessage } from "../api/client";

export function Card({
  title,
  subtitle,
  action,
  children,
  dark = false,
  headExtra,
}: {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  dark?: boolean;
  headExtra?: ReactNode;
}) {
  return (
    <section className={dark ? "card card-dark" : "card"}>
      {(title || action || headExtra) && (
        <header className="card-head">
          <div>
            {title && <div className="card-title">{title}</div>}
            {subtitle && <div className="card-sub">{subtitle}</div>}
          </div>
          {headExtra}
          {action && <div className="card-link">{action}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

export function Badge({ tone = "badge-grey", children }: { tone?: string; children: ReactNode }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function Loading({ label = "Chargement..." }: { label?: string }) {
  return (
    <div className="state">
      <div className="spinner" />
      {label}
    </div>
  );
}

export function ErrorState({ error }: { error: unknown }) {
  return (
    <div className="alert alert-red">
      <IconAlert size={18} />
      <div>{errorMessage(error)}</div>
    </div>
  );
}

export function EmptyState({ label }: { label: string }) {
  return <div className="state">{label}</div>;
}

/** Barre de progression horizontale avec valeur a droite. */
export function BarRow({
  label,
  value,
  max,
  display,
  color = "var(--accent)",
  valueColor,
}: {
  label: string;
  value: number;
  max: number;
  display: string;
  color?: string;
  valueColor?: string;
}) {
  const ratio = max > 0 ? Math.max(0, Math.min(1, value / max)) : 0;
  return (
    <div className="bar-row">
      <div className="bar-label">{label}</div>
      <div className="bar-track">
        <div className="bar-fill" style={{ width: `${ratio * 100}%`, background: color }} />
      </div>
      <div className="bar-value" style={{ color: valueColor ?? "var(--text)" }}>
        {display}
      </div>
    </div>
  );
}

export function StatTile({
  label,
  value,
  foot,
  valueColor,
}: {
  label: string;
  value: ReactNode;
  foot?: string;
  valueColor?: string;
}) {
  return (
    <div className="stat-tile">
      <div className="label">{label}</div>
      <div className="value" style={valueColor ? { color: valueColor } : undefined}>
        {value}
      </div>
      {foot && <div className="foot">{foot}</div>}
    </div>
  );
}

export function KeyValue({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="kv">
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

export function MetaItem({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="meta-item">
      <div className="meta-label">{label}</div>
      <div className="meta-value">{value}</div>
    </div>
  );
}
