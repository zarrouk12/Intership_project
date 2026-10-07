/**
 * Écran 3b — Recueil et modification d'une opportunité.
 *
 * Le même formulaire sert à créer et à modifier : en modification il est pré-rempli
 * depuis l'API et n'envoie que les champs réellement changés, ce qui laisse le journal
 * d'audit lisible au lieu de le remplir de faux changements.
 *
 * Le questionnaire lui-même vient du backend : tronc commun plus volet propre à la
 * famille métier du département choisi.
 */
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { errorMessage } from "../api/client";
import {
  useCreateOpportunity,
  useDeleteOpportunity,
  useDepartments,
  useOpportunity,
  useQuestionnaire,
  useSites,
  useUpdateOpportunity,
} from "../api/queries";
import type { Opportunity, QuestionnaireQuestion, QuestionnaireSection } from "../api/types";
import { IconAlert, IconArrowLeft, IconCheck, IconTrash } from "../components/Icons";
import { Page, PageHeader } from "../components/Layout";
import { Card, ErrorState, Loading } from "../components/ui";
import { useAuth } from "../lib/auth";

type FormValue = string | number | boolean | null;

/** Champs portés par la table opportunity ; le reste part dans `answers`. */
const MODEL_FIELDS = new Set([
  "title",
  "summary",
  "as_is_context",
  "pain_points",
  "desired_outcome",
  "sponsor",
  "business_owner",
  "technical_owner",
  "volume_per_month",
  "data_available",
  "data_structured",
  "data_quality",
  "ground_truth_available",
  "unstructured_text",
  "image_or_video",
  "content_generation",
  "multi_step_autonomy",
  "rule_based",
  "repetitive_task",
  "reporting_need",
  "process_unstable",
  "regulated_gxp",
  "human_in_the_loop",
  "impact_business",
  "impact_financial",
  "feasibility",
  "alignment",
  "expected_benefit_eur",
  "estimated_cost_eur",
  "risk_probability",
  "risk_impact",
]);

function Question({
  question,
  value,
  onChange,
}: {
  question: QuestionnaireQuestion;
  value: FormValue;
  onChange: (value: FormValue) => void;
}) {
  if (question.type === "boolean") {
    const checked = value === true;
    return (
      <label className={checked ? "check on" : "check"} style={{ marginBottom: 16 }}>
        <input
          type="checkbox"
          checked={checked}
          onChange={(event) => onChange(event.target.checked)}
        />
        <span>{question.label}</span>
      </label>
    );
  }

  return (
    <div className="field">
      <label htmlFor={question.field}>
        {question.label}
        {question.required && <span style={{ color: "var(--red)" }}> *</span>}
      </label>

      {question.type === "textarea" && (
        <textarea
          id={question.field}
          className="textarea"
          value={typeof value === "string" ? value : ""}
          onChange={(event) => onChange(event.target.value)}
        />
      )}

      {question.type === "text" && (
        <input
          id={question.field}
          className="input"
          value={typeof value === "string" ? value : ""}
          onChange={(event) => onChange(event.target.value)}
        />
      )}

      {(question.type === "number" || question.type === "scale") && (
        <>
          <input
            id={question.field}
            className="input"
            type="number"
            min={question.min}
            max={question.max}
            value={value === null || value === undefined || value === "" ? "" : Number(value)}
            onChange={(event) =>
              onChange(event.target.value === "" ? null : Number(event.target.value))
            }
          />
          {(question.unit || question.type === "scale") && (
            <span className="help">
              {question.type === "scale"
                ? `Échelle ${question.min ?? 0} à ${question.max ?? 100}`
                : question.unit}
            </span>
          )}
        </>
      )}
    </div>
  );
}

function Section({
  section,
  values,
  onChange,
}: {
  section: QuestionnaireSection;
  values: Record<string, FormValue>;
  onChange: (field: string, value: FormValue) => void;
}) {
  // L'ordre déclaré par le questionnaire est conservé : seules les zones de texte long
  // occupent toute la largeur, les autres champs se rangent en colonnes.
  return (
    <>
      <h3 className="section-title">{section.title}</h3>
      <div className="form-grid">
        {section.questions.map((question) => (
          <div key={question.field} className={question.type === "textarea" ? "cell wide" : "cell"}>
            <Question
              question={question}
              value={values[question.field] ?? (question.type === "boolean" ? false : null)}
              onChange={(value) => onChange(question.field, value)}
            />
          </div>
        ))}
      </div>
    </>
  );
}

/** Reconstruit l'état du formulaire à partir d'une opportunité existante. */
function toFormValues(opportunity: Opportunity): Record<string, FormValue> {
  const values: Record<string, FormValue> = {};
  MODEL_FIELDS.forEach((field) => {
    const value = (opportunity as unknown as Record<string, unknown>)[field];
    if (value !== null && value !== undefined) values[field] = value as FormValue;
  });
  // Les réponses libres du questionnaire départemental reviennent telles quelles.
  Object.entries(opportunity.answers ?? {}).forEach(([field, value]) => {
    if (!MODEL_FIELDS.has(field) && typeof value !== "object") {
      values[field] = value as FormValue;
    }
  });
  return values;
}

