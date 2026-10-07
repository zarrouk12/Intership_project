/** Formatage francais des nombres, montants et libelles metier. */

const nf = new Intl.NumberFormat("fr-FR");
const nf1 = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });

export const formatNumber = (value: number): string => nf.format(Math.round(value));

export const formatDecimal = (value: number): string => nf1.format(value);

/** Montant compact : 2,4 M EUR / 185 k EUR / 940 EUR. */
export function formatEuro(value: number, compact = true): string {
  if (!Number.isFinite(value)) return "-";
  if (compact && Math.abs(value) >= 1_000_000) return `${nf1.format(value / 1_000_000)} M€`;
  if (compact && Math.abs(value) >= 1_000) return `${nf.format(Math.round(value / 1000))} k€`;
  return `${nf.format(Math.round(value))} €`;
}

export function formatPercent(value: number, digits = 0): string {
  return `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: digits }).format(value)} %`;
}

export function formatDate(iso?: string | null): string {
  if (!iso) return "-";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" });
}

export const initials = (name: string): string =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");

/* ------------------------------------------------------- libelles metier */

export const STATUS_LABELS: Record<string, string> = {
  brouillon: "Brouillon",
  evalue: "Évalué",
  business_case: "Business case",
  approuve: "Approuvé",
  en_poc: "En POC",
  en_attente: "En attente",
  rejete: "Rejeté",
};

export const STATUS_TONES: Record<string, string> = {
  brouillon: "badge-grey",
  evalue: "badge-grey",
  business_case: "badge-teal",
  approuve: "badge-green",
  en_poc: "badge-amber",
  en_attente: "badge-amber",
  rejete: "badge-red",
};

export const PHASE_LABELS: Record<string, string> = {
  qualification: "Qualification",
  cadrage: "Cadrage",
  poc: "POC",
  pilote: "Pilote",
  production: "En production",
};

/** Couleur de serie par type de solution, conforme au design system. */
export const AI_TYPE_COLORS: Record<string, string> = {
  ia_classique: "#157F5C",
  generative: "#1C6B7D",
  agentique: "#A66A16",
  nlp: "#1C6B7D",
  computer_vision: "#0F5E44",
  bi: "#5E6F67",
  rpa: "#7A8F84",
  amelioration_processus: "#B23A3A",
};

export const aiTypeColor = (code?: string | null): string =>
  (code && AI_TYPE_COLORS[code]) || "#5E6F67";

/** Couleur d'une note de maturite 0-5 : rouge sous le seuil critique, ambre en vigilance. */
export function maturityColor(score: number, blocking: boolean, watch: boolean): string {
  if (blocking) return "var(--red)";
  if (watch) return "var(--amber)";
  if (score >= 4) return "var(--accent)";
  return "#4FA383";
}

export function severityTone(score: number): string {
  if (score >= 16) return "badge-red";
  if (score >= 10) return "badge-amber";
  if (score >= 5) return "badge-amber";
  return "badge-grey";
}

export const SEVERITY_LABELS: Record<string, string> = {
  faible: "Faible",
  modere: "Modéré",
  eleve: "Élevé",
  critique: "Critique",
};
