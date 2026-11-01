#!/usr/bin/env node

import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { validateReadiness } from "./validate-pilot-readiness.mjs";

const root = mkdtempSync(join(tmpdir(), "sarce-admission-"));
const sha = "a".repeat(40);
const digest = `sha256:${"b".repeat(64)}`;
const gates = Object.fromEntries([
  "legalOwnerApproval", "privacyNoticeApproval", "crossBorderBasisApproval", "backupRetentionConfigured",
  "productionCi", "productionMigrations", "tenantIsolation", "durableRestartSmoke", "backupRestore",
  "restoreDeletionCheck", "exportAndDeletion", "desktopAndMobileSmoke", "operatorRunbookDryRun",
].map((name) => [name, true]));
const evidenceFiles = {};
for (const name of ["runtime", "talBenchmark", "isolation", "restart", "privacy", "restore", "browserQa", "operations"]) {
  const path = join(root, `${name}.json`);
  writeFileSync(path, JSON.stringify({
    schemaVersion: 1, artifactSha: sha, imageDigest: digest, status: "passed",
    checkedAt: "2026-11-01T00:00:00Z", verifiedBy: "release-operator", checks: { proof: true },
  }));
  evidenceFiles[name] = path;
}
const claimsLedger = join(root, "claims.json");
writeFileSync(claimsLedger, JSON.stringify({ claims: [
  { id: "brilliant-v4", status: "proven" },
  { id: "tal-reference-band", status: "proven" },
  { id: "participant-resonance", status: "pilot_question" },
  { id: "experimental-lenses", status: "not_admitted" },
] }));
const manifest = {
  schemaVersion: 3, artifactSha: sha, status: "admitted", participantCap: 10, durationDays: 14,
  minimumReadsPerParticipant: 10,
  successThresholds: { medianFeelsLikeMePercent: 70, minimumContinueFraction: 0.5 },
  gates, evidenceFiles, claimsLedger,
  evidence: {
    deploymentUrl: "https://pilot.example", webDeploymentId: "web-123", apiDeploymentId: "api-123",
    migrationLogId: "migration-123", apiImageDigest: digest, databaseRegion: "Singapore",
    backupId: "backup-123", restoreProject: "restore-123", backupRetentionDays: 30,
    restoreDeletionCheckResult: "restore-check-123", protocolApprovalId: "legal-123",
    privacyApprovalId: "privacy-123", crossBorderBasisId: "cross-border-123",
    retentionApprovalId: "retention-123", verifiedAt: "2026-11-01T00:00:00Z", verifiedBy: "operator-123",
  },
};

assert.deepEqual(validateReadiness(manifest, sha), []);
assert(validateReadiness({ ...manifest, artifactSha: "c".repeat(40) }, "c".repeat(40)).some((failure) => failure.includes("artifact SHA does not match")));
assert(validateReadiness({ ...manifest, evidence: { ...manifest.evidence, protocolApprovalId: "TODO" } }, sha).some((failure) => failure.includes("protocolApprovalId")));
assert(validateReadiness({ ...manifest, evidence: { ...manifest.evidence, backupRetentionDays: 14 } }, sha).some((failure) => failure.includes("must be 30")));
console.log("pilot admission evidence contract: PASS");
