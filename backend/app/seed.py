"""Jeu de données de demonstration : laboratoire pharmaceutique Medicacom.

Usage :  python -m app.seed  [--reset]

Le seed est idempotent : relance sans option, il ne recree rien si l'organisation
existe deja. Avec --reset, il vide les tables métier de cette organisation avant
de les reconstruire.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.rbac import PERMISSIONS as PERMISSION_CATALOG
from app.core.rbac import ROLE_TEMPLATES, ScopeLevel
from app.core.security import hash_password
from app.models import (
    KPI,
    AIRecommendation,
    Application,
    Approval,
    Assessment,
    AssessmentResponse,
    AuditLog,
    Benefit,
    Cost,
    DataSource,
    Department,
    Dependency,
    Document,
    Issue,
    Measurement,
    Milestone,
    Mitigation,
    Notification,
    Opportunity,
    Organization,
    Permission,
    Process,
    Project,
    Risk,
    Role,
    Site,
    Stage,
    Task,
    User,
    Version,
)
from app.models.base import AIType, Phase, RiskLevel
from app.services import recommendation, scoring

ORG_CODE = "MEDICACOM"
TODAY = date(2026, 9, 24)


# ======================================================================================
# Referentiels
# ======================================================================================

# Le catalogue des permissions et les modeles de roles vivent dans app/core/rbac.py :
# le seed, les routers et les tests partagent ainsi la meme source de verite.

SITES = [
    ("Site de Tunis", "TUN", "Tunis", "Tunisie", "Production"),
    ("Site de Lyon", "LYO", "Lyon", "France", "R&D"),
    ("Plateforme de Casablanca", "CAS", "Casablanca", "Maroc", "Distribution"),
    ("Siège de Paris", "PAR", "Paris", "France", "Siege"),
]

DEPARTMENTS = [
    ("Commercial", "COM", "commercial", "L. Trabelsi", "TUN"),
    ("Supply Chain", "SUP", "supply_chain", "N. Ben Salah", "CAS"),
    ("Production", "PRD", "production", "H. Gharbi", "TUN"),
    ("Qualité", "QUA", "qualite", "S. Meddeb", "TUN"),
    ("R&D", "RND", "r_and_d", "A. Rousseau", "LYO"),
    ("Affaires réglementaires", "REG", "affaires_reglementaires", "C. Lambert", "PAR"),
    ("Finance & Achats", "FIN", "support", "M. Dupuis", "PAR"),
    ("IT & Data Office", "ITD", "support", "K. Zouari", "TUN"),
]

# Un compte par role fonctionnel, rattache a un departement et a un site coherents.
# (email, nom, fonction, departement principal, departements couverts, sites, roles)
DEMO_PASSWORD = "medicacom2026"

USERS = [
    ("marwen.b@medicacom.com", "Marwen B.", "Directeur IA", "ITD", ["ITD"], ["TUN"], ["direction"]),
    ("admin.entreprise@medicacom.com", "S. Bouazizi", "Responsable administration SI", "ITD",
     ["ITD"], ["TUN", "LYO", "CAS", "PAR"], ["admin_entreprise"]),
    ("l.trabelsi@medicacom.com", "L. Trabelsi", "Directrice commerciale", "COM",
     ["COM"], ["TUN"], ["responsable_departement"]),
    ("h.gharbi@medicacom.com", "H. Gharbi", "Responsable production", "PRD",
     ["PRD"], ["TUN"], ["responsable_departement"]),
    ("c.lambert@medicacom.com", "C. Lambert", "Responsable affaires reglementaires", "REG",
     ["REG"], ["PAR"], ["responsable_departement"]),
    ("a.rousseau@medicacom.com", "A. Rousseau", "Chef de projet R&D", "RND",
     ["RND"], ["LYO"], ["contributeur_metier"]),
    ("k.zouari@medicacom.com", "K. Zouari", "Architecte d'entreprise", "ITD",
     ["ITD"], ["TUN"], ["dsi_architecte"]),
    ("n.hamdi@medicacom.com", "N. Hamdi", "Data engineer", "ITD",
     ["ITD"], ["TUN"], ["data_office"]),
    ("y.benali@medicacom.com", "Y. Ben Ali", "AI Lead", "ITD",
     ["ITD"], ["TUN"], ["ai_lead"]),
    ("m.dupuis@medicacom.com", "M. Dupuis", "Controleur de gestion", "FIN",
     ["FIN"], ["PAR"], ["finance"]),
    ("f.moreau@medicacom.com", "F. Moreau", "Cheffe de projet PMO", "ITD",
     ["ITD"], ["TUN", "PAR"], ["pmo"]),
    ("audit@medicacom.com", "Cabinet Vermeil", "Auditeur externe", "ITD",
     ["ITD"], ["TUN"], ["auditeur"]),
]

# --------------------------------------------------------------------------------------
# Diagnostic AS-IS (campagne 2026, site de Tunis)
# Les poids et confiances sont calibres sur le constat terrain : les dimensions mal
# etayees portent une confiance plus faible et pesent donc moins dans le score global.
# --------------------------------------------------------------------------------------
ASSESSMENT_RESPONSES = [
    # axe, code, libelle, note, poids, confiance, critique, preuve
    ("technique", "DATA_AVAIL", "Données disponibles", 4, 1.0, 1.0, True,
     "Historique ERP sur 5 ans, extraction hebdomadaire opérationnelle."),
    ("technique", "DATA_QUALITY", "Qualité des données", 3, 1.2, 1.0, True,
     "Référentiel produit fiable, historique promotions incomplet sur 2 marchés."),
    ("technique", "ETL", "Intégration & ETL", 3, 1.0, 1.0, True,
     "Flux planifiés sous Talend, reprises manuelles en cas d'échec."),
    ("technique", "DWH", "DWH / Lakehouse", 3, 0.8, 1.0, True,
     "Entrepôt PostgreSQL centralisé, pas de couche analytique dédiée."),
    ("technique", "DATA_GOV", "Gouvernance data", 2, 1.8, 0.62, True,
     "Pas de data owner nommé ni de catalogue ; constat déclaratif à confirmer."),
    ("technique", "AI_INFRA", "Infrastructure IA", 2, 1.8, 0.62, True,
     "Aucun environnement d'entraînement ni de mise en service industrialisée."),
    ("technique", "SECURITY", "Sécurité & conformité", 4, 1.0, 1.0, True,
     "Politique d'accès validée, chiffrement au repos, audit annuel."),
    ("metier", "NEED_CLARITY", "Clarté du besoin", 4, 1.0, 1.0, False,
     "Besoins formalisés lors des ateliers métier de janvier 2026."),
    ("metier", "PROCESS_MATURITY", "Maturité du processus", 3, 1.2, 1.0, False,
     "Processus décrits, variantes par marché non harmonisées."),
    ("metier", "SPONSORSHIP", "Sponsoring & ownership", 4, 1.0, 1.0, False,
     "Sponsor identifié au comité de direction pour chaque vague."),
    ("metier", "KPI_BASELINE", "KPI & baseline", 3, 1.2, 1.0, False,
     "Baselines disponibles sur les processus clés, partielles ailleurs."),
    ("metier", "VALUE_PNL", "Valeur & P&L", 3, 1.2, 1.0, False,
     "Gains chiffrés avec le contrôle de gestion, sans rattachement P&L formel."),
    ("metier", "ADOPTION", "Adoption & changement", 2, 2.0, 0.62, False,
     "Pas de plan de conduite du changement ni de réseau de relais terrain."),
    ("metier", "REG_RISK", "Risque réglementaire", 4, 1.0, 1.0, False,
     "Cartographie GxP à jour, procédure de validation informatique en place."),
    # Deux dimensions restent a instruire : une confiance nulle les exclut du score
    # tant qu'elles ne sont pas evaluees, et fait apparaitre la campagne comme
    # incomplete. Ce sont elles que l'action « Poursuivre le diagnostic » propose
    # de renseigner.
    ("technique", "MLOPS", "MLOps & mise en service", 0, 1.4, 0.0, True, None),
    ("metier", "SKILLS", "Compétences & formation", 0, 1.2, 0.0, False, None),
]

PROCESSES = [
    ("PRC-FCT", "Prévision des ventes et S&OP", "COM", 2.0, 12, 20.0, False),
    ("PRC-STK", "Pilotage des stocks et réapprovisionnement", "SUP", 3.0, 320, 14.0, False),
    ("PRC-MNT", "Maintenance des équipements de production", "PRD", 2.0, 180, 22.0, True),
    ("PRC-LIB", "Libération des lots", "QUA", 2.0, 240, 30.0, True),
    ("PRC-DEV", "Gestion des déviations et CAPA", "QUA", 3.0, 45, 18.0, True),
    ("PRC-REG", "Constitution des dossiers d'enregistrement", "REG", 3.0, 9, 46.0, True),
    ("PRC-LIT", "Veille et revue de littérature scientifique", "RND", 2.0, 60, 25.0, False),
    ("PRC-FAC", "Traitement des factures fournisseurs", "FIN", 3.0, 1400, 16.0, False),
    ("PRC-INS", "Contrôle visuel en ligne de conditionnement", "QUA", 3.0, 45000, 34.0, True),
]

APPLICATIONS = [
    ("SAP S/4HANA", "SAP", "ERP", True, "critique", True),
    ("LIMS LabWare", "LabWare", "LIMS", True, "critique", True),
    ("MES Werum PAS-X", "Korber", "MES", True, "critique", True),
    ("QMS TrackWise", "Sparta", "QMS", True, "critique", True),
    ("Veeva Vault RIM", "Veeva", "RIM", True, "critique", True),
    ("Salesforce Health Cloud", "Salesforce", "CRM", True, "important", False),
    ("GED SharePoint", "Microsoft", "DMS", True, "important", False),
    ("Historien PI System", "AVEVA", "Historien", True, "important", False),
]

DATASOURCES = [
    ("Historique des ventes multi-marchés", "SAP S/4HANA", "structuree", "table SQL", 60, "1,2 M lignes", 4.0, True, False, "Data Office"),
    ("Référentiel produit et nomenclatures", "SAP S/4HANA", "structuree", "table SQL", 96, "18 k références", 4.0, False, False, "Supply Chain"),
    ("Historique des promotions commerciales", "Salesforce Health Cloud", "structuree", "export CSV", 24, "9 k campagnes", 2.0, False, False, "Commercial"),
    ("Series temporelles capteurs ligne 3", "Historien PI System", "serie_temporelle", "flux OPC-UA", 36, "40 M points", 4.0, True, False, "Production"),
    ("Dossiers de déviation qualité", "QMS TrackWise", "texte", "texte libre", 72, "3 200 dossiers", 3.0, True, False, "Qualite"),
    ("Certificats d'analyse fournisseurs", "GED SharePoint", "texte", "PDF scanné", 48, "14 k documents", 2.0, False, False, "Qualite"),
    ("Images de contrôle blister", "MES Werum PAS-X", "image", "PNG 2048x2048", 18, "420 k images", 3.0, True, False, "Qualite"),
    ("Dossiers d'enregistrement eCTD", "Veeva Vault RIM", "texte", "eCTD / PDF", 120, "2 800 documents", 4.0, False, False, "Affaires réglementaires"),
    ("Corpus de littérature scientifique", "GED SharePoint", "texte", "PDF", 120, "36 k articles", 3.0, False, False, "R&D"),
    ("Factures fournisseurs dématérialisées", "SAP S/4HANA", "structuree", "EDI / PDF", 60, "17 k factures/an", 4.0, False, False, "Finance & Achats"),
    ("Relevés de consommation des utilités", "Historien PI System", "serie_temporelle", "flux OPC-UA", 30, "8 M points", 3.0, False, False, "Production"),
]


# --------------------------------------------------------------------------------------
# Les 18 opportunites du portefeuille
# facts : faits de qualification lus par le moteur de règles M4
# --------------------------------------------------------------------------------------
def _facts(**kwargs) -> dict:
    base = {
        "data_available": False,
        "data_structured": False,
        "data_quality": 0.0,
        "ground_truth_available": False,
        "unstructured_text": False,
        "image_or_video": False,
        "content_generation": False,
        "multi_step_autonomy": False,
        "rule_based": False,
        "repetitive_task": False,
        "reporting_need": False,
        "process_unstable": False,
        "regulated_gxp": False,
        "human_in_the_loop": True,
        "volume_per_month": None,
    }
    base.update(kwargs)
    return base


CLASSIC = dict(data_available=True, data_structured=True, data_quality=4.0, ground_truth_available=True)
GENERATIVE = dict(data_available=True, unstructured_text=True, content_generation=True, human_in_the_loop=True)
AGENTIC = dict(data_available=True, unstructured_text=True, content_generation=True, multi_step_autonomy=True)
VISION = dict(data_available=True, image_or_video=True, ground_truth_available=True, repetitive_task=True)
NLP = dict(data_available=True, unstructured_text=True, ground_truth_available=True)
RPA = dict(data_available=True, data_structured=True, data_quality=4.0, rule_based=True, repetitive_task=True)
BI = dict(data_available=True, data_structured=True, data_quality=3.0, reporting_need=True)
PROCESS = dict(process_unstable=True, data_quality=1.0)

OPPORTUNITIES = [
    # (code, titre, dept, site, process, phase, statut, scores(im,if,fe,al,rd,sy), risque(p,i), bénéfice, coût, facts, textes)
    dict(
        code="OPP-2026-014",
        title="Prévision des ventes multi-marchés",
        dept="COM", site="TUN", process="PRC-FCT",
        phase=Phase.PILOT, status="approuve",
        scores=(92, 88, 84, 90, 78, 85), risk=(1, 1),
        benefit=175230, cost=185100,
        facts=_facts(**CLASSIC, volume_per_month=1200),
        as_is=(
            "Les prévisions de vente sont produites manuellement sous Excel par marché, avec un "
            "historique fragmenté entre l'ERP et les fichiers commerciaux. Le cycle mensuel mobilise "
            "4 personnes, l'erreur moyenne atteint 22 % et génère surstock et ruptures ponctuelles "
            "sur les références sensibles."
        ),
        pain="Cycle mensuel de 5 jours, erreur de prévision de 22 %, arbitrages tardifs en S&OP.",
        outcome="Ramener l'erreur de prévision à 10 % et le cycle a 1,5 jour par mois.",
        sponsor="Dir. Commerciale", owner="L. Trabelsi", tech="Data Office",
        summary="Modèle de série temporelle multi-variable pour fiabiliser le S&OP sur tous les marchés.",
    ),
    dict(
        code="OPP-2026-002",
        title="Assistant documentaire réglementaire",
        dept="REG", site="PAR", process="PRC-REG",
        phase=Phase.FRAMING, status="business_case",
        scores=(95, 87, 83, 94, 79, 85), risk=(3, 4),
        benefit=225000, cost=240000,
        facts=_facts(**GENERATIVE, regulated_gxp=True, volume_per_month=300),
        as_is=(
            "La rédaction des modules du dossier d'enregistrement repose sur la reprise manuelle de "
            "documents antérieurs dispersés entre Veeva Vault et la GED. Chaque dossier mobilise "
            "3 rédacteurs pendant plusieurs semaines."
        ),
        pain="Réutilisation documentaire faible, délais de dépôt contraints par la capacité de rédaction.",
        outcome="Réduire de moitié le temps de rédaction des sections récurrentes, sources citées.",
        sponsor="Dir. Affaires réglementaires", owner="C. Lambert", tech="Data Office",
        summary="Assistant LLM ancré sur le référentiel documentaire, avec citation systématique des sources.",
    ),
    dict(
        code="OPP-2026-003",
        title="Maintenance prédictive - ligne 3",
        dept="PRD", site="TUN", process="PRC-MNT",
        phase=Phase.POC, status="en_poc",
        scores=(85, 83, 79, 77, 71, 69), risk=(3, 3),
        benefit=180000, cost=196000,
        facts=_facts(**CLASSIC, regulated_gxp=True, volume_per_month=4000),
        as_is=(
            "La maintenance de la ligne 3 est preventive et calendaire. Les arrêts non planifiés "
            "représentent 46 heures par mois, sans exploitation des données capteurs historisées "
            "dans le PI System."
        ),
        pain="46 h d'arrêt non planifié par mois, pieces changees trop tot ou trop tard.",
        outcome="Anticiper les dérives 72 h a l'avance et réduire les arrêts de 35 %.",
        sponsor="Dir. Industrielle", owner="H. Gharbi", tech="Data Office",
        summary="Détection de dérive sur séries temporelles capteurs avec alerte à 72 heures.",
    ),
    dict(
        code="OPP-2026-004",
        title="Détection des ruptures de stock",
        dept="SUP", site="CAS", process="PRC-STK",
        phase=Phase.QUALIFICATION, status="evalue",
        scores=(78, 74, 74, 70, 66, 64), risk=(2, 3),
        benefit=144000, cost=152000,
        facts=_facts(**CLASSIC, volume_per_month=18000),
        as_is=(
            "Les ruptures sont constatées a posteriori dans les rapports hebdomadaires. Le taux de "
            "rupture s'établit a 4,2 % sur les références à rotation lente."
        ),
        pain="Détection tardive, arbitrages d'allocation manuels entre marchés.",
        outcome="Alerter 3 semaines avant la rupture et ramener le taux sous 2 %.",
        sponsor="Dir. Supply Chain", owner="N. Ben Salah", tech="Data Office",
        summary="Modèle de risque de rupture par référence et par marché, alimente par l'ERP.",
    ),
    dict(
        code="OPP-2026-005",
        title="Revue documentaire R&D assistée",
        dept="RND", site="LYO", process="PRC-LIT",
        phase=Phase.FRAMING, status="business_case",
        scores=(76, 64, 72, 74, 68, 66), risk=(2, 3),
        benefit=167000, cost=178000,
        facts=_facts(**GENERATIVE, volume_per_month=900),
        as_is=(
            "La veille scientifique est réalisée manuellement par les chefs de projet R&D sur un "
            "corpus de 36 000 articles, avec une couverture partielle et hétérogène."
        ),
        pain="25 jours-homme par mois consacrés a la lecture et a la synthèse.",
        outcome="Produire des synthetiques sourcées et diviser par trois le temps de revue.",
        sponsor="Dir. R&D", owner="A. Rousseau", tech="Data Office",
        summary="Synthèse assistée du corpus scientifique avec citation des passages sources.",
    ),
    dict(
        code="OPP-2026-006",
        title="Agent de constitution des dossiers réglementaires",
        dept="REG", site="PAR", process="PRC-REG",
        phase=Phase.QUALIFICATION, status="evalue",
        scores=(72, 66, 38, 74, 58, 64), risk=(4, 5),
        benefit=204000, cost=265000,
        facts=_facts(**AGENTIC, regulated_gxp=True, volume_per_month=120),
        as_is=(
            "La constitution d'un dossier eCTD enchaîne une quinzaine d'étapes réparties entre "
            "plusieurs systemes, chaque transition etant réalisée et tracée manuellement."
        ),
        pain="Enchainement multi-systemes, ressaisies, traçabilité coûteuse a produire.",
        outcome="Orchestrer la chaîne documentaire avec points de contrôle humains à chaque etape engageante.",
        sponsor="Dir. Affaires réglementaires", owner="C. Lambert", tech="Data Office",
        summary="Agent orchestrant la collecte, l'assemblage et le contrôle du dossier eCTD.",
    ),
    dict(
        code="OPP-2026-007",
        title="Contrôle visuel des défauts de blister",
        dept="QUA", site="TUN", process="PRC-INS",
        phase=Phase.POC, status="en_poc",
        scores=(35, 58, 42, 54, 60, 40), risk=(3, 4),
        benefit=103000, cost=142000,
        facts=_facts(**VISION, regulated_gxp=True, volume_per_month=45000),
        as_is=(
            "Le contrôle visuel des blisters est realise par échantillonnage manuel en fin de ligne. "
            "Le taux de détection dépend fortement de l'opérateur et du poste."
        ),
        pain="Détection hétérogène, réclamations clients sur des défauts d'aspect.",
        outcome="Contrôler 100 % des blisters avec un taux de détection stable.",
        sponsor="Dir. Qualité", owner="S. Meddeb", tech="Data Office",
        summary="Classification d'images en ligne pour detecter les défauts d'aspect des blisters.",
    ),
    dict(
        code="OPP-2026-008",
        title="Rapprochement automatique des factures fournisseurs",
        dept="FIN", site="PAR", process="PRC-FAC",
        phase=Phase.PRODUCTION, status="approuve",
        scores=(40, 72, 78, 52, 74, 46), risk=(1, 2),
        benefit=127000, cost=96000,
        facts=_facts(**RPA, volume_per_month=1400),
        as_is=(
            "Le rapprochement facture / commande / réception est realise manuellement pour "
            "17 000 factures par an, avec 3,5 ETP mobilises."
        ),
        pain="Volume eleve, délais de paiement dégradés, escomptes perdus.",
        outcome="Automatiser 80 % des rapprochements sans exception.",
        sponsor="Dir. Financiere", owner="M. Dupuis", tech="Data Office",
        summary="Robot déterministe de rapprochement à trois voies sur les flux ERP.",
    ),
    dict(
        code="OPP-2026-009",
        title="Classification des déviations qualité",
        dept="QUA", site="TUN", process="PRC-DEV",
        phase=Phase.PILOT, status="approuve",
        scores=(76, 66, 74, 76, 70, 68), risk=(2, 4),
        benefit=152000, cost=158000,
        facts=_facts(**NLP, regulated_gxp=True, volume_per_month=380),
        as_is=(
            "Les déviations sont saisies en texte libre dans TrackWise puis classées à la main, "
            "avec des écarts de catégorisation entre évaluateurs."
        ),
        pain="Classement hétérogène, analyse de tendance peu fiable, backlog CAPA.",
        outcome="Proposer une catégorie et une criticité, validées par l'évaluateur.",
        sponsor="Dir. Qualité", owner="S. Meddeb", tech="Data Office",
        summary="Classification assistée des déviations avec revue humaine des cas incertains.",
    ),
    dict(
        code="OPP-2026-010",
        title="Optimisation du plan de production",
        dept="PRD", site="TUN", process="PRC-MNT",
        phase=Phase.FRAMING, status="business_case",
        scores=(74, 72, 68, 70, 64, 72), risk=(3, 3),
        benefit=199000, cost=205000,
        facts=_facts(**CLASSIC, volume_per_month=600),
        as_is=(
            "L'ordonnancement est construit sous Excel a partir du carnet de commandes, sans "
            "arbitrage outillé entre changements de format et taux de service."
        ),
        pain="Changements de format trop frequents, taux d'occupation des lignes sous-optimal.",
        outcome="Augmenter le taux d'occupation des lignes de 8 points.",
        sponsor="Dir. Industrielle", owner="H. Gharbi", tech="Data Office",
        summary="Optimisation de l'ordonnancement sous contraintes de format et de péremption.",
    ),
    dict(
        code="OPP-2026-011",
        title="Tableau de bord pharmacovigilance",
        dept="REG", site="PAR", process="PRC-REG",
        phase=Phase.PRODUCTION, status="approuve",
        scores=(62, 54, 82, 72, 76, 58), risk=(1, 3),
        benefit=77000, cost=64000,
        facts=_facts(**BI, regulated_gxp=True, volume_per_month=800),
        as_is=(
            "Le suivi des cas de pharmacovigilance est reconstitué chaque mois par extraction "
            "manuelle, sans vision consolidée par produit et par marché."
        ),
        pain="Restitution mensuelle tardive, pas d'alerte sur les signaux émergents.",
        outcome="Disposer d'un suivi quotidien consolidé et d'alertes sur seuils.",
        sponsor="Dir. Affaires réglementaires", owner="C. Lambert", tech="Data Office",
        summary="Entrepôt et tableau de bord de suivi des cas, avec alerting sur seuils.",
    ),
    dict(
        code="OPP-2026-012",
        title="Prévision de la demande cold chain",
        dept="SUP", site="CAS", process="PRC-STK",
        phase=Phase.PILOT, status="approuve",
        scores=(72, 68, 72, 68, 64, 68), risk=(2, 3),
        benefit=176000, cost=172000,
        facts=_facts(**CLASSIC, volume_per_month=2600),
        as_is=(
            "La demande des produits thermosensibles est estimée par règles empiriques, ce qui "
            "provoque des surcapacités de transport réfrigéré."
        ),
        pain="Surcoût logistique du froid, destruction de lots en fin de péremption.",
        outcome="Réduire de 15 % le coût du transport réfrigéré.",
        sponsor="Dir. Supply Chain", owner="N. Ben Salah", tech="Data Office",
        summary="Prévision dédiée aux références thermosensibles, intégrée au plan de transport.",
    ),
    dict(
        code="OPP-2026-013",
        title="Extraction des données de certificats d'analyse",
        dept="QUA", site="TUN", process="PRC-LIB",
        phase=Phase.QUALIFICATION, status="evalue",
        scores=(66, 62, 70, 64, 62, 66), risk=(2, 4),
        benefit=116000, cost=124000,
        facts=_facts(**NLP, regulated_gxp=True, volume_per_month=1200),
        as_is=(
            "Les certificats d'analyse fournisseurs arrivent en PDF scanné et sont ressaisis dans "
            "le LIMS, poste par poste, avant libération."
        ),
        pain="Ressaisie de 14 000 documents par an, risque d'erreur de transcription.",
        outcome="Extraire automatiquement les résultats et les controler avant intégration LIMS.",
        sponsor="Dir. Qualité", owner="S. Meddeb", tech="Data Office",
        summary="Extraction structurée des résultats analytiques à partir des PDF fournisseurs.",
    ),
    dict(
        code="OPP-2026-015",
        title="Assistant de réponse aux appels d'offres hospitaliers",
        dept="COM", site="PAR", process="PRC-FCT",
        phase=Phase.QUALIFICATION, status="evalue",
        scores=(64, 58, 66, 62, 60, 56), risk=(2, 3),
        benefit=101000, cost=112000,
        facts=_facts(**GENERATIVE, volume_per_month=140),
        as_is=(
            "Les réponses aux appels d'offres hospitaliers sont rédigés à partir de réponses "
            "précédentes retrouvées au cas par cas dans la GED."
        ),
        pain="Delais courts, qualité de réponse dépendante du rédacteur.",
        outcome="Produire une premiere version sourcée en moins d'une journée.",
        sponsor="Dir. Commerciale", owner="L. Trabelsi", tech="Data Office",
        summary="Génération assistée des réponses a partir du référentiel de réponses validées.",
    ),
    dict(
        code="OPP-2026-016",
        title="Détection d'anomalies sur les paramètres de granulation",
        dept="PRD", site="TUN", process="PRC-MNT",
        phase=Phase.POC, status="en_poc",
        scores=(70, 68, 72, 66, 64, 60), risk=(3, 3),
        benefit=135000, cost=138000,
        facts=_facts(**CLASSIC, regulated_gxp=True, volume_per_month=3200),
        as_is=(
            "Les paramètres critiques de granulation sont suivis par cartes de contrôle "
            "manuelles, avec détection tardive des dérives multi-variables."
        ),
        pain="Lots non conformes detectes en fin de process, rebuts coûteux.",
        outcome="Détecter les dérives multi-variables en cours de lot.",
        sponsor="Dir. Industrielle", owner="H. Gharbi", tech="Data Office",
        summary="Détection d'anomalies multi-variables sur les paramètres critiques de procédé.",
    ),
    dict(
        code="OPP-2026-017",
        title="Standardisation du processus de libération des lots",
        dept="QUA", site="TUN", process="PRC-LIB",
        phase=Phase.QUALIFICATION, status="en_attente",
        scores=(58, 44, 36, 60, 40, 48), risk=(3, 4),
        benefit=69000, cost=88000,
        facts=_facts(**PROCESS, regulated_gxp=True, volume_per_month=60),
        as_is=(
            "La libération des lots suit des variantes différentes selon les ateliers, sans "
            "procédure unique ni données exploitables sur les temps de cycle."
        ),
        pain="Délai de libération variable de 3 à 9 jours selon l'atelier.",
        outcome="Harmoniser le processus avant d'envisager toute automatisation.",
        sponsor="Dir. Qualité", owner="S. Meddeb", tech="Excellence opérationnelle",
        summary="Refonte et standardisation du processus avant toute qualification de solution IA.",
    ),
    dict(
        code="OPP-2026-018",
        title="Synthèse automatique de la littérature scientifique",
        dept="RND", site="LYO", process="PRC-LIT",
        phase=Phase.FRAMING, status="business_case",
        scores=(72, 64, 74, 70, 68, 66), risk=(2, 3),
        benefit=127000, cost=132000,
        facts=_facts(**GENERATIVE, volume_per_month=420),
        as_is=(
            "Les revues bibliographiques périodiques sont produites manuellement, sans "
            "capitalisation d'une revue a l'autre."
        ),
        pain="Effort répété à chaque revue, couverture inégale des sources.",
        outcome="Générer une synthèse sourcée réutilisable à chaque cycle de revue.",
        sponsor="Dir. R&D", owner="A. Rousseau", tech="Data Office",
        summary="Synthèse periodique du corpus scientifique avec suivi des nouveautes.",
    ),
    dict(
        code="OPP-2026-019",
        title="Suivi énergétique des utilités",
        dept="PRD", site="TUN", process="PRC-MNT",
        phase=Phase.PRODUCTION, status="approuve",
        scores=(54, 60, 84, 58, 72, 50), risk=(1, 2),
        benefit=92000, cost=68000,
        facts=_facts(**BI, volume_per_month=2400),
        as_is=(
            "La consommation des utilités est relevée mensuellement sur facture, sans suivi par "
            "atelier ni détection des dérives."
        ),
        pain="Aucune visibilité temps réel, dérives detectees avec un mois de retard.",
        outcome="Suivre la consommation par atelier et alerter sur les dérives.",
        sponsor="Dir. Industrielle", owner="H. Gharbi", tech="Data Office",
        summary="Tableau de bord de consommation des utilités par atelier, avec alerting.",
    ),
]


# ======================================================================================
# Construction
# ======================================================================================

def _reset(db: Session, org: Organization) -> None:
    """Vide les tables métier de l'organisation avant reconstruction."""
    org_id = org.id
    for model in (
        Measurement, Benefit, Cost, Version, Approval, Document, Mitigation, Risk, Issue,
        Task, Milestone, Stage, Project, Dependency, AIRecommendation, KPI, Opportunity,
        AssessmentResponse, Assessment, DataSource, Application, Process, Notification,
    ):
        db.execute(delete(model).where(model.organization_id == org_id))
    db.execute(delete(AuditLog).where(AuditLog.organization_id == org_id))
    for user in db.scalars(select(User).where(User.organization_id == org_id)):
        user.roles = []
    db.flush()
    db.execute(delete(User).where(User.organization_id == org_id))
    db.execute(delete(Role).where(Role.organization_id == org_id))
    db.execute(delete(Department).where(Department.organization_id == org_id))
    db.execute(delete(Site).where(Site.organization_id == org_id))
    db.flush()


