"""Data generation with real map data integration that satisfy project constraints."""

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
    RegionType,
    TransportMode,
)
from .map_crawler import (
    convert_osm_graph_to_components,
    get_osm_data_for_location,
)
from .osm_adapter import AdaptedRegionData, RealDataUnavailableError, adapt_osm_payload

faker = Faker("zh_CN")

MIN_REGION_COUNT = 5
BUILDINGS_PER_REGION = (5, 12)
FACILITIES_PER_REGION = (3, 6)
TRANSPORT_MODE_MAP = {
    RegionType.SCENIC: [TransportMode.WALK, TransportMode.ELECTRIC_CART],
    RegionType.CAMPUS: [TransportMode.WALK, TransportMode.BIKE],
}
CONNECTOR_NEAREST_JUNCTIONS = 3
CONNECTOR_MIN_DISTANCE_METERS = 8.0
CONNECTOR_CONGESTION = 0.9


def _transport_mode_values(region_type: RegionType) -> List[str]:
    modes = TRANSPORT_MODE_MAP.get(region_type)
    if not modes:
        return [TransportMode.WALK.value]
    return [mode.value for mode in modes]


def _connector_ideal_speed(region_type: RegionType) -> float:
    if region_type is RegionType.CAMPUS:
        return 2.8  # mixed walk/bike bridge speed (m/s)
    if region_type is RegionType.SCENIC:
        return 1.6  # pedestrian-friendly boardwalk speed (m/s)
    return 1.5


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Approximate great-circle distance between two coordinates."""

    radius = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


@dataclass
class Counters:
    region: int = 1
    building: int = 1
    facility: int = 1
    node: int = 1
    edge: int = 1


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

    generated_regions = 0
    location_index = 0

    if target_region_count > len(known_locations):
        raise RealDataUnavailableError(
            f"需要 {target_region_count} 个真实区域，但仅配置 {len(known_locations)} 个地点。请扩充地点列表。"
        )

    while generated_regions < target_region_count and location_index < len(known_locations):
        display_name, queries, region_type = known_locations[location_index]
        location_index += 1

        try:
            region_id = counters.region

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
                "city": _pick_city(generated_regions),
                "latitude": center_lat,
                "longitude": center_lon,
            }
            dataset["regions"].append(region)

            region_buildings: list[dict] = []
            for building in adapted.buildings:
                new_building = {
                    **building,
                    "id": counters.building,
                    "region_id": region_id,
                }
                dataset["buildings"].append(new_building)
                region_buildings.append(new_building)
                counters.building += 1

            region_facilities: list[dict] = []
            for facility in adapted.facilities:
                new_facility = {
                    **facility,
                    "id": counters.facility,
                    "region_id": region_id,
                }
                dataset["facilities"].append(new_facility)
                region_facilities.append(new_facility)
                counters.facility += 1

            graph_nodes_payload, graph_edges_payload = convert_osm_graph_to_components(
                osm_data.get("graph"), region_type
            )

            if len(graph_nodes_payload) < 2 or not graph_edges_payload:
                raise RealDataUnavailableError("OSM 数据缺少足够的路网节点。", location=display_name)

            node_id_lookup: List[int] = []
            junction_nodes: list[dict] = []
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
                junction_nodes.append(
                    {
                        "id": node_id,
                        "latitude": float(node_payload["latitude"]),
                        "longitude": float(node_payload["longitude"]),
                    }
                )

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

            _attach_points_to_graph(
                dataset,
                counters,
                region_id=region_id,
                region_type=region_type,
                location_label=display_name,
                junctions=junction_nodes,
                points=region_buildings,
                kind="building",
            )

            _attach_points_to_graph(
                dataset,
                counters,
                region_id=region_id,
                region_type=region_type,
                location_label=display_name,
                junctions=junction_nodes,
                points=region_facilities,
                kind="facility",
            )

            generated_regions += 1

        except RealDataUnavailableError as exc:
            print(f"[generator] 跳过 {display_name}: {exc}")
            continue

    if generated_regions < target_region_count:
        raise RealDataUnavailableError(
            f"仅生成 {generated_regions} 个真实区域，未达到要求的 {target_region_count} 个。"
        )

    print(f"[generator] total regions ready: {len(dataset['regions'])}")
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
        f"graph_nodes={len(dataset['graph_nodes'])}",
        f"graph_edges={len(dataset['graph_edges'])}",
    )

    return dataset


def _attach_points_to_graph(
    dataset: Dict[str, List[dict]],
    counters: Counters,
    *,
    region_id: int,
    region_type: RegionType,
    location_label: str,
    junctions: Sequence[dict[str, float]],
    points: Sequence[dict],
    kind: str,
) -> None:
    if not points:
        return

    if not junctions:
        raise RealDataUnavailableError("区域缺少路口节点，无法连接导航图。", location=location_label)

    modes = _transport_mode_values(region_type)
    speed = _connector_ideal_speed(region_type)
    nearest = min(CONNECTOR_NEAREST_JUNCTIONS, len(junctions))

    for point in points:
        latitude = float(point["latitude"])
        longitude = float(point["longitude"])
        node_id = counters.node
        counters.node += 1

        dataset["graph_nodes"].append(
            {
                "id": node_id,
                "region_id": region_id,
                "name": point.get("name"),
                "latitude": round(latitude, 6),
                "longitude": round(longitude, 6),
                "building_id": point["id"] if kind == "building" else None,
                "facility_id": point["id"] if kind == "facility" else None,
                "is_virtual": True,
            }
        )

        _connect_node_to_junctions(
            dataset,
            counters,
            region_id=region_id,
            node_id=node_id,
            latitude=latitude,
            longitude=longitude,
            junctions=junctions,
            modes=modes,
            speed=speed,
            nearest=nearest,
            location_label=location_label,
        )


def _connect_node_to_junctions(
    dataset: Dict[str, List[dict]],
    counters: Counters,
    *,
    region_id: int,
    node_id: int,
    latitude: float,
    longitude: float,
    junctions: Sequence[dict[str, float]],
    modes: Sequence[str],
    speed: float,
    nearest: int,
    location_label: str,
) -> None:
    if not junctions:
        raise RealDataUnavailableError("区域缺少路口节点，无法构建导航连通性。", location=location_label)

    ordered = sorted(
        junctions,
        key=lambda item: _haversine_meters(latitude, longitude, item["latitude"], item["longitude"]),
    )[:nearest]

    for junction in ordered:
        distance = _haversine_meters(latitude, longitude, junction["latitude"], junction["longitude"])
        distance = max(distance, CONNECTOR_MIN_DISTANCE_METERS)
        distance = round(distance, 2)

        dataset["graph_edges"].append(
            {
                "id": counters.edge,
                "region_id": region_id,
                "start_node_id": node_id,
                "end_node_id": junction["id"],
                "distance": distance,
                "ideal_speed": speed,
                "congestion": CONNECTOR_CONGESTION,
                "transport_modes": list(modes),
            }
        )
        counters.edge += 1

        dataset["graph_edges"].append(
            {
                "id": counters.edge,
                "region_id": region_id,
                "start_node_id": junction["id"],
                "end_node_id": node_id,
                "distance": distance,
                "ideal_speed": speed,
                "congestion": CONNECTOR_CONGESTION,
                "transport_modes": list(modes),
            }
        )
        counters.edge += 1


def generate_dataset(
    output_dir: Path, seed: int | None = None, region_target: int | None = None
) -> Dict[str, List[dict]]:
    """Generate synthetic dataset and write individual JSON files."""
    return generate_dataset_with_real_map_data(output_dir, seed, region_target)