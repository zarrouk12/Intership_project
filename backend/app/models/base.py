"""Mixins communs et enumerations metier (stockees en texte pour rester portables)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class TenantMixin:
    """Isolation multi-tenant : toute table metier porte organization_id."""

    @staticmethod
    def _org_column():
        return mapped_column(
            Integer, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
        )


# --------------------------------------------------------------------------------------
# Referentiels (valeurs textuelles, validees cote Pydantic)
# --------------------------------------------------------------------------------------

class AIType:
    CLASSIC = "ia_classique"
    COMPUTER_VISION = "computer_vision"
    NLP = "nlp"
    GENERATIVE = "generative"
    AGENTIC = "agentique"
    BI = "bi"
    RPA = "rpa"
    PROCESS = "amelioration_processus"

    ALL = [CLASSIC, COMPUTER_VISION, NLP, GENERATIVE, AGENTIC, BI, RPA, PROCESS]
    LABELS = {
        CLASSIC: "IA classique",
        COMPUTER_VISION: "Computer Vision",
        NLP: "NLP",
        GENERATIVE: "Générative",
        AGENTIC: "Agentique",
        BI: "BI / Analytique",
        RPA: "RPA",
        PROCESS: "Amélioration processus",
    }


class Phase:
    """Phases du funnel TOGAF : opportunite -> production."""

    QUALIFICATION = "qualification"
    FRAMING = "cadrage"
    POC = "poc"
    PILOT = "pilote"
    PRODUCTION = "production"

    ALL = [QUALIFICATION, FRAMING, POC, PILOT, PRODUCTION]
    LABELS = {
        QUALIFICATION: "Qualification",
        FRAMING: "Cadrage / Business case",
        POC: "POC",
        PILOT: "Pilote",
        PRODUCTION: "En production",
    }


class OpportunityStatus:
    DRAFT = "brouillon"
    EVALUATED = "evalue"
    BUSINESS_CASE = "business_case"
    APPROVED = "approuve"
    IN_POC = "en_poc"
    REJECTED = "rejete"
    ON_HOLD = "en_attente"

    ALL = [DRAFT, EVALUATED, BUSINESS_CASE, APPROVED, IN_POC, REJECTED, ON_HOLD]


class ReadinessAxis:
    TECHNICAL = "technique"
    BUSINESS = "metier"

    ALL = [TECHNICAL, BUSINESS]


class RiskLevel:
    LOW = "faible"
    MODERATE = "modere"
    HIGH = "eleve"
    CRITICAL = "critique"

    ALL = [LOW, MODERATE, HIGH, CRITICAL]

    @staticmethod
    def from_score(score: int) -> str:
        if score >= 16:
            return RiskLevel.CRITICAL
        if score >= 10:
            return RiskLevel.HIGH
        if score >= 5:
            return RiskLevel.MODERATE
        return RiskLevel.LOW


class DependencyKind:
    DATA = "data"
    PROCESS = "process"
    KPI = "kpi"
    APPLICATION = "application"
    ORGANIZATION = "organisation"

    ALL = [DATA, PROCESS, KPI, APPLICATION, ORGANIZATION]


class ApprovalDecision:
    PENDING = "en_attente"
    GO = "go"
    NO_GO = "no_go"
    REVISION = "revision"

    ALL = [PENDING, GO, NO_GO, REVISION]
