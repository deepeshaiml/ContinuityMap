# ContinuityMap API guide for AI agents and automation

This guide is for an AI assistant, script, or other API client that needs to read the fictional ContinuityMap demo. It uses everyday explanations first and API details second.

## Non-negotiable boundary

This development instance contains invented Northbank data only. Do not send real facility, network, supplier, continuity-plan, or emergency-operation details to it. The API has no authentication or access controls and is not a production service.

An agent may **read**, **summarize**, and **propose**. It must not claim a result is a real outage forecast or make a relationship verified unless an accountable human explicitly directs that change after reviewing the evidence. Do not invent a source quote, owner, assumption, capacity, timing, recovery period, or evidence reference.

## Start and discover the API

Start the local stack with `docker compose up --build`. Default addresses:

- Web app: `http://localhost:5173`
- API: `http://localhost:8000`
- Interactive API reference: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`

If the default ports are occupied, this project has also been run with API port `8001` and web port `5174`. Set `API_BASE` to the actual local API address before using the examples below.

```bash
export API_BASE=http://localhost:8000
curl -sS "$API_BASE/api/health"
```

Check the health response and confirm that the loaded dataset is the fictional ContinuityMap dataset before continuing. Use the OpenAPI schema as the source of truth for current field names and request shapes.

## Example: run the Alpha power exercise

Ask the API to run the saved fictional scenario:

```bash
curl -sS -X POST "$API_BASE/api/scenarios/run" \
  -H 'Content-Type: application/json' \
  -d '{"scenario_id":"substation-alpha-outage"}'
```

The response includes fields like these (the lists below are shortened for readability):

```json
{
  "scenario_name": "Substation Alpha unavailable",
  "disrupted_nodes": ["grid-alpha"],
  "affected_nodes": ["city-data-center", "health-records", "hospital-central"],
  "unaffected_nodes": ["water-treatment"],
  "uncertain_review_nodes": ["records-archive", "shelter-west"],
  "explanations": [
    {
      "node_id": "hospital-central",
      "node_name": "Northbank General Hospital",
      "status": "affected",
      "path": ["grid-alpha", "city-data-center", "health-records", "hospital-central"],
      "edge_ids": ["edge-026", "edge-027", "edge-028"]
    }
  ],
  "caveat": "Planning screen only: ...",
  "evaluation": {"fixture_expected_affected": 17, "exact_match": true}
}
```

`affected_nodes` means “marked unavailable by this rule calculation.” The list includes the starting disrupted node. The API returns more than the shortened example; inspect each `explanations` item to see the reason, complete path, evidence-bearing edge IDs, and uncertainty flags. `unaffected_nodes` means no verified rule in this calculation made those services unavailable. It is not a guarantee of real-world availability.

`uncertain_review_nodes` are open questions for a human owner. They are not included in the affected count. For example, the Alpha fixture has two review paths and 17 unavailable entries (one starting substation plus 16 downstream entries).

## Example: ask for a continuity assessment

```bash
curl -sS -X POST "$API_BASE/api/assistant/assessment" \
  -H 'Content-Type: application/json' \
  -d '{"scenario_id":"substation-alpha-outage"}'
```

The result contains a plain-language `summary`, lists such as `available_fallback_resources`, `missing_contingency_evidence`, and `suggested_planning_actions`, plus `evidence_refs`, `caveat`, and `state_changed`. Read and preserve the cited references when summarizing. Treat actions as prompts for an accountable planner to review. `state_changed` should be `false`: an assessment does not update the graph, status, or recovery plan.

## How to explain dependency rules

- **Verified:** a human approved the declared relationship and its evidence. Only this status participates in official scenario propagation.
- **Proposed:** a possible relationship waiting for review. It can be described as a suggestion, not a fact.
- **Unknown:** an unresolved question. Do not interpret it as proof the relationship exists or does not exist.
- **Rejected:** a reviewer declined the claim. Do not reintroduce it as accepted evidence.
- **ANY:** one available provider in the group is enough. Example: utility power **or** a generator.
- **ALL:** every provider in the group is required. Example: power **and** data connectivity.
- **Evidence reference:** a pointer to the source record. A valid reference does not by itself prove the summary sentence is correct; retain the quoted evidence and ask an owner to validate meaning.

When the Alpha substation is disrupted, the demo’s water-treatment `ANY` group remains satisfied by the solar microgrid. The hospital remains marked affected because its separate electronic-records path is declared as required. Do not infer generator capacity, whether hospital staff can use another workflow, or how long any service can operate; the dataset does not answer those questions.

## Safe agent behavior

1. Confirm the dataset is fictional using `/api/health` and, when needed, inspect `/api/graph`.
2. Use `/api/scenarios/run` for the deterministic calculation; do not reconstruct impacts by guessing from names.
3. Keep affected results, unaffected results, and review-only questions separate in every summary.
4. For every material conclusion, retain the `node_id`, `path`, `edge_ids`, and `evidence_refs` that support it.
5. Say “the declared graph marks this service unavailable in the exercise,” not “the service will fail.”
6. Do not change `verification_status` to `verified`, approve contradictory statements, or alter a recovery plan on behalf of the owner. A human may review a proposal in the user interface.
7. State when evidence, timing, capacity, backup testing, or recovery steps are missing. Never fill those gaps with plausible-sounding values.
8. If the API response or evidence conflicts, report the conflict and request human review. Do not silently choose one statement.

## Additional endpoints

Use `/docs` or `/openapi.json` for the complete schema. Common read and review routes include:

| Route | Purpose |
|---|---|
| `GET /api/graph` | Read nodes, relationships, scenarios, and validation information. |
| `POST /api/graph/validate` | Check for structural or evidence issues. |
| `POST /api/scenarios/run` | Run a saved or custom fictional what-if exercise. |
| `POST /api/assistant/assessment` | Return a non-mutating evidence-based assessment. |
| `POST /api/documents/extract` | Turn uploaded fictional text into proposed relationships for human review. |
| `GET /api/reports/impact/{scenario_id}.pdf` | Download an impact report. |
| `GET /api/reports/dependency-gaps.pdf` | Download a dependency-gap report. |
| `GET /api/reports/checklist/{scenario_id}.pdf` | Download a human-review checklist. |

The development API is intended for the bundled fictional demo. Before connecting an external agent in a future customer deployment, an organization would need authentication, scoped authorization, logging, data-retention rules, and human approval controls.
