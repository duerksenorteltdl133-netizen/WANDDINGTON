import { mkdirSync } from "node:fs";
import { homedir } from "node:os";
import { resolve } from "node:path";

export function getWaddingtonHome(): string {
	return resolve(process.env.WADDINGTON_HOME ?? homedir(), ".waddington");
}

export function getWaddingtonAgentDir(home = getWaddingtonHome()): string {
	return resolve(home, "agent");
}

export function getWaddingtonMemoryDir(home = getWaddingtonHome()): string {
	return resolve(home, "memory");
}

export function getWaddingtonStateDir(home = getWaddingtonHome()): string {
	return resolve(home, ".state");
}

export function getDefaultSessionDir(home = getWaddingtonHome()): string {
	return resolve(home, "sessions");
}

export function getBootstrapStatePath(home = getWaddingtonHome()): string {
	return resolve(getWaddingtonStateDir(home), "bootstrap.json");
}

export function ensureWaddingtonHome(home = getWaddingtonHome()): void {
	for (const dir of [
		home,
		getWaddingtonAgentDir(home),
		getWaddingtonMemoryDir(home),
		getWaddingtonStateDir(home),
		getDefaultSessionDir(home),
	]) {
		mkdirSync(dir, { recursive: true });
	}
}