def _permissions(db: Session) -> dict[str, Permission]:
    """Synchronise le catalogue de permissions avec la base.

    Les permissions sont globales a la plateforme : seuls les roles, qui les regroupent,
    sont rattaches a une organisation. Une permission deja presente est mise a jour, pas
    dupliquee, ce qui rend le seed rejouable sur une base existante.
    """
    existing = {p.code: p for p in db.scalars(select(Permission))}
    for code, label, module, group in PERMISSION_CATALOG:
        permission = existing.get(code)
        if permission is None:
            permission = Permission(code=code, label=label, module=module, group=group)
            db.add(permission)
            existing[code] = permission
        else:
            permission.label = label
            permission.module = module
            permission.group = group

    # Les codes retires du catalogue sont supprimes, ainsi que leurs rattachements aux
    # roles : sans cela une ancienne permission continuerait d'ouvrir des droits.
    catalog = {code for code, _, _, _ in PERMISSION_CATALOG}
    obsoletes = [p for code, p in existing.items() if code not in catalog]
    for permission in obsoletes:
        permission.roles = []
        db.delete(permission)
        existing.pop(permission.code, None)
    db.flush()
    return existing


def _roles(db: Session, org: Organization, permissions: dict[str, Permission]) -> dict[str, Role]:
    """Instancie les onze roles fonctionnels pour l'organisation."""
    roles: dict[str, Role] = {}
    for template in ROLE_TEMPLATES:
        role = db.scalar(
            select(Role).where(Role.organization_id == org.id, Role.code == template.code)
        )
        if role is None:
            role = Role(organization_id=org.id, code=template.code)
            db.add(role)
        role.label = template.label
        role.description = template.description
        role.scope_level = template.scope_level
        role.is_system = template.is_system
        role.is_platform = template.is_platform
        role.permissions = [permissions[c] for c in template.permissions if c in permissions]
        roles[template.code] = role
    db.flush()
    return roles


