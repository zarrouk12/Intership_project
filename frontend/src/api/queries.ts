/** Hooks TanStack Query : un hook par ressource de l'API. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";
import type {
  Assessment,
  AssessmentDetail,
  AssessmentResponse,
  DemoAccounts,
  DepartmentDashboard,
  BusinessCase,
  CurrentUser,
  Department,
  DirectionDashboard,
  DuplicatePair,
  Notification,
  Opportunity,
  PrioritizeResult,
  PortfolioRow,
  ProjectSheet,
  Questionnaire,
  Readiness,
  Recommendation,
  Reference,
  ScoreExplanation,
  Organization,
  RoleSummary,
  RoleTemplate,
  Site,
  UserDetail,
  UserSummary,
  ValueDashboard,
} from "./types";

async function get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const { data } = await api.get<T>(url, { params });
  return data;
}

/* ------------------------------------------------------------------- M1 */

/**
 * Comptes de demonstration proposes a la connexion.
 *
 * L'endpoint n'existe qu'en developpement : en production il repond 404 et le hook
 * renvoie simplement rien. Aucun compte n'est donc ecrit dans le code de l'interface,
 * et passer en production suffit a faire disparaitre l'aide.
 */
export const useDemoAccounts = () =>
  useQuery({
    queryKey: ["demo-accounts"],
    queryFn: async () => {
      try {
        return await get<DemoAccounts>("/auth/demo-accounts");
      } catch {
        return null;
      }
    },
    retry: false,
    staleTime: Infinity,
  });

export const useMe = (enabled: boolean) =>
  useQuery({
    queryKey: ["me"],
    queryFn: () => get<CurrentUser>("/auth/me"),
    enabled,
    staleTime: 5 * 60 * 1000,
  });

export const useSites = (enabled = true) =>
  useQuery({
    queryKey: ["sites"],
    queryFn: () => get<Site[]>("/org/sites"),
    enabled,
    staleTime: 10 * 60 * 1000,
  });

export const useDepartments = (enabled = true) =>
  useQuery({
    queryKey: ["departments"],
    queryFn: () => get<Department[]>("/org/departments"),
    enabled,
    staleTime: 10 * 60 * 1000,
  });

export const useOrganization = (enabled = true) =>
  useQuery({
    queryKey: ["organization"],
    queryFn: () => get<Organization>("/org/organization"),
    enabled,
    staleTime: 10 * 60 * 1000,
  });

/* ------------------------------------------------- M1 : administration des utilisateurs */
export const useUsers = (enabled = true) =>
  useQuery({ queryKey: ["users"], queryFn: () => get<UserSummary[]>("/org/users"), enabled });

export const useRoles = (enabled = true) =>
  useQuery({ queryKey: ["roles"], queryFn: () => get<RoleSummary[]>("/org/roles"), enabled });

export const useRoleTemplates = (enabled = true) =>
  useQuery({
    queryKey: ["role-templates"],
    queryFn: () => get<RoleTemplate[]>("/org/role-templates"),
    enabled,
    staleTime: 30 * 60 * 1000,
  });

export const usePermissionCatalog = (enabled = true) =>
  useQuery({
    queryKey: ["permission-catalog"],
    queryFn: () => get<{ code: string; label: string; module?: string | null; group?: string | null }[]>(
      "/org/permissions",
    ),
    enabled,
    staleTime: 30 * 60 * 1000,
  });

function invalidateAdmin(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["users"] });
  queryClient.invalidateQueries({ queryKey: ["roles"] });
}

export const useCreateUser = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const { data } = await api.post<UserDetail>("/org/users", payload);
      return data;
    },
    onSuccess: () => invalidateAdmin(queryClient),
  });
};

export const useUpdateUser = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: { id: number } & Record<string, unknown>) => {
      const { data } = await api.patch<UserDetail>(`/org/users/${id}`, payload);
      return data;
    },
    onSuccess: () => invalidateAdmin(queryClient),
  });
};

