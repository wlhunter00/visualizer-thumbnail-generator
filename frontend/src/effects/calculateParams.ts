import type { AudioFeatures, EffectToggles } from '../types';
import { buildTriggers } from './buildTriggers';
import { hexToRgb, prepareParticleColors, type RGB } from './colorUtils';
import type { EffectParameters, ImageContext } from './types';

export function calculateEffectParams(
  audioFeatures: AudioFeatures,
  toggles: EffectToggles,
  imageContext?: ImageContext | null
): EffectParameters {
  const ctx = imageContext ?? {
    bounds: { x: 0.25, y: 0.25, w: 0.5, h: 0.5, center_x: 0.5, center_y: 0.5 },
    glow_points: [],
    colors: ['#FFFFFF', '#FFD700', '#FF6B35'],
    mood: 'neutral',
  };
  const bounds = ctx.bounds;
  const colorsRgb: RGB[] = ctx.colors.slice(0, 5).map(hexToRgb);
  const primaryColor = colorsRgb[0] ?? [255, 200, 100] as RGB;

  const ts = (key: keyof EffectToggles) => toggles[key].trigger_source ?? 'beats';

  const glowTriggers = toggles.element_glow.enabled
    ? buildTriggers(audioFeatures, ts('element_glow'), toggles.element_glow.intensity, 0.3)
    : [];

  const scaleTriggers = toggles.element_scale.enabled
    ? buildTriggers(audioFeatures, ts('element_scale'), toggles.element_scale.intensity, 0.3, false)
    : [];

  const outlineTriggers = toggles.neon_outline.enabled
    ? buildTriggers(audioFeatures, ts('neon_outline'), toggles.neon_outline.intensity, 0.4)
    : [];

  const outlineColor = colorsRgb[1] ?? [0, 255, 255] as RGB;

  const burstTriggers = toggles.particle_burst.enabled
    ? buildTriggers(audioFeatures, ts('particle_burst'), toggles.particle_burst.intensity, 0.4)
    : [];

  const particleColors = prepareParticleColors(colorsRgb.slice(0, 5));
  const trailColors = prepareParticleColors(colorsRgb.slice(0, 3)).slice(0, 2);

  const flareTriggers = toggles.light_flares.enabled
    ? buildTriggers(audioFeatures, ts('light_flares'), toggles.light_flares.intensity, 0.6)
    : [];

  const flarePoints: [number, number][] = ctx.glow_points.length
    ? ctx.glow_points.map(gp => [gp.x, gp.y])
    : [[bounds.center_x, bounds.center_y]];

  const glitchTriggers: [number, number, number][] = [];
  if (toggles.glitch.enabled) {
    const intensity = toggles.glitch.intensity;
    const sourceTriggers = buildTriggers(
      audioFeatures,
      ts('glitch'),
      intensity,
      0.5
    );
    for (const [triggerTime, strength] of sourceTriggers) {
      const glitchDuration = 0.08 + strength * 0.15 + intensity * 0.12;
      glitchTriggers.push([triggerTime, glitchDuration, strength]);
    }
    if (ts('glitch') === 'onsets' && intensity > 0.5) {
      const beatTriggers = buildTriggers(audioFeatures, 'beats', intensity * 0.8, 0.4);
      for (const [beatTime, beatStrength] of beatTriggers) {
        const glitchDuration = 0.06 + beatStrength * 0.1 + intensity * 0.08;
        glitchTriggers.push([beatTime, glitchDuration, beatStrength]);
      }
    }
  }

  const rippleTriggers = toggles.ripple_wave.enabled
    ? buildTriggers(audioFeatures, ts('ripple_wave'), toggles.ripple_wave.intensity, 0.5)
    : [];

  const strobeTriggers = toggles.strobe_flash.enabled
    ? buildTriggers(audioFeatures, ts('strobe_flash'), toggles.strobe_flash.intensity, 0.8).map(([t]) => t)
    : [];

  const vignetteTriggers = toggles.vignette_pulse.enabled
    ? buildTriggers(audioFeatures, ts('vignette_pulse'), toggles.vignette_pulse.intensity, 0.3, false)
    : [];

  return {
    duration: audioFeatures.duration,
    fps: 30,
    subject_bounds: bounds,
    element_glow: {
      enabled: toggles.element_glow.enabled,
      intensity: toggles.element_glow.intensity,
      color: primaryColor,
      radius: 30 + toggles.element_glow.intensity * 70,
      pulse_triggers: glowTriggers,
    },
    element_scale: {
      enabled: toggles.element_scale.enabled,
      intensity: toggles.element_scale.intensity,
      base_scale: 1.0,
      max_scale: 1.0 + toggles.element_scale.intensity * 0.15,
      triggers: scaleTriggers,
    },
    neon_outline: {
      enabled: toggles.neon_outline.enabled,
      intensity: toggles.neon_outline.intensity,
      color: outlineColor,
      width: 2 + toggles.neon_outline.intensity * 4,
      glow_radius: 5 + toggles.neon_outline.intensity * 15,
      pulse_triggers: outlineTriggers,
    },
    echo_trail: {
      enabled: toggles.echo_trail.enabled,
      intensity: toggles.echo_trail.intensity,
      trail_count: 3 + Math.floor(toggles.echo_trail.intensity * 5),
      trail_spacing: 0.03 + (1 - toggles.echo_trail.intensity) * 0.05,
      opacity_decay: 0.6 + (1 - toggles.echo_trail.intensity) * 0.2,
    },
    particle_burst: {
      enabled: toggles.particle_burst.enabled,
      intensity: toggles.particle_burst.intensity,
      particle_count: Math.floor(30 + toggles.particle_burst.intensity * 70),
      colors: particleColors,
      size_range: [
        2 + toggles.particle_burst.intensity * 2,
        8 + toggles.particle_burst.intensity * 8,
      ],
      speed: 150 + toggles.particle_burst.intensity * 150,
      lifetime: 0.8 + toggles.particle_burst.intensity * 0.6,
      triggers: burstTriggers,
      bounds_x: bounds.x,
      bounds_y: bounds.y,
      bounds_w: bounds.w,
      bounds_h: bounds.h,
    },
    energy_trails: {
      enabled: toggles.energy_trails.enabled,
      intensity: toggles.energy_trails.intensity,
      trail_count: 4 + Math.floor(toggles.energy_trails.intensity * 8),
      colors: trailColors.length ? trailColors : [[255, 255, 255]],
      width: 1 + toggles.energy_trails.intensity * 3,
      speed: 0.5 + toggles.energy_trails.intensity,
      bounds_x: bounds.x,
      bounds_y: bounds.y,
      bounds_w: bounds.w,
      bounds_h: bounds.h,
    },
    light_flares: {
      enabled: toggles.light_flares.enabled,
      intensity: toggles.light_flares.intensity,
      flare_points: flarePoints,
      colors: [[255, 255, 200], ...colorsRgb.slice(0, 1)],
      size: 50 + toggles.light_flares.intensity * 100,
      triggers: flareTriggers,
    },
    glitch: {
      enabled: toggles.glitch.enabled,
      intensity: toggles.glitch.intensity,
      chromatic_aberration: 3 + toggles.glitch.intensity * 10,
      rgb_split: 2 + toggles.glitch.intensity * 6,
      scan_lines: toggles.glitch.intensity > 0.3,
      scan_line_opacity: 0.05 + toggles.glitch.intensity * 0.1,
      slice_displacement: toggles.glitch.intensity > 0.4,
      triggers: glitchTriggers,
    },
    ripple_wave: {
      enabled: toggles.ripple_wave.enabled,
      intensity: toggles.ripple_wave.intensity,
      bounds_x: bounds.x,
      bounds_y: bounds.y,
      bounds_w: bounds.w,
      bounds_h: bounds.h,
      wavelength: 30 + (1 - toggles.ripple_wave.intensity) * 40,
      amplitude: 5 + toggles.ripple_wave.intensity * 15,
      speed: 150 + toggles.ripple_wave.intensity * 150,
      triggers: rippleTriggers,
    },
    film_grain: {
      enabled: toggles.film_grain.enabled,
      intensity: toggles.film_grain.intensity,
      grain_size: 1 + toggles.film_grain.intensity * 2,
      color_variation: 0.05 + toggles.film_grain.intensity * 0.15,
    },
    strobe_flash: {
      enabled: toggles.strobe_flash.enabled,
      intensity: toggles.strobe_flash.intensity,
      flash_duration: 0.03 + toggles.strobe_flash.intensity * 0.05,
      color: [255, 255, 255],
      triggers: strobeTriggers,
    },
    vignette_pulse: {
      enabled: toggles.vignette_pulse.enabled,
      intensity: toggles.vignette_pulse.intensity,
      base_strength: 0.3 + toggles.vignette_pulse.intensity * 0.4,
      pulse_strength: 0.3 + toggles.vignette_pulse.intensity * 0.5,
      triggers: vignetteTriggers,
    },
    background_dim: {
      enabled: toggles.background_dim.enabled,
      intensity: toggles.background_dim.intensity,
      dim_amount: 0.2 + toggles.background_dim.intensity * 0.4,
      blur_amount: 1 + toggles.background_dim.intensity * 4,
    },
  };
}
