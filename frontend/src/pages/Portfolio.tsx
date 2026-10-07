/** Ecran 4 - Portefeuille IA : table filtrable et repriorisation. */
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { usePortfolio, useReference } from "../api/queries";
import { IconTrend } from "../components/Icons";
import PrioritizeDrawer from "../components/PrioritizeDrawer";
import { Page, PageHeader } from "../components/Layout";
import { Badge, Card, ErrorState, Loading } from "../components/ui";
import { useAuth } from "../lib/auth";
import {
  STATUS_LABELS,
  STATUS_TONES,
  aiTypeColor,
  formatEuro,
  severityTone,
} from "../lib/format";

type SortKey = "priority_score" | "expected_benefit_eur" | "risk_score" | "title";

export default function Portfolio() {
  const navigate = useNavigate();
  const { can } = useAuth();
  const { data, isLoading, error } = usePortfolio();
  const { data: reference } = useReference();
  const [prioritizing, setPrioritizing] = useState(false);

  const [department, setDepartment] = useState("");
  const [aiType, setAiType] = useState("");
  const [phase, setPhase] = useState("");
  const [status, setStatus] = useState("");
  const [minScore, setMinScore] = useState(0);
  const [sortKey, setSortKey] = useState<SortKey>("priority_score");

  const departments = useMemo(
    () => [...new Set((data ?? []).map((r) => r.department_name).filter(Boolean))] as string[],
    [data],
  );

  const rows = useMemo(() => {
    const filtered = (data ?? []).filter(
      (row) =>
        (!department || row.department_name === department) &&
        (!aiType || row.ai_type === aiType) &&
        (!phase || row.phase === phase) &&
        (!status || row.status === status) &&
        row.priority_score >= minScore,
    );
    return [...filtered].sort((a, b) => {
      if (sortKey === "title") return a.title.localeCompare(b.title, "fr");
      const delta = (b[sortKey] as number) - (a[sortKey] as number);
      if (delta !== 0) return delta;
      // A score egal, on suit le rang calcule par le backend : sans cela deux
      // opportunites ex aequo s'afficheraient dans un ordre arbitraire.
      return (a.priority_rank ?? Infinity) - (b.priority_rank ?? Infinity);
    });
  }, [data, department, aiType, phase, status, minScore, sortKey]);

  const totalBenefit = rows.reduce((sum, row) => sum + row.expected_benefit_eur, 0);

  return (
    <>
      <PageHeader
        title="Portefeuille IA"
        subtitle={`${rows.length} opportunité${rows.length > 1 ? "s" : ""} · bénéfice attendu cumulé ${formatEuro(totalBenefit)}`}
        actions={
          can("portfolio.prioritize") ? (
            <button type="button" className="btn btn-primary" onClick={() => setPrioritizing(true)}>
              <IconTrend size={17} />
              Recalculer la priorisation
            </button>
          ) : undefined
        }
      />
      <Page>
        <Card
          title="Table du portefeuille"
          subtitle="Filtrez par département, type de solution, phase, score et statut"
        >
          <div className="filters">
            <div className="field">
              <label htmlFor="f-dept">Département</label>
              <select
                id="f-dept"
                className="select"
                value={department}
                onChange={(event) => setDepartment(event.target.value)}
              >
                <option value="">Tous</option>
                {departments.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label htmlFor="f-type">Type IA</label>
              <select
                id="f-type"
                className="select"
                value={aiType}
                onChange={(event) => setAiType(event.target.value)}
              >
                <option value="">Tous</option>
                {reference?.ai_types.map((item) => (
                  <option key={item.code} value={item.code}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label htmlFor="f-phase">Phase</label>
              <select
                id="f-phase"
                className="select"
                value={phase}
                onChange={(event) => setPhase(event.target.value)}
              >
                <option value="">Toutes</option>
                {reference?.phases.map((item) => (
                  <option key={item.code} value={item.code}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label htmlFor="f-status">Statut</label>
              <select
                id="f-status"
                className="select"
                value={status}
                onChange={(event) => setStatus(event.target.value)}
              >
                <option value="">Tous</option>
                {reference?.statuses.map((item) => (
                  <option key={item.code} value={item.code}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label htmlFor="f-score">Score minimum : {minScore}</label>
              <input
                id="f-score"
                type="range"
                min={0}
                max={100}
                step={5}
                value={minScore}
                onChange={(event) => setMinScore(Number(event.target.value))}
              />
            </div>

            <div className="field">
              <label htmlFor="f-sort">Tri</label>
              <select
                id="f-sort"
                className="select"
                value={sortKey}
                onChange={(event) => setSortKey(event.target.value as SortKey)}
              >
                <option value="priority_score">Score de priorité</option>
                <option value="expected_benefit_eur">Bénéfice attendu</option>
                <option value="risk_score">Niveau de risque</option>
                <option value="title">Ordre alphabétique</option>
              </select>
            </div>
          </div>

          {isLoading && <Loading />}
          {error && <ErrorState error={error} />}
          {rows.length === 0 && !isLoading && (
            <div className="state">Aucune opportunité ne correspond à ces filtres.</div>
          )}

          {rows.length > 0 && (
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Rang</th>
                    <th>Projet</th>
                    <th>Département</th>
                    <th>Type IA</th>
                    <th>Phase</th>
                    <th>Bénéfice</th>
                    <th>Risque</th>
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
                    >
                      <td className="muted" style={{ whiteSpace: "nowrap" }}>
                        {row.priority_rank ?? "-"}
                        {row.wave ? ` · V${row.wave}` : ""}
                      </td>
                      <td style={{ fontWeight: 500 }}>
                        {row.title}
                        <div className="muted" style={{ fontSize: 12.5 }}>
                          {row.code}
                        </div>
                      </td>
                      <td className="muted">{row.department_name ?? "-"}</td>
                      <td>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                          <span
                            className="legend-dot"
                            style={{ background: aiTypeColor(row.ai_type) }}
                          />
                          {row.ai_type_label ?? "Non qualifié"}
                        </span>
                      </td>
                      <td className="muted">{row.phase_label}</td>
                      <td className="muted">{formatEuro(row.expected_benefit_eur)}</td>
                      <td>
                        <Badge tone={severityTone(row.risk_score)}>{row.risk_score}</Badge>
                      </td>
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
      </Page>

      {prioritizing && (
        <PrioritizeDrawer rows={data ?? []} onClose={() => setPrioritizing(false)} />
      )}
    </>
  );
}
