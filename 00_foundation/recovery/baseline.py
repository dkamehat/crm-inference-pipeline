"""
Baseline detector (spec §5.5): the L0 self_check ⑥ rule, ported verbatim as a
narration-grade comparator — `cell ARPA > q75(all cells) ∧ cell count < median`.

It is intentionally naive (a fixed quantile band, no null calibration). The
payoff test (spec §7.3) shows this baseline fires on low-count noise under a
permutation null while the inference detector does not — demonstrating why L1's
null-calibrated method is a real advance over the L0 rule.
"""

from __future__ import annotations

import pandas as pd


def baseline_flags(won: pd.DataFrame, value_col: str = "Amount",
                   segment_col: str = "Segment", category_col: str = "Category") -> dict:
    """Cells flagged by the L0 rule. Returns the flagged cell ids and their categories."""
    cells = (won.groupby([segment_col, category_col], observed=True)
                .agg(arpa=(value_col, "mean"), cnt=(value_col, "size"))
                .reset_index())
    q75 = cells["arpa"].quantile(0.75)
    med = cells["cnt"].median()
    flagged = cells[(cells["arpa"] > q75) & (cells["cnt"] < med)]
    cell_ids = [f"{row[segment_col]}|{row[category_col]}" for _, row in flagged.iterrows()]
    categories = sorted(set(flagged[category_col].astype(str)))
    return {"cells": cell_ids, "categories": categories}
