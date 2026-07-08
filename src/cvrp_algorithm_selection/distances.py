"""Distance conventions for symmetric Euclidean CVRP instances."""

from __future__ import annotations

from typing import Literal

import numpy as np

from cvrp_algorithm_selection.instance import CVRPInstance


DistanceConvention = Literal["euclidean_float", "cvrplib_euc_2d"]
DEFAULT_DISTANCE_CONVENTION: DistanceConvention = "euclidean_float"


def instance_distance_convention(instance: CVRPInstance) -> DistanceConvention:
    convention = instance.metadata.get("distance_convention", DEFAULT_DISTANCE_CONVENTION)
    if convention not in ("euclidean_float", "cvrplib_euc_2d"):
        raise ValueError(f"unsupported distance convention: {convention}")
    return convention


def distance_matrix(instance: CVRPInstance) -> np.ndarray:
    """Return the full distance matrix using the instance's convention."""

    return distance_matrix_from_coordinates(instance.coordinates, instance_distance_convention(instance))


def distance_matrix_from_coordinates(
    coordinates: tuple[tuple[float, float], ...],
    convention: DistanceConvention = DEFAULT_DISTANCE_CONVENTION,
) -> np.ndarray:
    coords = np.asarray(coordinates, dtype=float)
    diff = coords[:, None, :] - coords[None, :, :]
    distances = np.sqrt(np.sum(diff * diff, axis=2))
    if convention == "euclidean_float":
        return distances
    if convention == "cvrplib_euc_2d":
        return np.floor(distances + 0.5).astype(float)
    raise ValueError(f"unsupported distance convention: {convention}")
