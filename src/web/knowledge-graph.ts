import { randomUUID } from "node:crypto";
import { callText } from "./vision.js";
import { getDb, type ConvMsg } from "./db.js";
import type { ProtocolSpec } from "./protocol.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type NodeType = "Paper" | "Model" | "Gene" | "Dataset" | "Metric" | "CellType";
export type RelType =
  | "benchmarks_on"   // Paper → Dataset
  | "claims"          // Paper → Metric  (props: value)
  | "evaluated_by"    // Model → Paper
  | "perturbed_in"    // Gene  → Dataset
  | "uses_metric"     // Paper → Metric
  | "part_of";        // Gene  → CellType (pathway membership)

export interface KgNode {
  id: string;        // "{type}:{label}" e.g. "paper:gears-2024"
  type: NodeType;
  label: string;
  props: Record<string, unknown>;
}

export interface KgEdge {
  id: string;
  src: string;
  rel: RelType;
  dst: string;
  props: Record<string, unknown>;
}

interface NodeRow { id: string; type: string; label: string; props_json: string; }
interface EdgeRow { id: string; src: string; rel: string; dst: string; props_json: string; }

// Convenience: deterministic node id from type + label
export function nodeId(type: NodeType, label: string): string {
  return `${type.toLowerCase()}:${label.toLowerCase().replace(/\s+/g, "-")}`;
}

// ---------------------------------------------------------------------------
// Low-level upsert helpers
// ---------------------------------------------------------------------------

export function kgUpsertNode(node: KgNode): void {
  getDb().prepare(`
    INSERT INTO kg_nodes (id, type, label, props_json)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
      label = excluded.label, props_json = excluded.props_json
  `).run(node.id, node.type, node.label, JSON.stringify(node.props));
}

export function kgUpsertEdge(edge: KgEdge): void {
  getDb().prepare(`
    INSERT INTO kg_edges (id, src, rel, dst, props_json)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(src, rel, dst) DO UPDATE SET props_json = excluded.props_json
  `).run(edge.id, edge.src, edge.rel, edge.dst, JSON.stringify(edge.props));
}

// ---------------------------------------------------------------------------
// Seed from ProtocolSpec (no LLM needed)
// ---------------------------------------------------------------------------

export function seedFromProtocol(spec: ProtocolSpec): void {
  const paperId   = nodeId("Paper",   spec.paper_slug);
  const modelId   = nodeId("Model",   spec.paper_slug);
  const datasetId = nodeId("Dataset", spec.dataset.name);

  kgUpsertNode({ id: paperId,   type: "Paper",   label: spec.paper_slug,
    props: { title: spec.paper_title, year: spec.year, arxiv_id: spec.arxiv_id } });
  kgUpsertNode({ id: modelId,   type: "Model",   label: spec.paper_slug,
    props: { github_url: spec.github_url } });
  kgUpsertNode({ id: datasetId, type: "Dataset", label: spec.dataset.name,
    props: { geo_accession: spec.dataset.geo_accession, cell_line: spec.dataset.cell_line } });

  kgUpsertEdge({ id: randomUUID(), src: paperId, rel: "benchmarks_on", dst: datasetId,
    props: { perturbation_type: spec.perturbation_type } });

  for (const m of spec.metrics) {
    const metricId = nodeId("Metric", m.name);
    kgUpsertNode({ id: metricId, type: "Metric", label: m.name,
      props: { top_k: m.top_k, de_reference: m.de_reference } });
    kgUpsertEdge({ id: randomUUID(), src: paperId, rel: "uses_metric", dst: metricId,
      props: { primary: m.primary ?? false } });
    const reported = spec.reported_values?.[m.name];
    if (reported !== undefined) {
      kgUpsertEdge({ id: randomUUID(), src: paperId, rel: "claims", dst: metricId,
        props: { value: reported } });
    }
  }

  kgUpsertEdge({ id: randomUUID(), src: modelId, rel: "evaluated_by", dst: paperId, props: {} });
}

// ---------------------------------------------------------------------------
// LLM-based entity extraction from /discuss conversation
// ---------------------------------------------------------------------------

const EXTRACT_PROMPT = `You are extracting a knowledge graph from a computational biology conversation.

Conversation (last 6000 chars):
{TEXT}

Extract entities and relationships. Return JSON only:
{
  "nodes": [
    { "type": "Paper|Model|Gene|Dataset|Metric|CellType", "label": "<name>" }
  ],
  "edges": [
    { "src_label": "<label>", "src_type": "<type>",
      "rel": "benchmarks_on|claims|evaluated_by|perturbed_in|uses_metric|part_of",
      "dst_label": "<label>", "dst_type": "<type>",
      "props": {} }
  ]
}

Rules:
- Only include entities clearly mentioned, do not invent
- Gene labels must be uppercase symbols (e.g. CEBPE, GFI1)
- Model labels: GEARS, scGPT, CPA, SAMS-VAE etc.
- Dataset labels: Norman2019, Replogle2022 etc.
- Metric labels: pearson_de, pearson, r2, mse etc.
- For "claims" edges, add props: {"value": <number>} if a result is stated
- Max 20 nodes and 30 edges`;

