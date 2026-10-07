/**
 * Écran de connexion.
 *
 * L'authentification reste celle du backend : `login()` appelle `POST /auth/login`,
 * stocke le jeton JWT et la redirection suit le rôle via l'écran d'accueil. Ce fichier
 * ne touche qu'à la présentation, aux états d'erreur et à l'accessibilité.
 *
 * Aucun compte n'est écrit en dur ici. L'aide de connexion interroge
 * `GET /auth/demo-accounts`, qui n'existe qu'en environnement de développement : en
 * production elle répond 404 et le bloc disparaît sans modifier le code.
 */
import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import axios from "axios";

import { useDemoAccounts } from "../api/queries";
import {
  IconAlert,
  IconChevronDown,
  IconCross,
  IconEye,
  IconEyeOff,
  IconLock,
} from "../components/Icons";
import { useAuth } from "../lib/auth";

/** Les quatre temps du parcours, tels qu'ils structurent l'application. */
const ETAPES = [
  {
    numero: "01",
    titre: "Diagnostiquer",
    texte: "Évaluez la maturité métier, data et technologique.",
  },
  {
    numero: "02",
    titre: "Qualifier",
    texte:
      "Identifiez la solution la plus adaptée : IA, BI, automatisation ou optimisation de processus.",
  },
  {
    numero: "03",
    titre: "Prioriser",
    texte: "Comparez impact, faisabilité, risques, coûts et ROI.",
  },
  {
    numero: "04",
    titre: "Piloter la valeur",
    texte: "Suivez les projets, les KPI, les budgets et les bénéfices réalisés.",
  },
];

interface LoginError {
  /** Message affiché à l'utilisateur. */
  message: string;
  /** Précision facultative, quand une action de sa part est possible. */
  hint?: string;
  tone: "invalid" | "disabled" | "network";
}

/**
 * Traduit une erreur d'authentification en message actionnable.
 *
 * Le backend distingue déjà les cas : 401 pour des identifiants erronés, 403 pour un
 * compte désactivé. On conserve cette distinction plutôt que d'afficher un message
 * unique, qui laisserait l'utilisateur chercher une faute de frappe inexistante.
 */
function toLoginError(error: unknown): LoginError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;

    if (status === 401) {
      return {
        message: "Adresse e-mail ou mot de passe incorrect.",
        hint: "Vérifiez la saisie, puis réessayez.",
        tone: "invalid",
      };
    }
    if (status === 403) {
      return {
        message: "Ce compte est désactivé.",
        hint: "Contactez l'administrateur de votre organisation pour le réactiver.",
        tone: "disabled",
      };
    }
    if (status === 422) {
      return {
        message: "L'adresse e-mail saisie n'est pas valide.",
        tone: "invalid",
      };
    }
    if (!error.response) {
      return {
        message: "Service momentanément indisponible.",
        hint: "Vérifiez votre connexion, puis réessayez dans quelques instants.",
        tone: "network",
      };
    }
    return {
      message: "La connexion a échoué.",
      hint: "Réessayez, et contactez le support si le problème persiste.",
      tone: "network",
    };
  }
  return { message: "Une erreur inattendue est survenue.", tone: "network" };
}

