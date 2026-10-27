# ContinuityMap project guidance

- Keep all included infrastructure data fictional and clearly labeled as synthetic.
- Treat the system as planning support. Never present deterministic graph propagation as a physical forecast.
- Only `verified` dependency edges participate in official scenario results. Proposed and unknown relationships may add uncertainty/review notes, never a failed service status.
- Preserve provenance on every dependency: source evidence, owner, assumptions, and validation date.
- Keep the core simulation deterministic and independently testable from HTTP, persistence, and any LLM.
- LLM output may create review proposals or evidence-backed narrative only. It must not mutate verified edges or service status.
- Prefer stable, maintained, permissively licensed components. Record pinned versions and source/limitations in technical documentation.
- Do not include operational details for real critical infrastructure.

## Commands

- Backend: `cd backend && python -m pytest`
- Backend lint: `cd backend && ruff check .`
- Frontend: `cd frontend && npm run build`
- Full local stack: `docker compose up --build`
