"""Core financial calculations. Pure Python: no UI code, so everything is testable."""
import math

CURRENCY = "₹"          # module-level (global) constant: variable scope demo
MAX_MONTHS = 480        # recursion safety cap (40 years)


class InputError(ValueError):
    """Raised when a user-supplied value is empty, non-numeric or invalid."""


def validate_amount(value, name="Amount", *, allow_zero=True):
    """Convert value to a non-negative float or raise InputError (keyword-only flag)."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise InputError(f"{name} is required.")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise InputError(f"{name} must be a number.") from None
    if not math.isfinite(number):
        raise InputError(f"{name} must be a finite number.")
    if number < 0:
        raise InputError(f"{name} cannot be negative.")
    if number == 0 and not allow_zero:
        raise InputError(f"{name} must be greater than zero.")
    return round(number, 2)


def safe_percentage(part, whole, default=0.0):
    """part/whole*100 with division-by-zero protection (default argument)."""
    return round(part / whole * 100, 2) if whole else default


def calculate_summary(income, expenses, currency=CURRENCY):
    """Return totals for one month. income: number; expenses: {category: amount}."""
    income = validate_amount(income, "Monthly income", allow_zero=False)
    clean = {c: validate_amount(v, f"{c} expense") for c, v in expenses.items()}
    total = round(sum(clean.values()), 2)
    balance = round(income - total, 2)
    return {
        "income": income, "expenses": clean, "total_expenses": total,
        "balance": balance,
        "savings_pct": safe_percentage(balance, income),
        "expense_pct": safe_percentage(total, income),
        "currency": currency,
    }


def months_to_goal(target, saved, monthly, annual_rate=0.0, _months=0):
    """Recursively count months until saved >= target (monthly deposit + optional
    interest). Returns None if the goal can never be reached. _months is internal."""
    if saved >= target:
        return _months
    if _months >= MAX_MONTHS or (monthly <= 0 and (saved <= 0 or annual_rate <= 0)):
        return None
    grown = saved * (1 + annual_rate / 1200) + monthly
    return months_to_goal(target, grown, monthly, annual_rate, _months + 1)


def goal_progress(target, saved):
    """Percent of goal completed, capped at 100."""
    return min(100.0, safe_percentage(saved, target))