/** Aide de développement : liste les comptes du jeu de démonstration. */
function DemoAccountsPanel({ onPick }: { onPick: (email: string, password?: string) => void }) {
  const { data } = useDemoAccounts();
  const [open, setOpen] = useState(false);

  if (!data || data.accounts.length === 0) return null;

  return (
    <div className="demo-panel">
      <button
        type="button"
        className="demo-toggle"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls="demo-accounts-list"
      >
        Comptes de démonstration
        <span className="demo-count">{data.accounts.length}</span>
        <IconChevronDown
          size={15}
          className={open ? "demo-caret open" : "demo-caret"}
          aria-hidden="true"
        />
      </button>

      {open && (
        <div id="demo-accounts-list" className="demo-list">
          <p className="demo-note">
            Environnement de développement. Ces comptes proviennent du jeu de données de
            démonstration et n'apparaissent pas en production.
          </p>
          {data.accounts.map((account) => (
            <button
              type="button"
              key={account.email}
              className="demo-item"
              onClick={() => onPick(account.email, data.password ?? undefined)}
            >
              <span className="demo-item-role">{account.role_label}</span>
              <span className="demo-item-email">{account.email}</span>
              <span className="demo-item-scope">
                {account.departments.length > 0
                  ? account.departments.join(", ")
                  : account.scope_label}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Login() {
  const { token, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [revealPassword, setRevealPassword] = useState(false);
  const [error, setError] = useState<LoginError | null>(null);
  const [pending, setPending] = useState(false);

  if (token) return <Navigate to="/" replace />;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      await login(email.trim(), password);
      // La destination suit le rôle : l'écran d'accueil aiguille selon les permissions.
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname ?? "/";
      navigate(from, { replace: true });
    } catch (loginError) {
      setError(toLoginError(loginError));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="login-page">
      {/* --------------------------------------------------------- panneau de gauche */}
      <aside className="login-aside">
        <div className="login-brand">
          <div className="brand-mark">
            <IconCross size={22} />
          </div>
          <div>
            <div className="brand-name">Medicacom</div>
            <div className="brand-sub">AOI Transformation</div>
          </div>
        </div>

        <div className="login-pitch">
          <h2>Transformez vos opportunités IA en projets mesurables et gouvernés.</h2>
          <p className="login-lead">
            Medicacom AOI Transformation accompagne les organisations pharmaceutiques de
            l'identification des besoins jusqu'au suivi de la valeur créée.
          </p>
          <p className="login-desc">
            Centralisez vos diagnostics, qualifiez les opportunités, évaluez la readiness,
            priorisez les investissements et pilotez chaque initiative jusqu'à sa mise en
            production.
          </p>
        </div>

        <ol className="login-steps">
          {ETAPES.map((etape) => (
            <li className="login-step" key={etape.numero}>
              <span className="login-step-head">
                <span className="login-step-num">{etape.numero}</span>
                <span className="login-step-dash" aria-hidden="true">
                  —
                </span>
                <span className="login-step-title">{etape.titre}</span>
              </span>
              <span className="login-step-text">{etape.texte}</span>
            </li>
          ))}
        </ol>
      </aside>

      {/* ---------------------------------------------------------- panneau de droite */}
      <div className="login-form-wrap">
        <div className="login-form">
          {/* Marque reprise ici : le panneau de gauche disparaît sur petit écran. */}
          <div className="login-brand login-brand-compact">
            <div className="brand-mark">
              <IconCross size={20} />
            </div>
            <div>
              <div className="brand-name">Medicacom</div>
              <div className="brand-sub">AOI Transformation</div>
            </div>
          </div>

          <div className="login-card">
            <h1 className="login-title">Bienvenue sur Medicacom AOI</h1>
            <p className="login-subtitle">
              Connectez-vous à votre espace sécurisé pour piloter vos initiatives de
              transformation.
            </p>

            <form onSubmit={submit} noValidate>
              <div className="field">
                <label htmlFor="email">Adresse e-mail professionnelle</label>
                <input
                  id="email"
                  name="email"
                  className="input"
                  type="email"
                  inputMode="email"
                  autoComplete="username"
                  autoCapitalize="none"
                  spellCheck={false}
                  placeholder="prenom.nom@votre-entreprise.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  aria-invalid={error?.tone === "invalid" || undefined}
                  aria-describedby={error ? "login-error" : undefined}
                  required
                  autoFocus
                />
              </div>

              <div className="field">
                <label htmlFor="password">Mot de passe</label>
                <div className="input-affix">
                  <input
                    id="password"
                    name="password"
                    className="input"
                    type={revealPassword ? "text" : "password"}
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    aria-invalid={error?.tone === "invalid" || undefined}
                    aria-describedby={error ? "login-error" : undefined}
                    required
                  />
                  <button
                    type="button"
                    className="input-affix-btn"
                    onClick={() => setRevealPassword((value) => !value)}
                    aria-label={
                      revealPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"
                    }
                    aria-pressed={revealPassword}
                    tabIndex={0}
                  >
                    {revealPassword ? <IconEyeOff size={18} /> : <IconEye size={18} />}
                  </button>
                </div>
                <a className="login-forgot" href="#recuperation">
                  Mot de passe oublié ?
                </a>
              </div>

              {/* aria-live : le lecteur d'écran annonce l'erreur sans déplacer le focus. */}
              <div aria-live="polite" aria-atomic="true">
                {error && (
                  <div id="login-error" className="login-error" role="alert">
                    <IconAlert size={18} />
                    <div>
                      <strong>{error.message}</strong>
                      {error.hint && <span>{error.hint}</span>}
                    </div>
                  </div>
                )}
              </div>

              <button type="submit" className="btn btn-primary login-submit" disabled={pending}>
                {pending && <span className="btn-spinner" aria-hidden="true" />}
                {pending ? "Connexion en cours..." : "Se connecter"}
              </button>
            </form>

            <p className="login-secure">
              <IconLock size={14} />
              Environnement sécurisé — accès réservé aux utilisateurs autorisés
            </p>

            <DemoAccountsPanel
              onPick={(pickedEmail, pickedPassword) => {
                setEmail(pickedEmail);
                if (pickedPassword) setPassword(pickedPassword);
                setError(null);
              }}
            />
          </div>

          <footer className="login-footer">
            <span>© 2026 Medicacom. Tous droits réservés.</span>
            <nav aria-label="Informations légales">
              <a href="#confidentialite">Confidentialité</a>
              <span aria-hidden="true">·</span>
              <a href="#securite">Sécurité</a>
              <span aria-hidden="true">·</span>
              <a href="#mentions-legales">Mentions légales</a>
            </nav>
          </footer>
        </div>
      </div>
    </div>
  );
}
