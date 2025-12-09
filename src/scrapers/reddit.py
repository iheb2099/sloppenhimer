"""
Reddit scraper using PRAW (Python Reddit API Wrapper).
"""

import json
from datetime import datetime
from pathlib import Path

import praw
from loguru import logger
from praw.models import Submission

from config.settings import get_settings
from src.models import RedditStory


class RedditScraper:
    """Scrape stories from Reddit subreddits."""

    def __init__(self):
        self.settings = get_settings()
        self._client: praw.Reddit | None = None

    @property
    def client(self) -> praw.Reddit:
        """Lazy-initialize Reddit client."""
        if self._client is None:
            if not self.settings.reddit.client_id:
                raise ValueError(
                    "Reddit client_id not configured. "
                    "Set REDDIT_CLIENT_ID in .env file."
                )
            self._client = praw.Reddit(
                client_id=self.settings.reddit.client_id,
                client_secret=self.settings.reddit.client_secret,
                user_agent=self.settings.reddit.user_agent,
            )
            logger.info("Reddit client initialized")
        return self._client

    def _submission_to_story(self, submission: Submission) -> RedditStory | None:
        """Convert PRAW submission to RedditStory model."""
        # Skip if no selftext (text post content)
        if not submission.selftext or submission.selftext == "[removed]":
            return None

        # Skip if too short or too long
        text_len = len(submission.selftext)
        if text_len < self.settings.reddit.min_length:
            return None
        if text_len > self.settings.reddit.max_length:
            return None

        # Skip if score too low
        if submission.score < self.settings.reddit.min_score:
            return None

        return RedditStory(
            id=submission.id,
            subreddit=submission.subreddit.display_name,
            title=submission.title,
            body=submission.selftext,
            author=str(submission.author) if submission.author else "[deleted]",
            score=submission.score,
            url=f"https://reddit.com{submission.permalink}",
            created_utc=datetime.fromtimestamp(submission.created_utc),
            num_comments=submission.num_comments,
        )

    def scrape_subreddit(
        self,
        subreddit_name: str,
        limit: int | None = None,
        time_filter: str = "week",
    ) -> list[RedditStory]:
        """
        Scrape stories from a subreddit.

        Args:
            subreddit_name: Name of subreddit (without r/)
            limit: Max posts to fetch (defaults to config)
            time_filter: Time filter for top posts (hour/day/week/month/year/all)

        Returns:
            List of RedditStory objects
        """
        if limit is None:
            limit = self.settings.reddit.posts_per_subreddit

        logger.info(f"Scraping r/{subreddit_name} (top {time_filter}, limit={limit})")
        subreddit = self.client.subreddit(subreddit_name)

        stories = []
        for submission in subreddit.top(time_filter=time_filter, limit=limit * 2):
            story = self._submission_to_story(submission)
            if story:
                stories.append(story)
                if len(stories) >= limit:
                    break

        logger.info(f"Found {len(stories)} valid stories from r/{subreddit_name}")
        return stories

    def scrape_all(self, time_filter: str = "week") -> list[RedditStory]:
        """Scrape stories from all configured subreddits."""
        all_stories = []
        for sub in self.settings.reddit.subreddits:
            try:
                stories = self.scrape_subreddit(sub, time_filter=time_filter)
                all_stories.extend(stories)
            except Exception as e:
                logger.error(f"Failed to scrape r/{sub}: {e}")
                continue
        return all_stories

    def save_stories(self, stories: list[RedditStory]) -> list[Path]:
        """Save stories to individual JSON files."""
        saved_paths = []
        stories_dir = self.settings.stories_dir
        stories_dir.mkdir(parents=True, exist_ok=True)

        for story in stories:
            path = stories_dir / f"{story.id}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(story.model_dump(), f, indent=2, default=str)
            saved_paths.append(path)
            logger.debug(f"Saved story {story.id} to {path}")

        logger.info(f"Saved {len(saved_paths)} stories to {stories_dir}")
        return saved_paths

    def load_story(self, story_id: str) -> RedditStory | None:
        """Load a story from disk by ID."""
        path = self.settings.stories_dir / f"{story_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return RedditStory(**data)

    def list_stories(self) -> list[str]:
        """List all saved story IDs."""
        stories_dir = self.settings.stories_dir
        if not stories_dir.exists():
            return []
        return [p.stem for p in stories_dir.glob("*.json")]
