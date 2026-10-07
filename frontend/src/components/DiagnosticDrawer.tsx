/**
 * Questionnaire de diagnostic éditable.
 *
 * Ouvert par « Poursuivre le diagnostic », il liste les dimensions de la campagne et
 * permet de renseigner note, poids, confiance et preuve. Seules les lignes réellement
 * modifiées sont envoyées au backend, qui recalcule ensuite le readiness et le taux de
 * complétion à partir des réponses.
 *
 * Une confiance nulle signifie « dimension non encore instruite » : la dimension sort du
 * score tant qu'elle n'est pas évaluée, au lieu de compter comme un zéro.
 */
import { useMemo, useState } from "react";

import { errorMessage } from "../api/client";
import { useAssessmentDetail, useSaveResponses } from "../api/queries";
import type { AssessmentResponse } from "../api/types";
import { useAuth } from "../lib/auth";
import { IconAlert, IconCheck, IconLock } from "./Icons";
import { ErrorState, Loading } from "./ui";

/** Valeur locale d'une ligne en cours d'édition. */
interface Draft {
  score: number;
  weight: number;
  confidence: number;
  evidence: string;
}

const CONFIDENCE_OPTIONS = [
  { value: 0, label: "Non instruite" },
  { value: 0.25, label: "Faible — déclaratif" },
  { value: 0.5, label: "Moyenne — partiellement étayée" },
  { value: 0.75, label: "Bonne — étayée" },
  { value: 1, label: "Élevée — preuve vérifiée" },
];

const AXIS_LABELS: Record<string, string> = {
  technique: "Readiness technique",
  metier: "Readiness métier & organisationnel",
};

function toDraft(response: AssessmentResponse): Draft {
  return {
    score: response.score,
    weight: response.weight,
    confidence: response.confidence,
    evidence: response.evidence ?? "",
  };
}

function isDirty(draft: Draft, response: AssessmentResponse): boolean {
  return (
    draft.score !== response.score ||
    draft.weight !== response.weight ||
    draft.confidence !== response.confidence ||
    draft.evidence !== (response.evidence ?? "")
  );
}

/** Sélecteur de note 0 à 5, plus lisible qu'un champ numérique. */
function ScorePicker({
  value,
  disabled,
  onChange,
}: {
  value: number;
  disabled: boolean;
  onChange: (value: number) => void;
}) {
  return (
    <div className="score-picker" role="group" aria-label="Note de maturité">
      {[0, 1, 2, 3, 4, 5].map((level) => (
        <button
          key={level}
          type="button"
          disabled={disabled}
          className={level === value ? "score-dot active" : "score-dot"}
          onClick={() => onChange(level)}
          aria-pressed={level === value}
        >
          {level}
        </button>
      ))}
    </div>
  );
}

