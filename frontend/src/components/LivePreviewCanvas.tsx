import { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import { Play, Pause, RotateCcw } from 'lucide-react';
import type { AudioFeatures, EffectToggles, ImageAnalysis } from '../types';
import {
  calculateEffectParams,
  getValuesAtTime,
  imageContextFromAnalysis,
  getPreviewDimensions,
  fitImageToFrame,
} from '../effects';
import { createDrawState, drawFrame, resetDrawState } from '../effects/drawFrame';
import { useAudioPreview } from '../context/AudioPreviewContext';

interface LivePreviewCanvasProps {
  imageUrl: string;
  aspectRatio: string;
  effectToggles: EffectToggles;
  audioFeatures: AudioFeatures | null;
  imageAnalysis: ImageAnalysis | null;
  isLoading?: boolean;
}

export default function LivePreviewCanvas({
  imageUrl,
  aspectRatio,
  effectToggles,
  audioFeatures,
  imageAnalysis,
  isLoading,
}: LivePreviewCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const baseCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const drawStateRef = useRef(createDrawState());
  const rafRef = useRef<number | null>(null);

  const [imageLoaded, setImageLoaded] = useState(false);
  const audioCtx = useAudioPreview();
  const { isPlaying, clipTime, play, pause, restart, toggle } = audioCtx;
  const audioCtxRef = useRef(audioCtx);
  audioCtxRef.current = audioCtx;

  const [width, height] = getPreviewDimensions(aspectRatio);

  const effectParams = useMemo(() => {
    if (!audioFeatures) return null;
    const ctx = imageContextFromAnalysis(imageAnalysis);
    return calculateEffectParams(audioFeatures, effectToggles, ctx);
  }, [audioFeatures, effectToggles, imageAnalysis]);

  // Load and prepare base image (crop-to-fill)
  useEffect(() => {
    setImageLoaded(false);
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const baseCanvas = document.createElement('canvas');
      baseCanvas.width = width;
      baseCanvas.height = height;
      const bctx = baseCanvas.getContext('2d')!;
      const fit = fitImageToFrame(img.width, img.height, width, height);
      bctx.drawImage(img, fit.sx, fit.sy, fit.sw, fit.sh, fit.dx, fit.dy, fit.dw, fit.dh);
      baseCanvasRef.current = baseCanvas;
      setImageLoaded(true);
    };
    img.onerror = () => setImageLoaded(false);
    img.src = imageUrl;
  }, [imageUrl, width, height]);

  const renderFrame = useCallback((time: number) => {
    const canvas = canvasRef.current;
    const baseCanvas = baseCanvasRef.current;
    if (!canvas || !baseCanvas || !effectParams) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const values = getValuesAtTime(effectParams, time);
    ctx.clearRect(0, 0, width, height);
    drawFrame(ctx, baseCanvas, values, drawStateRef.current, time, width, height);
  }, [effectParams, width, height]);

  // Static preview when paused — reset particle state when toggles change
  useEffect(() => {
    resetDrawState(drawStateRef.current);
    if (!isPlaying && imageLoaded && effectParams) {
      renderFrame(clipTime);
    }
  }, [effectToggles, isPlaying, clipTime, imageLoaded, effectParams, renderFrame]);

  // RAF loop while playing
  useEffect(() => {
    if (!isPlaying || !imageLoaded || !effectParams) {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      return;
    }

    const loop = () => {
      renderFrame(audioCtxRef.current.clipTime);
      rafRef.current = requestAnimationFrame(loop);
    };

    resetDrawState(drawStateRef.current);
    rafRef.current = requestAnimationFrame(loop);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [isPlaying, imageLoaded, effectParams, renderFrame]);

  // Spacebar handler
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.code === 'Space' && !['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement).tagName)) {
        e.preventDefault();
        toggle();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [toggle]);

  const aspectClass = {
    '9:16': 'aspect-[9/16] max-h-[500px]',
    '1:1': 'aspect-square max-h-[400px]',
    '16:9': 'aspect-video max-h-[400px]',
    '4:5': 'aspect-[4/5] max-h-[450px]',
  }[aspectRatio] ?? 'aspect-video';

  const showPlaceholder = isLoading || !audioFeatures || !imageLoaded;

  return (
    <div className="bg-white rounded-2xl border border-surface-200 p-4">
      <div className={`relative mx-auto bg-surface-900 rounded-xl overflow-hidden ${aspectClass}`}>
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          className="w-full h-full object-contain"
        />
        {showPlaceholder && (
          <div className="absolute inset-0 bg-surface-900/80 flex items-center justify-center">
            <span className="text-sm text-white/70">
              {isLoading ? 'Preparing preview…' : 'Loading…'}
            </span>
          </div>
        )}

        {/* Controls overlay */}
        <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/70 to-transparent p-4">
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={() => { resetDrawState(drawStateRef.current); restart(); }}
              className="p-2 rounded-full bg-white/20 hover:bg-white/30 text-white transition-colors"
              title="Restart"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={isPlaying ? pause : play}
              disabled={showPlaceholder}
              className="p-3 rounded-full bg-accent hover:bg-accent-dark text-white transition-colors disabled:opacity-50"
              title={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
            </button>
          </div>
        </div>
      </div>
      <p className="text-xs text-surface-400 mt-2 text-center">
        Press Play to preview effects · Spacebar to toggle · Export for final quality
      </p>
    </div>
  );
}
