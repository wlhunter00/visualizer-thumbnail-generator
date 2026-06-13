"""
Export history — store successful export settings for few-shot Auto-Suggest.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

HISTORY_PATH = Path(__file__).parent / "data" / "export_history.jsonl"
MAX_ENTRIES = 200


@dataclass
class ExportHistoryEntry:
    id: str
    exported_at: str
    effect_toggles: Dict[str, Any]
    audio_metrics: Dict[str, float]
    image_summary: Dict[str, Any]
    aspect_ratio: str
    clip_duration_sec: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "exported_at": self.exported_at,
            "effect_toggles": self.effect_toggles,
            "audio_metrics": self.audio_metrics,
            "image_summary": self.image_summary,
            "aspect_ratio": self.aspect_ratio,
            "clip_duration_sec": self.clip_duration_sec,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExportHistoryEntry":
        return cls(
            id=data["id"],
            exported_at=data["exported_at"],
            effect_toggles=data["effect_toggles"],
            audio_metrics=data["audio_metrics"],
            image_summary=data["image_summary"],
            aspect_ratio=data.get("aspect_ratio", "9:16"),
            clip_duration_sec=float(data.get("clip_duration_sec", 30.0)),
        )


def _ensure_data_dir() -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_export_history(limit: int = MAX_ENTRIES) -> List[ExportHistoryEntry]:
    if not HISTORY_PATH.exists():
        return []
    entries: List[ExportHistoryEntry] = []
    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(ExportHistoryEntry.from_dict(json.loads(line)))
            except (json.JSONDecodeError, KeyError):
                continue
    return entries[-limit:]


def append_export_history(entry: ExportHistoryEntry) -> None:
    _ensure_data_dir()
    entries = load_export_history(MAX_ENTRIES - 1)
    entries.append(entry)
    if len(entries) > MAX_ENTRIES:
        entries = entries[-MAX_ENTRIES:]
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e.to_dict()) + "\n")


def build_history_entry(
    effect_toggles: Dict[str, Any],
    audio_metrics: Dict[str, float],
    image_analysis_dict: Optional[Dict[str, Any]],
    aspect_ratio: str,
    clip_duration_sec: float,
) -> ExportHistoryEntry:
    bounds = (image_analysis_dict or {}).get("bounds", {})
    w = float(bounds.get("w", 0.5))
    h = float(bounds.get("h", 0.5))
    colors = (image_analysis_dict or {}).get("colors", [])[:5]

    return ExportHistoryEntry(
        id=str(uuid.uuid4()),
        exported_at=datetime.now(timezone.utc).isoformat(),
        effect_toggles=effect_toggles,
        audio_metrics=audio_metrics,
        image_summary={
            "subject": (image_analysis_dict or {}).get("subject", "subject"),
            "mood": (image_analysis_dict or {}).get("mood", "neutral"),
            "colors": colors,
            "bounds": {
                "x": bounds.get("x", 0.25),
                "y": bounds.get("y", 0.25),
                "w": w,
                "h": h,
            },
            "subject_area": w * h,
        },
        aspect_ratio=aspect_ratio,
        clip_duration_sec=clip_duration_sec,
    )


def _similarity_score(
    entry: ExportHistoryEntry,
    audio_metrics: Dict[str, float],
    image_analysis: Any,
    aspect_ratio: Optional[str] = None,
) -> float:
    """Lower is more similar."""
    em = entry.audio_metrics
    score = 0.0

    for key, weight in (
        ("average_bass", 3.0),
        ("average_mid", 3.0),
        ("average_high", 3.0),
        ("onset_density", 1.5),
        ("average_energy", 1.5),
        ("dynamic_range", 1.5),
    ):
        a = float(audio_metrics.get(key, 0.5))
        b = float(em.get(key, 0.5))
        if key == "onset_density":
            a = min(a, 20) / 20.0
            b = min(b, 20) / 20.0
        score += weight * abs(a - b)

    if entry.image_summary.get("mood") == getattr(image_analysis, "mood", ""):
        score -= 1.0

    subject_area = image_analysis.bounds.w * image_analysis.bounds.h
    entry_area = float(entry.image_summary.get("subject_area", 0.25))
    score += 0.5 * abs(subject_area - entry_area)

    if aspect_ratio and entry.aspect_ratio == aspect_ratio:
        score -= 0.5

    return score


def find_similar_exports(
    audio_metrics: Dict[str, float],
    image_analysis: Any,
    k: int = 3,
    aspect_ratio: Optional[str] = None,
) -> List[ExportHistoryEntry]:
    entries = load_export_history()
    if not entries:
        return []

    scored = [
        (_similarity_score(e, audio_metrics, image_analysis, aspect_ratio), e)
        for e in entries
    ]
    scored.sort(key=lambda x: x[0])
    return [e for _, e in scored[:k]]


def build_few_shot_examples_section(
    examples: List[ExportHistoryEntry],
) -> str:
    if not examples:
        return ""

    lines = [
        "EXAMPLES OF SUCCESSFUL EXPORTS (similar audio + image — prefer patterns like these):",
        "Use these as inspiration for lever choices; adapt to the current track, don't copy blindly.",
        "",
    ]
    for i, ex in enumerate(examples, 1):
        im = ex.image_summary
        am = ex.audio_metrics
        lines.append(
            f"Example {i}: mood={im.get('mood')}, subject={im.get('subject')}, "
            f"bass={am.get('average_bass', 0):.2f}, mid={am.get('average_mid', 0):.2f}, "
            f"high={am.get('average_high', 0):.2f}, onset_density={am.get('onset_density', 0):.1f}"
        )
        lines.append(json.dumps(ex.effect_toggles, indent=2))
        lines.append("")

    return "\n".join(lines)
