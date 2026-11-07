"""Core MapReduce pipeline for CloudLog Analytics.

Implements Partition -> Map -> Shuffle -> Reduce -> Derive stages for web log
analysis. Supports both serial and bounded 2-process execution with automatic
graceful fallback.
"""

import os
import time
import math
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any, Optional
from concurrent.futures import ProcessPoolExecutor
import pandas as pd

from cloudlog.schema import AggregatedMetrics, MapReduceStageOutput

logger = logging.getLogger(__name__)

# Value tuple format emitted by mapper:
# (count: int, error_count: int, sum_response_time: float)
MapperValue = Tuple[int, int, float]
EmittedPair = Tuple[Any, MapperValue]


def partition_data(records: List[Dict[str, Any]], num_partitions: int = 2) -> List[List[Dict[str, Any]]]:
    """Splits records into num_partitions disjoint partitions.

    Handles uneven partition counts and empty records gracefully.
    """
    if num_partitions <= 0:
        raise ValueError(f"num_partitions must be >= 1, got {num_partitions}")
    if not records:
        return [[] for _ in range(num_partitions)]

    n = len(records)
    actual_partitions = min(num_partitions, n)
    k, m = divmod(n, actual_partitions)

    partitions: List[List[Dict[str, Any]]] = []
    start = 0
    for i in range(actual_partitions):
        # Distribute remainder m across the first m partitions
        chunk_size = k + (1 if i < m else 0)
        partitions.append(records[start:start + chunk_size])
        start += chunk_size

    # Pad with empty partitions if n < num_partitions
    while len(partitions) < num_partitions:
        partitions.append([])

    return partitions


def map_partition_records(
    partition_records: List[Dict[str, Any]]
) -> Dict[str, List[EmittedPair]]:
    """Top-level picklable mapper function.

    Processes a single partition and emits (key, value) pairs for:
    - endpoint: key = str(endpoint)
    - status_code: key = int(status_code)
    - hour_bucket: key = str(hour_bucket)

    Value is a uniform tuple: (1, 1 if is_error else 0, response_time_ms)
    """
    mapped_by_endpoint: List[EmittedPair] = []
    mapped_by_status: List[EmittedPair] = []
    mapped_by_hour: List[EmittedPair] = []

    for rec in partition_records:
        ep = rec["endpoint"]
        status = int(rec["status_code"])
        hour = rec["hour_bucket"]
        rt = float(rec["response_time_ms"])
        is_err = 1 if (status >= 400 or rec.get("is_error", False)) else 0

        val: MapperValue = (1, is_err, rt)

        mapped_by_endpoint.append((ep, val))
        mapped_by_status.append((status, val))
        mapped_by_hour.append((hour, val))

    return {
        "endpoint": mapped_by_endpoint,
        "status_code": mapped_by_status,
        "hour_bucket": mapped_by_hour,
        "worker_pid": os.getpid(),
    }


def shuffle_and_group(
    partition_outputs: List[List[EmittedPair]]
) -> Dict[Any, List[MapperValue]]:
    """Groups emitted pairs from all partitions by key."""
    grouped: Dict[Any, List[MapperValue]] = {}
    for part in partition_outputs:
        for key, val in part:
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(val)
    return grouped


def reduce_group(key: Any, values: List[MapperValue]) -> Dict[str, Any]:
    """Reduces a list of values for a single key into aggregated sums/counts."""
    total_count = sum(v[0] for v in values)
    total_errors = sum(v[1] for v in values)
    total_rt_sum = sum(v[2] for v in values)

    return {
        "key": key,
        "request_count": total_count,
        "error_count": total_errors,
        "sum_response_time_ms": total_rt_sum,
    }


