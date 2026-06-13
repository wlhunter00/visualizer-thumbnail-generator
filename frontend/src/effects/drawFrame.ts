import type { EffectValues } from './types';
import type { RGB } from './colorUtils';
import { ParticleSystem } from './particleSystem';

export interface DrawFrameState {
  particleSystem: ParticleSystem;
  lastClipTime: number;
  noiseCanvas: HTMLCanvasElement | null;
}

export function createDrawState(): DrawFrameState {
  return {
    particleSystem: new ParticleSystem(),
    lastClipTime: -1,
    noiseCanvas: null,
  };
}

function drawSubjectClipped(
  ctx: CanvasRenderingContext2D,
  baseImage: HTMLCanvasElement,
  w: number,
  h: number,
  bounds: { x: number; y: number; w: number; h: number; center_x: number; center_y: number },
  scale: number,
  alpha: number,
  offsetX = 0,
  offsetY = 0
) {
  const cx = bounds.center_x * w;
  const cy = bounds.center_y * h;
  const ecx = (bounds.x + bounds.w / 2) * w;
  const ecy = (bounds.y + bounds.h / 2) * h;

  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.translate(cx + offsetX, cy + offsetY);
  ctx.scale(scale, scale);
  ctx.translate(-cx, -cy);
  ctx.beginPath();
  ctx.ellipse(
    ecx, ecy,
    (bounds.w / 2) * w, (bounds.h / 2) * h,
    0, 0, Math.PI * 2
  );
  ctx.clip();
  ctx.drawImage(baseImage, 0, 0, w, h);
  ctx.restore();
}

function getNoiseCanvas(state: DrawFrameState, w: number, h: number): HTMLCanvasElement {
  if (!state.noiseCanvas) {
    state.noiseCanvas = document.createElement('canvas');
  }
  if (state.noiseCanvas.width !== w || state.noiseCanvas.height !== h) {
    state.noiseCanvas.width = w;
    state.noiseCanvas.height = h;
    const nctx = state.noiseCanvas.getContext('2d')!;
    const imgData = nctx.createImageData(w, h);
    for (let i = 0; i < imgData.data.length; i += 4) {
      const v = Math.random() * 255;
      imgData.data[i] = v;
      imgData.data[i + 1] = v;
      imgData.data[i + 2] = v;
      imgData.data[i + 3] = 255;
    }
    nctx.putImageData(imgData, 0, 0);
  }
  return state.noiseCanvas;
}

function drawVignette(ctx: CanvasRenderingContext2D, w: number, h: number, strength: number) {
  if (strength <= 0) return;
  const gradient = ctx.createRadialGradient(w / 2, h / 2, w * 0.2, w / 2, h / 2, w * 0.75);
  gradient.addColorStop(0, 'rgba(0,0,0,0)');
  gradient.addColorStop(1, `rgba(0,0,0,${Math.min(0.9, strength)})`);
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, w, h);
}

function drawGlow(ctx: CanvasRenderingContext2D, w: number, h: number, values: EffectValues) {
  const intensity = values.element_glow_intensity as number;
  if (!intensity || intensity <= 0) return;
  const color = values.element_glow_color as RGB;
  const radius = values.element_glow_radius as number;
  const bounds = values.subject_bounds as { center_x: number; center_y: number };
  const cx = bounds.center_x * w;
  const cy = bounds.center_y * h;

  ctx.save();
  ctx.globalCompositeOperation = 'screen';
  const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius * (w / 540));
  gradient.addColorStop(0, `rgba(${color[0]},${color[1]},${color[2]},${intensity * 0.6})`);
  gradient.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, w, h);
  ctx.restore();
}

