import type { RGB } from './colorUtils';

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
    burstKey: string
  ) {
    if (this.spawnedBursts.has(burstKey)) return;
    this.spawnedBursts.add(burstKey);

    const centerX = (boundsX + boundsW / 2) * width;
    const centerY = (boundsY + boundsH / 2) * height;
    const radiusX = (boundsW / 2) * width * 1.1;
    const radiusY = (boundsH / 2) * height * 1.1;
    const previewCount = Math.max(5, Math.floor(count * 0.5 * strength));

    for (let i = 0; i < previewCount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const spawnX = centerX + Math.cos(angle) * radiusX;
      const spawnY = centerY + Math.sin(angle) * radiusY;
      const dirAngle = angle + (Math.random() - 0.5) * 0.8;
      const particleSpeed = speed * (0.5 + Math.random() * 0.5) * strength;
      const color = colors[Math.floor(Math.random() * colors.length)] ?? [255, 255, 255];
      const size = sizeRange[0] + Math.random() * (sizeRange[1] - sizeRange[0]);

      this.particles.push({
        x: spawnX,
        y: spawnY,
        vx: Math.cos(dirAngle) * particleSpeed,
        vy: Math.sin(dirAngle) * particleSpeed,
        size,
        color,
        alpha: 0.8 + Math.random() * 0.2,
        birthTime: time,
        lifetime,
      });
    }
  }

  update(time: number, dt: number) {
    this.particles = this.particles.filter(p => {
      const age = time - p.birthTime;
      return age < p.lifetime;
    });
    for (const p of this.particles) {
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.vy += 30 * dt; // slight gravity
    }
  }

  draw(ctx: CanvasRenderingContext2D, time: number) {
    for (const p of this.particles) {
      const age = time - p.birthTime;
      const progress = age / p.lifetime;
      const alpha = p.alpha * (1 - progress);
      if (alpha <= 0) continue;
      const size = p.size * (1 - progress * 0.5);
      ctx.beginPath();
      ctx.arc(p.x, p.y, size / 2, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${p.color[0]},${p.color[1]},${p.color[2]},${alpha})`;
      ctx.fill();
    }
  }
}
