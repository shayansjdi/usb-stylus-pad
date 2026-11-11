"""
ماژول کنترل ماوس و نشانگر ویندوز با سرعت بالا و بدون تاخیر
با پشتیبانی کامل از رسم در Adobe Acrobat Reader، Paint، OneNote و لایه ویندوز
"""
import ctypes
import time

user32 = ctypes.windll.user32

# ثابت‌های Windows API برای رویدادهای ماوس
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class MouseController:
    def __init__(self):
        self.screen_width = max(1, user32.GetSystemMetrics(0))
        self.screen_height = max(1, user32.GetSystemMetrics(1))
        self.sensitivity = 1.3
        self.is_dragging = False

    def get_position(self):
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def set_position(self, x, y):
        x = max(0, min(self.screen_width - 1, int(x)))
        y = max(0, min(self.screen_height - 1, int(y)))
        user32.SetCursorPos(x, y)

    def move_relative(self, dx, dy):
        cx, cy = self.get_position()
        nx = cx + int(dx * self.sensitivity)
        ny = cy + int(dy * self.sensitivity)
        self.set_position(nx, ny)
        
        # در صورت درگ یا نوشتن، ارسال رویداد حرکتی رسمی ویندوز برای نرم‌افزارهای PDF و طراحی
        if self.is_dragging:
            norm_x = nx / self.screen_width
            norm_y = ny / self.screen_height
            abs_x = int(norm_x * 65535)
            abs_y = int(norm_y * 65535)
            user32.mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, abs_x, abs_y, 0, 0)

    def move_normalized(self, norm_x, norm_y):
        """انتقال مستقیم مکان‌نما بر اساس مختصات 0 تا 1 تبلت همراه با سیگنال رسمی سخت‌افزاری"""
        x = int(norm_x * self.screen_width)
        y = int(norm_y * self.screen_height)
        self.set_position(x, y)
        abs_x = int(norm_x * 65535)
        abs_y = int(norm_y * 65535)
        user32.mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, abs_x, abs_y, 0, 0)

    def pen_down(self, norm_x, norm_y):
        """شروع رسم در نرم‌افزارهای خارجی (مثل Acrobat Reader / Paint)"""
        x = int(norm_x * self.screen_width)
        y = int(norm_y * self.screen_height)
        self.set_position(x, y)
        abs_x = int(norm_x * 65535)
        abs_y = int(norm_y * 65535)
        user32.mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, abs_x, abs_y, 0, 0)
        time.sleep(0.005)
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        self.is_dragging = True

    def pen_move(self, norm_x, norm_y):
        """ادامه رسم خط در نرم‌افزارهای خارجی با شبیه‌سازی استریم دقیق قلم"""
        x = int(norm_x * self.screen_width)
        y = int(norm_y * self.screen_height)
        self.set_position(x, y)
        abs_x = int(norm_x * 65535)
        abs_y = int(norm_y * 65535)
        user32.mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, abs_x, abs_y, 0, 0)

    def pen_up(self):
        """اتمام رسم خط"""
        cx, cy = self.get_position()
        user32.mouse_event(MOUSEEVENTF_LEFTUP, cx, cy, 0, 0)
        self.is_dragging = False

    def click(self, button="left"):
        cx, cy = self.get_position()
        if button == "left":
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, cx, cy, 0, 0)
            time.sleep(0.015)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, cx, cy, 0, 0)
        elif button == "right":
            user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, cx, cy, 0, 0)
            time.sleep(0.015)
            user32.mouse_event(MOUSEEVENTF_RIGHTUP, cx, cy, 0, 0)

    def double_click(self):
        cx, cy = self.get_position()
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, cx, cy, 0, 0)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, cx, cy, 0, 0)
        time.sleep(0.04)
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, cx, cy, 0, 0)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, cx, cy, 0, 0)

    def mouse_down(self, button="left"):
        cx, cy = self.get_position()
        self.is_dragging = True
        if button == "left":
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, cx, cy, 0, 0)
        elif button == "right":
            user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, cx, cy, 0, 0)

    def mouse_up(self, button="left"):
        cx, cy = self.get_position()
        self.is_dragging = False
        if button == "left":
            user32.mouse_event(MOUSEEVENTF_LEFTUP, cx, cy, 0, 0)
        elif button == "right":
            user32.mouse_event(MOUSEEVENTF_RIGHTUP, cx, cy, 0, 0)

    def scroll(self, amount):
        cx, cy = self.get_position()
        # مقدار مثبت اسکرول به بالا، منفی به پایین
        user32.mouse_event(MOUSEEVENTF_WHEEL, cx, cy, int(amount * 120), 0)


