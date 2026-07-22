"""Reproducible synthetic CVRP instance generation."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

import numpy as np

from cvrp_algorithm_selection.distances import DistanceConvention
from cvrp_algorithm_selection.instance import CVRPInstance
from cvrp_algorithm_selection.validation import validate_instance


CustomerCount = Literal[20, 50, 100]
SpatialFamily = Literal["uniform", "clustered", "two_clusters", "radial", "mixed"]
DepotPosition = Literal["center", "corner", "random"]
DemandRegime = Literal["low_variance", "high_variance", "high_pressure", "low_pressure"]


@dataclass(frozen=True)
class SyntheticCVRPConfig:
    n_customers: CustomerCount
    spatial_family: SpatialFamily
    depot_position: DepotPosition
    demand_regime: DemandRegime
    seed: int
    distance_convention: DistanceConvention = "euclidean_float"
    params: dict[str, Any] = field(default_factory=dict)

    def stable_id(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
        return (
            f"syn-n{self.n_customers}-{self.spatial_family}-"
            f"{self.depot_position}-{self.demand_regime}-s{self.seed}-{digest}"
        )


def generate_synthetic_instance(config: SyntheticCVRPConfig) -> CVRPInstance:
    rng = np.random.default_rng(config.seed)
    customers = _generate_customer_coordinates(config, rng)
    depot = _generate_depot(config.depot_position, rng)
    demands, capacity = _generate_demands_and_capacity(config.n_customers, config.demand_regime, rng)

    instance = CVRPInstance(
        name=config.stable_id(),
        coordinates=tuple([(float(depot[0]), float(depot[1]))] + [(float(x), float(y)) for x, y in customers]),
        demands=tuple([0.0] + [float(value) for value in demands]),
        vehicle_capacity=float(capacity),
        depot_index=0,
        metadata={
            "source": "synthetic",
            "instance_id": config.stable_id(),
            "seed": config.seed,
            "n_customers": config.n_customers,
            "spatial_family": config.spatial_family,
            "depot_position": config.depot_position,
            "demand_regime": config.demand_regime,
            "distance_convention": config.distance_convention,
            "params": dict(config.params),
        },
    )
    validation = validate_instance(instance)
    if not validation.feasible:
        raise ValueError(f"generated invalid instance {instance.name}: {validation.errors}")
    if sum(instance.demands[1:]) <= instance.vehicle_capacity:
        raise ValueError(f"generated trivial one-route instance {instance.name}")
    return instance


def development_dataset_configs(
    seeds: tuple[int, ...] = (0, 1),
    customer_counts: tuple[CustomerCount, ...] = (20, 50),
    demand_regimes: tuple[DemandRegime, ...] = ("low_variance", "high_variance", "high_pressure", "low_pressure"),
    distance_convention: DistanceConvention = "cvrplib_euc_2d",
) -> list[SyntheticCVRPConfig]:
    return [
        SyntheticCVRPConfig(
            n_customers=n,
            spatial_family=spatial,
            depot_position=depot,
            demand_regime=regime,
            seed=seed,
            distance_convention=distance_convention,
        )
        for n in customer_counts
        for spatial in ("uniform", "clustered", "two_clusters", "radial", "mixed")
        for depot in ("center", "corner", "random")
        for regime in demand_regimes
        for seed in seeds
    ]


def final_dataset_configs(
    seeds: tuple[int, ...] = tuple(range(7)),
    customer_counts: tuple[CustomerCount, ...] = (20, 50, 100),
    demand_regimes: tuple[DemandRegime, ...] = ("low_variance", "high_variance", "high_pressure", "low_pressure"),
    distance_convention: DistanceConvention = "cvrplib_euc_2d",
) -> list[SyntheticCVRPConfig]:
    """Balanced final design: 5 x 3 x 4 x 3 x 7 = 1260 instances."""

    return [
        SyntheticCVRPConfig(
            n_customers=n,
            spatial_family=spatial,
            depot_position=depot,
            demand_regime=regime,
            seed=seed,
            distance_convention=distance_convention,
            params={"dataset": "final", "generator_version": "2026-07-08-v1"},
        )
        for n in customer_counts
        for spatial in ("uniform", "clustered", "two_clusters", "radial", "mixed")
        for depot in ("center", "corner", "random")
        for regime in demand_regimes
        for seed in seeds
    ]


def _generate_customer_coordinates(config: SyntheticCVRPConfig, rng: np.random.Generator) -> np.ndarray:
    n = config.n_customers
    family = config.spatial_family
    if family == "uniform":
        return rng.uniform(0.0, 100.0, size=(n, 2))
    if family == "clustered":
        k = int(rng.integers(2, 6))
        centers = rng.uniform(15.0, 85.0, size=(k, 2))
        assignments = rng.integers(0, k, size=n)
        points = centers[assignments] + rng.normal(0.0, 7.5, size=(n, 2))
        return np.clip(points, 0.0, 100.0)
    if family == "two_clusters":
        centers = np.array([[25.0, 25.0], [75.0, 75.0]]) + rng.normal(0.0, 4.0, size=(2, 2))
        assignments = rng.integers(0, 2, size=n)
        points = centers[assignments] + rng.normal(0.0, 6.0, size=(n, 2))
        return np.clip(points, 0.0, 100.0)
    if family == "radial":
        angles = rng.uniform(0.0, 2.0 * math.pi, size=n)
        radii = rng.triangular(8.0, 45.0, 70.0, size=n)
        points = np.column_stack((50.0 + radii * np.cos(angles), 50.0 + radii * np.sin(angles)))
        return np.clip(points, 0.0, 100.0)
    if family == "mixed":
        cluster_count = max(1, int(round(0.6 * n)))
        uniform_count = n - cluster_count
        clustered = _generate_customer_coordinates(
            SyntheticCVRPConfig(n, "clustered", config.depot_position, config.demand_regime, config.seed),
            rng,
        )[:cluster_count]
        uniform = rng.uniform(0.0, 100.0, size=(uniform_count, 2))
        points = np.vstack((clustered, uniform))
        rng.shuffle(points)
        return points
    raise ValueError(f"unsupported spatial family: {family}")


def _generate_depot(position: DepotPosition, rng: np.random.Generator) -> np.ndarray:
    if position == "center":
        return np.array([50.0, 50.0])
    if position == "corner":
        return np.array([0.0, 0.0])
    if position == "random":
        return rng.uniform(10.0, 90.0, size=2)
    raise ValueError(f"unsupported depot position: {position}")


def _generate_demands_and_capacity(
    n_customers: int,
    regime: DemandRegime,
    rng: np.random.Generator,
) -> tuple[np.ndarray, int]:
    if regime == "low_variance":
        demands = np.rint(np.clip(rng.normal(8.0, 1.5, size=n_customers), 4.0, 12.0)).astype(int)
        target_routes = max(2, math.ceil(n_customers / 8))
        slack = 1.25
    elif regime == "high_variance":
        large = rng.random(n_customers) < 0.3
        demands = np.where(
            large,
            rng.integers(18, 36, size=n_customers),
            rng.integers(2, 11, size=n_customers),
        )
        target_routes = max(2, math.ceil(n_customers / 7))
        slack = 1.15
    elif regime == "high_pressure":
        demands = rng.integers(8, 24, size=n_customers)
        target_routes = max(2, math.ceil(n_customers / 5))
        slack = 1.03
    elif regime == "low_pressure":
        demands = rng.integers(4, 16, size=n_customers)
        target_routes = max(2, math.ceil(n_customers / 12))
        slack = 1.45
    else:
        raise ValueError(f"unsupported demand regime: {regime}")

    total = int(demands.sum())
    capacity = max(int(demands.max()), math.ceil(total / target_routes * slack))
    if capacity >= total:
        capacity = max(int(demands.max()), math.ceil(total / 2))
    return demands.astype(float), int(capacity)
