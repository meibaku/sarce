#!/usr/bin/env node
/** Create a PR with base branch `staging`. Example: npm run pr:create -- --title "feat(scope): ..." */
import { spawnSync } from "node:child_process";

const extra = process.argv.slice(2);
const result = spawnSync("gh", ["pr", "create", "--base", "staging", ...extra], {
  stdio: "inherit",
  shell: process.platform === "win32",
});
if (result.error) {
  process.stderr.write(`error: failed to run gh: ${result.error.message}\n`);
}
process.exit(result.status ?? 1);
