import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { basename, extname, resolve } from "node:path";
import { promisify } from "node:util";
import { callText, callVision, renderPdfPages } from "./vision.js";
import { saveProtocolSpec, isProtocolSpec, type ProtocolSpec } from "./protocol.js";
import { getWaddingtonHome } from "../config/paths.js";

const execFileAsync = promisify(execFile);

// ---------------------------------------------------------------------------
// PDF text extraction via pymupdf subprocess
// ---------------------------------------------------------------------------

const PDF_RENDER_SCRIPT = resolve(
  getWaddingtonHome(), "..", "workspace", "evaluation", "pdf_render.py"
);

interface TextPage { page_num: number; text: string; }

async function extractPdfText(pdfPath: string, maxPages = 40): Promise<TextPage[]> {
  const { stdout } = await execFileAsync("python3", [
    PDF_RENDER_SCRIPT, "--text", pdfPath, String(maxPages),
  ]);
  const result = JSON.parse(stdout);
  if (result.error) throw new Error(`pdf text: ${result.error}`);
  return result as TextPage[];
}

// ---------------------------------------------------------------------------
// Heuristics: find pages likely containing tables (for vision extraction)
// ---------------------------------------------------------------------------

function findLikelyTablePages(pages: TextPage[]): number[] {
  return pages
    .filter(p => /table\s+\d|pearson|mse|r2\s*=|\|\s*model\s*\|/i.test(p.text))
    .map(p => p.page_num)
    .slice(0, 5); // cap at 5 pages to limit API cost
}

// ---------------------------------------------------------------------------
// ProtocolSpec extraction prompt
// ---------------------------------------------------------------------------

const PROTOCOL_SCHEMA = `{
  paper_slug: string,             // kebab-case identifier, e.g. "gears-2024"
  paper_title: string,
  arxiv_id?: string,              // e.g. "2211.02023"
  year?: number,
  github_url?: string,
  dataset: {
    name: string,                 // e.g. "Norman2019"
    geo_accession?: string,       // e.g. "GSE133344"
    cell_line?: string,           // e.g. "K562"
    organism?: string,
    perturbation_count?: number
  },
  perturbation_type: string,      // "CRISPRi" | "CRISPRa" | "knockout" | "overexpression"
  split: {
    type: string,                 // "combination_holdout" | "single_holdout" | "random"
    unseen_single?: boolean,
    test_fraction?: number,
    seed?: number,
    note?: string
  },
  preprocess: {
    normalization: string,        // "log1p" | "scran" | "none"
    n_hvg?: number,               // number of highly variable genes
    min_genes?: number,
    note?: string
  },
  metrics: Array<{
    name: string,                 // "pearson_de" | "pearson" | "mse_de" | "r2" | "mse"
    top_k?: number,               // for DEG-based metrics (e.g. top-20 DEGs)
    de_reference?: string,        // "observed_vs_control" | "paper_provided"
    primary?: boolean,
    note?: string
  }>,
  reported_values?: Record<string, number>,  // e.g. {"pearson_de": 0.74}
  notes?: string
}`;

const TABLE_EXTRACT_PROMPT =
  `Extract all tables on this page as CSV. For each table, start with a comment line "# Table N: <description>".
Output only CSV and comment lines. If no tables, output: NO_TABLES`;

function buildAuditPrompt(slug: string, text: string, tablesCsv: string): string {
  const tablesSection = tablesCsv.trim()
    ? `\n\nExtracted tables from results pages:\n${tablesCsv}`
    : "";

  return `You are extracting a ProtocolSpec from a computational biology paper about gene perturbation prediction.

Paper slug (identifier): ${slug}

Paper text (methods + results):
${text}
${tablesSection}

Extract a ProtocolSpec matching this schema:
${PROTOCOL_SCHEMA}

Guidelines:
- paper_slug must be "${slug}"
- For reported_values, extract numerical results for the primary metric (e.g. pearson_de on the main benchmark dataset). Use the exact value from the paper table.
- If a field is unknown, omit it (do not guess).
- For split.type: "combination_holdout" means unseen combinations of single perturbations; "single_holdout" means unseen individual perturbations.
- annotated_by must be "llm"
- annotated_at must be "${new Date().toISOString().split("T")[0]}"

Return only valid JSON, no markdown fences, no explanation.`;
}

// ---------------------------------------------------------------------------
// Main audit function
// ---------------------------------------------------------------------------

export interface AuditOptions {
  dpi?: number;
  maxTextPages?: number;
  skipTableExtraction?: boolean;
  saveToWorkspace?: boolean;
}

export async function auditPaper(
  pdfPath: string,
  slug: string,
  options: AuditOptions = {},
): Promise<ProtocolSpec> {
  const {
    maxTextPages = 40,
    skipTableExtraction = false,
    saveToWorkspace = true,
  } = options;

  if (!existsSync(pdfPath)) {
    throw new Error(`PDF not found: ${pdfPath}`);
  }

  // 1. Extract text
  const textPages = await extractPdfText(pdfPath, maxTextPages);

  // Use a focused window: first 6000 chars (abstract+intro+methods) + last 3000 (results+conclusion)
  const allText = textPages.map(p => p.text).join("\n");
  const focusedText = allText.length > 12000
    ? allText.slice(0, 8000) + "\n\n[...]\n\n" + allText.slice(-4000)
    : allText;

  // 2. Optionally extract tables from visually rendered pages
  let tablesCsv = "";
  if (!skipTableExtraction) {
    try {
      const tablePageNums = findLikelyTablePages(textPages);
      if (tablePageNums.length > 0) {
        const allPages = await renderPdfPages(pdfPath, { dpi: 120, maxPages: Math.max(...tablePageNums) });
        const targetPages = allPages.filter(p => tablePageNums.includes(p.page_num));
        const csvParts: string[] = [];
        for (const page of targetPages) {
          const r = await callVision(TABLE_EXTRACT_PROMPT, page.b64_png);
          if (r.content.trim() !== "NO_TABLES" && r.content.trim()) {
            csvParts.push(`=== Page ${page.page_num} ===\n${r.content}`);
          }
        }
        tablesCsv = csvParts.join("\n\n");
      }
    } catch {
      // Table extraction is optional — continue without it
    }
  }

  // 3. Extract ProtocolSpec via LLM
  const prompt = buildAuditPrompt(slug, focusedText, tablesCsv);
  const llmResult = await callText(prompt);

  // 4. Parse and validate
  let raw: string = llmResult.content.trim();
  // Strip markdown code fences if present
  raw = raw.replace(/^```(?:json)?\n?/, "").replace(/\n?```$/, "").trim();

  let spec: unknown;
  try {
    spec = JSON.parse(raw);
  } catch (e) {
    throw new Error(`LLM returned invalid JSON: ${(e as Error).message}\n---\n${raw.slice(0, 500)}`);
  }

  if (!isProtocolSpec(spec)) {
    throw new Error(`Extracted JSON missing required fields. Got: ${JSON.stringify(spec).slice(0, 300)}`);
  }

  // Force annotated_by = "llm" (the LLM might override this)
  spec.annotated_by = "llm";

  // 5. Save
  if (saveToWorkspace) {
    saveProtocolSpec(spec);
  }

  return spec;
}

// ---------------------------------------------------------------------------
// Derive a slug from a PDF filename
// ---------------------------------------------------------------------------

export function slugFromFilename(filename: string): string {
  return basename(filename, extname(filename))
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 60)
    || "paper";
}
