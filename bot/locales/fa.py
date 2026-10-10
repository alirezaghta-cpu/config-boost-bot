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
BTN_QUOTA = "سهمیهٔ من"
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
BTN_IRAN_OK = "✅ وصل شدم (از ایران)"
BTN_IRAN_FAIL = "❌ وصل نشدم"
ADMIN_MODE_H5 = "هر ۵ ساعت"
DATA_CAP_GB: int = 5
IRAN_VOTE_OK_SAVED = "✅ گزارش «وصل شد» برای این کانفیگ ثبت شد. ممنون!"
IRAN_VOTE_FAIL_SAVED = "❌ گزارش «قطع شد» برای این کانفیگ ثبت شد. ممنون!"
IRAN_VOTE_ONLY_DELIVERED = (
    "گزارش فقط برای کانفیگ‌هایی که قبلاً با سهمیهٔ خودتان دریافت کرده‌اید ثبت می‌شود."
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


WELCOME = (
    "سلام! 👋\n\n"
    "از منوی زیر انتخاب کنید:\n"
    "• دریافت کانفیگ این هفته\n"
    "• تست و لوکیشن\n"
    "• سهمیهٔ من\n"
    "• زیرمجموعه‌گیری\n"
    "• راهنما\n"
    "• پشتیبانی\n\n"
    "📡 هر ۵ ساعت یک‌بار، کانفیگ‌های تست‌شده به‌طور خودکار در کانال و گروه ارسال می‌شوند.\n"
    "🌍 بیشتر کانفیگ‌ها از کشورهای آلمان، فرانسه، هلند، کانادا و آمریکا هستند.\n"
    "💾 سقف مصرف هر کانفیگ ۵ گیگابایت است؛ پس از رسیدن به سقف، کانفیگ جدید دریافت کنید."
)
GENERIC_ERROR = "متأسفانه خطایی رخ داد. لطفاً کمی بعد دوباره تلاش کنید."
RATE_LIMIT = "درخواست‌ها خیلی سریع ارسال شده‌اند. لطفاً کمی بعد دوباره تلاش کنید."
IGNORED_CONTENT = "فقط متن یا فایل پذیرفته می‌شود."
NO_HEALTHY_CONFIG = "این هفته کانفیگ تست‌شده موجود نیست"
CONFIG_TEST_FAILED = "تست اتصال ناموفق بود؛ این کانفیگ تحویل یا منتشر نشد."
CONFIG_NOT_FOUND = "کانفیگ پیدا نشد یا دیگر معتبر نیست."
COPY_DENIED = "این کانفیگ با سهمیهٔ شما تحویل نشده است؛ فقط پیش‌نمایش لوکیشن نمایش داده می‌شود."
QR_DENIED = COPY_DENIED
TEST_PROMPT = "یک URI از نوع vless، vmess، trojan یا ss بفرستید."
INVALID_URI = "فرمت کانفیگ معتبر نیست."
TEST_DAILY_LIMIT = "سهمیهٔ تست امروز تمام شده است. هر کاربر روزانه ۳ تست دارد."
TEST_24H_LIMIT = "برای همین کانفیگ در هر ۲۴ ساعت فقط یک تست تازه انجام می‌شود؛ نتیجهٔ ذخیره‌شده نمایش داده شد."
SUPPORT_PROMPT = "پیام یا فایل خود را بفرستید تا برای ادمین ارسال شود."
SUPPORT_SENT = "پیام شما برای ادمین ارسال شد."
SUPPORT_LIMIT = "حد پشتیبانی شما ۲ پیام در ساعت است."
NO_ADMIN = "ادمینی برای دریافت پیام پشتیبانی تنظیم نشده است."
REFERRAL_CAP_LOG = "سقف ۱۰ دعوت جدید روزانه برای دعوت‌کننده رد شد."
REFERRAL_SELF_LOG = "دعوت از خود رد شد."
REFERRAL_ACCEPTED = "دعوت با موفقیت ثبت شد."
REFERRAL_PENDING = "زیرمجموعه پس از گرفتن اولین کانفیگ معتبر می‌شود."
REFERRAL_QUALIFIED_LOG = "یک زیرمجموعه پس از اولین مصرف سهمیه معتبر شد."

REFERRAL_LAW = (
    "هر کاربر هفته‌ای ۱ کانفیگ پایه دارد. هر ۲ زیرمجموعهٔ معتبر = ۱ کانفیگ اضافه در همان هفته. "
    "معتبر یعنی با لینک تو آمده و خودش یک کانفیگ گرفته باشد. گیگ هدیه، سرور اختصاصی و پول در این فاز وجود ندارد."
)

PURCHASE_TEXT = (
    "فروش فعال نیست و سهمیه را زیاد نمی‌کند. فعلاً فقط سهمیهٔ هفتگی و بونوس زیرمجموعه فعال است."
)
PLAN_LIGHT = "سبک ۲۰ گیگ"
PLAN_STANDARD = "استاندارد ۵۰ گیگ"
PLAN_PRO = "پرو ۱۲۰ گیگ"
PLAN_FAIR = "نامحدود منصفانه"
PLAN_SERVER = "سرور اختصاصی"
NOT_ORDERED = "سفارشی نیست"

HELP_TEXT = (
    "• هر هفته از شنبه ۰۰:۰۰ تهران یک سهمیهٔ پایه دارید.\n"
    "• هر ۲ زیرمجموعهٔ معتبر، یک کانفیگ اضافه در همان هفته باز می‌کند.\n"
    "• زیرمجموعه وقتی معتبر است که اولین‌بار با لینک شما وارد شود و خودش یک کانفیگ بگیرد.\n"
    "• کارت تست، سلامت TCP، IP، کشور/شهر، ISP، پینگ و زمان تست را نشان می‌دهد؛ اطلاعات ناموجود جعل نمی‌شود.\n"
    "• دیدن پست کانال یا کارت لوکیشن سهمیه کم نمی‌کند؛ فقط دکمهٔ «دریافت کانفیگ این هفته» مصرف را ثبت می‌کند.\n"
    "• کپی و QR فقط برای کانفیگی فعال است که قبلاً با سهمیهٔ خودتان گرفته باشید.\n"
    "• سقف مصرف هر کانفیگ ۵ گیگابایت است؛ حجم باقی‌مانده در کنار کارت تست نمایش داده می‌شود.\n"
    "• گزارش‌های اتصال یا قطع از ایران، روی اولویت کانفیگ‌ها تأثیر می‌گذارد.\n"
    "• ارسال خودکار کانفیگ‌های تست‌شده هر ۵ ساعت یک‌بار انجام می‌شود."
)

UNKNOWN = "نامشخص"
HEALTHY = "سالم"
TEHRAN_LABEL = "تهران"


def shortage(q: int, used: int) -> str:
    return (
        "سهمیهٔ این هفته تمام شده. پایه: ۱ کانفیگ. "
        f"زیرمجموعهٔ معتبر: {num(q)}. کانفیگ اضافه: {num(q // 2)}. "
        f"مصرف‌شده: {num(used)}. مانده: ۰. "
        "با ۲ زیرمجموعهٔ معتبر جدید، ۱ کانفیگ دیگر همین هفته باز می‌شود. "
        "ریست بعدی: شنبه ۰۰:۰۰ تهران."
    )


def quota_status(qualified: int, pending: int, used: int, balance: int) -> str:
    return (
        "وضعیت سهمیهٔ این هفته\n"
        f"پایه: {num(1)}\n"
        f"زیرمجموعهٔ معتبر: {num(qualified)}\n"
        f"در انتظار: {num(pending)}\n"
        f"بونوس: {num(qualified // 2)}\n"
        f"مصرف‌شده: {num(used)}\n"
        f"مانده: {num(balance)}\n"
        "ریست: شنبه ۰۰:۰۰ تهران"
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
    if country and city:
        location = f"{flag + ' ' if flag else ''}{country} / {city}"
    else:
        location = UNKNOWN
    return (
        f"وضعیت: {HEALTHY}\n"
        f"پروتکل: {html.escape(protocol)}\n"
        f"هاست: {html.escape(host)}\n"
        f"پورت: {port}\n"
        f"IP: {html.escape(ip)}\n"
        f"لوکیشن: {html.escape(location)}\n"
        f"ISP: {html.escape(isp or UNKNOWN)}\n"
        f"پینگ: {latency_ms} ms\n"
        f"زمان تست: {html.escape(tested_at)}\n"
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
    return (
        "<b>کانفیگ رایگان — ارسال هر ۵ ساعت</b>\n"
        "وضعیت: تست‌شده و سالم\n"
        f"لوکیشن: {html.escape(location)}\n"
        f"IP: {html.escape(str(record['ip']))}\n"
        f"ISP: {html.escape(str(record.get('isp') or UNKNOWN))}\n"
        f"پینگ: {record['latency_ms']} ms\n"
        f"پروتکل: {html.escape(str(record['protocol']))}\n"
        f"زمان تست: {html.escape(str(record['tested_at_tehran']))}\n\n"
        f"<code>{escaped_uri}</code>\n\n"
        f"{data_line(record.get('data_remaining_gb'))}\n"
        f"{iran_line(iran_ok, iran_fail)}\n\n"
        f"دریافت از ربات با سهمیهٔ هفتگی: @{html.escape(bot_username)}"
    )


def config_code(escaped_uri: str) -> str:
    return f"<code>{escaped_uri}</code>"


CONFIG_RESENT = "کانفیگ‌های همین هفته دوباره ارسال شدند و سهمیه‌ای کم نشد."
CONFIG_DELIVERED = "یک کانفیگ سالم با سهمیهٔ شما ثبت شد."
QR_CAPTION = "QR کانفیگ تحویل‌شده"
START_PREVIEW = "این پیش‌نمایش سهمیه‌ای کم نمی‌کند."

ADMIN_ONLY = "این بخش فقط برای ادمین است."
ADMIN_PANEL = "پنل ادمین؛ یک گزینه را انتخاب کنید."
ADMIN_STATUS_BTN = "وضعیت"
ADMIN_SEND_BTN = "ارسال دستی"
ADMIN_MODE_BTN = "بازهٔ ارسال"
ADMIN_SOURCES_BTN = "منابع"
ADMIN_ADD_CONFIG_BTN = "افزودن کانفیگ"
ADMIN_QUOTA_BTN = "مشاهده/ویرایش سهمیه"
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
