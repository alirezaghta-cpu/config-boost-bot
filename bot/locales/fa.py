"""تمام متن‌های کاربرمحور فارسی ربات در این ماژول نگهداری می‌شود."""

import html

_DIGIT_MAP = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def num(value: object) -> str:
    return str(value).translate(_DIGIT_MAP)


def missing_keys(keys: list[str]) -> str:
    return "\n".join(f"کلید گمشده: {key}" for key in keys)


def invalid_key(key: str) -> str:
    return f"مقدار کلید نامعتبر است: {key}"


BTN_RECEIVE = "دریافت کانفیگ این هفته"
BTN_TEST = "تست و لوکیشن"
BTN_QUOTA = "📦 دریافت کانفیگ رایگان"
BTN_REFERRAL = "زیرمجموعه‌گیری"
BTN_BUY = "خرید پلن"
BTN_HELP = "راهنما"
BTN_SUPPORT = "پشتیبانی"
BTN_ADMIN = "پنل ادمین"
BTN_COPY = "کپی کانفیگ"
BTN_QR = "QR"
BTN_COPY_FROM_BOT = "کپی از ربات"
BTN_SOON = "به‌زودی"
BTN_ORDERS = "سفارش‌ها"
BTN_BACK = "بازگشت"
BTN_CONFIRM = "تأیید"
BTN_CANCEL = "لغو"
BTN_IRAN_VOTE_OK = "✅ وصل شدم (از ایران)"
BTN_IRAN_VOTE_FAIL = "❌ وصل نشدم"
BTN_IRAN_OK = "✅ وصل شدم — ارسال فوری"
BTN_IRAN_FAIL = "❌ وصل نشدم — کانفیگ بعدی"
ADMIN_MODE_H5 = "هر ۵ ساعت"
DATA_CAP_GB: int = 5
IRAN_VOTE_OK_SAVED = "✅ گزارش «وصل شد» برای این کانفیگ ثبت شد. ممنون!"
IRAN_VOTE_FAIL_SAVED = "❌ گزارش «قطع شد» برای این کانفیگ ثبت شد. ممنون!"
IRAN_VOTE_ONLY_DELIVERED = (
    "گزارش فقط برای کانفیگ‌هایی که قبلاً به شما تحویل شده‌اند ثبت می‌شود."
)
IRAN_REPORT_PROMPT = (
    "اگر الان با آیپی ایران وصل شدید یا قطع شدید، یکی از دکمه‌های زیر را بزنید:"
)


def data_line(remaining_gb: float | None = None) -> str:
    if remaining_gb is not None:
        return f"حجم باقی‌مانده: {num(remaining_gb)} از {num(DATA_CAP_GB)} گیگ"
    return "حجم: نامحدود ← سقف هر کانفیگ: ۵ گیگ"


def iran_line(ok: int = 0, fail: int = 0) -> str:
    if ok == 0 and fail == 0:
        return (
            "اتصال از ایران: هنوز گزارشی ثبت نشده؛ "
            "اگر با آیپی ایران وصل شدید گزارش بدهید"
        )
    return f"اتصال از ایران: ✅ {num(ok)} موفق / ❌ {num(fail)} ناموفق"


