"""ConfigBoost — Phase 1 Telegram bot entry point.

Long polling, single-process, no external database. Reads
``data/servers.json`` and ``data/channel.json`` written by n8n and
keeps per-user language preference in ``data/users.json``.

Run with::

    export BOT_TOKEN=...
    python -m bot.main
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from bot import data_sources as ds
from bot.i18n import LANG_LABELS, t

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, LOG_LEVEL, logging.INFO),
)
logger = logging.getLogger("configboost")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

ADMIN_IDS: set[int] = {
    int(x.strip())
    for x in os.environ.get("ADMIN_IDS", "").replace(";", ",").split(",")
    if x.strip().isdigit()
}

SUPPORTED_LANGS: tuple[str, ...] = ("fa", "en")
DEFAULT_LANG = "en"
TEST_TIMEOUT_S = 3.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _lang_of(user_data: dict | None) -> str | None:
    if not user_data:
        return None
    lang = user_data.get("lang")
    return lang if lang in SUPPORTED_LANGS else None


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _safe_answer(query) -> None:
    try:
        await query.answer()
    except Exception:
        # Callback may have expired; safe to ignore.
        pass


def _language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(LANG_LABELS["fa"], callback_data="lang:fa")],
            [InlineKeyboardButton(LANG_LABELS["en"], callback_data="lang:en")],
        ]
    )


def _main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t("btn_servers", lang), callback_data="menu:servers"),
                InlineKeyboardButton(t("btn_test", lang), callback_data="menu:test"),
            ],
            [
                InlineKeyboardButton(t("btn_my_servers", lang), callback_data="menu:my"),
                InlineKeyboardButton(t("btn_refresh", lang), callback_data="menu:refresh"),
            ],
            [
                InlineKeyboardButton(t("btn_channel", lang), callback_data="menu:channel"),
                InlineKeyboardButton(t("btn_guide", lang), callback_data="menu:guide"),
            ],
            [
                InlineKeyboardButton(t("btn_change_lang", lang), callback_data="menu:lang"),
            ],
            [
                InlineKeyboardButton(t("btn_soon_referral", lang), callback_data="menu:soon:ref"),
            ],
            [
                InlineKeyboardButton(t("btn_soon_subscription", lang), callback_data="menu:soon:sub"),
            ],
            [
                InlineKeyboardButton(t("btn_soon_admin", lang), callback_data="menu:soon:admin"),
            ],
        ]
    )


def _format_servers_list(servers: list[dict], lang: str) -> str:
    lines = [t("servers_title", lang), ""]
    for idx, srv in enumerate(servers, start=1):
        name = str(srv.get("name") or f"Server-{idx}")
        proto = str(srv.get("protocol") or "-")
        host = str(srv.get("host") or "?")
        port = srv.get("port", "?")
        lines.append(f"{idx}. {name} | {proto} | {host}:{port}")
    lines.append("")
    lines.append(t("servers_count", lang, n=len(servers)))
    return "\n".join(lines)


def _test_buttons(servers: list[dict], lang: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for idx, srv in enumerate(servers):
        name = str(srv.get("name") or f"Server-{idx + 1}")
        if len(name) > 32:
            name = name[:29] + "..."
        rows.append(
            [InlineKeyboardButton(name, callback_data=f"test:server:{idx}")]
        )
    rows.append([InlineKeyboardButton(t("back", lang), callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


async def _edit_or_send(query, context, text: str, reply_markup=None) -> None:
    """Edit the callback's message, fall back to a new send on failure."""
    try:
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
        return
    except Exception:
        pass
    if query.message is None:
        return
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=text,
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


async def _prompt_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    await update.message.reply_text(
        t("ask_language", DEFAULT_LANG),
        reply_markup=_language_keyboard(),
    )


async def _prompt_language_callback(query, context) -> None:
    await _edit_or_send(
        query,
        context,
        t("ask_language", DEFAULT_LANG),
        reply_markup=_language_keyboard(),
    )


