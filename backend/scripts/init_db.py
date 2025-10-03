"""One-shot database initialization helper.

This script creates the SQLite schema, loads generated map data when
available, and seeds a small set of demo diaries so the Travel Website
backend can run locally without bulky fixtures.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
from typing import Any, Callable, Iterable, Sequence

from sqlalchemy import delete, func, select  # type: ignore[import-untyped]
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore[import-untyped]

from app.core.db import get_session_maker, init_db_async
from app.models.diaries import Diary, DiaryRating
from app.models.enums import (
    BuildingCategory,
    DiaryMediaType,
    DiaryStatus,
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


async def _get_or_create_user(
    session: AsyncSession,
    *,
    username: str,
    display_name: str,
    email: str,
    interests: list[str],
) -> User:
    existing = await session.scalar(select(User).where(User.username == username))
    if existing:
        return existing

    user = User(
        username=username,
        display_name=display_name,
        email=email,
        interests=interests,
    )
    session.add(user)
    await session.flush()
    return user

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


async def seed_sample_content(session: AsyncSession, *, keep_existing: bool) -> None:
    existing_diaries = await session.scalar(select(func.count(Diary.id)))
    if existing_diaries and keep_existing:
        print("[init-db] Existing diaries detected; skipping sample diary seed.")
        return

    if not keep_existing:
        print("[init-db] Clearing diary-related tables before seeding samples...")
        await _clear_existing_data(session, (DiaryRating, Diary))

    regions_result = await session.execute(select(Region).order_by(Region.id))
    regions = list(regions_result.scalars().all())

    if not regions:
        print("[init-db] No regions available; creating fallback demo regions.")
        fallback_regions = [
            Region(
                name="West Lake Scenic Area",
                type=RegionType.SCENIC,
                popularity=85,
                rating=4.6,
                description="Famous scenic area in Hangzhou with beautiful lakeside views.",
                city="Hangzhou",
                latitude=30.241,
                longitude=120.150,
            ),
            Region(
                name="Tsinghua University",
                type=RegionType.CAMPUS,
                popularity=92,
                rating=4.8,
                description="Historic campus known for academia and architecture.",
                city="Beijing",
                latitude=40.003,
                longitude=116.326,
            ),
        ]
        session.add_all(fallback_regions)
        await session.flush()
        regions = fallback_regions

    sample_users = [
        {
            "username": "traveler_anna",
            "display_name": "Anna Wang",
            "email": "anna@example.com",
            "interests": ["艺术", "美食"],
        },
        {
            "username": "explorer_li",
            "display_name": "Li Zhang",
            "email": "li.zhang@example.com",
            "interests": ["自然", "运动"],
        },
    ]

    users: list[User] = []
    for spec in sample_users:
        user = await _get_or_create_user(session, **spec)
        users.append(user)

    primary_region = regions[0]
    secondary_region = regions[1] if len(regions) > 1 else regions[0]

    diaries = [
        Diary(
            user_id=users[0].id,
            region_id=primary_region.id,
            title="西湖慢行一日游",
            summary="漫步苏堤与断桥，乘船赏雷峰塔的傍晚余晖。",
            content="清晨从断桥出发，骑行绕湖一圈，中午品尝楼外楼的西湖醋鱼...",
            compressed_content=None,
            is_compressed=False,
            media_urls=["https://example.com/photos/westlake-sunset.jpg"],
            media_types=[DiaryMediaType.IMAGE],
            tags=["自然", "美食"],
            popularity=128,
            rating=4.7,
            ratings_count=2,
            comments_count=0,
            status=DiaryStatus.PUBLISHED,
        ),
        Diary(
            user_id=users[1].id,
            region_id=secondary_region.id,
            title="清华校园骑行路线分享",
            summary="骑行清华大学园区，探访荷塘月色和清华学堂。",
            content="下午从西门进入校园，沿主干道骑行，经过二校门、清华学堂...",
            compressed_content=None,
            is_compressed=False,
            media_urls=["https://example.com/photos/tsinghua-gate.png"],
            media_types=[DiaryMediaType.IMAGE],
            tags=["校园", "运动"],
            popularity=86,
            rating=4.5,
            ratings_count=1,
            comments_count=0,
            status=DiaryStatus.PUBLISHED,
        ),
        Diary(
            user_id=users[0].id,
            region_id=secondary_region.id,
            title="清华食堂探店打卡",
            summary="盘点最受欢迎的清华食堂美食，含深夜小吃推荐。",
            content="午餐在紫荆餐厅，推荐宫保鸡丁和现做豆腐；晚上在熙春园...",
            compressed_content=None,
            is_compressed=False,
            media_urls=[
                "https://example.com/photos/tsinghua-canteen.jpg",
                "https://example.com/photos/late-night-snack.jpg",
            ],
            media_types=[DiaryMediaType.IMAGE, DiaryMediaType.IMAGE],
            tags=["美食", "校园"],
            popularity=64,
            rating=4.2,
            ratings_count=0,
            comments_count=0,
            status=DiaryStatus.PUBLISHED,
        ),
    ]

    session.add_all(diaries)
    await session.flush()

    ratings = [
        DiaryRating(
            diary_id=diaries[0].id,
            user_id=users[1].id,
            score=5,
            comment="景色实在太美了，路线安排也很详细！",
        ),
        DiaryRating(
            diary_id=diaries[1].id,
            user_id=users[0].id,
            score=4,
            comment="校园骑行路线很实用，期待更多照片。",
        ),
    ]
    session.add_all(ratings)

    await session.commit()
    print("[init-db] Sample diaries inserted successfully.")


async def initialize_database(keep_existing: bool, dataset_dir: Path | None = None) -> None:
    print("[init-db] Ensuring database schema exists...")
    await init_db_async()

    print("[init-db] Ensuring auxiliary directories...")
    ensure_directories()

    maker = get_session_maker()
    async with maker() as session:
        await import_generated_map_data(
            session,
            dataset_dir or GENERATED_DATA_DIR,
            keep_existing=keep_existing,
        )
        await seed_sample_content(session, keep_existing=keep_existing)

    print("[init-db] Database initialization complete.")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Initialize the SQLite schema, import generated map data, and seed demo diaries.",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Keep existing rows instead of dropping them before seeding sample data.",
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
