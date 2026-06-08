/**
 * F3 — Skill Refinement Loop
 *
 * Inspired by:
 *   SkillEvolver (2605.10500): contrastive trajectory comparison + independent auditor
 *   EmbodíSkill  (2605.10332): 4-type skill-aware reflection before updating
 *
 * Flow:
 *   1. classifyReflection()  → one of 4 types
 *   2a. EXECUTION_LAPSE      → append emphasis note only (never touch skill rules)
 *   2b. others               → generatePatch() → auditPatch() → save if passed
 */

import { callText } from "./vision.js";
import { loadSkill, saveSkill, type SkillRecord, type SkillPatch } from "./skills.js";
import type { FailureRecord } from "./failure.js";
import type { ConvMsg } from "./db.js";
import type { ProtocolSpec } from "./protocol.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ReflectionType = "discovery" | "optimization" | "skill_defect" | "execution_lapse";

interface ReflectionResult {
  type: ReflectionType;
  evidence: string;   // what in the skill/failure supports this classification
  suggestion: string; // what should change (for patch generation)
}

interface PatchProposal {
  conda_env?: string;
  n_hvg?: number;
  split_type?: string;
  normalization?: string;
  key_deps?: string[];
  extra_params?: Record<string, unknown>;
  appendix_addition?: string;  // EXECUTION_LAPSE only
  rationale: string;
}

// ---------------------------------------------------------------------------
// Skill → human-readable text (for LLM prompts)
// ---------------------------------------------------------------------------

