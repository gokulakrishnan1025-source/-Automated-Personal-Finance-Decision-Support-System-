"""Recommendation engine.
IMPORTANT: this is RULE-BASED decision logic, not machine learning. Every item
carries source="Rule-based" and a plain-language reason. Not financial advice."""
from budget_analysis import rank_categories

TARGET_SAVINGS_PCT = 20


def generate_recommendations(summary, rows, *, max_items=6):
    recs = []
    income, total = summary["income"], summary["total_expenses"]

    def add(priority, title, reason):
        recs.append({"priority": priority, "title": title, "reason": reason,
                     "source": "Rule-based"})

    if summary["balance"] < 0:
        add("High", "Expenses exceed income",
            f"You spend {-summary['balance']:,.0f} more than you earn this month. "
            "Cut flexible categories first.")
    elif summary["savings_pct"] < TARGET_SAVINGS_PCT:
        gap = income * TARGET_SAVINGS_PCT / 100 - summary["balance"]
        add("Medium", f"Raise savings to {TARGET_SAVINGS_PCT}%",
            f"You save {summary['savings_pct']:.1f}%. Saving {gap:,.0f} more reaches the target.")
    for r in sorted((r for r in rows if r["status"] == "Over"),
                    key=lambda r: r["spent"] - r["limit"], reverse=True)[:3]:
        add("High", f"Reduce {r['category']} spending",
            f"{r['category']} is {r['spent'] - r['limit']:,.0f} over its {r['limit']:,.0f} limit.")
    ranked = rank_categories(summary["expenses"], 1)
    if ranked and total and ranked[0][1] / total > 0.4:
        add("Medium", f"{ranked[0][0]} dominates your spending",
            f"{ranked[0][0]} is {ranked[0][1] / total * 100:.0f}% of all expenses.")
    if summary["savings_pct"] >= TARGET_SAVINGS_PCT and not any(r["status"] == "Over" for r in rows):
        add("Low", "Build an emergency fund",
            f"Aim for 3 months of expenses (about {3 * total:,.0f}) before taking investment risk.")
    return recs[:max_items]