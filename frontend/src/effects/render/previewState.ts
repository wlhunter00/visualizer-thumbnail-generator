import type { EffectToggles } from '../../types';
import type { SubjectBounds } from '../types';
import { precomputeBackgroundDim } from './backgroundDim';
import { buildVignetteDistSq } from './vignette';

export interface PreviewRenderState {
  baseImage: HTMLCanvasElement;
  backgroundDimBase: HTMLCanvasElement | null;
  vignetteDistSq: Float32Array;
  bounds: SubjectBounds;
  w: number;
  h: number;
}

export function buildPreviewRenderState(
  baseImage: HTMLCanvasElement,
  bounds: SubjectBounds,
  toggles: EffectToggles,
  w: number,
  h: number,
): PreviewRenderState {
  const bgDim = toggles.background_dim;
  let backgroundDimBase: HTMLCanvasElement | null = null;

  if (bgDim.enabled) {
    const dimAmount = 0.2 + bgDim.intensity * 0.4;
    const blurAmount = 1 + bgDim.intensity * 4;
    const focusRadius = bgDim.radius ?? 0.5;
    backgroundDimBase = precomputeBackgroundDim(
      baseImage, bounds, dimAmount, blurAmount, focusRadius, w, h,
    );
  }

  return {
    baseImage,
    backgroundDimBase,
    vignetteDistSq: buildVignetteDistSq(w, h),
    bounds,
    w,
    h,
  };
}
