/** Ecran 6 - Valeur & ROI : KPI avant/apres, ROI, payback, impact P&L. */
import { useNavigate } from "react-router-dom";

import { useValueDashboard } from "../api/queries";
import type { KpiProgress } from "../api/types";
import { DepartmentValueChart, RoiRankingChart } from "../components/charts";
import { Page, PageHeader } from "../components/Layout";
import { Card, ErrorState, Loading, StatTile } from "../components/ui";
import { formatDecimal, formatEuro, formatPercent } from "../lib/format";

function KpiBeforeAfter({ kpi }: { kpi: KpiProgress }) {
  const baseline = kpi.baseline_value ?? 0;
  const target = kpi.target_value ?? 0;
  const current = kpi.current_value ?? baseline;
  const progress = kpi.progress_percent ?? 0;

  return (
    <div className="stat-tile">
      <div className="label">{kpi.name}</div>
      <div className="value" style={{ fontSize: 22 }}>
        <span style={{ color: "var(--muted)" }}>
          {formatDecimal(baseline)}
          {kpi.unit === "%" ? " %" : ""}
        </span>
        <span style={{ color: "var(--muted)", margin: "0 8px", fontWeight: 400 }}>→</span>
        <span style={{ color: "var(--accent)" }}>
          {formatDecimal(current)}
          {kpi.unit === "%" ? " %" : ""}
        </span>
        <span style={{ color: "var(--muted)", margin: "0 8px", fontWeight: 400, fontSize: 16 }}>
          cible {formatDecimal(target)}
          {kpi.unit === "%" ? " %" : ""}
        </span>
      </div>
      <div className="bar-track" style={{ marginTop: 6 }}>
        <div
          className="bar-fill"
          style={{
            width: `${Math.max(0, Math.min(100, progress))}%`,
            background: progress >= 70 ? "var(--accent)" : progress >= 35 ? "#4FA383" : "var(--amber)",
          }}
        />
      </div>
      <div className="foot" style={{ marginTop: 8 }}>
        {Math.round(progress)} % de l'écart baseline → cible déjà capté
      </div>
    </div>
  );
}

export default function Value() {
  const { data, isLoading, error } = useValueDashboard();
  const navigate = useNavigate();

  return (
    <>
      <PageHeader
        title="Valeur & ROI"
        subtitle="Business cases consolidés sur un horizon de 3 ans"
      />
      <Page>
        {isLoading && <Loading label="Consolidation des business cases..." />}
        {error && <ErrorState error={error} />}

        {data && (
          <div className="stack">
            <div className="grid grid-kpi">
              <StatTile
                label="Investissement total (TCO 3 ans)"
                value={formatEuro(data.portfolio.tco_eur)}
                foot={`${data.portfolio.projects} business cases chiffrés`}
              />
              <StatTile
                label="Gains annuels attendus"
                value={formatEuro(data.portfolio.annual_benefit_eur)}
                foot={`Soit ${formatEuro(data.portfolio.cumulated_benefit_eur)} cumulés sur 3 ans`}
                valueColor="var(--accent)"
              />
              <StatTile
                label="ROI portefeuille"
                value={formatPercent(data.portfolio.roi_percent)}
                foot={`Valeur nette ${formatEuro(data.portfolio.net_value_eur)}`}
                valueColor="var(--accent)"
              />
              <StatTile
                label="Payback moyen"
                value={
                  data.portfolio.average_payback_months
                    ? `${formatDecimal(data.portfolio.average_payback_months)} mois`
                    : "—"
                }
                foot="Récupération de l'investissement initial"
              />
            </div>

            <div className="grid grid-2-even">
              <Card
                title="Gains annuels par département"
                subtitle="Répartition de la valeur attendue"
              >
                <DepartmentValueChart data={data.by_department} />
              </Card>

              <Card title="Classement ROI par projet" subtitle="Horizon 3 ans, huit premiers">
                <RoiRankingChart data={data.roi_ranking} />
              </Card>
            </div>

            <Card
              title="KPI suivis — avant / après"
              subtitle="Valeur mesurée par rapport à la baseline et à la cible"
            >
              {data.kpis.length === 0 ? (
                <div className="state">Aucun KPI avec baseline renseignée.</div>
              ) : (
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
                    gap: 14,
                  }}
                >
                  {data.kpis.map((kpi) => (
                    <KpiBeforeAfter key={kpi.id} kpi={kpi} />
                  ))}
                </div>
              )}
            </Card>

            <Card title="Détail par projet" subtitle="TCO, gains annuels, ROI et payback">
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Projet</th>
                      <th>Département</th>
                      <th>TCO 3 ans</th>
                      <th>Gains annuels</th>
                      <th>ROI</th>
                      <th>Payback</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.roi_ranking.map((row) => (
                      <tr
                        key={row.id}
                        className="clickable"
                        onClick={() => navigate(`/fiches/${row.id}`)}
                      >
                        <td style={{ fontWeight: 500 }}>{row.title}</td>
                        <td className="muted">{row.department_name ?? "-"}</td>
                        <td className="muted">{formatEuro(row.tco_eur)}</td>
                        <td className="muted">{formatEuro(row.annual_benefit_eur)}</td>
                        <td className="num">{formatPercent(row.roi_percent, 1)}</td>
                        <td className="muted">
                          {row.payback_months ? `${formatDecimal(row.payback_months)} mois` : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        )}
      </Page>
    </>
  );
}
