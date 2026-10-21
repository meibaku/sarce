#!/usr/bin/env node
/** Create a PR with base branch `staging`. Example: npm run pr:create -- --title "feat(scope): ..." */
import { spawnSync } from "node:child_process";

const extra = process.argv.slice(2);
// No `shell: true`: a shell re-splits arguments, which breaks titles containing
// spaces or parentheses on Windows. gh is a real executable, so none is needed.
const result = spawnSync("gh", ["pr", "create", "--base", "staging", ...extra], {
  stdio: "inherit",
});
if (result.error) {
  process.stderr.write(`error: failed to run gh: ${result.error.message}\n`);
}
process.exit(result.status ?? 1);
