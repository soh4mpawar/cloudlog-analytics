"""Styling module for CloudLog Analytics.

Implements a restrained editorial theme adhering strictly to:
- Background: Warm Ivory (#F7F5F0)
- Surface: White (#FFFFFF)
- Text: Charcoal (#252823)
- Accent: Dark Olive (#526044)
- Error / Highlight: Muted Terracotta (#B65C3A)
- Borders: Subtle Warm Grey (#E2DFD8)
- Zero Blue or Purple anywhere.
"""

CUSTOM_CSS = """
<style>
/* Global resets & typography */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #F7F5F0 !important;
    color: #252823 !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
}

[data-testid="stHeader"] {
    background-color: rgba(247, 245, 240, 0.9) !important;
}

[data-testid="stSidebar"] {
    background-color: #EFECE4 !important;
    border-right: 1px solid #E2DFD8 !important;
}

[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #252823 !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em !important;
}

/* Links and buttons */
a {
    color: #526044 !important;
    text-decoration: underline !important;
    text-underline-offset: 3px !important;
}
a:hover {
    color: #3b4631 !important;
}

/* Primary buttons */
.stButton > button {
    background-color: #526044 !important;
    color: #FFFFFF !important;
    border: 1px solid #526044 !important;
    border-radius: 4px !important;
    font-weight: 500 !important;
    padding: 0.45rem 1rem !important;
    transition: background-color 0.15s ease-in-out !important;
}
.stButton > button:hover {
    background-color: #404b35 !important;
    border-color: #404b35 !important;
    color: #FFFFFF !important;
}
.stButton > button:focus {
    box-shadow: 0 0 0 2px #E2DFD8, 0 0 0 4px #526044 !important;
    outline: none !important;
}

/* Secondary / Download buttons */
.stDownloadButton > button {
    background-color: #FFFFFF !important;
    color: #526044 !important;
    border: 1px solid #526044 !important;
    border-radius: 4px !important;
    font-weight: 500 !important;
    padding: 0.45rem 1rem !important;
}
.stDownloadButton > button:hover {
    background-color: #F7F5F0 !important;
    color: #3b4631 !important;
}

/* Radio buttons & Select boxes */
div[role="radiogroup"] label {
    color: #252823 !important;
}

/* Monospace text */
code, pre, .mono-text {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace !important;
    font-size: 0.88rem !important;
}

/* Metric Strip Container */
.metric-strip {
    display: flex;
    flex-direction: row;
    align-items: stretch;
    background-color: #FFFFFF;
    border: 1px solid #E2DFD8;
    border-radius: 4px;
    margin-bottom: 1.5rem;
    overflow-x: auto;
}
.metric-item {
    flex: 1;
    min-width: 140px;
    padding: 1rem 1.25rem;
    border-right: 1px solid #E2DFD8;
}
.metric-item:last-child {
    border-right: none;
}
.metric-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #61655B;
    margin-bottom: 0.25rem;
    font-weight: 600;
}
.metric-value {
    font-size: 1.65rem;
    font-weight: 600;
    color: #252823;
    line-height: 1.1;
}
.metric-unit {
    font-size: 0.85rem;
    font-weight: 400;
    color: #61655B;
    margin-left: 0.2rem;
}
.metric-error-highlight {
    color: #B65C3A !important;
}

/* Educational Stage Card */
.stage-card {
    background-color: #FFFFFF;
    border: 1px solid #E2DFD8;
    border-radius: 4px;
    padding: 1.1rem 1.25rem;
    margin-bottom: 1rem;
}
.stage-badge {
    display: inline-block;
    background-color: #EFECE4;
    color: #526044;
    border: 1px solid #E2DFD8;
    padding: 0.15rem 0.5rem;
    border-radius: 3px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
}
.stage-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #252823;
    margin-bottom: 0.35rem;
}
.stage-desc {
    font-size: 0.9rem;
    color: #52564C;
    line-height: 1.45;
    margin-bottom: 0.75rem;
}

/* Status / Alert callouts without generic icons */
.notice-box {
    background-color: #FFFFFF;
    border-left: 3px solid #526044;
    border-top: 1px solid #E2DFD8;
    border-right: 1px solid #E2DFD8;
    border-bottom: 1px solid #E2DFD8;
    padding: 0.75rem 1rem;
    border-radius: 0 4px 4px 0;
    font-size: 0.9rem;
    color: #252823;
    margin: 0.75rem 0;
}
.warning-box {
    background-color: #FFFDFB;
    border-left: 3px solid #B65C3A;
    border-top: 1px solid #E2DFD8;
    border-right: 1px solid #E2DFD8;
    border-bottom: 1px solid #E2DFD8;
    padding: 0.75rem 1rem;
    border-radius: 0 4px 4px 0;
    font-size: 0.9rem;
    color: #252823;
    margin: 0.75rem 0;
}

/* Compact data table headers */
[data-testid="stDataFrame"] {
    border: 1px solid #E2DFD8 !important;
    border-radius: 4px !important;
    background-color: #FFFFFF !important;
}

/* Responsive adjustments */
@media (max-width: 640px) {
    .metric-strip {
        flex-direction: column;
    }
    .metric-item {
        border-right: none;
        border-bottom: 1px solid #E2DFD8;
    }
    .metric-item:last-child {
        border-bottom: none;
    }
}
</style>
"""


def apply_custom_styles():
    """Returns CSS markup to be injected via st.markdown."""
    return CUSTOM_CSS
