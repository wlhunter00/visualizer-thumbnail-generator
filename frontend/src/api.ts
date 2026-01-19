const API_BASE = '/api';

export async function createSession(): Promise<{ session_id: string }> {
  const res = await fetch(`${API_BASE}/session/create`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to create session');
  return res.json();
}

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

export async function getWaveform(sessionId: string): Promise<{ waveform: [number, number][]; duration: number }> {
  const res = await fetch(`${API_BASE}/audio/waveform/${sessionId}`);
  if (!res.ok) throw new Error('Failed to get waveform');
  return res.json();
}

export async function generateVideo(
  sessionId: string,
  settings: {
    start_time: number;
    end_time: number;
    aspect_ratio: string;
    motion_intensity: number;
    beat_reactivity: number;
    energy_level: number;
  }
): Promise<void> {
  const res = await fetch(`${API_BASE}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      ...settings,
    }),
  });
  
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to start generation');
  }
}

export async function getGenerationStatus(sessionId: string): Promise<{
  status: 'idle' | 'rendering' | 'complete' | 'error';
  progress: number;
  output_path: string | null;
  playbook: any | null;
}> {
  const res = await fetch(`${API_BASE}/generate/status/${sessionId}`);
  if (!res.ok) throw new Error('Failed to get status');
  return res.json();
}

export async function exportVideo(sessionId: string): Promise<{ download_url: string }> {
  const res = await fetch(`${API_BASE}/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  });
  
  if (!res.ok) throw new Error('Failed to export');
  return res.json();
}

export function getPreviewUrl(sessionId: string): string {
  return `${API_BASE}/outputs/${sessionId}/preview.mp4`;
}

export function getAudioStreamUrl(sessionId: string): string {
  return `${API_BASE}/audio/stream/${sessionId}`;
}

export function getDownloadUrl(sessionId: string): string {
  return `${API_BASE}/download/${sessionId}`;
}

