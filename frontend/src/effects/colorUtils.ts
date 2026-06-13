export type RGB = [number, number, number];

export function hexToRgb(hexColor: string): RGB {
  const hex = hexColor.replace('#', '');
  return [
    parseInt(hex.slice(0, 2), 16),
    parseInt(hex.slice(2, 4), 16),
    parseInt(hex.slice(4, 6), 16),
  ];
}

function rgbToHsv(r: number, g: number, b: number): [number, number, number] {
  r /= 255; g /= 255; b /= 255;
  const maxC = Math.max(r, g, b);
  const minC = Math.min(r, g, b);
  const diff = maxC - minC;
  const v = maxC;
  const s = maxC === 0 ? 0 : diff / maxC;
  let h = 0;
  if (diff !== 0) {
    if (maxC === r) h = 60 * (((g - b) / diff) % 6);
    else if (maxC === g) h = 60 * (((b - r) / diff) + 2);
    else h = 60 * (((r - g) / diff) + 4);
  }
  return [h, s, v];
}

function hsvToRgb(h: number, s: number, v: number): RGB {
  const c = v * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = v - c;
  let r = 0, g = 0, b = 0;
  if (h < 60) [r, g, b] = [c, x, 0];
  else if (h < 120) [r, g, b] = [x, c, 0];
  else if (h < 180) [r, g, b] = [0, c, x];
  else if (h < 240) [r, g, b] = [0, x, c];
  else if (h < 300) [r, g, b] = [x, 0, c];
  else [r, g, b] = [c, 0, x];
  return [
    Math.round((r + m) * 255),
    Math.round((g + m) * 255),
    Math.round((b + m) * 255),
  ];
}

function hueVariance(hues: number[]): number {
  if (hues.length < 2) return 0;
  const sorted = [...hues].sort((a, b) => a - b);
  let maxGap = 0;
  for (let i = 0; i < sorted.length; i++) {
    const nextI = (i + 1) % sorted.length;
    let gap = sorted[nextI] - sorted[i];
    if (nextI === 0) gap = (360 - sorted[i]) + sorted[nextI];
    maxGap = Math.max(maxGap, gap);
  }
  return 360 - maxGap;
}

function boostColorForParticles(color: RGB, preservePalette: boolean): RGB {
  const [h, s, v] = rgbToHsv(color[0], color[1], color[2]);
  const newS = preservePalette ? Math.min(1, s * 1.1) : Math.min(1, s * 1.15 + 0.05);
  const newV = Math.max(0.5, Math.min(1, v * 1.2 + 0.2));
  return hsvToRgb(h, newS, newV);
}

export function prepareParticleColors(colors: RGB[]): RGB[] {
  if (!colors.length) return [[255, 255, 255]];

  const hues: number[] = [];
  for (const color of colors) {
    const [, s, ] = rgbToHsv(color[0], color[1], color[2]);
    if (s > 0.1) hues.push(rgbToHsv(color[0], color[1], color[2])[0]);
  }
  const isLimited = hues.length <= 1 || (hues.length > 1 && hueVariance(hues) < 30);

  let boosted: RGB[] = [];
  for (const color of colors) {
    const brightness = (color[0] + color[1] + color[2]) / 3;
    if (brightness < 40) continue;
    boosted.push(boostColorForParticles(color, isLimited));
  }

  if (!boosted.length) {
    boosted = colors.slice(0, 3).map(c => boostColorForParticles(c, isLimited));
  }
  return boosted.length ? boosted : [[255, 255, 255]];
}