export const useCreateRole = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const { data } = await api.post<RoleSummary>("/org/roles", payload);
      return data;
    },
    onSuccess: () => invalidateAdmin(queryClient),
  });
};

export const useUpdateRole = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: { id: number } & Record<string, unknown>) => {
      const { data } = await api.patch<RoleSummary>(`/org/roles/${id}`, payload);
      return data;
    },
    onSuccess: () => invalidateAdmin(queryClient),
  });
};

export const useCreateSite = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const { data } = await api.post<Site>("/org/sites", payload);
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sites"] }),
  });
};

export const useCreateDepartment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const { data } = await api.post<Department>("/org/departments", payload);
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["departments"] }),
  });
};

export const useAuditLog = (enabled = true, limit = 60) =>
  useQuery({
    queryKey: ["audit-log", limit],
    queryFn: () =>
      get<
        {
          id: number;
          user_email?: string | null;
          action: string;
          entity_type: string;
          entity_label?: string | null;
          old_value?: Record<string, unknown> | null;
          new_value?: Record<string, unknown> | null;
          created_at: string;
        }[]
      >("/admin/audit-logs", { limit }),
    enabled,
  });

/* ---------------------------------------------------------------- M2/M5 */
export const useReadiness = (siteId?: number) =>
  useQuery({
    queryKey: ["readiness", siteId ?? null],
    queryFn: () => get<Readiness>("/diagnostic/readiness", siteId ? { site_id: siteId } : undefined),
  });

export const useAssessments = (enabled = true) =>
  useQuery({
    queryKey: ["assessments"],
    queryFn: () => get<Assessment[]>("/diagnostic/assessments"),
    enabled,
  });

/** Detail d'une campagne avec ses reponses : c'est la base du questionnaire editable. */
export const useAssessmentDetail = (assessmentId?: number) =>
  useQuery({
    queryKey: ["assessment", assessmentId],
    queryFn: () => get<AssessmentDetail>(`/diagnostic/assessments/${assessmentId}`),
    enabled: Boolean(assessmentId),
  });

/**
 * Enregistre les reponses modifiees, une requete par dimension.
 *
 * Le backend recalcule le readiness et le taux de completion a partir des reponses :
 * il n'y a donc rien d'autre a synchroniser que l'invalidation du cache.
 */
export const useSaveResponses = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (
      changes: { id: number; score?: number; confidence?: number; weight?: number; evidence?: string | null }[],
    ) => {
      const saved: AssessmentResponse[] = [];
      for (const change of changes) {
        const { id, ...payload } = change;
        const { data } = await api.patch<AssessmentResponse>(`/diagnostic/responses/${id}`, payload);
        saved.push(data);
      }
      return saved;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["readiness"] });
      queryClient.invalidateQueries({ queryKey: ["assessment"] });
      queryClient.invalidateQueries({ queryKey: ["assessments"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
};

/* ------------------------------------------------------------- M3/M4/M7 */
export interface OpportunityFilters {
  department_id?: number;
  ai_type?: string;
  phase?: string;
  status?: string;
  min_score?: number;
  search?: string;
}

export const useOpportunities = (filters: OpportunityFilters = {}) =>
  useQuery({
    queryKey: ["opportunities", filters],
    queryFn: () => get<Opportunity[]>("/opportunities", filters as Record<string, unknown>),
  });

export const useOpportunity = (id?: number) =>
  useQuery({
    queryKey: ["opportunity", id],
    queryFn: () => get<Opportunity>(`/opportunities/${id}`),
    enabled: Boolean(id),
  });

export const useReference = () =>
  useQuery({
    queryKey: ["reference"],
    queryFn: () => get<Reference>("/opportunities/reference"),
    staleTime: 30 * 60 * 1000,
  });

export const useQuestionnaire = (departmentId?: number) =>
  useQuery({
    queryKey: ["questionnaire", departmentId ?? null],
    queryFn: () =>
      get<Questionnaire>(
        "/opportunities/questionnaire",
        departmentId ? { department_id: departmentId } : undefined,
      ),
  });

export const useScoreExplanation = (id?: number) =>
  useQuery({
    queryKey: ["score", id],
    queryFn: () => get<ScoreExplanation>(`/opportunities/${id}/score`),
    enabled: Boolean(id),
  });

/** Invalide tout ce qui depend du portefeuille apres une ecriture. */
function invalidatePortfolio(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["opportunities"] });
  queryClient.invalidateQueries({ queryKey: ["opportunity"] });
  queryClient.invalidateQueries({ queryKey: ["portfolio"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard-department"] });
  queryClient.invalidateQueries({ queryKey: ["duplicates"] });
  queryClient.invalidateQueries({ queryKey: ["sheet"] });
}

export const useCreateOpportunity = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const { data } = await api.post<Opportunity>("/opportunities", payload);
      return data;
    },
    onSuccess: () => invalidatePortfolio(queryClient),
  });
};

