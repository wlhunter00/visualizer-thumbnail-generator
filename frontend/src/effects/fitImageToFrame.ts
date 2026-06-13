/** Crop-to-fill fit matching backend fit_image_to_frame(). */
export function fitImageToFrame(
  imgWidth: number,
  imgHeight: number,
  frameWidth: number,
  frameHeight: number
): { sx: number; sy: number; sw: number; sh: number; dx: number; dy: number; dw: number; dh: number } {
  const scale = Math.max(frameWidth / imgWidth, frameHeight / imgHeight);
  const drawW = imgWidth * scale;
  const drawH = imgHeight * scale;
  const dx = (frameWidth - drawW) / 2;
  const dy = (frameHeight - drawH) / 2;

  return {
    sx: 0,
    sy: 0,
    sw: imgWidth,
    sh: imgHeight,
    dx,
    dy,
    dw: drawW,
    dh: drawH,
  };
}

export const PREVIEW_DIMENSIONS: Record<string, [number, number]> = {
  '9:16': [540, 960],
  '1:1': [540, 540],
  '16:9': [960, 540],
  '4:5': [540, 675],
};

export function getPreviewDimensions(aspectRatio: string): [number, number] {
  return PREVIEW_DIMENSIONS[aspectRatio] ?? PREVIEW_DIMENSIONS['9:16'];
}
