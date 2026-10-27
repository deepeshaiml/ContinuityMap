from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NodeCategory(StrEnum):
    SERVICE = "service"
    FACILITY = "facility"
    ASSET = "asset"
    RECOVERY = "recovery_resource"


class DependencyType(StrEnum):
    POWER = "power"
    WATER = "water"
    TELECOM = "telecommunications"
    DATA = "data_connectivity"
    TRANSPORT = "transport"
    FUEL = "fuel"
    STAFF = "staffing"
    OTHER = "other"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    PROPOSED = "proposed"
    UNKNOWN = "unknown"
    REJECTED = "rejected"


class GroupMode(StrEnum):
    ANY = "ANY"
    ALL = "ALL"


class Assumption(BaseModel):
    text: str
    support_status: str = "unverified"
    evidence_ref: str | None = None


class Node(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    name: str
    category: NodeCategory
    sector: str
    description: str
    capacity: float | None = None
    capacity_unit: str | None = None
    criticality: str = "medium"
    aliases: list[str] = Field(default_factory=list)
    fictional: bool = True


class Edge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source: str
    dependent: str
    dependency_type: DependencyType
    evidence: str
    evidence_ref: str
    verification_status: VerificationStatus
    owner: str
    conditions: list[str] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    last_validated: date | None = None
    group_id: str
    group_mode: GroupMode = GroupMode.ANY

    @field_validator("source", "dependent", "group_id", "id", "owner", "evidence_ref")
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class UnknownRelationship(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source: str
    dependent: str
    dependency_type: DependencyType | None
    question: str
    evidence: str
    verification_status: Literal["unknown"] = "unknown"
    owner: str
    evidence_ref: str
    conditions: list[str] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    last_validated: date | None = None

    @field_validator("id", "source", "dependent", "question", "evidence", "owner", "evidence_ref")
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class Scenario(BaseModel):
    id: str
    name: str
    description: str
    disrupted_nodes: list[str]
    expected_affected: list[str] = Field(default_factory=list)
    review_actions: list[str] = Field(default_factory=list)


class InfrastructureGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str
    title: str
    synthetic_notice: str
    nodes: list[Node]
    edges: list[Edge]
    unknown_relationships: list[UnknownRelationship] = Field(default_factory=list)
    scenarios: list[Scenario] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationIssue(BaseModel):
    severity: str
    code: str
    message: str
    object_id: str | None = None


class ValidationResult(BaseModel):
    valid: bool
    issues: list[ValidationIssue]
    counts: dict[str, int]


class ScenarioRequest(BaseModel):
    scenario_id: str | None = None
    disrupted_nodes: list[str] | None = None


class ImpactExplanation(BaseModel):
    node_id: str
    node_name: str
    status: str
    reason: str
    path: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    uncertainty_flags: list[str] = Field(default_factory=list)


class SimulationResult(BaseModel):
    scenario_name: str
    disrupted_nodes: list[str]
    affected_nodes: list[str]
    unaffected_nodes: list[str]
    uncertain_review_nodes: list[str]
    explanations: list[ImpactExplanation]
    caveat: str
    processing_ms: float
    evaluation: dict[str, Any] = Field(default_factory=dict)
