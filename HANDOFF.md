# HANDOFF.md — config-boost-bot (بازنویسی‌شده: ۲۰۲۶-۱۰-۱۰)

> این فایل تنها ورودی لازم برای تحویل به مایند بعدی است؛ بدون توضیح اضافه آن را بده. مقادیر secretها عمداً داخل نیست (ریپو عمومی است).

---

## ۱. پروژه چیست
ربات تلگرامی رایگان **@ConfigBoostbot** برای جمع‌آوری، تست و توزیع کانفیگ‌های v2ray (vless / vmess / trojan / ss) در:
- کانال **@GalaxiesDrop** — id: `-1001686062564`
- گروه **@IRvasl** — id: `-1003793302941`

مقررات سخت‌گیرانه صاحب پروژه: **۱۰۰٪ رایگان** — بدون کارت بانکی، VPS پولی، دامنه پولی یا درگاه پرداخت. پاسخ به کاربر فارسی؛ فارسی و انگلیسی در یک پاراگراف قاطی نشود. کانفیگ بدون تست موفق TCP نباید تحویل شود.

---

## ۲. اجزا و معماری

| جزء | کجاست | چه می‌کند |
|---|---|---|
| مخزن | `github.com/alirezaghta-cpu/config-boost-bot` (عمومی، شاخه `main`) | کد + گردش‌کارها + داده subscription |
| ربات | `bot/` — Python 3.12 + aiogram 3، حالت polling | منو، سهمیه، رفرال، تست، پنل ادمین |
| Worker | `worker/tcp-test.js` روی Cloudflare Workers | تست TCP از شبکه Cloudflare |
| ذخیره‌سازی | Cloudflare KV — namespace `config-boost-bot` | کانفیگ‌ها، کاربران، قفل‌ها، geo |
| زمان‌بندی | GitHub Actions (۶ گردش‌کار — بند ۴) | refresh، پست هفتگی، میزبانی ۲۴/۷ ربات، استقرار Worker |

- ورودی ربات: `python -m bot.main` (فایل‌های کلیدی: `bot/main.py`, `bot/handlers.py`, `bot/quota.py`, `bot/storage.py`, `bot/cards.py`, `bot/locales/fa.py`)
- Worker: `GET /health` → `{"ok":true}` — `POST /test` با بدنه `{"host":...,"port":...}` و هدر `X-Worker-Secret` (اگر Worker دارای secret باشد)
- تست TCP فقط اتصال سوکت است ≠ تست تونل واقعی؛ اگر Worker جواب ندهد، اسکریپت‌ها خودکار از خود runner تست می‌کنند (fallback).

---

## ۳. شناسه‌ها و آدرس‌ها

- مخزن: `alirezaghta-cpu/config-boost-bot`
- ربات: `@ConfigBoostbot` — id `8840739761` (ادمین کانال با `can_post_messages`، عضو گروه با اجازه ارسال — تأیید API شده)
- ادمین/ steward عددی: `452259540`
- Cloudflare account id: `85c015039637471c2402dfeb4c23efc`
- KV namespace id: `2cbd1ab46bd942809c89592830a94719`
- Worker URL: `https://config-boost-test.configboost.workers.dev`
- BOT_USERNAME: `ConfigBoostbot`

---

## ۴. گردش‌کارهای GitHub Actions

| گردش‌کار | فایل | زمان‌بندی | کار |
|---|---|---|---|
| Refresh healthy sources | `.github/workflows/refresh-sources.yml` | هر ۶ ساعت + دستی | `scripts/refresh_sources.py` — جمع‌آوری از ۵ منبع، تست ۳۰ تا در هر اجرا **با چرخش پنجره (cursor در KV: `refresh:cursor`)**، بازسازی `configs:healthy`، به‌روزرسانی `data/subscription.txt` |
| Weekly Telegram post | `.github/workflows/weekly-post.yml` | جمعه ۱۴:۳۰ UTC (= ۱۸:۰۰ تهران) + دستی با ورودی `force` | `scripts/weekly_post.py` — انتخاب **تازه‌ترین** ۵ کاندید، تست مجدد تا اولین موفق، ارسال به کانال+گروه |
| Force post | `.github/workflows/force-post.yml` | فقط دستی | `scripts/force_post.py` — ارسال فوری همین حالا؛ نتیجه JSON در لاگ: `{"posted":...,"targets":[...],"errors":[]}` |
| **Bot host (24/7 chain)** | `.github/workflows/bot-host.yml` | زنجیره‌ای + cron هر ۶ ساعت (پشتیبان) | اجرای ربات تا ۵ ساعت و ۴۰ دقیقه (`timeout 20400s`)، سپس شروع خودکار اجرای بعدی با `gh workflow run` (۳ بار تلاش). گروه concurrency `bot-host` جلوی اجرای همزمان دو نمونه را می‌گیرد. **رایگان چون ریپو عمومی است.** |
| Deploy Cloudflare Worker | `.github/workflows/deploy-worker.yml` | فقط دستی | آپلود `worker/tcp-test.js` + باند secret + health check. بدون secret معتبر متوقف می‌شود. |

