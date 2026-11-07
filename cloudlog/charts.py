"""Custom Plotly chart components for CloudLog Analytics.

Implements custom editorial styling:
- Palette: Dark Olive (#526044), Terracotta (#B65C3A), Ochre (#C49A45), Sage (#7A8B6E), Stone (#6B705C)
- Strict ban on blue and purple.
- Quiet gridlines, explicit units (ms, reqs, %), clean typography.
"""

import pandas as pd
import plotly.graph_objects as go

# Custom palette strictly without blue or purple
PALETTE = {
    "primary": "#526044",       # Dark Olive
    "error": "#B65C3A",         # Muted Terracotta
    "accent_warm": "#C49A45",   # Ochre / Warm Amber
    "accent_sage": "#7A8B6E",   # Sage Green
    "stone": "#6B705C",         # Olive Stone
    "chestnut": "#8C6D58",      # Warm Chestnut
    "background": "#FFFFFF",
    "text": "#252823",
    "text_muted": "#61655B",
    "grid": "#E8E5DD",
    "border": "#E2DFD8",
}

BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(
        family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
        color=PALETTE["text"],
        size=12,
    ),
    margin=dict(l=40, r=20, t=35, b=40),
    hoverlabel=dict(
        bgcolor="#FFFFFF",
        bordercolor=PALETTE["border"],
        font=dict(color=PALETTE["text"], size=12),
    ),
)


def create_endpoint_bar_chart(df_endpoint: pd.DataFrame) -> go.Figure:
    """Creates a horizontal bar chart of request volume by endpoint.

    Horizontal layout ensures long endpoint paths are legible without diagonal truncation.
    """
    fig = go.Figure()

    if df_endpoint.empty:
        fig.add_annotation(
            text="No data matching current filter criteria",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=PALETTE["text_muted"]),
        )
        fig.update_layout(**BASE_LAYOUT, height=280)
        return fig

    # Sort ascending so top endpoint appears at top of vertical axis
    df_sorted = df_endpoint.sort_values(by="request_count", ascending=True)

    # Hover text with explicit units
    hover_texts = [
        f"<b>{ep}</b><br>Requests: {cnt:,} ({pct}%)<br>Mean Latency: {mean_rt:.1f} ms<br>Error Rate: {err_rt:.1f}%"
        for ep, cnt, pct, mean_rt, err_rt in zip(
            df_sorted["endpoint"],
            df_sorted["request_count"],
            df_sorted["share_pct"],
            df_sorted["mean_response_time_ms"],
            df_sorted["error_rate_pct"],
        )
    ]

    fig.add_trace(go.Bar(
        x=df_sorted["request_count"],
        y=df_sorted["endpoint"],
        orientation="h",
        marker=dict(
            color=PALETTE["primary"],
            line=dict(color="#3F4B34", width=1),
        ),
        hoverinfo="text",
        hovertext=hover_texts,
        name="Requests",
    ))

    layout = dict(BASE_LAYOUT)
    layout.update(
        title=dict(
            text="Request Volume by Endpoint",
            font=dict(size=14, color=PALETTE["text"]),
            x=0.0,
        ),
        xaxis=dict(
            title="Total Requests",
            gridcolor=PALETTE["grid"],
            zeroline=True,
            zerolinecolor=PALETTE["border"],
            tickfont=dict(size=11, color=PALETTE["text_muted"]),
        ),
        yaxis=dict(
            autorange=True,
            tickfont=dict(family="monospace", size=11, color=PALETTE["text"]),
        ),
        height=max(260, 45 * len(df_sorted)),
    )
    fig.update_layout(**layout)
    return fig


