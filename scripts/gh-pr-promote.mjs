#!/usr/bin/env node
/** Open promotion PR staging → main, pre-filled with the promotion template. */
import { spawnSync } from "node:child_process";

// No `shell: true`: a shell re-splits arguments, which breaks titles containing
// spaces or parentheses on Windows. gh is a real executable, so none is needed.
const result = spawnSync(
  "gh",
  [
    "pr",
    "create",
    "--base",
    "main",
    "--head",
    "staging",
    "--title",
    "chore(release): promote staging to main",
    "--body-file",
    ".github/PULL_REQUEST_TEMPLATE/promotion.md",
  ],
  { stdio: "inherit" },
);
if (result.error) {
  process.stderr.write(`error: failed to run gh: ${result.error.message}\n`);
}
process.exit(result.status ?? 1);
