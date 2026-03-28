from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def sync_web_dist_to_docs(dist_dir: str | Path, docs_dir: str | Path) -> None:
    dist_path = Path(dist_dir)
    docs_path = Path(docs_dir)
    index_path = dist_path / "index.html"
    assets_path = dist_path / "assets"

    if not index_path.exists():
        raise FileNotFoundError(f"Missing frontend entrypoint: {index_path}")

    docs_path.mkdir(parents=True, exist_ok=True)
    shutil.copy2(index_path, docs_path / "index.html")

    target_assets_path = docs_path / "assets"
    if target_assets_path.exists():
        shutil.rmtree(target_assets_path)
    if assets_path.exists():
        shutil.copytree(assets_path, target_assets_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync Vite build output into docs/ without touching RSS assets."
    )
    parser.add_argument("dist_dir")
    parser.add_argument("docs_dir")
    args = parser.parse_args()
    sync_web_dist_to_docs(args.dist_dir, args.docs_dir)


if __name__ == "__main__":
    main()
