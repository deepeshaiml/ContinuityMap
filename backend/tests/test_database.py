from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from continuitymap.database import Base, UnknownRow, load_graph, save_graph
from continuitymap.models import InfrastructureGraph

ROOT = Path(__file__).resolve().parents[2]


def test_save_graph_inserts_nodes_before_foreign_key_relationships():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def enforce_foreign_keys(dbapi_connection, _connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    graph = InfrastructureGraph.model_validate(
        json.loads((ROOT / "data" / "infrastructure.json").read_text(encoding="utf-8"))
    )
    with Session(engine, autoflush=False) as session:
        save_graph(session, graph)
        loaded = load_graph(session)

    assert loaded is not None
    assert len(loaded.nodes) == 43
    assert len(loaded.edges) == 80


def test_load_graph_normalizes_legacy_unknown_relationship_records():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    graph = InfrastructureGraph.model_validate(
        json.loads((ROOT / "data" / "infrastructure.json").read_text(encoding="utf-8"))
    )
    with Session(engine, autoflush=False) as session:
        save_graph(session, graph)
        row = session.get(UnknownRow, "unknown-001")
        assert row is not None
        legacy = {
            key: value
            for key, value in row.payload.items()
            if key
            not in {
                "dependency_type",
                "evidence",
                "verification_status",
                "conditions",
                "assumptions",
                "last_validated",
            }
        }
        row.payload = legacy
        session.commit()
        migrated = load_graph(session)

    assert migrated is not None
    unknown = migrated.unknown_relationships[0]
    assert unknown.verification_status == "unknown"
    assert unknown.evidence == unknown.question
    assert unknown.evidence_ref == "CM-DRAFT-02 §4"
    assert unknown.conditions == []
