from __future__ import annotations

from collections import defaultdict
from time import perf_counter

import networkx as nx

from continuitymap.models import (
    Edge,
    GroupMode,
    ImpactExplanation,
    InfrastructureGraph,
    SimulationResult,
    ValidationIssue,
    ValidationResult,
    VerificationStatus,
)

CAVEAT = (
    "Planning screen only: this result propagates declared, verified dependencies. "
    "It does not model physical damage, network flow, capacity, duration, restoration, or probability. "
    "Review assumptions and validate findings with service owners."
)


def validate_graph(graph: InfrastructureGraph) -> ValidationResult:
    issues: list[ValidationIssue] = []
    node_ids = [node.id for node in graph.nodes]
    edge_ids = [edge.id for edge in graph.edges]
    node_set = set(node_ids)
    duplicate_nodes = sorted({item for item in node_ids if node_ids.count(item) > 1})
    duplicate_edge_ids = sorted({item for item in edge_ids if edge_ids.count(item) > 1})
    unknown_ids = [item.id for item in graph.unknown_relationships]
    duplicate_unknown_ids = sorted({item for item in unknown_ids if unknown_ids.count(item) > 1})

    for node_id in duplicate_nodes:
        issues.append(
            ValidationIssue(
                severity="error",
                code="duplicate_node_id",
                message="Node ID is duplicated",
                object_id=node_id,
            )
        )
    for edge_id in duplicate_edge_ids:
        issues.append(
            ValidationIssue(
                severity="error",
                code="duplicate_edge_id",
                message="Edge ID is duplicated",
                object_id=edge_id,
            )
        )

    for unknown_id in duplicate_unknown_ids:
        issues.append(
            ValidationIssue(
                severity="error",
                code="duplicate_unknown_id",
                message="Unknown relationship ID is duplicated",
                object_id=unknown_id,
            )
        )

    duplicate_keys: dict[tuple[str, str, str, str], list[Edge]] = defaultdict(list)
    group_modes: dict[tuple[str, str], set[GroupMode]] = defaultdict(set)
    for edge in graph.edges:
        if edge.source not in node_set:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="missing_source",
                    message=f"Source node {edge.source!r} does not exist",
                    object_id=edge.id,
                )
            )
        if edge.dependent not in node_set:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="missing_dependent",
                    message=f"Dependent node {edge.dependent!r} does not exist",
                    object_id=edge.id,
                )
            )
        if edge.source == edge.dependent:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    code="self_dependency",
                    message="Self-dependency requires owner review",
                    object_id=edge.id,
                )
            )
        duplicate_keys[
            (edge.source, edge.dependent, edge.dependency_type.value, edge.group_id)
        ].append(edge)
        group_modes[(edge.dependent, edge.group_id)].add(edge.group_mode)
        for assumption in edge.assumptions:
            if assumption.support_status != "supported" or not assumption.evidence_ref:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        code="unsupported_assumption",
                        message=f"Assumption is not evidence-supported: {assumption.text}",
                        object_id=edge.id,
                    )
                )
        if edge.verification_status == VerificationStatus.VERIFIED and edge.last_validated is None:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    code="verified_without_date",
                    message="Verified relationship has no validation date",
                    object_id=edge.id,
                )
            )

    for (dependent, group_id), modes in group_modes.items():
        if len(modes) > 1:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="inconsistent_group_mode",
                    message=f"Dependency group {group_id!r} on {dependent!r} mixes ANY and ALL semantics",
                    object_id=dependent,
                )
            )

    for key, copies in duplicate_keys.items():
        if len(copies) > 1:
            statuses = {edge.verification_status for edge in copies}
            if len(statuses) > 1:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        code="contradictory_relationship",
                        message=f"Conflicting statuses for relationship {key[0]} → {key[1]}",
                        object_id=", ".join(edge.id for edge in copies),
                    )
                )
            else:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        code="duplicate_relationship",
                        message=f"Repeated relationship {key[0]} → {key[1]} in group {key[3]}",
                        object_id=", ".join(edge.id for edge in copies),
                    )
                )

    for unknown in graph.unknown_relationships:
        for node_id in [unknown.source, unknown.dependent]:
            if node_id not in node_set:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        code="missing_unknown_endpoint",
                        message=f"Unknown relationship references missing node {node_id!r}",
                        object_id=unknown.id,
                    )
                )
        for assumption in unknown.assumptions:
            if assumption.support_status != "supported" or not assumption.evidence_ref:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        code="unsupported_assumption",
                        message=f"Unknown relationship assumption lacks supporting evidence: {assumption.text}",
                        object_id=unknown.id,
                    )
                )

    verified = [
        edge for edge in graph.edges if edge.verification_status == VerificationStatus.VERIFIED
    ]
    digraph = nx.DiGraph()
    digraph.add_edges_from(
        (edge.source, edge.dependent)
        for edge in verified
        if edge.source in node_set and edge.dependent in node_set
    )
    cycles = list(nx.simple_cycles(digraph))
    for cycle in cycles:
        issues.append(
            ValidationIssue(
                severity="warning",
                code="dependency_cycle",
                message="Verified dependency cycle is handled by monotonic fixed-point propagation and should be reviewed: "
                + " → ".join(cycle + [cycle[0]]),
                object_id=cycle[0],
            )
        )

    errors = sum(issue.severity == "error" for issue in issues)
    return ValidationResult(
        valid=errors == 0,
        issues=issues,
        counts={
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
            "verified_edges": len(verified),
            "proposed_edges": sum(
                e.verification_status == VerificationStatus.PROPOSED for e in graph.edges
            ),
            "unknown_relationships": len(graph.unknown_relationships),
            "errors": errors,
            "warnings": sum(issue.severity == "warning" for issue in issues),
        },
    )


