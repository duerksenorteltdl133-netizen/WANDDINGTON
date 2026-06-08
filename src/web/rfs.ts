import { callText } from "./vision.js";
import type { ProtocolSpec, MetricSpec } from "./protocol.js";
import type { ConvMsg } from "./db.js";
import { computeBiologyValidity } from "./biology.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface RFSResult {
  overall: number;         // weighted average of computed dimensions
  result: number;          // Result Fidelity (0-1), always computed when paperMetrics available
  metric: number;          // Metric Fidelity (0-1), -1 if skipped
  protocol: number;        // Protocol Fidelity (0-1), -1 if no conv msgs or no spec
  biology: number;         // Biology Validity (GO + STRING enrichment), -1 if skipped
  warnings: string[];
  details: {
    result_per_metric: Record<string, number>;
    metric_issues: string[];
    protocol_issues: string[];
    biology_issues: string[];
  };
}

export interface ComputeRFSOptions {
  evalDescription?: string;  // how metrics were computed in this run (for Metric Fidelity)
  convMsgs?: ConvMsg[];      // conversation messages for Protocol + Biology judges
  skipMetricFidelity?: boolean;
  skipProtocolFidelity?: boolean;
  skipBiologyValidity?: boolean;
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
// Protocol Fidelity — LLM-as-judge comparing ProtocolSpec vs run code
// ---------------------------------------------------------------------------

function extractCodeBlocks(msgs: ConvMsg[]): string {
  const blocks: string[] = [];
  for (const msg of msgs) {
    if (msg.role !== "assistant") continue;
    // Extract fenced Python blocks
    for (const m of msg.content.matchAll(/```(?:python|bash|sh)?\n([\s\S]*?)```/g)) {
      if (m[1]?.trim()) blocks.push(m[1].trim());
    }
  }
  // Cap at 6000 chars to stay within prompt budget
  return blocks.join("\n\n# ---\n\n").slice(0, 6000);
}

function buildProtocolFidelityPrompt(spec: ProtocolSpec, code: string): string {
  const p = spec.preprocess;
  const s = spec.split;
  const specLines = [
    `Dataset: ${spec.dataset.name}`,
    `Perturbation type: ${spec.perturbation_type}`,
    `Split strategy: ${s.type}${s.note ? ` (${s.note})` : ""}`,
    `Normalization: ${p.normalization}`,
    p.n_hvg !== undefined ? `n_hvg (highly variable genes): ${p.n_hvg}` : null,
    p.min_genes !== undefined ? `min_genes filter: ${p.min_genes}` : null,
    p.note ? `Additional preprocessing note: ${p.note}` : null,
  ].filter(Boolean).join("\n");

  return `You are evaluating whether Python code correctly implements the protocol from a computational biology paper.

Paper protocol specification:
${specLines}

Python code executed in this experiment:
${code || "(no Python code blocks found in conversation)"}

Check whether the code matches the protocol. Focus on:
1. Normalization: does the code use "${p.normalization}"? (look for sc.pp.normalize_total + sc.pp.log1p or equivalent)
2. n_hvg: does sc.pp.highly_variable_genes use n_top_genes=${p.n_hvg ?? "unspecified"}?
3. Split: does the code implement "${s.type}"?
4. Any other preprocessing deviation from the specification

Score 1.0 = code exactly matches protocol
Score 0.7 = one minor deviation (e.g. n_hvg off by ≤20%)
Score 0.5 = one significant deviation (e.g. wrong normalization or n_hvg off by >20%)
Score 0.0 = multiple major deviations or fundamentally wrong protocol

If no code blocks were provided, score 0.5 and note the absence.

Return JSON only: {"score": <0.0-1.0>, "issues": ["<description>"]}`;
}

export async function computeProtocolFidelity(
  spec: ProtocolSpec,
  convMsgs: ConvMsg[],
): Promise<{ score: number; issues: string[] }> {
  const code = extractCodeBlocks(convMsgs);
  if (!code) {
    return { score: 0.5, issues: ["No Python code blocks found in conversation — cannot verify protocol"] };
  }
  const prompt = buildProtocolFidelityPrompt(spec, code);
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
  const details: RFSResult["details"] = {
    result_per_metric: {},
    metric_issues: [],
    protocol_issues: [],
    biology_issues: [],
  };

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

  // --- Protocol Fidelity ---
  let protocolScore = -1;
  if (spec && options.convMsgs && !options.skipProtocolFidelity) {
    try {
      const pf = await computeProtocolFidelity(spec, options.convMsgs);
      protocolScore = pf.score;
      details.protocol_issues = pf.issues;
      for (const issue of pf.issues) {
        warnings.push(`WARNING [Protocol]: ${issue}`);
      }
    } catch (err) {
      warnings.push(`INFO [Protocol]: LLM judge failed — ${(err as Error).message}`);
    }
  } else if (!spec) {
    warnings.push("INFO [Protocol]: No ProtocolSpec — run /paper-audit first.");
  } else if (!options.convMsgs) {
    warnings.push("INFO [Protocol]: No conversation messages provided — Protocol Fidelity skipped.");
  }

  // --- Biology Validity ---
  let biologyScore = -1;
  if (options.convMsgs && !options.skipBiologyValidity) {
    try {
      const bv = await computeBiologyValidity(ourMetrics, options.convMsgs, spec ?? undefined);
      biologyScore = bv.score;
      details.biology_issues = bv.issues;
      for (const issue of bv.issues) {
        const level = issue.startsWith("Top GO") || issue.startsWith("Too few") ? "INFO" : "WARNING";
        warnings.push(`${level} [Biology]: ${issue}`);
      }
    } catch (err) {
      warnings.push(`INFO [Biology]: Computation failed — ${(err as Error).message}`);
    }
  } else if (!options.convMsgs) {
    warnings.push("INFO [Biology]: No conversation messages — Biology Validity skipped.");
  }

  // --- Overall: average of computed dimensions only ---
  const computed = [resultScore, metricScore, protocolScore, biologyScore].filter((s) => s >= 0);
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
