"""Retirement projection — deterministic path + Monte Carlo probability of success.

Pure math, no market data. Returns are modeled as normal annual draws;
inflation is applied so all outputs are in today's dollars.
"""

import random


def project(current_age: int, retire_age: int, current_assets: float,
            monthly_contribution: float, expected_return_pct: float = 7.0,
            inflation_pct: float = 2.5, monthly_spending: float | None = None,
            simulations: int = 1000) -> dict:
    years = max(0, retire_age - current_age)
    real_return = (1 + expected_return_pct / 100) / (1 + inflation_pct / 100) - 1
    annual_contribution = monthly_contribution * 12

    # Deterministic path in today's dollars
    path = []
    balance = float(current_assets)
    for year in range(years + 1):
        path.append({"age": current_age + year, "balance": round(balance)})
        balance = balance * (1 + real_return) + annual_contribution

    projected = path[-1]["balance"] if path else current_assets
    safe_monthly = projected * 0.04 / 12  # 4% rule, today's dollars

    # Monte Carlo: how often does the plan cover spending through age 90?
    success_prob = None
    if monthly_spending and monthly_spending > 0:
        volatility = 0.15
        retirement_years = max(1, 90 - retire_age)
        annual_spending = monthly_spending * 12
        rng = random.Random(42)  # deterministic result for identical inputs
        successes = 0
        for _ in range(simulations):
            b = float(current_assets)
            for _ in range(years):
                b = b * (1 + rng.gauss(real_return, volatility)) + annual_contribution
            ok = True
            for _ in range(retirement_years):
                b = b * (1 + rng.gauss(real_return, volatility)) - annual_spending
                if b <= 0:
                    ok = False
                    break
            if ok:
                successes += 1
        success_prob = round(successes / simulations * 100, 1)

    if success_prob is None:
        readiness = None
    elif success_prob >= 85:
        readiness = "You're on track. Keep contributing and stay the course."
    elif success_prob >= 60:
        readiness = "You're close, but there's real risk of falling short. Contributing a bit " \
                    "more each month, or retiring slightly later, would firm this up."
    else:
        readiness = "The current plan likely falls short. The biggest levers: contribute more " \
                    "monthly, plan for lower spending, or retire a few years later."

    return {
        "years_to_retirement": years,
        "projected_at_retirement": round(projected),
        "safe_monthly_withdrawal": round(safe_monthly),
        "success_probability": success_prob,
        "readiness": readiness,
        "path": path[:: max(1, len(path) // 20)],  # ≤ ~20 points for charting
        "assumptions": {
            "expected_return_pct": expected_return_pct,
            "inflation_pct": inflation_pct,
            "note": "All amounts are in today's dollars. The 4% rule estimates sustainable "
                    "spending; the probability runs 1,000 simulated market histories through age 90.",
        },
    }
