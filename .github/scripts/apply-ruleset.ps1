# Create or update the main branch ruleset (GitHub Rulesets API).
# Usage:
#   .\.github\scripts\apply-ruleset.ps1
#   .\.github\scripts\apply-ruleset.ps1 -Replace   # remove classic protection first
#
# Requires: gh auth login, admin access to meibaku/sarce

param([switch]$Replace)

$Repo = if ($env:REPO) { $env:REPO } else { "meibaku/sarce" }
$Config = Join-Path $PSScriptRoot "..\rulesets\main.json"

Write-Host "=== Sarce ruleset setup for $Repo ==="

Write-Host "Current rulesets:"
gh api "/repos/$Repo/rulesets" --jq '.[] | "\(.id) \(.name) (\(.enforcement))"' 2>$null

if ($Replace) {
    Write-Host "Removing classic branch protection on main..."
    gh api --method DELETE "/repos/$Repo/branches/main/protection" 2>$null
}

$existingId = gh api "/repos/$Repo/rulesets" --jq '.[] | select(.name=="Protect main") | .id' 2>$null

if ($existingId) {
    Write-Host "Updating ruleset id=$existingId..."
    gh api --method PUT "/repos/$Repo/rulesets/$existingId" --input $Config
} else {
    Write-Host "Creating new ruleset..."
    gh api --method POST "/repos/$Repo/rulesets" --input $Config
}

Write-Host "Done. Verify at: https://github.com/$Repo/settings/rules"
gh api "/repos/$Repo/rulesets" --jq '.[] | {id, name, enforcement}'
