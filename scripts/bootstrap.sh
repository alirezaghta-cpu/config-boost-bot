#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "فایل .env پیدا نشد." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

mask() {
  local value="${1:-}"
  if [[ -z "$value" ]]; then printf '****'; else printf '%s****' "${value:0:8}"; fi
}

required=(BOT_TOKEN ADMIN_IDS CHANNEL_ID GROUP_ID GITHUB_REPO GITHUB_TOKEN CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID WORKER_URL BOT_USERNAME)
for key in "${required[@]}"; do
  if [[ -z "${!key:-}" ]]; then
    echo "کلید گمشده: $key" >&2
    exit 1
  fi
done

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

http_code() {
  local output="$1"; shift
  curl -sS -o "$output" -w '%{http_code}' "$@"
}

echo "بررسی توکن ربات $(mask "$BOT_TOKEN")"
code="$(http_code "$tmpdir/getme.json" "https://api.telegram.org/bot${BOT_TOKEN}/getMe")"
[[ "$code" == "200" ]] || { echo "توکن ربات نامعتبر است." >&2; exit 1; }
bot_id="$(python3 - "$tmpdir/getme.json" <<'PY'
import json, sys
data=json.load(open(sys.argv[1], encoding="utf-8"))
if not data.get("ok"):
    raise SystemExit(1)
print(data["result"]["id"])
PY
)"

echo "بررسی توکن Cloudflare $(mask "$CLOUDFLARE_API_TOKEN")"
code="$(http_code "$tmpdir/cf.json" -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  "https://api.cloudflare.com/client/v4/user/tokens/verify")"
[[ "$code" == "200" ]] || { echo "توکن Cloudflare نامعتبر است." >&2; exit 1; }

echo "بررسی توکن GitHub $(mask "$GITHUB_TOKEN")"
code="$(http_code "$tmpdir/gh.json" -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" "https://api.github.com/user")"
[[ "$code" == "200" ]] || { echo "توکن GitHub نامعتبر است." >&2; exit 1; }

if [[ -z "${KV_NAMESPACE_ID:-}" ]]; then
  echo "ساخت KV namespace"
  code="$(http_code "$tmpdir/kv.json" -X POST \
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H "Content-Type: application/json" \
    --data '{"title":"config-boost-bot"}' \
    "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/storage/kv/namespaces")"
  [[ "$code" == "200" ]] || { echo "ساخت KV ناموفق بود." >&2; exit 1; }
  KV_NAMESPACE_ID="$(python3 - "$tmpdir/kv.json" <<'PY'
import json, sys
data=json.load(open(sys.argv[1], encoding="utf-8"))
print(data["result"]["id"])
PY
)"
  export KV_NAMESPACE_ID
  python3 - "$ENV_FILE" "$KV_NAMESPACE_ID" <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1])
value=sys.argv[2]
lines=path.read_text(encoding="utf-8").splitlines()
out=[]
done=False
for line in lines:
    if line.startswith("KV_NAMESPACE_ID="):
        out.append("KV_NAMESPACE_ID="+value)
        done=True
    else:
        out.append(line)
if not done:
    out.append("KV_NAMESPACE_ID="+value)
path.write_text("\n".join(out)+"\n", encoding="utf-8")
PY
  echo "KV ساخته و در .env ثبت شد: $(mask "$KV_NAMESPACE_ID")"
fi

for chat_id in "$CHANNEL_ID" "$GROUP_ID"; do
  code="$(http_code "$tmpdir/chat-${chat_id}.json" \
    --get --data-urlencode "chat_id=${chat_id}" --data-urlencode "user_id=${bot_id}" \
    "https://api.telegram.org/bot${BOT_TOKEN}/getChatMember")"
  [[ "$code" == "200" ]] || { echo "بررسی دسترسی ربات برای مقصد ${chat_id} ناموفق بود." >&2; exit 1; }
  status="$(python3 - "$tmpdir/chat-${chat_id}.json" <<'PY'
import json, sys
data=json.load(open(sys.argv[1], encoding="utf-8"))
print((data.get("result") or {}).get("status", ""))
PY
)"
  if [[ "$status" != "administrator" && "$status" != "creator" ]]; then
    echo "ربات در مقصد ${chat_id} ادمین نیست." >&2
    exit 1
  fi
