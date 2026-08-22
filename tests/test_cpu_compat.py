"""Unit checks for CPU-only boxes: tempo coercion and NVENC/CUDA gating."""
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from audio_analysis import coerce_tempo
import video_renderer as vr

_HELPER_PATH = Path(__file__).resolve().parent.parent / "scripts" / "load_openai_key.py"
_HELPER_SPEC = importlib.util.spec_from_file_location("load_openai_key", _HELPER_PATH)
load_openai_key = importlib.util.module_from_spec(_HELPER_SPEC)
assert _HELPER_SPEC.loader is not None
_HELPER_SPEC.loader.exec_module(load_openai_key)


@pytest.fixture
def reset_nvenc_cache():
    previous = vr._nvenc_available_cache
    vr._nvenc_available_cache = None
    yield
    vr._nvenc_available_cache = previous


def test_coerce_tempo_length1_ndarray():
    assert coerce_tempo(np.array([128.5])) == pytest.approx(128.5)


def test_coerce_tempo_0d_ndarray():
    assert coerce_tempo(np.array(99.0)) == pytest.approx(99.0)


def test_coerce_tempo_python_float():
    assert coerce_tempo(120.0) == pytest.approx(120.0)


def test_cuda_present_false_without_device_or_libcuda():
    with patch.object(vr.os.path, "exists", return_value=False), \
         patch("ctypes.CDLL", side_effect=OSError("cannot load libcuda.so.1")):
        assert vr._cuda_present() is False


def test_cuda_present_true_when_nvidia_device_exists():
    with patch.object(vr.os.path, "exists", side_effect=lambda p: p == vr._NVIDIA_DEVICE):
        assert vr._cuda_present() is True


def test_nvenc_false_when_no_cuda_even_if_ffmpeg_lists_encoder(reset_nvenc_cache):
    fake = MagicMock()
    fake.returncode = 0
    fake.stdout = " V..... h264_nvenc           NVIDIA NVENC H.264 encoder\n"
    with patch.object(vr, "_cuda_present", return_value=False), \
         patch.object(vr.subprocess, "run", return_value=fake) as ffmpeg_run:
        assert vr._nvenc_available() is False
        ffmpeg_run.assert_not_called()


def test_export_encode_args_fall_back_to_libx264_without_cuda(reset_nvenc_cache):
    with patch.object(vr, "_cuda_present", return_value=False):
        args, label = vr._ffmpeg_video_encode_args("medium", preview=False)
    assert label == "libx264"
    assert args[:2] == ["-c:v", "libx264"]


def test_preview_encode_args_always_libx264():
    with patch.object(vr, "_nvenc_available", return_value=True):
        args, label = vr._ffmpeg_video_encode_args("high", preview=True)
    assert label == "libx264"
    assert args[:2] == ["-c:v", "libx264"]


def test_openai_key_placeholder_is_not_real():
    assert load_openai_key.is_real_key(None) is False
    assert load_openai_key.is_real_key("") is False
    assert load_openai_key.is_real_key("sk-your-api-key-here") is False
    assert load_openai_key.is_real_key("sk-test-not-a-real-secret") is True


def test_openai_key_prefers_env_over_connector(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=sk-your-api-key-here\n", encoding="utf-8")
    connector = tmp_path / "openai.json"
    connector.write_text('{"api_key": "sk-from-connector-dummy"}', encoding="utf-8")

    key, source = load_openai_key.resolve_openai_key(
        env={"OPENAI_API_KEY": "sk-already-in-env-dummy"},
        env_file=env_file,
        connector_json=connector,
    )
    assert source == "env"
    assert key is not None
    assert len(key) == len("sk-already-in-env-dummy")


def test_openai_key_loads_connector_when_env_missing(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=sk-your-api-key-here\n", encoding="utf-8")
    connector = tmp_path / "openai.json"
    connector.write_text('{"api_key": "sk-from-connector-dummy"}', encoding="utf-8")

    key, source = load_openai_key.resolve_openai_key(
        env={},
        env_file=env_file,
        connector_json=connector,
    )
    assert source == "connector"
    assert key is not None
    assert len(key) == len("sk-from-connector-dummy")
    status = load_openai_key.status_line(source, key)
    assert "connector" in status
    assert str(len(key)) in status
    assert "sk-from-connector-dummy" not in status