def _build(db: Session) -> Organization:
    permissions = _permissions(db)

    org = db.scalar(select(Organization).where(Organization.code == ORG_CODE))
    if org is None:
        org = Organization(
            name="Medicacom",
            code=ORG_CODE,
            industry="Pharmaceutique",
            country="Tunisie",
            description=(
                "Laboratoire pharmaceutique opérant trois sites industriels et un centre de R&D, "
                "engagé dans un programme de transformation IA structuré selon TOGAF."
            ),
        )
        db.add(org)
        db.flush()

    # --- sites et departements ---
    sites: dict[str, Site] = {}
    for name, code, city, country, kind in SITES:
        site = Site(
            organization_id=org.id, name=name, code=code, city=city, country=country, site_type=kind
        )
        db.add(site)
        sites[code] = site
    db.flush()

    departments: dict[str, Department] = {}
    for name, code, family, head, site_code in DEPARTMENTS:
        dept = Department(
            organization_id=org.id,
            site_id=sites[site_code].id,
            name=name,
            code=code,
            family=family,
            head_name=head,
        )
        db.add(dept)
        departments[code] = dept
    db.flush()

    # --- roles et utilisateurs ---
    roles = _roles(db, org, permissions)

    # Le collaborateur Medicacom porte le role de plateforme : il franchit la frontiere
    # des organisations, contrairement a l'administrateur d'entreprise.
    admin = db.scalar(select(User).where(User.email == settings.FIRST_SUPERUSER_EMAIL.lower()))
    if admin is None:
        admin = User(
            organization_id=org.id,
            email=settings.FIRST_SUPERUSER_EMAIL.lower(),
            full_name="Administrateur Medicacom",
            job_title="Administrateur de la plateforme",
            hashed_password=hash_password(settings.FIRST_SUPERUSER_PASSWORD),
            is_superuser=True,
        )
        db.add(admin)
    else:
        admin.organization_id = org.id
    admin.roles = [roles["admin_medicacom"]]
    db.flush()

    for email, full_name, job, dept_code, dept_codes, site_codes, role_codes in USERS:
        user = User(
            organization_id=org.id,
            department_id=departments[dept_code].id,
            email=email,
            full_name=full_name,
            job_title=job,
            hashed_password=hash_password(DEMO_PASSWORD),
        )
        user.roles = [roles[c] for c in role_codes]
        user.departments = [departments[c] for c in dept_codes]
        user.sites = [sites[c] for c in site_codes]
        db.add(user)
    db.flush()
    director = db.scalar(select(User).where(User.email == "marwen.b@medicacom.com"))

    # --- diagnostic AS-IS ---
    assessment = Assessment(
        organization_id=org.id,
        site_id=sites["TUN"].id,
        name="Diagnostic AS-IS & Readiness",
        campaign="campagne 2026",
        status="en_cours",
        started_on=TODAY - timedelta(days=62),
        completion_rate=0.0,  # recalcule a partir des reponses
        blocking_threshold=2.5,
        notes="Ateliers menes avec les 8 departements du site de Tunis.",
    )
    db.add(assessment)
    db.flush()

    for axis, code, label, score, weight, confidence, critical, evidence in ASSESSMENT_RESPONSES:
        db.add(
            AssessmentResponse(
                organization_id=org.id,
                assessment_id=assessment.id,
                axis=axis,
                dimension_code=code,
                dimension_label=label,
                question=f"Quel est le niveau de maturité constaté sur : {label} ?",
                score=float(score),
                weight=weight,
                confidence=confidence,
                is_critical=critical,
                evidence=evidence,
                owner="K. Zouari",
            )
        )
    db.flush()

    # --- référentiel d'architecture ---
    processes: dict[str, Process] = {}
    for code, name, dept_code, maturity, volume, effort, gxp in PROCESSES:
        process = Process(
            organization_id=org.id,
            department_id=departments[dept_code].id,
            code=code,
            name=name,
            maturity=maturity,
            volume_per_month=volume,
            manual_effort_days=effort,
            is_gxp=gxp,
        )
        db.add(process)
        processes[code] = process
    db.flush()

    applications: dict[str, Application] = {}
    for name, vendor, category, api, criticality, gxp in APPLICATIONS:
        application = Application(
            organization_id=org.id,
            name=name,
            vendor=vendor,
            category=category,
            has_api=api,
            criticality=criticality,
            validated_gxp=gxp,
        )
        db.add(application)
        applications[name] = application
    db.flush()

    for name, app_name, kind, fmt, history, volume, quality, truth, personal, owner in DATASOURCES:
        db.add(
            DataSource(
                organization_id=org.id,
                application_id=applications[app_name].id,
                name=name,
                kind=kind,
                format=fmt,
                history_months=history,
                volume=volume,
                quality_score=quality,
                has_ground_truth=truth,
                personal_data=personal,
                owner=owner,
            )
        )
    db.flush()

    # --- opportunites, qualification et scoring ---
    opportunities: dict[str, Opportunity] = {}
    for spec in OPPORTUNITIES:
        im, fi, fe, al, rd, sy = spec["scores"]
        prob, impact = spec["risk"]
        opportunity = Opportunity(
            organization_id=org.id,
            department_id=departments[spec["dept"]].id,
            site_id=sites[spec["site"]].id,
            process_id=processes[spec["process"]].id,
            code=spec["code"],
            title=spec["title"],
            summary=spec["summary"],
            as_is_context=spec["as_is"],
            pain_points=spec["pain"],
            desired_outcome=spec["outcome"],
            sponsor=spec["sponsor"],
            business_owner=spec["owner"],
            technical_owner=spec["tech"],
            phase=spec["phase"],
            status=spec["status"],
            answers={"source": "atelier de cadrage 2026", **spec["facts"]},
            impact_business=im,
            impact_financial=fi,
            feasibility=fe,
            alignment=al,
            readiness=rd,
            synergies=sy,
            risk_probability=prob,
            risk_impact=impact,
            expected_benefit_eur=spec["benefit"],
            estimated_cost_eur=spec["cost"],
            **spec["facts"],
        )
        db.add(opportunity)
        db.flush()
        opportunities[spec["code"]] = opportunity

        result = recommendation.qualify(opportunity)
        db.add(
            AIRecommendation(
                organization_id=org.id,
                opportunity_id=opportunity.id,
                ai_type=result["ai_type"],
                ai_type_label=result["ai_type_label"],
                solution_pattern=result["solution_pattern"],
                rationale=result["rationale"],
                confidence=result["confidence"],
                fired_rules=result["fired_rules"],
                alternatives=result["alternatives"],
                guardrails=result["guardrails"],
            )
        )
        breakdown = scoring.score_opportunity(opportunity)
        opportunity.priority_score = breakdown.priority_score
        opportunity.score_explanation = breakdown.as_dict()
    db.flush()

    scoring.assign_ranks_and_waves(list(opportunities.values()), wave_size=6)
    db.flush()

    _seed_kpis(db, org, opportunities)
    _seed_value(db, org, opportunities)
    _seed_dependencies(db, org, opportunities)
    _seed_projects(db, org, opportunities, departments)
    _seed_risks(db, org, opportunities)
    _seed_sheet(db, org, opportunities["OPP-2026-014"], director)
    _seed_notifications(db, org, director)
    return org


