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
    def get_segments_v2(self, words_per_segment: int = None) -> list[CaptionSegment]:
        """
        Group words into caption segments aligned with sentences.

        - If `words_per_segment` is provided, fallback to fixed-size segments (legacy).
        - Otherwise, segments are split at '.', '?', or '!'.
        """
        segments = []
        if words_per_segment:
            # Legacy fixed-size grouping
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

        # Sentence-aware grouping
        current: list[WordTiming] = []
        for word in self.words:
            current.append(word)

            if word.word.rstrip().endswith((".", "?", "!",",")):
                segments.append(
                    CaptionSegment(
                        words=current.copy(),
                        start_time=current[0].start_time,
                        end_time=current[-1].end_time,
                    )
                )
                current = []

        if current:
            segments.append(
                CaptionSegment(
                    words=current.copy(),
                    start_time=current[0].start_time,
                    end_time=current[-1].end_time,
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
    def get_sentence_segments(self) -> list[CaptionSegment]:
        """
        Split transcript into sentence-aligned caption segments.
        A segment ends on '.', '?', or '!'.
        """
        segments: list[CaptionSegment] = []
        current: list[WordTiming] = []

        for word in self.words:
            current.append(word)

            if word.word.rstrip().endswith((".", "?", "!")):
                segments.append(
                    CaptionSegment(
                        words=current,
                        start_time=current[0].start_time,
                        end_time=current[-1].end_time,
                    )
                )
                current = []

        # Add any leftover words as a segment
        if current:
            segments.append(
                CaptionSegment(
                    words=current,
                    start_time=current[0].start_time,
                    end_time=current[-1].end_time,
                )
            )

        return segments



def _format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
