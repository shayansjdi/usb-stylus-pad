// ==========================================
// تنظیمات اولیه و متغیرهای وضعیت (State)
// ==========================================
let ws = null;
let currentMode = "draw"; // "draw" یا "mouse" یا "spotlight"
let currentColor = "#FF3B30"; // رنگ پیش‌فرض: قرمز
let isEraser = false;
let currentBrushSize = 6;
let drawTarget = "desktop"; // "desktop" (لایه شفاف) یا "paint" (نرم‌افزارها/Acrobat)
let isDragging = false;
let isPdfPenActive = false; // حالت نوشتن در PDF در مود ماوس
let isPointerDown = false;
let isConnected = false;

// متغیرهای نورافکن (Spotlight)
let spotlightRadius = 140;
let spotlightLaser = true;

// متغیرهای ماوس و ژست‌های لمسی
let lastTouchX = 0;
let lastTouchY = 0;
let lastTouchTime = 0;
let lastTapTime = 0;
let touchMoved = false;
let activeTouchCount = 0;
let lastTwoFingerY = 0;

// المان‌های DOM
const padCanvas = document.getElementById("pad-canvas");
const ctx = padCanvas.getContext("2d");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const sidePalette = document.getElementById("side-palette");
const spotlightPalette = document.getElementById("spotlight-palette");
const mouseControls = document.getElementById("mouse-controls-bar");
const touchpadHint = document.getElementById("touchpad-hint");
const spotlightHint = document.getElementById("spotlight-hint");
const mouseHintTitle = document.getElementById("mouse-hint-title");
const mouseHintDesc = document.getElementById("mouse-hint-desc");
const btnModeDraw = document.getElementById("btn-mode-draw");
const btnModeMouse = document.getElementById("btn-mode-mouse");
const btnModeSpotlight = document.getElementById("btn-mode-spotlight");
const btnDrag = document.getElementById("btn-drag-toggle");
const btnPdfPen = document.getElementById("btn-pdf-pen");
const pdfPenText = document.getElementById("pdf-pen-text");
const btnEraser = document.getElementById("btn-eraser");
const portraitWarning = document.getElementById("portrait-warning");
const toastMsg = document.getElementById("toast-msg");
const pinModal = document.getElementById("pin-modal");
const pinInput = document.getElementById("pin-input");
const pinError = document.getElementById("pin-error");

let authPin = "";
let openedOnce = false;
let reconnectTimer = null;

let toastTimer = null;
function showToast(text, duration = 3000) {
    if (!toastMsg) return;
    toastMsg.innerText = text;
    toastMsg.classList.remove("hidden");
    toastMsg.style.opacity = "1";
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
        toastMsg.style.opacity = "0";
        setTimeout(() => toastMsg.classList.add("hidden"), 300);
    }, duration);
}

// بررسی و اعمال جهت صفحه (افقی / Landscape)
function checkOrientation() {
    if (window.innerHeight > window.innerWidth) {
        if (portraitWarning) portraitWarning.classList.remove("hidden");
    } else {
        if (portraitWarning) portraitWarning.classList.add("hidden");
    }
    resizeCanvas();
}

function lockLandscape() {
    try {
        if (screen.orientation && screen.orientation.lock) {
            screen.orientation.lock("landscape").catch(() => {});
        }
    } catch (e) {}
}

// تنظیم ابعاد Canvas بر اساس رزولوشن صفحه
function resizeCanvas() {
    const container = document.getElementById("pad-container");
    if (!container) return;
    const dpr = window.devicePixelRatio || 1;
    padCanvas.width = container.clientWidth * dpr;
    padCanvas.height = container.clientHeight * dpr;
    ctx.scale(dpr, dpr);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
}

window.addEventListener("resize", checkOrientation);
window.addEventListener("orientationchange", () => setTimeout(checkOrientation, 200));

// ارتعاش گوشی (Haptic Feedback)
function vibrate(ms = 15) {
    if (navigator.vibrate) {
        navigator.vibrate(ms);
    }
}