# --------------------------------------------------------------------------------- KPI
KPIS = [
    ("OPP-2026-014", "KPI-FCT-ERR", "Erreur de prévision", "%", "down", 22, 10, 16, "baseline", "cible"),
    ("OPP-2026-014", "KPI-FCT-TIME", "Temps de production de la prévision", "j/mois", "down", 5, 1.5, 2.4, "5 j / mois", "1,5 j / mois"),
    ("OPP-2026-014", "KPI-FCT-STOCK", "Surstock immobilisé", "%", "down", 100, 88, 93, "BFR immobilisé", "-12 %"),
    ("OPP-2026-002", "KPI-REG-TIME", "Temps de rédaction par dossier", "jours", "down", 42, 22, 34, "42 jours", "22 jours"),
    ("OPP-2026-003", "KPI-MNT-STOP", "Arrêts non planifiés", "h/mois", "down", 46, 30, 38, "46 h", "30 h"),
    ("OPP-2026-004", "KPI-STK-RUP", "Taux de rupture", "%", "down", 4.2, 2.0, 3.4, "4,2 %", "2,0 %"),
    ("OPP-2026-005", "KPI-RND-REV", "Effort de revue documentaire", "j/mois", "down", 25, 9, 18, "25 j", "9 j"),
    ("OPP-2026-008", "KPI-FAC-AUTO", "Factures rapprochées automatiquement", "%", "up", 12, 80, 74, "12 %", "80 %"),
    ("OPP-2026-009", "KPI-DEV-CLASS", "Déviations correctement classées", "%", "up", 71, 92, 86, "71 %", "92 %"),
    ("OPP-2026-011", "KPI-PV-DELAI", "Délai de restitution pharmacovigilance", "jours", "down", 30, 1, 1, "30 jours", "quotidien"),
    ("OPP-2026-012", "KPI-COLD-COST", "Coût du transport réfrigéré", "%", "down", 100, 85, 92, "base 100", "-15 %"),
    ("OPP-2026-019", "KPI-ENE-CONSO", "Consommation des utilités", "%", "down", 100, 91, 95, "base 100", "-9 %"),
]


