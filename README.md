# ConfigBoost — Free v2ray Config Telegram Bot (Phase 1)

A lightweight, single-process Telegram bot that distributes free v2ray
configs. Phase 1 covers language selection, an inline main menu, server
listing, TCP latency testing, a "my servers" placeholder, refresh,
channel link, guide, and a few "coming soon" buttons.

Server data is collected by an external **n8n** workflow that periodically
fetches free configs from public GitHub repositories and writes them to
`data/servers.json`. This bot only reads that file and reacts to user
input — it does not crawl the internet itself.

---

## Features (Phase 1)

- 🇮🇷 / 🇬🇧 Bilingual UI (Persian + English); no mixed languages in one message
- 🚀 Inline main menu with emoji-rich buttons
- 📡 Server list read from `data/servers.json`
- ⚡ TCP-connect latency test with a 3s timeout
- 👤 "My Servers" empty-state placeholder (Phase 2 hook)
- 🔄 Refresh re-reads `data/servers.json` from disk
- 📢 Channel button using `data/channel.json`
- 📖 Guide for v2rayNG, NekoBox, v2rayN, Nekoray, Streisand, V2Box, V2RayXS
- 🚧 "Soon" placeholders for referral, subscription, and admin panel
- 🛠️ `/admin` command restricted to user IDs in `ADMIN_IDS`

---

## Project Layout

```
.
├── README.md
├── bot/
│   ├── main.py             # bot entry point
│   ├── i18n.py             # Persian + English strings
│   └── data_sources.py     # JSON I/O for ./data
├── data/                   # created automatically on first run
│   ├── servers.json        # written by n8n
│   ├── channel.json        # written by n8n
│   └── users.json          # written by the bot
```

> The `bot` package works as a PEP 420 *namespace package* (no
> `__init__.py` required) when launched with `python -m bot.main`. If
> you prefer a regular package, add an empty `bot/__init__.py`.

---

## Requirements

- Python 3.10+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

---

## Environment Variables

| Variable     | Required | Description                                                            |
|--------------|----------|------------------------------------------------------------------------|
| `BOT_TOKEN`  | **yes**  | Telegram bot token from @BotFather                                     |
| `ADMIN_IDS`  | no       | Comma-separated Telegram user IDs allowed to use `/admin`             |
| `DATA_DIR`   | no       | Override the `./data` folder (default: project root `./data`)         |
| `LOG_LEVEL`  | no       | Python logging level, e.g. `INFO`, `DEBUG` (default `INFO`)           |

> The bot **never** hardcodes tokens or secrets. `BOT_TOKEN` must be
> provided via the environment.

---

## Install & Run

```bash
# 1. clone
git clone https://github.com/alirezaghta-cpu/config-boost-bot.git
cd config-boost-bot

# 2. virtualenv
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. install
pip install -r bot/requirements.txt

# 4. configure
export BOT_TOKEN="<paste-from-botfather>"
export ADMIN_IDS="11111111,22222222"   # optional

# 5. run (long polling, single process)
python -m bot.main
```

On first start the bot creates `data/servers.json`, `data/channel.json`,
and `data/users.json` with safe empty defaults. The bot stays usable
even before n8n has produced any server data.

---

## Data Files

### `data/servers.json` (written by **n8n**)

Array of server objects. Any field may be missing; the bot reads
defensively.

```json
[
  {
    "id": "srv-001",
    "name": "Germany-VLESS",
    "url": "vless://uuid@host:443?type=tcp#Germany-VLESS",
    "protocol": "vless",
    "host": "1.2.3.4",
    "port": 443,
    "source": "ebrasha/free-v2ray-public-list",
    "lastCheck": "2025-01-01T00:00:00Z",
    "alive": true
  }
]
```

### `data/channel.json` (written by **n8n**)

```json
{
  "username": "@ConfigBoost",
  "link": "https://t.me/ConfigBoost"
}
```

### `data/users.json` (written by **the bot**)

```json
{
  "123456789": {
    "lang": "fa",
    "first_seen": "2025-01-01T00:00:00+00:00",
    "assigned": []
  }
}
```

---

## Commands

| Command       | Description                                                  |
|---------------|--------------------------------------------------------------|
| `/start`      | Show welcome + language picker                               |
| `/menu`       | Open the inline main menu                                    |
| `/lang`       | Change language                                              |
| `/servers`    | List servers                                                 |
| `/test`       | Pick a server to TCP-test                                    |
| `/status`     | Show bot status and server count                             |
| `/help`       | Show help                                                    |
| `/ref`        | "Soon" placeholder (referral)                                |
| `/subscribe`  | "Soon" placeholder (subscription)                            |
| `/admin`      | Admin panel (only if user id is in `ADMIN_IDS`)             |

---

## Suggested free config sources (for n8n)

- `ebrasha/free-v2ray-public-list`
- `MatinGhanbari/v2ray-configs`
- `Epodonios/v2ray-configs`
- `0xRadikal/Free-v2ray-Configs`
- `Delta-Kronecker/V2ray-Config`

Refresh every 5–15 minutes from the GitHub `raw` endpoints, normalize
each entry into the `servers.json` schema above, and write atomically.

---

## Phase 2 Hooks

- The **My Servers** button currently shows a friendly empty-state
  message. The user record already has an `assigned: []` field ready to
  be populated when subscriptions are introduced.
- **"Soon"** buttons (referral / subscription / admin panel) already
  route through real callback handlers and can be replaced with full
  flows without changing the menu layout.
- The **Test Server** action is a TCP connect with a 3s timeout. A full
  v2ray handshake test can be added later behind the same callback.