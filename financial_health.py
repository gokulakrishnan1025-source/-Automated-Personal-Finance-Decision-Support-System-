"""Financial health score (0-100) from transparent, rule-based components."""

LABELS = [(80, "Excellent"), (60, "Good"), (40, "Fair"), (0, "Needs attention")]


def classify(score):
    """Map a numeric score to a label."""
    return next(label for floor, label in LABELS if score >= floor)


def health_score(savings_pct, adherence, *, expense_pct):
    """50 pts savings rate (20% = full marks), 30 pts budget adherence,
    20 pts expense control (full at <=50% of income, zero at 100%).
    Returns (score, label, components)."""
    savings = 50 * min(max(savings_pct, 0) / 20, 1)
    budget = 30 * adherence
    control = 20 if expense_pct <= 50 else max(0.0, 20 * (100 - expense_pct) / 50)
    score = round(savings + budget + control, 1)
    return score, classify(score), {"Savings rate (50)": round(savings, 1),
                                    "Budget adherence (30)": round(budget, 1),
                                    "Expense control (20)": round(control, 1)}