function drawNeonOutline(ctx: CanvasRenderingContext2D, w: number, h: number, values: EffectValues) {
  const intensity = values.neon_outline_intensity as number;
  if (!intensity || intensity <= 0) return;
  const color = values.neon_outline_color as RGB;
  const width = values.neon_outline_width as number;
  const glow = values.neon_outline_glow as number;
  const bounds = values.subject_bounds as { x: number; y: number; w: number; h: number };

  const x = bounds.x * w;
  const y = bounds.y * h;
  const bw = bounds.w * w;
  const bh = bounds.h * h;

  ctx.save();
  ctx.strokeStyle = `rgba(${color[0]},${color[1]},${color[2]},${intensity})`;
  ctx.lineWidth = width;
  ctx.shadowColor = `rgb(${color[0]},${color[1]},${color[2]})`;
  ctx.shadowBlur = glow;
  ctx.beginPath();
  ctx.ellipse(x + bw / 2, y + bh / 2, bw / 2, bh / 2, 0, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
}

function drawBackgroundDim(
  ctx: CanvasRenderingContext2D,
  sourceCanvas: HTMLCanvasElement,
  w: number,
  h: number,
  values: EffectValues
) {
  if (!values.background_dim_enabled) return;
  const dimAmount = values.background_dim_amount as number;
  const blurAmount = values.background_blur as number;
  const focusRadius = (values.background_focus_radius as number) ?? 0.5;
  if (dimAmount < 0.01 && blurAmount < 0.1) return;

  const bounds = values.subject_bounds as { x: number; y: number; w: number; h: number };
  const bx = bounds.x * w;
  const by = bounds.y * h;
  const bw = bounds.w * w;
  const bh = bounds.h * h;
  const minDim = Math.min(bw, bh);
  const maxDim = Math.max(bw, bh);
  const innerR = minDim * (0.05 + focusRadius * 0.4);
  const outerR = maxDim * (0.35 + focusRadius * 0.9) + minDim * (0.1 + focusRadius * 0.3);

  const offscreen = document.createElement('canvas');
  offscreen.width = w;
  offscreen.height = h;
  const offCtx = offscreen.getContext('2d')!;
  offCtx.filter = blurAmount > 0.1 ? `blur(${blurAmount}px) brightness(${1 - dimAmount})` : `brightness(${1 - dimAmount})`;
  offCtx.drawImage(sourceCanvas, 0, 0);

  ctx.drawImage(offscreen, 0, 0);

  ctx.save();
  ctx.globalCompositeOperation = 'destination-out';
  const mask = ctx.createRadialGradient(
    bx + bw / 2, by + bh / 2, innerR,
    bx + bw / 2, by + bh / 2, outerR
  );
  mask.addColorStop(0, 'rgba(0,0,0,0)');
  mask.addColorStop(0.6, 'rgba(0,0,0,0.3)');
  mask.addColorStop(1, 'rgba(0,0,0,1)');
  ctx.fillStyle = mask;
  ctx.fillRect(0, 0, w, h);
  ctx.globalCompositeOperation = 'destination-over';
  ctx.drawImage(sourceCanvas, 0, 0);
  ctx.globalCompositeOperation = 'source-over';
  ctx.restore();
}

function drawFilmGrain(ctx: CanvasRenderingContext2D, state: DrawFrameState, w: number, h: number, values: EffectValues) {
  if (!values.film_grain_enabled) return;
  const intensity = values.film_grain_intensity as number;
  if (intensity <= 0) return;
  const noise = getNoiseCanvas(state, w, h);
  ctx.save();
  ctx.globalAlpha = intensity * 0.25;
  ctx.drawImage(noise, 0, 0);
  ctx.restore();
}

function drawStrobe(ctx: CanvasRenderingContext2D, w: number, h: number, values: EffectValues) {
  if (!values.strobe_active) return;
  const intensity = values.strobe_intensity as number;
  const color = values.strobe_color as RGB;
  ctx.fillStyle = `rgba(${color[0]},${color[1]},${color[2]},${intensity * 0.7})`;
  ctx.fillRect(0, 0, w, h);
}

function drawGlitch(ctx: CanvasRenderingContext2D, sourceCanvas: HTMLCanvasElement, w: number, h: number, values: EffectValues) {
  if (!values.glitch_active) return;
  const rgbSplit = values.glitch_rgb_split as number;
  const scanOpacity = values.glitch_scan_opacity as number;

  if (rgbSplit > 0) {
    ctx.save();
    ctx.globalCompositeOperation = 'screen';
    ctx.globalAlpha = 0.4;
    ctx.drawImage(sourceCanvas, rgbSplit, 0);
    ctx.globalCompositeOperation = 'multiply';
    ctx.drawImage(sourceCanvas, -rgbSplit, 0);
    ctx.restore();
  }

  if (values.glitch_slice) {
    const sliceH = Math.floor(h / 8);
    for (let i = 0; i < 8; i += 2) {
      const offset = (Math.random() - 0.5) * rgbSplit * 4;
      ctx.drawImage(sourceCanvas, 0, i * sliceH, w, sliceH, offset, i * sliceH, w, sliceH);
    }
  }

  if (values.glitch_scan_lines && scanOpacity > 0) {
    ctx.fillStyle = `rgba(0,0,0,${scanOpacity})`;
    for (let y = 0; y < h; y += 4) {
      ctx.fillRect(0, y, w, 2);
    }
  }
}

function drawEnergyTrails(ctx: CanvasRenderingContext2D, w: number, h: number, values: EffectValues) {
  if (!values.energy_trails_enabled) return;
  const params = values.energy_trails_params as {
    count: number; colors: RGB[]; width: number;
    bounds_x: number; bounds_y: number; bounds_w: number; bounds_h: number;
    speed: number; time: number; intensity: number;
  };
  const cx = (params.bounds_x + params.bounds_w / 2) * w;
  const cy = (params.bounds_y + params.bounds_h / 2) * h;
  const rx = (params.bounds_w / 2) * w * 1.2;
  const ry = (params.bounds_h / 2) * h * 1.2;

  ctx.save();
  ctx.lineWidth = params.width;
  ctx.globalAlpha = params.intensity;
  for (let i = 0; i < params.count; i++) {
    const angle = params.time * params.speed * Math.PI * 2 + (i / params.count) * Math.PI * 2;
    const color = params.colors[i % params.colors.length];
    const x = cx + Math.cos(angle) * rx;
    const y = cy + Math.sin(angle) * ry;
    ctx.strokeStyle = `rgb(${color[0]},${color[1]},${color[2]})`;
    ctx.shadowColor = ctx.strokeStyle;
    ctx.shadowBlur = 8;
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.restore();
}

function drawLightFlares(ctx: CanvasRenderingContext2D, w: number, h: number, values: EffectValues) {
  const intensity = values.light_flares_intensity as number;
  if (!intensity || intensity <= 0) return;
  const points = values.light_flares_points as [number, number][];
  const size = values.light_flares_size as number;
  const colors = values.light_flares_colors as RGB[];

  for (const [px, py] of points) {
    const cx = px * w;
    const cy = py * h;
    const color = colors[0] ?? [255, 255, 200];
    const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, size * intensity * (w / 540));
    gradient.addColorStop(0, `rgba(${color[0]},${color[1]},${color[2]},${intensity * 0.8})`);
    gradient.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, w, h);
  }
}

