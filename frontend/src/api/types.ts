/** Types miroir des schemas Pydantic exposes par l'API. */

export interface Permission {
  id: number;
  code: string;
  label: string;
  module?: string | null;
  group?: string | null;
}

export type ScopeLevel = "platform" | "organization" | "site" | "department" | "own";

export interface Role {
  id: number;
  code: string;
  label: string;
  description?: string | null;
  scope_level: ScopeLevel;
  is_system: boolean;
  is_platform: boolean;
  permissions: Permission[];
}

/** Vue compacte d'un role, telle que renvoyee par /auth/me et /org/roles. */
export interface RoleSummary {
  id: number;
  code: string;
  label: string;
  description?: string | null;
  scope_level: ScopeLevel;
  is_system: boolean;
  is_platform: boolean;
  permission_codes: string[];
  user_count: number;
}

export interface NamedRef {
  id: number;
  name: string;
  code: string;
}

export interface AccessScope {
  level: ScopeLevel;
  level_label: string;
  organization_id: number;
  department_ids: number[];
  site_ids: number[];
  is_organization_wide: boolean;
}

/** Profil complet : c'est lui qui pilote menu, ecrans et actions disponibles. */
export interface CurrentUser {
  id: number;
  email: string;
  full_name: string;
  job_title?: string | null;
  is_active: boolean;
  is_superuser: boolean;
  last_login_at?: string | null;
  organization: NamedRef;
  sites: NamedRef[];
  departments: NamedRef[];
  roles: RoleSummary[];
  primary_role?: RoleSummary | null;
  permissions: string[];
  scope: AccessScope;
}

/** Ligne de la table des utilisateurs dans l'administration. */
export interface UserSummary {
  id: number;
  email: string;
  full_name: string;
  job_title?: string | null;
  is_active: boolean;
  is_superuser: boolean;
  last_login_at?: string | null;
  role_codes: string[];
  role_labels: string[];
  department_names: string[];
  site_names: string[];
  scope_level: ScopeLevel;
}

export interface UserDetail {
  id: number;
  organization_id: number;
  department_id?: number | null;
  email: string;
  full_name: string;
  job_title?: string | null;
  is_active: boolean;
  is_superuser: boolean;
  last_login_at?: string | null;
  roles: Role[];
  departments: NamedRef[];
  sites: NamedRef[];
}

export interface RoleTemplate {
  code: string;
  label: string;
  description: string;
  scope_level: ScopeLevel;
  scope_label: string;
  is_platform: boolean;
  permissions: string[];
}

export interface Organization {
  id: number;
  name: string;
  code: string;
  industry?: string | null;
  country?: string | null;
  description?: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface Site {
  id: number;
  name: string;
  code: string;
  city?: string | null;
  country?: string | null;
  site_type?: string | null;
}

export interface Department {
  id: number;
  name: string;
  code: string;
  family?: string | null;
  head_name?: string | null;
  site_id?: number | null;
}

/* ------------------------------------------------------------ diagnostic */
export interface DimensionScore {
  axis: "technique" | "metier";
  dimension_code: string;
  dimension_label: string;
  score: number;
  weight: number;
  confidence: number;
  weighted_score: number;
  max_weighted: number;
  is_blocking: boolean;
  is_watch: boolean;
  is_critical: boolean;
  /** Faux tant que la dimension n'a pas été instruite (confiance nulle). */
  is_answered: boolean;
  evidence?: string | null;
}

export interface MaturityLevel {
  level: number;
  label: string;
  description: string;
}

export interface Readiness {
  global_score: number;
  level: number;
  level_label: string;
  level_description: string;
  technical_average: number;
  business_average: number;
  completion_rate: number;
  answered_count: number;
  total_count: number;
  blocking_threshold: number;
  dimensions: DimensionScore[];
  blocking_dimensions: DimensionScore[];
  watch_dimensions: DimensionScore[];
  pending_dimensions: DimensionScore[];
  maturity_scale: MaturityLevel[];
}

/** Une réponse de diagnostic, telle qu'elle est éditée dans le questionnaire. */
export interface AssessmentResponse {
  id: number;
  assessment_id: number;
  axis: "technique" | "metier";
  dimension_code: string;
  dimension_label: string;
  question?: string | null;
  score: number;
  weight: number;
  confidence: number;
  evidence?: string | null;
  owner?: string | null;
  is_critical?: boolean | null;
}

export interface AssessmentDetail extends Assessment {
  responses: AssessmentResponse[];
}

export interface Assessment {
  id: number;
  name: string;
  campaign?: string | null;
  site_id?: number | null;
  status: string;
  completion_rate: number;
  blocking_threshold: number;
  notes?: string | null;
}

/* ---------------------------------------------------------- opportunites */
export interface Recommendation {
  id: number;
  opportunity_id: number;
  ai_type: string;
  ai_type_label: string;
  solution_pattern?: string | null;
  rationale?: string | null;
  confidence: number;
  fired_rules?: FiredRule[] | null;
  alternatives?: Alternative[] | null;
  guardrails?: string[] | null;
}

export interface FiredRule {
  code: string;
  label: string;
  weight: number;
  satisfied: boolean;
  blocking: boolean;
}

export interface Alternative {
  ai_type: string;
  label: string;
  score: number;
  reason: string;
}

export interface Opportunity {
  id: number;
  organization_id: number;
  code: string;
  title: string;
  summary?: string | null;
  department_id?: number | null;
  site_id?: number | null;
  process_id?: number | null;
  as_is_context?: string | null;
  pain_points?: string | null;
  desired_outcome?: string | null;
  sponsor?: string | null;
  business_owner?: string | null;
  technical_owner?: string | null;
  phase: string;
  status: string;
  answers: Record<string, unknown>;

