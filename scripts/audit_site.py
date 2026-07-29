"""Report non-sensitive counts for one isolated SiteMind site."""
import argparse

from app.api.routes import store
from app.core.storage import read_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site_id")
    args = parser.parse_args()
    path = store.site_path(args.site_id)
    print({
        "site_id": args.site_id,
        "pages": len(read_json(path / "pages.json", [])),
        "documents": len(read_json(path / "documents.json", [])),
        "chunks": len(read_json(path / "index" / "chunks.json", [])),
        "progress": read_json(path / "crawl_progress.json", {}),
    })


if __name__ == "__main__":
    main()