function drawRipple(ctx: CanvasRenderingContext2D, w: number, h: number, values: EffectValues) {
  const ripples = values.ripple_waves as Record<string, number>[];
  if (!ripples.length) return;
  for (const ripple of ripples) {
    const cx = (ripple.bounds_x + ripple.bounds_w / 2) * w;
    const cy = (ripple.bounds_y + ripple.bounds_h / 2) * h;
    ctx.save();
    ctx.strokeStyle = `rgba(255,255,255,${ripple.amplitude / 20})`;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.ellipse(cx, cy, ripple.radius, ripple.radius * 0.8, 0, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }
}

export function drawFrame(
  ctx: CanvasRenderingContext2D,
  baseImage: HTMLCanvasElement,
  values: EffectValues,
  state: DrawFrameState,
  clipTime: number,
  w: number,
  h: number
) {
  const scale = values.element_scale as number ?? 1;
  const bounds = values.subject_bounds as { center_x: number; center_y: number };

  // Base image with scale pulse
  ctx.save();
  if (scale !== 1) {
    const cx = bounds.center_x * w;
    const cy = bounds.center_y * h;
    ctx.translate(cx, cy);
    ctx.scale(scale, scale);
    ctx.translate(-cx, -cy);
  }
  ctx.drawImage(baseImage, 0, 0, w, h);
  ctx.restore();

  // Background dim (needs base drawn first)
  drawBackgroundDim(ctx, baseImage, w, h, values);

  const b = values.subject_bounds as { x: number; y: number; w: number; h: number; center_x: number; center_y: number };

  // Re-draw subject on top after dim
  drawSubjectClipped(ctx, baseImage, w, h, b, scale, 1);

  drawGlow(ctx, w, h, values);
  drawNeonOutline(ctx, w, h, values);

  drawEnergyTrails(ctx, w, h, values);
  drawLightFlares(ctx, w, h, values);

  // Particle bursts
  const bursts = values.particle_bursts as Record<string, number>[];
  const burstParams = values.particle_burst_params as {
    count: number; colors: RGB[]; size_range: [number, number]; speed: number; intensity: number;
  } | undefined;
  if (bursts.length && burstParams) {
    for (const burst of bursts) {
      if (burst.progress < 0.05) {
        const key = `${clipTime}-${burst.bounds_x}-${burst.bounds_y}`;
        state.particleSystem.spawnBurstFromBounds(
          burst.bounds_x, burst.bounds_y, burst.bounds_w, burst.bounds_h,
          burstParams.count, burstParams.colors, burstParams.size_range,
          burstParams.speed, 1.0, clipTime, w, h, burst.strength,
          key
        );
      }
    }
  }

  const dt = state.lastClipTime >= 0 ? clipTime - state.lastClipTime : 1 / 60;
  state.particleSystem.update(clipTime, Math.min(dt, 0.05));
  state.particleSystem.draw(ctx, clipTime);
  state.lastClipTime = clipTime;

  drawRipple(ctx, w, h, values);
  drawVignette(ctx, w, h, values.vignette_strength as number);
  drawFilmGrain(ctx, state, w, h, values);
  drawStrobe(ctx, w, h, values);
  drawGlitch(ctx, baseImage, w, h, values);
}

export function resetDrawState(state: DrawFrameState) {
  state.particleSystem.reset();
  state.lastClipTime = -1;
}
