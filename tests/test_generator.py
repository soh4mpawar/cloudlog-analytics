"""Unit tests for synthetic log generator."""

import pandas as pd
from cloudlog.generator import generate_synthetic_logs
from cloudlog.schema import REQUIRED_COLUMNS


def test_generator_deterministic_seed():
    """Verifies that the same seed produces bit-for-bit identical dataframes."""
    df1 = generate_synthetic_logs(row_count=100, seed=42)
    df2 = generate_synthetic_logs(row_count=100, seed=42)
    assert df1.equals(df2)

    df3 = generate_synthetic_logs(row_count=100, seed=99)
    assert not df1.equals(df3)


def test_generator_schema_compliance():
    """Verifies that generated logs conform to required columns and constraints."""
    df = generate_synthetic_logs(row_count=200, seed=123)
    assert list(df.columns) == REQUIRED_COLUMNS
    assert len(df) == 200

    # All response times positive
    assert (df["response_time_ms"] > 0).all()

    # All status codes in valid HTTP range
    assert (df["status_code"] >= 100).all()
    assert (df["status_code"] <= 599).all()

    # Endpoints non-empty
    assert (df["endpoint"].str.len() > 0).all()
