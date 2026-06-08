import { existsSync, readFileSync, writeFileSync, readdirSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { getWaddingtonHome } from "../config/paths.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

// Patch record written by F3 skill-refine loop
export interface SkillPatch {
  date: string;
  type: "discovery" | "optimization" | "skill_defect" | "execution_lapse";
  evidence: string;   // what in the failure+skill supports this classification
  rationale: string;  // what changed and why
  auditor_passed: boolean;
}

export type GeneClass =
  | "transcription_factor"
  | "kinase"
  | "epigenetic"
  | "metabolic"
  | "signaling"
  | "unknown";

export interface SkillRecord {
  // Identity
  slug: string;               // "{GENE}_{model}_{dataset}", kebab-case
  gene: string;               // e.g. "CEBPE"
  model: string;              // e.g. "GEARS"
  dataset: string;            // e.g. "norman2019"

  // Environment
  conda_env: string | null;   // conda env name that worked
  python_version?: string;
  key_deps?: string[];        // e.g. ["torch==2.1.0", "scanpy==1.9.6"]

  // Protocol
  n_hvg?: number;
  split_type?: string;        // e.g. "combination_holdout"
  normalization?: string;     // e.g. "log1p"
  extra_params?: Record<string, unknown>;

  // Biology context
  gene_class: GeneClass;
  pathway?: string;           // e.g. "granulopoiesis"

  // Performance
  best_pearson_de?: number;
  best_rfs?: number;
  success_rate: number;       // fraction of runs that produced valid metrics
  run_count: number;

  // Lifecycle
  status: "active" | "deprecated";
  created_at: string;         // ISO date
  updated_at: string;

  // F3 refinement (added by skill-refine loop)
  appendix?: string;          // execution-lapse notes: emphasis text, never changes rules
  patch_history?: SkillPatch[];  // ordered log of all audited patches
}

// ---------------------------------------------------------------------------
// File paths
// ---------------------------------------------------------------------------

function skillsDir(): string {
  return resolve(getWaddingtonHome(), "..", "workspace", "skills");
}

function skillPath(slug: string): string {
  return resolve(skillsDir(), `${slug}.skill.json`);
}

function makeSlug(gene: string, model: string, dataset: string): string {
  return [gene, model, dataset]
    .map(s => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""))
    .join("_");
}

// ---------------------------------------------------------------------------
// I/O
// ---------------------------------------------------------------------------

export function loadSkill(slug: string): SkillRecord | null {
  const p = skillPath(slug);
  if (!existsSync(p)) return null;
  try {
    return JSON.parse(readFileSync(p, "utf8")) as SkillRecord;
  } catch {
    return null;
  }
}

export function saveSkill(skill: SkillRecord): void {
  mkdirSync(skillsDir(), { recursive: true });
  writeFileSync(skillPath(skill.slug), JSON.stringify(skill, null, 2));
}

export function listSkills(filter?: { status?: "active" | "deprecated" }): SkillRecord[] {
  const dir = skillsDir();
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter(f => f.endsWith(".skill.json"))
    .map(f => {
      try { return JSON.parse(readFileSync(resolve(dir, f), "utf8")) as SkillRecord; }
      catch { return null; }
    })
    .filter((s): s is SkillRecord => s !== null)
    .filter(s => !filter?.status || s.status === filter.status);
}

// ---------------------------------------------------------------------------
// Gene class inference (heuristic, no network)
// ---------------------------------------------------------------------------

const TF_SUFFIXES = /^(CEBP|GATA|MYC|SP[0-9]|KLF|ETS|IRF|STAT|RUNX|NFkB|REL|FOS|JUN|PAX|SOX)/i;
const KINASE_PATTERN = /K(?:INASE)?$|^[A-Z]+K$|MAP[0-9]?K|CDK[0-9]|PLK[0-9]|AKT|PIK3/i;
const EPIGENETIC_PATTERN = /^(DNMT|TET|EZH|SUZ|BMI|KDM|KMT|HDAC|HAT|BRD|SMARCA)/i;

export function inferGeneClass(gene: string): GeneClass {
  if (TF_SUFFIXES.test(gene)) return "transcription_factor";
  if (KINASE_PATTERN.test(gene)) return "kinase";
  if (EPIGENETIC_PATTERN.test(gene)) return "epigenetic";
  return "unknown";
}

// ---------------------------------------------------------------------------
// Crystallise a SKILL from a successful experiment
// ---------------------------------------------------------------------------

export interface CrystalliseOptions {
  condaEnv?: string;
  pythonVersion?: string;
  keyDeps?: string[];
  nHvg?: number;
  splitType?: string;
  normalization?: string;
  extraParams?: Record<string, unknown>;
  pathway?: string;
}