def simulate(
    graph: InfrastructureGraph, disrupted_nodes: list[str], scenario_name: str = "Custom disruption"
) -> SimulationResult:
    """Compute the least fixed point of failures under verified AND/OR edge groups."""
    started = perf_counter()
    node_map = {node.id: node for node in graph.nodes}
    invalid_seeds = [node for node in disrupted_nodes if node not in node_map]
    if invalid_seeds:
        raise ValueError("Unknown disrupted node(s): " + ", ".join(invalid_seeds))
    verified = [
        edge for edge in graph.edges if edge.verification_status == VerificationStatus.VERIFIED
    ]
    requirements: dict[str, dict[str, list[Edge]]] = defaultdict(lambda: defaultdict(list))
    for edge in verified:
        requirements[edge.dependent][edge.group_id].append(edge)

    failed = set(disrupted_nodes)
    explanation_by_node: dict[str, ImpactExplanation] = {}
    for node_id in disrupted_nodes:
        explanation_by_node[node_id] = ImpactExplanation(
            node_id=node_id,
            node_name=node_map[node_id].name,
            status="disrupted",
            reason="Explicitly selected as a scenario disruption seed.",
            path=[node_id],
        )

    changed = True
    while changed:
        changed = False
        for dependent, groups in requirements.items():
            if dependent in failed:
                continue
            for group_id, edges in groups.items():
                mode = edges[0].group_mode
                available_edges = [edge for edge in edges if edge.source not in failed]
                group_failed = (mode == GroupMode.ANY and not available_edges) or (
                    mode == GroupMode.ALL and len(available_edges) != len(edges)
                )
                if not group_failed:
                    continue
                causes = (
                    edges
                    if mode == GroupMode.ANY
                    else [edge for edge in edges if edge.source in failed]
                )
                failed_sources = [edge for edge in causes if edge.source in failed]
                cause = failed_sources[0] if failed_sources else edges[0]
                source_explanation = explanation_by_node.get(cause.source)
                path = (source_explanation.path if source_explanation else [cause.source]) + [
                    dependent
                ]
                edge_ids = (source_explanation.edge_ids if source_explanation else []) + [cause.id]
                reason = (
                    f"Required {mode} dependency group '{group_id}' ({cause.dependency_type.value}) has no available provider. "
                    if mode == GroupMode.ANY
                    else f"Required ALL dependency group '{group_id}' includes an unavailable provider. "
                )
                reason += f"Evidence: {cause.evidence}"
                explanation_by_node[dependent] = ImpactExplanation(
                    node_id=dependent,
                    node_name=node_map[dependent].name,
                    status="affected",
                    reason=reason,
                    path=path,
                    edge_ids=edge_ids,
                )
                failed.add(dependent)
                changed = True
                break

    uncertain_by_node: dict[str, list[str]] = defaultdict(list)
    for relationship in graph.unknown_relationships:
        if relationship.source in failed and relationship.dependent not in failed:
            uncertain_by_node[relationship.dependent].append(relationship.id)
    for edge in graph.edges:
        if (
            edge.verification_status in {VerificationStatus.PROPOSED, VerificationStatus.UNKNOWN}
            and edge.source in failed
            and edge.dependent not in failed
        ):
            uncertain_by_node[edge.dependent].append(edge.id)

    unaffected = sorted(set(node_map) - failed)
    for node_id, relationships in uncertain_by_node.items():
        if node_id in explanation_by_node:
            explanation_by_node[node_id].uncertainty_flags.extend(relationships)
        else:
            explanation_by_node[node_id] = ImpactExplanation(
                node_id=node_id,
                node_name=node_map[node_id].name,
                status="unaffected_review",
                reason="No official failure is inferred; an unverified relationship from a disrupted node merits owner review.",
                uncertainty_flags=relationships,
            )

    relevant_explanations = [
        explanation_by_node[node_id] for node_id in sorted(explanation_by_node)
    ]
    elapsed_ms = (perf_counter() - started) * 1000
    return SimulationResult(
        scenario_name=scenario_name,
        disrupted_nodes=disrupted_nodes,
        affected_nodes=sorted(failed),
        unaffected_nodes=unaffected,
        uncertain_review_nodes=sorted(uncertain_by_node),
        explanations=relevant_explanations,
        caveat=CAVEAT,
        processing_ms=round(elapsed_ms, 3),
    )
