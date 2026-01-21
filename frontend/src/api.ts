import { EffectToggles, ImageAnalysis, AudioMetrics, GenerateSettings } from './types';

const API_BASE = '/api';

// ============================================================================
// Session Management
// ============================================================================

export async function createSession(): Promise<{ session_id: string }> {
  const res = await fetch(`${API_BASE}/session/create`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to create session');
  return res.json();
}

// ============================================================================
// Upload Endpoints
// ============================================================================

export async function uploadImage(sessionId: string, file: File): Promise<{ path: string }> {
  const formData = new FormData();
  formData.append('file', file);
  
  const res = await fetch(`${API_BASE}/upload/image/${sessionId}`, {
    method: 'POST',
    body: formData,
  });
  
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to upload image');
  }
  return res.json();
}

export async function uploadAudio(sessionId: string, file: File): Promise<{ path: string; duration: number }> {
  const formData = new FormData();
  formData.append('file', file);
  
  const res = await fetch(`${API_BASE}/upload/audio/${sessionId}`, {
    method: 'POST',
    body: formData,
  });
  
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to upload audio');
  }
  return res.json();
}

// ============================================================================
// Audio Endpoints
// ============================================================================

export async function getWaveform(sessionId: string): Promise<{ waveform: [number, number][]; duration: number }> {
  const res = await fetch(`${API_BASE}/audio/waveform/${sessionId}`);
  if (!res.ok) throw new Error('Failed to get waveform');
  return res.json();
}

export async function getAudioAnalysis(sessionId: string): Promise<AudioMetrics & { 
  tempo: number; 
  duration: number; 
  beat_count: number;
  beat_times: number[];
  beat_strengths: number[];
}> {
  const res = await fetch(`${API_BASE}/audio/analysis/${sessionId}`);
  if (!res.ok) throw new Error('Failed to get audio analysis');
  return res.json();
}

// ============================================================================
// NEW: Image Analysis Endpoints
// ============================================================================

export async function analyzeImage(sessionId: string): Promise<{ 
  message: string; 
  analysis: ImageAnalysis 
}> {
  const res = await fetch(`${API_BASE}/analyze-image/${sessionId}`, {
    method: 'POST',
  });
  
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to analyze image');
  }
  return res.json();
}

export async function generateParticles(sessionId: string): Promise<{ 
  message: string; 
  path: string 
}> {
  const res = await fetch(`${API_BASE}/generate-particles/${sessionId}`, {
    method: 'POST',
  });
  
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to generate particles');
  }
  return res.json();
}

export async function autoSuggest(sessionId: string): Promise<{
  message: string;
  effect_toggles: EffectToggles;
  audio_metrics: AudioMetrics;
}> {
  const res = await fetch(`${API_BASE}/auto-suggest/${sessionId}`, {
    method: 'POST',
  });
  
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to get auto-suggestions');
  }
  return res.json();
}

export async function updateEffectToggles(
  sessionId: string, 
  toggles: EffectToggles
): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/effect-toggles/${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(toggles),
  });
  
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to update effect toggles');
  }
  return res.json();
}

// ============================================================================
// Generation Endpoints
// ============================================================================

export async function generateVideo(
  sessionId: string,
  settings: GenerateSettings
): Promise<void> {
  const res = await fetch(`${API_BASE}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      start_time: settings.start_time,
      end_time: settings.end_time,
      aspect_ratio: settings.aspect_ratio,
      effect_toggles: settings.effect_toggles,
      // Legacy support
      motion_intensity: settings.motion_intensity,
      beat_reactivity: settings.beat_reactivity,
      energy_level: settings.energy_level,
    }),
  });
  
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to start generation');
  }
}

export async function getGenerationStatus(sessionId: string): Promise<{
  status: 'idle' | 'rendering' | 'complete' | 'error' | 'exporting' | 'export_complete';
  progress: number;
  output_path: string | null;
  playbook: any | null;
}> {
  const res = await fetch(`${API_BASE}/generate/status/${sessionId}`);
  if (!res.ok) throw new Error('Failed to get status');
  return res.json();
}

// ============================================================================
// Export Endpoints
// ============================================================================

export async function exportVideo(sessionId: string): Promise<{ download_url: string }> {
  const res = await fetch(`${API_BASE}/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  });
  
  if (!res.ok) throw new Error('Failed to export');
  return res.json();
}

// ============================================================================
// URL Helpers
// ============================================================================

export function getPreviewUrl(sessionId: string): string {
  return `${API_BASE}/outputs/${sessionId}/preview.mp4`;
}

export function getAudioStreamUrl(sessionId: string): string {
  return `${API_BASE}/audio/stream/${sessionId}`;
}

export function getDownloadUrl(sessionId: string): string {
  return `${API_BASE}/download/${sessionId}`;
}
