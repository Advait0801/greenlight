"""The deployed site: one address serves the frontend and the API under /api."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.site import create_site


@pytest.fixture()
def site(tmp_path: Path) -> TestClient:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>Greenlight</title><div id=root></div>")
    (dist / "assets" / "app.js").write_text("console.log('ok')")
    return TestClient(create_site(dist))


def test_api_is_served_under_api(site: TestClient) -> None:
    with site:
        response = site.get("/api/health")
        assert response.status_code == 200
        assert response.json()["rules"]["loaded"] is True


def test_page_addresses_load_the_single_page_app(site: TestClient) -> None:
    with site:
        for path in ("/", "/money/check", "/usg"):
            response = site.get(path)
            assert response.status_code == 200 and "<title>Greenlight" in response.text
        assert site.get("/assets/app.js").text == "console.log('ok')"


def test_unknown_api_route_is_a_json_404_not_the_page(site: TestClient) -> None:
    with site:
        response = site.get("/api/no-such-route")
        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/json")


def test_missing_build_is_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="npm run build"):
        create_site(tmp_path / "nothing")
