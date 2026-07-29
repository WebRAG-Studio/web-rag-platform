# Security Policy

Report vulnerabilities privately to the repository maintainers rather than opening a public issue. Do not include real credentials or private data in reports.

SiteMind treats crawled content as untrusted data. Its crawler rejects local/private network targets, validates redirects, enforces response limits, and isolates storage by site. Deployments should also use network egress controls, authentication, TLS, rate limiting, and a non-administrator service account.

API keys belong in environment variables or a secret manager. Never commit `.env`, runtime data, indexes, or downloaded documents.
