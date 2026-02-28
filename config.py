import os
from dotenv import load_dotenv, dotenv_values
from dataclasses import dataclass
from urllib.parse import quote

# Load environment variables from .env file
load_dotenv()

# Load .env file for direct access to values with special characters
_env_values = dotenv_values(".env")


@dataclass
class DatabaseConfig:
    host: str
    port: int
    name: str
    user: str
    password: str

    def get_url(self) -> str:
        # URL encode the password to handle special characters
        encoded_password = quote(self.password, safe='')
        return f"postgresql+asyncpg://{self.user}:{encoded_password}@{self.host}:{self.port}/{self.name}"


@dataclass
class BotConfig:
    token: str
    admin_id: int


@dataclass
class CloudflareConfig:
    account_id: str
    api_token: str


@dataclass
class Config:
    bot: BotConfig
    db: DatabaseConfig
    cloudflare: CloudflareConfig


def load_config() -> Config:
    return Config(
        bot=BotConfig(
            token=os.getenv("BOT_TOKEN"),
            admin_id=int(os.getenv("ADMIN_ID", 0)),
        ),
        db=DatabaseConfig(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432)),
            name=os.getenv("DB_NAME", "trainbot"),
            user=os.getenv("DB_USER", "postgres"),
            password=_env_values.get("DB_PASS", ""),  # Use direct parsing for special characters
        ),
        cloudflare=CloudflareConfig(
            account_id=os.getenv("CLOUDFLARE_ACCOUNT_ID", ""),
            api_token=os.getenv("CLOUDFLARE_API_TOKEN", ""),
        ),
    )


config = load_config()