def derive_aggregates_dataframe(
    reduced_items: List[Dict[str, Any]],
    key_column_name: str,
    total_dataset_requests: int = 0
) -> pd.DataFrame:
    """Derives weighted metrics (mean RT, error rate) from reduced sums and counts.

    Crucially computes mean = total_sum / total_count (never average of partition averages).
    """
    if not reduced_items:
        return pd.DataFrame(columns=[
            key_column_name,
            "request_count",
            "error_count",
            "error_rate_pct",
            "mean_response_time_ms",
            "share_pct",
        ])

    rows = []
    for item in reduced_items:
        cnt = item["request_count"]
        errs = item["error_count"]
        rt_sum = item["sum_response_time_ms"]

        mean_rt = round(rt_sum / cnt, 2) if cnt > 0 else 0.0
        err_rate = round((errs / cnt) * 100.0, 2) if cnt > 0 else 0.0
        share_pct = round((cnt / total_dataset_requests) * 100.0, 2) if total_dataset_requests > 0 else 0.0

        rows.append({
            key_column_name: item["key"],
            "request_count": cnt,
            "error_count": errs,
            "error_rate_pct": err_rate,
            "mean_response_time_ms": mean_rt,
            "share_pct": share_pct,
        })

    df = pd.DataFrame(rows)
    # Sort sensibly
    if key_column_name == "request_count":
        df = df.sort_values(by="request_count", ascending=False)
    elif key_column_name in ("hour_bucket", "timestamp"):
        df = df.sort_values(by=key_column_name, ascending=True)
    elif key_column_name == "status_code":
        df = df.sort_values(by="status_code", ascending=True)
    else:
        df = df.sort_values(by="request_count", ascending=False)
    return df.reset_index(drop=True)


@dataclass
class MapReduceExecutionResult:
    """Complete execution result of the MapReduce pipeline."""
    by_endpoint: pd.DataFrame
    by_status_code: pd.DataFrame
    by_hour: pd.DataFrame
    metrics: AggregatedMetrics
    mode_requested: str
    mode_executed: str
    num_partitions: int
    execution_time_ms: float
    stage_output: MapReduceStageOutput
    worker_pids: List[int] = field(default_factory=list)
    parent_pid: int = field(default_factory=os.getpid)
    fallback_reason: Optional[str] = None


