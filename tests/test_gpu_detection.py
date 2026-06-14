"""Unit tests for GPU renderer detection and routing (no hardware required)."""
from unittest.mock import MagicMock, patch

import pytest

from gpu_renderer import cuda_available, resolve_renderer


def test_cuda_available_false_on_import_error():
    with patch("gpu_renderer._import_torch", side_effect=ImportError("no torch")):
        assert cuda_available() is False


def test_cuda_available_uses_torch_cuda():
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    with patch("gpu_renderer._import_torch", return_value=(mock_torch, None, None)):
        assert cuda_available() is True


def test_resolve_renderer_auto_cpu_when_no_cuda():
    with patch("gpu_renderer.cuda_available", return_value=False):
        assert resolve_renderer("auto") == "cpu"


def test_resolve_renderer_auto_gpu_when_cuda():
    with patch("gpu_renderer.cuda_available", return_value=True):
        assert resolve_renderer("auto") == "gpu"


def test_resolve_renderer_cpu_forces_cpu():
    assert resolve_renderer("cpu") == "cpu"


def test_resolve_renderer_gpu_raises_without_cuda():
    with patch("gpu_renderer.cuda_available", return_value=False):
        with pytest.raises(RuntimeError, match="CUDA"):
            resolve_renderer("gpu")


def test_resolve_renderer_invalid_mode():
    with pytest.raises(ValueError, match="Invalid EXPORT_RENDERER"):
        resolve_renderer("invalid")
