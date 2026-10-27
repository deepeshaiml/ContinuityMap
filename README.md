# ContinuityMap

**A planning workspace that helps teams see which essential services depend on one another and explore a clearly defined “what if?” disruption.**

ContinuityMap is a hackathon prototype for resilience planners and service owners. It brings service relationships, their supporting evidence, open questions, and simple disruption exercises into one reviewable place.

> **Important boundary:** This demo uses an invented city and invented records. It follows owner-confirmed relationships in a graph; it does not predict real outages, damage, service duration, or restoration. Do not upload real infrastructure plans or expose this development build to the internet.

## The idea in one example

Imagine the fictional Northbank Substation Alpha loses power. In the demo’s declared graph:

- The model infers no failed path to water treatment because its power group says **either** Substation Alpha **or** the Civic Solar Microgrid is enough. The app flags this backup rule for owner review; the service is not confirmed operational.
- A hospital is marked unavailable in the exercise because its declared electronic health-records path runs through a data center powered by Substation Alpha. This is a logical result from the recorded links, not a claim about what a real hospital would do.
- Two possible links are marked for owner review. They are **not** counted as failed services.

The demo lists 17 unavailable entries: the disrupted substation plus 16 downstream results. This number is a property of the fictional graph and its rules.

## Who should start where

- **General audience / decision makers:** read [DEMO_GUIDE.md](DEMO_GUIDE.md), then the [Idea Document](ContinuityMap_Idea_Document.pdf).
- **Resilience planners / service owners:** start with the demo guide and [Data Dictionary](docs/DATA_DICTIONARY.md). The dictionary explains each relationship and review status.
- **Developers / technical reviewers:** see [Technical Design](ContinuityMap_Technical_Design.md), [Architecture](ContinuityMap_Architecture.svg), and [OpenAPI](http://localhost:8000/docs) after startup.
- **AI agents / API clients:** follow [AI Agent Guide](AI_AGENT_GUIDE.md). It gives safe request examples and explains which fields are evidence and which results are only review prompts.
- **Commercial or funding reviewers:** see [Business Case](ContinuityMap_Business_Case.pdf), [Pitch Deck](ContinuityMap_Pitch_Deck.pdf), and the research [Sources](docs/SOURCES.md).
- **Evaluation reviewers:** see [Evaluation Report](ContinuityMap_Evaluation_Report.pdf) and [PROGRESS.md](PROGRESS.md) for tests and limits.

## Run the demonstration

Requirements: Docker Engine/Desktop with Compose v2.

```bash
docker compose up --build
```

Open [http://localhost:5173](http://localhost:5173). The API’s interactive reference is at [http://localhost:8000/docs](http://localhost:8000/docs). PostgreSQL stores the demo graph in a named volume. Stop with `Ctrl+C`; `docker compose down` keeps that volume, and `docker compose down -v` deletes it.

If those ports are already in use, try:

```bash
API_PORT=8001 WEB_PORT=5174 VITE_API_URL=http://localhost:8001 docker compose up --build
```

For local development, use Python 3.12 and Node 22.12 or newer:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e 'backend[dev]'
(cd backend && ../.venv/bin/uvicorn continuitymap.main:app --reload)
```

In a second terminal:

```bash
(cd frontend && npm ci && npm run dev)
```

Local development uses SQLite. To recreate the fictional network, run `.venv/bin/python scripts/generate_synthetic_data.py`.

## What the prototype can do

- Load and validate a 43-node fictional service network with 80 relationship records and three fixed exercises.
- Show who provides a service and which services rely on it, alongside evidence, owner, conditions, and review status.
- Keep four relationship states separate: **verified** (owner-confirmed and used in exercises), **proposed** (waiting for review), **unknown** (an open question), and **rejected** (a claim declined by a reviewer).
- Model simple backup rules: **ANY** means one provider is enough; **ALL** means every listed provider is required.
- Flag services whose declared **ANY** backup rule was used in a scenario, and state that backup capacity, runtime, and shared upstream dependencies were not checked.
- Track an owner review due date for each relationship; overdue dates appear as warnings and do not silently change relationship status.
- Let users inspect and edit the graph, run an exercise again, and export impact, gap, and human-review PDFs.
- Offer optional local Ollama document suggestions and continuity summaries. Without a local model, a labeled rule-based/template path is used.

## Words used in the app

| Term | Plain meaning |
|---|---|
| Node | A service, facility, asset, or recovery resource. |
| Dependency | A recorded statement that one service needs another resource or service. |
| Provider → dependent | The arrow points from the supplier/resource to the service that relies on it. |
| Verified | A human reviewer approved the relationship and its evidence. |
| Proposed / unknown | A candidate relationship / a question that has not been resolved. Neither changes official exercise status. |
| Scenario | A “what if this named resource is unavailable?” planning exercise. |
| Review path | An uncertain relationship to check with its owner; it is not a calculated failure. |
| No impact inferred | No failed path was found in the current verified graph; this does not confirm service availability. |
| Backup review | A declared alternative provider kept a service outside the model's affected set; owner review is needed for capacity, runtime, and shared dependencies. |

## Safety, security, and product limits

The importer accepts only nodes marked fictional. All bundled places, owners, evidence, services, and statements are invented. The prototype has no user login, role permissions, tenant separation, production secret management, hardened upload isolation, high availability, or security certification. Keep it on a trusted local development environment and use only bundled fictional content.

AI can suggest relationships and draft evidence-backed summaries, but it cannot verify a relationship or change a service’s calculated status. Model output can still be wrong. A real deployment would need customer-specific data agreements, identity and access controls, threat review, secure document handling, and validation by accountable service owners.

## Useful files

- [Five-minute walkthrough](DEMO_GUIDE.md)
- [Technical Design](ContinuityMap_Technical_Design.md)
- [Data Dictionary](docs/DATA_DICTIONARY.md)
- [AI Agent Guide](AI_AGENT_GUIDE.md)
- [Architecture SVG](ContinuityMap_Architecture.svg)
- [Idea Document DOCX](ContinuityMap_Idea_Document.docx) and [PDF](ContinuityMap_Idea_Document.pdf)
- [Pitch Deck PPTX](ContinuityMap_Pitch_Deck.pptx) and [PDF](ContinuityMap_Pitch_Deck.pdf)
- [Business Case PDF](ContinuityMap_Business_Case.pdf)
- [Evaluation Report PDF](ContinuityMap_Evaluation_Report.pdf)
- [Sources and version/license notes](docs/SOURCES.md)

## Development checks

```bash
(cd backend && ../.venv/bin/python -m pytest -q && ../.venv/bin/ruff check .)
(cd frontend && npm run build && npm audit)
.venv/bin/python scripts/evaluate.py
```

Evaluation results describe fixed fictional test cases only. See [PROGRESS.md](PROGRESS.md) for the verified state and known limits.
