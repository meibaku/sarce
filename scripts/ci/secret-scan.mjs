#!/usr/bin/env node
/**
 * Lightweight repository secret scanner for CI.
 * Dependency-free; scans every tracked file that is not binary. A finding is
 * skipped only when the secret value itself is a placeholder, or its line
 * carries `secret-scan:ignore`.
 * Run via `npm run scan:secrets` (CI job: security-gates).
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

const MAX_FILE_BYTES = 5 * 1024 * 1024;

// Everything else is scanned, including extensionless files (id_rsa, .npmrc).
const BINARY_EXTENSIONS = new Set([
  ".gif",
  ".ico",
  ".jpeg",
  ".jpg",
  ".pdf",
  ".png",
  ".webp",
  ".woff",
  ".woff2",
  ".zip",
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

// Anchored and tested against the secret value only — a real secret that merely
// contains "sample", or sits next to the word "test", must still be reported.
const PLACEHOLDER_VALUE =
  /^(?:(?:example|placeholder|dummy|sample|fake|mock|redacted|changeme|ci-placeholder|x{3,})(?![a-z0-9])|your[_-]|<[^>]+>$|\$\{[^}]+\}$)/i;
const IGNORE_MARKER = "secret-scan:ignore";

const CREDENTIAL_NAME =
  "[A-Za-z0-9_-]*(?:password|passwd|secret|api[_-]?key|token|service[_-]?role[_-]?key)[A-Za-z0-9_-]*";

// A pattern with a `value` group has its placeholder check applied to that group;
// one with `files` only runs on matching paths.
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
    name: "Supabase secret key",
    pattern: /\bsb_secret_[A-Za-z0-9_-]{20,}\b/,
  },
  {
    name: "JWT",
    pattern:
      /\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/,
  },
  {
    // Quoted assignment in code or config; the name may carry a prefix (AUTH_TOKEN).
    name: "Hard-coded credential assignment",
    pattern: new RegExp(
      `(?<![A-Za-z0-9_-])${CREDENTIAL_NAME}["']?\\s*[:=]\\s*["'](?<value>[^"'\\s]{12,})["']`,
      "i",
    ),
  },
  {
    // Unquoted KEY=value line; limited to env-style files, where it is not ordinary code.
    name: "Credential in env-style assignment",
    files: /(^|\/)(\.env[^/]*|\.npmrc|\.pypirc|[^/]*\.(ini|cfg|conf|properties|toml))$/i,
    pattern: new RegExp(
      `^[ \\t]*(?:export[ \\t]+)?(?:[^\\s=]*:)?${CREDENTIAL_NAME}[ \\t]*=[ \\t]*(?<value>[^\\s"'#]{12,})[ \\t]*$`,
      "im",
    ),
  },
];

function normalizeGitPath(file) {
  return file.replaceAll("\\", "/");
}

function isBinaryExtension(file) {
  const base = file.split("/").pop() ?? file;
  const dot = base.lastIndexOf(".");
  return dot > 0 && BINARY_EXTENSIONS.has(base.slice(dot).toLowerCase());
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

/** Returns { findings } for a scanned file, or { skipped: reason } when it was not scanned. */
function scanFile(file) {
  let buf;
  try {
    buf = readFileSync(file);
  } catch (err) {
    // Tracked but deleted in the working tree is normal; anything else is worth a warning.
    return err.code === "ENOENT" ? { findings: [] } : { skipped: `unreadable (${err.code})` };
  }
  if (buf.length > MAX_FILE_BYTES) return { skipped: "larger than 5 MB" };
  if (buf.includes(0)) return { findings: [] }; // binary content
  const content = buf.toString("utf8");

  const findings = [];
  for (const { name, pattern, files: onlyFiles } of SECRET_PATTERNS) {
    if (onlyFiles && !onlyFiles.test(file)) continue;
    const re = new RegExp(pattern.source, `${pattern.flags.replace("g", "")}g`);
    let match;
    while ((match = re.exec(content)) !== null) {
      const value = match.groups?.value ?? match[0];
      if (PLACEHOLDER_VALUE.test(value)) continue;
      const lineStart = content.lastIndexOf("\n", match.index) + 1;
      const lineEnd = content.indexOf("\n", match.index);
      const lineText = content.slice(lineStart, lineEnd < 0 ? content.length : lineEnd);
      if (lineText.includes(IGNORE_MARKER)) continue;
      const line = content.slice(0, match.index).split(/\r?\n/).length;
      findings.push({ file, line, name });
    }
  }
  return { findings };
}

const files = listTrackedFiles().filter(
  (f) => !shouldSkip(f) && !isBinaryExtension(f),
);
const all = [];
const skipped = [];
for (const file of files) {
  const result = scanFile(file);
  if (result.skipped) skipped.push(`${file} — ${result.skipped}`);
  else all.push(...result.findings);
}

for (const s of skipped) console.warn(`Secret scan: NOT scanned: ${s}`);

if (all.length) {
  console.error("Secret scan failed:");
  for (const f of all) {
    console.error(`  ${f.file}:${f.line} — ${f.name}`);
  }
  process.exit(1);
}

console.log(
  `Secret scan passed (${files.length - skipped.length} files scanned, ${skipped.length} skipped).`,
);
