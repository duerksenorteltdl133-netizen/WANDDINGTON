import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { getWaddingtonHome } from "../config/paths.js";

// ---------------------------------------------------------------------------
// Schema
// ---------------------------------------------------------------------------

export interface DatasetSpec {
  name: string;
  geo_accession?: string;
  cell_line?: string;
  organism?: string;
  perturbation_count?: number;
}

export type SplitType =
  | "combination_holdout"
  | "single_holdout"
  | "random"
  | "custom";

export interface SplitSpec {
  type: SplitType;
  unseen_single?: boolean;
  test_fraction?: number;
  seed?: number;
  note?: string;
}

export interface PreprocessSpec {
  normalization: "log1p" | "scran" | "none" | string;
  n_hvg?: number;
  min_genes?: number;
  min_cells?: number;
  note?: string;
}

export interface MetricSpec {
  name: string;
  top_k?: number;
  de_reference?: "observed_vs_control" | "paper_provided" | string;
  primary?: boolean;
  note?: string;
}

export interface ProtocolSpec {
  // Paper identity
  paper_slug: string;
  paper_title?: string;
  arxiv_id?: string;
  year?: number;
  github_url?: string;

  // Experimental setup
  dataset: DatasetSpec;
  perturbation_type: "CRISPRi" | "CRISPRa" | "overexpression" | "knockout" | string;
  split: SplitSpec;
  preprocess: PreprocessSpec;

  // Metric definitions (as described in the paper)
  metrics: MetricSpec[];

  // Ground-truth values reported in the paper (for Result Fidelity)
  reported_values?: Record<string, number>;

  // Provenance
  notes?: string;
  annotated_by: "human" | "llm";
  annotated_at?: string;
}

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------

function papersDir(): string {
  return resolve(getWaddingtonHome(), "..", "workspace", "papers");
}

export function protocolPath(slug: string): string {
  return join(papersDir(), slug, "protocol.json");
}

// ---------------------------------------------------------------------------
// I/O
// ---------------------------------------------------------------------------

export function loadProtocolSpec(slug: string): ProtocolSpec | null {
  const path = protocolPath(slug);
  if (!existsSync(path)) return null;
  try {
    return JSON.parse(readFileSync(path, "utf8")) as ProtocolSpec;
  } catch {
    return null;
  }
}

export function saveProtocolSpec(spec: ProtocolSpec): void {
  const dir = join(papersDir(), spec.paper_slug);
  mkdirSync(dir, { recursive: true });
  writeFileSync(
    join(dir, "protocol.json"),
    JSON.stringify(spec, null, 2) + "\n",
    "utf8"
  );
}

export function listProtocolSlugs(): string[] {
  if (!existsSync(papersDir())) return [];
  const { readdirSync } = require("node:fs");
  return readdirSync(papersDir(), { withFileTypes: true })
    .filter((d: { isDirectory: () => boolean }) => d.isDirectory())
    .map((d: { name: string }) => d.name)
    .filter((name: string) => existsSync(join(papersDir(), name, "protocol.json")));
}

// ---------------------------------------------------------------------------
// Validation (light — just checks required fields exist)
// ---------------------------------------------------------------------------

export function isProtocolSpec(obj: unknown): obj is ProtocolSpec {
  if (!obj || typeof obj !== "object") return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.paper_slug === "string" &&
    typeof o.dataset === "object" &&
    typeof o.split === "object" &&
    typeof o.preprocess === "object" &&
    Array.isArray(o.metrics) &&
    (o.annotated_by === "human" || o.annotated_by === "llm")
  );
}

// ---------------------------------------------------------------------------
// Primary metric helper
// ---------------------------------------------------------------------------

export function primaryMetric(spec: ProtocolSpec): MetricSpec | undefined {
  return spec.metrics.find((m) => m.primary) ?? spec.metrics[0];
}
