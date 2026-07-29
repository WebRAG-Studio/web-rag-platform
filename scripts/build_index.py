"""Rebuild one site's index from its already extracted local records."""
import argparse

from app.api.routes import store
from app.retrieval.engine import build_index


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site_id")
    args = parser.parse_args()
    print(build_index(store.site_path(args.site_id)))


if __name__ == "__main__":
    main()
