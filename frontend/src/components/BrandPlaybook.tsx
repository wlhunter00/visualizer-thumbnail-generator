import { Playbook } from '../types';
import { Sparkles, Music, Palette, Tag } from 'lucide-react';

interface BrandPlaybookProps {
  playbook: Playbook;
}

export default function BrandPlaybook({ playbook }: BrandPlaybookProps) {
  return (
    <div className="bg-white rounded-2xl border border-surface-200 p-4 space-y-4">
      <div className="flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-accent" />
        <span className="text-sm font-medium text-surface-700">Your Visual Identity</span>
      </div>
      
      {/* Summary */}
      <p className="text-sm text-surface-600 leading-relaxed">
        {playbook.summary}
      </p>
      
      {/* Attributes */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-surface-50 rounded-xl p-3">
          <div className="flex items-center gap-1.5 text-surface-500 mb-1">
            <Palette className="w-3 h-3" />
            <span className="text-xs">Motion</span>
          </div>
          <span className="text-sm font-medium text-surface-700 capitalize">
            {playbook.attributes.motion}
          </span>
        </div>
        
        <div className="bg-surface-50 rounded-xl p-3">
          <div className="flex items-center gap-1.5 text-surface-500 mb-1">
            <Music className="w-3 h-3" />
            <span className="text-xs">Reactivity</span>
          </div>
          <span className="text-sm font-medium text-surface-700 capitalize">
            {playbook.attributes.reactivity}
          </span>
        </div>
      </div>
      
      {/* Mood */}
      <div className="bg-accent/5 rounded-xl p-3">
        <span className="text-xs text-accent font-medium">Mood</span>
        <p className="text-sm text-surface-700 mt-1 capitalize">{playbook.mood}</p>
      </div>
      
      {/* Genre Fit */}
      <div>
        <div className="flex items-center gap-1.5 text-surface-500 mb-2">
          <Tag className="w-3 h-3" />
          <span className="text-xs">Works well with</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {playbook.genre_fit.map((genre) => (
            <span
              key={genre}
              className="px-2.5 py-1 bg-surface-100 text-surface-600 text-xs rounded-full"
            >
              {genre}
            </span>
          ))}
        </div>
      </div>
      
      {/* Active Effects */}
      {playbook.active_effects.length > 0 && (
        <div>
          <span className="text-xs text-surface-500 block mb-2">Active effects</span>
          <div className="flex flex-wrap gap-1.5">
            {playbook.active_effects.map((effect) => (
              <span
                key={effect}
                className="px-2.5 py-1 bg-accent/10 text-accent text-xs rounded-full"
              >
                {effect}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