WELCOME_TEXT = (
    "سلام! خوش اومدی 👋\n\n"
    "اینجا می‌تونی:\n"
    "🎁 کانفیگ رایگان دریافت کنی\n"
    "🇮🇷 وصل‌شدن یا نشدن از ایران را با دکمه‌های ✅ و ❌ گزارش کنی\n"
    "📱 کد QR کانفیگ تحویل‌گرفته‌شده را بگیری\n"
    "👥 با هر ۲ زیرمجموعه واجد شرایط، ۱ کانفیگ رایگان هفتگی ۵ گیگ بگیری\n"
    "📡 از ارسال خودکار کانفیگ‌های سالم هر ۵ ساعت استفاده کنی\n\n"
    "از منوی زیر یک گزینه را انتخاب کن."
)
WELCOME = WELCOME_TEXT
GENERIC_ERROR = "متأسفانه خطایی رخ داد. لطفاً کمی بعد دوباره تلاش کنید."
RATE_LIMIT = "درخواست‌ها خیلی سریع ارسال شده‌اند. لطفاً کمی بعد دوباره تلاش کنید."
IGNORED_CONTENT = "فقط متن یا فایل پذیرفته می‌شود."
NO_HEALTHY_CONFIG = "این هفته کانفیگ تست‌شده موجود نیست"
CONFIG_TEST_FAILED = "تست اتصال ناموفق بود؛ این کانفیگ تحویل یا منتشر نشد."
CONFIG_NOT_FOUND = "کانفیگ پیدا نشد یا دیگر معتبر نیست."
COPY_DENIED = "این کانفیگ قبلاً به شما تحویل نشده است؛ فقط پیش‌نمایش لوکیشن نمایش داده می‌شود."
QR_DENIED = COPY_DENIED
TEST_PROMPT = "یک URI از نوع vless، vmess، trojan یا ss بفرستید."
INVALID_URI = "فرمت کانفیگ معتبر نیست."
TEST_DAILY_LIMIT = "تست رایگان امروز تمام شده است. هر کاربر روزانه ۳ تست دارد."
TEST_24H_LIMIT = "برای همین کانفیگ در هر ۲۴ ساعت فقط یک تست تازه انجام می‌شود؛ نتیجهٔ ذخیره‌شده نمایش داده شد."
SUPPORT_PROMPT = "پیام یا فایل خود را بفرستید تا برای ادمین ارسال شود."
SUPPORT_SENT = "پیام شما برای ادمین ارسال شد."
SUPPORT_LIMIT = "حد پشتیبانی شما ۲ پیام در ساعت است."
NO_ADMIN = "ادمینی برای دریافت پیام پشتیبانی تنظیم نشده است."
REFERRAL_CAP_LOG = "سقف ۱۰ دعوت جدید روزانه برای دعوت‌کننده رد شد."
REFERRAL_SELF_LOG = "دعوت از خود رد شد."
REFERRAL_ACCEPTED = "دعوت با موفقیت ثبت شد."
REFERRAL_PENDING = "زیرمجموعه پس از گرفتن اولین کانفیگ معتبر می‌شود."
REFERRAL_QUALIFIED_LOG = "یک زیرمجموعه پس از دریافت اولین کانفیگ واجد شرایط شد."

REFERRAL_LAW = (
    "هر ۲ زیرمجموعه واجد شرایط = ۱ کانفیگ رایگان هفتگی ۵ گیگ\n"
    "کف روزانه دعوت: ۱۰ نفر\n"
    "اولین دعوت‌کننده برنده است\n"
    "خوددعوتی ممنوع"
)

PURCHASE_TEXT = (
    "فروش فعال نیست و تعداد کانفیگ رایگان را زیاد نمی‌کند. فعلاً دریافت هفتگی و پاداش زیرمجموعه فعال است."
)
PLAN_LIGHT = "سبک ۲۰ گیگ"
PLAN_STANDARD = "استاندارد ۵۰ گیگ"
PLAN_PRO = "پرو ۱۲۰ گیگ"
PLAN_FAIR = "نامحدود منصفانه"
PLAN_SERVER = "سرور اختصاصی"
NOT_ORDERED = "سفارشی نیست"

HELP_TEXT = (
    "راهنمای سریع 🧭\n\n"
    "🎁 دریافت کانفیگ رایگان\n"
    "• هر هفته ۱ کانفیگ پایه داری.\n"
    "• هر ۲ زیرمجموعه واجد شرایط، ۱ کانفیگ رایگان هفتگی ۵ گیگ اضافه می‌کند.\n"
    "• زیرمجموعه وقتی واجد شرایط است که با لینک تو وارد شود و حداقل ۱ کانفیگ بگیرد.\n\n"
    "🇮🇷 گزارش اتصال از ایران\n"
    "• بعد از تست، با دکمه‌های ✅ یا ❌ وصل‌شدن واقعی از ایران را گزارش کن.\n"
    "• این گزارش‌ها روی اولویت کانفیگ‌ها اثر می‌گذارند.\n\n"
    "📱 کپی و کد QR\n"
    "• کپی و کد QR برای کانفیگی فعال است که قبلاً به تو تحویل شده باشد.\n\n"
    "📡 ارسال خودکار\n"
    "• کانفیگ‌های سالم هر ۵ ساعت به کانال و گروه ارسال می‌شوند.\n"
    "• سقف اعلامی مصرف هر کانفیگ ۵ گیگ است."
)

UNKNOWN = "نامشخص"
HEALTHY = "سالم"
TEHRAN_LABEL = "تهران"


QUOTA_SHORTAGE = (
    "کانفیگ‌های رایگان این هفته تموم شد 🥲\n\n"
    "با دعوت دوستان واجد شرایط (حداقل ۱ کانفیگ گرفته باشند)، هر ۲ نفر = ۱ کانفیگ رایگان هفتگی ۵ گیگ بهت اضافه می‌کنه."
)


