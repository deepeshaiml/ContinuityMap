from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from continuitymap.graph import simulate, validate_graph
from continuitymap.models import Assumption, InfrastructureGraph

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def demo_graph():
    return InfrastructureGraph.model_validate(
        json.loads((ROOT / "data" / "infrastructure.json").read_text())
    )


def tiny_graph(nodes, edges, unknown=None):
    return InfrastructureGraph.model_validate(
        {
            "dataset_id": "toy",
            "title": "Toy network",
            "synthetic_notice": "Synthetic test fixture",
            "nodes": [
                {
                    "id": node,
                    "name": node,
                    "category": "service",
                    "sector": "test",
                    "description": "Toy node",
                }
                for node in nodes
            ],
            "edges": [
                {
                    "id": f"e{i}",
                    "source": source,
                    "dependent": target,
                    "dependency_type": "power",
                    "evidence": f"Toy evidence {source} supplies {target}.",
                    "evidence_ref": f"toy#{i}",
                    "verification_status": status,
                    "owner": "Test owner",
                    "conditions": [],
                    "assumptions": [],
                    "last_validated": date(2026, 1, 1) if status == "verified" else None,
                    "group_id": group,
                    "group_mode": mode,
                }
                for i, (source, target, group, mode, status) in enumerate(edges, 1)
            ],
            "unknown_relationships": unknown or [],
            "scenarios": [],
            "metadata": {},
        }
    )


def test_demo_fixture_integrity_and_size(demo_graph):
    result = validate_graph(demo_graph)
    assert result.valid
    assert len(demo_graph.nodes) == 43
    assert len(demo_graph.nodes) >= 30
    assert len(demo_graph.nodes) <= 60
    assert result.counts["verified_edges"] >= 70
    assert any(edge.verification_status.value == "proposed" for edge in demo_graph.edges)
    assert len(demo_graph.unknown_relationships) >= 1
    assert all(
        item.verification_status == "unknown" and item.evidence and item.evidence_ref
        for item in demo_graph.unknown_relationships
    )


@pytest.mark.parametrize(
    "scenario_id",
    ["substation-alpha-outage", "water-pumping-backup-loss", "regional-communications-outage"],
)
def test_fixed_scenarios_match_hand_checked_expected_sets(demo_graph, scenario_id):
    scenario = next(item for item in demo_graph.scenarios if item.id == scenario_id)
    result = simulate(demo_graph, scenario.disrupted_nodes, scenario.name)
    assert set(result.affected_nodes) == set(scenario.expected_affected)
    assert result.evaluation == {}
    assert "does not model physical damage" in result.caveat.lower()


def test_any_group_does_not_infer_failure_but_flags_backup_review(demo_graph):
    result = simulate(demo_graph, ["grid-alpha"], "Alpha only")
    assert "water-treatment" not in result.affected_nodes
    assert "water-treatment" in result.backup_review_nodes
    assert "backup capacity" in result.caveat.lower()


def test_all_group_fails_if_a_required_supplier_is_disrupted():
    graph = tiny_graph(["supply", "service"], [("supply", "service", "power", "ALL", "verified")])
    result = simulate(graph, ["supply"])
    assert result.affected_nodes == ["service", "supply"]


def test_any_group_requires_all_alternatives_to_be_lost():
    graph = tiny_graph(
        ["a", "b", "service"],
        [
            ("a", "service", "power", "ANY", "verified"),
            ("b", "service", "power", "ANY", "verified"),
        ],
    )
    assert "service" not in simulate(graph, ["a"]).affected_nodes
    assert "service" in simulate(graph, ["a", "b"]).affected_nodes


def test_overdue_review_date_warns_without_automatically_changing_verified_status():
    graph = tiny_graph(["supplier", "service"], [("supplier", "service", "power", "ALL", "verified")])
    graph.edges[0].review_due_date = date(2000, 1, 1)

    validation = validate_graph(graph)
    overdue = next(issue for issue in validation.issues if issue.code == "overdue_verified_relationship")
    assert overdue.object_id == "e1"
    assert "remains in scenario calculations" in overdue.message
    assert graph.edges[0].verification_status.value == "verified"
    assert simulate(graph, ["supplier"]).affected_nodes == ["service", "supplier"]


