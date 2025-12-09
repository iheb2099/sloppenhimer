"""
Final video assembler.
Combines gameplay video, TTS audio, and captions into final output.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from moviepy import VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip

from config.settings import get_settings
from src.models import ProcessedStory, Transcript, StoryStatus, VideoMetadata
from src.video.editor import VideoEditor
from src.video.captions import KaraokeCaptions


class VideoAssembler:
    """Assemble final video from components."""

    def __init__(self):
        self.settings = get_settings()
        self.editor = VideoEditor()
        self.captions = KaraokeCaptions()

    def assemble(
        self,
        story: ProcessedStory,
        background_video: Path | VideoMetadata,
        audio_path: Path,
        transcript: Transcript,
        output_path: Path | None = None,
    ) -> Path:
        """
        Assemble final video from all components.

        Args:
            story: The processed story
            background_video: Path to background video or VideoMetadata
            audio_path: Path to TTS audio
            transcript: Transcript with word timings
            output_path: Output video path (defaults to output_dir/story_id.mp4)

        Returns:
            Path to final video
        """
        # Resolve paths
        if isinstance(background_video, VideoMetadata):
            background_path = background_video.local_path
        else:
            background_path = Path(background_video)

        audio_path = Path(audio_path)

        if output_path is None:
            output_path = self.settings.output_dir / f"{story.original.id}.mp4"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Assembling video for story: {story.original.id}")

        # Get audio duration to match video
        with AudioFileClip(str(audio_path)) as audio:
            target_duration = audio.duration

        logger.info(f"Target duration: {target_duration:.1f}s")

        # Prepare background video (trim/loop, scale to vertical)
        cache_dir = self.settings.cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)

        prepared_bg_path = cache_dir / f"{story.original.id}_bg.mp4"
        self.editor.prepare_background(
            background_path,
            prepared_bg_path,
            duration=target_duration,
            loop=True,
        )

        # Load prepared background
        with VideoFileClip(str(prepared_bg_path)) as video:
            with AudioFileClip(str(audio_path)) as audio:
                # Add audio
                video_with_audio = video.with_audio(audio)

                # Generate caption clips
                video_size = (video.w, video.h)
                caption_clips = self.captions.generate_captions(transcript, video_size)

                # Composite everything
                final = CompositeVideoClip([video_with_audio] + caption_clips)

                # Write final video
                logger.info(f"Writing final video to {output_path}")
                final.write_videofile(
                    str(output_path),
                    codec=self.settings.video.codec,
                    audio_codec=self.settings.video.audio_codec,
                    fps=self.settings.video.fps,
                    bitrate=self.settings.video.bitrate,
                    logger=None,
                )

        # Cleanup temp file
        if prepared_bg_path.exists():
            prepared_bg_path.unlink()

        logger.info(f"Video assembled successfully: {output_path}")
        return output_path

    def quick_assemble(
        self,
        story: ProcessedStory,
        background_video: Path | VideoMetadata,
        audio_path: Path,
        transcript: Transcript,
        output_path: Path | None = None,
    ) -> Path:
        """
        Quick assembly without fancy captions (faster render).

        Uses SRT subtitles burned in with ffmpeg instead of per-word clips.
        """
        if isinstance(background_video, VideoMetadata):
            background_path = background_video.local_path
        else:
            background_path = Path(background_video)

        audio_path = Path(audio_path)

        if output_path is None:
            output_path = self.settings.output_dir / f"{story.original.id}.mp4"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Quick assembling video for story: {story.original.id}")

        with AudioFileClip(str(audio_path)) as audio:
            target_duration = audio.duration

        # Prepare background
        cache_dir = self.settings.cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)

        prepared_bg_path = cache_dir / f"{story.original.id}_bg.mp4"
        self.editor.prepare_background(
            background_path,
            prepared_bg_path,
            duration=target_duration,
            loop=True,
        )

        # Create simple centered captions (segment-based, not word-by-word)
        with VideoFileClip(str(prepared_bg_path)) as video:
            with AudioFileClip(str(audio_path)) as audio:
                video_with_audio = video.with_audio(audio)
                video_size = (video.w, video.h)

                # Create segment-based captions
                segments = transcript.get_segments(self.settings.caption.words_per_group)
                caption_clips = []

                for segment in segments:
                    text = segment.text
                    clip = TextClip(
                        text=text,
                        font_size=self.settings.caption.font_size,
                        color=self.settings.caption.color,
                        font=self.settings.caption.font,
                        stroke_color=self.settings.caption.stroke_color,
                        stroke_width=self.settings.caption.stroke_width,
                        method="caption",
                        size=(video_size[0] - 80, None),
                        text_align="center",
                    )
                    clip = (
                        clip
                        .with_position(("center", video_size[1] // 2))
                        .with_start(segment.start_time)
                        .with_end(segment.end_time)
                    )
                    caption_clips.append(clip)

                final = CompositeVideoClip([video_with_audio] + caption_clips)

                final.write_videofile(
                    str(output_path),
                    codec=self.settings.video.codec,
                    audio_codec=self.settings.video.audio_codec,
                    fps=self.settings.video.fps,
                    bitrate=self.settings.video.bitrate,
                    logger=None,
                )

        # Cleanup
        if prepared_bg_path.exists():
            prepared_bg_path.unlink()

        logger.info(f"Video assembled: {output_path}")
        return output_path


class Pipeline:
    """Full pipeline orchestrator."""

    def __init__(self):
        self.settings = get_settings()
        self.assembler = VideoAssembler()

        # Lazy imports to avoid circular dependencies
        self._llm = None
        self._tts = None
        self._transcriber = None
        self._youtube = None

    @property
    def llm(self):
        if self._llm is None:
            from src.processors import LLMProcessor
            self._llm = LLMProcessor()
        return self._llm

    @property
    def tts(self):
        if self._tts is None:
            from src.processors import TTSEngine
            self._tts = TTSEngine()
        return self._tts

    @property
    def transcriber(self):
        if self._transcriber is None:
            from src.processors import TranscriptionProcessor
            self._transcriber = TranscriptionProcessor()
        return self._transcriber

    @property
    def youtube(self):
        if self._youtube is None:
            from src.scrapers import YouTubeDownloader
            self._youtube = YouTubeDownloader()
        return self._youtube

    def process_story(
        self,
        story_id: str,
        quick_mode: bool = False,
    ) -> Optional[Path]:
        """
        Process a single story through the full pipeline.

        Args:
            story_id: ID of the story to process
            quick_mode: Use faster rendering without word-by-word captions

        Returns:
            Path to output video or None if failed
        """
        from src.scrapers import RedditScraper

        logger.info(f"Starting pipeline for story: {story_id}")

        # Load story
        scraper = RedditScraper()
        story = scraper.load_story(story_id)
        if not story:
            logger.error(f"Story not found: {story_id}")
            return None

        try:
            # 1. Simplify with LLM
            logger.info("Step 1/5: Simplifying story with LLM")
            processed = self.llm.simplify_story(story)

            # 2. Generate TTS audio
            logger.info("Step 2/5: Generating TTS audio")
            audio_path = self.settings.audio_dir / f"{story_id}.mp3"
            self.tts.generate_audio(processed.simplified_text, audio_path)

            # 3. Transcribe for word timing
            logger.info("Step 3/5: Transcribing audio for timestamps")
            transcript, _ = self.transcriber.transcribe_and_save(audio_path)

            # 4. Get background video
            logger.info("Step 4/5: Selecting background video")
            background = self.youtube.get_random_video()
            if not background:
                logger.warning("No background videos available, downloading one...")
                videos = self.youtube.download_random(count=1)
                if not videos:
                    logger.error("Failed to get background video")
                    return None
                background = videos[0]

            # 5. Assemble final video
            logger.info("Step 5/5: Assembling final video")
            if quick_mode:
                output = self.assembler.quick_assemble(
                    processed, background, audio_path, transcript
                )
            else:
                output = self.assembler.assemble(
                    processed, background, audio_path, transcript
                )

            # Update story status
            processed.status = StoryStatus.ASSEMBLED
            processed.output_video_path = output

            logger.info(f"Pipeline complete! Output: {output}")
            return output

        except Exception as e:
            logger.error(f"Pipeline failed for {story_id}: {e}")
            return None
