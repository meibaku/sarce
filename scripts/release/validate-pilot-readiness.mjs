#!/usr/bin/env node

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const evidencePath = resolve(process.argv[2] ?? "docs/evidence/style-pilot-readiness.json");
const expectedSha = process.argv[3] ?? process.env.PILOT_ARTIFACT_SHA;
const evidence = JSON.parse(readFileSync(evidencePath, "utf8"));
const failures = [];

if (!expectedSha) failures.push("expected artifact SHA is required as argument 2 or PILOT_ARTIFACT_SHA");
if (!/^[0-9a-f]{40}$/.test(evidence.artifactSha ?? "")) failures.push("artifactSha must be a full Git SHA");
if (expectedSha && evidence.artifactSha !== expectedSha) failures.push("artifactSha does not match the artifact being admitted");
if (evidence.status !== "admitted") failures.push("status must be admitted");
if (evidence.participantCap < 5 || evidence.participantCap > 10) failures.push("participantCap must remain between 5 and 10");
if (evidence.durationDays !== 14) failures.push("durationDays must be 14");
if (evidence.minimumReadsPerParticipant !== 10) failures.push("minimumReadsPerParticipant must be 10");
if (evidence.successThresholds?.medianFeelsLikeMePercent !== 70) failures.push("median feels-like-me threshold must be 70%");
if (evidence.successThresholds?.minimumContinueFraction !== 0.5) failures.push("continue threshold must be 0.5");

for (const [gate, value] of Object.entries(evidence.gates ?? {})) {
  if (value !== true) failures.push(`gate ${gate} is not proven`);
}
for (const field of ["deploymentUrl", "apiImageDigest", "databaseRegion", "backupId", "restoreProject", "backupRetentionDays", "restoreDeletionCheckResult", "protocolApprovalId", "privacyApprovalId", "crossBorderBasisId", "verifiedAt", "verifiedBy"]) {
  if (!evidence.evidence?.[field]) failures.push(`evidence.${field} is missing`);
}
if (evidence.evidence?.backupRetentionDays && !Number.isInteger(evidence.evidence.backupRetentionDays)) failures.push("evidence.backupRetentionDays must be an integer");

if (failures.length) {
  console.error("STYLE PILOT ADMISSION: BLOCKED");
  failures.forEach((failure) => console.error(`- ${failure}`));
  process.exit(1);
}
console.log(`STYLE PILOT ADMISSION: PASS (${evidence.artifactSha})`);
