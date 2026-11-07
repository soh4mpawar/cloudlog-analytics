"""Equivalence tests comparing MapReduce with independent reference aggregations and
comparing serial vs 2-process executions.
"""

import os
import math
import copy
import pytest
import pandas as pd
from typing import List, Dict, Any
from cloudlog.mapreduce import execute_mapreduce_pipeline
from cloudlog.benchmark import run_benchmark, compare_pipeline_results


def reference_aggregation_pandas(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Independently written baseline aggregator using standard Pandas groupby operations."""
    if not records:
        return {
            "total_requests": 0,
            "total_errors": 0,
            "mean_response_time_ms": 0.0,
            "by_endpoint": {},
            "by_status": {},
        }

    df = pd.DataFrame(records)
    total_requests = len(df)
    total_errors = int(df["is_error"].sum())
    mean_rt = round(float(df["response_time_ms"].mean()), 2)

    # Endpoint reference
    ep_ref = {}
    for ep, group in df.groupby("endpoint"):
        ep_ref[ep] = {
            "count": len(group),
            "errors": int(group["is_error"].sum()),
            "mean_rt": round(float(group["response_time_ms"].mean()), 2),
        }

    # Status reference
    status_ref = {}
    for sc, group in df.groupby("status_code"):
        status_ref[int(sc)] = {
            "count": len(group),
            "mean_rt": round(float(group["response_time_ms"].mean()), 2),
        }

    return {
        "total_requests": total_requests,
        "total_errors": total_errors,
        "mean_response_time_ms": mean_rt,
        "by_endpoint": ep_ref,
        "by_status": status_ref,
    }


def test_mapreduce_vs_reference_aggregation(default_sample_records):
    """Compares MapReduce serial execution directly against independent Pandas reference aggregation."""
    # Run MapReduce
    mr_res = execute_mapreduce_pipeline(default_sample_records, mode="serial", num_partitions=2)

    # Run Reference
    ref = reference_aggregation_pandas(default_sample_records)

    # 1. Total requests & error count & mean RT match
    assert mr_res.metrics.total_requests == ref["total_requests"]
    assert mr_res.metrics.total_errors == ref["total_errors"]
    assert abs(mr_res.metrics.mean_response_time_ms - ref["mean_response_time_ms"]) <= 0.05

    # 2. Endpoint counts match
    mr_ep = mr_res.by_endpoint.set_index("endpoint")
    for ep, data in ref["by_endpoint"].items():
        assert ep in mr_ep.index
        assert mr_ep.loc[ep, "request_count"] == data["count"]
        assert mr_ep.loc[ep, "error_count"] == data["errors"]
        assert abs(mr_ep.loc[ep, "mean_response_time_ms"] - data["mean_rt"]) <= 0.05

    # 3. Status counts match
    mr_status = mr_res.by_status_code.set_index("status_code")
    for sc, data in ref["by_status"].items():
        assert sc in mr_status.index
        assert mr_status.loc[sc, "request_count"] == data["count"]
        assert abs(mr_status.loc[sc, "mean_response_time_ms"] - data["mean_rt"]) <= 0.05


def test_serial_vs_process_pool_equivalence(default_sample_records):
    """Verifies that serial mode and 2-process pool mode yield identical mathematical outputs,
    and proves that actual child-process execution occurred (different worker PIDs)."""
    serial_res = execute_mapreduce_pipeline(default_sample_records, mode="serial", num_partitions=2)
    process_res = execute_mapreduce_pipeline(default_sample_records, mode="process", num_partitions=2)

    # 1. Assert that actual multiprocessing occurred and did not silently fall back to serial
    assert process_res.mode_executed == "process (2 workers)"
    assert process_res.fallback_reason is None
    assert len(process_res.worker_pids) > 0
    # At least one worker process PID must differ from parent PID
    assert any(pid != process_res.parent_pid for pid in process_res.worker_pids)

    # 2. Total metrics match (exact integer counts, float tolerance of 0.01)
    assert serial_res.metrics.total_requests == process_res.metrics.total_requests
    assert serial_res.metrics.total_errors == process_res.metrics.total_errors
    assert math.isclose(serial_res.metrics.mean_response_time_ms, process_res.metrics.mean_response_time_ms, abs_tol=0.01)
    assert math.isclose(serial_res.metrics.error_rate_pct, process_res.metrics.error_rate_pct, abs_tol=0.01)

    # 3. Endpoint dataframes match
    s_ep = serial_res.by_endpoint.sort_values(by="endpoint").reset_index(drop=True)
    p_ep = process_res.by_endpoint.sort_values(by="endpoint").reset_index(drop=True)
    assert s_ep["request_count"].equals(p_ep["request_count"])
    assert s_ep["error_count"].equals(p_ep["error_count"])
    assert (s_ep["mean_response_time_ms"] - p_ep["mean_response_time_ms"]).abs().max() < 0.01

    # 4. Status code dataframes match
    s_sc = serial_res.by_status_code.sort_values(by="status_code").reset_index(drop=True)
    p_sc = process_res.by_status_code.sort_values(by="status_code").reset_index(drop=True)
    assert s_sc["request_count"].equals(p_sc["request_count"])
    assert (s_sc["mean_response_time_ms"] - p_sc["mean_response_time_ms"]).abs().max() < 0.01

    # 5. Hourly buckets match
    s_hr = serial_res.by_hour.sort_values(by="hour_bucket").reset_index(drop=True)
    p_hr = process_res.by_hour.sort_values(by="hour_bucket").reset_index(drop=True)
    assert s_hr["request_count"].equals(p_hr["request_count"])
    assert s_hr["error_count"].equals(p_hr["error_count"])

    # 6. Comprehensive benchmark comparator verification
    match, disc = compare_pipeline_results(serial_res, process_res, tolerance=0.01)
    assert match is True, f"Benchmark comparison detected differences: {disc}"


def test_forced_process_pool_failure_fallback(default_sample_records, monkeypatch):
    """Verifies that if ProcessPoolExecutor fails, the pipeline cleanly falls back to serial mode
    with an explicit fallback reason and notice, while establishing full output correctness across
    all metrics and all three aggregate tables against a normal serial run."""
    class BrokenExecutor:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            raise OSError("Simulated container worker spawn failure")
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    # Baseline reference serial run
    serial_ref = execute_mapreduce_pipeline(default_sample_records, mode="serial", num_partitions=2)

    # Monkeypatch ProcessPoolExecutor to simulate spawn/worker failure
    monkeypatch.setattr("cloudlog.mapreduce.ProcessPoolExecutor", BrokenExecutor)
    fallback_res = execute_mapreduce_pipeline(default_sample_records, mode="process", num_partitions=2)

    assert fallback_res.mode_executed == "serial (fallback)"
    assert fallback_res.fallback_reason is not None
    assert "Simulated container worker spawn failure" in fallback_res.fallback_reason

    # Verify full output correctness across all metrics and all three aggregate tables
    match, discrepancies = compare_pipeline_results(serial_ref, fallback_res, tolerance=0.01)
    assert match is True, f"Fallback output differed from serial baseline: {discrepancies}"
    assert fallback_res.metrics.total_requests == serial_ref.metrics.total_requests
    assert fallback_res.metrics.total_errors == serial_ref.metrics.total_errors
    assert math.isclose(fallback_res.metrics.mean_response_time_ms, serial_ref.metrics.mean_response_time_ms, abs_tol=0.01)


def test_benchmark_under_forced_process_pool_failure(default_sample_records, monkeypatch):
    """Verifies that run_benchmark correctly identifies serial fallback when process pooling fails,
    reporting actual execution mode and an explanatory notice rather than claiming parallel execution."""
    class BrokenExecutor:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            raise OSError("Simulated container worker spawn failure")
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("cloudlog.mapreduce.ProcessPoolExecutor", BrokenExecutor)
    bench = run_benchmark(default_sample_records)

    assert bench.mode_actually_executed == "serial (fallback)"
    assert bench.results_match is True
    assert bench.discrepancy_details is None
    assert "Process execution fallback active" in bench.explanation
    assert "Simulated container worker spawn failure" in bench.explanation
    assert "Both runs executed serially" in bench.explanation


def test_benchmark_detects_altered_grouping_key(default_sample_records):
    """Regression test: verifies that benchmark comparison detects missing/extra or altered grouping keys."""
    serial_res = execute_mapreduce_pipeline(default_sample_records, mode="serial", num_partitions=2)
    corrupted_proc = copy.deepcopy(serial_res)

    # Corrupt an endpoint key: change one endpoint to a new name
    corrupted_df = corrupted_proc.by_endpoint.copy()
    corrupted_df.loc[0, "endpoint"] = "/api/v1/corrupted_endpoint"
    corrupted_proc.by_endpoint = corrupted_df

    match, discrepancies = compare_pipeline_results(serial_res, corrupted_proc)
    assert match is False
    assert any("grouping keys mismatch" in d.lower() or "endpoint" in d.lower() for d in discrepancies)


def test_benchmark_detects_altered_hourly_value(default_sample_records):
    """Regression test: verifies that benchmark comparison detects altered hourly request counts."""
    serial_res = execute_mapreduce_pipeline(default_sample_records, mode="serial", num_partitions=2)
    corrupted_proc = copy.deepcopy(serial_res)

    # Corrupt hourly request count
    corrupted_df = corrupted_proc.by_hour.copy()
    corrupted_df.loc[0, "request_count"] += 42
    corrupted_proc.by_hour = corrupted_df

    match, discrepancies = compare_pipeline_results(serial_res, corrupted_proc)
    assert match is False
    assert any("hourly" in d.lower() and "integer count mismatch" in d.lower() for d in discrepancies)


def test_benchmark_detects_altered_floating_point_value(default_sample_records):
    """Regression test: verifies that benchmark comparison detects floating-point differences exceeding tolerance."""
    serial_res = execute_mapreduce_pipeline(default_sample_records, mode="serial", num_partitions=2)
    corrupted_proc = copy.deepcopy(serial_res)

    # Corrupt mean response time by 0.50 ms, well beyond the 0.01 ms tolerance
    corrupted_df = corrupted_proc.by_status_code.copy()
    corrupted_df.loc[0, "mean_response_time_ms"] += 0.50
    corrupted_proc.by_status_code = corrupted_df

    match, discrepancies = compare_pipeline_results(serial_res, corrupted_proc, tolerance=0.01)
    assert match is False
    assert any("status code" in d.lower() and "floating-point mismatch" in d.lower() for d in discrepancies)


def test_benchmark_detects_unexpected_non_finite_values(default_sample_records):
    """Regression test: verifies that benchmark comparison detects unexpected NaN or Inf values."""
    serial_res = execute_mapreduce_pipeline(default_sample_records, mode="serial", num_partitions=2)
    corrupted_proc = copy.deepcopy(serial_res)

    # Inject NaN into endpoint mean response time
    corrupted_df = corrupted_proc.by_endpoint.copy()
    corrupted_df.loc[0, "mean_response_time_ms"] = float("nan")
    corrupted_proc.by_endpoint = corrupted_df

    match, discrepancies = compare_pipeline_results(serial_res, corrupted_proc)
    assert match is False
    assert any("non-finite" in d.lower() for d in discrepancies)


def test_benchmark_handles_empty_dataset():
    """Verifies that run_benchmark gracefully and correctly handles an empty input dataset."""
    bench = run_benchmark([])
    assert bench.results_match is True
    assert bench.discrepancy_details is None
    assert bench.serial_result.metrics.total_requests == 0
    assert bench.process_result.metrics.total_requests == 0
    assert bench.serial_result.by_endpoint.empty
    assert bench.process_result.by_endpoint.empty
    assert bench.serial_result.by_status_code.empty
    assert bench.process_result.by_status_code.empty
    assert bench.serial_result.by_hour.empty
    assert bench.process_result.by_hour.empty
