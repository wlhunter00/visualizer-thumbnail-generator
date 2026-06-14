import type { AudioFeatures, TriggerSource } from '../types';
import { detectEnvelopePeaks } from './detectEnvelopePeaks';

export function buildTriggers(
  audioFeatures: AudioFeatures,
  triggerSource: TriggerSource,
  intensity: number,
  baseThreshold = 0.3,
  applyThreshold = true,
  scaleStrength = true
): [number, number][] {
  const threshold = applyThreshold ? baseThreshold * (1 - intensity) : 0;
  const triggers: [number, number][] = [];

  if (triggerSource === 'beats') {
    audioFeatures.beat_times.forEach((beatTime, i) => {
      const strength = audioFeatures.beat_strengths[i] ?? 0.5;
      if (strength >= threshold) {
        triggers.push([beatTime, scaleStrength ? strength * intensity : strength]);
      }
    });
  } else if (triggerSource === 'onsets') {
    audioFeatures.onset_times.forEach((onsetTime, i) => {
      const strength = audioFeatures.onset_strengths[i] ?? 0.5;
      if (strength >= threshold) {
        triggers.push([onsetTime, scaleStrength ? strength * intensity : strength]);
      }
    });
  } else if (triggerSource === 'full') {
    detectEnvelopePeaks(audioFeatures.energy_envelope, threshold).forEach(
      ([t, s]) => triggers.push([t, scaleStrength ? s * intensity : s])
    );
  } else if (triggerSource === 'low') {
    detectEnvelopePeaks(audioFeatures.low_freq_energy, threshold).forEach(
      ([t, s]) => triggers.push([t, scaleStrength ? s * intensity : s])
    );
  } else if (triggerSource === 'medium') {
    detectEnvelopePeaks(audioFeatures.mid_freq_energy, threshold).forEach(
      ([t, s]) => triggers.push([t, scaleStrength ? s * intensity : s])
    );
  } else if (triggerSource === 'high') {
    detectEnvelopePeaks(audioFeatures.high_freq_energy, threshold).forEach(
      ([t, s]) => triggers.push([t, scaleStrength ? s * intensity : s])
    );
  }

  return triggers;
}

export function buildGlitchBurstTriggers(
  audioFeatures: AudioFeatures,
  triggerSource: TriggerSource,
  intensity: number,
  baseThreshold = 0.5
): [number, number, number][] {
  const triggers: [number, number, number][] = [];
  const sourceTriggers = buildTriggers(
    audioFeatures,
    triggerSource,
    intensity,
    baseThreshold,
    true,
    false
  );
  for (const [triggerTime, rawStrength] of sourceTriggers) {
    const duration = Math.max(0.1, 0.08 + rawStrength * 0.15 + intensity * 0.12);
    triggers.push([triggerTime, duration, rawStrength]);
  }
  if (triggerSource === 'onsets' && intensity > 0.5) {
    const beatTriggers = buildTriggers(audioFeatures, 'beats', intensity * 0.8, 0.4, true, false);
    for (const [beatTime, beatStrength] of beatTriggers) {
      const duration = Math.max(0.1, 0.06 + beatStrength * 0.1 + intensity * 0.08);
      triggers.push([beatTime, duration, beatStrength]);
    }
  }
  return triggers;
}
