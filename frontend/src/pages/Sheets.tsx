/** Index des fiches projet : selection de l'opportunite a ouvrir. */
import { useNavigate } from "react-router-dom";

import { usePortfolio } from "../api/queries";
import { Page, PageHeader } from "../components/Layout";
import { Badge, Card, ErrorState, Loading } from "../components/ui";
import { STATUS_LABELS, STATUS_TONES, formatEuro } from "../lib/format";

export default function Sheets() {
  const navigate = useNavigate();
  const { data, isLoading, error } = usePortfolio();

  return (
    <>
      <PageHeader
        title="Fiches projet"
        subtitle="Dossier de cadrage généré à partir des données vivantes du portefeuille"
      />
      <Page>
        <Card
          title="Sélectionner une fiche"
          subtitle={`${data?.length ?? 0} opportunités instruites, classées par score de priorité`}
        >
          {isLoading && <Loading />}
          {error && <ErrorState error={error} />}
          {data && (
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
                    <th>Score</th>
                    <th>Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((row) => (
                    <tr
                      key={row.id}
                      className="clickable"
                      onClick={() => navigate(`/fiches/${row.id}`)}
                    >
                      <td className="muted">{row.priority_rank ?? "-"}</td>
                      <td style={{ fontWeight: 500 }}>
                        {row.title}
                        <div className="muted" style={{ fontSize: 12.5 }}>
                          {row.code}
                        </div>
                      </td>
                      <td className="muted">{row.department_name ?? "-"}</td>
                      <td className="muted">{row.ai_type_label ?? "Non qualifié"}</td>
                      <td className="muted">{row.phase_label}</td>
                      <td className="muted">{formatEuro(row.expected_benefit_eur)}</td>
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
    </>
  );
}
