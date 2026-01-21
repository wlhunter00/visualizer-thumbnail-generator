// ============================================================================
// Effect Toggle Types
// ============================================================================

export interface EffectToggle {
  enabled: boolean;
  intensity: number; // 0-1
}

export interface EffectToggles {
  // Element effects
  element_glow: EffectToggle;
  element_scale: EffectToggle;
  neon_outline: EffectToggle;
  echo_trail: EffectToggle;
  
  // Particle effects
  particle_burst: EffectToggle;
  energy_trails: EffectToggle;
  light_flares: EffectToggle;
  
  // Style effects
  glitch: EffectToggle;
  ripple_wave: EffectToggle;
  film_grain: EffectToggle;
  strobe_flash: EffectToggle;
  vignette_pulse: EffectToggle;
  
  // Background
  background_dim: EffectToggle;
}

export const DEFAULT_EFFECT_TOGGLES: EffectToggles = {
  element_glow: { enabled: true, intensity: 0.5 },
  element_scale: { enabled: true, intensity: 0.3 },
  neon_outline: { enabled: false, intensity: 0.5 },
  echo_trail: { enabled: false, intensity: 0.4 },
  particle_burst: { enabled: true, intensity: 0.5 },
  energy_trails: { enabled: false, intensity: 0.4 },
  light_flares: { enabled: false, intensity: 0.3 },
  glitch: { enabled: false, intensity: 0.3 },
  ripple_wave: { enabled: false, intensity: 0.4 },
  film_grain: { enabled: false, intensity: 0.2 },
  strobe_flash: { enabled: false, intensity: 0.3 },
  vignette_pulse: { enabled: true, intensity: 0.4 },
  background_dim: { enabled: true, intensity: 0.3 },
};

// Effect metadata for UI
export interface EffectMeta {
  key: keyof EffectToggles;
  name: string;
  description: string;
  category: 'element' | 'particle' | 'style' | 'background';
}

export const EFFECT_METADATA: EffectMeta[] = [
  // Element effects
  { key: 'element_glow', name: 'Glow Pulse', description: 'Subject emits pulsating light', category: 'element' },
  { key: 'element_scale', name: 'Scale Pulse', description: 'Subject grows/shrinks on beats', category: 'element' },
  { key: 'neon_outline', name: 'Neon Outline', description: 'Glowing edge around subject', category: 'element' },
  { key: 'echo_trail', name: 'Echo Trail', description: 'Ghostly afterimage effect', category: 'element' },
  
  // Particle effects
  { key: 'particle_burst', name: 'Particle Burst', description: 'Particles explode on beats', category: 'particle' },
  { key: 'energy_trails', name: 'Energy Trails', description: 'Glowing lines orbit subject', category: 'particle' },
  { key: 'light_flares', name: 'Light Flares', description: 'Lens flare from bright spots', category: 'particle' },
  
  // Style effects
  { key: 'glitch', name: 'Glitch', description: 'RGB split and distortion', category: 'style' },
  { key: 'ripple_wave', name: 'Ripple Wave', description: 'Distortion waves from center', category: 'style' },
  { key: 'film_grain', name: 'Film Grain', description: 'VHS/retro texture', category: 'style' },
  { key: 'strobe_flash', name: 'Strobe Flash', description: 'Brief flashes on strong beats', category: 'style' },
  { key: 'vignette_pulse', name: 'Vignette Pulse', description: 'Dark edges pulse with rhythm', category: 'style' },
  
  // Background
  { key: 'background_dim', name: 'Background Dim', description: 'Darken background for contrast', category: 'background' },
];

// ============================================================================
// Image Analysis Types
// ============================================================================

export interface SubjectBounds {
  x: number; // 0-1
  y: number; // 0-1
  w: number; // 0-1
  h: number; // 0-1
}

export interface GlowPoint {
  x: number;
  y: number;
  intensity: number;
}

export interface ImageAnalysis {
  subject: string;
  subject_description: string;
  bounds: SubjectBounds;
  glow_points: GlowPoint[];
  colors: string[]; // Hex codes
  mood: string;
  suggested_particle_style: string;
}

// ============================================================================
// Audio Analysis Types
// ============================================================================

export interface AudioMetrics {
  tempo: number;
  onset_density: number;
  average_bass: number;
  average_mid: number;
  average_high: number;
  dynamic_range: number;
  beat_strength_variance: number;
  average_energy: number;
}

// ============================================================================
// Session Types
// ============================================================================

export interface SessionData {
  session_id: string;
  image_path: string | null;
  audio_path: string | null;
  audio_duration: number | null;
  start_time: number;
  end_time: number | null;
  aspect_ratio: string;
  
  // New: Image analysis
  image_analysis: ImageAnalysis | null;
  
  // New: Effect toggles
  effect_toggles: EffectToggles | null;
  
  // Legacy (deprecated)
  motion_intensity: number;
  beat_reactivity: number;
  energy_level: number;
  
  output_path: string | null;
  render_status: 'idle' | 'rendering' | 'complete' | 'error' | 'exporting' | 'export_complete';
  render_progress: number;
  playbook: Playbook | null;
}

export interface Playbook {
  summary: string;
  active_effects: string[];
  audio_info: {
    tempo: number;
    beat_count: number;
    onset_density: number;
    average_energy: number;
  };
  image_info: {
    subject: string | null;
    mood: string | null;
    colors: string[];
  };
}

// ============================================================================
// Request Types
// ============================================================================

export interface WaveformData {
  waveform: [number, number][];
  duration: number;
}

export interface GenerateSettings {
  start_time: number;
  end_time: number;
  aspect_ratio: string;
  effect_toggles?: EffectToggles;
  
  // Legacy (for backwards compatibility)
  motion_intensity?: number;
  beat_reactivity?: number;
  energy_level?: number;
}

export type Step = 1 | 2 | 3 | 4;

export const ASPECT_RATIOS = [
  { value: '9:16', label: 'Vertical (9:16)', description: 'TikTok, Reels, Shorts' },
  { value: '1:1', label: 'Square (1:1)', description: 'Instagram Feed' },
  { value: '16:9', label: 'Horizontal (16:9)', description: 'YouTube' },
  { value: '4:5', label: 'Portrait (4:5)', description: 'Instagram/Facebook' },
] as const;

// ============================================================================
// Effect Categories for UI Grouping
// ============================================================================

export const EFFECT_CATEGORIES = [
  {
    id: 'element',
    name: 'Element Effects',
    description: 'Effects applied to the detected subject',
    icon: '🎯',
  },
  {
    id: 'particle',
    name: 'Particles',
    description: 'Particle and trail effects',
    icon: '✨',
  },
  {
    id: 'style',
    name: 'Style',
    description: 'Visual style and post-processing',
    icon: '🎬',
  },
  {
    id: 'background',
    name: 'Background',
    description: 'Background treatment',
    icon: '🖼️',
  },
] as const;
