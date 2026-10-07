/** Ecran 5 - Fiche projet : contexte AS-IS, solution, KPI, business case, risques, decision. */
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "../api/client";
import { useGenerateSheet, useOpportunity, useProjectSheet } from "../api/queries";
import type { KpiProgress, SheetRisk } from "../api/types";
import {
  IconAlert,
  IconArrowLeft,
  IconBulb,
  IconCheck,
  IconClock,
  IconDownload,
  IconPencil,
  IconTrend,
} from "../components/Icons";
import { Page, PageHeader } from "../components/Layout";
import { Badge, Card, ErrorState, KeyValue, Loading, MetaItem } from "../components/ui";
import { useAuth } from "../lib/auth";
import {
  PHASE_LABELS,
  SEVERITY_LABELS,
  STATUS_LABELS,
  formatDate,
  formatDecimal,
  formatEuro,
  formatPercent,
  severityTone,
} from "../lib/format";

function SectionIcon({ children, tone }: { children: React.ReactNode; tone: string }) {
  return (
    <span
      style={{
        width: 32,
        height: 32,
        borderRadius: 9,
        display: "grid",
        placeItems: "center",
        background: tone,
        flex: "0 0 32px",
      }}
    >
      {children}
    </span>
  );
}

function KpiTile({ kpi }: { kpi: KpiProgress }) {
  const improving =
    kpi.baseline_value !== null &&
    kpi.baseline_value !== undefined &&
    kpi.target_value !== null &&
    kpi.target_value !== undefined;
  // Le delta n'est affiche que si le libelle de cible ne l'exprime pas deja.
  const targetLabel = kpi.target_label ?? "cible";
  const labelCarriesDelta = /[+\-−]\s*\d/.test(targetLabel);
  const delta =
    improving && kpi.baseline_value && !labelCarriesDelta
      ? ((kpi.target_value as number) - (kpi.baseline_value as number)) / (kpi.baseline_value as number)
      : null;

  return (
    <div className="stat-tile">
      <div className="label">{kpi.name}</div>
      <div className="value">
        <span style={{ color: "var(--red)" }}>
          {formatDecimal(kpi.baseline_value ?? 0)}
          {kpi.unit === "%" ? "%" : ""}
        </span>
        <span style={{ color: "var(--muted)", margin: "0 8px", fontWeight: 400 }}>→</span>
        <span style={{ color: "var(--accent)" }}>
          {formatDecimal(kpi.target_value ?? 0)}
          {kpi.unit === "%" ? "%" : ""}
        </span>
      </div>
      <div className="foot">
        {kpi.baseline_label ?? "baseline"} → {targetLabel}
        {delta !== null && (
          <>
            {" · "}
            {delta < 0 ? "−" : "+"}
            {Math.abs(Math.round(delta * 100))} %
          </>
        )}
      </div>
    </div>
  );
}

function RiskRow({ risk }: { risk: SheetRisk }) {
  return (
    <div className="list-row" title={risk.mitigations.join(" · ")}>
      <span>{risk.title}</span>
      <Badge tone={severityTone(risk.score)}>{SEVERITY_LABELS[risk.severity] ?? risk.severity}</Badge>
    </div>
  );
}

