"""
Effect Engine Module
Maps audio features to visual effect parameters based on toggle-based user settings.
No BPM-based assumptions - effects are controlled explicitly by user toggles.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional, Literal
from effect_schema import EFFECT_KEYS, EFFECTS_WITH_TRIGGER_SOURCE, EFFECTS_WITH_RADIUS, GLITCH_STYLE_EFFECTS
from audio_analysis import AudioFeatures, detect_envelope_peaks
import math

TriggerSource = Literal["beats", "full", "low", "medium", "high", "onsets"]

DEFAULT_TRIGGER_SOURCE: TriggerSource = "beats"
GLITCH_DEFAULT_TRIGGER_SOURCE: TriggerSource = "onsets"


@dataclass
class EffectToggle:
    """A single effect toggle with enabled state and intensity."""
    enabled: bool = False
    intensity: float = 0.5  # 0-1
    trigger_source: str = "beats"
    radius: Optional[float] = None  # 0-1 focus area size (background_dim only)


@dataclass
class EffectToggles:
    """All user-controlled effect toggles."""
    # Element effects
    element_glow: EffectToggle = field(default_factory=lambda: EffectToggle(True, 0.5))
    element_scale: EffectToggle = field(default_factory=lambda: EffectToggle(True, 0.3))
    neon_outline: EffectToggle = field(default_factory=lambda: EffectToggle(False, 0.5))
    
    # Particle effects
    particle_burst: EffectToggle = field(default_factory=lambda: EffectToggle(True, 0.5))
    energy_trails: EffectToggle = field(default_factory=lambda: EffectToggle(False, 0.4))
    light_flares: EffectToggle = field(default_factory=lambda: EffectToggle(False, 0.3))
    
    # Style effects
    glitch: EffectToggle = field(default_factory=lambda: EffectToggle(False, 0.3, "onsets"))
    glitch_slice: EffectToggle = field(default_factory=lambda: EffectToggle(False, 0.4, "onsets"))
    ripple_wave: EffectToggle = field(default_factory=lambda: EffectToggle(False, 0.4))
    film_grain: EffectToggle = field(default_factory=lambda: EffectToggle(False, 0.2))
    strobe_flash: EffectToggle = field(default_factory=lambda: EffectToggle(False, 0.3))
    vignette_pulse: EffectToggle = field(default_factory=lambda: EffectToggle(True, 0.4))
    
    # Background
    background_dim: EffectToggle = field(default_factory=lambda: EffectToggle(False, 0.3))


@dataclass
class SubjectBounds:
    """Bounding box for the detected subject (as percentages 0-1)."""
    x: float = 0.25
    y: float = 0.25
    w: float = 0.5
    h: float = 0.5
    
    @property
    def center_x(self) -> float:
        return self.x + self.w / 2
    
    @property
    def center_y(self) -> float:
        return self.y + self.h / 2


@dataclass
class GlowPoint:
    """A point that emits light."""
    x: float
    y: float
    intensity: float = 1.0


@dataclass
class ImageContext:
    """Context from image analysis for effect generation."""
    bounds: SubjectBounds = field(default_factory=SubjectBounds)
    glow_points: List[GlowPoint] = field(default_factory=list)
    colors: List[str] = field(default_factory=lambda: ["#FFFFFF", "#FFD700", "#FF6B35"])
    mood: str = "neutral"


# ============================================================================
# Effect Parameter Structures
# ============================================================================

@dataclass
class ElementGlowParams:
    """Parameters for element glow effect."""
    enabled: bool = True
    intensity: float = 0.5
    color: Tuple[int, int, int] = (255, 200, 100)  # Warm glow default
    radius: float = 50.0  # Glow radius in pixels
    pulse_triggers: List[Tuple[float, float]] = field(default_factory=list)  # (time, strength)


@dataclass
class ElementScaleParams:
    """Parameters for element scale pulse effect."""
    enabled: bool = True
    intensity: float = 0.3
    base_scale: float = 1.0
    max_scale: float = 1.1
    triggers: List[Tuple[float, float]] = field(default_factory=list)  # (time, strength)


@dataclass
class NeonOutlineParams:
    """Parameters for neon outline effect."""
    enabled: bool = False
    intensity: float = 0.5
    color: Tuple[int, int, int] = (0, 255, 255)
    width: float = 3.0
    glow_radius: float = 15.0
    pulse_triggers: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class ParticleBurstParams:
    """Parameters for particle burst effect."""
    enabled: bool = True
    intensity: float = 0.5
    particle_count: int = 50
    colors: List[Tuple[int, int, int]] = field(default_factory=lambda: [(255, 255, 255), (255, 220, 180), (200, 220, 255)])
    size_range: Tuple[float, float] = (3, 12)
    speed: float = 200.0  # Pixels per second
    lifetime: float = 1.0  # Seconds
    triggers: List[Tuple[float, float]] = field(default_factory=list)  # (time, strength)
    # Full subject bounds for spawning from perimeter
    bounds_x: float = 0.25  # Normalized position
    bounds_y: float = 0.25
    bounds_w: float = 0.5
    bounds_h: float = 0.5


@dataclass
class EnergyTrailsParams:
    """Parameters for energy trails effect."""
    enabled: bool = False
    intensity: float = 0.4
    trail_count: int = 8
    colors: List[Tuple[int, int, int]] = field(default_factory=lambda: [(255, 255, 255), (200, 220, 255)])
    width: float = 2.0
    speed: float = 1.0  # Revolutions per second
    # Full subject bounds for elliptical orbit
    bounds_x: float = 0.25
    bounds_y: float = 0.25
    bounds_w: float = 0.5
    bounds_h: float = 0.5


@dataclass
class LightFlaresParams:
    """Parameters for light flares effect."""
    enabled: bool = False
    intensity: float = 0.3
    flare_points: List[Tuple[float, float]] = field(default_factory=list)  # (x, y) normalized
    colors: List[Tuple[int, int, int]] = field(default_factory=lambda: [(255, 255, 200)])
    size: float = 100.0
    triggers: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class GlitchParams:
    """Parameters for chromatic glitch effect."""
    enabled: bool = False
    intensity: float = 0.3
    chromatic_aberration: float = 5.0
    rgb_split: float = 3.0
    scan_lines: bool = True
    scan_line_opacity: float = 0.1
    triggers: List[Tuple[float, float, float]] = field(default_factory=list)  # (time, duration, raw strength)


@dataclass
class GlitchSliceParams:
    """Parameters for horizontal slice glitch effect."""
    enabled: bool = False
    intensity: float = 0.4
    slice_offset: float = 8.0
    triggers: List[Tuple[float, float, float]] = field(default_factory=list)  # (time, duration, raw strength)


@dataclass
class RippleWaveParams:
    """Parameters for ripple wave effect."""
    enabled: bool = False
    intensity: float = 0.4
    # Full subject bounds for elliptical ripple origin
    bounds_x: float = 0.25
    bounds_y: float = 0.25
    bounds_w: float = 0.5
    bounds_h: float = 0.5
    wavelength: float = 50.0
    amplitude: float = 10.0
    speed: float = 200.0  # Pixels per second
    triggers: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class FilmGrainParams:
    """Parameters for film grain effect."""
    enabled: bool = False
    intensity: float = 0.2
    grain_size: float = 1.5
    color_variation: float = 0.1


@dataclass
class StrobeFlashParams:
    """Parameters for strobe flash effect."""
    enabled: bool = False
    intensity: float = 0.3
    flash_duration: float = 0.05  # Seconds
    color: Tuple[int, int, int] = (255, 255, 255)
    triggers: List[float] = field(default_factory=list)  # Times of flashes


@dataclass
class VignettePulseParams:
    """Parameters for vignette pulse effect."""
    enabled: bool = True
    intensity: float = 0.4
    base_strength: float = 0.5
    pulse_strength: float = 0.4
    triggers: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class BackgroundDimParams:
    """Parameters for background dim effect."""
    enabled: bool = True
    intensity: float = 0.3
    dim_amount: float = 0.3  # How much to darken (0-1)
    blur_amount: float = 2.0  # Blur radius
    focus_radius: float = 0.5  # 0-1 size of the bright focus area


@dataclass
class EffectParameters:
    """All effect parameters for a video."""
    duration: float
    fps: int = 30
    subject_bounds: SubjectBounds = field(default_factory=SubjectBounds)
    
    # All 11 effects
    element_glow: ElementGlowParams = field(default_factory=ElementGlowParams)
    element_scale: ElementScaleParams = field(default_factory=ElementScaleParams)
    neon_outline: NeonOutlineParams = field(default_factory=NeonOutlineParams)
    particle_burst: ParticleBurstParams = field(default_factory=ParticleBurstParams)
    energy_trails: EnergyTrailsParams = field(default_factory=EnergyTrailsParams)
    light_flares: LightFlaresParams = field(default_factory=LightFlaresParams)
    glitch: GlitchParams = field(default_factory=GlitchParams)
    glitch_slice: GlitchSliceParams = field(default_factory=GlitchSliceParams)
    ripple_wave: RippleWaveParams = field(default_factory=RippleWaveParams)
    film_grain: FilmGrainParams = field(default_factory=FilmGrainParams)
    strobe_flash: StrobeFlashParams = field(default_factory=StrobeFlashParams)
    vignette_pulse: VignettePulseParams = field(default_factory=VignettePulseParams)
    background_dim: BackgroundDimParams = field(default_factory=BackgroundDimParams)


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hsv(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convert RGB to HSV (hue 0-360, saturation 0-1, value 0-1)."""
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    diff = max_c - min_c
    
    # Value
    v = max_c
    
    # Saturation
    s = 0 if max_c == 0 else diff / max_c
    
    # Hue
    if diff == 0:
        h = 0
    elif max_c == r:
        h = 60 * (((g - b) / diff) % 6)
    elif max_c == g:
        h = 60 * (((b - r) / diff) + 2)
    else:
        h = 60 * (((r - g) / diff) + 4)
    
    return (h, s, v)