function skillToText(skill: SkillRecord): string {
  const lines = [
    `Gene: ${skill.gene}  |  Model: ${skill.model}  |  Dataset: ${skill.dataset}`,
    `Gene class: ${skill.gene_class}`,
    `conda_env: ${skill.conda_env ?? "unknown"}`,
    `n_hvg: ${skill.n_hvg ?? "unspecified"}`,
    `split_type: ${skill.split_type ?? "unspecified"}`,
    `normalization: ${skill.normalization ?? "unspecified"}`,
    `key_deps: ${skill.key_deps?.join(", ") ?? "none recorded"}`,
    `success_rate: ${(skill.success_rate * 100).toFixed(0)}% (${skill.run_count} runs)`,
  ];
  if (skill.pathway) lines.push(`pathway: ${skill.pathway}`);
  if (skill.extra_params) lines.push(`extra_params: ${JSON.stringify(skill.extra_params)}`);
  if (skill.appendix) lines.push(`\nAppendix (execution emphasis):\n${skill.appendix}`);
  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// Step 1 — Classify reflection type (EmbodíSkill 4-type taxonomy)
// ---------------------------------------------------------------------------

async function classifyReflection(
  skill: SkillRecord,
  failure: FailureRecord,
  convMsgs: ConvMsg[],
): Promise<ReflectionResult> {
  const lastCode = convMsgs
    .filter(m => m.role === "assistant")
    .slice(-3)
    .map(m => m.content)
    .join("\n")
    .slice(0, 3000);

  const prompt = `You are analysing a failed bioinformatics experiment to improve a reusable SKILL.

## Current SKILL
${skillToText(skill)}

## Failure
Type: ${failure.type}
Message: ${failure.message}
Evidence: ${failure.evidence.slice(0, 3).join(" | ")}
${failure.suggested_fix ? `Suggested fix: ${failure.suggested_fix}` : ""}

## Last code blocks from the run
${lastCode || "(none found)"}

## Task
Classify this failure into exactly one of 4 reflection types:

DISCOVERY      – The SKILL is missing a step or piece of information that would have
                 prevented this failure (e.g. a missing dependency, an unrecorded split seed).

OPTIMIZATION   – The SKILL is technically correct but could be written more clearly or
                 efficiently to prevent this kind of misinterpretation.

SKILL_DEFECT   – The SKILL contains incorrect or misleading information that directly
                 caused this failure (e.g. wrong n_hvg, wrong split type recorded).

EXECUTION_LAPSE – The SKILL is correct and complete; the agent simply failed to follow
                  it (e.g. used a different conda env despite the SKILL specifying one).
                  Do NOT update skill rules in this case.

Return JSON only:
{"type":"discovery|optimization|skill_defect|execution_lapse","evidence":"<one sentence>","suggestion":"<what should change>"}`;

  const raw = await callText(prompt);
  const cleaned = raw.content.replace(/```(?:json)?\n?/g, "").trim();
  try {
    const parsed = JSON.parse(cleaned) as Partial<ReflectionResult>;
    const validTypes: ReflectionType[] = ["discovery", "optimization", "skill_defect", "execution_lapse"];
    const type = validTypes.includes(parsed.type as ReflectionType)
      ? parsed.type as ReflectionType
      : "execution_lapse"; // safe fallback: don't modify skill
    return {
      type,
      evidence: parsed.evidence ?? "",
      suggestion: parsed.suggestion ?? "",
    };
  } catch {
    return { type: "execution_lapse", evidence: "parse failed", suggestion: "" };
  }
}

// ---------------------------------------------------------------------------
// Step 2 — Generate patch (SkillEvolver-style contrastive update)
// ---------------------------------------------------------------------------

async function generatePatch(
  skill: SkillRecord,
  reflection: ReflectionResult,
  spec?: ProtocolSpec,
): Promise<PatchProposal | null> {
  const specSection = spec
    ? `\n## ProtocolSpec (ground truth)\n` +
      `n_hvg: ${spec.preprocess.n_hvg ?? "unspecified"}\n` +
      `split_type: ${spec.split.type}\n` +
      `normalization: ${spec.preprocess.normalization}\n`
    : "";

  const prompt = `You are generating a targeted patch for a bioinformatics SKILL.

## Current SKILL
${skillToText(skill)}
${specSection}
## Reflection
Type: ${reflection.type}
Evidence: ${reflection.evidence}
Suggestion: ${reflection.suggestion}

Generate a minimal patch — only change what is implicated by the reflection.
For EXECUTION_LAPSE: only produce appendix_addition (an emphasis note), set all other fields to null.
For others: update only the fields that are wrong or missing.

Return JSON only (null means "do not change"):
{
  "conda_env": <string or null>,
  "n_hvg": <number or null>,
  "split_type": <string or null>,
  "normalization": <string or null>,
  "key_deps": <string[] or null>,
  "extra_params": <object or null>,
  "appendix_addition": <string or null>,
  "rationale": "<one sentence>"
}`;

  const raw = await callText(prompt);
  const cleaned = raw.content.replace(/```(?:json)?\n?/g, "").trim();
  try {
    return JSON.parse(cleaned) as PatchProposal;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Step 3 — Independent auditor (SkillEvolver mechanical checks)
// ---------------------------------------------------------------------------

async function auditPatch(
  original: SkillRecord,
  patched: SkillRecord,
  spec?: ProtocolSpec,
): Promise<{ pass: boolean; issues: string[] }> {
  const specSection = spec
    ? `ProtocolSpec ground truth — n_hvg: ${spec.preprocess.n_hvg ?? "?"}, ` +
      `split: ${spec.split.type}, normalization: ${spec.preprocess.normalization}`
    : "No ProtocolSpec available.";

  const prompt = `You are an independent auditor checking a SKILL patch for correctness.

## Original SKILL
${skillToText(original)}

## Patched SKILL
${skillToText(patched)}

## ${specSection}

Check for ALL of these 6 issues:
1. n_hvg mismatch with ProtocolSpec (if spec available)
2. split_type mismatch with ProtocolSpec
3. normalization mismatch with ProtocolSpec
4. Silent bypass: does the patch tell the agent to skip a required step?
5. Contradiction: does the patched skill contain conflicting instructions?
6. Hallucination: does the patch introduce specific values not supported by evidence?

A patch PASSES only if it has zero issues.

Return JSON only:
{"pass": true|false, "issues": ["<issue description>", ...]}`;

  const raw = await callText(prompt);
  const cleaned = raw.content.replace(/```(?:json)?\n?/g, "").trim();
  try {
    const parsed = JSON.parse(cleaned) as { pass?: boolean; issues?: unknown[] };
    const issues = Array.isArray(parsed.issues)
      ? parsed.issues.filter((i): i is string => typeof i === "string")
      : [];
    return { pass: parsed.pass === true && issues.length === 0, issues };
  } catch {
    return { pass: false, issues: ["Auditor response could not be parsed"] };
  }
}

// ---------------------------------------------------------------------------
// Apply patch to skill (pure function — does not save)
// ---------------------------------------------------------------------------

function applyPatch(skill: SkillRecord, patch: PatchProposal): SkillRecord {
  const today = new Date().toISOString().split("T")[0]!;
  return {
    ...skill,
    ...(patch.conda_env   != null ? { conda_env:   patch.conda_env }   : {}),
    ...(patch.n_hvg       != null ? { n_hvg:       patch.n_hvg }       : {}),
    ...(patch.split_type  != null ? { split_type:  patch.split_type }  : {}),
    ...(patch.normalization != null ? { normalization: patch.normalization } : {}),
    ...(patch.key_deps    != null ? { key_deps:    patch.key_deps }    : {}),
    ...(patch.extra_params != null ? { extra_params: patch.extra_params } : {}),
    updated_at: today,
  };
}

// ---------------------------------------------------------------------------
// Main entry point
// ---------------------------------------------------------------------------

export async function refineSkill(
  slug: string,
  failure: FailureRecord,
  convMsgs: ConvMsg[],
  spec?: ProtocolSpec,
): Promise<{ updated: boolean; type: ReflectionType; issues?: string[] }> {
  const skill = loadSkill(slug);
  if (!skill || skill.status === "deprecated") {
    return { updated: false, type: "execution_lapse" };
  }

  // Step 1: classify
  const reflection = await classifyReflection(skill, failure, convMsgs);
  const today = new Date().toISOString().split("T")[0]!;

  // Step 2a: EXECUTION_LAPSE — only update appendix, no rule changes
  if (reflection.type === "execution_lapse") {
    const patch = await generatePatch(skill, reflection, spec);
    const note = patch?.appendix_addition;
    if (note) {
      const patchRecord: SkillPatch = {
        date: today,
        type: "execution_lapse",
        evidence: reflection.evidence,
        rationale: `Appendix note added: ${note.slice(0, 80)}`,
        auditor_passed: true,  // no auditor needed for appendix-only change
      };
      const updated: SkillRecord = {
        ...skill,
        appendix: skill.appendix ? `${skill.appendix}\n- ${note}` : `- ${note}`,
        patch_history: [...(skill.patch_history ?? []), patchRecord],
        updated_at: today,
      };
      saveSkill(updated);
      return { updated: true, type: "execution_lapse" };
    }
    return { updated: false, type: "execution_lapse" };
  }

  // Step 2b: DISCOVERY / OPTIMIZATION / SKILL_DEFECT — patch + audit
  const patch = await generatePatch(skill, reflection, spec);
  if (!patch) return { updated: false, type: reflection.type };

  const patched = applyPatch(skill, patch);
  const audit = await auditPatch(skill, patched, spec);

  const patchRecord: SkillPatch = {
    date: today,
    type: reflection.type,
    evidence: reflection.evidence,
    rationale: patch.rationale,
    auditor_passed: audit.pass,
  };

  if (audit.pass) {
    saveSkill({
      ...patched,
      patch_history: [...(skill.patch_history ?? []), patchRecord],
    });
    return { updated: true, type: reflection.type };
  } else {
    // Auditor failed: record the attempt but don't apply the patch
    saveSkill({
      ...skill,
      patch_history: [...(skill.patch_history ?? []), patchRecord],
      updated_at: today,
    });
    return { updated: false, type: reflection.type, issues: audit.issues };
  }
}
