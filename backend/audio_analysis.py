"""
Audio Analysis Module
Handles beat detection, energy envelope, onset detection, and frequency band analysis.
"""

import subprocess
import json
import numpy as np
import librosa
from dataclasses import dataclass
from typing import List, Tuple, Optional


# Cache for loaded audio to avoid reloading
_audio_cache: dict = {}


@dataclass
class AudioFeatures:
    """Container for all extracted audio features."""
    duration: float
    sample_rate: int
    tempo: float
    beat_times: List[float]  # Times in seconds when beats occur
    beat_strengths: List[float]  # Relative strength of each beat (0-1)
    onset_times: List[float]  # Times of musical onsets/transients
    onset_strengths: List[float]  # Strength of each onset
    energy_envelope: List[Tuple[float, float]]  # (time, energy) pairs
    bass_energy: List[Tuple[float, float]]  # Low frequency energy over time
    mid_energy: List[Tuple[float, float]]  # Mid frequency energy over time
    high_energy: List[Tuple[float, float]]  # High frequency energy over time
    
    # Computed metrics for AI interpretation (no BPM-based assumptions)
    onset_density: float = 0.0  # Onsets per second - indicates rhythmic activity
    average_bass: float = 0.0  # Average bass energy (0-1)
    average_mid: float = 0.0   # Average mid energy (0-1)
    average_high: float = 0.0  # Average high energy (0-1)
    dynamic_range: float = 0.0  # Difference between max and min energy
    beat_strength_variance: float = 0.0  # How much beat strengths vary
    average_energy: float = 0.0  # Overall average energy level


def analyze_audio(audio_path: str, start_time: float = 0.0, duration: float = None) -> AudioFeatures:
    """
    Analyze an audio file and extract beat-reactive features.
    
    Args:
        audio_path: Path to the audio file
        start_time: Start time in seconds for analysis region
        duration: Duration in seconds to analyze (None = full file)
    
    Returns:
        AudioFeatures object containing all extracted features
    """
    # Load audio file
    y, sr = librosa.load(audio_path, sr=22050, offset=start_time, duration=duration)
    actual_duration = len(y) / sr
    
    # Beat detection
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
    
    # Calculate beat strengths based on onset envelope at beat times
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_env_normalized = onset_env / (onset_env.max() + 1e-6)
    
    beat_strengths = []
    for frame in beat_frames:
        if frame < len(onset_env_normalized):
            beat_strengths.append(float(onset_env_normalized[frame]))
        else:
            beat_strengths.append(0.5)
    
    # Onset detection (musical transients)
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, onset_envelope=onset_env)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr).tolist()
    
    onset_strengths = []
    for frame in onset_frames:
        if frame < len(onset_env_normalized):
            onset_strengths.append(float(onset_env_normalized[frame]))
        else:
            onset_strengths.append(0.5)
    
    # Energy envelope (RMS energy over time)
    hop_length = 512
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    rms_normalized = rms / (rms.max() + 1e-6)
    rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
    energy_envelope = list(zip(rms_times.tolist(), rms_normalized.tolist()))
    
    # Frequency band analysis using mel spectrogram
    mel_spec = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, hop_length=hop_length)
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
    
    # Normalize mel spectrogram
    mel_spec_norm = (mel_spec_db - mel_spec_db.min()) / (mel_spec_db.max() - mel_spec_db.min() + 1e-6)
    
    # Split into frequency bands (bass: 0-300Hz, mid: 300-2000Hz, high: 2000Hz+)
    # Approximate mel bin ranges
    bass_bins = mel_spec_norm[:20, :]  # Low frequencies
    mid_bins = mel_spec_norm[20:80, :]  # Mid frequencies
    high_bins = mel_spec_norm[80:, :]  # High frequencies
    
    bass_energy_values = bass_bins.mean(axis=0)
    mid_energy_values = mid_bins.mean(axis=0)
    high_energy_values = high_bins.mean(axis=0)
    
    times = librosa.frames_to_time(np.arange(mel_spec_norm.shape[1]), sr=sr, hop_length=hop_length)
    
    bass_energy = list(zip(times.tolist(), bass_energy_values.tolist()))
    mid_energy = list(zip(times.tolist(), mid_energy_values.tolist()))
    high_energy = list(zip(times.tolist(), high_energy_values.tolist()))
    
    # Compute additional metrics for AI interpretation
    # These are raw metrics - let AI interpret what they mean for effects
    onset_density = len(onset_times) / actual_duration if actual_duration > 0 else 0.0
    
    # Average frequency band energies
    avg_bass = float(np.mean(bass_energy_values)) if len(bass_energy_values) > 0 else 0.0
    avg_mid = float(np.mean(mid_energy_values)) if len(mid_energy_values) > 0 else 0.0
    avg_high = float(np.mean(high_energy_values)) if len(high_energy_values) > 0 else 0.0
    
    # Dynamic range (how much energy varies)
    energy_values = [e[1] for e in energy_envelope]
    dynamic_range = float(max(energy_values) - min(energy_values)) if energy_values else 0.0
    
    # Beat strength variance (are beats consistent or varied)
    beat_variance = float(np.var(beat_strengths)) if len(beat_strengths) > 1 else 0.0
    
    # Average energy level
    avg_energy = float(np.mean(energy_values)) if energy_values else 0.0
    
    return AudioFeatures(
        duration=actual_duration,
        sample_rate=sr,
        tempo=float(tempo) if isinstance(tempo, np.ndarray) else tempo,
        beat_times=beat_times,
        beat_strengths=beat_strengths,
        onset_times=onset_times,
        onset_strengths=onset_strengths,
        energy_envelope=energy_envelope,
        bass_energy=bass_energy,
        mid_energy=mid_energy,
        high_energy=high_energy,
        onset_density=onset_density,
        average_bass=avg_bass,
        average_mid=avg_mid,
        average_high=avg_high,
        dynamic_range=dynamic_range,
        beat_strength_variance=beat_variance,
        average_energy=avg_energy
    )


