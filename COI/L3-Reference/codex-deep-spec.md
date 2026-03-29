# Codex Deep — Graph Structure Specification
Layer 3 Reference. Immutable once ratified. Version 1.0 — 2026-03-29.

## What Codex Deep Is
Codex Deep is the knowledge graph foundation for COI V6 and Forge V2.
It replaces flat file memory with a structured graph of nodes and typed edges.
Every concept, component, model, decision, and person in COI's world is a node.
Relationships between them are edges. Retrieval is graph traversal — not file scanning.

---

## Node Structure

Every node in the graph has exactly these fields:

```json
{
  "id": "unique_snake_case_identifier",
  "type": "component|pipeline|model|concept|reference|person|open_loop|decision",
  "tag": "oneword",
  "shorthand": "2-3 sentences. What this is, why it matters, what it connects to.",
  "content_path": "relative/or/absolute/path/to/full/content",
  "weight": 0.0,
  "created": "YYYY-MM-DD",
  "updated": "YYYY-MM-DD",
  "edges": []
}
```

### Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier. Snake_case. Never changes once set. |
| type | enum | One of eight node types (see below). |
| tag | string | Single word. Used for ultra-fast lookup and graph traversal. |
| shorthand | string | 2-3 sentences. Retrieved first — full content only loaded if needed. |
| content_path | string | Path to the full document, file, or data this node represents. |
| weight | float | 0.0–1.0. Importance score. Drives ranking in query results. |
| created | date | ISO date when node was first created. |
| updated | date | ISO date when node was last modified. |
| edges | array | List of edge objects connecting this node to others. |

---

## Node Types

| Type | What It Represents |
|------|-------------------|
| component | A running piece of software (main.py, forge_manager.py, etc.) |
| pipeline | A processing stage or workflow (Forge pipeline stages, V6 pipelines) |
| model | An LLM or AI model in the roster |
| concept | An architectural idea or rule (VRAM cap, one-model rule, GraphRAG) |
| reference | A Codex document (constitution, roadmap, spec files) |
| person | A human in COI's world (Dave) |
| open_loop | An unresolved item that needs attention |
| decision | A recorded decision with rationale |

---

## Edge Structure

Every edge is an object inside a node's `edges` array:

```json
{
  "to": "target_node_id",
  "rel": "edge_type",
  "weight": 0.0
}
```

| Field | Description |
|-------|-------------|
| to | The id of the target node. Must reference a real node in the graph. |
| rel | The relationship type (see edge types below). |
| weight | 0.0–1.0. Strength of this connection. Drives traversal priority. |

---

## Edge Types

| Type | Meaning | Example |
|------|---------|---------|
| is_part_of | This node belongs to or is a subsystem of another | forge_manager is_part_of coi_desktop_v5 |
| depends_on | This node requires another node to function | coi_desktop_v5 depends_on vram_manager |
| implements | This node is the code/execution of a concept | vram_manager implements concept_vram_cap |
| feeds_into | Output of this node flows into another | pipeline_review feeds_into pipeline_sandbox |
| routes_to | This node sends jobs or data to another | forge_manager routes_to dept_engineering |
| used_by | This model or tool is used by a component | model_gemma3_4b used_by dept_forge_analyst |
| references | This node documents or describes another | ref_constitution references coi_desktop_v5 |

---

## Content Tiers

Every node has three access tiers. Retrieval starts at tier 1 and goes deeper only when needed.

| Tier | Field | Size | Use |
|------|-------|------|-----|
| 1 — Tag | tag | 1 word | Graph traversal, instant lookup |
| 2 — Shorthand | shorthand | 2-3 sentences | Most queries resolve here |
| 3 — Full content | content_path | Full file | Load only when detail is required |

---

## Weight System

Node weights drive ranking. Higher weight = surfaces first in query results.

| Weight | Level | Examples |
|--------|-------|---------|
| 1.0 | Mission critical | COI desktop, Forge Manager, VRAM rules, Dave, Claude Sonnet |
| 0.9 | Core infrastructure | VRAM manager, router model, key concepts |
| 0.8 | Important | Forge departments, active tools, reference docs |
| 0.7 | Supporting | Secondary tools, background services |
| 0.6 | Contextual | Open loops, session data |
| 0.4–0.5 | Low priority | Deprecated paths, over-cap models |

Edge weights follow the same scale. Frequently-traversed edges increase in weight over time.

---

## Graph Storage

The live graph lives at:
`COI/L4-Working/graph/codex-graph.json`

Structure:
```json
{
  "meta": {
    "version": "1.0",
    "created": "YYYY-MM-DD",
    "schema": "codex-deep-v1",
    "node_count": 0,
    "last_updated": "YYYY-MM-DD"
  },
  "nodes": {
    "node_id": { ...node object... },
    "node_id": { ...node object... }
  }
}
```

Nodes are keyed by id for O(1) lookup. The graph is append-only by default —
nodes are added and updated, never deleted (mark deprecated instead).

---

## Rules

1. Every node id is unique and permanent. Never reuse a deleted id.
2. Every edge `to` field must reference a real node id in the graph.
3. Nodes are never deleted — set weight to 0.1 and add a `deprecated: true` field.
4. The graph file is the source of truth. Memory files are secondary.
5. Every session that makes a significant decision must write a decision node.
6. Open loop nodes are cleared (weight → 0.1, resolved: true) when resolved.
