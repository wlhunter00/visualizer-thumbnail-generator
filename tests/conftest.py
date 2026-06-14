import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def pytest_configure(config):
    config.addinivalue_line("markers", "gpu: requires CUDA and torch")
    config.addinivalue_line("markers", "integration: slow end-to-end tests")
