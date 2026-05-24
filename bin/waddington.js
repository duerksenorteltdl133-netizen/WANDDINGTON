#!/usr/bin/env node
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const MIN_NODE_VERSION    = "20.19.0";
const MAX_NODE_MAJOR      = 24;
const PREFERRED_NODE_MAJOR = 22;

function parseNodeVersion(v) {
  const [major = "0", minor = "0", patch = "0"] = v.replace(/^v/, "").split(".");
  return { major: +major || 0, minor: +minor || 0, patch: +patch || 0 };
}
function cmpNodeVersions(l, r) {
  if (l.major !== r.major) return l.major - r.major;
  if (l.minor !== r.minor) return l.minor - r.minor;
  return l.patch - r.patch;
}

const parsed = parseNodeVersion(process.versions.node);
if (cmpNodeVersions(parsed, parseNodeVersion(MIN_NODE_VERSION)) < 0 || parsed.major > MAX_NODE_MAJOR) {
  console.error(`waddington requires Node.js ${MIN_NODE_VERSION}–${MAX_NODE_MAJOR}.x (detected ${process.versions.node}).`);
  console.error(`Switch with: nvm install ${PREFERRED_NODE_MAJOR} && nvm use ${PREFERRED_NODE_MAJOR}`);
  process.exit(1);
}

const here = import.meta.dirname;
await import(pathToFileURL(resolve(here, "..", "scripts", "patch-embedded-pi.mjs")).href);
await import(pathToFileURL(resolve(here, "..", "dist", "index.js")).href);
