"""Advanced options analysis — unusual activity, smart money, conviction V2, IV, GEX."""

import math
from datetime import datetime
from pathlib import Path

import yaml

from src.utils.logging_config import get_logger

logger = get_logger("options_advanced")

PROJECT_ROOT = Path(__file__).parent.parent.parent


def _load_options_config() -> dict:
    """Load options config from config/options.yaml."""
    path = PROJECT_ROOT / "config" / "options.yaml"
    if path.exists():
        try:
            with open(path) as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {}


# ── Unusual Activity Detection ────────────────────────────────


def detect_unusual_activity(flow_alerts: list[dict] | None, chain_data: dict | None) -> dict:
    """Detect unusual activity from sweep/block alerts and chain data."""
    if not flow_alerts:
        return {
            "available": False,
            "sweep_count": 0,
            "block_count": 0,
            "golden_sweep_count": 0,
            "total_sweep_premium": 0,
            "dominant_side": "neutral",
            "largest_sweep": None,
            "volume_oi_flags": [],
        }

    _load_options_config()

    sweeps = [a for a in flow_alerts if a.get("type") in ("sweep", "golden_sweep")]
    blocks = [a for a in flow_alerts if a.get("type") == "block"]
    golden = [a for a in flow_alerts if a.get("type") == "golden_sweep"]

    total_sweep_prem = sum(a.get("premium", 0) for a in sweeps)
    bull_prem = sum(a.get("premium", 0) for a in sweeps if a.get("sentiment") == "bullish")
    bear_prem = sum(a.get("premium", 0) for a in sweeps if a.get("sentiment") == "bearish")

    if bull_prem > bear_prem * 1.5:
        dominant_side = "bullish"
    elif bear_prem > bull_prem * 1.5:
        dominant_side = "bearish"
    else:
        dominant_side = "mixed"

    largest = max(sweeps, key=lambda x: x.get("premium", 0)) if sweeps else None

    # Volume-to-OI flags from chain data
    vol_oi_flags = []
    if chain_data and chain_data.get("chains"):
        for _exp, data in chain_data["chains"].items():
            for contract_list in [data.get("calls", []), data.get("puts", [])]:
                for c in contract_list:
                    vol = c.get("volume") or 0
                    oi = c.get("openInterest") or 0
                    if oi > 0 and vol > oi * 2:
                        vol_oi_flags.append({
                            "strike": c.get("strike"),
                            "volume": vol,
                            "oi": oi,
                            "ratio": round(vol / oi, 1),
                        })
    vol_oi_flags.sort(key=lambda x: x.get("ratio", 0), reverse=True)

    return {
        "available": True,
        "sweep_count": len(sweeps),
        "block_count": len(blocks),
        "golden_sweep_count": len(golden),
        "total_sweep_premium": total_sweep_prem,
        "dominant_side": dominant_side,
        "largest_sweep": largest,
        "volume_oi_flags": vol_oi_flags[:10],
    }


# ── Smart Money vs Retail ─────────────────────────────────────


