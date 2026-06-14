"""Tests for export correctness fixes (grain size, neon outline, envelope peaks)."""
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from audio_analysis import detect_envelope_peaks
from effect_engine import calculate_effect_parameters, get_effect_value_at_time, toggles_from_dict
from video_renderer import apply_film_grain


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


def _fixture_audio_features() -> FixtureAudioFeatures:
    data = json.loads((Path(__file__).parent / "fixtures" / "effect_parity.json").read_text())
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


def test_film_grain_size_changes_pixels():
    img = Image.new("RGBA", (108, 192), (128, 128, 128, 255))
    fine = np.array(apply_film_grain(img, 0.8, 1.0))
    coarse = np.array(apply_film_grain(img, 0.8, 8.0))
    assert not np.array_equal(fine, coarse)


def test_detect_envelope_peaks_matches_scipy_pattern():
    envelope = [(i * 0.1, v) for i, v in enumerate([
        0.1, 0.3, 0.5, 0.9, 0.4, 0.2, 0.6, 0.95, 0.3, 0.1,
    ])]
    peaks = detect_envelope_peaks(envelope, threshold=0.5, min_distance_sec=0.15)
    times = [round(p[0], 1) for p in peaks]
    assert 0.3 in times
    assert 0.7 in times
    assert len(peaks) == 2


def test_neon_outline_values_at_beat():
    features = _fixture_audio_features()
    toggles = toggles_from_dict({
        "element_glow": {"enabled": False, "intensity": 0.5},
        "element_scale": {"enabled": False, "intensity": 0.3},
        "neon_outline": {"enabled": True, "intensity": 0.8, "trigger_source": "beats"},
        "particle_burst": {"enabled": False, "intensity": 0.5},
        "vignette_pulse": {"enabled": False, "intensity": 0.4},
    })
    params = calculate_effect_parameters(features, toggles)
    values = get_effect_value_at_time(params, features.beat_times[0] + 0.02)
    assert values.get("neon_outline_intensity", 0) > 0.01
    assert "neon_outline_color" in values
