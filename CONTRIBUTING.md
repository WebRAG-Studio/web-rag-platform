# Contributing

Thank you for improving SiteMind.

1. Open an issue describing the behavior and intended change.
2. Create a focused branch.
3. Keep crawls offline in tests; use synthetic fixtures and mocked HTTP.
4. Run `python -m pytest -q`.
5. Confirm `git add --dry-run .` does not include runtime data, secrets, PDFs, indexes, logs, or backups.
6. Submit a pull request with testing evidence and security implications.

Never include private website content, personal paths, API keys, or customer indexes in a contribution.
