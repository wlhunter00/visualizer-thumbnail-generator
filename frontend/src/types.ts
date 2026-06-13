// ============================================================================
// Effect Toggle Types
// ============================================================================

export type TriggerSource = 'beats' | 'full' | 'low' | 'medium' | 'high' | 'onsets';

export interface TriggerSourceOption {
  value: TriggerSource;
  label: string;
  description: string;
}

export const TRIGGER_SOURCE_OPTIONS: TriggerSourceOption[] = [
  { value: 'beats', label: 'Beats', description: 'Synced to kick, snare, and tempo' },
  { value: 'full', label: 'dB', description: 'Overall loudness' },
  { value: 'low', label: 'Low freq', description: 'Below 250 Hz — sub, kick, bass' },
  { value: 'medium', label: 'Mid freq', description: '250 Hz–3500 Hz — vocals, snare, guitars' },
  { value: 'high', label: 'High freq', description: 'Above 3500 Hz — cymbals, hi-hats, air' },
];

export const GLITCH_TRIGGER_SOURCE_OPTIONS: TriggerSourceOption[] = [
  { value: 'onsets', label: 'Onsets', description: 'Transients and sharp hits' },
  ...TRIGGER_SOURCE_OPTIONS,
];

export interface EffectToggle {
  enabled: boolean;
  intensity: number; // 0-1
  trigger_source?: TriggerSource;
  radius?: number; // 0-1, focus area size (background_dim only)
}

export interface EffectToggles {
  // Element effects
  element_glow: EffectToggle;
  element_scale: EffectToggle;
  
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
  element_glow: { enabled: true, intensity: 0.5, trigger_source: 'beats' },
  element_scale: { enabled: true, intensity: 0.3, trigger_source: 'beats' },
  particle_burst: { enabled: true, intensity: 0.5, trigger_source: 'beats' },
  energy_trails: { enabled: false, intensity: 0.4, trigger_source: 'beats' },
  light_flares: { enabled: false, intensity: 0.3, trigger_source: 'beats' },
  glitch: { enabled: false, intensity: 0.3, trigger_source: 'onsets' },
  ripple_wave: { enabled: false, intensity: 0.4, trigger_source: 'beats' },
  film_grain: { enabled: false, intensity: 0.2, trigger_source: 'beats' },
  strobe_flash: { enabled: false, intensity: 0.3, trigger_source: 'beats' },
  vignette_pulse: { enabled: true, intensity: 0.4, trigger_source: 'beats' },
  background_dim: { enabled: false, intensity: 0.3, radius: 0.5, trigger_source: 'beats' },
};

export interface SavedEffectPreset {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  effect_toggles: EffectToggles;
}

// Effect metadata for UI
export interface EffectMeta {
  key: keyof EffectToggles;
  name: string;
  description: string;
  category: 'element' | 'particle' | 'style' | 'background';
  supportsTriggerSource?: boolean;
  supportsRadius?: boolean;
}

export const EFFECT_METADATA: EffectMeta[] = [
  // Element effects
  { key: 'element_glow', name: 'Glow Pulse', description: 'Subject emits pulsating light', category: 'element', supportsTriggerSource: true },
  { key: 'element_scale', name: 'Scale Pulse', description: 'Subject grows/shrinks on beats', category: 'element', supportsTriggerSource: true },
  
  // Particle effects
  { key: 'particle_burst', name: 'Particle Burst', description: 'Particles explode on beats', category: 'particle', supportsTriggerSource: true },
  { key: 'energy_trails', name: 'Energy Trails', description: 'Glowing lines orbit subject', category: 'particle' },
  { key: 'light_flares', name: 'Light Flares', description: 'Lens flare from bright spots', category: 'particle', supportsTriggerSource: true },
  
  // Style effects
  { key: 'glitch', name: 'Glitch', description: 'RGB split and distortion', category: 'style', supportsTriggerSource: true },
  { key: 'ripple_wave', name: 'Ripple Wave', description: 'Distortion waves from center', category: 'style', supportsTriggerSource: true },
  { key: 'film_grain', name: 'Film Grain', description: 'VHS/retro texture', category: 'style' },
  { key: 'strobe_flash', name: 'Strobe Flash', description: 'Brief flashes on strong beats', category: 'style', supportsTriggerSource: true },
  { key: 'vignette_pulse', name: 'Vignette Pulse', description: 'Dark edges pulse with rhythm', category: 'style', supportsTriggerSource: true },
  
  // Background
  { key: 'background_dim', name: 'Background Dim', description: 'Darken background for contrast', category: 'background', supportsRadius: true },
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

export type EnergyEnvelope = [number, number][];

export interface AudioFeatures extends AudioMetrics {
  duration: number;
  beat_count: number;
  beat_times: number[];
  beat_strengths: number[];
  onset_times: number[];
  onset_strengths: number[];
  energy_envelope: EnergyEnvelope;
  low_freq_energy: EnergyEnvelope;
  mid_freq_energy: EnergyEnvelope;
  high_freq_energy: EnergyEnvelope;
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

export interface ExportFile {
  aspect_ratio: string;
  filename: string;
}

export interface GenerationStatus {
  status: 'idle' | 'rendering' | 'complete' | 'error' | 'exporting' | 'export_complete';
  progress: number;
  output_path: string | null;
  playbook: Playbook | null;
  export_current_ratio?: string;
  export_total?: number;
  export_completed?: number;
  export_files?: ExportFile[];
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
  // Legacy fields used by BrandPlaybook
  mood?: string;
  genre_fit?: string[];
  attributes?: {
    motion: string;
    reactivity: string;
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
  resolution_scale?: number; // Multiplier for output resolution
  
  // Legacy (for backwards compatibility)
  motion_intensity?: number;
  beat_reactivity?: number;
  energy_level?: number;
}

export type Step = 1 | 2 | 3;

export const ASPECT_RATIOS = [
  { value: '9:16', label: 'Vertical (9:16)', description: 'TikTok, Reels, Shorts' },
  { value: '1:1', label: 'Square (1:1)', description: 'Instagram Feed' },
  { value: '16:9', label: 'Horizontal (16:9)', description: 'YouTube' },
  { value: '4:5', label: 'Portrait (4:5)', description: 'Instagram/Facebook' },
] as const;

// ============================================================================
// Render Resolution Options
// ============================================================================

export interface RenderResolution {
  value: string;
  label: string;
  description: string;
  scale: number; // Multiplier for base dimensions
}

export const RENDER_RESOLUTIONS: RenderResolution[] = [
  { value: '720p', label: '720p', description: 'Fast render, small file', scale: 0.67 },
  { value: '1080p', label: '1080p', description: 'Standard HD quality', scale: 1.0 },
  { value: '1440p', label: '1440p (2K)', description: 'High quality', scale: 1.33 },
  { value: '4k', label: '4K', description: 'Maximum quality', scale: 2.0 },
];

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
