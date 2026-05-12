import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qsl


TOKEN_PLACEHOLDERS = {
    "",
    "your_telegram_bot_token_here",
    "your_token_here",
}


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def is_real_token(token: str) -> bool:
    return bool(token and token.strip() not in TOKEN_PLACEHOLDERS)


def allowed_user_ids() -> set[str]:
    ids: set[str] = set()
    owner = os.getenv("TELEGRAM_OWNER_ID", "").strip()
    if owner and owner != "your_telegram_id_here":
        ids.add(owner)
    extra = os.getenv("TELEGRAM_ALLOWED_IDS", "")
    for value in extra.split(","):
        value = value.strip()
        if value:
            ids.add(value)
    return ids


def require_telegram_auth() -> bool:
    default = is_real_token(os.getenv("TELEGRAM_BOT_TOKEN", ""))
    return env_bool("GHOST_REQUIRE_TELEGRAM_AUTH", default)


def agent_token() -> str:
    return os.getenv("GHOST_AGENT_TOKEN", "").strip()


@dataclass
class TelegramSession:
    user_id: str
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    language_code: str = ""
    platform: str = "telegram"
    is_dev: bool = False

    @property
    def display_name(self) -> str:
        full = " ".join([self.first_name, self.last_name]).strip()
        return full or self.username or self.user_id or "Developer"

    def as_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "username": self.username,
            "language_code": self.language_code,
            "display_name": self.display_name,
            "platform": self.platform,
            "is_dev": self.is_dev,
        }


def dev_session() -> TelegramSession:
    return TelegramSession(
        user_id="dev",
        first_name="Developer",
        platform="browser",
        is_dev=True,
    )


def validate_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 86400,
) -> tuple[Optional[TelegramSession], Optional[str]]:
    if not init_data:
        return None, "Telegram initData topilmadi."
    if not is_real_token(bot_token):
        return None, "TELEGRAM_BOT_TOKEN sozlanmagan."

    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    except ValueError:
        return None, "Telegram initData formati noto'g'ri."

    received_hash = pairs.pop("hash", "")
    pairs.pop("signature", None)
    if not received_hash:
        return None, "Telegram initData hash topilmadi."

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(pairs.items())
    )
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        return None, "Telegram initData imzosi mos kelmadi."

    auth_date_raw = pairs.get("auth_date")
    try:
        auth_date = int(auth_date_raw or "0")
    except ValueError:
        return None, "Telegram auth_date noto'g'ri."

    now = int(time.time())
    if max_age_seconds > 0 and now - auth_date > max_age_seconds:
        return None, "Telegram sessiya muddati tugagan."
    if auth_date - now > 60:
        return None, "Telegram auth_date kelajak vaqtida."

    user_raw = pairs.get("user", "{}")
    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError:
        return None, "Telegram user ma'lumoti noto'g'ri."

    user_id = str(user.get("id", "")).strip()
    if not user_id:
        return None, "Telegram user id topilmadi."

    allowed = allowed_user_ids()
    if allowed and user_id not in allowed:
        return None, "Bu Telegram foydalanuvchiga ruxsat berilmagan."

    return TelegramSession(
        user_id=user_id,
        first_name=user.get("first_name", "") or "",
        last_name=user.get("last_name", "") or "",
        username=user.get("username", "") or "",
        language_code=user.get("language_code", "") or "",
    ), None