def hsv_to_rgb(h: float, s: float, v: float) -> Tuple[int, int, int]:
    """Convert HSV to RGB."""
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    
    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    
    return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))


def boost_color_for_particles(color: Tuple[int, int, int], preserve_palette: bool = False) -> Tuple[int, int, int]:
    """
    Boost a color's brightness to make it more visible as a particle.
    When preserve_palette is True, saturation is kept closer to original.
    """
    h, s, v = rgb_to_hsv(color[0], color[1], color[2])
    
    if preserve_palette:
        # Preserve saturation closer to original - don't add color that isn't there
        s = min(1.0, s * 1.1)
    else:
        # Slight saturation boost for multi-color palettes
        s = min(1.0, s * 1.15 + 0.05)
    
    # Boost brightness (particles need to be visible)
    v = min(1.0, v * 1.2 + 0.2)
    
    # Ensure minimum brightness
    v = max(0.5, v)
    
    return hsv_to_rgb(h, s, v)


def prepare_particle_colors(colors: List[Tuple[int, int, int]]) -> List[Tuple[int, int, int]]:
    """
    Prepare colors for particle effects by boosting brightness for visibility.
    Respects the original palette - if image has limited colors, particles stay limited.
    """
    if not colors:
        return [(255, 255, 255)]  # Simple white default
    
    # Check if the palette is essentially monochromatic (low hue variance)
    hues = []
    for color in colors:
        h, s, v = rgb_to_hsv(color[0], color[1], color[2])
        if s > 0.1:  # Only consider saturated colors for hue analysis
            hues.append(h)
    
    # Determine if this is a limited/monochromatic palette
    is_limited_palette = len(hues) <= 1 or (len(hues) > 1 and _hue_variance(hues) < 30)
    
    boosted = []
    for color in colors:
        # Skip very dark colors (they won't be visible as particles)
        brightness = (color[0] + color[1] + color[2]) / 3
        if brightness < 40:
            continue
        
        boosted_color = boost_color_for_particles(color, preserve_palette=is_limited_palette)
        boosted.append(boosted_color)
    
    # If all colors were filtered out, use boosted versions of originals
    if not boosted:
        boosted = [boost_color_for_particles(c, preserve_palette=is_limited_palette) for c in colors[:3]]
    
    # For limited palettes, just return what we have - don't artificially add colors
    # For varied palettes, still don't add extra - use what's in the image
    return boosted if boosted else [(255, 255, 255)]


