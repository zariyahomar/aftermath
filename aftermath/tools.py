from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Literal


def compute_payoff(
    remaining_balance: float,
    installment: float,
    extra_per_period: float = 0.0,
) -> dict:
    if remaining_balance <= 0:
        return {"periods": 0, "total_paid": 0.0, "schedule_head": []}
    payment = max(installment + extra_per_period, 0.01)
    periods = 0
    balance = remaining_balance
    total = 0.0
    head: list[float] = []
    while balance > 0.009 and periods < 120:
        pay = min(payment, balance)
        balance = round(balance - pay, 2)
        total = round(total + pay, 2)
        periods += 1
        if len(head) < 6:
            head.append(pay)
    return {"periods": periods, "total_paid": total, "schedule_head": head}


def stacking_risk(window_dues: float, available_cash: float) -> dict:
    if available_cash <= 0:
        utilization = 9.99 if window_dues > 0 else 0.0
    else:
        utilization = round(window_dues / available_cash, 3)
    level: Literal["low", "medium", "high", "critical"]
    if utilization > 1.0:
        level = "critical"
    elif utilization >= 0.8:
        level = "high"
    elif utilization >= 0.4:
        level = "medium"
    else:
        level = "low"
    return {
        "window_dues": round(window_dues, 2),
        "available_cash": round(available_cash, 2),
        "utilization": utilization,
        "level": level,
    }


def dues_in_window(next_due: date, today: date | None = None, days: int = 7) -> bool:
    today = today or date.today()
    return today <= next_due <= today + timedelta(days=days)


def ceil_periods(remaining_balance: float, installment: float) -> int:
    if installment <= 0:
        return 0
    return int(math.ceil(remaining_balance / installment))
