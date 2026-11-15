"""The scripts listed in scripts/README.md run and fail loudly on bad input."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from app.config import REPO_ROOT

SCRIPTS = REPO_ROOT / "scripts"


def run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=120,
        env={**os.environ, **(env or {})},
    )


def test_validate_rules_passes_on_the_repository() -> None:
    result = run(str(SCRIPTS / "validate_rules.py"))
    assert result.returncode == 0, result.stderr
    assert "matches its snapshot text exactly" in result.stdout
    assert result.stdout.strip().endswith("OK")


def test_validate_rules_fails_on_a_broken_table(rules_copy: Path) -> None:
    path = rules_copy / "events.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["rules"][3]["source_text"] = "This sentence is not in any snapshot at all."
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(str(SCRIPTS / "validate_rules.py"), "--rules-dir", str(rules_copy))
    assert result.returncode == 1
    assert "not in the snapshot" in result.stderr


def test_validate_rules_fails_when_calendar_and_rule_disagree(rules_copy: Path) -> None:
    path = rules_copy / "calendar.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["verified"] = "read"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(str(SCRIPTS / "validate_rules.py"), "--rules-dir", str(rules_copy))
    assert result.returncode == 1
    assert "must agree" in result.stderr


def test_run_eval_validates_every_set() -> None:
    result = run(str(SCRIPTS / "run_eval.py"))
    assert result.returncode == 0, result.stderr
    for name in ("events", "budgets", "constitutions", "year_plans"):
        assert name in result.stdout
    rows = json.loads(run(str(SCRIPTS / "run_eval.py"), "--json").stdout)
    assert {row["set"]: row["cases"] for row in rows} == {"events": 30, "budgets": 20, "constitutions": 10, "year_plans": 2}


def test_run_eval_rejects_unknown_set() -> None:
    result = run(str(SCRIPTS / "run_eval.py"), "nonsense")
    assert result.returncode == 2


def test_seed_demo_is_repeatable(tmp_path: Path) -> None:
    db = tmp_path / "demo.db"
    env = {"DATABASE_URL": f"sqlite:///{db}"}
    for _ in range(2):
        result = run(str(SCRIPTS / "seed_demo.py"), env=env)
        assert result.returncode == 0, result.stderr
    from sqlalchemy import create_engine, text

    engine = create_engine(f"sqlite:///{db}")
    with engine.connect() as connection:
        assert connection.execute(text("select count(*) from clubs")).scalar() == 1
        assert connection.execute(text("select count(*) from events")).scalar() == 5
        assert connection.execute(text("select count(*) from users")).scalar() == 2
    engine.dispose()


def test_fetch_sources_rejects_unknown_ids_without_network() -> None:
    result = run(str(SCRIPTS / "fetch_sources.py"), "no-such-source")
    assert result.returncode == 2
    assert "Unknown source id" in result.stderr


def test_validate_rules_fails_when_business_day_rule_and_calendar_disagree(rules_copy: Path) -> None:
    path = rules_copy / "calendar.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["business_days"]["verified"] = "read"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run(str(SCRIPTS / "validate_rules.py"), "--rules-dir", str(rules_copy))
    assert result.returncode == 1
    assert "usc-business-days-definition" in result.stderr


def test_seed_demo_and_app_share_one_database_file(tmp_path: Path) -> None:
    """Regression (phase 0 iteration 1, M2): a relative DATABASE_URL means backend/<file> for everyone."""
    from app.config import BACKEND_DIR, Settings

    name = f"seed-check-{tmp_path.name}.db"
    target = BACKEND_DIR / name
    try:
        result = run(str(SCRIPTS / "seed_demo.py"), env={"DATABASE_URL": f"sqlite:///./{name}"})
        assert result.returncode == 0, result.stderr
        assert target.is_file()
        assert Settings(_env_file=None, database_url=f"sqlite:///./{name}").database_url == f"sqlite:///{target}"  # type: ignore[call-arg]
    finally:
        target.unlink(missing_ok=True)


def test_seed_demo_never_deletes_a_real_club_with_the_same_name(tmp_path: Path) -> None:
    """Regression (phase 0 iteration 2, L12)."""
    from sqlalchemy import create_engine, text

    from app.db import init_db

    db = tmp_path / "shared.db"
    engine = create_engine(f"sqlite:///{db}")
    init_db(engine)
    demo_name = json.loads((REPO_ROOT / "data" / "demo" / "club.json").read_text())["club"]["name"]
    with engine.begin() as connection:
        connection.execute(text("insert into clubs (name, level, created_at, updated_at) values (:n, 'undergraduate', current_timestamp, current_timestamp)"), {"n": demo_name})
        connection.execute(text("insert into users (email, display_name, role, club_id, created_at, updated_at) values ('real@usc.edu', 'Real Officer', 'officer', 1, current_timestamp, current_timestamp)"))
    engine.dispose()
    result = run(str(SCRIPTS / "seed_demo.py"), env={"DATABASE_URL": f"sqlite:///{db}"})
    assert result.returncode != 0
    assert "refusing to replace it" in result.stderr
    engine = create_engine(f"sqlite:///{db}")
    with engine.connect() as connection:
        assert connection.execute(text("select count(*) from users where email = 'real@usc.edu'")).scalar() == 1
    engine.dispose()
