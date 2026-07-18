"""
========================================================================
   Almatry OTP Receiver — app.py (نسخة الـ 50 ميزة)
   المطوّر: @altazyabody | 967733723953
   ------------------------------------------------------------------------
   يشغّل:  python app.py
   متطلبات:  pip install flask bcrypt telebot requests
   ------------------------------------------------------------------------
   المراحل المدمجة:
     M1: البنية + السحب التلقائي + الإحصائيات + Random Pick
     M2: الواجهة (Dark Mode, Font Size, Matrix Rain, Audio, Push)
     M3: لوحة الأدمن الكاملة (روابط، كومبوهات، مستخدمين، نسخ احتياطي)
     M4: الأمان (Rate Limit, Hashing, IP Blacklist, Ban System)
     M5: Telegram Bots + Regex + Duplicate Detection + CSV Export
     M6: API + Heatmap + Drag & Drop + Instant Search + Auto Maintenance
========================================================================
"""

import os
import re
import csv
import io
import json
import time
import sqlite3
import hashlib
import secrets
import threading
import ipaddress
from datetime import datetime, timedelta, timezone
from functools import wraps
from collections import defaultdict

from flask import (
    Flask, request, jsonify, render_template, redirect, url_for,
    session, send_file, abort, flash, Response
)
import bcrypt
import telebot
import requests

# =========================================================================
# 1) الإعدادات العامة + إدارة المفاتيح السرية
# =========================================================================
APP_SECRET = os.environ.get("APP_SECRET", "altazy_secret_change_me_in_render")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")  # غيّرها فوراً

# بوتات تيليجرام — كل بوت يراقب قناة مختلفة
TELEGRAM_BOTS = [
    {
        "token": os.environ.get("BOT1_TOKEN", "8814038881:AAGyuACUYA4YPKlJQhAyUMkpRNiV0u1gNuU"),
        "channel": os.environ.get("BOT1_CHANNEL", "@jsjsgsjsvh"),
        "platform": "telegram",
    },
    {
        "token": os.environ.get("BOT2_TOKEN", "8845420882:AAHZ-7qhCL3_ddDT3am4zWNtBRBy3mVDgws"),
        "channel": os.environ.get("BOT2_CHANNEL", "@jsjsgsjsvh"),
        "platform": "telegram",
    },
]

# إعدادات قابلة للتعديل من لوحة الأدمن (تُحفظ في DB)
DEFAULT_SETTINGS = {
    "site_name": "Almatry OTP",
    "main_color": "#00ff88",
    "secondary_color": "#00d4ff",
    "bg_color": "#0a0e1a",
    "text_color": "#e6f1ff",
    "marquee_text": "مرحباً بك في موقع المطري لاستقبال الأكواد | للدعم: 967733723953",
    "maintenance_mode": "off",
    "auto_maintenance_from": "",
    "auto_maintenance_to": "",
    "rate_limit_per_minute": 3,
    "announcement": "🔥 جديد: نظام الكومبوهات الجديد متاح الآن!",
}

# =========================================================================
# 2) قاعدة البيانات SQLite + دوال مساعدة
# =========================================================================
DB_PATH = os.path.join(os.path.dirname(__file__), "altazy.db")