done

export BOT_TOKEN ADMIN_IDS CHANNEL_ID GROUP_ID GITHUB_TOKEN GITHUB_REPO
export CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID KV_NAMESPACE_ID WORKER_URL BOT_USERNAME

echo "ثبت GitHub Actions secrets"
if python3 <<'PY'
import base64
import ctypes
import ctypes.util
import json
import os
import urllib.error
import urllib.request

repo=os.environ["GITHUB_REPO"]
token=os.environ["GITHUB_TOKEN"]
names=[
    "BOT_TOKEN","ADMIN_IDS","CHANNEL_ID","GROUP_ID","GITHUB_TOKEN","GITHUB_REPO",
    "CLOUDFLARE_API_TOKEN","CLOUDFLARE_ACCOUNT_ID","KV_NAMESPACE_ID","WORKER_URL","BOT_USERNAME"
]
if os.environ.get("WORKER_SECRET"):
    names.append("WORKER_SECRET")
libname=ctypes.util.find_library("sodium")
if not libname:
    raise SystemExit(3)
lib=ctypes.cdll.LoadLibrary(libname)
if lib.sodium_init() < 0:
    raise SystemExit(3)
sealbytes=lib.crypto_box_sealbytes()
lib.crypto_box_seal.argtypes=[ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulonglong, ctypes.c_void_p]
headers={
    "Authorization": "Bearer "+token,
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "config-boost-bootstrap",
}
def call(url, method="GET", payload=None):
    data=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request(url, data=data, method=method, headers={**headers, "Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
base=f"https://api.github.com/repos/{repo}/actions/secrets"
status, body=call(base+"/public-key")
if status != 200:
    raise SystemExit("دریافت کلید عمومی GitHub ناموفق بود.")
public=json.loads(body)
public_key=base64.b64decode(public["key"])
for name in names:
    value=os.environ.get(name, "").encode()
    output=ctypes.create_string_buffer(len(value)+sealbytes)
    message=ctypes.create_string_buffer(value, len(value))
    key=ctypes.create_string_buffer(public_key, len(public_key))
    if lib.crypto_box_seal(output, message, len(value), key) != 0:
        raise SystemExit("رمزگذاری secret ناموفق بود.")
    payload={
        "encrypted_value": base64.b64encode(output.raw).decode(),
        "key_id": public["key_id"],
    }
    status, body=call(base+"/"+name, "PUT", payload)
    if status not in {201, 204}:
        if name == "GITHUB_TOKEN" and status == 422:
            print("GITHUB_TOKEN داخلی Actions است و نیاز به ساخت secret جدا ندارد.")
            continue
        raise SystemExit(f"ثبت secret {name} ناموفق بود: HTTP {status}")
    print(f"secret ثبت شد: {name}")
PY
then
  :
elif command -v gh >/dev/null 2>&1; then
  echo "libsodium پیدا نشد؛ استفاده از GitHub CLI"
  secret_keys=(BOT_TOKEN ADMIN_IDS CHANNEL_ID GROUP_ID GITHUB_REPO CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID KV_NAMESPACE_ID WORKER_URL BOT_USERNAME)
  if [[ -n "${WORKER_SECRET:-}" ]]; then secret_keys+=(WORKER_SECRET); fi
  for key in "${secret_keys[@]}"; do
    printf '%s' "${!key}" | GH_TOKEN="$GITHUB_TOKEN" gh secret set "$key" --repo "$GITHUB_REPO" --body -
  done
  echo "GITHUB_TOKEN داخلی Actions است."
else
  echo "برای ثبت secrets، libsodium یا GitHub CLI لازم است." >&2
  exit 1
fi

if command -v npx >/dev/null 2>&1; then
  echo "استقرار Cloudflare Worker"
  npx --yes wrangler deploy worker/tcp-test.js \
    --name config-boost-tcp-test \
    --compatibility-date 2024-11-01
  if [[ -n "${WORKER_SECRET:-}" ]]; then
    printf '%s' "$WORKER_SECRET" | npx --yes wrangler secret put WORKER_SECRET --name config-boost-tcp-test
  fi
else
  echo "npx موجود نیست؛ Worker را دستی با «npx wrangler deploy» مستقر کنید."
fi

echo "راه‌اندازی اولیه با موفقیت تمام شد."
