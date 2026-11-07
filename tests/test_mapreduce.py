"""Unit tests for CloudLog MapReduce pipeline.

Covers partitioning, mapping, shuffling, reducing, deriving weighted means,
uneven partitions, empty datasets, and fallback handling.
"""

import pytest
from cloudlog.mapreduce import (
    partition_data,
    execute_mapreduce_pipeline,
)


def test_partitioning_even_and_uneven():
    """Verifies that partition_data distributes records cleanly across uneven chunks."""
    records_7 = [{"id": i} for i in range(7)]
    parts_2 = partition_data(records_7, num_partitions=2)
    assert len(parts_2) == 2
    assert len(parts_2[0]) == 4
    assert len(parts_2[1]) == 3
    # Check completeness
    flattened = [r["id"] for p in parts_2 for r in p]
    assert flattened == list(range(7))

    # Test edge case: more partitions than records
    parts_5 = partition_data(records_7[:2], num_partitions=5)
    assert len(parts_5) == 5
    assert len(parts_5[0]) == 1
    assert len(parts_5[1]) == 1
    assert len(parts_5[2]) == 0
    assert len(parts_5[3]) == 0
    assert len(parts_5[4]) == 0


def test_partitioning_empty():
    """Verifies partitioning on an empty dataset."""
    empty_parts = partition_data([], num_partitions=2)
    assert len(empty_parts) == 2
    assert empty_parts[0] == []
    assert empty_parts[1] == []


def test_tiny_sample_hand_checked_equivalence(tiny_sample_records):
    """Verifies MapReduce outputs against exact manual calculations on tiny_sample.csv.

    Expected:
    - /catalog: 3 requests, 1 error, 70.0 ms mean RT
    - /checkout: 2 requests, 1 error, 300.0 ms mean RT
    - /login: 2 requests, 1 error, 200.0 ms mean RT
    - Overall: 7 requests, 3 errors (42.86%), 172.86 ms mean RT
    """
    res = execute_mapreduce_pipeline(tiny_sample_records, mode="serial", num_partitions=2)

    # 1. Overall metrics check
    assert res.metrics.total_requests == 7
    assert res.metrics.total_errors == 3
    assert res.metrics.error_rate_pct == 42.86
    assert res.metrics.mean_response_time_ms == 172.86

    # 2. Endpoint aggregation check
    ep_df = res.by_endpoint.set_index("endpoint")

    assert ep_df.loc["/catalog", "request_count"] == 3
    assert ep_df.loc["/catalog", "error_count"] == 1
    assert ep_df.loc["/catalog", "error_rate_pct"] == 33.33
    assert ep_df.loc["/catalog", "mean_response_time_ms"] == 70.0

    assert ep_df.loc["/checkout", "request_count"] == 2
    assert ep_df.loc["/checkout", "error_count"] == 1
    assert ep_df.loc["/checkout", "error_rate_pct"] == 50.00
    assert ep_df.loc["/checkout", "mean_response_time_ms"] == 300.0

    assert ep_df.loc["/login", "request_count"] == 2
    assert ep_df.loc["/login", "error_count"] == 1
    assert ep_df.loc["/login", "error_rate_pct"] == 50.00
    assert ep_df.loc["/login", "mean_response_time_ms"] == 200.0

    # 3. Status code aggregation check
    status_df = res.by_status_code.set_index("status_code")
    assert status_df.loc[200, "request_count"] == 4
    assert status_df.loc[200, "mean_response_time_ms"] == 115.0
    assert status_df.loc[401, "request_count"] == 1
    assert status_df.loc[401, "mean_response_time_ms"] == 250.0
    assert status_df.loc[404, "request_count"] == 1
    assert status_df.loc[404, "mean_response_time_ms"] == 100.0
    assert status_df.loc[500, "request_count"] == 1
    assert status_df.loc[500, "mean_response_time_ms"] == 400.0


def test_weighted_mean_not_average_of_partition_averages(tiny_sample_records):
    """Proves that overall mean response time is derived from total sum / total count,
    avoiding the mathematical fallacy of averaging partition averages.

    Partition 0 has 4 records, sum=410, average = 102.5 ms.
    Partition 1 has 3 records, sum=800, average = 266.67 ms.
    Naive unweighted average = (102.5 + 266.67) / 2 = 184.58 ms.
    True weighted average = (410 + 800) / 7 = 172.86 ms.
    """
    res = execute_mapreduce_pipeline(tiny_sample_records, mode="serial", num_partitions=2)

    # Must be 172.86, NOT 184.58
    assert res.metrics.mean_response_time_ms == 172.86
    assert abs(res.metrics.mean_response_time_ms - 184.58) > 10.0


def test_empty_dataset_handling():
    """Verifies that an empty record set executes without errors."""
    res = execute_mapreduce_pipeline([], mode="serial", num_partitions=2)
    assert res.metrics.total_requests == 0
    assert res.metrics.total_errors == 0
    assert res.metrics.error_rate_pct == 0.0
    assert res.metrics.mean_response_time_ms == 0.0
    assert res.by_endpoint.empty
    assert res.by_status_code.empty
    assert res.by_hour.empty


def test_stage_output_inspection(tiny_sample_records):
    """Verifies that stage_output contains sample emitted pairs, groups, and partitions."""
    res = execute_mapreduce_pipeline(tiny_sample_records, mode="serial", num_partitions=2)
    stage = res.stage_output
    assert stage.partition_counts == [4, 3]
    assert len(stage.sample_emitted_pairs) > 0
    assert len(stage.sample_grouped_pairs) > 0
    assert len(stage.sample_reduced_records) > 0
