// Lazy-loaded local embedding pipeline via @xenova/transformers (ONNX).
// First call downloads ~25 MB model to ~/.cache/huggingface; subsequent calls
// use the on-disk cache and warm up in < 1 s.

const MODEL_ID = "Xenova/all-MiniLM-L6-v2";
export const EMBED_DIMS = 384;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let _pipe: any = null;
let _loading: Promise<void> | null = null;

async function loadPipeline(): Promise<void> {
	if (_pipe) return;
	if (_loading) { await _loading; return; }
	_loading = (async () => {
		const { pipeline, env } = await import("@xenova/transformers");
		// suppress progress logs in production
		env.allowLocalModels = false;
		_pipe = await pipeline("feature-extraction", MODEL_ID, { quantized: true });
	})();
	await _loading;
}

export async function embed(text: string): Promise<Float32Array> {
	await loadPipeline();
	// eslint-disable-next-line @typescript-eslint/no-unsafe-call
	const out = await _pipe(text.slice(0, 512), { pooling: "mean", normalize: true });
	// out.data is Float32Array
	return out.data as Float32Array;
}

/** Dot product of two unit-normalized vectors == cosine similarity. */
export function dotSim(a: Float32Array, b: Float32Array): number {
	let s = 0;
	for (let i = 0; i < a.length; i++) s += a[i] * b[i];
	return s;
}

/** Serialize Float32Array → Buffer for SQLite BLOB storage. */
export function vecToBlob(v: Float32Array): Buffer {
	return Buffer.from(v.buffer, v.byteOffset, v.byteLength);
}

/** Deserialize SQLite BLOB → Float32Array. */
export function blobToVec(buf: Buffer): Float32Array {
	return new Float32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4);
}

/** Reciprocal Rank Fusion over two ranked lists. k = 60 (standard default). */
export function rrf(
	lists: Array<Array<{ id: string; rank: number }>>,
	k = 60,
): Array<{ id: string; score: number }> {
	const acc = new Map<string, number>();
	for (const list of lists) {
		for (const { id, rank } of list) {
			acc.set(id, (acc.get(id) ?? 0) + 1 / (k + rank));
		}
	}
	return [...acc.entries()]
		.map(([id, score]) => ({ id, score }))
		.sort((a, b) => b.score - a.score);
}
