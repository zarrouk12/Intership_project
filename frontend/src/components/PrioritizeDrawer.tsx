/**
 * M7 — Repriorisation du portefeuille avec pondérations réglables.
 *
 * Le bouton « Recalculer la priorisation » envoyait toujours les poids par défaut : le
 * classement ne pouvait donc jamais changer, et l'action paraissait sans effet. Ce
 * panneau expose les six critères, laisse ajuster leur poids, puis affiche les
 * mouvements de rang effectivement produits.
 *
 * Les poids sont renormalisés à 1 côté serveur : ce qui compte est leur rapport, pas
 * leur somme. Le pourcentage affiché ici reprend ce calcul pour que l'écran dise la
 * même chose que le backend.
 */
import { useMemo, useState } from "react";

import { errorMessage } from "../api/client";
import { usePrioritize, useReference } from "../api/queries";
import type { PortfolioRow, PrioritizedItem } from "../api/types";
import { IconAlert, IconArrowUp, IconTrend } from "./Icons";
import { ErrorState } from "./ui";

const CRITERIA: { key: string; label: string; help: string }[] = [
  { key: "impact_business", label: "Impact métier", help: "Bénéfice opérationnel attendu" },
  { key: "impact_financial", label: "Impact financier / P&L", help: "Gains chiffrés et effet sur le résultat" },
  { key: "feasibility", label: "Faisabilité technique", help: "Données, compétences, intégration" },
  { key: "alignment", label: "Alignement stratégique", help: "Cohérence avec les priorités du groupe" },
  { key: "readiness", label: "Readiness organisationnel", help: "Capacité à absorber le changement" },
  { key: "synergies", label: "Synergies", help: "Réutilisation entre départements" },
];

const DEFAULTS: Record<string, number> = {
  impact_business: 0.25,
  impact_financial: 0.2,
  feasibility: 0.2,
  alignment: 0.15,
  readiness: 0.1,
  synergies: 0.1,
};

/** Mouvement de rang d'une opportunité entre l'état précédent et le nouveau. */
interface Movement {
  item: PrioritizedItem;
  previousRank: number | null;
  delta: number;
}

function MovementBadge({ delta }: { delta: number }) {
  if (delta === 0) return <span className="muted">—</span>;
  const up = delta > 0;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 3,
        color: up ? "var(--accent)" : "var(--red)",
        fontWeight: 600,
        fontVariantNumeric: "tabular-nums",
      }}
    >
      <IconArrowUp size={13} style={up ? undefined : { transform: "rotate(180deg)" }} />
      {Math.abs(delta)}
    </span>
  );
}

