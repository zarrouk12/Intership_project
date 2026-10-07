/** Ecran 1 - Tableau de bord Direction. */
import { Link, useNavigate } from "react-router-dom";

import { useDashboard, useNotifications } from "../api/queries";
import type { KpiCardData, PortfolioRow } from "../api/types";
import { ImpactMatrix, MatrixLegend } from "../components/charts";
import {
  IconAlert,
  IconArrowUp,
  IconBell,
  IconEuro,
  IconFilter,
  IconLayers,
  IconPlus,
  IconTrend,
} from "../components/Icons";
import { Page, PageHeader } from "../components/Layout";
import { Badge, Card, ErrorState, Loading } from "../components/ui";
import { useAuth } from "../lib/auth";
import {
  STATUS_LABELS,
  STATUS_TONES,
  formatEuro,
  formatNumber,
  formatPercent,
} from "../lib/format";

const KPI_ICONS: Record<string, typeof IconLayers> = {
  active_projects: IconLayers,
  investment: IconEuro,
  roi: IconTrend,
  critical_risks: IconAlert,
};

const KPI_BADGE_STYLE: Record<string, { background: string; color: string }> = {
  active_projects: { background: "var(--accent-soft)", color: "var(--accent-dark)" },
  investment: { background: "var(--teal-soft)", color: "var(--teal)" },
  roi: { background: "var(--accent-soft)", color: "var(--accent-dark)" },
  critical_risks: { background: "var(--red-soft)", color: "var(--red)" },
};

function formatKpi(kpi: KpiCardData): string {
  if (kpi.unit === "EUR") return formatEuro(kpi.value);
  if (kpi.unit === "%") return formatPercent(kpi.value);
  return formatNumber(kpi.value);
}

function KpiTile({ kpi }: { kpi: KpiCardData }) {
  const Icon = KPI_ICONS[kpi.key] ?? IconLayers;
  const badge = KPI_BADGE_STYLE[kpi.key] ?? { background: "#f0f4f2", color: "var(--muted)" };
  return (
    <article className="kpi-card">
      <div className="kpi-top">
        <span className="kpi-label">{kpi.label}</span>
        <span className="kpi-badge" style={badge}>
          <Icon size={17} />
        </span>
      </div>
      <div className="kpi-value">{formatKpi(kpi)}</div>
      <div className={`kpi-hint ${kpi.tone === "negative" ? "tone-negative" : kpi.tone === "positive" ? "tone-positive" : ""}`}>
        {kpi.trend === "up" && <IconArrowUp size={14} />}
        {kpi.hint}
      </div>
    </article>
  );
}

function PhaseBars({ phases }: { phases: { code: string; label: string; count: number }[] }) {
  const max = Math.max(...phases.map((p) => p.count), 1);
  const colors: Record<string, string> = {
    qualification: "#8FBFAA",
    cadrage: "#1C6B7D",
    poc: "#A66A16",
    pilote: "#1E9C72",
    production: "#0F5E44",
  };
  return (
    <div>
      {phases.map((phase) => (
        <div className="phase-row" key={phase.code}>
          <div className="phase-head">
            <span>{phase.label}</span>
            <b>{phase.count}</b>
          </div>
          <div className="bar-track">
            <div
              className="bar-fill"
              style={{
                width: `${(phase.count / max) * 100}%`,
                background: colors[phase.code] ?? "var(--accent)",
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function TopPriorities({ rows }: { rows: PortfolioRow[] }) {
  const navigate = useNavigate();
  return (
    <div className="table-wrap">
      <table className="data">
        <thead>
          <tr>
            <th>Projet</th>
            <th>Département</th>
            <th>Type IA</th>
            <th>Phase</th>
            <th>Score</th>
            <th>Statut</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.id}
              className="clickable"
              onClick={() => navigate(`/fiches/${row.id}`)}
              title="Ouvrir la fiche projet"
            >
              <td style={{ fontWeight: 500 }}>{row.title}</td>
              <td className="muted">{row.department_name ?? "-"}</td>
              <td className="muted">{row.ai_type_label ?? "Non qualifié"}</td>
              <td className="muted">{row.phase_label}</td>
              <td className="num">{Math.round(row.priority_score)}</td>
              <td>
                <Badge tone={STATUS_TONES[row.status] ?? "badge-grey"}>
                  {STATUS_LABELS[row.status] ?? row.status}
                </Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Dashboard() {
  const { can } = useAuth();
  const { data, isLoading, error } = useDashboard();
  const { data: notifications } = useNotifications();
  const unread = notifications?.filter((n) => !n.is_read).length ?? 0;

  return (
    <>
      <PageHeader
        title="Tableau de bord — Direction"
        subtitle="Portefeuille de transformation IA · T3 2026"
        actions={
          <>
            {can("portfolio.read") && (
              <Link className="btn" to="/portefeuille">
                <IconFilter size={17} />
                Filtres
              </Link>
            )}
            <button type="button" className="btn btn-icon" aria-label="Notifications">
              <IconBell size={18} />
              {unread > 0 && <span className="dot" />}
            </button>
            {can("opportunity.create") && (
              <Link className="btn btn-primary" to="/opportunites/nouvelle">
                <IconPlus size={17} />
                Nouvelle opportunité
              </Link>
            )}
          </>
        }
      />
      <Page>
        {isLoading && <Loading label="Chargement du portefeuille..." />}
        {error && <ErrorState error={error} />}
        {data && (
          <div className="stack">
            <div className="grid grid-kpi">
              {data.kpis.map((kpi) => (
                <KpiTile key={kpi.key} kpi={kpi} />
              ))}
            </div>

            <div className="grid grid-2">
              <Card
                title="Matrice Impact × Faisabilité"
                subtitle="Taille de bulle = bénéfice attendu"
                headExtra={<MatrixLegend points={data.matrix} />}
              >
                <ImpactMatrix points={data.matrix} />
              </Card>

              <Card
                title="Répartition par phase TOGAF"
                subtitle={`${data.total_opportunities} projets · funnel opportunité → production`}
              >
                <PhaseBars phases={data.phases} />
              </Card>
            </div>

            <Card
              title="Top priorités du portefeuille"
              action={<Link to="/portefeuille">Voir tout le portefeuille →</Link>}
            >
              <TopPriorities rows={data.top_priorities.slice(0, 4)} />
            </Card>
          </div>
        )}
      </Page>
    </>
  );
}
