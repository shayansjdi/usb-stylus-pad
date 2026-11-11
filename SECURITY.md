# Security Policy & Architecture (سیاست‌های امنیتی)

## 🛡️ Built-in Security Safeguards

Because **Galam Noori** exposes a local HTTP/WebSocket control server capable of simulating Windows mouse and stylus input, strict security controls are built into the core server (`pc_server/websocket_server.py` and `pc_server/server.py`):

1. **Session PIN Authentication (احراز هویت با کد تصادفی):**
   - On every startup, the server generates a cryptographically random 4-digit PIN using Python's `secrets` module.
   - All WebSocket upgrade requests (`/ws?pin=...`) are validated using constant-time comparison (`secrets.compare_digest`) to prevent timing attacks.
   - Users can regenerate a fresh PIN at any time from the desktop UI.
2. **Brute-Force Rate Limiting (محدودیت تلاش ناموفق):**
   - After **5 failed authentication attempts** from an IP address, that IP is temporarily blocked (`429 Too Many Requests`) for **30 seconds**.
3. **Cross-Site WebSocket Hijacking (CSWSH) Protection:**
   - The server validates the `Origin` header against the `Host` header on WebSocket upgrades, blocking untrusted websites (`403 Forbidden`) from opening background connections to `localhost` or LAN IPs.
4. **DoS & Frame Size Protection:**
   - Enforces RFC 6455 client-to-server masking, bounded frame reads with socket timeouts (Slowloris protection), and a strict **64 KB (`65,536 bytes`) maximum WebSocket payload limit**.
   - Incoming command queues (`overlay.py`) are bounded (`maxsize=2000`) to prevent memory exhaustion.
5. **Strict Input Sanitization & Bounds Clamping:**
   - All coordinates (`x`, `y`, `dx`, `dy`, `amount`), brush widths, spotlight radii, mouse buttons, and hex colors (`^#[0-9a-fA-F]{6}$`) are validated and clamped before touching `user32.dll` or Tkinter.
6. **HTTP Hardening:**
   - Directory listing is explicitly disabled (`403 Forbidden`).
   - Only whitelisted static client files (`/`, `/index.html`, `/style.css`, `/app.js`, `/manifest.json`, `/icon.svg`) are served.
   - Security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Content-Security-Policy`) are injected on all HTTP responses.
7. **Zero Third-Party Dependencies:**
   - Uses only Python's audited standard library—eliminating supply-chain risks from external packages.

---

## ⚠️ Network Usage Recommendations

- **Recommended (Highest Security & Lowest Latency):** Connect via **USB Cable (USB Tethering / Apple Mobile Device Ethernet)**. Traffic stays completely isolated over the physical USB cable.
- **Public / University Wi-Fi:** Always keep your session PIN private and avoid sharing the `?pin=...` URL on untrusted networks. Note that local LAN HTTP/WebSocket traffic is unencrypted (`ws://`) because local private IP addresses do not carry public TLS certificates.

---

## 📩 Reporting a Vulnerability

If you discover a security issue in this project, please open a private report or issue via GitHub:
- **Developer:** [Shayan (@shayansjdi)](https://github.com/shayansjdi)

