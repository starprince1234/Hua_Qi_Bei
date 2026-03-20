from __future__ import annotations

from app.utils.math_utils import compute_var, compute_cvar
from app.core.constants import RISK_THRESHOLDS


def compute_risk(quantiles: dict[str, list[float]], horizon: int) -> dict:
    """
    Derive risk metrics from model quantile predictions.

    Args:
        quantiles: dict keyed by quantile level string, values are list of floats (one per horizon step).
        horizon: prediction horizon in days.

    Returns:
        dict with keys: risk_level, var_95, cvar_95, volatility.
    """
    # Use the 5th and 95th quantile to approximate VaR/CVaR
    q05 = quantiles.get("0.05", [])
    q50 = quantiles.get("0.50", [])
    q95 = quantiles.get("0.95", [])

    # Point estimate at end of horizon
    p50_end = q50[-1] if q50 else 0.0
    p05_end = q05[-1] if q05 else p50_end * 0.9

    var_95 = p05_end - p50_end  # negative means loss
    cvar_95 = var_95 * 1.35  # rough CVaR as 1.35× VaR

    # Approximate volatility from IQR (q75 - q25) / 1.35
    q25 = quantiles.get("0.25", [])
    q75 = quantiles.get("0.75", [])
    if q25 and q75:
        iqr = (q75[-1] if q75 else 0) - (q25[-1] if q25 else 0)
        volatility = iqr / (1.35 * max(abs(p50_end), 1e-9))
    else:
        volatility = abs(var_95) / max(abs(p50_end), 1e-9)

    # Scale to annualised proxy
    annualised_vol = volatility * (252 / horizon) ** 0.5

    if annualised_vol <= RISK_THRESHOLDS["low"]:
        risk_level = "low"
    elif annualised_vol <= RISK_THRESHOLDS["medium"]:
        risk_level = "medium"
    elif annualised_vol <= RISK_THRESHOLDS["high"]:
        risk_level = "high"
    else:
        risk_level = "extreme"

    return {
        "risk_level": risk_level,
        "var_95": round(var_95, 4),
        "cvar_95": round(cvar_95, 4),
        "volatility": round(volatility, 6),
    }
