/**
 * Aiguillage de la page d'accueil selon les droits de l'utilisateur.
 *
 * Plutôt que onze tableaux de bord distincts, l'application sert la vue la plus
 * pertinente pour le périmètre de chacun : la Direction voit le portefeuille consolidé,
 * un responsable voit son département, un profil sans tableau de bord est renvoyé vers
 * l'écran qui correspond à son métier.
 */
import { Navigate } from "react-router-dom";

import { useAuth } from "../lib/auth";
import Dashboard from "./Dashboard";
import DepartmentDashboard from "./DepartmentDashboard";

export default function Home() {
  const { can, canAny } = useAuth();

  if (can("dashboard.direction")) return <Dashboard />;
  if (can("dashboard.department")) return <DepartmentDashboard />;

  // Profils sans tableau de bord dédié : on ouvre leur écran de travail principal,
  // du plus spécifique au plus général.
  if (can("admin.access")) return <Navigate to="/administration" replace />;
  if (canAny("data.manage", "architecture.manage")) return <Navigate to="/architecture" replace />;
  if (can("finance.manage")) return <Navigate to="/valeur" replace />;
  if (can("portfolio.read")) return <Navigate to="/portefeuille" replace />;
  if (can("finance.read")) return <Navigate to="/valeur" replace />;
  if (can("opportunity.read")) return <Navigate to="/opportunites" replace />;
  if (canAny("user.read", "role.read")) return <Navigate to="/administration" replace />;

  return (
    <div className="content">
      <div className="card">
        <div className="card-title" style={{ marginBottom: 8 }}>
          Aucun écran accessible
        </div>
        <p className="muted" style={{ marginTop: 0, lineHeight: 1.7, marginBottom: 0 }}>
          Votre compte ne porte encore aucun rôle. Contactez l'administrateur de votre
          organisation pour qu'il vous en attribue un.
        </p>
      </div>
    </div>
  );
}
