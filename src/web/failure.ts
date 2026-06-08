import type { ConvMsg } from "./db.js";

// ---------------------------------------------------------------------------
// Failure taxonomy (补充4)
// 5 structured types that Waddington can learn from and recover
// ---------------------------------------------------------------------------

export type FailureType =
  | "environment_failure"    // CUDA / torch / scanpy version conflict
  | "data_access_failure"    // GEO / Zenodo link broken or data format mismatch
  | "protocol_ambiguity"     // Paper didn't specify split seed / HVG count etc.
  | "metric_mismatch"        // Our metric definition differs from paper (top-k, de_ref)
  | "biology_suspicious"     // DE genes don't match known pathway priors
  | "unknown";

export interface FailureRecord {
  type: FailureType;
  message: string;           // human-readable description
  evidence: string[];        // text snippets that triggered this classification
  suggested_fix?: string;    // remediation hint
}

// ---------------------------------------------------------------------------
// Pattern-based classifier (fast, no LLM)
// ---------------------------------------------------------------------------

const PATTERNS: Array<{
  type: FailureType;
  regexes: RegExp[];
  fix: string;
}> = [
  {
    type: "environment_failure",
    regexes: [
      /ModuleNotFoundError|ImportError|No module named/i,
      /CUDA out of memory|RuntimeError.*CUDA/i,
      /incompatible.*version|version.*conflict|requires.*torch/i,
      /conda.*error|pip.*error|environment.*failed/i,
    ],
    fix: "Check conda environment; try pinning torch/scanpy versions from the model's README.",
  },
  {
    type: "data_access_failure",
    regexes: [
      /FileNotFoundError|No such file|cannot open|404.*GEO|HTTPError/i,
      /GEO accession|GSE[0-9]+.*not found|download.*failed/i,
      /h5ad.*not found|anndata.*load.*error/i,
    ],
    fix: "Verify GEO/Zenodo accession; check if data requires access approval or format conversion.",
  },
  {
    type: "metric_mismatch",
    regexes: [
      /top[_\s-]?(?:20|50|100)\s+DE|top_k.*mismatch|k=\d+.*paper.*k=\d+/i,
      /metric.*different|wrong.*metric|pearson_de.*vs.*pearson\b/i,
      /RFS.*[Mm]etric.*0\.[0-3]/,  // low metric fidelity score
    ],
    fix: "Align top_k and de_reference settings with ProtocolSpec; rerun with correct metric definition.",
  },
  {
    type: "protocol_ambiguity",
    regexes: [
      /split.*not.*specified|seed.*unknown|combination.*holdout.*unclear/i,
      /preprocessing.*ambiguous|hvg.*not.*mentioned|n_hvg.*unclear/i,
      /paper.*does not.*specify|method.*section.*unclear/i,
    ],
    fix: "Run /paper-audit to extract ProtocolSpec; generate multiple plausible splits and report sensitivity.",
  },
  {
    type: "biology_suspicious",
    regexes: [
      /biology.*score.*0\.[0-2]|suspicious.*biology|RFS.*[Bb]iology.*low/i,
      /no.*significant.*GO|STRING.*PPI.*p.*[0-9]e-[01]\b/i,  // very high p-value
      /DE genes.*not.*pathway|unexpected.*DE|artifact/i,
    ],
    fix: "Inspect top DE genes; check for batch effects or data leakage; validate against known perturbation atlases.",
  },
];

function extractTextWindow(msgs: ConvMsg[]): string {
  // Focus on the last 4 assistant messages where errors typically appear
  return msgs
    .filter(m => m.role === "assistant")
    .slice(-4)
    .map(m => m.content)
    .join("\n")
    .slice(0, 6000);
}

export function classifyFailure(msgs: ConvMsg[], rfsJson?: string): FailureRecord | null {
  const text = extractTextWindow(msgs);
  const combined = rfsJson ? text + "\n" + rfsJson : text;

  for (const { type, regexes, fix } of PATTERNS) {
    const evidence: string[] = [];
    for (const rx of regexes) {
      const m = combined.match(rx);
      if (m) evidence.push(m[0].slice(0, 120));
    }
    if (evidence.length > 0) {
      return {
        type,
        message: failureMessage(type),
        evidence,
        suggested_fix: fix,
      };
    }
  }

  return null;  // no failure detected — experiment looks successful
}

function failureMessage(type: FailureType): string {
  switch (type) {
    case "environment_failure":   return "Dependency or runtime environment error detected";
    case "data_access_failure":   return "Dataset could not be loaded or accessed";
    case "metric_mismatch":       return "Metric definition differs from paper specification";
    case "protocol_ambiguity":    return "Paper protocol is underspecified — using assumptions";
    case "biology_suspicious":    return "DE gene profile does not match expected biology";
    default:                      return "Unknown failure";
  }
}

// ---------------------------------------------------------------------------
// Failure history search — find past fixes for same failure type
// ---------------------------------------------------------------------------

export function formatFailureContext(failure: FailureRecord): string {
  const lines = [
    `Failure type: ${failure.type}`,
    `Message: ${failure.message}`,
    `Evidence: ${failure.evidence.slice(0, 2).join(" | ")}`,
  ];
  if (failure.suggested_fix) lines.push(`Suggested fix: ${failure.suggested_fix}`);
  return lines.join("\n");
}
