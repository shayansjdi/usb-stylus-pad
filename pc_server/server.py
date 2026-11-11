"""
برنامه اصلی قلم نوری و ماوس برای ویندوز
ارتباط با گوشی اندروید و iOS از طریق کابل شارژر (USB Tethering) یا شبکه وای‌فای
"""
import sys
import os
import re
import math
import json
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

# اضافه کردن مسیر جاری به sys.path
sys.path.insert(0, os.path.dirname(__file__))

from websocket_server import HybridServer, get_network_ips
from mouse_controller import MouseController
from overlay import ScreenOverlay

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _clamp_float(val, lo, hi, default):
    try:
        num = float(val)
        if not math.isfinite(num):
            return default
        return max(lo, min(hi, num))
    except (TypeError, ValueError):
        return default


def _clamp_int(val, lo, hi, default):
    try:
        num = int(float(val))
        return max(lo, min(hi, num))
    except (TypeError, ValueError):
        return default


def _validate_color(color):
    if color == "eraser":
        return "eraser"
    if isinstance(color, str) and _HEX_COLOR_RE.match(color):
        return color
    return "#FF3B30"


def _validate_button(btn):
    return btn if btn in ("left", "right") else "left"


def _validate_target(target):
    return target if target in ("desktop", "paint") else "desktop"


