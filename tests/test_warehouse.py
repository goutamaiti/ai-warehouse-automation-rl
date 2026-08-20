"""Tests for the static layout: geometry, semantics and validation."""

from __future__ import annotations

import numpy as np
import pytest

from simulation.config import LayoutConfig
from simulation.navigation import bfs_distance_field, reachable_cells
from simulation.warehouse import CellType, WarehouseLayout, build_layout, validate_layout


def test_layout_has_requested_dimensions_and_closed_walls():
    config = LayoutConfig()
    layout = build_layout(config)
    assert layout.shape == (config.height, config.width)
    assert (layout.grid[0, :] == CellType.WALL).all()
    assert (layout.grid[-1, :] == CellType.WALL).all()
    assert (layout.grid[:, 0] == CellType.WALL).all()
    assert (layout.grid[:, -1] == CellType.WALL).all()


def test_points_of_interest_are_walkable_and_distinct():
    layout = build_layout(LayoutConfig())
    points = layout.storage_points + layout.packing_stations + layout.charging_stations
    assert len(points) == len(set(points)), "a cell was assigned two roles"
    assert all(layout.is_walkable(point) for point in points)
    assert len(layout.storage_points) > 0
    assert len(layout.packing_stations) == LayoutConfig().n_packing_stations
    assert len(layout.charging_stations) == LayoutConfig().n_charging_stations


def test_every_point_of_interest_is_mutually_reachable():
    layout = build_layout(LayoutConfig())
    connected = reachable_cells(layout.walkable_mask(), layout.charging_stations[0])
    points = layout.storage_points + layout.packing_stations + layout.charging_stations
    assert set(points).issubset(connected)


def test_storage_points_touch_a_shelf():
    layout = build_layout(LayoutConfig())
    for row, col in layout.storage_points:
        neighbours = [
            layout.grid[row + dr, col + dc]
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
            if 0 <= row + dr < layout.height and 0 <= col + dc < layout.width
        ]
        assert CellType.SHELF in neighbours


@pytest.mark.parametrize(
    "config",
    [
        LayoutConfig(width=31, height=21, shelf_block_height=3),
        LayoutConfig(width=15, height=11, n_packing_stations=1),
        LayoutConfig(width=25, height=17, aisle_width=2),
    ],
)
def test_alternative_layouts_are_valid(config: LayoutConfig):
    validate_layout(build_layout(config))


def test_too_small_layout_is_rejected():
    with pytest.raises(ValueError):
        build_layout(LayoutConfig(width=5, height=5))


def test_validation_catches_a_sealed_off_station():
    layout = build_layout(LayoutConfig())
    grid = layout.grid.copy()
    station = layout.packing_stations[-1]
    # Wall in every neighbour of the station: it becomes an island.
    for d_row, d_col in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        grid[station[0] + d_row, station[1] + d_col] = int(CellType.WALL)
    sealed = WarehouseLayout(
        grid=grid,
        storage_points=layout.storage_points,
        packing_stations=layout.packing_stations,
        charging_stations=layout.charging_stations,
    )
    with pytest.raises(ValueError, match="unreachable"):
        validate_layout(sealed)


def test_distance_field_matches_manual_bfs_on_a_tiny_grid():
    walkable = np.array(
        [
            [True, True, True],
            [False, False, True],
            [True, True, True],
        ]
    )
    field = bfs_distance_field(walkable, (0, 0))
    assert field[0, 0] == 0
    assert field[0, 2] == 2
    assert field[2, 0] == 6  # forced detour around the wall row
    assert field[1, 0] == -1  # blocked cell stays unreachable


def test_layout_serialises_to_json_friendly_types():
    payload = build_layout(LayoutConfig()).to_dict()
    assert payload["height"] and payload["width"]
    assert isinstance(payload["grid"][0][0], int)
    assert payload["legend"]["charging"] == int(CellType.CHARGING)