async def _tcp_latency_ms(host: str, port: int, timeout: float = TEST_TIMEOUT_S) -> float | None:
    """Open a TCP connection to ``host:port`` and measure the connect latency.

    Returns latency in milliseconds, or ``None`` if the connection failed
    or timed out. Phase 1 deliberately avoids a full v2ray handshake.
    """
    start = time.perf_counter()
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        return round((time.perf_counter() - start) * 1000.0, 1)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or update.message is None:
        return
    text = (
        f"{t('welcome_title', DEFAULT_LANG)}\n\n"
        f"{t('welcome_body', DEFAULT_LANG)}\n\n"
        f"{t('ask_language', DEFAULT_LANG)}"
    )
    await update.message.reply_text(text, reply_markup=_language_keyboard())


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or update.message is None:
        return
    lang = _lang_of(ds.get_user(user.id))
    if not lang:
        await _prompt_language(update, context)
        return
    text = f"{t('menu_title', lang)}\n\n{t('menu_subtitle', lang)}"
    await update.message.reply_text(
        text,
        reply_markup=_main_menu_keyboard(lang),
    )


async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _prompt_language(update, context)


async def cmd_servers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or update.message is None:
        return
    lang = _lang_of(ds.get_user(user.id))
    if not lang:
        await _prompt_language(update, context)
        return
    servers = ds.load_servers()
    if not servers:
        await update.message.reply_text(
            t("servers_empty", lang),
            reply_markup=_main_menu_keyboard(lang),
        )
        return
    await update.message.reply_text(
        _format_servers_list(servers, lang),
        reply_markup=_main_menu_keyboard(lang),
    )