def db():
    """فتح اتصال جديد بقاعدة البيانات مع إعدادات أمان."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    """إنشاء الجداول في أول تشغيل."""
    conn = db()
    c = conn.cursor()
    # جدول الإعدادات (key-value)
    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT
    )""")
    # جدول المنصات
    c.execute("""CREATE TABLE IF NOT EXISTS platforms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE, icon TEXT, color TEXT, sort_order INTEGER DEFAULT 0
    )""")
    # جدول الدول
    c.execute("""CREATE TABLE IF NOT EXISTS countries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform_id INTEGER, name TEXT, code TEXT, flag TEXT,
        FOREIGN KEY(platform_id) REFERENCES platforms(id) ON DELETE CASCADE
    )""")
    # جدول الأرقام
    c.execute("""CREATE TABLE IF NOT EXISTS numbers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER, number TEXT, status TEXT DEFAULT 'available',
        used_by_ip TEXT, used_at TIMESTAMP,
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
    )""")
    # جدول الأكواد المستلمة
    c.execute("""CREATE TABLE IF NOT EXISTS codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        number_id INTEGER, code TEXT, message TEXT, source TEXT,
        received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(number_id) REFERENCES numbers(id) ON DELETE CASCADE
    )""")
    # جدول المستخدمين (المحظورين/الزائرين)
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT, first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen TIMESTAMP, requests_count INTEGER DEFAULT 0, banned INTEGER DEFAULT 0
    )""")
    # جدول الأدمن (متعدد الصلاحيات)
    c.execute("""CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE, password_hash TEXT, role TEXT DEFAULT 'moderator',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    # جدول الروابط (إعلان/تواصل)
    c.execute("""CREATE TABLE IF NOT EXISTS links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        label TEXT, url TEXT, icon TEXT, sort_order INTEGER DEFAULT 0
    )""")
    # جدول حظر IP
    c.execute("""CREATE TABLE IF NOT EXISTS ip_blacklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT UNIQUE, reason TEXT, banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    # جدول سجل حركات الأدمن
    c.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_user TEXT, action TEXT, details TEXT, ip TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    # إدراج الإعدادات الافتراضية
    for k, v in DEFAULT_SETTINGS.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
    # إنشاء حساب الأدمن الافتراضي
    c.execute("SELECT id FROM admins WHERE username=?", (ADMIN_USER,))
    if not c.fetchone():
        ph = bcrypt.hashpw(ADMIN_PASS.encode(), bcrypt.gensalt())
        c.execute("INSERT INTO admins (username, password_hash, role) VALUES (?, ?, 'admin')",
                  (ADMIN_USER, ph))
    # منصات افتراضية
    defaults = [
        ("Telegram", "📨", "#0088cc", 1),
        ("WhatsApp", "💬", "#25d366", 2),
        ("Instagram", "📷", "#e1306c", 3),
        ("Facebook", "📘", "#1877f2", 4),
        ("Google", "🔍", "#4285f4", 5),
        ("Twitter", "🐦", "#1da1f2", 6),
    ]
    for n, i, col, so in defaults:
        c.execute("INSERT OR IGNORE INTO platforms (name, icon, color, sort_order) VALUES (?, ?, ?, ?)",
                  (n, i, col, so))
    # روابط افتراضية
    default_links = [
        ("المطور واتساب", "https://wa.me/967733723953", "📞", 1),
        ("قناة السحب", "https://t.me/jsjsgsjsvh", "📢", 2),
        ("تيليجرام المطور", "https://t.me/altazyabody", "👤", 3),
    ]
    for lbl, u, ic, so in default_links:
        c.execute("INSERT OR IGNORE INTO links (label, url, icon, sort_order) VALUES (?, ?, ?, ?)",
                  (lbl, u, ic, so))
    conn.commit()
    conn.close()

def get_settings():
    conn = db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    s = dict(DEFAULT_SETTINGS)
    s.update({r["key"]: r["value"] for r in rows})
    return s

def set_setting(key, value):
    conn = db()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def audit(admin_user, action, details=""):
    conn = db()
    conn.execute("INSERT INTO audit_logs (admin_user, action, details, ip) VALUES (?, ?, ?, ?)",
                 (admin_user, action, details, request.remote_addr if request else "-"))
    conn.commit()
    conn.close()

# =========================================================================
# 3) نظام الأمان: Rate Limiting + IP Blacklist + Ban
# =========================================================================
rate_limit_store = defaultdict(list)  # ip -> [timestamps]
blacklist_cache = set()

def load_blacklist():
    global blacklist_cache
    conn = db()
    rows = conn.execute("SELECT ip FROM ip_blacklist").fetchall()
    conn.close()
    blacklist_cache = {r["ip"] for r in rows}

def is_ip_blacklisted(ip):
    if not blacklist_cache:
        load_blacklist()
    return ip in blacklist_cache

def client_ip():
    """جلب IP الحقيقي (مع مراعاة Proxy Headers على Render)."""
    return request.headers.get("X-Forwarded-For", request.remote_addr or "0.0.0.0").split(",")[0].strip()

def security_check():
    """فحص Rate Limit + Blacklist. يرجع (allowed, message)."""
    ip = client_ip()
    if is_ip_blacklisted(ip):
        return False, "🚫 تم حظرك من الموقع."
    # فحص إذا المستخدم محظور
    conn = db()
    u = conn.execute("SELECT banned FROM users WHERE ip=?", (ip,)).fetchone()
    conn.close()
    if u and u["banned"]:
        return False, "🚫 حسابك محظور."
    # Rate Limit
    settings = get_settings()
    limit = int(settings.get("rate_limit_per_minute", 3))
    now = time.time()
    rate_limit_store[ip] = [t for t in rate_limit_store[ip] if now - t < 60]
    if len(rate_limit_store[ip]) >= limit:
        return False, f"⏳ طلبات كثيرة. حاول بعد {60 - int(now - rate_limit_store[ip][0])} ثانية."
    rate_limit_store[ip].append(now)
    return True, ""

def track_visit():
    """تتبع الزيارات (للإحصائيات)."""
    ip = client_ip()
    conn = db()
    u = conn.execute("SELECT id, requests_count FROM users WHERE ip=?", (ip,)).fetchone()
    if u:
        conn.execute("UPDATE users SET last_seen=CURRENT_TIMESTAMP, requests_count=? WHERE id=?",
                     (u["requests_count"] + 1, u["id"]))
    else:
        conn.execute("INSERT INTO users (ip, last_seen) VALUES (?, CURRENT_TIMESTAMP)", (ip,))
    conn.commit()
    conn.close()

# =========================================================================
# 4) ذكاء استخراج الأكواد (Regex) + كشف التكرار
# =========================================================================
CODE_REGEX = re.compile(r"\b(\d{4,8})\b")

def extract_codes(text):
    """استخراج جميع الأكواد المحتملة من نص، مع تجاهل المكرر."""
    if not text:
        return []
    found = set()
    # أولوية: أكود بطول 5-6 أرقام (أغلب OTP)
    for m in re.finditer(r"\b(\d{5,6})\b", text):
        found.add(m.group(1))
    for m in CODE_REGEX.finditer(text):
        found.add(m.group(1))
    return list(found)

def save_code(number_id, code, message, source):
    """حفظ كود مع كشف التكرار."""
    conn = db()
    # كشف التكرار
    existing = conn.execute("SELECT id FROM codes WHERE number_id=? AND code=?", (number_id, code)).fetchone()
    if existing:
        conn.close()
        return False
    conn.execute("INSERT INTO codes (number_id, code, message, source) VALUES (?, ?, ?, ?)",
                 (number_id, code, message, source))
    conn.close()
    return True

# =========================================================================
# 5) تيليجرام Poller — Multi-Bot + Channel Mapping
# =========================================================================
poller_threads = []
poller_running = threading.Event()

def start_poller(bot_config):
    """بدء سكريبت سحب أكواد من بوت واحد (يعمل في Thread مستقل)."""
    token = bot_config["token"]
    channel = bot_config["channel"]
    platform = bot_config["platform"]
    bot = telebot.TeleBot(token)

    @bot.message_handler(func=lambda m: True)
    def on_message(message):
        try:
            text = message.text or ""
            codes = extract_codes(text)
            for code in codes:
                conn = db()
                # محاولة ربط الكود برقم متاح في هذه المنصة
                number = conn.execute("""
                    SELECT n.id, n.number FROM numbers n
                    JOIN countries c ON n.country_id = c.id
                    JOIN platforms p ON c.platform_id = p.id
                    WHERE p.name=? AND n.status='available'
                    ORDER BY RANDOM() LIMIT 1
                """, (platform,)).fetchone()
                if number:
                    save_code(number["id"], code, text, f"{channel}:{token[:10]}")
                conn.close()
        except Exception as e:
            print(f"[Poller Error] {e}")

    def run():
        print(f"[Poller] Started for {channel} ({platform})")
        while poller_running.is_set():
            try:
                bot.infinity_polling(timeout=30, long_polling_timeout=20, non_stop=False)
            except Exception as e:
                print(f"[Poller Retry] {e} — restarting in 5s")
                time.sleep(5)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    poller_threads.append(t)

def start_all_pollers():
    """تشغيل كل البوتات."""
    poller_running.set()
    for bc in TELEGRAM_BOTS:
        start_poller(bc)

# =========================================================================
# 6) التطبيق Flask + Middlewares
# =========================================================================
app = Flask(__name__)
app.secret_key = APP_SECRET
app.permanent_session_lifetime = timedelta(days=7)

@app.before_request
def before_request():
    # تجاهل فحص للأدمن والستاتيك
    if request.path.startswith("/admin") or request.path.startswith("/static"):
        return
    settings = get_settings()
    # Maintenance Mode (يدوي)
    if settings.get("maintenance_mode") == "on":
        if request.path != "/maintenance":
            return render_template("maintenance.html", settings=settings), 503
    # Auto Maintenance (مجدول)
    auto_from = settings.get("auto_maintenance_from", "")
    auto_to = settings.get("auto_maintenance_to", "")
    if auto_from and auto_to:
        try:
            now_t = datetime.now().strftime("%H:%M")
            if auto_from <= now_t <= auto_to:
                if request.path != "/maintenance":
                    return render_template("maintenance.html", settings=settings), 503
        except:
            pass
    track_visit()

# =========================================================================
# 7) Routes العامة (الواجهة)
# =========================================================================
@app.route("/")
def index():
    settings = get_settings()
    conn = db()
    platforms = conn.execute("SELECT * FROM platforms ORDER BY sort_order").fetchall()
    countries = conn.execute("""
        SELECT c.*, p.name as platform_name, p.icon as platform_icon, p.color as platform_color
        FROM countries c JOIN platforms p ON c.platform_id = p.id
    """).fetchall()
    # إحصائيات حية
    today = datetime.now().strftime("%Y-%m-%d")
    stats = {
        "today_numbers": conn.execute(
            "SELECT COUNT(*) as c FROM numbers WHERE date(used_at)=?", (today,)).fetchone()["c"],
        "today_codes": conn.execute(
            "SELECT COUNT(*) as c FROM codes WHERE date(received_at)=?", (today,)).fetchone()["c"],
        "total_visits": conn.execute("SELECT COALESCE(SUM(requests_count),0) as c FROM users").fetchone()["c"],
        "active_users": conn.execute(
            "SELECT COUNT(*) as c FROM users WHERE last_seen > datetime('now','-1 hour')").fetchone()["c"],
    }
    # آخر 5 أكواد (للشريط الجانبي المتحرك)
    recent_codes = conn.execute("""
        SELECT c.code, n.number, p.name as platform, c.received_at
        FROM codes c
        JOIN numbers n ON c.number_id = n.id
        JOIN countries co ON n.country_id = co.id
        JOIN platforms p ON co.platform_id = p.id
        ORDER BY c.received_at DESC LIMIT 5
    """).fetchall()
    # Heatmap: أكثر المنصات استخداماً
    heatmap = conn.execute("""
        SELECT p.name, p.color, COUNT(c.id) as uses
        FROM platforms p
        LEFT JOIN countries co ON co.platform_id = p.id
        LEFT JOIN numbers n ON n.country_id = co.id
        LEFT JOIN codes c ON c.number_id = n.id
        GROUP BY p.id ORDER BY uses DESC
    """).fetchall()
    # Audience Analytics: الدول الأكثر استخداماً
    audience = conn.execute("""
        SELECT co.name as country, COUNT(c.id) as uses
        FROM countries co
        LEFT JOIN numbers n ON n.country_id = co.id
        LEFT JOIN codes c ON c.number_id = n.id
        GROUP BY co.id ORDER BY uses DESC LIMIT 10
    """).fetchall()
    conn.close()
    return render_template("index.html",
                           settings=settings, platforms=platforms, countries=countries,
                           stats=stats, recent_codes=recent_codes, heatmap=heatmap,
                           audience=audience)

@app.route("/maintenance")
def maintenance():
    settings = get_settings()
    return render_template("maintenance.html", settings=settings), 503

@app.route("/api/get_number", methods=["POST"])
def api_get_number():
    """جلب رقم عشوائي لدولة معيّنة."""
    allowed, msg = security_check()
    if not allowed:
        return jsonify({"ok": False, "error": msg}), 429
    data = request.get_json() or {}
    country_id = data.get("country_id")
    if not country_id:
        return jsonify({"ok": False, "error": "country_id مطلوب"}), 400
    conn = db()
    # Random Pick
    num = conn.execute("""
        SELECT * FROM numbers WHERE country_id=? AND status='available' ORDER BY RANDOM() LIMIT 1
    """, (country_id,)).fetchone()
    if not num:
        conn.close()
        return jsonify({"ok": False, "error": "لا توجد أرقام متاحة لهذه الدولة"}), 404
    # تحديث الحالة
    conn.execute("UPDATE numbers SET status='in_use', used_by_ip=?, used_at=CURRENT_TIMESTAMP WHERE id=?",
                 (client_ip(), num["id"]))
    conn.commit()
    # جلب أي كود سابق لهذا الرقم
    code = conn.execute("SELECT code FROM codes WHERE number_id=? ORDER BY received_at DESC LIMIT 1",
                        (num["id"],)).fetchone()
    conn.close()
    return jsonify({
        "ok": True,
        "number": num["number"],
        "number_id": num["id"],
        "code": code["code"] if code else None,
        "expires_in": 120  # مؤقت 2 دقيقة
    })

@app.route("/api/next_number", methods=["POST"])
def api_next_number():
    """جلب رقم آخر في نفس الدولة (تبديل بدون إعادة اختيار)."""
    allowed, msg = security_check()
    if not allowed:
        return jsonify({"ok": False, "error": msg}), 429
    data = request.get_json() or {}
    country_id = data.get("country_id")
    current_number_id = data.get("current_number_id")
    conn = db()
    if current_number_id:
        # تحرير الرقم الحالي
        conn.execute("UPDATE numbers SET status='used' WHERE id=?", (current_number_id,))
    num = conn.execute("""
        SELECT * FROM numbers WHERE country_id=? AND status='available'
        ORDER BY RANDOM() LIMIT 1
    """, (country_id,)).fetchone()
    if not num:
        conn.close()
        return jsonify({"ok": False, "error": "لا توجد أرقام أخرى"}), 404
    conn.execute("UPDATE numbers SET status='in_use', used_by_ip=?, used_at=CURRENT_TIMESTAMP WHERE id=?",
                 (client_ip(), num["id"]))
    conn.commit()
    code = conn.execute("SELECT code FROM codes WHERE number_id=? ORDER BY received_at DESC LIMIT 1",
                        (num["id"],)).fetchone()
    conn.close()
    return jsonify({"ok": True, "number": num["number"], "number_id": num["id"],
                    "code": code["code"] if code else None, "expires_in": 120})

@app.route("/api/check_code/<int:number_id>")
def api_check_code(number_id):
    """استعلام عن آخر كود وصل لرقم معيّن (Polling من الفرونت)."""
    conn = db()
    code = conn.execute("SELECT code, received_at FROM codes WHERE number_id=? ORDER BY received_at DESC LIMIT 1",
                        (number_id,)).fetchone()
    conn.close()
    if code:
        return jsonify({"ok": True, "code": code["code"], "received_at": code["received_at"]})
    return jsonify({"ok": True, "code": None})

@app.route("/api/search")
def api_search():
    """بحث فوري في الأرقام المتاحة (Instant Search)."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"ok": True, "results": []})
    conn = db()
    rows = conn.execute("""
        SELECT n.number, co.name as country, p.name as platform, p.icon
        FROM numbers n
        JOIN countries co ON n.country_id = co.id
        JOIN platforms p ON co.platform_id = p.id
        WHERE n.status='available' AND (n.number LIKE ? OR co.name LIKE ? OR p.name LIKE ?)
        LIMIT 20
    """, (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
    conn.close()
    return jsonify({"ok": True, "results": [dict(r) for r in rows]})

# =========================================================================
# 8) API عام للمطورين (Feature 45) — يحتاج API Key
# =========================================================================
API_KEYS = {"demo_key_change_me": "demo"}

def require_api_key(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if key not in API_KEYS:
            return jsonify({"ok": False, "error": "Invalid API key"}), 401
        return f(*args, **kwargs)
    return wrapper

@app.route("/v1/platforms")
@require_api_key
def api_v1_platforms():
    conn = db()
    rows = conn.execute("SELECT id, name, icon, color FROM platforms ORDER BY sort_order").fetchall()
    conn.close()
    return jsonify({"ok": True, "platforms": [dict(r) for r in rows]})

@app.route("/v1/numbers")
@require_api_key
def api_v1_numbers():
    platform = request.args.get("platform")
    conn = db()
    if platform:
        rows = conn.execute("""
            SELECT n.number, co.name as country FROM numbers n
            JOIN countries co ON n.country_id = co.id
            JOIN platforms p ON co.platform_id = p.id
            WHERE p.name=? AND n.status='available' LIMIT 50
        """, (platform,)).fetchall()
    else:
        rows = conn.execute("SELECT n.number, co.name as country FROM numbers n "
                            "JOIN countries co ON n.country_id = co.id "
                            "WHERE n.status='available' LIMIT 50").fetchall()
    conn.close()
    return jsonify({"ok": True, "numbers": [dict(r) for r in rows]})

# =========================================================================
# 9) نظام تسجيل الدخول للأدمن
# =========================================================================
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "").strip()
        conn = db()
        row = conn.execute("SELECT * FROM admins WHERE username=?", (u,)).fetchone()
        conn.close()
        if row and bcrypt.checkpw(p.encode(), row["password_hash"]):
            session.permanent = True
            session["admin_id"] = row["id"]
            session["admin_user"] = row["username"]
            session["admin_role"] = row["role"]
            audit(row["username"], "login", "دخول للوحة التحكم")
            return redirect(url_for("admin_dashboard"))
        flash("بيانات خاطئة", "error")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    audit(session.get("admin_user", "?"), "logout")
    session.clear()
    return redirect(url_for("admin_login"))

# =========================================================================
# 10) لوحة الأدمن الكاملة
# =========================================================================
@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = db()
    stats = {
        "total_numbers": conn.execute("SELECT COUNT(*) as c FROM numbers").fetchone()["c"],
        "available": conn.execute("SELECT COUNT(*) as c FROM numbers WHERE status='available'").fetchone()["c"],
        "total_codes": conn.execute("SELECT COUNT(*) as c FROM codes").fetchone()["c"],
        "total_users": conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"],
        "banned_users": conn.execute("SELECT COUNT(*) as c FROM users WHERE banned=1").fetchone()["c"],
        "platforms": conn.execute("SELECT COUNT(*) as c FROM platforms").fetchone()["c"],
        "countries": conn.execute("SELECT COUNT(*) as c FROM countries").fetchone()["c"],
    }
    recent_audits = conn.execute("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 10").fetchall()
    conn.close()
    return render_template("admin_dashboard.html", stats=stats, audits=recent_audits,
                           admin_user=session.get("admin_user"), role=session.get("admin_role"))

@app.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def admin_settings():
    if request.method == "POST":
        for key in DEFAULT_SETTINGS.keys():
            v = request.form.get(key, "")
            set_setting(key, v)
        audit(session["admin_user"], "settings_update", "تحديث الإعدادات")
        flash("تم الحفظ ✅", "success")
        return redirect(url_for("admin_settings"))
    return render_template("admin_settings.html", settings=get_settings())

@app.route("/admin/platforms", methods=["GET", "POST"])
@admin_required
def admin_platforms():
    conn = db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            conn.execute("INSERT INTO platforms (name, icon, color, sort_order) VALUES (?, ?, ?, ?)",
                         (request.form["name"], request.form["icon"], request.form["color"],
                          int(request.form.get("sort_order", 0))))
            audit(session["admin_user"], "platform_add", request.form["name"])
        elif action == "delete":
            pid = request.form["id"]
            conn.execute("DELETE FROM platforms WHERE id=?", (pid,))
            audit(session["admin_user"], "platform_delete", pid)
        elif action == "reorder":
            # Drag & Drop حفظ
            order = json.loads(request.form["order"])
            for idx, pid in enumerate(order):
                conn.execute("UPDATE platforms SET sort_order=? WHERE id=?", (idx, pid))
            audit(session["admin_user"], "platform_reorder", str(len(order)) + " منصات")
        conn.commit()
        conn.close()
        return redirect(url_for("admin_platforms"))
    platforms = conn.execute("SELECT * FROM platforms ORDER BY sort_order").fetchall()
    conn.close()
    return render_template("admin_platforms.html", platforms=platforms)

@app.route("/admin/combos", methods=["GET", "POST"])
@admin_required
def admin_combos():
    """رفع ملفات TXT — كل سطر: رقم أو platform|country|number"""
    conn = db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add_country":
            conn.execute("INSERT INTO countries (platform_id, name, code, flag) VALUES (?, ?, ?, ?)",
                         (request.form["platform_id"], request.form["name"],
                          request.form["code"], request.form.get("flag", "🌍")))
            audit(session["admin_user"], "country_add", request.form["name"])
        elif action == "delete_country":
            cid = request.form["id"]
            conn.execute("DELETE FROM countries WHERE id=?", (cid,))
            audit(session["admin_user"], "country_delete", cid)
        elif action == "upload_combo":
            # رفع ملف: platform_name|country_name|number per line
            f = request.files.get("file")
            if f:
                content = f.read().decode("utf-8", errors="ignore")
                count = 0
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("|")
                    if len(parts) >= 3:
                        p_name, c_name, number = parts[0].strip(), parts[1].strip(), parts[2].strip()
                        p = conn.execute("SELECT id FROM platforms WHERE name=?", (p_name,)).fetchone()
                        if not p:
                            c = conn.execute("INSERT INTO platforms (name) VALUES (?)", (p_name,))
                            p_id = c.lastrowid
                        else:
                            p_id = p["id"]
                        c = conn.execute("SELECT id FROM countries WHERE platform_id=? AND name=?",
                                         (p_id, c_name)).fetchone()
                        if not c:
                            cr = conn.execute("INSERT INTO countries (platform_id, name, code) VALUES (?, ?, ?)",
                                              (p_id, c_name, c_name[:2].upper()))
                            c_id = cr.lastrowid
                        else:
                            c_id = c["id"]
                        conn.execute("INSERT INTO numbers (country_id, number) VALUES (?, ?)", (c_id, number))
                        count += 1
                audit(session["admin_user"], "combo_upload", f"{count} رقم")
                flash(f"✅ تم رفع {count} رقم", "success")
        conn.commit()
        conn.close()
        return redirect(url_for("admin_combos"))
    countries = conn.execute("""
        SELECT c.*, p.name as platform_name FROM countries c
        JOIN platforms p ON c.platform_id = p.id ORDER BY p.name, c.name
    """).fetchall()
    platforms = conn.execute("SELECT * FROM platforms ORDER BY name").fetchall()
    conn.close()
    return render_template("admin_combos.html", countries=countries, platforms=platforms)

@app.route("/admin/users", methods=["GET", "POST"])
@admin_required
def admin_users():
    conn = db()
    if request.method == "POST":
        action = request.form.get("action")
        uid = request.form.get("id")
        ip = request.form.get("ip")
        if action == "ban":
            conn.execute("UPDATE users SET banned=1 WHERE id=?", (uid,))
            audit(session["admin_user"], "user_ban", f"user_id={uid}")
        elif action == "unban":
            conn.execute("UPDATE users SET banned=0 WHERE id=?", (uid,))
            audit(session["admin_user"], "user_unban", f"user_id={uid}")
        elif action == "blacklist_ip":
            reason = request.form.get("reason", "حظر من الأدمن")
            try:
                conn.execute("INSERT OR IGNORE INTO ip_blacklist (ip, reason) VALUES (?, ?)", (ip, reason))
                load_blacklist()
                audit(session["admin_user"], "ip_blacklist", f"{ip} - {reason}")
            except Exception as e:
                flash(f"خطأ: {e}", "error")
        elif action == "unblacklist_ip":
            conn.execute("DELETE FROM ip_blacklist WHERE ip=?", (ip,))
            load_blacklist()
            audit(session["admin_user"], "ip_unblacklist", ip)
        conn.commit()
    users = conn.execute("SELECT * FROM users ORDER BY last_seen DESC LIMIT 100").fetchall()
    blacklisted = conn.execute("SELECT * FROM ip_blacklist ORDER BY banned_at DESC").fetchall()
    conn.close()
    return render_template("admin_users.html", users=users, blacklisted=blacklisted)

@app.route("/admin/links", methods=["GET", "POST"])
@admin_required
def admin_links():
    conn = db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            conn.execute("INSERT INTO links (label, url, icon, sort_order) VALUES (?, ?, ?, ?)",
                         (request.form["label"], request.form["url"], request.form.get("icon", "🔗"),
                          int(request.form.get("sort_order", 0))))
        elif action == "delete":
            conn.execute("DELETE FROM links WHERE id=?", (request.form["id"],))
        audit(session["admin_user"], "links_modify", action)
        conn.commit()
        conn.close()
        return redirect(url_for("admin_links"))
    links = conn.execute("SELECT * FROM links ORDER BY sort_order").fetchall()
    conn.close()
    return render_template("admin_links.html", links=links)

@app.route("/admin/codes", methods=["GET", "POST"])
@admin_required
def admin_codes():
    conn = db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "delete_all":
            conn.execute("DELETE FROM codes")
            audit(session["admin_user"], "codes_delete_all", "")
        elif action == "delete_filter":
            days = int(request.form.get("days", 7))
            conn.execute("DELETE FROM codes WHERE received_at < datetime('now', ?)",
                         (f"-{days} days",))
            audit(session["admin_user"], "codes_delete_filter", f"{days} يوم")
        elif action == "delete_id":
            conn.execute("DELETE FROM codes WHERE id=?", (request.form["id"],))
        conn.commit()
    codes = conn.execute("""
        SELECT c.*, n.number, co.name as country, p.name as platform
        FROM codes c
        JOIN numbers n ON c.number_id = n.id
        JOIN countries co ON n.country_id = co.id
        JOIN platforms p ON co.platform_id = p.id
        ORDER BY c.received_at DESC LIMIT 200
    """).fetchall()
    conn.close()
    return render_template("admin_codes.html", codes=codes)

@app.route("/admin/backup")
@admin_required
def admin_backup():
    """تحميل نسخة احتياطية من قاعدة البيانات."""
    audit(session["admin_user"], "backup_download", "")
    return send_file(DB_PATH, as_attachment=True, download_name=f"altazy_backup_{int(time.time())}.db")

@app.route("/admin/restore", methods=["POST"])
@admin_required
def admin_restore():
    f = request.files.get("file")
    if f:
        f.save(DB_PATH)
        audit(session["admin_user"], "backup_restore", "")
        flash("✅ تمت الاستعادة", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/export_csv")
@admin_required
def export_csv():
    """تصدير الأكواد إلى CSV (Feature 40)."""
    conn = db()
    rows = conn.execute("""
        SELECT c.code, n.number, co.name as country, p.name as platform, c.source, c.received_at
        FROM codes c
        JOIN numbers n ON c.number_id = n.id
        JOIN countries co ON n.country_id = co.id
        JOIN platforms p ON co.platform_id = p.id
        ORDER BY c.received_at DESC
    """).fetchall()
    conn.close()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(["Code", "Number", "Country", "Platform", "Source", "Received At"])
    for r in rows:
        cw.writerow([r["code"], r["number"], r["country"], r["platform"], r["source"], r["received_at"]])
    output = si.getvalue()
    audit(session["admin_user"], "export_csv", f"{len(rows)} أكواد")
    return Response(output, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=codes.csv"})

@app.route("/admin/audits")
@admin_required
def admin_audits():
    conn = db()
    rows = conn.execute("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 200").fetchall()
    conn.close()
    return render_template("admin_audits.html", audits=rows)

# =========================================================================
# 11) API مساعدة للفرونت (يدعمها الـ JS)
# =========================================================================
@app.route("/api/links")
def api_links():
    conn = db()
    rows = conn.execute("SELECT * FROM links ORDER BY sort_order").fetchall()
    conn.close()
    return jsonify({"ok": True, "links": [dict(r) for r in rows]})

@app.route("/api/countries/<int:platform_id>")
def api_countries(platform_id):
    conn = db()
    rows = conn.execute("""
        SELECT c.id, c.name, c.code, c.flag,
               (SELECT COUNT(*) FROM numbers WHERE country_id=c.id AND status='available') as available
        FROM countries c WHERE c.platform_id=?
    """, (platform_id,)).fetchall()
    conn.close()
    return jsonify({"ok": True, "countries": [dict(r) for r in rows]})

@app.route("/api/help", methods=["POST"])
def api_help():
    """إرسال طلب مساعدة للأدمن (Feature 19)."""
    data = request.get_json() or {}
    msg = data.get("message", "").strip()
    if not msg:
        return jsonify({"ok": False, "error": "رسالة فارغة"}), 400
    # حفظ في audit كطلب مساعدة
    audit("GUEST", "help_request", f"{client_ip()} - {msg[:200]}")
    return jsonify({"ok": True, "message": "✅ تم الإرسال"})

# =========================================================================
# 12) التشغيل — نقطة البداية
# =========================================================================
if __name__ == "__main__":
    init_db()
    load_blacklist()
    # تشغيل البوتات في الخلفية
    try:
        start_all_pollers()
    except Exception as e:
        print(f"[Warning] Pollers failed: {e}")
    port = int(os.environ.get("PORT", 5000))
    print(f"""
========================================================================
   🚀 Almatry OTP Running on http://localhost:{port}
   👤 Admin Panel: http://localhost:{port}/admin/login
   🔑 Default: {ADMIN_USER} / {ADMIN_PASS}
   📞 Developer: 967733723953
========================================================================
    """)
    app.run(host="0.0.0.0", port=port, debug=False)
