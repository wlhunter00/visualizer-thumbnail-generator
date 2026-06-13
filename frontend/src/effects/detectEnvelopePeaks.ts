import type { EnergyEnvelope } from '../types';

/** Return (time, strength) peaks above threshold from a 0-1 envelope. */
export function detectEnvelopePeaks(
  envelope: EnergyEnvelope,
  threshold: number,
  minDistanceSec = 0.1
): [number, number][] {
  if (!envelope.length) return [];

  const times = envelope.map(([t]) => t);
  const values = envelope.map(([, v]) => v);

  if (times.length < 2) return [];

  const diffs = times.slice(1).map((t, i) => t - times[i]);
  const avgDt = diffs.reduce((a, b) => a + b, 0) / diffs.length || 0.01;
  const minDistance = Math.max(1, Math.floor(minDistanceSec / Math.max(avgDt, 1e-6)));

  const peaks: [number, number][] = [];
  for (let i = minDistance; i < values.length - minDistance; i++) {
    if (values[i] < threshold) continue;
    let isPeak = true;
    for (let j = i - minDistance; j <= i + minDistance; j++) {
      if (j !== i && values[j] >= values[i]) {
        isPeak = false;
        break;
      }
    }
    if (isPeak) peaks.push([times[i], values[i]]);
  }
  return peaks;
}
