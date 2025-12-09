"""
Configuration settings for Project Sloppenhimer.
Uses Pydantic Settings for type-safe environment variable handling.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedditSettings(BaseSettings):
    """Reddit API configuration."""

    model_config = SettingsConfigDict(env_prefix="REDDIT_")

    client_id: str = Field(default="", description="Reddit API client ID")
    client_secret: str = Field(default="", description="Reddit API client secret")
    user_agent: str = Field(
        default="sloppenhimer:v1.0 (by /u/sloppenhimer)",
        description="Reddit API user agent",
    )
    subreddits: list[str] = Field(
        default=["AITA", "tifu", "AmItheAsshole", "relationships", "confession"],
        description="Subreddits to scrape",
    )
    posts_per_subreddit: int = Field(default=25, description="Posts to fetch per sub")
    min_score: int = Field(default=100, description="Minimum post score")
    min_length: int = Field(default=500, description="Minimum story length in chars")
    max_length: int = Field(default=5000, description="Maximum story length in chars")


class OllamaSettings(BaseSettings):
    """Ollama LLM configuration."""

    model_config = SettingsConfigDict(env_prefix="OLLAMA_")

    host: str = Field(default="http://localhost:11434", description="Ollama API host")
    model: str = Field(default="llama3.2:3b", description="Model to use")
    timeout: int = Field(default=120, description="Request timeout in seconds")


class TTSSettings(BaseSettings):
    """Text-to-Speech configuration."""

    model_config = SettingsConfigDict(env_prefix="")

    engine: Literal["edge-tts", "piper"] = Field(
        default="edge-tts",
        alias="TTS_ENGINE",
        description="TTS engine to use",
    )
    edge_voice: str = Field(
        default="en-US-ChristopherNeural",
        alias="EDGE_TTS_VOICE",
        description="Edge TTS voice",
    )
    piper_voice: str = Field(
        default="en_US-amy-medium",
        alias="PIPER_VOICE",
        description="Piper TTS voice model",
    )
    speech_rate: str = Field(
        default="+0%",
        alias="TTS_SPEECH_RATE",
        description="Speech rate adjustment",
    )


class VideoSettings(BaseSettings):
    """Video processing configuration."""

    model_config = SettingsConfigDict(env_prefix="")

    width: int = Field(
        default=1080,
        alias="OUTPUT_RESOLUTION_WIDTH",
        description="Output video width",
    )
    height: int = Field(
        default=1920,
        alias="OUTPUT_RESOLUTION_HEIGHT",
        description="Output video height (9:16 vertical)",
    )
    fps: int = Field(default=30, alias="VIDEO_FPS", description="Output FPS")
    codec: str = Field(default="libx264", description="Video codec")
    audio_codec: str = Field(default="aac", description="Audio codec")
    bitrate: str = Field(default="8M", description="Video bitrate")


class CaptionSettings(BaseSettings):
    """Caption/subtitle configuration."""

    model_config = SettingsConfigDict(env_prefix="CAPTION_")

    font: str = Field(default="Arial-Bold", description="Caption font")
    font_size: int = Field(default=60, description="Caption font size")
    color: str = Field(default="white", description="Default text color")
    highlight_color: str = Field(default="yellow", description="Active word color")
    stroke_color: str = Field(default="black", description="Text outline color")
    stroke_width: int = Field(default=3, description="Text outline width")
    position: str = Field(default="center", description="Caption position")
    words_per_group: int = Field(default=4, description="Words to show at once")


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Sub-configurations
    reddit: RedditSettings = Field(default_factory=RedditSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    tts: TTSSettings = Field(default_factory=TTSSettings)
    video: VideoSettings = Field(default_factory=VideoSettings)
    caption: CaptionSettings = Field(default_factory=CaptionSettings)

    # Paths
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent,
        description="Project root directory",
    )

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def videos_dir(self) -> Path:
        return self.data_dir / "videos"

    @property
    def stories_dir(self) -> Path:
        return self.data_dir / "stories"

    @property
    def audio_dir(self) -> Path:
        return self.data_dir / "audio"

    @property
    def output_dir(self) -> Path:
        return self.data_dir / "output"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def assets_dir(self) -> Path:
        return self.project_root / "assets"

    @property
    def prompts_dir(self) -> Path:
        return self.project_root / "config" / "prompts"


# Singleton instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create the settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