def _hue_variance(hues: List[float]) -> float:
    """Calculate hue variance, accounting for circular nature of hue (0-360)."""
    if len(hues) < 2:
        return 0
    
    # Find the minimum spread considering circular wraparound
    hues = sorted(hues)
    max_gap = 0
    for i in range(len(hues)):
        next_i = (i + 1) % len(hues)
        gap = hues[next_i] - hues[i]
        if next_i == 0:  # Wrap around
            gap = (360 - hues[i]) + hues[next_i]
        max_gap = max(max_gap, gap)
    
    # Variance is 360 minus the largest gap
    return 360 - max_gap


def build_triggers(
    audio_features: AudioFeatures,
    trigger_source: str,
    intensity: float,
    base_threshold: float = 0.3,
    apply_threshold: bool = True,
    scale_strength: bool = True,
) -> List[Tuple[float, float]]:
    """
    Build (time, strength) trigger list from the selected audio source.

    Args:
        audio_features: Analyzed audio data
        trigger_source: beats, full, low, medium, high, or onsets
        intensity: Effect intensity (0-1), scales trigger strength when scale_strength is True
        base_threshold: Base threshold before intensity scaling
        apply_threshold: If False, include all events (e.g. scale pulse on every beat)
    """
    threshold = base_threshold * (1 - intensity) if apply_threshold else 0.0
    triggers: List[Tuple[float, float]] = []

    if trigger_source == "beats":
        for beat_time, beat_strength in zip(audio_features.beat_times, audio_features.beat_strengths):
            if beat_strength >= threshold:
                out = beat_strength * intensity if scale_strength else beat_strength
                triggers.append((beat_time, out))
    elif trigger_source == "onsets":
        for onset_time, strength in zip(audio_features.onset_times, audio_features.onset_strengths):
            if strength >= threshold:
                out = strength * intensity if scale_strength else strength
                triggers.append((onset_time, out))
    elif trigger_source == "full":
        for peak_time, peak_strength in detect_envelope_peaks(audio_features.energy_envelope, threshold):
            out = peak_strength * intensity if scale_strength else peak_strength
            triggers.append((peak_time, out))
    elif trigger_source == "low":
        for peak_time, peak_strength in detect_envelope_peaks(audio_features.low_freq_energy, threshold):
            out = peak_strength * intensity if scale_strength else peak_strength
            triggers.append((peak_time, out))
    elif trigger_source == "medium":
        for peak_time, peak_strength in detect_envelope_peaks(audio_features.mid_freq_energy, threshold):
            out = peak_strength * intensity if scale_strength else peak_strength
            triggers.append((peak_time, out))
    elif trigger_source == "high":
        for peak_time, peak_strength in detect_envelope_peaks(audio_features.high_freq_energy, threshold):
            out = peak_strength * intensity if scale_strength else peak_strength
            triggers.append((peak_time, out))

    return triggers


