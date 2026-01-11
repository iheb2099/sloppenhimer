"""
Karaoke-style caption generator.
Creates word-by-word highlighted captions for video.
"""

from pathlib import Path
from typing import Callable
import textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from loguru import logger
from moviepy import TextClip, CompositeVideoClip, VideoFileClip, ImageClip

from config.settings import get_settings
from src.models import Transcript, WordTiming, CaptionSegment


class KaraokeCaptions:
    """Generate karaoke-style word-by-word captions."""

    def __init__(self):
        self.settings = get_settings()

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _create_text_image_with_highlight(
        self,
        words: list[WordTiming],
        highlight_index: int,
        width: int,
        font_size: int,
        max_chars: int
    ) -> np.ndarray:
        """
        Create a PIL image with text where one word is highlighted.
        
        Args:
            words: List of word timings
            highlight_index: Index of word to highlight
            width: Image width
            font_size: Font size
            max_chars: Max characters per line for wrapping
            
        Returns:
            numpy array of RGBA image
        """
        # Build and wrap text
        full_text = " ".join(w.word for w in words)
        wrapped_text = self._wrap_text_properly(full_text, max_chars)
        lines = wrapped_text.split('\n')
        
        # Load font
        try:
            font = ImageFont.truetype(self.settings.caption.font, font_size)
        except:
            font = ImageFont.load_default()
        
        # Calculate image height
        line_height = font_size + 10
        height = len(lines) * line_height + 40
        
        # Create transparent image
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Parse colors
        if self.settings.caption.color.startswith('#'):
            default_color = self._hex_to_rgb(self.settings.caption.color)
        else:
            default_color = (255, 255, 255)  # white
            
        if self.settings.caption.highlight_color.startswith('#'):
            highlight_color = self._hex_to_rgb(self.settings.caption.highlight_color)
        else:
            highlight_color = (255, 255, 0)  # yellow
        
        # Track word index as we render
        word_index = 0
        y_offset = 20
        
        for line in lines:
            line_words = line.split()
            
            # Calculate starting x for centered text
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
            except:
                line_width = len(line) * (font_size // 2)
            
            x_offset = (width - line_width) // 2
            
            # Draw each word
            for word_text in line_words:
                # Determine color
                color = highlight_color if word_index == highlight_index else default_color
                
                # Draw word
                draw.text((x_offset, y_offset), word_text, font=font, fill=color)
                
                # Move x position
                try:
                    bbox = draw.textbbox((0, 0), word_text + ' ', font=font)
                    word_width = bbox[2] - bbox[0]
                except:
                    word_width = len(word_text + ' ') * (font_size // 2)
                
                x_offset += word_width
                word_index += 1
            
            y_offset += line_height
        
        # Convert to numpy array
        return np.array(img)

    def _create_karaoke_with_highlight(
        self,
        segment: CaptionSegment,
        video_size: tuple[int, int],
    ) -> list:
        """
        Create karaoke captions with word-by-word yellow highlighting using PIL.
        """
        clips = []
        width, height = video_size
        
        if not segment.words:
            return clips
        
        approx_chars_per_line = (width - 80) // (self.settings.caption.font_size // 2)
        
        # Create image clip for each word timing
        for i, current_word in enumerate(segment.words):
            # Generate image with current word highlighted
            img_array = self._create_text_image_with_highlight(
                segment.words,
                i,
                width,
                self.settings.caption.font_size,
                approx_chars_per_line
            )
            
            # Create ImageClip from array
            img_clip = ImageClip(img_array, duration=current_word.end_time - current_word.start_time)
            
            # Center vertically
            y_pos = int(height * 0.5 - img_clip.h * 0.5)
            
            img_clip = (
                img_clip
                .with_position(("center", y_pos))
                .with_start(current_word.start_time)
            )
            
            clips.append(img_clip)
        
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
            List of clip objects
        """
        all_clips = []
        segments = transcript.get_segments_v2()

        logger.info(f"Generating captions for {len(segments)} segments")

        for segment in segments:
            clips = self._create_karaoke_with_highlight(segment, video_size)
            all_clips.extend(clips)

        return all_clips

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