import type { SubjectBounds } from '../types';
import { createOffscreen } from './compositor';

/** Masked subject scale (matches backend apply_element_scale). */
export function applyElementScale(
  source: HTMLCanvasElement,
  bounds: SubjectBounds,
  scale: number,
  w: number,
  h: number,
): HTMLCanvasElement {
  if (Math.abs(scale - 1.0) < 0.001) {
    const out = createOffscreen(w, h);
    out.getContext('2d')!.drawImage(source, 0, 0, w, h);
    return out;
  }

  let bx = Math.floor(bounds.x * w);
  let by = Math.floor(bounds.y * h);
  let bw = Math.floor(bounds.w * w);
  let bh = Math.floor(bounds.h * h);
  const padding = Math.floor(Math.min(bw, bh) * 0.15);
  bx = Math.max(0, bx - padding);
  by = Math.max(0, by - padding);
  bw = Math.min(w - bx, bw + padding * 2);
  bh = Math.min(h - by, bh + padding * 2);

  const newW = Math.floor(bw * scale);
  const newH = Math.floor(bh * scale);
  if (newW <= 0 || newH <= 0) {
    const out = createOffscreen(w, h);
    out.getContext('2d')!.drawImage(source, 0, 0, w, h);
    return out;
  }

  const mask = createOffscreen(bw, bh);
  const mctx = mask.getContext('2d')!;
  mctx.fillStyle = '#fff';
  mctx.beginPath();
  mctx.ellipse(bw / 2, bh / 2, bw / 2, bh / 2, 0, 0, Math.PI * 2);
  mctx.fill();
  const feather = Math.max(5, Math.floor(Math.min(bw, bh) * 0.1));
  mctx.filter = `blur(${feather}px)`;
  const maskBlur = createOffscreen(bw, bh);
  maskBlur.getContext('2d')!.drawImage(mask, 0, 0);
  mctx.clearRect(0, 0, bw, bh);
  mctx.drawImage(maskBlur, 0, 0);
  mctx.filter = 'none';

  const element = createOffscreen(bw, bh);
  const ectx = element.getContext('2d')!;
  ectx.drawImage(source, -bx, -by, w, h);
  ectx.globalCompositeOperation = 'destination-in';
  ectx.drawImage(mask, 0, 0);
  ectx.globalCompositeOperation = 'source-over';

  const scaled = createOffscreen(newW, newH);
  scaled.getContext('2d')!.drawImage(element, 0, 0, newW, newH);

  const result = createOffscreen(w, h);
  const rctx = result.getContext('2d')!;
  rctx.drawImage(source, 0, 0, w, h);
  const centerX = bx + bw / 2;
  const centerY = by + bh / 2;
  rctx.drawImage(scaled, centerX - newW / 2, centerY - newH / 2);
  return result;
}