def build_glitch_burst_triggers(
    audio_features: AudioFeatures,
    trigger_source: str,
    intensity: float,
    base_threshold: float = 0.5,
) -> List[Tuple[float, float, float]]:
    """Build (time, duration, raw_strength) triggers for glitch-style effects."""
    triggers: List[Tuple[float, float, float]] = []
    source_triggers = build_triggers(
        audio_features,
        trigger_source,
        intensity,
        base_threshold=base_threshold,
        scale_strength=False,
    )
    for trigger_time, raw_strength in source_triggers:
        duration = max(0.1, 0.08 + raw_strength * 0.15 + intensity * 0.12)
        triggers.append((trigger_time, duration, raw_strength))

    if trigger_source == "onsets" and intensity > 0.5:
        beat_triggers = build_triggers(
            audio_features,
            "beats",
            intensity * 0.8,
            base_threshold=0.4,
            scale_strength=False,
        )
        for beat_time, beat_strength in beat_triggers:
            duration = max(0.1, 0.06 + beat_strength * 0.1 + intensity * 0.08)
            triggers.append((beat_time, duration, beat_strength))

    return triggers


def calculate_effect_parameters(
    audio_features: AudioFeatures,
    toggles: EffectToggles,
    image_context: Optional[ImageContext] = None
) -> EffectParameters:
    """
    Calculate all effect parameters based on audio analysis and user toggles.
    
    Args:
        audio_features: Analyzed audio data
        toggles: User's effect toggle settings
        image_context: Optional image analysis context
    
    Returns:
        EffectParameters with all timing and values calculated
    """
    duration = audio_features.duration
    
    # Use provided image context or defaults
    ctx = image_context or ImageContext()
    bounds = ctx.bounds
    
    # Convert colors to RGB
    colors_rgb = [hex_to_rgb(c) for c in ctx.colors[:5]] if ctx.colors else [(255, 200, 100)]
    primary_color = colors_rgb[0] if colors_rgb else (255, 200, 100)
    
    # ========================================================================
    # ELEMENT GLOW
    # ========================================================================
    glow_triggers = []
    if toggles.element_glow.enabled:
        glow_triggers = build_triggers(
            audio_features,
            toggles.element_glow.trigger_source,
            toggles.element_glow.intensity,
            base_threshold=0.3,
        )
    
    element_glow = ElementGlowParams(
        enabled=toggles.element_glow.enabled,
        intensity=toggles.element_glow.intensity,
        color=primary_color,
        radius=30 + toggles.element_glow.intensity * 70,
        pulse_triggers=glow_triggers
    )
    
    # ========================================================================
    # ELEMENT SCALE
    # ========================================================================
    scale_triggers = []
    if toggles.element_scale.enabled:
        scale_triggers = build_triggers(
            audio_features,
            toggles.element_scale.trigger_source,
            toggles.element_scale.intensity,
            apply_threshold=False,
        )
    
    element_scale = ElementScaleParams(
        enabled=toggles.element_scale.enabled,
        intensity=toggles.element_scale.intensity,
        base_scale=1.0,
        max_scale=1.0 + toggles.element_scale.intensity * 0.15,
        triggers=scale_triggers
    )
    
    # ========================================================================
    # NEON OUTLINE
    # ========================================================================
    neon_triggers = []
    if toggles.neon_outline.enabled:
        neon_triggers = build_triggers(
            audio_features,
            toggles.neon_outline.trigger_source,
            toggles.neon_outline.intensity,
            base_threshold=0.3,
        )
    
    neon_outline = NeonOutlineParams(
        enabled=toggles.neon_outline.enabled,
        intensity=toggles.neon_outline.intensity,
        color=primary_color,
        width=2 + toggles.neon_outline.intensity * 4,
        glow_radius=10 + toggles.neon_outline.intensity * 20,
        pulse_triggers=neon_triggers,
    )
    
    # ========================================================================
    # PARTICLE BURST
    # ========================================================================
    burst_triggers = []
    if toggles.particle_burst.enabled:
        burst_triggers = build_triggers(
            audio_features,
            toggles.particle_burst.trigger_source,
            toggles.particle_burst.intensity,
            base_threshold=0.4,
        )
    
    # Prepare particle colors - boost saturation/brightness for visibility
    particle_colors = prepare_particle_colors(colors_rgb[:5])
    
    particle_burst = ParticleBurstParams(
        enabled=toggles.particle_burst.enabled,
        intensity=toggles.particle_burst.intensity,
        particle_count=int(30 + toggles.particle_burst.intensity * 70),
        colors=particle_colors,
        size_range=(2 + toggles.particle_burst.intensity * 2, 8 + toggles.particle_burst.intensity * 8),
        speed=150 + toggles.particle_burst.intensity * 150,
        lifetime=0.8 + toggles.particle_burst.intensity * 0.6,
        triggers=burst_triggers,
        bounds_x=bounds.x,
        bounds_y=bounds.y,
        bounds_w=bounds.w,
        bounds_h=bounds.h
    )
    
    # ========================================================================
    # ENERGY TRAILS
    # ========================================================================
    # Use boosted colors for energy trails too (they need to be visible)
    trail_colors = prepare_particle_colors(colors_rgb[:3])[:2]
    
    energy_trails = EnergyTrailsParams(
        enabled=toggles.energy_trails.enabled,
        intensity=toggles.energy_trails.intensity,
        trail_count=4 + int(toggles.energy_trails.intensity * 8),
        colors=trail_colors,
        width=1 + toggles.energy_trails.intensity * 3,
        speed=0.5 + toggles.energy_trails.intensity * 1.0,
        bounds_x=bounds.x,
        bounds_y=bounds.y,
        bounds_w=bounds.w,
        bounds_h=bounds.h
    )
    
    # ========================================================================
    # LIGHT FLARES
    # ========================================================================
    flare_triggers = []
    if toggles.light_flares.enabled:
        flare_triggers = build_triggers(
            audio_features,
            toggles.light_flares.trigger_source,
            toggles.light_flares.intensity,
            base_threshold=0.6,
        )
    
    flare_points = [(gp.x, gp.y) for gp in ctx.glow_points] if ctx.glow_points else [(bounds.center_x, bounds.center_y)]
    
    light_flares = LightFlaresParams(
        enabled=toggles.light_flares.enabled,
        intensity=toggles.light_flares.intensity,
        flare_points=flare_points,
        colors=[(255, 255, 200)] + colors_rgb[:1],
        size=50 + toggles.light_flares.intensity * 100,
        triggers=flare_triggers
    )
    
    # ========================================================================
    # GLITCH (chromatic)
    # ========================================================================
    glitch_triggers = []
    if toggles.glitch.enabled:
        glitch_triggers = build_glitch_burst_triggers(
            audio_features,
            toggles.glitch.trigger_source,
            toggles.glitch.intensity,
            base_threshold=0.5,
        )

    glitch = GlitchParams(
        enabled=toggles.glitch.enabled,
        intensity=toggles.glitch.intensity,
        chromatic_aberration=4 + toggles.glitch.intensity * 14,
        rgb_split=3 + toggles.glitch.intensity * 10,
        scan_lines=toggles.glitch.intensity > 0.2,
        scan_line_opacity=0.05 + toggles.glitch.intensity * 0.1,
        triggers=glitch_triggers,
    )

    # ========================================================================
    # GLITCH SLICE
    # ========================================================================
    slice_triggers = []
    if toggles.glitch_slice.enabled:
        slice_triggers = build_glitch_burst_triggers(
            audio_features,
            toggles.glitch_slice.trigger_source,
            toggles.glitch_slice.intensity,
            base_threshold=0.5,
        )

    glitch_slice = GlitchSliceParams(
        enabled=toggles.glitch_slice.enabled,
        intensity=toggles.glitch_slice.intensity,
        slice_offset=2 + toggles.glitch_slice.intensity * 18,
        triggers=slice_triggers,
    )
    
    # ========================================================================
    # RIPPLE WAVE
    # ========================================================================
    ripple_triggers = []
    if toggles.ripple_wave.enabled:
        ripple_triggers = build_triggers(
            audio_features,
            toggles.ripple_wave.trigger_source,
            toggles.ripple_wave.intensity,
            base_threshold=0.5,
        )
    
    ripple_wave = RippleWaveParams(
        enabled=toggles.ripple_wave.enabled,
        intensity=toggles.ripple_wave.intensity,
        bounds_x=bounds.x,
        bounds_y=bounds.y,
        bounds_w=bounds.w,
        bounds_h=bounds.h,
        wavelength=30 + (1 - toggles.ripple_wave.intensity) * 40,
        amplitude=5 + toggles.ripple_wave.intensity * 15,
        speed=150 + toggles.ripple_wave.intensity * 150,
        triggers=ripple_triggers
    )
    
    # ========================================================================
    # FILM GRAIN
    # ========================================================================
    film_grain = FilmGrainParams(
        enabled=toggles.film_grain.enabled,
        intensity=toggles.film_grain.intensity,
        grain_size=1 + toggles.film_grain.intensity * 2,
        color_variation=0.05 + toggles.film_grain.intensity * 0.15
    )
    
    # ========================================================================
    # STROBE FLASH
    # ========================================================================
    strobe_triggers = []
    if toggles.strobe_flash.enabled:
        strobe_triggers = [
            t for t, _ in build_triggers(
                audio_features,
                toggles.strobe_flash.trigger_source,
                toggles.strobe_flash.intensity,
                base_threshold=0.8,
            )
        ]
    
    strobe_flash = StrobeFlashParams(
        enabled=toggles.strobe_flash.enabled,
        intensity=toggles.strobe_flash.intensity,
        flash_duration=0.03 + toggles.strobe_flash.intensity * 0.05,
        color=(255, 255, 255),
        triggers=strobe_triggers
    )
    
    # ========================================================================
    # VIGNETTE PULSE
    # ========================================================================
    vignette_triggers = []
    if toggles.vignette_pulse.enabled:
        vignette_triggers = build_triggers(
            audio_features,
            toggles.vignette_pulse.trigger_source,
            toggles.vignette_pulse.intensity,
            apply_threshold=False,
        )
    
    vignette_pulse = VignettePulseParams(
        enabled=toggles.vignette_pulse.enabled,
        intensity=toggles.vignette_pulse.intensity,
        base_strength=0.3 + toggles.vignette_pulse.intensity * 0.4,
        pulse_strength=0.3 + toggles.vignette_pulse.intensity * 0.5,
        triggers=vignette_triggers
    )
    
    # ========================================================================
    # BACKGROUND DIM
    # ========================================================================
    bg_focus_radius = toggles.background_dim.radius if toggles.background_dim.radius is not None else 0.5
    background_dim = BackgroundDimParams(
        enabled=toggles.background_dim.enabled,
        intensity=toggles.background_dim.intensity,
        dim_amount=0.2 + toggles.background_dim.intensity * 0.4,
        blur_amount=1 + toggles.background_dim.intensity * 4,
        focus_radius=bg_focus_radius,
    )
    
    return EffectParameters(
        duration=duration,
        fps=30,
        subject_bounds=bounds,
        element_glow=element_glow,
        element_scale=element_scale,
        neon_outline=neon_outline,
        particle_burst=particle_burst,
        energy_trails=energy_trails,
        light_flares=light_flares,
        glitch=glitch,
        glitch_slice=glitch_slice,
        ripple_wave=ripple_wave,
        film_grain=film_grain,
        strobe_flash=strobe_flash,
        vignette_pulse=vignette_pulse,
        background_dim=background_dim
    )


