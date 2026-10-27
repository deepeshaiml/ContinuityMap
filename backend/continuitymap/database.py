from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE = f"sqlite:///{(ROOT / 'backend' / 'continuitymap.db').as_posix()}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class DatasetRow(Base):
    __tablename__ = "dataset"
    id: Mapped[str] = mapped_column(String(30), primary_key=True, default="current")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class NodeRow(Base):
    __tablename__ = "infrastructure_nodes"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class EdgeRow(Base):
    __tablename__ = "dependency_edges"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    source: Mapped[str] = mapped_column(
        ForeignKey("infrastructure_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dependent: Mapped[str] = mapped_column(
        ForeignKey("infrastructure_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class UnknownRow(Base):
    __tablename__ = "unknown_relationships"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    source: Mapped[str] = mapped_column(
        ForeignKey("infrastructure_nodes.id", ondelete="CASCADE"), nullable=False
    )
    dependent: Mapped[str] = mapped_column(
        ForeignKey("infrastructure_nodes.id", ondelete="CASCADE"), nullable=False
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ScenarioRow(Base):
    __tablename__ = "scenarios"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class AuditRow(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    object_id: Mapped[str] = mapped_column(String(100), nullable=False)
    actor: Mapped[str] = mapped_column(String(160), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_session():
    with SessionLocal() as session:
        yield session


def load_graph(session: Session):
    from continuitymap.models import InfrastructureGraph

    dataset = session.get(DatasetRow, "current")
    if dataset is None:
        return None
    nodes = [row.payload for row in session.scalars(select(NodeRow).order_by(NodeRow.id))]
    edges = [row.payload for row in session.scalars(select(EdgeRow).order_by(EdgeRow.id))]
    unknown = []
    for row in session.scalars(select(UnknownRow).order_by(UnknownRow.id)):
        payload = dict(row.payload)
        payload.setdefault("dependency_type", None)
        if not payload.get("evidence"):
            payload["evidence"] = payload.get("question") or "Legacy record has no evidence text."
        payload.setdefault("verification_status", "unknown")
        if not payload.get("evidence_ref"):
            payload["evidence_ref"] = "legacy-record-no-reference"
        payload.setdefault("conditions", [])
        payload.setdefault("assumptions", [])
        payload.setdefault("last_validated", None)
        unknown.append(payload)
    scenarios = [
        row.payload for row in session.scalars(select(ScenarioRow).order_by(ScenarioRow.id))
    ]
    return InfrastructureGraph.model_validate(
        {
            **dataset.payload,
            "nodes": nodes,
            "edges": edges,
            "unknown_relationships": unknown,
            "scenarios": scenarios,
        }
    )


def save_graph(session: Session, graph) -> None:
    payload = graph.model_dump(mode="json")
    session.query(EdgeRow).delete()
    session.query(UnknownRow).delete()
    session.query(ScenarioRow).delete()
    session.query(NodeRow).delete()
    session.merge(
        DatasetRow(
            id="current",
            payload={
                key: value
                for key, value in payload.items()
                if key not in {"nodes", "edges", "unknown_relationships", "scenarios"}
            },
        )
    )
    session.add_all(NodeRow(id=node["id"], payload=node) for node in payload["nodes"])
    session.flush()
    session.add_all(
        EdgeRow(
            id=edge["id"],
            source=edge["source"],
            dependent=edge["dependent"],
            verification_status=edge["verification_status"],
            payload=edge,
        )
        for edge in payload["edges"]
    )
    session.add_all(
        UnknownRow(id=row["id"], source=row["source"], dependent=row["dependent"], payload=row)
        for row in payload["unknown_relationships"]
    )
    session.add_all(ScenarioRow(id=row["id"], payload=row) for row in payload["scenarios"])
    session.commit()


def add_audit(
    session: Session, action: str, object_id: str, actor: str, details: dict[str, Any]
) -> None:
    import uuid

    session.add(
        AuditRow(
            id=str(uuid.uuid4()), action=action, object_id=object_id, actor=actor, details=details
        )
    )