export function crystalliseSkill(
  gene: string,
  model: string,
  dataset: string,
  metrics: Record<string, number>,
  rfsOverall: number | undefined,
  opts: CrystalliseOptions = {},
): SkillRecord {
  const slug = makeSlug(gene, model, dataset);
  const today = new Date().toISOString().split("T")[0]!;
  const existing = loadSkill(slug);

  // Determine if this run was "successful" (has at least one metric)
  const hasMetrics = Object.keys(metrics).length > 0;

  if (existing) {
    // Update existing skill: recalculate success_rate, update best scores
    const newRunCount = existing.run_count + 1;
    const prevSuccesses = Math.round(existing.success_rate * existing.run_count);
    const newSuccesses = prevSuccesses + (hasMetrics ? 1 : 0);

    const pde = metrics["pearson_de"] ?? metrics["pearson"];
    const updated: SkillRecord = {
      ...existing,
      run_count: newRunCount,
      success_rate: newSuccesses / newRunCount,
      best_pearson_de: pde !== undefined
        ? Math.max(existing.best_pearson_de ?? 0, pde)
        : existing.best_pearson_de,
      best_rfs: rfsOverall !== undefined
        ? Math.max(existing.best_rfs ?? 0, rfsOverall)
        : existing.best_rfs,
      // Auto-deprecate if success rate falls below 50% after ≥4 runs
      status: (newRunCount >= 4 && newSuccesses / newRunCount < 0.5) ? "deprecated" : "active",
      updated_at: today,
    };
    // Update env info if provided and currently unknown
    if (opts.condaEnv && !updated.conda_env) updated.conda_env = opts.condaEnv;
    if (opts.nHvg && !updated.n_hvg) updated.n_hvg = opts.nHvg;
    if (opts.pathway && !updated.pathway) updated.pathway = opts.pathway;

    saveSkill(updated);
    return updated;
  }

  // Create new skill
  const pde = metrics["pearson_de"] ?? metrics["pearson"];
  const skill: SkillRecord = {
    slug,
    gene: gene.toUpperCase(),
    model: model.toUpperCase(),
    dataset,
    conda_env: opts.condaEnv ?? null,
    python_version: opts.pythonVersion,
    key_deps: opts.keyDeps,
    n_hvg: opts.nHvg,
    split_type: opts.splitType,
    normalization: opts.normalization ?? "log1p",
    extra_params: opts.extraParams,
    gene_class: inferGeneClass(gene),
    pathway: opts.pathway,
    best_pearson_de: pde,
    best_rfs: rfsOverall,
    success_rate: hasMetrics ? 1 : 0,
    run_count: 1,
    status: "active",
    created_at: today,
    updated_at: today,
  };
  saveSkill(skill);
  return skill;
}

// ---------------------------------------------------------------------------
// Retrieve best matching skill for a new experiment
// ---------------------------------------------------------------------------

export function findMatchingSkill(
  gene: string,
  model?: string,
  dataset?: string,
): SkillRecord | null {
  const active = listSkills({ status: "active" });

  // Exact match first
  const exact = active.find(
    s => s.gene === gene.toUpperCase() &&
         (!model || s.model === model.toUpperCase()) &&
         (!dataset || s.dataset === dataset),
  );
  if (exact) return exact;

  // Same gene, same gene_class, any model
  const geneClass = inferGeneClass(gene);
  if (geneClass !== "unknown") {
    const byClass = active
      .filter(s => s.gene_class === geneClass && s.success_rate >= 0.7)
      .sort((a, b) => (b.best_pearson_de ?? 0) - (a.best_pearson_de ?? 0));
    if (byClass[0]) return byClass[0];
  }

  return null;
}

// ---------------------------------------------------------------------------
// Format skill as context hint for Pi
// ---------------------------------------------------------------------------

export function formatSkillContext(skill: SkillRecord): string {
  const lines = [
    `Prior SKILL: ${skill.gene} (${skill.model} on ${skill.dataset})`,
    `  Success rate: ${(skill.success_rate * 100).toFixed(0)}% over ${skill.run_count} runs`,
  ];
  if (skill.best_pearson_de !== undefined)
    lines.push(`  Best pearson_de: ${skill.best_pearson_de.toFixed(3)}`);
  if (skill.conda_env)
    lines.push(`  Conda env: ${skill.conda_env}`);
  if (skill.n_hvg)
    lines.push(`  n_hvg: ${skill.n_hvg}`);
  if (skill.split_type)
    lines.push(`  Split: ${skill.split_type}`);
  return lines.join("\n");
}
