"""M3 - Questionnaire de recueil d'opportunite : tronc commun + volet departement.

Le tronc commun alimente directement les faits de qualification du moteur M4 : chaque
question porte le nom du champ qu'elle renseigne. Le volet specifique depend de la
famille metier du departement (production, qualite, R&D, supply chain, commercial,
affaires reglementaires, support) et enrichit le dictionnaire `answers`.
"""
from __future__ import annotations

from typing import Any

COMMON_SECTIONS: list[dict[str, Any]] = [
    {
        "code": "contexte",
        "title": "Contexte et besoin",
        "questions": [
            {"field": "title", "label": "Intitulé de l'opportunité", "type": "text", "required": True},
            {"field": "summary", "label": "Résumé en une phrase", "type": "text"},
            {"field": "as_is_context", "label": "Comment le processus fonctionne-t-il aujourd'hui ?", "type": "textarea", "required": True},
            {"field": "pain_points", "label": "Quels sont les points de douleur constatés ?", "type": "textarea"},
            {"field": "desired_outcome", "label": "Quel résultat est attendu ?", "type": "textarea"},
            {"field": "volume_per_month", "label": "Volume traité par mois", "type": "number", "unit": "occurrences"},
        ],
    },
    {
        "code": "donnees",
        "title": "Données disponibles",
        "questions": [
            {"field": "data_available", "label": "Des données historiques existent-elles ?", "type": "boolean"},
            {"field": "data_structured", "label": "Ces données sont-elles structurées (ERP, MES, LIMS) ?", "type": "boolean"},
            {"field": "data_quality", "label": "Qualité estimée des données", "type": "scale", "min": 0, "max": 5},
            {"field": "ground_truth_available", "label": "Dispose-t-on d'une vérité terrain exploitable ?", "type": "boolean"},
            {"field": "unstructured_text", "label": "Le besoin porte-t-il sur du texte non structuré ?", "type": "boolean"},
            {"field": "image_or_video", "label": "Le besoin porte-t-il sur des images ou des vidéos ?", "type": "boolean"},
        ],
    },
    {
        "code": "nature",
        "title": "Nature de la tâche",
        "questions": [
            {"field": "content_generation", "label": "Faut-il produire du contenu (rédaction, synthèse) ?", "type": "boolean"},
            {"field": "multi_step_autonomy", "label": "Faut-il enchaîner plusieurs étapes de façon autonome ?", "type": "boolean"},
            {"field": "rule_based", "label": "La tâche suit-elle des règles déterministes explicites ?", "type": "boolean"},
            {"field": "repetitive_task", "label": "La tâche est-elle répétitive et à fort volume ?", "type": "boolean"},
            {"field": "reporting_need", "label": "S'agit-il d'un besoin de restitution et de pilotage ?", "type": "boolean"},
            {"field": "process_unstable", "label": "Le processus est-il instable ou non formalisé ?", "type": "boolean"},
        ],
    },
    {
        "code": "conformite",
        "title": "Conformité et gouvernance",
        "questions": [
            {"field": "regulated_gxp", "label": "Le périmètre est-il GxP, soumis à inspection ?", "type": "boolean"},
            {"field": "human_in_the_loop", "label": "Une validation humaine est-elle prévue ?", "type": "boolean"},
            {"field": "sponsor", "label": "Sponsor", "type": "text"},
            {"field": "business_owner", "label": "Owner métier", "type": "text"},
            {"field": "technical_owner", "label": "Owner technique", "type": "text"},
        ],
    },
    {
        "code": "valeur",
        "title": "Valeur attendue et risque",
        "questions": [
            {"field": "impact_business", "label": "Impact métier estimé", "type": "scale", "min": 0, "max": 100},
            {"field": "impact_financial", "label": "Impact financier estimé", "type": "scale", "min": 0, "max": 100},
            {"field": "feasibility", "label": "Faisabilité technique estimée", "type": "scale", "min": 0, "max": 100},
            {"field": "alignment", "label": "Alignement stratégique", "type": "scale", "min": 0, "max": 100},
            {"field": "expected_benefit_eur", "label": "Bénéfice annuel attendu", "type": "number", "unit": "EUR"},
            {"field": "estimated_cost_eur", "label": "Coût estimé", "type": "number", "unit": "EUR"},
            {"field": "risk_probability", "label": "Probabilité du risque principal", "type": "scale", "min": 1, "max": 5},
            {"field": "risk_impact", "label": "Impact du risque principal", "type": "scale", "min": 1, "max": 5},
        ],
    },
]

