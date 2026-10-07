"""M1 - Catalogue des permissions, niveaux de perimetre et modeles de roles.

Ce module est la source unique de verite du RBAC. Les routers, le seed et les tests
s'y referent : aucune decision d'autorisation n'est prise a partir d'un nom de role
code en dur ailleurs dans l'application.

Trois notions distinctes :

  - la PERMISSION dit *ce qui* est autorise (creer une opportunite, valider une gate) ;
  - le PERIMETRE dit *sur quoi* (toute la plateforme, une organisation, un site,
    un departement, ou les seuls objets dont on est contributeur) ;
  - le ROLE n'est qu'un paquet nomme de permissions, assorti d'un perimetre par defaut.

Un utilisateur peut porter plusieurs roles. Ses permissions sont l'union de celles de
ses roles ; son perimetre est le plus large de ceux de ses roles.
"""
from __future__ import annotations

from dataclasses import dataclass


# ======================================================================================
# Niveaux de perimetre, du plus large au plus etroit
# ======================================================================================

class ScopeLevel:
    PLATFORM = "platform"          # Medicacom : toutes les organisations clientes
    ORGANIZATION = "organization"  # une organisation entiere
    SITE = "site"                  # les sites rattaches a l'utilisateur
    DEPARTMENT = "department"      # les departements rattaches a l'utilisateur
    OWN = "own"                    # les seuls objets dont l'utilisateur est contributeur

    ORDER = [PLATFORM, ORGANIZATION, SITE, DEPARTMENT, OWN]
    LABELS = {
        PLATFORM: "Plateforme Medicacom",
        ORGANIZATION: "Organisation",
        SITE: "Site",
        DEPARTMENT: "Département",
        OWN: "Contributions personnelles",
    }

    @staticmethod
    def rank(level: str) -> int:
        """Plus le rang est bas, plus le perimetre est large."""
        try:
            return ScopeLevel.ORDER.index(level)
        except ValueError:
            return len(ScopeLevel.ORDER)

    @staticmethod
    def widest(levels) -> str:
        """Perimetre le plus large parmi ceux fournis."""
        candidates = [lvl for lvl in levels if lvl in ScopeLevel.ORDER]
        if not candidates:
            return ScopeLevel.OWN
        return min(candidates, key=ScopeLevel.rank)


# ======================================================================================
# Catalogue des permissions : (code, libelle, module, groupe)
# ======================================================================================

