from cvrp_algorithm_selection.data import load_cvrplib_with_verypy, tiny_manual_instance
from cvrp_algorithm_selection.experiments import run_experiment_table
from cvrp_algorithm_selection.features import extract_instance_features
from cvrp_algorithm_selection.instance import CVRPInstance
from cvrp_algorithm_selection.solvers import SolverResult, benchmark, selected_solver_portfolio
from cvrp_algorithm_selection.synthetic import SyntheticCVRPConfig, generate_synthetic_instance
from cvrp_algorithm_selection.validation import ValidationResult, validate_solution

__all__ = [
    "CVRPInstance",
    "SolverResult",
    "ValidationResult",
    "SyntheticCVRPConfig",
    "benchmark",
    "extract_instance_features",
    "generate_synthetic_instance",
    "load_cvrplib_with_verypy",
    "run_experiment_table",
    "selected_solver_portfolio",
    "tiny_manual_instance",
    "validate_solution",
]


def main() -> None:
    instance = tiny_manual_instance()
    for result in benchmark(instance, seed=0):
        status = "feasible" if result.feasible else f"failed: {result.failure_reason}"
        print(
            f"{result.configuration_name}: {status}, "
            f"cost={result.total_distance}, runtime={result.runtime_seconds:.6f}s"
        )
