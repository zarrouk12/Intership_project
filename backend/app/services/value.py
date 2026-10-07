"""M10 - Calcul de la valeur : TCO, gains annuels, ROI, payback, impact P&L.

TCO sur l'horizon retenu = couts non recurrents + (couts recurrents x nombre d'annees).
Gains annuels nets = somme des benefices annuels ponderes par leur taux de realisation.
ROI (%) = (gains cumules sur l'horizon - TCO) / TCO x 100.
Payback (mois) = capex / ((gains annuels - couts recurrents annuels) / 12). On mesure le
temps de recuperation de l'investissement initial par le gain annuel net d'exploitation :
faire porter au payback trois annees d'opex qui ne sont pas encore engagees le fausserait.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass
class ValueSummary:
    horizon_years: int
    tco_eur: float
    capex_eur: float
    opex_annual_eur: float
    annual_benefit_eur: float
    cumulated_benefit_eur: float
    net_value_eur: float
    roi_percent: float
    payback_months: float | None
    pnl_breakdown: dict[str, float]

    def as_dict(self) -> dict:
        return {
            "horizon_years": self.horizon_years,
            "tco_eur": round(self.tco_eur, 2),
            "capex_eur": round(self.capex_eur, 2),
            "opex_annual_eur": round(self.opex_annual_eur, 2),
            "annual_benefit_eur": round(self.annual_benefit_eur, 2),
            "cumulated_benefit_eur": round(self.cumulated_benefit_eur, 2),
            "net_value_eur": round(self.net_value_eur, 2),
            "roi_percent": round(self.roi_percent, 1),
            "payback_months": round(self.payback_months, 1) if self.payback_months is not None else None,
            "pnl_breakdown": {k: round(v, 2) for k, v in self.pnl_breakdown.items()},
        }


def compute_value(
    costs: Sequence,
    benefits: Sequence,
    horizon_years: int = 3,
) -> ValueSummary:
    capex = sum(float(c.amount_eur or 0.0) for c in costs if not c.recurring)
    opex_annual = sum(float(c.amount_eur or 0.0) for c in costs if c.recurring)
    tco = capex + opex_annual * horizon_years

    annual_benefit = sum(
        float(b.annual_amount_eur or 0.0) * float(b.realization_rate or 1.0) for b in benefits
    )
    cumulated = annual_benefit * horizon_years
    net = cumulated - tco
    roi = (net / tco * 100.0) if tco > 0 else 0.0

    payback: float | None = None
    net_annual = annual_benefit - opex_annual
    if net_annual > 0 and capex > 0:
        payback = capex / (net_annual / 12.0)

    pnl: dict[str, float] = {}
    for b in benefits:
        line = b.pnl_line or "autre"
        pnl[line] = pnl.get(line, 0.0) + float(b.annual_amount_eur or 0.0) * float(
            b.realization_rate or 1.0
        )

    return ValueSummary(
        horizon_years=horizon_years,
        tco_eur=tco,
        capex_eur=capex,
        opex_annual_eur=opex_annual,
        annual_benefit_eur=annual_benefit,
        cumulated_benefit_eur=cumulated,
        net_value_eur=net,
        roi_percent=roi,
        payback_months=payback,
        pnl_breakdown=pnl,
    )


def kpi_progress(kpi) -> dict:
    """Taux d'atteinte d'un KPI entre sa baseline et sa cible."""
    baseline = kpi.baseline_value
    target = kpi.target_value
    current = kpi.current_value if kpi.current_value is not None else baseline
    progress = None
    if baseline is not None and target is not None and baseline != target and current is not None:
        progress = (current - baseline) / (target - baseline) * 100.0
        progress = max(0.0, min(150.0, progress))
    return {
        "id": kpi.id,
        "code": kpi.code,
        "name": kpi.name,
        "unit": kpi.unit,
        "direction": kpi.direction,
        "baseline_value": baseline,
        "target_value": target,
        "current_value": current,
        "baseline_label": kpi.baseline_label,
        "target_label": kpi.target_label,
        "progress_percent": round(progress, 1) if progress is not None else None,
        "opportunity_id": kpi.opportunity_id,
    }


def aggregate_portfolio_value(summaries: Iterable[ValueSummary]) -> dict:
    """Consolide plusieurs business cases en une vue portefeuille."""
    items = list(summaries)
    tco = sum(s.tco_eur for s in items)
    benefit = sum(s.annual_benefit_eur for s in items)
    cumulated = sum(s.cumulated_benefit_eur for s in items)
    net = cumulated - tco
    roi = (net / tco * 100.0) if tco > 0 else 0.0
    paybacks = [s.payback_months for s in items if s.payback_months is not None]
    return {
        "projects": len(items),
        "tco_eur": round(tco, 2),
        "annual_benefit_eur": round(benefit, 2),
        "cumulated_benefit_eur": round(cumulated, 2),
        "net_value_eur": round(net, 2),
        "roi_percent": round(roi, 1),
        "average_payback_months": round(sum(paybacks) / len(paybacks), 1) if paybacks else None,
    }
