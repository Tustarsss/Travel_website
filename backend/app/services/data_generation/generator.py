"""Synthetic data generation utilities that satisfy project constraints."""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np
from faker import Faker

from app.models.enums import (
    BuildingCategory,
    DiaryMediaType,
    DiaryStatus,
    FacilityCategory,
    RegionType,
    TransportMode,
)

faker = Faker("zh_CN")
faker = Faker("zh_CN")

MIN_REGION_COUNT = 200
BUILDINGS_PER_REGION = (20, 28)
FACILITIES_PER_REGION = (10, 14)
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
BUILDING_CHOICES = list(BuildingCategory)
FACILITY_CHOICES = list(FacilityCategory)
MEDIA_TYPES = list(DiaryMediaType)
REGION_TYPES = list(RegionType)


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


def _random_offset() -> tuple[float, float]:
    return (random.uniform(-0.02, 0.02), random.uniform(-0.02, 0.02))


def _city_pool() -> Sequence[str]:
    return [
        "北京",
        "上海",
        "广州",
        "深圳",
        "杭州",
        "成都",
        "重庆",
        "武汉",
        "西安",
        "南京",
    ]


def _pick_city(idx: int) -> str:
    cities = _city_pool()
    return cities[idx % len(cities)]


def _region_name(region_type: RegionType, idx: int) -> str:
    suffix = f"-{idx:03d}"
    if region_type is RegionType.SCENIC:
        return f"{faker.city_name()}景区{suffix}"
    return f"{faker.city_name()}大学{suffix}"


def _build_graph(node_coords: List[tuple[int, float, float]], modes: List[TransportMode]) -> List[dict]:
    if len(node_coords) < 2:
        return []

    edges: List[dict] = []
    seen_pairs: set[tuple[int, int]] = set()
    for idx, (node_id, lat, lon) in enumerate(node_coords):
        distances: List[tuple[float, tuple[int, float, float]]] = []
        for other in node_coords:
            if other[0] == node_id:
                continue
            distance = math.dist((lat, lon), (other[1], other[2])) * 1000
            distances.append((distance, other))
        distances.sort(key=lambda item: item[0])
        for distance, (target_id, t_lat, t_lon) in distances[: min(4, len(distances))]:
            pair_key = tuple(sorted((node_id, target_id)))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            ideal_speed = random.uniform(0.8, 1.8)
            congestion = random.uniform(0.3, 1.0)
            payload = {
                "distance": round(distance, 2),
                "ideal_speed": round(ideal_speed, 2),
                "congestion": round(congestion, 2),
                "transport_modes": [mode.value for mode in modes],
            }
            edges.append(
                {
                    "id": None,
                    "start_node_id": node_id,
                    "end_node_id": target_id,
                    **payload,
                }
            )
            edges.append(
                {
                    "id": None,
                    "start_node_id": target_id,
                    "end_node_id": node_id,
                    **payload,
                }
            )
    return edges


def generate_dataset(output_dir: Path, seed: int | None = None) -> Dict[str, List[dict]]:
    """Generate synthetic dataset and write individual JSON files."""

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

    print("[generator] Generating regions, buildings, facilities, and graph edges...")
    for idx in range(MIN_REGION_COUNT):
        region_type = random.choice(REGION_TYPES)
        region_id = counters.region
        counters.region += 1
        popularity = random.randint(30, 100)
        rating = round(random.uniform(2.5, 5.0), 1)
        base_lat = float(faker.latitude())
        base_lon = float(faker.longitude())
        region_lat = round(base_lat, 6)
        region_lon = round(base_lon, 6)
        region = {
            "id": region_id,
            "name": _region_name(region_type, region_id),
            "type": region_type.value,
            "popularity": popularity,
            "rating": rating,
            "description": faker.text(max_nb_chars=120),
            "city": _pick_city(idx),
            "latitude": region_lat,
            "longitude": region_lon,
        }
        dataset["regions"].append(region)

        node_coordinates: List[tuple[int, float, float]] = []

        building_count = random.randint(*BUILDINGS_PER_REGION)
        for _ in range(building_count):
            lat_off, lon_off = _random_offset()
            building = {
                "id": counters.building,
                "region_id": region_id,
                "name": faker.street_name(),
                "category": random.choice(BUILDING_CHOICES).value,
                "latitude": round(base_lat + lat_off, 6),
                "longitude": round(base_lon + lon_off, 6),
            }
            dataset["buildings"].append(building)
            node = {
                "id": counters.node,
                "region_id": region_id,
                "name": building["name"],
                "latitude": building["latitude"],
                "longitude": building["longitude"],
                "building_id": building["id"],
                "facility_id": None,
                "is_virtual": False,
            }
            dataset["graph_nodes"].append(node)
            node_coordinates.append((counters.node, node["latitude"], node["longitude"]))
            counters.node += 1
            counters.building += 1

        facility_count = random.randint(*FACILITIES_PER_REGION)
        for _ in range(facility_count):
            lat_off, lon_off = _random_offset()
            facility = {
                "id": counters.facility,
                "region_id": region_id,
                "name": faker.company_suffix() + faker.street_suffix(),
                "category": random.choice(FACILITY_CHOICES).value,
                "latitude": round(base_lat + lat_off, 6),
                "longitude": round(base_lon + lon_off, 6),
            }
            dataset["facilities"].append(facility)
            node = {
                "id": counters.node,
                "region_id": region_id,
                "name": facility["name"],
                "latitude": facility["latitude"],
                "longitude": facility["longitude"],
                "building_id": None,
                "facility_id": facility["id"],
                "is_virtual": False,
            }
            dataset["graph_nodes"].append(node)
            node_coordinates.append((counters.node, node["latitude"], node["longitude"]))
            counters.node += 1
            counters.facility += 1

        modes = TRANSPORT_MODE_MAP[region_type]
        edges = _build_graph(node_coordinates, modes)
        for edge in edges:
            edge["id"] = counters.edge
            edge["region_id"] = region_id
            dataset["graph_edges"].append(edge)
            counters.edge += 1

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