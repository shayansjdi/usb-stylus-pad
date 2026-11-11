"""
سرور ترکیبی HTTP و WebSocket مستقل بدون وابستگی به کتابخانه‌های خارجی
جهت ارتباط پرسرعت و امن گوشی با کامپیوتر از طریق کابل USB یا شبکه محلی

موارد امنیتی اعمال‌شده:
- احراز هویت نشست با کد امنیتی تصادفی (PIN) و مقایسه مقاوم در برابر Timing Attack
- محافظت در برابر حملات Brute-Force با محدودیت نرخ تلاش (Rate Limiting)
- محافظت در برابر Cross-Site WebSocket Hijacking (اعتبارسنجی هدر Origin)
- محدودیت حداکثر اندازه فریم WebSocket جهت جلوگیری از حملات DoS / پر شدن حافظه
- غیرفعال‌سازی نمایش لیست دایرکتوری‌ها و اعمال هدرهای امنیتی HTTP
"""
import http.server
import socketserver
import socket
import base64
import hashlib
import struct
import threading
import secrets
import time
import urllib.parse
import os
import subprocess

MAX_WS_PAYLOAD = 65536  # حداکثر ۶۴ کیلوبایت برای هر پیام وب‌سوکت
MAX_AUTH_FAILURES = 5
LOCKOUT_SECONDS = 30
ALLOWED_STATIC_PATHS = {
    "/",
    "/index.html",
    "/style.css",
    "/app.js",
    "/manifest.json",
    "/icon.svg",
}


def get_network_ips():
    """یافتن تمام IPهای فعال سیستم، با اولویت کابل USB (Tethering)"""
    ips = []
    usb_ips = []
    wifi_ips = []

    try:
        # استخراج آدرس‌ها از ipconfig برای شناسایی دقیق نام کارت شبکه
        output = subprocess.check_output("ipconfig", text=True, errors="ignore")
        current_adapter = ""
        for line in output.splitlines():
            line_str = line.strip()
            if "adapter" in line.lower() or "کارت شبکه" in line:
                current_adapter = line_str
            if "IPv4" in line or "آدرس IPv4" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    ip = parts[1].strip().split("(")[0].strip()
                    if ip and not ip.startswith("127."):
                        is_android_usb = any(
                            x in current_adapter.lower()
                            for x in ["rndis", "tether", "remote ndis"]
                        ) or ip.startswith("192.168.42.")
                        is_apple_usb = (
                            "apple" in current_adapter.lower()
                            or ip.startswith("172.20.10.")
                        )

                        if is_android_usb:
                            usb_ips.append((ip, "کابل USB اندروید (Tethering)"))
                        elif is_apple_usb:
                            usb_ips.append((ip, "کابل USB آیفون/آیپد (Apple Tethering)"))
                        elif (
                            "wi-fi" in current_adapter.lower()
                            or "wireless" in current_adapter.lower()
                        ):
                            wifi_ips.append((ip, "شبکه وای‌فای (Wi-Fi)"))
                        else:
                            adapter_name = (
                                current_adapter.split("adapter")[-1]
                                .replace(":", "")
                                .strip()
                                or "کارت شبکه"
                            )
                            ips.append((ip, adapter_name))
    except Exception:
        pass

    # روش کمکی با سوکت
    if not usb_ips and not wifi_ips and not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            main_ip = s.getsockname()[0]
            s.close()
            ips.append((main_ip, "شبکه اصلی"))
        except Exception:
            ips.append(("127.0.0.1", "لوکال‌هاست"))

    # ترکیب نتایج با اولویت کابل USB
    all_found = usb_ips + wifi_ips + ips
    seen = set()
    result = []
    for ip, desc in all_found:
        if ip not in seen:
            seen.add(ip)
            result.append((ip, desc))
    return result


def _recv_exact(sock, num_bytes, timeout=5.0):
    """خواندن دقیق تعداد مشخصی بایت با تایم‌اوت جهت جلوگیری از حملات Slowloris"""
    prev_timeout = sock.gettimeout()
    sock.settimeout(timeout)
    data = bytearray()
    try:
        while len(data) < num_bytes:
            chunk = sock.recv(num_bytes - len(data))
            if not chunk:
                return None
            data.extend(chunk)
        return bytes(data)
    finally:
        sock.settimeout(prev_timeout)


