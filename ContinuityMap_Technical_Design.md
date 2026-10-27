# ContinuityMap technical design

**Status:** hackathon MVP · **Data boundary:** fictional demonstration only · **As of:** 2026-10-26

## Quick explanation

ContinuityMap is a service inventory with evidence attached to each dependency, plus a calculator for repeatable “what if?” exercises. It follows only relationships that a human has marked **verified**. AI can suggest a relationship or draft a summary, but it cannot approve a relationship or change a service’s result.

### Worked example

In the fictional Northbank data, the declared path is:

```text
Northbank Substation Alpha
        ↓ powers
Municipal Data Center
        ↓ hosts
Shared Health Records
        ↓ supports
Northbank General Hospital
```

The arrows represent verified statements in the demo data. If the scenario marks Alpha unavailable, the engine follows the path and marks dependent services unavailable when their declared rules are no longer satisfied. The hospital generator keeps the hospital’s separate power requirement satisfied, but it does not replace the required health-records path in this graph. The water-treatment power group is **ANY**: either Alpha or the Civic Solar Microgrid satisfies the declared rule. The model therefore infers no failed path to water treatment and flags the backup rule for owner review; it does not confirm service availability.

This answer means “unavailable under these recorded links and rules.” It does not estimate power flow, generator runtime, hospital operating behavior, or actual physical outcomes. A **review path** is an open question for an owner; it is not a failure result. **No impact inferred** means the graph found no failed path, not that the service is confirmed operating. **Backup review** asks an owner to confirm capacity, runtime, and shared upstream dependencies.

### Plain-language term map

| Technical term | Meaning here |
|---|---|
| Node | A service, facility, asset, or recovery resource. |
| Edge / relationship | A recorded statement that one node provides something another needs. |
| Source → dependent | Provider → service that relies on it. |
| Provenance | The evidence quote, source reference, owner, and validation date behind a relationship. |
| Deterministic | The same graph and same starting disruption give the same calculated result. |
| Fixed-point propagation | Recheck the declared links until one full pass finds no newly affected service. |
| `ANY` / `ALL` | One declared provider satisfies the rule / every declared provider is needed. |

## Product boundary

ContinuityMap stores declared infrastructure relationships and runs deterministic planning exercises. A result means “this service is unavailable under the currently verified dependency declarations and selected disruption seeds.” It does not predict physical damage, power/water flow, capacity, service duration, probability, restoration time, common-cause effects, human response, or actual public safety outcomes.

Only `verification_status=verified` edges participate in status propagation. A proposed, unknown, or rejected relationship cannot independently make a service unavailable. Open relationships from a disrupted source add an amber review marker. If a scenario relies on a surviving `ANY` provider, the dependent is listed in `backup_review_nodes` for review of capacity, runtime, and shared upstream dependencies. No AI output mutates graph state or recovery procedures.

## Architecture

See [`ContinuityMap_Architecture.svg`](ContinuityMap_Architecture.svg). The MVP uses React/TypeScript and Cytoscape.js, FastAPI/Pydantic, a pure NetworkX analysis service, SQLAlchemy with PostgreSQL, and optional local Ollama inference. SQLite is used in local development and tests. PostgreSQL is the Compose deployment default. No graph database is needed at this scale.

### Runtime components

1. **Web client:** inventory, dependency map, status filters, evidence drawer, scenario selector, review form, and PDF downloads.
2. **FastAPI API:** graph read/import/validation, proposal create/update, scenario simulation, upload extraction, planning assessment, PDF report endpoints, and audit events. OpenAPI at `/docs` lets developers and software agents inspect request and response fields.
3. **Domain service:** Pydantic validation plus NetworkX cycle checks and deterministic fixed-point propagation. Kept independent of database and model calls.
4. **Persistence:** relational node, edge, unknown-question, scenario, dataset manifest, and audit-event tables. Payload JSON columns preserve schema evolution; edge endpoints have foreign keys.
5. **Local AI adapter:** optional Ollama `/api/chat` integration. Uploaded content is parsed in memory and is not retained as a source document. Extracted quote, evidence reference, and proposal become graph records only after parsing.

## Data model

See [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md). Edge direction is provider/source → dependent. Each edge stores dependency type, evidence, source reference, verification status, owner, conditions, assumptions, last validation, owner review due date, `group_id`, and `group_mode`.

For agent-facing API examples and safe automated behavior, see [`AI_AGENT_GUIDE.md`](AI_AGENT_GUIDE.md). For a first-time human walkthrough, see [`DEMO_GUIDE.md`](DEMO_GUIDE.md).

Open unknowns are separate review records with source, dependent, dependency type (nullable only when the type itself is unknown), question/evidence, fixed `unknown` status, owner, reference, conditions, assumptions, and last-validation date. The cited question is evidence that the relationship remains unresolved; it is not proof of a dependency.

For a dependent service, each dependency group must be satisfied:

