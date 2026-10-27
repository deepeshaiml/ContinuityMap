import json
from pathlib import Path

from continuitymap.ai import heuristic_extract
from continuitymap.models import InfrastructureGraph

ROOT = Path(__file__).resolve().parents[2]


def test_synthetic_extraction_fixture_precision_and_recall():
    graph = InfrastructureGraph.model_validate(
        json.loads((ROOT / "data" / "infrastructure.json").read_text())
    )
    fixture = json.loads((ROOT / "data" / "extraction_eval.json").read_text())
    true_positive = false_positive = false_negative = 0
    for example in fixture["examples"]:
        predicted = {
            (item["source"], item["dependent"], item["dependency_type"])
            for item in heuristic_extract(example["text"], "eval.txt", graph)
        }
        gold = {tuple(item) for item in example["gold"]}
        true_positive += len(predicted & gold)
        false_positive += len(predicted - gold)
        false_negative += len(gold - predicted)
    assert (true_positive, false_positive, false_negative) == (5, 0, 0)


def test_contradictory_continuity_statements_are_not_treated_as_dependencies():
    graph = InfrastructureGraph.model_validate(
        json.loads((ROOT / "data" / "infrastructure.json").read_text())
    )
    text = (ROOT / "data" / "fictional_continuity_pack.md").read_text()
    proposals = heuristic_extract(text, "fictional_continuity_pack.md", graph)
    assert not any(
        item["dependent"] == "clinic-east" and item["dependency_type"] == "power"
        for item in proposals
    )
