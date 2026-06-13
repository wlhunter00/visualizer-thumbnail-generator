"""
Effect lever schema — single source of truth for Auto-Suggest and export history.
Mirrors frontend/src/types.ts EFFECT_METADATA conventions.
"""

from typing import Any, Dict, List, Optional, Tuple

TRIGGER_SOURCES = ("beats", "full", "low", "medium", "high", "onsets")
GLITCH_TRIGGER_SOURCES = ("onsets", "beats", "full", "low", "medium", "high")

EFFECT_KEYS = (
    "element_glow",
    "element_scale",
    "echo_trail",
    "particle_burst",
    "energy_trails",
    "light_flares",
    "glitch",
    "ripple_wave",
    "film_grain",
    "strobe_flash",
    "vignette_pulse",
    "background_dim",
)

EFFECTS_WITH_TRIGGER_SOURCE = frozenset({
    "element_glow",
    "element_scale",
    "particle_burst",
    "light_flares",
    "glitch",
    "ripple_wave",
    "strobe_flash",
    "vignette_pulse",
})

EFFECTS_WITH_RADIUS = frozenset({"background_dim"})

DEFAULT_TRIGGER_BY_EFFECT: Dict[str, str] = {key: "beats" for key in EFFECT_KEYS}
DEFAULT_TRIGGER_BY_EFFECT["glitch"] = "onsets"

EFFECT_DESCRIPTIONS: Dict[str, str] = {
    "element_glow": "Subject emits pulsating light (light sources, faces, focal points)",
    "element_scale": "Subject grows/shrinks with audio (subtle, adds life)",
    "echo_trail": "Afterimage effect (motion, dreamy)",
    "particle_burst": "Particles explode from subject (energetic, celebratory)",
    "energy_trails": "Glowing lines orbit subject (mystical, flowing)",
    "light_flares": "Lens flare from glow points (cinematic, dramatic)",
    "glitch": "RGB split, chromatic aberration (edgy, electronic)",
    "ripple_wave": "Distortion waves from subject (impactful, bass-heavy)",
    "film_grain": "VHS/retro texture (nostalgic, lo-fi)",
    "strobe_flash": "Brief flashes on strong hits (intense, use sparingly)",
    "vignette_pulse": "Dark edges pulse with rhythm (focus, atmosphere)",
    "background_dim": "Darken background to make subject pop (contrast)",
}

TRIGGER_SOURCE_DOCS = """Trigger sources (set on enabled beat-reactive effects only):
- beats: tempo-synced kick, snare, and rhythm grid
- full: overall loudness (dB)
- low: below 250 Hz — sub, kick, bass
- medium: 250 Hz–3500 Hz — vocals, snare, guitars
- high: above 3500 Hz — cymbals, hi-hats, air
- onsets: transients and sharp hits (glitch default; glitch only otherwise optional)"""


def default_effect_toggle(effect_key: str) -> Dict[str, Any]:
    """Default toggle dict for one effect."""
    toggle: Dict[str, Any] = {
        "enabled": effect_key in ("element_glow", "element_scale", "particle_burst", "vignette_pulse"),
        "intensity": 0.5,
    }
    if effect_key in EFFECTS_WITH_TRIGGER_SOURCE:
        toggle["trigger_source"] = DEFAULT_TRIGGER_BY_EFFECT[effect_key]
    if effect_key == "background_dim":
        toggle["enabled"] = False
        toggle["intensity"] = 0.3
        toggle["radius"] = 0.5
    elif effect_key == "element_scale":
        toggle["intensity"] = 0.3
    elif effect_key == "film_grain":
        toggle["intensity"] = 0.2
    elif effect_key == "glitch":
        toggle["intensity"] = 0.3
    return toggle


def default_suggestion_dict() -> Dict[str, Any]:
    return {key: default_effect_toggle(key) for key in EFFECT_KEYS}


def build_prompt_effect_docs() -> str:
    lines = ["AVAILABLE EFFECTS (fields per effect):"]
    for i, key in enumerate(EFFECT_KEYS, 1):
        fields = ['"enabled" (boolean)', '"intensity" (0.0-1.0)']
        if key in EFFECTS_WITH_TRIGGER_SOURCE:
            fields.append('"trigger_source" (beats|full|low|medium|high' + ('|onsets' if key == "glitch" else '') + ')')
        if key in EFFECTS_WITH_RADIUS:
            fields.append('"radius" (0.0-1.0 focus area size)')
        lines.append(f"{i}. {key} — {EFFECT_DESCRIPTIONS[key]}")
        lines.append(f"   Fields: {', '.join(fields)}")
    lines.append("")
    lines.append(TRIGGER_SOURCE_DOCS)
    return "\n".join(lines)


