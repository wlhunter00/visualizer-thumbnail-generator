"""
User-saved effect presets — persisted to effect_presets.json (repo-tracked).
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from effect_engine import toggles_from_dict, toggles_to_dict

PRESETS_PATH = Path(__file__).parent / "effect_presets.json"
MAX_PRESETS = 50
_preset_lock = threading.Lock()


@dataclass
class EffectPreset:
    id: str
    name: str
    created_at: str
    updated_at: str
    effect_toggles: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "effect_toggles": self.effect_toggles,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EffectPreset":
        return cls(
            id=data["id"],
            name=data["name"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            effect_toggles=data["effect_toggles"],
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_name(name: str) -> str:
    return name.strip()


def validate_effect_toggles(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Round-trip toggles through effect_engine for consistent shape."""
    return toggles_to_dict(toggles_from_dict(raw))


def _read_presets_unlocked() -> List[EffectPreset]:
    if not PRESETS_PATH.exists():
        return []
    try:
        with open(PRESETS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    presets: List[EffectPreset] = []
    for item in data:
        try:
            presets.append(EffectPreset.from_dict(item))
        except (KeyError, TypeError):
            continue
    return presets


def _write_presets_unlocked(presets: List[EffectPreset]) -> None:
    with open(PRESETS_PATH, "w", encoding="utf-8") as f:
        json.dump([p.to_dict() for p in presets], f, indent=2)
        f.write("\n")


def load_presets() -> List[EffectPreset]:
    with _preset_lock:
        presets = _read_presets_unlocked()
    presets.sort(key=lambda p: p.updated_at, reverse=True)
    return presets


def get_preset(preset_id: str) -> Optional[EffectPreset]:
    with _preset_lock:
        for preset in _read_presets_unlocked():
            if preset.id == preset_id:
                return preset
    return None


def save_preset(name: str, effect_toggles: Dict[str, Any]) -> EffectPreset:
    clean_name = _normalize_name(name)
    if not clean_name:
        raise ValueError("Preset name cannot be empty")

    validated = validate_effect_toggles(effect_toggles)
    now = _utc_now()

    with _preset_lock:
        presets = _read_presets_unlocked()

        for i, preset in enumerate(presets):
            if preset.name.lower() == clean_name.lower():
                updated = EffectPreset(
                    id=preset.id,
                    name=clean_name,
                    created_at=preset.created_at,
                    updated_at=now,
                    effect_toggles=validated,
                )
                presets[i] = updated
                _write_presets_unlocked(presets)
                return updated

        if len(presets) >= MAX_PRESETS:
            raise ValueError(f"Maximum of {MAX_PRESETS} presets reached")

        created = EffectPreset(
            id=str(uuid.uuid4()),
            name=clean_name,
            created_at=now,
            updated_at=now,
            effect_toggles=validated,
        )
        presets.append(created)
        _write_presets_unlocked(presets)
        return created


def update_preset(
    preset_id: str,
    *,
    name: Optional[str] = None,
    effect_toggles: Optional[Dict[str, Any]] = None,
) -> Optional[EffectPreset]:
    with _preset_lock:
        presets = _read_presets_unlocked()
        for i, preset in enumerate(presets):
            if preset.id != preset_id:
                continue

            new_name = _normalize_name(name) if name is not None else preset.name
            if not new_name:
                raise ValueError("Preset name cannot be empty")

            new_toggles = (
                validate_effect_toggles(effect_toggles)
                if effect_toggles is not None
                else preset.effect_toggles
            )

            updated = EffectPreset(
                id=preset.id,
                name=new_name,
                created_at=preset.created_at,
                updated_at=_utc_now(),
                effect_toggles=new_toggles,
            )
            presets[i] = updated
            _write_presets_unlocked(presets)
            return updated

    return None


def delete_preset(preset_id: str) -> bool:
    with _preset_lock:
        presets = _read_presets_unlocked()
        next_presets = [p for p in presets if p.id != preset_id]
        if len(next_presets) == len(presets):
            return False
        _write_presets_unlocked(next_presets)
        return True
