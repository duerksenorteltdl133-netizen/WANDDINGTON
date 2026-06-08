import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { getWaddingtonHome } from "../config/paths.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface LeaderboardRun {
  date: string;                         // ISO date string
  metrics: Record<string, number>;      // e.g. {pearson_de: 0.74, pearson: 0.85}
  rfs?: number;                         // overall RFS score if available
  conv_id?: string;                     // conversation that produced this run
}

export interface LeaderboardEntry {
  dataset: string;
  model: string;
  best: Record<string, number>;         // best observed value per metric
  best_rfs?: number;
  run_count: number;
  last_updated: string;
  history: LeaderboardRun[];            // chronological run log
}

// Leaderboard[dataset][model] = entry
type Leaderboard = Record<string, Record<string, LeaderboardEntry>>;

// ---------------------------------------------------------------------------
// File path
// ---------------------------------------------------------------------------

function leaderboardPath(): string {
  return resolve(getWaddingtonHome(), "..", "workspace", "benchmarks", "leaderboard.json");
}

// ---------------------------------------------------------------------------
// I/O
// ---------------------------------------------------------------------------

export function loadLeaderboard(): Leaderboard {
  const p = leaderboardPath();
  if (!existsSync(p)) return {};
  try {
    return JSON.parse(readFileSync(p, "utf8")) as Leaderboard;
  } catch {
    return {};
  }
}

function saveLeaderboard(lb: Leaderboard): void {
  const p = leaderboardPath();
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, JSON.stringify(lb, null, 2));
}

// ---------------------------------------------------------------------------
// Update
// ---------------------------------------------------------------------------

export function updateLeaderboard(
  dataset: string,
  model: string,
  metrics: Record<string, number>,
  rfs?: number,
  convId?: string,
): void {
  if (!dataset || !model) return;

  const lb = loadLeaderboard();
  if (!lb[dataset]) lb[dataset] = {};

  const existing = lb[dataset]![model];
  const run: LeaderboardRun = {
    date: new Date().toISOString().split("T")[0]!,
    metrics,
    ...(rfs !== undefined ? { rfs } : {}),
    ...(convId ? { conv_id: convId } : {}),
  };

  if (!existing) {
    lb[dataset]![model] = {
      dataset,
      model,
      best: { ...metrics },
      ...(rfs !== undefined ? { best_rfs: rfs } : {}),
      run_count: 1,
      last_updated: run.date,
      history: [run],
    };
  } else {
    // Update best per metric
    for (const [k, v] of Object.entries(metrics)) {
      const cur = existing.best[k];
      // For MSE: lower is better; for everything else: higher is better
      const isBetter = k.startsWith("mse")
        ? (cur === undefined || v < cur)
        : (cur === undefined || v > cur);
      if (isBetter) existing.best[k] = v;
    }
    if (rfs !== undefined && (existing.best_rfs === undefined || rfs > existing.best_rfs)) {
      existing.best_rfs = rfs;
    }
    existing.run_count += 1;
    existing.last_updated = run.date;
    existing.history.push(run);
  }

  saveLeaderboard(lb);
}

// ---------------------------------------------------------------------------
// Read helpers
// ---------------------------------------------------------------------------

export function getLeaderboardEntry(dataset: string, model: string): LeaderboardEntry | null {
  return loadLeaderboard()[dataset]?.[model] ?? null;
}

export function listLeaderboardDatasets(): string[] {
  return Object.keys(loadLeaderboard());
}

// Returns a flat sorted list of entries for a given dataset (or all datasets)
export function rankLeaderboard(dataset?: string): LeaderboardEntry[] {
  const lb = loadLeaderboard();
  const entries: LeaderboardEntry[] = [];
  for (const [ds, models] of Object.entries(lb)) {
    if (dataset && ds !== dataset) continue;
    for (const entry of Object.values(models)) {
      entries.push(entry);
    }
  }
  // Sort by best pearson_de (desc), fallback to best_rfs
  return entries.sort((a, b) => {
    const ad = a.best["pearson_de"] ?? a.best_rfs ?? 0;
    const bd = b.best["pearson_de"] ?? b.best_rfs ?? 0;
    return bd - ad;
  });
}
