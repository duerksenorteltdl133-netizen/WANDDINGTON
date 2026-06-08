import { randomUUID } from "node:crypto";
import { callText } from "./vision.js";
import { dbInsertHypothesis, dbListHypotheses, dbListExperiments, type HypothesisRecord, type ConvMsg } from "./db.js";
import { extractDeGenes } from "./biology.js";

// ---------------------------------------------------------------------------
// Prompt builder
// ---------------------------------------------------------------------------

function buildHypothesisPrompt(
  gene: string,
  model: string | null,
  dataset: string | null,
  metrics: Record<string, number>,
  deGenes: string[],
  priorContext: string,
): string {
  const metricsStr = Object.entries(metrics)
    .map(([k, v]) => `${k}=${v.toFixed(4)}`)
    .join(", ");

  const deSection = deGenes.length > 0
    ? `\nTop DE genes detected in this run: ${deGenes.slice(0, 20).join(", ")}`
    : "";

  const priorSection = priorContext
    ? `\nPrior experiments on related genes:\n${priorContext}`
    : "";

  return `You are a computational biology research assistant analyzing a gene perturbation experiment.

Current experiment:
- Gene: ${gene}
- Model: ${model ?? "unknown"}
- Dataset: ${dataset ?? "unknown"}
- Metrics: ${metricsStr}${deSection}${priorSection}

Generate 1-2 concise, testable biological hypotheses based on these results.
Each hypothesis should:
1. Make a specific, falsifiable claim about gene function, pathway membership, or model behaviour
2. Reference the evidence from this experiment
3. Suggest a follow-up experiment to test it
4. Assign a confidence: "speculative" (no prior support), "supported" (consistent with prior), or "refuted" (contradicts prior)

Return JSON only:
[
  {
    "hypothesis": "<one sentence testable claim>",
    "evidence": "<specific numbers/genes from this experiment that support it>",
    "confidence": "speculative" | "supported" | "refuted",
    "suggested_followup": "<one sentence next experiment>"
  }
]`;
}

// ---------------------------------------------------------------------------
// Prior context builder
// ---------------------------------------------------------------------------

function buildPriorContext(gene: string): string {
  // Fetch recent experiments on same or related gene (simple prefix match)
  const exps = dbListExperiments({ limit: 50 });
  const related = exps.filter(e =>
    e.gene && (
      e.gene.toUpperCase() === gene.toUpperCase() ||
      gene.toUpperCase().includes(e.gene.toUpperCase()) ||
      e.gene.toUpperCase().includes(gene.toUpperCase())
    )
  ).slice(0, 5);

  if (related.length === 0) return "";

  return related.map(e => {
    const m = JSON.parse(e.metrics || "{}") as Record<string, number>;
    const mStr = Object.entries(m).map(([k, v]) => `${k}=${v.toFixed(3)}`).join(", ");
    return `  ${e.gene} (${e.model ?? "?"} on ${e.dataset ?? "?"}): ${mStr}`;
  }).join("\n");
}

// ---------------------------------------------------------------------------
// Response parser
// ---------------------------------------------------------------------------

interface RawHypothesis {
  hypothesis?: string;
  evidence?: string;
  confidence?: string;
  suggested_followup?: string;
}

function parseHypothesesResponse(raw: string): RawHypothesis[] {
  const cleaned = raw.replace(/```(?:json)?\n?/g, "").trim();
  try {
    const parsed = JSON.parse(cleaned);
    return Array.isArray(parsed) ? (parsed as RawHypothesis[]) : [];
  } catch {
    return [];
  }
}

// ---------------------------------------------------------------------------
// Main entry point
// ---------------------------------------------------------------------------

export async function generateHypotheses(
  gene: string,
  model: string | null,
  dataset: string | null,
  metrics: Record<string, number>,
  convMsgs: ConvMsg[],
  expId: string,
  convId: string,
): Promise<HypothesisRecord[]> {
  if (!gene || Object.keys(metrics).length === 0) return [];

  const deGenes = extractDeGenes(convMsgs);
  const priorContext = buildPriorContext(gene);
  const prompt = buildHypothesisPrompt(gene, model, dataset, metrics, deGenes, priorContext);

  const result = await callText(prompt);
  const parsed = parseHypothesesResponse(result.content);

  const saved: HypothesisRecord[] = [];
  for (const h of parsed.slice(0, 2)) {  // cap at 2 hypotheses
    if (!h.hypothesis) continue;
    const confidence = (["speculative", "supported", "refuted"] as const)
      .includes(h.confidence as "speculative" | "supported" | "refuted")
      ? (h.confidence as "speculative" | "supported" | "refuted")
      : "speculative";

    const rec = dbInsertHypothesis({
      id: randomUUID(),
      gene: gene.toUpperCase(),
      related_genes: JSON.stringify(deGenes.slice(0, 10)),
      model: model ?? null,
      dataset: dataset ?? null,
      hypothesis: h.hypothesis,
      evidence: h.evidence ?? "",
      confidence,
      exp_id: expId,
      conv_id: convId,
    });
    saved.push(rec);
  }
  return saved;
}

// ---------------------------------------------------------------------------
// Retrieve hypotheses relevant to a gene (for context injection)
// ---------------------------------------------------------------------------

export function getHypothesesForGene(gene: string, limit = 5): HypothesisRecord[] {
  return dbListHypotheses({ gene: gene.toUpperCase(), limit });
}

export function formatHypothesesContext(hypotheses: HypothesisRecord[]): string {
  if (hypotheses.length === 0) return "";
  const lines = hypotheses.map(h =>
    `[${h.confidence.toUpperCase()}] ${h.hypothesis} (Evidence: ${h.evidence})`
  );
  return `Prior hypotheses for this gene:\n${lines.join("\n")}`;
}
