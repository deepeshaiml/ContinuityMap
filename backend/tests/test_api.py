from __future__ import annotations

import importlib
import json
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
TEMP_DB = Path(tempfile.gettempdir()) / f"continuitymap-test-{os.getpid()}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEMP_DB.as_posix()}"

app = importlib.import_module("continuitymap.main").app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        fixture_graph = (ROOT / "data" / "infrastructure.json").read_text()
        reset = test_client.put(
            "/api/graph/import",
            content=fixture_graph,
            headers={"Content-Type": "application/json"},
        )
        assert reset.status_code == 200
        yield test_client


def test_health_graph_and_validation(client):
    assert client.get("/api/health").json()["synthetic_only"] is True
    response = client.get("/api/graph")
    assert response.status_code == 200
    assert len(response.json()["graph"]["nodes"]) == 43
    assert response.json()["validation"]["valid"] is True


def test_scenario_api_matches_fixed_fixture(client):
    response = client.post("/api/scenarios/run", json={"scenario_id": "substation-alpha-outage"})
    assert response.status_code == 200
    assert response.json()["evaluation"]["exact_match"] is True
    assert len(response.json()["affected_nodes"]) == 17


def test_ai_assessment_is_evidence_linked_and_does_not_mutate_status(client):
    response = client.post(
        "/api/assistant/assessment", json={"scenario_id": "substation-alpha-outage"}
    )
    assert response.status_code == 200
    assessment = response.json()
    assert assessment["state_changed"] is False
    assert assessment["affected_services"]
    assert assessment["evidence_refs"]
    assert "verified dependencies" in assessment["caveat"]


def test_document_upload_creates_proposals_only(client):
    fixture = (ROOT / "data" / "extraction_eval.txt").read_text()
    response = client.post(
        "/api/documents/extract",
        files={"file": ("fictional-eval.txt", fixture, "text/plain")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "heuristic_review_only"
    assert len(payload["proposals"]) == 5
    assert all(item["verification_status"] == "proposed" for item in payload["proposals"])
    scenario = client.post(
        "/api/scenarios/run", json={"scenario_id": "substation-alpha-outage"}
    ).json()
    assert scenario["evaluation"]["exact_match"] is True


def test_human_verification_changes_official_scenario_graph(client):
    graph = client.get("/api/graph").json()["graph"]
    edge = next(item for item in graph["edges"] if item["verification_status"] == "proposed")
    edge["verification_status"] = "verified"
    edge["owner"] = "Records service owner — approved in exercise"
    edge["last_validated"] = "2026-10-26"
    response = client.put(f"/api/edges/{edge['id']}", json=edge)
    assert response.status_code == 200
    assert response.json()["edge"]["verification_status"] == "verified"
    scenario = client.post(
        "/api/scenarios/run", json={"scenario_id": "substation-alpha-outage"}
    ).json()
    assert "records-archive" in scenario["affected_nodes"]


def test_human_rejection_keeps_relationship_out_of_scenario_status(client):
    graph = client.get("/api/graph").json()["graph"]
    edge = next(item for item in graph["edges"] if item["verification_status"] == "proposed")
    edge["verification_status"] = "rejected"
    edge["last_validated"] = None
    response = client.put(f"/api/edges/{edge['id']}", json=edge)
    assert response.status_code == 200
    assert response.json()["edge"]["verification_status"] == "rejected"
    scenario = client.post(
        "/api/scenarios/run", json={"scenario_id": "substation-alpha-outage"}
    ).json()
    assert "records-archive" not in scenario["affected_nodes"]


def test_report_endpoints_return_pdf(client):
    paths = [
        "/api/reports/impact/substation-alpha-outage.pdf",
        "/api/reports/dependency-gaps.pdf",
        "/api/reports/checklist/substation-alpha-outage.pdf",
    ]
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")


def test_nonfictional_import_is_rejected(client):
    graph = json.loads((ROOT / "data" / "infrastructure.json").read_text())
    graph["nodes"][0]["fictional"] = False
    response = client.put("/api/graph/import", json=graph)
    assert response.status_code == 400