def _seed_kpis(db: Session, org: Organization, opportunities: dict[str, Opportunity]) -> None:
    for opp_code, code, name, unit, direction, baseline, target, current, b_label, t_label in KPIS:
        opportunity = opportunities[opp_code]
        kpi = KPI(
            organization_id=org.id,
            department_id=opportunity.department_id,
            opportunity_id=opportunity.id,
            code=code,
            name=name,
            unit=unit,
            direction=direction,
            baseline_value=baseline,
            target_value=target,
            current_value=current,
            baseline_label=b_label,
            target_label=t_label,
        )
        db.add(kpi)
        db.flush()
        # Trois relevés trimestriels entre la baseline et la valeur courante
        for index in range(3):
            ratio = (index + 1) / 3
            db.add(
                Measurement(
                    organization_id=org.id,
                    kpi_id=kpi.id,
                    measured_on=TODAY - timedelta(days=90 * (3 - index)),
                    value=round(baseline + (current - baseline) * ratio, 2),
                    period_label=f"T{index + 1} 2026",
                    source="Relevé mensuel consolidé",
                )
            )
    db.flush()


# ------------------------------------------------------------------------ coûts et gains
def _seed_value(db: Session, org: Organization, opportunities: dict[str, Opportunity]) -> None:
    """Construit un business case par opportunite.

    Repartition retenue : 81 % du TCO en investissement initial (build) et le solde en
    coûts recurrents lisses sur trois ans (run). Les gains sont ventiles sur trois lignes
    de P&L pour rester exploitables par le contrôle de gestion.
    """
    pnl_lines = ["Coût des ventes", "Frais généraux", "Chiffre d'affaires"]
    shares = [0.55, 0.28, 0.17]

    for spec in OPPORTUNITIES:
        opportunity = opportunities[spec["code"]]
        tco = float(spec["cost"])
        benefit = float(spec["benefit"])
        capex = round(tco * 0.81, 0)
        opex = round((tco - capex) / 3.0, 0)

        db.add_all(
            [
                Cost(
                    organization_id=org.id, opportunity_id=opportunity.id,
                    label="Conception et developpement de la solution",
                    category="build", nature="capex", amount_eur=round(capex * 0.58, 0), year=2026,
                ),
                Cost(
                    organization_id=org.id, opportunity_id=opportunity.id,
                    label="Intégration au système d'information et reprise des données",
                    category="build", nature="capex", amount_eur=round(capex * 0.27, 0), year=2026,
                ),
                Cost(
                    organization_id=org.id, opportunity_id=opportunity.id,
                    label="Conduite du changement et formation",
                    category="build", nature="capex", amount_eur=round(capex * 0.15, 0), year=2026,
                ),
                Cost(
                    organization_id=org.id, opportunity_id=opportunity.id,
                    label="Hébergement, supervision et maintien en condition opérationnelle",
                    category="run", nature="opex", amount_eur=opex, recurring=True,
                ),
            ]
        )

        for line, share in zip(pnl_lines, shares):
            db.add(
                Benefit(
                    organization_id=org.id,
                    opportunity_id=opportunity.id,
                    label=f"Gain annuel - {line.lower()}",
                    category="productivité" if line != "Chiffre d'affaires" else "revenu",
                    nature="hard" if line != "Frais generaux" else "soft",
                    annual_amount_eur=round(benefit * share, 0),
                    realization_rate=1.0,
                    pnl_line=line,
                    start_year=2026,
                )
            )
    db.flush()


