"""
Video editor using MoviePy.
Handles trimming, scaling, and format conversion.
"""

from pathlib import Path

from loguru import logger
from moviepy import VideoFileClip, AudioFileClip

from config.settings import get_settings


class VideoEditor:
    """Edit and transform video clips."""

    def __init__(self):
        self.settings = get_settings()

    def get_video_duration(self, video_path: Path) -> float:
        """Get duration of a video file in seconds."""
        with VideoFileClip(str(video_path)) as clip:
            return clip.duration

    def trim_video(
        self,
        input_path: Path,
        output_path: Path,
        start_time: float = 0,
        duration: float | None = None,
        end_time: float | None = None,
    ) -> Path:
        """
        Trim video to specified duration.

        Args:
            input_path: Source video path
            output_path: Output video path
            start_time: Start time in seconds
            duration: Duration in seconds (alternative to end_time)
            end_time: End time in seconds (alternative to duration)

        Returns:
            Path to trimmed video
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with VideoFileClip(str(input_path)) as clip:
            if end_time is not None:
                trimmed = clip.subclipped(start_time, end_time)
            elif duration is not None:
                end = min(start_time + duration, clip.duration)
                trimmed = clip.subclipped(start_time, end)
            else:
                trimmed = clip

            logger.info(f"Trimming video: {start_time}s to {trimmed.duration}s")
            trimmed.write_videofile(
                str(output_path),
                codec="libx264",
                audio_codec="aac",
                logger=None,
            )

        return output_path

    def scale_to_vertical(
        self,
        input_path: Path,
        output_path: Path,
        width: int | None = None,
        height: int | None = None,
    ) -> Path:
        """
        Scale and crop video to vertical 9:16 format.

        Args:
            input_path: Source video path
            output_path: Output video path
            width: Target width (defaults to config)
            height: Target height (defaults to config)

        Returns:
            Path to scaled video
        """
        width = width or self.settings.video.width
        height = height or self.settings.video.height

        input_path = Path(input_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with VideoFileClip(str(input_path)) as clip:
            # Calculate crop dimensions to maintain aspect ratio
            target_ratio = width / height
            source_ratio = clip.w / clip.h

            if source_ratio > target_ratio:
                # Source is wider - crop sides
                new_width = int(clip.h * target_ratio)
                x_center = clip.w / 2
                cropped = clip.cropped(
                    x1=x_center - new_width / 2,
                    x2=x_center + new_width / 2,
                )
            else:
                # Source is taller - crop top/bottom
                new_height = int(clip.w / target_ratio)
                y_center = clip.h / 2
                cropped = clip.cropped(
                    y1=y_center - new_height / 2,
                    y2=y_center + new_height / 2,
                )

            # Resize to target dimensions
            scaled = cropped.resized((width, height))

            logger.info(f"Scaling video to {width}x{height}")
            scaled.write_videofile(
                str(output_path),
                codec="libx264",
                audio_codec="aac",
                fps=self.settings.video.fps,
                logger=None,
            )

        return output_path

    def prepare_background(
        self,
        input_path: Path,
        output_path: Path,
        duration: float,
        loop: bool = True,
    ) -> Path:
        """
        Prepare background video for final assembly.

        Trims/loops video to match target duration and scales to vertical format.

        Args:
            input_path: Source video path
            output_path: Output video path
            duration: Target duration in seconds
            loop: Whether to loop if source is shorter

        Returns:
            Path to prepared video
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with VideoFileClip(str(input_path)) as clip:
            # Handle duration
            if clip.duration >= duration:
                # Trim to duration
                prepared = clip.subclipped(0, duration)
            elif loop:
                # Loop to reach duration
                loops_needed = int(duration / clip.duration) + 1
                prepared = clip.looped(loops_needed).subclipped(0, duration)
            else:
                prepared = clip

            # Scale to vertical
            target_ratio = self.settings.video.width / self.settings.video.height
            source_ratio = prepared.w / prepared.h

            if source_ratio > target_ratio:
                new_width = int(prepared.h * target_ratio)
                x_center = prepared.w / 2
                prepared = prepared.cropped(
                    x1=x_center - new_width / 2,
                    x2=x_center + new_width / 2,
                )
            else:
                new_height = int(prepared.w / target_ratio)
                y_center = prepared.h / 2
                prepared = prepared.cropped(
                    y1=y_center - new_height / 2,
                    y2=y_center + new_height / 2,
                )

            prepared = prepared.resized(
                (self.settings.video.width, self.settings.video.height)
            )

            # Remove audio (will be replaced with TTS)
            prepared = prepared.without_audio()

            logger.info(
                f"Prepared background: {prepared.duration:.1f}s, "
                f"{self.settings.video.width}x{self.settings.video.height}"
            )
            prepared.write_videofile(
                str(output_path),
                codec="libx264",
                fps=self.settings.video.fps,
                logger=None,
            )

        return output_path

    def add_audio(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
    ) -> Path:
        """
        Add audio track to video.

        Args:
            video_path: Video file path
            audio_path: Audio file path
            output_path: Output file path

        Returns:
            Path to video with audio
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with VideoFileClip(str(video_path)) as video:
            with AudioFileClip(str(audio_path)) as audio:
                final = video.with_audio(audio)

                logger.info(f"Adding audio to video")
                final.write_videofile(
                    str(output_path),
                    codec="libx264",
                    audio_codec="aac",
                    fps=self.settings.video.fps,
                    logger=None,
                )

        return output_path
