# ContinuityMap progress

## Status

MVP implementation and handoff artifacts completed on 2026-10-26. The workspace began empty and without a Git repository. The app is deliberately framed as synthetic planning support; it is not a real-time infrastructure prediction product.

## Reader-focused documentation review — 2026-10-27

- Added plain-language introductions, a consistent Northbank outage example, and brief definitions for verified/proposed/unknown relationships and ANY/ALL backup rules.
- Reworked the idea brief, demo walkthrough, technical design, data dictionary, research register, business case, evaluation report, architecture diagram, and 14-slide deck to make the first explanation understandable without graph or AI terminology.
- Added `AI_AGENT_GUIDE.md` with runnable API examples, response-field meanings, evidence-handling rules, and explicit limits on automated approvals.
- Rewrote all 14 speaker notes as spoken explanations and made `data/deck_content.json` the pitch deck source of truth, so generated slides and notes stay editable in one place.
- Regenerated DOCX, PDF, PPTX and deck PDF. Visual inspection confirmed the idea brief remains 8 pages, business case 3 pages, evaluation report 3 pages, and pitch deck 14 pages. All 14 PPTX slides contain substantive speaker notes.

## Research and technology decisions

- `docs/SOURCES.md` records the source register, findings, licenses, version snapshot, and research limits. Research covers NATO's 2026 Resilience Baseline Requirements, NIST SP 800-34, FEMA continuity guidance, CISA/FEMA cyber incident planning, public dependency research, and Everbridge's publicly stated capabilities.
- PostgreSQL plus SQLAlchemy and NetworkX is sufficient for this MVP. No graph database was added for appearance. PostgreSQL 18.6 container storage uses its current `/var/lib/postgresql` mount layout.
- Current dependency and security checks are snapshots dated 2026-10-26. The npm audits reported zero vulnerabilities; pip-audit reported no known Python dependency advisories and skipped the unpublished local project. `psycopg` is in the LGPL-3.0 family and merits redistribution review.
- Everbridge publicly describes service/dependency mapping and resilience workflows, so differentiation is scoped to editable evidence, human validation, explicit unknowns, and deterministic transparent scenario rules—not generic maps or crisis dashboards.

## Implemented

- FastAPI/Pydantic API, SQLAlchemy persistence, SQLite development mode, PostgreSQL Docker mode, audit records, graph import/edit/validation, simulation, AI helper endpoints, and PDF report endpoints.
- React/TypeScript/Cytoscape client with service and relationship inspection, review filters, evidence views, relationship creation and verification, scenario selector, graph import, fictional-plan upload, planning assistant, and report downloads.
- Deterministic NetworkX engine with `ANY` / `ALL` groups, cycle handling, fixed-point propagation, verified-edge gating, and separate unverified review paths.
- Ollama-compatible local inference is optional. The no-model path remains available; the heuristic extractor is expressly labeled and sends proposals to human review.
- Bundled Northbank fictional network: 43 nodes, 80 relationships (78 verified, 1 proposed, 1 rejected), explicit unknown relationships, three reproducible scenarios, recovery resources, and contradictory statements for review.
- Data dictionary, synthetic extraction/review fixtures, evaluation script, detailed technical design, architecture SVG, idea DOCX/PDF, 14-slide PowerPoint with 14 speaker-note slides, companion deck PDF, business case PDF, evaluation report PDF, walkthrough guide, and AI agent guide.
- Authentic browser captures: `reports/ContinuityMap_Demo_Screenshot.png` and `reports/ContinuityMap_Assessment_Screenshot.png`.

## Verification results

- Backend: 29 tests passed; Ruff passed. Tests cover graph integrity, unknown metadata and migration, redundancy, cycles, disconnected nodes, simultaneous disruptions, API review states, reports, and AI fallback. One upstream Starlette deprecation warning recommends `httpx2` for `TestClient`.
- Frontend TypeScript/Vite production build passed; npm audit reported zero vulnerabilities. Vite warns that the bundled Cytoscape client chunk is about 703 kB before gzip (219 kB gzip).
- Root deck dependency audit reported zero vulnerabilities after overriding PptxGenJS's affected `image-size` transitive dependency to 2.0.4.
- Synthetic evaluation: graph integrity passed (0 errors / 0 warnings); three scenario fixtures matched expected result sets; proposed and unknown edges produced zero official failed-service statuses; 5/5 synthetic review-state transitions passed; extraction was 5/5 on five simple synthetic sentences; evidence reference coverage was 35/35. These are implementation checks on fixed fixtures, not proof of human accuracy or customer-document performance.
- Scenario processing median was about 0.043 ms and p95 about 0.054 ms in the local run. This is hardware-specific and informational only.
- PDF inspection found 8 idea pages, 3 business-case pages, 3 evaluation pages, and 14 deck pages. The DOCX and PPTX were also exported through LibreOffice for layout checks; both rendered to 8 and 14 pages respectively. All 14 PPTX slides have notes.
- Browser smoke check against the Compose UI/API loaded the network, ran the substation case with a fixed-fixture match, opened the assessment, and reported no browser console errors. The generated impact PDF endpoint was also exercised.
- Full Docker Compose build/start validation passed on 2026-10-26: Postgres 18.6 became healthy, the API seeded and loaded the 43-node graph with zero validation issues, the UI loaded, the fixed substation scenario matched, and the API returned a valid impact-report PDF. The Postgres named volume is mounted at `/var/lib/postgresql` for the version 18 image layout.

## Remaining boundaries

- All owners, places, service relationships, evidence, and forecasts are fictional. The prototype has no authentication, authorization, tenant separation, hardened public upload isolation, production secret management, high availability, security certification, or customer data governance controls.
- Human relationship accuracy, model quality, customer adoption, and financial assumptions have not been validated with a pilot or user study. The small extraction set does not establish general extraction precision or recall.
- No model is bundled or pulled by default. Model choice and model-specific licensing must be reviewed by the deploying organization.
- The graph does not model physical damage, shared-cause failure, capacity, timing, flow, thresholds, service duration, or restoration. Unstated values remain unknown.
- A customer rollout depends on site-specific discovery, accountable service owners, source access, and repeated data validation; accurate dependencies are the core implementation challenge.
