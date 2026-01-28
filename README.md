# TrainBot - AI Prompt Engineering Trainer

**Type:** Telegram Bot with Educational AI Integration

A Telegram bot that teaches users to create effective prompts for text and image generation using modern AI APIs.

## Platform & Runtime Requirements

This is a **Telegram Bot** running within the Telegram ecosystem. It is platform-dependent by design and requires external infrastructure.

**Core Dependencies:**
- Telegram Bot API (bot token required)
- PostgreSQL 12+ database (async operations)
- LLM provider: LLM7 API
- Image generation provider: Together AI
- Python 3.8+ with asyncio runtime

**Why local execution without external services is not applicable:**
- Telegram Bot API connectivity requires network access and valid bot token
- PostgreSQL must be accessible (local Docker container or remote instance)
- AI provider credentials (LLM7, Together AI) required for generation features
- Admin features require Telegram user ID configuration

This is standard for Telegram Bot applications. The architecture is production-oriented from design.

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

## What to Review Instead of Running Locally

Best understood through code architecture and design patterns:

### Handler Architecture & State Management
- **Modular Handler Organization** (`/bot/handlers/`) – Independent handler modules (basic, admin, lessons, generation, quizzes) with clean separation of concerns
- **Middleware Pattern** – Session management with database transaction handling
- **ConversationHandler for Complex Flows** – Multi-step lesson navigation without losing user context

### Educational System Design
- **Lesson Progression Engine** – Step-by-step lesson delivery with progress persistence
- **Quiz System Architecture** – Quiz state management and assessment based on lesson completion
- **Content Seeding Pipeline** – Lesson initialization on startup for environment consistency

### AI Integration & Evaluation
- **Provider Resilience** – LLM7 and Together AI calls with retry logic and timeout handling
- **Quiz Grading Logic** – LLM-powered assessment of user answers with automated feedback
- **Image Generation Pipeline** – Together AI integration with quota tracking

### Quota & Access Control
- **Daily Quota Management** – Database-backed tracking with automatic midnight resets
- **Role-Based Access** – Middleware checking admin status from Telegram user IDs
- **Leaderboard System** – User progress aggregation and ranking

### Data Integrity & Concurrency
- **Async SQLAlchemy Patterns** – asyncpg enables non-blocking database operations
- **User Progress Atomicity** – Race condition prevention in progress updates
- **Session Isolation** – Concurrent user request isolation

## License

MIT License