from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from continuitymap.ai import extract_text, grounded_assessment, propose_relationships
from continuitymap.database import (
    AuditRow,
    SessionLocal,
    add_audit,
    get_session,
    init_db,
    load_graph,
    save_graph,
)
from continuitymap.graph import simulate, validate_graph
from continuitymap.models import Edge, InfrastructureGraph, ScenarioRequest, VerificationStatus
from continuitymap.reports import checklist_pdf, gaps_pdf, impact_pdf

_module_path = Path(__file__).resolve()
ROOT = next(
    (
        parent
        for parent in _module_path.parents
        if (parent / "data" / "infrastructure.json").is_file()
    ),
    _module_path.parents[1],
)
DATA_PATH = ROOT / "data" / "infrastructure.json"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    with SessionLocal() as session:
        if load_graph(session) is None:
            seed = InfrastructureGraph.model_validate(
                json.loads(DATA_PATH.read_text(encoding="utf-8"))
            )
            save_graph(session, seed)
    yield


app = FastAPI(
    title="ContinuityMap API",
    version="0.1.0",
    description="Synthetic infrastructure dependency planning support.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _graph(session: Session) -> InfrastructureGraph:
    value = load_graph(session)
    if value is None:
        raise HTTPException(status_code=503, detail="The demonstration graph is not initialized.")
    return value


@app.get("/api/health")
def health(session: Session = Depends(get_session)):
    graph = load_graph(session)
    return {
        "ok": graph is not None,
        "dataset_id": graph.dataset_id if graph else None,
        "synthetic_only": True,
    }


@app.get("/api/graph")
def get_graph(session: Session = Depends(get_session)):
    graph = _graph(session)
    return {
        "graph": graph.model_dump(mode="json"),
        "validation": validate_graph(graph).model_dump(mode="json"),
    }


@app.put("/api/graph/import")
def import_graph(graph: InfrastructureGraph, session: Session = Depends(get_session)):
    if any(not node.fictional for node in graph.nodes):
        raise HTTPException(
            status_code=400, detail="This demonstration build accepts fictional nodes only."
        )
    validation = validate_graph(graph)
    if not validation.valid:
        raise HTTPException(status_code=422, detail=validation.model_dump(mode="json"))
    save_graph(session, graph)
    add_audit(
        session,
        "graph_imported",
        graph.dataset_id,
        "local-demo-user",
        {"nodes": len(graph.nodes), "edges": len(graph.edges)},
    )
    session.commit()
    return {"ok": True, "validation": validation.model_dump(mode="json")}


@app.post("/api/graph/validate")
def graph_validation(session: Session = Depends(get_session)):
    return validate_graph(_graph(session)).model_dump(mode="json")


@app.post("/api/scenarios/run")
def run_scenario(request: ScenarioRequest, session: Session = Depends(get_session)):
    graph = _graph(session)
    scenario = (
        next((item for item in graph.scenarios if item.id == request.scenario_id), None)
        if request.scenario_id
        else None
    )
    if request.scenario_id and scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found.")
    disrupted = (
        request.disrupted_nodes
        if request.disrupted_nodes is not None
        else (scenario.disrupted_nodes if scenario else [])
    )
    if not disrupted:
        raise HTTPException(status_code=422, detail="Select at least one disrupted node.")
    try:
        result = simulate(graph, disrupted, scenario.name if scenario else "Custom disruption")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if scenario:
        expected = set(scenario.expected_affected)
        actual = set(result.affected_nodes)
        true_positive = len(expected & actual)
        precision = true_positive / len(actual) if actual else 1.0
        recall = true_positive / len(expected) if expected else 1.0
        result.evaluation = {
            "fixture_expected_affected": len(expected),
            "exact_match": expected == actual,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
        }
    add_audit(
        session,
        "scenario_run",
        request.scenario_id or "custom",
        "local-demo-user",
        {"disrupted_nodes": disrupted, "affected_count": len(result.affected_nodes)},
    )
    session.commit()
    return result.model_dump(mode="json")


@app.post("/api/edges", status_code=201)
def add_proposed_edge(edge: Edge, session: Session = Depends(get_session)):
    if edge.verification_status != VerificationStatus.PROPOSED:
        raise HTTPException(
            status_code=400, detail="New relationships enter as proposed and require human review."
        )
    graph = _graph(session)
    if edge.id in {item.id for item in graph.edges}:
        raise HTTPException(status_code=409, detail="Relationship ID already exists.")
    candidate = graph.model_copy(update={"edges": [*graph.edges, edge]})
    validation = validate_graph(candidate)
    if not validation.valid:
        raise HTTPException(status_code=422, detail=validation.model_dump(mode="json"))
    save_graph(session, candidate)
    add_audit(
        session,
        "edge_proposed",
        edge.id,
        edge.owner,
        {"source": edge.source, "dependent": edge.dependent, "status": "proposed"},
    )
    session.commit()
    return edge.model_dump(mode="json")


@app.put("/api/edges/{edge_id}")
def update_edge(edge_id: str, edge: Edge, session: Session = Depends(get_session)):
    if edge.id != edge_id:
        raise HTTPException(status_code=400, detail="Path and relationship IDs must match.")
    graph = _graph(session)
    if edge_id not in {item.id for item in graph.edges}:
        raise HTTPException(status_code=404, detail="Relationship not found.")
    if edge.verification_status == VerificationStatus.VERIFIED and edge.last_validated is None:
        edge.last_validated = date.today()
    updated = graph.model_copy(
        update={"edges": [edge if item.id == edge_id else item for item in graph.edges]}
    )
    validation = validate_graph(updated)
    if not validation.valid:
        raise HTTPException(status_code=422, detail=validation.model_dump(mode="json"))
    save_graph(session, updated)
    add_audit(
        session,
        "edge_updated",
        edge.id,
        edge.owner,
        {
            "status": edge.verification_status.value,
            "source": edge.source,
            "dependent": edge.dependent,
        },
    )
    session.commit()
    return {"edge": edge.model_dump(mode="json"), "validation": validation.model_dump(mode="json")}


@app.post("/api/documents/extract")
async def extract_document(file: UploadFile = File(...), session: Session = Depends(get_session)):
    filename = (file.filename or "fictional-upload.txt").replace("\\", "/").split("/")[-1][:100]
    try:
        text = extract_text(filename, await file.read())
    except (ValueError, Exception) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    graph = _graph(session)
    proposals, mode = await propose_relationships(text, filename, graph)
    if proposals:
        updated = graph.model_copy(update={"edges": [*graph.edges, *proposals]})
        save_graph(session, updated)
        for proposal in proposals:
            add_audit(
                session,
                "edge_proposed",
                proposal.id,
                proposal.owner,
                {
                    "source": proposal.source,
                    "dependent": proposal.dependent,
                    "evidence_ref": proposal.evidence_ref,
                    "mode": mode,
                },
            )
        session.commit()
    return {
        "filename": filename,
        "mode": mode,
        "proposals": [item.model_dump(mode="json") for item in proposals],
        "human_review_required": True,
        "note": "Proposals do not affect scenario status until a human verifies each relationship.",
    }


@app.post("/api/assistant/assessment")
async def assistant_assessment(request: ScenarioRequest, session: Session = Depends(get_session)):
    graph = _graph(session)
    scenario = (
        next((item for item in graph.scenarios if item.id == request.scenario_id), None)
        if request.scenario_id
        else None
    )
    if request.scenario_id and scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found.")
    disrupted = (
        request.disrupted_nodes
        if request.disrupted_nodes is not None
        else (scenario.disrupted_nodes if scenario else [])
    )
    if not disrupted:
        raise HTTPException(
            status_code=422, detail="Select a scenario or at least one disrupted node."
        )
    try:
        result = simulate(graph, disrupted, scenario.name if scenario else "Custom disruption")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await grounded_assessment(graph, result, validate_graph(graph), scenario)


def _scenario_result(graph: InfrastructureGraph, scenario_id: str):
    scenario = next((item for item in graph.scenarios if item.id == scenario_id), None)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found.")
    return simulate(graph, scenario.disrupted_nodes, scenario.name)


@app.get("/api/reports/impact/{scenario_id}.pdf")
def impact_report(scenario_id: str, session: Session = Depends(get_session)):
    graph = _graph(session)
    report = impact_pdf(graph, _scenario_result(graph, scenario_id))
    return Response(
        report,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=ContinuityMap_Impact_{scenario_id}.pdf"
        },
    )


@app.get("/api/reports/dependency-gaps.pdf")
def dependency_gap_report(session: Session = Depends(get_session)):
    graph = _graph(session)
    report = gaps_pdf(graph, validate_graph(graph))
    return Response(
        report,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=ContinuityMap_Dependency_Gaps.pdf"},
    )


@app.get("/api/reports/checklist/{scenario_id}.pdf")
def checklist_report(scenario_id: str, session: Session = Depends(get_session)):
    graph = _graph(session)
    report = checklist_pdf(graph, _scenario_result(graph, scenario_id))
    return Response(
        report,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=ContinuityMap_Checklist_{scenario_id}.pdf"
        },
    )


@app.get("/api/audit")
def audit_log(session: Session = Depends(get_session)):
    rows = session.scalars(select(AuditRow).order_by(AuditRow.created_at.desc()).limit(100))
    return [
        {
            "id": row.id,
            "action": row.action,
            "object_id": row.object_id,
            "actor": row.actor,
            "details": row.details,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