def create_timeline_chart(df_hour: pd.DataFrame) -> go.Figure:
    """Creates a time-series bar chart showing total requests and error breakdown over time (UTC)."""
    fig = go.Figure()

    if df_hour.empty:
        fig.add_annotation(
            text="No temporal data matching current filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=PALETTE["text_muted"]),
        )
        fig.update_layout(**BASE_LAYOUT, height=280)
        return fig

    df_sorted = df_hour.sort_values(by="hour_bucket", ascending=True)
    success_counts = df_sorted["request_count"] - df_sorted["error_count"]

    fig.add_trace(go.Bar(
        x=df_sorted["hour_bucket"],
        y=success_counts,
        name="Success (2xx/3xx)",
        marker=dict(color=PALETTE["accent_sage"]),
        hovertemplate="<b>%{x} UTC</b><br>Successful: %{y:,}<extra></extra>",
    ))

    fig.add_trace(go.Bar(
        x=df_sorted["hour_bucket"],
        y=df_sorted["error_count"],
        name="Errors (4xx/5xx)",
        marker=dict(color=PALETTE["error"]),
        hovertemplate="<b>%{x} UTC</b><br>Errors: %{y:,}<extra></extra>",
    ))

    layout = dict(BASE_LAYOUT)
    layout.update(
        barmode="stack",
        title=dict(
            text="Requests over Time (Hourly Buckets, UTC)",
            font=dict(size=14, color=PALETTE["text"]),
            x=0.0,
        ),
        xaxis=dict(
            title="Time Bucket (UTC)",
            gridcolor=PALETTE["grid"],
            tickangle=-30,
            tickfont=dict(size=10, color=PALETTE["text_muted"]),
        ),
        yaxis=dict(
            title="Requests / Hour",
            gridcolor=PALETTE["grid"],
            zeroline=True,
            zerolinecolor=PALETTE["border"],
            tickfont=dict(size=11, color=PALETTE["text_muted"]),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            font=dict(size=11),
        ),
        height=320,
    )
    fig.update_layout(**layout)
    return fig


def create_status_code_chart(df_status: pd.DataFrame) -> go.Figure:
    """Creates a status code distribution bar chart."""
    fig = go.Figure()

    if df_status.empty:
        fig.add_annotation(
            text="No status code data",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=PALETTE["text_muted"]),
        )
        fig.update_layout(**BASE_LAYOUT, height=260)
        return fig

    df_sorted = df_status.sort_values(by="status_code", ascending=True)

    # Assign distinct muted earth colors based on status category
    colors = []
    for sc in df_sorted["status_code"]:
        code = int(sc)
        if 200 <= code < 300:
            colors.append(PALETTE["primary"])       # Olive
        elif 300 <= code < 400:
            colors.append(PALETTE["stone"])         # Stone
        elif 400 <= code < 500:
            colors.append(PALETTE["accent_warm"])   # Ochre
        elif code >= 500:
            colors.append(PALETTE["error"])         # Terracotta
        else:
            colors.append(PALETTE["accent_sage"])

    fig.add_trace(go.Bar(
        x=[str(sc) for sc in df_sorted["status_code"]],
        y=df_sorted["request_count"],
        marker=dict(color=colors),
        hovertemplate="<b>HTTP %{x}</b><br>Requests: %{y:,}<br>Mean Latency: %{customdata[0]:.1f} ms<br>Share: %{customdata[1]:.1f}%<extra></extra>",
        customdata=df_sorted[["mean_response_time_ms", "share_pct"]].values,
    ))

    layout = dict(BASE_LAYOUT)
    layout.update(
        title=dict(
            text="HTTP Status Code Distribution",
            font=dict(size=14, color=PALETTE["text"]),
            x=0.0,
        ),
        xaxis=dict(
            title="HTTP Status Code",
            type="category",
            tickfont=dict(family="monospace", size=11, color=PALETTE["text"]),
        ),
        yaxis=dict(
            title="Count",
            gridcolor=PALETTE["grid"],
            zeroline=True,
            zerolinecolor=PALETTE["border"],
            tickfont=dict(size=11, color=PALETTE["text_muted"]),
        ),
        height=280,
    )
    fig.update_layout(**layout)
    return fig


def create_benchmark_comparison_chart(
    serial_time_ms: float,
    process_time_ms: float,
    mode_executed: str,
) -> go.Figure:
    """Creates an execution time comparison bar chart for benchmark view."""
    fig = go.Figure()

    labels = ["Serial (1 Core)", f"Parallel ({mode_executed})"]
    times = [serial_time_ms, process_time_ms]
    colors = [PALETTE["stone"], PALETTE["primary"]]

    fig.add_trace(go.Bar(
        x=labels,
        y=times,
        marker=dict(color=colors),
        text=[f"{t:.1f} ms" for t in times],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Execution Time: %{y:.2f} ms<extra></extra>",
    ))

    layout = dict(BASE_LAYOUT)
    layout.update(
        title=dict(
            text="Execution Time Comparison (Lower is Faster)",
            font=dict(size=14, color=PALETTE["text"]),
            x=0.0,
        ),
        yaxis=dict(
            title="Time (ms)",
            gridcolor=PALETTE["grid"],
            zeroline=True,
            zerolinecolor=PALETTE["border"],
        ),
        height=260,
    )
    fig.update_layout(**layout)
    return fig
