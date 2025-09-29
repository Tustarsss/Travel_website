"""Generate dataset for the travel system with real map data when available."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.services.data_generation.generator import generate_dataset


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
        f"edges={len(dataset['graph_edges'])}",
        f"users={len(dataset['users'])}",
        f"diaries={len(dataset['diaries'])}",
    )


if __name__ == "__main__":
    main()