function ResponseRow({
  response,
  draft,
  readOnly,
  onChange,
}: {
  response: AssessmentResponse;
  draft: Draft;
  readOnly: boolean;
  onChange: (patch: Partial<Draft>) => void;
}) {
  const pending = draft.confidence === 0;
  const dirty = isDirty(draft, response);

  return (
    <div className={dirty ? "dim-row dirty" : "dim-row"}>
      <div className="dim-head">
        <div>
          <div className="dim-label">
            {response.dimension_label}
            {response.is_critical && (
              <span className="chip-sm" style={{ marginLeft: 8 }}>
                critique
              </span>
            )}
          </div>
          {response.question && <div className="dim-question">{response.question}</div>}
        </div>
        {pending && <span className="badge badge-amber">À instruire</span>}
        {dirty && <span className="badge badge-teal">Modifiée</span>}
      </div>

      <div className="dim-fields">
        <div className="field" style={{ marginBottom: 0 }}>
          <label>Note de maturité</label>
          <ScorePicker
            value={draft.score}
            disabled={readOnly}
            onChange={(score) =>
              // Noter une dimension revient a l'instruire : on sort de l'etat
              // « non instruite » en lui donnant une confiance par defaut.
              onChange({ score, confidence: draft.confidence === 0 ? 0.75 : draft.confidence })
            }
          />
        </div>

        <div className="field" style={{ marginBottom: 0 }}>
          <label htmlFor={`conf-${response.id}`}>Confiance</label>
          <select
            id={`conf-${response.id}`}
            className="select"
            disabled={readOnly}
            value={draft.confidence}
            onChange={(event) => onChange({ confidence: Number(event.target.value) })}
          >
            {CONFIDENCE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="field" style={{ marginBottom: 0 }}>
          <label htmlFor={`weight-${response.id}`}>Poids</label>
          <input
            id={`weight-${response.id}`}
            className="input"
            type="number"
            min={0.1}
            max={5}
            step={0.1}
            disabled={readOnly}
            value={draft.weight}
            onChange={(event) => onChange({ weight: Number(event.target.value) })}
          />
        </div>
      </div>

      <div className="field" style={{ marginTop: 12, marginBottom: 0 }}>
        <label htmlFor={`ev-${response.id}`}>Preuve ou constat</label>
        <textarea
          id={`ev-${response.id}`}
          className="textarea"
          style={{ minHeight: 68 }}
          readOnly={readOnly}
          placeholder={
            readOnly
              ? "Aucune preuve renseignee"
              : "Sur quoi repose cette note ? Document, entretien, mesure..."
          }
          value={draft.evidence}
          onChange={(event) => onChange({ evidence: event.target.value })}
        />
      </div>
    </div>
  );
}

export default function DiagnosticDrawer({
  assessmentId,
  onClose,
}: {
  assessmentId: number;
  onClose: () => void;
}) {
  const { can } = useAuth();
  // Sans le droit de repondre, le tiroir s'ouvre en consultation : le questionnaire et
  // son etat d'avancement restent lisibles, seule l'edition est fermee.
  const readOnly = !can("diagnostic.answer");
  const { data, isLoading, error } = useAssessmentDetail(assessmentId);
  const save = useSaveResponses();
  const [drafts, setDrafts] = useState<Record<number, Draft>>({});
  const [saveError, setSaveError] = useState<string | null>(null);
  const [onlyPending, setOnlyPending] = useState(false);

  const responses = useMemo(
    () =>
      [...(data?.responses ?? [])].sort(
        (a, b) => a.axis.localeCompare(b.axis) || a.dimension_label.localeCompare(b.dimension_label, "fr"),
      ),
    [data],
  );

  const draftFor = (response: AssessmentResponse): Draft => drafts[response.id] ?? toDraft(response);

  const update = (response: AssessmentResponse, patch: Partial<Draft>) =>
    setDrafts((previous) => ({
      ...previous,
      [response.id]: { ...draftFor(response), ...patch },
    }));

  const changed = responses.filter((response) => isDirty(draftFor(response), response));
  const answered = responses.filter((response) => draftFor(response).confidence > 0).length;
  const progress = responses.length ? (answered / responses.length) * 100 : 0;

  const visible = onlyPending
    ? responses.filter((response) => draftFor(response).confidence === 0)
    : responses;

  const byAxis = useMemo(() => {
    const groups = new Map<string, AssessmentResponse[]>();
    visible.forEach((response) => {
      if (!groups.has(response.axis)) groups.set(response.axis, []);
      groups.get(response.axis)!.push(response);
    });
    return [...groups.entries()];
  }, [visible]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSaveError(null);
    if (!changed.length) {
      onClose();
      return;
    }
    try {
      await save.mutateAsync(
        changed.map((response) => {
          const draft = draftFor(response);
          return {
            id: response.id,
            score: draft.score,
            weight: draft.weight,
            confidence: draft.confidence,
            evidence: draft.evidence.trim() || null,
          };
        }),
      );
      onClose();
    } catch (e) {
      setSaveError(errorMessage(e));
    }
  }

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <form className="drawer drawer-wide" onSubmit={submit}>
        <div className="drawer-head">
          <div style={{ flex: 1 }}>
            <div className="card-title">
              {readOnly ? "Questionnaire de diagnostic" : "Poursuivre le diagnostic"}
            </div>
            <div className="card-sub">
              {data?.name}
              {data?.campaign ? ` · ${data.campaign}` : ""}
            </div>
            <div className="drawer-progress">
              <div className="bar-track" style={{ flex: 1 }}>
                <div className="bar-fill" style={{ width: `${progress}%` }} />
              </div>
              <span className="muted" style={{ fontSize: 13, whiteSpace: "nowrap" }}>
                {answered} / {responses.length} dimensions instruites
              </span>
            </div>
          </div>
        </div>

        <div className="drawer-body">
          {isLoading && <Loading label="Chargement du questionnaire..." />}
          {error && <ErrorState error={error} />}
          {saveError && <ErrorState error={new Error(saveError)} />}

          {data && (
            <>
              <div className="readonly-banner" style={{ marginBottom: 20 }}>
                {readOnly ? <IconLock size={16} /> : <IconAlert size={16} />}
                {readOnly
                  ? "Consultation seule : votre rôle ne porte pas la permission diagnostic.answer, qui permet de renseigner les dimensions."
                  : "Une confiance « non instruite » écarte la dimension du score tant qu'elle n'est pas évaluée : une dimension non mesurée ne vaut pas zéro."}
              </div>

              {responses.some((r) => draftFor(r).confidence === 0) && (
                <label className={onlyPending ? "check on" : "check"} style={{ marginBottom: 20 }}>
                  <input
                    type="checkbox"
                    checked={onlyPending}
                    onChange={(event) => setOnlyPending(event.target.checked)}
                  />
                  <span>N'afficher que les dimensions restant à instruire</span>
                </label>
              )}

              {byAxis.map(([axis, group]) => (
                <div key={axis}>
                  <h3 className="section-title">{AXIS_LABELS[axis] ?? axis}</h3>
                  {group.map((response) => (
                    <ResponseRow
                      key={response.id}
                      response={response}
                      draft={draftFor(response)}
                      readOnly={readOnly}
                      onChange={(patch) => update(response, patch)}
                    />
                  ))}
                </div>
              ))}

              {visible.length === 0 && (
                <div className="state">Toutes les dimensions sont instruites.</div>
              )}
            </>
          )}
        </div>

        <div className="drawer-foot">
          <span className="muted" style={{ marginRight: "auto", fontSize: 13 }}>
            {readOnly
              ? `${responses.length - answered} dimension${
                  responses.length - answered > 1 ? "s" : ""
                } restant à instruire`
              : changed.length === 0
                ? "Aucune modification"
                : `${changed.length} dimension${changed.length > 1 ? "s" : ""} modifiée${
                    changed.length > 1 ? "s" : ""
                  }`}
          </span>
          <button type="button" className="btn" onClick={onClose}>
            Fermer
          </button>
          {!readOnly && (
            <button
              type="submit"
              className="btn btn-primary"
              disabled={save.isPending || changed.length === 0}
            >
              <IconCheck size={16} />
              {save.isPending ? "Enregistrement..." : "Enregistrer et recalculer"}
            </button>
          )}
        </div>
      </form>
    </>
  );
}
