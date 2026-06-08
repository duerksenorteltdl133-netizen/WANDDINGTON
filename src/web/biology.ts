import { execFile } from "node:child_process";
import { resolve } from "node:path";
import { promisify } from "node:util";
import { getWaddingtonHome } from "../config/paths.js";
import type { ConvMsg } from "./db.js";
import type { ProtocolSpec } from "./protocol.js";

const execFileAsync = promisify(execFile);

const GO_SCRIPT = resolve(
  getWaddingtonHome(), "..", "workspace", "evaluation", "go_enrichment.py"
);

const STRING_SCRIPT = resolve(
  getWaddingtonHome(), "..", "workspace", "evaluation", "string_network.py"
);

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface EnrichTerm {
  rank: number;
  term: string;
  pval: number;
  z_score: number;
  combined_score: number;
  genes: string[];
}

// ---------------------------------------------------------------------------
// Gene extraction from conversation messages
// ---------------------------------------------------------------------------

// Common abbreviations that match the gene-symbol pattern but are not genes
const STOPWORDS = new Set([
  "RNA", "DNA", "PCR", "HVG", "MSE", "AUC", "ROC", "GEO", "API", "GPU",
  "CPU", "KO", "WT", "DE", "GO", "FDR", "NaN", "NULL", "TRUE", "FALSE",
  "OK", "LOG", "VAE", "GNN", "MLP", "LLM", "RAG", "FTS", "RRF", "SQL",
  "CSV", "TSV", "JSON", "YAML", "PDF", "URL", "SSH", "PCA", "UMP", "TSNE",
]);

export function extractDeGenes(msgs: ConvMsg[]): string[] {
  // Match gene symbols: start with letter, all caps+digits, 2-8 chars
  const genePattern = /\b([A-Z][A-Z0-9]{1,7})\b/g;
  const counts = new Map<string, number>();

  for (const msg of msgs) {
    if (msg.role !== "assistant") continue;
    for (const m of msg.content.matchAll(genePattern)) {
      const word = m[1]!;
      if (!STOPWORDS.has(word)) {
        counts.set(word, (counts.get(word) ?? 0) + 1);
      }
    }
  }

  // Return genes mentioned ≥2 times to reduce noise, capped at 50
  return Array.from(counts.entries())
    .filter(([, n]) => n >= 2)
    .sort((a, b) => b[1] - a[1])
    .map(([gene]) => gene)
    .slice(0, 50);
}

// ---------------------------------------------------------------------------
// Metric plausibility check (fast, no network)
// ---------------------------------------------------------------------------

// Expected ranges for common perturbation metrics
const METRIC_RANGES: Record<string, [number, number]> = {
  pearson_de:    [0.05, 0.97],
  pearson:       [0.00, 0.99],
  pearson_delta: [0.00, 0.99],
  r2:            [0.00, 0.99],
};

export function checkMetricPlausibility(
  ourMetrics: Record<string, number>,
): { score: number; issues: string[] } {
  const issues: string[] = [];
  const checks: boolean[] = [];

  for (const [name, [lo, hi]] of Object.entries(METRIC_RANGES)) {
    const val = ourMetrics[name];
    if (val === undefined) continue;
    if (val < lo) {
      issues.push(
        `${name}=${val.toFixed(3)} is below expected minimum ${lo} — possible model failure or wrong metric`
      );
      checks.push(false);
    } else if (val > hi) {
      issues.push(
        `${name}=${val.toFixed(3)} is suspiciously high (>${hi}) — check for data leakage`
      );
      checks.push(false);
    } else {
      checks.push(true);
    }
  }

  const score = checks.length > 0
    ? checks.filter(Boolean).length / checks.length
    : 0.5; // no checks = neutral
  return { score, issues };
}

// ---------------------------------------------------------------------------
// GO enrichment via subprocess
// ---------------------------------------------------------------------------

async function runGoEnrichment(genes: string[]): Promise<EnrichTerm[]> {
  const { stdout } = await execFileAsync(
    "python3",
    [GO_SCRIPT, genes.join(",")],
    { timeout: 15_000 },
  );
  const result = JSON.parse(stdout) as { error?: string; results?: EnrichTerm[] };
  if (result.error) throw new Error(result.error);
  return result.results ?? [];
}

// ---------------------------------------------------------------------------
// STRING PPI enrichment via subprocess
// ---------------------------------------------------------------------------

