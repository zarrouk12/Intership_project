"""M7 - Moteur de priorisation du portefeuille.

score = 0.25*impact_metier + 0.20*impact_financier + 0.20*faisabilite
      + 0.15*alignement    + 0.10*readiness       + 0.10*synergies
      - penalite_risque

Le risque brut vaut probabilite (1-5) x impact (1-5), soit 1 a 25. La penalite est
normalisee sur l'echelle du score : penalite = (risque / 25) * MAX_RISK_PENALTY.
Les poids sont parametrables (par organisation ou par appel) et leur somme est
verifiee : toute ponderation fournie est renormalisee a 1 pour rester comparable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

DEFAULT_WEIGHTS: dict[str, float] = {
    "impact_business": 0.25,
    "impact_financial": 0.20,
    "feasibility": 0.20,
    "alignment": 0.15,
    "readiness": 0.10,
    "synergies": 0.10,
}

CRITERION_LABELS: dict[str, str] = {
    "impact_business": "Impact métier",
    "impact_financial": "Impact financier / P&L",
    "feasibility": "Faisabilité technique",
    "alignment": "Alignement stratégique",
    "readiness": "Readiness org.",
    "synergies": "Synergies",
}

# Penalite maximale (en points de score) appliquee pour un risque maximal de 25.
MAX_RISK_PENALTY = 15.0


@dataclass
class ScoreBreakdown:
    priority_score: float
    weighted_sum: float
    risk_score: int
    risk_penalty: float
    weights: dict[str, float]
    contributions: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "priority_score": round(self.priority_score, 1),
            "weighted_sum": round(self.weighted_sum, 2),
            "risk_score": self.risk_score,
            "risk_penalty": round(self.risk_penalty, 2),
            "max_risk_penalty": MAX_RISK_PENALTY,
            "weights": self.weights,
            "contributions": self.contributions,
            "formula": (
                "score = 0,25 × impact métier + 0,20 × impact financier + 0,20 × faisabilité "
                "+ 0,15 × alignement + 0,10 × readiness + 0,10 × synergies − pénalité de risque"
            ),
        }


def normalize_weights(weights: dict[str, float] | None) -> dict[str, float]:
    """Complete les poids manquants par defaut puis renormalise la somme a 1."""
    merged = dict(DEFAULT_WEIGHTS)
    if weights:
        for key, value in weights.items():
            if key in merged and value is not None:
                merged[key] = float(value)
    total = sum(merged.values())
    if total <= 0:
        return dict(DEFAULT_WEIGHTS)
    return {k: round(v / total, 6) for k, v in merged.items()}


def risk_penalty(probability: int, impact: int) -> tuple[int, float]:
    p = min(max(int(probability or 1), 1), 5)
    i = min(max(int(impact or 1), 1), 5)
    raw = p * i
    return raw, (raw / 25.0) * MAX_RISK_PENALTY


def compute_priority_score(
    impact_business: float,
    impact_financial: float,
    feasibility: float,
    alignment: float,
    readiness: float,
    synergies: float,
    risk_probability: int = 1,
    risk_impact: int = 1,
    weights: dict[str, float] | None = None,
) -> ScoreBreakdown:
    """Calcule le score de priorite et renvoie le detail de chaque contribution."""
    w = normalize_weights(weights)
    values = {
        "impact_business": float(impact_business or 0.0),
        "impact_financial": float(impact_financial or 0.0),
        "feasibility": float(feasibility or 0.0),
        "alignment": float(alignment or 0.0),
        "readiness": float(readiness or 0.0),
        "synergies": float(synergies or 0.0),
    }

    contributions = []
    weighted_sum = 0.0
    for key, value in values.items():
        clamped = min(max(value, 0.0), 100.0)
        contribution = clamped * w[key]
        weighted_sum += contribution
        contributions.append(
            {
                "criterion": key,
                "label": CRITERION_LABELS[key],
                "value": round(clamped, 1),
                "weight": w[key],
                "contribution": round(contribution, 2),
            }
        )

    raw_risk, penalty = risk_penalty(risk_probability, risk_impact)
    final = max(0.0, min(100.0, weighted_sum - penalty))

    return ScoreBreakdown(
        priority_score=final,
        weighted_sum=weighted_sum,
        risk_score=raw_risk,
        risk_penalty=penalty,
        weights=w,
        contributions=contributions,
    )


def score_opportunity(opportunity, weights: dict[str, float] | None = None) -> ScoreBreakdown:
    return compute_priority_score(
        impact_business=opportunity.impact_business,
        impact_financial=opportunity.impact_financial,
        feasibility=opportunity.feasibility,
        alignment=opportunity.alignment,
        readiness=opportunity.readiness,
        synergies=opportunity.synergies,
        risk_probability=opportunity.risk_probability,
        risk_impact=opportunity.risk_impact,
        weights=weights,
    )


def assign_ranks_and_waves(opportunities: Sequence, wave_size: int = 6) -> list:
    """Classe les opportunites par score decroissant et les repartit en vagues."""
    ordered = sorted(opportunities, key=lambda o: (-(o.priority_score or 0.0), o.id))
    for index, opp in enumerate(ordered):
        opp.priority_rank = index + 1
        opp.wave = (index // max(wave_size, 1)) + 1
    return ordered


def quadrant(impact: float, feasibility: float, threshold: float = 50.0) -> str:
    """Positionne une opportunite dans la matrice Impact x Faisabilite."""
    if impact >= threshold and feasibility >= threshold:
        return "prioritaire"
    if impact >= threshold and feasibility < threshold:
        return "reflechir"
    if impact < threshold and feasibility >= threshold:
        return "quick_win"
    return "ecarter"


def portfolio_matrix(opportunities: Iterable) -> list[dict]:
    """Serie de points pour la matrice Impact x Faisabilite (taille = benefice attendu)."""
    points = []
    for o in opportunities:
        points.append(
            {
                "id": o.id,
                "code": o.code,
                "title": o.title,
                "impact": round(float(o.impact_business or 0.0), 1),
                "feasibility": round(float(o.feasibility or 0.0), 1),
                "benefit": float(o.expected_benefit_eur or 0.0),
                "ai_type": o.recommendation.ai_type if o.recommendation else None,
                "ai_type_label": o.recommendation.ai_type_label if o.recommendation else None,
                "quadrant": quadrant(
                    float(o.impact_business or 0.0), float(o.feasibility or 0.0)
                ),
                "priority_score": round(float(o.priority_score or 0.0), 1),
            }
        )
    return points
