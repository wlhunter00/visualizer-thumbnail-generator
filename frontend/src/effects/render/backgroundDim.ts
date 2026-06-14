import type { SubjectBounds } from '../types';
import { createOffscreen, previewScale } from './compositor';

/** Precompute background-dim base (matches backend apply_background_dim). */
export function precomputeBackgroundDim(
  baseImage: HTMLCanvasElement,
  bounds: SubjectBounds,
  dimAmount: number,
  blurAmount: number,
  focusRadius: number,
  w: number,
  h: number,
): HTMLCanvasElement {
  const result = createOffscreen(w, h);
  const ctx = result.getContext('2d')!;

  if (dimAmount < 0.01 && blurAmount < 0.1) {
    ctx.drawImage(baseImage, 0, 0, w, h);
    return result;
  }

  const bg = createOffscreen(w, h);
  const bgCtx = bg.getContext('2d')!;
  const scaledBlur = blurAmount * previewScale(w);
  const filters: string[] = [];
  if (blurAmount > 0.1) filters.push(`blur(${scaledBlur}px)`);
  if (dimAmount > 0.01) filters.push(`brightness(${1 - dimAmount})`);
  bgCtx.filter = filters.join(' ');
  bgCtx.drawImage(baseImage, 0, 0, w, h);
  bgCtx.filter = 'none';

  const x = Math.floor(bounds.x * w);
  const y = Math.floor(bounds.y * h);
  const bw = Math.floor(bounds.w * w);
  const bh = Math.floor(bounds.h * h);
  const minDim = Math.min(bw, bh);
  const maxDim = Math.max(bw, bh);
  const padding = Math.floor(minDim * (0.05 + focusRadius * 0.45));
  const expand = Math.floor(maxDim * focusRadius * 0.3);
  const ex = x - padding - expand;
  const ey = y - padding - expand;
  const ew = bw + 2 * (padding + expand);
  const eh = bh + 2 * (padding + expand);
  const blurMask = Math.max(1, padding * (0.8 + focusRadius * 0.4));

  const mask = createOffscreen(w, h);
  const mctx = mask.getContext('2d')!;
  mctx.fillStyle = '#000';
  mctx.fillRect(0, 0, w, h);
  mctx.fillStyle = '#fff';
  mctx.beginPath();
  mctx.ellipse(ex + ew / 2, ey + eh / 2, ew / 2, eh / 2, 0, 0, Math.PI * 2);
  mctx.fill();
  mctx.filter = `blur(${blurMask}px)`;
  mctx.globalCompositeOperation = 'source-over';
  const maskCopy = createOffscreen(w, h);
  maskCopy.getContext('2d')!.drawImage(mask, 0, 0);
  mctx.clearRect(0, 0, w, h);
  mctx.drawImage(maskCopy, 0, 0);
  mctx.filter = 'none';

  const maskData = mctx.getImageData(0, 0, w, h);
  const baseData = baseImage.getContext('2d')!.getImageData(0, 0, w, h);
  const bgData = bgCtx.getImageData(0, 0, w, h);
  const out = ctx.createImageData(w, h);

  for (let i = 0; i < maskData.data.length; i += 4) {
    const m = maskData.data[i] / 255;
    out.data[i] = baseData.data[i] * m + bgData.data[i] * (1 - m);
    out.data[i + 1] = baseData.data[i + 1] * m + bgData.data[i + 1] * (1 - m);
    out.data[i + 2] = baseData.data[i + 2] * m + bgData.data[i + 2] * (1 - m);
    out.data[i + 3] = 255;
  }
  ctx.putImageData(out, 0, 0);
  return result;
}