- `ANY`: at least one listed provider is outside the disruption set.
- `ALL`: every listed provider is outside the disruption set.

Multiple groups on one dependent are cumulative. The schema rejects missing node references on import, mixed group modes, duplicate IDs, and conflicting statuses for the same relationship key. Duplicate relationships, cycles, unsupported assumptions, missing validation dates, and overdue owner review dates are surfaced as review warnings/errors. An overdue relationship remains in calculations until an owner updates its status. Cycles are processed without unbounded looping and reported for owner review.

## Simulation algorithm

1. Validate that each explicit disruption seed exists.
2. Initialize the unavailable set with only those seeds.
3. For each dependent and each verified group, check `ANY`/`ALL` satisfaction against the current unavailable set.
4. When a required group is unsatisfied, add the dependent and record the triggering edge and path.
5. Repeat until a full pass adds no node.
6. Evaluate proposed and unknown relationships separately. If their source is unavailable and their target did not otherwise fail, return the target as `unaffected_review` with uncertainty flags.
7. Identify surviving `ANY` groups where a disrupted provider caused the scenario to rely on another listed provider; return their dependents in `backup_review_nodes`.
8. Return `affected_nodes`, `unaffected_nodes` (shown in the UI as “No impact inferred”), `backup_review_nodes`, evidence-linked trace explanations, other review nodes, caveat, and local processing time.

Because the unavailable set only grows, the process stops after at most one successful addition per node. In graph notation, `|V|` means the number of nodes. The semantics are intentionally binary and qualitative. No numeric capacity is consumed and no duration threshold is inferred.

## API surface

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/health`, `/api/graph`, `/api/audit` | Health, current graph plus integrity result, recent audit events. |
| `PUT` | `/api/graph/import` | Replace the graph after fictional-only and integrity validation. |
| `POST` | `/api/graph/validate` | Run graph validation. |
| `POST` | `/api/scenarios/run` | Execute a saved scenario or explicit disruption set. |
| `POST` | `/api/edges` | Add a proposed relationship only. |
| `PUT` | `/api/edges/{id}` | Edit, verify, or reject a relationship while retaining evidence fields. |
| `POST` | `/api/documents/extract` | Parse a bounded upload and persist only proposed relationships. |
| `POST` | `/api/assistant/assessment` | Return a structured, non-mutating, evidence-referenced assessment. |
| `GET` | `/api/reports/*.pdf` | Impact, gap, and human review checklist exports. |

The development API has no authentication and accepts only nodes marked fictional. It must not be exposed publicly or used for real infrastructure records.

## AI behavior

Supported uploads: TXT, Markdown, CSV, PDF, and DOCX; 2 MB maximum; 80,000 extracted characters. The local model prompt includes graph node IDs and requests explicit claims with verbatim evidence. Returned endpoints must exist and cited evidence must appear in the document. Model failures fall back to a deterministic entity/trigger heuristic and the response labels that mode. All results remain `proposed` with owner assignment required.

The assessment starts from simulation and graph records. A local model may rewrite the summary and action list; its evidence references must be from the known allowed list. If model output fails validation or its references are unknown, the service returns its structured evidence template. The user must review every result; this is not an autonomous planning or readiness system.

## Deployment and data handling

- Compose services: PostgreSQL 18, FastAPI, Vite dev server, and optional Ollama profile.
- Python API can use SQLite locally; database URL is controlled through `DATABASE_URL`.
- No cloud inference or third-party data upload is configured.
- Source uploads are parsed in memory; extracted relationship evidence is stored in PostgreSQL.
- The Compose password is a demo default. Set `POSTGRES_PASSWORD` privately before any shared environment.
- Add identity, role-based graph edit/verify permissions, tenant isolation, secret management, database backups, event retention, encrypted transport/storage, upload scanning, and security monitoring before production.

## Evaluation and test design

`backend/tests` covers fixed scenario sets, ANY/ALL redundancy, simultaneous disruption, cycles, missing nodes, disconnected nodes, unsupported assumptions, contradictions, proposed/unknown exclusion, API workflow, document proposals, PDF responses, and fictional-only import. `scripts/evaluate.py` measures synthetic extraction precision/recall, verification-state transition correctness, provenance completeness, fixture exact matches, unverified propagation rate, uncertainty preservation, latency, evidence-reference validity, and report section completeness.

The evaluation report records the current local snapshot. Its 5-sentence extraction set is clean and synthetic; 100% scores are fixture behavior, not general extraction quality. Latency is hardware-specific. Citation ID resolution does not prove narrative truth. Customer data requires a separately adjudicated benchmark.

## Technology selection snapshot

Pinned versions, license notes, security check, and official sources are in [`docs/SOURCES.md`](docs/SOURCES.md). PostgreSQL and NetworkX meet the MVP need; no Neo4j, embedding model, or cloud service is included. An embedding model is not necessary for this small entity catalog and document upload workflow.
