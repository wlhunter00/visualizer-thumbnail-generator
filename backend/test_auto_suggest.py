"""Tests for Auto-Suggest normalization and export history."""

import json
import tempfile
from pathlib import Path
from unittest import TestCase, main

from effect_schema import normalize_suggestion, EFFECT_KEYS
from effect_engine import toggles_from_dict, toggles_to_dict
from image_analysis import ImageAnalysis, SubjectBounds
import export_history as eh


class TestNormalizeSuggestion(TestCase):
    def setUp(self):
        self.image = ImageAnalysis(
            subject="person",
            subject_description="portrait",
            bounds=SubjectBounds(x=0.3, y=0.2, w=0.2, h=0.3),
            glow_points=[],
            colors=["#FFFFFF"],
            mood="energetic",
            suggested_particle_style="sparkles",
        )
        self.bass_heavy_metrics = {
            "tempo": 90,
            "onset_density": 4.0,
            "average_bass": 0.85,
            "average_mid": 0.4,
            "average_high": 0.3,
            "dynamic_range": 0.6,
            "beat_strength_variance": 0.1,
            "average_energy": 0.7,
        }

    def test_strips_trigger_from_echo_trail(self):
        raw = {
            "echo_trail": {
                "enabled": True,
                "intensity": 0.5,
                "trigger_source": "low",
            }
        }
        result = normalize_suggestion(raw, self.bass_heavy_metrics, self.image)
        self.assertNotIn("trigger_source", result["echo_trail"])

    def test_invalid_trigger_coerced_to_default(self):
        raw = {
            "element_glow": {
                "enabled": True,
                "intensity": 0.5,
                "trigger_source": "invalid",
            }
        }
        result = normalize_suggestion(raw, self.bass_heavy_metrics, self.image)
        self.assertEqual(result["element_glow"]["trigger_source"], "beats")

    def test_bass_heavy_ripple_gets_low_trigger_when_omitted(self):
        raw = {
            "ripple_wave": {"enabled": True, "intensity": 0.6},
        }
        result = normalize_suggestion(raw, self.bass_heavy_metrics, self.image)
        self.assertEqual(result["ripple_wave"]["trigger_source"], "low")

    def test_small_subject_background_dim_radius(self):
        raw = {
            "background_dim": {"enabled": True, "intensity": 0.4},
        }
        result = normalize_suggestion(raw, self.bass_heavy_metrics, self.image)
        self.assertAlmostEqual(result["background_dim"]["radius"], 0.35)

    def test_round_trip_preserves_fields(self):
        raw = {
            "ripple_wave": {"enabled": True, "intensity": 0.6, "trigger_source": "low"},
            "glitch": {"enabled": True, "intensity": 0.4, "trigger_source": "onsets"},
            "background_dim": {"enabled": True, "intensity": 0.4, "radius": 0.35},
        }
        normalized = normalize_suggestion(raw, self.bass_heavy_metrics, self.image)
        toggles = toggles_from_dict(normalized)
        out = toggles_to_dict(toggles)
        self.assertEqual(out["ripple_wave"]["trigger_source"], "low")
        self.assertEqual(out["glitch"]["trigger_source"], "onsets")
        self.assertAlmostEqual(out["background_dim"]["radius"], 0.35)
        for key in EFFECT_KEYS:
            self.assertIn(key, out)


class TestExportHistory(TestCase):
    def test_append_and_find_similar(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.jsonl"
            original_path = eh.HISTORY_PATH
            eh.HISTORY_PATH = path
            try:
                entry = eh.build_history_entry(
                    effect_toggles={"element_glow": {"enabled": True, "intensity": 0.7, "trigger_source": "low"}},
                    audio_metrics={
                        "tempo": 90,
                        "onset_density": 4,
                        "average_bass": 0.9,
                        "average_mid": 0.3,
                        "average_high": 0.2,
                        "dynamic_range": 0.5,
                        "beat_strength_variance": 0.1,
                        "average_energy": 0.6,
                    },
                    image_analysis_dict={
                        "subject": "guitar",
                        "mood": "energetic",
                        "colors": ["#FF0000"],
                        "bounds": {"x": 0.2, "y": 0.2, "w": 0.3, "h": 0.4},
                    },
                    aspect_ratio="9:16",
                    clip_duration_sec=30.0,
                )
                eh.append_export_history(entry)

                query_image = ImageAnalysis(
                    subject="drums",
                    subject_description="",
                    bounds=SubjectBounds(x=0.2, y=0.2, w=0.3, h=0.4),
                    glow_points=[],
                    colors=[],
                    mood="energetic",
                    suggested_particle_style="",
                )
                similar = eh.find_similar_exports(
                    {
                        "average_bass": 0.88,
                        "average_mid": 0.35,
                        "average_high": 0.25,
                        "onset_density": 5,
                        "average_energy": 0.55,
                        "dynamic_range": 0.45,
                    },
                    query_image,
                    k=1,
                    aspect_ratio="9:16",
                )
                self.assertEqual(len(similar), 1)
                self.assertEqual(similar[0].id, entry.id)
            finally:
                eh.HISTORY_PATH = original_path


if __name__ == "__main__":
    main()
