"""M6 - Croisements interservices : dependances, synergies et detection de doublons.

Deux opportunites sont rapprochees sur trois signaux :
  1. similarite lexicale du titre et du resume (indice de Jaccard sur les mots utiles) ;
  2. actifs partages declares via les dependances (data, process, KPI, application) ;
  3. appartenance au meme processus ou au meme departement.

Le score de similarite combine ces signaux. Au-dela de 0,55 le couple est signale comme
doublon probable ; entre 0,30 et 0,55 il est signale comme synergie a exploiter.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from itertools import combinations
from typing import Iterable, Sequence

STOPWORDS = {
    "de", "des", "du", "la", "le", "les", "un", "une", "et", "en", "sur", "pour", "par",
    "au", "aux", "dans", "avec", "sans", "a", "l", "d", "the", "of", "multi", "par",
}

DUPLICATE_THRESHOLD = 0.55
SYNERGY_THRESHOLD = 0.30


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", _normalize(text))
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _assets(opportunity, dependencies: Sequence) -> set[str]:
    assets = set()
    for dep in dependencies:
        if dep.source_opportunity_id == opportunity.id and dep.asset_ref:
            assets.add(f"{dep.kind}:{_normalize(dep.asset_ref)}")
        if dep.target_opportunity_id == opportunity.id and dep.asset_ref:
            assets.add(f"{dep.kind}:{_normalize(dep.asset_ref)}")
    return assets


def compare(opp_a, opp_b, dependencies: Sequence) -> dict:
    tokens_a = tokenize(f"{opp_a.title} {opp_a.summary or ''}")
    tokens_b = tokenize(f"{opp_b.title} {opp_b.summary or ''}")
    lexical = jaccard(tokens_a, tokens_b)

    assets_a = _assets(opp_a, dependencies)
    assets_b = _assets(opp_b, dependencies)
    asset_overlap = jaccard(assets_a, assets_b)

    context = 0.0
    if opp_a.process_id and opp_a.process_id == opp_b.process_id:
        context += 0.6
    if opp_a.department_id and opp_a.department_id == opp_b.department_id:
        context += 0.4
    context = min(context, 1.0)

    score = 0.55 * lexical + 0.30 * asset_overlap + 0.15 * context
    shared_terms = sorted(tokens_a & tokens_b)

    if score >= DUPLICATE_THRESHOLD:
        verdict = "doublon_probable"
    elif score >= SYNERGY_THRESHOLD:
        verdict = "synergie"
    else:
        verdict = "independant"

    return {
        "source_id": opp_a.id,
        "source_code": opp_a.code,
        "source_title": opp_a.title,
        "target_id": opp_b.id,
        "target_code": opp_b.code,
        "target_title": opp_b.title,
        "similarity": round(score, 3),
        "lexical_similarity": round(lexical, 3),
        "asset_overlap": round(asset_overlap, 3),
        "context_overlap": round(context, 3),
        "shared_terms": shared_terms[:12],
        "shared_assets": sorted(assets_a & assets_b),
        "verdict": verdict,
    }


def detect_duplicates(
    opportunities: Sequence, dependencies: Sequence, min_similarity: float = SYNERGY_THRESHOLD
) -> list[dict]:
    """Compare toutes les paires et renvoie celles au-dessus du seuil, triees."""
    pairs = [
        compare(a, b, dependencies)
        for a, b in combinations(list(opportunities), 2)
    ]
    kept = [p for p in pairs if p["similarity"] >= min_similarity]
    kept.sort(key=lambda p: -p["similarity"])
    return kept


def synergy_scores(opportunities: Sequence, dependencies: Sequence) -> dict[int, float]:
    """Score de synergie (0-100) par opportunite, alimentant le critere M7."""
    by_opp: dict[int, float] = defaultdict(float)
    for dep in dependencies:
        weight = float(dep.strength or 1.0)
        by_opp[dep.source_opportunity_id] += weight
        if dep.target_opportunity_id:
            by_opp[dep.target_opportunity_id] += weight

    if not by_opp:
        return {o.id: 0.0 for o in opportunities}

    highest = max(by_opp.values()) or 1.0
    return {o.id: round(min(100.0, by_opp.get(o.id, 0.0) / highest * 100.0), 1) for o in opportunities}


def dependency_graph(opportunities: Sequence, dependencies: Iterable) -> dict:
    """Graphe pret a afficher : noeuds = opportunites, aretes = dependances."""
    index = {o.id: o for o in opportunities}
    nodes = [
        {
            "id": o.id,
            "code": o.code,
            "label": o.title,
            "department_id": o.department_id,
            "phase": o.phase,
            "priority_score": round(float(o.priority_score or 0.0), 1),
        }
        for o in opportunities
    ]
    edges = []
    for dep in dependencies:
        if dep.source_opportunity_id not in index:
            continue
        edges.append(
            {
                "id": dep.id,
                "source": dep.source_opportunity_id,
                "target": dep.target_opportunity_id,
                "kind": dep.kind,
                "label": dep.label,
                "asset_ref": dep.asset_ref,
                "strength": float(dep.strength or 1.0),
                "is_blocking": bool(dep.is_blocking),
            }
        )
    return {"nodes": nodes, "edges": edges}