def shortage(q: int, used: int) -> str:
    _ = q, used
    return QUOTA_SHORTAGE


def quota_status(qualified: int, pending: int, used: int, balance: int) -> str:
    total = 1 + max(0, int(qualified)) // 2
    return (
        "🎁 کانفیگ رایگان این هفته\n\n"
        f"باقی‌مانده: {num(balance)} از {num(total)}\n"
        f"ارزان‌شده: {num(qualified)}\n"
        f"در انتظار: {num(pending)}\n"
        f"دعوت‌شده: {num(used)}\n\n"
        "💡 هر ۲ زیرمجموعه واجد شرایط = ۱ کانفیگ رایگان هفتگی ۵ گیگ"
    )


def referral_status(link: str, total: int, qualified: int, pending: int, leaderboard: str) -> str:
    return (
        f"لینک دعوت شما:\n{html.escape(link)}\n\n"
        f"کل زیرمجموعه‌ها: {num(total)}\n"
        f"معتبر: {num(qualified)}\n"
        f"در انتظار: {num(pending)}\n"
        f"بونوس: {num(qualified // 2)}\n\n"
        f"{REFERRAL_LAW}\n\n"
        f"۱۰ نفر برتر:\n{leaderboard}"
    )


LEADERBOARD_EMPTY = "هنوز رتبه‌ای ثبت نشده است."


def leaderboard_row(rank: int, user_id: int, qualified: int) -> str:
    return f"{num(rank)}. کاربر {num(user_id)} — {num(qualified)} معتبر"


def test_card(
    protocol: str,
    host: str,
    port: int,
    ip: str,
    country: str | None,
    city: str | None,
    flag: str | None,
    isp: str | None,
    latency_ms: int,
    tested_at: str,
    *,
    data_remaining_gb: float | None = None,
    iran_ok: int = 0,
    iran_fail: int = 0,
) -> str:
    _ = host, port, ip, isp, tested_at
    if country and city:
        location = f"{flag + ' ' if flag else ''}{country} / {city}"
    else:
        location = UNKNOWN
    return (
        f"وضعیت: {HEALTHY} ✅\n"
        f"پروتکل: {html.escape(protocol)}\n"
        f"لوکیشن: {html.escape(location)}\n"
        f"پینگ: {latency_ms} ms\n"
        f"{data_line(data_remaining_gb)}\n"
        f"{iran_line(iran_ok, iran_fail)}"
    )


def channel_post(
    record: dict,
    bot_username: str,
    escaped_uri: str,
    *,
    iran_ok: int = 0,
    iran_fail: int = 0,
) -> str:
    country = record.get("country") or UNKNOWN
    city = record.get("city") or UNKNOWN
    flag = record.get("flag") or ""
    location = f"{flag + ' ' if flag else ''}{country} / {city}"
    reality_line = (
        "🛡 پروتکل: Reality (پیشنهادی برای ایران)\n"
        if str(record.get("security") or "").lower() == "reality"
        else ""
    )
    return (
        "<b>کانفیگ رایگان — ارسال هر ۵ ساعت</b>\n"
        "وضعیت: تست‌شده و سالم ✅\n"
        f"لوکیشن: {html.escape(location)}\n"
        f"پروتکل: {html.escape(str(record['protocol']))}\n"
        f"{reality_line}\n"
        f"<code>{escaped_uri}</code>\n\n"
        f"{data_line(record.get('data_remaining_gb'))}\n"
        f"{iran_line(iran_ok, iran_fail)}\n\n"
        f"دریافت کانفیگ رایگان از ربات: @{html.escape(bot_username)}"
    )


def config_code(escaped_uri: str) -> str:
    return f"<code>{escaped_uri}</code>"


CONFIG_RESENT = "کانفیگ‌های همین هفته دوباره ارسال شدند و دریافت جدیدی ثبت نشد."
CONFIG_DELIVERED = "یک کانفیگ رایگان سالم برای شما ثبت شد."
QR_CAPTION = "QR کانفیگ تحویل‌شده"
START_PREVIEW = "این پیش‌نمایش دریافت جدیدی ثبت نمی‌کند."

