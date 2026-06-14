import type { RGB } from '../colorUtils';
import type { SubjectBounds } from '../types';
import { createOffscreen, previewScale } from './compositor';

/** Stacked ellipses + blur glow (matches backend apply_element_glow). */
export function applyElementGlow(
  source: HTMLCanvasElement,
  bounds: SubjectBounds,
  intensity: number,
  radius: number,
  color: RGB,
  w: number,
  h: number,
): HTMLCanvasElement {
  if (intensity < 0.01) {
    const out = createOffscreen(w, h);
    out.getContext('2d')!.drawImage(source, 0, 0, w, h);
    return out;
  }

  const scaledRadius = radius * previewScale(w);
  const cx = bounds.center_x * w;
  const cy = bounds.center_y * h;
  const bw = bounds.w * w;
  const bh = bounds.h * h;

  const glow = createOffscreen(w, h);
  const gctx = glow.getContext('2d')!;
  const step = Math.max(3, Math.floor(5 * previewScale(w)));

  for (let i = Math.floor(scaledRadius); i > 0; i -= step) {
    const alpha = Math.min(255, Math.floor(intensity * 100 * (i / scaledRadius)));
    const rx = bw / 2 + i;
    const ry = bh / 2 + i;
    gctx.fillStyle = `rgba(${color[0]},${color[1]},${color[2]},${alpha / 255})`;
    gctx.beginPath();
    gctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
    gctx.fill();
  }

  gctx.filter = `blur(${scaledRadius / 3}px)`;
  const blurred = createOffscreen(w, h);
  blurred.getContext('2d')!.drawImage(glow, 0, 0);
  gctx.clearRect(0, 0, w, h);
  gctx.drawImage(blurred, 0, 0);
  gctx.filter = 'none';

  const result = createOffscreen(w, h);
  const rctx = result.getContext('2d')!;
  rctx.drawImage(source, 0, 0, w, h);
  rctx.globalCompositeOperation = 'lighter';
  rctx.drawImage(glow, 0, 0);
  rctx.globalCompositeOperation = 'source-over';
  return result;
}
