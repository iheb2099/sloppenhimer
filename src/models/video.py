"""
Data models for video metadata.
"""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class VideoMetadata(BaseModel):
    """Metadata for downloaded gameplay videos."""

    id: str = Field(description="YouTube video ID")
    title: str = Field(description="Video title")
    source_url: str = Field(description="YouTube URL")
    local_path: Path = Field(description="Local file path")
    duration_seconds: float = Field(description="Video duration")
    width: int = Field(description="Video width in pixels")
    height: int = Field(description="Video height in pixels")
    license: str = Field(default="unknown", description="Video license type")
    channel: str = Field(default="", description="YouTube channel name")
    downloaded_at: datetime = Field(default_factory=datetime.now)
    used_count: int = Field(default=0, description="Times used in output")

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height if self.height > 0 else 0

    @property
    def is_vertical(self) -> bool:
        return self.height > self.width

    model_config = {"arbitrary_types_allowed": True}


class VideoSegment(BaseModel):
    """A segment of video to use in final output."""

    source: VideoMetadata = Field(description="Source video")
    start_time: float = Field(description="Start time in seconds")
    end_time: float = Field(description="End time in seconds")

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time
