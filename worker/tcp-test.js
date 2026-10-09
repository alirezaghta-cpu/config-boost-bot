import { connect } from "cloudflare:sockets";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type,X-Worker-Secret",
  "Content-Type": "application/json; charset=utf-8",
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: cors });
}

function validPort(port) {
  return Number.isInteger(port) && port >= 1 && port <= 65535;
}

function validHost(host) {
  return typeof host === "string" && host.length > 0 && host.length <= 253 &&
    /^[A-Za-z0-9._:-]+$/.test(host);
}

function isIPv4(value) {
  const parts = value.split(".");
  return parts.length === 4 && parts.every((part) => /^\d{1,3}$/.test(part) && Number(part) <= 255);
}

function isPublicIPv4(ip) {
  if (!isIPv4(ip)) return false;
  const [a, b] = ip.split(".").map(Number);
  if (a === 0 || a === 10 || a === 127 || a >= 224) return false;
  if (a === 169 && b === 254) return false;
  if (a === 172 && b >= 16 && b <= 31) return false;
  if (a === 192 && b === 168) return false;
  if (a === 100 && b >= 64 && b <= 127) return false;
  return true;
}

async function resolveA(host) {
  if (isIPv4(host)) return host;
  const url = `https://cloudflare-dns.com/dns-query?name=${encodeURIComponent(host)}&type=A`;
  const response = await fetch(url, {
    headers: { Accept: "application/dns-json" },
  });
  if (!response.ok) throw new Error(`dns_http_${response.status}`);
  const payload = await response.json();
  const answer = (payload.Answer || []).find((item) => item.type === 1 && isIPv4(item.data));
  if (!answer) throw new Error("dns_no_a_record");
  return answer.data;
}

async function tcpTest(host, port) {
  const ip = await resolveA(host);
  if (!isPublicIPv4(ip)) throw new Error("private_or_invalid_ip");

  let socket;
  let timer;
  const started = Date.now();
  try {
    socket = connect({ hostname: ip, port });
    const timeout = new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error("tcp_timeout")), 8000);
    });
    await Promise.race([socket.opened, timeout]);
    return { ok: true, ip, latency_ms: Date.now() - started };
  } finally {
    if (timer) clearTimeout(timer);
    if (socket) {
      try {
        socket.close();
      } catch (error) {
        console.log("socket_close_failed", error?.name || "Error");
      }
    }
  }
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });

    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return json({ ok: true });
    }
    if (request.method !== "POST" || url.pathname !== "/test") {
      return json({ ok: false, error: "not_found" }, 404);
    }
    if (env.WORKER_SECRET && request.headers.get("X-Worker-Secret") !== env.WORKER_SECRET) {
      return json({ ok: false, error: "unauthorized" }, 401);
    }

    try {
      const body = await request.json();
      const host = String(body.host || "").trim();
      const port = Number(body.port);
      if (!validHost(host) || !validPort(port)) {
        return json({ ok: false, error: "invalid_host_or_port" }, 400);
      }
      return json(await tcpTest(host, port));
    } catch (error) {
      return json({ ok: false, ip: null, latency_ms: null, error: error?.message || "tcp_error" });
    }
  },
};
