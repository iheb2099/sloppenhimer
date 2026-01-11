"""
Text-to-Speech engine using edge-tts.
Generates audio from simplified story text.
"""

import asyncio
from pathlib import Path

import edge_tts
from loguru import logger
from pydub import AudioSegment

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

    def generate_title_and_body_audio(
        self,
        title: str,
        body: str,
        output_path: Path,
        voice: str | None = None,
        rate: str | None = None,
        pause_duration: float = 1.0,
    ) -> tuple[Path, float]:
        """
        Generate combined audio with title first, then body.
        
        Args:
            title: Story title text
            body: Story body text
            output_path: Path to save combined audio
            voice: Voice to use
            rate: Speech rate
            pause_duration: Silence duration between title and body (seconds)
            
        Returns:
            Tuple of (audio_path, title_duration_seconds)
        """
        output_path = Path(output_path)
        cache_dir = output_path.parent / "temp"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate title audio
        title_path = cache_dir / f"{output_path.stem}_title.mp3"
        self.generate_audio(title, title_path, voice, rate)
        
        # Generate body audio
        body_path = cache_dir / f"{output_path.stem}_body.mp3"
        self.generate_audio(body, body_path, voice, rate)
        
        # Load audio segments
        title_audio = AudioSegment.from_mp3(str(title_path))
        body_audio = AudioSegment.from_mp3(str(body_path))
        
        # Get title duration
        title_duration = len(title_audio) / 1000.0  # Convert ms to seconds
        
        # Create pause
        pause = AudioSegment.silent(duration=int(pause_duration * 1000))
        
        # Combine: title + pause + body
        combined = title_audio + pause + body_audio
        
        # Export combined audio
        combined.export(str(output_path), format="mp3")
        
        # Cleanup temp files
        title_path.unlink()
        body_path.unlink()
        
        logger.info(
            f"Generated combined audio: title={title_duration:.2f}s, "
            f"pause={pause_duration}s, total={len(combined)/1000:.2f}s"
        )
        
        return output_path, title_duration

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
