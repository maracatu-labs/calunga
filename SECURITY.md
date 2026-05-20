# Security Policy

We take the security of Calunga and its users seriously. Thanks for helping us keep the project safe.

## Reporting a vulnerability

**Don't open public issues for security vulnerabilities.** Instead:

- Use [GitHub Security Advisories](https://github.com/maracatu-labs/calunga/security/advisories/new) (preferred — private by default), **or** email **contact@maracatu.org** with:
  - A description of the vulnerability
  - Steps to reproduce
  - Potential impact
  - A suggested fix, if you have one

We'll confirm receipt within 72 hours and work with you to understand and fix the issue. Once a fix is published, we can credit you in the release notes (if you'd like).

## Scope

This project includes:

- REST API (`terreiro/`)
- AI chat agent (`terreiro/app/agent/`)
- Web frontend (`cortejo/`)
- Ingestion pipeline (`terreiro/pipeline/`, `terreiro/app/tasks/`)
- Classifiers (`terreiro/app/classifiers/`)

**Out of scope:**

- Vulnerabilities in third-party dependencies — report them to the original maintainer first. Let us know if it directly affects Calunga.
- Attacks that rely on physical access or social engineering against specific contributors.

## Best practices for self-hosters

If you're running Calunga in production:

- Always set `JWT_SECRET` to a strong random value (32+ bytes). Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- Don't expose PostgreSQL or Redis ports publicly — use only the internal Docker network.
- Configure `CORS_ORIGINS` pointing to your public domain (don't use `*`).
- Keep `COOKIE_SECURE=true` in production (it's the default).
- Use HTTPS via Caddy (auto-SSL with Let's Encrypt) or another reverse proxy of your choice.
- Rotate `GOOGLE_API_KEY`, `TRANSPARENCIA_API_TOKEN`, and `RESEND_API_KEY` regularly.
- Run periodic database backups (`make backup`).

## Advisory history

When we publish a security advisory, it will appear at [GitHub Security Advisories](https://github.com/maracatu-labs/calunga/security/advisories).
