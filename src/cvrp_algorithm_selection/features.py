"""Instance-only feature extraction for CVRP algorithm selection."""

from __future__ import annotations

import math

import numpy as np

from cvrp_algorithm_selection.distances import distance_matrix
from cvrp_algorithm_selection.instance import CVRPInstance


def extract_instance_features(instance: CVRPInstance) -> dict[str, float]:
    customers = np.asarray([instance.coordinates[i] for i in instance.customer_indices], dtype=float)
    depot = np.asarray(instance.coordinates[instance.depot_index], dtype=float)
    demands = np.asarray([instance.demands[i] for i in instance.customer_indices], dtype=float)
    distances = distance_matrix(instance)
    customer_indices = list(instance.customer_indices)
    customer_distances = distances[np.ix_(customer_indices, customer_indices)]
    depot_distances = distances[instance.depot_index, customer_indices]

    n = len(customer_indices)
    total_demand = float(demands.sum())
    capacity = float(instance.vehicle_capacity)
    min_vehicles_lb = max(1, math.ceil(total_demand / capacity))

    width = float(customers[:, 0].max() - customers[:, 0].min()) if n else 0.0
    height = float(customers[:, 1].max() - customers[:, 1].min()) if n else 0.0
    area = width * height
    spatial_scale = max(width, height, 1e-12)

    pairwise = customer_distances[np.triu_indices(n, k=1)] if n > 1 else np.asarray([0.0])
    masked = customer_distances.copy()
    np.fill_diagonal(masked, np.inf)
    nearest = np.min(masked, axis=1) if n > 1 else np.asarray([0.0])
    centroid = customers.mean(axis=0)

    ring_ratios = _ring_ratios(depot_distances)
    demand_std = float(np.std(demands))
    mean_pairwise = _safe_mean(pairwise)

    features = {
        "n_customers": float(n),
        "capacity": capacity,
        "total_demand": total_demand,
        "min_vehicles_lb": float(min_vehicles_lb),
        "capacity_pressure": total_demand / capacity,
        "mean_customers_per_min_vehicle": n / min_vehicles_lb,
        "demand_mean": _safe_mean(demands),
        "demand_std": demand_std,
        "demand_min": float(np.min(demands)),
        "demand_max": float(np.max(demands)),
        "demand_cv": demand_std / _safe_mean(demands) if _safe_mean(demands) > 0 else 0.0,
        "demand_q10": float(np.quantile(demands, 0.10)),
        "demand_q25": float(np.quantile(demands, 0.25)),
        "demand_q50": float(np.quantile(demands, 0.50)),
        "demand_q75": float(np.quantile(demands, 0.75)),
        "demand_q90": float(np.quantile(demands, 0.90)),
        "depot_distance_mean": _safe_mean(depot_distances),
        "depot_distance_std": float(np.std(depot_distances)),
        "depot_distance_min": float(np.min(depot_distances)),
        "depot_distance_max": float(np.max(depot_distances)),
        "depot_to_centroid_distance": float(np.linalg.norm(depot - centroid)),
        "depot_centrality_normalized": float(np.linalg.norm(depot - centroid) / spatial_scale),
        "coordinate_width": width,
        "coordinate_height": height,
        "bounding_box_area": area,
        "customer_density": n / area if area > 1e-12 else 0.0,
        "mean_pairwise_customer_distance": mean_pairwise,
        "std_pairwise_customer_distance": float(np.std(pairwise)),
        "mean_nearest_neighbor_distance": _safe_mean(nearest),
        "std_nearest_neighbor_distance": float(np.std(nearest)),
        "nn_to_pairwise_ratio": _safe_mean(nearest) / mean_pairwise if mean_pairwise > 1e-12 else 0.0,
        "mean_distance_to_3_centers": _mean_distance_to_quantile_centers(customers, k=3),
        "cluster_separation_estimate": _cluster_separation_estimate(customers, k=3),
    }
    for i, ratio in enumerate(ring_ratios, start=1):
        features[f"ring_{i}_ratio"] = float(ratio)

    bad = [key for key, value in features.items() if not math.isfinite(value)]
    if bad:
        raise ValueError(f"non-finite features for {instance.name}: {bad}")
    return features


def _ring_ratios(depot_distances: np.ndarray) -> np.ndarray:
    max_distance = float(np.max(depot_distances)) if len(depot_distances) else 0.0
    if max_distance <= 1e-12:
        ratios = np.zeros(5)
        ratios[0] = 1.0
        return ratios
    bins = np.linspace(0.0, max_distance, 6)
    # Use digitize for robust inclusion of the farthest customer in the last bin.
    indices = np.minimum(np.digitize(depot_distances, bins[1:], right=True), 4)
    counts = np.bincount(indices, minlength=5)
    return counts / counts.sum()


def _safe_mean(values: np.ndarray) -> float:
    return float(np.mean(values)) if len(values) else 0.0


def _mean_distance_to_quantile_centers(customers: np.ndarray, k: int) -> float:
    centers = _simple_centers(customers, k)
    distances = np.linalg.norm(customers[:, None, :] - centers[None, :, :], axis=2)
    return float(np.mean(np.min(distances, axis=1)))


def _cluster_separation_estimate(customers: np.ndarray, k: int) -> float:
    centers = _simple_centers(customers, k)
    distances = np.linalg.norm(customers[:, None, :] - centers[None, :, :], axis=2)
    assignments = np.argmin(distances, axis=1)
    within = float(np.mean(np.min(distances, axis=1)))
    center_distances = np.linalg.norm(centers[:, None, :] - centers[None, :, :], axis=2)
    between = center_distances[np.triu_indices(len(centers), k=1)]
    occupied = len(set(int(a) for a in assignments))
    if occupied <= 1 or len(between) == 0:
        return 0.0
    return float(np.mean(between) / within) if within > 1e-12 else 0.0


def _simple_centers(customers: np.ndarray, k: int) -> np.ndarray:
    if len(customers) <= k:
        return customers.copy()
    order = np.argsort(customers[:, 0])
    chunks = np.array_split(customers[order], k)
    return np.asarray([chunk.mean(axis=0) for chunk in chunks])