# --------------------------------------------------------------------------- dependances
DEPENDENCIES = [
    ("OPP-2026-014", "OPP-2026-004", "data", "Historique des ventes multi-marchés",
     "Partage de l'historique de ventes consolidé", 0.9, False),
    ("OPP-2026-014", "OPP-2026-012", "data", "Référentiel produit et nomenclatures",
     "Meme référentiel produit et même maille de prévision", 0.8, False),
    ("OPP-2026-004", "OPP-2026-012", "process", "PRC-STK",
     "Deux briques du même processus de pilotage des stocks", 0.7, False),
    ("OPP-2026-002", "OPP-2026-006", "process", "PRC-REG",
     "L'agent réglementaire réutilise l'assistant de rédaction", 0.9, True),
    ("OPP-2026-002", "OPP-2026-018", "data", "Corpus de littérature scientifique",
     "Socle documentaire et ancrage communs", 0.6, False),
    ("OPP-2026-005", "OPP-2026-018", "data", "Corpus de littérature scientifique",
     "Recouvrement fort sur la revue documentaire R&D", 0.9, False),
    ("OPP-2026-009", "OPP-2026-013", "application", "QMS TrackWise",
     "Même socle d'extraction documentaire qualité", 0.7, False),
    ("OPP-2026-013", "OPP-2026-017", "process", "PRC-LIB",
     "L'extraction suppose un processus de libération harmonisé", 0.8, True),
    ("OPP-2026-003", "OPP-2026-016", "data", "Series temporelles capteurs ligne 3",
     "Meme socle de séries temporelles capteurs", 0.9, False),
    ("OPP-2026-003", "OPP-2026-019", "application", "Historien PI System",
     "Connexion commune a l'historien de procede", 0.5, False),
    ("OPP-2026-011", "OPP-2026-002", "kpi", "KPI-REG-TIME",
     "Indicateurs réglementaires partagés", 0.4, False),
    ("OPP-2026-008", "OPP-2026-013", "application", "SAP S/4HANA",
     "Meme chaine de dematerialisation documentaire", 0.5, False),
    ("OPP-2026-010", "OPP-2026-003", "process", "PRC-MNT",
     "Le plan de production consomme les fenetres de maintenance", 0.7, True),
    ("OPP-2026-015", "OPP-2026-002", "data", "Dossiers d'enregistrement eCTD",
     "Réutilisation du référentiel de réponses validées", 0.5, False),
]


