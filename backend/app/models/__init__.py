"""Import centralise des modeles (necessaire pour Alembic autogenerate)."""
from app.models.base import (  # noqa: F401
    AIType,
    ApprovalDecision,
    DependencyKind,
    OpportunityStatus,
    Phase,
    ReadinessAxis,
    RiskLevel,
    TimestampMixin,
)
from app.models.organization import Department, Organization, Site  # noqa: F401
from app.models.rbac import (  # noqa: F401
    Permission,
    Role,
    User,
    role_permission,
    user_department,
    user_role,
    user_site,
)
from app.models.diagnostic import Assessment, AssessmentResponse  # noqa: F401
from app.models.architecture import KPI, Application, DataSource, Process  # noqa: F401
from app.models.opportunity import AIRecommendation, Dependency, Opportunity  # noqa: F401
from app.models.project import (  # noqa: F401
    Issue,
    Milestone,
    Mitigation,
    Project,
    Risk,
    Stage,
    Task,
)
from app.models.value import Benefit, Cost, Measurement  # noqa: F401
from app.models.governance import (  # noqa: F401
    Approval,
    AuditLog,
    Document,
    Notification,
    Version,
)

__all__ = [
    "Organization",
    "Site",
    "Department",
    "User",
    "Role",
    "Permission",
    "Assessment",
    "AssessmentResponse",
    "Process",
    "Application",
    "DataSource",
    "KPI",
    "Opportunity",
    "AIRecommendation",
    "Dependency",
    "Project",
    "Stage",
    "Milestone",
    "Task",
    "Risk",
    "Mitigation",
    "Issue",
    "Cost",
    "Benefit",
    "Measurement",
    "Document",
    "Version",
    "Approval",
    "Notification",
    "AuditLog",
]