export default function ProjectSheet() {
  const { can } = useAuth();
  const { id } = useParams();
  const navigate = useNavigate();
  const opportunityId = id ? Number(id) : undefined;
  const { data: sheet, isLoading, error } = useProjectSheet(opportunityId);
  const { data: opportunity } = useOpportunity(opportunityId);
  const generate = useGenerateSheet();
  const [submitted, setSubmitted] = useState(false);

  // L'export passe par le client authentifie, puis s'ouvre depuis un blob : le jeton ne
  // transite jamais par l'URL. La page obtenue est imprimable en PDF depuis le navigateur.
  async function exportSheet() {
    if (!opportunityId) return;
    const response = await api.get(`/sheets/opportunity/${opportunityId}/export`, {
      params: { format: "html" },
      responseType: "blob",
    });
    const url = URL.createObjectURL(new Blob([response.data], { type: "text/html" }));
    window.open(url, "_blank", "noopener");
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  }

  return (
    <>
      <PageHeader
        leading={
          <button
            type="button"
            className="btn btn-icon"
            onClick={() => navigate(-1)}
            aria-label="Retour au portefeuille"
          >
            <IconArrowLeft size={18} />
          </button>
        }
        title={sheet?.title ?? "Fiche projet"}
        subtitle={sheet ? `Portefeuille · ${sheet.code}` : undefined}
        actions={
          <>
            {can("opportunity.update") && (
              <button
                type="button"
                className="btn"
                onClick={() => navigate(`/opportunites/${opportunityId}/modifier`)}
                disabled={!opportunityId}
              >
                <IconPencil size={17} />
                Modifier
              </button>
            )}
            <button type="button" className="btn" onClick={exportSheet} disabled={!sheet}>
              <IconDownload size={17} />
              Export Word / PDF
            </button>
            {can("sheet.write") && (
              <button
                type="button"
                className="btn btn-primary"
                disabled={!opportunityId || generate.isPending}
                onClick={async () => {
                  if (!opportunityId) return;
                  await generate.mutateAsync(opportunityId);
                  setSubmitted(true);
                }}
              >
                <IconCheck size={17} />
                {generate.isPending
                  ? "Envoi..."
                  : submitted
                    ? "Soumis au comité"
                    : "Soumettre au comité"}
              </button>
            )}
          </>
        }
      />
      <Page>
        {isLoading && <Loading label="Assemblage de la fiche projet..." />}
        {error && <ErrorState error={error} />}

        {sheet && (
          <div className="stack">
            <Card>
              <div className="meta-strip">
                <MetaItem label="Département" value={opportunity?.department_name ?? "—"} />
                <MetaItem label="Sponsor" value={sheet.identity.sponsor ?? "—"} />
                <MetaItem label="Owner métier" value={sheet.identity.business_owner ?? "—"} />
                <MetaItem label="Owner technique" value={sheet.identity.technical_owner ?? "—"} />
                <MetaItem
                  label="Statut"
                  value={
                    <Badge tone="badge-green">
                      {PHASE_LABELS[sheet.identity.phase] ?? sheet.identity.phase} —{" "}
                      {STATUS_LABELS[sheet.identity.status] ?? sheet.identity.status}
                    </Badge>
                  }
                />
              </div>
            </Card>

            <div className="grid grid-sheet">
              {/* -------------------------------------------------- colonne principale */}
              <div className="stack">
                <Card>
                  <header className="card-head">
                    <SectionIcon tone="#F0F4F2">
                      <IconClock size={17} />
                    </SectionIcon>
                    <div className="card-title">Contexte AS-IS</div>
                  </header>
                  <p style={{ margin: 0, lineHeight: 1.7 }}>{sheet.as_is.context ?? "Non renseigné."}</p>
                  {sheet.as_is.pain_points && (
                    <p style={{ marginBottom: 0, color: "var(--muted)" }}>
                      <b style={{ color: "var(--text)" }}>Points de douleur : </b>
                      {sheet.as_is.pain_points}
                    </p>
                  )}
                </Card>

                <Card>
                  <header className="card-head">
                    <SectionIcon tone="#F0F4F2">
                      <IconBulb size={17} />
                    </SectionIcon>
                    <div className="card-title">Solution recommandée</div>
                    <span style={{ marginLeft: "auto" }}>
                      <Badge tone="badge-green">
                        {sheet.recommendation.ai_type_label ?? "Non qualifié"}
                      </Badge>
                    </span>
                  </header>
                  <p style={{ marginTop: 0, lineHeight: 1.7 }}>
                    {sheet.recommendation.solution_pattern}
                  </p>
                  <p style={{ color: "var(--muted)", lineHeight: 1.7 }}>
                    {sheet.recommendation.rationale}
                  </p>

                  <div className="row" style={{ marginTop: 6 }}>
                    {sheet.recommendation.fired_rules
                      .filter((rule) => rule.satisfied)
                      .slice(0, 3)
                      .map((rule) => (
                        <span className="chip" key={rule.code}>
                          {rule.label} ✓
                        </span>
                      ))}
                    {sheet.recommendation.alternatives.slice(0, 1).map((alternative) => (
                      <span className="chip" key={alternative.ai_type}>
                        Alt. écartée : {alternative.label}
                      </span>
                    ))}
                  </div>

                  {sheet.recommendation.guardrails.length > 0 && (
                    <div className="alert alert-green" style={{ marginTop: 18 }}>
                      <IconCheck size={18} style={{ flex: "0 0 18px", marginTop: 2 }} />
                      <div>
                        <b>Garde-fous à mettre en place :</b>{" "}
                        {sheet.recommendation.guardrails.join(" · ")}
                      </div>
                    </div>
                  )}
                </Card>

                <Card>
                  <header className="card-head">
                    <SectionIcon tone="#F0F4F2">
                      <IconTrend size={17} />
                    </SectionIcon>
                    <div className="card-title">KPI & bénéfice</div>
                  </header>
                  {sheet.kpis.length === 0 ? (
                    <div className="state">Aucun KPI rattaché à cette opportunité.</div>
                  ) : (
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
                        gap: 14,
                      }}
                    >
                      {sheet.kpis.map((kpi) => (
                        <KpiTile key={kpi.id} kpi={kpi} />
                      ))}
                    </div>
                  )}
                </Card>

                <Card>
                  <header className="card-head">
                    <SectionIcon tone="var(--red-soft)">
                      <IconAlert size={17} style={{ color: "var(--red)" }} />
                    </SectionIcon>
                    <div className="card-title">Risques & conformité</div>
                  </header>
                  {sheet.risks.length === 0 ? (
                    <div className="state">Aucun risque déclaré.</div>
                  ) : (
                    sheet.risks.map((risk) => <RiskRow key={risk.title} risk={risk} />)
                  )}
                </Card>
              </div>

              {/* ------------------------------------------------------ colonne latérale */}
              <div className="stack">
                <Card dark>
                  <div
                    style={{
                      fontSize: 11.5,
                      letterSpacing: "0.1em",
                      textTransform: "uppercase",
                      color: "#8ba79a",
                      textAlign: "center",
                    }}
                  >
                    Score de priorité
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--serif)",
                      fontSize: 56,
                      fontWeight: 600,
                      textAlign: "center",
                      color: "#fff",
                      lineHeight: 1.1,
                      margin: "10px 0 4px",
                    }}
                  >
                    {Math.round(sheet.priority.priority_score)}
                  </div>
                  <div style={{ textAlign: "center", color: "#3FBF8F", fontSize: 14 }}>
                    Rang {sheet.priority.rank ?? "—"} / {sheet.priority.portfolio_size} · Vague{" "}
                    {sheet.priority.wave ?? "—"}
                  </div>
                  <div
                    style={{
                      borderTop: "1px solid rgba(255,255,255,0.1)",
                      margin: "18px 0 4px",
                    }}
                  />
                  {sheet.priority.contributions.map((contribution) => (
                    <KeyValue
                      key={contribution.criterion}
                      label={contribution.label}
                      value={Math.round(contribution.value)}
                    />
                  ))}
                  {sheet.priority.risk_penalty > 0 && (
                    <KeyValue
                      label="Pénalité de risque"
                      value={`− ${formatDecimal(sheet.priority.risk_penalty)}`}
                    />
                  )}
                </Card>

                {can("finance.read") && (
                <Card title="Business case">
                  <KeyValue
                    label={`TCO (${sheet.business_case.horizon_years} ans)`}
                    value={formatEuro(sheet.business_case.tco_eur)}
                  />
                  <KeyValue
                    label="Gains annuels"
                    value={
                      <span style={{ color: "var(--accent)" }}>
                        {formatEuro(sheet.business_case.annual_benefit_eur)}
                      </span>
                    }
                  />
                  <KeyValue
                    label="ROI"
                    value={
                      <span style={{ color: "var(--accent)" }}>
                        {formatPercent(sheet.business_case.roi_percent)}
                      </span>
                    }
                  />
                  <KeyValue
                    label="Payback"
                    value={
                      sheet.business_case.payback_months
                        ? `${formatDecimal(sheet.business_case.payback_months)} mois`
                        : "—"
                    }
                  />
                </Card>
                )}

                <Card title="Décision comité">
                  {can("sheet.approve") ? (
                    <>
                      <button
                        type="button"
                        className="btn btn-primary"
                        style={{ width: "100%", justifyContent: "center" }}
                      >
                        Go — lancer la vague {sheet.priority.wave ?? 1}
                      </button>
                      <button
                        type="button"
                        className="btn"
                        style={{ width: "100%", justifyContent: "center", marginTop: 10 }}
                      >
                        Renvoyer pour révision
                      </button>
                    </>
                  ) : (
                    <p className="muted" style={{ marginTop: 0, lineHeight: 1.6 }}>
                      La décision revient au comité. Votre rôle vous donne accès au dossier en
                      consultation.
                    </p>
                  )}
                  <div style={{ color: "var(--muted)", fontSize: 13, marginTop: 14, lineHeight: 1.6 }}>
                    Prochaine revue : {formatDate(sheet.project.next_gate_date)}
                    {sheet.project.next_gate_label ? ` · ${sheet.project.next_gate_label}` : ""}
                  </div>
                </Card>

                <Card title="Explicabilité">
                  <div style={{ fontSize: 13, color: "var(--muted)", lineHeight: 1.65 }}>
                    {sheet.priority.formula}
                  </div>
                  <Link className="card-link" to="/portefeuille" style={{ display: "inline-block", marginTop: 12 }}>
                    Ajuster les pondérations →
                  </Link>
                </Card>
              </div>
            </div>
          </div>
        )}
      </Page>
    </>
  );
}
