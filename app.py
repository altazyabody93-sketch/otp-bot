"""
========================================================================
   🔐 المطري OTP — ملف واحد متكامل
   المطور: @altazyabody | 📞 967733723953
   
   ▶️ التشغيل: python app.py
   📦 المتطلبات: pip install flask bcrypt pyTelegramBotAPI requests gunicorn
========================================================================
"""
import os, re, json, time, sqlite3, hashlib, secrets, threading, csv, io
from datetime import datetime, timedelta, timezone
from functools import wraps
from collections import defaultdict

from flask import (Flask, request, jsonify, render_template_string, redirect,
                   url_for, session, send_file, abort, flash, Response)
import bcrypt
import telebot
import requests

# =========================================================================
# 1) الإعدادات العامة
# =========================================================================
APP_SECRET = os.environ.get("APP_SECRET", "almatry_secret_" + secrets.token_hex(8))
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")

# رابط واتساب المطور
OWNER_WHATSAPP = "https://wa.me/967733723953"

# Telegram Bots
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

# =========================================================================
# 2) قاعدة البيانات
# =========================================================================
DB_PATH = "almatry.db"

def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # جدول الإعدادات
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT
    )''')
    
    # الإعدادات الافتراضية
    default_settings = {
        "site_name": "🚀 المطري OTP",
        "main_color": "#00ffc8",
        "secondary_color": "#8b5cf6",
        "bg_color": "#0a0e1a",
        "text_color": "#ffffff",
        "marquee_text": "🚀 المطري OTP - أسرع موقع للحصول على الأكواد | للدعم: 967733723953",
        "announcement": "🔥 نظام الكومبوهات الجديد متاح الآن!",
        "maintenance_mode": "off",
        "auto_maintenance_from": "",
        "auto_maintenance_to": "",
        "rate_limit_per_minute": "10",
        "smart_btn_text": "⚡ استلام ذكي فوري",
        "smart_btn_subtext": "يختار لك أفضل رقم متاح مع كوده تلقائياً",
        "choose_platform": "اختر المنصة",
        "choose_country": "اختر الدولة",
        "your_number": "رقمك",
        "your_code": "الكود",
        "waiting_code": "في انتظار الكود...",
        "copy_number": "نسخ الرقم",
        "copy_code": "نسخ الكود",
        "next_number": "الرقم التالي",
        "help": "مساعدة",
        "live_codes": "⚡ آخر الأكواد من القنوات (لايف)",
        "search_placeholder": "🔍 بحث فوري في الأرقام والدول والمنصات...",
        "digit_rain_enabled": "1",
        "matrix_rain_enabled": "1",
        "sound_enabled": "1",
        "push_enabled": "1",
        "footer_text": "💎 صُنع بحب ⚡ بواسطة المطري",
    }
    for k, v in default_settings.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
    
    # جداول الأدمن
    c.execute('''CREATE TABLE IF NOT EXISTS platforms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE, icon TEXT, color TEXT, sort_order INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS countries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform_id INTEGER, name TEXT, code TEXT, flag TEXT,
        FOREIGN KEY(platform_id) REFERENCES platforms(id) ON DELETE CASCADE
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS numbers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER, number TEXT, status TEXT DEFAULT 'available',
        used_by_ip TEXT, used_at TIMESTAMP,
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        number_id INTEGER, code TEXT, message TEXT, source TEXT,
        received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(number_id) REFERENCES numbers(id) ON DELETE CASCADE
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT, first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen TIMESTAMP, requests_count INTEGER DEFAULT 0, banned INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE, password_hash TEXT, role TEXT DEFAULT 'moderator',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        label TEXT, url TEXT, icon TEXT, sort_order INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS ip_blacklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT UNIQUE, reason TEXT, banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_user TEXT, action TEXT, details TEXT, ip TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS code_pulls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        number_id INTEGER, ip TEXT,
        pulled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(number_id) REFERENCES numbers(id) ON DELETE CASCADE
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS combos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT, country_name TEXT, country_code TEXT,
        country_flag TEXT, numbers TEXT,
        UNIQUE(platform, country_code)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT, content TEXT, media_url TEXT, button_text TEXT,
        button_url TEXT, source_msg_id INTEGER, created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS help_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT, message TEXT, source TEXT,
        status TEXT DEFAULT 'pending', created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS site_texts (
        key TEXT PRIMARY KEY, value TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS site_links (
        key TEXT PRIMARY KEY, value TEXT, icon TEXT
    )''')
    
    # إدراج الأدمن الافتراضي
    c.execute("SELECT id FROM admins WHERE username=?", (ADMIN_USER,))
    if not c.fetchone():
        ph = bcrypt.hashpw(ADMIN_PASS.encode(), bcrypt.gensalt())
        c.execute("INSERT INTO admins (username, password_hash, role) VALUES (?, ?, 'admin')",
                  (ADMIN_USER, ph))
    
    # المنصات الافتراضية
    defaults = [
        ("Telegram", "📨", "#0088cc", 1),
        ("WhatsApp", "💬", "#25d366", 2),
        ("Instagram", "📷", "#e1306c", 3),
        ("Facebook", "📘", "#1877f2", 4),
        ("Google", "🔍", "#4285f4", 5),
        ("Twitter", "🐦", "#1da1f2", 6),
        ("TikTok", "🎵", "#000000", 7),
        ("Snapchat", "👻", "#FFFC00", 8),
    ]
    for n, i, col, so in defaults:
        c.execute("INSERT OR IGNORE INTO platforms (name, icon, color, sort_order) VALUES (?, ?, ?, ?)",
                  (n, i, col, so))
    
    # الروابط الافتراضية
    default_links = [
        ("المطور واتساب", OWNER_WHATSAPP, "📞", 1),
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
    return {r['key']: r['value'] for r in rows}

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
# 3) الدول
# =========================================================================
COUNTRY_DATA = {
    "966": {"n": "السعودية", "f": "🇸🇦"},
    "971": {"n": "الإمارات", "f": "🇦🇪"},
    "20": {"n": "مصر", "f": "🇪🇬"},
    "1": {"n": "أمريكا", "f": "🇺🇸"},
    "44": {"n": "بريطانيا", "f": "🇬🇧"},
    "90": {"n": "تركيا", "f": "🇹🇷"},
    "91": {"n": "الهند", "f": "🇮🇳"},
    "49": {"n": "ألمانيا", "f": "🇩🇪"},
    "7": {"n": "روسيا", "f": "🇷🇺"},
    "33": {"n": "فرنسا", "f": "🇫🇷"},
    "34": {"n": "إسبانيا", "f": "🇪🇸"},
    "39": {"n": "إيطاليا", "f": "🇮🇹"},
    "212": {"n": "المغرب", "f": "🇲🇦"},
    "213": {"n": "الجزائر", "f": "🇩🇿"},
    "216": {"n": "تونس", "f": "🇹🇳"},
    "218": {"n": "ليبيا", "f": "🇱🇾"},
    "92": {"n": "باكستان", "f": "🇵🇰"},
    "967": {"n": "اليمن", "f": "🇾🇪"},
    "962": {"n": "الأردن", "f": "🇯🇴"},
    "963": {"n": "سوريا", "f": "🇸🇾"},
    "964": {"n": "العراق", "f": "🇮🇶"},
    "965": {"n": "الكويت", "f": "🇰🇼"},
    "968": {"n": "عمان", "f": "🇴🇲"},
    "973": {"n": "البحرين", "f": "🇧🇭"},
    "974": {"n": "قطر", "f": "🇶🇦"},
    "970": {"n": "فلسطين", "f": "🇵🇸"},
    "81": {"n": "اليابان", "f": "🇯🇵"},
    "82": {"n": "كوريا", "f": "🇰🇷"},
    "86": {"n": "الصين", "f": "🇨🇳"},
    "60": {"n": "ماليزيا", "f": "🇲🇾"},
    "65": {"n": "سنغافورة", "f": "🇸🇬"},
    "66": {"n": "تايلاند", "f": "🇹🇭"},
    "84": {"n": "فيتنام", "f": "🇻🇳"},
    "62": {"n": "إندونيسيا", "f": "🇮🇩"},
    "63": {"n": "الفلبين", "f": "🇵🇭"},
    "52": {"n": "المكسيك", "f": "🇲🇽"},
    "55": {"n": "البرازيل", "f": "🇧🇷"},
    "54": {"n": "الأرجنتين", "f": "🇦🇷"},
    "56": {"n": "تشيلي", "f": "🇨🇱"},
    "57": {"n": "كولومبيا", "f": "🇨🇴"},
    "51": {"n": "بيرو", "f": "🇵🇪"},
    "58": {"n": "فنزويلا", "f": "🇻🇪"},
    "31": {"n": "هولندا", "f": "🇳🇱"},
    "32": {"n": "بلجيكا", "f": "🇧🇪"},
    "41": {"n": "سويسرا", "f": "🇨🇭"},
    "43": {"n": "النمسا", "f": "🇦🇹"},
    "45": {"n": "الدنمارك", "f": "🇩🇰"},
    "46": {"n": "السويد", "f": "🇸🇪"},
    "47": {"n": "النرويج", "f": "🇳🇴"},
    "48": {"n": "بولندا", "f": "🇵🇱"},
    "30": {"n": "اليونان", "f": "🇬🇷"},
    "351": {"n": "البرتغال", "f": "🇵🇹"},
    "353": {"n": "أيرلندا", "f": "🇮🇪"},
    "61": {"n": "أستراليا", "f": "🇦🇺"},
    "64": {"n": "نيوزيلندا", "f": "🇳🇿"},
    "27": {"n": "جنوب أفريقيا", "f": "🇿🇦"},
    "972": {"n": "إسرائيل", "f": "🇮🇱"},
    "94": {"n": "سريلانكا", "f": "🇱🇰"},
    "880": {"n": "بنغلاديش", "f": "🇧🇩"},
    "234": {"n": "نيجيريا", "f": "🇳🇬"},
    "254": {"n": "كينيا", "f": "🇰🇪"},
    "255": {"n": "تنزانيا", "f": "🇹🇿"},
    "20": {"n": "مصر", "f": "🇪🇬"},
    "993": {"n": "تركمانستان", "f": "🇹🇲"},
    "992": {"n": "طاجيكستان", "f": "🇹🇯"},
    "996": {"n": "قرغيزستان", "f": "🇰🇬"},
    "998": {"n": "أوزبكستان", "f": "🇺🇿"},
    "375": {"n": "بيلاروس", "f": "🇧🇾"},
    "380": {"n": "أوكرانيا", "f": "🇺🇦"},
    "7": {"n": "كازاخستان", "f": "🇰🇿"},
    "995": {"n": "جورجيا", "f": "🇬🇪"},
    "994": {"n": "أذربيجان", "f": "🇦🇿"},
    "373": {"n": "مولدوفا", "f": "🇲🇩"},
    "374": {"n": "أرمينيا", "f": "🇦🇲"},
    "961": {"n": "لبنان", "f": "🇱🇧"},
}

def get_country_info(code):
    info = COUNTRY_DATA.get(code)
    return (info["n"], info["f"]) if info else ("أخرى", "🌍")

# =========================================================================
# 4) الأمان
# =========================================================================
rate_limit_store = defaultdict(list)
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
    return request.headers.get("X-Forwarded-For", request.remote_addr or "0.0.0.0").split(",")[0].strip()

def security_check():
    ip = client_ip()
    if is_ip_blacklisted(ip):
        return False, "🚫 تم حظرك من الموقع."
    conn = db()
    u = conn.execute("SELECT banned FROM users WHERE ip=?", (ip,)).fetchone()
    conn.close()
    if u and u["banned"]:
        return False, "🚫 حسابك محظور."
    settings = get_settings()
    limit = int(settings.get("rate_limit_per_minute", 10))
    now = time.time()
    rate_limit_store[ip] = [t for t in rate_limit_store[ip] if now - t < 60]
    if len(rate_limit_store[ip]) >= limit:
        return False, f"⏳ طلبات كثيرة. حاول بعد {60 - int(now - rate_limit_store[ip][0])} ثانية."
    rate_limit_store[ip].append(now)
    return True, ""

def track_visit():
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
# 5) AI Engine لاستقبال الأكواد
# =========================================================================
CODE_REGEX = re.compile(r"\b(\d{4,8})\b")
PHONE_REGEX = re.compile(r"(\+?\d[\d\s\-\(\)]{6,18}\d)")

PLATFORM_KEYWORDS = {
    "telegram": ["telegram", "تيليجرام", "تلجرام", "تلي", "tg"],
    "whatsapp": ["whatsapp", "واتس", "واتساب", "whats", "wa"],
    "instagram": ["instagram", "انستقرام", "انستا", "ig", "insta"],
    "facebook": ["facebook", "فيسبوك", "فيس", "fb"],
    "google": ["google", "جوجل", "gmail"],
    "twitter": ["twitter", "تويتر"],
    "tiktok": ["tiktok", "تيك توك"],
    "snapchat": ["snapchat", "سناب", "سناب شات"],
}

def detect_platform(text):
    if not text: return None
    t = text.lower()
    for platform, keywords in PLATFORM_KEYWORDS.items():
        for kw in keywords:
            if kw in t:
                return platform
    return None

def extract_phone(text):
    if not text: return [], None
    found = []
    for m in PHONE_REGEX.finditer(text):
        num = re.sub(r"[\s\-\(\)]", "", m.group(1))
        digits = re.sub(r"[^\d]", "", num)
        if 7 <= len(digits) <= 15:
            found.append(digits)
    last4 = re.findall(r"(?:x{2,}|X{2,}|\*{2,}|…{2,})(\d{3,4})", text)
    return found, last4[0] if last4 else None

def extract_codes(text):
    if not text: return []
    found = []
    specific = re.findall(
        r"(?:code|kode|otp|كود|رمز|كود\s*التأكيد|verification|pin)\s*[:\-\s]*(\d{4,8})",
        text, re.IGNORECASE
    )
    found.extend(specific)
    found.extend(re.findall(r"\b(\d{5,6})\b", text))
    seen = set()
    unique = []
    for c in found:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique

def find_best_number_match(phone_digits, platform=None, last4=None):
    conn = db()
    candidates = []
    
    if phone_digits:
        candidates.extend(conn.execute("""
            SELECT n.id, n.number, p.name as platform, c.name as country, c.flag
            FROM numbers n
            JOIN countries c ON n.country_id = c.id
            JOIN platforms p ON c.platform_id = p.id
            WHERE REPLACE(REPLACE(REPLACE(REPLACE(n.number, '+', ''), ' ', ''), '-', ''), '()', '') = ?
              AND n.status = 'available'
            ORDER BY n.used_at ASC NULLS FIRST LIMIT 5
        """, (phone_digits,)).fetchall())

    if not candidates and last4:
        candidates.extend(conn.execute("""
            SELECT n.id, n.number, p.name as platform, c.name as country, c.flag
            FROM numbers n
            JOIN countries c ON n.country_id = c.id
            JOIN platforms p ON c.platform_id = p.id
            WHERE REPLACE(REPLACE(REPLACE(REPLACE(n.number, '+', ''), ' ', ''), '-', ''), '()', '')
                  LIKE ? AND n.status = 'available'
            ORDER BY n.used_at ASC NULLS FIRST LIMIT 5
        """, (f"%{last4}",)).fetchall())

    if not candidates:
        candidates.extend(conn.execute("""
            SELECT n.id, n.number, p.name as platform, c.name as country, c.flag
            FROM numbers n
            JOIN countries c ON n.country_id = c.id
            JOIN platforms p ON c.platform_id = p.id
            ORDER BY n.status = 'available' DESC, RANDOM() LIMIT 5
        """).fetchall())

    conn.close()
    return [dict(c) for c in candidates]

def save_code(number_id, code, message, source, auto_assign=True):
    conn = db()
    existing = conn.execute("SELECT id FROM codes WHERE number_id=? AND code=?", (number_id, code)).fetchone()
    if existing:
        conn.close()
        return False, "duplicate"
    conn.execute("INSERT INTO codes (number_id, code, message, source) VALUES (?, ?, ?, ?)",
                 (number_id, code, message, source))
    if auto_assign:
        conn.execute(
            "UPDATE numbers SET status='assigned', used_at=CURRENT_TIMESTAMP WHERE id=? AND status='available'",
            (number_id,)
        )
    conn.commit()
    conn.close()
    return True, "saved"

def process_smart_message(text, source_label):
    if not text: return None
    platform = detect_platform(text)
    phones, last4 = extract_phone(text)
    codes = extract_codes(text)
    if not codes:
        return {"status": "no_code", "text": text[:100]}
    results = []
    for code in codes:
        phone_to_match = phones[0] if phones else None
        candidates = find_best_number_match(phone_to_match, platform, last4)
        if candidates:
            best = candidates[0]
            ok, status = save_code(best["id"], code, text, source_label, auto_assign=True)
            results.append({
                "code": code, "matched_number": best["number"],
                "country": best["country"], "platform": best["platform"],
                "status": status
            })
            if ok: break
        else:
            results.append({"code": code, "matched": None, "status": "no_match"})
    return {
        "status": "ok", "platform_detected": platform,
        "phones_found": phones, "last4_found": last4,
        "codes_found": codes, "results": results
    }

# =========================================================================
# 6) Telegram Pollers
# =========================================================================
poller_threads = []
poller_running = threading.Event()

def start_poller(bot_config):
    token = bot_config["token"]
    channel = bot_config["channel"]
    bot = telebot.TeleBot(token)
    source_label = f"{channel}:{token[:10]}"

    @bot.message_handler(func=lambda m: True, content_types=["text"])
    def on_message(message):
        try:
            text = message.text or message.caption or ""
            if not text.strip(): return
            result = process_smart_message(text, source_label)
            if result and result.get("status") == "ok":
                for r in result.get("results", []):
                    if r.get("status") == "saved":
                        print(f"✅ [{channel}] {r['code']} ← {r['matched_number']} ({r['country']}/{r['platform']})")
        except Exception as e:
            print(f"[Poller Error] {e}")

    def run():
        print(f"[Poller] 🧠 Smart poller started for {channel}")
        while poller_running.is_set():
            try:
                bot.infinity_polling(timeout=30, long_polling_timeout=20)
            except Exception as e:
                print(f"[Poller Retry] {e} — restarting in 5s")
                time.sleep(5)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    poller_threads.append(t)

def start_all_pollers():
    poller_running.set()
    for bc in TELEGRAM_BOTS:
        start_poller(bc)

# =========================================================================
# 7) Flask App
# =========================================================================
app = Flask(__name__)
app.secret_key = APP_SECRET
app.permanent_session_lifetime = timedelta(days=7)

@app.before_request
def before_request():
    if request.path.startswith("/admin") or request.path.startswith("/static"):
        return
    settings = get_settings()
    if settings.get("maintenance_mode") == "on":
        if request.path != "/maintenance":
            return MAINTENANCE_HTML, 503

# =========================================================================
# 8) HTML الرئيسي - واجهة المستخدم
# =========================================================================
INDEX_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ settings.site_name }}</title>
<style>
:root {
  --main-color: {{ settings.main_color }};
  --secondary-color: {{ settings.secondary_color }};
  --bg-color: {{ settings.bg_color }};
  --text-color: {{ settings.text_color }};
  --base-font-size: 16px;
  --card-bg: rgba(255,255,255,0.05);
  --border-color: rgba(0,255,136,0.3);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: var(--base-font-size); }
body {
  font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
  background: var(--bg-color); color: var(--text-color);
  min-height: 100vh; position: relative; overflow-x: hidden;
}
.matrix-bg { position: fixed; inset: 0; z-index: -2; opacity: 0.15; pointer-events: none; }
.digit-bg { position: fixed; inset: 0; z-index: -1; opacity: 0.2; pointer-events: none; }

.marquee {
  background: linear-gradient(90deg, var(--main-color), var(--secondary-color));
  color: #000; padding: 10px 0; overflow: hidden; font-weight: bold;
  text-align: center;
}
.marquee-inner { display: inline-block; white-space: nowrap; animation: marquee-scroll 25s linear infinite; }
@keyframes marquee-scroll { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }

.header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 15px 20px; background: var(--card-bg);
  border-bottom: 2px solid var(--main-color); position: sticky; top: 0; z-index: 100;
  backdrop-filter: blur(10px);
}
.logo { display: flex; align-items: center; gap: 10px; }
.logo-icon { font-size: 2em; }
.logo-text { color: var(--main-color); font-size: 1.3em; font-weight: bold; }
.header-actions { display: flex; gap: 8px; }

.icon-btn {
  background: var(--card-bg); border: 1px solid var(--border-color);
  color: var(--text-color); padding: 10px 14px; border-radius: 8px;
  cursor: pointer; font-size: 16px; transition: all 0.2s;
}
.icon-btn:hover { background: var(--main-color); color: #000; }

.side-menu {
  position: fixed; top: 0; right: -320px; width: 300px; height: 100vh;
  background: var(--bg-color); border-left: 2px solid var(--main-color);
  z-index: 200; transition: right 0.3s; padding: 20px;
  display: flex; flex-direction: column;
}
.side-menu.open { right: 0; }
.menu-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 150; display: none; }
.menu-overlay.open { display: block; }
.side-menu-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.side-menu-header h3 { color: var(--main-color); }
.side-menu-links { display: flex; flex-direction: column; gap: 10px; flex: 1; }
.side-menu-links a {
  display: block; padding: 14px; background: var(--card-bg);
  border: 1px solid var(--border-color); border-radius: 8px;
  color: var(--text-color); text-decoration: none; transition: all 0.2s;
}
.side-menu-links a:hover { background: var(--main-color); color: #000; }
.admin-link { display: block; padding: 14px; text-align: center; background: var(--secondary-color); color: #000; text-decoration: none; border-radius: 8px; font-weight: bold; }

.container { max-width: 1200px; margin: 0 auto; padding: 20px; }

.stats-bar {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px; margin-bottom: 25px;
}
.stat { background: var(--card-bg); padding: 18px; border-radius: 12px; text-align: center; border: 1px solid var(--border-color); border-right: 4px solid var(--main-color); }
.stat-num { display: block; font-size: 1.8em; color: var(--main-color); font-weight: bold; }
.stat-label { color: var(--text-color); opacity: 0.7; font-size: 0.85em; }

.smart-btn {
  width: 100%; padding: 22px; display: flex; align-items: center;
  gap: 15px; background: linear-gradient(135deg, var(--main-color), var(--secondary-color));
  color: #000; border: none; border-radius: 14px; cursor: pointer;
  font-family: inherit; transition: all 0.3s;
  box-shadow: 0 5px 25px rgba(0,255,136,0.3); margin-bottom: 25px;
}
.smart-btn:hover { transform: translateY(-3px); box-shadow: 0 10px 35px rgba(0,255,136,0.5); }
.smart-btn-icon { font-size: 2.5em; }
.smart-btn-text { display: flex; flex-direction: column; text-align: right; }
.smart-btn-text strong { font-size: 1.2em; }
.smart-btn-text small { opacity: 0.8; font-size: 0.85em; }

.section-title { color: var(--main-color); margin: 25px 0 15px; font-size: 1.2em; display: flex; align-items: center; gap: 8px; }

.platforms-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 15px; margin-bottom: 25px; position: relative;
}
.platform-card {
  background: var(--card-bg); border: 2px solid var(--border-color);
  border-radius: 14px; padding: 25px 15px; text-align: center;
  cursor: pointer; transition: all 0.3s; position: relative; overflow: hidden;
  min-height: 100px; display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.platform-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: var(--card-color, var(--main-color));
  transform: scaleX(0); transition: transform 0.3s;
}
.platform-card:hover::before { transform: scaleX(1); }
.platform-card:hover { transform: translateY(-5px); box-shadow: 0 10px 30px rgba(0,255,136,0.2); }
.platform-card.active { border-color: var(--card-color, var(--main-color)); background: rgba(0,255,136,0.1); }
.platform-icon { font-size: 2.8em; margin-bottom: 8px; }
.platform-name { font-weight: bold; font-size: 1em; }

.countries-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 10px; margin-bottom: 25px;
}
.country-card {
  background: var(--card-bg); border: 1px solid var(--border-color);
  border-radius: 8px; padding: 12px; cursor: pointer;
  display: flex; justify-content: space-between; align-items: center; transition: all 0.2s;
}
.country-card:hover { background: var(--main-color); color: #000; transform: translateX(-5px); }
.country-name { display: flex; align-items: center; gap: 8px; }
.country-flag { font-size: 1.4em; }
.country-available { background: var(--main-color); color: #000; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; }

.number-display {
  background: var(--card-bg); border: 2px solid var(--main-color);
  border-radius: 16px; padding: 25px; margin-bottom: 25px;
  text-align: center; box-shadow: 0 0 35px rgba(0,255,136,0.2);
}
.number-box, .code-box { margin-bottom: 20px; }
.number-label, .code-label { color: var(--secondary-color); margin-bottom: 10px; font-weight: bold; }
.number-value {
  font-size: 2em; color: var(--main-color); font-weight: bold;
  letter-spacing: 3px; font-family: 'Courier New', monospace;
  padding: 15px; background: rgba(0,0,0,0.3); border-radius: 10px;
  margin-bottom: 10px; display: inline-block; min-width: 280px;
}
.digit { display: inline-block; opacity: 0; transform: translateY(-50px); animation: digit-drop 0.4s forwards; }
@keyframes digit-drop { to { opacity: 1; transform: translateY(0); } }
.copy-btn {
  background: var(--secondary-color); color: #000; border: none;
  padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: bold;
  margin: 5px; transition: all 0.2s;
}
.copy-btn:hover { background: var(--main-color); transform: scale(1.05); }
.number-timer { color: var(--secondary-color); font-size: 1.1em; margin-top: 10px; }
.code-value {
  font-size: 2.2em; color: var(--main-color); font-weight: bold;
  letter-spacing: 5px; padding: 18px; background: rgba(0,0,0,0.3);
  border-radius: 10px; display: inline-block; min-width: 250px;
  border: 2px dashed var(--main-color);
}
.waiting-spinner {
  display: inline-block; width: 20px; height: 20px;
  border: 3px solid var(--border-color); border-top-color: var(--main-color);
  border-radius: 50%; animation: spin 1s linear infinite;
  vertical-align: middle; margin-left: 10px;
}
@keyframes spin { to { transform: rotate(360deg); } }
.actions-row { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }
.action-btn {
  background: var(--card-bg); border: 1px solid var(--secondary-color);
  color: var(--secondary-color); padding: 12px 22px; border-radius: 8px;
  cursor: pointer; transition: all 0.2s;
}
.action-btn:hover { background: var(--secondary-color); color: #000; }

.live-feed { max-height: 350px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
.feed-item {
  display: grid; grid-template-columns: 50px 1fr 1fr 1fr; gap: 10px;
  padding: 12px 15px; background: rgba(0,0,0,0.3); border-radius: 8px;
  align-items: center; font-size: 0.9em;
  border-right: 3px solid var(--secondary-color);
  animation: slide-in 0.3s;
}
.feed-item.new { border-right-color: var(--main-color); background: rgba(0,255,136,0.05); }
.feed-icon { font-size: 1.5em; }
.feed-number { font-family: 'Courier New', monospace; color: var(--secondary-color); }
.feed-code { color: var(--main-color); font-weight: bold; text-align: left; }
.feed-time { font-size: 0.75em; opacity: 0.6; }
@keyframes slide-in { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } }

.card {
  background: var(--card-bg); border: 1px solid var(--border-color);
  border-radius: 12px; padding: 20px; margin-bottom: 20px;
}
.card h3 { color: var(--main-color); margin-bottom: 15px; }
.empty { text-align: center; color: #888; padding: 20px; }

.search-box { position: relative; margin-bottom: 25px; }
.search-box input {
  width: 100%; padding: 14px 20px; font-size: 1em;
  background: var(--card-bg); border: 1px solid var(--border-color);
  border-radius: 10px; color: var(--text-color);
}
.search-box input:focus { outline: none; border-color: var(--main-color); }
.search-results {
  position: absolute; top: 100%; left: 0; right: 0;
  background: var(--bg-color); border: 1px solid var(--border-color);
  border-radius: 0 0 10px 10px; max-height: 300px; overflow-y: auto;
  z-index: 50; display: none;
}
.search-results.open { display: block; }
.search-result-item { padding: 12px 20px; border-bottom: 1px solid var(--border-color); cursor: pointer; }
.search-result-item:hover { background: var(--card-bg); }

.font-controls {
  display: flex; gap: 8px; align-items: center; justify-content: center;
  margin-bottom: 20px; padding: 12px; background: var(--card-bg);
  border: 1px solid var(--border-color); border-radius: 10px;
}
.font-btn {
  background: var(--main-color); color: #000; border: none;
  padding: 8px 16px; border-radius: 6px; font-weight: bold; cursor: pointer;
}
.font-label { color: var(--text-color); font-size: 0.9em; }

.modal { position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 300; display: flex; align-items: center; justify-content: center; }
.modal-content { background: var(--bg-color); border: 2px solid var(--main-color); border-radius: 12px; padding: 25px; width: 90%; max-width: 450px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
.modal-header h3 { color: var(--main-color); }
.modal-close { background: none; border: none; color: var(--text-color); font-size: 1.5em; cursor: pointer; }
.modal-content textarea { width: 100%; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-color); color: var(--text-color); border-radius: 6px; font-family: inherit; resize: vertical; }
.primary-btn { width: 100%; padding: 14px; background: var(--main-color); color: #000; border: none; border-radius: 8px; font-weight: bold; margin-top: 12px; cursor: pointer; }

#toast-container { position: fixed; top: 80px; left: 20px; z-index: 9999; display: flex; flex-direction: column; gap: 10px; }
.toast { background: var(--bg-color); border-left: 4px solid var(--main-color); padding: 14px 20px; border-radius: 6px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); animation: toast-in 0.3s; }
.toast.error { border-left-color: #ff4444; }
@keyframes toast-in { from { transform: translateX(-100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }

.top-banner {
  position: fixed; top: 0; left: 0; right: 0;
  background: linear-gradient(135deg, var(--main-color), var(--secondary-color));
  color: #000; padding: 15px 20px; font-weight: bold; text-align: center;
  z-index: 9999; transform: translateY(-150%);
  transition: transform 0.4s ease; box-shadow: 0 5px 20px rgba(0,0,0,0.5);
  font-size: 1.1em;
}
.top-banner.show { transform: translateY(0); }
.top-banner .banner-code { font-size: 1.4em; font-family: 'Courier New', monospace; background: #000; color: var(--main-color); padding: 4px 12px; border-radius: 6px; margin: 0 10px; }
.top-banner .banner-close { position: absolute; right: 15px; top: 50%; transform: translateY(-50%); background: none; border: none; font-size: 1.5em; cursor: pointer; }

.footer-info { text-align: center; padding: 20px; color: #888; font-size: 0.9em; }
.footer-info strong { color: var(--main-color); }

@media (max-width: 768px) {
  .stats-bar { grid-template-columns: repeat(2, 1fr); }
  .platforms-grid { grid-template-columns: repeat(3, 1fr); }
  .countries-grid { grid-template-columns: repeat(2, 1fr); }
  .number-value, .code-value { font-size: 1.5em; min-width: 200px; }
  .feed-item { grid-template-columns: 40px 1fr 1fr; }
  .feed-time { display: none; }
}
</style>
</head>
<body>
<canvas id="matrix-rain" class="matrix-bg"></canvas>
<canvas id="digit-rain" class="digit-bg"></canvas>

<div class="top-banner" id="top-banner"></div>

<div class="marquee">
  <div class="marquee-inner">
    <span>📢 {{ settings.announcement }}</span>
    <span>•</span>
    <span>{{ settings.marquee_text }}</span>
    <span>•</span>
    <span>📞 للدعم: 967733723953</span>
  </div>
</div>

<header class="header">
  <button id="menu-toggle" class="icon-btn">☰</button>
  <h1 class="logo">
    <span class="logo-icon">🔐</span>
    <span class="logo-text">{{ settings.site_name }}</span>
  </h1>
  <div class="header-actions">
    <button id="sound-toggle" class="icon-btn" title="تشغيل/إيقاف الصوت">🔔</button>
  </div>
</header>

<aside id="side-menu" class="side-menu">
  <div class="side-menu-header">
    <h3>القائمة</h3>
    <button id="menu-close" class="icon-btn">✕</button>
  </div>
  <nav class="side-menu-links" id="side-menu-links"></nav>
  <div class="side-menu-footer">
    <a href="/admin/login" class="admin-link">🔧 دخول الأدمن</a>
  </div>
</aside>
<div id="menu-overlay" class="menu-overlay"></div>

<div class="container">
  <section class="stats-bar">
    <div class="stat"><span class="stat-num">{{ stats.today_numbers }}</span><span class="stat-label">أرقام اليوم</span></div>
    <div class="stat"><span class="stat-num">{{ stats.today_codes }}</span><span class="stat-label">أكواد اليوم</span></div>
    <div class="stat"><span class="stat-num">{{ stats.active_users }}</span><span class="stat-label">نشطين الآن</span></div>
    <div class="stat"><span class="stat-num">{{ stats.total_visits }}</span><span class="stat-label">إجمالي الزيارات</span></div>
  </section>

  <button id="btn-smart-pick" class="smart-btn">
    <span class="smart-btn-icon">⚡</span>
    <span class="smart-btn-text">
      <strong>{{ settings.smart_btn_text or '⚡ استلام ذكي فوري' }}</strong>
      <small>{{ settings.smart_btn_subtext or 'يختار لك أفضل رقم متاح مع كوده تلقائياً' }}</small>
    </span>
  </button>

  <div class="card">
    <h3>{{ settings.live_codes or '⚡ آخر الأكواد من القنوات (لايف)' }}</h3>
    <div id="live-feed" class="live-feed"><div class="empty">جاري التحميل...</div></div>
  </div>

  <div class="search-box">
    <input type="text" id="instant-search" placeholder="{{ settings.search_placeholder or '🔍 بحث فوري...' }}" autocomplete="off">
    <div id="search-results" class="search-results"></div>
  </div>

  <div class="font-controls">
    <button class="font-btn" onclick="changeFontSize(-2)">A-</button>
    <span class="font-label">حجم الخط</span>
    <button class="font-btn" onclick="changeFontSize(2)">A+</button>
  </div>

  <section>
    <h2 class="section-title">📱 {{ settings.choose_platform or 'اختر المنصة' }}</h2>
    <div class="platforms-grid" id="platforms-grid">
      {% for p in platforms %}
      <div class="platform-card" data-platform-id="{{ p.id }}" style="--card-color: {{ p.color }}">
        <div class="platform-icon">{{ p.icon }}</div>
        <div class="platform-name">{{ p.name }}</div>
      </div>
      {% endfor %}
    </div>
  </section>

  <section id="countries-section" style="display:none">
    <h2 class="section-title">🌍 {{ settings.choose_country or 'اختر الدولة' }}</h2>
    <div class="countries-grid" id="countries-grid"></div>
  </section>

  <section class="number-display" id="number-display" style="display:none">
    <div class="number-box">
      <div class="number-label">📞 {{ settings.your_number or 'رقمك' }}</div>
      <div class="number-value" id="number-value">---</div>
      <button class="copy-btn" id="copy-number">📋 {{ settings.copy_number or 'نسخ الرقم' }}</button>
      <div class="number-timer" id="number-timer">⏱ 02:00</div>
    </div>
    <div class="code-box">
      <div class="code-label">🔑 {{ settings.your_code or 'الكود' }}</div>
      <div class="code-value" id="code-value">
        <div class="waiting-spinner"></div>
        <span>{{ settings.waiting_code or 'في انتظار الكود...' }}</span>
      </div>
      <button class="copy-btn" id="copy-code" style="display:none">📋 {{ settings.copy_code or 'نسخ الكود' }}</button>
    </div>
    <div class="actions-row">
      <button class="action-btn" id="btn-next">🔄 {{ settings.next_number or 'الرقم التالي' }}</button>
      <button class="action-btn" id="btn-help">🆘 {{ settings.help or 'مساعدة' }}</button>
    </div>
  </section>
</div>

<div class="footer-info">{{ settings.footer_text or '💎 صُنع بحب ⚡ بواسطة المطري' }}</div>

<div id="help-modal" class="modal" style="display:none">
  <div class="modal-content">
    <div class="modal-header">
      <h3>🆘 طلب مساعدة</h3>
      <button class="modal-close" id="help-close">✕</button>
    </div>
    <textarea id="help-message" rows="5" placeholder="اكتب مشكلتك هنا..."></textarea>
    <button class="primary-btn" id="help-send">إرسال</button>
  </div>
</div>

<div id="toast-container"></div>

<script>
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

// ============ الألوان والإعدادات ============
fetch('/api/ui_settings').then(r=>r.json()).then(d=>{
  if (d.ok && d.settings) {
    const s = d.settings;
    if (s.main_color) document.documentElement.style.setProperty('--main-color', s.main_color);
    if (s.secondary_color) document.documentElement.style.setProperty('--secondary-color', s.secondary_color);
    if (s.bg_color) document.documentElement.style.setProperty('--bg-color', s.bg_color);
    if (s.text_color) document.documentElement.style.setProperty('--text-color', s.text_color);
    if (s.digit_rain_enabled !== '1') { const dr = document.getElementById('digit-rain'); if (dr) dr.style.display = 'none'; }
    if (s.matrix_rain_enabled !== '1') { const mr = document.getElementById('matrix-rain'); if (mr) mr.style.display = 'none'; }
  }
}).catch(()=>{});

// ============ الصوت ============
let soundEnabled = localStorage.getItem('soundEnabled') !== 'false';
const soundBtn = document.getElementById('sound-toggle');
if (soundBtn) {
  soundBtn.textContent = soundEnabled ? '🔔' : '🔕';
  soundBtn.addEventListener('click', () => {
    soundEnabled = !soundEnabled;
    localStorage.setItem('soundEnabled', soundEnabled);
    soundBtn.textContent = soundEnabled ? '🔔' : '🔕';
  });
}
function playAlert() {
  if (!soundEnabled) return;
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    [880, 1100, 1320].forEach((f, i) => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.frequency.value = f; o.type = 'sine';
      g.gain.setValueAtTime(0.3, ctx.currentTime + i * 0.15);
      g.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + i * 0.15 + 0.3);
      o.start(ctx.currentTime + i * 0.15);
      o.stop(ctx.currentTime + i * 0.15 + 0.3);
    });
  } catch (e) {}
}

// ============ الإشعارات ============
function showTopBanner(title, code) {
  const banner = document.getElementById('top-banner');
  if (!banner) return;
  banner.innerHTML = '<button class="banner-close" onclick="this.parentElement.classList.remove(\'show\')">✕</button>' + title + ' <span class="banner-code">' + code + '</span>';
  banner.classList.add('show');
  setTimeout(() => banner.classList.remove('show'), 5000);
}
function pushNotification(title, body) {
  if ('Notification' in window && Notification.permission === 'granted') {
    try { new Notification(title, { body }); } catch (e) {}
  }
}
if ('Notification' in window && Notification.permission === 'default') Notification.requestPermission();

// ============ القائمة ============
const mt = document.getElementById('menu-toggle');
if (mt) mt.addEventListener('click', () => {
  document.getElementById('side-menu').classList.add('open');
  document.getElementById('menu-overlay').classList.add('open');
});
const mc = document.getElementById('menu-close');
if (mc) mc.addEventListener('click', () => {
  document.getElementById('side-menu').classList.remove('open');
  document.getElementById('menu-overlay').classList.remove('open');
});
const mo = document.getElementById('menu-overlay');
if (mo) mo.addEventListener('click', () => {
  document.getElementById('side-menu').classList.remove('open');
  document.getElementById('menu-overlay').classList.remove('open');
});

fetch('/api/links').then(r=>r.json()).then(d=>{
  const el = document.getElementById('side-menu-links');
  if (el && d.links) el.innerHTML = d.links.map(l => '<a href="'+l.url+'" target="_blank">'+(l.icon||'🔗')+' '+l.label+'</a>').join('');
});

// ============ Toast ============
function toast(msg, type) {
  const t = document.createElement('div');
  t.className = 'toast ' + (type || '');
  t.textContent = msg;
  const c = document.getElementById('toast-container');
  if (c) c.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ============ حجم الخط ============
function changeFontSize(delta) {
  let f = parseInt(localStorage.getItem('fontSize') || '16');
  f = Math.max(12, Math.min(24, f + delta));
  localStorage.setItem('fontSize', f);
  document.documentElement.style.setProperty('--base-font-size', f + 'px');
  toast('📏 حجم الخط: ' + f + 'px');
}
document.documentElement.style.setProperty('--base-font-size', (parseInt(localStorage.getItem('fontSize') || '16')) + 'px');

// ============ أرقام متساقطة ============
function startDigitRain() {
  const canvas = document.getElementById('digit-rain');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  const drops = [];
  for (let i = 0; i < 40; i++) {
    drops.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      s: Math.random() * 3 + 1,
      txt: '0123456789'[Math.floor(Math.random() * 10)]
    });
  }
  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#00ffc8';
    ctx.font = '18px monospace';
    drops.forEach(d => {
      ctx.fillText(d.txt, d.x, d.y);
      d.y += d.s;
      if (d.y > canvas.height) { d.y = 0; d.x = Math.random() * canvas.width; d.txt = '0123456789'[Math.floor(Math.random() * 10)]; }
    });
  }
  setInterval(draw, 80);
  window.addEventListener('resize', () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight; });
}

// ============ Matrix Rain ============
function startMatrixRain() {
  const canvas = document.getElementById('matrix-rain');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ابتثجحخدذرزسشصضطظعغفقكلمنهوي';
  const fontSize = 14;
  const cols = Math.floor(canvas.width / fontSize);
  const drops = Array(cols).fill(1);
  function draw() {
    ctx.fillStyle = 'rgba(0,0,0,0.05)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#0f0';
    ctx.font = fontSize + 'px monospace';
    for (let i = 0; i < drops.length; i++) {
      ctx.fillText(chars[Math.floor(Math.random() * chars.length)], i * fontSize, drops[i] * fontSize);
      if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0;
      drops[i]++;
    }
  }
  setInterval(draw, 50);
  window.addEventListener('resize', () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight; });
}

startMatrixRain();
startDigitRain();

// ============ المنصات والدول ============
let selectedPlatform = null;
let currentNumber = null, currentCode = null, currentNumberId = null, currentCountryId = null, timerInterval = null;

document.querySelectorAll('.platform-card').forEach(card => {
  card.addEventListener('click', () => {
    document.querySelectorAll('.platform-card').forEach(c => c.classList.remove('active'));
    card.classList.add('active');
    selectedPlatform = card.dataset.platformId;
    loadCountries(selectedPlatform);
  });
});

function loadCountries(pid) {
  fetch('/api/countries/' + pid).then(r=>r.json()).then(d => {
    if (!d.countries || !d.countries.length) { toast('لا توجد دول لهذه المنصة', 'error'); return; }
    const g = document.getElementById('countries-grid');
    if (g) g.innerHTML = d.countries.map(c => '<div class="country-card" data-country-id="'+c.id+'"><div class="country-name"><span class="country-flag">'+(c.flag||'🌍')+'</span><span>'+c.name+'</span></div><span class="country-available">'+c.available+'</span></div>').join('');
    const s = document.getElementById('countries-section');
    if (s) s.style.display = 'block';
    document.querySelectorAll('#countries-grid .country-card').forEach(c => {
      c.addEventListener('click', () => { currentCountryId = c.dataset.countryId; requestNumber(currentCountryId); });
    });
  });
}

function requestNumber(countryId, numberId) {
  const url = numberId ? '/api/next_number' : '/api/get_number';
  fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ country_id: countryId, current_number_id: numberId }) })
    .then(r=>r.json()).then(d => {
      if (!d.ok) { toast(d.error, 'error'); return; }
      currentNumber = d.number; currentNumberId = d.number_id; currentCode = d.code;
      renderNumberWithDrop(d.number, 'number-value');
      if (d.code) {
        document.getElementById('code-value').textContent = d.code;
        document.getElementById('copy-code').style.display = 'inline-block';
      } else {
        document.getElementById('code-value').innerHTML = '<div class="waiting-spinner"></div><span>في انتظار الكود...</span>';
        document.getElementById('copy-code').style.display = 'none';
        startCodePolling(d.number_id);
      }
      document.getElementById('number-display').style.display = 'block';
      document.getElementById('number-display').scrollIntoView({ behavior: 'smooth' });
      startTimer(d.expires_in || 120);
    });
}

function renderNumberWithDrop(text, id) {
  const el = document.getElementById(id);
  el.innerHTML = '';
  text.split('').forEach((ch, i) => {
    const s = document.createElement('span');
    s.className = 'digit';
    s.textContent = ch;
    s.style.animationDelay = (i * 0.05) + 's';
    el.appendChild(s);
  });
}

const bn = document.getElementById('btn-next');
if (bn) bn.addEventListener('click', () => {
  if (currentCountryId) { stopCodePolling(); requestNumber(currentCountryId, currentNumberId); }
});

// ============ زر الاستلام الذكي ============
const bs = document.getElementById('btn-smart-pick');
if (bs) bs.addEventListener('click', () => {
  fetch('/api/smart_pick', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({}) })
    .then(r=>r.json()).then(d => {
      if (!d.ok) { toast(d.error, 'error'); return; }
      currentNumber = d.number; currentNumberId = d.number_id; currentCode = d.code;
      renderNumberWithDrop(d.number, 'number-value');
      if (d.code) {
        document.getElementById('code-value').textContent = d.code;
        document.getElementById('copy-code').style.display = 'inline-block';
        playAlert();
        showTopBanner('✅ كود جاهز', d.code);
        toast('✅ ' + d.platform + ' - ' + d.country);
      } else {
        document.getElementById('code-value').innerHTML = '<div class="waiting-spinner"></div><span>في انتظار الكود...</span>';
        document.getElementById('copy-code').style.display = 'none';
        startCodePolling(d.number_id);
        toast('⏳ في انتظار الكود...');
      }
      document.getElementById('number-display').style.display = 'block';
      document.getElementById('number-display').scrollIntoView({ behavior: 'smooth' });
      startTimer(d.expires_in || 120);
    });
});

// ============ التايمر ============
function startTimer(seconds) {
  if (timerInterval) clearInterval(timerInterval);
  let remaining = seconds;
  const update = () => {
    const m = Math.floor(remaining / 60); const s = remaining % 60;
    const t = document.getElementById('number-timer');
    if (t) t.textContent = '⏱ ' + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
    if (remaining <= 0) { clearInterval(timerInterval); toast('⏰ انتهت صلاحية الرقم'); }
    else remaining--;
  };
  update();
  timerInterval = setInterval(update, 1000);
}

// ============ سحب الكود ============
let codePollInterval = null;
function startCodePolling(numberId) {
  if (codePollInterval) clearInterval(codePollInterval);
  codePollInterval = setInterval(() => {
    fetch('/api/check_code/' + numberId).then(r=>r.json()).then(d => {
      if (d.code && d.code !== currentCode) {
        currentCode = d.code;
        document.getElementById('code-value').textContent = d.code;
        document.getElementById('copy-code').style.display = 'inline-block';
        playAlert();
        pushNotification('🔑 كود جديد!', 'الكود: ' + d.code);
        showTopBanner('🔑 كود جديد!', d.code);
        toast('🔑 الكود وصل: ' + d.code);
      }
    });
  }, 3000);
}
function stopCodePolling() { if (codePollInterval) clearInterval(codePollInterval); }

// ============ مساعدة ============
const bh = document.getElementById('btn-help');
if (bh) bh.addEventListener('click', () => { const m = document.getElementById('help-modal'); if (m) m.style.display = 'flex'; });
const hc = document.getElementById('help-close');
if (hc) hc.addEventListener('click', () => { const m = document.getElementById('help-modal'); if (m) m.style.display = 'none'; });
const hs = document.getElementById('help-send');
if (hs) hs.addEventListener('click', () => {
  const me = document.getElementById('help-message');
  const msg = me ? me.value.trim() : '';
  if (!msg) { toast('اكتب رسالتك أولاً', 'error'); return; }
  fetch('/api/help', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ message: msg }) })
    .then(r=>r.json()).then(d => { if (d.ok) { toast(d.message); const m = document.getElementById('help-modal'); if (m) m.style.display = 'none'; if (me) me.value = ''; } });
});

// ============ بحث ============
const isearch = document.getElementById('instant-search');
if (isearch) isearch.addEventListener('input', e => {
  const q = e.target.value.trim();
  if (q.length < 2) { document.getElementById('search-results').classList.remove('open'); return; }
  fetch('/api/search?q=' + encodeURIComponent(q)).then(r=>r.json()).then(d => {
    if (!d.results || !d.results.length) { document.getElementById('search-results').classList.remove('open'); return; }
    document.getElementById('search-results').innerHTML = d.results.map(r => '<div class="search-result-item">'+r.icon+' <b>'+r.platform+'</b> / '+r.country+' — <code>'+r.number+'</code></div>').join('');
    document.getElementById('search-results').classList.add('open');
  });
});
document.addEventListener('click', e => { if (!e.target.closest('.search-box')) { const sr = document.getElementById('search-results'); if (sr) sr.classList.remove('open'); } });

// ============ اللايف فيد ============
function loadFeed() {
  fetch('/api/feed').then(r=>r.json()).then(d => {
    const box = document.getElementById('live-feed');
    if (!box) return;
    if (!d.feed || !d.feed.length) { box.innerHTML = '<div class="empty">لا توجد أكواد بعد</div>'; return; }
    box.innerHTML = d.feed.map(f => '<div class="feed-item"><div class="feed-icon">'+(f.icon||'📱')+'</div><div><b style="color:'+(f.color||'#00ff88')+'">'+f.platform+'</b> / '+(f.flag||'')+' '+f.country+'</div><div class="feed-number">'+f.number+'</div><div class="feed-code">'+f.code+' <span class="feed-time">'+(f.received_at||'').slice(11,19)+'</span></div></div>').join('');
  });
}
loadFeed();
setInterval(loadFeed, 5000);

// ============ نسخ ============
function copyText(text) {
  if (!text) return;
  if (navigator.clipboard) navigator.clipboard.writeText(text).then(() => toast('✅ تم النسخ: ' + text));
}
document.getElementById('copy-number')?.addEventListener('click', () => copyText(currentNumber));
document.getElementById('copy-code')?.addEventListener('click', () => copyText(currentCode));
</script>
</body>
</html>
"""

# =========================================================================
# 9) لوحة الأدمن - HTML مع ألوان جديدة
# =========================================================================
ADMIN_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Arial, sans-serif; }
body { background: linear-gradient(135deg, #0f0f23, #1a1a35); color: #e0e0ff; min-height: 100vh; padding: 20px; }
.header {
  display: flex; justify-content: space-between; align-items: center;
  background: linear-gradient(135deg, #667eea, #764ba2);
  padding: 20px 30px; border-radius: 15px; margin-bottom: 25px;
  box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
}
h1 { color: #fff; font-size: 1.8em; text-shadow: 0 2px 10px rgba(0,0,0,0.3); }
h3 { color: #a78bfa; margin-bottom: 15px; }
.nav {
  display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 25px;
  background: rgba(255,255,255,0.05); padding: 15px; border-radius: 12px;
}
.nav a {
  padding: 10px 16px; background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff; text-decoration: none; border-radius: 8px; font-size: 13px;
  font-weight: 600; transition: all 0.3s; border: 1px solid transparent;
}
.nav a:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(102,126,234,0.4); border-color: #fff; }
.nav a.active { background: linear-gradient(135deg, #f093fb, #f5576c); }
.stats {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 15px; margin-bottom: 25px;
}
.stat {
  background: linear-gradient(135deg, #1a1a35, #2d2d5a);
  padding: 22px; border-radius: 12px; text-align: center;
  border: 1px solid #667eea; box-shadow: 0 5px 20px rgba(102,126,234,0.2);
}
.stat-num { font-size: 2.2em; color: #a78bfa; font-weight: bold; display: block; }
.stat-label { color: #9ca3af; font-size: 13px; margin-top: 5px; }
.card {
  background: linear-gradient(135deg, #1a1a35, #2d2d5a);
  padding: 25px; border-radius: 15px; margin-bottom: 25px;
  border: 1px solid #667eea; box-shadow: 0 5px 25px rgba(102,126,234,0.15);
}
table { width: 100%; border-collapse: collapse; margin-top: 15px; }
th, td { padding: 12px 8px; text-align: right; border-bottom: 1px solid #374151; font-size: 13px; }
th {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff; font-weight: 600; border-radius: 8px 8px 0 0;
}
tr:hover td { background: rgba(102, 126, 234, 0.1); }
.logout {
  background: linear-gradient(135deg, #f5576c, #f093fb);
  color: #fff; padding: 10px 20px; border-radius: 8px; text-decoration: none;
  font-weight: 600; transition: all 0.3s;
}
.logout:hover { transform: scale(1.05); box-shadow: 0 5px 20px rgba(245,87,108,0.4); }
.form-row { margin-bottom: 15px; }
label { display: block; color: #a78bfa; margin-bottom: 8px; font-size: 13px; font-weight: 600; }
input, select, textarea {
  width: 100%; padding: 12px; background: rgba(0,0,0,0.3);
  border: 1px solid #4b5563; color: #fff; border-radius: 8px;
  font-family: inherit; font-size: 14px;
}
input:focus, select:focus, textarea:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102,126,234,0.2); }
input[type=color] { height: 45px; padding: 5px; cursor: pointer; }
button[type=submit] {
  padding: 14px 28px; background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff; border: none; border-radius: 8px; font-weight: bold;
  cursor: pointer; font-size: 14px; transition: all 0.3s;
}
button[type=submit]:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(102,126,234,0.4); }
.del-btn {
  background: linear-gradient(135deg, #f5576c, #e53935);
  color: #fff; padding: 6px 12px; border-radius: 6px; border: none; cursor: pointer; font-size: 12px;
}
.unban-btn {
  background: linear-gradient(135deg, #10b981, #059669);
  color: #fff; padding: 6px 12px; border-radius: 6px; border: none; cursor: pointer; font-size: 12px;
}
.ban-btn {
  background: linear-gradient(135deg, #f5576c, #e53935);
  color: #fff; padding: 6px 12px; border-radius: 6px; border: none; cursor: pointer; font-size: 12px;
}
.flash {
  background: linear-gradient(135deg, #10b981, #059669);
  color: #fff; padding: 14px; border-radius: 8px; margin-bottom: 15px; text-align: center; font-weight: 600;
}
.flash.error { background: linear-gradient(135deg, #f5576c, #e53935); }
pre { background: #000; padding: 15px; border-radius: 8px; color: #0f0; overflow-x: auto; font-size: 12px; }
.banned { color: #f5576c; font-weight: bold; }
.row { display: flex; gap: 12px; margin-bottom: 15px; flex-wrap: wrap; align-items: flex-end; }
.row form { margin: 0; }
.switch {
  position: relative; width: 55px; height: 28px;
  background: #374151; border-radius: 14px; cursor: pointer; transition: 0.3s;
}
.switch.on { background: linear-gradient(135deg, #667eea, #764ba2); }
.switch::after {
  content: ''; position: absolute; top: 3px; right: 3px;
  width: 22px; height: 22px; background: #fff; border-radius: 50%; transition: 0.3s;
}
.switch.on::after { right: 30px; }
.toggle-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px; background: rgba(0,0,0,0.2); border-radius: 8px; margin-bottom: 10px;
}
.toggle-row label { color: #a78bfa; font-size: 14px; margin: 0; }
.section {
  background: linear-gradient(135deg, #1a1a35, #2d2d5a);
  padding: 20px; border-radius: 12px; margin-bottom: 20px;
  border: 1px solid #667eea;
}
.section h3 { color: #f093fb; margin-bottom: 15px; }
.color-row { display: grid; grid-template-columns: 1fr 100px; gap: 10px; align-items: center; margin-bottom: 10px; }
.text-row { display: grid; grid-template-columns: 1fr 2fr; gap: 10px; margin-bottom: 10px; }
"""

ADMIN_NAV = """
<div class="nav">
  <a href="/admin">🏠 الرئيسية</a>
  <a href="/admin/settings">⚙️ الإعدادات</a>
  <a href="/admin/customize">🎨 تخصيص الموقع</a>
  <a href="/admin/platforms">📱 المنصات</a>
  <a href="/admin/combos">📂 الكومبوهات</a>
  <a href="/admin/users">👥 المستخدمون</a>
  <a href="/admin/links">🔗 الروابط</a>
  <a href="/admin/codes">🔑 الأكواد</a>
  <a href="/admin/audits">📋 السجلات</a>
  <a href="/admin/backup">💾 نسخة احتياطية</a>
</div>
"""

ADMIN_LOGIN_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>دخول الأدمن</title>
<style>""" + ADMIN_CSS + """
.login-box {
  background: linear-gradient(135deg, #1a1a35, #2d2d5a);
  padding: 50px; border-radius: 20px; border: 2px solid #667eea;
  width: 400px; margin: 80px auto;
  box-shadow: 0 20px 60px rgba(102,126,234,0.3);
}
h1 { text-align: center; margin-bottom: 30px; font-size: 2em; }
</style></head>
<body>
<form class="login-box" method="POST">
  <h1>🔐 لوحة الأدمن</h1>
  {% with messages = get_flashed_messages(with_categories=true) %}{% for cat,msg in messages %}
  <div class="flash {{ cat }}">{{ msg }}</div>{% endfor %}{% endwith %}
  <div class="form-row"><input type="text" name="username" placeholder="اسم المستخدم" required autofocus></div>
  <div class="form-row"><input type="password" name="password" placeholder="كلمة المرور" required></div>
  <button type="submit" style="width:100%;margin-top:10px">دخول</button>
</form>
</body></html>
"""

ADMIN_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>لوحة الأدمن</title>
<style>""" + ADMIN_CSS + """</style></head>
<body>
<div class="header">
  <h1>🔐 مرحباً {{ admin_user }} ({{ role }})</h1>
  <a class="logout" href="/admin/logout">خروج</a>
</div>
""" + ADMIN_NAV + """
<div class="stats">
  <div class="stat"><span class="stat-num">{{ stats.total_numbers }}</span><span class="stat-label">إجمالي الأرقام</span></div>
  <div class="stat"><span class="stat-num">{{ stats.available }}</span><span class="stat-label">متاحة</span></div>
  <div class="stat"><span class="stat-num">{{ stats.total_codes }}</span><span class="stat-label">إجمالي الأكواد</span></div>
  <div class="stat"><span class="stat-num">{{ stats.total_users }}</span><span class="stat-label">مستخدمين</span></div>
  <div class="stat"><span class="stat-num">{{ stats.banned_users }}</span><span class="stat-label">محظورين</span></div>
  <div class="stat"><span class="stat-num">{{ stats.platforms }}</span><span class="stat-label">منصات</span></div>
  <div class="stat"><span class="stat-num">{{ stats.countries }}</span><span class="stat-label">دول</span></div>
</div>
<div class="card">
  <h3>📋 آخر 10 حركات</h3>
  <table>
    <tr><th>الوقت</th><th>المستخدم</th><th>الحركة</th><th>التفاصيل</th><th>IP</th></tr>
    {% for a in audits %}
    <tr><td>{{ a.created_at }}</td><td>{{ a.admin_user }}</td><td>{{ a.action }}</td><td>{{ a.details }}</td><td>{{ a.ip }}</td></tr>
    {% else %}<tr><td colspan="5" style="text-align:center;color:#888">لا يوجد</td></tr>{% endfor %}
  </table>
</div>
</body></html>
"""

ADMIN_SETTINGS_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>الإعدادات</title>
<style>""" + ADMIN_CSS + """.form{max-width:700px}</style></head>
<body>
""" + ADMIN_NAV + """
<h1>⚙️ إعدادات الموقع</h1>
{% with messages = get_flashed_messages(with_categories=true) %}{% for cat,msg in messages %}
<div class="flash {{ cat }}">{{ msg }}</div>{% endfor %}{% endwith %}
<form method="POST" class="form">
  <div class="form-row"><label>اسم الموقع</label><input name="site_name" value="{{ settings.site_name }}"></div>
  <div class="form-row"><label>نص الإعلانات</label><input name="announcement" value="{{ settings.announcement }}"></div>
  <div class="form-row"><label>نص Marquee المتحرك</label><input name="marquee_text" value="{{ settings.marquee_text }}"></div>
  <div class="form-row"><label>اللون الرئيسي</label><input type="color" name="main_color" value="{{ settings.main_color }}"></div>
  <div class="form-row"><label>اللون الثانوي</label><input type="color" name="secondary_color" value="{{ settings.secondary_color }}"></div>
  <div class="form-row"><label>لون الخلفية</label><input type="color" name="bg_color" value="{{ settings.bg_color }}"></div>
  <div class="form-row"><label>لون النص</label><input type="color" name="text_color" value="{{ settings.text_color }}"></div>
  <div class="form-row"><label>وضع الصيانة</label>
    <select name="maintenance_mode">
      <option value="off" {% if settings.maintenance_mode=='off' %}selected{% endif %}>off</option>
      <option value="on" {% if settings.maintenance_mode=='on' %}selected{% endif %}>on</option>
    </select>
  </div>
  <div class="form-row"><label>حد الطلبات/دقيقة</label><input type="number" name="rate_limit_per_minute" value="{{ settings.rate_limit_per_minute }}"></div>
  <div class="form-row"><label>نص الفوتر</label><input name="footer_text" value="{{ settings.footer_text }}"></div>
  <button type="submit">💾 حفظ</button>
</form>
</body></html>
"""

ADMIN_PLATFORMS_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>المنصات</title>
<style>""" + ADMIN_CSS + """</style></head>
<body>
""" + ADMIN_NAV + """
<h1>📱 إدارة المنصات</h1>
<div class="card">
  <h3>➕ إضافة منصة جديدة</h3>
  <form method="POST" class="row">
    <input type="hidden" name="action" value="add">
    <input name="name" placeholder="اسم المنصة" required>
    <input name="icon" placeholder="📱" maxlength="4">
    <input type="color" name="color" value="#667eea">
    <input type="number" name="sort_order" value="0" style="width:80px">
    <button type="submit">إضافة</button>
  </form>
</div>
<div class="card">
  <h3>📋 المنصات الحالية</h3>
  <table>
    <tr><th>الأيقونة</th><th>الاسم</th><th>اللون</th><th>الترتيب</th><th>إجراءات</th></tr>
    {% for p in platforms %}
    <tr>
      <td style="font-size:28px">{{ p.icon }}</td>
      <td>{{ p.name }}</td>
      <td><span style="display:inline-block;width:35px;height:22px;background:{{ p.color }};border-radius:4px"></span> {{ p.color }}</td>
      <td>{{ p.sort_order }}</td>
      <td>
        <form method="POST" style="display:inline">
          <input type="hidden" name="action" value="delete">
          <input type="hidden" name="id" value="{{ p.id }}">
          <button class="del-btn" onclick="return confirm('تأكيد الحذف؟')">🗑</button>
        </form>
      </td>
    </tr>
    {% endfor %}
  </table>
</div>
</body></html>
"""

ADMIN_COMBOS_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>الكومبوهات</title>
<style>""" + ADMIN_CSS + """</style></head>
<body>
""" + ADMIN_NAV + """
<h1>📂 إدارة الكومبوهات</h1>
{% with messages = get_flashed_messages(with_categories=true) %}{% for cat,msg in messages %}
<div class="flash {{ cat }}">{{ msg }}</div>{% endfor %}{% endwith %}
<div class="card">
  <h3>📤 رفع ملف كومبو (.txt)</h3>
  <p style="color:#9ca3af;margin-bottom:10px">الصيغة: <code>platform|country_name|country_code|flag|number</code></p>
  <form method="POST" enctype="multipart/form-data">
    <input type="hidden" name="action" value="upload_combo">
    <input type="file" name="file" accept=".txt" required>
    <button type="submit">رفع الملف</button>
  </form>
  <pre style="margin-top:15px">WhatsApp|اليمن|967|🇾🇪|+967700000001
Telegram|مصر|20|🇪🇬|+201000000002
Instagram|سعودية|966|🇸🇦|+966500000003</pre>
</div>
<div class="card">
  <h3>🌍 الدول الحالية ({{ countries|length }})</h3>
  <table>
    <tr><th>المنصة</th><th>الدولة</th><th>الكود</th><th>العلم</th><th>الأرقام</th><th>إجراءات</th></tr>
    {% for c in countries %}
    <tr>
      <td>{{ c.platform_name }}</td>
      <td>{{ c.name }}</td>
      <td>{{ c.code }}</td>
      <td style="font-size:22px">{{ c.flag or '🌍' }}</td>
      <td>{{ c.num_count }}</td>
      <td>
        <form method="POST" style="display:inline">
          <input type="hidden" name="action" value="delete_country">
          <input type="hidden" name="id" value="{{ c.id }}">
          <button class="del-btn" onclick="return confirm('سيتم حذف كل الأرقام!')">🗑</button>
        </form>
      </td>
    </tr>
    {% endfor %}
  </table>
</div>
</body></html>
"""

ADMIN_USERS_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>المستخدمون</title>
<style>""" + ADMIN_CSS + """</style></head>
<body>
""" + ADMIN_NAV + """
<h1>👥 المستخدمون وحظر IP</h1>
<div class="card">
  <h3>🚫 إضافة IP للقائمة السوداء</h3>
  <form method="POST" class="row">
    <input type="hidden" name="action" value="blacklist_ip">
    <input name="ip" placeholder="1.2.3.4" required>
    <input name="reason" placeholder="السبب" style="flex:1">
    <button type="submit">حظر</button>
  </form>
</div>
<div class="card">
  <h3>📋 القائمة السوداء</h3>
  <table>
    <tr><th>IP</th><th>السبب</th><th>التاريخ</th><th>إجراءات</th></tr>
    {% for b in blacklisted %}
    <tr>
      <td><code>{{ b.ip }}</code></td>
      <td>{{ b.reason }}</td>
      <td>{{ b.banned_at }}</td>
      <td>
        <form method="POST" style="display:inline">
          <input type="hidden" name="action" value="unblacklist_ip">
          <input type="hidden" name="ip" value="{{ b.ip }}">
          <button class="unban-btn">🔓 فك الحظر</button>
        </form>
      </td>
    </tr>
    {% else %}<tr><td colspan="4" style="text-align:center;color:#888">لا يوجد</td></tr>{% endfor %}
  </table>
</div>
<div class="card">
  <h3>👥 الزائرون</h3>
  <table>
    <tr><th>IP</th><th>آخر زيارة</th><th>الطلبات</th><th>الحالة</th><th>إجراءات</th></tr>
    {% for u in users %}
    <tr>
      <td><code>{{ u.ip }}</code></td>
      <td>{{ u.last_seen }}</td>
      <td>{{ u.requests_count }}</td>
      <td>{% if u.banned %}<span class="banned">محظور</span>{% else %}نشط{% endif %}</td>
      <td>
        <form method="POST" style="display:inline">
          <input type="hidden" name="id" value="{{ u.id }}">
          {% if u.banned %}
          <input type="hidden" name="action" value="unban">
          <button class="unban-btn">🔓 فك</button>
          {% else %}
          <input type="hidden" name="action" value="ban">
          <button class="ban-btn" onclick="return confirm('حظر هذا المستخدم؟')">🚫 حظر</button>
          {% endif %}
        </form>
      </td>
    </tr>
    {% endfor %}
  </table>
</div>
</body></html>
"""

ADMIN_LINKS_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>الروابط</title>
<style>""" + ADMIN_CSS + """</style></head>
<body>
""" + ADMIN_NAV + """
<h1>🔗 إدارة الروابط</h1>
<form method="POST" class="row">
  <input type="hidden" name="action" value="add">
  <input name="label" placeholder="اسم الرابط" required>
  <input name="url" placeholder="https://..." required style="flex:1">
  <input name="icon" placeholder="🔗" maxlength="4">
  <input type="number" name="sort_order" value="0" style="width:80px">
  <button type="submit">إضافة</button>
</form>
<table>
  <tr><th>الأيقونة</th><th>الاسم</th><th>الرابط</th><th>إجراءات</th></tr>
  {% for l in links %}
  <tr>
    <td style="font-size:24px">{{ l.icon }}</td>
    <td>{{ l.label }}</td>
    <td><a href="{{ l.url }}" style="color:#a78bfa" target="_blank">{{ l.url }}</a></td>
    <td>
      <form method="POST" style="display:inline">
        <input type="hidden" name="action" value="delete">
        <input type="hidden" name="id" value="{{ l.id }}">
        <button class="del-btn">🗑</button>
      </form>
    </td>
  </tr>
  {% endfor %}
</table>
</body></html>
"""

ADMIN_CODES_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>الأكواد</title>
<style>""" + ADMIN_CSS + """</style></head>
<body>
""" + ADMIN_NAV + """
<h1>🔑 إدارة الأكواد</h1>
<div class="card">
  <h3>🗑 مسح الأكواد</h3>
  <form method="POST" class="row">
    <select name="action">
      <option value="delete_filter">حذف أقدم من...</option>
      <option value="delete_all">حذف الكل</option>
    </select>
    <input type="number" name="days" value="7" min="1" style="width:80px"> يوم
    <button type="submit" onclick="return confirm('تأكيد؟')">تنفيذ</button>
  </form>
</div>
<div class="card">
  <h3>📜 آخر 200 كود</h3>
  <table>
    <tr><th>الوقت</th><th>المنصة</th><th>الدولة</th><th>الرقم</th><th>الكود</th><th>المصدر</th><th>حذف</th></tr>
    {% for c in codes %}
    <tr>
      <td>{{ c.received_at }}</td>
      <td>{{ c.platform }}</td>
      <td>{{ c.country }}</td>
      <td><code>{{ c.number }}</code></td>
      <td style="color:#a78bfa;font-weight:bold;font-size:16px">{{ c.code }}</td>
      <td style="font-size:10px">{{ c.source[:30] }}</td>
      <td>
        <form method="POST" style="display:inline">
          <input type="hidden" name="action" value="delete_id">
          <input type="hidden" name="id" value="{{ c.id }}">
          <button class="del-btn">🗑</button>
        </form>
      </td>
    </tr>
    {% endfor %}
  </table>
</div>
</body></html>
"""

ADMIN_AUDITS_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>السجلات</title>
<style>""" + ADMIN_CSS + """</style></head>
<body>
""" + ADMIN_NAV + """
<h1>📋 سجل حركات الأدمن</h1>
<table>
  <tr><th>الوقت</th><th>المستخدم</th><th>الحركة</th><th>التفاصيل</th><th>IP</th></tr>
  {% for a in audits %}
  <tr>
    <td>{{ a.created_at }}</td>
    <td><b style="color:#a78bfa">{{ a.admin_user }}</b></td>
    <td>{{ a.action }}</td>
    <td>{{ a.details }}</td>
    <td><code style="font-size:11px">{{ a.ip }}</code></td>
  </tr>
  {% else %}<tr><td colspan="5" style="text-align:center;color:#888;padding:30px">لا توجد حركات</td></tr>{% endfor %}
</table>
</body></html>
"""

ADMIN_CUSTOMIZE_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>تخصيص الموقع</title>
<style>""" + ADMIN_CSS + """</style></head>
<body>
""" + ADMIN_NAV + """
<h1>🎨 تخصيص الموقع الكامل</h1>
{% with messages = get_flashed_messages(with_categories=true) %}{% for cat,msg in messages %}
<div class="flash {{ cat }}">{{ msg }}</div>{% endfor %}{% endwith %}
<form method="POST">
<div class="section">
  <h3>🎛️ تشغيل / إيقاف الميزات</h3>
  <div class="toggle-row">
    <label>🌧️ مطر الأرقام خلف المنصات</label>
    <div class="switch {% if settings.digit_rain_enabled == '1' %}on{% endif %}" onclick="toggleSwitch(this)"></div>
    <input type="hidden" name="digit_rain_enabled" id="digit_rain_enabled" value="{{ settings.digit_rain_enabled }}">
  </div>
  <div class="toggle-row">
    <label>🌃 Matrix Rain</label>
    <div class="switch {% if settings.matrix_rain_enabled == '1' %}on{% endif %}" onclick="toggleSwitch(this)"></div>
    <input type="hidden" name="matrix_rain_enabled" id="matrix_rain_enabled" value="{{ settings.matrix_rain_enabled }}">
  </div>
  <div class="toggle-row">
    <label>🔊 صوت الإشعارات</label>
    <div class="switch {% if settings.sound_enabled == '1' %}on{% endif %}" onclick="toggleSwitch(this)"></div>
    <input type="hidden" name="sound_enabled" id="sound_enabled" value="{{ settings.sound_enabled }}">
  </div>
  <div class="toggle-row">
    <label>📬 إشعارات المتصفح</label>
    <div class="switch {% if settings.push_enabled == '1' %}on{% endif %}" onclick="toggleSwitch(this)"></div>
    <input type="hidden" name="push_enabled" id="push_enabled" value="{{ settings.push_enabled }}">
  </div>
</div>
<div class="section">
  <h3>🎨 ألوان العناصر</h3>
  <div class="color-row"><label>الخلفية الرئيسية</label><input type="color" name="bg_color" value="{{ settings.bg_color }}"></div>
  <div class="color-row"><label>اللون الرئيسي</label><input type="color" name="main_color" value="{{ settings.main_color }}"></div>
  <div class="color-row"><label>اللون الثانوي</label><input type="color" name="secondary_color" value="{{ settings.secondary_color }}"></div>
  <div class="color-row"><label>لون النص</label><input type="color" name="text_color" value="{{ settings.text_color }}"></div>
</div>
<div class="section">
  <h3>✏️ نصوص قابلة للتعديل</h3>
  <div class="text-row"><label>اسم الموقع</label><input name="site_name" value="{{ settings.site_name }}"></div>
  <div class="text-row"><label>شريط الإعلانات</label><input name="announcement" value="{{ settings.announcement }}"></div>
  <div class="text-row"><label>نص Marquee</label><input name="marquee_text" value="{{ settings.marquee_text }}"></div>
  <div class="text-row"><label>زر الاستلام الذكي</label><input name="smart_btn_text" value="{{ settings.smart_btn_text }}"></div>
  <div class="text-row"><label>وصف زر الاستلام</label><input name="smart_btn_subtext" value="{{ settings.smart_btn_subtext }}"></div>
  <div class="text-row"><label>نص الفوتر</label><input name="footer_text" value="{{ settings.footer_text }}"></div>
  <div class="text-row"><label>Placeholder البحث</label><input name="search_placeholder" value="{{ settings.search_placeholder }}"></div>
</div>
<button type="submit" style="width:100%;padding:18px;font-size:16px">💾 حفظ كل التغييرات</button>
</form>
<script>
function toggleSwitch(el) {
  el.classList.toggle('on');
  const inputs = el.parentElement.querySelectorAll('input[type=hidden]');
  inputs.forEach(input => {
    input.value = el.classList.contains('on') ? '1' : '0';
  });
}
</script>
</body></html>
"""

MAINTENANCE_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>صيانة</title>
<style>
body{margin:0;padding:0;height:100vh;display:flex;align-items:center;justify-content:center;
background:linear-gradient(135deg,#0f0f23,#1a1a35);color:#e0e0ff;font-family:Tahoma,Arial,sans-serif;text-align:center}
.box{padding:50px;border:2px solid #667eea;border-radius:20px;background:rgba(102,126,234,0.1);max-width:500px}
h1{color:#a78bfa;font-size:2.5em;margin-bottom:20px}
p{font-size:1.2em;line-height:1.6}
.icon{font-size:5em;margin-bottom:20px}
</style></head>
<body>
<div class="box">
  <div class="icon">🔧</div>
  <h1>الموقع تحت الصيانة</h1>
  <p>نعمل على تحسين الخدمة حالياً. سنعود قريباً إن شاء الله.</p>
  <p style="margin-top:20px;color:#a78bfa">📞 للدعم: 967733723953</p>
</div>
</body></html>
"""

# =========================================================================
# 10) Routes
# =========================================================================
@app.route("/")
def index():
    settings = get_settings()
    conn = db()
    platforms = conn.execute("SELECT * FROM platforms ORDER BY sort_order").fetchall()
    today = datetime.now().strftime("%Y-%m-%d")
    stats = {
        "today_numbers": conn.execute("SELECT COUNT(*) as c FROM numbers WHERE date(used_at)=?", (today,)).fetchone()["c"],
        "today_codes": conn.execute("SELECT COUNT(*) as c FROM codes WHERE date(received_at)=?", (today,)).fetchone()["c"],
        "total_visits": conn.execute("SELECT COALESCE(SUM(requests_count),0) as c FROM users").fetchone()["c"],
        "active_users": conn.execute("SELECT COUNT(*) as c FROM users WHERE last_seen > datetime('now','-1 hour')").fetchone()["c"],
    }
    conn.close()
    return render_template_string(INDEX_HTML, settings=settings, platforms=platforms, stats=stats)

@app.route("/maintenance")
def maintenance():
    return render_template_string(MAINTENANCE_HTML), 503

@app.route("/api/ui_settings")
def api_ui_settings():
    return jsonify({"ok": True, "settings": get_settings()})

@app.route("/api/links")
def api_links():
    conn = db()
    links = conn.execute("SELECT * FROM links ORDER BY sort_order").fetchall()
    conn.close()
    return jsonify({"links": [dict(l) for l in links]})

@app.route("/api/countries/<int:pid>")
def api_countries(pid):
    conn = db()
    countries = conn.execute("""
        SELECT c.*, COUNT(n.id) as available
        FROM countries c LEFT JOIN numbers n ON n.country_id = c.id AND n.status='available'
        WHERE c.platform_id=? GROUP BY c.id
    """, (pid,)).fetchall()
    conn.close()
    return jsonify({"countries": [dict(c) for c in countries]})

@app.route("/api/get_number", methods=["POST"])
def api_get_number():
    allowed, msg = security_check()
    if not allowed: return jsonify({"ok": False, "error": msg}), 429
    data = request.json
    country_id = data.get("country_id")
    if not country_id: return jsonify({"ok": False, "error": "الدولة مطلوبة"})
    conn = db()
    num = conn.execute("SELECT * FROM numbers WHERE country_id=? AND status='available' ORDER BY RANDOM() LIMIT 1").fetchone()
    if not num:
        conn.close()
        return jsonify({"ok": False, "error": "لا توجد أرقام متاحة"})
    conn.execute("UPDATE numbers SET status='in_use', used_by_ip=?, used_at=CURRENT_TIMESTAMP WHERE id=?", (client_ip(), num["id"]))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "number_id": num["id"], "number": num["number"], "expires_in": 120})

@app.route("/api/next_number", methods=["POST"])
def api_next_number():
    allowed, msg = security_check()
    if not allowed: return jsonify({"ok": False, "error": msg}), 429
    data = request.json
    country_id = data.get("country_id")
    conn = db()
    num = conn.execute("SELECT * FROM numbers WHERE country_id=? AND status='available' ORDER BY RANDOM() LIMIT 1").fetchone()
    if not num:
        conn.close()
        return jsonify({"ok": False, "error": "لا توجد أرقام متاحة"})
    conn.execute("UPDATE numbers SET status='in_use', used_by_ip=?, used_at=CURRENT_TIMESTAMP WHERE id=?", (client_ip(), num["id"]))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "number_id": num["id"], "number": num["number"], "expires_in": 120})

@app.route("/api/smart_pick", methods=["POST"])
def api_smart_pick():
    allowed, msg = security_check()
    if not allowed: return jsonify({"ok": False, "error": msg}), 429
    conn = db()
    num = conn.execute("SELECT * FROM numbers WHERE status='available' ORDER BY RANDOM() LIMIT 1").fetchone()
    if not num:
        conn.close()
        return jsonify({"ok": False, "error": "لا توجد أرقام متاحة"})
    country = conn.execute("SELECT c.*, p.name as platform, p.icon as icon, p.color as color FROM countries c JOIN platforms p ON c.platform_id = p.id WHERE c.id=?", (num["country_id"],)).fetchone()
    conn.execute("UPDATE numbers SET status='in_use', used_by_ip=?, used_at=CURRENT_TIMESTAMP WHERE id=?", (client_ip(), num["id"]))
    conn.commit()
    conn.close()
    code_row = None
    return jsonify({
        "ok": True, "number_id": num["id"], "number": num["number"],
        "platform": country["platform"] if country else "?",
        "country": country["name"] if country else "?",
        "code": code_row["code"] if code_row else None,
        "expires_in": 120
    })

@app.route("/api/check_code/<int:number_id>")
def api_check_code(number_id):
    conn = db()
    code = conn.execute("SELECT code FROM codes WHERE number_id=? ORDER BY received_at DESC LIMIT 1", (number_id,)).fetchone()
    conn.close()
    return jsonify({"code": code["code"] if code else None})

@app.route("/api/feed")
def api_feed():
    conn = db()
    feed = conn.execute("""
        SELECT c.code, n.number, p.name as platform, p.icon, p.color, co.name as country, co.flag, c.received_at
        FROM codes c
        JOIN numbers n ON c.number_id = n.id
        JOIN countries co ON n.country_id = co.id
        JOIN platforms p ON co.platform_id = p.id
        ORDER BY c.received_at DESC LIMIT 20
    """).fetchall()
    conn.close()
    return jsonify({"feed": [dict(f) for f in feed]})

@app.route("/api/search")
def api_search():
    q = request.args.get("q", "")
    conn = db()
    results = conn.execute("""
        SELECT n.number, p.name as platform, p.icon, p.color, co.name as country, co.flag
        FROM numbers n
        JOIN countries co ON n.country_id = co.id
        JOIN platforms p ON co.platform_id = p.id
        WHERE n.number LIKE ? OR co.name LIKE ? OR p.name LIKE ?
        LIMIT 10
    """, (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
    conn.close()
    return jsonify({"results": [dict(r) for r in results]})

@app.route("/api/help", methods=["POST"])
def api_help():
    data = request.json
    msg = data.get("message", "").strip()
    if not msg: return jsonify({"ok": False, "error": "الرسالة مطلوبة"})
    conn = db()
    conn.execute("INSERT INTO help_requests (user_id, message, source) VALUES (?, ?, ?)",
                 (client_ip(), msg, "website"))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "message": "✅ تم إرسال رسالتك!"})

# =========================================================================
# 11) Routes - الأدمن
# =========================================================================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        conn = db()
        admin = conn.execute("SELECT * FROM admins WHERE username=?", (username,)).fetchone()
        conn.close()
        if admin and bcrypt.checkpw(password.encode(), admin["password_hash"]):
            session["admin_user"] = admin["username"]
            session["admin_role"] = admin["role"]
            audit(username, "دخول الأدمن")
            return redirect("/admin")
        flash("بيانات الدخول غير صحيحة", "error")
    return render_template_string(ADMIN_LOGIN_HTML)

@app.route("/admin/logout")
def admin_logout():
    user = session.get("admin_user", "?")
    audit(user, "خروج من الأدمن")
    session.clear()
    return redirect("/admin/login")

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_user"):
            return redirect("/admin/login")
        return f(*args, **kwargs)
    return decorated

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
    audits = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()
    return render_template_string(ADMIN_DASHBOARD_HTML, stats=stats, audits=[dict(a) for a in audits],
                                  admin_user=session["admin_user"], role=session["admin_role"])

@app.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def admin_settings():
    if request.method == "POST":
        for key in ["site_name", "announcement", "marquee_text", "main_color", "secondary_color",
                    "bg_color", "text_color", "maintenance_mode", "rate_limit_per_minute", "footer_text"]:
            val = request.form.get(key, "")
            set_setting(key, val)
        audit(session["admin_user"], "تعديل الإعدادات")
        flash("✅ تم حفظ الإعدادات")
    settings = get_settings()
    return render_template_string(ADMIN_SETTINGS_HTML, settings=settings)

@app.route("/admin/customize", methods=["GET", "POST"])
@admin_required
def admin_customize():
    if request.method == "POST":
        for key in ["digit_rain_enabled", "matrix_rain_enabled", "sound_enabled", "push_enabled",
                    "bg_color", "main_color", "secondary_color", "text_color",
                    "site_name", "announcement", "marquee_text", "smart_btn_text",
                    "smart_btn_subtext", "footer_text", "search_placeholder"]:
            val = request.form.get(key, "0")
            set_setting(key, val)
        audit(session["admin_user"], "تخصيص الموقع")
        flash("✅ تم حفظ التخصيصات")
    settings = get_settings()
    return render_template_string(ADMIN_CUSTOMIZE_HTML, settings=settings)

@app.route("/admin/platforms", methods=["GET", "POST"])
@admin_required
def admin_platforms():
    conn = db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            conn.execute("INSERT INTO platforms (name, icon, color, sort_order) VALUES (?, ?, ?, ?)",
                        (request.form["name"], request.form.get("icon", "📱"),
                         request.form.get("color", "#667eea"), request.form.get("sort_order", 0)))
            conn.commit()
            audit(session["admin_user"], "إضافة منصة", request.form["name"])
            flash("✅ تمت إضافة المنصة")
        elif action == "delete":
            conn.execute("DELETE FROM platforms WHERE id=?", (request.form["id"],))
            conn.commit()
            audit(session["admin_user"], "حذف منصة", request.form["id"])
            flash("✅ تم الحذف")
    platforms = conn.execute("SELECT * FROM platforms ORDER BY sort_order").fetchall()
    conn.close()
    return render_template_string(ADMIN_PLATFORMS_HTML, platforms=[dict(p) for p in platforms])

@app.route("/admin/combos", methods=["GET", "POST"])
@admin_required
def admin_combos():
    conn = db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "upload_combo":
            file = request.files.get("file")
            if file:
                content = file.read().decode("utf-8")
                count = 0
                for line in content.strip().split("\n"):
                    parts = line.strip().split("|")
                    if len(parts) >= 5:
                        platform, country_name, code, flag, number = parts[0], parts[1], parts[2], parts[3], parts[4]
                        # Find or create platform
                        p = conn.execute("SELECT id FROM platforms WHERE LOWER(name)=LOWER(?)", (platform,)).fetchone()
                        if p:
                            # Find or create country
                            c = conn.execute("SELECT id FROM countries WHERE platform_id=? AND code=?",
                                           (p["id"], code)).fetchone()
                            if c:
                                conn.execute("INSERT INTO numbers (country_id, number, status) VALUES (?, ?, 'available')",
                                            (c["id"], number))
                            else:
                                conn.execute("INSERT INTO countries (platform_id, name, code, flag) VALUES (?, ?, ?, ?)",
                                            (p["id"], country_name, code, flag))
                                cid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                                conn.execute("INSERT INTO numbers (country_id, number, status) VALUES (?, ?, 'available')",
                                            (cid, number))
                            count += 1
                conn.commit()
                audit(session["admin_user"], "رفع كومبو", f"{count} رقم")
                flash(f"✅ تم إضافة {count} رقم")
        elif action == "delete_country":
            conn.execute("DELETE FROM countries WHERE id=?", (request.form["id"],))
            conn.commit()
            audit(session["admin_user"], "حذف دولة", request.form["id"])
            flash("✅ تم الحذف")
    countries = conn.execute("""
        SELECT c.*, p.name as platform_name, COUNT(n.id) as num_count
        FROM countries c
        JOIN platforms p ON c.platform_id = p.id
        LEFT JOIN numbers n ON n.country_id = c.id
        GROUP BY c.id
    """).fetchall()
    conn.close()
    return render_template_string(ADMIN_COMBOS_HTML, countries=[dict(c) for c in countries])

@app.route("/admin/users", methods=["GET", "POST"])
@admin_required
def admin_users():
    conn = db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "ban":
            conn.execute("UPDATE users SET banned=1 WHERE id=?", (request.form["id"],))
            conn.commit()
            audit(session["admin_user"], "حظر مستخدم", request.form["id"])
            flash("✅ تم الحظر")
        elif action == "unban":
            conn.execute("UPDATE users SET banned=0 WHERE id=?", (request.form["id"],))
            conn.commit()
            audit(session["admin_user"], "فك حظر", request.form["id"])
            flash("✅ تم فك الحظر")
        elif action == "blacklist_ip":
            conn.execute("INSERT OR REPLACE INTO ip_blacklist (ip, reason) VALUES (?, ?)",
                        (request.form["ip"], request.form.get("reason", "")))
            conn.commit()
            global blacklist_cache
            blacklist_cache = set()
            audit(session["admin_user"], "إضافة IP للقائمة السوداء", request.form["ip"])
            flash("✅ تم الحظر")
        elif action == "unblacklist_ip":
            conn.execute("DELETE FROM ip_blacklist WHERE ip=?", (request.form["ip"],))
            conn.commit()
            global blacklist_cache
            blacklist_cache = set()
            audit(session["admin_user"], "إزالة من القائمة السوداء", request.form["ip"])
            flash("✅ تم الإزالة")
    users = conn.execute("SELECT * FROM users ORDER BY id DESC LIMIT 100").fetchall()
    blacklisted = conn.execute("SELECT * FROM ip_blacklist ORDER BY id DESC").fetchall()
    conn.close()
    return render_template_string(ADMIN_USERS_HTML, users=[dict(u) for u in users],
                                 blacklisted=[dict(b) for b in blacklisted])

@app.route("/admin/links", methods=["GET", "POST"])
@admin_required
def admin_links():
    conn = db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            conn.execute("INSERT INTO links (label, url, icon, sort_order) VALUES (?, ?, ?, ?)",
                        (request.form["label"], request.form["url"],
                         request.form.get("icon", "🔗"), request.form.get("sort_order", 0)))
            conn.commit()
            audit(session["admin_user"], "إضافة رابط", request.form["label"])
            flash("✅ تمت إضافة الرابط")
        elif action == "delete":
            conn.execute("DELETE FROM links WHERE id=?", (request.form["id"],))
            conn.commit()
            audit(session["admin_user"], "حذف رابط", request.form["id"])
            flash("✅ تم الحذف")
    links = conn.execute("SELECT * FROM links ORDER BY sort_order").fetchall()
    conn.close()
    return render_template_string(ADMIN_LINKS_HTML, links=[dict(l) for l in links])

@app.route("/admin/codes", methods=["GET", "POST"])
@admin_required
def admin_codes():
    conn = db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "delete_all":
            conn.execute("DELETE FROM codes")
            conn.commit()
            audit(session["admin_user"], "حذف كل الأكواد", "ALL")
            flash("✅ تم حذف كل الأكواد")
        elif action == "delete_filter":
            days = int(request.form.get("days", 7))
            conn.execute("DELETE FROM codes WHERE received_at < datetime('now', ?)", (f"-{days} days",))
            conn.commit()
            audit(session["admin_user"], "حذف أكواد قديمة", f"{days} يوم")
            flash(f"✅ تم حذف الأكواد الأقدم من {days} يوم")
        elif action == "delete_id":
            conn.execute("DELETE FROM codes WHERE id=?", (request.form["id"],))
            conn.commit()
            audit(session["admin_user"], "حذف كود", request.form["id"])
            flash("✅ تم الحذف")
    codes = conn.execute("""
        SELECT c.*, n.number, p.name as platform, co.name as country
        FROM codes c
        JOIN numbers n ON c.number_id = n.id
        JOIN countries co ON n.country_id = co.id
        JOIN platforms p ON co.platform_id = p.id
        ORDER BY c.id DESC LIMIT 200
    """).fetchall()
    conn.close()
    return render_template_string(ADMIN_CODES_HTML, codes=[dict(c) for c in codes])

@app.route("/admin/audits")
@admin_required
def admin_audits():
    conn = db()
    audits = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 200").fetchall()
    conn.close()
    return render_template_string(ADMIN_AUDITS_HTML, audits=[dict(a) for a in audits])

@app.route("/admin/backup")
@admin_required
def admin_backup():
    conn = db()
    with open("backup_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".db", "wb") as f:
        f.write(conn.execute("SELECT * FROM sqlite_master").fetchone()["sql"].encode() if False else b"")
    # Export as JSON
    tables = ["platforms", "countries", "numbers", "codes", "users", "links", "settings"]
    data = {}
    for table in tables:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        data[table] = [dict(r) for r in rows]
    conn.close()
    return jsonify({"ok": True, "backup": data, "message": "تم إنشاء نسخة احتياطية"})

@app.route("/api/pull_code/<int:number_id>", methods=["POST"])
def api_pull_code(number_id):
    conn = db()
    conn.execute("INSERT INTO code_pulls (number_id, ip) VALUES (?, ?)", (number_id, client_ip()))
    code = conn.execute("SELECT code, received_at FROM codes WHERE number_id=? ORDER BY received_at DESC LIMIT 1",
                        (number_id,)).fetchone()
    conn.commit()
    conn.close()
    if code:
        return jsonify({"ok": True, "code": code["code"], "received_at": code["received_at"]})
    return jsonify({"ok": True, "code": None, "message": "لا يوجد كود بعد"})

# =========================================================================
# 12) تشغيل البوتات والتطبيق
# =========================================================================
if __name__ == "__main__":
    init_db()
    print("🚀 جاري تشغيل البوتات...")
    start_all_pollers()
    print("✅ تم تشغيل البوتات")
    print(f"🌐 الموقع: http://localhost:5000")
    print(f"🔐 الأدمن: http://localhost:5000/admin/login")
    print(f"   Username: {ADMIN_USER}")
    print(f"   Password: {ADMIN_PASS}")
    app.run(host="0.0.0.0", port=5000, debug=True)