def classify_flow(flow_alerts: list[dict] | None) -> dict:
    """Classify flow into smart money vs retail buckets."""
    if not flow_alerts:
        return {
            "available": False,
            "smart_money_pct": 0,
            "retail_pct": 0,
            "smart_money_sentiment": "neutral",
            "retail_sentiment": "neutral",
            "divergence_score": 0,
        }

    smart_money = []
    retail = []

    for alert in flow_alerts:
        premium = alert.get("premium", 0)
        ask_side = alert.get("ask_side_pct")
        alert_type = alert.get("type", "trade")

        is_smart = (
            alert_type in ("sweep", "golden_sweep", "block")
            or premium >= 100000
            or (ask_side is not None and ask_side >= 0.7)
        )

        if is_smart:
            smart_money.append(alert)
        elif premium < 5000:
            retail.append(alert)
        # Mid-range: could be either, count as retail for now
        else:
            retail.append(alert)

    total = len(smart_money) + len(retail)
    smart_pct = round(len(smart_money) / total * 100, 1) if total > 0 else 0
    retail_pct = round(len(retail) / total * 100, 1) if total > 0 else 0

    def _sentiment(trades: list[dict]) -> str:
        bull = sum(1 for t in trades if t.get("sentiment") == "bullish")
        bear = sum(1 for t in trades if t.get("sentiment") == "bearish")
        total_trades = bull + bear
        if total_trades == 0:
            return "neutral"
        ratio = bull / total_trades
        if ratio >= 0.65:
            return "bullish"
        if ratio <= 0.35:
            return "bearish"
        return "mixed"

    smart_sent = _sentiment(smart_money)
    retail_sent = _sentiment(retail)

    # Divergence: 0-100, high when smart and retail disagree
    sent_map = {"bullish": 1, "mixed": 0, "neutral": 0, "bearish": -1}
    smart_val = sent_map.get(smart_sent, 0)
    retail_val = sent_map.get(retail_sent, 0)
    divergence = abs(smart_val - retail_val) * 50  # max 100

    return {
        "available": True,
        "smart_money_pct": smart_pct,
        "retail_pct": retail_pct,
        "smart_money_sentiment": smart_sent,
        "retail_sentiment": retail_sent,
        "divergence_score": divergence,
        "smart_money_count": len(smart_money),
        "retail_count": len(retail),
    }


# ── Conviction V2 ─────────────────────────────────────────────


