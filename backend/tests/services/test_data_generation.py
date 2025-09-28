"""Tests for synthetic data generation and validation utilities."""

import json
from pathlib import Path

import pytest

from app.services.data_generation import generator
from scripts import validate_data


@pytest.mark.parametrize("region_count, buildings_range, facilities_range, users_count", [(5, (2, 3), (1, 2), 3)])
def test_generate_dataset_writes_expected_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, region_count: int, buildings_range: tuple[int, int], facilities_range: tuple[int, int], users_count: int) -> None:
    """Generation should honour patched configuration and create JSON outputs."""

    monkeypatch.setattr(generator, "MIN_REGION_COUNT", region_count)
    monkeypatch.setattr(generator, "BUILDINGS_PER_REGION", buildings_range)
    monkeypatch.setattr(generator, "FACILITIES_PER_REGION", facilities_range)
    monkeypatch.setattr(generator, "USERS_COUNT", users_count)
    monkeypatch.setattr(generator, "DIARIES_PER_USER", (1, 2))

    dataset = generator.generate_dataset(tmp_path, seed=7)

    assert len(dataset["regions"]) == region_count
    assert len(dataset["buildings"]) >= region_count * buildings_range[0]
    assert len(dataset["facilities"]) >= region_count * facilities_range[0]
    assert len(dataset["users"]) == users_count
    assert len(dataset["graph_nodes"]) > 0
    assert len(dataset["graph_edges"]) > 0
    assert len(dataset["diaries"]) > 0

    for key in dataset:
        assert (tmp_path / f"{key}.json").exists()


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
    (dataset_dir / "users.json").write_text(
        json.dumps(
            [
                {
                    "id": 1,
                    "username": "tester",
                    "display_name": "Tester",
                    "email": "tester@example.com",
                    "interests": ["自然"],
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