نکته میزبانی: قبلاً تصمیم میزبانی ۲۴/۷ باز بود؛ **حل شد** — ربات روی همین Actions زنجیره‌ای اجرا می‌شود. وقفه بین اجراها حداکثر چند ثانیه تا چند دقیقه است و آپدیت‌های تلگرام روی سرور صف می‌مانند (تا ۲۴ ساعت)، پس هیچ پیامی گم نمی‌شود.

---

## ۵. قوانین کسب‌وکار (منطق خالص در `bot/quota.py`)

- **سهمیه هفتگی** = `۱ + div(زیرمجموعه‌های معتبر, ۲) − مصرف همین هفته`. هفته از **شنبه تا جمعه، وقت تهران** ریست می‌شود (`week_key`).
- **زیرمجموعه معتبر**: دعوت‌شده‌ای که نخستین‌بار با لینک دعوت آمده، قبلاً به دعوت‌کننده دیگری ثبت نشده، و حداقل یک کانفیگ گرفته (`used_total ≥ 1` و `qualified_at` ست شده).
- **سقف دعوت روزانه هر کاربر: ۱۰** (`MAX_NEW_INVITES_PER_DAY`).
- خوددعوتی ممنوع؛ اولین دعوت‌کننده برنده است.
- محدودیت نرخ: اکشن‌ها ۱۵ بار در ۶۰ ثانیه (میدل‌ور `ActionRateMiddleware`)؛ پشتیبانی ۲ پیام در ساعت؛ تست کانفیگ محدودیت روزانه و ۲۴ ساعته دارد (`storage.claim_test_slot`).
- **ارسال خودکار**: پیش‌فرض هفته‌ای یک پست (جمعه ۱۸:۰۰ تهران). حالت در KV کلید `post:mode`: `weekly` / `d3` (هر ۳ روز) / `off`؛ کلید `auto_post`: `on`/`off`. هر کانفیگ تا **۷ روز دوباره پست نمی‌شود** (`posted:{id}`). همیشه **تست مجدد قبل از ارسال**؛ اگر تست رد شود پست نمی‌رود و به ادمین خطا اطلاع داده می‌شود.
- دکمه‌های پست کانال لینک‌دارند: `t.me/ConfigBoostbot?start=cfg_{id}` (نمایش پیش‌نویس + منو).

---

## ۶. داده‌ها (Cloudflare KV)

- `config:{sha256_20}` — رکورد کانفیگ: uri, protocol, host, port, ip, country/city/flag/isp, latency_ms, tested_at, tested_at_tehran, healthy, queued
- `configs:healthy` — آرایه شناسه‌های سالم (تازه‌ترین تست، اعتبار ۷ روزه)
- `sources` — لیست منابع (پیش‌فرض ۵ سورس عمومی در `DEFAULT_SOURCES`)
- `refresh:cursor` — شاخص چرخش پنجره تست (هر اجرا ۳۰ تای بعدی)
- `posted:{id}` — زمان آخرین پست هر کانفیگ
- `last_post`, `last_error`, `post:mode`, `auto_post`, `lock:weekly-post` (قفل اجرا، TTL 3000s)
- `healthy:summary` — خلاصه آخرین refresh
- `geo:{ip}` — کش جغرافیا (۲۴ ساعته، از `ipwho.is`)
- داده کاربران/ادمین‌لاگ/شمارنده‌های نرخ: جزئیات کلیدها در `bot/storage.py`
- فایل عمومی: `data/subscription.txt` — لیست کانفیگ‌های سالم برای اشتراک (توسط refresh کامیت می‌شود)

---

## ۷. secretهای GitHub Actions (فقط نام؛ مقادیر هرگز داخل ریپو نرود)

`BOT_TOKEN`, `ADMIN_IDS`, `CHANNEL_ID`, `GROUP_ID`, `BOT_USERNAME`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `WORKER_SECRET`

غیر-secret ولی ثابت در workflowها: `KV_NAMESPACE_ID`, `WORKER_URL`.

**نکته WORKER_SECRET**: مقداری که در گفتگو اعلام شد (`9d4e...c61`) هنگام تست دستی با Worker جواب ۴۰۱ می‌دهد — یعنی مقدار ثبت‌شده در secret با مقدار مستقر روی Worker ناهماهنگ است. اثر عملی **ندارد** چون همه اسکریپت‌ها اگر Worker ۴۰۱ بدهد خودکار از تست TCP مستقیم روی runner استفاده می‌کنند و پست/refresh سبز می‌مانند. برای همسان‌سازی کامل: مقدار دلخواه را در `Settings → Secrets and variables → Actions → WORKER_SECRET` پیست کن و اکشن `Deploy Cloudflare Worker` را دستی اجرا کن. (توکن‌های دیگر افشا شده در گذشته را نیز در صورت امکان از BotFather/Cloudflare باطل و بچرخان.)

---

## ۸. وضعیت تأییدشده (۲۰۲۶-۱۰-۱۰ ~۰۶:۲۳ UTC — کامیت `c4040fb`)