def build_example_json() -> str:
    return """{
    "ripple_wave": {"enabled": true, "intensity": 0.6, "trigger_source": "low"},
    "glitch": {"enabled": true, "intensity": 0.4, "trigger_source": "onsets"},
    "background_dim": {"enabled": true, "intensity": 0.4, "radius": 0.35},
    "echo_trail": {"enabled": false, "intensity": 0.4},
    "element_glow": {"enabled": true, "intensity": 0.7, "trigger_source": "beats"},
    "element_scale": {"enabled": true, "intensity": 0.3, "trigger_source": "beats"},
    "particle_burst": {"enabled": true, "intensity": 0.6, "trigger_source": "beats"},
    "energy_trails": {"enabled": false, "intensity": 0.4},
    "light_flares": {"enabled": false, "intensity": 0.3, "trigger_source": "high"},
    "film_grain": {"enabled": false, "intensity": 0.2},
    "strobe_flash": {"enabled": false, "intensity": 0.3, "trigger_source": "beats"},
    "vignette_pulse": {"enabled": true, "intensity": 0.4, "trigger_source": "beats"}
}"""


def _clamp01(value: Any, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _dominant_band(audio_metrics: Dict[str, float]) -> str:
    bass = audio_metrics.get("average_bass", 0.0)
    mid = audio_metrics.get("average_mid", 0.0)
    high = audio_metrics.get("average_high", 0.0)
    if bass >= mid and bass >= high:
        return "low"
    if high >= mid and high >= bass:
        return "high"
    return "medium"


def _heuristic_trigger(effect_key: str, audio_metrics: Dict[str, float]) -> str:
    if effect_key == "glitch":
        if audio_metrics.get("onset_density", 0) > 8:
            return "onsets"
        return "onsets"

    band = _dominant_band(audio_metrics)
    onset_density = audio_metrics.get("onset_density", 0)

    if effect_key in ("ripple_wave", "element_scale", "particle_burst") and band == "low":
        return "low"
    if effect_key in ("light_flares", "strobe_flash", "particle_burst") and band == "high":
        return "high"
    if effect_key in ("element_glow", "vignette_pulse") and band == "medium":
        return "medium"
    if effect_key == "strobe_flash" and onset_density > 8:
        return "full"

    return DEFAULT_TRIGGER_BY_EFFECT.get(effect_key, "beats")


def _heuristic_radius(image_bounds: Any) -> float:
    area = image_bounds.w * image_bounds.h
    if area < 0.25:
        return 0.35
    if area > 0.5:
        return 0.65
    return 0.5


def normalize_suggestion(
    raw: Dict[str, Any],
    audio_metrics: Dict[str, float],
    image_analysis: Any,
) -> Dict[str, Any]:
    """
    Validate GPT output and apply heuristic fallbacks for missing levers.
    image_analysis must have .bounds with x, y, w, h attributes.
    """
    result: Dict[str, Any] = {}

    for key in EFFECT_KEYS:
        base = default_effect_toggle(key)
        effect_data = raw.get(key, {}) if isinstance(raw.get(key), dict) else {}

        enabled = bool(effect_data.get("enabled", base["enabled"]))
        intensity = _clamp01(effect_data.get("intensity", base["intensity"]), base["intensity"])

        toggle: Dict[str, Any] = {"enabled": enabled, "intensity": intensity}

        if key in EFFECTS_WITH_TRIGGER_SOURCE:
            source = effect_data.get("trigger_source")
            valid_sources = GLITCH_TRIGGER_SOURCES if key == "glitch" else TRIGGER_SOURCES
            if source not in valid_sources:
                source = None
            if source is None and enabled:
                source = _heuristic_trigger(key, audio_metrics)
            elif source is None:
                source = DEFAULT_TRIGGER_BY_EFFECT[key]
            toggle["trigger_source"] = source

        if key in EFFECTS_WITH_RADIUS:
            radius = effect_data.get("radius")
            if radius is None and enabled:
                radius = _heuristic_radius(image_analysis.bounds)
            elif radius is not None:
                radius = _clamp01(radius, 0.5)
            elif not enabled:
                radius = base.get("radius", 0.5)
            else:
                radius = _heuristic_radius(image_analysis.bounds)
            toggle["radius"] = radius

        result[key] = toggle

    return result
