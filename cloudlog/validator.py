"""CSV validation and ingestion module for CloudLog Analytics.

Enforces schema constraints, limits (5 MB, 50,000 rows), and provides detailed
rejection tracking.
"""

import io
import math
import pandas as pd
from typing import Tuple, List, Dict, Optional, Union
from datetime import datetime, timezone
from cloudlog.schema import (
    MAX_UPLOAD_SIZE_BYTES,
    MAX_ROW_LIMIT,
    REQUIRED_COLUMNS,
    ALLOWED_METHODS,
    MIN_STATUS_CODE,
    MAX_STATUS_CODE,
    ValidationSummary,
)


def validate_and_parse_csv(
    file_or_content: Union[io.BytesIO, io.StringIO, bytes, str],
    file_size_bytes: Optional[int] = None,
) -> Tuple[pd.DataFrame, ValidationSummary]:
    """Validates raw CSV content against CloudLog schema and processing constraints.

    Args:
        file_or_content: Uploaded file object, bytes, or string content.
        file_size_bytes: Explicit byte size if available (e.g. from UploadedFile.size).

    Returns:
        Tuple of (validated_dataframe, ValidationSummary)
    """
    rejection_reasons: Dict[str, int] = {}
    sample_errors: List[str] = []

    def record_rejection(reason: str, sample_detail: Optional[str] = None):
        rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
        if sample_detail and len(sample_errors) < 10:
            sample_errors.append(sample_detail)

    # 1. Byte size validation
    raw_bytes: Optional[bytes] = None
    if isinstance(file_or_content, bytes):
        raw_bytes = file_or_content
    elif isinstance(file_or_content, str):
        raw_bytes = file_or_content.encode("utf-8")
    elif hasattr(file_or_content, "getvalue"):
        raw_bytes = file_or_content.getvalue()  # BytesIO / StringIO
    elif hasattr(file_or_content, "read"):
        current_pos = file_or_content.tell() if hasattr(file_or_content, "tell") else 0
        raw_bytes = file_or_content.read()
        if hasattr(file_or_content, "seek"):
            file_or_content.seek(current_pos)

    # Empty content check
    if raw_bytes is not None and len(raw_bytes.strip()) == 0:
        return pd.DataFrame(), ValidationSummary(
            total_raw_rows=0,
            accepted_rows=0,
            rejected_rows=0,
            rejection_reasons={},
            sample_errors=[],
            is_valid=True,
            error_message="Uploaded CSV contains 0 rows.",
        )

    actual_size = file_size_bytes or (len(raw_bytes) if raw_bytes is not None else 0)
    if actual_size > MAX_UPLOAD_SIZE_BYTES:
        err = f"File size ({actual_size / (1024 * 1024):.2f} MB) exceeds maximum allowed limit of 5.0 MB."
        return pd.DataFrame(), ValidationSummary(
            total_raw_rows=0,
            accepted_rows=0,
            rejected_rows=0,
            rejection_reasons={"file_size_exceeded": 1},
            sample_errors=[err],
            is_valid=False,
            error_message=err,
        )

    # 2. Parse CSV into DataFrame (bounded by MAX_ROW_LIMIT + 1 to prevent memory exhaustion)
    try:
        if raw_bytes is not None:
            df_raw = pd.read_csv(
                io.BytesIO(raw_bytes),
                dtype=str,
                keep_default_na=False,
                nrows=MAX_ROW_LIMIT + 1,
            )
        else:
            df_raw = pd.read_csv(
                file_or_content,
                dtype=str,
                keep_default_na=False,
                nrows=MAX_ROW_LIMIT + 1,
            )
    except pd.errors.EmptyDataError:
        return pd.DataFrame(), ValidationSummary(
            total_raw_rows=0,
            accepted_rows=0,
            rejected_rows=0,
            rejection_reasons={},
            sample_errors=[],
            is_valid=True,
            error_message="Uploaded CSV contains 0 rows.",
        )
    except Exception as exc:
        err = f"Malformed CSV format: {str(exc)}"
        return pd.DataFrame(), ValidationSummary(
            total_raw_rows=0,
            accepted_rows=0,
            rejected_rows=0,
            rejection_reasons={"malformed_csv_syntax": 1},
            sample_errors=[err],
            is_valid=False,
            error_message=err,
        )

    total_rows = len(df_raw)
    if total_rows == 0:
        return pd.DataFrame(), ValidationSummary(
            total_raw_rows=0,
            accepted_rows=0,
            rejected_rows=0,
            rejection_reasons={},
            sample_errors=[],
            is_valid=True,
            error_message="Uploaded CSV contains 0 rows.",
        )

    # 3. Check Row Limit (enforced before executing row-by-row iteration)
    if total_rows > MAX_ROW_LIMIT:
        err = f"Row count exceeds safety processing limit of {MAX_ROW_LIMIT:,} rows."
        return pd.DataFrame(), ValidationSummary(
            total_raw_rows=total_rows,
            accepted_rows=0,
            rejected_rows=total_rows,
            rejection_reasons={"row_limit_exceeded": total_rows},
            sample_errors=[err],
            is_valid=False,
            error_message=err,
        )

    # 4. Check Required Columns
    # Normalize column names: strip whitespace and lowercase
    raw_col_map = {col.strip().lower(): col for col in df_raw.columns}
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in raw_col_map]
    if missing_cols:
        err = f"Missing required column(s): {', '.join(missing_cols)}. Expected schema: {', '.join(REQUIRED_COLUMNS)}."
        return pd.DataFrame(), ValidationSummary(
            total_raw_rows=total_rows,
            accepted_rows=0,
            rejected_rows=total_rows,
            rejection_reasons={"missing_required_columns": total_rows},
            sample_errors=[err],
            is_valid=False,
            error_message=err,
        )

    # Map normalized names to original
    target_df = pd.DataFrame()
    for col in REQUIRED_COLUMNS:
        target_df[col] = df_raw[raw_col_map[col]]

    # 5. Row-by-row validation
    accepted_records: List[Dict[str, Union[str, int, float, bool]]] = []

    for idx, row in target_df.iterrows():
        row_num = idx + 2  # 1-based index including CSV header
        ts_val = str(row["timestamp"]).strip()
        ep_val = str(row["endpoint"]).strip()
        method_val = str(row["method"]).strip().upper()
        status_val = str(row["status_code"]).strip()
        rt_val = str(row["response_time_ms"]).strip()

        # Check blank endpoint
        if not ep_val:
            record_rejection("blank_endpoint", f"Row {row_num}: endpoint is empty or whitespace.")
            continue

        # Check method
        if method_val not in ALLOWED_METHODS:
            record_rejection("invalid_http_method", f"Row {row_num}: unsupported HTTP method '{method_val}'.")
            continue

        # Check status_code
        if "." in status_val:
            record_rejection("fractional_status_code", f"Row {row_num}: HTTP status code '{status_val}' cannot be fractional.")
            continue

        try:
            status_int = int(status_val)
            if not (MIN_STATUS_CODE <= status_int <= MAX_STATUS_CODE):
                record_rejection("invalid_status_code", f"Row {row_num}: status code {status_int} out of range [100, 599].")
                continue
        except (ValueError, TypeError):
            record_rejection("malformed_status_code", f"Row {row_num}: status code '{status_val}' is not an integer.")
            continue

        # Check response_time_ms
        try:
            rt_float = float(rt_val)
            if math.isnan(rt_float) or math.isinf(rt_float) or rt_float < 0:
                record_rejection("negative_or_nonfinite_response_time", f"Row {row_num}: invalid response time {rt_val}.")
                continue
        except (ValueError, TypeError):
            record_rejection("malformed_response_time", f"Row {row_num}: response time '{rt_val}' is not numeric.")
            continue

        # Check timestamp
        try:
            dt = None
            # Standard formats: ISO 8601 with Z, ISO 8601 with offset, standard YYYY-MM-DD HH:MM:SS
            ts_clean = ts_val.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(ts_clean)
            except ValueError:
                # Fallback to dateutil / strptime formats
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y/%m/%d %H:%M:%S"):
                    try:
                        dt = datetime.strptime(ts_val, fmt)
                        break
                    except ValueError:
                        pass

            if dt is None:
                record_rejection("malformed_timestamp", f"Row {row_num}: unparseable timestamp '{ts_val}'.")
                continue

            # Ensure UTC timezone awareness
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)

            iso_ts = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            hour_bucket = dt.strftime("%Y-%m-%d %H:00:00")
        except Exception:
            record_rejection("malformed_timestamp", f"Row {row_num}: invalid timestamp value '{ts_val}'.")
            continue

        accepted_records.append({
            "timestamp": iso_ts,
            "hour_bucket": hour_bucket,
            "endpoint": ep_val,
            "method": method_val,
            "status_code": status_int,
            "response_time_ms": round(rt_float, 2),
            "is_error": status_int >= 400,
        })

    valid_df = pd.DataFrame(accepted_records)
    accepted_count = len(accepted_records)
    rejected_count = total_rows - accepted_count

    summary = ValidationSummary(
        total_raw_rows=total_rows,
        accepted_rows=accepted_count,
        rejected_rows=rejected_count,
        rejection_reasons=rejection_reasons,
        sample_errors=sample_errors,
        is_valid=True,
    )
    return valid_df, summary
