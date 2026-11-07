"""Deterministic synthetic web log generator for CloudLog Analytics.

Generates realistic, schema-compliant HTTP request logs with predictable distributions
and UTC timestamps using a fixed random seed.
"""

import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import pandas as pd

from cloudlog.schema import REQUIRED_COLUMNS

ENDPOINTS = [
    ("/api/v1/catalog/items", "GET", 0.32, 45.0, 15.0),
    ("/api/v1/cart/items", "POST", 0.18, 85.0, 25.0),
    ("/api/v1/orders/checkout", "POST", 0.12, 190.0, 60.0),
    ("/api/v1/search", "GET", 0.15, 110.0, 40.0),
    ("/api/v1/auth/login", "POST", 0.10, 140.0, 35.0),
    ("/api/v1/user/profile", "GET", 0.08, 60.0, 20.0),
    ("/healthz", "GET", 0.05, 12.0, 4.0),
]

STATUS_DISTRIBUTION = [
    (200, 0.84),
    (201, 0.05),
    (400, 0.03),
    (401, 0.02),
    (404, 0.03),
    (500, 0.02),
    (503, 0.01),
]


def generate_synthetic_logs(
    row_count: int = 5000,
    seed: int = 42,
    base_time: datetime = datetime(2026, 11, 7, 0, 0, 0, tzinfo=timezone.utc),
    time_span_hours: int = 24,
) -> pd.DataFrame:
    """Generates a deterministic synthetic dataset of web server logs.

    Args:
        row_count: Number of log rows to generate.
        seed: Random seed for 100% reproducibility.
        base_time: Start timestamp in UTC.
        time_span_hours: Span over which timestamps are distributed.

    Returns:
        pd.DataFrame containing valid log records conforming to REQUIRED_COLUMNS.
    """
    rng = random.Random(seed)

    endpoints, methods, ep_weights, base_rts, std_rts = zip(*ENDPOINTS)
    statuses, status_weights = zip(*STATUS_DISTRIBUTION)

    records: List[Dict[str, Any]] = []
    total_seconds = time_span_hours * 3600

    for _ in range(row_count):
        # Pick endpoint
        idx = rng.choices(range(len(endpoints)), weights=ep_weights, k=1)[0]
        endpoint = endpoints[idx]
        method = methods[idx]
        base_rt = base_rts[idx]
        std_rt = std_rts[idx]

        # Timestamp distributed across time span
        offset_seconds = rng.randint(0, total_seconds)
        record_time = base_time + timedelta(seconds=offset_seconds)
        ts_str = record_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Status code selection (errors slightly more likely on checkout and login)
        if endpoint in ("/api/v1/orders/checkout", "/api/v1/auth/login") and rng.random() < 0.08:
            status_code = rng.choice([400, 401, 500, 503])
        else:
            status_code = rng.choices(statuses, weights=status_weights, k=1)[0]

        # Response time (normal distribution clamped to positive, higher for 5xx)
        rt = rng.gauss(base_rt, std_rt)
        if status_code >= 500:
            rt += rng.uniform(200.0, 600.0)
        elif status_code == 404:
            rt = rng.uniform(15.0, 45.0)

        rt_clamped = max(5.0, round(rt, 2))

        records.append({
            "timestamp": ts_str,
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "response_time_ms": rt_clamped,
        })

    # Sort deterministically by timestamp
    records.sort(key=lambda r: r["timestamp"])
    df = pd.DataFrame(records)[REQUIRED_COLUMNS]
    return df


def save_synthetic_dataset_to_file(filepath: str, row_count: int = 5000, seed: int = 42) -> str:
    """Generates and writes sample dataset to CSV file."""
    df = generate_synthetic_logs(row_count=row_count, seed=seed)
    df.to_csv(filepath, index=False)
    return filepath
