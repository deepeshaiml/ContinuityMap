# Data dictionary

This page explains the fields stored for a fictional ContinuityMap network. JSON is the import/export format. PostgreSQL stores nodes, relationships, open questions, scenarios, the dataset manifest, and audit events.

## Read this first

A **node** is a service, facility, asset, or recovery resource. A **relationship** records that one node supplies or supports another. In the data, `source` means the provider and `dependent` means the service that relies on it. The arrow points from provider to dependent.

Example: “The water treatment site can get power from either Substation Alpha or the solar microgrid.” This is represented by two verified relationships in one `ANY` group:

```text
Northbank Substation Alpha ─┐
                            ├─ ANY power group → Northbank Water Treatment
Civic Solar Microgrid ─────┘
```

If Alpha is disrupted but solar remains available, the recorded `ANY` rule is still satisfied. The simulation does not check the actual capacity or runtime of either source.

## Node fields

| Field | Type | Plain meaning |
|---|---|---|
| `id` | string | Stable unique key used by relationships and API clients, such as `grid-alpha`. |
| `name` | string | Human-readable display name. |
| `category` | enum | `service`, `facility`, `asset`, or `recovery_resource`. |
| `sector` | string | Planning category such as water, transport, or healthcare. |
| `description` | string | Context for reviewers. All bundled descriptions are fictional. |
| `capacity`, `capacity_unit` | number/string/null | Optional owner-provided capacity. Blank means unknown; the app does not estimate it. |
| `criticality` | string | Owner-supplied planning label. This is not an automatic readiness score. |
| `aliases` | string[] | Alternate names that help match document text to this node. |
| `fictional` | boolean | This prototype accepts imported nodes only when this is `true`. |

## Relationship fields

| Field | Type | Plain meaning |
|---|---|---|
| `id` | string | Unique relationship record key. |
| `source` | node ID | Provider/resource at the start of the arrow. |
| `dependent` | node ID | Service at the end of the arrow; it relies on `source`. |
| `dependency_type` | enum | What the provider supplies: power, water, telecommunications, data connectivity, transport, fuel, staff, or other. |
| `evidence` | string | Short supporting quote or declaration. |
| `evidence_ref` | string | Where the quote came from, such as document/section or a fixture reference. |
| `verification_status` | enum | `verified`, `proposed`, `unknown`, or `rejected`. Only verified relationships affect official exercise results. |
| `owner` | string | Person/team accountable for checking the relationship. |
| `conditions` | string[] | Conditions stated alongside the relationship. |
| `assumptions` | object[] | `{text, support_status, evidence_ref}`. Unsupported assumptions raise a warning. |
| `last_validated` | date/null | Date a human last checked the relationship. |
| `review_due_date` | date/null | Owner-agreed date to review the relationship again. An overdue date creates a validation warning; it does not silently change the verification status or remove the relationship from scenario calculations. |
| `group_id` | string | Identifier that groups providers for one requirement on a dependent service. |
| `group_mode` | enum | `ANY`: one provider in the group is enough. `ALL`: every provider is required. Separate groups on the same service are all required. |

## Example relationship record

```json
{
  "id": "edge-example",
  "source": "grid-alpha",
  "dependent": "water-treatment",
  "dependency_type": "power",
  "evidence": "The treatment site can use the Northbank distribution feed.",
  "evidence_ref": "CM-DEMO-01 §05",
  "verification_status": "verified",
  "owner": "Water Operations Lead",
  "conditions": [],
  "assumptions": [],
  "last_validated": "2026-10-01",
  "review_due_date": "2026-10-15",
  "group_id": "treatment-power",
  "group_mode": "ANY"
}
```

This record says Alpha is one possible power supplier. The group rule is interpreted together with the other providers in `treatment-power`.

## Open questions and review status

An unknown relationship is stored separately from a normal relationship. It includes `id`, `source`, `dependent`, `dependency_type` (nullable if the type is not known), `question`, `evidence`, `verification_status` fixed to `unknown`, `owner`, `evidence_ref`, `conditions`, `assumptions`, and `last_validated`. Its evidence proves that a question was recorded; it does not prove that the dependency exists.

| Status | Meaning in everyday terms | Used in unavailable calculation? |
|---|---|---|
| `verified` | A human approved the evidence and declaration. | Yes. |
| `proposed` | A person or AI suggested a relationship; it awaits review. | No. |
| `unknown` | The source leaves an open question for an owner. | No. |
| `rejected` | A reviewer declined the relationship claim. | No. |

If an unverified provider is disrupted, the app can show its dependent as a review path. It does not mark that dependent unavailable because of the unverified relationship.

## Scenario fields

A scenario has `id`, `name`, `description`, and `disrupted_nodes`: the explicitly unavailable starting point(s) for the exercise. It may also store `expected_affected` for evaluation and `review_actions` as planning prompts. The expected list is a synthetic test answer, not a real-world outcome.

## Integrity checks

The validator checks for missing node references, duplicate IDs and relationships, invalid dependency types, contradictory statuses for the same relationship, inconsistent `ANY`/`ALL` modes inside one group, unsupported assumptions, missing validation dates, and overdue owner review dates. An overdue date is a warning; the relationship remains in scenario calculations until an owner changes its status. Cycles are reported for review. The calculation can handle cycles without looping forever, but owners should confirm that the circular declarations make sense.

When an `ANY` group keeps a dependent outside the affected set after one provider is disrupted, the result includes that dependent in `backup_review_nodes`. This is a prompt to check the declared alternative's capacity, runtime, and shared upstream dependencies; the engine does not evaluate those conditions.

## Small glossary

- **Graph:** the collection of nodes and the relationships between them.
- **Upstream / downstream:** toward the providers / toward the services relying on them.
- **Evidence-linked:** the relationship keeps the quote and its source reference beside it.
- **Scenario propagation:** the app repeatedly checks verified relationships to find which declared requirements are no longer met. It is a rule-based planning result, not a physical prediction.
