"""Schema definitions, limits, and type annotations for CloudLog Analytics."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

# Strict limits as per requirements
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_ROW_LIMIT = 50_000

REQUIRED_COLUMNS = [
    "timestamp",
    "endpoint",
    "method",
    "status_code",
    "response_time_ms",
]

ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}

MIN_STATUS_CODE = 100
MAX_STATUS_CODE = 599


@dataclass
class ValidationSummary:
    """Summary of CSV ingestion and validation."""
    total_raw_rows: int
    accepted_rows: int
    rejected_rows: int
    rejection_reasons: Dict[str, int]
    sample_errors: List[str]
    is_valid: bool
    error_message: Optional[str] = None


@dataclass
class LogRecord:
    """Represents a validated log entry."""
    timestamp: str  # ISO UTC string YYYY-MM-DDTHH:MM:SSZ
    hour_bucket: str  # YYYY-MM-DD HH:00:00 UTC
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    is_error: bool  # True if status_code >= 400


@dataclass
class AggregatedMetrics:
    """Aggregated metrics summary."""
    total_requests: int
    total_errors: int
    error_rate_pct: float
    mean_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float


@dataclass
class MapReduceStageOutput:
    """Detailed intermediate stage outputs for inspection."""
    partition_counts: List[int]
    sample_emitted_pairs: List[Tuple[str, Tuple[Any, ...]]]
    sample_grouped_pairs: List[Tuple[str, List[Tuple[Any, ...]]]]
    sample_reduced_records: List[Dict[str, Any]]
    sample_derived_records: List[Dict[str, Any]]
    traced_sample_keys: List[str]
