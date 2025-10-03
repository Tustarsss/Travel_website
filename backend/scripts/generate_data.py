"""Generate dataset for the travel system with real map data when available."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.services.data_generation.generator import generate_dataset
from scripts.init_db import initialize_database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic travel datasets")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/generated"),
        help="Directory where JSON files will be written.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducibility.",
    )
    parser.add_argument(
        "--regions",
        type=int,
        default=None,
        help="Optional target number of regions to generate (defaults to project minimum).",
    )
    parser.add_argument(
        "--populate-db",
        action="store_true",
        help="After generating JSON files, import them into the database using init_db logic.",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Forwarded to database initialization when --populate-db is set.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print("[generate-data] Starting data generation")
    dataset = generate_dataset(args.output, seed=args.seed, region_target=args.regions)
    print(
        "[generate-data] Data generation finished",
        f"regions={len(dataset['regions'])}",
        f"buildings={len(dataset['buildings'])}",
        f"facilities={len(dataset['facilities'])}",
        f"graph_nodes={len(dataset['graph_nodes'])}",
        f"graph_edges={len(dataset['graph_edges'])}",
    )

    if args.populate_db:
        print("[generate-data] Importing generated dataset into database...")
        asyncio.run(
            initialize_database(
                keep_existing=args.keep_existing,
                dataset_dir=args.output,
            )
        )
        print("[generate-data] Database population finished.")


if __name__ == "__main__":
    main()
