"""
Video editor using MoviePy.
Handles trimming, scaling, and format conversion.
"""

from pathlib import Path

from loguru import logger
from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, ImageClip
import numpy as np

from config.settings import get_settings

# Try to import HTML thumbnail generator
try:
    from src.video.html_thumbnail import create_html_thumbnail
    HTML_THUMBNAIL_AVAILABLE = True
    logger.info("✓ HTML thumbnail generator loaded successfully")
except ImportError as e:
    HTML_THUMBNAIL_AVAILABLE = False
    logger.warning(f"✗ HTML thumbnail generator not available: {e}")
    logger.warning("  Install with: pip install html2image")


class VideoEditor:
    """Edit and transform video clips."""

    def __init__(self):
        self.settings = get_settings()
        
        # Check HTML thumbnail availability at init
        global HTML_THUMBNAIL_AVAILABLE
        if HTML_THUMBNAIL_AVAILABLE:
            logger.info("✓ HTML thumbnail rendering is ENABLED")
        else:
            logger.warning("✗ HTML thumbnail rendering is DISABLED")
            logger.warning("  Falling back to template/programmatic generation")

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

    def create_thumbnail_overlay(
        self,
        title: str,
        duration: float,
        video_size: tuple[int, int],
        username: str = "RedditPapi",
        template_path: Path | None = None,
        use_html: bool = True,
    ) -> list:
        """
        Create Reddit-style thumbnail overlay clips.
        
        Args:
            title: Story title to display
            duration: How long to show the thumbnail
            video_size: Tuple of (width, height)
            username: Reddit username to display
            template_path: Path to thumbnail template image (optional)
            use_html: Use HTML rendering for perfect auto-scaling (recommended)

        Returns:
            List of clips for the thumbnail overlay
        """
        width, height = video_size
        clips = []
        
        logger.info(f"Creating thumbnail: use_html={use_html}, HTML_THUMBNAIL_AVAILABLE={HTML_THUMBNAIL_AVAILABLE}")

        # Try HTML-based rendering first (best quality, auto-scales perfectly)
        if use_html and HTML_THUMBNAIL_AVAILABLE:
            try:
                logger.info("🎨 Generating HTML-based thumbnail (auto-scaling)")
                cache_dir = self.settings.cache_dir
                cache_dir.mkdir(parents=True, exist_ok=True)
                
                html_thumb_path = cache_dir / "html_thumbnail.png"
                
                # Call the HTML thumbnail generator
                logger.info(f"Calling create_html_thumbnail with title: {title[:50]}...")
                generated_path = create_html_thumbnail(
                    title=title,
                    username=username,
                    output_path=html_thumb_path,
                    width=int(width * 0.85)
                )
                logger.info(f"HTML thumbnail generated at: {generated_path}")
                
                # Load the generated HTML thumbnail
                thumbnail = ImageClip(str(generated_path))
                
                # Center it
                x_position = (width - thumbnail.w) // 2
                y_position = (height - thumbnail.h) // 2
                
                thumbnail = (
                    thumbnail
                    .with_duration(duration)
                    .with_position((x_position, y_position))
                )
                clips.append(thumbnail)
                
                logger.info(f"✓ HTML thumbnail created successfully: {thumbnail.w}x{thumbnail.h}")
                return clips
                
            except Exception as e:
                logger.error(f"✗ HTML thumbnail generation failed: {e}")
                import traceback
                traceback.print_exc()
                logger.warning("  Falling back to template/programmatic generation")
                use_html = False
        elif use_html and not HTML_THUMBNAIL_AVAILABLE:
            logger.warning("⚠️ HTML rendering requested but not available")
            logger.warning("  Install with: pip install html2image")
            logger.warning("  Falling back to template/programmatic generation")
        
        # If HTML failed or not available, use template or fallback
        # Load template image if it exists
        if template_path is None:
            template_path = self.settings.assets_dir / "reddit_thumbnail.png"
        
        template_path = Path(template_path)
        
        logger.info(f"Looking for thumbnail template at: {template_path}")
        logger.info(f"Template exists: {template_path.exists()}")
        
        use_template = template_path.exists()
        
        # Calculate title size first to know how much space we need
        target_width = int(width * 0.85)
        title_text_width = int(target_width * 0.85)
        
        # Calculate appropriate font size based on title length
        title_length = len(title)
        if title_length < 50:
            font_size = min(55, width // 16)
        elif title_length < 100:
            font_size = min(48, width // 18)
        else:
            font_size = min(42, width // 20)
        
        # Create temporary title clip to measure its height
        temp_title = TextClip(
            text=title,
            font_size=font_size,
            color='#1A1A1B',
            font=self.settings.caption.font if hasattr(self.settings.caption, 'font') else 'Arial-Bold',
            text_align='center',
            size=(title_text_width, None),
            method='caption'
        )
        
        title_height = temp_title.h
        
        if use_template:
            # Use template and overlay text
            logger.info(f"Using thumbnail template with dynamic sizing")
            
            thumbnail = ImageClip(str(template_path))
            
            # Check if template needs to be taller for the text
            thumbnail = thumbnail.resized(width=target_width)
            
            # If text is too tall for template, we need to scale the template
            # or create a taller version
            min_required_height = title_height + 300  # Header + footer + padding
            
            if thumbnail.h < min_required_height:
                # Scale template to accommodate text
                scale_factor = min_required_height / thumbnail.h
                thumbnail = ImageClip(str(template_path)).resized(height=int(thumbnail.h * scale_factor))
                thumbnail = thumbnail.resized(width=target_width)
            
            # Center both horizontally and vertically
            x_position = (width - thumbnail.w) // 2
            y_position = (height - thumbnail.h) // 2
            
            thumbnail = (
                thumbnail
                .with_duration(duration)
                .with_position((x_position, y_position))
            )
            clips.append(thumbnail)
            
            # Position title in middle of template
            title_y = y_position + int(thumbnail.h * 0.48)
            
            title_clip = (
                temp_title
                .with_duration(duration)
                .with_position(('center', title_y))
            )
            clips.append(title_clip)
            
        else:
            # Create dynamic card without template
            logger.info(f"Creating dynamic thumbnail card (no template)")
            
            # Calculate card height based on text
            header_height = 120  # Space for logo + username
            footer_height = 100  # Space for stats
            padding = 80  # Top and bottom padding
            
            card_height = header_height + title_height + footer_height + padding
            card_width = target_width
            
            # Create semi-transparent rounded card
            card_array = np.ones((card_height, card_width, 4), dtype=np.uint8) * 255
            card_array[:, :, 3] = 245  # Slightly opaque
            
            # Add rounded corners effect (simple approach)
            corner_radius = 30
            for i in range(corner_radius):
                alpha = int(255 * (i / corner_radius))
                # Top-left
                card_array[i, :i] = [255, 255, 255, alpha]
                # Top-right
                card_array[i, -(i+1):] = [255, 255, 255, alpha]
                # Bottom-left
                card_array[-(i+1), :i] = [255, 255, 255, alpha]
                # Bottom-right
                card_array[-(i+1), -(i+1):] = [255, 255, 255, alpha]
            
            x_position = (width - card_width) // 2
            y_position = (height - card_height) // 2
            
            card = (
                ImageClip(card_array)
                .with_duration(duration)
                .with_position((x_position, y_position))
            )
            clips.append(card)
            
            # Reddit logo (orange circle)
            icon_size = 70
            icon_array = np.zeros((icon_size, icon_size, 4), dtype=np.uint8)
            center = icon_size // 2
            y_grid, x_grid = np.ogrid[:icon_size, :icon_size]
            mask = (x_grid - center) ** 2 + (y_grid - center) ** 2 <= (icon_size // 2) ** 2
            icon_array[mask] = [255, 69, 0, 255]  # Reddit orange
            
            icon = (
                ImageClip(icon_array)
                .with_duration(duration)
                .with_position((x_position + 30, y_position + 30))
            )
            clips.append(icon)
            
            # Username and subreddit
            header_text = (
                TextClip(
                    text=f"r/{username}\n{username} ✓",
                    font_size=min(38, width // 22),
                    color='#1A1A1B',
                    font=self.settings.caption.font if hasattr(self.settings.caption, 'font') else 'Arial-Bold',
                    text_align='left',
                )
                .with_duration(duration)
                .with_position((x_position + 120, y_position + 35))
            )
            clips.append(header_text)
            
            # Title text
            title_y = y_position + header_height + 20
            title_clip = (
                temp_title
                .with_duration(duration)
                .with_position(('center', title_y))
            )
            clips.append(title_clip)
            
            # Stats at bottom
            stats_y = y_position + card_height - 70
            
            # Upvotes
            upvote_clip = (
                TextClip(
                    text="⬆ 999 ⬇",
                    font_size=min(32, width // 28),
                    color='#1A1A1B',
                    font=self.settings.caption.font if hasattr(self.settings.caption, 'font') else 'Arial'
                )
                .with_duration(duration)
                .with_position((x_position + 40, stats_y))
            )
            clips.append(upvote_clip)
            
            # Comments
            comments_clip = (
                TextClip(
                    text="💬 999",
                    font_size=min(32, width // 28),
                    color='#1A1A1B',
                    font=self.settings.caption.font if hasattr(self.settings.caption, 'font') else 'Arial'
                )
                .with_duration(duration)
                .with_position((x_position + 200, stats_y))
            )
            clips.append(comments_clip)
            
            # Share
            share_clip = (
                TextClip(
                    text="↗ Share",
                    font_size=min(32, width // 28),
                    color='#1A1A1B',
                    font=self.settings.caption.font if hasattr(self.settings.caption, 'font') else 'Arial'
                )
                .with_duration(duration)
                .with_position((x_position + card_width - 160, stats_y))
            )
            clips.append(share_clip)

        logger.info(f"Created thumbnail overlay for {duration:.1f}s with title height {title_height}px")
        return clips