def get_waveform_data(audio_path: str, num_points: int = 200) -> List[Tuple[float, float]]:
    """
    Get downsampled waveform data for visualization.
    Uses a very low sample rate for speed.
    
    Args:
        audio_path: Path to the audio file
        num_points: Number of points to return for visualization
    
    Returns:
        List of (time, amplitude) tuples
    """
    # Use very low sample rate for fast loading (just for visualization)
    # 8000 Hz is enough for waveform display
    y, sr = librosa.load(audio_path, sr=8000, mono=True)
    duration = len(y) / sr
    
    # Cache this for later use
    _audio_cache[audio_path] = {'duration': duration}
    
    # Downsample for visualization
    chunk_size = max(1, len(y) // num_points)
    
    waveform_data = []
    for i in range(0, len(y), chunk_size):
        chunk = y[i:i + chunk_size]
        if len(chunk) > 0:
            # Use peak amplitude for this chunk
            peak = float(np.max(np.abs(chunk)))
            time = (i + chunk_size // 2) / sr
            waveform_data.append((time, peak))
    
    return waveform_data[:num_points]


def get_audio_duration(audio_path: str) -> float:
    """
    Get the duration of an audio file in seconds.
    Uses ffprobe for speed (doesn't decode the entire file).
    """
    # Check cache first
    if audio_path in _audio_cache and 'duration' in _audio_cache[audio_path]:
        return _audio_cache[audio_path]['duration']
    
    try:
        # Use ffprobe for fast duration detection
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'json', audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            duration = float(data['format']['duration'])
            _audio_cache[audio_path] = {'duration': duration}
            return duration
    except Exception:
        pass
    
    # Fallback: use librosa with duration=0 to just get metadata
    try:
        # Load just 1 second at low sample rate to estimate
        y, sr = librosa.load(audio_path, sr=8000, mono=True, duration=1)
        # Get actual duration from file info
        import soundfile as sf
        info = sf.info(audio_path)
        duration = info.duration
        _audio_cache[audio_path] = {'duration': duration}
        return duration
    except Exception:
        pass
    
    # Last resort: load full file
    y, sr = librosa.load(audio_path, sr=8000, mono=True)
    duration = len(y) / sr
    _audio_cache[audio_path] = {'duration': duration}
    return duration

