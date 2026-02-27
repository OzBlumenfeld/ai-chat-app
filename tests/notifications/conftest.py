"""
Pytest configuration for notification tests.

This file provides custom pytest options and fixtures for email tests.
"""
import pytest


def pytest_addoption(parser):
    """Add custom pytest option for email integration tests"""
    parser.addoption(
        "--email-integration",
        action="store_true",
        default=False,
        help="run email integration tests (requires Gmail credentials)",
    )


def pytest_configure(config):
    """Register the marker"""
    config.addinivalue_line(
        "markers", "email_integration: mark test as requiring email integration"
    )


@pytest.fixture
def email_integration(request):
    """Skip tests if --email-integration flag not provided"""
    if not request.config.getoption("--email-integration"):
        pytest.skip("Email integration tests disabled. Use --email-integration to enable.")
