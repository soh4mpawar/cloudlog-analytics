"""Integration tests for Streamlit application UI using Streamlit AppTest."""

import os
import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


def test_app_loads_dashboard_default():
    """Verifies that the app loads cleanly on the Dashboard view."""
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    assert not at.exception
    # Check that title is rendered
    assert len(at.title) > 0 or any("CloudLog Analytics" in m.value for m in at.markdown)


def test_app_navigate_to_inside_mapreduce():
    """Verifies switching navigation to 'Inside MapReduce' view."""
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    assert not at.exception

    # Radio 0 is the navigation radio
    at.sidebar.radio[0].set_value("Inside MapReduce").run()
    assert not at.exception
    assert any("Inside MapReduce Pipeline" in m.value for m in at.markdown)


def test_app_navigate_to_benchmark_and_run():
    """Verifies switching to 'Benchmark' view and clicking 'Run Benchmark on Current Dataset'."""
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    assert not at.exception

    at.sidebar.radio[0].set_value("Benchmark").run()
    assert not at.exception
    assert any("Performance Benchmark" in m.value for m in at.markdown)

    # Click benchmark button
    if len(at.button) > 0:
        at.button[0].click().run()
        assert not at.exception
        assert any("Verification Passed" in m.value or "Execution Time" in m.value for m in at.markdown)


def test_app_navigate_to_cloud_architecture():
    """Verifies switching to 'Cloud Architecture' view."""
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    assert not at.exception

    at.sidebar.radio[0].set_value("Cloud Architecture").run()
    assert not at.exception
    assert any("Cloud Architecture" in m.value for m in at.markdown)
