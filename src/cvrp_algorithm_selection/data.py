"""Small instance construction and loading helpers."""

from __future__ import annotations

from pathlib import Path

from verypy.cvrp_io import read_TSPLIB_CVRP

from cvrp_algorithm_selection.instance import CVRPInstance


def tiny_manual_instance() -> CVRPInstance:
    """A 6-customer Euclidean CVRP that requires at least two routes."""

    return CVRPInstance(
        name="tiny-manual",
        coordinates=((0.0, 0.0), (3.0, 0.0), (0.0, 4.0), (6.0, 0.0), (0.0, 8.0), (6.0, 8.0), (8.0, 6.0)),
        demands=(0.0, 2.0, 3.0, 2.0, 3.0, 4.0, 2.0),
        vehicle_capacity=7.0,
        depot_index=0,
        metadata={"source": "manual", "distance_convention": "euclidean_float"},
    )


def load_cvrplib_with_verypy(path: str | Path, distance_convention: str = "cvrplib_euc_2d") -> CVRPInstance:
    """Load one TSPLIB/CVRPLIB CVRP file using VeRyPy's parser."""

    path = Path(path)
    problem = read_TSPLIB_CVRP(str(path))
    if problem.coordinate_points is None:
        raise ValueError(f"{path} does not contain Euclidean coordinates")
    if problem.capacity_constraint is None:
        raise ValueError(f"{path} does not contain a capacity constraint")
    if problem.customer_demands is None:
        raise ValueError(f"{path} does not contain customer demands")

    return CVRPInstance(
        name=path.stem,
        coordinates=tuple((float(x), float(y)) for x, y in problem.coordinate_points),
        demands=tuple(float(demand) for demand in problem.customer_demands),
        vehicle_capacity=float(problem.capacity_constraint),
        depot_index=0,
        metadata={
            "source": str(path),
            "parser": "verypy.cvrp_io.read_TSPLIB_CVRP",
            "edge_weight_type": problem.edge_weight_type,
            "distance_convention": distance_convention,
            "note": "CVRPLIB best-known integer costs should only be compared when using cvrplib_euc_2d.",
        },
    )
