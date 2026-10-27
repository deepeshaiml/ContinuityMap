from __future__ import annotations

import json
import os
import re
import uuid
from typing import Any

import httpx

from continuitymap.models import Edge, GroupMode, InfrastructureGraph, VerificationStatus

MAX_UPLOAD_BYTES = 2_000_000
MAX_TEXT_CHARS = 80_000


def extract_text(filename: str, content: bytes) -> str:
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("Upload exceeds the 2 MB demonstration limit.")
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix in {"txt", "md", "csv"}:
        return content.decode("utf-8", errors="replace")[:MAX_TEXT_CHARS]
    if suffix == "pdf":
        from io import BytesIO

        from pypdf import PdfReader

        text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
        return text[:MAX_TEXT_CHARS]
    if suffix == "docx":
        from io import BytesIO

        from docx import Document

        document = Document(BytesIO(content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)[:MAX_TEXT_CHARS]
    raise ValueError("Supported uploads: .txt, .md, .csv, .pdf, .docx")


def _sentences(text: str) -> list[str]:
    return [part.strip(" \t-•\r") for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]


def _resolve_aliases(sentence: str, graph: InfrastructureGraph) -> list[str]:
    lowered = sentence.casefold()
    hits: list[tuple[int, int, str]] = []
    for node in graph.nodes:
        for alias in {node.name, node.id.replace("-", " "), *node.aliases}:
            alias = alias.strip()
            if len(alias) < 5:
                continue
            match = re.search(r"(?<![\w])" + re.escape(alias.casefold()) + r"(?![\w])", lowered)
            if match:
                hits.append((match.start(), -len(alias), node.id))
    # Keep the longest non-overlapping entity matches, avoiding shorter aliases nested in names.
    selected: list[tuple[int, int, str]] = []
    for start, neg_len, node_id in sorted(hits):
        end = start - neg_len
        if any(
            start < prior_start - prior_neg_len and end > prior_start
            for prior_start, prior_neg_len, _ in selected
        ):
            continue
        if node_id not in [item[2] for item in selected]:
            selected.append((start, neg_len, node_id))
    return [item[2] for item in sorted(selected)]


def _infer_type(sentence: str) -> str:
    text = sentence.casefold()
    if any(word in text for word in ["power", "electric", "generator", "electricity"]):
        return "power"
    if any(word in text for word in ["water", "pumping", "reservoir"]):
        return "water"
    if any(word in text for word in ["telecom", "radio", "communications", "fiber"]):
        return "telecommunications"
    if any(word in text for word in ["data", "records", "connectivity", "digital"]):
        return "data_connectivity"
    return "other"


def heuristic_extract(text: str, filename: str, graph: InfrastructureGraph) -> list[dict[str, Any]]:
    proposals = []
    for index, sentence in enumerate(_sentences(text), 1):
        match = re.search(
            r"\b(depends on|depend on|requires?|relies on|needs?)\b", sentence.casefold()
        )
        if not match:
            continue
        entities = _resolve_aliases(sentence, graph)
        if len(entities) < 2:
            continue
        # Dependency wording reads dependent first, then its provider(s).
        lower_sentence = sentence.casefold()
        trigger_pos = match.start()
        before = [
            node
            for node in entities
            if (pos := lower_sentence.find(node.replace("-", " "))) >= 0 and pos < trigger_pos
        ]
        dependent = before[-1] if before else entities[0]
        providers = [node for node in entities if node != dependent]
        for provider in providers:
            proposals.append(
                {
                    "source": provider,
                    "dependent": dependent,
                    "dependency_type": _infer_type(sentence),
                    "evidence": sentence,
                    "evidence_ref": f"upload:{filename}#paragraph-{index}",
                    "confidence": 0.55,
                }
            )
    return proposals


async def llm_extract(
    text: str, filename: str, graph: InfrastructureGraph
) -> list[dict[str, Any]] | None:
    base_url = os.getenv("OLLAMA_BASE_URL")
    model = os.getenv("OLLAMA_MODEL")
    if not base_url or not model:
        return None
    node_catalog = [
        {"id": node.id, "name": node.name, "aliases": node.aliases} for node in graph.nodes
    ]
    prompt = (
        "Extract only explicit service dependency claims from this fictional document. Return JSON as "
        '{"relationships":[{"source":provider_id,"dependent":service_id,"dependency_type":one_of_power_water_telecommunications_data_connectivity_transport_fuel_staff_other,"evidence":exact_verbatim_sentence,"confidence":0_to_1}]}. '
        "Use only IDs in the catalog. Do not infer a claim from absence or general knowledge. Preserve ambiguity by omitting it.\n"
        f"Node catalog: {json.dumps(node_catalog)}\nDocument ({filename}):\n{text[:MAX_TEXT_CHARS]}"
    )
    try:
        async with httpx.AsyncClient(timeout=50) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/api/chat",
                json={
                    "model": model,
                    "stream": False,
                    "format": "json",
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
        content = response.json().get("message", {}).get("content", "")
        parsed = json.loads(content)
        result = []
        valid_ids = {node.id for node in graph.nodes}
        for item in parsed.get("relationships", []):
            if item.get("source") not in valid_ids or item.get("dependent") not in valid_ids:
                continue
            evidence = str(item.get("evidence", ""))
            if evidence and evidence in text:
                result.append(
                    {
                        **item,
                        "evidence_ref": f"upload:{filename}",
                        "confidence": max(0, min(1, float(item.get("confidence", 0.5)))),
                    }
                )
        return result
    except (httpx.HTTPError, json.JSONDecodeError, ValueError, TypeError):
        return None


async def propose_relationships(
    text: str, filename: str, graph: InfrastructureGraph
) -> tuple[list[Edge], str]:
    extracted = await llm_extract(text, filename, graph)
    mode = "local_ollama" if extracted is not None else "heuristic_review_only"
    if extracted is None:
        extracted = heuristic_extract(text, filename, graph)
    proposals: list[Edge] = []
    nodes = {node.id for node in graph.nodes}
    seen = set()
    for item in extracted:
        source, dependent = item.get("source"), item.get("dependent")
        if source not in nodes or dependent not in nodes or source == dependent:
            continue
        evidence = str(item.get("evidence", "")).strip()
        if not evidence:
            continue
        signature = (source, dependent, item.get("dependency_type", "other"), evidence.casefold())
        if signature in seen:
            continue
        seen.add(signature)
        try:
            dep_type = item.get("dependency_type", "other")
            proposals.append(
                Edge(
                    id=f"ai-{uuid.uuid4().hex[:12]}",
                    source=source,
                    dependent=dependent,
                    dependency_type=dep_type,
                    evidence=evidence,
                    evidence_ref=str(item.get("evidence_ref", f"upload:{filename}")),
                    verification_status=VerificationStatus.PROPOSED,
                    owner="Owner assignment required",
                    conditions=[
                        "Extracted from an uploaded fictional document; confirm applicability and operating conditions."
                    ],
                    assumptions=[],
                    last_validated=None,
                    group_id=f"review-{uuid.uuid4().hex[:8]}",
                    group_mode=GroupMode.ANY,
                )
            )
        except Exception:
            continue
    return proposals, mode


async def grounded_assessment(
    graph: InfrastructureGraph, result, validation, scenario
) -> dict[str, Any]:
    affected = set(result.affected_nodes)
    resources = [
        node.name
        for node in graph.nodes
        if node.category.value == "recovery_resource" and node.id not in affected
    ]
    gap_edges = [
        edge for edge in graph.edges if edge.verification_status.value in {"proposed", "unknown"}
    ]
    gaps = [f"{edge.source} → {edge.dependent}: {edge.evidence_ref}" for edge in gap_edges]
    gaps += [
        f"{item.source} → {item.dependent}: {item.question}" for item in graph.unknown_relationships
    ]
    evidence_refs = sorted(
        {
            edge.evidence_ref
            for edge in graph.edges
            if edge.verification_status.value == "verified" and edge.dependent in affected
        }
    )
    actions = list(scenario.review_actions if scenario else [])
    if validation.counts.get("warnings"):
        actions.append(
            f"Review {validation.counts['warnings']} graph validation warning(s), including unsupported assumptions or dependency cycles."
        )
    assessment = {
        "mode": "evidence_template",
        "summary": f"The declared dependency model marks {len(result.affected_nodes)} node(s) unavailable, including the explicit scenario seed(s), after {scenario.name if scenario else result.scenario_name}. These are logical consequences of verified edges only.",
        "affected_services": [
            {
                "id": item.node_id,
                "name": item.node_name,
                "reason": item.reason,
                "evidence_refs": [
                    next(
                        (edge.evidence_ref for edge in graph.edges if edge.id == edge_id),
                        "scenario seed",
                    )
                    for edge_id in item.edge_ids
                ],
            }
            for item in result.explanations
            if item.status in {"affected", "disrupted"}
        ],
        "declared_dependencies": [
            edge.model_dump(mode="json")
            for edge in graph.edges
            if edge.verification_status.value == "verified" and edge.dependent in affected
        ],
        "potential_recovery_blockers": [
            item
            for item in result.explanations
            if item.status == "affected"
            and any(token in item.node_id for token in ["power", "water", "telecom", "data"])
        ],
        "available_fallback_resources": resources,
        "missing_contingency_evidence": gaps,
        "suggested_planning_actions": actions,
        "evidence_refs": evidence_refs,
        "caveat": result.caveat,
        "state_changed": False,
    }
    base_url = os.getenv("OLLAMA_BASE_URL")
    model = os.getenv("OLLAMA_MODEL")
    if not base_url or not model:
        return assessment
    prompt = (
        "Write a concise continuity planning assessment using only the structured facts below. "
        "Return JSON with keys summary, suggested_planning_actions, evidence_refs. Do not change status, invent duration/capacity/probability, or state facts not in evidence. "
        "Every evidence_refs item must be copied exactly from the allowed list.\n"
        + json.dumps(assessment, ensure_ascii=False)
    )
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/api/chat",
                json={
                    "model": model,
                    "stream": False,
                    "format": "json",
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
        generated = json.loads(response.json().get("message", {}).get("content", "{}"))
        allowed = set(assessment["evidence_refs"])
        refs = generated.get("evidence_refs", [])
        if not isinstance(refs, list) or not set(refs).issubset(allowed):
            return assessment
        if isinstance(generated.get("summary"), str):
            assessment["summary"] = generated["summary"]
        if isinstance(generated.get("suggested_planning_actions"), list):
            assessment["suggested_planning_actions"] = [
                str(item) for item in generated["suggested_planning_actions"][:12]
            ]
        assessment["evidence_refs"] = refs
        assessment["mode"] = "local_ollama_grounded"
        assessment["human_review_required"] = True
        return assessment
    except (httpx.HTTPError, json.JSONDecodeError, ValueError, TypeError):
        return assessment
