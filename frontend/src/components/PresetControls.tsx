import { useState, useEffect, useCallback, useRef } from 'react';
import { EffectToggles, SavedEffectPreset } from '../types';
import {
  getEffectPresets,
  createEffectPreset,
  updateEffectPreset,
  deleteEffectPreset,
} from '../api';
import { Bookmark, Save, RefreshCw, Trash2, Loader2, X } from 'lucide-react';

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
  const [isNaming, setIsNaming] = useState(false);
  const [presetName, setPresetName] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const nameInputRef = useRef<HTMLInputElement>(null);

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

  useEffect(() => {
    if (isNaming) {
      nameInputRef.current?.focus();
    }
  }, [isNaming]);

  const handleSelect = (presetId: string) => {
    setSelectedId(presetId);
    setConfirmDelete(false);
    if (!presetId) return;
    const preset = presets.find(p => p.id === presetId);
    if (preset) {
      onLoad(preset.effect_toggles);
    }
  };

  const openSaveForm = () => {
    setError(null);
    setConfirmDelete(false);
    setPresetName('');
    setIsNaming(true);
  };

  const cancelSaveForm = () => {
    setIsNaming(false);
    setPresetName('');
  };

  const handleSave = async () => {
    const name = presetName.trim();
    if (!name) {
      setError('Enter a preset name');
      return;
    }

    try {
      setIsSaving(true);
      setError(null);
      const saved = await createEffectPreset(name, effectToggles);
      await loadPresets();
      setSelectedId(saved.id);
      setIsNaming(false);
      setPresetName('');
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

    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }

    try {
      setIsSaving(true);
      setError(null);
      await deleteEffectPreset(selectedId);
      setSelectedId('');
      setConfirmDelete(false);
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

          {isNaming ? (
            <div className="space-y-2">
              <input
                ref={nameInputRef}
                type="text"
                value={presetName}
                onChange={(e) => setPresetName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSave();
                  if (e.key === 'Escape') cancelSaveForm();
                }}
                placeholder="Preset name"
                className="w-full px-3 py-2 text-sm text-surface-700 bg-white border border-surface-200 rounded-lg focus:outline-none focus:border-violet-400"
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={isSaving}
                  className="flex-1 py-2 px-3 text-xs font-medium text-white bg-violet-600 border border-violet-600 rounded-lg hover:bg-violet-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
                >
                  {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                  Save preset
                </button>
                <button
                  type="button"
                  onClick={cancelSaveForm}
                  disabled={isSaving}
                  className="py-2 px-3 text-xs font-medium text-surface-600 bg-surface-50 border border-surface-200 rounded-lg hover:bg-surface-100 transition-colors disabled:opacity-50"
                  aria-label="Cancel"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ) : (
            <div className="flex gap-2">
              <button
                type="button"
                onClick={openSaveForm}
                disabled={isSaving}
                className="flex-1 py-2 px-3 text-xs font-medium text-violet-700 bg-violet-50 border border-violet-200 rounded-lg hover:bg-violet-100 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
              >
                <Save className="w-3.5 h-3.5" />
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
                    className={`py-2 px-3 text-xs font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center ${
                      confirmDelete
                        ? 'text-white bg-red-600 border border-red-600 hover:bg-red-700'
                        : 'text-red-600 bg-red-50 border border-red-200 hover:bg-red-100'
                    }`}
                    aria-label={confirmDelete ? 'Confirm delete preset' : 'Delete preset'}
                    title={confirmDelete ? 'Click again to confirm' : 'Delete preset'}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </>
              )}
            </div>
          )}

          {confirmDelete && (
            <p className="text-xs text-red-600">Click delete again to confirm.</p>
          )}
        </>
      )}

      {error && (
        <p className="text-xs text-red-600">{error}</p>
      )}
    </div>
  );
}
