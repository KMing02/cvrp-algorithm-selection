"""CVRP instance representation.

Routes in this project use ``list[list[int]]``. Each inner list contains only
customer indices. The depot is never stored inside a route; route costs
implicitly include depot -> first customer and last customer -> depot.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


Coordinate = tuple[float, float]


@dataclass(frozen=True)
class CVRPInstance:
    """Minimal symmetric Euclidean CVRP instance."""

    name: str
    coordinates: tuple[Coordinate, ...]
    demands: tuple[float, ...]
    vehicle_capacity: float
    depot_index: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def customer_indices(self) -> tuple[int, ...]:
        return tuple(i for i in range(len(self.coordinates)) if i != self.depot_index)

    @property
    def size(self) -> int:
        return len(self.coordinates)
