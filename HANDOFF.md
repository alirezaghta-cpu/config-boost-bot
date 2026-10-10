# بخش الف — HANDOFF.md (نسخهٔ بازنویسی‌شده و دسته‌بندی‌شده)

## ۱. شناسنامهٔ پروژه
- ربات تلگرامی رایگان **@ConfigBoostbot** (id `8840739761`) برای جمع‌آوری، تست و توزیع کانفیگ‌های v2ray (vless / vmess / trojan / ss).
- مقاصد ارسال: کانال **@GalaxiesDrop** (`-1001686062564`) و گروه **@IRvasl** (`-1003793302941`).
- مقررات سخت‌گیرانهٔ صاحب پروژه: **۱۰۰٪ رایگان** — بدون کارت بانکی، VPS پولی، دامنهٔ پولی یا درگاه پرداخت. پاسخ به کاربر فارسی؛ فارسی و انگلیسی در یک پاراگراف قاطی نشود. کانفیگ بدون تست موفق TCP نباید تحویل شود.
- اولویت جغرافیایی کانفیگ‌ها: **آلمان، فرانسه، هلند، کانادا، آمریکا** (`PRIORITY_COUNTRIES`).

## ۲. معماری و اجزا
| جزء | کجاست | کار |
|---|---|---|
| مخزن | `github.com/alirezaghta-cpu/config-boost-bot` (عمومی، `main`) | کد + گردش‌کارها + `data/subscription.txt` |
| ربات | `bot/` — Python 3.12 + aiogram 3، polling | منو، سهمیه، رفرال، تست، گزارش اتصال ایران، پنل ادمین |
| Worker | `worker/tcp-test.js` روی Cloudflare Workers | تست TCP از شبکهٔ Cloudflare |
| ذخیره‌سازی | Cloudflare KV — namespace `2cbd1ab46bd942809c89592830a94719` | کانفیگ‌ها، کاربران، رأی‌های ایران، قفل‌ها، geo |
| زمان‌بندی | GitHub Actions (۵ گردش‌کار) | refresh، پست هر ۵ ساعت، میزبانی ۲۴/۷ ربات، force-post، deploy Worker |

- فایل‌های کلیدی ربات: `bot/main.py`, `bot/handlers.py`, `bot/quota.py`, `bot/storage.py`, `bot/cards.py`, `bot/locales/fa.py`
- Worker: `GET /health` → `{"ok":true}`؛ `POST /test` با بدنه `{host,port}` و هدر `X-Worker-Secret`.
- تست TCP فقط اتصال سوکت است ≠ تست تونل واقعی؛ اگر Worker جواب ندهد fallback تست مستقیم از runner.

## ۳. شناسه‌ها و آدرس‌ها
- ربات: `@ConfigBoostbot` — ادمین کانال با `can_post_messages`، عضو گروه با اجازهٔ ارسال (تأیید API شده).
- ادمین/steward عددی: `452259540`
- Cloudflare account id: `85c015039637471c2402dfeb4c23efc`
- KV namespace id: `2cbd1ab46bd942809c89592830a94719`
- Worker URL: `https://config-boost-test.configboost.workers.dev`
- BOT_USERNAME: `ConfigBoostbot`

## ۴. گردش‌کارهای GitHub Actions
| گردش‌کار | فایل | زمان‌بندی | کار |
|---|---|---|---|
| Refresh healthy sources | `refresh-sources.yml` | هر ۶ ساعت + دستی | `scripts/refresh_sources.py` — جمع‌آوری از ۵ منبع، تست ۳۰ تا با چرخش cursor (`refresh:cursor`)، بازسازی `configs:healthy`، کامیت `data/subscription.txt` |
| **Auto Telegram post** | `weekly-post.yml` | **هر ۵ ساعت (`15 */5 * * *`) + دستی با `force`** | `scripts/weekly_post.py` — انتخاب کاندید با اولویت (کشورهای اولویت‌دار ← رأی «وصل شدم از ایران» ← تازه‌ترین)، تست مجدد تا اولین موفق، ارسال به کانال+گروه |
| Force post | `force-post.yml` | فقط دستی | `scripts/force_post.py` — همان اولویت‌بندی، ارسال فوری؛ لاگ JSON `{"posted","targets","errors"}` |
| Bot host (24/7 chain) | `bot-host.yml` | زنجیره‌ای + cron پشتیبان هر ۶ ساعت | اجرای ربات تا ۵:۴۰ (`timeout 20400s`) سپس `gh workflow run` خودکار؛ concurrency گروه `bot-host` |
| Deploy Worker | `deploy-worker.yml` | فقط دستی | آپلود `worker/tcp-test.js` + باند secret + health check |

