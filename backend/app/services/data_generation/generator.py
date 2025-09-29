"""Data generation with real map data integration that satisfy project constraints."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np
from faker import Faker

from app.models.enums import (
    DiaryMediaType,
    DiaryStatus,
    RegionType,
    TransportMode,
)
from .map_crawler import (
    build_graph_from_coordinates,
    convert_osm_graph_to_components,
    get_osm_data_for_location,
)
from .osm_adapter import AdaptedRegionData, RealDataUnavailableError, adapt_osm_payload

faker = Faker("zh_CN")

MIN_REGION_COUNT = 5
BUILDINGS_PER_REGION = (5, 12)
FACILITIES_PER_REGION = (3, 6)
USERS_COUNT = 25
DIARIES_PER_USER = (2, 5)
TRANSPORT_MODE_MAP = {
    RegionType.SCENIC: [TransportMode.WALK, TransportMode.ELECTRIC_CART],
    RegionType.CAMPUS: [TransportMode.WALK, TransportMode.BIKE],
}
INTEREST_TAGS = [
    "自然",
    "历史",
    "科教",
    "美食",
    "艺术",
    "亲子",
    "摄影",
    "运动",
]
MEDIA_TYPES = list(DiaryMediaType)


@dataclass
class Counters:
    region: int = 1
    building: int = 1
    facility: int = 1
    node: int = 1
    edge: int = 1
    user: int = 1
    diary: int = 1
    rating: int = 1


def _city_pool() -> Sequence[str]:
    return [
        "北京", "上海", "广州", "深圳", "杭州", 
        "成都", "重庆", "武汉", "西安", "南京",
        "苏州", "天津", "青岛", "大连", "厦门"
    ]


def _pick_city(idx: int) -> str:
    cities = _city_pool()
    return cities[idx % len(cities)]


def _region_name(region_type: RegionType, idx: int) -> str:
    suffix = f"-{idx:03d}"
    if region_type is RegionType.SCENIC:
        return f"{faker.city_name()}景区{suffix}"
    return f"{faker.city_name()}大学{suffix}"


def _derive_region_center(adapted: AdaptedRegionData) -> tuple[float, float]:
    coords: list[tuple[float, float]] = []
    for item in adapted.buildings:
        coords.append((float(item["latitude"]), float(item["longitude"])))
    for item in adapted.facilities:
        coords.append((float(item["latitude"]), float(item["longitude"])))

    if not coords:
        raise RealDataUnavailableError("无法从真实数据中推导区域中心坐标。")

    lat = sum(point[0] for point in coords) / len(coords)
    lon = sum(point[1] for point in coords) / len(coords)
    return round(lat, 6), round(lon, 6)


def generate_dataset_with_real_map_data(
    output_dir: Path, seed: int | None = None, region_target: int | None = None
) -> Dict[str, List[dict]]:
    """Generate dataset with only real map data from OSM."""
    
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
        Faker.seed(seed)

    counters = Counters()
    dataset: Dict[str, List[dict]] = {
        "regions": [],
        "buildings": [],
        "facilities": [],
        "graph_nodes": [],
        "graph_edges": [],
        "users": [],
        "diaries": [],
        "diary_ratings": [],
    }

    print("[generator] Generating regions with only real map data...")

    known_locations = [
        ("西湖景区", ["西湖景区", "West Lake Scenic Area, Hangzhou"], RegionType.SCENIC),
        ("清华大学", ["清华大学", "Tsinghua University, Beijing"], RegionType.CAMPUS),
        ("北京大学", ["北京大学", "Peking University, Beijing"], RegionType.CAMPUS),
        ("中山大学", ["中山大学", "Sun Yat-sen University, Guangzhou"], RegionType.CAMPUS),
    ("苏州大学", ["苏州大学", "Soochow University"], RegionType.CAMPUS),
        ("北京颐和园", ["颐和园", "Summer Palace, Beijing"], RegionType.SCENIC),
        ("上海外滩", ["上海外滩", "The Bund, Shanghai"], RegionType.SCENIC),
        ("成都宽窄巷子", ["宽窄巷子", "Kuanzhai Alley, Chengdu"], RegionType.SCENIC),
        ("西安大雁塔", ["大雁塔", "Giant Wild Goose Pagoda, Xi'an"], RegionType.SCENIC),
        ("杭州灵隐寺", ["灵隐寺", "Lingyin Temple, Hangzhou"], RegionType.SCENIC),
    ]

    default_target = min(MIN_REGION_COUNT, len(known_locations))
    target_region_count = max(1, region_target if region_target is not None else default_target)

    if target_region_count > len(known_locations):
        raise RealDataUnavailableError(
            f"需要 {target_region_count} 个真实区域，但仅配置 {len(known_locations)} 个地点。请扩充地点列表。"
        )

    for idx in range(target_region_count):
        region_id = counters.region
        display_name, queries, region_type = known_locations[idx]

        osm_data = None
        for query in queries:
            osm_data = get_osm_data_for_location(query)
            if osm_data:
                break
        if osm_data is None:
            raise RealDataUnavailableError("未能获取 OSM 数据。", location=display_name)

        min_buildings = random.randint(*BUILDINGS_PER_REGION)
        min_facilities = random.randint(*FACILITIES_PER_REGION)
        adapted: AdaptedRegionData = adapt_osm_payload(
            osm_data,
            region_id,
            region_type,
            min_buildings,
            min_facilities,
            location=display_name,
        )

        bounds = osm_data.get("bounds")
        if bounds is not None and len(bounds) == 4:
            min_lat, min_lon, max_lat, max_lon = bounds
            center_lat = round((min_lat + max_lat) / 2, 6)
            center_lon = round((min_lon + max_lon) / 2, 6)
        else:
            center_lat, center_lon = _derive_region_center(adapted)

        popularity = random.randint(30, 100)
        rating = round(random.uniform(2.5, 5.0), 1)
        region = {
            "id": region_id,
            "name": display_name,
            "type": region_type.value,
            "popularity": popularity,
            "rating": rating,
            "description": faker.text(max_nb_chars=120),
            "city": _pick_city(idx),
            "latitude": center_lat,
            "longitude": center_lon,
        }
        dataset["regions"].append(region)

        for building in adapted.buildings:
            new_building = {
                **building,
                "id": counters.building,
                "region_id": region_id,
            }
            dataset["buildings"].append(new_building)

            counters.building += 1

        for facility in adapted.facilities:
            new_facility = {
                **facility,
                "id": counters.facility,
                "region_id": region_id,
            }
            dataset["facilities"].append(new_facility)
            counters.facility += 1

        graph_nodes_payload, graph_edges_payload = convert_osm_graph_to_components(
            osm_data.get("graph"), region_type
        )

        if len(graph_nodes_payload) < 2 or not graph_edges_payload:
            fallback_coordinates: List[tuple[float, float]] = [
                (float(item["latitude"]), float(item["longitude"]))
                for item in [*adapted.buildings, *adapted.facilities]
            ]
            graph_nodes_payload, graph_edges_payload = build_graph_from_coordinates(
                fallback_coordinates,
                region_type,
            )

        if len(graph_nodes_payload) < 2 or not graph_edges_payload:
            raise RealDataUnavailableError("无法构建足够的路径路网节点。", location=display_name)

        node_id_lookup: List[int] = []
        for node_index, node_payload in enumerate(graph_nodes_payload):
            node_id = counters.node
            counters.node += 1
            dataset["graph_nodes"].append(
                {
                    "id": node_id,
                    "region_id": region_id,
                    "name": node_payload.get("name")
                    or f"路口-{region_id}-{node_index + 1}",
                    "latitude": node_payload["latitude"],
                    "longitude": node_payload["longitude"],
                    "building_id": None,
                    "facility_id": None,
                    "is_virtual": False,
                }
            )
            node_id_lookup.append(node_id)

        for edge_payload in graph_edges_payload:
            dataset["graph_edges"].append(
                {
                    "id": counters.edge,
                    "region_id": region_id,
                    "start_node_id": node_id_lookup[edge_payload["source_index"]],
                    "end_node_id": node_id_lookup[edge_payload["target_index"]],
                    "distance": edge_payload["distance"],
                    "ideal_speed": edge_payload["ideal_speed"],
                    "congestion": edge_payload["congestion"],
                    "transport_modes": edge_payload["transport_modes"],
                }
            )
            counters.edge += 1
        counters.region += 1

    if len(dataset["regions"]) < target_region_count:
        raise RealDataUnavailableError(
            f"仅生成 {len(dataset['regions'])} 个真实区域，未达到要求的 {target_region_count} 个。"
        )

    print(f"[generator] total regions ready: {len(dataset['regions'])}")
    print("[generator] Generating users and diaries...")
    interest_pool = list(INTEREST_TAGS)
    for _ in range(USERS_COUNT):
        user_id = counters.user
        counters.user += 1
        interests = random.sample(interest_pool, k=random.randint(2, 4))
        dataset["users"].append(
            {
                "id": user_id,
                "username": faker.user_name() + str(random.randint(100, 999)),
                "display_name": faker.name(),
                "email": faker.email(),
                "interests": interests,
            }
        )

        diaries_to_create = random.randint(*DIARIES_PER_USER)
        for _ in range(diaries_to_create):
            region = random.choice(dataset["regions"])
            diary_id = counters.diary
            counters.diary += 1
            max_media = min(3, len(MEDIA_TYPES))
            media_count = random.randint(1, max_media)
            media_types = random.sample(MEDIA_TYPES, k=media_count)
            dataset["diaries"].append(
                {
                    "id": diary_id,
                    "user_id": user_id,
                    "region_id": region["id"],
                    "title": faker.sentence(nb_words=6),
                    "summary": faker.sentence(nb_words=12),
                    "content": "\n".join(faker.paragraphs(nb=random.randint(3, 6))),
                    "compressed_content": None,
                    "media_urls": [faker.image_url() for _ in range(media_count)],
                    "media_types": [media_type.value for media_type in media_types],
                    "tags": random.sample(interest_pool, k=random.randint(1, 3)),
                    "popularity": random.randint(10, 500),
                    "rating": round(random.uniform(3.0, 5.0), 1),
                    "ratings_count": random.randint(1, 120),
                    "status": DiaryStatus.PUBLISHED.value,
                }
            )

            rating_count = random.randint(2, 6)
            for _ in range(rating_count):
                dataset["diary_ratings"].append(
                    {
                        "id": counters.rating,
                        "diary_id": diary_id,
                        "user_id": random.randint(1, USERS_COUNT),
                        "score": random.randint(3, 5),
                        "comment": faker.sentence(nb_words=10),
                    }
                )
                counters.rating += 1

    print("[generator] Writing JSON files to", str(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    for key, records in dataset.items():
        path = output_dir / f"{key}.json"
        path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(
        "[generator] Dataset generation complete",
        f"regions={len(dataset['regions'])}",
        f"buildings={len(dataset['buildings'])}",
        f"facilities={len(dataset['facilities'])}",
        f"edges={len(dataset['graph_edges'])}",
        f"users={len(dataset['users'])}",
        f"diaries={len(dataset['diaries'])}",
    )

    return dataset


def generate_dataset(
    output_dir: Path, seed: int | None = None, region_target: int | None = None
) -> Dict[str, List[dict]]:
    """Generate synthetic dataset and write individual JSON files."""
    return generate_dataset_with_real_map_data(output_dir, seed, region_target)