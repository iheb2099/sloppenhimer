"""
LLM processor using Ollama for local inference.
Simplifies Reddit stories for TTS readability.
"""

from pathlib import Path

import ollama
from loguru import logger

from config.settings import get_settings
from src.models import ProcessedStory, RedditStory, StoryStatus


class LLMProcessor:
    """Process stories using local Ollama LLM."""

    def __init__(self):
        self.settings = get_settings()
        self._prompt_template: str | None = None

    @property
    def prompt_template(self) -> str:
        """Load prompt template from file."""
        if self._prompt_template is None:
            prompt_path = self.settings.prompts_dir / "simplify_story.txt"
            if prompt_path.exists():
                # Fix: Add encoding='utf-8' to handle special characters
                self._prompt_template = prompt_path.read_text(encoding='utf-8')
            else:
                # Fallback template
                self._prompt_template = """Rewrite this story to be clearer and easier to read aloud.
Keep the same plot but use simpler sentences. Remove Reddit jargon like AITA.
Just output the rewritten story, nothing else.

STORY:
{story_text}

REWRITTEN:"""
        return self._prompt_template

    def check_ollama(self) -> bool:
        """Check if Ollama is available and model is loaded."""
        try:
            models = ollama.list()
            model_names = [m.get("name", "") for m in models.get("models", [])]
            target = self.settings.ollama.model

            # Check if model is available (partial match for tags)
            available = any(target.split(":")[0] in name for name in model_names)

            if not available:
                logger.warning(
                    f"Model {target} not found. Available: {model_names}. "
                    f"Run: ollama pull {target}"
                )
            return available
        except Exception as e:
            logger.error(f"Ollama not available: {e}")
            logger.info("Make sure Ollama is running: ollama serve")
            return False

    def simplify_story(
        self,
        story: RedditStory,
        max_retries: int = 2,
    ) -> ProcessedStory:
        """
        Simplify a Reddit story for TTS.

        Args:
            story: The original Reddit story
            max_retries: Number of retries on failure

        Returns:
            ProcessedStory with simplified text
        """
        prompt = self.prompt_template.format(story_text=story.body)

        for attempt in range(max_retries + 1):
            try:
                logger.info(
                    f"Simplifying story {story.id} "
                    f"({story.word_count} words) with {self.settings.ollama.model}"
                )

                response = ollama.generate(
                    model=self.settings.ollama.model,
                    prompt=prompt,
                    options={
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": story.word_count * 2,  # Allow some expansion
                    },
                )

                simplified = response.get("response", "").strip()

                if not simplified:
                    raise ValueError("Empty response from LLM")

                # Clean up common LLM artifacts
                simplified = self._clean_response(simplified)

                logger.info(
                    f"Simplified story: {story.word_count} -> "
                    f"{len(simplified.split())} words"
                )

                return ProcessedStory(
                    original=story,
                    simplified_text=simplified,
                    status=StoryStatus.SIMPLIFIED,
                )

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries:
                    logger.error(f"Failed to simplify story {story.id}")
                    # Return original text as fallback
                    return ProcessedStory(
                        original=story,
                        simplified_text=story.body,
                        status=StoryStatus.SIMPLIFIED,
                        error_message=f"LLM failed, using original: {e}",
                    )

        # Should never reach here
        return ProcessedStory(
            original=story,
            simplified_text=story.body,
            status=StoryStatus.FAILED,
        )

    def _clean_response(self, text: str) -> str:
        """Clean up common LLM response artifacts."""
        # Remove common prefixes
        prefixes_to_remove = [
            "Here's the rewritten story:",
            "Here is the rewritten story:",
            "REWRITTEN STORY:",
            "Rewritten story:",
            "REWRITTEN:",
        ]
        for prefix in prefixes_to_remove:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix) :].strip()

        # Remove quotes if entire text is quoted
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]

        return text.strip()

    def process_batch(
        self,
        stories: list[RedditStory],
    ) -> list[ProcessedStory]:
        """Process multiple stories."""
        results = []
        for i, story in enumerate(stories):
            logger.info(f"Processing story {i + 1}/{len(stories)}: {story.id}")
            result = self.simplify_story(story)
            results.append(result)
        return results