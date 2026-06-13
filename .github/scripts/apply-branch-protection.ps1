# Apply branch protection rules to main.
# Requires: gh auth login, admin access to meibaku/sarce
#
# Usage: .\.github\scripts\apply-branch-protection.ps1

$Repo = if ($env:REPO) { $env:REPO } else { "meibaku/sarce" }
$Branch = if ($env:BRANCH) { $env:BRANCH } else { "main" }
$Config = Join-Path $PSScriptRoot "..\branch-protection.json"

Write-Host "Applying branch protection to ${Repo}:${Branch}..."

gh api `
  --method PUT `
  -H "Accept: application/vnd.github+json" `
  "/repos/$Repo/branches/$Branch/protection" `
  --input $Config

Write-Host "Done. Verify at: https://github.com/$Repo/settings/branches"