interface RawExtraction {
  nodes?: Array<{ type?: string; label?: string }>;
  edges?: Array<{
    src_label?: string; src_type?: string;
    rel?: string;
    dst_label?: string; dst_type?: string;
    props?: Record<string, unknown>;
  }>;
}

const VALID_NODE_TYPES = new Set<string>(["Paper","Model","Gene","Dataset","Metric","CellType"]);
const VALID_REL_TYPES  = new Set<string>(
  ["benchmarks_on","claims","evaluated_by","perturbed_in","uses_metric","part_of"]
);

export async function extractAndStoreKg(
  msgs: ConvMsg[],
): Promise<{ nodes: number; edges: number }> {
  const text = msgs
    .map(m => `${m.role}: ${m.content}`)
    .join("\n")
    .slice(-6000);

  const prompt = EXTRACT_PROMPT.replace("{TEXT}", text);
  const result = await callText(prompt);

  const cleaned = result.content.replace(/```(?:json)?\n?/g, "").trim();
  let raw: RawExtraction;
  try { raw = JSON.parse(cleaned) as RawExtraction; }
  catch { return { nodes: 0, edges: 0 }; }

  let nodeCount = 0;
  let edgeCount = 0;

  for (const n of raw.nodes ?? []) {
    if (!n.label || !n.type || !VALID_NODE_TYPES.has(n.type)) continue;
    kgUpsertNode({ id: nodeId(n.type as NodeType, n.label),
      type: n.type as NodeType, label: n.label, props: {} });
    nodeCount++;
  }

  for (const e of raw.edges ?? []) {
    if (!e.src_label || !e.src_type || !e.dst_label || !e.dst_type) continue;
    if (!e.rel || !VALID_REL_TYPES.has(e.rel)) continue;
    if (!VALID_NODE_TYPES.has(e.src_type) || !VALID_NODE_TYPES.has(e.dst_type)) continue;

    const srcId = nodeId(e.src_type as NodeType, e.src_label);
    const dstId = nodeId(e.dst_type as NodeType, e.dst_label);
    // Ensure endpoint nodes exist
    kgUpsertNode({ id: srcId, type: e.src_type as NodeType, label: e.src_label, props: {} });
    kgUpsertNode({ id: dstId, type: e.dst_type as NodeType, label: e.dst_label, props: {} });
    kgUpsertEdge({ id: randomUUID(), src: srcId, rel: e.rel as RelType,
      dst: dstId, props: e.props ?? {} });
    edgeCount++;
  }

  return { nodes: nodeCount, edges: edgeCount };
}

// ---------------------------------------------------------------------------
// Graph query: neighbourhood up to given depth
// ---------------------------------------------------------------------------

export function queryNeighbourhood(
  nodeIdOrLabel: string,
  depth = 2,
): { nodes: KgNode[]; edges: KgEdge[] } {
  const db = getDb();
  const startRow = (
    db.prepare("SELECT * FROM kg_nodes WHERE id = ?").get(nodeIdOrLabel) ??
    db.prepare("SELECT * FROM kg_nodes WHERE label = ? COLLATE NOCASE").get(nodeIdOrLabel)
  ) as NodeRow | undefined;

  if (!startRow) return { nodes: [], edges: [] };

  const visitedNodes = new Map<string, KgNode>();
  const visitedEdges = new Map<string, KgEdge>();
  const toVisit = [startRow.id];

  for (let d = 0; d < depth && toVisit.length > 0; d++) {
    const current = toVisit.splice(0);
    for (const nid of current) {
      const row = db.prepare("SELECT * FROM kg_nodes WHERE id = ?").get(nid) as NodeRow | undefined;
      if (!row || visitedNodes.has(nid)) continue;
      visitedNodes.set(nid, { id: row.id, type: row.type as NodeType,
        label: row.label, props: JSON.parse(row.props_json) as Record<string, unknown> });

      const edges = db.prepare(
        "SELECT * FROM kg_edges WHERE src = ? OR dst = ?"
      ).all(nid, nid) as EdgeRow[];

      for (const e of edges) {
        if (!visitedEdges.has(e.id)) {
          visitedEdges.set(e.id, { id: e.id, src: e.src, rel: e.rel as RelType,
            dst: e.dst, props: JSON.parse(e.props_json) as Record<string, unknown> });
          const neighbour = e.src === nid ? e.dst : e.src;
          if (!visitedNodes.has(neighbour)) toVisit.push(neighbour);
        }
      }
    }
  }

  return { nodes: Array.from(visitedNodes.values()), edges: Array.from(visitedEdges.values()) };
}

// ---------------------------------------------------------------------------
// Stats
// ---------------------------------------------------------------------------

export function kgStats(): { nodes: number; edges: number } {
  const db = getDb();
  const nodes = (db.prepare("SELECT COUNT(*) as n FROM kg_nodes").get() as { n: number }).n;
  const edges = (db.prepare("SELECT COUNT(*) as n FROM kg_edges").get() as { n: number }).n;
  return { nodes, edges };
}
