"""Expense forecasting with a simple linear-trend (least-squares) model."""
import numpy as np


def predict_next(history):
    """history: oldest-to-newest monthly totals. Returns (value, method).
    With <3 months the average is used because a trend line would be unreliable."""
    values = [float(v) for v in history]
    if not values:
        raise ValueError("Add at least one monthly record to forecast.")
    if len(values) < 3:
        return round(sum(values) / len(values), 2), "Average (fewer than 3 months)"
    slope, intercept = np.polyfit(range(len(values)), values, 1)
    return round(float(max(0.0, slope * len(values) + intercept)), 2), "Linear trend (least squares)"