export default function OpportunityForm() {
  const navigate = useNavigate();
  const { id } = useParams();
  const { can } = useAuth();

  const opportunityId = id ? Number(id) : undefined;
  const isEdit = Boolean(opportunityId);

  const { data: existing, isLoading: loadingExisting, error: loadError } = useOpportunity(opportunityId);
  const { data: departments } = useDepartments(can("department.read"));
  const { data: sites } = useSites(can("site.read"));

  const [departmentId, setDepartmentId] = useState<string>("");
  const [siteId, setSiteId] = useState<string>("");
  const [values, setValues] = useState<Record<string, FormValue>>({ human_in_the_loop: true });
  const [initial, setInitial] = useState<Record<string, FormValue>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data: questionnaire, isLoading } = useQuestionnaire(
    departmentId ? Number(departmentId) : undefined,
  );
  const createOpportunity = useCreateOpportunity();
  const updateOpportunity = useUpdateOpportunity();
  const deleteOpportunity = useDeleteOpportunity();

  // Pré-remplissage : une seule fois, à l'arrivée de l'opportunité.
  useEffect(() => {
    if (!existing) return;
    const loaded = toFormValues(existing);
    setValues(loaded);
    setInitial(loaded);
    setDepartmentId(existing.department_id ? String(existing.department_id) : "");
    setSiteId(existing.site_id ? String(existing.site_id) : "");
  }, [existing]);

  const sections = useMemo(() => {
    if (!questionnaire) return [];
    return questionnaire.specific
      ? [...questionnaire.common, questionnaire.specific]
      : questionnaire.common;
  }, [questionnaire]);

  const setValue = (field: string, value: FormValue) =>
    setValues((previous) => ({ ...previous, [field]: value }));

  const changedFields = useMemo(() => {
    if (!isEdit) return Object.keys(values);
    return Object.keys({ ...initial, ...values }).filter((field) => values[field] !== initial[field]);
  }, [isEdit, values, initial]);

  const departmentChanged =
    isEdit && departmentId !== (existing?.department_id ? String(existing.department_id) : "");
  const siteChanged = isEdit && siteId !== (existing?.site_id ? String(existing.site_id) : "");
  const dirty = changedFields.length > 0 || departmentChanged || siteChanged;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitError(null);

    if (!values.title || String(values.title).trim() === "") {
      setSubmitError("L'intitulé de l'opportunité est obligatoire.");
      return;
    }

    const answers: Record<string, FormValue> = {};
    const payload: Record<string, unknown> = {};

    // En modification on n'envoie que le delta ; en création, tout ce qui est renseigné.
    const fields = isEdit ? changedFields : Object.keys(values);
    fields.forEach((field) => {
      const value = values[field];
      if (!isEdit && (value === null || value === "")) return;
      if (MODEL_FIELDS.has(field)) payload[field] = value;
      else answers[field] = value;
    });

    // Le questionnaire départemental voyage en bloc : un envoi partiel écraserait
    // les réponses non modifiées.
    if (Object.keys(answers).length > 0 || !isEdit) {
      const merged: Record<string, FormValue> = {};
      Object.entries(values).forEach(([field, value]) => {
        if (!MODEL_FIELDS.has(field) && value !== null && value !== "") merged[field] = value;
      });
      payload.answers = merged;
    }

    if (!isEdit || departmentChanged) {
      payload.department_id = departmentId ? Number(departmentId) : null;
    }
    if (!isEdit || siteChanged) {
      payload.site_id = siteId ? Number(siteId) : null;
    }

    try {
      if (isEdit && opportunityId) {
        await updateOpportunity.mutateAsync({ id: opportunityId, ...payload });
        navigate(`/fiches/${opportunityId}`);
      } else {
        const created = await createOpportunity.mutateAsync(payload);
        navigate(`/fiches/${created.id}`);
      }
    } catch (error) {
      setSubmitError(errorMessage(error));
    }
  }

  async function remove() {
    if (!opportunityId) return;
    setSubmitError(null);
    try {
      await deleteOpportunity.mutateAsync(opportunityId);
      navigate("/opportunites");
    } catch (error) {
      setSubmitError(errorMessage(error));
      setConfirmDelete(false);
    }
  }

  const pending = createOpportunity.isPending || updateOpportunity.isPending;
  const canEdit = isEdit ? can("opportunity.update") : can("opportunity.create");

  if (isEdit && loadingExisting) {
    return (
      <>
        <PageHeader title="Modifier l'opportunité" />
        <Page>
          <Loading label="Chargement de l'opportunité..." />
        </Page>
      </>
    );
  }

  if (isEdit && loadError) {
    return (
      <>
        <PageHeader title="Modifier l'opportunité" />
        <Page>
          <ErrorState error={loadError} />
        </Page>
      </>
    );
  }

  return (
    <>
      <PageHeader
        leading={
          <button
            type="button"
            className="btn btn-icon"
            onClick={() => navigate(isEdit ? `/fiches/${opportunityId}` : "/opportunites")}
            aria-label="Retour"
          >
            <IconArrowLeft size={18} />
          </button>
        }
        title={isEdit ? existing?.title ?? "Modifier l'opportunité" : "Nouvelle opportunité"}
        subtitle={
          isEdit
            ? `${existing?.code} · modification du dossier`
            : "Questionnaire commun, complété par le volet propre au département"
        }
        actions={
          <>
            {isEdit && can("opportunity.update") && (
              <button
                type="button"
                className="btn"
                onClick={() => setConfirmDelete(true)}
                disabled={deleteOpportunity.isPending}
              >
                <IconTrash size={17} />
                Supprimer
              </button>
            )}
            <button
              type="submit"
              form="opportunity-form"
              className="btn btn-primary"
              disabled={pending || !canEdit || (isEdit && !dirty)}
              title={isEdit && !dirty ? "Aucune modification à enregistrer" : undefined}
            >
              <IconCheck size={17} />
              {pending
                ? "Enregistrement..."
                : isEdit
                  ? "Enregistrer les modifications"
                  : "Créer et qualifier"}
            </button>
          </>
        }
      />
      <Page>
        <form id="opportunity-form" onSubmit={submit}>
          <div className="stack">
            {isEdit && (
              <div className="readonly-banner">
                <IconAlert size={16} />
                Modifier les réponses relance la qualification : le type de solution et le
                score de priorité sont recalculés à l'enregistrement.
              </div>
            )}

            <Card
              title="Rattachement"
              subtitle="Le département détermine le volet spécifique du questionnaire"
            >
              <div className="form-grid">
                <div className="cell field">
                  <label htmlFor="form-dept">Département</label>
                  <select
                    id="form-dept"
                    className="select"
                    value={departmentId}
                    onChange={(event) => setDepartmentId(event.target.value)}
                  >
                    <option value="">Sélectionner un département</option>
                    {departments?.map((department) => (
                      <option key={department.id} value={department.id}>
                        {department.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="cell field">
                  <label htmlFor="form-site">Site</label>
                  <select
                    id="form-site"
                    className="select"
                    value={siteId}
                    onChange={(event) => setSiteId(event.target.value)}
                  >
                    <option value="">Sélectionner un site</option>
                    {sites?.map((site) => (
                      <option key={site.id} value={site.id}>
                        {site.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </Card>

            {isLoading && <Loading label="Chargement du questionnaire..." />}

            {sections.length > 0 && (
              <Card
                title="Questionnaire de qualification"
                subtitle={
                  questionnaire?.specific
                    ? "Tronc commun + volet départemental"
                    : "Tronc commun — sélectionnez un département pour ajouter son volet"
                }
              >
                {sections.map((section) => (
                  <Section
                    key={section.code}
                    section={section}
                    values={values}
                    onChange={setValue}
                  />
                ))}
              </Card>
            )}

            {submitError && <ErrorState error={new Error(submitError)} />}

            {isEdit && (
              <div className="muted" style={{ fontSize: 13 }}>
                {dirty
                  ? `${changedFields.length + (departmentChanged ? 1 : 0) + (siteChanged ? 1 : 0)} champ(s) modifié(s) — seuls ces champs seront envoyés.`
                  : "Aucune modification."}
              </div>
            )}
          </div>
        </form>
      </Page>

      {confirmDelete && existing && (
        <>
          <div className="drawer-backdrop" onClick={() => setConfirmDelete(false)} />
          <div className="confirm-dialog" role="alertdialog" aria-label="Confirmer la suppression">
            <div className="card-title">Supprimer cette opportunité ?</div>
            <p style={{ lineHeight: 1.7 }}>
              <b>{existing.title}</b> ({existing.code}) sera supprimée, avec sa recommandation,
              ses KPI, ses coûts et ses bénéfices. Cette action est définitive.
            </p>
            <p className="muted" style={{ fontSize: 13 }}>
              La suppression est tracée dans le journal d'audit.
            </p>
            <div className="row" style={{ justifyContent: "flex-end", marginTop: 18 }}>
              <button type="button" className="btn" onClick={() => setConfirmDelete(false)}>
                Annuler
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={remove}
                disabled={deleteOpportunity.isPending}
              >
                <IconTrash size={16} />
                {deleteOpportunity.isPending ? "Suppression..." : "Supprimer définitivement"}
              </button>
            </div>
          </div>
        </>
      )}
    </>
  );
}
