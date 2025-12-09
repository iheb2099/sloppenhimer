"""
Data models for Reddit stories.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class StoryStatus(str, Enum):
    """Processing status for a story."""

    SCRAPED = "scraped"
    SIMPLIFIED = "simplified"
    TTS_GENERATED = "tts_generated"
    TRANSCRIBED = "transcribed"
    ASSEMBLED = "assembled"
    FAILED = "failed"


class RedditStory(BaseModel):
    """Raw Reddit story data."""

    id: str = Field(description="Reddit post ID")
    subreddit: str = Field(description="Source subreddit")
    title: str = Field(description="Post title")
    body: str = Field(description="Post body/selftext")
    author: str = Field(description="Reddit username")
    score: int = Field(description="Post score/upvotes")
    url: str = Field(description="Reddit post URL")
    created_utc: datetime = Field(description="Post creation time")
    num_comments: int = Field(default=0, description="Number of comments")

    @property
    def word_count(self) -> int:
        return len(self.body.split())

    @property
    def char_count(self) -> int:
        return len(self.body)


class ProcessedStory(BaseModel):
    """Story after LLM processing."""

    original: RedditStory = Field(description="Original Reddit story")
    simplified_text: str = Field(description="LLM-processed text for TTS")
    status: StoryStatus = Field(default=StoryStatus.SIMPLIFIED)
    processed_at: datetime = Field(default_factory=datetime.now)
    audio_path: Path | None = Field(default=None, description="Generated TTS audio")
    transcript_path: Path | None = Field(default=None, description="Whisper transcript")
    output_video_path: Path | None = Field(default=None, description="Final video")
    error_message: str | None = Field(default=None, description="Error if failed")

    @property
    def word_count(self) -> int:
        return len(self.simplified_text.split())

    @property
    def estimated_duration_seconds(self) -> float:
        """Estimate audio duration at ~150 words per minute."""
        return (self.word_count / 150) * 60

    model_config = {"arbitrary_types_allowed": True}
