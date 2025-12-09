"""
Data models for captions and word timing.
"""

from pydantic import BaseModel, Field


class WordTiming(BaseModel):
    """Timing information for a single word."""

    word: str = Field(description="The word text")
    start_time: float = Field(description="Start time in seconds")
    end_time: float = Field(description="End time in seconds")
    confidence: float = Field(default=1.0, description="Transcription confidence")

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


class CaptionSegment(BaseModel):
    """A group of words displayed together."""

    words: list[WordTiming] = Field(description="Words in this segment")
    start_time: float = Field(description="Segment start time")
    end_time: float = Field(description="Segment end time")

    @property
    def text(self) -> str:
        return " ".join(w.word for w in self.words)

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


class Transcript(BaseModel):
    """Full transcript with word-level timing."""

    words: list[WordTiming] = Field(description="All words with timing")
    duration: float = Field(description="Total audio duration")
    language: str = Field(default="en", description="Detected language")

    def get_segments(self, words_per_segment: int = 4) -> list[CaptionSegment]:
        """Group words into display segments."""
        segments = []
        for i in range(0, len(self.words), words_per_segment):
            group = self.words[i : i + words_per_segment]
            if group:
                segments.append(
                    CaptionSegment(
                        words=group,
                        start_time=group[0].start_time,
                        end_time=group[-1].end_time,
                    )
                )
        return segments

    def to_srt(self) -> str:
        """Export to SRT subtitle format."""
        segments = self.get_segments()
        lines = []
        for i, seg in enumerate(segments, 1):
            start = _format_srt_time(seg.start_time)
            end = _format_srt_time(seg.end_time)
            lines.append(f"{i}")
            lines.append(f"{start} --> {end}")
            lines.append(seg.text)
            lines.append("")
        return "\n".join(lines)


def _format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
