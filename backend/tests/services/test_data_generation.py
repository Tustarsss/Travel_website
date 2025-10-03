"""Tests for real-data-only generation and dataset validation utilities."""

import json
from pathlib import Path

import pytest

from app.services.data_generation import generator
from app.services.data_generation.osm_adapter import AdaptedRegionData, RealDataUnavailableError
from scripts import validate_data


def _stub_region_payload(region_id: int, min_buildings: int, min_facilities: int) -> AdaptedRegionData:
    """Build deterministic building/facility collections satisfying minimum counts."""

    building_count = max(min_buildings, 3)
    facility_count = max(min_facilities, 2)

    def _points(prefix: str, count: int) -> list[dict]:
        return [
            {
                "name": f"{prefix}-{region_id}-{index}",
                "latitude": 30.0 + region_id * 0.1 + index * 0.001,
                "longitude": 120.0 + region_id * 0.1 + index * 0.001,
            }
            for index in range(count)
        ]

    return AdaptedRegionData(buildings=_points("building", building_count), facilities=_points("facility", facility_count))


@pytest.mark.parametrize(
    "region_count, buildings_range, facilities_range",
    [(3, (2, 3), (1, 2))],
)
def test_generate_dataset_writes_expected_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    region_count: int,
    buildings_range: tuple[int, int],
    facilities_range: tuple[int, int],
) -> None:
    """Generation should honour patched configuration and create JSON outputs from real-data pipeline."""

    monkeypatch.setattr(generator, "MIN_REGION_COUNT", region_count)
    monkeypatch.setattr(generator, "BUILDINGS_PER_REGION", buildings_range)
    monkeypatch.setattr(generator, "FACILITIES_PER_REGION", facilities_range)

    call_tracker: list[int] = []

    def fake_get_osm_data(_: str) -> dict:
        call_tracker.append(1)
        return {"bounds": [10.0, 20.0, 30.0, 40.0]}

    def fake_adapt(osm_payload, region_id, region_type, min_buildings, min_facilities, *, location=None):
        return _stub_region_payload(region_id, min_buildings, min_facilities)

    monkeypatch.setattr(generator, "get_osm_data_for_location", fake_get_osm_data)
    monkeypatch.setattr(generator, "adapt_osm_payload", fake_adapt)

    graph_nodes_stub = [
        {"name": "交叉口1", "latitude": 30.0, "longitude": 120.0},
        {"name": "交叉口2", "latitude": 30.001, "longitude": 120.001},
        {"name": "交叉口3", "latitude": 30.002, "longitude": 120.002},
    ]
    graph_edges_stub = [
        {
            "source_index": 0,
            "target_index": 1,
            "distance": 100.0,
            "ideal_speed": 1.2,
            "congestion": 0.5,
            "transport_modes": ["walk"],
        },
        {
            "source_index": 1,
            "target_index": 2,
            "distance": 120.0,
            "ideal_speed": 1.3,
            "congestion": 0.6,
            "transport_modes": ["walk"],
        },
    ]

    monkeypatch.setattr(
        generator,
        "convert_osm_graph_to_components",
        lambda graph, region_type: (graph_nodes_stub, graph_edges_stub),
    )

    dataset = generator.generate_dataset(tmp_path, seed=7)

    expected_keys = {"regions", "buildings", "facilities", "graph_nodes", "graph_edges"}
    assert set(dataset.keys()) == expected_keys

    assert len(dataset["regions"]) == region_count
    assert len(dataset["buildings"]) >= region_count * buildings_range[0]
    assert len(dataset["facilities"]) >= region_count * facilities_range[0]
    assert len(dataset["graph_nodes"]) > 0
    assert len(dataset["graph_edges"]) > 0
    assert "users" not in dataset
    assert "diaries" not in dataset

    # All collections should have been flushed to disk for downstream import scripts.
    for key in expected_keys:
        assert (tmp_path / f"{key}.json").exists()
    # Ensure the real-data fetch pipeline was invoked for each region.
    assert len(call_tracker) == region_count
    # Graph should now contain dedicated junctions and virtual site bindings with connectors.
    junction_node_ids = {
        node["id"]
        for node in dataset["graph_nodes"]
        if node["building_id"] is None and node["facility_id"] is None
    }
    binding_node_ids = {
        node["id"]
        for node in dataset["graph_nodes"]
        if node["building_id"] is not None or node["facility_id"] is not None
    }

    assert junction_node_ids, "Expected at least one junction node in the graph"
    assert binding_node_ids, "Expected building/facility bindings to be present"

    adjacency: dict[int, set[int]] = {}
    for edge in dataset["graph_edges"]:
        adjacency.setdefault(edge["start_node_id"], set()).add(edge["end_node_id"])

    for binding_node_id in binding_node_ids:
        connected = adjacency.get(binding_node_id, set())
        assert connected & junction_node_ids, "Each site binding must connect to at least one junction node"


def test_generate_dataset_requires_real_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Generator must fail fast when no real OSM payload can be acquired."""

    monkeypatch.setattr(generator, "get_osm_data_for_location", lambda _: None)

    with pytest.raises(RealDataUnavailableError):
        generator.generate_dataset(tmp_path, seed=1, region_target=1)


def test_validate_dataset_detects_violations(tmp_path: Path) -> None:
    """Validator should raise when dataset does not meet size requirements."""

    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()

    (dataset_dir / "regions.json").write_text(
        json.dumps(
            [
                {
                    "id": 1,
                    "name": "Test Scenic",
                    "type": "scenic",
                    "popularity": 50,
                    "rating": 4.0,
                }
            ]
        ),
        encoding="utf-8",
    )
    (dataset_dir / "buildings.json").write_text(
        json.dumps(
            [
                {
                    "id": 1,
                    "region_id": 1,
                    "name": "Test Building",
                    "category": "scenic_spot",
                    "latitude": 0.0,
                    "longitude": 0.0,
                }
            ]
        ),
        encoding="utf-8",
    )
    (dataset_dir / "facilities.json").write_text(
        json.dumps(
            [
                {
                    "id": 1,
                    "region_id": 1,
                    "name": "Test Facility",
                    "category": "restroom",
                    "latitude": 0.0,
                    "longitude": 0.0,
                }
            ]
        ),
        encoding="utf-8",
    )
    (dataset_dir / "graph_nodes.json").write_text(
        json.dumps(
            [
                {
                    "id": 1,
                    "region_id": 1,
                    "name": "节点1",
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "building_id": None,
                    "facility_id": None,
                    "is_virtual": False,
                },
                {
                    "id": 2,
                    "region_id": 1,
                    "name": "节点2",
                    "latitude": 0.001,
                    "longitude": 0.001,
                    "building_id": None,
                    "facility_id": None,
                    "is_virtual": False,
                },
            ]
        ),
        encoding="utf-8",
    )
    (dataset_dir / "graph_edges.json").write_text(
        json.dumps(
            [
                {
                    "id": 1,
                    "region_id": 1,
                    "start_node_id": 1,
                    "end_node_id": 1,
                    "distance": 10.0,
                    "ideal_speed": 1.0,
                    "congestion": 0.5,
                    "transport_modes": ["walk"],
                }
            ]
        ),
        encoding="utf-8",
    )

    indexes_dir = tmp_path / "indexes"
    indexes_dir.mkdir()
    (indexes_dir / "spatial.idx").write_text("", encoding="utf-8")
    (indexes_dir / "fulltext.idx").write_text("", encoding="utf-8")

    with pytest.raises(AssertionError):
        validate_data.validate_dataset(dataset_dir, indexes_dir)
