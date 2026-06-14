"""End-to-end GPU export smoke test (short clip, valid MP4)."""
import subprocess
import tempfile
import wave
from pathlib import Path

import pytest

from effect_engine import calculate_effect_parameters, toggles_from_dict
from gpu_renderer import cuda_available, render_video_gpu
from video_renderer import AspectRatio, RenderSettings

FIXTURES = Path(__file__).parent / "fixtures"


def _write_silent_wav(path: Path, duration_sec: float = 2.0, sample_rate: int = 22050):
    n_frames = int(duration_sec * sample_rate)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_frames)


@pytest.mark.gpu
@pytest.mark.integration
@pytest.mark.skipif(not cuda_available(), reason="CUDA not available")
def test_gpu_export_produces_valid_mp4():
    from test_render_parity import _ensure_test_image, _load_audio_features
    import json

    parity_data = json.loads((FIXTURES / "effect_parity.json").read_text())
    features = _load_audio_features(parity_data)
    toggles = toggles_from_dict(parity_data["toggles"])
    effect_params = calculate_effect_parameters(features, toggles)

    image_path = _ensure_test_image()

    with tempfile.TemporaryDirectory() as tmp:
        audio_path = Path(tmp) / "silent.wav"
        output_path = Path(tmp) / "out.mp4"
        _write_silent_wav(audio_path, duration_sec=2.0)

        render_settings = RenderSettings(
            aspect_ratio=AspectRatio.VERTICAL,
            fps=30,
            quality="medium",
            duration=2.0,
            preview=True,
        )

        render_video_gpu(
            image_path=str(image_path),
            audio_path=str(audio_path),
            output_path=str(output_path),
            effect_params=effect_params,
            render_settings=render_settings,
            audio_start=0.0,
        )

        assert output_path.exists()
        assert output_path.stat().st_size > 1000

        probe = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration:stream=codec_type",
                "-of", "default=noprint_wrappers=1",
                str(output_path),
            ],
            capture_output=True,
            text=True,
        )
        assert probe.returncode == 0
        assert "video" in probe.stdout
        assert "duration=" in probe.stdout
