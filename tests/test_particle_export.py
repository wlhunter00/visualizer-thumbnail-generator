"""Regression tests: exported frames must contain visible particles."""
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from effect_engine import calculate_effect_parameters, toggles_from_dict
from image_analysis import preprocess_particle_sprite
from video_renderer import (
    AspectRatio,
    ParticleSystem,
    RenderSettings,
    prepare_frame_render_state,
    render_single_frame_cpu,
    resolve_render_dimensions,
    _load_particle_sprite,
)

FIXTURES = Path(__file__).parent / "fixtures"
SYNTHETIC_SPRITE = FIXTURES / "synthetic_particle_sprite.png"


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


def _ensure_synthetic_sprite() -> Path:
    """1024x1024 black canvas with tiny soft glow — low mean alpha unless cropped."""
    SYNTHETIC_SPRITE.parent.mkdir(parents=True, exist_ok=True)
    glow = Image.new("L", (32, 32), 0)
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([4, 4, 28, 28], fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=4))
    img = Image.new("RGB", (1024, 1024), (0, 0, 0))
    img.paste(Image.merge("RGB", (glow, glow, glow)), (496, 496))
    img.save(SYNTHETIC_SPRITE)
    return SYNTHETIC_SPRITE


def _load_fixture_features() -> FixtureAudioFeatures:
    data = json.loads((FIXTURES / "effect_parity.json").read_text())
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
    )


def _pixel_diff(a: Image.Image, b: Image.Image) -> tuple[float, float]:
    arr_a = np.asarray(a.convert("RGB"), dtype=np.float32)
    arr_b = np.asarray(b.convert("RGB"), dtype=np.float32)
    diff = np.abs(arr_a - arr_b)
    return float(diff.mean()), float(diff.max())


def _render_at_time(toggles_dict: dict, time_sec: float, sprite_path: str | None = None):
    features = _load_fixture_features()
    toggles = toggles_from_dict(toggles_dict)
    effect_params = calculate_effect_parameters(features, toggles)

    settings = RenderSettings(aspect_ratio=AspectRatio.VERTICAL, preview=True)
    width, height, resampling = resolve_render_dimensions(settings)
    base = Image.new("RGBA", (width, height), (40, 50, 60, 255))
    draw = ImageDraw.Draw(base)
    draw.ellipse([170, 280, 370, 680], fill=(220, 180, 140, 255))

    state = prepare_frame_render_state(
        base, effect_params, width, height, resampling,
        custom_particle_sprite=sprite_path,
    )
    frame = render_single_frame_cpu(state, effect_params, time_sec, 1 / 30)
    return frame, state


def test_preprocess_sprite_crops_large_canvas():
    raw = Image.open(_ensure_synthetic_sprite()).convert("RGBA")
    processed = preprocess_particle_sprite(raw)
    assert processed is not None
    assert max(processed.size) < 200


def test_load_particle_sprite_applies_preprocess():
    path = _ensure_synthetic_sprite()
    loaded = _load_particle_sprite(path)
    assert loaded is not None
    assert max(loaded.size) < 200


def test_preprocessed_sprite_visible_when_drawn():
    path = str(_ensure_synthetic_sprite())
    sprite = _load_particle_sprite(path)
    assert sprite is not None
    system = ParticleSystem(sprite)
    system.spawn_burst_from_bounds(
        0.25, 0.25, 0.5, 0.5, 30,
        [(255, 255, 255)], (8, 16), 200, 1.0, 0.5,
        540, 960, 1.0,
    )
    base = Image.new("RGBA", (540, 960), (40, 50, 60, 255))
    out = system.draw(base, 0.5)
    mean_diff, max_diff = _pixel_diff(base, out)
    assert max_diff > 15


def test_particles_spawn_and_change_pixels_at_beat():
    presets = json.loads((FIXTURES / "gpu_effect_presets.json").read_text())
    toggles_on = next(p for p in presets["presets"] if p["name"] == "particles_only")["toggles"]
    toggles_off = {**toggles_on, "particle_burst": {"enabled": False, "intensity": 0.5}}

    frame_on, state_on = _render_at_time(toggles_on, 0.55)
    assert len(state_on.particle_system.particles) > 0

    frame_off, _ = _render_at_time(toggles_off, 0.55)
    mean_diff, max_diff = _pixel_diff(frame_off, frame_on)
    assert max_diff > 10


def test_particles_with_sprite_path_in_render_pipeline():
    presets = json.loads((FIXTURES / "gpu_effect_presets.json").read_text())
    toggles_on = next(p for p in presets["presets"] if p["name"] == "particles_only")["toggles"]
    path = str(_ensure_synthetic_sprite())

    frame_sprite, state = _render_at_time(toggles_on, 0.55, sprite_path=path)
    assert state.particle_system.particle_sprite is not None
    assert len(state.particle_system.particles) > 0

    frame_no_sprite, _ = _render_at_time(toggles_on, 0.55)
    mean_diff, max_diff = _pixel_diff(frame_no_sprite, frame_sprite)
    assert max_diff > 5
