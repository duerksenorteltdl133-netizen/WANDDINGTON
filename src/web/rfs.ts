import { callText } from "./vision.js";
import type { ProtocolSpec, MetricSpec } from "./protocol.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface RFSResult {
  overall: number;         // weighted average of computed dimensions
  result: number;          // Result Fidelity (0-1), always computed when paperMetrics available
  metric: number;          // Metric Fidelity (0-1), -1 if skipped
  protocol: number;        // Protocol Fidelity — always -1 in B1 (needs Protocol Oracle)
  biology: number;         // Biology Validity — always -1 in B1 (needs NCBI API)
  warnings: string[];
  details: {
    result_per_metric: Record<string, number>;
    metric_issues: string[];
  };
}

export interface ComputeRFSOptions {
  evalDescription?: string;  // how metrics were computed in this run (for Metric Fidelity)
  skipMetricFidelity?: boolean;
}

// ---------------------------------------------------------------------------
// Result Fidelity — pure math
// ---------------------------------------------------------------------------

const RESULT_WARN_THRESHOLD = 0.85;   // warn if relative error > 15%

export function computeResultFidelity(
  ourMetrics: Record<string, number>,
  paperMetrics: Record<string, number>,
): { score: number; perMetric: Record<string, number>; warnings: string[] } {
  const perMetric: Record<string, number> = {};
  const warnings: string[] = [];
  const scores: number[] = [];

  for (const [key, paperVal] of Object.entries(paperMetrics)) {
    if (key.startsWith("_")) continue;                   // skip _note fields
    const ourVal = ourMetrics[key];
    if (ourVal === undefined || ourVal === null) continue;

    const denom = Math.abs(paperVal) > 1e-9 ? Math.abs(paperVal) : 1;
    const relErr = Math.abs(ourVal - paperVal) / denom;
    const s = Math.max(0, 1 - relErr);
    perMetric[key] = s;
    scores.push(s);

    if (s < RESULT_WARN_THRESHOLD) {
      const pct = (relErr * 100).toFixed(1);
      warnings.push(
        `WARNING [Result]: ${key} differs by ${pct}% from paper ` +
        `(paper=${paperVal.toFixed(4)}, ours=${ourVal.toFixed(4)})`
      );
    }
  }

  const score = scores.length > 0
    ? scores.reduce((a, b) => a + b, 0) / scores.length
    : -1;

  if (score === -1) {
    warnings.push("INFO [Result]: No shared metrics found between run output and paper reported values.");
  }

  return { score, perMetric, warnings };
}

// ---------------------------------------------------------------------------
// Metric Fidelity — LLM-as-judge
// ---------------------------------------------------------------------------

interface MetricJudgeResponse {
  score: number;
  issues: string[];
}

function buildMetricFidelityPrompt(
  specMetrics: MetricSpec[],
  ourMetrics: Record<string, number>,
  evalDescription?: string,
): string {
  const specLines = specMetrics.map((m) => {
    const parts = [`- ${m.name}`];
    if (m.top_k !== undefined) parts.push(`top_k=${m.top_k}`);
    if (m.de_reference) parts.push(`de_reference=${m.de_reference}`);
    if (m.note) parts.push(`(${m.note})`);
    return parts.join(", ");
  }).join("\n");

  const ourLines = Object.entries(ourMetrics)
    .map(([k, v]) => `- ${k}: ${v}`)
    .join("\n");

  const descSection = evalDescription
    ? `\nEvaluation description from this run:\n${evalDescription}\n`
    : "";

  return `You are evaluating whether a computational biology experiment computed its metrics correctly according to the paper's specification.

Paper metric specification:
${specLines}

Metrics computed in this run:
${ourLines}
${descSection}
Task: Compare what was computed against the paper's specification. Focus on:
1. Are the metric names consistent? (e.g. using pearson_de when paper specifies pearson_de)
2. Is the top_k value correct? (e.g. paper says top-20 DEGs but code might use top-50)
3. Is the de_reference method correct? (observed_vs_control vs other baselines)
4. Any other discrepancy that would make the numbers not directly comparable to the paper.

Score 1.0 = metrics computed exactly as specified.
Score 0.5 = one significant discrepancy (e.g. wrong top_k).
Score 0.0 = metric completely different from specification.

Respond with JSON only, no other text:
{"score": <0.0 to 1.0>, "issues": ["<issue1>", "<issue2>"]}`;
}

