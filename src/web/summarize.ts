import type { ConvMsg } from "./db.js";

export interface ConvSummaryResult {
	title: string | null;
	summary: string;
	topics: string[];
	msgCount: number;
}

// ── Title ─────────────────────────────────────────────────────────────────────

export function generateTitle(msgs: ConvMsg[]): string | null {
	const first = msgs.find(m => m.role === "user")?.content?.trim();
	if (!first) return null;

	const perturb = first.match(/\/perturb\s+([A-Z][A-Z0-9+,]{1,20})/i);
	if (perturb) {
		const gene = perturb[1].toUpperCase();
		const modelM = first.match(/--model\s+([a-z0-9_-]+)/i);
		return modelM ? `${gene} · ${modelM[1].toUpperCase()}` : `${gene} perturbation`;
	}

	const discuss = first.match(/\/discuss\s+(\S+)/i);
	if (discuss) {
		try {
			const host = new URL(discuss[1]).hostname.replace(/^www\./, "");
			return `Paper: ${host}`;
		} catch { return "Paper discussion"; }
	}

	const bench = first.match(/\/benchmark\s+(.+)/i);
	if (bench) return `Benchmark: ${bench[1].trim().slice(0, 36)}`;

	const analyze = first.match(/\/analyze\s+(\S+)/i);
	if (analyze) return `Analyze: ${analyze[1].split("/").pop()?.slice(0, 32) ?? analyze[1].slice(0, 32)}`;

	const replicate = first.match(/\/replicate\s+(\S+)/i);
	if (replicate) return `Replicate: ${replicate[1].slice(-36)}`;

	const design = first.match(/\/design\s+(.+)/i);
	if (design) return `Design: ${design[1].trim().slice(0, 40)}`;

	if (first.length > 4 && !first.startsWith("/"))
		return first.slice(0, 45) + (first.length > 45 ? "…" : "");

	return null;
}

// ── Summary body ──────────────────────────────────────────────────────────────

const STOP_WORDS = new Set(["a","an","the","is","are","was","were","be","been","being",
	"have","has","had","do","does","did","will","would","could","should","may","might",
	"and","or","but","for","not","with","from","by","on","at","to","of","in","as"]);

function extractTopics(msgs: ConvMsg[]): string[] {
	const topics = new Set<string>();
	for (const m of msgs) {
		if (m.role !== "user") continue;
		const t = m.content;
		const gene  = t.match(/\/(?:perturb|design|analyze)\s+([A-Z][A-Z0-9+,]{1,20})/i);
		if (gene) gene[1].toUpperCase().split(/[+,]/).forEach(g => topics.add(g));

		const cmd = t.match(/^\/([a-z-]+)/i);
		if (cmd) topics.add(cmd[1].toLowerCase());

		const model = t.match(/--model\s+([a-z0-9_-]+)/i)
		           ?? t.match(/\b(GEARS|scGPT|CPA|SAMS-VAE|SCVI|PERTPY)\b/i);
		if (model) topics.add(model[1].toUpperCase());
	}
	return [...topics];
}

function firstSentences(text: string, maxChars = 250): string {
	const clean = text
		.replace(/!\[.*?\]\(.*?\)/g, "")    // strip md images
		.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")  // strip md links
		.replace(/#{1,6}\s+/g, "")           // strip headings
		.replace(/\*{1,2}([^*]+)\*{1,2}/g, "$1")  // strip bold/italic
		.replace(/`[^`]+`/g, "")             // strip inline code
		.replace(/\n+/g, " ")
		.replace(/\s+/g, " ")
		.trim();

	if (clean.length <= maxChars) return clean;

	// cut at last sentence boundary within maxChars
	const sub = clean.slice(0, maxChars);
	const dot = Math.max(sub.lastIndexOf(". "), sub.lastIndexOf(".\n"), sub.lastIndexOf("! "), sub.lastIndexOf("? "));
	return dot > 40 ? clean.slice(0, dot + 1) : sub + "…";
}

export function generateSummary(msgs: ConvMsg[]): ConvSummaryResult {
	const topics = extractTopics(msgs);

	// Find the last substantial assistant message
	const asstMsgs = msgs.filter(m => m.role === "assistant" && m.content.length > 60);
	const lastAsst = asstMsgs.at(-1);

	// User intent: first user message
	const firstUser = msgs.find(m => m.role === "user")?.content?.trim() ?? "";
	const userSnippet = firstUser.slice(0, 80) + (firstUser.length > 80 ? "…" : "");

	let summary: string;
	if (lastAsst) {
		const finding = firstSentences(lastAsst.content, 220);
		summary = userSnippet
			? `[User] ${userSnippet} → ${finding}`
			: finding;
	} else {
		summary = userSnippet || "Empty conversation";
	}

	return {
		title: generateTitle(msgs),
		summary,
		topics,
		msgCount: msgs.length,
	};
}

// ── Context builder ───────────────────────────────────────────────────────────

export function buildSummaryContext(
	summaries: Array<{ conv_id: string; summary: string; topics_json: string; updated_at: number }>,
	relevantTopics: string[],
): string {
	const upper = relevantTopics.map(t => t.toUpperCase());
	const hits = summaries.filter(s => {
		try {
			const tList = JSON.parse(s.topics_json) as string[];
			return tList.some(t => upper.includes(t.toUpperCase()));
		} catch { return false; }
	}).slice(0, 3);

	if (!hits.length) return "";

	const lines = hits.map(s => {
		const date = new Date(s.updated_at).toISOString().slice(0, 10);
		return `  - [${date}] ${s.summary}`;
	});
	return `[Related past conversations:\n${lines.join("\n")}\n]\n\n`;
}
