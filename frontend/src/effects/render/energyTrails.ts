import type { RGB } from '../colorUtils';
import { createOffscreen, previewScale } from './compositor';

interface EnergyTrailsParams {
  count: number;
  colors: RGB[];
  width: number;
  bounds_x: number;
  bounds_y: number;
  bounds_w: number;
  bounds_h: number;
  speed: number;
  time: number;
  intensity: number;
}

/** Arc polyline trails with blur (matches backend apply_energy_trails). */
export function applyEnergyTrails(
  source: HTMLCanvasElement,
  params: EnergyTrailsParams,
  w: number,
  h: number,
): HTMLCanvasElement {
  const overlay = createOffscreen(w, h);
  const ctx = overlay.getContext('2d')!;
  const trailWidth = params.width * previewScale(w);
  const centerX = (params.bounds_x + params.bounds_w / 2) * w;
  const centerY = (params.bounds_y + params.bounds_h / 2) * h;
  const orbitRx = (params.bounds_w / 2) * w * 1.2;
  const orbitRy = (params.bounds_h / 2) * h * 1.2;
  const alpha = Math.floor(params.intensity * 200);
  const trailLength = 0.3;

  for (let i = 0; i < params.count; i++) {
    const baseAngle = (i / params.count) * 2 * Math.PI;
    const angle = baseAngle + params.time * params.speed * 2 * Math.PI;
    const color = params.colors[i % params.colors.length] ?? [255, 255, 255];
    const steps = 20;

    for (let j = 0; j < steps - 1; j++) {
      const t0 = (j / (steps - 1)) * trailLength;
      const t1 = ((j + 1) / (steps - 1)) * trailLength;
      const a0 = angle - t0;
      const a1 = angle - t1;
      const fade0 = 1 - t0 / trailLength * 0.3;
      const fade1 = 1 - t1 / trailLength * 0.3;
      const x0 = centerX + Math.cos(a0) * orbitRx * fade0;
      const y0 = centerY + Math.sin(a0) * orbitRy * fade0;
      const x1 = centerX + Math.cos(a1) * orbitRx * fade1;
      const y1 = centerY + Math.sin(a1) * orbitRy * fade1;
      const fade = 1 - j / steps;
      const lineAlpha = (alpha * fade) / 255;
      ctx.strokeStyle = `rgba(${color[0]},${color[1]},${color[2]},${lineAlpha})`;
      ctx.lineWidth = trailWidth;
      ctx.beginPath();
      ctx.moveTo(x0, y0);
      ctx.lineTo(x1, y1);
      ctx.stroke();
    }
  }

  ctx.filter = `blur(${trailWidth}px)`;
  const blurred = createOffscreen(w, h);
  blurred.getContext('2d')!.drawImage(overlay, 0, 0);
  ctx.clearRect(0, 0, w, h);
  ctx.drawImage(blurred, 0, 0);
  ctx.filter = 'none';

  const result = createOffscreen(w, h);
  const rctx = result.getContext('2d')!;
  rctx.drawImage(source, 0, 0, w, h);
  rctx.globalAlpha = 1;
  rctx.drawImage(overlay, 0, 0);
  return result;
}