function parseJudgeResponse(raw: string): MetricJudgeResponse {
  // Strip markdown code fences if present
  const cleaned = raw.replace(/```(?:json)?\n?/g, "").trim();
  try {
    const parsed = JSON.parse(cleaned) as { score?: number; issues?: unknown };
    const score = typeof parsed.score === "number"
      ? Math.min(1, Math.max(0, parsed.score))
      : 0.5;
    const issues = Array.isArray(parsed.issues)
      ? (parsed.issues as unknown[]).filter((i): i is string => typeof i === "string")
      : [];
    return { score, issues };
  } catch {
    // If JSON parse fails, try to extract a score number from the text
    const match = cleaned.match(/score["\s:]+([0-9.]+)/i);
    return {
      score: match ? Math.min(1, Math.max(0, parseFloat(match[1]!))) : 0.5,
      issues: ["Could not parse LLM response — score is approximate"],
    };
  }
}

export async function computeMetricFidelity(
  spec: ProtocolSpec,
  ourMetrics: Record<string, number>,
  evalDescription?: string,
): Promise<{ score: number; issues: string[] }> {
  const prompt = buildMetricFidelityPrompt(spec.metrics, ourMetrics, evalDescription);
  const result = await callText(prompt);
  return parseJudgeResponse(result.content);
}

// ---------------------------------------------------------------------------
// Main entry point
// ---------------------------------------------------------------------------

export async function computeRFS(
  spec: ProtocolSpec | null,
  ourMetrics: Record<string, number>,
  options: ComputeRFSOptions = {},
): Promise<RFSResult> {
  const warnings: string[] = [];
  const details: RFSResult["details"] = { result_per_metric: {}, metric_issues: [] };

  // --- Result Fidelity ---
  let resultScore = -1;
  if (spec?.reported_values && Object.keys(spec.reported_values).length > 0) {
    const rf = computeResultFidelity(ourMetrics, spec.reported_values);
    resultScore = rf.score;
    details.result_per_metric = rf.perMetric;
    warnings.push(...rf.warnings);
  } else {
    warnings.push("INFO [Result]: No reported_values in ProtocolSpec — skipping Result Fidelity.");
  }

  // --- Metric Fidelity ---
  let metricScore = -1;
  if (spec && !options.skipMetricFidelity) {
    try {
      const mf = await computeMetricFidelity(spec, ourMetrics, options.evalDescription);
      metricScore = mf.score;
      details.metric_issues = mf.issues;
      for (const issue of mf.issues) {
        warnings.push(`WARNING [Metric]: ${issue}`);
      }
    } catch (err) {
      warnings.push(`INFO [Metric]: LLM judge failed — ${(err as Error).message}`);
    }
  }

  // --- Stubs (future phases) ---
  const protocolScore = -1;
  const biologyScore = -1;

  if (!spec) {
    warnings.push("INFO [Protocol]: No ProtocolSpec provided — Protocol Fidelity skipped (use /paper-audit first).");
  } else {
    warnings.push("INFO [Protocol]: Protocol Fidelity not yet implemented (Phase C).");
  }
  warnings.push("INFO [Biology]: Biology Validity not yet implemented (Phase D).");

  // --- Overall score: average of computed dimensions only ---
  const computed = [resultScore, metricScore].filter((s) => s >= 0);
  const overall = computed.length > 0
    ? computed.reduce((a, b) => a + b, 0) / computed.length
    : -1;

  return {
    overall,
    result: resultScore,
    metric: metricScore,
    protocol: protocolScore,
    biology: biologyScore,
    warnings,
    details,
  };
}

// ---------------------------------------------------------------------------
// Formatting helper
// ---------------------------------------------------------------------------

export function formatRFS(r: RFSResult): string {
  const fmt = (v: number) => v < 0 ? "n/a" : v.toFixed(2);
  const lines = [
    `RFS = ${fmt(r.overall)} | Result: ${fmt(r.result)} | Metric: ${fmt(r.metric)} | Protocol: ${fmt(r.protocol)} | Biology: ${fmt(r.biology)}`,
    ...r.warnings,
  ];
  return lines.join("\n");
}