def execute_mapreduce_pipeline(
    records: List[Dict[str, Any]],
    mode: str = "serial",
    num_partitions: int = 2,
) -> MapReduceExecutionResult:
    """Executes the MapReduce pipeline over the provided records.

    Args:
        records: List of validated log dictionaries.
        mode: "serial" or "process" (uses ProcessPoolExecutor with 2 workers).
        num_partitions: Number of data partitions (default 2).

    Returns:
        MapReduceExecutionResult containing all aggregated dataframes and metrics.
    """
    mode_requested = mode.lower()
    mode_executed = "serial"
    fallback_reason: Optional[str] = None
    start_time = time.perf_counter()

    # Step 1: Partitioning
    partitions = partition_data(records, num_partitions=num_partitions)
    partition_counts = [len(p) for p in partitions]

    mapped_partitions: List[Dict[str, List[EmittedPair]]] = []

    # Step 2: Map phase execution
    if mode_requested == "process" and len(records) > 0:
        try:
            with ProcessPoolExecutor(max_workers=num_partitions) as executor:
                mapped_partitions = list(executor.map(map_partition_records, partitions))
            mode_executed = "process (2 workers)"
        except Exception as exc:
            logger.warning("ProcessPoolExecutor execution failed, falling back to serial: %s", exc)
            fallback_reason = f"ProcessPoolExecutor unavailable or failed ({type(exc).__name__}: {str(exc)}). Ran in serial mode."
            mode_executed = "serial (fallback)"
            mapped_partitions = [map_partition_records(p) for p in partitions]
    else:
        mode_executed = "serial"
        mapped_partitions = [map_partition_records(p) for p in partitions]

    # Step 3: Shuffle and Group phase
    endpoint_shuffled = shuffle_and_group([mp["endpoint"] for mp in mapped_partitions])
    status_shuffled = shuffle_and_group([mp["status_code"] for mp in mapped_partitions])
    hour_shuffled = shuffle_and_group([mp["hour_bucket"] for mp in mapped_partitions])

    # Step 4: Reduce phase
    endpoint_reduced = [reduce_group(k, v) for k, v in endpoint_shuffled.items()]
    status_reduced = [reduce_group(k, v) for k, v in status_shuffled.items()]
    hour_reduced = [reduce_group(k, v) for k, v in hour_shuffled.items()]

    # Step 5: Derive metrics
    total_records = len(records)
    total_errors = sum(r["error_count"] for r in endpoint_reduced)
    total_rt_sum = sum(r["sum_response_time_ms"] for r in endpoint_reduced)

    df_endpoint = derive_aggregates_dataframe(endpoint_reduced, "endpoint", total_records)
    df_status = derive_aggregates_dataframe(status_reduced, "status_code", total_records)
    df_hour = derive_aggregates_dataframe(hour_reduced, "hour_bucket", total_records)

    overall_error_rate = round((total_errors / total_records) * 100.0, 2) if total_records > 0 else 0.0
    overall_mean_rt = round(total_rt_sum / total_records, 2) if total_records > 0 else 0.0

    min_rt = min((float(r["response_time_ms"]) for r in records), default=0.0)
    max_rt = max((float(r["response_time_ms"]) for r in records), default=0.0)

    elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

    metrics = AggregatedMetrics(
        total_requests=total_records,
        total_errors=total_errors,
        error_rate_pct=overall_error_rate,
        mean_response_time_ms=overall_mean_rt,
        min_response_time_ms=round(min_rt, 2),
        max_response_time_ms=round(max_rt, 2),
    )

    # Extract worker PIDs from partition outputs
    worker_pids = [int(mp["worker_pid"]) for mp in mapped_partitions if "worker_pid" in mp]

    # Identify up to 2 distinct endpoint keys to trace consistently across stages 2 -> 5
    traced_keys: List[str] = []
    if mapped_partitions and mapped_partitions[0]["endpoint"]:
        for pair in mapped_partitions[0]["endpoint"]:
            key_str = str(pair[0])
            if key_str not in traced_keys:
                traced_keys.append(key_str)
            if len(traced_keys) >= 2:
                break
    if not traced_keys and endpoint_shuffled:
        traced_keys = [str(k) for k in list(endpoint_shuffled.keys())[:2]]

    # Stage 2 sample: emitted pairs corresponding to traced_keys
    sample_emitted: List[Tuple[str, MapperValue]] = []
    if mapped_partitions and mapped_partitions[0]["endpoint"]:
        sample_emitted = [
            pair for pair in mapped_partitions[0]["endpoint"]
            if str(pair[0]) in traced_keys
        ][:5]
        if not sample_emitted:
            sample_emitted = mapped_partitions[0]["endpoint"][:5]

    # Stage 3 sample: grouped values for the traced_keys
    sample_grouped: List[Tuple[str, List[MapperValue]]] = []
    for k in traced_keys:
        if k in endpoint_shuffled:
            sample_grouped.append((k, endpoint_shuffled[k][:5]))

    # Stage 4 sample: reduced records for the traced_keys
    sample_reduced: List[Dict[str, Any]] = [
        r for r in endpoint_reduced if str(r["key"]) in traced_keys
    ]

    # Stage 5 sample: derived records for the traced_keys
    sample_derived: List[Dict[str, Any]] = (
        df_endpoint[df_endpoint["endpoint"].isin(traced_keys)].to_dict(orient="records")
        if not df_endpoint.empty else []
    )

    stage_output = MapReduceStageOutput(
        partition_counts=partition_counts,
        sample_emitted_pairs=sample_emitted,
        sample_grouped_pairs=sample_grouped,
        sample_reduced_records=sample_reduced,
        sample_derived_records=sample_derived,
        traced_sample_keys=traced_keys,
    )

    return MapReduceExecutionResult(
        by_endpoint=df_endpoint,
        by_status_code=df_status,
        by_hour=df_hour,
        metrics=metrics,
        mode_requested=mode_requested,
        mode_executed=mode_executed,
        num_partitions=num_partitions,
        execution_time_ms=elapsed_ms,
        stage_output=stage_output,
        worker_pids=worker_pids,
        parent_pid=os.getpid(),
        fallback_reason=fallback_reason,
    )
