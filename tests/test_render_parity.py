"""CPU vs GPU single-frame pixel parity tests."""
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pytest
from PIL import Image, ImageDraw

from effect_engine import calculate_effect_parameters, toggles_from_dict
from gpu_renderer import cuda_available, prepare_gpu_frame_render_state, render_single_frame_gpu
from video_renderer import (
    AspectRatio,
    RenderSettings,
    fit_image_to_frame,
    prepare_frame_render_state,
    render_single_frame_cpu,
    resolve_render_dimensions,
)

FIXTURES = Path(__file__).parent / "fixtures"
TEST_IMAGE = FIXTURES / "test_image.png"


@dataclass
class FixtureAudioFeatures:
    duration: float
    beat_times: List[float]
    beat_strengths: List[float]
    onset_times: List[float]
    onset_strengths: List[float]
    energy_envelope: List[Tuple[float, float]]
    low_freq_energy: List[Tuple[float, float]]
    mid_freq_energy: List[Tuple[float, float]]
    high_freq_energy: List[Tuple[float, float]]
    tempo: float = 120.0
    sample_rate: int = 22050
    bass_energy: List[Tuple[float, float]] = field(default_factory=list)
    mid_energy: List[Tuple[float, float]] = field(default_factory=list)
    high_energy: List[Tuple[float, float]] = field(default_factory=list)
    onset_density: float = 0.0
    average_bass: float = 0.0
    average_mid: float = 0.0
    average_high: float = 0.0
    dynamic_range: float = 0.0
    beat_strength_variance: float = 0.0
    average_energy: float = 0.0


def _ensure_test_image() -> Path:
    if TEST_IMAGE.exists():
        return TEST_IMAGE
    img = Image.new("RGBA", (540, 960), (30, 40, 60, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse([170, 280, 370, 680], fill=(220, 180, 140, 255))
    draw.rectangle([0, 800, 540, 960], fill=(80, 120, 90, 255))
    TEST_IMAGE.parent.mkdir(parents=True, exist_ok=True)
    img.save(TEST_IMAGE)
    return TEST_IMAGE


def _load_audio_features(data: dict) -> FixtureAudioFeatures:
    af = data["audio_features"]
    return FixtureAudioFeatures(
        duration=af["duration"],
        beat_times=af["beat_times"],
        beat_strengths=af["beat_strengths"],
        onset_times=af["onset_times"],
        onset_strengths=af["onset_strengths"],
        energy_envelope=[tuple(x) for x in af["energy_envelope"]],
        low_freq_energy=[tuple(x) for x in af["low_freq_energy"]],
        mid_freq_energy=[tuple(x) for x in af["mid_freq_energy"]],
        high_freq_energy=[tuple(x) for x in af["high_freq_energy"]],
        tempo=af.get("tempo", 120.0),
        onset_density=af.get("onset_density", 0.0),
        average_bass=af.get("average_bass", 0.0),
        average_mid=af.get("average_mid", 0.0),
        average_high=af.get("average_high", 0.0),
        dynamic_range=af.get("dynamic_range", 0.0),
        beat_strength_variance=af.get("beat_strength_variance", 0.0),
        average_energy=af.get("average_energy", 0.0),
    )


def _compare_frames(cpu_img: Image.Image, gpu_img: Image.Image) -> Tuple[float, float]:
    cpu_rgb = np.asarray(cpu_img.convert("RGB"), dtype=np.float32)
    gpu_rgb = np.asarray(gpu_img.convert("RGB"), dtype=np.float32)
    diff = np.abs(cpu_rgb - gpu_rgb)
    return float(diff.mean()), float(diff.max())


def _render_pair_at_time(
    effect_params,
    base_image,
    width,
    height,
    resampling,
    time_sec: float,
    seed: int,
):
    random.seed(seed)
    np.random.seed(seed)

    cpu_state = prepare_frame_render_state(
        base_image, effect_params, width, height, resampling,
    )
    gpu_state = prepare_gpu_frame_render_state(
        base_image, effect_params, width, height, resampling,
    )

    dt = 1.0 / 30.0
    random.seed(seed)
    np.random.seed(seed)
    cpu_frame = render_single_frame_cpu(cpu_state, effect_params, time_sec, dt)
    random.seed(seed)
    np.random.seed(seed)
    gpu_frame = render_single_frame_gpu(gpu_state, effect_params, time_sec, dt)
    return cpu_frame, gpu_frame


@pytest.mark.gpu
@pytest.mark.skipif(not cuda_available(), reason="CUDA not available")
@pytest.mark.parametrize("preset_name", [
    "default_toggles",
    "glow_only",
    "scale_only",
    "vignette_only",
    "particles_only",
    "background_dim",
    "ripple_wave",
])
def test_cpu_gpu_frame_parity(preset_name: str):
    parity_data = json.loads((FIXTURES / "effect_parity.json").read_text())
    presets_data = json.loads((FIXTURES / "gpu_effect_presets.json").read_text())
    preset = next(p for p in presets_data["presets"] if p["name"] == preset_name)

    if preset.get("fixture"):
        toggles_dict = parity_data["toggles"]
        sample_times = parity_data["sample_times"]
    else:
        toggles_dict = preset["toggles"]
        sample_times = parity_data["sample_times"]

    features = _load_audio_features(parity_data)
    toggles = toggles_from_dict(toggles_dict)
    effect_params = calculate_effect_parameters(features, toggles)

    settings = RenderSettings(aspect_ratio=AspectRatio.VERTICAL, preview=True)
    width, height, resampling = resolve_render_dimensions(settings)
    base_image = fit_image_to_frame(
        Image.open(_ensure_test_image()).convert("RGBA"),
        width,
        height,
        resampling,
    )

    for i, time_sec in enumerate(sample_times):
        cpu_frame, gpu_frame = _render_pair_at_time(
            effect_params, base_image, width, height, resampling, time_sec, seed=42 + i,
        )
        mean_diff, max_diff = _compare_frames(cpu_frame, gpu_frame)
        assert mean_diff < 5.0, (
            f"{preset_name} @ t={time_sec}: mean diff {mean_diff:.2f} >= 5.0"
        )
        assert max_diff < 20.0, (
            f"{preset_name} @ t={time_sec}: max diff {max_diff:.2f} >= 20"
        )
