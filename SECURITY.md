# Security Policy

## Supported versions

| Version | Supported          |
| ------- | ------------------ |
| main    | ✅ Active development |
| < 0.1   | ❌ No longer supported |

## Reporting a vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

1. Go to [GitHub Security Advisories](https://github.com/meibaku/sarce/security/advisories/new)
2. Submit a **private** security advisory with:
   - Description of the vulnerability
   - Steps to reproduce
   - Impact assessment
   - Suggested fix (if any)

We aim to acknowledge reports within **7 days** and provide a status update within **30 days**.

## In scope

| Area | Concern |
|------|---------|
| **Secrets exposure** | `SUPABASE_SERVICE_ROLE_KEY`, API keys in `NEXT_PUBLIC_*` vars, `.env` committed |
| **Auth & RLS** | Bypassing Row Level Security on `games`, `game_moves`, `profiles` |
| **API input** | Stockfish path injection, SQL injection via unsanitized inputs |
| **Supabase** | `user_metadata` used for authorization (forbidden — see Supabase skill) |
| **Client exposure** | Service role key reachable from browser bundle |

## Out of scope (for now)

- Denial of service via expensive Stockfish analysis (rate limiting planned)
- Chess.com API availability or rate limits
- Social engineering
- Issues in third-party dependencies without a direct Sarce exploit path

## Security practices for contributors

- Never commit `.env` — use `.env.example` for templates
- Never put `service_role` key in `NEXT_PUBLIC_` variables
- Enable RLS on every new table in exposed schemas
- Run `npm run ci` before PR — includes architecture and philosophy contract tests

## Disclosure policy

- Valid reports are fixed before public disclosure when possible
- Credit given to reporters in the advisory (unless you prefer anonymity)
- Coordinated disclosure preferred

## Contact

Maintainer: [@meibaku](https://github.com/meibaku) via GitHub Security Advisories only.