def compute_conviction_v2(
    flow_data: dict,
    flow_alerts: list[dict] | None,
    dark_pool: list[dict] | None,
    institutional: dict | None,
    historical_iv: list[dict] | None,
    chain_data: dict | None,
) -> dict:
    """Multi-factor conviction scoring with provider-aware weight redistribution."""
    config = _load_options_config()
    base_weights = config.get("conviction_v2_weights", {
        "cp_ratio": 0.15,
        "sweep_ratio": 0.20,
        "dark_pool_signal": 0.15,
        "institutional_alignment": 0.10,
        "iv_skew": 0.10,
        "flow_momentum": 0.15,
        "oi_changes": 0.15,
    })

    factors: list[dict] = []
    available_weight = 0.0

    # Factor 1: C/P Ratio (always available from yfinance)
    cp_ratio = flow_data.get("cp_ratio", 1.0)
    cp_score = _cp_ratio_to_score(cp_ratio)
    factors.append({
        "name": "C/P Ratio",
        "score": cp_score,
        "weight": base_weights.get("cp_ratio", 0.15),
        "available": True,
        "source": "yfinance",
        "detail": f"C/P {cp_ratio:.2f}",
    })
    available_weight += base_weights.get("cp_ratio", 0.15)

    # Factor 2: Sweep Ratio (UW)
    if flow_alerts:
        sweeps = [a for a in flow_alerts if a.get("type") in ("sweep", "golden_sweep")]
        bull_sweeps = [s for s in sweeps if s.get("sentiment") == "bullish"]
        sweep_score = (len(bull_sweeps) / len(sweeps) * 100) if sweeps else 50
        factors.append({
            "name": "Sweep Ratio",
            "score": round(sweep_score),
            "weight": base_weights.get("sweep_ratio", 0.20),
            "available": True,
            "source": "unusual_whales",
            "detail": f"{len(bull_sweeps)}/{len(sweeps)} bullish sweeps",
        })
        available_weight += base_weights.get("sweep_ratio", 0.20)
    else:
        factors.append({
            "name": "Sweep Ratio",
            "score": 0,
            "weight": base_weights.get("sweep_ratio", 0.20),
            "available": False,
            "source": "unusual_whales",
            "detail": "Requires Unusual Whales",
        })

    # Factor 3: Dark Pool Signal (UW)
    if dark_pool:
        dp_score = _dark_pool_score(dark_pool, flow_data.get("stock_price", 0))
        factors.append({
            "name": "Dark Pool Signal",
            "score": dp_score,
            "weight": base_weights.get("dark_pool_signal", 0.15),
            "available": True,
            "source": "unusual_whales",
            "detail": f"{len(dark_pool)} prints",
        })
        available_weight += base_weights.get("dark_pool_signal", 0.15)
    else:
        factors.append({
            "name": "Dark Pool Signal",
            "score": 0,
            "weight": base_weights.get("dark_pool_signal", 0.15),
            "available": False,
            "source": "unusual_whales",
            "detail": "Requires Unusual Whales",
        })

    # Factor 4: Institutional Alignment (UW)
    if institutional and institutional.get("trades"):
        inst_score = _institutional_score(institutional)
        factors.append({
            "name": "Institutional Alignment",
            "score": inst_score,
            "weight": base_weights.get("institutional_alignment", 0.10),
            "available": True,
            "source": "unusual_whales",
            "detail": f"{len(institutional['trades'])} trades",
        })
        available_weight += base_weights.get("institutional_alignment", 0.10)
    else:
        factors.append({
            "name": "Institutional Alignment",
            "score": 0,
            "weight": base_weights.get("institutional_alignment", 0.10),
            "available": False,
            "source": "unusual_whales",
            "detail": "Requires Unusual Whales",
        })

    # Factor 5: IV Skew (AV)
    if historical_iv and len(historical_iv) > 1:
        iv_score = _iv_skew_score(historical_iv)
        factors.append({
            "name": "IV Skew",
            "score": iv_score,
            "weight": base_weights.get("iv_skew", 0.10),
            "available": True,
            "source": "alpha_vantage",
            "detail": f"IV data: {len(historical_iv)} points",
        })
        available_weight += base_weights.get("iv_skew", 0.10)
    else:
        factors.append({
            "name": "IV Skew",
            "score": 0,
            "weight": base_weights.get("iv_skew", 0.10),
            "available": False,
            "source": "alpha_vantage",
            "detail": "Requires Alpha Vantage",
        })

    # Factor 6: Flow Momentum (yfinance history + UW)
    momentum_score = _flow_momentum_score(flow_data, flow_alerts)
    factors.append({
        "name": "Flow Momentum",
        "score": momentum_score,
        "weight": base_weights.get("flow_momentum", 0.15),
        "available": True,
        "source": "yfinance",
        "detail": "Premium trend",
    })
    available_weight += base_weights.get("flow_momentum", 0.15)

    # Factor 7: OI Changes (yfinance)
    oi_score = _oi_changes_score(flow_data)
    factors.append({
        "name": "OI Changes",
        "score": oi_score,
        "weight": base_weights.get("oi_changes", 0.15),
        "available": True,
        "source": "yfinance",
        "detail": f"PCR: {flow_data.get('oi_analysis', {}).get('pcr_oi', 0):.2f}",
    })
    available_weight += base_weights.get("oi_changes", 0.15)

    # Redistribute weights to available factors
    if available_weight > 0:
        weight_multiplier = 1.0 / available_weight
    else:
        weight_multiplier = 1.0

    weighted_sum = 0.0
    for f in factors:
        if f["available"]:
            adj_weight = f["weight"] * weight_multiplier
            weighted_sum += f["score"] * adj_weight
            f["adjusted_weight"] = round(adj_weight, 3)
        else:
            f["adjusted_weight"] = 0.0

    score = round(min(max(weighted_sum, 0), 100))

    # Determine confidence based on how many factors are available
    available_count = sum(1 for f in factors if f["available"])
    if available_count >= 6:
        confidence = "high"
    elif available_count >= 4:
        confidence = "medium"
    else:
        confidence = "low"

    # Label
    if score >= 80:
        label = "Strong Bullish"
    elif score >= 65:
        label = "Bullish"
    elif score >= 45:
        label = "Neutral"
    elif score >= 30:
        label = "Bearish"
    else:
        label = "Strong Bearish"

    return {
        "score": score,
        "label": label,
        "confidence": confidence,
        "factors": factors,
        "available_factors": available_count,
        "total_factors": len(factors),
    }


# ── IV Analysis ───────────────────────────────────────────────


