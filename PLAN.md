# ContinuityMap implementation plan

## Goal

Deliver a hackathon-ready decision-support MVP that loads a fictional infrastructure graph, makes dependency evidence and review state visible, propagates declared outages deterministically with AND/OR dependency groups, supports safe AI-assisted review, and exports evidence-based planning documents.

## Phases

1. **Foundation — complete** — project instructions, architecture, data dictionary, version/license/source verification.
2. **Graph core — complete** — 43-node synthetic fixture, validation, deterministic simulator, reproducible scenarios and tests.
3. **Application — complete** — FastAPI, SQLAlchemy/PostgreSQL, graph import/edit APIs, React/Cytoscape interface, scenario and evidence review. Compose startup, PostgreSQL persistence after restart, browser flow, and PDF export passed.
4. **AI and reporting — implemented** — optional local Ollama integration, evidence-linked extraction/assessment, human review workflow, report PDF export.
5. **Evaluation and packaging — complete** — synthetic benchmark, diagrams and product/technical/business documents, 14-slide pitch deck with notes, startup/demo guide, authentic screenshots, limitations.

## MVP decisions

- Edge direction is provider `source` → service `dependent`.
- Dependencies are grouped by `group_id`; every group is a required condition. `ANY` means one provider in that group must remain available; `ALL` means every provider is required.
- Only human-verified edges propagate. Proposed/rejected/unknown relationships remain visible as review context.
- The simulator starts with an explicitly disrupted set and repeats checks until no new service is affected. It follows declared links and is not a physical prediction.
- Unknown capacity and timing are reported as unknown. No probabilistic failure rates are invented.
- PostgreSQL is the containerized default; SQLite supports fast local development and tests.
- Local inference is optional through Ollama. The product remains usable without a model, with extraction clearly labeled as heuristic and narrative generated from structured evidence.

## Acceptance checks

- A fictional network of at least 30 nodes and declared scenarios are bundled.
- Graph integrity checks cover reference errors, duplicate relationships, invalid types, contradictions, and cycles.
- Tests use hand-computed propagation fixtures, redundancy, uncertainty, cycles, disconnected components, missing suppliers, and simultaneous disruptions.
- UI allows selection, inspect/edit/verify, run scenarios, inspect impact explanations, and review proposals.
- Exports include requested idea, pitch, architecture, technical, business, and evaluation artifacts.
- Startup, evaluation boundaries, assumptions, and unfinished items are explicit in README and DEMO_GUIDE.

## Audience and API handoff

- General readers start with the short explanation and Northbank example in `README.md` or `DEMO_GUIDE.md`.
- Service owners can check relationship fields and review states in `docs/DATA_DICTIONARY.md`.
- Developers can inspect architecture, API routes, and the OpenAPI schema in `ContinuityMap_Technical_Design.md` and `/docs`.
- AI agents have a curl and JSON example in `AI_AGENT_GUIDE.md`, plus explicit instructions to preserve evidence, keep uncertain paths separate, and never approve relationships on their own.
- Generated brief, business case, evaluation report, and presentation explain technical terms and assumptions in plain language while retaining technical detail where useful.
