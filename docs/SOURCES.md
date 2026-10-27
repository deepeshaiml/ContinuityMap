# Research and software source register

Research and package snapshots checked **2026-10-26**. Stable version pins are recorded for reproducibility. Recheck official release and security pages before any production deployment.

## Plain-language summary

Public resilience guidance supports looking at how essential services depend on one another. That supports the problem ContinuityMap explores; it does **not** certify this product or prescribe its data model. NIST SP 800-34 focuses on information-system contingency planning, while FEMA and CISA/FEMA materials offer broader continuity and upstream/downstream planning guidance. NATO’s 2026 baseline discusses interdependencies across essential sectors. Everbridge publicly advertises existing dependency-mapping and continuity features, so ContinuityMap does not claim that maps or dashboards are new. Its proposed distinction—editable links with visible evidence and review state, plus repeatable rule-based scenarios—still needs buyer validation.

This page is the technical source register. The [Idea Document](../ContinuityMap_Idea_Document.pdf) and [Pitch Deck](../ContinuityMap_Pitch_Deck.pdf) give the shorter explanation for general audiences.

## Resilience and product research

1. **NATO, 2026 Resilience Baseline Requirements**, published 2026-09-15. The revision discusses cross-sector interdependencies and cascading effects and includes requirements for energy, civil communications, and transportation resilience. It is national resilience policy text, not a software specification. [Official NATO text](https://nato.int/en/about-us/official-texts-and-resources/official-texts/2026/09/15/2026-resilience-baseline-requirements)
2. **NIST SP 800-34 Rev. 1, Contingency Planning Guide for Federal Information Systems.** Practical system contingency planning and recovery guidance, published 2010; NIST shows a 2023 planning note. This is not a cross-sector physical infrastructure propagation model. [NIST publication](https://csrc.nist.gov/pubs/sp/800/34/r1/upd1/final)
3. **FEMA, Continuity Guidance Circular, 2018 (2024 update).** Guidance identifies essential functions and asks planners to consider functions that support or are supported by others. [FEMA PDF](https://www.fema.gov/sites/default/files/documents/fema_continuity-guidance-circular_082024.pdf)
4. **CISA/FEMA, Planning Considerations for Cyber Incidents (2023).** Includes upstream, internal, and downstream dependency examples and questions. [CISA-hosted PDF](https://www.cisa.gov/sites/default/files/2024-01/2023_fema_planning-considerations-cyber-incidents.pdf)
5. **CISA Infrastructure Dependency Primer, implementation resources.** Public materials for integrating dependency risk assessment into resilience planning. [CISA](https://www.cisa.gov/topics/critical-infrastructure-security-and-resilience/resilience-services/infrastructure-dependency-primer/implement)
6. **Everbridge 360 AI Bridge (official product page).** Everbridge publicly describes important service/dependency mapping, impact tolerance, gap identification, resilience dashboards, and links to response workflows. ContinuityMap therefore does not claim mapping or crisis coordination as novel; customer fit and feature comparisons still require buyer-led evaluation. [Everbridge Bridge](https://www.everbridge.com/products/bridge/)
7. **“Redefining dependencies/interdependencies of critical infrastructure: a systematic review of the existing knowledgebase,”** *Sustainable and Resilient Infrastructure* (2024). The review describes fragmented categories and how direction can be overlooked when dependency and interdependency labels are conflated. It supports an explicit source→dependent model, not a claim that one universal taxonomy has been settled. [DOI / article abstract](https://doi.org/10.1080/23789689.2024.2403885)
8. **Overview of Interdependency Models of Critical Infrastructure for Resilience Assessment**, *Natural Hazards Review* (2022). Review of modeling challenges and methods. [Article page](https://www.cse.lehigh.edu/~brian/pubs/2022/naturalhazardsreview/)

## Technology snapshot and licensing notes

Current releases were inspected in package indexes/official version pages on 2026-10-26. The repository pins exact application dependencies. A pinned version is a snapshot, not a promise to update itself.

| Component | Pinned version | License note | Role |
|---|---:|---|---|
| Python | 3.12.13 | PSF License; active maintenance branch | Runtime chosen for broad dependency compatibility. Python 3.14.10 is current, but not selected for this hackathon build. |
| FastAPI | 0.162.0 | MIT | API and schema docs. |
| Uvicorn | 0.54.0 | BSD-3-Clause | ASGI server. |
| Pydantic | 2.14.1 | MIT | Import/API validation. |
| SQLAlchemy | 2.1.6 | MIT | Relational persistence. |
| psycopg + psycopg-binary | 3.3.6 | LGPL-3.0 family | PostgreSQL DBAPI; commercially usable, but redistribution should be reviewed for LGPL compliance. |
| HTTPX | 0.28.1 | BSD-3-Clause | Ollama HTTP client; also used by Starlette's test client. |
| python-multipart | 0.0.32 | Apache-2.0 | Upload form parsing. |
| NetworkX | 3.7 | BSD-3-Clause | Directed graph validation and propagation. |
| PostgreSQL | 18.x (`postgres:18.6-alpine`) | PostgreSQL License; supported major line | Database; official policy shows support through 2030-11-14 and recommends current minor 18.6 as of this check. |
| React / React DOM | 19.3.1 | MIT | UI. |
| TypeScript | 7.0.2 | Apache-2.0 | Typed client. |
| Vite | 8.3.5 | MIT | Client build and local dev server. |
| Cytoscape.js | 3.34.4 | MIT | Interactive network graph. |
| Lucide React | 1.61.0 | ISC | Interface icons. |
| PptxGenJS | 4.0.1 | MIT | PowerPoint generation, including speaker notes. |
| Playwright (development) | 1.64.1 | Apache-2.0 | Browser smoke flow and authentic screenshots. |
| pytest / Ruff (development) | 9.1.1 / 0.17.2 | MIT / MIT | Backend tests and lint. |
| Ollama (optional container) | 0.40.11 | MIT | Local model serving; no model is bundled. Individual model terms vary. |
| python-docx | 1.2.0 | MIT | Idea document. |
| ReportLab | 5.1.0 | BSD license | PDF reports and documents. |
| pypdf | 6.21.2 | BSD-3-Clause | PDF parsing and artifact inspection. |
| Node.js | 22.x image | MIT | Frontend container runtime; satisfies Vite 8 engine requirement. |

Key release/support sources: [Python 3.14.10 release](https://www.python.org/downloads/release/python-31410/), [FastAPI release notes](https://fastapi.tiangolo.com/release-notes/), [React versions](https://react.dev/versions), [PostgreSQL version policy](https://www.postgresql.org/support/versioning/), [SQLAlchemy PostgreSQL dialects](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html), [Psycopg license](https://github.com/psycopg/psycopg/blob/master/LICENSE.txt). Package licenses should be checked again in the final redistribution SBOM.

The PostgreSQL 18 official container changes `PGDATA` and its declared volume to `/var/lib/postgresql/18/docker` and `/var/lib/postgresql`; Compose mounts the parent directory so the named volume persists across recreation. The optional Ollama image is pinned to the current 0.40.11 release, and no model is pulled automatically. [Official PostgreSQL Docker image guidance](https://hub.docker.com/_/postgres), [Ollama Docker tags](https://hub.docker.com/r/ollama/ollama/tags)

## Compatibility and security checks

- Local implementation used Python 3.12.13, Node 26.9.0, npm 11.19.1, Docker 29.6.2 / Compose 5.3.1.
- `FastAPI 0.162.0 + Pydantic 2.14.1 + SQLAlchemy 2.1.6 + NetworkX 3.7` installed successfully on Python 3.12.
- Vite 8.3.5 declares Node `^20.19.0 || >=22.12.0`; the container uses Node 22. React 19 and Cytoscape.js built together.
- `npm audit` on frontend and root deck-generation dependencies found **0 vulnerabilities** after remediation.
- Initial root `npm audit` surfaced two high-severity `image-size` advisories because PptxGenJS 4.0.1 resolves `image-size` 1.2.1. The advisories identify versions through 2.0.2 as affected and 2.0.3 as patched. This project pins an npm override to `image-size` 2.0.4 and verifies the deck still generates; final audit reports zero advisories. [JXL/HEIF advisory](https://github.com/advisories/GHSA-5p2g-fcmc-qvqq), [ICNS advisory](https://github.com/advisories/GHSA-w3rx-r6r6-pgpr)
- `pip-audit --desc` found no known advisories in installed Python dependencies; it skipped the editable `continuitymap==0.1.0` project itself because it is not a PyPI package. `npm audit` is registry snapshot-based and should be repeated during release.

No security certification, full license opinion, or production threat review has been completed. The default Compose password is a demo convenience and must be replaced in any shared environment.