def _seed_dependencies(db: Session, org: Organization, opportunities: dict[str, Opportunity]) -> None:
    for source, target, kind, asset, label, strength, blocking in DEPENDENCIES:
        db.add(
            Dependency(
                organization_id=org.id,
                source_opportunity_id=opportunities[source].id,
                target_opportunity_id=opportunities[target].id,
                kind=kind,
                asset_ref=asset,
                label=label,
                strength=strength,
                is_blocking=blocking,
            )
        )
    db.flush()


# ------------------------------------------------------------------------------- projets
PROJECT_BUDGETS = {
    # opportunite : (budget accorde, montant engagé, avancement %)
    "OPP-2026-014": (330000, 286000, 62.0),
    "OPP-2026-002": (395000, 232000, 34.0),
    "OPP-2026-003": (290000, 228000, 48.0),
    "OPP-2026-005": (255000, 168000, 30.0),
    "OPP-2026-007": (225000, 179000, 45.0),
    "OPP-2026-008": (165000, 165000, 100.0),
    "OPP-2026-009": (240000, 206000, 66.0),
    "OPP-2026-010": (280000, 158000, 28.0),
    "OPP-2026-011": (122000, 122000, 100.0),
    "OPP-2026-012": (245000, 202000, 58.0),
    "OPP-2026-016": (210000, 168000, 44.0),
    "OPP-2026-018": (191000, 122000, 26.0),
    "OPP-2026-019": (152000, 152000, 100.0),
}

STAGE_DEFS = [
    (Phase.QUALIFICATION, "Qualification", ["Besoin formalisé", "Type de solution qualifie"]),
    (Phase.FRAMING, "Cadrage / Business case", ["Business case valide", "Sponsor engagé"]),
    (Phase.POC, "POC", ["Faisabilité démontrée", "KPI baseline mesure"]),
    (Phase.PILOT, "Pilote", ["Pilote en conditions réelles", "Adoption mesurée"]),
    (Phase.PRODUCTION, "Mise en production", ["Run transféré", "Valeur captée suivie"]),
]


def _gate_label(phase: str) -> str:
    """Libelle de la prochaine gate : phase courante vers la phase suivante."""
    order = [code for code, _, _ in STAGE_DEFS]
    current = Phase.LABELS[phase]
    index = order.index(phase)
    if index + 1 < len(order):
        return f"Gate {current.lower()} → {Phase.LABELS[order[index + 1]].lower()}"
    return f"Revue de valeur {current.lower()}"


def _seed_projects(
    db: Session,
    org: Organization,
    opportunities: dict[str, Opportunity],
    departments: dict[str, Department],
) -> None:
    order = {code: index for index, (code, _, _) in enumerate(STAGE_DEFS)}
    index = 0
    for spec in OPPORTUNITIES:
        code = spec["code"]
        if code not in PROJECT_BUDGETS:
            continue
        index += 1
        opportunity = opportunities[code]
        budget, committed, progress = PROJECT_BUDGETS[code]
        current_rank = order[opportunity.phase]

        project = Project(
            organization_id=org.id,
            opportunity_id=opportunity.id,
            department_id=opportunity.department_id,
            code=f"PRJ-2026-{index:03d}",
            name=opportunity.title,
            phase=opportunity.phase,
            status="actif" if opportunity.phase != Phase.PRODUCTION else "en_run",
            sponsor=opportunity.sponsor,
            business_owner=opportunity.business_owner,
            technical_owner=opportunity.technical_owner,
            start_date=TODAY - timedelta(days=180 + index * 5),
            next_gate_date=TODAY + timedelta(days=6),
            next_gate_label=_gate_label(opportunity.phase),
            budget_eur=budget,
            committed_eur=committed,
            progress=progress,
            summary=opportunity.summary,
        )
        db.add(project)
        db.flush()

        for sequence, (stage_code, stage_name, criteria) in enumerate(STAGE_DEFS):
            if sequence < current_rank:
                status, passed = "termine", True
            elif sequence == current_rank:
                status, passed = "en_cours", False
            else:
                status, passed = "a_faire", False
            stage = Stage(
                organization_id=org.id,
                project_id=project.id,
                code=stage_code,
                name=stage_name,
                sequence=sequence,
                status=status,
                gate_passed=passed,
                gate_criteria=criteria,
                start_date=TODAY - timedelta(days=170 - sequence * 30) if sequence <= current_rank else None,
                end_date=TODAY - timedelta(days=150 - sequence * 30) if sequence < current_rank else None,
            )
            db.add(stage)
            db.flush()

            if sequence == current_rank:
                db.add(
                    Milestone(
                        organization_id=org.id,
                        project_id=project.id,
                        stage_id=stage.id,
                        name=f"Gate de sortie - {stage_name}",
                        due_date=project.next_gate_date,
                        status="a_faire",
                        is_gate=True,
                    )
                )
                for offset, (title, assignee) in enumerate(
                    [
                        ("Consolider les données de la phase", opportunity.technical_owner),
                        ("Mesurer les KPI de sortie de phase", opportunity.business_owner),
                        ("Preparer le dossier de passage en comité", opportunity.sponsor),
                    ]
                ):
                    db.add(
                        Task(
                            organization_id=org.id,
                            project_id=project.id,
                            stage_id=stage.id,
                            title=title,
                            assignee=assignee,
                            status="en_cours" if offset == 0 else "a_faire",
                            due_date=TODAY + timedelta(days=4 + offset * 3),
                            effort_days=float(2 + offset),
                        )
                    )
    db.flush()


