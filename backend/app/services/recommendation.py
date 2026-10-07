"""M4 - Moteur de qualification de solution, a base de regles explicables.

Chaque type de solution porte un jeu de regles ponderees evaluees sur les reponses de
qualification de l'opportunite. Le score d'un type est le rapport entre le poids des
regles satisfaites et le poids total de ses regles. Une regle marquee bloquante et non
satisfaite disqualifie le type : il reste visible, mais son score est divise par quatre.

Le moteur ne renvoie jamais un simple verdict. Il expose les regles declenchees, les
alternatives ecartees avec leur score, et les garde-fous a mettre en place. C'est cette
tracabilite qui rend la recommandation opposable en comite.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from app.models.base import AIType


@dataclass
class Rule:
    code: str
    label: str
    weight: float
    predicate: Callable[[dict[str, Any]], bool]
    blocking: bool = False  # si non satisfaite, le type est disqualifie


@dataclass
class TypeEvaluation:
    ai_type: str
    label: str
    score: float
    fired: list[dict] = field(default_factory=list)
    missed: list[dict] = field(default_factory=list)
    disqualified_by: str | None = None


def _g(facts: dict[str, Any], key: str, default: Any = False) -> Any:
    value = facts.get(key, default)
    return default if value is None else value


def _volume(facts: dict[str, Any]) -> int:
    try:
        return int(_g(facts, "volume_per_month", 0) or 0)
    except (TypeError, ValueError):
        return 0


# --------------------------------------------------------------------------------------
# Base de regles
# --------------------------------------------------------------------------------------

RULES: dict[str, list[Rule]] = {
    AIType.CLASSIC: [
        Rule("CLS-1", "Données historiques disponibles", 3.0, lambda f: bool(_g(f, "data_available")), blocking=True),
        Rule("CLS-2", "Données structurées (ERP, MES, LIMS)", 3.0, lambda f: bool(_g(f, "data_structured")), blocking=True),
        Rule("CLS-3", "Vérité terrain disponible pour l'apprentissage", 2.5, lambda f: bool(_g(f, "ground_truth_available"))),
        Rule("CLS-4", "Qualité des données suffisante (≥ 3/5)", 2.0, lambda f: float(_g(f, "data_quality", 0)) >= 3.0),
        Rule("CLS-5", "Besoin de prédiction plutôt que de génération", 2.0, lambda f: not bool(_g(f, "content_generation"))),
        Rule("CLS-6", "Processus stable et répétable", 1.5, lambda f: not bool(_g(f, "process_unstable"))),
    ],
    AIType.COMPUTER_VISION: [
        Rule("CV-1", "Données image ou vidéo en entrée", 4.0, lambda f: bool(_g(f, "image_or_video")), blocking=True),
        Rule("CV-2", "Données disponibles et annotables", 3.0, lambda f: bool(_g(f, "data_available")), blocking=True),
        Rule("CV-3", "Vérité terrain (images annotées) disponible", 2.5, lambda f: bool(_g(f, "ground_truth_available"))),
        Rule("CV-4", "Tâche répétitive à fort volume", 2.0, lambda f: bool(_g(f, "repetitive_task"))),
        Rule("CV-5", "Volume mensuel significatif (≥ 1 000)", 1.5, lambda f: _volume(f) >= 1000),
    ],
    AIType.NLP: [
        Rule("NLP-1", "Données textuelles non structurées", 4.0, lambda f: bool(_g(f, "unstructured_text")), blocking=True),
        Rule("NLP-2", "Extraction ou classification plutôt que rédaction", 3.0, lambda f: not bool(_g(f, "content_generation"))),
        Rule("NLP-3", "Corpus disponible", 2.5, lambda f: bool(_g(f, "data_available"))),
        Rule("NLP-4", "Vérité terrain (corpus annoté) disponible", 2.0, lambda f: bool(_g(f, "ground_truth_available"))),
        Rule("NLP-5", "Volume de documents significatif (≥ 200)", 1.5, lambda f: _volume(f) >= 200),
    ],
    AIType.GENERATIVE: [
        Rule("GEN-1", "Besoin de production de contenu (rédaction, synthèse)", 4.0, lambda f: bool(_g(f, "content_generation")), blocking=True),
        Rule("GEN-2", "Matière textuelle non structurée à exploiter", 3.0, lambda f: bool(_g(f, "unstructured_text"))),
        Rule("GEN-3", "Validation humaine prévue (human in the loop)", 2.5, lambda f: bool(_g(f, "human_in_the_loop"))),
        Rule("GEN-4", "Pas d'autonomie multi-étapes requise", 2.0, lambda f: not bool(_g(f, "multi_step_autonomy"))),
        Rule("GEN-5", "Base documentaire accessible pour l'ancrage (RAG)", 1.5, lambda f: bool(_g(f, "data_available"))),
    ],
    AIType.AGENTIC: [
        Rule("AGT-1", "Enchaînement multi-étapes avec décisions intermédiaires", 4.0, lambda f: bool(_g(f, "multi_step_autonomy")), blocking=True),
        Rule("AGT-2", "Accès aux outils et applications nécessaire", 3.0, lambda f: bool(_g(f, "data_available"))),
        Rule("AGT-3", "Composante générative dans la chaîne", 2.5, lambda f: bool(_g(f, "content_generation")) or bool(_g(f, "unstructured_text"))),
        Rule("AGT-4", "Supervision humaine sur les actions sensibles", 2.0, lambda f: bool(_g(f, "human_in_the_loop"))),
        Rule("AGT-5", "Processus suffisamment stable pour être automatisé", 1.5, lambda f: not bool(_g(f, "process_unstable"))),
    ],
    AIType.BI: [
        Rule("BI-1", "Besoin de restitution et de pilotage", 4.0, lambda f: bool(_g(f, "reporting_need")), blocking=True),
        Rule("BI-2", "Données structurées disponibles", 3.0, lambda f: bool(_g(f, "data_structured"))),
        Rule("BI-3", "Pas de prédiction requise (pas de vérité terrain)", 2.5, lambda f: not bool(_g(f, "ground_truth_available"))),
        Rule("BI-4", "Pas de génération de contenu", 2.0, lambda f: not bool(_g(f, "content_generation"))),
    ],
    AIType.RPA: [
        Rule("RPA-1", "Tâche répétitive à forte volumétrie", 3.5, lambda f: bool(_g(f, "repetitive_task")), blocking=True),
        Rule("RPA-2", "Règles déterministes explicites", 3.5, lambda f: bool(_g(f, "rule_based")), blocking=True),
        Rule("RPA-3", "Processus stable, peu d'exceptions", 2.5, lambda f: not bool(_g(f, "process_unstable"))),
        Rule("RPA-4", "Pas d'apprentissage nécessaire", 2.0, lambda f: not bool(_g(f, "ground_truth_available"))),
        Rule("RPA-5", "Données structurées manipulées", 1.5, lambda f: bool(_g(f, "data_structured"))),
    ],
    AIType.PROCESS: [
        Rule("PRC-1", "Processus instable ou non formalisé", 4.0, lambda f: bool(_g(f, "process_unstable")), blocking=True),
        Rule("PRC-2", "Données indisponibles ou de mauvaise qualité", 3.0, lambda f: not bool(_g(f, "data_available")) or float(_g(f, "data_quality", 0)) < 2.0),
        Rule("PRC-3", "Pas de vérité terrain exploitable", 2.0, lambda f: not bool(_g(f, "ground_truth_available"))),
        Rule("PRC-4", "Volume trop faible pour rentabiliser un modèle (< 100)", 1.5, lambda f: _volume(f) < 100),
    ],
}

SOLUTION_PATTERNS: dict[str, str] = {
    AIType.CLASSIC: "Modèle supervisé ou série temporelle sur données structurées",
    AIType.COMPUTER_VISION: "Détection ou classification d'images en ligne de production",
    AIType.NLP: "Extraction et classification de documents textuels",
    AIType.GENERATIVE: "Assistant LLM ancré sur base documentaire (RAG), sortie validée",
    AIType.AGENTIC: "Agent orchestrant plusieurs outils, avec points de contrôle humains",
    AIType.BI: "Tableau de bord et alerting sur entrepôt de données",
    AIType.RPA: "Robot logiciel déterministe sur enchaînement d'écrans et de fichiers",
    AIType.PROCESS: "Refonte et standardisation du processus avant toute automatisation",
}

GUARDRAILS: dict[str, list[str]] = {
    AIType.CLASSIC: [
        "Explicabilité du modèle exigée pour la validation métier",
        "Suivi de la dérive des données et réentraînement planifié",
    ],
    AIType.COMPUTER_VISION: [
        "Qualification du poste d'acquisition (éclairage, cadrage)",
        "Plan de validation sur échantillons de référence",
    ],
    AIType.NLP: [
        "Mesure de la précision et du rappel par type de document",
        "Revue humaine des cas à faible confiance",
    ],
    AIType.GENERATIVE: [
        "Ancrage documentaire obligatoire, citation des sources",
        "Revue humaine systématique avant usage réglementaire",
        "Journalisation des requêtes et des réponses",
    ],
    AIType.AGENTIC: [
        "Périmètre d'actions restreint et réversible",
        "Point de contrôle humain avant toute action engageante",
        "Journal d'audit complet des étapes de l'agent",
    ],
    AIType.BI: ["Définition partagée des indicateurs et de leur source"],
    AIType.RPA: ["Gestion documentée des exceptions et des reprises"],
    AIType.PROCESS: ["Cartographier le processus cible avant de relancer la qualification"],
}

GXP_GUARDRAILS = [
    "Périmètre GxP : validation informatique (CSV) et qualification requises",
    "Traçabilité ALCOA+ des données et des décisions",
    "Revue humaine obligatoire, pas de décision automatique non supervisée",
]


def facts_from_opportunity(opportunity) -> dict[str, Any]:
    """Extrait les faits de qualification depuis l'opportunite (et son questionnaire)."""
    answers = opportunity.answers if isinstance(opportunity.answers, dict) else {}
    facts = {
        "data_available": opportunity.data_available,
        "data_structured": opportunity.data_structured,
        "data_quality": opportunity.data_quality,
        "ground_truth_available": opportunity.ground_truth_available,
        "unstructured_text": opportunity.unstructured_text,
        "image_or_video": opportunity.image_or_video,
        "content_generation": opportunity.content_generation,
        "multi_step_autonomy": opportunity.multi_step_autonomy,
        "rule_based": opportunity.rule_based,
        "repetitive_task": opportunity.repetitive_task,
        "reporting_need": opportunity.reporting_need,
        "process_unstable": opportunity.process_unstable,
        "regulated_gxp": opportunity.regulated_gxp,
        "human_in_the_loop": opportunity.human_in_the_loop,
        "volume_per_month": opportunity.volume_per_month,
    }
    # Les reponses libres du questionnaire peuvent surcharger un fait.
    for key in list(facts.keys()):
        if key in answers:
            facts[key] = answers[key]
    return facts