class DesktopApp:
    def __init__(self, root):
        self.root = root
        self.root.title("قلم نوری و ماوس هوشمند | USB Stylus Pad")
        self.root.geometry("540x740")
        self.root.minsize(500, 680)
        self.root.configure(bg="#121214")

        # مقداردهی کنترلرها و سرور (قبل از ساخت UI تا PIN آماده باشد)
        self.mouse = MouseController()
        self.overlay = ScreenOverlay(master=self.root)
        self.server = HybridServer(
            port=8000,
            on_message=self.handle_incoming_message,
            on_status_change=self.handle_client_status,
        )
        self.connected_client = None

        self.setup_ui()
        self.server.start()

        # به هنگام بستن برنامه
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#121214")
        style.configure("TLabel", background="#121214", foreground="#E4E4E7", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#FFFFFF")
        style.configure("SubHeader.TLabel", font=("Segoe UI", 9), foreground="#A1A1AA")

        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill="both", expand=True)

        # ۱. سربرگ
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 12))

        lbl_title = ttk.Label(header_frame, text="✏️ تبدیل گوشی به قلم نوری و ماوس", style="Header.TLabel")
        lbl_title.pack(anchor="w")

        lbl_sub = ttk.Label(
            header_frame,
            text="اتصال امن با کابل USB و Wi-Fi (بدون تاخیر و مجهز به احراز هویت PIN)",
            style="SubHeader.TLabel",
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # ۲. کارت وضعیت اتصال
        status_card = tk.Frame(main_frame, bg="#1E1E24", bd=1, relief="flat", padx=16, pady=12)
        status_card.pack(fill="x", pady=8)

        status_header = tk.Frame(status_card, bg="#1E1E24")
        status_header.pack(fill="x")

        self.dot_indicator = tk.Canvas(status_header, width=14, height=14, bg="#1E1E24", highlightthickness=0)
        self.dot_indicator.pack(side="left", padx=(0, 8))
        self.draw_status_dot("#FFCC00")

        self.lbl_status = tk.Label(
            status_header,
            text="در انتظار اتصال گوشی...",
            font=("Segoe UI", 11, "bold"),
            fg="#FFCC00",
            bg="#1E1E24",
        )
        self.lbl_status.pack(side="left")

        self.lbl_client_info = tk.Label(
            status_card,
            text="سرور امن روی پورت 8000 آماده به کار است.",
            font=("Segoe UI", 9),
            fg="#A1A1AA",
            bg="#1E1E24",
        )
        self.lbl_client_info.pack(anchor="w", pady=(6, 0))

        # ۳. کارت راهنمای اتصال با سیم شارژر (USB) و کد امنیتی
        guide_card = tk.Frame(
            main_frame,
            bg="#18181B",
            bd=1,
            relief="solid",
            highlightbackground="#27272A",
            padx=16,
            pady=12,
        )
        guide_card.pack(fill="x", pady=8)

        guide_title = tk.Label(
            guide_card,
            text="🔌 نحوه اتصال با کابل USB (اندروید / آیفون):",
            font=("Segoe UI", 10, "bold"),
            fg="#60A5FA",
            bg="#18181B",
        )
        guide_title.pack(anchor="w", pady=(0, 6))

        steps_text = (
            "۱. گوشی را با سیم شارژر به لپ‌تاپ متصل کنید.\n"
            "۲. گزینه «USB Tethering» (در آیفون Personal Hotspot) را روشن کنید.\n"
            "۳. مرورگر گوشی را باز کرده و آدرس زیر را وارد کنید:"
        )
        lbl_steps = tk.Label(
            guide_card,
            text=steps_text,
            justify="left",
            font=("Segoe UI", 9),
            fg="#D4D4D8",
            bg="#18181B",
        )
        lbl_steps.pack(anchor="w")

        # کادر نمایش آدرس URL برای گوشی
        url_box = tk.Frame(guide_card, bg="#09090B", padx=10, pady=8, bd=1, relief="solid")
        url_box.pack(fill="x", pady=(8, 6))

        self.lbl_url = tk.Label(
            url_box,
            text="http://192.168.42.129:8000",
            font=("Consolas", 11, "bold"),
            fg="#34C759",
            bg="#09090B",
        )
        self.lbl_url.pack(side="left")

        btn_copy = tk.Button(
            url_box,
            text="کپی لینک کامل",
            font=("Segoe UI", 8),
            bg="#27272A",
            fg="#FFFFFF",
            relief="flat",
            padx=8,
            pady=2,
            command=self.copy_url,
        )
        btn_copy.pack(side="right")

        # کادر نمایش کد امنیتی PIN
        pin_box = tk.Frame(guide_card, bg="#111827", padx=10, pady=6, bd=1, relief="solid", highlightbackground="#1F2937")
        pin_box.pack(fill="x", pady=(2, 6))

        lbl_pin_title = tk.Label(
            pin_box,
            text="🔐 کد امنیتی (PIN):",
            font=("Segoe UI", 9, "bold"),
            fg="#FBBF24",
            bg="#111827",
        )
        lbl_pin_title.pack(side="left")

        self.lbl_pin = tk.Label(
            pin_box,
            text=self.server.auth_pin,
            font=("Consolas", 13, "bold"),
            fg="#FFFFFF",
            bg="#111827",
            padx=8,
        )
        self.lbl_pin.pack(side="left")

        btn_new_pin = tk.Button(
            pin_box,
            text="🔄 کد جدید",
            font=("Segoe UI", 8),
            bg="#1F2937",
            fg="#D1D5DB",
            relief="flat",
            padx=8,
            pady=2,
            command=self.regenerate_pin,
        )
        btn_new_pin.pack(side="right")

        # انتخاب آی‌پی در صورت وجود چند کارت شبکه
        self.ip_combo = ttk.Combobox(guide_card, state="readonly", font=("Segoe UI", 9))
        self.ip_combo.pack(fill="x", pady=(4, 0))
        self.ip_combo.bind("<<ComboboxSelected>>", self.on_ip_selected)

        # ۴. دکمه‌های کنترل سریع
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=10)

        btn_clear = tk.Button(
            btn_frame,
            text="🗑️ پاک کردن صفحه",
            font=("Segoe UI", 9),
            bg="#27272A",
            fg="#FFFFFF",
            relief="flat",
            padx=8,
            pady=7,
            command=self.overlay.clear,
        )
        btn_clear.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_toggle_overlay = tk.Button(
            btn_frame,
            text="👁️ لایه شفاف",
            font=("Segoe UI", 9),
            bg="#27272A",
            fg="#FFFFFF",
            relief="flat",
            padx=8,
            pady=7,
            command=self.overlay.toggle,
        )
        btn_toggle_overlay.pack(side="left", fill="x", expand=True, padx=4)

        btn_test_spotlight = tk.Button(
            btn_frame,
            text="🔦 تست نورافکن",
            font=("Segoe UI", 9),
            bg="#27272A",
            fg="#FFD60A",
            relief="flat",
            padx=8,
            pady=7,
            command=self.test_spotlight,
        )
        btn_test_spotlight.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # راهنمای ذخیره در PDF
        pdf_hint_box = tk.Frame(
            main_frame,
            bg="#1a202c",
            bd=1,
            relief="solid",
            highlightbackground="#2d3748",
            padx=12,
            pady=10,
        )
        pdf_hint_box.pack(fill="x", pady=(4, 8))
        lbl_pdf_hint_title = tk.Label(
            pdf_hint_box,
            text="📄 نحوه نوشتن و ذخیره دائمی روی PDF:",
            font=("Segoe UI", 9, "bold"),
            fg="#48BB78",
            bg="#1a202c",
        )
        lbl_pdf_hint_title.pack(anchor="w")
        lbl_pdf_hint_body = tk.Label(
            pdf_hint_box,
            text=(
                "در Acrobat Reader یا Edge، ابزار مداد (Draw/Pencil) را فعال کنید.\n"
                "سپس روی گوشی حالت «قلم PDF» یا رسم در برنامه‌ها را بزنید؛ هر چه بنویسید\n"
                "مستقیماً داخل فایل PDF ثبت شده و با Ctrl+S ذخیره می‌شود."
            ),
            justify="left",
            font=("Segoe UI", 8),
            fg="#CBD5E0",
            bg="#1a202c",
        )
        lbl_pdf_hint_body.pack(anchor="w", pady=(3, 0))

        # ۵. پاورقی و دکمه به‌روزرسانی IP
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(side="bottom", fill="x")

        btn_refresh_ip = tk.Button(
            footer_frame,
            text="🔄 بررسی مجدد اتصال کابل USB",
            font=("Segoe UI", 9),
            bg="#1E1E24",
            fg="#A1A1AA",
            relief="flat",
            pady=6,
            command=self.refresh_ips,
        )
        btn_refresh_ip.pack(fill="x")

        # بخش سازنده و لینک به گیت‌هاب (Developed by Shayan)
        dev_frame = tk.Frame(footer_frame, bg="#121214", pady=8)
        dev_frame.pack(fill="x")

        dev_inner = tk.Frame(dev_frame, bg="#121214")
        dev_inner.pack(anchor="center")

        lbl_dev_prefix = tk.Label(
            dev_inner,
            text="Developed by ",
            font=("Segoe UI", 10),
            fg="#A1A1AA",
            bg="#121214",
        )
        lbl_dev_prefix.pack(side="left")

        lbl_shayan = tk.Label(
            dev_inner,
            text="Shayan ↗",
            font=("Segoe UI", 10, "bold underline"),
            fg="#38BDF8",
            bg="#121214",
            cursor="hand2",
        )
        lbl_shayan.pack(side="left")

        def open_github(event):
            webbrowser.open("https://github.com/shayansjdi")

        lbl_shayan.bind("<Button-1>", open_github)
        lbl_shayan.bind("<Enter>", lambda e: lbl_shayan.config(fg="#7DD3FC"))
        lbl_shayan.bind("<Leave>", lambda e: lbl_shayan.config(fg="#38BDF8"))

        self.refresh_ips()

    def draw_status_dot(self, color):
        self.dot_indicator.delete("all")
        self.dot_indicator.create_oval(2, 2, 12, 12, fill=color, outline=color)

    def refresh_ips(self):
        ips = get_network_ips()
        display_list = []
        best_ip = "127.0.0.1"

        for ip, desc in ips:
            display_list.append(f"{ip} ({desc})")
            if "usb" in desc.lower() or "tether" in desc.lower():
                best_ip = ip

        if not display_list:
            display_list = ["127.0.0.1 (لوکال)"]

        self.ip_combo["values"] = display_list
        if display_list:
            default_idx = 0
            for i, text in enumerate(display_list):
                if best_ip in text:
                    default_idx = i
                    break
            self.ip_combo.current(default_idx)
            self.update_url_label(self.ip_combo.get())

    def on_ip_selected(self, event):
        self.update_url_label(self.ip_combo.get())

    def update_url_label(self, selected_text):
        ip = selected_text.split(" ")[0].strip()
        url = f"http://{ip}:8000/?pin={self.server.auth_pin}"
        self.lbl_url.config(text=url)

    def regenerate_pin(self):
        new_pin = self.server.regenerate_pin()
        self.lbl_pin.config(text=new_pin)
        if self.ip_combo.get():
            self.update_url_label(self.ip_combo.get())

    def copy_url(self):
        url = self.lbl_url.cget("text")
        self.root.clipboard_clear()
        self.root.clipboard_append(url)
        messagebox.showinfo("کپی شد", f"لینک اتصال مستقیم (همراه با کد امنیتی) کپی شد:\n{url}")

    def test_spotlight(self):
        if self.overlay.spotlight_active:
            self.overlay.queue_command("spotlight_stop")
        else:
            self.overlay.queue_command("spotlight_start", radius=140, laser=True)
            self.overlay.queue_command("spotlight_move", x=0.5, y=0.5)

    def handle_client_status(self, connected, client_ip):
        def update_ui():
            if connected:
                self.connected_client = client_ip
                self.draw_status_dot("#34C759")
                self.lbl_status.config(text="گوشی متصل شد! 📱", fg="#34C759")
                self.lbl_client_info.config(text=f"دستگاه احراز هویت‌شده: {client_ip} | اتصال امن برقرار است")
            else:
                self.connected_client = None
                self.draw_status_dot("#FFCC00")
                self.lbl_status.config(text="در انتظار اتصال گوشی...", fg="#FFCC00")
                self.lbl_client_info.config(text="ارتباط قطع شد. لطفاً مرورگر گوشی را مجدداً باز کنید.")

        self.root.after(0, update_ui)

    def handle_incoming_message(self, raw_message):
        try:
            data = json.loads(raw_message)
            if not isinstance(data, dict):
                return
            msg_type = data.get("type")
            if not isinstance(msg_type, str):
                return

            # ۱. تغییر حالت کلی (Mode Change)
            if msg_type == "mode_change":
                mode = data.get("mode")
                if mode == "spotlight":
                    radius = _clamp_int(data.get("radius"), 30, 500, 140)
                    laser = bool(data.get("laser", True))
                    self.overlay.queue_command("spotlight_start", radius=radius, laser=laser)
                elif mode == "mouse":
                    self.overlay.queue_command("spotlight_stop")
                elif mode == "draw":
                    self.overlay.queue_command("spotlight_stop")
                    target = _validate_target(data.get("target"))
                    if target == "desktop":
                        self.overlay.queue_command("show")
                    else:
                        self.overlay.queue_command("hide")

            # ۲. دستورات نورافکن (Spotlight)
            elif msg_type == "spotlight_start":
                radius = _clamp_int(data.get("radius"), 30, 500, 140)
                laser = bool(data.get("laser", True))
                x = _clamp_float(data.get("x"), 0.0, 1.0, 0.5)
                y = _clamp_float(data.get("y"), 0.0, 1.0, 0.5)
                self.overlay.queue_command("spotlight_start", radius=radius, laser=laser)
                self.mouse.move_normalized(x, y)

            elif msg_type == "spotlight_move":
                x = _clamp_float(data.get("x"), 0.0, 1.0, 0.5)
                y = _clamp_float(data.get("y"), 0.0, 1.0, 0.5)
                self.overlay.queue_command("spotlight_move", x=x, y=y)
                self.mouse.move_normalized(x, y)

            elif msg_type == "spotlight_stop":
                self.overlay.queue_command("spotlight_stop")

            elif msg_type == "spotlight_config":
                cfg = {}
                if "radius" in data:
                    cfg["radius"] = _clamp_int(data.get("radius"), 30, 500, 140)
                if "laser" in data:
                    cfg["laser"] = bool(data.get("laser"))
                if cfg:
                    self.overlay.queue_command("spotlight_config", **cfg)

            # ۳. دستورات رسم (Draw Mode)
            elif msg_type == "draw_down":
                target = _validate_target(data.get("target"))
                x = _clamp_float(data.get("x"), 0.0, 1.0, 0.0)
                y = _clamp_float(data.get("y"), 0.0, 1.0, 0.0)
                color = _validate_color(data.get("color"))
                width = _clamp_int(data.get("width"), 1, 100, 5)

                if target == "desktop":
                    self.overlay.queue_command("down", x=x, y=y, color=color, width=width)
                else:
                    self.overlay.queue_command("hide")
                    self.mouse.pen_down(x, y)

            elif msg_type == "draw_move":
                target = _validate_target(data.get("target"))
                x = _clamp_float(data.get("x"), 0.0, 1.0, 0.0)
                y = _clamp_float(data.get("y"), 0.0, 1.0, 0.0)

                if target == "desktop":
                    self.overlay.queue_command("move", x=x, y=y)
                else:
                    self.mouse.pen_move(x, y)

            elif msg_type == "draw_up":
                target = _validate_target(data.get("target"))
                if target == "desktop":
                    self.overlay.queue_command("up")
                else:
                    self.mouse.pen_up()

            elif msg_type == "set_draw_target":
                target = _validate_target(data.get("target"))
                if target == "paint":
                    self.overlay.queue_command("hide")
                else:
                    self.overlay.queue_command("show")

            elif msg_type == "clear":
                self.overlay.queue_command("clear")

            # ۴. دستورات ماوس (Mouse Mode & PDF Pen)
            elif msg_type == "mouse_move":
                dx = _clamp_float(data.get("dx"), -1500.0, 1500.0, 0.0)
                dy = _clamp_float(data.get("dy"), -1500.0, 1500.0, 0.0)
                self.mouse.move_relative(dx, dy)

            elif msg_type == "mouse_click":
                btn = _validate_button(data.get("button"))
                self.mouse.click(btn)

            elif msg_type == "mouse_dblclick":
                self.mouse.double_click()

            elif msg_type == "mouse_down":
                btn = _validate_button(data.get("button"))
                self.overlay.queue_command("hide")
                self.mouse.mouse_down(btn)

            elif msg_type == "mouse_up":
                btn = _validate_button(data.get("button"))
                self.mouse.mouse_up(btn)

            elif msg_type == "mouse_scroll":
                amount = _clamp_float(data.get("amount"), -20.0, 20.0, 0.0)
                self.mouse.scroll(amount)

        except Exception:
            pass

    def on_close(self):
        if self.server:
            self.server.stop()
        self.root.destroy()
        sys.exit(0)


if __name__ == "__main__":
    root = tk.Tk()
    app = DesktopApp(root)
    root.mainloop()
