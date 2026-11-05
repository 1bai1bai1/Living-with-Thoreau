import { useEffect, useRef } from 'react';

import type { SeasonKey } from '../api';

// The painted backdrop (visual direction C): a skyline, the pond, the cabin
// with a lit window, and the season's weather drifting over it. The static
// scene is painted once per season/size; only the particles animate. When
// the season changes, the old painting fades into the new one.

type Palette = { sky: [string, string]; glow: string; hills: [string, string, string]; fg: string; water: string; lamp: string };

const PALETTES: Record<SeasonKey, Palette> = {
  spring: { sky: ['#6f9bb5', '#f3d7c3'], glow: '#fff0cf', hills: ['#9fb7b0', '#7f9f92', '#5f8574'], fg: '#223629', water: '#c7d6dc', lamp: '#ffe2a0' },
  summer: { sky: ['#33608f', '#f4c27a'], glow: '#ffe0a0', hills: ['#6c8f86', '#4b7468', '#35594f'], fg: '#172a23', water: '#d9b88a', lamp: '#ffd27a' },
  autumn: { sky: ['#4a3b5c', '#f09a58'], glow: '#ffc07a', hills: ['#8a6070', '#6d4a57', '#4d3441'], fg: '#261b20', water: '#c98660', lamp: '#ffc86a' },
  winter: { sky: ['#1f2f4d', '#9db4d0'], glow: '#dfe9f5', hills: ['#8fa3bf', '#6d84a3', '#4f6685'], fg: '#121d30', water: '#a9bbd2', lamp: '#ffd98a' },
};

const COUNT: Record<SeasonKey, number> = { spring: 48, summer: 34, autumn: 46, winter: 130 };
const LEAVES = ['#e07b2f', '#c0392b', '#e8a33a', '#a8541f'];
const FADE_MS = 1600;

type Particle = { x: number; y: number; ph: number; v: number; r: number; vr: number; s: number; sp: number; c: string };

const rnd = (a: number, b: number) => a + Math.random() * (b - a);

function paint(season: SeasonKey, w: number, h: number, dpr: number): HTMLCanvasElement {
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, Math.round(w * dpr));
  canvas.height = Math.max(1, Math.round(h * dpr));
  const b = canvas.getContext('2d')!;
  b.scale(dpr, dpr);
  const p = PALETTES[season];

  const ridge = (base: number, amp: number, seed: number) => {
    b.beginPath();
    b.moveTo(0, h);
    for (let x = 0; x <= w + 6; x += 6) {
      b.lineTo(x, base + amp * (Math.sin(x * 0.0042 + seed) + 0.5 * Math.sin(x * 0.011 + seed * 2) + 0.25 * Math.sin(x * 0.027 + seed * 3)));
    }
    b.lineTo(w, h);
    b.closePath();
    b.fill();
  };
  const pine = (x: number, y: number, H: number) => {
    for (let i = 0; i < 4; i++) {
      const apex = y - H * (1 - 0.2 * i);
      const base = apex + H * 0.38;
      const half = H * (0.2 + 0.06 * i);
      b.beginPath();
      b.moveTo(x, apex);
      b.lineTo(x - half, base);
      b.lineTo(x + half, base);
      b.closePath();
      b.fill();
    }
    b.fillRect(x - H * 0.025, y - H * 0.04, H * 0.05, H * 0.08);
  };

  let g = b.createLinearGradient(0, 0, 0, h * 0.62);
  g.addColorStop(0, p.sky[0]);
  g.addColorStop(1, p.sky[1]);
  b.fillStyle = g;
  b.fillRect(0, 0, w, h);

  const gx = w * 0.74;
  const gy = h * 0.22;
  g = b.createRadialGradient(gx, gy, 0, gx, gy, h * 0.36);
  g.addColorStop(0, p.glow + 'cc');
  g.addColorStop(1, p.glow + '00');
  b.fillStyle = g;
  b.fillRect(0, 0, w, h);

  b.fillStyle = p.hills[0];
  ridge(h * 0.3, h * 0.035, 1.3);
  b.fillStyle = p.hills[1];
  ridge(h * 0.36, h * 0.04, 3.1);
  b.fillStyle = p.hills[2];
  ridge(h * 0.42, h * 0.035, 5.2);

  const wy = h * 0.47;
  g = b.createLinearGradient(0, wy, 0, wy + h * 0.07);
  g.addColorStop(0, p.water);
  g.addColorStop(1, p.hills[2]);
  b.fillStyle = g;
  b.beginPath();
  b.ellipse(w * 0.36, wy + h * 0.03, w * 0.3, h * 0.04, 0, 0, Math.PI * 2);
  b.fill();

  b.fillStyle = p.fg;
  ridge(h * 0.535, h * 0.012, 7.7);
  for (const [fx, fy, fh] of [[0.04, 0.6, 0.3], [0.1, 0.58, 0.22], [0.16, 0.56, 0.15], [0.93, 0.6, 0.32], [0.87, 0.58, 0.22], [0.79, 0.55, 0.14]]) {
    pine(w * fx, h * fy, h * fh);
  }

  // The cabin, ten by fifteen, with the lamp lit.
  const k = h / 700;
  const cx = w * 0.64;
  const cy = h * 0.46;
  b.fillStyle = p.fg;
  b.fillRect(cx, cy - 26 * k, 56 * k, 26 * k);
  b.beginPath();
  b.moveTo(cx - 6 * k, cy - 26 * k);
  b.lineTo(cx + 28 * k, cy - 50 * k);
  b.lineTo(cx + 62 * k, cy - 26 * k);
  b.closePath();
  b.fill();
  b.fillRect(cx + 44 * k, cy - 56 * k, 8 * k, 20 * k);
  const lx = cx + 14 * k;
  const ly = cy - 16 * k;
  g = b.createRadialGradient(lx, ly, 0, lx, ly, 38 * k);
  g.addColorStop(0, p.lamp + 'dd');
  g.addColorStop(1, p.lamp + '00');
  b.fillStyle = g;
  b.fillRect(lx - 40 * k, ly - 40 * k, 80 * k, 80 * k);
  b.fillStyle = p.lamp;
  b.fillRect(lx - 5 * k, ly - 5 * k, 10 * k, 10 * k);
  return canvas;
}

