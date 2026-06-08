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

  // 2. GO enrichment
  let enrichScore = 0.5; // neutral when no enrichment
  const genes = extractDeGenes(convMsgs);

  if (genes.length >= 3) {
    try {
      const terms = await runGoEnrichment(genes);
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
    } catch (err) {
      issues.push(`GO enrichment unavailable: ${(err as Error).message}`);
      // Keep enrichScore = 0.5 (neutral) on failure
    }
  } else {
    issues.push(
      `Too few gene symbols detected (${genes.length}) — GO enrichment skipped`
    );
  }

  // Combined: plausibility 40% + enrichment 60%
  const score = Math.min(1, Math.max(0, 0.4 * plausibility.score + 0.6 * enrichScore));
  return { score, issues };
}
