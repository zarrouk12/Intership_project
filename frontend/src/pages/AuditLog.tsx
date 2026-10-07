/** M12 — Journal d'audit : lecture seule, une ligne par modification significative. */
import { useMemo, useState } from "react";

import { useAuditLog } from "../api/queries";
import { IconShield } from "../components/Icons";
import { Page, PageHeader } from "../components/Layout";
import { Badge, Card, ErrorState, Loading } from "../components/ui";
import { useAuth } from "../lib/auth";

const ACTION_LABELS: Record<string, string> = {
  create: "Création",
  update: "Modification",
  delete: "Suppression",
  login: "Connexion",
  password_change: "Mot de passe",
  approve: "Validation",
  gate: "Passage de gate",
  generate: "Génération",
  prioritize: "Priorisation",
  qualify: "Qualification",
  measure: "Mesure",
};

const ACTION_TONES: Record<string, string> = {
  create: "badge-green",
  update: "badge-teal",
  delete: "badge-red",
  login: "badge-grey",
  password_change: "badge-amber",
  approve: "badge-green",
  gate: "badge-amber",
};

const ENTITY_LABELS: Record<string, string> = {
  app_user: "Utilisateur",
  role: "Rôle",
  site: "Site",
  department: "Département",
  organization: "Organisation",
  opportunity: "Opportunité",
  project: "Projet",
  stage: "Phase",
  document: "Fiche projet",
  risk: "Risque",
  cost: "Coût",
  benefit: "Bénéfice",
  kpi: "KPI",
  datasource: "Source de données",
  application: "Application",
  process: "Processus",
  dependency: "Dépendance",
  assessment: "Diagnostic",
  assessment_response: "Réponse de diagnostic",
  ai_recommendation: "Recommandation",
};

/** Rend un couple ancienne valeur / nouvelle valeur de façon lisible. */
function Diff({
  oldValue,
  newValue,
}: {
  oldValue?: Record<string, unknown> | null;
  newValue?: Record<string, unknown> | null;
}) {
  const keys = useMemo(
    () => [...new Set([...Object.keys(oldValue ?? {}), ...Object.keys(newValue ?? {})])],
    [oldValue, newValue],
  );
  if (!keys.length) return <span className="muted">—</span>;

  const render = (value: unknown) => {
    if (value === null || value === undefined) return "∅";
    if (Array.isArray(value)) return value.join(", ") || "∅";
    if (typeof value === "object") return JSON.stringify(value);
    if (typeof value === "boolean") return value ? "oui" : "non";
    return String(value);
  };

  return (
    <div className="diff-cell">
      {keys.slice(0, 5).map((key) => (
        <div key={key}>
          <span className="muted">{key} : </span>
          {oldValue && key in oldValue && (
            <>
              <span className="diff-old">{render(oldValue[key])}</span>
              <span className="muted"> → </span>
            </>
          )}
          <span className="diff-new">{render(newValue?.[key])}</span>
        </div>
      ))}
      {keys.length > 5 && <div className="muted">+ {keys.length - 5} autres champs</div>}
    </div>
  );
}

export default function AuditLog() {
  const { can } = useAuth();
  const { data, isLoading, error } = useAuditLog(can("audit.read"), 120);
  const [action, setAction] = useState("");
  const [entity, setEntity] = useState("");

  const actions = useMemo(() => [...new Set((data ?? []).map((e) => e.action))].sort(), [data]);
  const entities = useMemo(() => [...new Set((data ?? []).map((e) => e.entity_type))].sort(), [data]);

  const rows = (data ?? []).filter(
    (entry) => (!action || entry.action === action) && (!entity || entry.entity_type === entity),
  );

  return (
    <>
      <PageHeader
        title="Journal d'audit"
        subtitle="Insertion seule : aucune entrée ne peut être modifiée ni supprimée"
      />
      <Page>
        <div className="readonly-banner">
          <IconShield size={17} />
          Chaque modification significative est tracée avec son auteur, sa date, l'entité visée et
          le passage de l'ancienne à la nouvelle valeur.
        </div>

        <Card title="Événements" subtitle={`${rows.length} entrées affichées`}>
          <div className="filters">
            <div className="field">
              <label htmlFor="a-action">Action</label>
              <select
                id="a-action"
                className="select"
                value={action}
                onChange={(e) => setAction(e.target.value)}
              >
                <option value="">Toutes</option>
                {actions.map((code) => (
                  <option key={code} value={code}>
                    {ACTION_LABELS[code] ?? code}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="a-entity">Entité</label>
              <select
                id="a-entity"
                className="select"
                value={entity}
                onChange={(e) => setEntity(e.target.value)}
              >
                <option value="">Toutes</option>
                {entities.map((code) => (
                  <option key={code} value={code}>
                    {ENTITY_LABELS[code] ?? code}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {isLoading && <Loading />}
          {error && <ErrorState error={error} />}

          {!isLoading && !error && (
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Horodatage</th>
                    <th>Auteur</th>
                    <th>Action</th>
                    <th>Entité</th>
                    <th>Modification</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((entry) => (
                    <tr key={entry.id}>
                      <td className="muted" style={{ whiteSpace: "nowrap" }}>
                        {new Date(entry.created_at).toLocaleString("fr-FR", {
                          day: "2-digit",
                          month: "2-digit",
                          year: "2-digit",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>
                      <td className="muted">{entry.user_email ?? "système"}</td>
                      <td>
                        <Badge tone={ACTION_TONES[entry.action] ?? "badge-grey"}>
                          {ACTION_LABELS[entry.action] ?? entry.action}
                        </Badge>
                      </td>
                      <td>
                        {ENTITY_LABELS[entry.entity_type] ?? entry.entity_type}
                        {entry.entity_label && (
                          <div className="muted" style={{ fontSize: 12.5 }}>
                            {entry.entity_label}
                          </div>
                        )}
                      </td>
                      <td>
                        <Diff oldValue={entry.old_value} newValue={entry.new_value} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </Page>
    </>
  );
}