def analyze_iv(chain_data: dict | None, historical_iv: list[dict] | None, stock_price: float) -> dict | None:
    """Compute IV percentile rank, skew, term structure, crush risk."""
    if not chain_data or not chain_data.get("chains"):
        return None

    chains = chain_data["chains"]

    # Collect current IVs
    all_ivs = []
    call_ivs = []
    put_ivs = []
    near_term_iv = []
    far_term_iv = []
    now = datetime.now()

    sorted_expiries = sorted(chains.keys())
    for exp_str in sorted_expiries:
        data = chains[exp_str]
        try:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d")
            days = max((exp_date - now).days, 0)
        except ValueError:
            days = 30

        for c in data.get("calls", []):
            iv = c.get("impliedVolatility")
            if iv and iv > 0:
                all_ivs.append(iv)
                call_ivs.append(iv)
                if days <= 30:
                    near_term_iv.append(iv)
                else:
                    far_term_iv.append(iv)

        for p in data.get("puts", []):
            iv = p.get("impliedVolatility")
            if iv and iv > 0:
                all_ivs.append(iv)
                put_ivs.append(iv)
                if days <= 30:
                    near_term_iv.append(iv)
                else:
                    far_term_iv.append(iv)

    if not all_ivs:
        return None

    current_iv = sum(all_ivs) / len(all_ivs)

    # IV Percentile Rank (if historical available)
    iv_percentile = None
    if historical_iv and len(historical_iv) > 10:
        hist_vals = [h["avg_iv"] for h in historical_iv if h.get("avg_iv", 0) > 0]
        if hist_vals:
            below = sum(1 for v in hist_vals if v < current_iv)
            iv_percentile = round(below / len(hist_vals) * 100, 1)

    # IV Skew: put IV vs call IV
    avg_call_iv = sum(call_ivs) / len(call_ivs) if call_ivs else 0
    avg_put_iv = sum(put_ivs) / len(put_ivs) if put_ivs else 0
    iv_skew = round(avg_put_iv - avg_call_iv, 4) if avg_call_iv > 0 else 0

    # Term Structure
    avg_near = sum(near_term_iv) / len(near_term_iv) if near_term_iv else 0
    avg_far = sum(far_term_iv) / len(far_term_iv) if far_term_iv else 0
    term_structure = "normal"
    if avg_near > 0 and avg_far > 0:
        if avg_near > avg_far * 1.1:
            term_structure = "inverted"
        elif avg_far > avg_near * 1.1:
            term_structure = "contango"

    # Crush risk: first expiry within 7 days of potential event
    crush_risk = False
    if sorted_expiries:
        try:
            first_exp = datetime.strptime(sorted_expiries[0], "%Y-%m-%d")
            if (first_exp - now).days <= 7 and avg_near > avg_far * 1.2:
                crush_risk = True
        except ValueError:
            pass

    return {
        "current_iv": round(current_iv, 4),
        "iv_percentile": iv_percentile,
        "iv_skew": iv_skew,
        "avg_call_iv": round(avg_call_iv, 4),
        "avg_put_iv": round(avg_put_iv, 4),
        "term_structure": term_structure,
        "near_term_iv": round(avg_near, 4),
        "far_term_iv": round(avg_far, 4),
        "crush_risk": crush_risk,
    }


# ── Advanced Greeks (GEX, DEX, GEX Flip) ─────────────────────