## ۵. قوانین کسب‌وکار
- **سهمیهٔ هفتگی** = `۱ + div(زیرمجموعه‌های معتبر,۲) − مصرف هفته`؛ هفته شنبه تا جمعه، وقت تهران (`week_key`).
- زیرمجموعهٔ معتبر: اولین‌بار با لینک دعوت آمده، قبلاً ثبت‌نشده، و `used_total ≥ 1` و `qualified_at` ست شده. سقف دعوت روزانه ۱۰. خوددعوتی ممنوع.
- محدودیت نرخ: اکشن‌ها ۱۵ در ۶۰ ثانیه؛ پشتیبانی ۲ پیام در ساعت؛ تست روزانه ۳ و برای هر کانفیگ هر ۲۴ ساعت یک‌بار.
- **ارسال خودکار**: حالت جدید `h5` = هر ۵ ساعت (پیش‌فرض جدید)؛ `weekly` / `d3` / `off` همچنان معتبر. کلید KV `post:mode`، کلید `auto_post`. هر کانفیگ تا ۷ روز دوباره پست نمی‌شود. همیشه تست مجدد قبل از ارسال.
- **اولویت انتخاب کانفیگ** (هم در پست خودکار و هم در «دریافت کانفیگ» ربات): ۱) کشورهای `PRIORITY_COUNTRIES` (DE/FR/NL/CA/US) ۲) بیشترین رأی «وصل شدم از ایران» ۳) تازه‌ترین تست.
- **گزارش اتصال ایران**: دکمه‌های `✅ وصل شدم (از ایران)` / `❌ وصل نشدم` زیر هر کارت؛ فقط برای کانفیگ‌های تحویل‌گرفته‌شده مجاز؛ هر کاربر یک رأی (آخرین رأی برنده). نتیجه در کارت و پست کانال نمایش داده می‌شود.
- **حجم**: سقف اعلامی هر کانفیگ ۵ گیگ (`DATA_CAP_GB=5`)؛ خط `data_line` کنار کارت/پست نمایش داده می‌شود («نامحدود ← سقف ۵ گیگ» یا حجم باقی‌مانده اگر بعداً از پنل خوانده شود).
- دکمه‌های پست کانال: `t.me/ConfigBoostbot?start=cfg_{id}`.

## ۶. داده‌ها (Cloudflare KV)
- `config:{sha256_20}` — رکورد: uri, protocol, host, port, ip, country/city/flag/country_code/isp, latency_ms, tested_at, tested_at_tehran, healthy, queued (و بعداً اختیاری `data_remaining_gb`)
- `configs:healthy` — آرایهٔ شناسه‌های سالم (اعتبار ۷ روزه)
- **`iran:{id}` — جدید: `{"ok":[tg_id,...],"fail":[tg_id,...]}` رأی‌های اتصال از ایران**
- `sources`, `refresh:cursor`, `posted:{id}`, `last_post`, `last_error`, `post:mode` (اکنون ممکن است `h5`), `auto_post`, `lock:weekly-post`, `healthy:summary`, `geo:{ip}` (کش ۲۴ ساعته از `ipwho.is`)
- کلیدهای کاربران/ادمین‌لاگ/نرخ: در `bot/storage.py`
- `data/subscription.txt` — کامیت‌شده توسط refresh.

## ۷. secretهای GitHub Actions (فقط نام)
`BOT_TOKEN`, `ADMIN_IDS`, `CHANNEL_ID`, `GROUP_ID`, `BOT_USERNAME`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `WORKER_SECRET`
غیر-secret ثابت: `KV_NAMESPACE_ID`, `WORKER_URL`.
- ناهماهنگی `WORKER_SECRET` شناخته‌شده و بی‌اثرعملی است (fallback مستقیم). همسان‌سازی: مقدار دلخواه در Secrets و اجرای دستی `Deploy Cloudflare Worker`.

