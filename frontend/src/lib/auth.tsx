/**
 * Contexte d'authentification : jeton JWT, profil courant, droits et périmètre.
 *
 * Les droits ne sont jamais déduits d'un nom de rôle côté client : ils viennent de la
 * liste de permissions renvoyée par `/auth/me`. Masquer un bouton avec `can()` relève du
 * confort d'usage ; la protection réelle est celle du backend, qui revérifie chaque appel.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";

import { api, getToken, setToken, setUnauthorizedHandler } from "../api/client";
import { useMe } from "../api/queries";
import type { CurrentUser, ScopeLevel } from "../api/types";

interface AuthContextValue {
  token: string | null;
  user: CurrentUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  /** Vrai si l'utilisateur détient **toutes** les permissions demandées. */
  can: (...permissions: string[]) => boolean;
  /** Vrai si l'utilisateur détient **au moins une** des permissions demandées. */
  canAny: (...permissions: string[]) => boolean;
  /** Vrai si l'utilisateur porte l'un des rôles indiqués. */
  hasRole: (...roles: string[]) => boolean;
  /** Niveau de périmètre effectif : plateforme, organisation, site, département, propre. */
  scopeLevel: ScopeLevel | null;
  /** Vrai lorsque l'utilisateur voit et modifie toute son organisation. */
  isOrganizationWide: boolean;
  /** Vrai pour un rôle strictement en lecture, qui ne porte aucun droit d'écriture. */
  isReadOnly: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Suffixes de permission qui traduisent un droit d'écriture. */
const WRITE_SUFFIXES = [
  ".manage",
  ".create",
  ".update",
  ".disable",
  ".answer",
  ".validate",
  ".validate_gate",
  ".override",
  ".prioritize",
  ".write",
  ".approve",
];

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => getToken());
  const queryClient = useQueryClient();
  const { data: user, isLoading } = useMe(Boolean(token));

  const logout = useCallback(() => {
    setToken(null);
    setTokenState(null);
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    setUnauthorizedHandler(() => setTokenState(null));
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const { data } = await api.post<{ access_token: string }>("/auth/login", { email, password });
      setToken(data.access_token);
      setTokenState(data.access_token);
      await queryClient.invalidateQueries();
    },
    [queryClient],
  );

  const permissions = useMemo(() => new Set(user?.permissions ?? []), [user]);

  const can = useCallback(
    (...codes: string[]) => codes.every((code) => permissions.has(code)),
    [permissions],
  );

  const canAny = useCallback(
    (...codes: string[]) => codes.some((code) => permissions.has(code)),
    [permissions],
  );

  const hasRole = useCallback(
    (...codes: string[]) => codes.some((code) => user?.roles.some((role) => role.code === code)),
    [user],
  );

  const isReadOnly = useMemo(
    () => Boolean(user) && ![...permissions].some((code) => WRITE_SUFFIXES.some((s) => code.endsWith(s))),
    [user, permissions],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user: user ?? null,
      isLoading: Boolean(token) && isLoading,
      login,
      logout,
      can,
      canAny,
      hasRole,
      scopeLevel: user?.scope.level ?? null,
      isOrganizationWide: user?.scope.is_organization_wide ?? false,
      isReadOnly,
    }),
    [token, user, isLoading, login, logout, can, canAny, hasRole, isReadOnly],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth doit être utilisé à l'intérieur de AuthProvider");
  return context;
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { token, user, isLoading } = useAuth();
  const location = useLocation();

  if (!token) return <Navigate to="/connexion" state={{ from: location }} replace />;
  if (isLoading || !user) {
    return (
      <div className="state">
        <div className="spinner" />
        Chargement de la session...
      </div>
    );
  }
  return <>{children}</>;
}

/**
 * Garde de route par permission. Un utilisateur qui atteint une page interdite,
 * par une URL collée par exemple, voit un message explicite plutôt qu'un écran vide
 * ou une cascade d'erreurs réseau.
 */
export function RequirePermission({
  permission,
  anyOf,
  children,
}: {
  permission?: string;
  anyOf?: string[];
  children: ReactNode;
}) {
  const { can, canAny, user } = useAuth();
  const allowed = permission ? can(permission) : anyOf ? canAny(...anyOf) : true;

  if (allowed) return <>{children}</>;

  const required = permission ?? (anyOf ?? []).join(" ou ");
  return (
    <div className="content">
      <div className="card">
        <div className="card-title" style={{ marginBottom: 8 }}>
          Accès non autorisé
        </div>
        <p className="muted" style={{ marginTop: 0, lineHeight: 1.7 }}>
          Votre rôle {user?.primary_role?.label ? `« ${user.primary_role.label} »` : "actuel"} ne
          donne pas accès à cette page. Elle requiert la permission <code>{required}</code>.
        </p>
        <p className="muted" style={{ marginBottom: 0 }}>
          Contactez l'administrateur de votre organisation si vous pensez qu'il s'agit d'une erreur.
        </p>
      </div>
    </div>
  );
}
