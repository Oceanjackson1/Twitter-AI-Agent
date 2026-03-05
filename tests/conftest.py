import pytest


def pytest_collection_modifyitems(config, items):
    """Mark all async test functions as asyncio."""
    for item in items:
        if item.get_closest_marker("asyncio") is None:
            if "async" in str(item.function):
                item.add_marker(pytest.mark.asyncio)
