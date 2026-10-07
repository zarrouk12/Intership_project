/**
 * Routage applicatif.
 *
 * Chaque route métier est gardée par la permission qu'exige son écran. Cette garde est
 * un confort d'usage : elle affiche un message clair au lieu d'une cascade d'erreurs
 * réseau. L'autorisation qui compte reste celle du backend, appliquée à chaque appel.
 */
import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { RequireAuth, RequirePermission } from "./lib/auth";
import Administration from "./pages/Administration";
import Architecture from "./pages/Architecture";
import AuditLog from "./pages/AuditLog";
import Diagnostic from "./pages/Diagnostic";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Opportunities from "./pages/Opportunities";
import OpportunityForm from "./pages/OpportunityForm";
import Portfolio from "./pages/Portfolio";
import ProjectSheet from "./pages/ProjectSheet";
import Sheets from "./pages/Sheets";
import Value from "./pages/Value";

export default function App() {
  return (
    <Routes>
      <Route path="/connexion" element={<Login />} />
      <Route
        path="/*"
        element={
          <RequireAuth>
            <Layout>
              <Routes>
                <Route index element={<Home />} />

                <Route
                  path="diagnostic"
                  element={
                    <RequirePermission permission="diagnostic.read">
                      <Diagnostic />
                    </RequirePermission>
                  }
                />
                <Route
                  path="opportunites"
                  element={
                    <RequirePermission permission="opportunity.read">
                      <Opportunities />
                    </RequirePermission>
                  }
                />
                <Route
                  path="opportunites/nouvelle"
                  element={
                    <RequirePermission permission="opportunity.create">
                      <OpportunityForm />
                    </RequirePermission>
                  }
                />
                <Route
                  path="opportunites/:id/modifier"
                  element={
                    <RequirePermission permission="opportunity.update">
                      <OpportunityForm />
                    </RequirePermission>
                  }
                />
                <Route
                  path="architecture"
                  element={
                    <RequirePermission anyOf={["architecture.read", "data.read"]}>
                      <Architecture />
                    </RequirePermission>
                  }
                />
                <Route
                  path="portefeuille"
                  element={
                    <RequirePermission permission="portfolio.read">
                      <Portfolio />
                    </RequirePermission>
                  }
                />
                <Route
                  path="fiches"
                  element={
                    <RequirePermission permission="sheet.read">
                      <Sheets />
                    </RequirePermission>
                  }
                />
                <Route
                  path="fiches/:id"
                  element={
                    <RequirePermission permission="sheet.read">
                      <ProjectSheet />
                    </RequirePermission>
                  }
                />
                <Route
                  path="valeur"
                  element={
                    <RequirePermission permission="finance.read">
                      <Value />
                    </RequirePermission>
                  }
                />
                <Route
                  path="administration"
                  element={
                    <RequirePermission anyOf={["admin.access", "user.read", "role.read"]}>
                      <Administration />
                    </RequirePermission>
                  }
                />
                <Route
                  path="audit"
                  element={
                    <RequirePermission permission="audit.read">
                      <AuditLog />
                    </RequirePermission>
                  }
                />

                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Layout>
          </RequireAuth>
        }
      />
    </Routes>
  );
}
