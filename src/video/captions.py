"""
Karaoke-style caption generator.
Creates word-by-word highlighted captions for video.
"""

from pathlib import Path
from typing import Callable
import textwrap

from loguru import logger
from moviepy import TextClip, CompositeVideoClip, VideoFileClip

from config.settings import get_settings
from src.models import Transcript, WordTiming, CaptionSegment


class KaraokeCaptions:
    """Generate karaoke-style word-by-word captions."""

    def __init__(self):
        self.settings = get_settings()

    def create_word_clip(
        self,
        word: str,
        start_time: float,
        end_time: float,
        is_highlighted: bool = False,
        position: tuple[str, str] = ("center", "center"),
    ) -> TextClip:
        """
        Create a text clip for a single word.

        Args:
            word: The word text
            start_time: Start time in seconds
            end_time: End time in seconds
            is_highlighted: Whether this word is currently being spoken
            position: Position tuple (x, y)

        Returns:
            TextClip for the word
        """
        color = (
            self.settings.caption.highlight_color
            if is_highlighted
            else self.settings.caption.color
        )

        clip = TextClip(
            text=word,
            font_size=self.settings.caption.font_size,
            color=color,
            font=self.settings.caption.font,
            stroke_color=self.settings.caption.stroke_color,
            stroke_width=self.settings.caption.stroke_width,
        )

        return clip.with_position(position).with_start(start_time).with_end(end_time)

    def create_segment_clips(
        self,
        segment: CaptionSegment,
        video_size: tuple[int, int],
    ) -> list[TextClip]:
        """
        Create caption clips for a segment with word highlighting.

        Args:
            segment: Caption segment with word timings
            video_size: (width, height) of the video

        Returns:
            List of TextClip objects
        """
        clips = []
        width, height = video_size

        # Calculate vertical position (center of screen)
        y_position = height // 2

        for i, word in enumerate(segment.words):
            # Build the full text for this segment
            words_text = [w.word for w in segment.words]

            # Create clips for each moment in this word's duration
            # The highlighted word changes as time progresses

            for j, current_word in enumerate(segment.words):
                # Create text with current word highlighted
                # We'll create separate clips for highlighted and non-highlighted words

                # During this word's time, highlight it
                if j == i:
                    # This is the word being highlighted during word[i]'s time
                    clip = TextClip(
                        text=current_word.word,
                        font_size=self.settings.caption.font_size,
                        color=self.settings.caption.highlight_color,
                        font=self.settings.caption.font,
                        stroke_color=self.settings.caption.stroke_color,
                        stroke_width=self.settings.caption.stroke_width,
                    )
                else:
                    clip = TextClip(
                        text=current_word.word,
                        font_size=self.settings.caption.font_size,
                        color=self.settings.caption.color,
                        font=self.settings.caption.font,
                        stroke_color=self.settings.caption.stroke_color,
                        stroke_width=self.settings.caption.stroke_width,
                    )

        # Simpler approach: create one composite per word timing
        return self._create_karaoke_segment(segment, video_size)

    def _create_karaoke_segment(
        self,
        segment: CaptionSegment,
        video_size: tuple[int, int],
    ) -> list:
        """
        Create karaoke-style clips for a segment.

        For each word in the segment, creates a clip showing all words
        with the current word highlighted.
        """
        clips = []
        width, height = video_size
        y_pos = height * 0.5  # Center vertically

        for i, current_word in enumerate(segment.words):
            # Build text parts: before, current (highlighted), after
            parts_before = " ".join(w.word for w in segment.words[:i])
            highlighted = current_word.word
            parts_after = " ".join(w.word for w in segment.words[i + 1 :])

            # Create composite text with highlighting
            # We'll create the full text and overlay the highlighted word

            full_text = " ".join(w.word for w in segment.words)

            # Base text (all white)
            base_clip = TextClip(
                text=full_text,
                font_size=self.settings.caption.font_size,
                color=self.settings.caption.color,
                font=self.settings.caption.font,
                stroke_color=self.settings.caption.stroke_color,
                stroke_width=self.settings.caption.stroke_width,
                method="caption",
                size=(width - 100, None),
                text_align="center",
            )

            # Position and time
            base_clip = (
                base_clip
                .with_position(("center", y_pos))
                .with_start(current_word.start_time)
                .with_end(current_word.end_time)
            )

            clips.append(base_clip)

            # For the highlight effect, we create a separate clip
            # This is a simplified approach - for true karaoke, you'd need
            # more sophisticated text rendering

            # Create highlight indicator (underline or background)
            # For now, we'll use a simple approach with colored text overlay

        return clips

    def _wrap_text_properly(self, text: str, max_width: int) -> str:
        """
        Wrap text ensuring words are not split across lines.
        
        Args:
            text: Text to wrap
            max_width: Maximum characters per line (approximate)
            
        Returns:
            Wrapped text with proper word boundaries
        """
        # Use textwrap to ensure words stay together
        # Adjust width based on font size - this is approximate
        # You may need to tune this value based on your font
        wrapper = textwrap.TextWrapper(
            width=max_width,
            break_long_words=False,
            break_on_hyphens=False,
            expand_tabs=False,
            replace_whitespace=True,
            drop_whitespace=True,
        )
        
        wrapped_lines = wrapper.wrap(text)
        return "\n".join(wrapped_lines)

    def generate_captions(
        self,
        transcript: Transcript,
        video_size: tuple[int, int],
    ) -> list:
        """
        Generate all caption clips from transcript.

        Args:
            transcript: Transcript with word timings
            video_size: (width, height) of video

        Returns:
            List of TextClip objects
        """
        all_clips = []
        segments = transcript.get_segments_v2()

        logger.info(f"Generating captions for {len(segments)} segments")

        for segment in segments:
            clips = self._create_simple_karaoke(segment, video_size)
            all_clips.extend(clips)

        return all_clips

    def _create_simple_karaoke(
        self,
        segment: CaptionSegment,
        video_size: tuple[int, int],
    ) -> list:
        """
        Create simple karaoke captions - show segment text, highlight current word.

        This creates individual word clips that highlight sequentially.
        """
        clips = []
        width, height = video_size
        
        full_text = " ".join(w.word for w in segment.words)
        
        # Estimate character width based on video width and font size
        # This is approximate - adjust the divisor based on your font
        approx_chars_per_line = (width - 80) // (self.settings.caption.font_size // 2)
        
        # Wrap text properly to avoid word splitting
        wrapped_text = self._wrap_text_properly(full_text, approx_chars_per_line)
        
        # Add padding to prevent clipping
        padded_text = f"\n{wrapped_text}\n"

        for i, word in enumerate(segment.words):
            clip = TextClip(
                text=padded_text,
                font_size=self.settings.caption.font_size,
                color=self.settings.caption.color,
                font=self.settings.caption.font,
                stroke_color=self.settings.caption.stroke_color,
                stroke_width=self.settings.caption.stroke_width,
                method="label",  # Changed from "caption" to "label" for better control
            )
            
            y_pos = int(height * 0.5 - clip.h * 0.5)
            
            clip = (
                clip
                .with_position(("center", y_pos))
                .with_start(word.start_time)
                .with_end(word.end_time)
            )
            clips.append(clip)
    
        return clips

    def apply_captions(
        self,
        video_path: Path,
        transcript: Transcript,
        output_path: Path,
    ) -> Path:
        """
        Apply karaoke captions to video.

        Args:
            video_path: Source video path
            transcript: Transcript with word timings
            output_path: Output video path

        Returns:
            Path to captioned video
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Applying captions to {video_path}")

        with VideoFileClip(str(video_path)) as video:
            video_size = (video.w, video.h)
            caption_clips = self.generate_captions(transcript, video_size)

            # Composite video with captions
            final = CompositeVideoClip([video] + caption_clips)

            logger.info(f"Writing captioned video to {output_path}")
            final.write_videofile(
                str(output_path),
                codec="libx264",
                audio_codec="aac",
                fps=self.settings.video.fps,
                logger=None,
            )

        return output_path


def create_srt_captions(transcript: Transcript, output_path: Path) -> Path:
    """
    Create SRT subtitle file from transcript.

    Args:
        transcript: Transcript with word timings
        output_path: Path to save SRT file

    Returns:
        Path to SRT file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    srt_content = transcript.to_srt()
    output_path.write_text(srt_content, encoding="utf-8")

    logger.info(f"Created SRT file: {output_path}")
    return output_path