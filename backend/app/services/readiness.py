"""M2 / M5 - Calcul du readiness a partir des reponses de diagnostic.

Score global : chaque dimension est notee de 0 a 5, ponderee par son poids et par la
confiance declaree de la reponse (une reponse mal etayee pese moins dans les deux termes
du rapport).

    score_global = 100 * somme(note x poids x confiance) / somme(5 x poids x confiance)

Moyenne d'axe : moyenne des notes ponderee par le seul poids des dimensions. La confiance
n'y intervient pas, car cette moyenne decrit le niveau de maturite constate, pas la
solidite du constat.

Dimension sous le seuil de la campagne (2,5 par defaut) :
  - marquee critique  -> bloquante, a remedier avant tout passage en production ;
  - non critique      -> point de vigilance, a traiter dans le plan de conduite du changement.

Dimension non encore evaluee : une confiance nulle signifie que la dimension n'a pas
encore ete instruite. Elle sort du calcul du score et des moyennes -- une dimension non
mesuree ne vaut pas zero -- et elle fait baisser le taux de completion de la campagne.
Le taux de completion est donc calcule, jamais saisi.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from app.models.diagnostic import Assessment, AssessmentResponse

MATURITY_LEVELS = {
    0: ("Inexistant", "Aucune pratique en place."),
    1: ("Initial", "Pratiques ponctuelles, non formalisées."),
    2: ("Partiel", "Pratiques partielles, dépendantes des personnes."),
    3: ("Opérationnel", "Suffisant pour un pilote, avec remédiations ciblées."),
    4: ("Maîtrisé", "Pratiques outillées et mesurées."),
    5: ("Optimisé", "Amélioration continue et industrialisation."),
}


@dataclass
class DimensionScore:
    axis: str
    dimension_code: str
    dimension_label: str
    score: float
    weight: float
    confidence: float
    weighted_score: float
    max_weighted: float
    is_blocking: bool
    is_watch: bool
    is_critical: bool
    is_answered: bool
    evidence: str | None = None

    def as_dict(self) -> dict:
        return {
            "axis": self.axis,
            "dimension_code": self.dimension_code,
            "dimension_label": self.dimension_label,
            "score": round(self.score, 2),
            "weight": self.weight,
            "confidence": self.confidence,
            "weighted_score": round(self.weighted_score, 3),
            "max_weighted": round(self.max_weighted, 3),
            "is_blocking": self.is_blocking,
            "is_watch": self.is_watch,
            "is_critical": self.is_critical,
            "is_answered": self.is_answered,
            "evidence": self.evidence,
        }


@dataclass
class ReadinessResult:
    global_score: float
    level: int
    level_label: str
    level_description: str
    technical_average: float
    business_average: float
    dimensions: list[DimensionScore] = field(default_factory=list)
    blocking: list[DimensionScore] = field(default_factory=list)
    watch: list[DimensionScore] = field(default_factory=list)
    pending: list[DimensionScore] = field(default_factory=list)
    completion_rate: float = 0.0
    answered_count: int = 0
    total_count: int = 0
    blocking_threshold: float = 2.5

    def as_dict(self) -> dict:
        return {
            "global_score": round(self.global_score, 1),
            "level": self.level,
            "level_label": self.level_label,
            "level_description": self.level_description,
            "technical_average": round(self.technical_average, 2),
            "business_average": round(self.business_average, 2),
            "completion_rate": round(self.completion_rate, 1),
            "answered_count": self.answered_count,
            "total_count": self.total_count,
            "blocking_threshold": self.blocking_threshold,
            "dimensions": [d.as_dict() for d in self.dimensions],
            "blocking_dimensions": [d.as_dict() for d in self.blocking],
            "watch_dimensions": [d.as_dict() for d in self.watch],
            "pending_dimensions": [d.as_dict() for d in self.pending],
            "maturity_scale": [
                {"level": lvl, "label": lab, "description": desc}
                for lvl, (lab, desc) in sorted(MATURITY_LEVELS.items())
            ],
        }


def _weighted_average(dimensions: Sequence[DimensionScore]) -> float:
    """Moyenne des notes ponderee par le poids, sur les seules dimensions evaluees."""
    answered = [d for d in dimensions if d.is_answered]
    total_weight = sum(d.weight for d in answered)
    if not total_weight:
        return 0.0
    return sum(d.score * d.weight for d in answered) / total_weight


def compute_readiness(
    responses: Iterable[AssessmentResponse],
    blocking_threshold: float = 2.5,
) -> ReadinessResult:
    """Agrege une liste de reponses en un score de readiness explicable."""
    dims: list[DimensionScore] = []
    total_weighted = 0.0
    total_max = 0.0

    for r in responses:
        weight = float(r.weight or 1.0)
        confidence = min(max(float(r.confidence if r.confidence is not None else 1.0), 0.0), 1.0)
        score = min(max(float(r.score or 0.0), 0.0), 5.0)
        weighted = score * weight * confidence
        maximum = 5.0 * weight * confidence
        total_weighted += weighted
        total_max += maximum

        # Une confiance nulle marque une dimension non encore instruite : elle
        # n'apporte ni au numerateur ni au denominateur, donc elle ne tire pas le
        # score vers le bas ; elle pese seulement sur le taux de completion.
        answered = confidence > 0
        below = answered and score < blocking_threshold
        critical = bool(getattr(r, "is_critical", False))
        dims.append(
            DimensionScore(
                axis=r.axis,
                dimension_code=r.dimension_code,
                dimension_label=r.dimension_label,
                score=score,
                weight=weight,
                confidence=confidence,
                weighted_score=weighted,
                max_weighted=maximum,
                is_blocking=below and critical,
                is_watch=below and not critical,
                is_critical=critical,
                is_answered=answered,
                evidence=r.evidence,
            )
        )

    global_score = (total_weighted / total_max * 100.0) if total_max else 0.0
    level = min(int(global_score // 20), 5)
    label, description = MATURITY_LEVELS[level]

    answered_count = sum(1 for d in dims if d.is_answered)
    total_count = len(dims)

    return ReadinessResult(
        global_score=global_score,
        level=level,
        level_label=label,
        level_description=description,
        technical_average=_weighted_average([d for d in dims if d.axis == "technique"]),
        business_average=_weighted_average([d for d in dims if d.axis == "metier"]),
        dimensions=dims,
        blocking=[d for d in dims if d.is_blocking],
        watch=[d for d in dims if d.is_watch],
        pending=[d for d in dims if not d.is_answered],
        completion_rate=(answered_count / total_count * 100.0) if total_count else 0.0,
        answered_count=answered_count,
        total_count=total_count,
        blocking_threshold=blocking_threshold,
    )


def compute_for_assessment(assessment: Assessment) -> ReadinessResult:
    return compute_readiness(
        assessment.responses,
        blocking_threshold=float(assessment.blocking_threshold or 2.5),
    )