DEPARTMENT_SECTIONS: dict[str, dict[str, Any]] = {
    "production": {
        "title": "Volet Production et industrialisation",
        "questions": [
            {"field": "equipment_line", "label": "Ligne ou équipement concerné", "type": "text"},
            {"field": "downtime_hours_month", "label": "Heures d'arrêt non planifié par mois", "type": "number"},
            {"field": "sensor_data", "label": "Des données capteurs sont-elles historisées ?", "type": "boolean"},
            {"field": "batch_record_digital", "label": "Le dossier de lot est-il électronique ?", "type": "boolean"},
        ],
    },
    "qualite": {
        "title": "Volet Qualité",
        "questions": [
            {"field": "deviation_count_year", "label": "Nombre de déviations par an", "type": "number"},
            {"field": "capa_backlog", "label": "Encours CAPA", "type": "number"},
            {"field": "visual_inspection", "label": "Y a-t-il un contrôle visuel manuel ?", "type": "boolean"},
            {"field": "qms_system", "label": "Système QMS utilisé", "type": "text"},
        ],
    },
    "r_and_d": {
        "title": "Volet R&D",
        "questions": [
            {"field": "literature_volume", "label": "Volume de documents scientifiques à revoir", "type": "number"},
            {"field": "elnotebook", "label": "Cahier de laboratoire électronique en place ?", "type": "boolean"},
            {"field": "ip_sensitivity", "label": "Sensibilité propriété intellectuelle", "type": "scale", "min": 0, "max": 5},
        ],
    },
    "supply_chain": {
        "title": "Volet Supply Chain",
        "questions": [
            {"field": "sku_count", "label": "Nombre de références gérées", "type": "number"},
            {"field": "stockout_rate", "label": "Taux de rupture constaté", "type": "number", "unit": "%"},
            {"field": "forecast_horizon_months", "label": "Horizon de prévision", "type": "number", "unit": "mois"},
            {"field": "cold_chain", "label": "Chaîne du froid concernée ?", "type": "boolean"},
        ],
    },
    "commercial": {
        "title": "Volet Commercial",
        "questions": [
            {"field": "markets_count", "label": "Nombre de marchés couverts", "type": "number"},
            {"field": "crm_system", "label": "CRM utilisé", "type": "text"},
            {"field": "forecast_error_percent", "label": "Erreur de prévision actuelle", "type": "number", "unit": "%"},
        ],
    },
    "affaires_reglementaires": {
        "title": "Volet Affaires réglementaires",
        "questions": [
            {"field": "dossiers_per_year", "label": "Nombre de dossiers déposés par an", "type": "number"},
            {"field": "authorities", "label": "Autorités concernées", "type": "text"},
            {"field": "document_reuse_rate", "label": "Taux de réutilisation documentaire", "type": "number", "unit": "%"},
            {"field": "submission_format", "label": "Format de soumission (eCTD…)", "type": "text"},
        ],
    },
    "support": {
        "title": "Volet Fonctions support",
        "questions": [
            {"field": "documents_per_month", "label": "Documents traités par mois", "type": "number"},
            {"field": "fte_involved", "label": "ETP mobilisés", "type": "number"},
            {"field": "erp_module", "label": "Module ERP concerné", "type": "text"},
        ],
    },
}


def questionnaire_for(family: str | None) -> dict[str, Any]:
    """Renvoie le questionnaire applicable : tronc commun + volet departement eventuel."""
    sections = [dict(s) for s in COMMON_SECTIONS]
    specific = DEPARTMENT_SECTIONS.get((family or "").lower()) if family else None
    return {
        "family": family,
        "common": sections,
        "specific": (
            {"code": f"dept_{family}", "title": specific["title"], "questions": specific["questions"]}
            if specific
            else None
        ),
        "available_families": sorted(DEPARTMENT_SECTIONS.keys()),
    }
