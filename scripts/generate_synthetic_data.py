#!/usr/bin/env python3
"""Rebuild the entirely fictional ContinuityMap demonstration network."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from continuitymap.graph import simulate
from continuitymap.models import InfrastructureGraph


EXPECTED_AFFECTED = {
    "substation-alpha-outage": ["city-data-center", "clinic-east", "clinic-west", "emergency-portal", "fleet-dispatch", "grid-alpha", "health-records", "hospital-central", "hospital-east", "payment-service", "rail-signals", "recovery-crew", "road-signals", "telecom-east", "transit-control", "water-control", "water-quality-lab"],
    "water-pumping-backup-loss": ["booster-east", "city-data-center", "clinic-east", "clinic-west", "emergency-portal", "fleet-dispatch", "gen-water", "grid-alpha", "health-records", "hospital-central", "hospital-east", "payment-service", "rail-signals", "recovery-crew", "road-signals", "shelter-east", "telecom-east", "transit-control", "water-control", "water-quality-lab"],
    "regional-communications-outage": ["emergency-portal", "fiber-ring", "municipal-hotline", "payment-service", "telecom-core", "telecom-east", "transit-control", "water-control", "water-quality-lab"],
}


RAW_NODES = [
    ("grid-alpha", "Northbank Substation Alpha", "facility", "electricity", "Primary fictional distribution source; no real location."),
    ("grid-beta", "Southbank Substation Beta", "facility", "electricity", "Independent fictional distribution source."),
    ("solar-microgrid", "Civic Solar Microgrid", "facility", "electricity", "Islandable demonstration microgrid."),
    ("gen-water", "Water Backup Generator", "recovery_resource", "electricity", "Portable fictional standby unit for water operations."),
    ("gen-hospital", "Hospital Generator Set", "recovery_resource", "electricity", "Fictional hospital standby generator."),
    ("gen-telecom", "Exchange Generator Set", "recovery_resource", "electricity", "Fictional communications standby generator."),
    ("mobile-generator", "Mobile Generator Pool", "recovery_resource", "electricity", "Shared fictional mobile generation resource."),
    ("fuel-depot", "Civic Emergency Fuel Store", "facility", "recovery", "Fictional fuel inventory; no quantities are modeled."),
    ("water-treatment", "Northbank Water Treatment", "facility", "water", "Fictional treatment service."),
    ("booster-east", "East Water Booster Station", "facility", "water", "Fictional pumping service."),
    ("booster-west", "West Water Booster Station", "facility", "water", "Fictional pumping service."),
    ("reservoir-east", "East Reservoir Service", "service", "water", "Fictional distribution buffer; capacity unknown."),
    ("water-control", "Water Operations Control", "service", "water", "Fictional supervisory service."),
    ("water-quality-lab", "Water Quality Laboratory", "service", "water", "Fictional testing service."),
    ("telecom-core", "Central Telecom Exchange", "facility", "telecommunications", "Fictional central communications exchange."),
    ("telecom-east", "East Telecom Exchange", "facility", "telecommunications", "Fictional regional exchange."),
    ("fiber-ring", "Civic Fiber Ring", "service", "telecommunications", "Fictional connectivity service with declared provider alternatives."),
    ("radio-network", "Emergency Radio Network", "service", "telecommunications", "Fictional independent radio coordination service."),
    ("city-data-center", "Municipal Data Center", "facility", "digital", "Fictional shared data service; capacity and failover times unknown."),
    ("health-records", "Shared Health Records", "service", "healthcare", "Fictional electronic records service."),
    ("patient-coordination", "Patient Coordination Service", "service", "healthcare", "Fictional coordination service with radio alternative."),
    ("hospital-central", "Northbank General Hospital", "facility", "healthcare", "Fictional acute care facility."),
    ("hospital-east", "Eastbank Community Hospital", "facility", "healthcare", "Fictional community hospital."),
    ("clinic-east", "Eastbank Walk-in Clinic", "facility", "healthcare", "Fictional outpatient facility."),
    ("clinic-west", "Westbank Walk-in Clinic", "facility", "healthcare", "Fictional outpatient facility."),
    ("ambulance-dispatch", "Ambulance Dispatch", "service", "emergency_services", "Fictional dispatch service with radio and fiber alternatives."),
    ("emergency-ops", "Civic Emergency Operations Center", "facility", "government", "Fictional coordination center."),
    ("backup-control-room", "Alternate Coordination Room", "facility", "government", "Fictional alternate coordination room."),
    ("municipal-hotline", "Municipal Information Hotline", "service", "government", "Fictional public information service."),
    ("public-alert", "Public Alert Service", "service", "emergency_services", "Fictional warning service with two declared channels."),
    ("rail-signals", "Civic Rail Signaling", "service", "transport", "Fictional rail signaling service."),
    ("road-signals", "East Corridor Signals", "service", "transport", "Fictional traffic signal service."),
    ("transit-control", "Transit Operations Control", "service", "transport", "Fictional public transport control service."),
    ("airport-terminal", "Northbank Regional Terminal", "facility", "transport", "Fictional regional terminal."),
    ("shelter-east", "East Community Shelter", "facility", "community", "Fictional community shelter."),
    ("shelter-west", "West Community Shelter", "facility", "community", "Fictional community shelter."),
    ("supply-hub", "Civic Supply Hub", "facility", "logistics", "Fictional distribution and storage service."),
    ("recovery-crew", "Infrastructure Recovery Crew", "recovery_resource", "recovery", "Fictional restoration team; repair time is not modeled."),
    ("fleet-dispatch", "Municipal Fleet Dispatch", "service", "logistics", "Fictional fleet coordination service."),
    ("weather-alert", "Weather Warning Feed", "service", "emergency_services", "Fictional warning data service."),
    ("emergency-portal", "Emergency Information Portal", "service", "government", "Fictional public information web service."),
    ("payment-service", "Civic Payment Service", "service", "finance", "Fictional municipal payment service."),
    ("records-archive", "Continuity Records Archive", "service", "digital", "Fictional continuity document archive."),
]


def build_graph() -> InfrastructureGraph:
    nodes = []
    for node_id, name, category, sector, description in RAW_NODES:
        nodes.append({
            "id": node_id,
            "name": name,
            "category": category,
            "sector": sector,
            "description": description,
            "capacity": None,
            "capacity_unit": None,
            "criticality": "high" if sector in {"electricity", "water", "healthcare", "telecommunications", "emergency_services"} else "medium",
            "aliases": [node_id.replace("-", " ")],
            "fictional": True,
        })

    edges: list[dict] = []
    def edge(
        source,
        dependent,
        dep_type,
        group,
        mode="ANY",
        status="verified",
        note=None,
        owner="Continuity planning owner",
        date="2026-10-01",
        review_due=None,
    ):
        seq = len(edges) + 1
        evidence = note or f"Synthetic continuity register CM-DEMO-01 states that {dependent.replace('-', ' ')} requires {dep_type} from {source.replace('-', ' ')} under normal service conditions."
        record = {
            "id": f"edge-{seq:03d}", "source": source, "dependent": dependent,
            "dependency_type": dep_type, "evidence": evidence,
            "evidence_ref": f"CM-DEMO-01 §{seq:02d}", "verification_status": status,
            "owner": owner, "conditions": ["Normal operating arrangement in fictional exercise data."],
            "assumptions": [], "last_validated": date if status == "verified" else None,
            "group_id": group, "group_mode": mode,
        }
        if review_due is not None:
            record["review_due_date"] = review_due
        edges.append(record)

    # Add useful unambiguous aliases for document entity matching.
    by_id = {node["id"]: node for node in nodes}
    by_id["hospital-central"]["aliases"] += ["Northbank General"]
    by_id["health-records"]["aliases"] += ["electronic health records", "shared health records"]
    by_id["clinic-east"]["aliases"] += ["Eastbank Walk-in Clinic"]
    by_id["booster-east"]["aliases"] += ["East Water Booster Station"]
    by_id["hospital-east"]["aliases"] += ["Eastbank Community Hospital"]
    by_id["telecom-core"]["aliases"] += ["Central Telecom Exchange"]
    by_id["emergency-ops"]["aliases"] += ["Civic Emergency Operations Center"]
    by_id["fiber-ring"]["aliases"] += ["Civic Fiber Ring"]
    by_id["radio-network"]["aliases"] += ["Emergency Radio Network"]
    by_id["shelter-west"]["aliases"] += ["West Community Shelter"]

    # Backup generation and primary power requirements.
    edge("fuel-depot", "gen-water", "fuel", "generator-fuel", "ALL")
    edge("fuel-depot", "gen-hospital", "fuel", "generator-fuel", "ALL")
    edge("fuel-depot", "gen-telecom", "fuel", "generator-fuel", "ALL")
    edge("fuel-depot", "mobile-generator", "fuel", "generator-fuel", "ALL")
    edge("grid-alpha", "water-treatment", "power", "treatment-power", "ANY")
    edge(
        "solar-microgrid",
        "water-treatment",
        "power",
        "treatment-power",
        "ANY",
        review_due="2026-10-15",
    )
    edge("grid-alpha", "booster-east", "power", "east-pump-power", "ANY")
    edge("gen-water", "booster-east", "power", "east-pump-power", "ANY")
    edge("grid-beta", "booster-west", "power", "west-pump-power", "ANY")
    edge("gen-water", "booster-west", "power", "west-pump-power", "ANY")
    edge("water-treatment", "booster-east", "water", "treated-water", "ALL")
    edge("water-treatment", "booster-west", "water", "treated-water", "ALL")
    edge("booster-east", "reservoir-east", "water", "reservoir-feed", "ANY")
    edge("booster-west", "reservoir-east", "water", "reservoir-feed", "ANY")
    edge("grid-alpha", "water-control", "power", "control-power", "ALL")
    edge("telecom-core", "water-control", "data_connectivity", "control-data", "ALL")
    edge("water-control", "water-quality-lab", "data_connectivity", "lab-workflow", "ALL")
    edge("grid-alpha", "water-quality-lab", "power", "lab-power", "ALL")

    edge("grid-alpha", "telecom-core", "power", "exchange-power", "ANY")
    edge("gen-telecom", "telecom-core", "power", "exchange-power", "ANY")
    edge("grid-alpha", "telecom-east", "power", "exchange-power", "ALL")
    edge("telecom-core", "fiber-ring", "telecommunications", "fiber-access", "ANY")
    edge("telecom-east", "fiber-ring", "telecommunications", "fiber-access", "ANY")
    edge("grid-alpha", "radio-network", "power", "radio-power", "ANY")
    edge("mobile-generator", "radio-network", "power", "radio-power", "ANY")

    edge("grid-alpha", "city-data-center", "power", "data-center-power", "ALL")
    edge("city-data-center", "health-records", "data_connectivity", "records-hosting", "ALL")
    edge("health-records", "hospital-central", "data_connectivity", "clinical-records", "ALL")
    edge("health-records", "hospital-east", "data_connectivity", "clinical-records", "ALL")
    edge("health-records", "clinic-east", "data_connectivity", "clinical-records", "ALL")
    edge("health-records", "clinic-west", "data_connectivity", "clinical-records", "ALL")
    edge("grid-alpha", "hospital-central", "power", "hospital-power", "ANY")
    edge("gen-hospital", "hospital-central", "power", "hospital-power", "ANY")
    edge("grid-alpha", "hospital-east", "power", "hospital-power", "ANY")
    edge("gen-hospital", "hospital-east", "power", "hospital-power", "ANY")
    edge("booster-east", "hospital-central", "water", "hospital-water", "ANY")
    edge("booster-west", "hospital-central", "water", "hospital-water", "ANY")
    edge("booster-east", "hospital-east", "water", "hospital-water", "ANY")
    edge("booster-west", "hospital-east", "water", "hospital-water", "ANY")
    edge("booster-east", "clinic-east", "water", "clinic-water", "ALL")
    edge("booster-west", "clinic-west", "water", "clinic-water", "ALL")
    edge("grid-alpha", "clinic-east", "power", "clinic-power", "ALL")
    edge("grid-beta", "clinic-west", "power", "clinic-power", "ALL")

    edge("telecom-core", "patient-coordination", "telecommunications", "patient-coordination", "ANY")
    edge("radio-network", "patient-coordination", "telecommunications", "patient-coordination", "ANY")
    edge("telecom-core", "ambulance-dispatch", "telecommunications", "dispatch-comms", "ANY")
    edge("radio-network", "ambulance-dispatch", "telecommunications", "dispatch-comms", "ANY")
    edge("grid-alpha", "emergency-ops", "power", "eoc-power", "ANY")
    edge("gen-hospital", "emergency-ops", "power", "eoc-power", "ANY")
    edge("fiber-ring", "emergency-ops", "telecommunications", "eoc-comms", "ANY")
    edge("radio-network", "emergency-ops", "telecommunications", "eoc-comms", "ANY")
    edge("grid-beta", "backup-control-room", "power", "alternate-room-power", "ALL")
    edge("radio-network", "backup-control-room", "telecommunications", "alternate-room-comms", "ALL")
    edge("fiber-ring", "municipal-hotline", "telecommunications", "hotline-channel", "ALL")
    edge("telecom-core", "public-alert", "telecommunications", "public-alert-channel", "ANY")
    edge("radio-network", "public-alert", "telecommunications", "public-alert-channel", "ANY")

    edge("grid-alpha", "rail-signals", "power", "signal-power", "ALL")
    edge("grid-alpha", "road-signals", "power", "signal-power", "ALL")
    edge("grid-alpha", "transit-control", "power", "transit-power", "ALL")
    edge("fiber-ring", "transit-control", "telecommunications", "transit-comms", "ALL")
    edge("grid-beta", "airport-terminal", "power", "terminal-power", "ALL")
    edge("grid-alpha", "shelter-east", "power", "shelter-east-power", "ANY")
    edge("mobile-generator", "shelter-east", "power", "shelter-east-power", "ANY")
    edge("booster-east", "shelter-east", "water", "shelter-east-water", "ALL")
    edge("grid-beta", "shelter-west", "power", "shelter-west-power", "ALL")
    edge("booster-west", "shelter-west", "water", "shelter-west-water", "ALL")
    edge("grid-beta", "supply-hub", "power", "supply-hub-power", "ALL")
    edge("road-signals", "recovery-crew", "transport", "crew-access", "ALL")
    edge("fiber-ring", "fleet-dispatch", "telecommunications", "fleet-comms", "ANY")
    edge("radio-network", "fleet-dispatch", "telecommunications", "fleet-comms", "ANY")
    edge("grid-alpha", "fleet-dispatch", "power", "fleet-power", "ALL")
    edge("telecom-core", "weather-alert", "data_connectivity", "weather-feed", "ANY")
    edge("radio-network", "weather-alert", "data_connectivity", "weather-feed", "ANY")
    edge("city-data-center", "emergency-portal", "data_connectivity", "portal-hosting", "ALL")
    edge("fiber-ring", "emergency-portal", "telecommunications", "portal-connectivity", "ALL")
    edge("city-data-center", "payment-service", "data_connectivity", "payment-hosting", "ALL")
    edge("fiber-ring", "payment-service", "telecommunications", "payment-connectivity", "ALL")
    edge("grid-beta", "records-archive", "power", "archive-power", "ALL")
    edge("city-data-center", "records-archive", "data_connectivity", "archive-replication", "ALL", status="proposed", note="Draft recovery worksheet suggests the continuity archive replicates to the municipal data center; owner confirmation is pending.", owner="Records service owner", date=None)
    edge("gen-water", "hospital-east", "power", "temporary-water-generator", "ANY", status="rejected", note="Rejected draft claim: water generator supplies hospital backup power. Owner review states the generator is dedicated to water operations.", owner="Facilities review panel", date=None)

    unknown_relationships = [
        {
            "id": "unknown-001", "source": "grid-alpha", "dependent": "shelter-west",
            "dependency_type": "power",
            "question": "Does this shelter have a temporary utility feed from Substation Alpha during planned events?",
            "evidence": "Draft plan question: Does this shelter have a temporary utility feed from Substation Alpha during planned events?",
            "verification_status": "unknown", "owner": "Community services owner",
            "evidence_ref": "CM-DRAFT-02 §4", "conditions": ["Applies only during planned events."],
            "assumptions": [], "last_validated": None,
        },
        {
            "id": "unknown-002", "source": "city-data-center", "dependent": "records-archive",
            "dependency_type": "data_connectivity",
            "question": "Is the archive replica required for the records service, or is it a recovery-only copy?",
            "evidence": "Draft plan question: Is the archive replica required for the records service, or is it a recovery-only copy?",
            "verification_status": "unknown", "owner": "Digital services owner",
            "evidence_ref": "CM-DRAFT-02 §8", "conditions": ["Applies during records service recovery."],
            "assumptions": [], "last_validated": None,
        },
    ]

    scenarios = [
        {"id": "substation-alpha-outage", "name": "Substation Alpha unavailable", "description": "Planning exercise: the fictional primary distribution source is unavailable. Backup assets remain available unless a declared dependency says otherwise.", "disrupted_nodes": ["grid-alpha"], "expected_affected": [], "review_actions": ["Confirm generator fuel autonomy and start conditions with facility owners.", "Review the East Corridor signal and clinic contingency evidence.", "Resolve the proposed shelter and archive relationships before readiness reporting."]},
        {"id": "water-pumping-backup-loss", "name": "East water pumping loses utility and backup power", "description": "Planning exercise: Substation Alpha and the shared water backup generator are unavailable simultaneously.", "disrupted_nodes": ["grid-alpha", "gen-water"], "expected_affected": [], "review_actions": ["Validate alternative water supply, storage duration, and transfer arrangements.", "Confirm which health and shelter services have tested water contingencies."]},
        {"id": "regional-communications-outage", "name": "Regional communications outage", "description": "Planning exercise: both fictional telecom exchanges are unavailable; the independently modeled emergency radio network remains available.", "disrupted_nodes": ["telecom-core", "telecom-east"], "expected_affected": [], "review_actions": ["Confirm radio coverage, user access, and exercise evidence for emergency coordination.", "Review services with a single fiber-dependent channel."]},
    ]
    data = {
        "dataset_id": "northbank-fictional-v1",
        "title": "Northbank Fictional Civic Services Network",
        "synthetic_notice": "SYNTHETIC DEMONSTRATION DATA — every place, service, relationship, owner, and evidence reference is fictional. Do not treat this network as a real-world map.",
        "nodes": nodes,
        "edges": edges,
        "unknown_relationships": unknown_relationships,
        "scenarios": scenarios,
        "metadata": {"created": "2026-10-26", "node_count": len(nodes), "edge_count": len(edges), "source": "scripts/generate_synthetic_data.py", "edge_direction": "provider/source → dependent service", "scenario_semantics": "least fixed point of verified dependency requirements"},
    }
    graph = InfrastructureGraph.model_validate(data)
    for scenario in graph.scenarios:
        # Expected sets are fixed independently from simulator output and serve as evaluation gold.
        scenario.expected_affected = EXPECTED_AFFECTED[scenario.id]
    return graph


if __name__ == "__main__":
    result = build_graph()
    target = ROOT / "data" / "infrastructure.json"
    payload = result.model_dump(mode="json")
    for edge in payload["edges"]:
        if edge["review_due_date"] is None:
            edge.pop("review_due_date")
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {target.relative_to(ROOT)}: {len(result.nodes)} nodes, {len(result.edges)} relationships")
    for scenario in result.scenarios:
        print(f"{scenario.name}: {len(scenario.expected_affected)} affected nodes")
