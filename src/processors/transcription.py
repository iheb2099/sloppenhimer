"""
Transcription processor using OpenAI Whisper.
Generates word-level timestamps for caption synchronization.
"""

import json
from pathlib import Path

import whisper
from loguru import logger

from config.settings import get_settings
from src.models import Transcript, WordTiming


class TranscriptionProcessor:
    """Generate word-level transcriptions from audio using Whisper."""

    def __init__(self, model_size: str = "base"):
        """
        Initialize transcription processor.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
        """
        self.settings = get_settings()
        self.model_size = model_size
        self._model = None

    @property
    def model(self):
        """Lazy-load Whisper model."""
        if self._model is None:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self._model = whisper.load_model(self.model_size)
            logger.info("Whisper model loaded")
        return self._model

    def transcribe(
        self,
        audio_path: Path,
        language: str = "en",
    ) -> Transcript:
        """
        Transcribe audio file with word-level timestamps.

        Args:
            audio_path: Path to audio file
            language: Language code

        Returns:
            Transcript with word timings
        """
        audio_path = Path(audio_path)
        logger.info(f"Transcribing: {audio_path}")

        # Transcribe with word timestamps
        result = self.model.transcribe(
            str(audio_path),
            language=language,
            word_timestamps=True,
            verbose=False,
        )

        # Extract word timings
        words = []
        for segment in result.get("segments", []):
            for word_info in segment.get("words", []):
                words.append(
                    WordTiming(
                        word=word_info["word"].strip(),
                        start_time=word_info["start"],
                        end_time=word_info["end"],
                        confidence=word_info.get("probability", 1.0),
                    )
                )

        # Get total duration
        duration = 0.0
        if words:
            duration = words[-1].end_time
        elif result.get("segments"):
            duration = result["segments"][-1]["end"]

        transcript = Transcript(
            words=words,
            duration=duration,
            language=language,
        )

        logger.info(
            f"Transcribed {len(words)} words, duration: {duration:.2f}s"
        )
        return transcript

    def transcribe_and_save(
        self,
        audio_path: Path,
        output_path: Path | None = None,
        language: str = "en",
    ) -> tuple[Transcript, Path]:
        """
        Transcribe audio and save results.

        Args:
            audio_path: Path to audio file
            output_path: Path to save transcript JSON (defaults to audio_path.json)
            language: Language code

        Returns:
            Tuple of (Transcript, output_path)
        """
        transcript = self.transcribe(audio_path, language)

        if output_path is None:
            output_path = audio_path.with_suffix(".json")

        # Save transcript
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(transcript.model_dump(), f, indent=2)

        # Also save SRT for convenience
        srt_path = audio_path.with_suffix(".srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(transcript.to_srt())

        logger.info(f"Saved transcript to {output_path}")
        logger.info(f"Saved SRT to {srt_path}")

        return transcript, output_path

    @staticmethod
    def load_transcript(path: Path) -> Transcript:
        """Load transcript from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Transcript(**data)


def estimate_word_timings(
    text: str,
    audio_duration: float,
    words_per_minute: float = 150,
) -> Transcript:
    """
    Fallback: Estimate word timings when Whisper is unavailable.

    Args:
        text: The text content
        audio_duration: Total audio duration in seconds
        words_per_minute: Assumed speaking rate

    Returns:
        Transcript with estimated timings
    """
    words = text.split()
    if not words:
        return Transcript(words=[], duration=0, language="en")

    # Calculate time per word based on actual duration
    time_per_word = audio_duration / len(words)

    word_timings = []
    current_time = 0.0

    for word in words:
        word_timings.append(
            WordTiming(
                word=word,
                start_time=current_time,
                end_time=current_time + time_per_word,
                confidence=0.5,  # Lower confidence for estimates
            )
        )
        current_time += time_per_word

    return Transcript(
        words=word_timings,
        duration=audio_duration,
        language="en",
    )
