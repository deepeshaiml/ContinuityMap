#!/usr/bin/env python3
"""Run deterministic, synthetic-only ContinuityMap evaluation fixtures."""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from continuitymap.ai import heuristic_extract
from continuitymap.graph import simulate, validate_graph
from continuitymap.models import InfrastructureGraph
from continuitymap.reports import checklist_pdf, gaps_pdf, impact_pdf
from pypdf import PdfReader


def main() -> None:
    graph = InfrastructureGraph.model_validate(json.loads((ROOT / "data/infrastructure.json").read_text()))
    extraction_eval = json.loads((ROOT / "data/extraction_eval.json").read_text())
    tp = fp = fn = 0
    for example in extraction_eval["examples"]:
        predicted = {(item["source"], item["dependent"], item["dependency_type"]) for item in heuristic_extract(example["text"], "benchmark.txt", graph)}
        gold = {tuple(item) for item in example["gold"]}
        tp += len(predicted & gold)
        fp += len(predicted - gold)
        fn += len(gold - predicted)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0

    review_eval = json.loads((ROOT / "data/human_review_eval.json").read_text())
    review_correct = sum((case["review_action"] == "verify") == case["expected_official"] for case in review_eval["cases"])

    scenario_results = []
    latencies = []
    exact = 0
    for scenario in graph.scenarios:
        sample = simulate(graph, scenario.disrupted_nodes, scenario.name)
        expected, actual = set(scenario.expected_affected), set(sample.affected_nodes)
        exact += expected == actual
        latencies.append(sample.processing_ms)
        scenario_results.append({"id": scenario.id, "expected": len(expected), "calculated": len(actual), "exact_match": expected == actual, "precision": round(len(expected & actual) / len(actual), 4) if actual else 1, "recall": round(len(expected & actual) / len(expected), 4) if expected else 1, "latency_ms": sample.processing_ms})

    # Run repeated deterministic propagation for latency distribution.
    first = graph.scenarios[0]
    for _ in range(100):
        latencies.append(simulate(graph, first.disrupted_nodes, first.name).processing_ms)
    sorted_latencies = sorted(latencies)

    verified = [edge for edge in graph.edges if edge.verification_status.value == "verified"]
    provenance_missing = [edge.id for edge in verified if not edge.evidence.strip() or not edge.evidence_ref.strip() or not edge.owner.strip() or edge.last_validated is None]
    proposed_in_official = [edge.id for edge in graph.edges if edge.verification_status.value != "verified" and edge.id in {edge_id for result in [simulate(graph, item.disrupted_nodes, item.name) for item in graph.scenarios] for explanation in result.explanations for edge_id in explanation.edge_ids}]
    uncertain_preserved = []
    for scenario in graph.scenarios:
        result = simulate(graph, scenario.disrupted_nodes, scenario.name)
        uncertain_preserved.append({"scenario": scenario.id, "review_nodes": result.uncertain_review_nodes})

    scenario = graph.scenarios[0]
    result = simulate(graph, scenario.disrupted_nodes, scenario.name)
    validation = validate_graph(graph)
    pdfs = {"impact": impact_pdf(graph, result), "gaps": gaps_pdf(graph, validation), "checklist": checklist_pdf(graph, result)}
    required_report_terms = {"impact": ["Disruption impact report", "Declared impact trace"], "gaps": ["Dependency gap report", "Relationships and validation findings"], "checklist": ["Human-reviewed continuity checklist", "Actions for review"]}
    report_completeness = {}
    for name, payload in pdfs.items():
        text = " ".join(page.extract_text() or "" for page in PdfReader(__import__("io").BytesIO(payload)).pages)
        report_completeness[name] = all(term in text for term in required_report_terms[name])

    summary_refs = sorted({edge.evidence_ref for edge in verified if edge.dependent in result.affected_nodes})
    all_known_refs = {edge.evidence_ref for edge in graph.edges}
    summary_evidence_precision = sum(ref in all_known_refs for ref in summary_refs) / len(summary_refs) if summary_refs else 1.0
    report = {
        "title": "ContinuityMap synthetic evaluation report",
        "scope": "Synthetic fixtures only. Metrics measure implementation behavior against fixed fixture labels, not physical failure behavior or performance on customer documents.",
        "graph": {"nodes": len(graph.nodes), "edges": len(graph.edges), "verified_edges": len(verified), "integrity_valid": validation.valid, "integrity_errors": validation.counts["errors"], "integrity_warnings": validation.counts["warnings"]},
        "dependency_extraction": {"tp": tp, "fp": fp, "fn": fn, "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0, "n_sentences": len(extraction_eval["examples"]), "method": "Local deterministic entity/trigger heuristic; LLM path not evaluated."},
        "human_review_workflow": {"cases": len(review_eval["cases"]), "state_transition_correct": review_correct, "accuracy": round(review_correct / len(review_eval["cases"]), 4), "interpretation": "Synthetic workflow-state checks only; not user study or human relationship accuracy."},
        "unsupported_edge_rate": {"verified_edges_missing_required_provenance": len(provenance_missing), "rate": round(len(provenance_missing) / len(verified), 4) if verified else 0, "interpretation": "Metadata completeness proxy, not semantic truth of dependency claims."},
        "scenario_propagation": {"fixtures": scenario_results, "exact_fixture_matches": exact, "fixture_count": len(graph.scenarios), "redundancy_checks": "ANY/ALL behavior asserted in unit tests", "unverified_edge_propagations": len(proposed_in_official)},
        "uncertainty": {"scenario_reviews": uncertain_preserved, "unknown_and_proposed_edges_affect_official_status": False},
        "latency": {"n": len(latencies), "median_ms": round(statistics.median(latencies), 3), "p95_ms": round(sorted_latencies[min(len(sorted_latencies) - 1, int(len(sorted_latencies) * 0.95))], 3), "environment": "Local Python 3.12, NetworkX deterministic fixed-point traversal; latency is informational and hardware-specific."},
        "evidence_summary": {"checked_refs": len(summary_refs), "evidence_ref_validity": round(summary_evidence_precision, 4), "interpretation": "Citation identifiers resolve to graph edges; this does not establish narrative factual correctness."},
        "report_completeness": report_completeness,
        "limitations": ["No damage, flows, capacities, probabilities, thresholds, durations, restoration, or common-cause behavior are simulated.", "Extraction benchmark is a small synthetic set and excludes ambiguous/adversarial language.", "No local LLM was configured for this run.", "All business and infrastructure statements are fictional."],
    }
    target = ROOT / "data" / "evaluation_results.json"
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
