"""One-shot database initialization helper.

This script creates the SQLite schema, loads generated map data when
available, and prepares required directories so the Travel Website
backend can run locally without bulky fixtures.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
from typing import Any, Callable, Iterable, Sequence

from sqlalchemy import delete, func, select, text, update  # type: ignore[import-untyped]
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore[import-untyped]

from app.core.db import get_session_maker, init_db_async
from fastapi_users.password import PasswordHelper
from app.models.enums import (
    BuildingCategory,
    FacilityCategory,
    RegionType,
    TransportMode,
)
from app.models.graph import GraphEdge, GraphNode
from app.models.locations import Building, Facility, Region
from app.models.users import User

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

GENERATED_DATA_DIR = PROJECT_ROOT / "data" / "generated"

DEFAULT_MIGRATION_PASSWORD = "TravelTemp123!"
_pwd_helper = PasswordHelper()
DEFAULT_MIGRATION_PASSWORD_HASH = _pwd_helper.hash(DEFAULT_MIGRATION_PASSWORD)

REQUIRED_DATASET_KEYS = (
    "regions",
    "buildings",
    "facilities",
    "graph_nodes",
    "graph_edges",
)


def _dataset_files_present(dataset_dir: Path) -> tuple[bool, list[str]]:
    missing = [key for key in REQUIRED_DATASET_KEYS if not (dataset_dir / f"{key}.json").exists()]
    return (len(missing) == 0, missing)


def _load_json_records(path: Path) -> list[dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"Missing dataset file: {path}") from None


def _coerce_enum(enum_cls: Callable[[str], Any], value: str, fallback: Any) -> Any:
    try:
        return enum_cls(value)
    except ValueError:
        return fallback


async def _bulk_insert_models(
    session: AsyncSession,
    model_cls,
    records: Iterable[dict[str, Any]],
    *,
    chunk_size: int = 1000,
) -> None:
    buffer = []
    inserted = False
    for record in records:
        buffer.append(model_cls(**record))
        if len(buffer) >= chunk_size:
            session.add_all(buffer)
            await session.flush()
            session.expunge_all()
            buffer.clear()
            inserted = True

    if buffer:
        session.add_all(buffer)
        await session.flush()
        session.expunge_all()
        inserted = True

    if inserted:
        await session.commit()


def _prepare_region_records(records: list[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for record in records:
        yield {
            "id": record.get("id"),
            "name": record.get("name"),
            "type": _coerce_enum(RegionType, record.get("type", RegionType.SCENIC.value), RegionType.SCENIC),
            "popularity": int(record.get("popularity", 0)),
            "rating": float(record.get("rating", 0.0)),
            "description": record.get("description"),
            "city": record.get("city"),
            "latitude": record.get("latitude"),
            "longitude": record.get("longitude"),
        }


def _prepare_building_records(records: list[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for record in records:
        category = _coerce_enum(BuildingCategory, record.get("category", BuildingCategory.OTHER.value), BuildingCategory.OTHER)
        yield {
            "id": record.get("id"),
            "region_id": record.get("region_id"),
            "name": record.get("name"),
            "category": category,
            "latitude": float(record.get("latitude", 0.0)),
            "longitude": float(record.get("longitude", 0.0)),
        }


def _prepare_facility_records(records: list[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for record in records:
        category = _coerce_enum(FacilityCategory, record.get("category", FacilityCategory.SERVICE.value), FacilityCategory.SERVICE)
        yield {
            "id": record.get("id"),
            "region_id": record.get("region_id"),
            "name": record.get("name"),
            "category": category,
            "latitude": float(record.get("latitude", 0.0)),
            "longitude": float(record.get("longitude", 0.0)),
        }


def _prepare_graph_node_records(records: list[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for record in records:
        yield {
            "id": record.get("id"),
            "region_id": record.get("region_id"),
            "name": record.get("name"),
            "latitude": float(record.get("latitude", 0.0)),
            "longitude": float(record.get("longitude", 0.0)),
            "building_id": record.get("building_id"),
            "facility_id": record.get("facility_id"),
            "is_virtual": bool(record.get("is_virtual", False)),
        }


def _prepare_graph_edge_records(records: list[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for record in records:
        modes = [
            _coerce_enum(TransportMode, mode, TransportMode.WALK)
            for mode in record.get("transport_modes", [TransportMode.WALK.value])
        ]
        yield {
            "id": record.get("id"),
            "region_id": record.get("region_id"),
            "start_node_id": record.get("start_node_id"),
            "end_node_id": record.get("end_node_id"),
            "distance": float(record.get("distance", 0.0)),
            "ideal_speed": float(record.get("ideal_speed", 0.0)),
            "congestion": float(record.get("congestion", 0.0)),
            "transport_modes": modes,
        }


async def import_generated_map_data(
    session: AsyncSession,
    dataset_dir: Path,
    *,
    keep_existing: bool,
) -> bool:
    dataset_dir = dataset_dir.resolve()
    if not dataset_dir.exists():
        print(f"[init-db] Dataset directory {dataset_dir} not found; skipping real map import.")
        return False

    available, missing = _dataset_files_present(dataset_dir)
    if not available:
        print("[init-db] Dataset missing required files; skipping map import:", ", ".join(missing))
        return False

    region_count = await session.scalar(select(func.count(Region.id)))
    if keep_existing and region_count:
        print("[init-db] Existing regions detected and --keep-existing provided; skipping map import.")
        return True

    if not keep_existing:
        print("[init-db] Clearing existing map data before import...")
        await _clear_existing_data(
            session,
            (
                GraphEdge,
                GraphNode,
                Facility,
                Building,
                Region,
            ),
        )

    print(f"[init-db] Importing generated map data from {dataset_dir}...")
    regions = _load_json_records(dataset_dir / "regions.json")
    buildings = _load_json_records(dataset_dir / "buildings.json")
    facilities = _load_json_records(dataset_dir / "facilities.json")
    graph_nodes = _load_json_records(dataset_dir / "graph_nodes.json")
    graph_edges = _load_json_records(dataset_dir / "graph_edges.json")

    await _bulk_insert_models(session, Region, _prepare_region_records(regions))
    await _bulk_insert_models(session, Building, _prepare_building_records(buildings))
    await _bulk_insert_models(session, Facility, _prepare_facility_records(facilities))
    await _bulk_insert_models(session, GraphNode, _prepare_graph_node_records(graph_nodes), chunk_size=2000)
    await _bulk_insert_models(session, GraphEdge, _prepare_graph_edge_records(graph_edges), chunk_size=4000)

    print(
        "[init-db] Map data import complete",
        f"regions={len(regions)}",
        f"buildings={len(buildings)}",
        f"facilities={len(facilities)}",
        f"graph_nodes={len(graph_nodes)}",
        f"graph_edges={len(graph_edges)}",
    )
    return True
async def _ensure_user_schema(session: AsyncSession) -> None:
    """Add newly required user columns when initializing existing databases."""

    result = await session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    )
    table_exists = result.scalar() is not None
    if not table_exists:
        return

    pragma_result = await session.execute(text("PRAGMA table_info(users)"))
    columns = {row[1] for row in pragma_result}

    if "hashed_password" not in columns:
        print("[init-db] Adding missing 'hashed_password' column to users table...")
        await session.execute(text("ALTER TABLE users ADD COLUMN hashed_password TEXT"))
        await session.commit()

    if "is_active" not in columns:
        print("[init-db] Adding missing 'is_active' column to users table...")
        await session.execute(
            text("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
        )
        await session.commit()

    if "last_login_at" not in columns:
        print("[init-db] Adding missing 'last_login_at' column to users table...")
        await session.execute(text("ALTER TABLE users ADD COLUMN last_login_at DATETIME"))
        await session.commit()

    await session.execute(
        update(User)
        .where((User.hashed_password.is_(None)) | (User.hashed_password == ""))
        .values(hashed_password=DEFAULT_MIGRATION_PASSWORD_HASH)
    )
    await session.commit()

    await session.execute(
        update(User)
        .where(User.is_active.is_(None))
        .values(is_active=True)
    )
    await session.commit()

def ensure_directories() -> None:
    """Create directories that the application expects to exist."""

    storage_root = PROJECT_ROOT / "storage"
    indexes_root = PROJECT_ROOT / "indexes"
    tiles_root = indexes_root / "map_tiles"

    for path in (storage_root, indexes_root, tiles_root):
        path.mkdir(parents=True, exist_ok=True)

    for filename in (indexes_root / "spatial.idx", indexes_root / "fulltext.idx"):
        if not filename.exists():
            filename.write_text("", encoding="utf-8")


async def _clear_existing_data(session: AsyncSession, models: Sequence[type]) -> None:
    for model in models:
        await session.execute(delete(model))
    await session.commit()


async def initialize_database(keep_existing: bool, dataset_dir: Path | None = None) -> None:
    print("[init-db] Ensuring database schema exists...")
    await init_db_async()

    print("[init-db] Ensuring auxiliary directories...")
    ensure_directories()

    maker = get_session_maker()
    async with maker() as session:
        await _ensure_user_schema(session)
        await import_generated_map_data(
            session,
            dataset_dir or GENERATED_DATA_DIR,
            keep_existing=keep_existing,
        )

    print("[init-db] Database initialization complete.")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Initialize the SQLite schema, import generated map data, and seed demo diaries.",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
    help="Keep existing rows instead of dropping them before importing new data.",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=GENERATED_DATA_DIR,
        help="Path to generated map dataset directory (defaults to data/generated).",
    )
    args = parser.parse_args()

    asyncio.run(initialize_database(args.keep_existing, dataset_dir=args.dataset_dir))


if __name__ == "__main__":
    main()