def get_effect_value_at_time(
    effect_params: EffectParameters,
    time: float
) -> Dict[str, Any]:
    """
    Get interpolated effect values at a specific time.
    Used for frame-by-frame rendering.
    """
    values = {}
    
    # ========================================================================
    # ELEMENT GLOW
    # ========================================================================
    glow = effect_params.element_glow
    if glow.enabled:
        glow_intensity = 0.3  # Base glow
        for trigger_time, strength in glow.pulse_triggers:
            dt = time - trigger_time
            if 0 <= dt < 0.3:  # Glow lasts 0.3 seconds
                if dt < 0.05:  # Quick attack
                    pulse = (dt / 0.05) * strength
                else:  # Slow decay
                    pulse = strength * (1 - (dt - 0.05) / 0.25)
                glow_intensity = max(glow_intensity, 0.3 + pulse * 0.7)
        values["element_glow_intensity"] = glow_intensity * glow.intensity
        values["element_glow_radius"] = glow.radius
        values["element_glow_color"] = glow.color
    else:
        values["element_glow_intensity"] = 0
    
    # ========================================================================
    # ELEMENT SCALE
    # ========================================================================
    scale = effect_params.element_scale
    if scale.enabled:
        current_scale = scale.base_scale
        for trigger_time, strength in scale.triggers:
            dt = time - trigger_time
            if 0 <= dt < 0.2:  # Scale pulse lasts 0.2 seconds
                if dt < 0.05:  # Quick attack
                    scale_add = (dt / 0.05) * (scale.max_scale - scale.base_scale) * strength
                else:  # Ease out decay
                    progress = (dt - 0.05) / 0.15
                    scale_add = (1 - progress * progress) * (scale.max_scale - scale.base_scale) * strength
                current_scale = max(current_scale, scale.base_scale + scale_add)
        values["element_scale"] = current_scale
    else:
        values["element_scale"] = 1.0
    
    # ========================================================================
    # NEON OUTLINE
    # ========================================================================
    neon = effect_params.neon_outline
    if neon.enabled:
        neon_intensity = 0.0
        for trigger_time, strength in neon.pulse_triggers:
            dt = time - trigger_time
            if 0 <= dt < 0.3:
                if dt < 0.05:
                    pulse = (dt / 0.05) * strength
                else:
                    pulse = strength * (1 - (dt - 0.05) / 0.25)
                neon_intensity = max(neon_intensity, pulse)
        values["neon_outline_intensity"] = neon_intensity * neon.intensity
        values["neon_outline_color"] = neon.color
        values["neon_outline_width"] = neon.width
        values["neon_outline_glow"] = neon.glow_radius
    else:
        values["neon_outline_intensity"] = 0
    
    # ========================================================================
    # PARTICLE BURST
    # ========================================================================
    burst = effect_params.particle_burst
    if burst.enabled:
        # Check for active bursts
        active_bursts = []
        for trigger_time, strength in burst.triggers:
            dt = time - trigger_time
            if 0 <= dt < burst.lifetime:
                progress = dt / burst.lifetime
                active_bursts.append({
                    "trigger_time": trigger_time,
                    "progress": progress,
                    "strength": strength,
                    "bounds_x": burst.bounds_x,
                    "bounds_y": burst.bounds_y,
                    "bounds_w": burst.bounds_w,
                    "bounds_h": burst.bounds_h
                })
        values["particle_bursts"] = active_bursts
        values["particle_burst_params"] = {
            "count": burst.particle_count,
            "colors": burst.colors,
            "size_range": burst.size_range,
            "speed": burst.speed,
            "lifetime": burst.lifetime,
            "intensity": burst.intensity
        }
    else:
        values["particle_bursts"] = []
    
    # ========================================================================
    # ENERGY TRAILS
    # ========================================================================
    trails = effect_params.energy_trails
    if trails.enabled:
        values["energy_trails_enabled"] = True
        values["energy_trails_params"] = {
            "count": trails.trail_count,
            "colors": trails.colors,
            "width": trails.width,
            "bounds_x": trails.bounds_x,
            "bounds_y": trails.bounds_y,
            "bounds_w": trails.bounds_w,
            "bounds_h": trails.bounds_h,
            "speed": trails.speed,
            "time": time,
            "intensity": trails.intensity
        }
    else:
        values["energy_trails_enabled"] = False
    
    # ========================================================================
    # LIGHT FLARES
    # ========================================================================
    flares = effect_params.light_flares
    if flares.enabled:
        flare_intensity = 0
        for trigger_time, strength in flares.triggers:
            dt = time - trigger_time
            if 0 <= dt < 0.4:
                if dt < 0.05:
                    pulse = dt / 0.05
                else:
                    pulse = 1 - (dt - 0.05) / 0.35
                flare_intensity = max(flare_intensity, pulse * strength)
        values["light_flares_intensity"] = flare_intensity * flares.intensity
        values["light_flares_points"] = flares.flare_points
        values["light_flares_size"] = flares.size
        values["light_flares_colors"] = flares.colors
    else:
        values["light_flares_intensity"] = 0
    
    # ========================================================================
    # GLITCH
    # ========================================================================
    glitch = effect_params.glitch
    if glitch.enabled:
        max_strength = 0.0
        for trigger_time, duration, strength in glitch.triggers:
            if trigger_time <= time < trigger_time + duration:
                max_strength = max(max_strength, strength)
        glitch_active = max_strength > 0
        values["glitch_active"] = glitch_active
        values["glitch_intensity"] = max_strength * glitch.intensity if glitch_active else 0
        values["glitch_chromatic"] = glitch.chromatic_aberration * max_strength if glitch_active else 0
        values["glitch_rgb_split"] = glitch.rgb_split * max_strength if glitch_active else 0
        values["glitch_scan_lines"] = glitch.scan_lines and glitch_active
        values["glitch_scan_opacity"] = glitch.scan_line_opacity if glitch_active else 0
    else:
        values["glitch_active"] = False
        values["glitch_intensity"] = 0

    # ========================================================================
    # GLITCH SLICE
    # ========================================================================
    glitch_slice = effect_params.glitch_slice
    if glitch_slice.enabled:
        max_strength = 0.0
        active_trigger_time = 0.0
        for trigger_time, duration, strength in glitch_slice.triggers:
            if trigger_time <= time < trigger_time + duration:
                if strength > max_strength:
                    max_strength = strength
                    active_trigger_time = trigger_time
        slice_active = max_strength > 0
        values["glitch_slice_active"] = slice_active
        values["glitch_slice_intensity"] = max_strength * glitch_slice.intensity if slice_active else 0
        values["glitch_slice_offset"] = glitch_slice.slice_offset * max_strength if slice_active else 0
        values["glitch_slice_seed"] = active_trigger_time if slice_active else 0
    else:
        values["glitch_slice_active"] = False
        values["glitch_slice_intensity"] = 0
        values["glitch_slice_offset"] = 0
        values["glitch_slice_seed"] = 0
    
    # ========================================================================
    # RIPPLE WAVE
    # ========================================================================
    ripple = effect_params.ripple_wave
    if ripple.enabled:
        active_ripples = []
        for trigger_time, strength in ripple.triggers:
            dt = time - trigger_time
            if 0 <= dt < 2.0:  # Ripples last 2 seconds
                radius = dt * ripple.speed
                fade = 1 - dt / 2.0
                active_ripples.append({
                    "radius": radius,
                    "amplitude": ripple.amplitude * strength * fade,
                    "wavelength": ripple.wavelength,
                    "bounds_x": ripple.bounds_x,
                    "bounds_y": ripple.bounds_y,
                    "bounds_w": ripple.bounds_w,
                    "bounds_h": ripple.bounds_h
                })
        values["ripple_waves"] = active_ripples
        values["ripple_intensity"] = ripple.intensity
    else:
        values["ripple_waves"] = []
    
    # ========================================================================
    # FILM GRAIN
    # ========================================================================
    grain = effect_params.film_grain
    values["film_grain_enabled"] = grain.enabled
    values["film_grain_intensity"] = grain.intensity if grain.enabled else 0
    values["film_grain_size"] = grain.grain_size
    values["film_grain_color_var"] = grain.color_variation
    
    # ========================================================================
    # STROBE FLASH
    # ========================================================================
    strobe = effect_params.strobe_flash
    if strobe.enabled:
        flash_active = False
        for trigger_time in strobe.triggers:
            if trigger_time <= time < trigger_time + strobe.flash_duration:
                flash_active = True
                break
        values["strobe_active"] = flash_active
        values["strobe_intensity"] = strobe.intensity if flash_active else 0
        values["strobe_color"] = strobe.color
    else:
        values["strobe_active"] = False
        values["strobe_intensity"] = 0
    
    # ========================================================================
    # VIGNETTE PULSE
    # ========================================================================
    vignette = effect_params.vignette_pulse
    if vignette.enabled:
        vignette_strength = vignette.base_strength
        for trigger_time, strength in vignette.triggers:
            dt = time - trigger_time
            if 0 <= dt < 0.4:  # Slightly longer duration for visibility
                if dt < 0.08:  # Slightly longer attack
                    pulse = dt / 0.08
                else:  # Slower decay
                    pulse = 1 - (dt - 0.08) / 0.32
                # Apply pulse additively with full strength
                pulse_amount = vignette.pulse_strength * pulse * (0.5 + strength * 0.5)
                vignette_strength = max(vignette_strength, vignette.base_strength + pulse_amount)
        values["vignette_strength"] = vignette_strength
    else:
        values["vignette_strength"] = 0
    
    # ========================================================================
    # BACKGROUND DIM
    # ========================================================================
    bg_dim = effect_params.background_dim
    values["background_dim_enabled"] = bg_dim.enabled
    values["background_dim_amount"] = bg_dim.dim_amount if bg_dim.enabled else 0
    values["background_blur"] = bg_dim.blur_amount if bg_dim.enabled else 0
    values["background_focus_radius"] = bg_dim.focus_radius if bg_dim.enabled else 0
    
    # ========================================================================
    # SUBJECT BOUNDS (for masking)
    # ========================================================================
    values["subject_bounds"] = {
        "x": effect_params.subject_bounds.x,
        "y": effect_params.subject_bounds.y,
        "w": effect_params.subject_bounds.w,
        "h": effect_params.subject_bounds.h,
        "center_x": effect_params.subject_bounds.center_x,
        "center_y": effect_params.subject_bounds.center_y
    }
    
    return values