function spawn(season: SeasonKey, w: number, h: number): Particle[] {
  return Array.from({ length: COUNT[season] }, () => ({
    x: rnd(0, w),
    y: season === 'summer' ? rnd(h * 0.3, h * 0.56) : rnd(0, h),
    ph: rnd(0, 6.28),
    v: rnd(0, 1),
    r: rnd(0, 6.28),
    vr: rnd(-0.03, 0.03),
    s: season === 'winter' ? rnd(1, 3.2) : season === 'autumn' ? rnd(4, 7) : rnd(3, 5.5),
    sp: rnd(0.6, 1.4),
    c: LEAVES[Math.floor(Math.random() * LEAVES.length)],
  }));
}

function drawParticles(ctx: CanvasRenderingContext2D, season: SeasonKey, parts: Particle[], t: number, w: number, h: number, move: boolean) {
  for (const p of parts) {
    if (season === 'summer') {
      if (move) {
        p.x = (p.x + Math.cos(t * 0.0004 + p.ph) * 0.35 + w) % w;
        p.y = Math.min(h * 0.56, Math.max(h * 0.3, p.y + Math.sin(t * 0.0005 + p.ph * 1.7) * 0.3));
      }
      const a = 0.3 + 0.7 * Math.max(0, Math.sin(t * 0.002 * p.sp + p.ph));
      const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, 11);
      g.addColorStop(0, `rgba(235,255,150,${a})`);
      g.addColorStop(1, 'rgba(235,255,150,0)');
      ctx.fillStyle = g;
      ctx.fillRect(p.x - 11, p.y - 11, 22, 22);
      continue;
    }
    if (move) {
      if (season === 'spring') {
        p.x += Math.sin(t * 0.001 + p.ph) * 0.4 + 0.25;
        p.y += 0.5 + p.v * 0.5;
        p.r += p.vr;
      } else if (season === 'autumn') {
        p.x += Math.sin(t * 0.0011 + p.ph) * 0.7 + 0.2;
        p.y += 0.7 + p.v * 0.6;
        p.r += p.vr;
      } else {
        p.x += Math.sin(t * 0.0008 + p.ph) * 0.3 + 0.15 * p.v;
        p.y += 0.5 + p.v * 0.8;
      }
      if (p.y > h + 10) {
        p.y = -10;
        p.x = rnd(0, w);
      }
      if (p.x > w + 10) p.x = -10;
      else if (p.x < -10) p.x = w + 10;
    }
    ctx.save();
    ctx.translate(p.x, p.y);
    ctx.rotate(p.r);
    ctx.beginPath();
    if (season === 'spring') {
      ctx.fillStyle = 'rgba(248,214,224,.88)';
      ctx.ellipse(0, 0, p.s, p.s * 0.55, 0, 0, Math.PI * 2);
    } else if (season === 'autumn') {
      ctx.fillStyle = p.c;
      ctx.ellipse(0, 0, p.s, p.s * 0.5, 0, 0, Math.PI * 2);
    } else {
      ctx.fillStyle = `rgba(255,255,255,${0.5 + p.v * 0.4})`;
      ctx.arc(0, 0, p.s, 0, Math.PI * 2);
    }
    ctx.fill();
    ctx.restore();
  }
}

export default function Atmosphere({ season }: { season: SeasonKey }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const setSeasonRef = useRef<(s: SeasonKey) => void>(() => {});

  useEffect(() => {
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext('2d')!;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let current: SeasonKey = season;
    let w = 0;
    let h = 0;
    let dpr = 1;
    let bg: HTMLCanvasElement | null = null;
    let prev: HTMLCanvasElement | null = null;
    let fadeFrom = 0;
    let parts: Particle[] = [];
    let raf = 0;

    const frame = (t: number, move: boolean) => {
      ctx.clearRect(0, 0, w, h);
      if (bg) ctx.drawImage(bg, 0, 0, w, h);
      if (prev) {
        const left = 1 - (t - fadeFrom) / FADE_MS;
        if (left <= 0 || reduce) prev = null;
        else {
          ctx.globalAlpha = left;
          ctx.drawImage(prev, 0, 0, w, h);
          ctx.globalAlpha = 1;
        }
      }
      drawParticles(ctx, current, parts, t, w, h, move);
    };

    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      bg = paint(current, w, h, dpr);
      parts = spawn(current, w, h);
      if (reduce) frame(0, false);
    };

    setSeasonRef.current = (next: SeasonKey) => {
      if (next === current) return;
      prev = bg;
      fadeFrom = performance.now();
      current = next;
      bg = paint(current, w, h, dpr);
      parts = spawn(current, w, h);
      if (reduce) frame(0, false);
    };

    const loop = (t: number) => {
      if (!document.hidden) frame(t, true);
      raf = requestAnimationFrame(loop);
    };

    resize();
    window.addEventListener('resize', resize);
    if (!reduce) raf = requestAnimationFrame(loop);
    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(raf);
    };
    // Mount once; season changes go through setSeasonRef so the fade can run.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setSeasonRef.current(season);
  }, [season]);

  return <canvas ref={canvasRef} aria-hidden="true" className="fixed inset-0 h-full w-full" />;
}
