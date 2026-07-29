"""Create and crawl one SiteMind site from the command line."""
import argparse
import time

from app.api.routes import crawler, store
from app.core.security import canonicalize_url, validate_public_url
from app.models.site import SiteCreate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("url")
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--max-depth", type=int, default=3)
    args = parser.parse_args()
    url = validate_public_url(canonicalize_url(args.url))
    site = store.create(SiteCreate(
        site_name=args.name,
        website_url=url,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
    ), url)
    crawler.start(site.site_id)
    print(f"Created {site.site_id}. Monitor /api/sites/{site.site_id}/progress.")


if __name__ == "__main__":
    main()
