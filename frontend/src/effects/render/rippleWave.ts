import { canvasFromImageData, createOffscreen, getCanvasImageData, previewScale } from './compositor';

interface RippleWave {
  radius: number;
  amplitude: number;
  wavelength: number;
  bounds_x: number;
  bounds_y: number;
  bounds_w: number;
  bounds_h: number;
}

/** Pixel-remap ripple distortion (matches backend apply_ripple_wave). */
export function applyRippleWave(
  source: HTMLCanvasElement,
  ripples: RippleWave[],
  intensity: number,
  w: number,
  h: number,
): HTMLCanvasElement {
  if (!ripples.length || intensity < 0.01) {
    const out = createOffscreen(w, h);
    out.getContext('2d')!.drawImage(source, 0, 0, w, h);
    return out;
  }

  let current = source;
  for (const ripple of ripples) {
    current = remapRipple(current, ripple, intensity, w, h);
  }
  return current;
}

function remapRipple(
  source: HTMLCanvasElement,
  ripple: RippleWave,
  intensity: number,
  width: number,
  height: number,
): HTMLCanvasElement {
  const scale = previewScale(width);
  const centerX = (ripple.bounds_x + ripple.bounds_w / 2) * width;
  const centerY = (ripple.bounds_y + ripple.bounds_h / 2) * height;
  const radiusX = (ripple.bounds_w / 2) * width;
  const radiusY = (ripple.bounds_h / 2) * height;
  const rippleRadius = ripple.radius * scale;
  const amplitude = ripple.amplitude * intensity * scale;
  const wavelength = ripple.wavelength * scale;

  if (amplitude < 1) {
    const out = createOffscreen(width, height);
    out.getContext('2d')!.drawImage(source, 0, 0, width, height);
    return out;
  }

  const srcData = getCanvasImageData(source, width, height);
  const outData = new ImageData(width, height);
  const avgRadius = (radiusX + radiusY) / 2;

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const dx = (x - centerX) / Math.max(radiusX, 1);
      const dy = (y - centerY) / Math.max(radiusY, 1);
      const ellipseDist = Math.sqrt(dx * dx + dy * dy);
      const distFromEdge = (ellipseDist - 1.0) * avgRadius;
      const angle = Math.atan2(y - centerY, x - centerX);

      let displacement = 0;
      if (distFromEdge >= 0 && Math.abs(distFromEdge - rippleRadius) < wavelength * 2) {
        const wave = Math.sin((distFromEdge - rippleRadius) * 2 * Math.PI / wavelength);
        const gaussian = Math.exp(-(((distFromEdge - rippleRadius) / wavelength) ** 2));
        displacement = wave * amplitude * gaussian;
      }

      const srcX = Math.min(width - 1, Math.max(0, Math.round(x + Math.cos(angle) * displacement)));
      const srcY = Math.min(height - 1, Math.max(0, Math.round(y + Math.sin(angle) * displacement)));
      const si = (srcY * width + srcX) * 4;
      const di = (y * width + x) * 4;
      outData.data[di] = srcData.data[si];
      outData.data[di + 1] = srcData.data[si + 1];
      outData.data[di + 2] = srcData.data[si + 2];
      outData.data[di + 3] = srcData.data[si + 3];
    }
  }

  return canvasFromImageData(outData, width, height);
}
