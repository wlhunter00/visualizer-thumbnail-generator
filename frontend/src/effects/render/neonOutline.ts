import type { RGB } from '../colorUtils';
import type { SubjectBounds } from '../types';
import { createOffscreen, previewScale } from './compositor';

/** Stroked ellipse + Gaussian blur glow (matches backend apply_neon_outline). */
export function applyNeonOutline(
  source: HTMLCanvasElement,
  bounds: SubjectBounds,
  intensity: number,
  color: RGB,
  lineWidth: number,
  glowRadius: number,
  w: number,
  h: number,
): HTMLCanvasElement {
  if (intensity < 0.01) {
    const out = createOffscreen(w, h);
    out.getContext('2d')!.drawImage(source, 0, 0, w, h);
    return out;
  }

  const scale = previewScale(w);
  const x = bounds.x * w;
  const y = bounds.y * h;
  const bw = bounds.w * w;
  const bh = bounds.h * h;
  const strokeW = Math.max(1, lineWidth * scale);
  const glow = glowRadius * scale;

  const overlay = createOffscreen(w, h);
  const ctx = overlay.getContext('2d')!;
  ctx.strokeStyle = `rgba(${color[0]},${color[1]},${color[2]},${intensity})`;
  ctx.lineWidth = strokeW;
  ctx.beginPath();
  ctx.ellipse(x + bw / 2, y + bh / 2, bw / 2, bh / 2, 0, 0, Math.PI * 2);
  ctx.stroke();

  ctx.filter = `blur(${Math.max(1, glow / 2)}px)`;
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
