#!/usr/bin/env node
/** Open promotion PR staging → main, pre-filled with the promotion template. */
import { spawnSync } from "node:child_process";

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
  { stdio: "inherit", shell: process.platform === "win32" },
);
if (result.error) {
  process.stderr.write(`error: failed to run gh: ${result.error.message}\n`);
}
process.exit(result.status ?? 1);
