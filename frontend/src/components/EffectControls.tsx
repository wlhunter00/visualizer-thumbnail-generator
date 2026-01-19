import { GenerateSettings } from '../types';
import { Zap, Music2, Flame } from 'lucide-react';

interface EffectControlsProps {
  motionIntensity: number;
  beatReactivity: number;
  energyLevel: number;
  onChange: (key: keyof GenerateSettings, value: number) => void;
}

export default function EffectControls({
  motionIntensity,
  beatReactivity,
  energyLevel,
  onChange,
}: EffectControlsProps) {
  const sliders = [
    {
      key: 'motion_intensity' as const,
      label: 'Motion Intensity',
      description: 'How much the image moves',
      value: motionIntensity,
      icon: <Zap className="w-4 h-4" />,
      lowLabel: 'Subtle',
      highLabel: 'Dynamic',
    },
    {
      key: 'beat_reactivity' as const,
      label: 'Beat Reactivity',
      description: 'How tightly synced to the beat',
      value: beatReactivity,
      icon: <Music2 className="w-4 h-4" />,
      lowLabel: 'Flowing',
      highLabel: 'Punchy',
    },
    {
      key: 'energy_level' as const,
      label: 'Energy Level',
      description: 'Overall mood and vibe',
      value: energyLevel,
      icon: <Flame className="w-4 h-4" />,
      lowLabel: 'Calm',
      highLabel: 'Energetic',
    },
  ];
  
  return (
    <div className="bg-white rounded-2xl border border-surface-200 p-4 space-y-5">
      <span className="text-sm font-medium text-surface-700">Visual Settings</span>
      
      {sliders.map((slider) => (
        <div key={slider.key} className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-accent">{slider.icon}</span>
              <span className="text-sm font-medium text-surface-700">{slider.label}</span>
            </div>
            <span className="text-sm text-surface-500">{slider.value}%</span>
          </div>
          
          <input
            type="range"
            min="0"
            max="100"
            value={slider.value}
            onChange={(e) => onChange(slider.key, parseInt(e.target.value))}
            className="w-full"
          />
          
          <div className="flex justify-between text-xs text-surface-400">
            <span>{slider.lowLabel}</span>
            <span>{slider.highLabel}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

