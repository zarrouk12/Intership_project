/**
 * M11 — Tableau de bord de département.
 *
 * Même écran pour un responsable et pour la Direction, mais pas le même contenu :
 * les agrégats sont calculés côté serveur sur le périmètre réel de l'utilisateur.
 */
import { Link, useNavigate } from "react-router-dom";

import { useDepartmentDashboard } from "../api/queries";
import type { KpiCardData, KpiProgress } from "../api/types";
import { IconPlus } from "../components/Icons";
import { Page, PageHeader } from "../components/Layout";
import { Badge, Card, ErrorState, Loading, StatTile } from "../components/ui";
import { useAuth } from "../lib/auth";
import {
  STATUS_LABELS,
  STATUS_TONES,
  formatDate,
  formatDecimal,
  formatEuro,
  formatNumber,
  severityTone,
} from "../lib/format";

function formatKpi(kpi: KpiCardData): string {
  if (kpi.unit === "EUR") return formatEuro(kpi.value);
  if (kpi.unit === "%") return `${formatDecimal(kpi.value)} %`;
  return formatNumber(kpi.value);
}

function KpiRow({ kpi }: { kpi: KpiProgress }) {
  const progress = kpi.progress_percent ?? 0;
  return (
    <div className="bar-row">
      <div className="bar-label">{kpi.name}</div>
      <div className="bar-track">
        <div
          className="bar-fill"
          style={{
            width: `${Math.max(0, Math.min(100, progress))}%`,
            background: progress >= 70 ? "var(--accent)" : progress >= 35 ? "#4FA383" : "var(--amber)",
          }}
        />
      </div>
      <div className="bar-value">{Math.round(progress)}%</div>
    </div>
  );
}

export default function DepartmentDashboard() {
  const navigate = useNavigate();
  const { can } = useAuth();
  const { data, isLoading, error } = useDepartmentDashboard(can("dashboard.department"));

  const perimeter = data?.scope.department_names.join(", ") || "Aucun département rattaché";

  return (
    <>
      <PageHeader
        title="Tableau de bord — Département"
        subtitle={data ? `Périmètre : ${perimeter}` : "Chargement du périmètre..."}
        actions={
          can("opportunity.create") ? (
            <Link className="btn btn-primary" to="/opportunites/nouvelle">
              <IconPlus size={17} />
              Nouvelle opportunité
            </Link>
          ) : undefined
        }
      />
      <Page>
        {isLoading && <Loading label="Consolidation du périmètre..." />}
        {error && <ErrorState error={error} />}

        {data && (
          <div className="stack">
            <div className="grid grid-kpi">
              {data.kpis.map((kpi) => (
                <StatTile
                  key={kpi.key}
                  label={kpi.label}
                  value={formatKpi(kpi)}
                  foot={kpi.hint ?? undefined}
                  valueColor={
                    kpi.tone === "positive"
                      ? "var(--accent)"
                      : kpi.tone === "negative"
                        ? "var(--red)"
                        : undefined
                  }
                />
              ))}
            </div>

            <div className="grid grid-2">
              <Card
                title="Opportunités du périmètre"
                subtitle="Classées par score de priorité"
              >
                {data.opportunities.length === 0 ? (
                  <div className="state">Aucune opportunité sur ce périmètre.</div>
                ) : (
                  <div className="table-wrap">
                    <table className="data">
                      <thead>
                        <tr>
                          <th>Opportunité</th>
                          <th>Type IA</th>
                          <th>Phase</th>
                          <th>Score</th>
                          <th>Statut</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.opportunities.map((row) => (
                          <tr
                            key={row.id}
                            className="clickable"
                            onClick={() => navigate(`/fiches/${row.id}`)}
                          >
                            <td style={{ fontWeight: 500 }}>
                              {row.title}
                              <div className="muted" style={{ fontSize: 12.5 }}>
                                {row.code}
                              </div>
                            </td>
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
                )}
              </Card>

              <Card title="Répartition par phase" subtitle="Funnel du périmètre">
                {data.phases.map((phase) => {
                  const max = Math.max(...data.phases.map((p) => p.count), 1);
                  return (
                    <div className="phase-row" key={phase.code}>
                      <div className="phase-head">
                        <span>{phase.label}</span>
                        <b>{phase.count}</b>
                      </div>
                      <div className="bar-track">
                        <div
                          className="bar-fill"
                          style={{ width: `${(phase.count / max) * 100}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </Card>
            </div>

            <div className="grid grid-2-even">
              <Card title="Projets en cours" subtitle="Avancement et prochaine gate">
                {data.projects.length === 0 ? (
                  <div className="state">Aucun projet sur ce périmètre.</div>
                ) : (
                  data.projects.map((project) => (
                    <div className="bar-row" key={project.id}>
                      <div className="bar-label">
                        {project.name}
                        <div className="muted" style={{ fontSize: 12 }}>
                          {project.phase_label}
                          {project.next_gate_date && ` · gate ${formatDate(project.next_gate_date)}`}
                        </div>
                      </div>
                      <div className="bar-track">
                        <div className="bar-fill" style={{ width: `${project.progress}%` }} />
                      </div>
                      <div className="bar-value">{Math.round(project.progress)}%</div>
                    </div>
                  ))
                )}
              </Card>

              <Card title="Risques du périmètre" subtitle="Classés par criticité">
                {data.risks.length === 0 ? (
                  <div className="state">Aucun risque déclaré.</div>
                ) : (
                  data.risks.map((risk) => (
                    <div className="list-row" key={risk.id}>
                      <span>
                        {risk.title}
                        <span className="muted" style={{ display: "block", fontSize: 12 }}>
                          {risk.category ?? "non catégorisé"} · {risk.status}
                        </span>
                      </span>
                      <Badge tone={severityTone(risk.score)}>{risk.score}</Badge>
                    </div>
                  ))
                )}
              </Card>
            </div>

            {data.kpi_progress.length > 0 && (
              <Card
                title="KPI métier"
                subtitle="Part de l'écart baseline vers cible déjà captée"
              >
                {data.kpi_progress.map((kpi) => (
                  <KpiRow key={kpi.id} kpi={kpi} />
                ))}
              </Card>
            )}
          </div>
        )}
      </Page>
    </>
  );
}
