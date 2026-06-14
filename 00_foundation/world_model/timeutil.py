"""Small, dependency-free date helpers shared across the generator."""

from __future__ import annotations

import datetime


def month_index_to_date(start_y: int, start_m: int, idx: int) -> str:
    """First-of-month ISO date `idx` months after (start_y, start_m)."""
    m = start_m - 1 + idx
    y = start_y + m // 12
    mo = m % 12 + 1
    return f"{y:04d}-{mo:02d}-01"


def date_minus(y: int, m: int, days_before: int) -> str:
    """ISO date that is `days_before` days before the first of (y, m)."""
    d = datetime.date(y, m, 1) - datetime.timedelta(days=days_before)
    return d.isoformat()


def month_index_minus_days(start_y: int, start_m: int, idx: int, days: int) -> str:
    """First-of-month at `idx`, pulled back by `days` (used for close-optimism)."""
    base = month_index_to_date(start_y, start_m, idx)
    yy, mm, _ = base.split("-")
    d = datetime.date(int(yy), int(mm), 1) - datetime.timedelta(days=days)
    return d.isoformat()


def add_days(iso_date: str, days: int) -> str:
    """ISO date `days` after `iso_date` (used for day-level recorded close timing)."""
    y, m, d = (int(x) for x in iso_date.split("-"))
    return (datetime.date(y, m, d) + datetime.timedelta(days=days)).isoformat()
