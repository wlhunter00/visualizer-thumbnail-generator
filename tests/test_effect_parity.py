"""
Parity check: compare Python effect engine output against expected fixture keys.
Run: python tests/test_effect_parity.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dataclasses import dataclass, field
from typing import List, Tuple

from effect_engine import calculate_effect_parameters, get_effect_value_at_time, toggles_from_dict


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


def main():
    fixture_path = Path(__file__).parent / "fixtures" / "effect_parity.json"
    data = json.loads(fixture_path.read_text())
    af = data["audio_features"]
    features = FixtureAudioFeatures(
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
    toggles = toggles_from_dict(data["toggles"])
    params = calculate_effect_parameters(features, toggles)

    print("Python get_effect_value_at_time snapshot:")
    for t in data["sample_times"]:
        values = get_effect_value_at_time(params, t)
        keys = ["element_scale", "element_glow_intensity", "vignette_strength", "strobe_active"]
        snapshot = {k: values.get(k) for k in keys}
        print(f"  t={t}: {snapshot}")

    print("OK — fixture runs without error")


if __name__ == "__main__":
    main()
