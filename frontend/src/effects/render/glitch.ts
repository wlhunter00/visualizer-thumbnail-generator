import type { RGB } from '../colorUtils';
import { seededSliceOffset } from '../glitchUtils';
import { createOffscreen, previewScale } from './compositor';

export function applyChromaticGlitch(
  dest: HTMLCanvasElement,
  overlaySource: HTMLCanvasElement,
  chromatic: number,
  rgbSplit: number,
  glitchIntensity: number,
  scanLines: boolean,
  scanOpacity: number,
  w: number,
  h: number,
): HTMLCanvasElement {
  const scale = previewScale(w);
  const rgbOffset = Math.max(Math.round(rgbSplit * scale), Math.round(2 * scale));
  const chromaticOffset = Math.max(Math.round(chromatic * scale), Math.round(2 * scale));

  const result = createOffscreen(w, h);
  const ctx = result.getContext('2d')!;
  ctx.drawImage(dest, 0, 0, w, h);

  if (rgbOffset > 0 || chromaticOffset > 0) {
    const strength = Math.min(1.0, 0.4 + glitchIntensity * 0.55);
    ctx.save();
    ctx.globalCompositeOperation = 'screen';
    ctx.globalAlpha = strength;
    ctx.drawImage(overlaySource, rgbOffset, 0);
    ctx.globalCompositeOperation = 'multiply';
    ctx.globalAlpha = strength;
    ctx.drawImage(overlaySource, -chromaticOffset, 0);
    ctx.restore();
  }

  if (scanLines && scanOpacity > 0.01) {
    const lineStep = Math.max(2, Math.round(4 * scale));
    const lineHeight = Math.max(1, Math.round(2 * scale));
    ctx.fillStyle = `rgba(0,0,0,${scanOpacity})`;
    for (let y = 0; y < h; y += lineStep) {
      ctx.fillRect(0, y, w, lineHeight);
    }
  }

  return result;
}

export function applySliceGlitch(
  source: HTMLCanvasElement,
  offsetPx: number,
  seed: number,
  w: number,
  h: number,
): HTMLCanvasElement {
  if (offsetPx <= 0) {
    const out = createOffscreen(w, h);
    out.getContext('2d')!.drawImage(source, 0, 0, w, h);
    return out;
  }

  const result = createOffscreen(w, h);
  const ctx = result.getContext('2d')!;
  ctx.drawImage(source, 0, 0, w, h);
  const sliceH = Math.max(1, Math.floor(h / 8));

  for (let i = 0; i < 8; i += 2) {
    const displacement = Math.round(seededSliceOffset(seed, i, offsetPx));
    ctx.drawImage(source, 0, i * sliceH, w, sliceH, displacement, i * sliceH, w, sliceH);
  }
  return result;
}

export function applyStrobe(
  source: HTMLCanvasElement,
  intensity: number,
  color: RGB,
  w: number,
  h: number,
): HTMLCanvasElement {
  if (intensity < 0.01) {
    const out = createOffscreen(w, h);
    out.getContext('2d')!.drawImage(source, 0, 0, w, h);
    return out;
  }

  const result = createOffscreen(w, h);
  const ctx = result.getContext('2d')!;
  ctx.drawImage(source, 0, 0, w, h);
  ctx.fillStyle = `rgba(${color[0]},${color[1]},${color[2]},${intensity * 0.7})`;
  ctx.fillRect(0, 0, w, h);
  return result;
}