# ------------------------------------------------------------------------------- risques
RISKS = [
    # (opportunite, titre, catégorie, proba, impact, statut, owner, mitigations)
    ("OPP-2026-014", "Qualité de l'historique des promotions incomplète", "data", 3, 3, "ouvert", "Data Office",
     ["Reprise des campagnes 2024-2025 depuis le CRM", "Regle de repli en l'absence de promotion connue"]),
    ("OPP-2026-014", "Dépendance au référentiel produit ERP", "technique", 2, 2, "maitrise", "Data Office",
     ["Contrôle de coherence quotidien sur le référentiel"]),
    ("OPP-2026-014", "Adoption par les équipes commerciales terrain", "adoption", 3, 3, "ouvert", "L. Trabelsi",
     ["Réseau de relais par marché", "Ajustement manuel conservé dans l'outil"]),
    ("OPP-2026-006", "Perimetre GxP : validation informatique de l'agent", "réglementaire", 4, 5, "en_attente", "C. Lambert",
     ["Plan de validation CSV soumis à l'assurance qualité", "Point de contrôle humain sur chaque action engageante"]),
    ("OPP-2026-002", "Risque de contenu non source dans le dossier depose", "reglementaire", 4, 4, "en_attente", "C. Lambert",
     ["Ancrage documentaire obligatoire", "Revue humaine systématique avant dépôt"]),
    ("OPP-2026-007", "Variabilite des conditions d'acquisition des images", "technique", 4, 4, "ouvert", "S. Meddeb",
     ["Qualification du poste d'acquisition", "Jeu de reference pour le suivi de derive"]),
    ("OPP-2026-003", "Couverture capteurs insuffisante sur certains organes", "data", 3, 3, "ouvert", "H. Gharbi",
     ["Instrumentation complementaire budgetee en vague 2"]),
    ("OPP-2026-009", "Categorisation heterogene du corpus d'apprentissage", "data", 3, 4, "ouvert", "S. Meddeb",
     ["Réannotation d'un echantillon par deux evaluateurs"]),
    ("OPP-2026-013", "Qualite variable des PDF scannes fournisseurs", "data", 3, 3, "ouvert", "S. Meddeb",
     ["Seuil de confiance et reprise manuelle sous ce seuil"]),
    ("OPP-2026-017", "Absence de processus cible partage entre ateliers", "organisation", 4, 3, "ouvert", "S. Meddeb",
     ["Atelier de standardisation pilote par l'excellence opérationnelle"]),
    ("OPP-2026-012", "Fiabilité des relevés de température en transport", "data", 2, 3, "ouvert", "N. Ben Salah",
     ["Contrôle croisé avec les relevés des transporteurs"]),
    ("OPP-2026-010", "Acceptation des contraintes d'ordonnancement par les ateliers", "adoption", 3, 3, "ouvert", "H. Gharbi",
     ["Co-construction des règles avec les responsables d'atelier"]),
]


def _seed_risks(db: Session, org: Organization, opportunities: dict[str, Opportunity]) -> None:
    projects = {p.opportunity_id: p for p in db.scalars(select(Project).where(Project.organization_id == org.id))}
    for opp_code, title, category, probability, impact, status, owner, actions in RISKS:
        opportunity = opportunities[opp_code]
        project = projects.get(opportunity.id)
        risk = Risk(
            organization_id=org.id,
            opportunity_id=opportunity.id,
            project_id=project.id if project else None,
            title=title,
            category=category,
            probability=probability,
            impact=impact,
            severity=RiskLevel.from_score(probability * impact),
            status=status,
            owner=owner,
        )
        db.add(risk)
        db.flush()
        for action in actions:
            db.add(
                Mitigation(
                    organization_id=org.id,
                    risk_id=risk.id,
                    action=action,
                    owner=owner,
                    due_date=TODAY + timedelta(days=45),
                    status="en_cours",
                )
            )
    db.flush()

    # Un incident ouvert sur le projet en pilote, pour alimenter le suivi
    pilot = db.scalar(
        select(Project).where(Project.organization_id == org.id, Project.phase == Phase.PILOT)
    )
    if pilot:
        db.add(
            Issue(
                organization_id=org.id,
                project_id=pilot.id,
                title="Écart de périmètre sur deux marchés du pilote",
                severity="moyenne",
                status="ouvert",
                owner="Data Office",
                opened_on=TODAY - timedelta(days=11),
                description="Les marchés Maroc et Tunisie exposent des nomenclatures divergentes.",
            )
        )
    db.flush()


# -------------------------------------------------------------------------- fiche projet
def _seed_sheet(db: Session, org: Organization, opportunity: Opportunity, author: User | None) -> None:
    document = Document(
        organization_id=org.id,
        opportunity_id=opportunity.id,
        code=f"FICHE-{opportunity.code}",
        title=f"Fiche projet - {opportunity.title}",
        doc_type="fiche_projet",
        status="soumis",
        current_version=2,
        author=author.full_name if author else "Data Office",
    )
    db.add(document)
    db.flush()

    for number, label, summary, offset in [
        (1, "v1 - cadrage", "Première rédaction issue de l'atelier de cadrage", 120),
        (2, "v2 - business case", "Business case chiffré avec le contrôle de gestion", 24),
    ]:
        db.add(
            Version(
                organization_id=org.id,
                document_id=document.id,
                number=number,
                label=label,
                content={"note": summary, "opportunity_code": opportunity.code},
                change_summary=summary,
                created_by=author.full_name if author else "Data Office",
            )
        )
    db.add(
        Approval(
            organization_id=org.id,
            document_id=document.id,
            opportunity_id=opportunity.id,
            stage_code=Phase.PILOT,
            committee="Comité IA",
            approver_name=author.full_name if author else "Comité IA",
            approver_user_id=author.id if author else None,
            decision="en_attente",
            comment="Passage en comité du 30 septembre 2026 : gate pilote vers production.",
        )
    )
    db.flush()


def _seed_notifications(db: Session, org: Organization, user: User | None) -> None:
    notifications = [
        ("Gate pilote a valider", "La fiche OPP-2026-014 attend la décision du comité du 30 septembre.", "warning", "opportunity"),
        ("2 dimensions bloquantes", "Gouvernance data et Infrastructure IA restent sous le seuil de production.", "warning", "assessment"),
        ("Doublon probable detecte", "Revue documentaire R&D et Synthèse de la littérature partagent le même corpus.", "info", "opportunity"),
    ]
    for title, body, level, entity in notifications:
        db.add(
            Notification(
                organization_id=org.id,
                user_id=user.id if user else None,
                title=title,
                body=body,
                level=level,
                entity_type=entity,
            )
        )
    db.flush()


# ======================================================================================
# Entree
# ======================================================================================

def run(reset: bool = False) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        org = db.scalar(select(Organization).where(Organization.code == ORG_CODE))
        if org and not reset:
            print("Organisation Medicacom deja presente. Relancez avec --reset pour reconstruire.")
            return
        if org and reset:
            _reset(db, org)
        org = _build(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print("Seed termine.")
    print(f"  Organisation : Medicacom ({ORG_CODE})")
    print(f"  Mot de passe commun aux comptes de demonstration : {DEMO_PASSWORD}")
    print()
    print("  Comptes de demonstration, un par role fonctionnel :")
    print(f"    {settings.FIRST_SUPERUSER_EMAIL:<34} Administrateur Medicacom (plateforme)")
    for email, full_name, _job, _dept, _depts, _sites, role_codes in USERS:
        template = next((t for t in ROLE_TEMPLATES if t.code == role_codes[0]), None)
        label = template.label if template else role_codes[0]
        scope = ScopeLevel.LABELS[template.scope_level] if template else ""
        print(f"    {email:<34} {label} — périmètre {scope.lower()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed de demonstration Medicacom")
    parser.add_argument("--reset", action="store_true", help="Vide les données métier avant de reconstruire")
    args = parser.parse_args()
    run(reset=args.reset)
