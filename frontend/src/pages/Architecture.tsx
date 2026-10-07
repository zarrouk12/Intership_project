/**
 * M6 — Architecture et données, écran du DSI et du Data Office.
 *
 * Les deux rôles partagent la page mais pas les droits : le DSI tient le référentiel
 * applicatif, le Data Office les sources de données. Chaque onglet n'ouvre son
 * formulaire que si la permission correspondante est présente.
 */
import { useState } from "react";

import { errorMessage } from "../api/client";
import { api } from "../api/client";
import { useDepartments } from "../api/queries";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { IconCheck, IconLayers, IconPlus } from "../components/Icons";
import { Page, PageHeader } from "../components/Layout";
import { Badge, Card, ErrorState, Loading } from "../components/ui";
import { useAuth } from "../lib/auth";

interface Process {
  id: number;
  code: string;
  name: string;
  maturity: number;
  volume_per_month?: number | null;
  manual_effort_days?: number | null;
  is_gxp: boolean;
  department_id?: number | null;
}

interface Application {
  id: number;
  name: string;
  vendor?: string | null;
  category?: string | null;
  has_api: boolean;
  criticality?: string | null;
  validated_gxp: boolean;
}

interface DataSource {
  id: number;
  name: string;
  kind?: string | null;
  format?: string | null;
  history_months?: number | null;
  volume?: string | null;
  quality_score: number;
  has_ground_truth: boolean;
  personal_data: boolean;
  owner?: string | null;
}

type Tab = "processes" | "applications" | "datasources";

function useList<T>(key: string, path: string, enabled: boolean) {
  return useQuery({
    queryKey: [key],
    queryFn: async () => (await api.get<T[]>(path)).data,
    enabled,
  });
}

/** Note de qualité 0 à 5 rendue sous forme de barre. */
function Score({ value }: { value: number }) {
  const color = value >= 4 ? "var(--accent)" : value >= 3 ? "#4FA383" : value >= 2 ? "var(--amber)" : "var(--red)";
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
      <span className="bar-track" style={{ width: 62 }}>
        <span className="bar-fill" style={{ width: `${(value / 5) * 100}%`, background: color }} />
      </span>
      <b style={{ color, fontVariantNumeric: "tabular-nums" }}>{value}</b>
    </span>
  );
}

