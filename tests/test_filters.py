"""Tests for pre-aggregation filtering logic on datasets."""

import pytest
from datetime import datetime, timezone
from cloudlog.mapreduce import execute_mapreduce_pipeline


def test_endpoint_filtering(default_sample_records):
    """Verifies that filtering by specific endpoints before MapReduce correctly restricts output."""
    selected_endpoints = ["/api/v1/auth/login", "/healthz"]
    filtered_records = [r for r in default_sample_records if r["endpoint"] in selected_endpoints]

    assert len(filtered_records) > 0
    assert len(filtered_records) < len(default_sample_records)

    res = execute_mapreduce_pipeline(filtered_records, mode="serial", num_partitions=2)

    # Only the selected endpoints exist in the aggregation
    assert set(res.by_endpoint["endpoint"]) == set(selected_endpoints)
    assert res.metrics.total_requests == len(filtered_records)


def test_date_range_filtering(default_sample_records):
    """Verifies that filtering by date range restricts records to that interval."""
    # Pick a 2-hour window
    start_iso = "2026-11-07T04:00:00Z"
    end_iso = "2026-11-07T06:00:00Z"

    filtered_records = [
        r for r in default_sample_records
        if start_iso <= r["timestamp"] <= end_iso
    ]

    assert len(filtered_records) > 0

    res = execute_mapreduce_pipeline(filtered_records, mode="serial", num_partitions=2)
    assert res.metrics.total_requests == len(filtered_records)

    # All hour buckets in the result must be within the range
    for hr in res.by_hour["hour_bucket"]:
        assert "2026-11-07 04:00:00" <= hr <= "2026-11-07 06:00:00"


def test_filters_resulting_in_zero_records(default_sample_records):
    """Verifies that if user filters filter out 100% of records, the pipeline returns empty state cleanly."""
    filtered_records = [r for r in default_sample_records if r["endpoint"] == "/nonexistent/endpoint"]
    assert len(filtered_records) == 0

    res = execute_mapreduce_pipeline(filtered_records, mode="serial", num_partitions=2)
    assert res.metrics.total_requests == 0
    assert res.metrics.error_rate_pct == 0.0
    assert res.by_endpoint.empty
    assert res.by_status_code.empty
    assert res.by_hour.empty