def toggles_to_dict(toggles: EffectToggles) -> Dict[str, Any]:
    """Serialize EffectToggles to a JSON-friendly dictionary."""
    result: Dict[str, Any] = {}
    for name in EFFECT_KEYS:
        toggle: EffectToggle = getattr(toggles, name)
        entry: Dict[str, Any] = {
            "enabled": toggle.enabled,
            "intensity": toggle.intensity,
        }
        if name in EFFECTS_WITH_TRIGGER_SOURCE:
            entry["trigger_source"] = toggle.trigger_source
        if name in EFFECTS_WITH_RADIUS:
            entry["radius"] = toggle.radius if toggle.radius is not None else 0.5
        result[name] = entry
    return result


def toggles_from_dict(data: Dict[str, Any]) -> EffectToggles:
    """Create EffectToggles from a dictionary (e.g., from JSON request)."""
    toggles = EffectToggles()

    for name in EFFECT_KEYS:
        if name in data:
            effect_data = data[name]
            default_trigger = GLITCH_DEFAULT_TRIGGER_SOURCE if name in GLITCH_STYLE_EFFECTS else DEFAULT_TRIGGER_SOURCE
            toggle = EffectToggle(
                enabled=effect_data.get("enabled", False),
                intensity=effect_data.get("intensity", 0.5),
                trigger_source=effect_data.get("trigger_source", default_trigger),
                radius=effect_data.get("radius"),
            )
            setattr(toggles, name, toggle)

    # Migrate legacy combined glitch: high-intensity glitch implied slice displacement
    if "glitch_slice" not in data and "glitch" in data:
        legacy = data["glitch"]
        if legacy.get("enabled") and legacy.get("intensity", 0) > 0.4:
            toggles.glitch_slice = EffectToggle(
                enabled=True,
                intensity=legacy.get("intensity", 0.4),
                trigger_source=legacy.get("trigger_source", GLITCH_DEFAULT_TRIGGER_SOURCE),
            )

    return toggles