BTN_JOIN = "عضویت"
BTN_JOIN_CONFIRM = "تایید عضویت"
GATE_TEXT = (
    "برای استفاده از ربات ابتدا در کانال @GalaxiesDrop عضو شوید.\n\n"
    "۱) روی دکمهٔ «عضویت» بزنید و وارد کانال شوید.\n"
    "۲) در کانال عضو شوید و به ربات برگردید.\n"
    "۳) دکمهٔ «تایید عضویت» را بزنید."
)
GATE_NOT_MEMBER = "هنوز عضو کانال نیستید؛ اول عضو شوید، بعد تایید بزنید."
GATE_OK = "عضویت تأیید شد ✅"

ADMIN_ONLY = "این بخش فقط برای ادمین است."
ADMIN_PANEL = "پنل ادمین؛ یک گزینه را انتخاب کنید."
BTN_TEST_IRAN = "🧪 تست کانفیگ از ایران"
BTN_STATS = "🧮 آمار کانفیگ‌ها"
BTN_PURGE = "🧹 پاکسازی کانفیگ‌های مرده"
ADMIN_STATUS_BTN = "وضعیت"
ADMIN_SEND_BTN = "ارسال دستی"
ADMIN_MODE_BTN = "بازهٔ ارسال"
ADMIN_SOURCES_BTN = "منابع"
ADMIN_ADD_CONFIG_BTN = "افزودن کانفیگ"
ADMIN_QUOTA_BTN = "مشاهده/ویرایش کانفیگ رایگان"
ADMIN_REFS_BTN = "زیرمجموعه‌های کاربر"
ADMIN_AUTOPOST_BTN = "تغییر ارسال خودکار"
ADMIN_MODE_WEEKLY = "هفتگی"
ADMIN_MODE_D3 = "هر ۳ روز"
ADMIN_MODE_OFF = "خاموش"
ADMIN_SOURCE_ADD = "افزودن منبع"
ADMIN_SOURCE_REMOVE = "حذف منبع"
ADMIN_ASK_SOURCE = "نشانی HTTPS منبع را بفرستید."
ADMIN_SOURCE_INVALID = "نشانی منبع باید با https:// شروع شود."
ADMIN_SOURCE_ADDED = "منبع افزوده شد."
ADMIN_SOURCE_REMOVED = "منبع حذف شد."
ADMIN_SOURCE_NOT_FOUND = "منبع پیدا نشد."
ADMIN_SOURCES_EMPTY = "منبعی ثبت نشده است."
ADMIN_ASK_CONFIG = "URI کانفیگ را بفرستید؛ تا تکمیل تست و لوکیشن در صف می‌ماند."
ADMIN_CONFIG_QUEUED = "کانفیگ ذخیره شد و تا سلامت کامل در صف می‌ماند."
ADMIN_CONFIG_HEALTHY = "کانفیگ تست شد و به فهرست سالم افزوده شد."
ADMIN_ASK_TGID = "آیدی عددی تلگرام کاربر را بفرستید."
ADMIN_ASK_USED = "مقدار جدید را به‌شکل «آیدی مقدار» بفرستید."
ADMIN_BAD_NUMBER = "عدد معتبر وارد کنید."
ADMIN_CONFIRM_EDIT = "ویرایش مصرف این هفته تأیید شود؟"
ADMIN_EDITED = "مصرف این هفته ویرایش شد."
ADMIN_CONFIRM_SEND = "ارسال همین یک کانفیگ به کانال و گروه تأیید شود؟"
ADMIN_SENT = "ارسال انجام شد."
ADMIN_SEND_FAILED = "ارسال انجام نشد؛ جزئیات فقط برای ادمین ثبت شد."
ADMIN_NO_CANDIDATE = "کانفیگ سالم و قابل‌ارسال وجود ندارد."
ADMIN_TESTCFG_TEXT = (
    "🧪 تست کانفیگ از ایران\n\n"
    "هر بار یک کانفیگ با لوکیشن/پورت/پروتکل متفاوت می‌فرستم. با اینترنت ایران تست کن؛ اگر وصل شد یک‌دکمه‌ای مستقیم به کانال و گروه می‌رود."
)
ADMIN_TEST_SENT = "👆 این کانفیگ را با آیپی ایران تست کن"
ADMIN_IRAN_FAIL_SAVED = "ثبت شد ✔️ کانفیگ بعدی (لوکیشن/پروتکل متفاوت):"
ADMIN_PURGED_FMT = "🧹 پاکسازی انجام شد\nحذف‌شده: {removed}\nباقی‌مانده: {kept}"
ADMIN_STATS_FMT = (
    "🧮 آمار کانفیگ‌ها\n"
    "سالم: {healthy}\n"
    "در صف تست: {queued}\n"
    "پروتکل‌ها: {protocols}\n"
    "بیشترین لوکیشن‌ها: {countries}\n"
    "آخرین پست: {last_post}"
)
ADMIN_AUTOPOST_ON = "ارسال خودکار روشن شد."
ADMIN_AUTOPOST_OFF = "ارسال خودکار خاموش شد."
ADMIN_CANCELLED = "عملیات لغو شد."
ADMIN_LAST_ERROR_NONE = "ندارد"
ADMIN_ERROR_RECORDED = "یک خطا ثبت شده است"


