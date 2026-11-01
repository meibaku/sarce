#!/usr/bin/env node

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, isAbsolute, resolve } from "node:path";

const REQUIRED_GATES = [
  "legalOwnerApproval", "privacyNoticeApproval", "crossBorderBasisApproval",
  "backupRetentionConfigured", "productionCi", "productionMigrations", "tenantIsolation",
  "durableRestartSmoke", "backupRestore", "restoreDeletionCheck", "exportAndDeletion",
  "desktopAndMobileSmoke", "operatorRunbookDryRun",
];
const REQUIRED_EVIDENCE = [
  "runtime", "talBenchmark", "isolation", "restart", "privacy", "restore", "browserQa", "operations",
];
const REQUIRED_CLAIMS = {
  "brilliant-v4": "proven",
  "tal-reference-band": "proven",
  "experimental-lenses": "not_admitted",
};
const SHA = /^[0-9a-f]{40}$/;
const DIGEST = /^sha256:[0-9a-f]{64}$/;
const PLACEHOLDER = /^(?:todo|tbd|pending|placeholder|replace|example|none|null|n\/a)|(?:todo|placeholder|replace[-_ ]?me)/i;
const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function referencedPath(value) {
  return isAbsolute(value) ? value : resolve(repoRoot, value);
}

export function validateReadiness(manifest, expectedSha) {
  const failures = [];
  if (!expectedSha) failures.push("expected artifact SHA is required as argument 2 or PILOT_ARTIFACT_SHA");
  if (manifest.schemaVersion !== 3) failures.push("schemaVersion must be 3");
  if (!SHA.test(manifest.artifactSha ?? "")) failures.push("artifactSha must be a full Git SHA");
  if (expectedSha && manifest.artifactSha !== expectedSha) failures.push("artifactSha does not match the artifact being admitted");
  if (manifest.status !== "admitted") failures.push("status must be admitted");
  if (manifest.participantCap < 5 || manifest.participantCap > 10) failures.push("participantCap must remain between 5 and 10");
  if (manifest.durationDays !== 14) failures.push("durationDays must be 14");
  if (manifest.minimumReadsPerParticipant !== 10) failures.push("minimumReadsPerParticipant must be 10");
  if (manifest.successThresholds?.medianFeelsLikeMePercent !== 70) failures.push("median feels-like-me threshold must be 70%");
  if (manifest.successThresholds?.minimumContinueFraction !== 0.5) failures.push("continue threshold must be 0.5");

  for (const gate of REQUIRED_GATES) {
    if (manifest.gates?.[gate] !== true) failures.push(`gate ${gate} is not proven`);
  }
  const details = manifest.evidence ?? {};
  for (const field of ["deploymentUrl", "webDeploymentId", "apiDeploymentId", "migrationLogId", "backupId", "restoreProject", "restoreDeletionCheckResult", "verifiedAt", "verifiedBy"]) {
    if (!details[field]) failures.push(`evidence.${field} is missing`);
  }
  if (!DIGEST.test(details.apiImageDigest ?? "")) failures.push("evidence.apiImageDigest must be an immutable sha256 digest");
  if (!["Singapore", "ap-southeast-1"].includes(details.databaseRegion)) failures.push("evidence.databaseRegion must identify Singapore");
  if (details.backupRetentionDays !== 30) failures.push("evidence.backupRetentionDays must be 30");
  for (const field of ["protocolApprovalId", "privacyApprovalId", "crossBorderBasisId", "retentionApprovalId"]) {
    const value = details[field];
    if (typeof value !== "string" || value.trim().length < 3 || PLACEHOLDER.test(value.trim())) {
      failures.push(`evidence.${field} must be a named, non-placeholder approval identifier`);
    }
  }
  const approvals = [details.protocolApprovalId, details.privacyApprovalId, details.crossBorderBasisId, details.retentionApprovalId];
  if (approvals.every((value) => typeof value === "string") && new Set(approvals).size !== approvals.length) {
    failures.push("legal approval identifiers must be distinct");
  }

  for (const name of REQUIRED_EVIDENCE) {
    const reference = manifest.evidenceFiles?.[name];
    if (!reference) {
      failures.push(`evidenceFiles.${name} is missing`);
      continue;
    }
    try {
      const evidence = readJson(referencedPath(reference));
      if (!Number.isInteger(evidence.schemaVersion) || evidence.schemaVersion < 1) failures.push(`${name} evidence has no schema version`);
      if (evidence.artifactSha !== manifest.artifactSha) failures.push(`${name} evidence artifact SHA does not match`);
      if (evidence.imageDigest !== details.apiImageDigest) failures.push(`${name} evidence image digest does not match`);
      if (evidence.status !== "passed") failures.push(`${name} evidence did not pass`);
      if (!evidence.checkedAt || !evidence.verifiedBy) failures.push(`${name} evidence lacks verifier metadata`);
      const checks = Object.values(evidence.checks ?? {});
      if (!checks.length || checks.some((value) => value !== true)) failures.push(`${name} evidence checks are incomplete`);
    } catch (error) {
      failures.push(`evidenceFiles.${name} cannot be read: ${error.code ?? error.name}`);
    }
  }

  try {
    const claims = readJson(referencedPath(manifest.claimsLedger ?? ""));
    const allowed = new Set(["proven", "pilot_question", "not_admitted"]);
    const byId = new Map((claims.claims ?? []).map((claim) => [claim.id, claim]));
    if (!(claims.claims ?? []).length || (claims.claims ?? []).some((claim) => !allowed.has(claim.status))) failures.push("claims ledger contains an invalid status");
    for (const [id, status] of Object.entries(REQUIRED_CLAIMS)) {
      if (byId.get(id)?.status !== status) failures.push(`claim ${id} must be ${status}`);
    }
  } catch (error) {
    failures.push(`claimsLedger cannot be read: ${error.code ?? error.name}`);
  }
  return failures;
}

function main() {
  const manifestPath = resolve(process.argv[2] ?? "docs/evidence/style-pilot-readiness.json");
  const expectedSha = process.argv[3] ?? process.env.PILOT_ARTIFACT_SHA;
  const manifest = readJson(manifestPath);
  const failures = validateReadiness(manifest, expectedSha);
  if (failures.length) {
    console.error("STYLE PILOT ADMISSION: BLOCKED");
    failures.forEach((failure) => console.error(`- ${failure}`));
    process.exitCode = 1;
    return;
  }
  console.log(`STYLE PILOT ADMISSION: PASS (${manifest.artifactSha})`);
}

if (resolve(process.argv[1] ?? "") === fileURLToPath(import.meta.url)) main();
