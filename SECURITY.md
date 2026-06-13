# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| main    | ✅ Active development |

## Reporting a vulnerability

This is a private personal project. If you discover a security issue:

1. **Do not** open a public issue
2. Contact the maintainer via GitHub private security advisory:
   https://github.com/meibaku/sarce/security/advisories/new

## Scope

Areas we care about:

- Exposed `SUPABASE_SERVICE_ROLE_KEY` or secrets in client code
- RLS bypass on user game data
- Stockfish path injection via API input

Out of scope for now: denial-of-service via expensive Stockfish analysis (rate limiting planned).
