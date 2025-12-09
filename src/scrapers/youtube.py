"""
YouTube video downloader using yt-dlp.
Fetches Creative Commons Minecraft gameplay videos.
"""

import json
import random
from datetime import datetime
from pathlib import Path

import yt_dlp
from loguru import logger

from config.settings import get_settings
from src.models import VideoMetadata


# Default search queries for finding gameplay videos
DEFAULT_SEARCHES = [
    "minecraft parkour gameplay no commentary creative commons",
    "minecraft satisfying gameplay royalty free",
    "minecraft building timelapse no music",
    "minecraft survival gameplay no commentary",
    "minecraft hypixel bedwars gameplay",
]


class YouTubeDownloader:
    """Download Creative Commons gameplay videos from YouTube."""

    def __init__(self):
        self.settings = get_settings()
        self._downloaded_ids: set[str] = set()
        self._load_downloaded()

    def _load_downloaded(self) -> None:
        """Load list of already downloaded video IDs."""
        index_path = self.settings.videos_dir / "index.json"
        if index_path.exists():
            with open(index_path, "r") as f:
                data = json.load(f)
                self._downloaded_ids = set(data.get("downloaded_ids", []))
        logger.debug(f"Loaded {len(self._downloaded_ids)} downloaded video IDs")

    def _save_downloaded(self) -> None:
        """Save list of downloaded video IDs."""
        index_path = self.settings.videos_dir / "index.json"
        self.settings.videos_dir.mkdir(parents=True, exist_ok=True)
        with open(index_path, "w") as f:
            json.dump({"downloaded_ids": list(self._downloaded_ids)}, f)

    def search_videos(
        self,
        query: str | None = None,
        max_results: int = 10,
        min_duration: int = 60,
        max_duration: int = 600,
    ) -> list[dict]:
        """
        Search YouTube for videos matching criteria.

        Args:
            query: Search query (uses random default if None)
            max_results: Maximum number of results
            min_duration: Minimum video duration in seconds
            max_duration: Maximum video duration in seconds

        Returns:
            List of video info dictionaries
        """
        if query is None:
            query = random.choice(DEFAULT_SEARCHES)

        logger.info(f"Searching YouTube: {query}")

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "default_search": "ytsearch" + str(max_results * 2),
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(query, download=False)

        videos = []
        if result and "entries" in result:
            for entry in result["entries"]:
                if not entry:
                    continue
                # Skip already downloaded
                if entry.get("id") in self._downloaded_ids:
                    continue
                # Filter by duration if available
                duration = entry.get("duration", 0) or 0
                if duration < min_duration or duration > max_duration:
                    continue
                videos.append(entry)
                if len(videos) >= max_results:
                    break

        logger.info(f"Found {len(videos)} matching videos")
        return videos

    def download_video(
        self,
        url: str,
        output_name: str | None = None,
    ) -> VideoMetadata | None:
        """
        Download a video from YouTube.

        Args:
            url: YouTube video URL or ID
            output_name: Optional output filename (without extension)

        Returns:
            VideoMetadata if successful, None otherwise
        """
        self.settings.videos_dir.mkdir(parents=True, exist_ok=True)

        # Normalize URL
        if not url.startswith("http"):
            url = f"https://www.youtube.com/watch?v={url}"

        ydl_opts = {
            "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "outtmpl": str(self.settings.videos_dir / "%(id)s.%(ext)s"),
            "quiet": False,
            "no_warnings": False,
            "merge_output_format": "mp4",
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Downloading: {url}")
                info = ydl.extract_info(url, download=True)

                if not info:
                    logger.error("Failed to extract video info")
                    return None

                video_id = info.get("id", "unknown")
                ext = info.get("ext", "mp4")
                local_path = self.settings.videos_dir / f"{video_id}.{ext}"

                # Get video dimensions
                width = info.get("width", 1920)
                height = info.get("height", 1080)

                metadata = VideoMetadata(
                    id=video_id,
                    title=info.get("title", "Unknown"),
                    source_url=info.get("webpage_url", url),
                    local_path=local_path,
                    duration_seconds=info.get("duration", 0),
                    width=width,
                    height=height,
                    license=info.get("license", "unknown"),
                    channel=info.get("channel", info.get("uploader", "")),
                    downloaded_at=datetime.now(),
                )

                # Save metadata
                meta_path = self.settings.videos_dir / f"{video_id}.json"
                with open(meta_path, "w") as f:
                    json.dump(metadata.model_dump(), f, indent=2, default=str)

                # Track as downloaded
                self._downloaded_ids.add(video_id)
                self._save_downloaded()

                logger.info(f"Downloaded: {metadata.title} ({metadata.duration_seconds}s)")
                return metadata

        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return None

    def download_random(
        self,
        count: int = 1,
        query: str | None = None,
    ) -> list[VideoMetadata]:
        """
        Download random videos matching search criteria.

        Args:
            count: Number of videos to download
            query: Optional search query

        Returns:
            List of downloaded VideoMetadata
        """
        videos = self.search_videos(query=query, max_results=count * 2)
        downloaded = []

        for video in videos[:count]:
            url = video.get("url") or video.get("id")
            if url:
                metadata = self.download_video(url)
                if metadata:
                    downloaded.append(metadata)

        return downloaded

    def get_random_video(self) -> VideoMetadata | None:
        """Get a random downloaded video for use."""
        video_files = list(self.settings.videos_dir.glob("*.mp4"))
        if not video_files:
            logger.warning("No downloaded videos available")
            return None

        video_path = random.choice(video_files)
        meta_path = video_path.with_suffix(".json")

        if meta_path.exists():
            with open(meta_path, "r") as f:
                data = json.load(f)
            return VideoMetadata(**data)

        # Create basic metadata if JSON doesn't exist
        return VideoMetadata(
            id=video_path.stem,
            title=video_path.stem,
            source_url="",
            local_path=video_path,
            duration_seconds=0,  # Will be determined during editing
            width=1920,
            height=1080,
        )

    def list_videos(self) -> list[VideoMetadata]:
        """List all downloaded videos."""
        videos = []
        for meta_path in self.settings.videos_dir.glob("*.json"):
            if meta_path.name == "index.json":
                continue
            with open(meta_path, "r") as f:
                data = json.load(f)
            videos.append(VideoMetadata(**data))
        return videos
