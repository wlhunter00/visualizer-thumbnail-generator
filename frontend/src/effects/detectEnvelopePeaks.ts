import type { EnergyEnvelope } from '../types';

/** scipy.signal.find_peaks equivalent: height + minimum distance between peaks. */
function findPeaks(values: number[], height: number, distance: number): number[] {
  const n = values.length;
  const candidates: number[] = [];

  for (let i = 0; i < n; i++) {
    if (values[i] < height) continue;

    let leftOk = true;
    let j = i - 1;
    while (j >= 0 && values[j] === values[i]) j--;
    if (j >= 0 && values[j] > values[i]) leftOk = false;

    let rightOk = true;
    j = i + 1;
    while (j < n && values[j] === values[i]) j++;
    if (j < n && values[j] > values[i]) rightOk = false;

    if (leftOk && rightOk) candidates.push(i);
  }

  if (distance <= 0) return candidates;

  const byHeight = [...candidates].sort((a, b) => values[b] - values[a]);
  const kept: number[] = [];
  for (const idx of byHeight) {
    if (kept.every(k => Math.abs(k - idx) >= distance)) kept.push(idx);
  }
  return kept.sort((a, b) => a - b);
}

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

  const peakIndices = findPeaks(values, threshold, minDistance);
  return peakIndices.map(i => [times[i], values[i]]);
}
