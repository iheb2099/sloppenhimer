"""
Path utilities for Project Sloppenhimer.
"""

import json
from pathlib import Path
from typing import Any

from config.settings import get_settings


def ensure_dirs() -> None:
    """Create all required data directories."""
    settings = get_settings()
    dirs = [
        settings.videos_dir,
        settings.stories_dir,
        settings.audio_dir,
        settings.output_dir,
        settings.cache_dir,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def get_story_path(story_id: str) -> Path:
    """Get path for story JSON file."""
    settings = get_settings()
    return settings.stories_dir / f"{story_id}.json"


def get_audio_path(story_id: str) -> Path:
    """Get path for TTS audio file."""
    settings = get_settings()
    return settings.audio_dir / f"{story_id}.wav"


def get_transcript_path(story_id: str) -> Path:
    """Get path for transcript JSON file."""
    settings = get_settings()
    return settings.audio_dir / f"{story_id}_transcript.json"


def get_output_path(story_id: str) -> Path:
    """Get path for final output video."""
    settings = get_settings()
    return settings.output_dir / f"{story_id}.mp4"


def save_json(path: Path, data: Any) -> None:
    """Save data as JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def load_json(path: Path) -> Any:
    """Load data from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
