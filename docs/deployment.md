# Deployment

Run SiteMind behind an authenticated reverse proxy with TLS. Use a dedicated service account and persistent storage for `DATA_DIR`.

Recommended production controls:

- restrict outbound network access to intended public destinations;
- add authentication and per-user authorization;
- enforce rate limits and request-body limits at the proxy;
- store provider credentials in a secret manager;
- back up site configuration and indexes according to your retention policy;
- run multiple workers only after moving crawl coordination to a shared queue;
- review robots.txt, terms, copyright, and applicable data-protection obligations.

The bundled crawler is designed for one application process. Horizontal production deployments should replace in-process jobs with a durable worker system.
