"""
Reddit scraper using YARS (Yet Another Reddit Scraper).
No API keys required - scrapes directly from Reddit.
"""

import json
import re
import hashlib
from datetime import datetime
from pathlib import Path

import requests
from loguru import logger

from config.settings import get_settings
from src.models import RedditStory


class YARS:
    """
    Yet Another Reddit Scraper - API-free Reddit scraping.
    Based on https://github.com/datavorous/yars
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def fetch_subreddit_posts(
        self,
        subreddit: str,
        limit: int = 25,
        category: str = "top",
        time_filter: str = "week",
    ) -> list[dict]:
        """
        Fetch posts from a subreddit.

        Args:
            subreddit: Subreddit name (without r/)
            limit: Number of posts to fetch
            category: Sort category (hot, new, top, rising)
            time_filter: Time filter for top (hour, day, week, month, year, all)

        Returns:
            List of post dictionaries
        """
        base_url = f"https://www.reddit.com/r/{subreddit}/{category}.json"
        params = {"limit": min(limit, 100), "t": time_filter}

        posts = []
        after = None

        while len(posts) < limit:
            if after:
                params["after"] = after

            try:
                response = self.session.get(base_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                logger.error(f"Failed to fetch r/{subreddit}: {e}")
                break

            children = data.get("data", {}).get("children", [])
            if not children:
                break

            for child in children:
                post_data = child.get("data", {})
                posts.append(post_data)
                if len(posts) >= limit:
                    break

            after = data.get("data", {}).get("after")
            if not after:
                break

        return posts

    def scrape_post_details(self, permalink: str) -> dict | None:
        """
        Scrape full details of a post including body text.

        Args:
            permalink: Reddit permalink (e.g., /r/AITA/comments/abc123/title/)

        Returns:
            Post data dictionary or None
        """
        if not permalink.startswith("http"):
            url = f"https://www.reddit.com{permalink}.json"
        else:
            url = permalink if permalink.endswith(".json") else f"{permalink}.json"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data and len(data) > 0:
                return data[0].get("data", {}).get("children", [{}])[0].get("data", {})
        except Exception as e:
            logger.error(f"Failed to fetch post details: {e}")

        return None


class RedditScraper:
    """Scrape stories from Reddit subreddits using YARS."""

    def __init__(self):
        self.settings = get_settings()
        self._client: YARS | None = None

    @property
    def client(self) -> YARS:
        """Lazy-initialize YARS client."""
        if self._client is None:
            self._client = YARS()
            logger.info("YARS Reddit scraper initialized (no API key required)")
        return self._client

    def _post_to_story(self, post: dict) -> RedditStory | None:
        """Convert YARS post dict to RedditStory model."""
        # Get selftext (body content)
        selftext = post.get("selftext", "")

        # Skip if no selftext or removed/deleted
        if not selftext or selftext in ("[removed]", "[deleted]"):
            return None

        # Skip if too short or too long
        text_len = len(selftext)
        if text_len < self.settings.reddit.min_length:
            return None
        if text_len > self.settings.reddit.max_length:
            return None

        # Skip if score too low
        score = post.get("score", 0)
        if score < self.settings.reddit.min_score:
            return None

        # Generate ID from permalink if not available
        post_id = post.get("id", "")
        if not post_id:
            permalink = post.get("permalink", "")
            post_id = hashlib.md5(permalink.encode()).hexdigest()[:12]

        # Parse created time
        created_utc = post.get("created_utc", 0)
        if isinstance(created_utc, (int, float)):
            created_time = datetime.fromtimestamp(created_utc)
        else:
            created_time = datetime.now()

        return RedditStory(
            id=post_id,
            subreddit=post.get("subreddit", "unknown"),
            title=post.get("title", "Untitled"),
            body=selftext,
            author=post.get("author", "[deleted]"),
            score=score,
            url=f"https://reddit.com{post.get('permalink', '')}",
            created_utc=created_time,
            num_comments=post.get("num_comments", 0),
        )

    def scrape_subreddit(
        self,
        subreddit_name: str,
        limit: int | None = None,
        time_filter: str = "week",
        category: str = "top",
    ) -> list[RedditStory]:
        """
        Scrape stories from a subreddit.

        Args:
            subreddit_name: Name of subreddit (without r/)
            limit: Max posts to fetch (defaults to config)
            time_filter: Time filter for top posts (hour/day/week/month/year/all)
            category: Sort category (hot, new, top, rising)

        Returns:
            List of RedditStory objects
        """
        if limit is None:
            limit = self.settings.reddit.posts_per_subreddit

        logger.info(f"Scraping r/{subreddit_name} ({category} {time_filter}, limit={limit})")

        # Fetch more than needed since we'll filter
        posts = self.client.fetch_subreddit_posts(
            subreddit_name,
            limit=limit * 3,
            category=category,
            time_filter=time_filter,
        )

        stories = []
        for post in posts:
            story = self._post_to_story(post)
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
