"""
Card loader (L3-GRADING-SPEC §2). The L1 card is consumed as DATA — a persisted
JSON file read into a dict. L3 never imports or re-runs L1 (the card is a black box).
"""

from __future__ import annotations

import json
from pathlib import Path


def load_card(card_path) -> dict:
    """Read a persisted recovery card as a plain dict."""
    return json.loads(Path(card_path).read_text())
