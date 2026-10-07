/** Ecran 2 - Diagnostic AS-IS & Readiness. */
import { useState } from "react";

import { useAssessments, useReadiness, useSites } from "../api/queries";
import type { DimensionScore, Readiness } from "../api/types";
import { ReadinessGauge } from "../components/charts";
import DiagnosticDrawer from "../components/DiagnosticDrawer";
import { IconAlert, IconCheckSquare, IconDownload } from "../components/Icons";
import { Page, PageHeader } from "../components/Layout";
import { useAuth } from "../lib/auth";
import { Badge, Card, ErrorState, Loading } from "../components/ui";
import { formatDecimal, maturityColor } from "../lib/format";

/**
 * Export du diagnostic au format CSV.
 *
 * Le fichier est construit depuis les donnees deja chargees, sans appel supplementaire,
 * et remis par un blob : rien ne transite par l'URL.
 */
function exportCsv(readiness: Readiness, campaign: string) {
  const escape = (value: unknown) => {
    const text = value === null || value === undefined ? "" : String(value);
    return /[";\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  };

  const header = [
    "Axe", "Code", "Dimension", "Note sur 5", "Poids", "Confiance",
    "Instruite", "Critique", "Statut", "Preuve",
  ];
  const statut = (d: DimensionScore) =>
    !d.is_answered ? "A instruire" : d.is_blocking ? "Bloquante" : d.is_watch ? "Vigilance" : "Conforme";

  const rows = readiness.dimensions.map((d) => [
    d.axis === "technique" ? "Technique" : "Metier",
    d.dimension_code,
    d.dimension_label,
    d.is_answered ? d.score : "",
    d.weight,
    d.is_answered ? d.confidence : "",
    d.is_answered ? "oui" : "non",
    d.is_critical ? "oui" : "non",
    statut(d),
    d.evidence ?? "",
  ]);

  const synthese = [
    [],
    ["Score global sur 100", readiness.global_score],
    ["Niveau de maturite", `${readiness.level} - ${readiness.level_label}`],
    ["Moyenne technique sur 5", readiness.technical_average],
    ["Moyenne metier sur 5", readiness.business_average],
    ["Completion", `${readiness.answered_count}/${readiness.total_count}`],
  ];

  // Separateur point-virgule : Excel en locale francaise ouvre le fichier sans reglage.
  const csv = [header, ...rows, ...synthese]
    .map((row) => row.map(escape).join(";"))
    .join("\r\n");

  const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `diagnostic-readiness-${campaign.replace(/\s+/g, "-").toLowerCase()}.csv`;
  // L'ancre doit etre attachee au document : un lien detache ne declenche pas le
  // telechargement dans tous les navigateurs.
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  // La revocation est differee pour ne pas couper le telechargement en cours.
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

function MaturityScale({ levels }: { levels: { level: number; label: string }[] }) {
  const shades = ["#EEF3F0", "#CFE0D8", "#A8CEBC", "#6FBA99", "#2E9A72", "#0F5E44"];
  return (
    <div style={{ display: "grid", gridTemplateColumns: `repeat(${levels.length}, 1fr)`, gap: 12 }}>
      {levels.map((level) => (
        <div key={level.level}>
          <div style={{ height: 6, borderRadius: 3, background: shades[level.level] ?? "#EEF3F0" }} />
          <div
            style={{
              fontFamily: "var(--serif)",
              fontSize: 24,
              fontWeight: 600,
              marginTop: 12,
              textAlign: "center",
            }}
          >
            {level.level}
          </div>
          <div style={{ fontSize: 13, color: "var(--muted)", textAlign: "center" }}>{level.label}</div>
        </div>
      ))}
    </div>
  );
}

function DimensionList({
  dimensions,
  threshold,
}: {
  dimensions: DimensionScore[];
  threshold: number;
}) {
  return (
    <div>
      {dimensions.map((dimension) => {
        const color = maturityColor(dimension.score, dimension.is_blocking, dimension.is_watch);
        // Une dimension non instruite s'affiche comme telle : une barre vide et un tiret
        // valent mieux qu'un zero, qui se lirait comme une note.
        if (!dimension.is_answered) {
          return (
            <div className="bar-row" key={dimension.dimension_code}>
              <div className="bar-label muted">{dimension.dimension_label}</div>
              <div className="bar-track" />
              <div className="bar-value muted" title="Dimension non encore instruite">
                —
              </div>
            </div>
          );
        }
        return (
          <div className="bar-row" key={dimension.dimension_code}>
            <div className="bar-label" title={dimension.evidence ?? undefined}>
              {dimension.dimension_label}
            </div>
            <div className="bar-track">
              <div
                className="bar-fill"
                style={{ width: `${(dimension.score / 5) * 100}%`, background: color }}
              />
            </div>
            <div
              className="bar-value"
              style={{ color: dimension.score < threshold ? color : "var(--text)" }}
            >
              {dimension.score % 1 === 0 ? dimension.score : formatDecimal(dimension.score)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function Diagnostic() {
  const { can } = useAuth();
  const { data, isLoading, error } = useReadiness();
  const { data: assessments } = useAssessments(can("diagnostic.read"));
  const { data: sites } = useSites(can("site.read"));
  const [editing, setEditing] = useState(false);

  const campaign = assessments?.[0];
  const site = sites?.find((s) => s.id === campaign?.site_id);
  const technical = data?.dimensions.filter((d) => d.axis === "technique") ?? [];
  const business = data?.dimensions.filter((d) => d.axis === "metier") ?? [];

  return (
    <>
      <PageHeader
        title="Diagnostic AS-IS & Readiness"
        subtitle={
          campaign
            ? `${site?.name ?? "Toutes implantations"} · ${campaign.campaign ?? "campagne en cours"} · ${Math.round(data?.completion_rate ?? 0)} % complété`
            : "Aucune campagne enregistrée"
        }
        actions={
          <>
            <button
              type="button"
              className="btn"
              disabled={!data}
              onClick={() => data && exportCsv(data, campaign?.campaign ?? "campagne")}
            >
              <IconDownload size={17} />
              Exporter
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={!campaign}
              onClick={() => setEditing(true)}
              title={
                campaign
                  ? can("diagnostic.answer")
                    ? "Renseigner les dimensions de la campagne"
                    : "Consulter le questionnaire de la campagne"
                  : "Aucune campagne de diagnostic ouverte"
              }
            >
              <IconCheckSquare size={17} />
              {can("diagnostic.answer") ? "Poursuivre le diagnostic" : "Voir le questionnaire"}
            </button>
          </>
        }
      />
      <Page>
        {isLoading && <Loading label="Calcul du readiness..." />}
        {error && <ErrorState error={error} />}
        {data && (
          <div className="stack">
            <div className="grid grid-2">
              <Card dark>
                <div
                  style={{
                    fontSize: 12,
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                    color: "#8ba79a",
                    textAlign: "center",
                  }}
                >
                  Readiness global
                </div>
                <ReadinessGauge score={data.global_score} />
                <div style={{ textAlign: "center" }}>
                  <div style={{ color: "#3FBF8F", fontSize: 19, fontWeight: 600 }}>
                    Niveau {data.level} · {data.level_label}
                  </div>
                  <div style={{ color: "#9db3a8", fontSize: 13.5, marginTop: 6, lineHeight: 1.5 }}>
                    {data.level_description}
                  </div>
                </div>
              </Card>

              <Card title="Échelle de maturité (0 → 5)">
                <MaturityScale levels={data.maturity_scale} />

                {data.blocking_dimensions.length > 0 && (
                  <div className="alert alert-amber" style={{ marginTop: 26 }}>
                    <IconAlert size={19} style={{ flex: "0 0 19px", marginTop: 1 }} />
                    <div>
                      <b>
                        {data.blocking_dimensions.length} dimension
                        {data.blocking_dimensions.length > 1 ? "s" : ""} bloquante
                        {data.blocking_dimensions.length > 1 ? "s" : ""}
                      </b>{" "}
                      sous le seuil :{" "}
                      {data.blocking_dimensions
                        .map((d) => `${d.dimension_label} (${d.score})`)
                        .join(" et ")}
                      . À remédier avant tout passage en production.
                    </div>
                  </div>
                )}

                {data.watch_dimensions.length > 0 && (
                  <div className="alert alert-amber" style={{ marginTop: 12, background: "#F4F7F5", color: "var(--muted)" }}>
                    <IconAlert size={19} style={{ flex: "0 0 19px", marginTop: 1 }} />
                    <div>
                      Point de vigilance :{" "}
                      {data.watch_dimensions.map((d) => `${d.dimension_label} (${d.score})`).join(", ")}
                      . Non bloquant pour la production, à traiter dans le plan de conduite du changement.
                    </div>
                  </div>
                )}
              </Card>
            </div>

            <div className="grid grid-2-even">
              <Card
                title="Readiness technique"
                headExtra={
                  <span className="card-link" style={{ color: "var(--muted)" }}>
                    moy. <b style={{ color: "var(--text)" }}>{formatDecimal(data.technical_average)}</b>/5
                  </span>
                }
              >
                <DimensionList dimensions={technical} threshold={data.blocking_threshold} />
              </Card>

              <Card
                title="Readiness métier & organisationnel"
                headExtra={
                  <span className="card-link" style={{ color: "var(--muted)" }}>
                    moy. <b style={{ color: "var(--text)" }}>{formatDecimal(data.business_average)}</b>/5
                  </span>
                }
              >
                <DimensionList dimensions={business} threshold={data.blocking_threshold} />
              </Card>
            </div>

            <Card
              title="Preuves collectées"
              subtitle={`${data.answered_count} dimension${data.answered_count > 1 ? "s" : ""} instruite${
                data.answered_count > 1 ? "s" : ""
              } sur ${data.total_count} · chaque note est adossée à une preuve et pondérée par la confiance`}
            >
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Dimension</th>
                      <th>Axe</th>
                      <th>Note</th>
                      <th>Poids</th>
                      <th>Confiance</th>
                      <th>État</th>
                      <th>Preuve</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.dimensions.map((dimension) => (
                      <tr key={dimension.dimension_code}>
                        <td style={{ fontWeight: 500 }}>{dimension.dimension_label}</td>
                        <td className="muted">
                          {dimension.axis === "technique" ? "Technique" : "Métier"}
                        </td>
                        <td className={dimension.is_answered ? "num" : "muted"}>
                          {dimension.is_answered ? `${dimension.score}/5` : "—"}
                        </td>
                        <td className="muted">{formatDecimal(dimension.weight)}</td>
                        <td className="muted">
                          {dimension.is_answered ? `${Math.round(dimension.confidence * 100)} %` : "—"}
                        </td>
                        <td>
                          {!dimension.is_answered ? (
                            <Badge tone="badge-amber">À instruire</Badge>
                          ) : dimension.is_blocking ? (
                            <Badge tone="badge-red">Bloquante</Badge>
                          ) : dimension.is_watch ? (
                            <Badge tone="badge-amber">Vigilance</Badge>
                          ) : (
                            <span className="muted">Conforme</span>
                          )}
                        </td>
                        <td className="muted" style={{ minWidth: 300 }}>
                          {dimension.evidence ?? "—"}
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

      {editing && campaign && (
        <DiagnosticDrawer assessmentId={campaign.id} onClose={() => setEditing(false)} />
      )}
    </>
  );
}
