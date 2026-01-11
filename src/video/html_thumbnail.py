"""
HTML-based thumbnail generator that auto-scales like a webpage.
Uses html2image to render HTML/CSS as an image.
"""

from pathlib import Path
from loguru import logger

try:
    from html2image import Html2Image
    HTML2IMAGE_AVAILABLE = True
except ImportError:
    HTML2IMAGE_AVAILABLE = False
    logger.warning("html2image not available. Install with: pip install html2image")


class HTMLThumbnailGenerator:
    """Generate Reddit-style thumbnails using HTML/CSS rendering."""

    def __init__(self):
        if HTML2IMAGE_AVAILABLE:
            # Don't set output_path in init, we'll handle it per screenshot
            self.hti = Html2Image()
        else:
            self.hti = None

    def generate_thumbnail(
        self,
        title: str,
        username: str = "RedditPapi",
        upvotes: str = "249",
        comments: str = "57",
        output_path: Path | None = None,
        width: int = 1080,
    ) -> Path:
        """
        Generate a thumbnail image from HTML/CSS.

        Args:
            title: Story title
            username: Reddit username
            upvotes: Upvote count
            comments: Comment count
            output_path: Path to save image
            width: Width in pixels

        Returns:
            Path to generated image
        """
        if not HTML2IMAGE_AVAILABLE:
            raise ImportError("html2image is required. Install with: pip install html2image")

        if output_path is None:
            output_path = Path("temp") / "thumbnail.png"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        html_content = self._create_html(title, username, upvotes, comments)
        css_content = self._create_css()

        logger.info(f"Generating HTML thumbnail for title: {title[:50]}...")

        # Estimate height based on title length
        # Be generous with height to avoid clipping
        base_height = 500  # Increased from 400
        title_lines = len(title) // 35 + 1  # More conservative line estimate
        estimated_height = base_height + (title_lines * 80)  # More space per line
        
        # Add extra padding for safety
        estimated_height = int(estimated_height * 1.3)  # 30% extra buffer
        
        # Set output path for html2image
        self.hti.output_path = str(output_path.parent)
        
        # Generate the image with estimated size
        self.hti.screenshot(
            html_str=html_content,
            css_str=css_content,
            save_as=output_path.name,
            size=(width, estimated_height)
        )

        logger.info(f"Thumbnail generated at {output_path} with size {width}x{estimated_height}")
        return output_path

    def _create_html(self, title: str, username: str, upvotes: str, comments: str) -> str:
        """Create the HTML structure."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&display=swap" rel="stylesheet">
        </head>
        <body>
            <div class="reddit-card">
                <!-- Header -->
                <div class="header">
                    <div class="reddit-icon">
                        <svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="10" cy="10" r="10" fill="#FF4500"/>
                            <path d="M16.5,10.5c0,-0.8 -0.6,-1.4 -1.4,-1.4c-0.4,0 -0.7,0.1 -1,0.4c-1,-0.7 -2.4,-1.2 -3.9,-1.2l0.7,-3.1l2.2,0.5c0,0.6 0.5,1.1 1.1,1.1c0.6,0 1.1,-0.5 1.1,-1.1s-0.5,-1.1 -1.1,-1.1c-0.5,0 -0.9,0.3 -1,0.7l-2.5,-0.6c-0.1,0 -0.3,0.1 -0.3,0.2l-0.8,3.5c-1.6,0 -3,0.5 -4,1.2c-0.3,-0.2 -0.6,-0.4 -1,-0.4c-0.8,0 -1.4,0.6 -1.4,1.4c0,0.6 0.3,1.1 0.8,1.3c0,0.1 0,0.3 0,0.4c0,2.2 2.6,4 5.7,4s5.7,-1.8 5.7,-4c0,-0.1 0,-0.3 0,-0.4c0.5,-0.2 0.8,-0.7 0.8,-1.3Z" fill="white"/>
                        </svg>
                    </div>
                    <div class="header-text">
                        <div class="subreddit">RedditPapi</div>
                        <div class="username">{username} <span class="verified">✓</span></div>
                    </div>
                </div>

                <!-- Awards -->
                <div class="awards">
                    <span class="award">🏆</span>
                    <span class="award">👀</span>
                    <span class="award">⭐</span>
                    <span class="award">👍</span>
                    <span class="award">🔧</span>
                    <span class="award">⚠️</span>
                    <span class="award">💡</span>
                    <span class="award">🎉</span>
                    <span class="award">🙏</span>
                    <span class="award">👏</span>
                </div>

                <!-- Title -->
                <div class="title">{title}</div>

                <!-- Footer Actions -->
                <div class="actions">
                    <div class="action-item">
                        <svg class="icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z" fill="currentColor"/>
                        </svg>
                        <span>{upvotes}</span>
                        <svg class="icon down" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z" fill="currentColor"/>
                        </svg>
                    </div>
                    <div class="action-item">
                        <svg class="icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path d="M21 6h-2v9H6v2c0 .55.45 1 1 1h11l4 4V7c0-.55-.45-1-1-1zm-4 6V3c0-.55-.45-1-1-1H3c-.55 0-1 .45-1 1v14l4-4h10c.55 0 1-.45 1-1z" fill="currentColor"/>
                        </svg>
                        <span>{comments}</span>
                    </div>
                    <div class="action-item">
                        <svg class="icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z" fill="currentColor"/>
                        </svg>
                    </div>
                    <div class="action-item share">
                        <svg class="icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path d="M16 5l-1.42 1.42-1.59-1.59V16h-1.98V4.83L9.42 6.42 8 5l4-4 4 4zm4 5v11c0 1.1-.9 2-2 2H6c-1.11 0-2-.9-2-2V10c0-1.11.89-2 2-2h3v2H6v11h12V10h-3V8h3c1.1 0 2 .89 2 2z" fill="currentColor"/>
                        </svg>
                        <span>Share</span>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    def _create_css(self) -> str:
        """Create the CSS styling."""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: transparent;
            padding: 40px;
        }

        .reddit-card {
            background: white;
            border-radius: 16px;
            padding: 32px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            max-width: 1000px;
            margin: 0 auto;
        }

        .header {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 16px;
        }

        .reddit-icon {
            width: 56px;
            height: 56px;
            flex-shrink: 0;
        }

        .reddit-icon svg {
            width: 100%;
            height: 100%;
        }

        .header-text {
            flex: 1;
        }

        .subreddit {
            font-size: 28px;
            font-weight: 700;
            color: #1A1A1B;
            margin-bottom: 4px;
        }

        .username {
            font-size: 22px;
            color: #7C7C7C;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .verified {
            color: #0079D3;
            font-size: 24px;
        }

        .awards {
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
            flex-wrap: wrap;
        }

        .award {
            font-size: 32px;
        }

        .title {
            font-size: 42px;
            font-weight: 600;
            color: #1A1A1B;
            line-height: 1.4;
            margin-bottom: 32px;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }

        .actions {
            display: flex;
            gap: 24px;
            align-items: center;
            padding-top: 20px;
            border-top: 1px solid #EDEFF1;
        }

        .action-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 20px;
            background: #F6F7F8;
            border-radius: 24px;
            font-size: 24px;
            font-weight: 600;
            color: #1A1A1B;
            cursor: pointer;
            transition: background 0.2s;
        }

        .action-item:hover {
            background: #E9EAEB;
        }

        .action-item.share {
            margin-left: auto;
        }

        .icon {
            width: 28px;
            height: 28px;
            color: #878A8C;
        }

        .icon.down {
            transform: rotate(180deg);
        }
        """


# Integration function for VideoEditor
def create_html_thumbnail(
    title: str,
    username: str = "RedditPapi",
    output_path: Path | None = None,
    width: int = 1080,
) -> Path:
    """
    Create a Reddit-style thumbnail using HTML rendering.
    
    Args:
        title: Story title
        username: Reddit username
        output_path: Where to save the thumbnail
        width: Width in pixels
        
    Returns:
        Path to generated thumbnail image
    """
    generator = HTMLThumbnailGenerator()
    return generator.generate_thumbnail(title, username, output_path=output_path, width=width)