class HybridServer:
    def __init__(
        self,
        port=8000,
        static_dir=None,
        on_message=None,
        on_status_change=None,
        auth_pin=None,
    ):
        self.port = port
        self.static_dir = static_dir or os.path.join(
            os.path.dirname(__file__), "static"
        )
        self.on_message = on_message
        self.on_status_change = on_status_change
        # تولید کد امنیتی تصادفی ۴ رقمی در هر بار اجرای برنامه
        self.auth_pin = auth_pin or str(secrets.randbelow(9000) + 1000)
        self._auth_failures = {}  # ip -> (count, lockout_until)
        self._auth_lock = threading.Lock()
        self.server = None
        self.thread = None
        self.is_running = False

    def regenerate_pin(self):
        with self._auth_lock:
            self.auth_pin = str(secrets.randbelow(9000) + 1000)
            self._auth_failures.clear()
        return self.auth_pin

    def _is_rate_limited(self, ip):
        now = time.time()
        with self._auth_lock:
            count, lockout_until = self._auth_failures.get(ip, (0, 0.0))
            if now < lockout_until:
                return True
            if lockout_until > 0 and now >= lockout_until:
                self._auth_failures.pop(ip, None)
        return False

    def _record_auth_failure(self, ip):
        now = time.time()
        with self._auth_lock:
            count, _ = self._auth_failures.get(ip, (0, 0.0))
            count += 1
            lockout_until = now + LOCKOUT_SECONDS if count >= MAX_AUTH_FAILURES else 0.0
            self._auth_failures[ip] = (count, lockout_until)

    def _clear_auth_failures(self, ip):
        with self._auth_lock:
            self._auth_failures.pop(ip, None)

    def start(self):
        handler_class = self._create_handler()

        class CustomServer(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

        self.server = CustomServer(("0.0.0.0", self.port), handler_class)
        self.is_running = True
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        self.thread.start()

    def stop(self):
        self.is_running = False
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def _create_handler(outer_self):
        class CustomHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(
                    *args, directory=outer_self.static_dir, **kwargs
                )

            def log_message(self, format, *args):
                # خاموش کردن لاگ‌های پر سر و صدای ترمینال برای پرفورمنس بالا
                pass

            def list_directory(self, path):
                # جلوگیری از افشای لیست فایل‌ها
                self.send_error(403, "Directory listing is disabled")
                return None

            def end_headers(self):
                # افزودن هدرهای امنیتی استاندارد
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Cache-Control", "no-store")
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                    "style-src 'self' 'unsafe-inline'; connect-src 'self' ws: wss:; "
                    "img-src 'self' data:;",
                )
                super().end_headers()

            def do_GET(self):
                parsed = urllib.parse.urlsplit(self.path)
                if self.headers.get("Upgrade", "").lower() == "websocket":
                    self.handle_websocket(parsed)
                    return

                if parsed.path not in ALLOWED_STATIC_PATHS:
                    self.send_error(404, "Not Found")
                    return

                self.path = "/index.html" if parsed.path == "/" else parsed.path
                super().do_GET()

            def handle_websocket(self, parsed):
                client_ip = self.client_address[0]

                # ۱. بررسی محدودیت تلاش‌های ناموفق (Rate Limiting)
                if outer_self._is_rate_limited(client_ip):
                    self.send_error(429, "Too Many Failed Attempts")
                    return

                # ۲. جلوگیری از حملات Cross-Site WebSocket Hijacking (CSWSH)
                origin = self.headers.get("Origin")
                host = self.headers.get("Host")
                if origin and host:
                    origin_netloc = urllib.parse.urlparse(origin).netloc.lower()
                    if origin_netloc != host.lower():
                        self.send_error(403, "Forbidden Origin")
                        return

                # ۳. اعتبارسنجی کد امنیتی (PIN) در زمان ارتقای اتصال
                query_params = urllib.parse.parse_qs(parsed.query)
                client_pin = query_params.get("pin", [""])[0].strip()
                if not client_pin or not secrets.compare_digest(
                    client_pin, outer_self.auth_pin
                ):
                    outer_self._record_auth_failure(client_ip)
                    self.send_error(401, "Invalid or missing security PIN")
                    return

                outer_self._clear_auth_failures(client_ip)

                # ۴. اعتبارسنجی کلید استاندارد RFC 6455
                key = self.headers.get("Sec-WebSocket-Key")
                if not key or len(key) > 64:
                    self.send_error(400, "Invalid Sec-WebSocket-Key")
                    return

                accept_val = base64.b64encode(
                    hashlib.sha1(
                        (
                            key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
                        ).encode("utf-8")
                    ).digest()
                ).decode("utf-8")

                handshake = (
                    "HTTP/1.1 101 Switching Protocols\r\n"
                    "Upgrade: websocket\r\n"
                    "Connection: Upgrade\r\n"
                    f"Sec-WebSocket-Accept: {accept_val}\r\n\r\n"
                )
                self.wfile.write(handshake.encode("utf-8"))
                self.wfile.flush()

                sock = self.request
                sock.settimeout(None)
                if outer_self.on_status_change:
                    outer_self.on_status_change(True, client_ip)

                try:
                    while outer_self.is_running:
                        head = sock.recv(2)
                        if not head or len(head) < 2:
                            break
                        b1, b2 = head[0], head[1]
                        opcode = b1 & 0x0F
                        if opcode == 8:  # بستن اتصال
                            break

                        masked = (b2 & 0x80) != 0
                        if not masked:
                            # طبق استاندارد RFC 6455 فریم کلاینت به سرور باید Mask شده باشد
                            break

                        payload_len = b2 & 0x7F
                        if payload_len == 126:
                            len_bytes = _recv_exact(sock, 2)
                            if not len_bytes:
                                break
                            payload_len = struct.unpack(">H", len_bytes)[0]
                        elif payload_len == 127:
                            len_bytes = _recv_exact(sock, 8)
                            if not len_bytes:
                                break
                            payload_len = struct.unpack(">Q", len_bytes)[0]

                        # جلوگیری از حملات پر کردن حافظه (DoS)
                        if payload_len > MAX_WS_PAYLOAD:
                            sock.sendall(bytearray([0x88, 0x02, 0x03, 0xF1]))
                            break

                        masks = _recv_exact(sock, 4)
                        if not masks:
                            break

                        payload_raw = (
                            _recv_exact(sock, payload_len)
                            if payload_len > 0
                            else b""
                        )
                        if payload_raw is None:
                            break

                        payload = bytearray(payload_raw)
                        for i in range(len(payload)):
                            payload[i] ^= masks[i % 4]

                        if opcode == 1:  # Text message
                            text = payload.decode("utf-8", errors="ignore")
                            if outer_self.on_message:
                                outer_self.on_message(text)
                        elif opcode == 9:  # Ping
                            sock.sendall(bytearray([0x8A, 0x00]))
                except Exception:
                    pass
                finally:
                    if outer_self.on_status_change:
                        outer_self.on_status_change(False, client_ip)

        return CustomHandler