  data_available: boolean;
  data_structured: boolean;
  data_quality: number;
  ground_truth_available: boolean;
  unstructured_text: boolean;
  image_or_video: boolean;
  content_generation: boolean;
  multi_step_autonomy: boolean;
  rule_based: boolean;
  repetitive_task: boolean;
  reporting_need: boolean;
  process_unstable: boolean;
  regulated_gxp: boolean;
  human_in_the_loop: boolean;
  volume_per_month?: number | null;

  impact_business: number;
  impact_financial: number;
  feasibility: number;
  alignment: number;
  readiness: number;
  synergies: number;
  risk_probability: number;
  risk_impact: number;

  priority_score: number;
  priority_rank?: number | null;
  wave?: number | null;
  expected_benefit_eur: number;
  estimated_cost_eur: number;

  recommendation?: Recommendation | null;
  department_name?: string | null;
  site_name?: string | null;
}

export interface ScoreContribution {
  criterion: string;
  label: string;
  value: number;
  weight: number;
  contribution: number;
}

export interface ScoreExplanation {
  priority_score: number;
  weighted_sum: number;
  risk_score: number;
  risk_penalty: number;
  max_risk_penalty: number;
  weights: Record<string, number>;
  contributions: ScoreContribution[];
  formula: string;
}

export interface MatrixPoint {
  id: number;
  code: string;
  title: string;
  impact: number;
  feasibility: number;
  benefit: number;
  ai_type?: string | null;
  ai_type_label?: string | null;
  quadrant: string;
  priority_score: number;
}

export interface ReferenceItem {
  code: string;
  label: string;
}

export interface Reference {
  ai_types: ReferenceItem[];
  phases: ReferenceItem[];
  statuses: ReferenceItem[];
  scoring_weights: Record<string, number>;
}

export interface QuestionnaireQuestion {
  field: string;
  label: string;
  type: "text" | "textarea" | "number" | "boolean" | "scale";
  required?: boolean;
  unit?: string;
  min?: number;
  max?: number;
}

export interface QuestionnaireSection {
  code: string;
  title: string;
  questions: QuestionnaireQuestion[];
}

export interface Questionnaire {
  family?: string | null;
  common: QuestionnaireSection[];
  specific?: QuestionnaireSection | null;
  available_families: string[];
}

export interface DuplicatePair {
  source_id: number;
  source_code: string;
  source_title: string;
  target_id: number;
  target_code: string;
  target_title: string;
  similarity: number;
  shared_terms: string[];
  shared_assets: string[];
  verdict: string;
}

/* ------------------------------------------------------------ dashboards */
export interface KpiCardData {
  key: string;
  label: string;
  value: number;
  unit?: string | null;
  hint?: string | null;
  trend?: string | null;
  tone: string;
}

export interface PhaseBucket {
  code: string;
  label: string;
  count: number;
  share: number;
}

export interface PortfolioRow {
  id: number;
  code: string;
  title: string;
  department_name?: string | null;
  ai_type?: string | null;
  ai_type_label?: string | null;
  phase: string;
  phase_label: string;
  status: string;
  priority_score: number;
  priority_rank?: number | null;
  wave?: number | null;
  expected_benefit_eur: number;
  estimated_cost_eur?: number;
  risk_score: number;
}

export interface DirectionDashboard {
  kpis: KpiCardData[];
  matrix: MatrixPoint[];
  phases: PhaseBucket[];
  top_priorities: PortfolioRow[];
  readiness_global?: number | null;
  total_opportunities: number;
}

/* ---------------------------------------------------------------- valeur */
export interface BusinessCase {
  horizon_years: number;
  tco_eur: number;
  capex_eur: number;
  opex_annual_eur: number;
  annual_benefit_eur: number;
  cumulated_benefit_eur: number;
  net_value_eur: number;
  roi_percent: number;
  payback_months?: number | null;
  pnl_breakdown: Record<string, number>;
}

export interface KpiProgress {
  id: number;
  code: string;
  name: string;
  unit?: string | null;
  direction: string;
  baseline_value?: number | null;
  target_value?: number | null;
  current_value?: number | null;
  baseline_label?: string | null;
  target_label?: string | null;
  progress_percent?: number | null;
  opportunity_id?: number | null;
}

export interface ValueDashboard {
  portfolio: {
    projects: number;
    tco_eur: number;
    annual_benefit_eur: number;
    cumulated_benefit_eur: number;
    net_value_eur: number;
    roi_percent: number;
    average_payback_months?: number | null;
  };
  kpis: KpiProgress[];
  by_department: {
    department: string;
    tco_eur: number;
    annual_benefit_eur: number;
    roi_percent: number;
    count: number;
  }[];
  roi_ranking: {
    id: number;
    code: string;
    title: string;
    department_name?: string | null;
    tco_eur: number;
    annual_benefit_eur: number;
    roi_percent: number;
    payback_months?: number | null;
  }[];
}

/* -------------------------------------------------------- fiche projet */
export interface SheetRisk {
  title: string;
  category?: string | null;
  probability: number;
  impact: number;
  score: number;
  severity: string;
  mitigations: string[];
}

export interface ProjectSheet {
  code: string;
  title: string;
  generated_on: string;
  identity: {
    department_id?: number | null;
    sponsor?: string | null;
    business_owner?: string | null;
    technical_owner?: string | null;
    phase: string;
    status: string;
  };
  as_is: {
    context?: string | null;
    pain_points?: string | null;
    desired_outcome?: string | null;
  };
  recommendation: {
    ai_type?: string | null;
    ai_type_label?: string | null;
    solution_pattern?: string | null;
    rationale?: string | null;
    confidence?: number | null;
    alternatives: Alternative[];
    guardrails: string[];
    fired_rules: FiredRule[];
  };
  kpis: KpiProgress[];
  business_case: BusinessCase;
  risks: SheetRisk[];
  priority: ScoreExplanation & {
    rank?: number | null;
    portfolio_size: number;
    wave?: number | null;
  };
  project: {
    code?: string | null;
    next_gate_label?: string | null;
    next_gate_date?: string | null;
  };
}

export interface Notification {
  id: number;
  title: string;
  body?: string | null;
  level: string;
  entity_type?: string | null;
  entity_id?: number | null;
  is_read: boolean;
  created_at: string;
}


/* ------------------------------------------------- tableau de bord de departement */
export interface DepartmentDashboard {
  scope: AccessScope & { department_names: string[] };
  kpis: KpiCardData[];
  phases: PhaseBucket[];
  opportunities: PortfolioRow[];
  projects: {
    id: number;
    code: string;
    name: string;
    phase: string;
    phase_label: string;
    status: string;
    progress: number;
    next_gate_label?: string | null;
    next_gate_date?: string | null;
  }[];
  kpi_progress: KpiProgress[];
  risks: {
    id: number;
    title: string;
    category?: string | null;
    score: number;
    severity: string;
    status: string;
  }[];
}


/* ------------------------------------------------------------- M7 : priorisation */
export interface PrioritizedItem {
  id: number;
  code: string;
  title: string;
  priority_score: number;
  priority_rank: number;
  wave: number;
  department_name?: string | null;
  ai_type_label?: string | null;
  phase: string;
  status: string;
}

export interface PrioritizeResult {
  weights: Record<string, number>;
  items: PrioritizedItem[];
}


/* ------------------------------------- aide a la connexion (developpement seul) */
export interface DemoAccount {
  email: string;
  full_name: string;
  job_title?: string | null;
  role_label: string;
  scope_label: string;
  departments: string[];
}

export interface DemoAccounts {
  /** Renseigne seulement si l'exploitant a publie DEMO_PASSWORD. */
  password?: string | null;
  accounts: DemoAccount[];
}
