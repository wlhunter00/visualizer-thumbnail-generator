"""
Effect Engine Module
Maps audio features to visual effect parameters based on toggle-based user settings.
No BPM-based assumptions - effects are controlled explicitly by user toggles.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional
from audio_analysis import AudioFeatures
import math


@dataclass
class EffectToggle:
    """A single effect toggle with enabled state and intensity."""
    enabled: bool = False
    intensity: float = 0.5  # 0-1


@dataclass
class EffectToggles:
    """All user-controlled effect toggles."""
    # Element effects
    element_glow: EffectToggle = field(default_factory=lambda: EffectToggle(True, 0.5))
    element_scale: EffectToggle = field(default_factory=lambda: EffectToggle(True, 0.3))
    neon_outline: EffectToggle = field(default_factory=lambda: EffectToggle(False, 0.5))
    echo_trail: EffectToggle = field(default_factory=lambda: EffectToggle(False, 0.4))
    
    # Particle effects
    particle_burst: EffectToggle = field(default_factory=lambda: EffectToggle(True, 0.5))
    energy_trails: EffectToggle = field(default_factory=lambda: EffectToggle(False, 0.4))
    light_flares: EffectToggle = field(default_factory=lambda: EffectToggle(False, 0.3))
    
    # Style effects
    glitch: EffectToggle = field(default_factory=lambda: EffectToggle(False, 0.3))
    ripple_wave: EffectToggle = field(default_factory=lambda: EffectToggle(False, 0.4))
    film_grain: EffectToggle = field(default_factory=lambda: EffectToggle(False, 0.2))
    strobe_flash: EffectToggle = field(default_factory=lambda: EffectToggle(False, 0.3))
    vignette_pulse: EffectToggle = field(default_factory=lambda: EffectToggle(True, 0.4))
    
    # Background
    background_dim: EffectToggle = field(default_factory=lambda: EffectToggle(True, 0.3))


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
    color: Tuple[int, int, int] = (0, 255, 255)  # Cyan default
    width: float = 3.0
    glow_radius: float = 10.0
    pulse_triggers: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class EchoTrailParams:
    """Parameters for echo/ghost trail effect."""
    enabled: bool = False
    intensity: float = 0.4
    trail_count: int = 5
    trail_spacing: float = 0.05  # Time offset between trails
    opacity_decay: float = 0.7  # Each trail is this much dimmer


@dataclass
class ParticleBurstParams:
    """Parameters for particle burst effect."""
    enabled: bool = True
    intensity: float = 0.5
    particle_count: int = 50
    colors: List[Tuple[int, int, int]] = field(default_factory=lambda: [(255, 200, 100)])
    size_range: Tuple[float, float] = (3, 12)
    speed: float = 200.0  # Pixels per second
    lifetime: float = 1.0  # Seconds
    triggers: List[Tuple[float, float]] = field(default_factory=list)  # (time, strength)
    origin_x: float = 0.5  # Normalized position
    origin_y: float = 0.5


@dataclass
class EnergyTrailsParams:
    """Parameters for energy trails effect."""
    enabled: bool = False
    intensity: float = 0.4
    trail_count: int = 8
    colors: List[Tuple[int, int, int]] = field(default_factory=lambda: [(255, 200, 100)])
    width: float = 2.0
    orbit_radius: float = 100.0
    speed: float = 1.0  # Revolutions per second
    center_x: float = 0.5
    center_y: float = 0.5


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
    """Parameters for glitch effect."""
    enabled: bool = False
    intensity: float = 0.3
    chromatic_aberration: float = 5.0
    rgb_split: float = 3.0
    scan_lines: bool = True
    scan_line_opacity: float = 0.1
    slice_displacement: bool = True
    triggers: List[Tuple[float, float, float]] = field(default_factory=list)  # (time, duration, intensity)


@dataclass
class RippleWaveParams:
    """Parameters for ripple wave effect."""
    enabled: bool = False
    intensity: float = 0.4
    center_x: float = 0.5
    center_y: float = 0.5
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
    base_strength: float = 0.3
    pulse_strength: float = 0.2
    triggers: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class BackgroundDimParams:
    """Parameters for background dim effect."""
    enabled: bool = True
    intensity: float = 0.3
    dim_amount: float = 0.3  # How much to darken (0-1)
    blur_amount: float = 2.0  # Blur radius


@dataclass
class EffectParameters:
    """All effect parameters for a video."""
    duration: float
    fps: int = 30
    subject_bounds: SubjectBounds = field(default_factory=SubjectBounds)
    
    # All 13 effects
    element_glow: ElementGlowParams = field(default_factory=ElementGlowParams)
    element_scale: ElementScaleParams = field(default_factory=ElementScaleParams)
    neon_outline: NeonOutlineParams = field(default_factory=NeonOutlineParams)
    echo_trail: EchoTrailParams = field(default_factory=EchoTrailParams)
    particle_burst: ParticleBurstParams = field(default_factory=ParticleBurstParams)
    energy_trails: EnergyTrailsParams = field(default_factory=EnergyTrailsParams)
    light_flares: LightFlaresParams = field(default_factory=LightFlaresParams)
    glitch: GlitchParams = field(default_factory=GlitchParams)
    ripple_wave: RippleWaveParams = field(default_factory=RippleWaveParams)
    film_grain: FilmGrainParams = field(default_factory=FilmGrainParams)
    strobe_flash: StrobeFlashParams = field(default_factory=StrobeFlashParams)
    vignette_pulse: VignettePulseParams = field(default_factory=VignettePulseParams)
    background_dim: BackgroundDimParams = field(default_factory=BackgroundDimParams)


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


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
        # Threshold scales inversely with intensity: at 100% intensity, all beats trigger
        threshold = 0.3 * (1 - toggles.element_glow.intensity)
        for beat_time, beat_strength in zip(audio_features.beat_times, audio_features.beat_strengths):
            if beat_strength >= threshold:
                glow_triggers.append((beat_time, beat_strength * toggles.element_glow.intensity))
    
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
        for beat_time, beat_strength in zip(audio_features.beat_times, audio_features.beat_strengths):
            scale_triggers.append((beat_time, beat_strength * toggles.element_scale.intensity))
    
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
    outline_triggers = []
    if toggles.neon_outline.enabled:
        for beat_time, beat_strength in zip(audio_features.beat_times, audio_features.beat_strengths):
            if beat_strength >= 0.4:
                outline_triggers.append((beat_time, beat_strength * toggles.neon_outline.intensity))
    
    # Use a contrasting color for outline
    outline_color = colors_rgb[1] if len(colors_rgb) > 1 else (0, 255, 255)
    
    neon_outline = NeonOutlineParams(
        enabled=toggles.neon_outline.enabled,
        intensity=toggles.neon_outline.intensity,
        color=outline_color,
        width=2 + toggles.neon_outline.intensity * 4,
        glow_radius=5 + toggles.neon_outline.intensity * 15,
        pulse_triggers=outline_triggers
    )
    
    # ========================================================================
    # ECHO TRAIL
    # ========================================================================
    echo_trail = EchoTrailParams(
        enabled=toggles.echo_trail.enabled,
        intensity=toggles.echo_trail.intensity,
        trail_count=3 + int(toggles.echo_trail.intensity * 5),
        trail_spacing=0.03 + (1 - toggles.echo_trail.intensity) * 0.05,
        opacity_decay=0.6 + (1 - toggles.echo_trail.intensity) * 0.2
    )
    
    # ========================================================================
    # PARTICLE BURST
    # ========================================================================
    burst_triggers = []
    if toggles.particle_burst.enabled:
        for beat_time, beat_strength in zip(audio_features.beat_times, audio_features.beat_strengths):
            if beat_strength >= 0.5:  # Only on strong beats
                burst_triggers.append((beat_time, beat_strength * toggles.particle_burst.intensity))
    
    particle_burst = ParticleBurstParams(
        enabled=toggles.particle_burst.enabled,
        intensity=toggles.particle_burst.intensity,
        particle_count=int(30 + toggles.particle_burst.intensity * 70),
        colors=colors_rgb[:3],
        size_range=(2 + toggles.particle_burst.intensity * 2, 8 + toggles.particle_burst.intensity * 8),
        speed=150 + toggles.particle_burst.intensity * 150,
        lifetime=0.8 + toggles.particle_burst.intensity * 0.6,
        triggers=burst_triggers,
        origin_x=bounds.center_x,
        origin_y=bounds.center_y
    )
    
    # ========================================================================
    # ENERGY TRAILS
    # ========================================================================
    energy_trails = EnergyTrailsParams(
        enabled=toggles.energy_trails.enabled,
        intensity=toggles.energy_trails.intensity,
        trail_count=4 + int(toggles.energy_trails.intensity * 8),
        colors=colors_rgb[:2],
        width=1 + toggles.energy_trails.intensity * 3,
        orbit_radius=50 + toggles.energy_trails.intensity * 100,
        speed=0.5 + toggles.energy_trails.intensity * 1.0,
        center_x=bounds.center_x,
        center_y=bounds.center_y
    )
    
    # ========================================================================
    # LIGHT FLARES
    # ========================================================================
    flare_triggers = []
    if toggles.light_flares.enabled:
        for beat_time, beat_strength in zip(audio_features.beat_times, audio_features.beat_strengths):
            if beat_strength >= 0.6:
                flare_triggers.append((beat_time, beat_strength * toggles.light_flares.intensity))
    
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
    # GLITCH
    # ========================================================================
    glitch_triggers = []
    if toggles.glitch.enabled:
        # Trigger on strong transients
        strong_onsets = [
            (t, s) for t, s in zip(audio_features.onset_times, audio_features.onset_strengths)
            if s > 0.7
        ]
        for i, (onset_time, strength) in enumerate(strong_onsets):
            if i % max(1, int(4 - toggles.glitch.intensity * 3)) == 0:
                glitch_duration = 0.05 + strength * 0.1
                glitch_triggers.append((onset_time, glitch_duration, strength * toggles.glitch.intensity))
    
    glitch = GlitchParams(
        enabled=toggles.glitch.enabled,
        intensity=toggles.glitch.intensity,
        chromatic_aberration=3 + toggles.glitch.intensity * 10,
        rgb_split=2 + toggles.glitch.intensity * 6,
        scan_lines=toggles.glitch.intensity > 0.3,
        scan_line_opacity=0.05 + toggles.glitch.intensity * 0.1,
        slice_displacement=toggles.glitch.intensity > 0.4,
        triggers=glitch_triggers
    )
    
    # ========================================================================
    # RIPPLE WAVE
    # ========================================================================
    ripple_triggers = []
    if toggles.ripple_wave.enabled:
        for beat_time, beat_strength in zip(audio_features.beat_times, audio_features.beat_strengths):
            if beat_strength >= 0.5:
                ripple_triggers.append((beat_time, beat_strength * toggles.ripple_wave.intensity))
    
    ripple_wave = RippleWaveParams(
        enabled=toggles.ripple_wave.enabled,
        intensity=toggles.ripple_wave.intensity,
        center_x=bounds.center_x,
        center_y=bounds.center_y,
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
        # Only on the strongest beats
        for beat_time, beat_strength in zip(audio_features.beat_times, audio_features.beat_strengths):
            if beat_strength >= 0.8:
                strobe_triggers.append(beat_time)
    
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
        for beat_time, beat_strength in zip(audio_features.beat_times, audio_features.beat_strengths):
            vignette_triggers.append((beat_time, beat_strength * toggles.vignette_pulse.intensity))
    
    vignette_pulse = VignettePulseParams(
        enabled=toggles.vignette_pulse.enabled,
        intensity=toggles.vignette_pulse.intensity,
        base_strength=0.2 + toggles.vignette_pulse.intensity * 0.2,
        pulse_strength=0.1 + toggles.vignette_pulse.intensity * 0.2,
        triggers=vignette_triggers
    )
    
    # ========================================================================
    # BACKGROUND DIM
    # ========================================================================
    background_dim = BackgroundDimParams(
        enabled=toggles.background_dim.enabled,
        intensity=toggles.background_dim.intensity,
        dim_amount=0.2 + toggles.background_dim.intensity * 0.4,
        blur_amount=1 + toggles.background_dim.intensity * 4
    )
    
    return EffectParameters(
        duration=duration,
        fps=30,
        subject_bounds=bounds,
        element_glow=element_glow,
        element_scale=element_scale,
        neon_outline=neon_outline,
        echo_trail=echo_trail,
        particle_burst=particle_burst,
        energy_trails=energy_trails,
        light_flares=light_flares,
        glitch=glitch,
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
    outline = effect_params.neon_outline
    if outline.enabled:
        outline_intensity = 0.5  # Base intensity
        for trigger_time, strength in outline.pulse_triggers:
            dt = time - trigger_time
            if 0 <= dt < 0.25:
                if dt < 0.03:
                    pulse = (dt / 0.03)
                else:
                    pulse = 1 - (dt - 0.03) / 0.22
                outline_intensity = max(outline_intensity, 0.5 + pulse * 0.5 * strength)
        values["neon_outline_intensity"] = outline_intensity * outline.intensity
        values["neon_outline_color"] = outline.color
        values["neon_outline_width"] = outline.width
        values["neon_outline_glow"] = outline.glow_radius
    else:
        values["neon_outline_intensity"] = 0
    
    # ========================================================================
    # ECHO TRAIL
    # ========================================================================
    echo = effect_params.echo_trail
    values["echo_trail_enabled"] = echo.enabled
    values["echo_trail_count"] = echo.trail_count if echo.enabled else 0
    values["echo_trail_spacing"] = echo.trail_spacing
    values["echo_trail_decay"] = echo.opacity_decay
    values["echo_trail_intensity"] = echo.intensity if echo.enabled else 0
    
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
                    "progress": progress,
                    "strength": strength,
                    "origin_x": burst.origin_x,
                    "origin_y": burst.origin_y
                })
        values["particle_bursts"] = active_bursts
        values["particle_burst_params"] = {
            "count": burst.particle_count,
            "colors": burst.colors,
            "size_range": burst.size_range,
            "speed": burst.speed,
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
            "orbit_radius": trails.orbit_radius,
            "speed": trails.speed,
            "center_x": trails.center_x,
            "center_y": trails.center_y,
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
        glitch_active = False
        glitch_intensity = 0
        for trigger_time, duration, strength in glitch.triggers:
            if trigger_time <= time < trigger_time + duration:
                glitch_active = True
                glitch_intensity = strength
                break
        values["glitch_active"] = glitch_active
        values["glitch_intensity"] = glitch_intensity
        values["glitch_chromatic"] = glitch.chromatic_aberration * glitch_intensity if glitch_active else 0
        values["glitch_rgb_split"] = glitch.rgb_split * glitch_intensity if glitch_active else 0
        values["glitch_scan_lines"] = glitch.scan_lines and glitch_active
        values["glitch_scan_opacity"] = glitch.scan_line_opacity if glitch_active else 0
        values["glitch_slice"] = glitch.slice_displacement and glitch_active
    else:
        values["glitch_active"] = False
        values["glitch_intensity"] = 0
    
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
                    "center_x": ripple.center_x,
                    "center_y": ripple.center_y
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
            if 0 <= dt < 0.3:
                if dt < 0.05:
                    pulse = dt / 0.05
                else:
                    pulse = 1 - (dt - 0.05) / 0.25
                vignette_strength = max(vignette_strength, vignette.base_strength + vignette.pulse_strength * pulse * strength)
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


def toggles_from_dict(data: Dict[str, Any]) -> EffectToggles:
    """Create EffectToggles from a dictionary (e.g., from JSON request)."""
    toggles = EffectToggles()
    
    effect_names = [
        "element_glow", "element_scale", "neon_outline", "echo_trail",
        "particle_burst", "energy_trails", "light_flares",
        "glitch", "ripple_wave", "film_grain", "strobe_flash", "vignette_pulse",
        "background_dim"
    ]
    
    for name in effect_names:
        if name in data:
            effect_data = data[name]
            toggle = EffectToggle(
                enabled=effect_data.get("enabled", False),
                intensity=effect_data.get("intensity", 0.5)
            )
            setattr(toggles, name, toggle)
    
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
    toggles.echo_trail = EffectToggle(motion_intensity > 0.5, motion_intensity * 0.7)
    toggles.ripple_wave = EffectToggle(motion_intensity > 0.6, motion_intensity * 0.6)
    
    # Map beat reactivity to beat-triggered effects
    toggles.element_glow = EffectToggle(beat_reactivity > 0.2, beat_reactivity)
    toggles.particle_burst = EffectToggle(beat_reactivity > 0.3, beat_reactivity)
    toggles.vignette_pulse = EffectToggle(beat_reactivity > 0.2, beat_reactivity * 0.8)
    
    # Map energy level to intensity-related effects
    toggles.neon_outline = EffectToggle(energy_level > 0.6, energy_level)
    toggles.glitch = EffectToggle(energy_level > 0.7, energy_level * 0.5)
    toggles.strobe_flash = EffectToggle(energy_level > 0.8, energy_level * 0.4)
    toggles.light_flares = EffectToggle(energy_level > 0.5, energy_level * 0.6)
    toggles.energy_trails = EffectToggle(energy_level > 0.4, energy_level * 0.5)
    
    # Background always on at moderate level
    toggles.background_dim = EffectToggle(True, 0.3 + energy_level * 0.3)
    
    # Film grain for lower energy
    toggles.film_grain = EffectToggle(energy_level < 0.4, (1 - energy_level) * 0.3)
    
    return toggles
