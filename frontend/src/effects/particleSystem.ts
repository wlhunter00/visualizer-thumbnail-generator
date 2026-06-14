import type { RGB } from './colorUtils';
import { previewScale } from './render/compositor';

export interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  color: RGB;
  alpha: number;
  birthTime: number;
  lifetime: number;
}

export class ParticleSystem {
  particles: Particle[] = [];
  private spawnedBursts = new Set<string>();

  reset() {
    this.particles = [];
    this.spawnedBursts.clear();
  }

  spawnBurstFromBounds(
    boundsX: number, boundsY: number, boundsW: number, boundsH: number,
    count: number, colors: RGB[], sizeRange: [number, number],
    speed: number, lifetime: number, time: number,
    width: number, height: number, strength: number,
    burstKey: string,
  ) {
    if (this.spawnedBursts.has(burstKey)) return;
    this.spawnedBursts.add(burstKey);

    const scale = previewScale(width);
    const scaledSpeed = speed * scale;
    const scaledSizeRange: [number, number] = [sizeRange[0] * scale, sizeRange[1] * scale];
    const spawnCount = Math.max(1, Math.floor(count * Math.max(strength, 0.1)));

    const centerX = (boundsX + boundsW / 2) * width;
    const centerY = (boundsY + boundsH / 2) * height;
    const radiusX = (boundsW / 2) * width * 1.1;
    const radiusY = (boundsH / 2) * height * 1.1;

    for (let i = 0; i < spawnCount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const spawnX = centerX + Math.cos(angle) * radiusX;
      const spawnY = centerY + Math.sin(angle) * radiusY;
      const velocity = scaledSpeed * (0.5 + Math.random() * 0.5);
      const color = colors[Math.floor(Math.random() * colors.length)] ?? [255, 255, 255];

      this.particles.push({
        x: spawnX,
        y: spawnY,
        vx: Math.cos(angle) * velocity,
        vy: Math.sin(angle) * velocity,
        size: scaledSizeRange[0] + Math.random() * (scaledSizeRange[1] - scaledSizeRange[0]),
        color,
        alpha: 0.8 + Math.random() * 0.2,
        birthTime: time,
        lifetime: lifetime * (0.7 + Math.random() * 0.3),
      });
    }
  }

  update(time: number, dt: number) {
    const alive: Particle[] = [];
    for (const p of this.particles) {
      const age = time - p.birthTime;
      if (age < p.lifetime) {
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.vy += 50 * dt;
        p.vx *= 0.98;
        p.vy *= 0.98;
        alive.push(p);
      }
    }
    this.particles = alive;
  }

  draw(ctx: CanvasRenderingContext2D, time: number) {
    for (const p of this.particles) {
      const age = time - p.birthTime;
      const progress = age / p.lifetime;
      const alpha = Math.floor(p.alpha * (1 - progress) * 255);
      if (alpha <= 0) continue;
      const size = p.size * (1 - progress * 0.5);
      const r = Math.max(1, size / 2);
      ctx.beginPath();
      ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${p.color[0]},${p.color[1]},${p.color[2]},${alpha / 255})`;
      ctx.fill();
    }
  }
}