## ۸. وضعیت تأییدشده (۲۰۲۶-۱۰-۱۰ ~۰۶:۲۳ UTC، کامیت `c4040fb`)
- پست فوری موفق (کانفیگ `0a4161e35bbc5fa90b27` به هر دو مقصد)، refresh سبز (run #9: `healthy_total=43`)، ربات آنلاین با `pending_update_count=0`، Worker سالم (`/health → ok`).

## ۹. محدودیت‌های صادقانه + کارهای باز
1. **تست واقعی از آیپی ایران رایگان ممکن نیست**: نه Cloudflare Workers و نه GitHub Actions داخل ایران نیستند و هیچ API رایگانی تست TCP از ایران نمی‌دهد. راه‌حل پیاده‌شده: گزارش جمعی کاربران ایرانی (دکمه‌های ✅/❌) + اولویت‌بندی کشورها. گزینهٔ آینده: اجرای اسکریپت تست روی دستگاه شخصی شما در ایران (رایگان، بدون VPS).
2. **اجرای واقعی سقف ۵ گیگ**: کانفیگ‌های عمومی مالکیت ما نیستند و ترافیک آن‌ها قابل محدودکردن از سمت ما نیست؛ فعلاً سقف فقط در رابط کاربری اعلام می‌شود. اجرای واقعی فقط با API پنل اختصاصی (بند زیر) ممکن است.
3. **آدرس + کلید API پنل اصلی** هنوز داده نشده (برای منبع اختصاصی و اعمال واقعی سقف حجم).
4. **WORKER_SECRET ناهماهنگ** (بند ۷) — بی‌اثرعملی.
5. **خطای fetch چهار منبع از پنج** در refresh اخیر (احتمال rate-limit گیت‌هاب) — بررسی در refreshهای بعدی؛ در صورت تداوم منبع جایگزین از پنل ادمین → منابع.
6. **تست TCP ≠ تست تونل** — نیازمند طرح رایگان جدید در بلندمدت.
7. **هاست جایگزین ربات**: فقط گزینه‌های رایگان بدون کارت؛ ترجیح همین زنجیرهٔ Actions.

## ۱۰. عیب‌یابی سریع
- ربات آفلاین → Actions → `Bot host (24/7 chain)` → Run workflow (اگر زنجیره قطع شده، cron هر ۶ ساعت خودش شروع می‌کند).
- پست ارسال نشد → لاگ `force-post`/`weekly-post`: `locked; skipping` (قفل ۵۰ دقیمه‌ای)، `not due` (اگر KV هنوز حالت قدیمی `weekly`/`d3` است — در پنل ادمین «ارسال هر ۵ ساعت» را بزنید)، `no_candidates` (اول refresh)، `force_retest_failed`، `http_4xx` تلگرام.
- KV کار نمی‌کند → `CLOUDFLARE_API_TOKEN` باید دسترسی Workers KV Read/Write داشته باشد.
- استقرار Worker → `Deploy Cloudflare Worker`؛ توقف یعنی `WORKER_SECRET` ثبت نیست.
- هرگز secret/token در ریپو، لاگ عمومی یا پیام کانال قرار نگیرد.

## ۱۱. تاریخچهٔ تصمیم‌ها
- فاز آزمایشی: منو، سهمیهٔ هفتگی، رفرال، تست، پنل ادمین.
- میزبانی رایگان: GitHub Actions زنجیره‌ای + Worker کلودفلر.
- تست TCP دو سطحی: Worker + fallback مستقیم.
- راز لو رفته چرخانده شد؛ PAT از deploy حذف شد.
- **به‌روزرسانی ۲۰۲۶-۱۰-۱۰**: پست هر ۵ ساعت (`h5`)، اولویت کشوری DE/FR/NL/CA/US، گزارش اتصال ایران (`iran:{id}`)، نمایش سقف ۵ گیگ، منو/متن‌های جدید، بازنویسی HANDOFF.

## ۱۲. مراحل بعدی
1) پس از وصل شدن GitHub: اعمال پچ‌های بخش ب و push در یک کامیت.
2) در پنل ادمین ربات: «ارسال هر ۵ ساعت» را یک‌بار بزن تا مقدار قدیمی `post:mode` بازنویسی شود.
3) رفع خطای fetch منابع (بند ۹.۵).
4) دریافت API پنل از صاحب پروژه (بند ۹.۲–۹.۳).
5) در بلندمدت: تست تونل واقعی و اجرای واقعی سقف ۵ گیگ روی پنل اختصاصی.
