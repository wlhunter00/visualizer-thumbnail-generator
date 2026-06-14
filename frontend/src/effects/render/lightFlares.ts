import type { RGB } from '../colorUtils';
import { createOffscreen, previewScale } from './compositor';

/** Multi-ring flares + horizontal streak (matches backend apply_light_flares). */
export function applyLightFlares(
  source: HTMLCanvasElement,
  points: [number, number][],
  intensity: number,
  size: number,
  colors: RGB[],
  w: number,
  h: number,
): HTMLCanvasElement {
  if (intensity < 0.01 || !points.length) {
    const out = createOffscreen(w, h);
    out.getContext('2d')!.drawImage(source, 0, 0, w, h);
    return out;
  }

  const scaledSize = size * previewScale(w);
  const overlay = createOffscreen(w, h);
  const ctx = overlay.getContext('2d')!;
  const step = Math.max(3, Math.floor(5 * previewScale(w)));

  for (let i = 0; i < points.length; i++) {
    const [px, py] = points[i];
    const x = Math.floor(px * w);
    const y = Math.floor(py * h);
    const color = colors[i % colors.length] ?? [255, 255, 200];
    const flareRadius = scaledSize * intensity;

    for (let r = Math.floor(flareRadius); r > 0; r -= step) {
      const alpha = flareRadius > 0 ? Math.floor(intensity * 150 * (r / flareRadius)) : 0;
      ctx.fillStyle = `rgba(${color[0]},${color[1]},${color[2]},${alpha / 255})`;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    }

    const streakLength = Math.floor(scaledSize * intensity * 1.5);
    const dotRadius = Math.max(2, Math.floor(3 * previewScale(w)));
    for (let offset = -streakLength; offset < streakLength; offset += 2) {
      const dist = Math.abs(offset) / Math.max(streakLength, 1);
      const alpha = Math.floor(intensity * 100 * (1 - dist));
      ctx.fillStyle = `rgba(${color[0]},${color[1]},${color[2]},${alpha / 255})`;
      ctx.beginPath();
      ctx.arc(x + offset, y, dotRadius, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  ctx.filter = `blur(${Math.max(1, scaledSize / 5)}px)`;
  const blurred = createOffscreen(w, h);
  blurred.getContext('2d')!.drawImage(overlay, 0, 0);
  ctx.clearRect(0, 0, w, h);
  ctx.drawImage(blurred, 0, 0);
  ctx.filter = 'none';

  const result = createOffscreen(w, h);
  const rctx = result.getContext('2d')!;
  rctx.drawImage(source, 0, 0, w, h);
  rctx.drawImage(overlay, 0, 0);
  return result;
}
