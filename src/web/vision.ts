import { execFile } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { promisify } from "node:util";
import { getWaddingtonHome } from "../config/paths.js";

const execFileAsync = promisify(execFile);

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface RenderedPage {
  page_num: number;
  width: number;
  height: number;
  b64_png: string;
}

export interface VisionResult {
  provider: string;
  model: string;
  content: string;
}

// ---------------------------------------------------------------------------
// Provider routing
// ---------------------------------------------------------------------------

// Providers that support image inputs
const VISION_PROVIDERS = new Set([
  "anthropic",
  "openai",
  "openai-codex",
  "google",
  "google-gemini-cli",
  "kimi-coding",
]);

// OpenAI-compatible providers with custom base URLs
const OPENAI_COMPAT_BASE: Record<string, string | undefined> = {
  "kimi-coding": "https://api.moonshot.cn/v1",
};

function readCurrentModel(): { provider: string; model: string } {
  // Check project-level settings first, then user-level
  const candidates = [
    resolve(getWaddingtonHome(), "settings.json"),
    resolve(process.env.HOME ?? "~", ".waddington", "agent", "settings.json"),
  ];
  for (const p of candidates) {
    if (!existsSync(p)) continue;
    try {
      const s = JSON.parse(readFileSync(p, "utf8"));
      if (s.defaultProvider && s.defaultModel) {
        return { provider: s.defaultProvider, model: s.defaultModel };
      }
    } catch { /* skip */ }
  }
  // Fallback to Claude Sonnet
  return { provider: "anthropic", model: "claude-sonnet-4-6" };
}

export function supportsVision(provider: string): boolean {
  return VISION_PROVIDERS.has(provider);
}

// ---------------------------------------------------------------------------
// Vision call — routes to the right SDK
// ---------------------------------------------------------------------------

export async function callVision(
  prompt: string,
  imageBase64: string,
  override?: { provider?: string; model?: string },
): Promise<VisionResult> {
  const current = readCurrentModel();
  const provider = override?.provider ?? current.provider;
  const model = override?.model ?? current.model;

  if (!supportsVision(provider)) {
    throw new Error(
      `Provider "${provider}" does not support vision inputs. ` +
      `Switch to anthropic, openai, google, or kimi-coding.`
    );
  }

  if (provider === "anthropic") {
    return callAnthropic(prompt, imageBase64, model);
  }
  if (provider === "openai" || provider === "openai-codex") {
    return callOpenAI(prompt, imageBase64, model, OPENAI_COMPAT_BASE[provider]);
  }
  if (provider === "google" || provider === "google-gemini-cli") {
    return callGoogle(prompt, imageBase64, model);
  }
  if (provider === "kimi-coding") {
    return callOpenAI(prompt, imageBase64, model, OPENAI_COMPAT_BASE["kimi-coding"]);
  }
  throw new Error(`Unhandled vision provider: ${provider}`);
}

// ---------------------------------------------------------------------------
// Anthropic
// ---------------------------------------------------------------------------

async function callAnthropic(
  prompt: string,
  imageBase64: string,
  model: string,
): Promise<VisionResult> {
  const { default: Anthropic } = await import("@anthropic-ai/sdk");
  const client = new Anthropic();
  const response = await client.messages.create({
    model,
    max_tokens: 2048,
    messages: [{
      role: "user",
      content: [
        { type: "image", source: { type: "base64", media_type: "image/png", data: imageBase64 } },
        { type: "text", text: prompt },
      ],
    }],
  });
  const text = response.content.find((b) => b.type === "text");
  return { provider: "anthropic", model, content: text?.text ?? "" };
}

// ---------------------------------------------------------------------------
// OpenAI (and OpenAI-compatible: Codex, Kimi)
// ---------------------------------------------------------------------------

async function callOpenAI(
  prompt: string,
  imageBase64: string,
  model: string,
  baseURL?: string,
): Promise<VisionResult> {
  const { default: OpenAI } = await import("openai");
  const client = new OpenAI({ ...(baseURL ? { baseURL } : {}) });
  const response = await client.chat.completions.create({
    model,
    max_tokens: 2048,
    messages: [{
      role: "user",
      content: [
        { type: "image_url", image_url: { url: `data:image/png;base64,${imageBase64}`, detail: "high" } },
        { type: "text", text: prompt },
      ],
    }],
  });
  const content = response.choices[0]?.message?.content ?? "";
  return { provider: baseURL ? "openai-compat" : "openai", model, content };
}

// ---------------------------------------------------------------------------
// Google Gemini
// ---------------------------------------------------------------------------

async function callGoogle(
  prompt: string,
  imageBase64: string,
  model: string,
): Promise<VisionResult> {
  const { GoogleGenAI } = await import("@google/genai");
  const apiKey = process.env.GEMINI_API_KEY ?? process.env.GOOGLE_API_KEY ?? "";
  const client = new GoogleGenAI({ apiKey });
  const response = await client.models.generateContent({
    model,
    contents: [{
      role: "user",
      parts: [
        { inlineData: { mimeType: "image/png", data: imageBase64 } },
        { text: prompt },
      ],
    }],
  });
  const content = response.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
  return { provider: "google", model, content };
}

// ---------------------------------------------------------------------------
// PDF rendering via pymupdf subprocess
// ---------------------------------------------------------------------------

const PDF_RENDER_SCRIPT = resolve(
  getWaddingtonHome(), "..", "workspace", "evaluation", "pdf_render.py"
);

export async function renderPdfPages(
  pdfPath: string,
  options: { dpi?: number; maxPages?: number } = {},
): Promise<RenderedPage[]> {
  const { dpi = 150, maxPages = 30 } = options;
  const { stdout } = await execFileAsync("python3", [
    PDF_RENDER_SCRIPT,
    pdfPath,
    String(dpi),
    String(maxPages),
  ]);
  const result = JSON.parse(stdout);
  if (result.error) throw new Error(`pdf_render: ${result.error}`);
  return result as RenderedPage[];
}

// ---------------------------------------------------------------------------
// High-level: extract tables from a PDF as CSV strings
// ---------------------------------------------------------------------------

const TABLE_PROMPT = `Identify all tables on this page.
For each table, output it as CSV with a header row, preceded by a comment line "# Table N: <short description>".
If there are no tables, output exactly: NO_TABLES
Output only CSV and comment lines — no other text.`;

export async function extractTablesFromPdf(
  pdfPath: string,
  options: { dpi?: number; maxPages?: number; provider?: string; model?: string } = {},
): Promise<Array<{ page: number; csv: string }>> {
  const pages = await renderPdfPages(pdfPath, options);
  const results: Array<{ page: number; csv: string }> = [];

  for (const page of pages) {
    const result = await callVision(TABLE_PROMPT, page.b64_png, options);
    if (result.content.trim() !== "NO_TABLES" && result.content.trim() !== "") {
      results.push({ page: page.page_num, csv: result.content });
    }
  }

  return results;
}