async def cmd_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or update.message is None:
        return
    lang = _lang_of(ds.get_user(user.id))
    if not lang:
        await _prompt_language(update, context)
        return
    servers = ds.load_servers()
    if not servers:
        await update.message.reply_text(
            t("servers_empty", lang),
            reply_markup=_main_menu_keyboard(lang),
        )
        return
    await update.message.reply_text(
        t("test_pick", lang),
        reply_markup=_test_buttons(servers, lang),
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or update.message is None:
        return
    lang = _lang_of(ds.get_user(user.id))
    if not lang:
        await _prompt_language(update, context)
        return
    n = len(ds.load_servers())
    await update.message.reply_text(
        t("status_ok", lang, time=_now_str(), n=n),
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or update.message is None:
        return
    lang = _lang_of(ds.get_user(user.id))
    if not lang:
        await _prompt_language(update, context)
        return
    await update.message.reply_text(
        f"{t('help_title', lang)}\n\n{t('help_body', lang)}"
    )


async def cmd_ref(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    user = update.effective_user
    lang = _lang_of(ds.get_user(user.id) if user else None) or DEFAULT_LANG
    await update.message.reply_text(t("soon_msg", lang))


async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    user = update.effective_user
    lang = _lang_of(ds.get_user(user.id) if user else None) or DEFAULT_LANG
    await update.message.reply_text(t("soon_msg", lang))


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or update.message is None:
        return
    lang = _lang_of(ds.get_user(user.id)) or DEFAULT_LANG
    if not _is_admin(user.id):
        await update.message.reply_text(t("admin_unauthorized", lang))
        return
    n = len(ds.load_servers())
    u = ds.count_users()
    await update.message.reply_text(
        t("admin_welcome", lang, time=_now_str(), n=n, u=u),
    )


# ---------------------------------------------------------------------------
# Callback handlers
# ---------------------------------------------------------------------------


async def on_lang_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data or query.message is None:
        return
    await _safe_answer(query)
    _, chosen = query.data.split(":", 1)
    if chosen not in SUPPORTED_LANGS:
        return
    user = query.from_user
    ds.set_user_lang(user.id, chosen)
    text = (
        f"{t('lang_chosen', chosen)}\n\n"
        f"{t('menu_title', chosen)}\n\n"
        f"{t('menu_subtitle', chosen)}"
    )
    await _edit_or_send(query, context, text, reply_markup=_main_menu_keyboard(chosen))


async def on_menu_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data or query.message is None:
        return
    await _safe_answer(query)
    parts = query.data.split(":")
    action = parts[1] if len(parts) >= 2 else ""
    user = query.from_user
    lang = _lang_of(ds.get_user(user.id)) or DEFAULT_LANG

    if action == "home":
        await _edit_or_send(
            query,
            context,
            f"{t('menu_title', lang)}\n\n{t('menu_subtitle', lang)}",
            reply_markup=_main_menu_keyboard(lang),
        )
        return

    if action == "lang":
        await _prompt_language_callback(query, context)
        return

    if action == "servers":
        servers = ds.load_servers()
        if not servers:
            await _edit_or_send(
                query,
                context,
                t("servers_empty", lang),
                reply_markup=_main_menu_keyboard(lang),
            )
            return
        await _edit_or_send(
            query,
            context,
            _format_servers_list(servers, lang),
            reply_markup=_main_menu_keyboard(lang),
        )
        return

    if action == "test":
        servers = ds.load_servers()
        if not servers:
            await _edit_or_send(
                query,
                context,
                t("servers_empty", lang),
                reply_markup=_main_menu_keyboard(lang),
            )
            return
        await _edit_or_send(
            query,
            context,
            t("test_pick", lang),
            reply_markup=_test_buttons(servers, lang),
        )
        return

    if action == "my":
        await _edit_or_send(
            query,
            context,
            f"{t('my_servers_title', lang)}\n\n{t('my_servers_empty', lang)}",
            reply_markup=_main_menu_keyboard(lang),
        )
        return

    if action == "refresh":
        servers = ds.load_servers()
        text = (
            t("refresh_done", lang, n=len(servers))
            if servers
            else t("refresh_empty", lang)
        )
        await _edit_or_send(query, context, text, reply_markup=_main_menu_keyboard(lang))
        return

    if action == "channel":
        channel = ds.load_channel()
        link = channel.get("link") or channel.get("username") or ""
        if link:
            body = t("channel_link", lang, link=link)
        else:
            body = t("channel_missing", lang)
        await _edit_or_send(
            query,
            context,
            f"{t('channel_title', lang)}\n\n{body}",
            reply_markup=_main_menu_keyboard(lang),
        )
        return

    if action == "guide":
        await _edit_or_send(
            query,
            context,
            f"{t('guide_title', lang)}\n\n{t('guide_body', lang)}",
            reply_markup=_main_menu_keyboard(lang),
        )
        return

    if action == "soon":
        kind = parts[2] if len(parts) >= 3 else ""
        if kind == "admin" and not _is_admin(user.id):
            await _edit_or_send(
                query,
                context,
                t("admin_unauthorized", lang),
                reply_markup=_main_menu_keyboard(lang),
            )
            return
        await _edit_or_send(
            query,
            context,
            t("soon_msg", lang),
            reply_markup=_main_menu_keyboard(lang),
        )
        return


async def on_test_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data or query.message is None:
        return
    await _safe_answer(query)
    parts = query.data.split(":")
    if len(parts) < 3 or parts[1] != "server":
        return
    try:
        idx = int(parts[2])
    except ValueError:
        return

    servers = ds.load_servers()
    if idx < 0 or idx >= len(servers):
        return

    srv = servers[idx]
    host = str(srv.get("host") or "")
    try:
        port = int(srv.get("port") or 0)
    except (TypeError, ValueError):
        port = 0

    lang = _lang_of(ds.get_user(query.from_user.id)) or DEFAULT_LANG

    if not host or port <= 0:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=t("test_unknown", lang),
            reply_markup=_main_menu_keyboard(lang),
        )
        return

    # Show "Testing..." by editing the current message.
    try:
        await query.edit_message_text(
            t("test_running", lang, host=host, port=port),
            reply_markup=None,
        )
    except Exception:
        # Editing can fail if the message is too old; safe to ignore.
        pass

    ms = await _tcp_latency_ms(host, port, timeout=TEST_TIMEOUT_S)
    if ms is None:
        text = t("test_fail", lang, host=host, port=port, timeout=int(TEST_TIMEOUT_S))
    else:
        text = t("test_ok", lang, host=host, port=port, ms=ms)

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=text,
        reply_markup=_main_menu_keyboard(lang),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is required")

    if not ADMIN_IDS:
        logger.warning(
            "ADMIN_IDS is empty; /admin and admin-only callbacks will reject everyone."
        )

    # Make sure data files exist with safe defaults before we start polling.
    ds.ensure_files()

    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("lang", cmd_lang))
    app.add_handler(CommandHandler("servers", cmd_servers))
    app.add_handler(CommandHandler("test", cmd_test))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("ref", cmd_ref))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("admin", cmd_admin))

    # Callbacks
    app.add_handler(CallbackQueryHandler(on_lang_pick, pattern=r"^lang:"))
    app.add_handler(CallbackQueryHandler(on_test_pick, pattern=r"^test:server:"))
    app.add_handler(CallbackQueryHandler(on_menu_action, pattern=r"^menu:"))

    logger.info("ConfigBoost Phase 1 starting (long polling)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()