def test_unverified_edges_add_review_flags_but_do_not_propagate():
    graph = tiny_graph(
        ["outage", "possible-impact"],
        [("outage", "possible-impact", "draft", "ANY", "proposed")],
        [
            {
                "id": "u1",
                "source": "outage",
                "dependent": "possible-impact",
                "dependency_type": "power",
                "question": "Is this true?",
                "evidence": "Synthetic source question asks whether the relationship exists.",
                "verification_status": "unknown",
                "owner": "Owner",
                "evidence_ref": "plan#2",
                "conditions": [],
                "assumptions": [],
                "last_validated": None,
            }
        ],
    )
    result = simulate(graph, ["outage"])
    assert result.affected_nodes == ["outage"]
    assert result.uncertain_review_nodes == ["possible-impact"]
    explanation = next(item for item in result.explanations if item.node_id == "possible-impact")
    assert explanation.status == "unaffected_review"


def test_cycles_are_reported_and_fixed_point_propagation_terminates():
    graph = tiny_graph(
        ["seed", "a", "b", "island"],
        [
            ("seed", "a", "seed-a", "ALL", "verified"),
            ("a", "b", "a-b", "ALL", "verified"),
            ("b", "a", "b-a", "ALL", "verified"),
        ],
    )
    validation = validate_graph(graph)
    assert any(issue.code == "dependency_cycle" for issue in validation.issues)
    result = simulate(graph, ["seed"])
    assert set(result.affected_nodes) == {"seed", "a", "b"}
    assert "island" in result.unaffected_nodes


def test_missing_node_references_are_reported():
    graph = tiny_graph(
        ["dependent"], [("missing-supplier", "dependent", "power", "ALL", "verified")]
    )
    validation = validate_graph(graph)
    assert not validation.valid
    assert any(issue.code == "missing_source" for issue in validation.issues)


def test_duplicate_unknown_relationship_ids_are_reported(demo_graph):
    graph = demo_graph.model_copy(deep=True)
    graph.unknown_relationships.append(graph.unknown_relationships[0].model_copy(deep=True))
    result = validate_graph(graph)
    assert any(issue.code == "duplicate_unknown_id" for issue in result.issues)


def test_duplicate_edge_ids_are_reported(demo_graph):
    graph = demo_graph.model_copy(deep=True)
    graph.edges.append(graph.edges[0].model_copy(deep=True))
    result = validate_graph(graph)
    assert any(issue.code == "duplicate_edge_id" for issue in result.issues)


def test_missing_unknown_relationship_endpoints_are_reported(demo_graph):
    graph = demo_graph.model_copy(deep=True)
    graph.unknown_relationships[0].source = "missing-provider"
    result = validate_graph(graph)
    assert any(issue.code == "missing_unknown_endpoint" for issue in result.issues)


def test_conflicting_statuses_and_unsupported_assumptions_are_visible():
    graph = tiny_graph(
        ["a", "b"],
        [
            ("a", "b", "same", "ALL", "verified"),
            ("a", "b", "same", "ALL", "proposed"),
        ],
    )
    graph.edges[0].assumptions = [
        Assumption(text="unverified backup response", support_status="unverified")
    ]
    validation = validate_graph(graph)
    assert any(issue.code == "contradictory_relationship" for issue in validation.issues)
    assert any(issue.code == "unsupported_assumption" for issue in validation.issues)


def test_invalid_dependency_type_rejected_by_schema():
    with pytest.raises(ValidationError):
        raw = {
            "dataset_id": "bad",
            "title": "bad",
            "synthetic_notice": "synthetic",
            "nodes": [
                {
                    "id": key,
                    "name": key,
                    "category": "service",
                    "sector": "test",
                    "description": "test",
                }
                for key in ["a", "b"]
            ],
            "edges": [
                {
                    "id": "e",
                    "source": "a",
                    "dependent": "b",
                    "dependency_type": "gravity",
                    "evidence": "x",
                    "evidence_ref": "x",
                    "verification_status": "verified",
                    "owner": "x",
                    "group_id": "g",
                    "group_mode": "ALL",
                }
            ],
            "unknown_relationships": [],
            "scenarios": [],
        }
        InfrastructureGraph.model_validate(raw)


def test_simultaneous_disruptions_and_unknown_seed_rejection():
    graph = tiny_graph(
        ["a", "b", "service"],
        [("a", "service", "one", "ALL", "verified"), ("b", "service", "two", "ALL", "verified")],
    )
    assert "service" in simulate(graph, ["a", "b"]).affected_nodes
    with pytest.raises(ValueError, match="Unknown disrupted"):
        simulate(graph, ["not-in-graph"])


def test_scenario_results_are_reproducible_and_have_latency(demo_graph):
    scenario = next(item for item in demo_graph.scenarios if item.id == "substation-alpha-outage")
    first = simulate(demo_graph, scenario.disrupted_nodes)
    second = simulate(demo_graph, scenario.disrupted_nodes)
    assert first.affected_nodes == second.affected_nodes
    assert first.processing_ms >= 0
    assert first.processing_ms < 1000
