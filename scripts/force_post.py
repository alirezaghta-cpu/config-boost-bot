from __future__ import annotations

import html
import json
import os
import socket
import ipaddress
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bot.locales import fa  # noqa: E402

PRIORITY_COUNTRIES = ("DE", "FR", "NL", "CA", "US")
IRAN_TLS_PORTS = {8443, 2053, 2083, 2087, 2096, 80}


def _proto_port_score(record: dict) -> int:
    proto = str(record.get("protocol") or "").lower()
    sec = str(record.get("security") or "").lower()
    port = int(record.get("port") or 0)
    score = 0
    if proto == "vless" and sec == "reality":
        score += 60
    elif proto == "trojan":
        score += 45
    elif proto == "vless":
        score += 35
    elif proto == "vmess":
        score += 20
    else:
        score += 5
    if port == 443:
        score += 25
    elif port in IRAN_TLS_PORTS:
        score += 12
    return score


def req(url, method='GET', headers=None, data=None, timeout=15):
    request_obj = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request_obj, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


BOT_TOKEN = os.environ['BOT_TOKEN'].strip()
CHANNEL_ID = int(os.environ['CHANNEL_ID'])
GROUP_ID = int(os.environ['GROUP_ID'])
WORKER_URL = os.environ['WORKER_URL'].rstrip('/')
WORKER_SECRET = os.environ.get('WORKER_SECRET', '').strip()
CF_TOKEN = os.environ['CLOUDFLARE_API_TOKEN']
CF_ACCOUNT = os.environ['CLOUDFLARE_ACCOUNT_ID']
KV_NS = os.environ['KV_NAMESPACE_ID']
BOT_USERNAME = os.environ['BOT_USERNAME'].lstrip('@')
KV_BASE = 'https://api.cloudflare.com/client/v4/accounts/' + CF_ACCOUNT + '/storage/kv/namespaces/' + KV_NS


def kv_text(key):
    status, body = req(KV_BASE + '/values/' + urllib.parse.quote(key, safe=''), headers={'Authorization': 'Bearer ' + CF_TOKEN})
    if status == 404:
        return None
    if status >= 400:
        raise RuntimeError('kv read failed: ' + str(status))
    return body.decode('utf-8')


def kv_json(key, default=None):
    raw = kv_text(key)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except ValueError:
        return default


def iran_votes(item_id):
    try:
        data = kv_json('iran:' + str(item_id), None)
    except Exception:
        return {'ok': [], 'fail': []}
    if not isinstance(data, dict):
        return {'ok': [], 'fail': []}
    ok = data.get('ok') or []
    fail = data.get('fail') or []
    if not isinstance(ok, list) or not isinstance(fail, list):
        return {'ok': [], 'fail': []}
    return {'ok': [int(x) for x in ok], 'fail': [int(x) for x in fail]}


def kv_put(key, value, as_json=False):
    data = json.dumps(value, ensure_ascii=False) if as_json else str(value)
    status, _ = req(
        KV_BASE + '/values/' + urllib.parse.quote(key, safe=''),
        method='PUT',
        headers={'Authorization': 'Bearer ' + CF_TOKEN, 'Content-Type': 'text/plain; charset=utf-8'},
        data=data.encode('utf-8'),
    )
    if status >= 400:
        raise RuntimeError('kv write failed: ' + str(status))


def direct_test(host, port):
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        ip = infos[0][4][0]
        if not ipaddress.ip_address(ip).is_global:
            return {'ok': False}
        started = time.time()
        with socket.create_connection((ip, port), timeout=8):
            pass
        return {'ok': True, 'ip': ip, 'latency_ms': int((time.time() - started) * 1000)}
    except Exception:
        return {'ok': False}


def worker_test(host, port):
    endpoint = WORKER_URL if WORKER_URL.endswith('/test') else WORKER_URL + '/test'
    headers = {'Content-Type': 'application/json'}
    if WORKER_SECRET:
        headers['X-Worker-Secret'] = WORKER_SECRET
    try:
        status, body = req(
            endpoint,
            method='POST',
            headers=headers,
            data=json.dumps({'host': host, 'port': port}).encode('utf-8'),
            timeout=10,
        )
        if status == 200:
            payload = json.loads(body)
            if isinstance(payload, dict) and payload.get('ok'):
                return payload
    except Exception:
        pass
    return direct_test(host, port)


def telegram(method, payload):
    status, body = req(
        'https://api.telegram.org/bot' + BOT_TOKEN + '/' + method,
        method='POST',
        headers={'Content-Type': 'application/json'},
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
    )
    try:
        return status, json.loads(body)
    except ValueError:
        return status, {}


def send(chat_id, text, buttons):
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML', 'reply_markup': buttons}
    status, data = telegram('sendMessage', payload)
    if status == 429:
        wait = int(((data.get('parameters') or {}).get('retry_after') or 5))
        time.sleep(wait + 1)
        status, data = telegram('sendMessage', payload)
    return status < 400 and bool(data.get('ok')), status


def main():
    ids = kv_json('configs:healthy', []) or []
    cutoff = time.time() - 7 * 86400
    candidates = []
    for item_id in ids:
        record = kv_json('config:' + str(item_id))
        if not isinstance(record, dict) or not record.get('healthy') or not record.get('ip'):
            continue
        if float(record.get('tested_at', 0)) < cutoff:
            continue
        record['id'] = str(item_id)
        candidates.append(record)
    votes_by_id = {c['id']: iran_votes(c['id']) for c in candidates}
    candidates.sort(
        key=lambda c: (
            0 if str(c.get('country_code') or '') in PRIORITY_COUNTRIES else 1,
            -_proto_port_score(c),
            -float(c.get('tested_at') or 0),
        )
    )
    if not candidates:
        print(json.dumps({'error': 'no_candidates'}))
        raise SystemExit(1)
    selected = None
    tcp = {'ok': False}
    attempts = []
    for candidate in candidates[:5]:
        tcp = worker_test(str(candidate['host']), int(candidate['port']))
        attempts.append({'id': candidate['id'], 'ok': bool(tcp.get('ok'))})
        if tcp.get('ok') and tcp.get('ip'):
            selected = candidate
            break
    if selected is None:
        kv_put('last_error', {'ts': time.time(), 'event': 'force_retest_failed', 'attempts': attempts}, as_json=True)
        print(json.dumps({'error': 'force_retest_failed', 'attempts': attempts}))
        raise SystemExit(1)
    link = 'https://t.me/' + BOT_USERNAME + '?start=cfg_' + selected['id']
    code = html.escape(str(selected.get('uri', '')), quote=False)
    selected_votes = votes_by_id.get(selected['id'], {'ok': [], 'fail': []})
    text = fa.channel_post(selected, BOT_USERNAME, code, iran_ok=len(selected_votes['ok']), iran_fail=len(selected_votes['fail']))
    buttons = {'inline_keyboard': [[{'text': fa.BTN_TEST, 'url': link}], [{'text': fa.BTN_COPY_FROM_BOT, 'url': link}]]}
    sent = []
    errors = []
    for chat_id in (CHANNEL_ID, GROUP_ID):
        ok, status = send(chat_id, text, buttons)
        if ok:
            sent.append(chat_id)
        else:
            errors.append(str(chat_id) + ':' + str(status))
    if sent:
        now = time.time()
        kv_put('posted:' + selected['id'], str(now))
        kv_put('last_post', {'ts': now, 'config_id': selected['id'], 'targets': sent, 'force': True}, as_json=True)
    print(json.dumps({'posted': selected['id'], 'targets': sent, 'errors': errors, 'attempts': attempts}))
    if not sent:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
