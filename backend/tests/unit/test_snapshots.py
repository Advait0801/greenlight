"""A quote must start and end on a whole word or number of the snapshot."""

from __future__ import annotations

import pytest

from app.rules.snapshots import normalize, text_in_snapshot

SNAPSHOT = normalize("Food may not exceed $35.50 per person, and 1,200 guests is the most for the venue.")


@pytest.mark.parametrize(
    ("quote", "found"),
    [
        ("Food may not exceed $35.50 per person", True),
        ("exceed $35.50", True),
        ("exceed a $3", False),
        # Regression (phase 0 iteration 3, code audit L): a cut at a decimal point or thousands comma.
        ("Food may not exceed $35", False),
        ("and 1", False),
        ("50 per person", False),
        ("200 guests", False),
        ("1,200 guests", True),
    ],
)
def test_quote_boundaries(quote: str, found: bool) -> None:
    assert text_in_snapshot(quote, SNAPSHOT) is found
