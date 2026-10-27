export type NodeItem = {
  id: string
  name: string
  category: 'service' | 'facility' | 'asset' | 'recovery_resource'
  sector: string
  description: string
  capacity?: number | null
  capacity_unit?: string | null
  criticality: string
  aliases: string[]
  fictional: boolean
}

export type Edge = {
  id: string
  source: string
  dependent: string
  dependency_type: string
  evidence: string
  evidence_ref: string
  verification_status: 'verified' | 'proposed' | 'unknown' | 'rejected'
  owner: string
  conditions: string[]
  assumptions: { text: string; support_status: string; evidence_ref?: string | null }[]
  last_validated?: string | null
  group_id: string
  group_mode: 'ANY' | 'ALL'
}

export type UnknownRelationship = {
  id: string
  source: string
  dependent: string
  question: string
  owner: string
  evidence_ref?: string | null
}

export type Scenario = {
  id: string
  name: string
  description: string
  disrupted_nodes: string[]
  expected_affected: string[]
  review_actions: string[]
}

export type GraphData = {
  dataset_id: string
  title: string
  synthetic_notice: string
  nodes: NodeItem[]
  edges: Edge[]
  unknown_relationships: UnknownRelationship[]
  scenarios: Scenario[]
  metadata: Record<string, unknown>
}

export type Explanation = {
  node_id: string
  node_name: string
  status: string
  reason: string
  path: string[]
  edge_ids: string[]
  uncertainty_flags: string[]
}

export type Simulation = {
  scenario_name: string
  disrupted_nodes: string[]
  affected_nodes: string[]
  unaffected_nodes: string[]
  uncertain_review_nodes: string[]
  explanations: Explanation[]
  caveat: string
  processing_ms: number
  evaluation?: { fixture_expected_affected: number; exact_match: boolean; precision: number; recall: number }
}

export type Assessment = {
  mode: string
  summary: string
  affected_services: { id: string; name: string; reason: string; evidence_refs: string[] }[]
  declared_dependencies: Edge[]
  potential_recovery_blockers: Explanation[]
  available_fallback_resources: string[]
  missing_contingency_evidence: string[]
  suggested_planning_actions: string[]
  evidence_refs: string[]
  caveat: string
  state_changed: false
}
