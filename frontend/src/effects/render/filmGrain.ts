import { createOffscreen, previewScale } from './compositor';

/** Per-frame film grain with grain_size (matches backend apply_film_grain). */
export function applyFilmGrain(
  source: HTMLCanvasElement,
  intensity: number,
  grainSize: number,
  w: number,
  h: number,
): HTMLCanvasElement {
  if (intensity < 0.01) {
    const out = createOffscreen(w, h);
    out.getContext('2d')!.drawImage(source, 0, 0, w, h);
    return out;
  }

  const scale = previewScale(w);
  const block = Math.max(1, Math.floor(grainSize * scale));
  const smallW = Math.max(1, Math.floor(w / block));
  const smallH = Math.max(1, Math.floor(h / block));

  const noiseSmall = createOffscreen(smallW, smallH);
  const nctx = noiseSmall.getContext('2d')!;
  const imgData = nctx.createImageData(smallW, smallH);
  for (let i = 0; i < imgData.data.length; i += 4) {
    const v = Math.random() * 255;
    imgData.data[i] = v;
    imgData.data[i + 1] = v;
    imgData.data[i + 2] = v;
    imgData.data[i + 3] = 255;
  }
  nctx.putImageData(imgData, 0, 0);

  const noise = createOffscreen(w, h);
  const noiseCtx = noise.getContext('2d')!;
  noiseCtx.imageSmoothingEnabled = false;
  noiseCtx.drawImage(noiseSmall, 0, 0, w, h);

  const result = createOffscreen(w, h);
  const rctx = result.getContext('2d')!;
  rctx.drawImage(source, 0, 0, w, h);
  rctx.globalAlpha = intensity * 0.25;
  rctx.drawImage(noise, 0, 0);
  rctx.globalAlpha = 1;
  return result;
}
