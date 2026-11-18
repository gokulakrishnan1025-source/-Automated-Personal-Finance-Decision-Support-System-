"""Budget planning, ranking and overspending alerts."""
from finance_calculations import safe_percentage, validate_amount

# Suggested share of income per category (sums to 80%; the other 20% is the savings target).
DEFAULT_BUDGET_PCT = {"Rent": 25, "Food": 15, "Travel": 7, "Shopping": 7,
                      "Education": 10, "Bills": 8, "Entertainment": 4, "Other": 4}


def plan_budget(income, pct=None):
    """Turn percentage shares into rupee limits."""
    income = validate_amount(income, "Monthly income", allow_zero=False)
    pct = DEFAULT_BUDGET_PCT if pct is None else pct
    return {c: round(income * p / 100, 2) for c, p in pct.items()}


def _make_status_checker(near_ratio):
    """Closure: near_ratio is captured from the enclosing scope."""
    def status(spent, limit):
        if limit <= 0:
            return "No budget" if spent > 0 else "Within"
        if spent > limit:
            return "Over"
        return "Near" if spent >= near_ratio * limit else "Within"
    return status


def check_budget(expenses, budget, near_ratio=0.9):
    """Compare spending with limits. Returns one row (dict) per category."""
    status_of = _make_status_checker(near_ratio)
    rows = []
    for cat in sorted(set(expenses) | set(budget)):
        spent, limit = expenses.get(cat, 0.0), budget.get(cat, 0.0)
        rows.append({"category": cat, "spent": spent, "limit": limit,
                     "difference": round(limit - spent, 2),
                     "status": status_of(spent, limit)})
    return rows


def rank_categories(expenses, top_n=None):
    """Highest-spending categories first (lambda sort key)."""
    ranked = sorted(((c, v) for c, v in expenses.items() if v > 0),
                    key=lambda kv: kv[1], reverse=True)
    return ranked[:top_n] if top_n else ranked


def overspending_alerts(rows):
    """Plain-language alerts, biggest overshoot first."""
    over = sorted((r for r in rows if r["status"] in ("Over", "No budget")),
                  key=lambda r: r["spent"] - r["limit"], reverse=True)
    alerts = [f"{r['category']}: spent {r['spent']:,.0f} vs limit {r['limit']:,.0f} "
              f"(over by {r['spent'] - r['limit']:,.0f})" for r in over]
    alerts += [f"{r['category']}: at {safe_percentage(r['spent'], r['limit']):.0f}% of limit"
               for r in rows if r["status"] == "Near"]
    return alerts


def budget_adherence(rows):
    """Share (0-1) of categories with spending that stayed within their limit."""
    used = [r for r in rows if r["spent"] > 0]
    return 1.0 if not used else sum(r["status"] != "Over" and r["status"] != "No budget"
                                    for r in used) / len(used)