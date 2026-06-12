"""
config.py — Cấu hình và helpers dùng chung cho seed scripts

Đọc cấu hình từ:
  1. File .env trong cùng thư mục với scripts
  2. File .env trong thư mục deploy/dev
  3. Biến môi trường (override .env)
"""

import logging
import os
import sys
from pathlib import Path

from backstage_client import BackstageConfig

# ------------------------------------------------------------------ #
# Đường dẫn
# ------------------------------------------------------------------ #

SCRIPTS_DIR = Path(__file__).parent.resolve()
SEED_DIR = SCRIPTS_DIR.parent
DATA_DIR = SEED_DIR / "data"
REPO_ROOT = SEED_DIR.parent

# ------------------------------------------------------------------ #
# Load .env
# ------------------------------------------------------------------ #


def _load_dotenv(env_path: Path) -> None:
    """Load file .env đơn giản (không dùng thư viện external)."""
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            # Chỉ set nếu chưa có trong environment (environment override .env)
            os.environ.setdefault(key, value)


def load_env() -> None:
    """Load .env từ các vị trí ưu tiên."""
    # Tìm file .env theo thứ tự ưu tiên
    candidates = [
        SCRIPTS_DIR / ".env",                          # seed/scripts/.env (ưu tiên nhất)
        SEED_DIR / ".env",                             # seed/.env
        REPO_ROOT / "deploy" / "dev" / ".env",        # deploy/dev/.env (server config)
        REPO_ROOT / ".env",                            # root .env
    ]
    loaded = False
    for path in candidates:
        if path.exists():
            _load_dotenv(path)
            logging.getLogger(__name__).debug("Loaded .env from: %s", path)
            loaded = True
            break

    if not loaded:
        logging.getLogger(__name__).warning(
            "No .env file found. Using environment variables only."
        )


# ------------------------------------------------------------------ #
# Logging
# ------------------------------------------------------------------ #


def setup_logging(level: str = "INFO", log_file: str = "") -> None:
    """Cấu hình logging có màu sắc cho console."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = []

    # Console handler với format đẹp
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(numeric_level)
    console.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s  %(levelname)-8s  %(name)-20s  %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    handlers.append(console)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)-8s %(name)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        handlers.append(file_handler)

    logging.basicConfig(level=numeric_level, handlers=handlers, force=True)


# ------------------------------------------------------------------ #
# Config factory
# ------------------------------------------------------------------ #


def get_config() -> BackstageConfig:
    """
    Tạo BackstageConfig từ environment variables.
    Phải được gọi sau load_env().
    """
    base_url = os.environ.get("BACKSTAGE_BASE_URL", "http://localhost:7007")
    token = os.environ.get("BACKSTAGE_TOKEN", "")
    max_retries = int(os.environ.get("MAX_RETRIES", "3"))
    request_delay = float(os.environ.get("REQUEST_DELAY", "0.2"))
    timeout = int(os.environ.get("REQUEST_TIMEOUT", "30"))

    return BackstageConfig(
        base_url=base_url,
        token=token,
        max_retries=max_retries,
        request_delay=request_delay,
        timeout=timeout,
    )


def get_data_dir() -> Path:
    """Trả về đường dẫn đến thư mục data."""
    data_dir_env = os.environ.get("DATA_DIR", "")
    if data_dir_env:
        p = Path(data_dir_env)
        if not p.is_absolute():
            p = SCRIPTS_DIR / p
        return p.resolve()
    return DATA_DIR


def init() -> tuple[BackstageConfig, Path]:
    """
    Khởi tạo toàn bộ: load .env, setup logging, tạo config.

    Returns:
        (config, data_dir)
    """
    load_env()
    setup_logging(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        log_file=os.environ.get("LOG_FILE", ""),
    )
    config = get_config()
    data_dir = get_data_dir()
    return config, data_dir
