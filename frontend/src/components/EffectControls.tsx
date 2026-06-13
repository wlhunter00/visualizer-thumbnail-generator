import { useState, useRef, useEffect } from 'react';
import { 
  EffectToggles, 
  TriggerSource,
  EFFECT_METADATA, 
  EFFECT_CATEGORIES,
  ImageAnalysis,
  TRIGGER_SOURCE_OPTIONS,
  GLITCH_TRIGGER_SOURCE_OPTIONS,
} from '../types';
import { 
  Sparkles, 
  Zap, 
  Wand2, 
  Target, 
  Film,
  ChevronDown,
  ChevronUp,
  Loader2
} from 'lucide-react';

interface EffectControlsProps {
  effectToggles: EffectToggles;
  onChange: (toggles: EffectToggles) => void;
  onAutoSuggest?: () => void;
  isAutoSuggesting?: boolean;
  imageAnalysis?: ImageAnalysis | null;
}

const categoryIcons: Record<string, React.ReactNode> = {
  element: <Target className="w-4 h-4" />,
  particle: <Sparkles className="w-4 h-4" />,
  style: <Film className="w-4 h-4" />,
  background: <Zap className="w-4 h-4" />,
};

interface TriggerSourceSelectProps {
  value: TriggerSource;
  options: typeof TRIGGER_SOURCE_OPTIONS;
  onChange: (value: TriggerSource) => void;
}

