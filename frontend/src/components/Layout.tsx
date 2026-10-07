/**
 * Coquille applicative : sidebar sombre fixe, topbar, zone de contenu scrollable.
 *
 * La navigation est construite à partir des permissions renvoyées par `/auth/me`.
 * Une entrée n'apparaît que si son écran est réellement accessible, ce qui évite de
 * proposer un lien qui mènerait à un refus du backend.
 */
import { useState } from "react";
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { useDashboard, useDepartmentDashboard } from "../api/queries";
import { useAuth } from "../lib/auth";
import { formatDate, initials } from "../lib/format";
import {
  IconChart,
  IconCheckSquare,
  IconCross,
  IconDashboard,
  IconFile,
  IconLayers,
  IconLogout,
  IconPie,
  IconPulse,
  IconSettings,
  IconShield,
} from "./Icons";

interface NavEntry {
  to: string;
  label: string;
  icon: typeof IconDashboard;
  end?: boolean;
  /** Permission requise pour voir l'entrée. */
  permission?: string;
  /** Au moins une de ces permissions suffit. */
  anyOf?: string[];
  section?: string;
}

const NAV: NavEntry[] = [
  { to: "/", label: "Tableau de bord", icon: IconDashboard, end: true,
    anyOf: ["dashboard.direction", "dashboard.department"] },
  { to: "/diagnostic", label: "Diagnostic & Readiness", icon: IconPulse, permission: "diagnostic.read" },
  { to: "/opportunites", label: "Opportunités", icon: IconCheckSquare, permission: "opportunity.read" },
  { to: "/architecture", label: "Architecture & données", icon: IconLayers,
    anyOf: ["architecture.manage", "data.manage"] },
  { to: "/portefeuille", label: "Portefeuille IA", icon: IconChart, permission: "portfolio.read" },
  { to: "/fiches", label: "Fiches projet", icon: IconFile, permission: "sheet.read" },
  { to: "/valeur", label: "Valeur & ROI", icon: IconPie, permission: "finance.read" },
  { to: "/administration", label: "Administration", icon: IconSettings, section: "Organisation",
    anyOf: ["admin.access", "user.read", "role.read"] },
  { to: "/audit", label: "Journal d'audit", icon: IconShield, section: "Organisation",
    permission: "audit.read" },
];

