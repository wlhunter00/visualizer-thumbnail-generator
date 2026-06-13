import type { AudioFeatures, TriggerSource } from '../types';
import { detectEnvelopePeaks } from './detectEnvelopePeaks';

export function buildTriggers(
  audioFeatures: AudioFeatures,
  triggerSource: TriggerSource,
  intensity: number,
  baseThreshold = 0.3,
  applyThreshold = true
): [number, number][] {
  const threshold = applyThreshold ? baseThreshold * (1 - intensity) : 0;
  const triggers: [number, number][] = [];

  if (triggerSource === 'beats') {
    audioFeatures.beat_times.forEach((beatTime, i) => {
      const strength = audioFeatures.beat_strengths[i] ?? 0.5;
      if (strength >= threshold) triggers.push([beatTime, strength * intensity]);
    });
  } else if (triggerSource === 'onsets') {
    audioFeatures.onset_times.forEach((onsetTime, i) => {
      const strength = audioFeatures.onset_strengths[i] ?? 0.5;
      if (strength >= threshold) triggers.push([onsetTime, strength * intensity]);
    });
  } else if (triggerSource === 'full') {
    detectEnvelopePeaks(audioFeatures.energy_envelope, threshold).forEach(
      ([t, s]) => triggers.push([t, s * intensity])
    );
  } else if (triggerSource === 'low') {
    detectEnvelopePeaks(audioFeatures.low_freq_energy, threshold).forEach(
      ([t, s]) => triggers.push([t, s * intensity])
    );
  } else if (triggerSource === 'medium') {
    detectEnvelopePeaks(audioFeatures.mid_freq_energy, threshold).forEach(
      ([t, s]) => triggers.push([t, s * intensity])
    );
  } else if (triggerSource === 'high') {
    detectEnvelopePeaks(audioFeatures.high_freq_energy, threshold).forEach(
      ([t, s]) => triggers.push([t, s * intensity])
    );
  }

  return triggers;
}
