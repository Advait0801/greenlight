"""Phase 0, iteration 4 (break): scripts/seed_demo.py loads the demo club without checking it.

Every other data file (rules, manifest, calendar, test sets) is read with strict JSON (no duplicate
keys) and validated with plain-language errors. The demo club, which is what judges see in the
demo, is read with json.loads and inserted as is: a duplicated key silently changes a figure, and a
bad date or a negative amount ends in a raw SQLAlchemy traceback.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from app.config import REPO_ROOT

DEMO = REPO_ROOT / "data" / "demo" / "club.json"


def _seed(file: Path, db: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "seed_demo.py"), "--file", str(file)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=120,
        env={**os.environ, "DATABASE_URL": f"sqlite:///{db}"},
    )


def test_demo_file_with_a_duplicated_key_is_refused(tmp_path: Path) -> None:
    """`"estimated_cost_cents": 707000, "estimated_cost_cents": 7` seeds Culture night at 7 cents."""
    text = DEMO.read_text(encoding="utf-8")
    assert '"estimated_cost_cents": 707000' in text
    bad = tmp_path / "club.json"
    bad.write_text(text.replace('"estimated_cost_cents": 707000', '"estimated_cost_cents": 707000, "estimated_cost_cents": 7', 1), encoding="utf-8")
    result = _seed(bad, tmp_path / "demo.db")
    assert result.returncode != 0, result.stdout
    assert "Traceback" not in result.stderr, result.stderr[-800:]


def test_demo_event_that_ends_before_it_starts_gives_a_clear_error(tmp_path: Path) -> None:
    data = json.loads(DEMO.read_text(encoding="utf-8"))
    retreat = next(event for event in data["events"] if event.get("end_date"))
    retreat["end_date"] = "2027-02-20"  # starts 2027-02-26
    bad = tmp_path / "club.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    result = _seed(bad, tmp_path / "demo.db")
    assert result.returncode != 0
    assert "Traceback" not in result.stderr, result.stderr[-800:]
    assert retreat["name"] in result.stderr or "end_date" in result.stderr, result.stderr[-800:]
