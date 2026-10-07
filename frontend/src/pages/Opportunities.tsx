/** Ecran 3a - Liste des opportunites et detection de doublons. */
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  useDeleteOpportunity,
  useDepartments,
  useDuplicates,
  useOpportunities,
  useReference,
} from "../api/queries";
import { errorMessage } from "../api/client";
import { IconAlert, IconFilter, IconPencil, IconPlus, IconTrash } from "../components/Icons";
import { Page, PageHeader } from "../components/Layout";
import { Badge, Card, ErrorState, Loading } from "../components/ui";
import { useAuth } from "../lib/auth";
import {
  PHASE_LABELS,
  STATUS_LABELS,
  STATUS_TONES,
  aiTypeColor,
  formatEuro,
} from "../lib/format";

export default function Opportunities() {
  const navigate = useNavigate();
  const { can, isOrganizationWide, user } = useAuth();
  const [departmentId, setDepartmentId] = useState<string>("");
  const [search, setSearch] = useState("");
  const [toDelete, setToDelete] = useState<{ id: number; code: string; title: string } | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const removeOpportunity = useDeleteOpportunity();

  const filters = useMemo(
    () => ({
      ...(departmentId ? { department_id: Number(departmentId) } : {}),
      ...(search.trim() ? { search: search.trim() } : {}),
    }),
    [departmentId, search],
  );

  const { data, isLoading, error } = useOpportunities(filters);
  const { data: departments } = useDepartments(can("department.read"));
  const { data: duplicates } = useDuplicates(0.3, can("architecture.read"));
  useReference();

  const flagged = duplicates?.filter((d) => d.verdict === "doublon_probable") ?? [];

  return (
    <>
      <PageHeader
        title="Opportunités"
        subtitle="Recueil des besoins métier et qualification de la solution"
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
        <div className="stack">
          {!isOrganizationWide && (
            <div className="readonly-banner">
              <IconFilter size={16} />
              Vous consultez le périmètre{" "}
              <b>{user?.departments.map((d) => d.name).join(", ") || "qui vous est rattaché"}</b>.
              Les opportunités des autres départements ne sont pas listées ici.
            </div>
          )}
          {flagged.length > 0 && (
            <div className="alert alert-amber">
              <IconAlert size={19} style={{ flex: "0 0 19px", marginTop: 1 }} />
              <div>
                <b>
                  {flagged.length} doublon{flagged.length > 1 ? "s" : ""} probable
                  {flagged.length > 1 ? "s" : ""}
                </b>{" "}
                détecté{flagged.length > 1 ? "s" : ""} par le croisement interservices :{" "}
                {flagged
                  .slice(0, 3)
                  .map((d) => `${d.source_code} × ${d.target_code}`)
                  .join(", ")}
                . Termes partagés : {flagged[0].shared_terms.slice(0, 4).join(", ")}.
              </div>
            </div>
          )}

          <Card title="Portefeuille d'opportunités" subtitle={`${data?.length ?? 0} besoins recensés`}>
            <div className="filters">
              <div className="field">
                <label htmlFor="opp-dept">Département</label>
                <select
                  id="opp-dept"
                  className="select"
                  value={departmentId}
                  onChange={(event) => setDepartmentId(event.target.value)}
                >
                  <option value="">Tous les départements</option>
                  {departments?.map((department) => (
                    <option key={department.id} value={department.id}>
                      {department.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field" style={{ flex: 1, minWidth: 240 }}>
                <label htmlFor="opp-search">Recherche</label>
                <input
                  id="opp-search"
                  className="input"
                  placeholder="Titre ou code de l'opportunité"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                />
              </div>
            </div>

            {isLoading && <Loading />}
            {error && <ErrorState error={error} />}
            {data && data.length === 0 && (
              <div className="state">Aucune opportunité ne correspond à ces filtres.</div>
            )}

            {data && data.length > 0 && (
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Code</th>
                      <th>Opportunité</th>
                      <th>Département</th>
                      <th>Type IA</th>
                      <th>Phase</th>
                      <th>Bénéfice attendu</th>
                      <th>Score</th>
                      <th>Statut</th>
                      {(can("opportunity.update") || can("opportunity.create")) && (
                        <th style={{ textAlign: "right" }}>Actions</th>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((opportunity) => (
                      <tr
                        key={opportunity.id}
                        className="clickable"
                        onClick={() => navigate(`/fiches/${opportunity.id}`)}
                      >
                        <td className="muted">{opportunity.code}</td>
                        <td style={{ fontWeight: 500 }}>{opportunity.title}</td>
                        <td className="muted">{opportunity.department_name ?? "-"}</td>
                        <td>
                          <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                            <span
                              className="legend-dot"
                              style={{ background: aiTypeColor(opportunity.recommendation?.ai_type) }}
                            />
                            {opportunity.recommendation?.ai_type_label ?? "Non qualifié"}
                          </span>
                        </td>
                        <td className="muted">
                          {PHASE_LABELS[opportunity.phase] ?? opportunity.phase}
                        </td>
                        <td className="muted">{formatEuro(opportunity.expected_benefit_eur)}</td>
                        <td className="num">{Math.round(opportunity.priority_score)}</td>
                        <td>
                          <Badge tone={STATUS_TONES[opportunity.status] ?? "badge-grey"}>
                            {STATUS_LABELS[opportunity.status] ?? opportunity.status}
                          </Badge>
                        </td>
                        {(can("opportunity.update") || can("opportunity.create")) && (
                          <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                            {can("opportunity.update") && (
                              <>
                                <button
                                  type="button"
                                  className="btn-inline"
                                  title="Modifier"
                                  aria-label={`Modifier ${opportunity.title}`}
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    navigate(`/opportunites/${opportunity.id}/modifier`);
                                  }}
                                >
                                  <IconPencil size={16} />
                                </button>
                                <button
                                  type="button"
                                  className="btn-inline danger"
                                  title="Supprimer"
                                  aria-label={`Supprimer ${opportunity.title}`}
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    setToDelete({
                                      id: opportunity.id,
                                      code: opportunity.code,
                                      title: opportunity.title,
                                    });
                                  }}
                                >
                                  <IconTrash size={16} />
                                </button>
                              </>
                            )}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      </Page>

      {toDelete && (
        <>
          <div className="drawer-backdrop" onClick={() => setToDelete(null)} />
          <div className="confirm-dialog" role="alertdialog" aria-label="Confirmer la suppression">
            <div className="card-title">Supprimer cette opportunité ?</div>
            <p style={{ lineHeight: 1.7 }}>
              <b>{toDelete.title}</b> ({toDelete.code}) sera supprimée, avec sa recommandation,
              ses KPI, ses coûts et ses bénéfices. Cette action est définitive.
            </p>
            <p className="muted" style={{ fontSize: 13 }}>
              La suppression est tracée dans le journal d'audit.
            </p>
            {actionError && <ErrorState error={new Error(actionError)} />}
            <div className="row" style={{ justifyContent: "flex-end", marginTop: 18 }}>
              <button type="button" className="btn" onClick={() => setToDelete(null)}>
                Annuler
              </button>
              <button
                type="button"
                className="btn btn-danger"
                disabled={removeOpportunity.isPending}
                onClick={async () => {
                  setActionError(null);
                  try {
                    await removeOpportunity.mutateAsync(toDelete.id);
                    setToDelete(null);
                  } catch (e) {
                    setActionError(errorMessage(e));
                  }
                }}
              >
                <IconTrash size={16} />
                {removeOpportunity.isPending ? "Suppression..." : "Supprimer définitivement"}
              </button>
            </div>
          </div>
        </>
      )}
    </>
  );
}
