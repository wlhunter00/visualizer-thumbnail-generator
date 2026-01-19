export interface SessionData {
  session_id: string;
  image_path: string | null;
  audio_path: string | null;
  audio_duration: number | null;
  start_time: number;
  end_time: number | null;
  aspect_ratio: string;
  motion_intensity: number;
  beat_reactivity: number;
  energy_level: number;
  output_path: string | null;
  render_status: 'idle' | 'rendering' | 'complete' | 'error';
  render_progress: number;
  playbook: Playbook | null;
}

export interface Playbook {
  summary: string;
  attributes: {
    motion: string;
    reactivity: string;
    energy: string;
    tempo: string;
  };
  active_effects: string[];
  genre_fit: string[];
  mood: string;
  settings_used: {
    motion_intensity: number;
    beat_reactivity: number;
    energy_level: number;
  };
}

export interface WaveformData {
  waveform: [number, number][];
  duration: number;
}

export interface GenerateSettings {
  start_time: number;
  end_time: number;
  aspect_ratio: string;
  motion_intensity: number;
  beat_reactivity: number;
  energy_level: number;
}

export type Step = 1 | 2 | 3 | 4;

export const ASPECT_RATIOS = [
  { value: '9:16', label: 'Vertical (9:16)', description: 'TikTok, Reels, Shorts' },
  { value: '1:1', label: 'Square (1:1)', description: 'Instagram Feed' },
  { value: '16:9', label: 'Horizontal (16:9)', description: 'YouTube' },
  { value: '4:5', label: 'Portrait (4:5)', description: 'Instagram/Facebook' },
] as const;

