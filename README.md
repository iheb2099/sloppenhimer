# Project Sloppenhimer

Automated content pipeline for creating short-form vertical videos from Reddit stories with Minecraft gameplay backgrounds and TTS narration.

## What it does

1. **Scrapes Reddit** - Fetches top stories from r/AITA, r/tifu, r/relationships, etc.
2. **Downloads gameplay** - Grabs royalty-free Minecraft videos from YouTube
3. **Simplifies stories** - Uses local LLM (Ollama) to make text TTS-friendly
4. **Generates voiceover** - Creates natural speech with edge-tts
5. **Adds captions** - Word-level timestamps via Whisper for karaoke-style text
6. **Assembles video** - Combines everything into vertical 9:16 format (TikTok/Reels/Shorts)

## Installation

### Prerequisites

```bash
# macOS
brew install ffmpeg

# Install Ollama (local LLM)
brew install ollama
ollama serve  # Start in background
ollama pull llama3.2:3b  # Download model
```

### Reddit API Setup

1. Go to https://www.reddit.com/prefs/apps
2. Click "create another app..."
3. Select "script" type
4. Set redirect URI to `http://localhost:8080`
5. Note your `client_id` (under app name) and `client_secret`

### Install Sloppenhimer

```bash
git clone https://github.com/j8ckfi/sloppenhimer.git
cd sloppenhimer

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your Reddit credentials
```

## Configuration

Edit `.env`:

```bash
# Required: Reddit API
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=sloppenhimer:v1.0 (by /u/yourusername)

# Optional: Customize
OLLAMA_MODEL=llama3.2:3b
EDGE_TTS_VOICE=en-US-ChristopherNeural
```

## Usage

### Quick Start

```bash
# 1. Scrape some stories
sloppenhimer scrape

# 2. Download background videos
sloppenhimer fetch-videos

# 3. Process a story into a video
sloppenhimer list-stories  # Find a story ID
sloppenhimer process <story_id>
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `sloppenhimer scrape` | Scrape stories from configured subreddits |
| `sloppenhimer fetch-videos` | Download Minecraft gameplay from YouTube |
| `sloppenhimer list-stories` | List all scraped stories |
| `sloppenhimer list-videos` | List downloaded background videos |
| `sloppenhimer process <id>` | Run full pipeline on a story |
| `sloppenhimer process <id> --quick` | Fast render (simpler captions) |
| `sloppenhimer check` | Verify system dependencies |
| `sloppenhimer voices` | List available TTS voices |

### Scrape Options

```bash
# Specific subreddits
sloppenhimer scrape -s AITA -s tifu -s confession

# More posts
sloppenhimer scrape --limit 50

# Different time range
sloppenhimer scrape --time month  # hour/day/week/month/year/all
```

### Video Options

```bash
# Download more videos
sloppenhimer fetch-videos --count 10

# Custom search
sloppenhimer fetch-videos --query "minecraft speedrun gameplay"
```

## Output

Videos are saved to `data/output/` as MP4 files:
- **Format**: 1080x1920 (9:16 vertical)
- **Codec**: H.264 video, AAC audio
- **Captions**: Burned-in, karaoke-style word highlighting

## Project Structure

```
sloppenhimer/
├── config/
│   ├── settings.py              # Pydantic configuration
│   └── prompts/
│       └── simplify_story.txt   # LLM prompt template
├── src/
│   ├── cli/main.py              # Typer CLI
│   ├── scrapers/
│   │   ├── reddit.py            # PRAW Reddit scraper
│   │   └── youtube.py           # yt-dlp downloader
│   ├── processors/
│   │   ├── llm.py               # Ollama integration
│   │   ├── tts.py               # edge-tts engine
│   │   └── transcription.py     # Whisper timestamps
│   ├── video/
│   │   ├── editor.py            # MoviePy editing
│   │   ├── captions.py          # Karaoke captions
│   │   └── assembler.py         # Final assembly
│   └── models/                  # Pydantic data models
├── data/
│   ├── stories/                 # Scraped Reddit stories (JSON)
│   ├── videos/                  # Downloaded gameplay
│   ├── audio/                   # Generated TTS audio
│   └── output/                  # Final videos
└── assets/
    ├── fonts/                   # Custom fonts
    └── voices/                  # Piper voice models
```

## Tech Stack

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - YouTube downloading
- **[PRAW](https://praw.readthedocs.io/)** - Reddit API wrapper
- **[Ollama](https://ollama.ai/)** - Local LLM inference
- **[edge-tts](https://github.com/rany2/edge-tts)** - Microsoft TTS
- **[OpenAI Whisper](https://github.com/openai/whisper)** - Speech transcription
- **[MoviePy](https://zulko.github.io/moviepy/)** - Video editing
- **[Typer](https://typer.tiangolo.com/)** - CLI framework

## TTS Voices

List available voices:
```bash
sloppenhimer voices
```

Popular options:
- `en-US-ChristopherNeural` - Male US (default)
- `en-US-JennyNeural` - Female US
- `en-GB-RyanNeural` - Male UK
- `en-GB-SoniaNeural` - Female UK
- `en-AU-WilliamNeural` - Male Australian

Change in `.env`:
```bash
EDGE_TTS_VOICE=en-US-JennyNeural
```

## Troubleshooting

### "Ollama not available"
```bash
# Start Ollama service
ollama serve

# In another terminal, pull a model
ollama pull llama3.2:3b
```

### "Reddit client_id not configured"
Make sure `.env` exists and has valid Reddit API credentials.

### "No background videos available"
```bash
sloppenhimer fetch-videos --count 5
```

### Slow video rendering
Use quick mode for faster (but simpler) captions:
```bash
sloppenhimer process <id> --quick
```

## License

MIT