def compute_advanced_greeks(chain_data: dict | None, stock_price: float) -> dict | None:
    """Compute GEX, DEX, GEX flip level, and related metrics."""
    if not chain_data or not chain_data.get("chains") or stock_price <= 0:
        return None

    chains = chain_data["chains"]
    r = 0.05
    now = datetime.now()

    gex_by_strike: dict[float, float] = {}
    total_gex = 0.0
    total_dex = 0.0

    for exp_str, data in chains.items():
        try:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d")
            T = max((exp_date - now).days / 365.0, 1 / 365.0)
        except ValueError:
            continue

        for c in data.get("calls", []):
            strike = c.get("strike")
            oi = c.get("openInterest") or 0
            iv = c.get("impliedVolatility") or 0.3
            if strike and oi > 0 and iv > 0:
                gamma = _bs_gamma(stock_price, strike, T, r, iv)
                delta = _bs_delta(stock_price, strike, T, r, iv, "call")
                # Dealers are short calls -> positive GEX means dealers buy dips
                gex = gamma * oi * 100 * stock_price * stock_price * 0.01
                gex_by_strike[strike] = gex_by_strike.get(strike, 0) + gex
                total_gex += gex
                total_dex += delta * oi * 100 * stock_price

        for p in data.get("puts", []):
            strike = p.get("strike")
            oi = p.get("openInterest") or 0
            iv = p.get("impliedVolatility") or 0.3
            if strike and oi > 0 and iv > 0:
                gamma = _bs_gamma(stock_price, strike, T, r, iv)
                delta = _bs_delta(stock_price, strike, T, r, iv, "put")
                # Dealers are short puts -> negative GEX
                gex = -gamma * oi * 100 * stock_price * stock_price * 0.01
                gex_by_strike[strike] = gex_by_strike.get(strike, 0) + gex
                total_gex += gex
                total_dex += delta * oi * 100 * stock_price

    # GEX flip level: strike where cumulative GEX crosses zero
    gex_flip = None
    if gex_by_strike:
        sorted_strikes = sorted(gex_by_strike.keys())
        cumulative = 0.0
        for i, strike in enumerate(sorted_strikes):
            prev_cum = cumulative
            cumulative += gex_by_strike[strike]
            if prev_cum * cumulative < 0 and i > 0:
                # Linear interpolation
                prev_strike = sorted_strikes[i - 1]
                if abs(cumulative - prev_cum) > 0:
                    gex_flip = round(prev_strike + (strike - prev_strike) * abs(prev_cum) / abs(cumulative - prev_cum), 2)
                break

    # Top GEX strikes for chart
    gex_chart = sorted(
        [{"strike": s, "gex": round(g, 0)} for s, g in gex_by_strike.items()],
        key=lambda x: abs(x["gex"]),
        reverse=True,
    )[:20]

    # GEX regime
    if total_gex > 0:
        gex_regime = "positive"
        gex_description = "Dealers sell rallies, buy dips (mean-reversion)"
    else:
        gex_regime = "negative"
        gex_description = "Dealers amplify moves (momentum)"

    return {
        "total_gex": round(total_gex, 0),
        "total_dex": round(total_dex, 0),
        "gex_flip_level": gex_flip,
        "gex_regime": gex_regime,
        "gex_description": gex_description,
        "gex_by_strike": gex_chart,
    }


# ── Dark Pool Correlation ─────────────────────────────────────


def correlate_dark_pool(
    dark_pool: list[dict] | None,
    flow_alerts: list[dict] | None,
    stock_price: float,
) -> dict | None:
    """Correlate dark pool prints with sweep timing and price."""
    if not dark_pool:
        return None

    total_notional = sum(dp.get("notional", 0) for dp in dark_pool)
    above_spot = sum(1 for dp in dark_pool if dp.get("price", 0) > stock_price)
    below_spot = sum(1 for dp in dark_pool if dp.get("price", 0) < stock_price)

    if above_spot > below_spot * 1.3:
        dp_sentiment = "bullish"
    elif below_spot > above_spot * 1.3:
        dp_sentiment = "bearish"
    else:
        dp_sentiment = "neutral"

    # Average DP price vs spot
    avg_dp_price = (
        sum(dp.get("price", 0) for dp in dark_pool) / len(dark_pool)
        if dark_pool else 0
    )
    price_vs_spot = round(((avg_dp_price / stock_price) - 1) * 100, 2) if stock_price > 0 else 0

    return {
        "total_prints": len(dark_pool),
        "total_notional": round(total_notional, 0),
        "above_spot": above_spot,
        "below_spot": below_spot,
        "dp_sentiment": dp_sentiment,
        "avg_dp_price": round(avg_dp_price, 2),
        "price_vs_spot_pct": price_vs_spot,
    }


# ── Flow Momentum ─────────────────────────────────────────────


