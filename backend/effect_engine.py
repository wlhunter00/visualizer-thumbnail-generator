"""
Effect Engine Module
Maps audio features to visual effect parameters based on user settings.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple
from audio_analysis import AudioFeatures
import math


@dataclass
class EffectSettings:
    """User-controlled high-level settings."""
    motion_intensity: float = 0.5  # 0-1
    beat_reactivity: float = 0.5  # 0-1
    energy_level: float = 0.5  # 0-1 (calm to energetic)


@dataclass
class ZoomPulseParams:
    """Parameters for zoom pulse effect."""
    enabled: bool = True
    base_scale: float = 1.0
    pulse_amplitude: float = 0.05  # Max zoom amount
    attack_time: float = 0.05  # Seconds to reach peak
    decay_time: float = 0.15  # Seconds to return to base
    triggers: List[Tuple[float, float]] = field(default_factory=list)  # (time, strength)


@dataclass
class ShakeParams:
    """Parameters for shake/vibration effect."""
    enabled: bool = True
    max_offset_x: float = 10  # Pixels
    max_offset_y: float = 10
    frequency: float = 30  # Hz
    triggers: List[Tuple[float, float]] = field(default_factory=list)  # (time, strength)


@dataclass
class BlurFocusParams:
    """Parameters for blur/focus shift effect."""
    enabled: bool = True
    max_blur: float = 3.0  # Blur radius
    focus_points: List[Tuple[float, float]] = field(default_factory=list)  # (time, blur_amount)


@dataclass
class ColorShiftParams:
    """Parameters for color/brightness shifts."""
    enabled: bool = True
    warmth_shift: float = 0.1  # Color temperature shift
    brightness_boost: float = 0.1  # Max brightness increase
    saturation_boost: float = 0.1  # Max saturation increase
    keyframes: List[Tuple[float, float, float, float]] = field(default_factory=list)  # (time, warmth, brightness, saturation)


@dataclass
class ParticleParams:
    """Parameters for particle overlay effect."""
    enabled: bool = True
    particle_type: str = "dust"  # dust, sparkle, bokeh
    density: float = 0.5  # 0-1
    size_range: Tuple[float, float] = (2, 8)
    speed: float = 1.0
    opacity: float = 0.4
    color: Tuple[int, int, int] = (255, 255, 255)
    reactive_density: List[Tuple[float, float]] = field(default_factory=list)  # (time, density_multiplier)


@dataclass
class GeometricParams:
    """Parameters for geometric overlay effect."""
    enabled: bool = True
    shape_type: str = "lines"  # lines, circles, grid
    complexity: float = 0.5  # 0-1, affects number of shapes
    line_width: float = 2.0
    opacity: float = 0.3
    color: Tuple[int, int, int] = (255, 255, 255)
    beat_sync: List[Tuple[float, float]] = field(default_factory=list)  # (time, intensity)


@dataclass
class GlitchParams:
    """Parameters for glitch effect."""
    enabled: bool = True
    chromatic_aberration: float = 5.0  # Pixel offset
    scan_lines: bool = True
    scan_line_opacity: float = 0.1
    rgb_split: float = 3.0
    triggers: List[Tuple[float, float, float]] = field(default_factory=list)  # (time, duration, intensity)


@dataclass
class EffectParameters:
    """All effect parameters for a video."""
    duration: float
    fps: int = 30
    zoom_pulse: ZoomPulseParams = field(default_factory=ZoomPulseParams)
    shake: ShakeParams = field(default_factory=ShakeParams)
    blur_focus: BlurFocusParams = field(default_factory=BlurFocusParams)
    color_shift: ColorShiftParams = field(default_factory=ColorShiftParams)
    particles: ParticleParams = field(default_factory=ParticleParams)
    geometric: GeometricParams = field(default_factory=GeometricParams)
    glitch: GlitchParams = field(default_factory=GlitchParams)


def calculate_effect_parameters(
    audio_features: AudioFeatures,
    settings: EffectSettings
) -> EffectParameters:
    """
    Calculate all effect parameters based on audio analysis and user settings.
    
    Args:
        audio_features: Analyzed audio data
        settings: User's high-level settings
    
    Returns:
        EffectParameters with all timing and values calculated
    """
    duration = audio_features.duration
    intensity = settings.motion_intensity
    reactivity = settings.beat_reactivity
    energy = settings.energy_level
    
    # === ZOOM PULSE ===
    # Triggered by beats, intensity controls amplitude
    zoom_triggers = []
    for i, (beat_time, beat_strength) in enumerate(zip(
        audio_features.beat_times, 
        audio_features.beat_strengths
    )):
        # Only trigger on stronger beats based on reactivity
        if beat_strength >= (1 - reactivity) * 0.5:
            trigger_strength = beat_strength * intensity
            zoom_triggers.append((beat_time, trigger_strength))
    
    zoom_pulse = ZoomPulseParams(
        enabled=intensity > 0.1,
        base_scale=1.0,
        pulse_amplitude=0.03 + (intensity * 0.07),  # 3-10% zoom
        attack_time=0.03 + (1 - reactivity) * 0.05,  # Faster attack with more reactivity
        decay_time=0.1 + (1 - reactivity) * 0.2,
        triggers=zoom_triggers
    )
    
    # === SHAKE ===
    # Triggered by strong onsets/transients
    shake_triggers = []
    onset_threshold = 0.6 - (reactivity * 0.3)  # Lower threshold = more triggers
    
    for onset_time, onset_strength in zip(
        audio_features.onset_times,
        audio_features.onset_strengths
    ):
        if onset_strength >= onset_threshold:
            shake_triggers.append((onset_time, onset_strength * intensity))
    
    shake = ShakeParams(
        enabled=intensity > 0.2 and energy > 0.3,
        max_offset_x=5 + intensity * 15,
        max_offset_y=5 + intensity * 15,
        frequency=20 + energy * 20,
        triggers=shake_triggers
    )
    
    # === BLUR/FOCUS ===
    # Follows energy envelope - blur increases during quiet parts
    focus_points = []
    for time, energy_val in audio_features.energy_envelope[::10]:  # Downsample
        # Invert: high energy = sharp focus, low energy = slight blur
        blur_amount = (1 - energy_val) * settings.motion_intensity * 2
        focus_points.append((time, blur_amount))
    
    blur_focus = BlurFocusParams(
        enabled=intensity > 0.2,
        max_blur=2 + intensity * 4,
        focus_points=focus_points
    )
    
    # === COLOR SHIFT ===
    # Based on frequency bands
    color_keyframes = []
    
    for i in range(0, len(audio_features.bass_energy), 10):
        time = audio_features.bass_energy[i][0]
        bass = audio_features.bass_energy[i][1] if i < len(audio_features.bass_energy) else 0.5
        mid = audio_features.mid_energy[i][1] if i < len(audio_features.mid_energy) else 0.5
        high = audio_features.high_energy[i][1] if i < len(audio_features.high_energy) else 0.5
        
        # Warmth from bass, brightness from mids, saturation from highs
        warmth = (bass - 0.5) * intensity * 0.3
        brightness = mid * intensity * 0.2
        saturation = high * energy * 0.2
        
        color_keyframes.append((time, warmth, brightness, saturation))
    
    color_shift = ColorShiftParams(
        enabled=True,
        warmth_shift=0.1 + energy * 0.15,
        brightness_boost=0.05 + intensity * 0.15,
        saturation_boost=0.05 + energy * 0.1,
        keyframes=color_keyframes
    )
    
    # === PARTICLES ===
    # Density reacts to high frequencies
    particle_density_keyframes = []
    for time, high_val in audio_features.high_energy[::5]:
        density_mult = 0.5 + high_val * energy
        particle_density_keyframes.append((time, density_mult))
    
    # Choose particle type based on energy level
    particle_type = "dust" if energy < 0.4 else ("sparkle" if energy < 0.7 else "bokeh")
    
    particles = ParticleParams(
        enabled=energy > 0.2,
        particle_type=particle_type,
        density=0.3 + energy * 0.5,
        size_range=(2 + energy * 2, 6 + energy * 6),
        speed=0.5 + energy * 1.0,
        opacity=0.2 + energy * 0.3,
        color=(255, 255, 255),
        reactive_density=particle_density_keyframes
    )
    
    # === GEOMETRIC ===
    # Beat-synced, complexity from reactivity
    geo_keyframes = []
    for beat_time, beat_strength in zip(
        audio_features.beat_times,
        audio_features.beat_strengths
    ):
        if beat_strength >= 0.4:
            geo_keyframes.append((beat_time, beat_strength * reactivity))
    
    # Shape type based on energy
    shape_type = "lines" if energy < 0.4 else ("circles" if energy < 0.7 else "grid")
    
    geometric = GeometricParams(
        enabled=reactivity > 0.3,
        shape_type=shape_type,
        complexity=reactivity,
        line_width=1 + reactivity * 2,
        opacity=0.15 + reactivity * 0.2,
        color=(255, 255, 255),
        beat_sync=geo_keyframes
    )
    
    # === GLITCH ===
    # Random triggers on strong transients
    glitch_triggers = []
    
    # Find strong transients for glitch moments
    strong_onsets = [
        (t, s) for t, s in zip(audio_features.onset_times, audio_features.onset_strengths)
        if s > 0.7
    ]
    
    # Only use occasional glitches
    for i, (onset_time, strength) in enumerate(strong_onsets):
        if i % max(1, int(4 - reactivity * 3)) == 0:  # More frequent with higher reactivity
            glitch_duration = 0.05 + strength * 0.1
            glitch_triggers.append((onset_time, glitch_duration, strength * intensity))
    
    glitch = GlitchParams(
        enabled=energy > 0.5 and intensity > 0.4,
        chromatic_aberration=3 + intensity * 7,
        scan_lines=energy > 0.6,
        scan_line_opacity=0.05 + energy * 0.1,
        rgb_split=2 + intensity * 5,
        triggers=glitch_triggers
    )
    
    return EffectParameters(
        duration=duration,
        fps=30,
        zoom_pulse=zoom_pulse,
        shake=shake,
        blur_focus=blur_focus,
        color_shift=color_shift,
        particles=particles,
        geometric=geometric,
        glitch=glitch
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
    
    # Zoom pulse
    zoom = effect_params.zoom_pulse
    if zoom.enabled:
        scale = zoom.base_scale
        for trigger_time, strength in zoom.triggers:
            dt = time - trigger_time
            if 0 <= dt < zoom.attack_time + zoom.decay_time:
                if dt < zoom.attack_time:
                    # Attack phase
                    progress = dt / zoom.attack_time
                    scale += zoom.pulse_amplitude * strength * progress
                else:
                    # Decay phase
                    decay_progress = (dt - zoom.attack_time) / zoom.decay_time
                    scale += zoom.pulse_amplitude * strength * (1 - decay_progress)
        values["zoom_scale"] = scale
    else:
        values["zoom_scale"] = 1.0
    
    # Shake
    shake = effect_params.shake
    if shake.enabled:
        offset_x, offset_y = 0, 0
        for trigger_time, strength in shake.triggers:
            dt = time - trigger_time
            if 0 <= dt < 0.15:  # Shake duration
                decay = 1 - (dt / 0.15)
                phase = dt * shake.frequency * 2 * math.pi
                offset_x += math.sin(phase) * shake.max_offset_x * strength * decay
                offset_y += math.cos(phase * 1.3) * shake.max_offset_y * strength * decay
        values["shake_offset"] = (offset_x, offset_y)
    else:
        values["shake_offset"] = (0, 0)
    
    # Blur - interpolate from keyframes
    blur = effect_params.blur_focus
    if blur.enabled and blur.focus_points:
        blur_amount = interpolate_keyframes(blur.focus_points, time)
        values["blur_amount"] = min(blur_amount, blur.max_blur)
    else:
        values["blur_amount"] = 0
    
    # Color shift - interpolate from keyframes
    color = effect_params.color_shift
    if color.enabled and color.keyframes:
        idx = find_keyframe_index([(k[0], 0) for k in color.keyframes], time)
        if idx < len(color.keyframes):
            kf = color.keyframes[idx]
            values["color_warmth"] = kf[1]
            values["color_brightness"] = kf[2]
            values["color_saturation"] = kf[3]
        else:
            values["color_warmth"] = 0
            values["color_brightness"] = 0
            values["color_saturation"] = 0
    else:
        values["color_warmth"] = 0
        values["color_brightness"] = 0
        values["color_saturation"] = 0
    
    # Particles
    particles = effect_params.particles
    if particles.enabled:
        density_mult = 1.0
        if particles.reactive_density:
            density_mult = interpolate_keyframes(particles.reactive_density, time)
        values["particle_density"] = particles.density * density_mult
        values["particle_type"] = particles.particle_type
        values["particle_opacity"] = particles.opacity
    else:
        values["particle_density"] = 0
    
    # Geometric
    geo = effect_params.geometric
    if geo.enabled:
        geo_intensity = 0
        for beat_time, strength in geo.beat_sync:
            dt = time - beat_time
            if 0 <= dt < 0.2:  # Brief flash on beat
                decay = 1 - (dt / 0.2)
                geo_intensity = max(geo_intensity, strength * decay)
        values["geometric_intensity"] = geo_intensity
        values["geometric_type"] = geo.shape_type
        values["geometric_opacity"] = geo.opacity * geo_intensity
    else:
        values["geometric_intensity"] = 0
    
    # Glitch
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
        values["chromatic_aberration"] = glitch.chromatic_aberration * glitch_intensity if glitch_active else 0
    else:
        values["glitch_active"] = False
        values["glitch_intensity"] = 0
    
    return values


def interpolate_keyframes(keyframes: List[Tuple[float, float]], time: float) -> float:
    """Linear interpolation between keyframes."""
    if not keyframes:
        return 0.0
    
    if time <= keyframes[0][0]:
        return keyframes[0][1]
    
    if time >= keyframes[-1][0]:
        return keyframes[-1][1]
    
    for i in range(len(keyframes) - 1):
        t1, v1 = keyframes[i]
        t2, v2 = keyframes[i + 1]
        
        if t1 <= time <= t2:
            progress = (time - t1) / (t2 - t1) if t2 != t1 else 0
            return v1 + (v2 - v1) * progress
    
    return keyframes[-1][1]


def find_keyframe_index(keyframes: List[Tuple[float, float]], time: float) -> int:
    """Find the index of the keyframe at or before the given time."""
    for i, (t, _) in enumerate(keyframes):
        if t > time:
            return max(0, i - 1)
    return len(keyframes) - 1