export const useUpdateOpportunity = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: { id: number } & Record<string, unknown>) => {
      const { data } = await api.patch<Opportunity>(`/opportunities/${id}`, payload);
      return data;
    },
    onSuccess: () => invalidatePortfolio(queryClient),
  });
};

export const useDeleteOpportunity = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/opportunities/${id}`);
      return id;
    },
    onSuccess: () => invalidatePortfolio(queryClient),
  });
};

export const useQualify = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await api.post<Recommendation>(`/opportunities/${id}/qualify`);
      return data;
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ["opportunity", id] });
      queryClient.invalidateQueries({ queryKey: ["opportunities"] });
    },
  });
};

export const usePrioritize = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      weights?: Record<string, number>;
      wave_size?: number;
      apply_synergies?: boolean;
    }) => {
      const { data } = await api.post<PrioritizeResult>("/opportunities/prioritize", payload);
      return data;
    },
    onSuccess: () => invalidatePortfolio(queryClient),
  });
};

/* ------------------------------------------------------------------- M6 */
export const useDuplicates = (minSimilarity = 0.3, enabled = true) =>
  useQuery({
    queryKey: ["duplicates", minSimilarity],
    queryFn: () => get<DuplicatePair[]>("/crossings/duplicates", { min_similarity: minSimilarity }),
    enabled,
  });

/* ---------------------------------------------------------------- M8/M11 */
export const useDashboard = (enabled = true) =>
  useQuery({
    queryKey: ["dashboard"],
    queryFn: () => get<DirectionDashboard>("/dashboards/direction"),
    enabled,
  });

export const useDepartmentDashboard = (enabled = true) =>
  useQuery({
    queryKey: ["dashboard-department"],
    queryFn: () => get<DepartmentDashboard>("/dashboards/department"),
    enabled,
  });

export const usePortfolio = () =>
  useQuery({ queryKey: ["portfolio"], queryFn: () => get<PortfolioRow[]>("/dashboards/portfolio") });

export const useProjectSheet = (opportunityId?: number) =>
  useQuery({
    queryKey: ["sheet", opportunityId],
    queryFn: () => get<ProjectSheet>(`/sheets/opportunity/${opportunityId}/preview`),
    enabled: Boolean(opportunityId),
  });

export const useGenerateSheet = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (opportunityId: number) => {
      const { data } = await api.post(`/sheets/opportunity/${opportunityId}/generate`, {
        change_summary: "Soumission au comite depuis la fiche projet",
      });
      return data;
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ["sheet", id] });
    },
  });
};

/* ------------------------------------------------------------------ M10 */
export const useValueDashboard = () =>
  useQuery({ queryKey: ["value-dashboard"], queryFn: () => get<ValueDashboard>("/value/dashboard") });

export const useBusinessCase = (opportunityId?: number) =>
  useQuery({
    queryKey: ["business-case", opportunityId],
    queryFn: () => get<BusinessCase>(`/value/business-case/${opportunityId}`),
    enabled: Boolean(opportunityId),
  });

/* ------------------------------------------------------------------ M12 */
export const useNotifications = () =>
  useQuery({
    queryKey: ["notifications"],
    queryFn: () => get<Notification[]>("/admin/notifications"),
    staleTime: 60 * 1000,
  });