def image_context_from_dict(data: Dict[str, Any]) -> ImageContext:
    """Create ImageContext from a dictionary (e.g., from image analysis)."""
    bounds_data = data.get("bounds", {})
    bounds = SubjectBounds(
        x=bounds_data.get("x", 0.25),
        y=bounds_data.get("y", 0.25),
        w=bounds_data.get("w", 0.5),
        h=bounds_data.get("h", 0.5)
    )
    
    glow_points = [
        GlowPoint(x=gp["x"], y=gp["y"], intensity=gp.get("intensity", 1.0))
        for gp in data.get("glow_points", [])
    ]
    
    return ImageContext(
        bounds=bounds,
        glow_points=glow_points,
        colors=data.get("colors", ["#FFFFFF", "#FFD700", "#FF6B35"]),
        mood=data.get("mood", "neutral")
    )


# Legacy support - map old settings to new toggles
def legacy_settings_to_toggles(
    motion_intensity: float,
    beat_reactivity: float,
    energy_level: float
) -> EffectToggles:
    """
    Convert legacy slider settings to new toggle system.
    For backwards compatibility during transition.
    """
    toggles = EffectToggles()
    
    # Map motion intensity to movement-related effects
    toggles.element_scale = EffectToggle(motion_intensity > 0.2, motion_intensity)
    toggles.ripple_wave = EffectToggle(motion_intensity > 0.6, motion_intensity * 0.6)
    
    # Map beat reactivity to beat-triggered effects
    toggles.element_glow = EffectToggle(beat_reactivity > 0.2, beat_reactivity)
    toggles.particle_burst = EffectToggle(beat_reactivity > 0.3, beat_reactivity)
    toggles.vignette_pulse = EffectToggle(beat_reactivity > 0.2, beat_reactivity * 0.8)
    
    # Map energy level to intensity-related effects
    toggles.glitch = EffectToggle(energy_level > 0.7, energy_level * 0.5, "onsets")
    toggles.glitch_slice = EffectToggle(energy_level > 0.8, energy_level * 0.5, "onsets")
    toggles.strobe_flash = EffectToggle(energy_level > 0.8, energy_level * 0.4)
    toggles.light_flares = EffectToggle(energy_level > 0.5, energy_level * 0.6)
    toggles.energy_trails = EffectToggle(energy_level > 0.4, energy_level * 0.5)
    
    toggles.background_dim = EffectToggle(False, 0.3 + energy_level * 0.3)
    
    # Film grain for lower energy
    toggles.film_grain = EffectToggle(energy_level < 0.4, (1 - energy_level) * 0.3)
    
    return toggles
