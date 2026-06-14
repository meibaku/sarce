#!/usr/bin/env bash
# Create or update the main branch ruleset (GitHub Rulesets API).
# Rulesets are the modern replacement for classic branch protection.
#
# Usage:
#   ./.github/scripts/apply-ruleset.sh          # create
#   ./.github/scripts/apply-ruleset.sh --replace  # delete classic + recreate ruleset
#
# Requires: gh auth login, admin access to meibaku/sarce

set -euo pipefail

REPO="${REPO:-meibaku/sarce}"
CONFIG="$(dirname "$0")/../rulesets/main.json"

echo "=== Sarce ruleset setup for ${REPO} ==="

# List existing rulesets
echo "Current rulesets:"
gh api "/repos/${REPO}/rulesets" --jq '.[] | "\(.id) \(.name) (\(.enforcement))"' || true

if [[ "${1:-}" == "--replace" ]]; then
  echo ""
  echo "Removing classic branch protection on main (rulesets replace it)..."
  gh api --method DELETE "/repos/${REPO}/branches/main/protection" 2>/dev/null || true
fi

# Check if 'Protect main' already exists
EXISTING_ID=$(gh api "/repos/${REPO}/rulesets" --jq '.[] | select(.name=="Protect main") | .id' 2>/dev/null || true)

if [[ -n "${EXISTING_ID}" ]]; then
  echo "Updating ruleset id=${EXISTING_ID}..."
  gh api --method PUT "/repos/${REPO}/rulesets/${EXISTING_ID}" --input "${CONFIG}"
else
  echo "Creating new ruleset..."
  gh api --method POST "/repos/${REPO}/rulesets" --input "${CONFIG}"
fi

echo ""
echo "Done. Verify at: https://github.com/${REPO}/settings/rules"
gh api "/repos/${REPO}/rulesets" --jq '.[] | {id, name, enforcement, rules: [.rules[].type]}'