interface StringPpiResult {
  number_of_nodes: number;
  number_of_edges: number;
  average_node_degree?: number;
  local_clustering_coefficient?: number;
  expected_number_of_edges: number;
  p_value: number;
}

async function runStringEnrichment(genes: string[]): Promise<StringPpiResult> {
  const { stdout } = await execFileAsync(
    "python3",
    [STRING_SCRIPT, genes.join(",")],
    { timeout: 20_000 },
  );
  const parsed = JSON.parse(stdout) as { error?: string; result?: StringPpiResult };
  if (parsed.error) throw new Error(parsed.error);
  if (!parsed.result) throw new Error("No PPI result returned");
  return parsed.result;
}

function scoreFromStringPpi(result: StringPpiResult): number {
  if (result.number_of_nodes < 3) return 0.3;  // too few genes mapped
  const p = result.p_value;
  if (p < 1e-5)  return 0.90;
  if (p < 0.001) return 0.75;
  if (p < 0.01)  return 0.60;
  if (p < 0.05)  return 0.45;
  return 0.20;
}

function scoreFromEnrichment(terms: EnrichTerm[]): number {
  if (terms.length === 0) return 0.3;
  const minPval = Math.min(...terms.map((t) => t.pval));
  if (minPval < 1e-5) return 0.95;
  if (minPval < 0.001) return 0.85;
  if (minPval < 0.01)  return 0.70;
  if (minPval < 0.05)  return 0.50;
  return 0.20;
}

// ---------------------------------------------------------------------------
// Main entry point
// ---------------------------------------------------------------------------

export async function computeBiologyValidity(
  ourMetrics: Record<string, number>,
  convMsgs: ConvMsg[],
  _spec?: ProtocolSpec,
): Promise<{ score: number; issues: string[] }> {
  const issues: string[] = [];

  // 1. Plausibility check (instant, no network)
  const plausibility = checkMetricPlausibility(ourMetrics);
  issues.push(...plausibility.issues);

  // 2. GO + STRING enrichment in parallel
  let enrichScore = 0.5;   // neutral fallback
  let stringScore: number | null = null;
  const genes = extractDeGenes(convMsgs);

  if (genes.length >= 3) {
    const [goResult, stringResult] = await Promise.allSettled([
      runGoEnrichment(genes),
      runStringEnrichment(genes),
    ]);

    // GO Biological Process
    if (goResult.status === "fulfilled") {
      const terms = goResult.value;
      enrichScore = scoreFromEnrichment(terms);
      if (terms.length > 0) {
        const top = terms[0]!;
        issues.push(`Top GO term: ${top.term} (p=${top.pval.toExponential(2)})`);
      }
      if (enrichScore < 0.4) {
        const minP = terms.length > 0
          ? Math.min(...terms.map((t) => t.pval)).toExponential(2)
          : "n/a";
        issues.push(
          `No significant GO enrichment (best p=${minP}) — DE genes may not reflect known biology`
        );
      }
    } else {
      issues.push(`GO enrichment unavailable: ${(goResult.reason as Error).message}`);
    }

    // STRING PPI network
    if (stringResult.status === "fulfilled") {
      const ppi = stringResult.value;
      stringScore = scoreFromStringPpi(ppi);
      if (ppi.number_of_nodes >= 3) {
        issues.push(
          `STRING PPI: ${ppi.number_of_edges} interactions among ${ppi.number_of_nodes} mapped genes` +
          ` (expected ${ppi.expected_number_of_edges.toFixed(1)}, p=${ppi.p_value.toExponential(2)})`
        );
      } else {
        issues.push(
          `STRING PPI: only ${ppi.number_of_nodes} gene(s) mapped — network analysis skipped`
        );
        stringScore = null; // don't penalise when mapping fails
      }
    } else {
      issues.push(`STRING PPI unavailable: ${(stringResult.reason as Error).message}`);
    }
  } else {
    issues.push(
      `Too few gene symbols detected (${genes.length}) — GO/STRING enrichment skipped`
    );
  }

  // Combined score:
  //   With STRING:    plausibility 30% + GO 40% + STRING 30%
  //   Without STRING: plausibility 40% + GO 60%  (D1 fallback)
  const score = stringScore !== null
    ? 0.3 * plausibility.score + 0.4 * enrichScore + 0.3 * stringScore
    : 0.4 * plausibility.score + 0.6 * enrichScore;

  return { score: Math.min(1, Math.max(0, score)), issues };
}