export default function PrioritizeDrawer({
  rows,
  onClose,
}: {
  rows: PortfolioRow[];
  onClose: () => void;
}) {
  const { data: reference } = useReference();
  const prioritize = usePrioritize();

  const [weights, setWeights] = useState<Record<string, number>>({ ...DEFAULTS });
  const [waveSize, setWaveSize] = useState(6);
  const [applySynergies, setApplySynergies] = useState(false);
  const [result, setResult] = useState<Movement[] | null>(null);
  const [appliedWeights, setAppliedWeights] = useState<Record<string, number> | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Rangs actuels, relevés avant le recalcul pour mesurer les mouvements.
  const previousRanks = useMemo(() => {
    const map = new Map<number, number>();
    rows.forEach((row) => {
      if (row.priority_rank) map.set(row.id, row.priority_rank);
    });
    return map;
  }, [rows]);

  const total = Object.values(weights).reduce((sum, value) => sum + value, 0);
  const share = (key: string) => (total > 0 ? (weights[key] / total) * 100 : 0);
  const isDefault = CRITERIA.every((c) => Math.abs(share(c.key) / 100 - DEFAULTS[c.key]) < 0.001);

  async function run() {
    setError(null);
    try {
      const data = await prioritize.mutateAsync({
        weights,
        wave_size: waveSize,
        apply_synergies: applySynergies,
      });
      setAppliedWeights(data.weights);
      setResult(
        data.items.map((item) => {
          const previous = previousRanks.get(item.id) ?? null;
          return {
            item,
            previousRank: previous,
            // Un rang qui baisse en valeur est une montée dans le classement.
            delta: previous ? previous - item.priority_rank : 0,
          };
        }),
      );
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  const moved = result?.filter((m) => m.delta !== 0) ?? [];

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <div className="drawer drawer-wide" role="dialog" aria-label="Recalculer la priorisation">
        <div className="drawer-head">
          <div style={{ flex: 1 }}>
            <div className="card-title">Recalculer la priorisation</div>
            <div className="card-sub">
              {rows.length} opportunités · pondérations du score de priorité
            </div>
          </div>
        </div>

        <div className="drawer-body">
          {error && <ErrorState error={new Error(error)} />}

          <div className="readonly-banner" style={{ marginBottom: 20 }}>
            <IconAlert size={16} />
            Les poids sont renormalisés à 100 % : seul leur rapport compte. La pénalité de
            risque, égale à probabilité × impact, reste appliquée après pondération.
          </div>

          <h3 className="section-title">Pondération des critères</h3>
          {CRITERIA.map((criterion) => (
            <div className="weight-row" key={criterion.key}>
              <div>
                <div className="weight-label">{criterion.label}</div>
                <div className="weight-help">{criterion.help}</div>
              </div>
              <input
                type="range"
                min={0}
                max={0.5}
                step={0.01}
                value={weights[criterion.key]}
                onChange={(event) =>
                  setWeights((previous) => ({
                    ...previous,
                    [criterion.key]: Number(event.target.value),
                  }))
                }
                aria-label={`Poids de ${criterion.label}`}
              />
              <div className="weight-value">
                {share(criterion.key).toFixed(1)} %
                {Math.abs(share(criterion.key) / 100 - DEFAULTS[criterion.key]) >= 0.005 && (
                  <span className="weight-default">déf. {(DEFAULTS[criterion.key] * 100).toFixed(0)} %</span>
                )}
              </div>
            </div>
          ))}

          <div className="row" style={{ marginTop: 6 }}>
            <button
              type="button"
              className="btn"
              onClick={() => setWeights({ ...DEFAULTS })}
              disabled={isDefault}
            >
              Rétablir les poids par défaut
            </button>
            {total === 0 && (
              <span className="muted" style={{ fontSize: 13 }}>
                Au moins un critère doit porter un poids.
              </span>
            )}
          </div>

          <h3 className="section-title">Options</h3>
          <div className="form-grid">
            <div className="cell field">
              <label htmlFor="wave-size">Taille de vague</label>
              <input
                id="wave-size"
                className="input"
                type="number"
                min={1}
                max={50}
                value={waveSize}
                onChange={(event) => setWaveSize(Number(event.target.value))}
              />
              <span className="help">
                Nombre d'opportunités par vague de lancement.{" "}
                {Math.ceil(rows.length / Math.max(waveSize, 1))} vagues au total.
              </span>
            </div>
            <label className={applySynergies ? "cell check on" : "cell check"}>
              <input
                type="checkbox"
                checked={applySynergies}
                onChange={(event) => setApplySynergies(event.target.checked)}
              />
              <span>
                Recalculer les synergies depuis le graphe de dépendances
                <span className="muted" style={{ display: "block", fontSize: 12 }}>
                  Écrase les valeurs évaluées en atelier par le score dérivé des dépendances
                  déclarées.
                </span>
              </span>
            </label>
          </div>

          {result && (
            <>
              <h3 className="section-title">
                Résultat — {moved.length} changement{moved.length > 1 ? "s" : ""} de rang
              </h3>

              {moved.length === 0 ? (
                <div className="readonly-banner">
                  <IconTrend size={16} />
                  Le classement est inchangé avec ces pondérations. Ajustez les poids pour voir
                  l'arbitrage bouger.
                </div>
              ) : (
                <div className="table-wrap">
                  <table className="data">
                    <thead>
                      <tr>
                        <th>Rang</th>
                        <th>Mouvement</th>
                        <th>Opportunité</th>
                        <th>Département</th>
                        <th>Score</th>
                        <th>Vague</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.slice(0, 20).map(({ item, previousRank, delta }) => (
                        <tr key={item.id} className={delta !== 0 ? "row-moved" : undefined}>
                          <td className="muted" style={{ whiteSpace: "nowrap" }}>
                            {previousRank && previousRank !== item.priority_rank ? (
                              <>
                                <span style={{ textDecoration: "line-through" }}>{previousRank}</span>{" "}
                                → <b>{item.priority_rank}</b>
                              </>
                            ) : (
                              item.priority_rank
                            )}
                          </td>
                          <td>
                            <MovementBadge delta={delta} />
                          </td>
                          <td style={{ fontWeight: 500 }}>{item.title}</td>
                          <td className="muted">{item.department_name ?? "—"}</td>
                          <td className="num">{Math.round(item.priority_score)}</td>
                          <td className="muted">V{item.wave}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {appliedWeights && (
                <div className="muted" style={{ fontSize: 12.5, marginTop: 12, lineHeight: 1.7 }}>
                  Pondérations appliquées :{" "}
                  {CRITERIA.map((c) => `${c.label} ${(appliedWeights[c.key] * 100).toFixed(1)} %`).join(
                    " · ",
                  )}
                  .{" "}
                  {reference && "Le nouveau classement est enregistré et visible dans le portefeuille."}
                </div>
              )}
            </>
          )}
        </div>

        <div className="drawer-foot">
          <span className="muted" style={{ marginRight: "auto", fontSize: 13 }}>
            {result ? "Classement enregistré." : isDefault ? "Pondérations par défaut" : "Pondérations ajustées"}
          </span>
          <button type="button" className="btn" onClick={onClose}>
            {result ? "Fermer" : "Annuler"}
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={run}
            disabled={prioritize.isPending || total === 0}
          >
            <IconTrend size={16} />
            {prioritize.isPending
              ? "Calcul en cours..."
              : result
                ? "Recalculer à nouveau"
                : "Appliquer et recalculer"}
          </button>
        </div>
      </div>
    </>
  );
}
