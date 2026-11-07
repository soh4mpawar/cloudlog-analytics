"""Pytest fixtures and configuration for CloudLog Analytics test suite."""

import os
import pytest
import pandas as pd
from cloudlog.validator import validate_and_parse_csv

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
TINY_SAMPLE_PATH = os.path.join(FIXTURES_DIR, "tiny_sample.csv")
SAMPLE_LOGS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sample_logs.csv")


@pytest.fixture
def tiny_sample_records():
    """Loads and validates the 7-row hand-checkable fixture."""
    with open(TINY_SAMPLE_PATH, "rb") as f:
        df, summary = validate_and_parse_csv(f.read())
    assert summary.is_valid
    assert len(df) == 7
    return df.to_dict(orient="records")


@pytest.fixture
def default_sample_records():
    """Loads and validates the default 5,000-row synthetic sample."""
    with open(SAMPLE_LOGS_PATH, "rb") as f:
        df, summary = validate_and_parse_csv(f.read())
    assert summary.is_valid
    assert len(df) == 5000
    return df.to_dict(orient="records")
