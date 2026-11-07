"""Benchmark module for CloudLog Analytics.

Compares Serial vs 2-Process MapReduce execution on identical datasets, verifies
deterministic equivalence across all aggregate tables (endpoint, status code, hourly),
and provides educational performance analysis.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import math
import numpy as np
import pandas as pd
from cloudlog.mapreduce import execute_mapreduce_pipeline, MapReduceExecutionResult


@dataclass
class BenchmarkComparison:
    """Results of running both serial and 2-process modes."""
    serial_result: MapReduceExecutionResult
    process_result: MapReduceExecutionResult
    results_match: bool
    discrepancy_details: Optional[str]
    serial_time_ms: float
    process_time_ms: float
    speedup_factor: float
    mode_actually_executed: str
    explanation: str


def compare_aggregate_tables(
    serial_df: pd.DataFrame,
    process_df: pd.DataFrame,
    key_column: str,
    table_name: str,
    int_columns: List[str],
    float_columns: List[str],
    tolerance: float = 0.01,
) -> List[str]:
    """Compares two aggregate DataFrames across grouping keys, integer counts, and floating-point values.

    Checks:
    - Empty DataFrame handling (both empty = match; one empty = discrepancy).
    - Grouping keys presence and set equivalence (detects missing or extra groups).
    - Unexpected non-finite values (NaN, Inf, -Inf).
    - Exact integer count equality.
    - Floating-point aggregate comparison within documented numerical tolerance.
    """
    discrepancies: List[str] = []

    # 1. Emptiness check
    if serial_df.empty and process_df.empty:
        return []
    if serial_df.empty != process_df.empty:
        discrepancies.append(
            f"{table_name}: emptiness mismatch (serial has {len(serial_df)} rows, process has {len(process_df)} rows)."
        )
        return discrepancies

    # 2. Key column presence
    if key_column not in serial_df.columns:
        discrepancies.append(f"{table_name}: key column '{key_column}' missing in serial results.")
        return discrepancies
    if key_column not in process_df.columns:
        discrepancies.append(f"{table_name}: key column '{key_column}' missing in process results.")
        return discrepancies

    # 3. Grouping keys equivalence (missing or extra groups)
    keys_serial = set(serial_df[key_column])
    keys_process = set(process_df[key_column])
    missing_in_proc = keys_serial - keys_process
    extra_in_proc = keys_process - keys_serial

    if missing_in_proc or extra_in_proc:
        discrepancies.append(
            f"{table_name} grouping keys mismatch: missing in process={sorted(list(missing_in_proc))}, "
            f"extra in process={sorted(list(extra_in_proc))}."
        )
        return discrepancies

    # 4. Check for unexpected non-finite values in numeric columns
    for col in int_columns + float_columns:
        if col in serial_df.columns:
            non_finite = serial_df[~np.isfinite(pd.to_numeric(serial_df[col], errors="coerce"))]
            if not non_finite.empty:
                discrepancies.append(f"{table_name} (serial) contains non-finite values in '{col}'.")
        if col in process_df.columns:
            non_finite = process_df[~np.isfinite(pd.to_numeric(process_df[col], errors="coerce"))]
            if not non_finite.empty:
                discrepancies.append(f"{table_name} (process) contains non-finite values in '{col}'.")

    # 5. Sort identically by key for row-by-row checks
    s_sorted = serial_df.sort_values(by=key_column).reset_index(drop=True)
    p_sorted = process_df.sort_values(by=key_column).reset_index(drop=True)

    # Check grouping key order/values
    if not s_sorted[key_column].equals(p_sorted[key_column]):
        discrepancies.append(f"{table_name} grouping key sequence differs after sorting.")

    # Check exact integer columns
    for col in int_columns:
        if col in s_sorted.columns and col in p_sorted.columns:
            diff_mask = s_sorted[col] != p_sorted[col]
            if diff_mask.any():
                mismatched = s_sorted.loc[diff_mask, key_column].tolist()
                discrepancies.append(
                    f"{table_name} exact integer count mismatch in column '{col}' for keys: {mismatched}."
                )
        elif col in s_sorted.columns or col in p_sorted.columns:
            discrepancies.append(f"{table_name} column schema mismatch for integer column '{col}'.")

    # Check floating-point columns with documented tolerance
    for col in float_columns:
        if col in s_sorted.columns and col in p_sorted.columns:
            diffs = (s_sorted[col] - p_sorted[col]).abs()
            max_diff = diffs.max() if not diffs.empty else 0.0
            if max_diff > tolerance:
                exceeded_mask = diffs > tolerance
                mismatched = s_sorted.loc[exceeded_mask, key_column].tolist()
                discrepancies.append(
                    f"{table_name} floating-point mismatch in column '{col}' "
                    f"(max diff {max_diff:.4f} > tolerance {tolerance:.4f}) for keys: {mismatched}."
                )
        elif col in s_sorted.columns or col in p_sorted.columns:
            discrepancies.append(f"{table_name} column schema mismatch for float column '{col}'.")

    return discrepancies


def compare_pipeline_results(
    serial_res: MapReduceExecutionResult,
    process_res: MapReduceExecutionResult,
    tolerance: float = 0.01,
) -> Tuple[bool, List[str]]:
    """Compares serial and process pipeline outputs across top-level metrics and all three aggregate tables:
    endpoint, status code, and hourly.
    """
    discrepancies: List[str] = []

    # 1. Global Metrics comparison
    if serial_res.metrics.total_requests != process_res.metrics.total_requests:
        discrepancies.append(
            f"Total requests mismatch: serial={serial_res.metrics.total_requests}, "
            f"process={process_res.metrics.total_requests}"
        )
    if serial_res.metrics.total_errors != process_res.metrics.total_errors:
        discrepancies.append(
            f"Total errors mismatch: serial={serial_res.metrics.total_errors}, "
            f"process={process_res.metrics.total_errors}"
        )

    # Check non-finite global metric values
    for name, val in [
        ("mean_response_time_ms", serial_res.metrics.mean_response_time_ms),
        ("error_rate_pct", serial_res.metrics.error_rate_pct),
    ]:
        if not math.isfinite(val):
            discrepancies.append(f"Global metric '{name}' in serial results is non-finite: {val}")

    for name, val in [
        ("mean_response_time_ms", process_res.metrics.mean_response_time_ms),
        ("error_rate_pct", process_res.metrics.error_rate_pct),
    ]:
        if not math.isfinite(val):
            discrepancies.append(f"Global metric '{name}' in process results is non-finite: {val}")

    if abs(serial_res.metrics.mean_response_time_ms - process_res.metrics.mean_response_time_ms) > tolerance:
        discrepancies.append(
            f"Mean RT mismatch: serial={serial_res.metrics.mean_response_time_ms:.2f}, "
            f"process={process_res.metrics.mean_response_time_ms:.2f} (tol={tolerance})"
        )
    if abs(serial_res.metrics.error_rate_pct - process_res.metrics.error_rate_pct) > tolerance:
        discrepancies.append(
            f"Error rate mismatch: serial={serial_res.metrics.error_rate_pct:.2f}%, "
            f"process={process_res.metrics.error_rate_pct:.2f}% (tol={tolerance})"
        )

    # 2. Table 1: Endpoint aggregates
    int_cols = ["request_count", "error_count"]
    float_cols = ["error_rate_pct", "mean_response_time_ms", "share_pct"]

    ep_discrepancies = compare_aggregate_tables(
        serial_res.by_endpoint,
        process_res.by_endpoint,
        key_column="endpoint",
        table_name="Endpoint",
        int_columns=int_cols,
        float_columns=float_cols,
        tolerance=tolerance,
    )
    discrepancies.extend(ep_discrepancies)

    # 3. Table 2: Status code aggregates
    sc_discrepancies = compare_aggregate_tables(
        serial_res.by_status_code,
        process_res.by_status_code,
        key_column="status_code",
        table_name="Status code",
        int_columns=int_cols,
        float_columns=float_cols,
        tolerance=tolerance,
    )
    discrepancies.extend(sc_discrepancies)

    # 4. Table 3: Hourly aggregates
    hr_discrepancies = compare_aggregate_tables(
        serial_res.by_hour,
        process_res.by_hour,
        key_column="hour_bucket",
        table_name="Hourly",
        int_columns=int_cols,
        float_columns=float_cols,
        tolerance=tolerance,
    )
    discrepancies.extend(hr_discrepancies)

    return (len(discrepancies) == 0, discrepancies)


def run_benchmark(records: List[Dict[str, Any]], tolerance: float = 0.01) -> BenchmarkComparison:
    """Executes both serial and 2-process pipelines on the exact same dataset.

    Verifies output equivalence across all three aggregate tables (endpoint, status code, hourly)
    and captures real, non-fabricated execution times.
    """
    # 1. Serial run
    serial_res = execute_mapreduce_pipeline(records, mode="serial", num_partitions=2)

    # 2. Process run (2 workers)
    process_res = execute_mapreduce_pipeline(records, mode="process", num_partitions=2)

    # 3. Equivalence check across all metrics and all three aggregate tables
    results_match, discrepancies = compare_pipeline_results(serial_res, process_res, tolerance=tolerance)
    discrepancy_str = "; ".join(discrepancies) if discrepancies else None

    # Calculate actual ratio
    s_time = serial_res.execution_time_ms
    p_time = process_res.execution_time_ms
    speedup = round(s_time / p_time, 2) if p_time > 0 else 1.0

    # Educational commentary based on actual measured numbers
    if process_res.fallback_reason or "fallback" in process_res.mode_executed:
        explanation = (
            f"Process execution fallback active: {process_res.fallback_reason}. "
            "Both runs executed serially in this environment; no parallel speedup can be evaluated."
        )
    elif len(records) < 10_000:
        if p_time >= s_time:
            explanation = (
                f"Serial mode was faster ({s_time:.1f} ms vs {p_time:.1f} ms, ratio {speedup:.2f}x). "
                "This is expected for small-to-medium datasets: the fixed overhead of spawning OS worker processes, "
                "pickling record dictionaries, and IPC inter-process communication outweighs the CPU savings of splitting the work."
            )
        else:
            explanation = (
                f"Multiprocessing completed in {p_time:.1f} ms vs serial {s_time:.1f} ms (speedup {speedup:.2f}x). "
                "On this machine, the CPU parallelism benefits exceeded the IPC and process creation overhead."
            )
    else:
        if speedup > 1.0:
            explanation = (
                f"2-Process mode achieved a {speedup:.2f}x speedup ({p_time:.1f} ms vs {s_time:.1f} ms). "
                f"With {len(records):,} records, the computational workload amortised the multiprocessing startup cost."
            )
        else:
            explanation = (
                f"Multiprocessing ran in {p_time:.1f} ms vs {s_time:.1f} ms serial (ratio {speedup:.2f}x). "
                "Memory bandwidth and data serialization overhead remained the dominant cost."
            )

    return BenchmarkComparison(
        serial_result=serial_res,
        process_result=process_res,
        results_match=results_match,
        discrepancy_details=discrepancy_str,
        serial_time_ms=s_time,
        process_time_ms=p_time,
        speedup_factor=speedup,
        mode_actually_executed=process_res.mode_executed,
        explanation=explanation,
    )
