#!/usr/bin/env bash
# Apply branch protection rules to main using gh CLI.
# Requires: gh auth login, admin access to meibaku/sarce
#
# Usage: ./.github/scripts/apply-branch-protection.sh

set -euo pipefail

REPO="${REPO:-meibaku/sarce}"
BRANCH="${BRANCH:-main}"
CONFIG="$(dirname "$0")/../branch-protection.json"

echo "Applying branch protection to ${REPO}:${BRANCH}..."

gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "/repos/${REPO}/branches/${BRANCH}/protection" \
  --input "${CONFIG}"

echo "Done. Verify at: https://github.com/${REPO}/settings/branches"
