import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


class Config:
    """Configuration class for SuperBox"""

    def __init__(self) -> None:
        # API Configurations
        self.SUPERBOX_API_URL = get_env("SUPERBOX_API_URL")

        # Cloudflare Configurations
        self.CLOUDFLARE_ACCOUNT_ID = get_env("CLOUDFLARE_ACCOUNT_ID")
        self.CLOUDFLARE_R2_ACCESS_KEY_ID = get_env("CLOUDFLARE_R2_ACCESS_KEY_ID")
        self.CLOUDFLARE_R2_SECRET_ACCESS_KEY = get_env("CLOUDFLARE_R2_SECRET_ACCESS_KEY")
        self.CLOUDFLARE_R2_BUCKET_NAME = get_env("CLOUDFLARE_R2_BUCKET_NAME")
        self.CLOUDFLARE_WORKER_URL = get_env("CLOUDFLARE_WORKER_URL")

        # Firebase Configurations
        self.FIREBASE_API_KEY = get_env("FIREBASE_API_KEY")
        self.FIREBASE_PROJECT_ID = get_env("FIREBASE_PROJECT_ID")

        # OAuth Configurations
        self.GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
        self.GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
        self.GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
        self.GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")

        # Scanners Configurations
        self.SONAR_TOKEN = get_env("SONAR_TOKEN")
        self.SONAR_ORGANIZATION = get_env("SONAR_ORGANIZATION")
        self.SNYK_API_TOKEN = get_env("SNYK_API_TOKEN")
        self.GITGUARDIAN_API_KEY = get_env("GITGUARDIAN_API_KEY")

        # Razorpay Configurations
        self.RAZORPAY_KEY_ID = get_env("RAZORPAY_KEY_ID")
        self.RAZORPAY_KEY_SECRET = get_env("RAZORPAY_KEY_SECRET")

    def validate_server(self) -> bool:
        """Validate required configuration for server"""
        required = {
            "SUPERBOX_API_URL": self.SUPERBOX_API_URL,
            "CLOUDFLARE_ACCOUNT_ID": self.CLOUDFLARE_ACCOUNT_ID,
            "CLOUDFLARE_R2_ACCESS_KEY_ID": self.CLOUDFLARE_R2_ACCESS_KEY_ID,
            "CLOUDFLARE_R2_SECRET_ACCESS_KEY": self.CLOUDFLARE_R2_SECRET_ACCESS_KEY,
            "CLOUDFLARE_R2_BUCKET_NAME": self.CLOUDFLARE_R2_BUCKET_NAME,
            "FIREBASE_API_KEY": self.FIREBASE_API_KEY,
            "FIREBASE_PROJECT_ID": self.FIREBASE_PROJECT_ID,
            "RAZORPAY_KEY_ID": self.RAZORPAY_KEY_ID,
            "RAZORPAY_KEY_SECRET": self.RAZORPAY_KEY_SECRET,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(f"Missing required config: {', '.join(missing)}")
        return True

    def validate_cli(self) -> bool:
        """Validate required configuration for CLI"""
        required = {
            "SUPERBOX_API_URL": self.SUPERBOX_API_URL,
            "CLOUDFLARE_ACCOUNT_ID": self.CLOUDFLARE_ACCOUNT_ID,
            "CLOUDFLARE_R2_ACCESS_KEY_ID": self.CLOUDFLARE_R2_ACCESS_KEY_ID,
            "CLOUDFLARE_R2_SECRET_ACCESS_KEY": self.CLOUDFLARE_R2_SECRET_ACCESS_KEY,
            "CLOUDFLARE_R2_BUCKET_NAME": self.CLOUDFLARE_R2_BUCKET_NAME,
            "FIREBASE_API_KEY": self.FIREBASE_API_KEY,
            "FIREBASE_PROJECT_ID": self.FIREBASE_PROJECT_ID,
            "SONAR_TOKEN": self.SONAR_TOKEN,
            "SONAR_ORGANIZATION": self.SONAR_ORGANIZATION,
            "SNYK_API_TOKEN": self.SNYK_API_TOKEN,
            "GITGUARDIAN_API_KEY": self.GITGUARDIAN_API_KEY,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(f"Missing required config: {', '.join(missing)}")
        return True


def load_env(env_path: Optional[os.PathLike | str] = None) -> None:
    """Load environment variables from .env file"""
    if env_path is None:
        env_path = Path.cwd() / ".env"
    else:
        env_path = Path(env_path)

    if env_path.exists():
        load_dotenv(env_path)


def get_env(key: str) -> str:
    """Get environment variable - raises error if not found."""
    value = os.environ.get(key)
    if value is None:
        raise ValueError(f"Required environment variable '{key}' not found")
    return value