function Sidebar() {
  const { user, logout, can, canAny, isOrganizationWide } = useAuth();

  // Le bandeau de readiness n'est chargé que si l'utilisateur a droit au diagnostic.
  const canSeeDirection = can("dashboard.direction");
  const { data: direction } = useDashboard(canSeeDirection);
  const { data: department } = useDepartmentDashboard(!canSeeDirection && can("dashboard.department"));
  const readiness = direction?.readiness_global ?? null;

  const visible = NAV.filter((entry) => {
    if (entry.permission) return can(entry.permission);
    if (entry.anyOf) return canAny(...entry.anyOf);
    return true;
  });

  const principal = visible.filter((entry) => !entry.section);
  const organisation = visible.filter((entry) => entry.section === "Organisation");

  const scopeLabel = isOrganizationWide
    ? user?.organization.name
    : user?.departments.map((d) => d.name).join(", ") || "Périmètre restreint";

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">
          <IconCross size={22} />
        </div>
        <div>
          <div className="brand-name">{user?.organization.name ?? "Medicacom"}</div>
          <div className="brand-sub">AOI Transformation</div>
        </div>
      </div>

      <nav className="nav">
        {principal.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")}
          >
            <Icon size={19} />
            {label}
          </NavLink>
        ))}

        {organisation.length > 0 && (
          <>
            <div className="nav-section">Organisation</div>
            {organisation.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")}
              >
                <Icon size={19} />
                {label}
              </NavLink>
            ))}
          </>
        )}
      </nav>

      <div className="sidebar-footer">
        {readiness !== null && (
          <div className="readiness-chip">
            <div className="readiness-chip-label">Readiness global</div>
            <div className="readiness-chip-value">
              {Math.round(readiness)} <span>/100</span>
            </div>
            <div className="readiness-chip-bar">
              <i style={{ width: `${Math.max(0, Math.min(100, readiness))}%` }} />
            </div>
          </div>
        )}

        {!canSeeDirection && department && (
          <div className="readiness-chip">
            <div className="readiness-chip-label">Périmètre</div>
            <div className="readiness-chip-value" style={{ fontSize: 17, lineHeight: 1.35 }}>
              {/* Enumerer les huit departements d'une organisation n'apprend rien :
                  on ne detaille que lorsque le perimetre est reellement restreint. */}
              {department.scope.is_organization_wide
                ? (user?.organization.name ?? "Toute l'organisation")
                : department.scope.department_names.join(", ") || "Non rattaché"}
            </div>
            {!department.scope.is_organization_wide && (
              <div className="readiness-chip-label" style={{ marginTop: 6 }}>
                {department.scope.department_names.length} département
                {department.scope.department_names.length > 1 ? "s" : ""}
              </div>
            )}
          </div>
        )}

        {user && (
          <div className="user-block">
            <div className="avatar">{initials(user.full_name)}</div>
            <div style={{ minWidth: 0 }}>
              <div className="user-name">{user.full_name}</div>
              <div className="user-role" title={scopeLabel ?? undefined}>
                {user.primary_role?.label ?? user.job_title ?? "Utilisateur"}
              </div>
            </div>
            <button
              type="button"
              className="logout"
              onClick={logout}
              style={{ marginLeft: "auto" }}
              aria-label="Se déconnecter"
              title="Se déconnecter"
            >
              <IconLogout size={18} />
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}

/** Pastille d'identité affichée dans la topbar, avec le détail des droits au clic. */
export function ProfileChip() {
  const { user, isReadOnly } = useAuth();
  const [open, setOpen] = useState(false);
  if (!user) return null;

  const scope = user.scope.is_organization_wide
    ? user.organization.name
    : user.departments.map((d) => d.name).join(", ") || "Aucun rattachement";

  return (
    <div className="profile">
      <button type="button" className="profile-trigger" onClick={() => setOpen((v) => !v)}>
        <span className="avatar avatar-sm">{initials(user.full_name)}</span>
        <span className="profile-text">
          <span className="profile-name">{user.full_name}</span>
          <span className="profile-role">
            {user.primary_role?.label ?? "Utilisateur"} · {scope}
          </span>
        </span>
      </button>

      {open && (
        <>
          <div className="profile-backdrop" onClick={() => setOpen(false)} />
          <div className="profile-menu" role="dialog" aria-label="Mon profil">
            <div className="profile-menu-head">
              <div style={{ fontWeight: 600 }}>{user.full_name}</div>
              <div className="muted" style={{ fontSize: 12.5 }}>
                {user.email}
              </div>
            </div>

            <dl className="profile-grid">
              <dt>Organisation</dt>
              <dd>{user.organization.name}</dd>

              <dt>Rôle{user.roles.length > 1 ? "s" : ""}</dt>
              <dd>{user.roles.map((r) => r.label).join(", ") || "Aucun"}</dd>

              <dt>Périmètre</dt>
              <dd>
                {user.scope.level_label}
                {isReadOnly && <span className="badge badge-grey" style={{ marginLeft: 8 }}>Lecture seule</span>}
              </dd>

              <dt>Département{user.departments.length > 1 ? "s" : ""}</dt>
              <dd>{user.departments.map((d) => d.name).join(", ") || "—"}</dd>

              <dt>Site{user.sites.length > 1 ? "s" : ""}</dt>
              <dd>{user.sites.map((s) => s.name).join(", ") || "—"}</dd>

              <dt>Dernière connexion</dt>
              <dd>{formatDate(user.last_login_at)}</dd>
            </dl>

            <div className="profile-perms">
              <div className="profile-perms-title">
                Permissions actives ({user.permissions.length})
              </div>
              <div className="profile-perms-list">
                {user.permissions.map((code) => (
                  <code key={code}>{code}</code>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
  leading,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  leading?: ReactNode;
}) {
  return (
    <header className="topbar">
      {leading}
      <div>
        <h1>{title}</h1>
        {subtitle && <div className="topbar-sub">{subtitle}</div>}
      </div>
      <div className="topbar-actions">
        {actions}
        <ProfileChip />
      </div>
    </header>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="app">
      <Sidebar />
      <div className="main">{children}</div>
    </div>
  );
}

export function Page({ children }: { children: ReactNode }) {
  return <div className="content">{children}</div>;
}