def evaluate_type(ai_type: str, facts: dict[str, Any]) -> TypeEvaluation:
    rules = RULES[ai_type]
    total_weight = sum(r.weight for r in rules)
    fired_weight = 0.0
    fired: list[dict] = []
    missed: list[dict] = []
    disqualified_by: str | None = None

    for rule in rules:
        try:
            satisfied = bool(rule.predicate(facts))
        except Exception:
            satisfied = False
        entry = {
            "code": rule.code,
            "label": rule.label,
            "weight": rule.weight,
            "satisfied": satisfied,
            "blocking": rule.blocking,
        }
        if satisfied:
            fired_weight += rule.weight
            fired.append(entry)
        else:
            missed.append(entry)
            if rule.blocking and disqualified_by is None:
                disqualified_by = rule.label

    score = (fired_weight / total_weight) if total_weight else 0.0
    if disqualified_by:
        score *= 0.25  # un type disqualifie reste visible mais fortement penalise

    return TypeEvaluation(
        ai_type=ai_type,
        label=AIType.LABELS[ai_type],
        score=round(score, 4),
        fired=fired,
        missed=missed,
        disqualified_by=disqualified_by,
    )


def qualify(opportunity) -> dict[str, Any]:
    """Qualifie une opportunite et renvoie la recommandation complete et explicable."""
    facts = facts_from_opportunity(opportunity)
    evaluations = [evaluate_type(t, facts) for t in AIType.ALL]
    evaluations.sort(key=lambda e: (-e.score, e.ai_type))

    best = evaluations[0]
    runners = evaluations[1:4]

    rationale_parts = [f"Type retenu : {best.label}."]
    if best.fired:
        rationale_parts.append(
            "Règles satisfaites : " + ", ".join(r["label"] for r in best.fired) + "."
        )
    else:
        rationale_parts.append("Aucune règle déterminante n'est satisfaite.")
    if best.missed:
        rationale_parts.append(
            "Points à sécuriser : " + ", ".join(r["label"] for r in best.missed) + "."
        )
    if best.disqualified_by:
        rationale_parts.append(
            f"Attention : une condition bloquante n'est pas remplie ({best.disqualified_by}). "
            "La recommandation doit être réexaminée après remédiation."
        )

    guardrails = list(GUARDRAILS.get(best.ai_type, []))
    if facts.get("regulated_gxp"):
        guardrails = GXP_GUARDRAILS + guardrails

    alternatives = [
        {
            "ai_type": e.ai_type,
            "label": e.label,
            "score": round(e.score * 100, 1),
            "reason": e.disqualified_by
            or (
                "Moins de règles satisfaites que le type retenu"
                if e.fired
                else "Aucune règle satisfaite"
            ),
        }
        for e in runners
    ]

    return {
        "ai_type": best.ai_type,
        "ai_type_label": best.label,
        "solution_pattern": SOLUTION_PATTERNS.get(best.ai_type),
        "confidence": round(best.score, 3),
        "rationale": " ".join(rationale_parts),
        "fired_rules": best.fired + best.missed,
        "alternatives": alternatives,
        "guardrails": guardrails,
        "facts": facts,
    }