PERMISSIONS: list[tuple[str, str, str, str]] = [
    # --- M1 Organisation ---
    ("organization.read", "Consulter les informations de l'organisation", "M1", "Organisation"),
    ("organization.manage", "Modifier les informations de l'organisation", "M1", "Organisation"),
    ("site.read", "Consulter les sites", "M1", "Organisation"),
    ("site.manage", "Créer et modifier les sites", "M1", "Organisation"),
    ("department.read", "Consulter les départements", "M1", "Organisation"),
    ("department.manage", "Créer et modifier les départements", "M1", "Organisation"),
    ("user.read", "Consulter les utilisateurs et leurs droits", "M1", "Utilisateurs"),
    ("user.create", "Créer ou inviter un utilisateur", "M1", "Utilisateurs"),
    ("user.update", "Modifier un utilisateur, ses rôles et ses rattachements", "M1", "Utilisateurs"),
    ("user.disable", "Activer ou désactiver un utilisateur", "M1", "Utilisateurs"),
    ("role.read", "Consulter les rôles et leurs permissions", "M1", "Utilisateurs"),
    ("role.manage", "Créer et modifier les rôles de l'organisation", "M1", "Utilisateurs"),
    ("admin.access", "Accéder à l'administration de l'entreprise", "M1", "Administration"),
    ("platform.admin", "Administrer la plateforme et les organisations clientes", "M1", "Administration"),

    # --- M2 / M5 Diagnostic ---
    ("diagnostic.read", "Consulter les diagnostics et le readiness", "M2", "Diagnostic"),
    ("diagnostic.answer", "Répondre aux questionnaires de diagnostic", "M2", "Diagnostic"),
    ("diagnostic.validate", "Valider une campagne de diagnostic", "M2", "Diagnostic"),

    # --- M3 / M4 Opportunites ---
    ("opportunity.read", "Consulter les opportunités", "M3", "Opportunités"),
    ("opportunity.create", "Créer une opportunité", "M3", "Opportunités"),
    ("opportunity.update", "Modifier une opportunité", "M3", "Opportunités"),
    ("opportunity.validate", "Valider ou arbitrer une opportunité", "M3", "Opportunités"),
    ("recommendation.read", "Consulter le détail du moteur de qualification", "M4", "Opportunités"),
    ("recommendation.override", "Modifier la recommandation avec justification", "M4", "Opportunités"),

    # --- M6 Architecture et donnees ---
    ("architecture.read", "Consulter processus, applications et dépendances", "M6", "Architecture"),
    ("architecture.manage", "Tenir le référentiel processus et applications", "M6", "Architecture"),
    ("data.read", "Consulter les sources de données et leur qualité", "M6", "Données"),
    ("data.manage", "Tenir le référentiel des sources de données", "M6", "Données"),

    # --- M7 Portefeuille ---
    ("portfolio.read", "Consulter le portefeuille consolidé", "M7", "Portefeuille"),
    ("portfolio.prioritize", "Recalculer la priorisation du portefeuille", "M7", "Portefeuille"),

    # --- M8 Fiche projet ---
    ("sheet.read", "Consulter les fiches projet", "M8", "Fiche projet"),
    ("sheet.write", "Générer et versionner les fiches projet", "M8", "Fiche projet"),
    ("sheet.approve", "Rendre une décision de comité", "M8", "Fiche projet"),

    # --- M9 Projets ---
    ("project.read", "Consulter les projets et leur avancement", "M9", "Projets"),
    ("project.manage", "Piloter phases, jalons, tâches, risques et incidents", "M9", "Projets"),
    ("project.validate_gate", "Valider une gate de phase", "M9", "Projets"),

    # --- M10 Valeur ---
    ("finance.read", "Consulter coûts, gains, ROI et payback", "M10", "Valeur"),
    ("finance.manage", "Saisir coûts, bénéfices et mesures", "M10", "Valeur"),
    ("finance.validate", "Valider les hypothèses et les bénéfices financiers", "M10", "Valeur"),

    # --- M11 Tableaux de bord ---
    ("dashboard.direction", "Accéder au tableau de bord Direction", "M11", "Tableaux de bord"),
    ("dashboard.department", "Accéder au tableau de bord de département", "M11", "Tableaux de bord"),

    # --- M12 Audit ---
    ("audit.read", "Consulter le journal d'audit", "M12", "Audit"),
]

ALL_PERMISSIONS: list[str] = [code for code, _, _, _ in PERMISSIONS]
PERMISSION_LABELS: dict[str, str] = {code: label for code, label, _, _ in PERMISSIONS}

#: Permissions reservees a l'editeur : un administrateur d'entreprise ne peut ni se les
#: accorder ni les placer dans un role qu'il cree.
PLATFORM_ONLY: set[str] = {"platform.admin"}

#: Toutes les permissions de consultation, utile pour construire un role lecture seule.
READ_ONLY_PERMISSIONS: list[str] = [
    code
    for code in ALL_PERMISSIONS
    if code.endswith(".read") and code not in PLATFORM_ONLY
]

#: Correspondance entre l'ancien catalogue et le nouveau. Les jetons et les roles
#: existants continuent de fonctionner apres migration.
LEGACY_ALIASES: dict[str, list[str]] = {
    "org.manage": [
        "organization.manage", "site.manage", "department.manage",
        "user.create", "user.update", "user.disable", "role.manage",
    ],
    "diagnostic.write": ["diagnostic.answer"],
    "opportunity.write": ["opportunity.create", "opportunity.update"],
    "architecture.write": ["architecture.manage", "data.manage"],
    "project.write": ["project.manage"],
    "project.approve": ["project.validate_gate"],
    "value.write": ["finance.manage"],
    "admin.audit": ["audit.read"],
}


