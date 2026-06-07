import type { ConvMsg } from "./db.js";

export interface ExtractedExperiment {
	gene: string | null;
	model: string | null;
	dataset: string | null;
	metrics: Record<string, number>;
}

const KNOWN_MODELS = ["GEARS", "SCGPT", "CPA", "SAMS-VAE", "SCVI", "PERTPY"];

const METRIC_PATTERNS: [string, RegExp][] = [
	["pearson_de",    /pearson[_\s-]*de\s*[=:]\s*([0-9]+\.?[0-9]*)/i],
	["pearson_delta", /pearson[_\s-]*delta\s*[=:]\s*([0-9]+\.?[0-9]*)/i],
	["pearson",       /\bpearson\b(?![_\s-]*(?:de|delta))\s*[=:]\s*([0-9]+\.?[0-9]*)/i],
	["mse_de",        /MSE[_\s-]*DE\s*[=:]\s*([0-9]+\.?[0-9]*)/i],
	["mse",           /\bMSE\b(?![_\s-]*de)\s*[=:]\s*([0-9]+\.?[0-9]*)/i],
	["r2",            /\bR2\s*[=:]\s*([0-9]+\.?[0-9]*)/i],
];

export function extractExperiment(msgs: ConvMsg[]): ExtractedExperiment | null {
	const userText = msgs.filter(m => m.role === "user").map(m => m.content).join("\n");
	const asstText = msgs.filter(m => m.role === "assistant").map(m => m.content).join("\n");

	// Gene: from /perturb or /design user command
	const geneCmd = userText.match(/\/(?:perturb|design)\s+([A-Z][A-Z0-9]{1,11}(?:[+,][A-Z][A-Z0-9]{1,11})*)/i);
	const gene = geneCmd ? geneCmd[1].toUpperCase() : null;

	// Model: explicit --model flag first, then mention in either side
	const modelFlag = userText.match(/--model\s+([A-Za-z0-9_-]+)/i)
	               ?? asstText.match(new RegExp(`\\b(${KNOWN_MODELS.join("|")})\\b`, "i"));
	const model = modelFlag ? modelFlag[1].toUpperCase() : null;

	// Dataset: h5ad file path
	const dsMatch = userText.match(/--data(?:set)?\s+(\S+\.h5ad)/i)
	             ?? asstText.match(/([a-zA-Z0-9_\-]+\.h5ad)/);
	const dataset = dsMatch ? dsMatch[1] : null;

	// Metrics: scan assistant messages
	const metrics: Record<string, number> = {};
	for (const [key, rx] of METRIC_PATTERNS) {
		const m = asstText.match(rx);
		if (m) metrics[key] = parseFloat(m[1]);
	}

	// Only record if we have a gene perturbation command or actual metrics
	const hasMetrics = Object.keys(metrics).length > 0;
	if (!gene && !hasMetrics) return null;

	return { gene, model, dataset, metrics };
}

export function buildContextPrefix(
	gene: string,
	exps: Array<{ model: string | null; dataset: string | null; metrics: string; created_at: number }>,
): string {
	const lines = exps.slice(0, 4).map(e => {
		const m = JSON.parse(e.metrics) as Record<string, number>;
		const pde = m.pearson_de ?? m.pearson;
		const metric = pde != null ? `pearson_de=${pde.toFixed(3)}` : "no metrics";
		const date = new Date(e.created_at).toISOString().slice(0, 10);
		const modelStr = e.model ?? "unknown model";
		const dataStr = e.dataset ? ` on ${e.dataset}` : "";
		return `  - ${modelStr}${dataStr}: ${metric} (${date})`;
	});
	return `[Previous experiments with ${gene}:\n${lines.join("\n")}\n]\n\n`;
}