function TriggerSourceSelect({ value, options, onChange }: TriggerSourceSelectProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const selected = options.find(o => o.value === value) ?? options[0];

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={containerRef} className="relative mt-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-1.5 text-xs font-medium text-surface-700 bg-white border border-surface-200 rounded-lg hover:border-accent/40 transition-colors"
      >
        <span>{selected.label}</span>
        <ChevronDown className={`w-3.5 h-3.5 text-surface-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="absolute z-20 left-0 right-0 mt-1 bg-white border border-surface-200 rounded-lg shadow-lg overflow-hidden">
          {options.map(option => (
            <button
              key={option.value}
              type="button"
              onClick={() => {
                onChange(option.value);
                setOpen(false);
              }}
              className={`w-full text-left px-3 py-2 hover:bg-accent/5 transition-colors ${
                option.value === value ? 'bg-accent/10' : ''
              }`}
            >
              <div className="text-xs font-medium text-surface-800">{option.label}</div>
              <div className="text-[10px] text-surface-500 mt-0.5">{option.description}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function EffectControls({
  effectToggles,
  onChange,
  onAutoSuggest,
  isAutoSuggesting = false,
  imageAnalysis,
}: EffectControlsProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(['element', 'particle', 'style'])
  );

  const toggleCategory = (categoryId: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(categoryId)) {
        next.delete(categoryId);
      } else {
        next.add(categoryId);
      }
      return next;
    });
  };

  const handleToggleChange = (
    key: keyof EffectToggles,
    field: 'enabled' | 'intensity' | 'trigger_source',
    value: boolean | number | TriggerSource
  ) => {
    const newToggles = { ...effectToggles };
    newToggles[key] = {
      ...newToggles[key],
      [field]: value,
    };
    onChange(newToggles);
  };

  const getEffectsByCategory = (categoryId: string) => {
    return EFFECT_METADATA.filter(effect => effect.category === categoryId);
  };

  const countEnabledInCategory = (categoryId: string) => {
    return getEffectsByCategory(categoryId).filter(
      effect => effectToggles[effect.key]?.enabled
    ).length;
  };

  return (
    <div className="space-y-4">
      {/* Auto-Suggest Button */}
      {onAutoSuggest && (
        <button
          onClick={onAutoSuggest}
          disabled={isAutoSuggesting}
          className="w-full py-3 px-4 bg-gradient-to-r from-violet-500 to-purple-600 text-white font-medium rounded-xl hover:from-violet-600 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg shadow-purple-500/20"
        >
          {isAutoSuggesting ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Wand2 className="w-5 h-5" />
              Auto-Suggest Settings
            </>
          )}
        </button>
      )}

      {/* Image Analysis Info */}
      {imageAnalysis && (
        <div className="bg-gradient-to-r from-violet-50 to-purple-50 rounded-xl p-4 border border-violet-200">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-violet-100 flex items-center justify-center flex-shrink-0">
              <Target className="w-4 h-4 text-violet-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-violet-900">
                Detected: {imageAnalysis.subject}
              </p>
              <p className="text-xs text-violet-600 mt-0.5">
                Mood: {imageAnalysis.mood}
              </p>
              {imageAnalysis.colors.length > 0 && (
                <div className="flex gap-1 mt-2">
                  {imageAnalysis.colors.slice(0, 5).map((color, i) => (
                    <div
                      key={i}
                      className="w-5 h-5 rounded-full border border-white shadow-sm"
                      style={{ backgroundColor: color }}
                      title={color}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Effect Categories */}
      <div className="bg-white rounded-2xl border border-surface-200 overflow-hidden">
        {EFFECT_CATEGORIES.map((category, idx) => {
          const effects = getEffectsByCategory(category.id);
          const enabledCount = countEnabledInCategory(category.id);
          const isExpanded = expandedCategories.has(category.id);

          return (
            <div
              key={category.id}
              className={idx > 0 ? 'border-t border-surface-100' : ''}
            >
              {/* Category Header */}
              <button
                onClick={() => toggleCategory(category.id)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-surface-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="text-accent">{categoryIcons[category.id]}</span>
                  <div className="text-left">
                    <span className="text-sm font-medium text-surface-800">
                      {category.name}
                    </span>
                    {enabledCount > 0 && (
                      <span className="ml-2 text-xs px-1.5 py-0.5 bg-accent/10 text-accent rounded-full">
                        {enabledCount} active
                      </span>
                    )}
                  </div>
                </div>
                {isExpanded ? (
                  <ChevronUp className="w-4 h-4 text-surface-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-surface-400" />
                )}
              </button>

              {/* Effects List */}
              {isExpanded && (
                <div className="px-4 pb-4 space-y-3">
                  {effects.map(effect => {
                    const toggle = effectToggles[effect.key];
                    return (
                      <div
                        key={effect.key}
                        className={`rounded-xl p-3 transition-all ${
                          toggle?.enabled
                            ? 'bg-accent/5 border border-accent/20'
                            : 'bg-surface-50 border border-transparent'
                        }`}
                      >
                        {/* Effect Header */}
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <label className="relative inline-flex items-center cursor-pointer">
                              <input
                                type="checkbox"
                                checked={toggle?.enabled ?? false}
                                onChange={(e) => handleToggleChange(effect.key, 'enabled', e.target.checked)}
                                className="sr-only peer"
                              />
                              <div className="w-9 h-5 bg-surface-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-accent/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-surface-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-accent"></div>
                            </label>
                            <div>
                              <span className="text-sm font-medium text-surface-800">
                                {effect.name}
                              </span>
                            </div>
                          </div>
                          {toggle?.enabled && (
                            <span className="text-xs font-medium text-accent">
                              {Math.round((toggle?.intensity ?? 0.5) * 100)}%
                            </span>
                          )}
                        </div>

                        {/* Description */}
                        <p className="text-xs text-surface-500 mb-2 ml-11">
                          {effect.description}
                        </p>

                        {/* Intensity Slider (only when enabled) */}
                        {toggle?.enabled && (
                          <div className="ml-11">
                            <input
                              type="range"
                              min="0"
                              max="100"
                              value={Math.round((toggle?.intensity ?? 0.5) * 100)}
                              onChange={(e) => handleToggleChange(effect.key, 'intensity', parseInt(e.target.value) / 100)}
                              className="w-full h-1.5 bg-surface-200 rounded-lg appearance-none cursor-pointer accent-accent"
                            />
                            <div className="flex justify-between text-[10px] text-surface-400 mt-1">
                              <span>Subtle</span>
                              <span>Intense</span>
                            </div>
                            {effect.supportsTriggerSource && (
                              <div>
                                <div className="text-[10px] text-surface-500 mt-2 mb-0.5">Reacts to</div>
                                <TriggerSourceSelect
                                  value={(toggle?.trigger_source ?? (effect.key === 'glitch' ? 'onsets' : 'beats')) as TriggerSource}
                                  options={effect.key === 'glitch' ? GLITCH_TRIGGER_SOURCE_OPTIONS : TRIGGER_SOURCE_OPTIONS}
                                  onChange={(source) => handleToggleChange(effect.key, 'trigger_source', source)}
                                />
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Active Effects Summary */}
      <div className="text-xs text-surface-500 text-center">
        {Object.values(effectToggles).filter(t => t?.enabled).length} effects active
      </div>
    </div>
  );
}
