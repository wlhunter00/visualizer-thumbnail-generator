/** Deterministic pseudo-random offset for slice bands within a glitch burst. */
export function seededSliceOffset(seed: number, bandIndex: number, magnitude: number): number {
  const x = Math.sin(seed * 0.001 + bandIndex * 12.9898) * 43758.5453;
  const frac = x - Math.floor(x);
  return (frac - 0.5) * magnitude * 4;
}