export default function Architecture() {
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("processes");
  const [error, setError] = useState<string | null>(null);

  const canReadArchitecture = can("architecture.read");
  const canReadData = can("data.read");

  const processes = useList<Process>("processes", "/crossings/processes", canReadArchitecture);
  const applications = useList<Application>("applications", "/crossings/applications", canReadArchitecture);
  const datasources = useList<DataSource>("datasources", "/crossings/datasources", canReadData);
  const { data: departments } = useDepartments(can("department.read"));

  const [appForm, setAppForm] = useState({ name: "", vendor: "", category: "", has_api: false });
  const [sourceForm, setSourceForm] = useState({
    name: "",
    kind: "structuree",
    quality_score: 3,
    owner: "",
    has_ground_truth: false,
  });

  async function submit(path: string, body: unknown, key: string, reset: () => void) {
    setError(null);
    try {
      await api.post(path, body);
      await queryClient.invalidateQueries({ queryKey: [key] });
      reset();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  const tabs: { key: Tab; label: string; visible: boolean }[] = [
    { key: "processes", label: "Processus", visible: canReadArchitecture },
    { key: "applications", label: "Applications", visible: canReadArchitecture },
    { key: "datasources", label: "Sources de données", visible: canReadData },
  ];
  const visibleTabs = tabs.filter((t) => t.visible);
  const active = visibleTabs.some((t) => t.key === tab) ? tab : visibleTabs[0]?.key;

  const departmentName = (id?: number | null) =>
    departments?.find((d) => d.id === id)?.name ?? "—";

  return (
    <>
      <PageHeader
        title="Architecture & données"
        subtitle="Référentiel AS-IS : processus, applications, sources de données et leur qualité"
      />
      <Page>
        <div className="tabs">
          {visibleTabs.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              className={active === key ? "tab active" : "tab"}
              onClick={() => setTab(key)}
            >
              <IconLayers size={16} />
              {label}
            </button>
          ))}
        </div>

        {error && <ErrorState error={new Error(error)} />}

        {active === "processes" && (
          <Card title="Processus" subtitle={`${processes.data?.length ?? 0} processus cartographiés`}>
            {processes.isLoading && <Loading />}
            {processes.data && (
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Processus</th>
                      <th>Département</th>
                      <th>Maturité</th>
                      <th>Volume / mois</th>
                      <th>Effort manuel</th>
                      <th>Périmètre</th>
                    </tr>
                  </thead>
                  <tbody>
                    {processes.data.map((process) => (
                      <tr key={process.id}>
                        <td style={{ fontWeight: 500 }}>
                          {process.name}
                          <div className="muted" style={{ fontSize: 12.5 }}>
                            {process.code}
                          </div>
                        </td>
                        <td className="muted">{departmentName(process.department_id)}</td>
                        <td>
                          <Score value={process.maturity} />
                        </td>
                        <td className="muted">{process.volume_per_month ?? "—"}</td>
                        <td className="muted">
                          {process.manual_effort_days ? `${process.manual_effort_days} j` : "—"}
                        </td>
                        <td>
                          {process.is_gxp ? (
                            <Badge tone="badge-amber">GxP</Badge>
                          ) : (
                            <span className="muted">Hors GxP</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        )}

        {active === "applications" && (
          <Card
            title="Applications"
            subtitle={`${applications.data?.length ?? 0} applications du système d'information`}
          >
            {applications.isLoading && <Loading />}
            {applications.data && (
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Application</th>
                      <th>Éditeur</th>
                      <th>Catégorie</th>
                      <th>API</th>
                      <th>Criticité</th>
                      <th>Validation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {applications.data.map((application) => (
                      <tr key={application.id}>
                        <td style={{ fontWeight: 500 }}>{application.name}</td>
                        <td className="muted">{application.vendor ?? "—"}</td>
                        <td className="muted">{application.category ?? "—"}</td>
                        <td>
                          {application.has_api ? (
                            <Badge tone="badge-green">Disponible</Badge>
                          ) : (
                            <span className="muted">Aucune</span>
                          )}
                        </td>
                        <td className="muted">{application.criticality ?? "—"}</td>
                        <td>
                          {application.validated_gxp ? (
                            <Badge tone="badge-amber">Validée GxP</Badge>
                          ) : (
                            <span className="muted">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {can("architecture.manage") && (
              <form
                style={{ marginTop: 18, borderTop: "1px solid var(--border)", paddingTop: 16 }}
                onSubmit={(event) => {
                  event.preventDefault();
                  submit("/crossings/applications", appForm, "applications", () =>
                    setAppForm({ name: "", vendor: "", category: "", has_api: false }),
                  );
                }}
              >
                <h3 className="section-title">Déclarer une application</h3>
                <div className="form-grid">
                  <div className="cell field">
                    <label htmlFor="app-name">Nom</label>
                    <input
                      id="app-name"
                      className="input"
                      required
                      value={appForm.name}
                      onChange={(e) => setAppForm({ ...appForm, name: e.target.value })}
                    />
                  </div>
                  <div className="cell field">
                    <label htmlFor="app-vendor">Éditeur</label>
                    <input
                      id="app-vendor"
                      className="input"
                      value={appForm.vendor}
                      onChange={(e) => setAppForm({ ...appForm, vendor: e.target.value })}
                    />
                  </div>
                  <div className="cell field">
                    <label htmlFor="app-cat">Catégorie</label>
                    <input
                      id="app-cat"
                      className="input"
                      placeholder="ERP, LIMS, MES, QMS..."
                      value={appForm.category}
                      onChange={(e) => setAppForm({ ...appForm, category: e.target.value })}
                    />
                  </div>
                  <label className={appForm.has_api ? "cell check on" : "cell check"}>
                    <input
                      type="checkbox"
                      checked={appForm.has_api}
                      onChange={(e) => setAppForm({ ...appForm, has_api: e.target.checked })}
                    />
                    <span>Expose une API d'intégration</span>
                  </label>
                </div>
                <button type="submit" className="btn btn-primary">
                  <IconPlus size={16} />
                  Ajouter l'application
                </button>
              </form>
            )}
          </Card>
        )}

        {active === "datasources" && (
          <Card
            title="Sources de données"
            subtitle={`${datasources.data?.length ?? 0} sources évaluées`}
          >
            {datasources.isLoading && <Loading />}
            {datasources.data && (
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Source</th>
                      <th>Nature</th>
                      <th>Historique</th>
                      <th>Volume</th>
                      <th>Qualité</th>
                      <th>Vérité terrain</th>
                      <th>Owner</th>
                    </tr>
                  </thead>
                  <tbody>
                    {datasources.data.map((source) => (
                      <tr key={source.id}>
                        <td style={{ fontWeight: 500 }}>
                          {source.name}
                          {source.personal_data && (
                            <Badge tone="badge-amber">Données personnelles</Badge>
                          )}
                        </td>
                        <td className="muted">{source.kind ?? "—"}</td>
                        <td className="muted">
                          {source.history_months ? `${source.history_months} mois` : "—"}
                        </td>
                        <td className="muted">{source.volume ?? "—"}</td>
                        <td>
                          <Score value={source.quality_score} />
                        </td>
                        <td>
                          {source.has_ground_truth ? (
                            <Badge tone="badge-green">Disponible</Badge>
                          ) : (
                            <span className="muted">Absente</span>
                          )}
                        </td>
                        <td className="muted">{source.owner ?? "Non désigné"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {can("data.manage") && (
              <form
                style={{ marginTop: 18, borderTop: "1px solid var(--border)", paddingTop: 16 }}
                onSubmit={(event) => {
                  event.preventDefault();
                  submit("/crossings/datasources", sourceForm, "datasources", () =>
                    setSourceForm({
                      name: "",
                      kind: "structuree",
                      quality_score: 3,
                      owner: "",
                      has_ground_truth: false,
                    }),
                  );
                }}
              >
                <h3 className="section-title">Déclarer une source de données</h3>
                <div className="form-grid">
                  <div className="cell field">
                    <label htmlFor="ds-name">Nom</label>
                    <input
                      id="ds-name"
                      className="input"
                      required
                      value={sourceForm.name}
                      onChange={(e) => setSourceForm({ ...sourceForm, name: e.target.value })}
                    />
                  </div>
                  <div className="cell field">
                    <label htmlFor="ds-kind">Nature</label>
                    <select
                      id="ds-kind"
                      className="select"
                      value={sourceForm.kind}
                      onChange={(e) => setSourceForm({ ...sourceForm, kind: e.target.value })}
                    >
                      <option value="structuree">Structurée</option>
                      <option value="texte">Texte</option>
                      <option value="image">Image</option>
                      <option value="serie_temporelle">Série temporelle</option>
                    </select>
                  </div>
                  <div className="cell field">
                    <label htmlFor="ds-quality">Qualité estimée (0 à 5)</label>
                    <input
                      id="ds-quality"
                      className="input"
                      type="number"
                      min={0}
                      max={5}
                      value={sourceForm.quality_score}
                      onChange={(e) =>
                        setSourceForm({ ...sourceForm, quality_score: Number(e.target.value) })
                      }
                    />
                  </div>
                  <div className="cell field">
                    <label htmlFor="ds-owner">Owner</label>
                    <input
                      id="ds-owner"
                      className="input"
                      value={sourceForm.owner}
                      onChange={(e) => setSourceForm({ ...sourceForm, owner: e.target.value })}
                    />
                  </div>
                  <label className={sourceForm.has_ground_truth ? "cell check on" : "cell check"}>
                    <input
                      type="checkbox"
                      checked={sourceForm.has_ground_truth}
                      onChange={(e) =>
                        setSourceForm({ ...sourceForm, has_ground_truth: e.target.checked })
                      }
                    />
                    <span>Vérité terrain exploitable</span>
                  </label>
                </div>
                <button type="submit" className="btn btn-primary">
                  <IconCheck size={16} />
                  Ajouter la source
                </button>
              </form>
            )}
          </Card>
        )}
      </Page>
    </>
  );
}
