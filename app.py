"""CloudLog Analytics: Cloud-Based Web Log Analysis Using MapReduce.

Streamlit application providing:
1. Operational Log Analytics Dashboard
2. Step-by-step "Inside MapReduce" educational view
3. Serial vs 2-Process Performance Benchmark
4. Cloud Architecture & PaaS vs IaaS Technical Overview
"""

import os
import io
from datetime import datetime, timezone, timedelta
import streamlit as st
import pandas as pd

from cloudlog.schema import (
    MAX_UPLOAD_SIZE_BYTES,
    MAX_ROW_LIMIT,
    REQUIRED_COLUMNS,
)
from cloudlog.validator import validate_and_parse_csv
from cloudlog.mapreduce import execute_mapreduce_pipeline
from cloudlog.benchmark import run_benchmark
from cloudlog.charts import (
    create_endpoint_bar_chart,
    create_timeline_chart,
    create_status_code_chart,
    create_benchmark_comparison_chart,
    PALETTE,
)
from cloudlog.styles import apply_custom_styles

# Page configuration
st.set_page_config(
    page_title="CloudLog Analytics | Cloud-Based Log Analysis",
    page_icon="CL",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply custom styling (enforces warm ivory, olive, charcoal palette; zero blue/purple)
st.markdown(apply_custom_styles(), unsafe_allow_html=True)

DEFAULT_SAMPLE_PATH = os.path.join(os.path.dirname(__file__), "data", "sample_logs.csv")


@st.cache_data(show_spinner=False)
def load_default_sample():
    """Loads and caches the default synthetic dataset."""
    if os.path.exists(DEFAULT_SAMPLE_PATH):
        with open(DEFAULT_SAMPLE_PATH, "rb") as f:
            return validate_and_parse_csv(f.read())
    return pd.DataFrame(), None


def main():
    # Sidebar navigation and controls
    with st.sidebar:
        st.markdown("<h2 style='margin-bottom: 0.2rem;'>CloudLog Analytics</h2>", unsafe_allow_html=True)
        st.markdown(
            "<p style='color: #61655B; font-size: 0.85rem; margin-bottom: 1.25rem;'>"
            "MapReduce Log Processing Platform</p>",
            unsafe_allow_html=True,
        )

        navigation = st.radio(
            "Navigation",
            options=["Dashboard", "Inside MapReduce", "Benchmark", "Cloud Architecture"],
            index=0,
            label_visibility="collapsed",
        )

        st.markdown("<hr style='border: none; border-top: 1px solid #E2DFD8; margin: 1rem 0;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; color: #61655B; margin-bottom: 0.75rem;'>Data Source</h4>", unsafe_allow_html=True)

        dataset_mode = st.radio(
            "Select Dataset",
            options=["Default Sample (5,000 logs)", "Upload CSV File"],
            index=0,
            label_visibility="collapsed",
        )

        raw_df = pd.DataFrame()
        val_summary = None

        if dataset_mode == "Default Sample (5,000 logs)":
            raw_df, val_summary = load_default_sample()
        else:
            st.markdown(
                "<div style='font-size: 0.8rem; color: #52564C; background-color: #FFFFFF; border: 1px solid #E2DFD8; padding: 0.6rem; border-radius: 4px; margin-bottom: 0.5rem;'>"
                "<b>Schema:</b> timestamp, endpoint, method, status_code, response_time_ms<br>"
                "<b>Limits:</b> Max 5.0 MB | Max 50,000 rows"
                "</div>",
                unsafe_allow_html=True,
            )
            uploaded_file = st.file_uploader(
                "Upload Web Server Logs CSV",
                type=["csv"],
                help="Requires headers: timestamp, endpoint, method, status_code, response_time_ms",
            )
            if uploaded_file is not None:
                file_bytes = uploaded_file.getvalue()
                raw_df, val_summary = validate_and_parse_csv(file_bytes, file_size_bytes=len(file_bytes))
            else:
                st.info("Upload a CSV file or switch to Default Sample to explore the dashboard.")
                raw_df = pd.DataFrame()

        # Pre-aggregation filters
        st.markdown("<hr style='border: none; border-top: 1px solid #E2DFD8; margin: 1rem 0;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; color: #61655B; margin-bottom: 0.75rem;'>Pre-Aggregation Filters</h4>", unsafe_allow_html=True)

        filtered_records = []
        endpoint_empty_selection = False
        filter_fingerprint = ""

        if not raw_df.empty and "endpoint" in raw_df.columns:
            all_endpoints = sorted(raw_df["endpoint"].unique())
            selected_endpoints = st.multiselect(
                "Filter Endpoints",
                options=all_endpoints,
                default=all_endpoints,
            )

            if not selected_endpoints:
                endpoint_empty_selection = True

            # Date range filter
            min_ts = pd.to_datetime(raw_df["timestamp"], utc=True).min().to_pydatetime()
            max_ts = pd.to_datetime(raw_df["timestamp"], utc=True).max().to_pydatetime()

            date_range = st.date_input(
                "Date Range (UTC)",
                value=(min_ts.date(), max_ts.date()),
                min_value=min_ts.date(),
                max_value=max_ts.date(),
            )

            exec_mode = st.selectbox(
                "Execution Mode",
                options=["Serial (1 Process)", "Parallel (2 Processes)"],
                index=0,
                help="ProcessPoolExecutor runs 2 workers; falls back cleanly if environment restricts processes.",
            )

            # Apply filters before aggregation
            mask = raw_df["endpoint"].isin(selected_endpoints)
            if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                start_dt = datetime.combine(date_range[0], datetime.min.time(), tzinfo=timezone.utc)
                # Include the entire end date in UTC up to the start of the next day
                end_dt_exclusive = datetime.combine(date_range[1] + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
                ts_series = pd.to_datetime(raw_df["timestamp"], utc=True)
                mask = mask & (ts_series >= start_dt) & (ts_series < end_dt_exclusive)

            filtered_df = raw_df[mask]
            filtered_records = filtered_df.to_dict(orient="records")
            filter_fingerprint = f"{dataset_mode}_{len(filtered_records)}_{tuple(selected_endpoints)}_{date_range}"
        else:
            exec_mode = "Serial (1 Process)"

    # Main content router
    if navigation == "Dashboard":
        render_dashboard(raw_df, val_summary, filtered_records, exec_mode, endpoint_empty_selection)
    elif navigation == "Inside MapReduce":
        render_inside_mapreduce(filtered_records, exec_mode, endpoint_empty_selection)
    elif navigation == "Benchmark":
        render_benchmark(filtered_records, filter_fingerprint, endpoint_empty_selection)
    elif navigation == "Cloud Architecture":
        render_cloud_architecture()


def render_dashboard(raw_df, val_summary, filtered_records, exec_mode, endpoint_empty_selection=False):
    # Header
    st.markdown("<h1 style='margin-bottom: 0.1rem; font-size: 1.85rem;'>CloudLog Analytics</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color: #61655B; font-size: 1.0rem; margin-bottom: 1.25rem;'>"
        "Web server log analytics engine powered by a single-host MapReduce pipeline."
        "</p>",
        unsafe_allow_html=True,
    )

    # Ingestion summary notices
    if val_summary:
        if not val_summary.is_valid:
            st.markdown(
                f"<div class='warning-box'><b>Upload Rejected:</b> {val_summary.error_message}</div>",
                unsafe_allow_html=True,
            )
            return

        if val_summary.rejected_rows > 0:
            reasons_str = ", ".join(f"{k}: {v}" for k, v in val_summary.rejection_reasons.items())
            st.markdown(
                f"<div class='warning-box'>"
                f"<b>Dataset Quality Notice:</b> Accepted {val_summary.accepted_rows:,} rows; "
                f"rejected {val_summary.rejected_rows:,} malformed rows ({reasons_str})."
                f"</div>",
                unsafe_allow_html=True,
            )

    if endpoint_empty_selection:
        st.markdown(
            "<div class='notice-box'><b>No endpoints selected:</b> Please select at least one endpoint from the sidebar filter controls to view analytics.</div>",
            unsafe_allow_html=True,
        )
        return

    if not filtered_records:
        if raw_df.empty:
            st.markdown(
                "<div class='notice-box'>No log records available. Select the built-in sample or upload a valid CSV.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='notice-box'>Current filter settings matched 0 records. Adjust the endpoint or date selection in the sidebar.</div>",
                unsafe_allow_html=True,
            )
        return

    # Execute MapReduce pipeline
    run_mode = "process" if "Parallel" in exec_mode else "serial"
    mr_result = execute_mapreduce_pipeline(filtered_records, mode=run_mode, num_partitions=2)

    if mr_result.fallback_reason:
        st.markdown(
            f"<div class='warning-box'><b>Execution Mode Notice:</b> {mr_result.fallback_reason}</div>",
            unsafe_allow_html=True,
        )

    # Status subline
    st.markdown(
        f"<div style='font-size: 0.85rem; color: #61655B; margin-bottom: 1rem;'>"
        f"Active Dataset: <b>{len(filtered_records):,} records</b> &nbsp;|&nbsp; "
        f"Pipeline Mode: <b>{mr_result.mode_executed}</b> &nbsp;|&nbsp; "
        f"MapReduce Execution Time: <b>{mr_result.execution_time_ms:.1f} ms</b>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Key metrics horizontal strip
    m = mr_result.metrics
    error_class = "metric-error-highlight" if m.error_rate_pct > 5.0 else ""
    st.markdown(
        f"""
        <div class="metric-strip">
            <div class="metric-item">
                <div class="metric-label">Total Requests</div>
                <div class="metric-value">{m.total_requests:,}</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">Error Rate (4xx/5xx)</div>
                <div class="metric-value {error_class}">{m.error_rate_pct:.2f}<span class="metric-unit">%</span></div>
            </div>
            <div class="metric-item">
                <div class="metric-label">Mean Latency</div>
                <div class="metric-value">{m.mean_response_time_ms:.1f}<span class="metric-unit">ms</span></div>
            </div>
            <div class="metric-item">
                <div class="metric-label">Latency Range</div>
                <div class="metric-value" style="font-size: 1.25rem; padding-top: 0.35rem;">{m.min_response_time_ms:.0f} - {m.max_response_time_ms:.0f}<span class="metric-unit">ms</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Visualizations layout: Prominent horizontal bar for endpoints, followed by timeline and status
    col_main, col_side = st.columns([1.6, 1.0])
    with col_main:
        fig_ep = create_endpoint_bar_chart(mr_result.by_endpoint)
        st.plotly_chart(fig_ep, use_container_width=True)

    with col_side:
        fig_sc = create_status_code_chart(mr_result.by_status_code)
        st.plotly_chart(fig_sc, use_container_width=True)

    # Timeline across full width
    fig_time = create_timeline_chart(mr_result.by_hour)
    st.plotly_chart(fig_time, use_container_width=True)

    # Tabulated aggregated outputs and downloads
    st.markdown("<h3 style='font-size: 1.15rem; margin-top: 1.5rem; margin-bottom: 0.75rem;'>Aggregated Results</h3>", unsafe_allow_html=True)
    tab_ep, tab_sc, tab_hr = st.tabs(["Endpoint Summary", "Status Code Summary", "Hourly Summary"])

    with tab_ep:
        st.dataframe(
            mr_result.by_endpoint.rename(columns={
                "endpoint": "Endpoint",
                "request_count": "Requests",
                "error_count": "Errors",
                "error_rate_pct": "Error Rate (%)",
                "mean_response_time_ms": "Mean Latency (ms)",
                "share_pct": "Traffic Share (%)",
            }),
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            label="Download Endpoint Aggregates (CSV)",
            data=mr_result.by_endpoint.to_csv(index=False),
            file_name="endpoint_aggregates.csv",
            mime="text/csv",
        )

    with tab_sc:
        st.dataframe(
            mr_result.by_status_code.rename(columns={
                "status_code": "HTTP Status",
                "request_count": "Count",
                "mean_response_time_ms": "Mean Latency (ms)",
                "share_pct": "Share (%)",
            }),
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            label="Download Status Code Aggregates (CSV)",
            data=mr_result.by_status_code.to_csv(index=False),
            file_name="status_code_aggregates.csv",
            mime="text/csv",
        )

    with tab_hr:
        st.dataframe(
            mr_result.by_hour.rename(columns={
                "hour_bucket": "Hour Bucket (UTC)",
                "request_count": "Requests",
                "error_count": "Errors",
                "error_rate_pct": "Error Rate (%)",
                "mean_response_time_ms": "Mean Latency (ms)",
                "share_pct": "Share (%)",
            }),
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            label="Download Hourly Aggregates (CSV)",
            data=mr_result.by_hour.to_csv(index=False),
            file_name="hourly_aggregates.csv",
            mime="text/csv",
        )


def render_inside_mapreduce(filtered_records, exec_mode, endpoint_empty_selection=False):
    st.markdown("<h1 style='font-size: 1.85rem; margin-bottom: 0.1rem;'>Inside MapReduce Pipeline</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color: #61655B; font-size: 1.0rem; margin-bottom: 1.25rem;'>"
        "Step-by-step breakdown of Partitioning, Mapping, Shuffling, Reducing, and Deriving metrics."
        "</p>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='notice-box'>"
        "<b>Educational Architecture Note:</b> This is a single-host educational MapReduce implementation "
        "written in pure Python, optionally parallelised across CPU cores using Python's <code>ProcessPoolExecutor</code>. "
        "It demonstrates the mathematical and structural primitives of MapReduce (partitioning, mapping, key shuffling, associative reduction) "
        "without requiring an external Apache Hadoop or multi-node cluster."
        "</div>",
        unsafe_allow_html=True,
    )

    if endpoint_empty_selection:
        st.markdown(
            "<div class='notice-box'><b>No endpoints selected:</b> Please select at least one endpoint from the sidebar filter controls to inspect the pipeline.</div>",
            unsafe_allow_html=True,
        )
        return

    if not filtered_records:
        st.warning("No records selected. Load data in the sidebar to inspect the pipeline.")
        return

    run_mode = "process" if "Parallel" in exec_mode else "serial"
    mr_result = execute_mapreduce_pipeline(filtered_records, mode=run_mode, num_partitions=2)
    stage = mr_result.stage_output
    traced_str = ", ".join(stage.traced_sample_keys) if stage.traced_sample_keys else "N/A"

    # Stage 1: Partitioning
    st.markdown(
        f"""
        <div class="stage-card">
            <span class="stage-badge">Stage 1</span>
            <div class="stage-title">Data Partitioning</div>
            <div class="stage-desc">
                The validated input dataset of <b>{len(filtered_records):,} records</b> is split into 
                <b>{len(stage.partition_counts)} disjoint partitions</b> for independent worker processing.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Partition 0 Size", f"{stage.partition_counts[0]:,} records")
    with col2:
        st.metric("Partition 1 Size", f"{stage.partition_counts[1]:,} records")

    # Stage 2: Map Phase
    st.markdown(
        f"""
        <div class="stage-card" style="margin-top: 1.5rem;">
            <span class="stage-badge">Stage 2</span>
            <div class="stage-title">Map Phase (Record Transformation)</div>
            <div class="stage-desc">
                Each worker process maps individual records into uniform key-value pairs:<br>
                <code>key &rarr; (count=1, error_count, response_time_ms)</code>.<br>
                Below is a bounded sample of emitted pairs for traced endpoint(s) <code>{traced_str}</code> from Partition 0:
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    sample_emitted_df = pd.DataFrame([
        {
            "Key (Endpoint)": str(pair[0]),
            "Emitted Value (count, is_error, response_time_ms)": str(pair[1]),
        }
        for pair in stage.sample_emitted_pairs
    ])
    st.table(sample_emitted_df)

    # Stage 3: Shuffle and Group Phase
    st.markdown(
        f"""
        <div class="stage-card" style="margin-top: 1.5rem;">
            <span class="stage-badge">Stage 3</span>
            <div class="stage-title">Shuffle & Group Phase</div>
            <div class="stage-desc">
                Emitted pairs from all partition outputs are grouped by their distinct key across partitions. 
                Values for traced endpoint(s) <code>{traced_str}</code> are brought together into an aggregated iterable:
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    sample_grouped_df = pd.DataFrame([
        {
            "Key": str(item[0]),
            "Grouped Values List (sample preview)": str(item[1]) + (" ..." if len(item[1]) >= 5 else ""),
        }
        for item in stage.sample_grouped_pairs
    ])
    st.table(sample_grouped_df)

    # Stage 4: Reduce Phase
    st.markdown(
        f"""
        <div class="stage-card" style="margin-top: 1.5rem;">
            <span class="stage-badge">Stage 4</span>
            <div class="stage-title">Reduce Phase</div>
            <div class="stage-desc">
                The reducer combines grouped tuples for <code>{traced_str}</code> into cumulative totals:
                <code>sum(count)</code>, <code>sum(error_count)</code>, and <code>sum(response_time_ms)</code>.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    sample_reduced_df = pd.DataFrame([
        {
            "Key": r["key"],
            "Total Requests": r["request_count"],
            "Total Errors": r["error_count"],
            "Cumulative Latency Sum (ms)": f"{r['sum_response_time_ms']:,.1f}",
        }
        for r in stage.sample_reduced_records
    ])
    st.table(sample_reduced_df)

    # Stage 5: Derive Phase
    st.markdown(
        """
        <div class="stage-card" style="margin-top: 1.5rem;">
            <span class="stage-badge">Stage 5</span>
            <div class="stage-title">Derive Phase (True Weighted Metrics)</div>
            <div class="stage-desc">
                Final analytical metrics are derived directly from global sums and counts:
                <br>&bull; <code>Mean Latency = Total Latency Sum / Total Requests</code>
                <br>&bull; <code>Error Rate % = (Total Errors / Total Requests) &times; 100</code>
                <br><br>
                <b>Statistical Integrity:</b> Computing the mean from aggregate sums ensures true weighted averages. 
                Averaging pre-computed partition averages would introduce Simpson's paradox when partition sizes vary.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Contrast Sample Traced Results vs Full Dataset Results
    st.markdown("<b>Sample Traced Keys Derived Results:</b>", unsafe_allow_html=True)
    if stage.sample_derived_records:
        st.table(pd.DataFrame(stage.sample_derived_records).rename(columns={
            "endpoint": "Endpoint",
            "request_count": "Requests",
            "error_count": "Errors",
            "error_rate_pct": "Error Rate (%)",
            "mean_response_time_ms": "Mean Latency (ms)",
            "share_pct": "Share of Dataset (%)",
        }))

    st.markdown(
        f"<b>Full Filtered Dataset Derived Totals ({len(filtered_records):,} records):</b>",
        unsafe_allow_html=True,
    )
    st.table(pd.DataFrame([{
        "Total Filtered Requests": f"{mr_result.metrics.total_requests:,}",
        "Total HTTP Errors": f"{mr_result.metrics.total_errors:,}",
        "Global Error Rate": f"{mr_result.metrics.error_rate_pct:.2f}%",
        "Global Weighted Mean Latency": f"{mr_result.metrics.mean_response_time_ms:.1f} ms",
        "Latency Span": f"{mr_result.metrics.min_response_time_ms:.0f} - {mr_result.metrics.max_response_time_ms:.0f} ms",
    }]))


def render_benchmark(filtered_records, current_fingerprint="", endpoint_empty_selection=False):
    st.markdown("<h1 style='font-size: 1.85rem; margin-bottom: 0.1rem;'>Pipeline Performance Benchmark</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color: #61655B; font-size: 1.0rem; margin-bottom: 1.25rem;'>"
        "Rigorous comparison of Serial vs 2-Process MapReduce execution on identical datasets."
        "</p>",
        unsafe_allow_html=True,
    )

    if endpoint_empty_selection:
        st.markdown(
            "<div class='notice-box'><b>No endpoints selected:</b> Please select at least one endpoint from the sidebar filter controls to run benchmarks.</div>",
            unsafe_allow_html=True,
        )
        return

    if not filtered_records:
        st.warning("No records selected. Load data in the sidebar before running benchmarks.")
        return

    bench = st.session_state.get("benchmark_comparison")
    stored_fingerprint = st.session_state.get("benchmark_fingerprint")
    is_stale = (bench is not None and stored_fingerprint != current_fingerprint)

    st.markdown(
        f"<div class='notice-box'>"
        f"Click the button below to execute both <b>Serial (1 Process)</b> and <b>Parallel (2 Processes)</b> "
        f"pipelines on the active <b>{len(filtered_records):,} validated records</b>. "
        f"High-precision timers measure actual wall-clock processing time on this host, and an automated check verifies execution equivalence (exact integer counts, 0.01 ms latency tolerance, and 0.01 percentage points for percentage metrics)."
        f"</div>",
        unsafe_allow_html=True,
    )

    if st.button("Run Benchmark on Current Dataset"):
        with st.spinner("Executing benchmark pipelines..."):
            bench = run_benchmark(filtered_records)
            st.session_state["benchmark_comparison"] = bench
            st.session_state["benchmark_fingerprint"] = current_fingerprint
            is_stale = False

    if bench is not None:
        if is_stale:
            st.markdown(
                "<div class='warning-box'>"
                "<b>Notice: Configuration Changed.</b> The benchmark results displayed below were measured for a previous dataset or filter configuration. "
                "Click <i>'Run Benchmark on Current Dataset'</i> to benchmark the currently active data."
                "</div>",
                unsafe_allow_html=True,
            )

        # Equivalence Verification Banner
        if bench.results_match:
            st.markdown(
                "<div style='background-color: #FFFFFF; border-left: 3px solid #526044; border-top: 1px solid #E2DFD8; border-right: 1px solid #E2DFD8; border-bottom: 1px solid #E2DFD8; padding: 0.75rem 1rem; border-radius: 0 4px 4px 0; margin-bottom: 1rem;'>"
                "<b style='color: #526044;'>Verification Passed:</b> Serial and Process executions matched across grouping keys, integer counts, and derived aggregates (tolerance: 0.01 ms for latency, 0.01 percentage points for percentage metrics)."
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='warning-box'><b>Verification Warning:</b> Discrepancies detected: {bench.discrepancy_details}</div>",
                unsafe_allow_html=True,
            )

        # Timing metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Serial Execution Time", f"{bench.serial_time_ms:.1f} ms")
        with col2:
            st.metric(f"Parallel Execution ({bench.mode_actually_executed})", f"{bench.process_time_ms:.1f} ms")
        with col3:
            st.metric("Speedup Ratio (Serial / Parallel)", f"{bench.speedup_factor:.2f}x")

        # Chart
        fig_bench = create_benchmark_comparison_chart(
            bench.serial_time_ms,
            bench.process_time_ms,
            bench.mode_actually_executed,
        )
        st.plotly_chart(fig_bench, use_container_width=True)

        # Honest educational explanation
        st.markdown("<h4 style='font-size: 1.05rem; margin-top: 1rem;'>Analysis and Computational Trade-Offs</h4>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='notice-box' style='line-height: 1.5;'>"
            f"<b>Measured Reality:</b> {bench.explanation}<br><br>"
            f"<b>Host-Specific Observation:</b> Measured execution runtimes are observations from this specific host machine and OS environment, illustrating fixed process startup and serialization trade-offs rather than universal performance guarantees.<br><br>"
            f"<b>Why multiprocessing can be slower for moderate datasets:</b><br>"
            f"&bull; <b>Process Spawning:</b> Creating child processes requires OS kernel allocations.<br>"
            f"&bull; <b>Pickling Overhead:</b> Python must serialize (pickle) records to pass across IPC process boundaries.<br>"
            f"&bull; <b>IPC Synchronization:</b> Gathering partition outputs back into the parent process incurs memory copying.<br>"
            f"In cloud distributed systems (such as AWS EMR, Databricks, or Hadoop), MapReduce pays off when data volumes "
            f"cannot fit into single-machine memory or CPU cache (terabytes to petabytes), rather than modest memory-resident datasets."
            f"</div>",
            unsafe_allow_html=True,
        )


def render_cloud_architecture():
    st.markdown("<h1 style='font-size: 1.85rem; margin-bottom: 0.1rem;'>Cloud Architecture & System Design</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color: #61655B; font-size: 1.0rem; margin-bottom: 1.5rem;'>"
        "Technical overview of the hosting model, runtime constraints, and trade-offs."
        "</p>",
        unsafe_allow_html=True,
    )

    # Architecture Overview
    st.markdown("<h3 style='font-size: 1.15rem; margin-bottom: 0.5rem;'>1. End-to-End System Flow</h3>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="stage-card">
            <div style="font-family: monospace; font-size: 0.9rem; line-height: 1.6; color: #252823;">
                <b>Client Web Browser</b><br>
                &nbsp;&nbsp;&darr; (HTTPS / WebSocket request)<br>
                <b>Streamlit Community Cloud (Managed PaaS Container)</b><br>
                &nbsp;&nbsp;&darr; (Payload validation & 5 MB / 50k row limits check)<br>
                <b>cloudlog.validator</b> (Schema enforcement & rejection categorization)<br>
                &nbsp;&nbsp;&darr; (Disjoint record chunking)<br>
                <b>cloudlog.mapreduce Partition & Map</b> (Picklable worker functions / ProcessPoolExecutor)<br>
                &nbsp;&nbsp;&darr; (Key aggregation across partition streams)<br>
                <b>Shuffle & Group</b> (Dictionary-backed accumulator)<br>
                &nbsp;&nbsp;&darr; (Associative reduction & metric derivation)<br>
                <b>Reduce & Derive</b> (True weighted means & error percentages)<br>
                &nbsp;&nbsp;&darr; (Custom Plotly visualizations & CSV export)<br>
                <b>Browser Dashboard Presentation</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Managed PaaS vs IaaS
    st.markdown("<h3 style='font-size: 1.15rem; margin-top: 1.5rem; margin-bottom: 0.5rem;'>2. Hosting Strategy: Managed PaaS vs. Self-Managed EC2 VM</h3>", unsafe_allow_html=True)
    comparison_data = [
        {
            "Dimension": "Infrastructure Management",
            "Streamlit Community Cloud (Current)": "Zero OS/VM administration; automated container provisioning from Git",
            "Self-Managed Amazon EC2 (IaaS)": "Requires manual AMI setup, Linux patching, security groups, SSH keys",
        },
        {
            "Dimension": "Cost & Credit Requirements",
            "Streamlit Community Cloud (Current)": "100% Free tier; no credit card or billing risk for university demo",
            "Self-Managed Amazon EC2 (IaaS)": "Requires AWS account, billing threshold monitoring, risk of unexpected charges",
        },
        {
            "Dimension": "Application Lifecycle",
            "Streamlit Community Cloud (Current)": "Serverless container model; sleeps on inactivity, boots on request",
            "Self-Managed Amazon EC2 (IaaS)": "Persistent virtual machine running continuously until stopped",
        },
        {
            "Dimension": "Data Persistence",
            "Streamlit Community Cloud (Current)": "Transient in-memory execution; uploads discarded on session teardown",
            "Self-Managed Amazon EC2 (IaaS)": "Attached EBS block storage volumes retain data across reboots",
        },
        {
            "Dimension": "Concurrency & Cores",
            "Streamlit Community Cloud (Current)": "Bounded shared vCPU; graceful fallback to serial mode when restricted",
            "Self-Managed Amazon EC2 (IaaS)": "Dedicated vCPU based on instance type (e.g. t3.micro vs c6i.xlarge)",
        },
    ]
    st.table(pd.DataFrame(comparison_data).set_index("Dimension"))

    # Operational Boundaries and Honest Limitations
    st.markdown("<h3 style='font-size: 1.15rem; margin-top: 1.5rem; margin-bottom: 0.5rem;'>3. Cloud Boundaries & Honest Operational Realities</h3>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="notice-box" style="line-height: 1.55;">
            <b>Boundary Distinctions:</b><br>
            &bull; <b>Single-Host Teaching Pipeline:</b> This application executes MapReduce algorithms on a single host 
            using multiple Python processes. It is not an Apache Hadoop cluster spanning multiple rack-mounted servers. 
            There is no distributed file system (HDFS) or cluster resource manager (YARN).<br>
            &bull; <b>No Permanent Upload Storage:</b> Uploaded log CSVs are parsed in transient RAM buffers and 
            never persisted to durable cloud storage (S3/GCS). Closing the browser session destroys the in-memory state.<br>
            &bull; <b>Observed Latency vs. Contractual SLA:</b> The execution times reported in this dashboard represent 
            observed wall-clock runtimes in a shared multitenant container. They do not constitute an uptime SLA 
            (e.g., AWS 99.99% availability). Free PaaS tiers have no guaranteed compute availability.<br>
            &bull; <b>Defensive Resource Bounds:</b> To prevent container out-of-memory (OOM) termination on shared cloud infrastructure, 
            the application strictly enforces a <b>5.0 MB file size limit</b> and a <b>50,000-row processing ceiling</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
