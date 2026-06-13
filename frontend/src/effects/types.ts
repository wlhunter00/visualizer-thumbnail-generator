import type { ImageAnalysis } from '../types';
import type { RGB } from './colorUtils';

export interface SubjectBounds {
  x: number;
  y: number;
  w: number;
  h: number;
  center_x: number;
  center_y: number;
}

export interface ImageContext {
  bounds: SubjectBounds;
  glow_points: { x: number; y: number; intensity: number }[];
  colors: string[];
  mood: string;
}

export interface ElementGlowParams {
  enabled: boolean;
  intensity: number;
  color: RGB;
  radius: number;
  pulse_triggers: [number, number][];
}

export interface ElementScaleParams {
  enabled: boolean;
  intensity: number;
  base_scale: number;
  max_scale: number;
  triggers: [number, number][];
}

export interface ParticleBurstParams {
  enabled: boolean;
  intensity: number;
  particle_count: number;
  colors: RGB[];
  size_range: [number, number];
  speed: number;
  lifetime: number;
  triggers: [number, number][];
  bounds_x: number;
  bounds_y: number;
  bounds_w: number;
  bounds_h: number;
}

export interface EnergyTrailsParams {
  enabled: boolean;
  intensity: number;
  trail_count: number;
  colors: RGB[];
  width: number;
  speed: number;
  bounds_x: number;
  bounds_y: number;
  bounds_w: number;
  bounds_h: number;
}

export interface LightFlaresParams {
  enabled: boolean;
  intensity: number;
  flare_points: [number, number][];
  colors: RGB[];
  size: number;
  triggers: [number, number][];
}

export interface GlitchParams {
  enabled: boolean;
  intensity: number;
  chromatic_aberration: number;
  rgb_split: number;
  scan_lines: boolean;
  scan_line_opacity: number;
  slice_displacement: boolean;
  triggers: [number, number, number][];
}

export interface RippleWaveParams {
  enabled: boolean;
  intensity: number;
  bounds_x: number;
  bounds_y: number;
  bounds_w: number;
  bounds_h: number;
  wavelength: number;
  amplitude: number;
  speed: number;
  triggers: [number, number][];
}

export interface FilmGrainParams {
  enabled: boolean;
  intensity: number;
  grain_size: number;
  color_variation: number;
}

export interface StrobeFlashParams {
  enabled: boolean;
  intensity: number;
  flash_duration: number;
  color: RGB;
  triggers: number[];
}

export interface VignettePulseParams {
  enabled: boolean;
  intensity: number;
  base_strength: number;
  pulse_strength: number;
  triggers: [number, number][];
}

export interface BackgroundDimParams {
  enabled: boolean;
  intensity: number;
  dim_amount: number;
  blur_amount: number;
  focus_radius: number;
}

export interface EffectParameters {
  duration: number;
  fps: number;
  subject_bounds: SubjectBounds;
  element_glow: ElementGlowParams;
  element_scale: ElementScaleParams;
  particle_burst: ParticleBurstParams;
  energy_trails: EnergyTrailsParams;
  light_flares: LightFlaresParams;
  glitch: GlitchParams;
  ripple_wave: RippleWaveParams;
  film_grain: FilmGrainParams;
  strobe_flash: StrobeFlashParams;
  vignette_pulse: VignettePulseParams;
  background_dim: BackgroundDimParams;
}

export function imageContextFromAnalysis(analysis: ImageAnalysis | null): ImageContext {
  if (!analysis) {
    return {
      bounds: { x: 0.25, y: 0.25, w: 0.5, h: 0.5, center_x: 0.5, center_y: 0.5 },
      glow_points: [],
      colors: ['#FFFFFF', '#FFD700', '#FF6B35'],
      mood: 'neutral',
    };
  }
  const b = analysis.bounds;
  return {
    bounds: {
      x: b.x,
      y: b.y,
      w: b.w,
      h: b.h,
      center_x: b.x + b.w / 2,
      center_y: b.y + b.h / 2,
    },
    glow_points: analysis.glow_points,
    colors: analysis.colors.length ? analysis.colors : ['#FFFFFF', '#FFD700', '#FF6B35'],
    mood: analysis.mood,
  };
}

export type EffectValues = Record<string, unknown>;
