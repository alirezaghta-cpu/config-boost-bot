"""Persian + English strings for ConfigBoost.

Every key exists in BOTH languages. The ``t()`` helper always returns text
in a single language; never mix FA/EN inside one rendered message.
"""

from __future__ import annotations

TEXTS: dict[str, dict[str, str]] = {
    "fa": {
        "welcome_title": "🎉 به ConfigBoost خوش آمدید!",
        "welcome_body": (
            "ربات رایگان اشتراک و کانفیگ‌های v2ray.\n"
            "برای شروع، لطفاً زبان خود را انتخاب کنید."
        ),
        "ask_language": "🌐 لطفاً زبان خود را انتخاب کنید:",
        "lang_chosen": "✅ زبان شما به فارسی تغییر کرد.",
        "menu_title": "🏠 منوی اصلی",
        "menu_subtitle": "یکی از گزینه‌های زیر را انتخاب کنید:",
        "btn_servers": "📡 سرورها",
        "btn_test": "⚡ تست سرور",
        "btn_my_servers": "👤 سرورهای من",
        "btn_refresh": "🔄 بروزرسانی",
        "btn_channel": "📢 کانال",
        "btn_guide": "📖 راهنما",
        "btn_change_lang": "🌐 تغییر زبان",
        "btn_soon_referral": "🎁 دعوت از دوستان (به‌زودی)",
        "btn_soon_subscription": "⭐ اشتراک ویژه (به‌زودی)",
        "btn_soon_admin": "🛠️ پنل مدیریت (به‌زودی)",
        "soon_msg": (
            "🚧 این قابلیت به‌زودی فعال خواهد شد.\n"
            "منتظر ما باشید! 💎"
        ),
        "servers_title": "📡 فهرست سرورها",
        "servers_empty": (
            "😔 در حال حاضر هیچ سرور فعالی موجود نیست.\n"
            "لطفاً بعداً دوباره تلاش کنید یا 🔄 بروزرسانی را بزنید."
        ),
        "servers_count": "تعداد: {n}",
        "test_pick": "⚡ لطفاً یک سرور برای تست انتخاب کنید:",
        "test_running": "⏳ در حال تست {host}:{port} ...",
        "test_ok": (
            "✅ تست موفق\n"
            "📍 میزبان: {host}\n"
            "🔌 پورت: {port}\n"
            "⏱️ تأخیر: {ms} میلی‌ثانیه"
        ),
        "test_fail": (
            "❌ تست ناموفق\n"
            "📍 میزبان: {host}\n"
            "🔌 پورت: {port}\n"
            "⏱️ پاسخ: بیش از {timeout} ثانیه"
        ),
        "test_unknown": "❓ نتیجه تست نامشخص بود.",
        "my_servers_title": "👤 سرورهای من",
        "my_servers_empty": (
            "📭 شما هنوز هیچ سرور اختصاصی ندارید.\n"
            "در Phase 2 سرورهای انتخابی شما اینجا نمایش داده می‌شوند."
        ),
        "refresh_done": "✅ فهرست سرورها با موفقیت بروزرسانی شد.\nتعداد: {n}",
        "refresh_empty": "ℹ️ بروزرسانی انجام شد ولی فایل سرورها خالی است.",
        "channel_title": "📢 کانال ما",
        "channel_missing": "😔 لینک کانال هنوز تنظیم نشده است.",
        "channel_link": "🔗 لینک کانال: {link}",
        "guide_title": "📖 راهنمای استفاده",
        "guide_body": (
            "برای اتصال، یکی از کلاینت‌های مناسب دستگاه خود را نصب کنید "
            "و لینک کانفیگ (vmess:// یا vless:// یا trojan://) را در آن وارد کنید.\n\n"
            "📱 اندروید:\n"
            "• v2rayNG\n"
            "• NekoBox\n\n"
            "📱 آیفون:\n"
            "• Streisand\n"
            "• V2Box\n\n"
            "💻 ویندوز:\n"
            "• v2rayN\n"
            "• Nekoray\n\n"
            "💻 مک:\n"
            "• V2RayXS\n"
            "• Nekoray\n\n"
            "🔧 مراحل کلی:\n"
            "1) کلاینت مناسب با دستگاه خود را نصب کنید.\n"
            "2) لینک کانفیگ را کپی کنید.\n"
            "3) در کلاینت، گزینه «افزودن از کلیپ‌بورد» یا «Import from clipboard» را بزنید.\n"
            "4) به سرور متصل شوید و از اینترنت آزاد لذت ببرید! 🚀"
        ),
        "help_title": "ℹ️ راهنمای دستورات",
        "help_body": (
            "دستورات موجود:\n"
            "/start - شروع و انتخاب زبان\n"
            "/menu - نمایش منوی اصلی\n"
            "/lang - تغییر زبان\n"
            "/servers - نمایش سرورها\n"
            "/test - تست سرور\n"
            "/status - وضعیت ربات\n"
            "/help - نمایش این راهنما\n"
            "/ref - دعوت از دوستان (به‌زودی)\n"
            "/subscribe - اشتراک ویژه (به‌زودی)\n"
            "/admin - پنل مدیریت (فقط مالک)"
        ),
        "status_ok": "✅ ربات فعال است.\n🕒 زمان: {time}\n📡 تعداد سرورها: {n}",
        "admin_welcome": (
            "🛠️ خوش آمدید به پنل مدیریت.\n"
            "⏱️ زمان: {time}\n"
            "📡 سرورها: {n}\n"
            "👥 کاربران: {u}"
        ),
        "admin_unauthorized": "⛔ این دستور فقط برای مدیران فعال است.",
        "back": "↩️ بازگشت به منو",
    },
    "en": {
        "welcome_title": "🎉 Welcome to ConfigBoost!",
        "welcome_body": (
            "Free bot for v2ray configs and subscriptions.\n"
            "To get started, please choose your language."
        ),
        "ask_language": "🌐 Please choose your language:",
        "lang_chosen": "✅ Your language has been set to English.",
        "menu_title": "🏠 Main Menu",
        "menu_subtitle": "Pick an option below:",
        "btn_servers": "📡 Servers",
        "btn_test": "⚡ Test Server",
        "btn_my_servers": "👤 My Servers",
        "btn_refresh": "🔄 Refresh",
        "btn_channel": "📢 Channel",
        "btn_guide": "📖 Guide",
        "btn_change_lang": "🌐 Change Language",
        "btn_soon_referral": "🎁 Invite Friends (Soon)",
        "btn_soon_subscription": "⭐ Subscription (Soon)",
        "btn_soon_admin": "🛠️ Admin Panel (Soon)",
        "soon_msg": (
            "🚧 This feature is coming soon.\n"
            "Stay tuned! 💎"
        ),
        "servers_title": "📡 Server List",
        "servers_empty": (
            "😔 No active servers are available right now.\n"
            "Please try again later or tap 🔄 Refresh."
        ),
        "servers_count": "Total: {n}",
        "test_pick": "⚡ Pick a server to test:",
        "test_running": "⏳ Testing {host}:{port} ...",
        "test_ok": (
            "✅ Test successful\n"
            "📍 Host: {host}\n"
            "🔌 Port: {port}\n"
            "⏱️ Latency: {ms} ms"
        ),
        "test_fail": (
            "❌ Test failed\n"
            "📍 Host: {host}\n"
            "🔌 Port: {port}\n"
            "⏱️ Response: over {timeout} seconds"
        ),
        "test_unknown": "❓ Test result was inconclusive.",
        "my_servers_title": "👤 My Servers",
        "my_servers_empty": (
            "📭 You don't have any assigned servers yet.\n"
            "In Phase 2, your saved servers will appear here."
        ),
        "refresh_done": "✅ Server list refreshed successfully.\nTotal: {n}",
        "refresh_empty": "ℹ️ Refresh done, but the server file is empty.",
        "channel_title": "📢 Our Channel",
        "channel_missing": "😔 The channel link is not configured yet.",
        "channel_link": "🔗 Channel link: {link}",
        "guide_title": "📖 User Guide",
        "guide_body": (
            "To connect, install a client for your device and paste a "
            "config link (vmess://, vless://, or trojan://).\n\n"
            "📱 Android:\n"
            "• v2rayNG\n"
            "• NekoBox\n\n"
            "📱 iPhone:\n"
            "• Streisand\n"
            "• V2Box\n\n"
            "💻 Windows:\n"
            "• v2rayN\n"
            "• Nekoray\n\n"
            "💻 macOS:\n"
            "• V2RayXS\n"
            "• Nekoray\n\n"
            "🔧 General steps:\n"
            "1) Install the right client for your device.\n"
            "2) Copy a config link.\n"
            "3) In the client, tap \"Add from clipboard\" / \"Import from clipboard\".\n"
            "4) Connect and enjoy a free internet! 🚀"
        ),
        "help_title": "ℹ️ Command Help",
        "help_body": (
            "Available commands:\n"
            "/start - Start and choose language\n"
            "/menu - Show main menu\n"
            "/lang - Change language\n"
            "/servers - List servers\n"
            "/test - Test a server\n"
            "/status - Bot status\n"
            "/help - Show this help\n"
            "/ref - Invite friends (soon)\n"
            "/subscribe - Subscription (soon)\n"
            "/admin - Admin panel (owner only)"
        ),
        "status_ok": "✅ Bot is online.\n🕒 Time: {time}\n📡 Servers: {n}",
        "admin_welcome": (
            "🛠️ Welcome to the admin panel.\n"
            "⏱️ Time: {time}\n"
            "📡 Servers: {n}\n"
            "👥 Users: {u}"
        ),
        "admin_unauthorized": "⛔ This command is restricted to admins.",
        "back": "↩️ Back to menu",
    },
}


LANG_LABELS: dict[str, str] = {
    "fa": "🇮🇷 فارسی",
    "en": "🇬🇧 English",
}


def t(key: str, lang: str, **kwargs) -> str:
    """Look up a translation key in the requested language.

    Falls back to English if the key is missing in the requested language,
    and to the raw key if it is missing everywhere. Persian/English text is
    never mixed in a single return value.
    """
    lang = lang if lang in TEXTS else "en"
    text = TEXTS[lang].get(key)
    if text is None:
        text = TEXTS["en"].get(key, key)
    if not kwargs:
        return text
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError):
        return text