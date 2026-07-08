from __future__ import annotations

from cvrp_algorithm_selection.distances import distance_matrix
from cvrp_algorithm_selection.instance import CVRPInstance


def test_float_and_cvrplib_euc_2d_distances_differ() -> None:
    base = {
        "name": "distance-convention",
        "coordinates": ((0.0, 0.0), (1.4, 0.0), (2.5, 0.0)),
        "demands": (0.0, 1.0, 1.0),
        "vehicle_capacity": 2.0,
    }
    float_instance = CVRPInstance(**base, metadata={"distance_convention": "euclidean_float"})
    rounded_instance = CVRPInstance(**base, metadata={"distance_convention": "cvrplib_euc_2d"})

    float_distances = distance_matrix(float_instance)
    rounded_distances = distance_matrix(rounded_instance)

    assert float_distances[0, 1] == 1.4
    assert rounded_distances[0, 1] == 1.0
    assert float_distances[0, 2] == 2.5
    assert rounded_distances[0, 2] == 3.0