// احراز هویت با PIN و اتصال امن WebSocket
function showPinModal(showErr = false) {
    if (!pinModal) return;
    pinModal.classList.remove("hidden");
    if (pinError) {
        if (showErr) pinError.classList.remove("hidden");
        else pinError.classList.add("hidden");
    }
    if (pinInput) {
        pinInput.value = "";
        setTimeout(() => pinInput.focus(), 100);
    }
}

function hidePinModal() {
    if (pinModal) pinModal.classList.add("hidden");
    if (pinError) pinError.classList.add("hidden");
}

function submitPin() {
    if (!pinInput) return;
    const val = pinInput.value.trim();
    if (!/^\d{4}$/.test(val)) {
        if (pinError) {
            pinError.innerText = "لطفاً کد ۴ رقمی معتبر وارد کنید.";
            pinError.classList.remove("hidden");
        }
        return;
    }
    authPin = val;
    sessionStorage.setItem("galam_pin", authPin);
    hidePinModal();
    connectWebSocket();
}

function connectWebSocket() {
    if (!authPin) {
        showPinModal(false);
        updateStatus(false, "در انتظار کد امنیتی 🔐");
        return;
    }

    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws?pin=${encodeURIComponent(authPin)}`;

    updateStatus(false, "در حال اتصال امن به کامپیوتر...");
    openedOnce = false;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        openedOnce = true;
        hidePinModal();
        updateStatus(true, "متصل به کامپیوتر 🟢");
        vibrate(30);
    };

    ws.onclose = () => {
        if (!openedOnce) {
            // رد اتصال در مرحله هندشیک (کد اشتباه یا مسدود شدن موقت)
            authPin = "";
            sessionStorage.removeItem("galam_pin");
            updateStatus(false, "کد امنیتی نامعتبر 🔐");
            showPinModal(true);
            return;
        }
        updateStatus(false, "قطع اتصال 🔴 (در حال تلاش مجدد)");
        reconnectTimer = setTimeout(connectWebSocket, 2000);
    };

    ws.onerror = () => {
        if (ws) ws.close();
    };
}

function updateStatus(connected, text) {
    isConnected = connected;
    if (connected) {
        statusDot.className = "dot connected";
    } else {
        statusDot.className = "dot disconnected";
    }
    statusText.innerText = text;
}

function sendMsg(obj) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(obj));
    }
}

// ==========================================
// مدیریت حالت‌های برنامه (Draw / Mouse / Spotlight)
// ==========================================
function setMode(mode) {
    currentMode = mode;
    vibrate(20);

    // ریست کلاس‌های فعال دکمه‌های هدر
    btnModeDraw.classList.remove("active");
    btnModeMouse.classList.remove("active");
    if (btnModeSpotlight) btnModeSpotlight.classList.remove("active");

    // مخفی‌سازی اولیه تمام پنل‌ها
    sidePalette.classList.add("hidden");
    if (spotlightPalette) spotlightPalette.classList.add("hidden");
    mouseControls.classList.add("hidden");
    touchpadHint.classList.add("hidden");
    if (spotlightHint) spotlightHint.classList.add("hidden");

    if (mode === "draw") {
        btnModeDraw.classList.add("active");
        sidePalette.classList.remove("hidden");
        padCanvas.style.cursor = "crosshair";
        sendMsg({ type: "mode_change", mode: "draw", target: drawTarget });
    } else if (mode === "mouse") {
        btnModeMouse.classList.add("active");
        mouseControls.classList.remove("hidden");
        touchpadHint.classList.remove("hidden");
        padCanvas.style.cursor = "default";
        ctx.clearRect(0, 0, padCanvas.width, padCanvas.height);
        sendMsg({ type: "mode_change", mode: "mouse" });
    } else if (mode === "spotlight") {
        if (btnModeSpotlight) btnModeSpotlight.classList.add("active");
        if (spotlightPalette) spotlightPalette.classList.remove("hidden");
        if (spotlightHint) spotlightHint.classList.remove("hidden");
        padCanvas.style.cursor = "crosshair";
        ctx.clearRect(0, 0, padCanvas.width, padCanvas.height);
        sendMsg({
            type: "mode_change",
            mode: "spotlight",
            radius: spotlightRadius,
            laser: spotlightLaser
        });
        showToast("🔦 نورافکن فعال شد: انگشت را بکشید تا نور روی صفحه حرکت کند", 2500);
    }
}

// ==========================================
// حالت نورافکن (Spotlight)
// ==========================================
function setSpotlightSize(radius, btn) {
    spotlightRadius = radius;
    vibrate(15);
    document.querySelectorAll("#spotlight-palette .action-btn").forEach(b => {
        if (b.id.startsWith("btn-spot-")) b.classList.remove("active");
    });
    if (btn) btn.classList.add("active");
    sendMsg({ type: "spotlight_config", radius: radius });
}

function toggleSpotlightLaser() {
    spotlightLaser = !spotlightLaser;
    vibrate(20);
    const laserBtn = document.getElementById("btn-spot-laser");
    const label = document.getElementById("laser-label");
    if (spotlightLaser) {
        if (laserBtn) laserBtn.classList.add("active");
        if (label) label.innerText = "لیزر روشن";
    } else {
        if (laserBtn) laserBtn.classList.remove("active");
        if (label) label.innerText = "لیزر خاموش";
    }
    sendMsg({ type: "spotlight_config", laser: spotlightLaser });
}

// ==========================================
// حالت قلم PDF در مود ماوس (PDF Pen Mode)
// ==========================================
function togglePdfPen() {
    vibrate(25);
    isPdfPenActive = !isPdfPenActive;

    if (isPdfPenActive) {
        if (btnPdfPen) btnPdfPen.classList.add("active");
        if (pdfPenText) pdfPenText.innerText = "قلم فعال";
        if (mouseHintTitle) mouseHintTitle.innerText = "🖊️ حالت قلم PDF فعال است";
        if (mouseHintDesc) mouseHintDesc.innerText = "لمس کنید و بنویسید (در پایان در Acrobat کلید Ctrl+S بزنید)";
        showToast("🖊️ قلم PDF فعال شد: مستقیماً در Acrobat بنویسید", 3000);
    } else {
        if (btnPdfPen) btnPdfPen.classList.remove("active");
        if (pdfPenText) pdfPenText.innerText = "قلم PDF";
        if (mouseHintTitle) mouseHintTitle.innerText = "صفحه لمسی ماوس";
        if (mouseHintDesc) mouseHintDesc.innerText = "حرکت با یک انگشت | ضربه = کلیک | دو انگشت = راست کلیک و اسکرول";
        showToast("حالت ماوس عادی فعال شد", 2000);
    }
}

// ==========================================
// ابزارهای حالت رسم (Draw Tools)
// ==========================================
function selectColor(color, btn) {
    isEraser = false;
    currentColor = color;
    document.querySelectorAll(".color-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    vibrate(15);
}

function selectEraser(btn) {
    isEraser = true;
    document.querySelectorAll(".color-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    vibrate(20);
}

function getEffectiveSize() {
    if (isEraser) {
        return Math.max(20, currentBrushSize * 3.5);
    }
    return currentBrushSize;
}

function setBrushSize(size, btn) {
    currentBrushSize = size;
    document.querySelectorAll(".size-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    vibrate(15);
}

// سوئیچ محل رسم: روی دسکتاپ یا داخل نرم‌افزارها (Acrobat/Paint)
function toggleDrawTarget() {
    vibrate(25);
    const label = document.getElementById("target-label");
    const icon = document.getElementById("target-icon");
    if (drawTarget === "desktop") {
        drawTarget = "paint";
        label.innerText = "ذخیره در PDF";
        icon.innerText = "📄";
        showToast("📄 حالت رسم در PDF فعال شد: قلم را در Acrobat انتخاب کنید و بنویسید", 3500);
    } else {
        drawTarget = "desktop";
        label.innerText = "دسکتاپ";
        icon.innerText = "🖥️";
        showToast("🖥️ حالت رسم روی لایه دسکتاپ فعال شد", 2500);
    }
    sendMsg({ type: "set_draw_target", target: drawTarget });
}

function clearScreen() {
    vibrate(40);
    const container = document.getElementById("pad-container");
    ctx.clearRect(0, 0, container.clientWidth, container.clientHeight);
    sendMsg({ type: "clear" });
}

function sendMouseAction(action, button = "left") {
    vibrate(25);
    if (action === "click") {
        sendMsg({ type: "mouse_click", button: button });
    } else if (action === "dblclick") {
        sendMsg({ type: "mouse_dblclick" });
    }
}

function toggleDrag() {
    vibrate(30);
    isDragging = !isDragging;
    const dragText = document.getElementById("drag-text");
    if (isDragging) {
        btnDrag.classList.add("dragging");
        dragText.innerText = "در حال درگ";
        sendMsg({ type: "mouse_down", button: "left" });
    } else {
        btnDrag.classList.remove("dragging");
        dragText.innerText = "درگ";
        sendMsg({ type: "mouse_up", button: "left" });
    }
}

function toggleFullScreen() {
    lockLandscape();
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().then(() => {
            lockLandscape();
        }).catch(() => {});
    } else {
        document.exitFullscreen().catch(() => {});
    }
}

// ==========================================
// مدیریت رویدادهای لمسی (Pointer Events)
// ==========================================
let lastX = 0;
let lastY = 0;

function getNormalizedCoords(e) {
    const rect = padCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const normX = Math.max(0, Math.min(1, x / rect.width));
    const normY = Math.max(0, Math.min(1, y / rect.height));
    return { x, y, normX, normY };
}

// رویداد Pointer Down
padCanvas.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    padCanvas.setPointerCapture(e.pointerId);
    isPointerDown = true;
    lockLandscape();
    const { x, y, normX, normY } = getNormalizedCoords(e);
    const effSize = getEffectiveSize();

    if (currentMode === "draw") {
        lastX = x;
        lastY = y;

        if (isEraser) {
            ctx.save();
            ctx.globalCompositeOperation = "destination-out";
            ctx.beginPath();
            ctx.arc(x, y, effSize / 2, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();

            sendMsg({
                type: "draw_down",
                x: normX,
                y: normY,
                color: "eraser",
                width: effSize,
                target: drawTarget
            });
        } else {
            ctx.save();
            ctx.globalCompositeOperation = "source-over";
            ctx.beginPath();
            ctx.arc(x, y, effSize / 2, 0, Math.PI * 2);
            ctx.fillStyle = currentColor;
            ctx.fill();
            ctx.restore();

            sendMsg({
                type: "draw_down",
                x: normX,
                y: normY,
                color: currentColor,
                width: effSize,
                target: drawTarget
            });
        }
    } else if (currentMode === "spotlight") {
        sendMsg({
            type: "spotlight_move",
            x: normX,
            y: normY
        });
        lastTouchTime = Date.now();
        touchMoved = false;
    } else {
        // حالت ماوس
        lastTouchX = e.clientX;
        lastTouchY = e.clientY;
        lastTouchTime = Date.now();
        touchMoved = false;

        // اگر قلم PDF فعال است، بلافاصله کلیک چپ نگه داشته شود
        if (isPdfPenActive) {
            sendMsg({ type: "mouse_down", button: "left" });
        }
    }
});

// رویداد Pointer Move
padCanvas.addEventListener("pointermove", (e) => {
    e.preventDefault();
    if (!isPointerDown) return;
    const effSize = getEffectiveSize();

    if (currentMode === "draw") {
        const { x, y, normX, normY } = getNormalizedCoords(e);

        ctx.save();
        if (isEraser) {
            ctx.globalCompositeOperation = "destination-out";
            ctx.beginPath();
            ctx.moveTo(lastX, lastY);
            ctx.lineTo(x, y);
            ctx.lineWidth = effSize;
            ctx.stroke();

            sendMsg({
                type: "draw_move",
                x: normX,
                y: normY,
                color: "eraser",
                width: effSize,
                target: drawTarget
            });
        } else {
            ctx.globalCompositeOperation = "source-over";
            ctx.beginPath();
            ctx.moveTo(lastX, lastY);
            ctx.lineTo(x, y);
            ctx.strokeStyle = currentColor;
            ctx.lineWidth = effSize;
            ctx.stroke();

            sendMsg({
                type: "draw_move",
                x: normX,
                y: normY,
                target: drawTarget
            });
        }
        ctx.restore();

        lastX = x;
        lastY = y;
    } else if (currentMode === "spotlight") {
        const { normX, normY } = getNormalizedCoords(e);
        touchMoved = true;
        sendMsg({
            type: "spotlight_move",
            x: normX,
            y: normY
        });
    } else {
        // حالت ماوس
        const dx = e.clientX - lastTouchX;
        const dy = e.clientY - lastTouchY;

        if (Math.abs(dx) > 1 || Math.abs(dy) > 1) {
            touchMoved = true;
            lastTouchX = e.clientX;
            lastTouchY = e.clientY;

            sendMsg({
                type: "mouse_move",
                dx: dx,
                dy: dy
            });
        }
    }
});

// رویداد Pointer Up
padCanvas.addEventListener("pointerup", (e) => {
    e.preventDefault();
    if (!isPointerDown) return;
    isPointerDown = false;

    if (currentMode === "draw") {
        sendMsg({ type: "draw_up", target: drawTarget });
    } else if (currentMode === "spotlight") {
        const pressDuration = Date.now() - lastTouchTime;
        if (!touchMoved && pressDuration < 250) {
            sendMouseAction("click", "left");
        }
    } else {
        // حالت ماوس
        if (isPdfPenActive) {
            sendMsg({ type: "mouse_up", button: "left" });
        } else {
            const pressDuration = Date.now() - lastTouchTime;
            if (!touchMoved && pressDuration < 250) {
                const now = Date.now();
                if (now - lastTapTime < 300) {
                    sendMouseAction("dblclick");
                    lastTapTime = 0;
                } else {
                    sendMouseAction("click", "left");
                    lastTapTime = now;
                }
            }
        }
    }
});

padCanvas.addEventListener("pointercancel", (e) => {
    isPointerDown = false;
    if (currentMode === "draw") {
        sendMsg({ type: "draw_up", target: drawTarget });
    } else if (currentMode === "mouse" && isPdfPenActive) {
        sendMsg({ type: "mouse_up", button: "left" });
    }
});

// ژست‌های چندانگشتی ماوس (دو انگشت برای راست‌کلیک و اسکرول)
padCanvas.addEventListener("touchstart", (e) => {
    activeTouchCount = e.touches.length;
    if (activeTouchCount === 2) {
        lastTwoFingerY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
    }
}, { passive: false });

padCanvas.addEventListener("touchmove", (e) => {
    if (currentMode === "mouse" && e.touches.length === 2) {
        e.preventDefault();
        const currentTwoFingerY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
        const dy = currentTwoFingerY - lastTwoFingerY;
        lastTwoFingerY = currentTwoFingerY;

        if (Math.abs(dy) > 2) {
            sendMsg({
                type: "mouse_scroll",
                amount: dy > 0 ? 1 : -1
            });
        }
    }
}, { passive: false });

padCanvas.addEventListener("touchend", (e) => {
    if (currentMode === "mouse" && activeTouchCount === 2 && e.touches.length === 0) {
        if (!touchMoved) {
            sendMouseAction("click", "right");
        }
    }
    activeTouchCount = e.touches.length;
}, { passive: false });

// راه‌اندازی اولیه
window.addEventListener("DOMContentLoaded", () => {
    checkOrientation();

    if (pinInput) {
        pinInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                submitPin();
            }
        });
    }

    const params = new URLSearchParams(window.location.search);
    const urlPin = params.get("pin");
    if (urlPin && /^\d{4}$/.test(urlPin)) {
        authPin = urlPin;
        sessionStorage.setItem("galam_pin", authPin);
        // پاک‌سازی PIN از نوار آدرس جهت امنیت بیشتر
        if (window.history && window.history.replaceState) {
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    } else {
        authPin = sessionStorage.getItem("galam_pin") || "";
    }

    connectWebSocket();
});