def expand_legacy(codes) -> set[str]:
    """Traduit d'eventuels codes de l'ancien catalogue vers le nouveau."""
    expanded: set[str] = set()
    for code in codes:
        if code in LEGACY_ALIASES:
            expanded.update(LEGACY_ALIASES[code])
        else:
            expanded.add(code)
    return expanded


# ======================================================================================
# Modeles de roles
# ======================================================================================

@dataclass(frozen=True)
class RoleTemplate:
    code: str
    label: str
    description: str
    scope_level: str
    permissions: tuple[str, ...]
    #: Un role systeme est fourni par la plateforme : son jeu de permissions n'est pas
    #: modifiable par l'administrateur d'entreprise.
    is_system: bool = True
    #: Un role de plateforme n'est attribuable qu'a un collaborateur Medicacom.
    is_platform: bool = False


def _p(*groups) -> tuple[str, ...]:
    """Concatene des groupes de permissions en supprimant les doublons."""
    out: list[str] = []
    for group in groups:
        for code in group:
            if code not in out:
                out.append(code)
    return tuple(out)


_READS = tuple(READ_ONLY_PERMISSIONS)

ROLE_TEMPLATES: list[RoleTemplate] = [
    RoleTemplate(
        code="admin_medicacom",
        label="Administrateur Medicacom",
        description=(
            "Administre la plateforme et les organisations clientes : référentiels, "
            "modèles de questionnaires, rôles disponibles et support des tenants."
        ),
        scope_level=ScopeLevel.PLATFORM,
        permissions=tuple(ALL_PERMISSIONS),
        is_platform=True,
    ),
    RoleTemplate(
        code="admin_entreprise",
        label="Administrateur entreprise",
        description=(
            "Administre son organisation : sites, départements, utilisateurs, rôles et "
            "paramètres. N'accède jamais à une autre organisation."
        ),
        scope_level=ScopeLevel.ORGANIZATION,
        permissions=_p(
            _READS,
            (
                "organization.manage", "site.manage", "department.manage",
                "user.create", "user.update", "user.disable", "role.manage",
                "admin.access", "audit.read",
            ),
        ),
    ),
    RoleTemplate(
        code="direction",
        label="Direction Générale",
        description=(
            "Vision globale du portefeuille, arbitrage et décision comité. "
            "N'administre pas les utilisateurs."
        ),
        scope_level=ScopeLevel.ORGANIZATION,
        permissions=_p(
            _READS,
            (
                "dashboard.direction", "dashboard.department",
                "opportunity.validate", "portfolio.prioritize",
                "project.validate_gate", "sheet.approve", "finance.validate", "audit.read",
            ),
        ),
    ),
    RoleTemplate(
        code="responsable_departement",
        label="Responsable de département",
        description=(
            "Pilote les besoins et les projets de son ou ses départements. Consulte les "
            "dépendances transverses sans pouvoir modifier les autres départements."
        ),
        scope_level=ScopeLevel.DEPARTMENT,
        permissions=_p(
            (
                "organization.read", "site.read", "department.read",
                "diagnostic.read", "diagnostic.answer", "diagnostic.validate",
                "opportunity.read", "opportunity.create", "opportunity.update",
                "recommendation.read", "architecture.read", "data.read",
                "portfolio.read", "sheet.read", "sheet.write",
                "project.read", "finance.read",
                "dashboard.department",
            ),
        ),
    ),
    RoleTemplate(
        code="contributeur_metier",
        label="Contributeur métier",
        description=(
            "Répond aux questionnaires qui lui sont assignés, documente les processus et "
            "propose des opportunités. Aucun arbitrage ni validation financière."
        ),
        scope_level=ScopeLevel.OWN,
        permissions=(
            "organization.read", "department.read",
            "diagnostic.read", "diagnostic.answer",
            "opportunity.read", "opportunity.create",
            "recommendation.read", "architecture.read", "data.read",
            "sheet.read", "project.read",
        ),
    ),
    RoleTemplate(
        code="dsi_architecte",
        label="DSI / Architecte SI",
        description=(
            "Évalue la faisabilité technique, tient l'architecture AS-IS et TO-BE et les "
            "dépendances applicatives, participe aux gates techniques."
        ),
        scope_level=ScopeLevel.ORGANIZATION,
        permissions=(
            "organization.read", "site.read", "department.read",
            "diagnostic.read", "diagnostic.answer",
            "opportunity.read", "opportunity.update",
            "recommendation.read",
            "architecture.read", "architecture.manage", "data.read",
            "portfolio.read", "sheet.read",
            "project.read", "project.validate_gate",
            "dashboard.department",
        ),
    ),
    RoleTemplate(
        code="data_office",
        label="Data Office / Data Engineer",
        description=(
            "Tient le référentiel des sources de données, leur qualité, leur ownership et "
            "les dépendances data interservices."
        ),
        scope_level=ScopeLevel.ORGANIZATION,
        permissions=(
            "organization.read", "site.read", "department.read",
            "diagnostic.read", "diagnostic.answer",
            "opportunity.read",
            "recommendation.read",
            "architecture.read", "data.read", "data.manage",
            "portfolio.read", "sheet.read", "project.read",
            "dashboard.department",
        ),
    ),
    RoleTemplate(
        code="ai_lead",
        label="AI Lead / Data Scientist",
        description=(
            "Analyse les opportunités qualifiées, peut amender la recommandation avec "
            "justification, définit les critères de performance et les garde-fous."
        ),
        scope_level=ScopeLevel.ORGANIZATION,
        permissions=(
            "organization.read", "site.read", "department.read",
            "diagnostic.read",
            "opportunity.read", "opportunity.update",
            "recommendation.read", "recommendation.override",
            "architecture.read", "data.read",
            "portfolio.read", "sheet.read", "sheet.write",
            "project.read", "project.validate_gate",
            "dashboard.department",
        ),
    ),
    RoleTemplate(
        code="finance",
        label="Finance / Contrôle de gestion",
        description=(
            "Instruit CAPEX, OPEX et gains, valide les hypothèses du business case et "
            "compare valeur attendue et valeur réalisée."
        ),
        scope_level=ScopeLevel.ORGANIZATION,
        permissions=(
            "organization.read", "site.read", "department.read",
            "diagnostic.read", "opportunity.read", "recommendation.read",
            "architecture.read", "data.read",
            "portfolio.read", "sheet.read",
            "project.read",
            "finance.read", "finance.manage", "finance.validate",
            "dashboard.department",
        ),
    ),
    RoleTemplate(
        code="pmo",
        label="PMO / Chef de projet",
        description=(
            "Gère le cycle de vie des projets : phases, jalons, tâches, risques, incidents, "
            "budget de suivi, gates et reporting."
        ),
        scope_level=ScopeLevel.ORGANIZATION,
        permissions=(
            "organization.read", "site.read", "department.read",
            "diagnostic.read", "opportunity.read", "recommendation.read",
            "architecture.read", "data.read",
            "portfolio.read", "sheet.read", "sheet.write",
            "project.read", "project.manage",
            "finance.read",
            "dashboard.department",
        ),
    ),
    RoleTemplate(
        code="auditeur",
        label="Auditeur / Lecture seule",
        description=(
            "Consulte preuves, scores, versions, décisions et journal d'audit. "
            "Aucune création, modification, suppression ni validation."
        ),
        scope_level=ScopeLevel.ORGANIZATION,
        permissions=_p(_READS, ("audit.read", "dashboard.department")),
    ),
]

ROLE_BY_CODE: dict[str, RoleTemplate] = {r.code: r for r in ROLE_TEMPLATES}


def role_matrix() -> dict[str, dict[str, bool]]:
    """Matrice role x permission, utilisee par la documentation et les tests."""
    return {
        template.code: {code: code in template.permissions for code in ALL_PERMISSIONS}
        for template in ROLE_TEMPLATES
    }
