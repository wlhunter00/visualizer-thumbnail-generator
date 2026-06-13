import type { EffectParameters } from './types';
import type { EffectValues } from './types';

export function getValuesAtTime(effectParams: EffectParameters, time: number): EffectValues {
  const values: EffectValues = {};

  const glow = effectParams.element_glow;
  if (glow.enabled) {
    let glowIntensity = 0.3;
    for (const [triggerTime, strength] of glow.pulse_triggers) {
      const dt = time - triggerTime;
      if (dt >= 0 && dt < 0.3) {
        const pulse = dt < 0.05
          ? (dt / 0.05) * strength
          : strength * (1 - (dt - 0.05) / 0.25);
        glowIntensity = Math.max(glowIntensity, 0.3 + pulse * 0.7);
      }
    }
    values.element_glow_intensity = glowIntensity * glow.intensity;
    values.element_glow_radius = glow.radius;
    values.element_glow_color = glow.color;
  } else {
    values.element_glow_intensity = 0;
  }

  const scale = effectParams.element_scale;
  if (scale.enabled) {
    let currentScale = scale.base_scale;
    for (const [triggerTime, strength] of scale.triggers) {
      const dt = time - triggerTime;
      if (dt >= 0 && dt < 0.2) {
        let scaleAdd: number;
        if (dt < 0.05) {
          scaleAdd = (dt / 0.05) * (scale.max_scale - scale.base_scale) * strength;
        } else {
          const progress = (dt - 0.05) / 0.15;
          scaleAdd = (1 - progress * progress) * (scale.max_scale - scale.base_scale) * strength;
        }
        currentScale = Math.max(currentScale, scale.base_scale + scaleAdd);
      }
    }
    values.element_scale = currentScale;
  } else {
    values.element_scale = 1.0;
  }

  const burst = effectParams.particle_burst;
  if (burst.enabled) {
    const activeBursts: Record<string, number>[] = [];
    for (const [triggerTime, strength] of burst.triggers) {
      const dt = time - triggerTime;
      if (dt >= 0 && dt < burst.lifetime) {
        activeBursts.push({
          progress: dt / burst.lifetime,
          strength,
          bounds_x: burst.bounds_x,
          bounds_y: burst.bounds_y,
          bounds_w: burst.bounds_w,
          bounds_h: burst.bounds_h,
        });
      }
    }
    values.particle_bursts = activeBursts;
    values.particle_burst_params = {
      count: burst.particle_count,
      colors: burst.colors,
      size_range: burst.size_range,
      speed: burst.speed,
      intensity: burst.intensity,
    };
  } else {
    values.particle_bursts = [];
  }

  const trails = effectParams.energy_trails;
  if (trails.enabled) {
    values.energy_trails_enabled = true;
    values.energy_trails_params = {
      count: trails.trail_count,
      colors: trails.colors,
      width: trails.width,
      bounds_x: trails.bounds_x,
      bounds_y: trails.bounds_y,
      bounds_w: trails.bounds_w,
      bounds_h: trails.bounds_h,
      speed: trails.speed,
      time,
      intensity: trails.intensity,
    };
  } else {
    values.energy_trails_enabled = false;
  }

  const flares = effectParams.light_flares;
  if (flares.enabled) {
    let flareIntensity = 0;
    for (const [triggerTime, strength] of flares.triggers) {
      const dt = time - triggerTime;
      if (dt >= 0 && dt < 0.4) {
        const pulse = dt < 0.05 ? dt / 0.05 : 1 - (dt - 0.05) / 0.35;
        flareIntensity = Math.max(flareIntensity, pulse * strength);
      }
    }
    values.light_flares_intensity = flareIntensity * flares.intensity;
    values.light_flares_points = flares.flare_points;
    values.light_flares_size = flares.size;
    values.light_flares_colors = flares.colors;
  } else {
    values.light_flares_intensity = 0;
  }

  const glitch = effectParams.glitch;
  if (glitch.enabled) {
    let glitchActive = false;
    let glitchIntensity = 0;
    for (const [triggerTime, duration, strength] of glitch.triggers) {
      if (time >= triggerTime && time < triggerTime + duration) {
        glitchActive = true;
        glitchIntensity = strength;
        break;
      }
    }
    values.glitch_active = glitchActive;
    values.glitch_intensity = glitchIntensity;
    values.glitch_chromatic = glitchActive ? glitch.chromatic_aberration * glitchIntensity : 0;
    values.glitch_rgb_split = glitchActive ? glitch.rgb_split * glitchIntensity : 0;
    values.glitch_scan_lines = glitch.scan_lines && glitchActive;
    values.glitch_scan_opacity = glitchActive ? glitch.scan_line_opacity : 0;
    values.glitch_slice = glitch.slice_displacement && glitchActive;
  } else {
    values.glitch_active = false;
    values.glitch_intensity = 0;
  }

  const ripple = effectParams.ripple_wave;
  if (ripple.enabled) {
    const activeRipples: Record<string, number>[] = [];
    for (const [triggerTime, strength] of ripple.triggers) {
      const dt = time - triggerTime;
      if (dt >= 0 && dt < 2.0) {
        activeRipples.push({
          radius: dt * ripple.speed,
          amplitude: ripple.amplitude * strength * (1 - dt / 2.0),
          wavelength: ripple.wavelength,
          bounds_x: ripple.bounds_x,
          bounds_y: ripple.bounds_y,
          bounds_w: ripple.bounds_w,
          bounds_h: ripple.bounds_h,
        });
      }
    }
    values.ripple_waves = activeRipples;
    values.ripple_intensity = ripple.intensity;
  } else {
    values.ripple_waves = [];
  }

  const grain = effectParams.film_grain;
  values.film_grain_enabled = grain.enabled;
  values.film_grain_intensity = grain.enabled ? grain.intensity : 0;
  values.film_grain_size = grain.grain_size;
  values.film_grain_color_var = grain.color_variation;

  const strobe = effectParams.strobe_flash;
  if (strobe.enabled) {
    let flashActive = false;
    for (const triggerTime of strobe.triggers) {
      if (time >= triggerTime && time < triggerTime + strobe.flash_duration) {
        flashActive = true;
        break;
      }
    }
    values.strobe_active = flashActive;
    values.strobe_intensity = flashActive ? strobe.intensity : 0;
    values.strobe_color = strobe.color;
  } else {
    values.strobe_active = false;
    values.strobe_intensity = 0;
  }

  const vignette = effectParams.vignette_pulse;
  if (vignette.enabled) {
    let vignetteStrength = vignette.base_strength;
    for (const [triggerTime, strength] of vignette.triggers) {
      const dt = time - triggerTime;
      if (dt >= 0 && dt < 0.4) {
        const pulse = dt < 0.08 ? dt / 0.08 : 1 - (dt - 0.08) / 0.32;
        const pulseAmount = vignette.pulse_strength * pulse * (0.5 + strength * 0.5);
        vignetteStrength = Math.max(vignetteStrength, vignette.base_strength + pulseAmount);
      }
    }
    values.vignette_strength = vignetteStrength;
  } else {
    values.vignette_strength = 0;
  }

  const bgDim = effectParams.background_dim;
  values.background_dim_enabled = bgDim.enabled;
  values.background_dim_amount = bgDim.enabled ? bgDim.dim_amount : 0;
  values.background_blur = bgDim.enabled ? bgDim.blur_amount : 0;
  values.background_focus_radius = bgDim.enabled ? bgDim.focus_radius : 0;

  values.subject_bounds = effectParams.subject_bounds;

  return values;
}