def admin_status(last_post: str, healthy_count: int, last_error: str) -> str:
    return (
        "وضعیت سامانه\n"
        f"آخرین ارسال: {last_post}\n"
        f"کانفیگ سالم: {num(healthy_count)}\n"
        f"آخرین خطا: {last_error}"
    )


def admin_user_quota(user_id: int, qualified: int, pending: int, used: int, balance: int) -> str:
    return (
        f"کاربر: {num(user_id)}\n"
        f"معتبر: {num(qualified)}\n"
        f"در انتظار: {num(pending)}\n"
        f"مصرف این هفته: {num(used)}\n"
        f"مانده: {num(balance)}"
    )


def admin_referral_row(user_id: int, qualified: bool) -> str:
    status = "معتبر" if qualified else "در انتظار"
    return f"کاربر {num(user_id)} — {status}"


def admin_referrals(
    user_id: int,
    total: int,
    qualified: int,
    pending: int,
    details: str = "",
) -> str:
    base = (
        f"زیرمجموعه‌های کاربر {num(user_id)}\n"
        f"کل: {num(total)}\n"
        f"معتبر: {num(qualified)}\n"
        f"در انتظار: {num(pending)}"
    )
    return f"{base}\n\n{details}" if details else base


def admin_mode_set(mode_label: str) -> str:
    return f"بازهٔ ارسال روی «{mode_label}» تنظیم شد."


def sources_list(items: list[str]) -> str:
    if not items:
        return ADMIN_SOURCES_EMPTY
    return "منابع مجاز:\n" + "\n".join(
        f"{num(i)}. {html.escape(url)}" for i, url in enumerate(items, 1)
    )


def post_admin_error(detail: str) -> str:
    return f"خطای ارسال خودکار: {detail}"


POST_TEST_FAILED_ADMIN = "تست تازهٔ کانفیگ ناموفق بود؛ هیچ پیام خطایی در کانال یا گروه منتشر نشد."
POST_PARTIAL_ADMIN = "ارسال فقط به بخشی از مقصدها موفق بود؛ سابقهٔ ارسال حفظ شد."
POST_RATE_LIMIT_ADMIN = "تلگرام پس از یک بار تلاش مجدد همچنان محدودیت ۴۲۹ برگرداند."
CRON_NO_CONFIG_ADMIN = "کانفیگ سالم و بدون تکرار برای ارسال پیدا نشد."

COUNTRY_NAMES = {
    "DE": "آلمان", "US": "ایالات متحده", "NL": "هلند", "FR": "فرانسه",
    "GB": "بریتانیا", "FI": "فنلاند", "CA": "کانادا", "TR": "ترکیه",
    "IR": "ایران", "RU": "روسیه", "SG": "سنگاپور", "JP": "ژاپن",
    "HK": "هنگ‌کنگ", "SE": "سوئد", "CH": "سوئیس", "AT": "اتریش",
    "PL": "لهستان", "IT": "ایتالیا", "ES": "اسپانیا", "AE": "امارات",
    "IN": "هند", "AU": "استرالیا", "KR": "کرهٔ جنوبی", "BR": "برزیل",
}

CITY_NAMES = {
    "Frankfurt": "فرانکفورت", "Frankfurt am Main": "فرانکفورت",
    "Amsterdam": "آمستردام", "Paris": "پاریس", "London": "لندن",
    "Helsinki": "هلسینکی", "Istanbul": "استانبول", "Tehran": "تهران",
    "Moscow": "مسکو", "Singapore": "سنگاپور", "Tokyo": "توکیو",
    "Stockholm": "استکهلم", "Zurich": "زوریخ", "Vienna": "وین",
    "Warsaw": "ورشو", "Milan": "میلان", "Madrid": "مادرید",
    "Dubai": "دبی", "Toronto": "تورنتو", "Montreal": "مونترال",
}
