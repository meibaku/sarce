#!/usr/bin/env node
/**
 * Lightweight repository secret scanner for CI.
 * Dependency-free; scans tracked text files; ignores example/placeholder context.
 * Run via `npm run scan:secrets` (CI job: security-gates).
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

const MAX_FILE_BYTES = 1024 * 1024;
const TEXT_EXTENSIONS = new Set([
  ".env",
  ".example",
  ".json",
  ".js",
  ".jsx",
  ".mjs",
  ".md",
  ".ps1",
  ".py",
  ".sh",
  ".sql",
  ".toml",
  ".ts",
  ".tsx",
  ".txt",
  ".yaml",
  ".yml",
]);

const SKIP_PATHS = [
  /^pnpm-lock\.yaml$/,
  /^package-lock\.json$/,
  /^yarn\.lock$/,
  /^node_modules\//,
  /^coverage\//,
  /^\.git\//,
  /^dist\//,
  /^build\//,
  /^\.next\//,
  /^\.turbo\//,
  /(^|\/)__pycache__\//,
  /(^|\/)\.venv\//,
];

const ALLOWED_CONTEXT =
  /\b(example|placeholder|dummy|sample|test|fake|mock|redacted|changeme|your[_-]?|xxx|demo:|<[^>]+>|\$\{[^}]+})\b/i;

const SECRET_PATTERNS = [
  {
    name: "Private key material",
    pattern: /-----BEGIN (?:RSA |EC |OPENSSH |DSA |)?PRIVATE KEY-----/,
  },
  {
    name: "GitHub token",
    pattern: /\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b/,
  },
  {
    name: "OpenAI API key",
    pattern: /\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b/,
  },
  {
    name: "AWS access key",
    pattern: /\b(?:AKIA|ASIA)[A-Z0-9]{16}\b/,
  },
  {
    name: "Slack token",
    pattern: /\bxox[baprs]-[A-Za-z0-9-]{20,}\b/,
  },
  {
    name: "JWT",
    pattern:
      /\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/,
  },
  {
    name: "Hard-coded credential assignment",
    pattern:
      /\b(?:password|passwd|secret|api[_-]?key|token|client[_-]?secret)\b\s*[:=]\s*["'][^"']{12,}["']/i,
  },
];

function normalizeGitPath(file) {
  return file.replaceAll("\\", "/");
}

function isTextCandidate(file) {
  const base = file.split("/").pop() ?? file;
  if (base === ".env" || base.startsWith(".env.")) return true;
  const dot = base.lastIndexOf(".");
  if (dot < 0) return false;
  return TEXT_EXTENSIONS.has(base.slice(dot).toLowerCase());
}

function shouldSkip(file) {
  return SKIP_PATHS.some((re) => re.test(file));
}

function listTrackedFiles() {
  const out = execFileSync("git", ["ls-files", "-z"], { encoding: "buffer" });
  return out
    .toString("utf8")
    .split("\0")
    .filter(Boolean)
    .map(normalizeGitPath);
}

function scanFile(file) {
  const findings = [];
  let content;
  try {
    const buf = readFileSync(file);
    if (buf.length > MAX_FILE_BYTES) return findings;
    content = buf.toString("utf8");
  } catch {
    return findings;
  }

  for (const { name, pattern } of SECRET_PATTERNS) {
    const re = new RegExp(pattern.source, pattern.flags.includes("g") ? pattern.flags : `${pattern.flags}g`);
    let match;
    while ((match = re.exec(content)) !== null) {
      const start = Math.max(0, match.index - 40);
      const end = Math.min(content.length, match.index + match[0].length + 40);
      const ctx = content.slice(start, end);
      if (ALLOWED_CONTEXT.test(ctx)) continue;
      const line = content.slice(0, match.index).split(/\r?\n/).length;
      findings.push({ file, line, name });
    }
  }
  return findings;
}

const files = listTrackedFiles().filter(
  (f) => !shouldSkip(f) && isTextCandidate(f),
);
const all = files.flatMap(scanFile);

if (all.length) {
  console.error("Secret scan failed:");
  for (const f of all) {
    console.error(`  ${f.file}:${f.line} — ${f.name}`);
  }
  process.exit(1);
}

console.log(`Secret scan passed (${files.length} files).`);
