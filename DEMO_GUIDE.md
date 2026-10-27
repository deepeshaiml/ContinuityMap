# ContinuityMap demo guide

## Before you begin

Start the local demo from the project folder:

```bash
docker compose up --build
```

Open `http://localhost:5173`. The API reference is at `http://localhost:8000/docs`.

The workspace is **Northbank**, an invented city. Explain this first: the result is a what-if calculation over declared relationships. It is not a prediction of what would happen in a real city.

## A 5-minute walkthrough

### 1. Start with a simple question (30 seconds)

Ask: “If Northbank Substation Alpha becomes unavailable, which services rely on it according to this fictional register?” A **scenario** is just a named what-if exercise. Click **Run scenario**.

### 2. Show what one line means (45 seconds)

Select Northbank Substation Alpha and choose a verified relationship. Explain the arrow in everyday words: “This resource supplies that service.” Show the evidence quote, document reference, named owner, validation date, and owner review due date. One synthetic backup relationship is overdue; the app warns about it and clearly shows that it still participates until an owner changes its status.

### 3. Explain a backup (45 seconds)

The water-treatment power group is marked **ANY**: either Substation Alpha or the Civic Solar Microgrid is enough in this example. When Alpha is unavailable, the solar option satisfies the recorded rule, so the model infers no failed path to water treatment and flags it for backup review. This does not confirm the service is operating or check solar capacity, runtime, or shared upstream dependencies.

### 4. Follow one impact path (60 seconds)

The declared path is:

```text
Substation Alpha
  → Municipal Data Center
  → Shared Health Records
  → Northbank General Hospital
```

The hospital is marked unavailable in this exercise because the records path is a required (**ALL**) group and the declared source chain is unavailable. The local hospital generator can satisfy a separate power group, but it does not replace the records service in this graph. This is a transparent result from the recorded statements, not a physical forecast.

### 5. Separate a result from a question (45 seconds)

The Alpha exercise lists 17 unavailable entries: one disrupted starting resource plus 16 downstream results. Two possible relationships are shown in amber for review. They are **not** counted as unavailable because they are not verified. Explain that blank capacity or timing is unknown; the tool does not fill it in.

### 6. Edit and compare (60 seconds)

Use **Add relationship** or select a relationship to edit it. A new relationship begins as proposed. A human reviewer can update its evidence, owner, and status. Only setting it to verified allows it to affect an official exercise. Rerun the same scenario to compare the result.

### 7. Show the other scenarios and the assistant (45 seconds)

Try **East water pumping loses utility and backup power** or **Regional communications outage**. The communications example keeps the separate radio service available. Then prepare a continuity assessment, upload `data/fictional_continuity_pack.md` to create review-only relationship suggestions, and export an impact report, dependency-gap report, or human-review checklist.

## What the status words mean

| Status | What to say |
|---|---|
| Verified | A human reviewed the evidence; this relationship is used in the exercise. |
| Proposed | A possible relationship waiting for a human to check. |
| Unknown | The source material asks a question, but the relationship is unresolved. |
| Rejected | A reviewer declined the claim; it remains visible as a record. |

**ANY** means at least one listed provider is enough under the declared rule. **ALL** means every listed provider is needed. **Review path** means “ask the owner”; it is not the same as a failed service. **No impact inferred** means the verified graph found no failed path; it does not confirm availability. **Backup review** means a scenario relied on a declared alternate provider whose capacity, runtime, and shared upstream dependencies were not assessed.

## Expected fictional results

- **Substation Alpha unavailable:** 17 unavailable entries, including the starting substation; 2 possible paths for review.
- **East water pumping loses utility and backup power:** 20 unavailable entries; 2 possible paths for review.
- **Regional communications outage:** 9 unavailable entries; the separately declared radio route remains available.

These fixed results can be reproduced from `data/infrastructure.json` and checked against `data/evaluation_results.json`. Counts include the explicit starting disruption. They are not estimates of real-world consequences.

## Local AI option

The app works without an AI model. If Ollama is installed locally, set `OLLAMA_BASE_URL` and `OLLAMA_MODEL` in a private `.env` file. For the optional Compose Ollama service, start the `llm` profile and install a model locally; model terms vary, so check its license before use. Without these variables, the interface labels its rule-based extraction or template summary clearly.

## Presentation boundary

Do not call the scenario count a forecast, probability, readiness score, or predicted outage. It means only: “Given this fictional starting disruption and these owner-verified links, these entries become unavailable under the declared rules.” A customer deployment would first need a separately approved graph, named owners, and evidence review.

## Screenshots

- `reports/ContinuityMap_Demo_Screenshot.png` — live UI after running the Alpha scenario.
- `reports/ContinuityMap_Assessment_Screenshot.png` — evidence-linked assessment, fallback resources, gaps, and owner actions.
