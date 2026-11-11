"""
لایه شفاف تمام‌صفحه ویندوز برای رسم خطوط قلم نوری و افکت نورافکن (Spotlight)
"""
import tkinter as tk
import queue

class ScreenOverlay:
    def __init__(self, master=None):
        self.cmd_queue = queue.Queue(maxsize=2000)
        self.last_point = None
        self.current_color = "#FF3B30"
        self.current_width = 4
        self.is_visible = False
        self.strokes = [] # ذخیره آی‌دی خطوط برای پاک‌کردن یا پاک‌کن

        # متغیرهای حالت نورافکن (Spotlight)
        self.spotlight_active = False
        self.spotlight_radius = 140
        self.spotlight_laser_enabled = True
        self.spotlight_bg_id = None
        self.spotlight_hole_id = None
        self.spotlight_ring_id = None
        self.spotlight_laser_id = None

        # اگر مستر داده نشده، پنجره مستقل ایجاد می‌کنیم
        if master is None:
            self.root = tk.Tk()
            self._own_root = True
        else:
            self.root = tk.Toplevel(master)
            self._own_root = False

        self.screen_width = max(1, self.root.winfo_screenwidth())
        self.screen_height = max(1, self.root.winfo_screenheight())

        self.root.overrideredirect(True)
        self.root.geometry(f"{self.screen_width}x{self.screen_height}+0+0")
        self.root.attributes("-topmost", True)
        
        # رنگ کلیدی برای شفافیت در ویندوز
        self.trans_color = "#020202"
        self.root.attributes("-transparentcolor", self.trans_color)
        self.root.config(bg=self.trans_color)

        self.canvas = tk.Canvas(
            self.root,
            width=self.screen_width,
            height=self.screen_height,
            bg=self.trans_color,
            highlightthickness=0,
            cursor="crosshair"
        )
        self.canvas.pack(fill="both", expand=True)

        # کلید میانبر Esc برای پاک کردن یا بستن
        self.root.bind("<Escape>", lambda e: self.hide())
        
        # پنجره را ابتدا مخفی می‌کنیم تا زمانی که کاربر شروع به رسم یا نورافکن کند
        self.root.withdraw()
        self._check_queue()

    def show(self):
        if not self.is_visible:
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.is_visible = True

    def hide(self):
        if self.spotlight_active:
            self._disable_spotlight()
        if self.is_visible:
            self.root.withdraw()
            self.is_visible = False

    def toggle(self):
        if self.is_visible:
            self.hide()
        else:
            self.show()

    def queue_command(self, cmd_type, **kwargs):
        try:
            self.cmd_queue.put_nowait((cmd_type, kwargs))
        except queue.Full:
            pass

    def _check_queue(self):
        while not self.cmd_queue.empty():
            try:
                cmd_type, args = self.cmd_queue.get_nowait()
                if cmd_type == "down":
                    self._draw_down(args.get("x", 0), args.get("y", 0), args.get("color"), args.get("width"))
                elif cmd_type == "move":
                    self._draw_move(args.get("x", 0), args.get("y", 0))
                elif cmd_type == "up":
                    self._draw_up()
                elif cmd_type == "clear":
                    self._clear()
                elif cmd_type == "show":
                    self.show()
                elif cmd_type == "hide":
                    self.hide()
                elif cmd_type == "spotlight_start":
                    self._enable_spotlight(args.get("radius", 140), args.get("laser", True))
                elif cmd_type == "spotlight_move":
                    self._move_spotlight(args.get("x", 0.5), args.get("y", 0.5))
                elif cmd_type == "spotlight_stop":
                    self._disable_spotlight()
                elif cmd_type == "spotlight_config":
                    if "radius" in args:
                        self.spotlight_radius = int(args["radius"])
                    if "laser" in args:
                        self.spotlight_laser_enabled = bool(args["laser"])
                    if self.spotlight_active:
                        self._update_spotlight_shape()
            except Exception:
                pass
        self.root.after(10, self._check_queue)

    # ==========================
    # توابع حالت نورافکن (Spotlight)
    # ==========================
    def _enable_spotlight(self, radius=140, laser=True):
        self.spotlight_active = True
        self.spotlight_radius = int(radius)
        self.spotlight_laser_enabled = bool(laser)

        # تاریک کردن پس‌زمینه با ترنسپرنسی زیبا
        try:
            self.root.attributes("-alpha", 0.72)
        except Exception:
            pass

        self.show()

        # پاکسازی المان‌های قدیمی نورافکن
        self.canvas.delete("spotlight")

        # رسم لایه ماسک تیره روی تمام صفحه
        self.spotlight_bg_id = self.canvas.create_rectangle(
            0, 0, self.screen_width, self.screen_height,
            fill="#08080c", outline="", tags="spotlight"
        )

        cx = self.screen_width // 2
        cy = self.screen_height // 2
        r = self.spotlight_radius

        # حفره کاملاً شفاف وسط نورافکن (رنگ کلیدی شفافیت ویندوز)
        self.spotlight_hole_id = self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            fill=self.trans_color, outline="", tags="spotlight"
        )

        # حلقه نورانی دور نورافکن
        self.spotlight_ring_id = self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            fill="", outline="#FFCC00", width=4, tags="spotlight"
        )

        # نقطه لیزر قرمز پررنگ در مرکز
        laser_state = "normal" if self.spotlight_laser_enabled else "hidden"
        self.spotlight_laser_id = self.canvas.create_oval(
            cx - 5, cy - 5, cx + 5, cy + 5,
            fill="#FF3B30", outline="#FFFFFF", width=2,
            state=laser_state, tags="spotlight"
        )

    def _move_spotlight(self, norm_x, norm_y):
        if not self.spotlight_active:
            self._enable_spotlight(self.spotlight_radius, self.spotlight_laser_enabled)

        cx = int(norm_x * self.screen_width)
        cy = int(norm_y * self.screen_height)
        r = self.spotlight_radius

        if self.spotlight_hole_id:
            self.canvas.coords(self.spotlight_hole_id, cx - r, cy - r, cx + r, cy + r)
        if self.spotlight_ring_id:
            self.canvas.coords(self.spotlight_ring_id, cx - r, cy - r, cx + r, cy + r)
        if self.spotlight_laser_id:
            self.canvas.coords(self.spotlight_laser_id, cx - 5, cy - 5, cx + 5, cy + 5)

    def _update_spotlight_shape(self):
        if not self.spotlight_active or not self.spotlight_hole_id:
            return
        coords = self.canvas.coords(self.spotlight_hole_id)
        if coords and len(coords) == 4:
            cx = (coords[0] + coords[2]) / 2
            cy = (coords[1] + coords[3]) / 2
            r = self.spotlight_radius
            self.canvas.coords(self.spotlight_hole_id, cx - r, cy - r, cx + r, cy + r)
            if self.spotlight_ring_id:
                self.canvas.coords(self.spotlight_ring_id, cx - r, cy - r, cx + r, cy + r)
            if self.spotlight_laser_id:
                state = "normal" if self.spotlight_laser_enabled else "hidden"
                self.canvas.itemconfigure(self.spotlight_laser_id, state=state)

    def _disable_spotlight(self):
        self.spotlight_active = False
        self.canvas.delete("spotlight")
        self.spotlight_bg_id = None
        self.spotlight_hole_id = None
        self.spotlight_ring_id = None
        self.spotlight_laser_id = None

        # بازگردانی شفافیت کامل
        try:
            self.root.attributes("-alpha", 1.0)
        except Exception:
            pass

        # اگر خطی روی صفحه نیست، لایه مخفی شود
        if len(self.strokes) == 0:
            self.hide()

    # ==========================
    # توابع رسم قلم نوری (Drawing)
    # ==========================
    def _draw_down(self, norm_x, norm_y, color=None, width=None):
        if self.spotlight_active:
            self._disable_spotlight()

        self.show()
        if color == "eraser":
            self.current_color = self.trans_color
            self.current_width = int(width or 24)
        else:
            if color:
                self.current_color = color
            if width:
                self.current_width = int(width)

        x = norm_x * self.screen_width
        y = norm_y * self.screen_height
        self.last_point = (x, y)

        r = max(2, self.current_width / 2)
        dot = self.canvas.create_oval(
            x - r, y - r, x + r, y + r,
            fill=self.current_color, outline=self.current_color
        )
        self.strokes.append(dot)

    def _draw_move(self, norm_x, norm_y):
        if not self.last_point:
            return
        x = norm_x * self.screen_width
        y = norm_y * self.screen_height
        lx, ly = self.last_point

        line = self.canvas.create_line(
            lx, ly, x, y,
            fill=self.current_color,
            width=self.current_width,
            capstyle=tk.ROUND,
            joinstyle=tk.ROUND,
            smooth=True
        )
        self.strokes.append(line)
        self.last_point = (x, y)

    def _draw_up(self):
        self.last_point = None

    def clear(self):
        self._clear()

    def _clear(self):
        # پاک کردن خطوط بدون آسیب به نورافکن
        for stroke in self.strokes:
            self.canvas.delete(stroke)
        self.strokes.clear()
        self.last_point = None
        if not self.spotlight_active:
            self.hide()