def compute_flow_momentum(flow_data: dict, flow_alerts: list[dict] | None) -> dict:
    """Compute flow momentum metrics."""
    # From basic flow data: C/P ratio direction
    cp_ratio = flow_data.get("cp_ratio", 1.0)
    cp_momentum = "accelerating" if cp_ratio > 1.5 else "decelerating" if cp_ratio < 0.7 else "stable"

    # From UW intervals if available
    intraday_trend = None
    if flow_alerts:
        # Simple: compare first half vs second half sentiment
        mid = len(flow_alerts) // 2
        if mid > 0:
            first_bull = sum(1 for a in flow_alerts[:mid] if a.get("sentiment") == "bullish")
            second_bull = sum(1 for a in flow_alerts[mid:] if a.get("sentiment") == "bullish")
            if second_bull > first_bull:
                intraday_trend = "accelerating_bullish"
            elif first_bull > second_bull:
                intraday_trend = "decelerating_bullish"
            else:
                intraday_trend = "stable"

    return {
        "cp_momentum": cp_momentum,
        "intraday_trend": intraday_trend,
    }


# ── Score Helpers ──────────────────────────────────────────────


def _cp_ratio_to_score(cp_ratio: float) -> int:
    """Convert C/P ratio to 0-100 score. >1 = bullish, <1 = bearish."""
    if cp_ratio >= 3.0:
        return 95
    if cp_ratio >= 2.0:
        return 80
    if cp_ratio >= 1.3:
        return 65
    if cp_ratio >= 0.8:
        return 50
    if cp_ratio >= 0.5:
        return 35
    if cp_ratio >= 0.3:
        return 20
    return 5


def _dark_pool_score(dark_pool: list[dict], stock_price: float) -> int:
    """Score dark pool activity 0-100 (50 = neutral)."""
    if not dark_pool or stock_price <= 0:
        return 50
    above = sum(1 for dp in dark_pool if dp.get("price", 0) > stock_price)
    total = len(dark_pool)
    if total == 0:
        return 50
    return round((above / total) * 100)


def _institutional_score(institutional: dict) -> int:
    """Score institutional activity 0-100."""
    trades = institutional.get("trades", [])
    if not trades:
        return 50
    buys = sum(1 for t in trades if "buy" in (t.get("type", "") or "").lower() or "purchase" in (t.get("type", "") or "").lower())
    total = len(trades)
    if total == 0:
        return 50
    return round((buys / total) * 100)


def _iv_skew_score(historical_iv: list[dict]) -> int:
    """Score IV positioning 0-100."""
    if not historical_iv:
        return 50
    current = historical_iv[-1].get("avg_iv", 0)
    avg = sum(h.get("avg_iv", 0) for h in historical_iv) / len(historical_iv)
    if avg <= 0:
        return 50
    ratio = current / avg
    # Low IV = cheap options = bullish setup, high IV = expensive = cautious
    if ratio < 0.8:
        return 70
    if ratio < 1.0:
        return 60
    if ratio < 1.2:
        return 40
    return 30


def _flow_momentum_score(flow_data: dict, flow_alerts: list[dict] | None) -> int:
    """Score flow momentum 0-100."""
    cp = flow_data.get("cp_ratio", 1.0)
    base = _cp_ratio_to_score(cp)
    if flow_alerts:
        recent = flow_alerts[:10]
        bull = sum(1 for a in recent if a.get("sentiment") == "bullish")
        if len(recent) > 0:
            recent_ratio = bull / len(recent)
            return round((base + recent_ratio * 100) / 2)
    return base


def _oi_changes_score(flow_data: dict) -> int:
    """Score OI changes 0-100."""
    oi = flow_data.get("oi_analysis", {})
    pcr = oi.get("pcr_oi", 1.0)
    # Low PCR = more calls = bullish, high PCR = more puts = bearish
    if pcr < 0.5:
        return 80
    if pcr < 0.8:
        return 65
    if pcr < 1.2:
        return 50
    if pcr < 1.5:
        return 35
    return 20


# ── Black-Scholes Helpers ─────────────────────────────────────


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _bs_delta(S: float, K: float, T: float, r: float, sigma: float, opt_type: str) -> float:
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    if opt_type == "call":
        return _norm_cdf(d1)
    return _norm_cdf(d1) - 1.0


def _bs_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return math.exp(-0.5 * d1 ** 2) / (S * sigma * math.sqrt(2 * math.pi * T))
