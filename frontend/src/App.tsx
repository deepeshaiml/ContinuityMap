import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import cytoscape, { type Core, type EventObject } from 'cytoscape'
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, Bot, Check, CheckCircle2,
  ChevronDown, CircleHelp, ClipboardList, CloudUpload, Download, FileText, Filter,
  GitBranch, Layers3, LoaderCircle, Map as MapIcon, Network, PanelRightClose, Play, Plus,
  RefreshCw, Search, ShieldCheck, SlidersHorizontal, Sparkles, X,
} from 'lucide-react'
import type { Assessment, Edge, GraphData, Simulation } from './types'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
type ViewFilter = 'all' | 'verified' | 'review' | 'unknown'

function App() {
  const [graph, setGraph] = useState<GraphData | null>(null)
  const [validation, setValidation] = useState<{ valid: boolean; issues: { severity: string; code: string; message: string; object_id?: string | null }[]; counts: Record<string, number> } | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState('grid-alpha')
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
  const [scenarioId, setScenarioId] = useState('substation-alpha-outage')
  const [simulation, setSimulation] = useState<Simulation | null>(null)
  const [assessment, setAssessment] = useState<Assessment | null>(null)
  const [filter, setFilter] = useState<ViewFilter>('all')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [assistantLoading, setAssistantLoading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [modal, setModal] = useState<'edge' | null>(null)
  const [editingEdge, setEditingEdge] = useState<Edge | null>(null)
  const [showAssessment, setShowAssessment] = useState(false)
  const cyRef = useRef<Core | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const fileRef = useRef<HTMLInputElement | null>(null)
  const documentRef = useRef<HTMLInputElement | null>(null)

  const selectedScenario = graph?.scenarios.find((item) => item.id === scenarioId)
  const selectedNode = graph?.nodes.find((item) => item.id === selectedNodeId)
  const selectedEdge = graph?.edges.find((item) => item.id === selectedEdgeId)
  const nodeNames = useMemo(() => new globalThis.Map(graph?.nodes.map((node) => [node.id, node.name]) ?? []), [graph])

  const loadGraph = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${API}/api/graph`)
      if (!response.ok) throw new Error(`API returned ${response.status}`)
      const payload = await response.json()
      setGraph(payload.graph)
      setValidation(payload.validation)
    } catch (err) {
      setError(`Could not reach the ContinuityMap API. ${err instanceof Error ? err.message : ''}`)
    } finally { setLoading(false) }
  }, [])

  const runScenario = useCallback(async (nextScenarioId = scenarioId) => {
    if (!nextScenarioId) return
    setRunning(true)
    setError('')
    try {
      const response = await fetch(`${API}/api/scenarios/run`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario_id: nextScenarioId }),
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail?.message || payload.detail || 'Scenario could not run')
      setSimulation(payload)
      setAssessment(null)
    } catch (err) { setError(err instanceof Error ? err.message : 'Scenario could not run') }
    finally { setRunning(false) }
  }, [scenarioId])

  useEffect(() => { void loadGraph() }, [loadGraph])
  useEffect(() => {
    if (graph && !simulation && graph.scenarios.length) void runScenario(scenarioId || graph.scenarios[0].id)
  }, [graph, runScenario, scenarioId, simulation])

  const drawGraph = useCallback(() => {
    if (!containerRef.current || !graph) return
    cyRef.current?.destroy()
    const failed = new Set(simulation?.affected_nodes ?? [])
    const uncertain = new Set(simulation?.uncertain_review_nodes ?? [])
    const backupReview = new Set(simulation?.backup_review_nodes ?? [])
    const query = search.trim().toLowerCase()
    const nodes = graph.nodes.map((node) => {
      const isFailed = failed.has(node.id)
      const isUncertain = uncertain.has(node.id)
      const needsBackupReview = backupReview.has(node.id)
      const matchesSearch = !query || `${node.name} ${node.sector} ${node.id}`.toLowerCase().includes(query)
      return { data: { id: node.id, label: node.name, category: node.category, sector: node.sector, state: isFailed ? 'affected' : isUncertain ? 'review' : needsBackupReview ? 'backup-review' : simulation ? 'no-modeled-impact' : 'no-scenario' }, classes: `${isFailed ? 'is-affected' : ''} ${isUncertain ? 'is-uncertain' : ''} ${needsBackupReview ? 'is-backup-review' : ''} ${matchesSearch ? '' : 'dimmed'}` }
    })
    const visibleByFilter = (status: string) => filter === 'all' || (filter === 'verified' && status === 'verified') || (filter === 'review' && status === 'proposed') || (filter === 'unknown' && status === 'unknown')
    const edges = graph.edges.filter((edge) => visibleByFilter(edge.verification_status)).map((edge) => ({
      data: { id: edge.id, source: edge.source, target: edge.dependent, status: edge.verification_status, label: edge.dependency_type.replace('_', ' '), mode: edge.group_mode },
      classes: edge.verification_status,
    }))
    const unknownEdges = graph.unknown_relationships.filter(() => filter === 'all' || filter === 'unknown').map((edge) => ({ data: { id: edge.id, source: edge.source, target: edge.dependent, status: 'unknown', label: 'unknown' }, classes: 'unknown' }))
    const cy = cytoscape({
      container: containerRef.current,
      elements: [...nodes, ...edges, ...unknownEdges],
      layout: { name: 'cose', animate: false, fit: true, padding: 45, nodeRepulsion: () => 7200, idealEdgeLength: () => 105, edgeElasticity: () => 80, gravity: 0.18, numIter: 800 },
      minZoom: 0.25, maxZoom: 2.5,
      style: [
        { selector: 'node', style: { 'background-color': '#C7D8E2', 'border-width': 1, 'border-color': '#7F9AA9', label: 'data(label)', color: '#173347', 'font-size': '8px', 'font-weight': 600, 'text-wrap': 'wrap', 'text-max-width': '86px', 'text-valign': 'bottom', 'text-margin-y': 5, width: 26, height: 26, 'overlay-opacity': 0 } },
        { selector: 'node[category = "facility"]', style: { shape: 'round-rectangle', 'background-color': '#B4DCE0', 'border-color': '#3A8994' } },
        { selector: 'node[category = "recovery_resource"]', style: { shape: 'diamond', 'background-color': '#F4D7A2', 'border-color': '#B48231' } },
        { selector: 'node[category = "service"]', style: { shape: 'ellipse', 'background-color': '#C7D8E2' } },
        { selector: 'node.is-affected', style: { 'background-color': '#F7C3B6', 'border-color': '#C7543F', 'border-width': 3, color: '#6F2C23' } },
        { selector: 'node.is-uncertain', style: { 'border-color': '#C38724', 'border-width': 3, 'border-style': 'dashed' } },
        { selector: 'node.is-backup-review', style: { 'border-color': '#54768A', 'border-width': 3, 'border-style': 'dashed' } },
        { selector: 'node.dimmed', style: { opacity: 0.2 } },
        { selector: 'node:selected', style: { 'border-color': '#087F8C', 'border-width': 4, 'overlay-color': '#087F8C', 'overlay-opacity': 0.1 } },
        { selector: 'edge', style: { width: 1.1, 'line-color': '#9CB0BA', 'target-arrow-color': '#9CB0BA', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', 'arrow-scale': 0.7, opacity: 0.56, 'overlay-opacity': 0 } },
        { selector: 'edge.proposed', style: { 'line-color': '#C38724', 'target-arrow-color': '#C38724', 'line-style': 'dashed', width: 1.5, opacity: 0.78 } },
        { selector: 'edge.unknown', style: { 'line-color': '#D58E20', 'target-arrow-color': '#D58E20', 'line-style': 'dotted', width: 2, opacity: 0.85 } },
        { selector: 'edge.rejected', style: { 'line-color': '#A8B3B9', 'target-arrow-color': '#A8B3B9', opacity: 0.15 } },
        { selector: 'edge:selected', style: { 'line-color': '#087F8C', 'target-arrow-color': '#087F8C', width: 3, opacity: 1 } },
      ],
    })
    cy.on('tap', 'node', (event: EventObject) => { setSelectedNodeId(event.target.id()); setSelectedEdgeId(null) })
    cy.on('tap', 'edge', (event: EventObject) => { setSelectedEdgeId(event.target.id()); setSelectedNodeId(event.target.data('source')) })
    cyRef.current = cy
    if (selectedNodeId) cy.getElementById(selectedNodeId).select()
  }, [filter, graph, search, selectedNodeId, simulation])

  useEffect(() => { drawGraph(); return () => cyRef.current?.destroy() }, [drawGraph])

  const assess = async () => {
    if (!scenarioId) return
    setAssistantLoading(true)
    try {
      const response = await fetch(`${API}/api/assistant/assessment`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario_id: scenarioId }) })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail || 'Assessment could not be prepared')
      setAssessment(payload)
      setShowAssessment(true)
    } catch (err) { setError(err instanceof Error ? err.message : 'Assessment could not be prepared') }
    finally { setAssistantLoading(false) }
  }

  const download = async (path: string, filename: string) => {
    try {
      const response = await fetch(`${API}${path}`)
      if (!response.ok) throw new Error('Report export failed')
      const url = URL.createObjectURL(await response.blob())
      const anchor = document.createElement('a'); anchor.href = url; anchor.download = filename; anchor.click(); URL.revokeObjectURL(url)
      setNotice('Report downloaded')
    } catch (err) { setError(err instanceof Error ? err.message : 'Report export failed') }
  }

  const openEdge = (edge?: Edge) => {
    setEditingEdge(edge ?? {
      id: `manual-${Date.now()}`, source: selectedNodeId, dependent: '', dependency_type: 'power', evidence: '', evidence_ref: 'manual-review',
      verification_status: 'proposed', owner: '', conditions: [], assumptions: [], last_validated: null, group_id: `review-${Date.now()}`, group_mode: 'ANY',
    })
    setModal('edge')
  }

  const saveEdge = async (edge: Edge) => {
    try {
      const creating = !graph?.edges.some((item) => item.id === edge.id)
      const response = await fetch(`${API}/api/edges${creating ? '' : `/${edge.id}`}`, {
        method: creating ? 'POST' : 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(edge),
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Could not save relationship')
      setModal(null); setNotice(edge.verification_status === 'verified' ? 'Relationship verified and saved' : 'Relationship saved for review')
      await loadGraph()
      if (simulation) await runScenario(scenarioId)
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not save relationship') }
  }

  const uploadDocument = async (file?: File) => {
    if (!file) return
    const body = new FormData(); body.append('file', file)
    try {
      const response = await fetch(`${API}/api/documents/extract`, { method: 'POST', body })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail || 'Document extraction failed')
      setNotice(`${payload.proposals.length} relationship proposal(s) added · ${payload.mode.replaceAll('_', ' ')}`)
      await loadGraph()
      const first = payload.proposals[0]
      if (first) { setSelectedEdgeId(first.id); setSelectedNodeId(first.source) }
    } catch (err) { setError(err instanceof Error ? err.message : 'Document extraction failed') }
  }

  const focusNode = (id: string) => {
    setSelectedNodeId(id); setSelectedEdgeId(null)
    const element = cyRef.current?.getElementById(id)
    if (element?.length) { cyRef.current?.animate({ center: { eles: element }, zoom: Math.max(cyRef.current.zoom(), 1.05) }, { duration: 350 }) }
  }

  const focusedEdges = graph?.edges.filter((edge) => edge.source === selectedNodeId || edge.dependent === selectedNodeId) ?? []
  const upstreamEdges = focusedEdges.filter((edge) => edge.dependent === selectedNodeId)
  const downstreamEdges = focusedEdges.filter((edge) => edge.source === selectedNodeId)
  const impactCount = simulation?.affected_nodes.length ?? 0
  const downstreamCount = Math.max(0, impactCount - (simulation?.disrupted_nodes.length ?? 0))
  const proposals = graph?.edges.filter((edge) => edge.verification_status === 'proposed') ?? []
  const currentExplanation = selectedNodeId ? simulation?.explanations.find((item) => item.node_id === selectedNodeId) : undefined
  const selectedNodeNeedsBackupReview = simulation?.backup_review_nodes.includes(selectedNodeId) ?? false
  const overdueReviewIssues = validation?.issues.filter((issue) => issue.code === 'overdue_verified_relationship') ?? []

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#" aria-label="ContinuityMap home"><span className="brand-mark"><Network size={19} strokeWidth={2.1} /></span><span>continuity<span className="brand-map">map</span></span></a>
        <div className="topbar-divider" />
        <div className="workspace-name"><span className="workspace-kicker">WORKSPACE</span><strong>Northbank resilience</strong><span className="synthetic-pill"><span /> SYNTHETIC</span></div>
        <div className="topbar-right">
          <span className="status-indicator"><span /> Synthetic demo ready</span>
          <button className="avatar" title="Demo user">DR</button>
        </div>
      </header>

      <div className="safety-banner"><ShieldCheck size={14} /><span>Fictional demonstration data only</span><i /> <span>Planning screens, not physical predictions</span><i /> <span>Local demo · user permissions are not enabled</span></div>

      <div className="layout">
        <aside className="left-rail">
          <div className="rail-section rail-primary">
            <button className="rail-link active"><MapIcon size={17} /><span>Dependency map</span><span className="rail-count">01</span></button>
            <button className="rail-link" onClick={() => setFilter('review')}><ClipboardList size={17} /><span>Review queue</span>{proposals.length > 0 && <span className="review-badge">{proposals.length}</span>}</button>
            <button className="rail-link" onClick={() => void download('/api/reports/dependency-gaps.pdf', 'ContinuityMap_Dependency_Gaps.pdf')}><FileText size={17} /><span>Reports</span></button>
          </div>
          <div className="rail-rule" />
          <div className="section-heading"><span>SCENARIO EXERCISES</span><span className="heading-icon"><SlidersHorizontal size={14} /></span></div>
          <div className="scenario-list">
            {graph?.scenarios.map((scenario, index) => (
              <button key={scenario.id} className={`scenario-item ${scenarioId === scenario.id ? 'selected' : ''}`} onClick={() => { setScenarioId(scenario.id); void runScenario(scenario.id) }}>
                <span className={`scenario-icon scenario-icon-${index}`}><Activity size={15} /></span>
                <span className="scenario-copy"><strong>{scenario.name}</strong><small>{scenario.disrupted_nodes.length} disruption{scenario.disrupted_nodes.length === 1 ? '' : 's'}</small></span>
                {scenarioId === scenario.id && <span className="scenario-selected-dot" />}
              </button>
            ))}
          </div>
          <div className="rail-rule" />
          <div className="section-heading"><span>NETWORK INVENTORY</span></div>
          <div className="inventory-row"><span className="inventory-dot dot-power" /><span>Electricity</span><span>{graph?.nodes.filter((node) => node.sector === 'electricity').length ?? 0}</span></div>
          <div className="inventory-row"><span className="inventory-dot dot-water" /><span>Water services</span><span>{graph?.nodes.filter((node) => node.sector === 'water').length ?? 0}</span></div>
          <div className="inventory-row"><span className="inventory-dot dot-health" /><span>Healthcare</span><span>{graph?.nodes.filter((node) => node.sector === 'healthcare').length ?? 0}</span></div>
          <div className="inventory-row"><span className="inventory-dot dot-comms" /><span>Communications</span><span>{graph?.nodes.filter((node) => node.sector === 'telecommunications').length ?? 0}</span></div>
          <div className="left-rail-spacer" />
          <div className="rail-footer-card"><div className="footer-card-icon"><GitBranch size={16} /></div><div><strong>Dependency confidence</strong><p>{validation?.counts.verified_edges ?? 0} verified relationships</p></div></div>
          <div className="rail-footer"><span className="small-lock"><ShieldCheck size={13} /></span> Local demo · no live infrastructure</div>
        </aside>

        <main className="main-area">
          <div className="page-heading">
            <div><div className="breadcrumb">CONTINUITY PLANNING <span>/</span> DEPENDENCY MAP</div><h1>Infrastructure dependency map</h1><p>See how essential services connect, and where a disruption may travel.</p></div>
            <div className="heading-actions">
              <button className="button button-secondary" onClick={() => fileRef.current?.click()}><CloudUpload size={15} /> Import network</button>
              <input ref={fileRef} type="file" accept="application/json,.json" hidden onChange={async (event) => {
                const file = event.target.files?.[0]; if (!file) return
                try { const response = await fetch(`${API}/api/graph/import`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: await file.text() }); const data = await response.json(); if (!response.ok) throw new Error('Graph import failed: inspect the validation response'); setNotice(`Imported ${data.validation.counts.nodes} nodes`); await loadGraph() } catch (err) { setError(err instanceof Error ? err.message : 'Graph import failed') } finally { event.target.value = '' }
              }} />
              <button className="button button-primary" onClick={() => openEdge()}><Plus size={16} /> Add relationship</button>
            </div>
          </div>

          <div className="metric-row">
            <div className="metric-card"><span className="metric-icon icon-nodes"><Layers3 size={16} /></span><div><strong>{graph?.nodes.length ?? '—'}</strong><small>Infrastructure nodes</small></div><span className="metric-caption">Declared</span></div>
            <div className="metric-card"><span className="metric-icon icon-verified"><CheckCircle2 size={16} /></span><div><strong>{validation?.counts.verified_edges ?? '—'}</strong><small>Verified dependencies</small></div><span className="metric-caption green">Owner confirmed</span></div>
            <div className="metric-card"><span className="metric-icon icon-review"><CircleHelp size={16} /></span><div><strong>{(validation?.counts.proposed_edges ?? 0) + (validation?.counts.unknown_relationships ?? 0)}</strong><small>Need review</small></div><span className="metric-caption amber">Proposal or unknown</span></div>
            <div className={`metric-card ${simulation ? 'metric-alert' : ''}`}><span className="metric-icon icon-impact"><AlertTriangle size={16} /></span><div><strong>{simulation ? impactCount : '—'}</strong><small>Unavailable in exercise</small></div><span className="metric-caption">Includes seed</span></div>
          </div>

          {(error || notice) && <div className={`toast ${error ? 'toast-error' : ''}`}><span>{error || notice}</span><button onClick={() => { setError(''); setNotice('') }}><X size={14} /></button></div>}

          <section className="map-card">
            <div className="map-toolbar">
              <div className="map-card-title"><span className="live-dot" /><div><strong>{graph?.title ?? 'Loading network…'}</strong><small>{graph?.nodes.length ?? 0} assets & services <span>·</span> declared dependency view</small></div></div>
              <div className="map-controls">
                <label className="search-field"><Search size={14} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Find a service" /></label>
                <div className="filter-wrap"><Filter size={14} /><select value={filter} onChange={(event) => setFilter(event.target.value as ViewFilter)} aria-label="Filter dependency relationships"><option value="all">All relationships</option><option value="verified">Verified only</option><option value="review">Proposed only</option><option value="unknown">Unknown only</option></select><ChevronDown size={13} /></div>
                <button className="icon-button" onClick={() => { cyRef.current?.fit(undefined, 45); cyRef.current?.center() }} title="Fit network"><RefreshCw size={15} /></button>
              </div>
            </div>
            <div className="map-canvas-wrap">
              <div className="map-background-grid" />
              {loading && <div className="loading-overlay"><LoaderCircle className="spin" size={26} /> Loading fictional network…</div>}
              <div ref={containerRef} className="cy-map" />
              <div className="map-legend"><span><i className="legend-node legend-service" />Service</span><span><i className="legend-node legend-facility" />Facility</span><span><i className="legend-node legend-recovery" />Recovery resource</span><span><i className="legend-node legend-impacted" />Impacted</span><span><i className="legend-node legend-backup" />Backup review</span><span><i className="legend-node legend-no-impact" />No impact inferred</span><span><i className="legend-line verified-line" />Verified</span><span><i className="legend-line proposed-line" />Proposed / unknown</span></div>
              {simulation && <div className="scenario-stamp"><AlertTriangle size={13} /><span>{simulation.scenario_name}</span></div>}
              <div className="map-expand"><button className="icon-button" onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)} title="Zoom in">+</button><button className="icon-button" onClick={() => cyRef.current?.zoom(cyRef.current.zoom() / 1.2)} title="Zoom out">−</button></div>
            </div>
            <div className="map-footer"><span><span className="footer-check"><Check size={11} /></span> Showing {graph?.nodes.length ?? 0} nodes and {filter === 'all' ? (graph?.edges.length ?? 0) + (graph?.unknown_relationships.length ?? 0) : 'filtered'} relationships</span><span>Click a node or line to inspect provenance</span></div>
          </section>

          <div className="bottom-row">
            <section className="impact-card">
              <div className="card-heading"><div><span className="eyebrow">SCENARIO IMPACT</span><h2>{selectedScenario?.name ?? 'Choose an exercise'}</h2></div><button className="button button-primary run-button" onClick={() => void runScenario()} disabled={running || !selectedScenario}>{running ? <LoaderCircle className="spin" size={14} /> : <Play size={14} fill="currentColor" />} Run scenario</button></div>
              <p className="scenario-description">{selectedScenario?.description}</p>
              <div className="impact-stats"><div><strong className="affected-number">{simulation?.affected_nodes.length ?? '—'}</strong><span>Unavailable <small>incl. disruption seed</small></span></div><div><strong>{downstreamCount}</strong><span>Downstream impacts</span></div><div><strong className="uncertain-number">{simulation?.uncertain_review_nodes.length ?? '—'}</strong><span>Unverified paths</span></div><div><strong>{simulation ? `${simulation.processing_ms} ms` : '—'}</strong><span>Calculation time</span></div></div>
              {simulation?.evaluation && <div className={`fixture-match ${simulation.evaluation.exact_match ? 'match-good' : 'match-warning'}`}><CheckCircle2 size={13} /> Fixed fixture {simulation.evaluation.exact_match ? 'matches expected results' : 'differs from expected results'} · precision {Math.round(simulation.evaluation.precision * 100)}% · recall {Math.round(simulation.evaluation.recall * 100)}%</div>}
              <div className="impact-actions"><div className="impact-node-list">{simulation?.affected_nodes.slice(0, 5).map((id) => <button key={id} onClick={() => focusNode(id)}>{nodeNames.get(id) ?? id}<ArrowDownRight size={12} /></button>)}{(simulation?.affected_nodes.length ?? 0) > 5 && <span>+{(simulation?.affected_nodes.length ?? 0) - 5} more</span>}</div><button className="text-button" onClick={() => simulation && void download(`/api/reports/impact/${scenarioId}.pdf`, `Impact_${scenarioId}.pdf`)}><Download size={14} /> Impact report</button></div>
              {simulation?.backup_review_nodes.length ? <div className="backup-review-note"><AlertTriangle size={14} /><span><strong>Declared backup needs owner review:</strong> {simulation.backup_review_nodes.map((id) => nodeNames.get(id) ?? id).join(', ')}. The scenario relies on an ANY rule; backup capacity, runtime, and shared upstream dependencies are not checked.</span></div> : null}
              <div className="impact-caveat"><AlertTriangle size={13} /><span>{simulation?.caveat}</span></div>
            </section>

            <section className="action-card">
              <div className="card-heading"><div><span className="eyebrow">PLANNING ASSISTANT</span><h2>Continuity review</h2></div><span className="ai-mark"><Sparkles size={14} /></span></div>
              <p>Generate a concise, evidence-linked summary of impacts, fallback resources, and review actions.</p>
              <button className="assistant-button" onClick={() => void assess()} disabled={assistantLoading || !simulation}>{assistantLoading ? <LoaderCircle className="spin" size={15} /> : <Bot size={16} />} Prepare continuity brief <ArrowUpRight size={14} /></button>
              <input ref={documentRef} type="file" accept=".txt,.md,.csv,.pdf,.docx" hidden onChange={(event) => { void uploadDocument(event.target.files?.[0]); event.target.value = '' }} />
              <button className="extract-button" onClick={() => documentRef.current?.click()}><FileText size={14} /> Upload a fictional plan for relationship review</button>
              {assessment && <div className="assessment-preview"><strong>{assessment.mode === 'local_ollama_grounded' ? 'Local model · evidence checked' : 'Evidence-based summary'}</strong><p>{assessment.summary}</p><button className="text-button" onClick={() => setShowAssessment(true)}>Open full review <ArrowUpRight size={13} /></button></div>}
              <div className="report-shortcuts"><button onClick={() => void download('/api/reports/dependency-gaps.pdf', 'ContinuityMap_Dependency_Gaps.pdf')}><FileText size={14} /> Dependency gaps</button><button onClick={() => selectedScenario && void download(`/api/reports/checklist/${scenarioId}.pdf`, `Checklist_${scenarioId}.pdf`)}><ClipboardList size={14} /> Review checklist</button></div>
            </section>
          </div>

          <div className="page-footnote"><ShieldCheck size={13} /> “No impact inferred” means no failed path was found in the verified graph; it does not confirm service availability. Backup capacity, runtime, and shared dependencies are not modeled.</div>
        </main>

        <aside className="right-panel">
          <div className="right-panel-header"><div><span className="eyebrow">DETAILS & EVIDENCE</span><h2>{selectedEdge ? 'Relationship detail' : 'Service detail'}</h2></div><button className="icon-button mobile-close" title="Close details"><PanelRightClose size={15} /></button></div>
          {selectedEdge ? (
            <RelationshipDetail edge={selectedEdge} onEdit={() => openEdge(selectedEdge)} onFocus={focusNode} nodeNames={nodeNames} />
          ) : selectedNode ? (
            <div className="node-detail">
              <div className={`node-type-icon type-${selectedNode.category}`}><Layers3 size={19} /></div>
              <div className="node-title-row"><h3>{selectedNode.name}</h3><span className={`status-chip ${currentExplanation?.status === 'affected' || currentExplanation?.status === 'disrupted' ? 'status-affected' : currentExplanation?.status === 'unaffected_review' || selectedNodeNeedsBackupReview ? 'status-review' : 'status-no-impact'}`}>{currentExplanation?.status === 'disrupted' ? 'Disrupted' : currentExplanation?.status === 'affected' ? 'Unavailable in model' : currentExplanation?.status === 'unaffected_review' ? 'Review path' : selectedNodeNeedsBackupReview ? 'Backup review' : simulation ? 'No impact inferred' : 'No scenario result'}</span></div>
              <div className="node-meta"><span>{selectedNode.sector.replaceAll('_', ' ')}</span><i /> <span>{selectedNode.category.replace('_', ' ')}</span><i /> <span>{selectedNode.criticality} criticality</span></div>
              <p className="node-description">{selectedNode.description}</p>
              {currentExplanation && <div className="impact-reason"><div className="reason-title"><AlertTriangle size={14} /> Scenario explanation</div><p>{currentExplanation.reason}</p>{currentExplanation.path.length > 1 && <div className="path-flow">{currentExplanation.path.map((id, index) => <span key={`${id}-${index}`}>{index > 0 && <ArrowDownRight size={12} />}{nodeNames.get(id) ?? id}</span>)}</div>}</div>}
              {selectedNodeNeedsBackupReview && <div className="backup-detail-note"><div className="reason-title"><AlertTriangle size={14} /> Declared backup needs review</div><p>A listed alternative kept this service outside the model’s affected set, but its capacity, runtime, and shared upstream dependencies were not assessed.</p></div>}
              <div className="detail-section"><div className="section-title"><span><ArrowUpRight size={13} /> DEPENDS ON</span><small>{upstreamEdges.length}</small></div>
                {upstreamEdges.length ? upstreamEdges.map((edge) => <button className="dependency-row" key={edge.id} onClick={() => { setSelectedEdgeId(edge.id); cyRef.current?.getElementById(edge.id).select() }}><span className={`mini-status mini-${edge.verification_status}`} /><span><strong>{nodeNames.get(edge.source) ?? edge.source}</strong><small>{edge.dependency_type.replaceAll('_', ' ')} · {edge.group_mode} group</small></span><ChevronDown size={14} className="side-chevron" /></button>) : <div className="empty-note">No declared upstream relationships.</div>}
              </div>
              <div className="detail-section"><div className="section-title"><span><ArrowDownRight size={13} /> SUPPORTS</span><small>{downstreamEdges.length}</small></div>
                {downstreamEdges.length ? downstreamEdges.map((edge) => <button className="dependency-row" key={edge.id} onClick={() => { setSelectedEdgeId(edge.id); cyRef.current?.getElementById(edge.id).select() }}><span className={`mini-status mini-${edge.verification_status}`} /><span><strong>{nodeNames.get(edge.dependent) ?? edge.dependent}</strong><small>{edge.dependency_type.replaceAll('_', ' ')} · {edge.group_mode} group</small></span><ChevronDown size={14} className="side-chevron" /></button>) : <div className="empty-note">No declared downstream relationships.</div>}
              </div>
              <div className="detail-section unknown-list"><div className="section-title"><span><CircleHelp size={13} /> POSSIBLE RELATIONSHIPS</span></div>{graph?.unknown_relationships.filter((item) => item.source === selectedNodeId || item.dependent === selectedNodeId).map((item) => <div className="unknown-item" key={item.id}><AlertTriangle size={13} /><span>{item.question}<small>{item.owner} · {item.evidence_ref}</small></span></div>) ?? <div className="empty-note">No open questions recorded for this service.</div>}</div>
              <button className="button button-outline full-button" onClick={() => openEdge()}><Plus size={14} /> Add dependency from this service</button>
            </div>
          ) : <div className="panel-empty"><Network size={24} /><p>Select a service or relationship in the map to inspect it.</p></div>}
          <div className="right-panel-spacer" />
          <div className="validation-summary"><div><ShieldCheck size={15} /><strong>Graph integrity</strong><span className={validation?.valid ? 'valid-text' : 'error-text'}>{validation?.valid ? 'Checks passed' : 'Review errors'}</span></div><small>{validation?.counts.errors ?? 0} errors · {validation?.counts.warnings ?? 0} review notes</small>{(validation?.counts.warnings ?? 0) > 0 && <button onClick={() => { setFilter('review'); setSelectedEdgeId(null) }}>Review validation notes <ArrowUpRight size={12} /></button>}</div>
          {overdueReviewIssues.length > 0 && <div className="overdue-review-list"><strong>Owner reviews overdue</strong>{overdueReviewIssues.map((issue) => { const edge = graph?.edges.find((item) => item.id === issue.object_id); return <button key={issue.object_id} onClick={() => { setFilter('all'); setSelectedEdgeId(issue.object_id ?? null) }}><AlertTriangle size={12} /><span>{edge ? `${nodeNames.get(edge.source) ?? edge.source} → ${nodeNames.get(edge.dependent) ?? edge.dependent}` : issue.object_id}</span><ArrowUpRight size={12} /></button> })}</div>}
          <div className="validation-actions"><button onClick={() => void loadGraph()}><RefreshCw size={13} /> Refresh graph</button><button onClick={() => void download('/api/reports/dependency-gaps.pdf', 'ContinuityMap_Dependency_Gaps.pdf')}><Download size={13} /> Export gaps</button></div>
        </aside>
      </div>

      {modal === 'edge' && editingEdge && graph && <EdgeModal edge={editingEdge} graph={graph} onClose={() => setModal(null)} onSave={(edge) => void saveEdge(edge)} />}
      {showAssessment && assessment && <AssessmentModal assessment={assessment} onClose={() => setShowAssessment(false)} onChecklist={() => selectedScenario && void download(`/api/reports/checklist/${scenarioId}.pdf`, `Checklist_${scenarioId}.pdf`)} />}
    </div>
  )
}

function RelationshipDetail({ edge, onEdit, onFocus, nodeNames }: { edge: Edge; onEdit: () => void; onFocus: (id: string) => void; nodeNames: Map<string, string> }) {
  const now = new Date()
  const localToday = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  const reviewOverdue = edge.verification_status === 'verified' && !!edge.review_due_date && edge.review_due_date < localToday
  return <div className="edge-detail">
    <div className={`edge-status-banner banner-${edge.verification_status}`}><span className="mini-status" />{edge.verification_status === 'verified' ? 'Verified relationship' : edge.verification_status === 'proposed' ? 'AI / human proposal · review required' : edge.verification_status === 'rejected' ? 'Rejected relationship' : 'Unknown relationship'}</div>
    <div className="edge-flow"><button onClick={() => onFocus(edge.source)}><small>PROVIDER</small><strong>{nodeNames.get(edge.source) ?? edge.source}</strong></button><ArrowDownRight size={18} /><button onClick={() => onFocus(edge.dependent)}><small>DEPENDENT SERVICE</small><strong>{nodeNames.get(edge.dependent) ?? edge.dependent}</strong></button></div>
    <div className="edge-facts"><div><span>Dependency type</span><strong>{edge.dependency_type.replaceAll('_', ' ')}</strong></div><div><span>Redundancy rule</span><strong>{edge.group_mode} · {edge.group_id}</strong></div><div><span>Accountable owner</span><strong>{edge.owner || 'Owner assignment required'}</strong></div><div><span>Last validated</span><strong>{edge.last_validated || 'Not validated'}</strong></div><div><span>Owner review due</span><strong className={reviewOverdue ? 'overdue-text' : ''}>{edge.review_due_date || 'No review date set'}{reviewOverdue ? ' · overdue' : ''}</strong></div></div>
    {reviewOverdue && <div className="overdue-review-note"><AlertTriangle size={13} /><span>Owner review is overdue. This relationship remains in scenario calculations until an owner updates its status.</span></div>}
    <div className="evidence-card"><div className="evidence-heading"><FileText size={14} /><span>SOURCE EVIDENCE</span><small>{edge.evidence_ref}</small></div><blockquote>“{edge.evidence}”</blockquote><small className="evidence-owner">Recorded by {edge.owner || 'unassigned owner'}</small></div>
    {edge.conditions.length > 0 && <div className="detail-section"><div className="section-title"><span>CONDITIONS</span></div>{edge.conditions.map((condition, index) => <p className="condition-copy" key={index}>{condition}</p>)}</div>}
    {edge.assumptions.length > 0 && <div className="detail-section"><div className="section-title"><span>ASSUMPTIONS</span></div>{edge.assumptions.map((assumption, index) => <div className="unknown-item" key={index}><AlertTriangle size={13} /><span>{assumption.text}<small>{assumption.support_status} {assumption.evidence_ref && `· ${assumption.evidence_ref}`}</small></span></div>)}</div>}
    <div className="edge-workflow"><div className="workflow-title"><CheckCircle2 size={14} /> Human validation workflow</div><p>{edge.verification_status === 'verified' ? 'A human owner has marked this relationship verified. It can influence declared scenario results.' : 'This relationship stays outside official scenario propagation until an owner confirms its evidence and conditions.'}</p><button className="button button-outline full-button" onClick={onEdit}>{edge.verification_status === 'verified' ? 'Edit relationship' : 'Review and validate'}</button></div>
  </div>
}

function EdgeModal({ edge, graph, onClose, onSave }: { edge: Edge; graph: GraphData; onClose: () => void; onSave: (edge: Edge) => void }) {
  const [form, setForm] = useState<Edge>({ ...edge, conditions: [...edge.conditions], assumptions: [...edge.assumptions] })
  const [evidenceRef, setEvidenceRef] = useState(edge.evidence_ref)
  const existing = graph.edges.some((item) => item.id === edge.id)
  const update = (key: keyof Edge, value: string) => setForm((current) => ({ ...current, [key]: value }))
  const verify = () => onSave({ ...form, evidence_ref: evidenceRef, verification_status: 'verified', last_validated: new Date().toISOString().slice(0, 10), owner: form.owner.trim() || 'Demo reviewer' })
  const saveReviewState = () => {
    if (form.verification_status === 'verified') return verify()
    onSave({ ...form, evidence_ref: evidenceRef, verification_status: form.verification_status, last_validated: null })
  }
  const actionLabel = form.verification_status === 'verified' ? 'Verify relationship' : form.verification_status === 'rejected' ? 'Reject relationship' : form.verification_status === 'unknown' ? 'Save as unknown' : 'Save as proposed'
  return <div className="modal-backdrop" onClick={onClose}><div className="edge-modal" onClick={(event) => event.stopPropagation()}>
    <div className="modal-header"><div><span className="eyebrow">DEPENDENCY REGISTER</span><h2>{graph.edges.some((item) => item.id === edge.id) ? 'Review relationship' : 'Add relationship'}</h2></div><button className="icon-button" onClick={onClose}><X size={17} /></button></div>
    <p className="modal-intro">Every relationship needs a source, owner, and evidence. New relationships enter as proposed and are excluded from scenario results.</p>
    <div className="form-grid"><label>Provider / source<select value={form.source} onChange={(event) => update('source', event.target.value)}>{graph.nodes.map((node) => <option key={node.id} value={node.id}>{node.name}</option>)}</select></label><label>Dependent service<select value={form.dependent} onChange={(event) => update('dependent', event.target.value)}><option value="">Choose service…</option>{graph.nodes.map((node) => <option key={node.id} value={node.id}>{node.name}</option>)}</select></label>
      <label>Dependency type<select value={form.dependency_type} onChange={(event) => update('dependency_type', event.target.value)}>{['power', 'water', 'telecommunications', 'data_connectivity', 'transport', 'fuel', 'staff', 'other'].map((type) => <option key={type} value={type}>{type.replaceAll('_', ' ')}</option>)}</select></label><label>Redundancy group<select value={form.group_mode} onChange={(event) => update('group_mode', event.target.value)}><option value="ANY">ANY · one supplier is enough</option><option value="ALL">ALL · every supplier is required</option></select></label>
      <label className="span-two">Group identifier<input value={form.group_id} onChange={(event) => update('group_id', event.target.value)} placeholder="e.g. hospital-power" /></label><label className="span-two">Source evidence<textarea value={form.evidence} onChange={(event) => update('evidence', event.target.value)} placeholder="Quote the continuity plan or service owner statement…" rows={3} /></label><label>Evidence reference<input value={evidenceRef} onChange={(event) => setEvidenceRef(event.target.value)} placeholder="Document · page / section" /></label><label>Accountable owner<input value={form.owner} onChange={(event) => update('owner', event.target.value)} placeholder="Service owner" /></label>
      <label className="span-two">Conditions and assumptions<input value={form.conditions.join('; ')} onChange={(event) => setForm((current) => ({ ...current, conditions: event.target.value ? event.target.value.split(';').map((item) => item.trim()) : [] }))} placeholder="Conditions, assumptions, or unmodeled limits" /></label>
      <label>Owner review due<input type="date" value={form.review_due_date ?? ''} onChange={(event) => setForm((current) => ({ ...current, review_due_date: event.target.value || null }))} /><small>Set this with the service owner. An overdue date raises a warning; it does not change relationship status automatically.</small></label>
      {existing && <label className="span-two">Review state<select value={form.verification_status} onChange={(event) => update('verification_status', event.target.value)}><option value="proposed">Proposed · needs review</option><option value="verified">Verified · owner approved</option><option value="unknown">Unknown · unresolved</option><option value="rejected">Rejected · retain evidence trail</option></select></label>}
    </div>
    <div className="modal-footer"><button className="button button-secondary" onClick={onClose}>Cancel</button>{existing && form.verification_status !== 'proposed' && <button className="button button-secondary" onClick={() => onSave({ ...form, evidence_ref: evidenceRef, verification_status: 'proposed', last_validated: null })}><ClipboardList size={14} /> Save as proposed</button>}<button className="button button-primary" onClick={existing ? saveReviewState : () => onSave({ ...form, evidence_ref: evidenceRef, verification_status: 'proposed', last_validated: null })} disabled={!form.source || !form.dependent || !form.evidence.trim() || !evidenceRef.trim()}><ShieldCheck size={14} /> {existing ? actionLabel : 'Save proposal for review'}</button></div>
  </div></div>
}

function AssessmentModal({ assessment, onClose, onChecklist }: { assessment: Assessment; onClose: () => void; onChecklist: () => void }) {
  return <div className="modal-backdrop" onClick={onClose}><div className="assessment-modal" onClick={(event) => event.stopPropagation()}>
    <div className="modal-header"><div><span className="eyebrow">CONTINUITYMAP PLANNING ASSISTANT</span><h2>Evidence-linked continuity review</h2></div><button className="icon-button" onClick={onClose}><X size={17} /></button></div>
    <div className="assessment-mode"><Sparkles size={14} /><strong>{assessment.mode === 'local_ollama_grounded' ? 'Local model · evidence checked' : 'Structured evidence summary'}</strong><span>{assessment.state_changed ? 'State changed' : 'No status or plan changes'}</span></div>
    <div className="assessment-section"><h3>Summary</h3><p>{assessment.summary}</p></div>
    <div className="assessment-columns"><section className="assessment-section"><h3>Affected services <small>{assessment.affected_services.length}</small></h3>{assessment.affected_services.slice(0, 10).map((item) => <div className="assessment-line" key={item.id}><strong>{item.name}</strong><span>{item.reason}</span><small>{item.evidence_refs.join(', ') || 'Explicit disruption seed'}</small></div>)}</section><section className="assessment-section"><h3>Fallback resources</h3>{assessment.available_fallback_resources.map((item) => <div className="assessment-bullet" key={item}><CheckCircle2 size={13} />{item}</div>)}<h3 className="second-heading">Evidence gaps</h3>{assessment.missing_contingency_evidence.slice(0, 8).map((item, index) => <div className="assessment-bullet amber-bullet" key={`${item}-${index}`}><CircleHelp size={13} />{item}</div>)}</section></div>
    <div className="assessment-section"><h3>Suggested owner review actions</h3><ol className="action-list">{assessment.suggested_planning_actions.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ol></div>
    <div className="assessment-foot"><AlertTriangle size={13} /><span>{assessment.caveat}</span></div>
    <div className="modal-footer"><button className="button button-secondary" onClick={onClose}>Close</button><button className="button button-primary" onClick={onChecklist}><Download size={14} /> Export human review checklist</button></div>
  </div></div>
}

export default App