- **پست فوری موفق**: کانفیگ `0a4161e35bbc5fa90b27` پس از تست موفق، هم به کانال و هم به گروه رفت — لاگ: `targets` دو تایی، `errors: []`.
- **refresh سبز (run #9)**: `found=5410, tested=30, healthy_new=28, healthy_total=43` — چرخش cursor کار می‌کند؛ `data/subscription.txt` به‌روز شد.
- **ربات آنلاین**: گردش‌کار `Bot host` در حال اجرا؛ همه ۲۸ آپدیت معوق مصرف شد (`pending_update_count=0`) یعنی ربات polling می‌کند و به `/start`های کاربر پاسخ داده/خواهد داد.
- سلامت Worker: `GET /health` → `{"ok":true}` (workers.dev فعال است).
- رمز چرخانده‌شده قدیمی (که در لاگ عمومی لو رفته بود) باطل است؛ رمز جدید فقط در گفتگو بوده و در هیچ فایلی نیست (بند ۷).

---

## ۹. مشکلات شناخته‌شده / کارهای باز

1. **ناهماهنگی WORKER_SECRET** (بند ۷) — تأثیر عملی ندارد؛ فنی/تمیزکاری.
2. **خطای fetch چهار منبع از پنج** در آخرین refresh (`RuntimeError` ← احتمالاً محدودیت نرخ خام گیت‌هاب یا تایم‌اوت). یک منبع سالم است و کل زنجیره سبز می‌ماند. بررسی در refreshهای بعدی؛ در صورت تداوم، منبع جایگزین اضافه کن (از داخل ربات: پنل ادمین → منابع → افزودن).
3. **تست TCP ≠ تست تونل واقعی** — محدودیت طراحی فعلی؛ کانفیگ ممکن است TCP باز کند ولی پروکسی کار نکند. راه‌حل آینده نیازمند طرح رایگان جدید است.
4. **آدرس + کلید API پنل اصلی** صاحب پروژه هنوز داده نشده (برای وصل کردن منبع کانفیگ اختصاصی).
5. **هاست جایگزین ربات** (اگر روزی Actions جواب نداد): فقط گزینه‌های رایگان بدون کارت مد نظر باشد — ترجیح همین زنجیره Actions است.

---

## ۱۰. عیب‌یابی سریع

- **ربات آفلاین/منو ندارد** → Actions → `Bot host (24/7 chain)` → Run workflow (دستی). اگر زنجیره قطع شده باشد cron هر ۶ ساعت خودش شروع می‌کند.
- **پست ارسال نشد** → لاگ `force-post`/`weekly-post`. دلایل ممکن: `locked; skipping` (قفل ۵۰ دقیقه‌ای)، `not due` (هنوز هفتگی نشده — با ورودی `force` دور بزن)، `no_candidates` (کانفیگ سالمِ تازه نیست — اول refresh بزن)، `force_retest_failed` (تست ۵ کاندید رد شد)، `http_4xx` از تلگرام (دسترسی ربات/عضویت).
- **کانفیگ بی‌پینگ** → تست تازه قبل از پست کافی نیست؟ یعنی منبع‌ها مرده‌اند؛ refresh بیشتر + منابع بهتر.
- **KV کار نمی‌کند** → `CLOUDFLARE_API_TOKEN` باید دسترسی Workers KV Read/Write داشته باشد.
- **استقرار Worker** → اکشن `Deploy Cloudflare Worker`؛ اگر متوقف شد یعنی `WORKER_SECRET` ثبت نیست.
- هرگز secret/token را در ریپو، لاگ عمومی یا پیام کانال قرار نده.

---

## ۱۱. تاریخچه تصمیم‌ها (خلاصه)

- فاز آزمایشی: ربات فارسی با منو، سهمیه هفتگی، رفرال، تست، پنل ادمین.
- زمان‌بندی با GitHub Actions (به‌جای سرور پولی) + Worker کلودفلر (رایگان، بدون کارت).
- تست TCP دو سطحی: Worker (شبکه CF) + fallback مستقیم از runner.
- راز لو رفته چرخانده شد؛ PAT-as-input از deploy حذف شد؛ deploy بدون secret متوقف می‌شود.
- میزبانی ۲۴/۷ ربات: زنجیره Actions (این نسخه) — قبلاً باز بود، حالا بسته.
- ارسال: پست هفتگی خودکار + `force-post` دستی برای ارسال فوری.
- refresh: پنجره چرخشی ۳۰تایی به‌جای همیشه همان ۳۰ تای اول.

---

## ۱۲. مراحل بعدی پیشنهادی

۱) مشاهده پست خودکار بعدی کانال در جمعه ۱۸:۰۰ تهران (یا `force-post` دستی هر وقت خواست).  ۲) رفع خطای fetch منابع (بند ۹.۲).  ۳) همسان‌سازی WORKER_SECRET (بند ۷).  ۴) دریافت API پنل از صاحب پروژه (بند ۹.۴).  ۵) در بلندمدت: طرح رایگان تست تونل واقعی به‌جای TCP خام.
