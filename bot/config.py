from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from bot.locales import fa

_REQUIRED = (
    "BOT_TOKEN",
    "ADMIN_IDS",
    "CHANNEL_ID",
    "GROUP_ID",
    "GITHUB_REPO",
    "GITHUB_TOKEN",
    "CLOUDFLARE_API_TOKEN",
    "CLOUDFLARE_ACCOUNT_ID",
    "KV_NAMESPACE_ID",
    "WORKER_URL",
    "BOT_USERNAME",
)


def _load_dotenv() -> None:
    candidates = (Path.cwd() / ".env", Path(__file__).resolve().parents[1] / ".env")
    seen: set[Path] = set()
    for path in candidates:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            key, sep, value = line.partition("=")
            if not sep:
                continue
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            if key:
                os.environ.setdefault(key, value)


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    admin_ids: tuple[int, ...]
    channel_id: int
    group_id: int
    github_repo: str
    github_token: str
    cloudflare_api_token: str
    cloudflare_account_id: str
    kv_namespace_id: str
    worker_url: str
    bot_username: str
    worker_secret: str = ""
    channel_link: str = "https://t.me/GalaxiesDrop"

    @property
    def first_admin_id(self) -> int:
        return self.admin_ids[0]

    def secret_values(self) -> tuple[str, ...]:
        return tuple(
            value
            for value in (
                self.bot_token,
                self.github_token,
                self.cloudflare_api_token,
                self.worker_secret,
            )
            if value
        )


def _fatal(message: str) -> "NoReturn":
    print(message, file=sys.stderr)
    raise SystemExit(1)


def load_config() -> Settings:
    _load_dotenv()
    missing = [key for key in _REQUIRED if not os.getenv(key, "").strip()]
    if missing:
        _fatal(fa.missing_keys(missing))

    try:
        admin_ids = tuple(
            dict.fromkeys(int(item.strip()) for item in os.environ["ADMIN_IDS"].split(",") if item.strip())
        )
        if not admin_ids:
            raise ValueError
    except ValueError:
        _fatal(fa.invalid_key("ADMIN_IDS"))

    try:
        channel_id = int(os.environ["CHANNEL_ID"])
    except ValueError:
        _fatal(fa.invalid_key("CHANNEL_ID"))

    try:
        group_id = int(os.environ["GROUP_ID"])
    except ValueError:
        _fatal(fa.invalid_key("GROUP_ID"))

    worker_url = os.environ["WORKER_URL"].strip().rstrip("/")
    bot_username = os.environ["BOT_USERNAME"].strip().lstrip("@")
    if not worker_url.startswith(("https://", "http://")):
        _fatal(fa.invalid_key("WORKER_URL"))
    if not bot_username:
        _fatal(fa.invalid_key("BOT_USERNAME"))

    channel_link = os.getenv("CHANNEL_LINK", "").strip() or "https://t.me/GalaxiesDrop"

    return Settings(
        bot_token=os.environ["BOT_TOKEN"].strip(),
        admin_ids=admin_ids,
        channel_id=channel_id,
        group_id=group_id,
        github_repo=os.environ["GITHUB_REPO"].strip(),
        github_token=os.environ["GITHUB_TOKEN"].strip(),
        cloudflare_api_token=os.environ["CLOUDFLARE_API_TOKEN"].strip(),
        cloudflare_account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"].strip(),
        kv_namespace_id=os.environ["KV_NAMESPACE_ID"].strip(),
        worker_url=worker_url,
        bot_username=bot_username,
        worker_secret=os.getenv("WORKER_SECRET", "").strip(),
        channel_link=channel_link,
    )
