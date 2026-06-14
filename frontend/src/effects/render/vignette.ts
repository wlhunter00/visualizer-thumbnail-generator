/** Precompute squared normalized distance from center (matches backend build_vignette_dist_sq). */
export function buildVignetteDistSq(w: number, h: number): Float32Array {
  const cx = Math.floor(w / 2);
  const cy = Math.floor(h / 2);
  const maxDist = Math.sqrt(cx * cx + cy * cy);
  const distSq = new Float32Array(w * h);

  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const dist = Math.sqrt((x - cx) ** 2 + (y - cy) ** 2);
      const normalized = dist / maxDist;
      distSq[y * w + x] = normalized * normalized;
    }
  }
  return distSq;
}

/** Darken edges using precomputed distance field (matches backend apply_vignette). */
export function applyVignette(
  source: HTMLCanvasElement,
  strength: number,
  distSq: Float32Array,
  w: number,
  h: number,
): HTMLCanvasElement {
  if (strength < 0.01) {
    const out = document.createElement('canvas');
    out.width = w;
    out.height = h;
    out.getContext('2d')!.drawImage(source, 0, 0, w, h);
    return out;
  }

  const srcData = source.getContext('2d')!.getImageData(0, 0, w, h);
  const outData = new ImageData(w, h);

  for (let i = 0; i < distSq.length; i++) {
    const vignette = Math.max(0, Math.min(1, 1 - distSq[i] * strength));
    const pi = i * 4;
    const brighten = 0.3 + vignette * 0.7;
    outData.data[pi] = Math.min(255, srcData.data[pi] * brighten);
    outData.data[pi + 1] = Math.min(255, srcData.data[pi + 1] * brighten);
    outData.data[pi + 2] = Math.min(255, srcData.data[pi + 2] * brighten);
    outData.data[pi + 3] = srcData.data[pi + 3];
  }

  const result = document.createElement('canvas');
  result.width = w;
  result.height = h;
  result.getContext('2d')!.putImageData(outData, 0, 0);
  return result;
}
