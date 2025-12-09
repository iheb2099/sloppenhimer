"""
Text-to-Speech engine using edge-tts.
Generates audio from simplified story text.
"""

import asyncio
from pathlib import Path

import edge_tts
from loguru import logger

from config.settings import get_settings


class TTSEngine:
    """Generate speech audio from text using edge-tts."""

    def __init__(self):
        self.settings = get_settings()

    async def generate_audio_async(
        self,
        text: str,
        output_path: Path,
        voice: str | None = None,
        rate: str | None = None,
    ) -> Path:
        """
        Generate audio from text asynchronously.

        Args:
            text: Text to convert to speech
            output_path: Path to save audio file
            voice: Voice to use (defaults to config)
            rate: Speech rate adjustment (e.g., "+10%", "-5%")

        Returns:
            Path to generated audio file
        """
        voice = voice or self.settings.tts.edge_voice
        rate = rate or self.settings.tts.speech_rate

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating TTS audio with voice={voice}, rate={rate}")
        logger.debug(f"Text length: {len(text)} chars, ~{len(text.split())} words")

        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(str(output_path))

        logger.info(f"Audio saved to {output_path}")
        return output_path

    def generate_audio(
        self,
        text: str,
        output_path: Path,
        voice: str | None = None,
        rate: str | None = None,
    ) -> Path:
        """
        Generate audio from text (synchronous wrapper).

        Args:
            text: Text to convert to speech
            output_path: Path to save audio file
            voice: Voice to use (defaults to config)
            rate: Speech rate adjustment

        Returns:
            Path to generated audio file
        """
        return asyncio.run(
            self.generate_audio_async(text, output_path, voice, rate)
        )

    async def generate_with_timestamps_async(
        self,
        text: str,
        output_path: Path,
        voice: str | None = None,
        rate: str | None = None,
    ) -> tuple[Path, list[dict]]:
        """
        Generate audio and collect word boundaries.

        Note: edge-tts provides word boundary events that can be used
        for caption timing, but whisper-timestamped is more accurate.

        Returns:
            Tuple of (audio_path, word_boundaries)
        """
        voice = voice or self.settings.tts.edge_voice
        rate = rate or self.settings.tts.speech_rate

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        word_boundaries = []

        communicate = edge_tts.Communicate(text, voice, rate=rate)

        with open(output_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    word_boundaries.append({
                        "text": chunk["text"],
                        "offset": chunk["offset"] / 10_000_000,  # Convert to seconds
                        "duration": chunk["duration"] / 10_000_000,
                    })

        logger.info(f"Generated audio with {len(word_boundaries)} word boundaries")
        return output_path, word_boundaries

    def generate_with_timestamps(
        self,
        text: str,
        output_path: Path,
        voice: str | None = None,
        rate: str | None = None,
    ) -> tuple[Path, list[dict]]:
        """Synchronous wrapper for generate_with_timestamps_async."""
        return asyncio.run(
            self.generate_with_timestamps_async(text, output_path, voice, rate)
        )

    @staticmethod
    async def list_voices_async(language: str = "en") -> list[dict]:
        """List available voices for a language."""
        voices = await edge_tts.list_voices()
        return [v for v in voices if v["Locale"].startswith(language)]

    @staticmethod
    def list_voices(language: str = "en") -> list[dict]:
        """List available voices (synchronous)."""
        return asyncio.run(TTSEngine.list_voices_async(language))


# Common voice options for reference:
VOICE_OPTIONS = {
    "male_us": "en-US-ChristopherNeural",
    "female_us": "en-US-JennyNeural",
    "male_uk": "en-GB-RyanNeural",
    "female_uk": "en-GB-SoniaNeural",
    "male_au": "en-AU-WilliamNeural",
    "female_au": "en-AU-NatashaNeural",
}
