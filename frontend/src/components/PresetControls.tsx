import { useState, useEffect, useCallback } from 'react';
import { EffectToggles, SavedEffectPreset } from '../types';
import {
  getEffectPresets,
  createEffectPreset,
  updateEffectPreset,
  deleteEffectPreset,
} from '../api';
import { Bookmark, Save, RefreshCw, Trash2, Loader2 } from 'lucide-react';

interface PresetControlsProps {
  effectToggles: EffectToggles;
  onLoad: (toggles: EffectToggles) => void;
}

export default function PresetControls({ effectToggles, onLoad }: PresetControlsProps) {
  const [presets, setPresets] = useState<SavedEffectPreset[]>([]);
  const [selectedId, setSelectedId] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPresets = useCallback(async () => {
    try {
      setError(null);
      const result = await getEffectPresets();
      setPresets(result.presets);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load presets');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPresets();
  }, [loadPresets]);

  const handleSelect = (presetId: string) => {
    setSelectedId(presetId);
    if (!presetId) return;
    const preset = presets.find(p => p.id === presetId);
    if (preset) {
      onLoad(preset.effect_toggles);
    }
  };

  const handleSave = async () => {
    const name = window.prompt('Preset name');
    if (!name?.trim()) return;

    try {
      setIsSaving(true);
      setError(null);
      const saved = await createEffectPreset(name.trim(), effectToggles);
      await loadPresets();
      setSelectedId(saved.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save preset');
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdate = async () => {
    if (!selectedId) return;

    try {
      setIsSaving(true);
      setError(null);
      await updateEffectPreset(selectedId, { effect_toggles: effectToggles });
      await loadPresets();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update preset');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedId) return;
    const preset = presets.find(p => p.id === selectedId);
    if (!preset) return;
    if (!window.confirm(`Delete preset "${preset.name}"?`)) return;

    try {
      setIsSaving(true);
      setError(null);
      await deleteEffectPreset(selectedId);
      setSelectedId('');
      await loadPresets();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete preset');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-surface-200 p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Bookmark className="w-4 h-4 text-violet-600" />
        <span className="text-sm font-medium text-surface-700">Saved Presets</span>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center gap-2 py-2 text-sm text-surface-500">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading presets...
        </div>
      ) : (
        <>
          <select
            value={selectedId}
            onChange={(e) => handleSelect(e.target.value)}
            className="w-full px-3 py-2 text-sm text-surface-700 bg-white border border-surface-200 rounded-lg focus:outline-none focus:border-violet-400"
          >
            <option value="">
              {presets.length === 0 ? 'No saved presets yet' : 'Select a preset...'}
            </option>
            {presets.map(preset => (
              <option key={preset.id} value={preset.id}>
                {preset.name}
              </option>
            ))}
          </select>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              className="flex-1 py-2 px-3 text-xs font-medium text-violet-700 bg-violet-50 border border-violet-200 rounded-lg hover:bg-violet-100 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
            >
              {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
              Save
            </button>
            {selectedId && (
              <>
                <button
                  type="button"
                  onClick={handleUpdate}
                  disabled={isSaving}
                  className="flex-1 py-2 px-3 text-xs font-medium text-surface-700 bg-surface-50 border border-surface-200 rounded-lg hover:bg-surface-100 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Update
                </button>
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={isSaving}
                  className="py-2 px-3 text-xs font-medium text-red-600 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors disabled:opacity-50 flex items-center justify-center"
                  aria-label="Delete preset"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </>
            )}
          </div>
        </>
      )}

      {error && (
        <p className="text-xs text-red-600">{error}</p>
      )}
    </div>
  );
}
