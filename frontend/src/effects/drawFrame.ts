import type { RGB } from './colorUtils';
import type { EffectValues } from './types';
import type { SubjectBounds } from './types';
import { ParticleSystem } from './particleSystem';
import { applyElementGlow } from './render/elementGlow';
import { applyElementScale } from './render/elementScale';
import { applyEnergyTrails } from './render/energyTrails';
import { applyFilmGrain } from './render/filmGrain';
import { applyChromaticGlitch, applySliceGlitch, applyStrobe } from './render/glitch';
import { applyLightFlares } from './render/lightFlares';
import { applyNeonOutline } from './render/neonOutline';
import type { PreviewRenderState } from './render/previewState';
import { applyRippleWave } from './render/rippleWave';
import { applyVignette } from './render/vignette';
import { createOffscreen } from './render/compositor';

export interface DrawFrameState {
  particleSystem: ParticleSystem;
  lastClipTime: number;
  workBuffer: HTMLCanvasElement | null;
}

export function createDrawState(): DrawFrameState {
  return {
    particleSystem: new ParticleSystem(),
    lastClipTime: -1,
    workBuffer: null,
  };
}

function ensureWorkBuffer(state: DrawFrameState, w: number, h: number): HTMLCanvasElement {
  if (!state.workBuffer || state.workBuffer.width !== w || state.workBuffer.height !== h) {
    state.workBuffer = createOffscreen(w, h);
  }
  return state.workBuffer;
}

export function drawFrame(
  ctx: CanvasRenderingContext2D,
  baseImage: HTMLCanvasElement,
  values: EffectValues,
  state: DrawFrameState,
  clipTime: number,
  w: number,
  h: number,
  previewState?: PreviewRenderState | null,
) {
  const bounds = values.subject_bounds as SubjectBounds;
  let frame: HTMLCanvasElement = previewState?.backgroundDimBase ?? baseImage;

  const ripples = values.ripple_waves as {
    radius: number; amplitude: number; wavelength: number;
    bounds_x: number; bounds_y: number; bounds_w: number; bounds_h: number;
  }[];
  if (ripples?.length) {
    frame = applyRippleWave(
      frame, ripples,
      (values.ripple_intensity as number) ?? 0.5, w, h,
    );
  }

  const scale = values.element_scale as number ?? 1;
  if (Math.abs(scale - 1) > 0.001) {
    frame = applyElementScale(frame, bounds, scale, w, h);
  }

  const glowIntensity = values.element_glow_intensity as number;
  if (glowIntensity > 0.01) {
    frame = applyElementGlow(
      frame, bounds, glowIntensity,
      values.element_glow_radius as number,
      values.element_glow_color as RGB, w, h,
    );
  }

  const neonIntensity = values.neon_outline_intensity as number;
  if (neonIntensity > 0.01) {
    frame = applyNeonOutline(
      frame, bounds, neonIntensity,
      values.neon_outline_color as RGB,
      values.neon_outline_width as number,
      values.neon_outline_glow as number, w, h,
    );
  }

  ctx.clearRect(0, 0, w, h);
  ctx.drawImage(frame, 0, 0, w, h);

  const bursts = values.particle_bursts as Record<string, number>[];
  const burstParams = values.particle_burst_params as {
    count: number; colors: RGB[]; size_range: [number, number]; speed: number;
    lifetime: number; intensity: number;
  } | undefined;

  if (bursts?.length && burstParams) {
    for (const burst of bursts) {
      const triggerTime = burst.trigger_time as number;
      const key = `${triggerTime}-${burst.bounds_x}-${burst.bounds_y}`;
      state.particleSystem.spawnBurstFromBounds(
        burst.bounds_x, burst.bounds_y, burst.bounds_w, burst.bounds_h,
        burstParams.count, burstParams.colors, burstParams.size_range,
        burstParams.speed, burstParams.lifetime, clipTime, w, h, burst.strength,
        key,
      );
    }
  }

  const dt = state.lastClipTime >= 0 ? clipTime - state.lastClipTime : 1 / 60;
  state.particleSystem.update(clipTime, Math.min(dt, 0.05));
  state.particleSystem.draw(ctx, clipTime);
  state.lastClipTime = clipTime;

  const work = ensureWorkBuffer(state, w, h);
  const wctx = work.getContext('2d')!;
  wctx.clearRect(0, 0, w, h);
  wctx.drawImage(ctx.canvas, 0, 0, w, h);
  let post = work;

  if (values.energy_trails_enabled) {
    post = applyEnergyTrails(
      post, values.energy_trails_params as Parameters<typeof applyEnergyTrails>[1], w, h,
    );
  }

  const flareIntensity = values.light_flares_intensity as number;
  if (flareIntensity > 0.01) {
    post = applyLightFlares(
      post,
      values.light_flares_points as [number, number][],
      flareIntensity,
      values.light_flares_size as number,
      values.light_flares_colors as RGB[],
      w, h,
    );
  }

  const vignetteStrength = values.vignette_strength as number;
  if (vignetteStrength > 0.01 && previewState?.vignetteDistSq) {
    post = applyVignette(post, vignetteStrength, previewState.vignetteDistSq, w, h);
  }

  if (values.film_grain_enabled) {
    post = applyFilmGrain(
      post,
      values.film_grain_intensity as number,
      values.film_grain_size as number,
      w, h,
    );
  }

  if (values.strobe_active) {
    post = applyStrobe(
      post,
      values.strobe_intensity as number,
      values.strobe_color as RGB,
      w, h,
    );
  }

  if (values.glitch_active || values.glitch_slice_active) {
    const snapshot = createOffscreen(w, h);
    snapshot.getContext('2d')!.drawImage(post, 0, 0, w, h);

    if (values.glitch_active) {
      post = applyChromaticGlitch(
        snapshot,
        baseImage,
        values.glitch_chromatic as number,
        values.glitch_rgb_split as number,
        values.glitch_intensity as number,
        values.glitch_scan_lines as boolean,
        values.glitch_scan_opacity as number,
        w, h,
      );
    } else {
      post = snapshot;
    }

    if (values.glitch_slice_active) {
      const sliceSource = values.glitch_active ? post : snapshot;
      post = applySliceGlitch(
        sliceSource,
        values.glitch_slice_offset as number,
        values.glitch_slice_seed as number,
        w, h,
      );
    }
  }

  ctx.clearRect(0, 0, w, h);
  ctx.drawImage(post, 0, 0, w, h);
}

export function resetDrawState(state: DrawFrameState) {
  state.particleSystem.reset();
  state.lastClipTime = -1;
}
