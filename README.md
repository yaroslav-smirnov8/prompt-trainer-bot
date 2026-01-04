# TrainBot - AI Prompt Engineering Trainer

A Telegram bot that teaches users to create effective prompts for text and image generation using modern AI APIs.

## Features

- **Text Prompt Lessons**: Learn to create effective prompts for text generation
- **Image Prompt Lessons**: Master the art of creating prompts for image generation
- **Interactive Quizzes**: Test your knowledge with AI-powered evaluation
- **Practice Generation**: Test your prompts with real AI models
- **Progress Tracking**: Monitor your learning progress
- **Leaderboard**: Compare your skills with other users

## Architecture

The bot uses:
- **Python 3** with asyncio
- **aiogram 3** for Telegram Bot API
- **SQLAlchemy async** with asyncpg for PostgreSQL
- **LLM7 API** for text generation
- **Together AI Flux Schnell** for image generation
- **Loguru** for logging

## API Keys Setup

Create a `.env` file with the following variables:

```env
# Bot settings
BOT_TOKEN=your_telegram_bot_token

# Database settings
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trainbot
DB_USER=postgres
DB_PASS=your_password

# AI API settings
LLM7_API_KEY=your_llm7_api_key
TOGETHER_API_KEY=your_together_ai_api_key

# Other settings
ADMIN_ID=your_telegram_user_id
```

## Setup & Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up PostgreSQL database
4. Create `.env` file with your credentials
5. Run the bot: `python main.py`

## API Integration

The bot connects to modern AI APIs:
- Text generation via LLM7 API
- Image generation via Together AI Flux Schnell model
- Evaluation and scoring via AI-powered services

## License

MIT License