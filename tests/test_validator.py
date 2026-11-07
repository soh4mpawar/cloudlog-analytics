"""Unit tests for CloudLog CSV validation and boundary enforcement."""

import io
import pytest
import pandas as pd
from cloudlog.validator import validate_and_parse_csv
from cloudlog.schema import MAX_UPLOAD_SIZE_BYTES, MAX_ROW_LIMIT


def test_valid_csv_parsing(tiny_sample_records):
    """Verifies that a valid CSV is parsed completely into validated records."""
    assert len(tiny_sample_records) == 7
    first = tiny_sample_records[0]
    assert first["endpoint"] == "/catalog"
    assert first["status_code"] == 200
    assert first["response_time_ms"] == 50.0
    assert not first["is_error"]


def test_file_size_limit_rejection():
    """Verifies rejection when file size exceeds 5 MB limit."""
    oversized_bytes = b"timestamp,endpoint,method,status_code,response_time_ms\n" + b"x" * (MAX_UPLOAD_SIZE_BYTES + 100)
    df, summary = validate_and_parse_csv(oversized_bytes)
    assert not summary.is_valid
    assert "file_size_exceeded" in summary.rejection_reasons
    assert df.empty


def test_row_limit_rejection():
    """Verifies rejection when CSV exceeds 50,000 row safety limit."""
    header = "timestamp,endpoint,method,status_code,response_time_ms\n"
    # Create a string buffer with > 50,000 rows
    row = "2026-11-07T10:00:00Z,/catalog,GET,200,50.0\n"
    content = header + (row * (MAX_ROW_LIMIT + 5))
    df, summary = validate_and_parse_csv(content)
    assert not summary.is_valid
    assert "row_limit_exceeded" in summary.rejection_reasons
    assert df.empty


def test_missing_required_columns():
    """Verifies detection of missing required schema columns."""
    bad_csv = "timestamp,endpoint,status_code\n2026-11-07T10:00:00Z,/catalog,200\n"
    df, summary = validate_and_parse_csv(bad_csv)
    assert not summary.is_valid
    assert "missing_required_columns" in summary.rejection_reasons
    assert "method" in summary.error_message


def test_invalid_and_malformed_rows():
    """Verifies tracking of individual malformed rows without crashing."""
    csv_data = """timestamp,endpoint,method,status_code,response_time_ms
2026-11-07T10:00:00Z,/valid,GET,200,45.0
invalid-date,/valid,GET,200,45.0
2026-11-07T10:00:00Z,   ,GET,200,45.0
2026-11-07T10:00:00Z,/valid,INVALID_METHOD,200,45.0
2026-11-07T10:00:00Z,/valid,GET,999,45.0
2026-11-07T10:00:00Z,/valid,GET,200,-15.0
2026-11-07T10:00:00Z,/valid,GET,200,NaN
"""
    df, summary = validate_and_parse_csv(csv_data)
    assert summary.is_valid
    assert summary.total_raw_rows == 7
    assert summary.accepted_rows == 1
    assert summary.rejected_rows == 6
    assert len(df) == 1
    assert df.iloc[0]["endpoint"] == "/valid"

    # Verify rejection reason breakdown
    assert "malformed_timestamp" in summary.rejection_reasons
    assert "blank_endpoint" in summary.rejection_reasons
    assert "invalid_http_method" in summary.rejection_reasons
    assert "invalid_status_code" in summary.rejection_reasons
    assert "negative_or_nonfinite_response_time" in summary.rejection_reasons


def test_empty_csv_handling():
    """Verifies that an empty CSV is handled gracefully without exception."""
    df, summary = validate_and_parse_csv("")
    assert summary.is_valid
    assert summary.total_raw_rows == 0
    assert summary.accepted_rows == 0
    assert df.empty


def test_fractional_status_code_rejection():
    """Verifies that fractional HTTP status codes (e.g. 200.5, 404.0) are strictly rejected."""
    csv_data = """timestamp,endpoint,method,status_code,response_time_ms
2026-11-07T10:00:00Z,/catalog,GET,200.5,50.0
2026-11-07T10:05:00Z,/catalog,GET,404.0,60.0
2026-11-07T10:10:00Z,/catalog,GET,200,70.0
"""
    df, summary = validate_and_parse_csv(csv_data)
    assert summary.is_valid
    assert summary.total_raw_rows == 3
    assert summary.accepted_rows == 1
    assert summary.rejected_rows == 2
    assert "fractional_status_code" in summary.rejection_reasons
    assert summary.rejection_reasons["fractional_status_code"] == 2
