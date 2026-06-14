export const PREVIEW_REFERENCE_WIDTH = 540;

export function previewScale(width: number): number {
  return width / PREVIEW_REFERENCE_WIDTH;
}

export function createOffscreen(w: number, h: number): HTMLCanvasElement {
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  return canvas;
}

/** Draw source onto dest using destination-over compositing (PIL alpha_composite equivalent). */
export function alphaComposite(
  destCtx: CanvasRenderingContext2D,
  source: HTMLCanvasElement,
  w: number,
  h: number,
) {
  destCtx.globalCompositeOperation = 'source-over';
  destCtx.drawImage(source, 0, 0, w, h);
}

export function canvasFromImageData(
  imageData: ImageData,
  w: number,
  h: number,
): HTMLCanvasElement {
  const canvas = createOffscreen(w, h);
  canvas.getContext('2d')!.putImageData(imageData, 0, 0);
  return canvas;
}

export function getCanvasImageData(
  source: HTMLCanvasElement,
  w: number,
  h: number,
): ImageData {
  const ctx = source.getContext('2d')!;
  return ctx.getImageData(0, 0, w, h);
}
