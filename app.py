from flask import Flask, request, render_template_string, jsonify, redirect, url_for, session, Response
import sqlite3
import json
import random
import os
import re
import requests
import threading
import time
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = "supersecretkey_change_this"
DB_PATH = "bot.db"

# ========== الإعدادات الأساسية ==========
ADMIN_PASSWORD = "admin123"

WHATSAPP_GROUP_LINK = "https://chat.whatsapp.com/IeK2gNS64fd8YSnenzt4WR"
OWNER_PHONE = "967733723953"
OWNER_LINK = f"https://wa.me/{OWNER_PHONE}"

TELEGRAM_BOT_TOKEN = "8814038881:AAGyuACUYA4YPKlJQhAyUMkpRNiV0u1gNuU"
CHANNEL_USERNAME = "@jsjsgsjsvh"
ASSISTANT_BOT_TOKEN = "8845420882:AAHZ-7qhCL3_ddDT3am4zWNtBRBy3mVDgws"
OWNER_TELEGRAM_ID = "@ABOD_90N"

# ========== قاعدة البيانات ==========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS combos (id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, country_code TEXT, country_name TEXT, country_flag TEXT, numbers TEXT, UNIQUE(platform, country_code))''')
    c.execute('''CREATE TABLE IF NOT EXISTS otp_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT, otp TEXT, timestamp TEXT, platform TEXT, country_code TEXT, country_flag TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS announcements (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, content TEXT, media_url TEXT, button_text TEXT, button_url TEXT, source_msg_id INTEGER, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS help_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, message TEXT, source TEXT, status TEXT DEFAULT 'pending', created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS admin_settings (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, username TEXT, first_name TEXT, last_name TEXT, country_code TEXT, assigned_number TEXT, is_banned INTEGER DEFAULT 0, join_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS site_texts (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS site_links (key TEXT PRIMARY KEY, value TEXT, icon TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS site_settings (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS visitors (id INTEGER PRIMARY KEY AUTOINCREMENT, ip TEXT, user_agent TEXT, visit_time TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS code_pulls (id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT, platform TEXT, pull_count INTEGER DEFAULT 1, last_pull_time TEXT)''')
    
    default_texts = {
        'site_title': '🚀 المطري OTP',
        'site_subtitle': '👑 أرقام واتساب سحب أكواد تطوير مطري 👑',
        'btn_get_number': '🚀 جلب رقم',
        'footer_text': '💎 صُنع بحب ⚡ بواسطة المطري',
        'ticker_text': '🚀 المطري OTP - أسرع موقع للحصول على الأكواد 💎',
    }
    for key, value in default_texts.items():
        c.execute("INSERT OR IGNORE INTO site_texts (key, value) VALUES (?, ?)", (key, value))
    
    default_links = [
        ('whatsapp_developer', OWNER_LINK, '💬'),
        ('whatsapp_group', WHATSAPP_GROUP_LINK, '👥'),
        ('telegram_channel', 'https://t.me/jsjsgsjsvh', '✈️'),
        ('instagram', 'https://instagram.com/', '📸'),
        ('tiktok', 'https://tiktok.com/', '🎵'),
        ('facebook', 'https://facebook.com/', '📘'),
    ]
    for key, value, icon in default_links:
        c.execute("INSERT OR IGNORE INTO site_links (key, value, icon) VALUES (?, ?, ?)", (key, value, icon))
    
    default_settings = {
        'main_color': '#00ffc8',
        'secondary_color': '#8b5cf6',
        'background_color': '#0a0e1a',
        'text_color': '#ffffff',
        'falling_numbers_enabled': '1',
        'matrix_enabled': '1',
        'ticker_enabled': '1',
        'sound_enabled': '0',
        'notification_enabled': '1',
        'push_enabled': '0',
        'digit_rain_enabled': '1',
    }
    for key, value in default_settings.items():
        c.execute("INSERT OR IGNORE INTO site_settings (key, value) VALUES (?, ?)", (key, value))
    
    conn.commit()
    conn.close()
init_db()

def get_text(key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM site_texts WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else ''

def get_all_links():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT key, value, icon FROM site_links")
    rows = c.fetchall()
    conn.close()
    return rows

def get_setting(key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM site_settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else ''

def set_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("REPLACE INTO site_settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def update_text(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("REPLACE INTO site_texts (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def update_link(key, value, icon=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if icon is not None:
        c.execute("REPLACE INTO site_links (key, value, icon) VALUES (?, ?, ?)", (key, value, icon))
    else:
        c.execute("UPDATE site_links SET value=? WHERE key=?", (value, key))
    conn.commit()
    conn.close()

def delete_link(key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM site_links WHERE key=?", (key,))
    conn.commit()
    conn.close()

def log_visitor(ip, user_agent):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO visitors (ip, user_agent, visit_time) VALUES (?, ?, ?)",
              (ip, user_agent, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_visitor_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM visitors")
    total = c.fetchone()[0]
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM visitors WHERE visit_time LIKE ?", (today + '%',))
    today_visitors = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT ip) FROM visitors")
    unique = c.fetchone()[0]
    conn.close()
    return total, today_visitors, unique

def log_code_pull(number, platform):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, pull_count FROM code_pulls WHERE number=? AND platform=?", (number, platform))
    row = c.fetchone()
    if row:
        c.execute("UPDATE code_pulls SET pull_count=pull_count+1, last_pull_time=? WHERE id=?", 
                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row[0]))
    else:
        c.execute("INSERT INTO code_pulls (number, platform, pull_count, last_pull_time) VALUES (?, ?, 1, ?)",
                  (number, platform, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_code_pull_count(number, platform):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT pull_count FROM code_pulls WHERE number=? AND platform=?", (number, platform))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def get_platforms():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT platform FROM combos")
    platforms = [row[0] for row in c.fetchall()]
    conn.close()
    return platforms

def get_countries_by_platform(platform):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT country_code, country_name, country_flag FROM combos WHERE platform=?", (platform,))
    countries = [{'code': row[0], 'name': row[1], 'flag': row[2]} for row in c.fetchall()]
    conn.close()
    return countries

def get_numbers(platform, country_code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT numbers FROM combos WHERE platform=? AND country_code=?", (platform, country_code))
    row = c.fetchone()
    conn.close()
    return json.loads(row[0]) if row else []

def save_combo(platform, country_code, country_name, country_flag, numbers):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("REPLACE INTO combos (platform, country_code, country_name, country_flag, numbers) VALUES (?, ?, ?, ?, ?)",
              (platform, country_code, country_name, country_flag, json.dumps(numbers)))
    conn.commit()
    conn.close()

def delete_combo(platform, country_code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM combos WHERE platform=? AND country_code=?", (platform, country_code))
    conn.commit()
    conn.close()

def get_all_combos():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT platform, country_code, country_name, country_flag FROM combos")
    rows = c.fetchall()
    conn.close()
    return rows

def get_admin_setting(key, default=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM admin_settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else default

def set_admin_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("REPLACE INTO admin_settings (key, value, updated_at) VALUES (?, ?, ?)",
              (key, value, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def notify_admin(text):
    admin_id = get_admin_setting('admin_telegram_id')
    if not admin_id:
        return False
    try:
        requests.post(f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/sendMessage",
                     json={'chat_id': admin_id, 'text': text, 'parse_mode': 'HTML'}, timeout=10)
        return True
    except:
        return False

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def track_visitor():
    if request.path == '/':
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown')
        ua = request.headers.get('User-Agent', 'unknown')
        try:
            log_visitor(ip, ua)
        except:
            pass

# ========== شعارات SVG ==========
PLATFORM_LOGOS = {
    "whatsapp": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%2325D366'/><path fill='%23fff' d='M50 18c-17.6 0-32 14.4-32 32 0 6 1.7 11.8 4.8 16.8L18 82l15.6-4.7C38.6 80.1 44.2 82 50 82c17.6 0 32-14.4 32-32S67.6 18 50 18zm18.6 45.6c-.8 2.2-4.6 4.2-6.4 4.5-1.6.3-3.7.4-5.9-.4-1.4-.5-3.1-1.1-5.4-2.2-9.5-4.1-15.7-13.7-16.2-14.3-.5-.7-3.9-5.1-3.9-9.7s2.4-6.9 3.3-7.9c.9-.9 1.9-1.2 2.6-1.2.6 0 1.2 0 1.7 0 .6 0 1.3-.2 2 .1 1.6.7 2.6 3 2.9 3.9.3.9.5 1.5 0 2.4-.4.9-1.5 2.4-2.2 3.4 0 0 .7.7 1.4 1.5 2.4 2.7 5.3 5.5 9.6 7.1 1.5.5 2.3.6 3-.4.6-1 2.5-3 3.2-4 .7-1 1.4-.8 2.3-.5.9.3 5.8 2.7 6.8 3.2 1 .5 1.6.7 1.8 1.1.2.5.2 2.5-.6 4.7z'/></svg>",
    "facebook": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%231877F2'/><path fill='%23fff' d='M58 84V52h10l1-12H58v-7c0-3 1-5 5-5h6V17h-9c-10 0-15 6-15 14v9H36v12h9v32h13z'/></svg>",
    "snapchat": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%23FFFC00'/><path fill='%23000' d='M50 16c-13 0-23 9-23 21 0 6 1 11 2 16-2 1-4 2-7 2-1 0-2 1-2 2 0 4 8 5 11 7 1 1 1 4 2 6 1 3 4 5 8 5 3 0 5-1 7-1 3 0 6 6 13 6 7 0 10-6 13-6 2 0 4 1 7 1 4 0 7-2 8-5 1-2 1-5 2-6 3-2 11-3 11-7 0-1-1-2-2-2-3 0-5-1-7-2 1-5 2-10 2-16 0-12-10-21-23-21-3 0-6 1-8 2-2-1-5-2-8-2z'/></svg>",
    "instagram": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><defs><radialGradient id='ig' cx='30%25' cy='30%25' r='80%25'><stop offset='0%25' stop-color='%23FEDA75'/><stop offset='50%25' stop-color='%23FA7E1E'/><stop offset='100%25' stop-color='%23D62976'/></radialGradient></defs><rect width='100' height='100' rx='22' fill='url(%23ig)'/><rect x='22' y='22' width='56' height='56' rx='14' fill='none' stroke='%23fff' stroke-width='5'/><circle cx='50' cy='50' r='13' fill='none' stroke='%23fff' stroke-width='5'/><circle cx='72' cy='28' r='4' fill='%23fff'/></svg>",
    "telegram": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%2326A5E4'/><path fill='%23fff' d='M22 50l50-22-7 48-18-8-7 12-3-17 31-26-37 24-9-4z'/></svg>",
    "tiktok": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%23000'/><path fill='%2325F4EE' d='M62 22c2 8 8 14 16 15v9c-6 0-12-2-16-5v22c0 12-9 20-20 20s-20-8-20-20 9-21 20-21v9c-6 0-11 5-11 12s5 12 11 12 12-6 12-12V22h8z'/><path fill='%23FE2C55' d='M70 22c2 8 8 14 16 15v9c-6 0-12-2-16-5v22c0 12-9 20-20 20v-9c6 0 12-6 12-12V22h8z'/></svg>",
    "google": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%23fff'/><path fill='%234285F4' d='M58 50c0-1-.1-2-.2-3H50v6h5.5c-.5 2-2 4-4.5 5l4 3c3-2 5-6 5-10 0-1 0-1-.5-1z'/><path fill='%2334A853' d='M40 56c1 4 4 7 9 7 3 0 5-1 7-3l-4-3c-1 1-2 1-4 1-3 0-5-2-6-4l-4 2z'/><path fill='%23FBBC04' d='M40 44l-4 2c-1 1-1 3-1 4s0 3 1 4l4-2c-.5-1-.5-2-.5-3s0-4 0-4z'/><path fill='%23EA4335' d='M50 36c3 0 5 1 6 2l-3 3c-1-1-2-1-4-1-5 0-9 4-9 4l-4-2c0-3 4-6 14-6z'/></svg>",
    "twitter": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%23000'/><path fill='%23fff' d='M70 35c-2 1-4 1-6 1 2-1 4-3 5-5-2 1-4 2-7 2-2-2-5-3-8-3-6 0-11 5-11 11 0 1 0 2 .3 3-9 0-17-5-22-12-1 2-1 4-1 6 0 4 2 7 5 9-2 0-4-1-5-2v.1c0 5 4 10 9 11-1 0-3 .5-4 .5-1 0-2 0-3-.1 2 4 6 7 11 7-4 3-9 5-15 5-1 0-2 0-3-.1 5 3 11 5 18 5 21 0 33-18 33-33v-1c2-2 4-3 6-6z'/></svg>",
}

platform_names = {
    'whatsapp': 'واتساب',
    'telegram': 'تيليجرام',
    'tiktok': 'تيك توك',
    'facebook': 'فيسبوك',
    'instagram': 'انستقرام',
    'snapchat': 'سناب شات',
    'google': 'جوجل',
    'twitter': 'تويتر/X'
}

platform_colors = {
    'whatsapp': '#25D366',
    'telegram': '#0088cc',
    'tiktok': '#FE2C55',
    'facebook': '#1877F2',
    'instagram': '#E4405F',
    'snapchat': '#FFFC00',
    'google': '#4285F4',
    'twitter': '#000000'
}

COUNTRY_DATA = {
    "966": {"n": "السعودية", "f": "🇸🇦"},
    "971": {"n": "الإمارات", "f": "🇦🇪"},
    "20": {"n": "مصر", "f": "🇪🇬"},
    "1": {"n": "أمريكا", "f": "🇺🇸"},
    "44": {"n": "بريطانيا", "f": "🇬🇧"},
    "90": {"n": "تركيا", "f": "🇹🇷"},
    "91": {"n": "الهند", "f": "🇮🇳"},
    "49": {"n": "ألمانيا", "f": "🇩🇪"},
    "33": {"n": "فرنسا", "f": "🇫🇷"},
    "34": {"n": "إسبانيا", "f": "🇪🇸"},
    "212": {"n": "المغرب", "f": "🇲🇦"},
    "213": {"n": "الجزائر", "f": "🇩🇿"},
    "216": {"n": "تونس", "f": "🇹🇳"},
    "218": {"n": "ليبيا", "f": "🇱🇾"},
    "92": {"n": "باكستان", "f": "🇵🇰"},
    "973": {"n": "البحرين", "f": "🇧🇭"},
    "974": {"n": "قطر", "f": "🇶🇦"},
    "968": {"n": "عمان", "f": "🇴🇲"},
    "965": {"n": "الكويت", "f": "🇰🇼"},
    "967": {"n": "اليمن", "f": "🇾🇪"},
    "962": {"n": "الأردن", "f": "🇯🇴"},
    "961": {"n": "لبنان", "f": "🇱🇧"},
    "963": {"n": "سوريا", "f": "🇸🇾"},
    "964": {"n": "العراق", "f": "🇮🇶"},
    "52": {"n": "المكسيك", "f": "🇲🇽"},
    "55": {"n": "البرازيل", "f": "🇧🇷"},
    "54": {"n": "الأرجنتين", "f": "🇦🇷"},
}

def get_country_info(code):
    info = COUNTRY_DATA.get(code)
    return (info["n"], info["f"]) if info else ("أخرى", "🌍")

# ========== HTML الرئيسي ==========
main_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>{{ site_title }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --main-color: {{ main_color }};
            --secondary-color: {{ secondary_color }};
            --bg-color: {{ background_color }};
            --text-color: {{ text_color }};
        }
        * { margin:0; padding:0; box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
        html, body { font-family:'Cairo',sans-serif; background:var(--bg-color); color:var(--text-color); overflow-x:hidden; }
        body { min-height:100vh; }
        
        /* Matrix Background */
        #matrix-bg {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            z-index: -999; opacity: 0.85; pointer-events: none;
        }

        /* Falling Numbers Animation */
        .falling-numbers {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            z-index: -998; pointer-events: none; overflow: hidden;
        }
        .falling-digit {
            position: absolute; font-family: 'Courier New', monospace;
            font-size: 18px; font-weight: bold; color: var(--main-color);
            opacity: 0.12; animation: fall linear infinite;
        }
        @keyframes fall {
            0% { transform: translateY(-30px) rotate(0deg); opacity: 0.4; }
            100% { transform: translateY(100vh) rotate(360deg); opacity: 0; }
        }

        .app { 
            max-width:500px; margin:0 auto; 
            background:rgba(13, 17, 23, 0.6); 
            backdrop-filter:blur(3px); 
            min-height:100vh; display:flex; flex-direction:column; 
            position:relative; z-index: 1;
        }

        .top-bar { 
            background:rgba(13, 17, 23, 0.95); 
            padding:14px 16px; 
            display:flex; align-items:center; justify-content:space-between; 
            border-bottom:1px solid rgba(48, 54, 61, 0.8); 
            position:sticky; top:0; z-index:50;
        }
        .brand { display:flex; align-items:center; gap:12px; }
        .brand-icon { 
            width:40px; height:40px; border-radius:12px; 
            background:linear-gradient(135deg, var(--main-color), var(--secondary-color)); 
            display:flex; align-items:center; justify-content:center; font-size:20px;
            animation: pulse-icon 2s ease-in-out infinite;
        }
        @keyframes pulse-icon {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        .brand-text { font-size:18px; font-weight:800; color:#fff; }
        
        .menu-btn { 
            background:transparent; border:2px solid #30363d; color:#8b949e; 
            padding:8px 14px; border-radius:10px; cursor:pointer; font-size:18px;
            transition: all 0.3s ease;
        }
        .menu-btn:hover { color:var(--main-color); border-color:var(--main-color); }

        .dropdown-menu { 
            position:fixed; top:0; right:-300px; width:280px; height:100vh;
            background:linear-gradient(180deg, #0d1117, #161b22);
            border-left:2px solid rgba(48, 54, 61, 0.8); 
            padding:20px 15px; z-index:10000; 
            box-shadow:-10px 0 40px rgba(0,0,0,0.8); 
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            overflow-y:auto; display:flex; flex-direction:column; gap:8px;
        }
        .dropdown-menu.show { right:0; }
        .menu-overlay {
            display:none; position:fixed; inset:0;
            background:rgba(0,0,0,0.7); backdrop-filter:blur(6px); z-index:9999;
        }
        .menu-overlay.show { display:block; }
        
        .dropdown-menu .menu-header-title {
            text-align:center; padding:10px 0 15px;
            border-bottom:1px solid rgba(48, 54, 61, 0.5); margin-bottom:10px;
        }
        .dropdown-menu .menu-header-title .icon { font-size:28px; animation: bounce 1s ease infinite; }
        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-5px); }
        }
        
        .dropdown-menu a { 
            display:flex; align-items:center; gap:12px; color:#c9d1d9; text-decoration:none; 
            padding:12px 16px; border-radius:10px; font-size:14px; font-weight:600; 
            transition:all 0.3s ease; border:1px solid transparent;
        }
        .dropdown-menu a:hover { 
            background:rgba(0, 255, 200, 0.1); color:var(--main-color); 
            border-color:rgba(0, 255, 200, 0.3); transform: translateX(-5px);
        }
        .dropdown-menu a .ico { 
            font-size:18px; width:28px; height:28px; 
            display:flex; align-items:center; justify-content:center; 
            background:rgba(48, 54, 61, 0.5); border-radius:8px; flex-shrink:0;
        }
        .dropdown-menu .menu-divider { 
            height:1px; background:linear-gradient(90deg, transparent, #30363d, transparent); 
            margin:8px 0;
        }
        .dropdown-menu .menu-section-title { 
            font-size:10px; color:#6e7681; font-weight:700; 
            padding:4px 12px 2px; text-transform:uppercase; letter-spacing:1px;
        }

        .main { padding:14px 16px; flex:1; }
        .hero { text-align:center; padding:6px 0 12px; }
        .hero h1 { font-size:22px; font-weight:800; color:#fff; }
        .hero p { font-size:13px; color:#8b949e; margin-top:4px; }

        .section-title { 
            font-size:14px; font-weight:700; color:#fff; margin:12px 0 8px; 
            display:flex; align-items:center; gap:8px;
        }
        .section-title .icon { color:var(--main-color); }

        .platforms { display:grid; grid-template-columns:repeat(2, 1fr); gap:10px; margin-bottom:6px; }
        
        .platform-btn {
            display:flex; align-items:center; gap:10px; padding:16px 14px;
            background:#1c2128; border:2px solid #30363d; border-radius:14px;
            color:#e6e6e6; cursor:pointer; transition:all 0.2s ease;
            font-size:14px; font-weight:700; font-family:'Cairo',sans-serif;
        }
        .platform-btn:hover { 
            background:#21262d; border-color:#484f58; transform: translateY(-2px);
            box-shadow:0 6px 20px rgba(0,0,0,0.3);
        }
        .platform-btn:active { transform:scale(0.97); }
        .platform-btn.active { 
            background:var(--platform-color, #1f6feb); border-color:var(--platform-color, #1f6feb); 
            color:#fff; box-shadow:0 0 0 3px var(--platform-color, #1f6feb), 0 0 25px rgba(31,111,235,0.4);
        }
        .platform-btn img { 
            width:38px; height:38px; object-fit:contain; 
            border-radius:10px; background:#fff; padding:4px; flex-shrink:0;
        }

        .form-control {
            width:100%; padding:14px 16px; border-radius:12px;
            border:2px solid #30363d; background:#0d1117; color:#e6e6e6;
            outline:none; font-family:'Cairo',sans-serif; font-size:14px; font-weight:600;
            appearance:none; -webkit-appearance:none;
            background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 12 12'><path fill='%238b949e' d='M6 9L1 4h10z'/></svg>");
            background-repeat:no-repeat; background-position:left 16px center; padding-left:44px;
        }
        .form-control:focus { border-color:var(--main-color); }
        .form-control:disabled { opacity:0.5; cursor:not-allowed; }

        .btn-primary {
            width:100%; padding:16px; border:none; border-radius:14px;
            background:linear-gradient(135deg, #238636, #2ea043); color:#fff; 
            font-size:16px; font-weight:800; cursor:pointer; margin-top:10px; 
            font-family:'Cairo',sans-serif; transition:all 0.2s ease;
            box-shadow:0 6px 20px rgba(35,134,54,0.4);
        }
        .btn-primary:hover:not(:disabled) { 
            background:linear-gradient(135deg, #2ea043, #3fb950); 
            transform: translateY(-2px); box-shadow:0 8px 25px rgba(35,134,54,0.5);
        }
        .btn-primary:disabled { opacity:0.5; cursor:not-allowed; }

        .number-card {
            background:linear-gradient(135deg, #0d1117, #161b22);
            border:2px solid #238636; border-radius:16px;
            padding:18px; margin:12px 0; text-align:center;
        }
        .number-card .number {
            font-family: 'Courier New', monospace; font-size:28px; font-weight:900;
            color: #3fb950; letter-spacing:3px;
            text-shadow: 0 0 15px rgba(63, 185, 80, 0.6);
            padding:8px 0; direction:ltr; unicode-bidi: bidi-override; display:inline-block;
        }
        .number-card .number .digit {
            display:inline-block; opacity:0; transform:translateY(10px) scale(0.7);
            animation:digitDrop 0.3s ease forwards;
        }
        @keyframes digitDrop { to { opacity:1; transform:translateY(0) scale(1); } }
        
        .code-timer {
            display:inline-flex; align-items:center; gap:6px; padding:6px 14px;
            background:rgba(139, 92, 246, 0.15); border:1px solid rgba(139, 92, 246, 0.4);
            border-radius:999px; font-size:11px; font-weight:700; color:#c4b5fd; margin-top:8px;
        }
        
        .copy-btn-mini {
            background:linear-gradient(135deg, #1f6feb, #388bfd); border:1px solid #388bfd;
            color:#fff; padding:6px 14px; border-radius:10px; cursor:pointer;
            font-size:12px; font-weight:700; transition:all 0.2s;
        }
        .copy-btn-mini:hover { background:linear-gradient(135deg, #388bfd, #58a6ff); }
        .copy-btn-mini.copied { background:linear-gradient(135deg, #238636, #2ea043); border-color:#2ea043; }

        .otp-list { display:flex; flex-direction:column; gap:8px; margin-top:10px; }
        .otp-item {
            background:#1c2128; border:1px solid #30363d; border-radius:12px;
            padding:12px 14px; display:flex; justify-content:space-between; align-items:center;
        }
        .otp-item .otp-code {
            font-family:'Courier New', monospace; font-size:16px; font-weight:900;
            background:linear-gradient(135deg, #ff6b9d 0%, #c084fc 50%, #38bdf8 100%);
            -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
            letter-spacing:2px;
        }
        .otp-item .otp-info { font-size:11px; color:#8b949e; }
        .otp-item .otp-time { font-size:10px; color:#8b949e; margin-top:3px; }
        .otp-item .copy-btn { 
            background:transparent; border:1px solid #30363d; color:var(--main-color); 
            padding:5px 12px; border-radius:8px; cursor:pointer; font-size:12px; font-weight:600;
        }
        .otp-item .copy-btn:hover { background:var(--main-color); color:#000; }

        .empty-state { text-align:center; padding:24px; color:#8b949e; font-size:13px; }
        .empty-state .icon { font-size:36px; margin-bottom:8px; opacity:0.5; animation:pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity:0.5; } 50% { opacity:0.8; } }

        .status { 
            background:#1c2128; border:1px solid #30363d; border-radius:12px; 
            padding:12px 16px; text-align:center; margin-top:10px; color:#8b949e; 
            font-size:13px; font-weight:600;
        }

        .footer-section { margin-top:12px; padding:0; border-top:1px solid #21262d; }
        .footer-info { text-align:center; padding:12px 16px; color:#8b949e; font-size:12px; font-weight:600; }
        .footer-info strong { color:var(--main-color); }
        
        .news-ticker {
            background:linear-gradient(135deg, #1c2128 0%, #21262d 50%, #1c2128 100%);
            border:1px solid #30363d; padding:8px 0; overflow:hidden; position:relative;
            direction:ltr; border-radius:10px; margin:0 16px 6px 16px; max-width:calc(100% - 32px);
        }
        .news-ticker::before, .news-ticker::after {
            content:''; position:absolute; top:0; bottom:0; width:30px; z-index:2; pointer-events:none;
        }
        .news-ticker::before { left:0; background:linear-gradient(90deg, #1c2128, transparent); border-radius:10px 0 0 10px; }
        .news-ticker::after { right:0; background:linear-gradient(-90deg, #1c2128, transparent); border-radius:0 10px 10px 0; }
        .ticker-content {
            display:flex; gap:50px; padding:0 25px; white-space:nowrap;
            animation:tickerScroll 35s linear infinite;
            font-weight:600; font-size:12px; color:#c9d1d9; align-items:center;
        }
        .ticker-content:hover { animation-play-state:paused; }
        @keyframes tickerScroll { 0% { transform:translateX(0); } 100% { transform:translateX(-50%); } }
        .ticker-name {
            background:linear-gradient(90deg, var(--main-color), var(--secondary-color), #f78166, var(--main-color));
            background-size:300% 300%; -webkit-background-clip:text; background-clip:text;
            -webkit-text-fill-color:transparent; animation:nameScroll 4s ease infinite;
            display:inline-block; font-weight:800;
        }
        @keyframes nameScroll { 0%,100% { background-position:0% 50%; } 50% { background-position:100% 50%; } }

        .modal-overlay {
            display:none; position:fixed; inset:0;
            background:rgba(0,0,0,0.8); backdrop-filter:blur(10px); z-index:10000;
            align-items:center; justify-content:center; padding:20px;
        }
        .modal-overlay.show { display:flex; }
        .modal-box {
            background:linear-gradient(180deg, #1c2128, #161b22);
            border:1px solid #30363d; border-radius:18px; padding:28px;
            max-width:420px; width:100%;
        }
        .modal-box h2 { color:#fff; font-size:20px; margin-bottom:8px; text-align:center; }
        .modal-box p { color:#8b949e; font-size:14px; text-align:center; margin-bottom:14px; }
        .modal-box textarea {
            width:100%; min-height:100px; background:#0d1117; color:#e6e6e6;
            border:1px solid #30363d; border-radius:12px; padding:14px;
            font-family:'Cairo',sans-serif; font-size:14px; resize:vertical; outline:none;
        }
        .modal-box textarea:focus { border-color:var(--main-color); }
        .modal-box .modal-actions { display:flex; gap:10px; margin-top:16px; }
        .modal-box button {
            flex:1; padding:14px; border:none; border-radius:12px;
            font-family:'Cairo',sans-serif; font-size:14px; font-weight:700; cursor:pointer;
        }
        .modal-box .btn-send { background:linear-gradient(135deg, #238636, #2ea043); color:#fff; }
        .modal-box .btn-cancel { background:#30363d; color:#e6e6e6; }
        .modal-box .success-msg {
            background:rgba(35, 134, 54, 0.15); border:1px solid #238636; color:#3fb950;
            padding:14px; border-radius:12px; text-align:center; font-size:14px; margin-top:10px; display:none;
        }

        /* Toast */
        #toast-notification {
            position:fixed; top:-80px; left:50%; transform:translateX(-50%);
            background:linear-gradient(135deg, #238636, #2ea043); color:#fff;
            padding:14px 28px; border-radius:14px; font-weight:700; font-size:15px;
            z-index:100000; box-shadow:0 10px 40px rgba(35,134,54,0.6);
            transition:top 0.5s cubic-bezier(0.4, 0, 0.2, 1);
            display:flex; align-items:center; gap:10px; max-width:90%;
        }
        #toast-notification.show { top:20px; }

        @media (max-width:400px) {
            .hero h1 { font-size:19px; }
            .platform-btn { font-size:13px; padding:14px 12px; }
            .platform-btn img { width:32px; height:32px; }
            .number-card .number { font-size:24px; }
        }
    </style>
</head>
<body>
    <canvas id="matrix-bg"></canvas>
    <div class="falling-numbers" id="fallingNumbers"></div>
    <div id="toast-notification"><span>🔔</span><span id="toast-text">تم استلام كود جديد!</span></div>

    <div class="app">
        <div class="top-bar">
            <div class="brand">
                <div class="brand-icon">🚀</div>
                <div class="brand-text">{{ site_title }}</div>
            </div>
            <div class="top-actions">
                <button class="menu-btn" onclick="toggleMenu()">☰</button>
            </div>
        </div>

        <div class="menu-overlay" id="menuOverlay" onclick="toggleMenu()"></div>
        <div class="dropdown-menu" id="contactMenu">
            <div class="menu-header-title">
                <div class="icon">🚀</div>
                <div style="font-weight:900; color:#fff; font-size:18px; margin-top:6px;">المطري OTP</div>
            </div>
            
            <div class="menu-section-title">📞 تواصل معنا</div>
            {% for key, value, icon in links %}
            <a href="{{ value }}" target="_blank">
                <span class="ico">{{ icon }}</span>
                {{ key.replace('_', ' ').title() }}
            </a>
            {% endfor %}
            
            <div class="menu-divider"></div>
            
            <a href="/announcements"><span class="ico">📢</span> إعلانات الموقع</a>
            <a href="#" onclick="openHelpModal(); return false;"><span class="ico">🆘</span> طلب مساعدة</a>
            
            <div class="menu-divider"></div>
            <a href="/admin"><span class="ico">⚙️</span> لوحة التحكم</a>
        </div>

        <div class="main">
            <div class="hero">
                <h1>{{ site_title }}</h1>
                <p>{{ site_subtitle }}</p>
            </div>

            <div class="section-title"><span class="icon">🎯</span> اختر المنصة</div>
            <div class="platforms" id="platformSelector"></div>

            <div class="section-title"><span class="icon">🌍</span> اختر الدولة</div>
            <select id="country" class="form-control" disabled>
                <option value="">-- اختر المنصة أولاً --</option>
            </select>

            <button class="btn-primary" id="getNumberBtn" onclick="getNumber()" disabled>{{ btn_get_number }}</button>

            <div id="numberContainer" style="display:none;">
                <div class="number-card">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <span style="font-size:11px; color:#8b949e; font-weight:600;">📞 الرقم</span>
                        <button class="copy-btn-mini" onclick="copyNumber()" id="copyNumBtn">📋 نسخ</button>
                    </div>
                    <div class="number" id="numberDisplay">+</div>
                    <div id="pullCount" style="font-size:11px; color:#8b949e; margin-top:6px;"></div>
                    <div class="code-timer" id="codeTimer">
                        <span>⏱️</span>
                        <span>جاري السحب...</span>
                    </div>
                    <div style="margin-top:10px;">
                        <button onclick="refreshNumber()" style="
                            background:#30363d; border:1px solid #484f58; color:#fff;
                            padding:10px 16px; border-radius:10px; cursor:pointer;
                            font-size:13px; font-weight:600; width:100%;
                        ">🔄 تبديل الرقم</button>
                    </div>
                </div>
            </div>

            <div class="section-title" style="margin-top:16px;"><span class="icon">📜</span> الأكواد المسحوبة</div>
            <div class="otp-list" id="otpHistory">
                <div class="empty-state"><div class="icon">⏳</div><div>في انتظار الأكواد...</div></div>
            </div>

            <div class="status" id="status">⚡ اختر المنصة والدولة للبدء</div>
        </div>

        <div class="footer-section">
            <div class="news-ticker" id="tickerContainer">
                <div class="ticker-content" id="tickerContent">{{ ticker_text }} • {{ ticker_text }}</div>
            </div>
            <div class="footer-info">{{ footer_text }}</div>
        </div>
    </div>

    <div class="modal-overlay" id="helpModal" onclick="if(event.target===this) closeHelpModal()">
        <div class="modal-box">
            <h2>🆘 طلب مساعدة</h2>
            <p>اشرح مشكلتك وسنرد عليك بأسرع وقت</p>
            <textarea id="helpMessage" placeholder="اكتب رسالتك هنا..."></textarea>
            <div class="modal-actions">
                <button class="btn-cancel" onclick="closeHelpModal()">إلغاء</button>
                <button class="btn-send" id="sendHelpBtn" onclick="sendHelpRequest()">إرسال</button>
            </div>
            <div class="success-msg" id="helpSuccess">✅ تم إرسال رسالتك!</div>
        </div>
    </div>

    <script>
        const platformLogos = {{ platform_logos | tojson }};
        const platformNames = {{ platform_names | tojson }};
        const platformColors = {{ platform_colors | tojson }};
        let fallingEnabled = {{ falling_enabled }};

        function toggleMenu() {
            document.getElementById('contactMenu').classList.toggle('show');
            document.getElementById('menuOverlay').classList.toggle('show');
            document.body.style.overflow = document.getElementById('contactMenu').classList.contains('show') ? 'hidden' : '';
        }

        function openHelpModal() {
            toggleMenu();
            setTimeout(() => {
                document.getElementById('helpModal').style.display = 'flex';
                document.getElementById('helpMessage').value = '';
                document.getElementById('helpSuccess').style.display = 'none';
            }, 300);
        }
        function closeHelpModal() { document.getElementById('helpModal').style.display = 'none'; }

        async function sendHelpRequest() {
            const msg = document.getElementById('helpMessage').value.trim();
            if (!msg) { alert('الرجاء كتابة رسالتك'); return; }
            const btn = document.getElementById('sendHelpBtn');
            btn.disabled = true; btn.textContent = '⏳ جاري الإرسال...';
            try {
                const res = await fetch('/api/help', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:msg})});
                const data = await res.json();
                if (data.ok) {
                    document.getElementById('helpSuccess').style.display = 'block';
                    document.getElementById('helpMessage').value = '';
                    setTimeout(() => closeHelpModal(), 2000);
                }
            } catch(e) { alert('❌ فشل الاتصال'); }
            btn.disabled = false; btn.textContent = 'إرسال';
        }

        async function copyNumber() {
            const num = document.getElementById('numberDisplay').textContent;
            try { await navigator.clipboard.writeText(num); } catch(e) {}
            const btn = document.getElementById('copyNumBtn');
            btn.classList.add('copied');
            btn.textContent = '✅ تم';
            setTimeout(() => { btn.classList.remove('copied'); btn.textContent = '📋 نسخ'; }, 1800);
        }

        function copyText(text, btn) {
            navigator.clipboard.writeText(text);
            if (btn) {
                const orig = btn.textContent;
                btn.textContent = '✅';
                setTimeout(() => btn.textContent = orig, 1200);
            }
        }

        function animateNumber(element, text) {
            element.innerHTML = '';
            const chars = text.split('');
            chars.forEach((ch, i) => {
                const span = document.createElement('span');
                span.className = 'digit';
                span.textContent = ch;
                span.style.animationDelay = (i * 0.05) + 's';
                element.appendChild(span);
            });
        }

        // Matrix Background
        function initMatrix() {
            const canvas = document.getElementById('matrix-bg');
            const ctx = canvas.getContext('2d');
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
            const digits = "0123456789+()#-*$!%&";
            const fontSize = 14;
            const columns = Math.floor(canvas.width / fontSize);
            const drops = [];
            for (let i = 0; i < columns; i++) drops[i] = Math.random() * -100;
            function draw() {
                ctx.fillStyle = "rgba(7, 9, 13, 0.08)";
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.font = "bold " + fontSize + "px monospace";
                for (let i = 0; i < drops.length; i++) {
                    const text = digits.charAt(Math.floor(Math.random() * digits.length));
                    ctx.shadowBlur = 12;
                    ctx.shadowColor = "#00ffc8";
                    ctx.fillStyle = Math.random() > 0.92 ? "#ffffff" : "#00ffc8";
                    ctx.fillText(text, i * fontSize, drops[i] * fontSize);
                    ctx.shadowBlur = 0;
                    if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0;
                    drops[i] += 0.8;
                }
            }
            setInterval(draw, 50);
            window.addEventListener('resize', () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight; });
        }
        initMatrix();

        // Falling Numbers
        function initFallingNumbers() {
            const container = document.getElementById('fallingNumbers');
            if (!fallingEnabled) { container.innerHTML = ''; return; }
            container.innerHTML = '';
            for (let i = 0; i < 20; i++) {
                const digit = document.createElement('div');
                digit.className = 'falling-digit';
                digit.textContent = Math.floor(Math.random() * 10);
                digit.style.left = Math.random() * 100 + '%';
                digit.style.animationDuration = (Math.random() * 10 + 10) + 's';
                digit.style.animationDelay = Math.random() * 10 + 's';
                container.appendChild(digit);
            }
        }
        initFallingNumbers();

        let currentPlatform = '';
        let currentNumber = '';
        let currentNumberIndex = 0;
        let monitorInterval = null;
        let allOtpsCache = [];

        function initPlatformSelector() {
            const selector = document.getElementById('platformSelector');
            selector.innerHTML = '';
            Object.keys(platformNames).forEach(platform => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'platform-btn';
                btn.onclick = () => selectPlatform(platform, btn);
                btn.style.setProperty('--platform-color', platformColors[platform] || '#1f6feb');
                btn.innerHTML = '<img src="' + platformLogos[platform] + '" alt="' + platformNames[platform] + '"><span>' + platformNames[platform] + '</span>';
                selector.appendChild(btn);
            });
        }

        function selectPlatform(platform, btn) {
            currentPlatform = platform;
            document.querySelectorAll('.platform-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadCountries();
        }

        async function loadCountries() {
            const countrySelect = document.getElementById('country');
            if (!currentPlatform) {
                countrySelect.innerHTML = '<option value="">-- اختر المنصة أولاً --</option>';
                countrySelect.disabled = true;
                document.getElementById('numberContainer').style.display = 'none';
                document.getElementById('getNumberBtn').disabled = true;
                return;
            }
            countrySelect.disabled = true;
            countrySelect.innerHTML = '<option value="">جاري التحميل...</option>';
            const res = await fetch('/api/countries', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({platform:currentPlatform})});
            const data = await res.json();
            let options = '<option value="">-- اختر الدولة --</option>';
            data.forEach(c => { options += '<option value="' + c.code + '">' + c.flag + ' ' + c.name + '</option>'; });
            countrySelect.innerHTML = options;
            countrySelect.disabled = false;
        }

        document.getElementById('country').addEventListener('change', function() {
            document.getElementById('getNumberBtn').disabled = !this.value;
        });

        async function getNumber() {
            const country = document.getElementById('country').value;
            if (!currentPlatform || !country) return;
            currentNumberIndex = 0;
            document.getElementById('status').textContent = '⏳ جاري جلب رقم...';
            const res = await fetch('/api/get_number', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({platform:currentPlatform, country, index: currentNumberIndex})});
            const data = await res.json();
            if (data.number) {
                currentNumber = data.number;
                animateNumber(document.getElementById('numberDisplay'), data.number);
                document.getElementById('numberContainer').style.display = 'block';
                document.getElementById('status').textContent = '✅ الرقم جاهز!';
                startMonitoring();
            } else {
                document.getElementById('status').textContent = '❌ لا توجد أرقام متاحة';
            }
        }

        async function refreshNumber() {
            const country = document.getElementById('country').value;
            if (!currentPlatform || !country) return;
            stopMonitoring();
            currentNumberIndex++;
            try {
                const res = await fetch('/api/get_number', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({platform:currentPlatform, country, index: currentNumberIndex})});
                const data = await res.json();
                if (data.number) {
                    currentNumber = data.number;
                    animateNumber(document.getElementById('numberDisplay'), data.number);
                    document.getElementById('status').textContent = '🔄 تم التبديل!';
                } else {
                    currentNumberIndex = 0;
                    const resRetry = await fetch('/api/get_number', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({platform:currentPlatform, country, index: 0})});
                    const dataRetry = await resRetry.json();
                    if (dataRetry.number) {
                        currentNumber = dataRetry.number;
                        animateNumber(document.getElementById('numberDisplay'), dataRetry.number);
                        document.getElementById('status').textContent = '🔄 العودة للأول';
                    }
                }
                startMonitoring();
            } catch(e) {
                document.getElementById('status').textContent = '❌ فشل التبديل';
            }
        }

        function startMonitoring() {
            if (!currentNumber) return;
            if (monitorInterval) clearInterval(monitorInterval);
            let lastSeenOtpTime = '';
            monitorInterval = setInterval(() => {
                if (!currentNumber) { stopMonitoring(); return; }
                fetch('/api/get_otp', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({number:currentNumber})})
                .then(res => res.json()).then(data => {
                    if (data.otp && data.otp !== lastSeenOtpTime) {
                        lastSeenOtpTime = data.otp;
                        const now = new Date().toLocaleString('en-US', {timeZone:'Asia/Aden', hour12:true});
                        addOtpToHistory(currentNumber, data.otp, now, currentPlatform);
                        showToast('🔔 تم استلام كود: ' + data.otp);
                        document.getElementById('status').innerHTML = '✅ <b>تم استلام كود!</b>';
                    }
                }).catch(()=>{});
            }, 3000);
        }

        function stopMonitoring() {
            if (monitorInterval) { clearInterval(monitorInterval); monitorInterval = null; }
        }

        function showToast(text) {
            const toast = document.getElementById('toast-notification');
            document.getElementById('toast-text').textContent = text;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 4000);
        }

        function addOtpToHistory(number, otp, timestamp, platform) {
            const container = document.getElementById('otpHistory');
            if (container.querySelector('.empty-state')) container.innerHTML = '';
            const otpData = {id: Date.now(), number, otp, timestamp, platform: platform || currentPlatform || 'unknown'};
            allOtpsCache.unshift(otpData);
            try { localStorage.setItem('allOtps', JSON.stringify(allOtpsCache.slice(0, 30))); } catch(e) {}
            renderOtpSections();
        }

        function renderOtpSections() {
            const container = document.getElementById('otpHistory');
            if (!allOtpsCache.length) {
                container.innerHTML = '<div class="empty-state"><div class="icon">⏳</div><div>في انتظار الأكواد...</div></div>';
                return;
            }
            container.innerHTML = allOtpsCache.map(o => {
                const logoUrl = platformLogos[o.platform] || '';
                const name = platformNames[o.platform] || o.platform;
                return '<div class="otp-item">' +
                    '<div><div class="otp-code">🔑 ' + o.otp + '</div><div class="otp-info">📞 ' + o.number + '</div><div class="otp-time">🕒 ' + o.timestamp + '</div></div>' +
                    '<button class="copy-btn" onclick="copyText(\'' + o.otp + '\', this)">نسخ</button>' +
                '</div>';
            }).join('');
        }

        function loadCachedOtps() {
            try {
                const cached = localStorage.getItem('allOtps');
                if (cached) {
                    allOtpsCache = JSON.parse(cached);
                    if (allOtpsCache.length) renderOtpSections();
                }
            } catch(e) {}
        }

        document.addEventListener('DOMContentLoaded', () => {
            initPlatformSelector();
            loadCachedOtps();
        });
    </script>
</body>
</html>
"""

# ========== Routes ==========
@app.route('/')
def home():
    site_title = get_text('site_title') or '🚀 المطري OTP'
    site_subtitle = get_text('site_subtitle') or '👑 أرقام واتساب سحب أكواد 👑'
    btn_get_number = get_text('btn_get_number') or '🚀 جلب رقم'
    footer_text = get_text('footer_text') or '💎 صُنع بحب'
    ticker_text = get_text('ticker_text') or '🚀 المطري OTP'
    
    links = get_all_links()
    platforms = get_platforms() or list(platform_names.keys())
    main_color = get_setting('main_color') or '#00ffc8'
    secondary_color = get_setting('secondary_color') or '#8b5cf6'
    background_color = get_setting('background_color') or '#0a0e1a'
    text_color = get_setting('text_color') or '#ffffff'
    falling_enabled = '1' if get_setting('falling_numbers_enabled') == '1' else '0'
    
    return render_template_string(main_html,
        site_title=site_title, site_subtitle=site_subtitle,
        btn_get_number=btn_get_number, footer_text=footer_text,
        ticker_text=ticker_text, links=links, platforms=platforms,
        platform_logos=PLATFORM_LOGOS, platform_names=platform_names,
        platform_colors=platform_colors,
        main_color=main_color, secondary_color=secondary_color,
        background_color=background_color, text_color=text_color,
        falling_enabled=falling_enabled
    )

@app.route('/announcements')
def announcements_page():
    return '''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>إعلانات الموقع</title>
        <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
        <style>
            * { margin:0; padding:0; box-sizing:border-box; }
            body { font-family:Cairo,sans-serif; background:#07090d; color:#c9d1d9; min-height:100vh; }
            .container { max-width:480px; margin:0 auto; padding:16px; }
            .header { background:linear-gradient(135deg, #00ffc8, #8b5cf6); padding:20px; border-radius:14px; margin-bottom:16px; text-align:center; }
            .header h1 { color:#fff; font-size:22px; font-weight:900; }
            .header p { color:rgba(255,255,255,0.85); font-size:13px; }
            .ann-card { background:#1c2128; border:1px solid #30363d; border-radius:12px; padding:14px; margin-bottom:10px; }
            .ann-content { color:#e6e6e6; font-size:14px; line-height:1.6; }
            .ann-time { color:#6e7681; font-size:11px; margin-top:8px; }
            .empty { text-align:center; padding:30px; color:#6e7681; }
            .back-btn { display:inline-block; padding:10px 18px; background:#30363d; color:#fff; text-decoration:none; border-radius:10px; font-weight:700; font-size:13px; margin-bottom:12px; }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/" class="back-btn">🔙 العودة</a>
            <div class="header"><h1>📢 إعلانات الموقع</h1><p>آخر الإعلانات والتحديثات</p></div>
            <div id="annList"><div class="empty">⏳ جاري التحميل...</div></div>
        </div>
        <script>
            fetch('/api/announcements').then(r=>r.json()).then(data=>{
                const c=document.getElementById('annList');
                if(!data.length){c.innerHTML='<div class=empty>📭 لا توجد إعلانات</div>';return;}
                c.innerHTML=data.map(a=>'<div class=ann-card><div class=ann-content>'+(a.content||'')+'</div><div class=ann-time>🕒 '+a.created_at+'</div></div>').join('');
            });
        </script>
    </body>
    </html>
    '''

# ========== API Routes ==========
@app.route('/api/countries', methods=['POST'])
def api_countries():
    return jsonify(get_countries_by_platform(request.json.get('platform')))

@app.route('/api/get_number', methods=['POST'])
def api_get_number():
    d = request.json
    platform = d.get('platform')
    country = d.get('country')
    index = int(d.get('index', 0))
    nums = get_numbers(platform, country)
    if not nums or index >= len(nums):
        return jsonify({'number': None})
    number = nums[index]
    log_code_pull(number, platform)
    pull_count = get_code_pull_count(number, platform)
    return jsonify({'number': number, 'pull_count': pull_count})

@app.route('/api/get_otp', methods=['POST'])
def api_get_otp():
    num = request.json.get('number')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT otp FROM otp_logs WHERE number LIKE ? ORDER BY id DESC LIMIT 1", (f"%{num[-4:]}",))
    row = c.fetchone()
    conn.close()
    return jsonify({'otp': row[0] if row else None})

@app.route('/api/announcements', methods=['GET'])
def api_get_announcements():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT content, created_at FROM announcements ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    return jsonify([{'content': r[0], 'created_at': r[1]} for r in rows])

@app.route('/api/help', methods=['POST'])
def api_help():
    msg = request.json.get('message', '').strip()
    if not msg:
        return jsonify({'ok': False}), 400
    user_id = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO help_requests (user_id, message, source, created_at) VALUES (?, ?, ?, ?)",
              (user_id, msg, 'website', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    notify_admin(f"🆘 <b>طلب مساعدة جديد</b>\n\n👤 المستخدم: {user_id}\n💬 الرسالة:\n{msg}")
    return jsonify({'ok': True})

# ========== Admin Panel ==========
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return '<script>alert("❌ كلمة المرور خاطئة!"); history.back();</script>'
    return '''
    <div style="text-align:center; margin-top:100px; font-family:Cairo,sans-serif; background:#0d1117; color:#fff; padding:40px; border-radius:20px; max-width:400px; margin-left:auto; margin-right:auto; border:1px solid #30363d;">
        <h2 style="color:#00ffc8;">🔐 دخول الأدمن</h2>
        <form method="POST">
            <input type="password" name="password" placeholder="كلمة المرور" style="padding:14px; border-radius:10px; border:1px solid #30363d; background:#161b22; color:#fff; width:100%; margin:12px 0; font-size:15px;">
            <button type="submit" style="padding:14px 25px; background:linear-gradient(135deg,#00ffc8,#8b5cf6); color:#000; border:none; border-radius:10px; cursor:pointer; font-weight:bold; width:100%; font-size:16px;">دخول</button>
        </form>
    </div>
    '''

@app.route('/admin')
@login_required
def admin_dashboard():
    total_visitors, today_visitors, unique_visitors = get_visitor_stats()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM otp_logs")
    total_otps = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM otp_logs WHERE timestamp LIKE ?", (datetime.now().strftime("%Y-%m-%d") + '%',))
    today_otps = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM code_pulls")
    total_pulls = c.fetchone()[0]
    c.execute("SELECT platform, COUNT(*) as cnt FROM otp_logs GROUP BY platform ORDER BY cnt DESC LIMIT 10")
    platform_stats = c.fetchall()
    c.execute("SELECT * FROM announcements ORDER BY id DESC LIMIT 10")
    announcements = c.fetchall()
    c.execute("SELECT * FROM help_requests WHERE status='pending' ORDER BY id DESC LIMIT 10")
    pending_requests = c.fetchall()
    conn.close()
    
    links = get_all_links()
    combos = get_all_combos()
    all_texts = {
        'site_title': get_text('site_title'),
        'site_subtitle': get_text('site_subtitle'),
        'btn_get_number': get_text('btn_get_number'),
        'footer_text': get_text('footer_text'),
        'ticker_text': get_text('ticker_text'),
    }
    
    return render_template_string('''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚙️ لوحة التحكم</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family:Cairo,sans-serif; background:#07090d; color:#fff; min-height:100vh; padding:20px; }
        .container { max-width:600px; margin:0 auto; }
        
        .header { text-align:center; margin-bottom:20px; }
        .header h1 { font-size:26px; font-weight:900; background:linear-gradient(90deg,#00ffc8,#8b5cf6); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
        
        .stats-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-bottom:20px; }
        .stat-card { background:#1c2128; border:1px solid #30363d; border-radius:14px; padding:16px; text-align:center; }
        .stat-card .num { font-size:28px; font-weight:900; color:#00ffc8; }
        .stat-card .label { font-size:11px; color:#8b949e; margin-top:4px; }
        
        .section { background:#1c2128; border:1px solid #30363d; border-radius:16px; padding:20px; margin-bottom:14px; }
        .section-title { font-size:16px; font-weight:800; color:#fff; margin-bottom:14px; display:flex; align-items:center; gap:8px; }
        .section-title .icon { font-size:20px; }
        
        .form-group { margin-bottom:12px; }
        .form-group label { display:block; color:#c9d1d9; font-weight:700; font-size:13px; margin-bottom:6px; }
        .form-control { width:100%; padding:12px; border-radius:10px; border:1px solid #30363d; background:#0d1117; color:#fff; font-family:Cairo,sans-serif; font-size:13px; }
        .form-control:focus { border-color:#00ffc8; outline:none; }
        
        .btn { padding:12px 20px; border:none; border-radius:10px; font-weight:700; cursor:pointer; font-family:Cairo,sans-serif; font-size:13px; }
        .btn-primary { background:linear-gradient(135deg,#00ffc8,#00d2ff); color:#000; }
        .btn-danger { background:linear-gradient(135deg,#ef4444,#b91c1c); color:#fff; }
        .btn-secondary { background:#30363d; color:#fff; }
        .btn-success { background:linear-gradient(135deg,#22c55e,#16a34a); color:#fff; }
        .btn:hover { transform:translateY(-2px); }
        
        .link-item { display:flex; gap:8px; align-items:center; margin-bottom:8px; }
        .link-item input { flex:1; }
        .link-item .icon-input { width:50px; text-align:center; }
        
        .combo-item { display:flex; justify-content:space-between; align-items:center; background:#0d1117; padding:10px 14px; border-radius:10px; margin-bottom:6px; font-size:13px; }
        .combo-item button { padding:4px 10px; font-size:11px; }
        
        .platform-stat { display:flex; justify-content:space-between; padding:8px 12px; background:#0d1117; border-radius:8px; margin-bottom:4px; font-size:13px; }
        .platform-stat .name { font-weight:700; }
        .platform-stat .count { color:#00ffc8; font-weight:800; }
        
        .color-item { display:flex; align-items:center; gap:10px; margin-bottom:8px; }
        .color-item label { flex:1; font-size:12px; color:#8b949e; }
        .color-item input[type="color"] { width:50px; height:36px; border:none; border-radius:8px; cursor:pointer; }
        
        .toggle-switch { position:relative; display:inline-block; width:50px; height:26px; }
        .toggle-switch input { opacity:0; width:0; height:0; }
        .slider { position:absolute; cursor:pointer; inset:0; background:#30363d; border-radius:26px; transition:.3s; }
        .slider:before { content:''; position:absolute; height:20px; width:20px; left:3px; bottom:3px; background:#fff; border-radius:50%; transition:.3s; }
        input:checked + .slider { background:#00ffc8; }
        input:checked + .slider:before { transform:translateX(24px); }
        
        .grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
        .grid-3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; }
        
        .back-link { display:block; text-align:center; color:#58a6ff; text-decoration:none; margin-top:20px; font-weight:700; }
        .back-link:hover { text-decoration:underline; }
        
        .ann-item { background:#0d1117; border:1px solid #30363d; border-radius:8px; padding:12px; margin-bottom:8px; }
        .ann-item .time { font-size:10px; color:#6e7681; margin-top:4px; }
        .ann-item textarea { width:100%; background:#161b22; border:1px solid #30363d; color:#fff; border-radius:8px; padding:10px; font-family:Cairo; resize:vertical; min-height:60px; }
        
        .request-item { background:#0d1117; border:1px solid #30363d; border-radius:8px; padding:10px; margin-bottom:6px; font-size:12px; }
        .request-item .msg { color:#c9d1d9; margin-bottom:4px; }
        .request-item .meta { color:#6e7681; font-size:10px; }
        
        @media (max-width:480px) { .stats-grid { grid-template-columns:1fr 1fr; } .grid-2 { grid-template-columns:1fr; } .grid-3 { grid-template-columns:1fr; } }
    </style>
</head>
<body>
<div class="container">
    <div class="header"><h1>⚙️ لوحة التحكم</h1></div>
    
    <!-- الإحصائيات -->
    <div class="stats-grid">
        <div class="stat-card"><div class="num">{{ total_visitors }}</div><div class="label">👥 الزوار</div></div>
        <div class="stat-card"><div class="num">{{ today_visitors }}</div><div class="label">📅 اليوم</div></div>
        <div class="stat-card"><div class="num">{{ total_otps }}</div><div class="label">🔑 الأكواد</div></div>
        <div class="stat-card"><div class="num">{{ today_otps }}</div><div class="label">📈 اليوم</div></div>
        <div class="stat-card"><div class="num">{{ total_users }}</div><div class="label">👤 المستخدمين</div></div>
        <div class="stat-card"><div class="num">{{ total_pulls }}</div><div class="label">📡 السحوبات</div></div>
    </div>
    
    <!-- النصوص -->
    <div class="section">
        <div class="section-title"><span class="icon">✏️</span> تحرير النصوص</div>
        <div class="form-group"><label>عنوان الموقع</label><input type="text" id="siteTitle" class="form-control" value="{{ all_texts.site_title }}"></div>
        <div class="form-group"><label>وصف الموقع</label><input type="text" id="siteSubtitle" class="form-control" value="{{ all_texts.site_subtitle }}"></div>
        <div class="form-group"><label>زر جلب الرقم</label><input type="text" id="btnGetNumber" class="form-control" value="{{ all_texts.btn_get_number }}"></div>
        <div class="form-group"><label>النص السفلي</label><input type="text" id="footerText" class="form-control" value="{{ all_texts.footer_text }}"></div>
        <div class="form-group"><label>شريط الأخبار</label><input type="text" id="tickerText" class="form-control" value="{{ all_texts.ticker_text }}"></div>
        <button class="btn btn-primary" onclick="saveTexts()" style="width:100%; margin-top:6px;">💾 حفظ النصوص</button>
    </div>
    
    <!-- الألوان -->
    <div class="section">
        <div class="section-title"><span class="icon">🎨</span> تخصيص الألوان</div>
        <div class="color-item"><label>اللون الرئيسي</label><input type="color" id="mainColor" value="{{ main_color }}"></div>
        <div class="color-item"><label>اللون الثانوي</label><input type="color" id="secondaryColor" value="{{ secondary_color }}"></div>
        <div class="color-item"><label>لون الخلفية</label><input type="color" id="bgColor" value="{{ bg_color }}"></div>
        <div class="color-item"><label>لون النص</label><input type="color" id="textColor" value="{{ text_color }}"></div>
        <button class="btn btn-primary" onclick="saveColors()" style="width:100%; margin-top:8px;">💾 حفظ الألوان</button>
    </div>
    
    <!-- الإعدادات -->
    <div class="section">
        <div class="section-title"><span class="icon">⚡</span> الإعدادات</div>
        <div class="color-item">
            <label>تفعيل أرقام متساقطة</label>
            <label class="toggle-switch">
                <input type="checkbox" id="fallingToggle" {{ 'checked' if falling_enabled == '1' else '' }}>
                <span class="slider"></span>
            </label>
        </div>
        <div class="color-item">
            <label>تفعيل Matrix Background</label>
            <label class="toggle-switch">
                <input type="checkbox" id="matrixToggle" {{ 'checked' if matrix_enabled == '1' else '' }}>
                <span class="slider"></span>
            </label>
        </div>
        <div class="color-item">
            <label>تفعيل الإشعارات</label>
            <label class="toggle-switch">
                <input type="checkbox" id="notifToggle" {{ 'checked' if notification_enabled == '1' else '' }}>
                <span class="slider"></span>
            </label>
        </div>
        <button class="btn btn-primary" onclick="saveSettings()" style="width:100%; margin-top:8px;">💾 حفظ الإعدادات</button>
    </div>
    
    <!-- الروابط -->
    <div class="section">
        <div class="section-title"><span class="icon">🔗</span> الروابط</div>
        {% for key, value, icon in links %}
        <div class="link-item">
            <input type="text" class="form-control icon-input" value="{{ icon }}" data-key="{{ key }}" id="icon-{{ key }}">
            <input type="text" class="form-control" value="{{ value }}" data-key="{{ key }}" id="link-{{ key }}">
            <button class="btn btn-danger" onclick="deleteLink('{{ key }}')">🗑️</button>
        </div>
        {% endfor %}
        <div class="link-item" style="margin-top:10px;">
            <input type="text" class="form-control icon-input" id="newIcon" placeholder="🎵">
            <input type="text" class="form-control" id="newLink" placeholder="الرابط الجديد">
            <button class="btn btn-success" onclick="addLink()">➕</button>
        </div>
        <button class="btn btn-primary" onclick="saveLinks()" style="width:100%; margin-top:8px;">💾 حفظ الروابط</button>
    </div>
    
    <!-- الكومبوهات -->
    <div class="section">
        <div class="section-title"><span class="icon">📦</span> الكومبوهات</div>
        <form method="POST" enctype="multipart/form-data" action="/admin/upload_combo">
            <div class="grid-2">
                <select name="platform" class="form-control">
                    <option value="whatsapp">واتساب</option><option value="telegram">تيليجرام</option>
                    <option value="tiktok">تيك توك</option><option value="facebook">فيسبوك</option>
                    <option value="instagram">انستقرام</option><option value="snapchat">سناب شات</option>
                    <option value="google">جوجل</option><option value="twitter">تويتر</option>
                </select>
                <input type="file" name="file" accept=".txt" class="form-control" required>
            </div>
            <button type="submit" class="btn btn-primary" style="width:100%; margin-top:8px;">📤 رفع ملف</button>
        </form>
        <div style="margin-top:12px;">
            {% for platform, code, name, flag in combos %}
            <div class="combo-item">
                <span>{{ flag }} {{ name }} ({{ platform }})</span>
                <form method="POST" action="/admin/delete_combo" style="display:inline;">
                    <input type="hidden" name="platform" value="{{ platform }}">
                    <input type="hidden" name="country_code" value="{{ code }}">
                    <button type="submit" class="btn btn-danger">🗑️</button>
                </form>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <!-- الإعلانات -->
    <div class="section">
        <div class="section-title"><span class="icon">📢</span> الإعلانات</div>
        <form method="POST" action="/admin/add_announcement">
            <textarea name="content" class="form-control" placeholder="نص الإعلان الجديد..." rows="2" required></textarea>
            <div class="grid-2" style="margin-top:8px;">
                <input type="text" name="button_text" class="form-control" placeholder="نص الزر">
                <input type="text" name="button_url" class="form-control" placeholder="رابط الزر">
            </div>
            <button type="submit" class="btn btn-primary" style="width:100%; margin-top:8px;">➕ إضافة إعلان</button>
        </form>
        {% for ann in announcements %}
        <div class="ann-item">
            <div>{{ ann[2] }}</div>
            <div class="time">{{ ann[7] }}</div>
            <form method="POST" action="/admin/delete_announcement" style="margin-top:6px;">
                <input type="hidden" name="id" value="{{ ann[0] }}">
                <button type="submit" class="btn btn-danger" style="padding:6px 12px; font-size:11px;">🗑️ حذف</button>
            </form>
        </div>
        {% endfor %}
    </div>
    
    <!-- طلبات المساعدة -->
    <div class="section">
        <div class="section-title"><span class="icon">🆘</span> طلبات المساعدة ({{ pending_requests|length }})</div>
        {% for req in pending_requests %}
        <div class="request-item">
            <div class="msg">{{ req[2] }}</div>
            <div class="meta">👤 {{ req[1] }} | 🕒 {{ req[5] }}</div>
            <form method="POST" action="/admin/resolve_request" style="margin-top:6px;">
                <input type="hidden" name="id" value="{{ req[0] }}">
                <button type="submit" class="btn btn-success" style="padding:6px 12px; font-size:11px;">✅ تم الحل</button>
            </form>
        </div>
        {% else %}
        <div style="text-align:center; color:#6e7681; padding:20px;">✅ لا توجد طلبات معلقة</div>
        {% endfor %}
    </div>
    
    <!-- إعدادات الأدمن -->
    <div class="section">
        <div class="section-title"><span class="icon">🔑</span> إعدادات الأدمن</div>
        <div class="form-group"><label>Chat ID للإشعاع</label><input type="text" id="adminChatId" class="form-control" value="{{ admin_chat_id }}"></div>
        <div class="form-group"><label>كلمة المرور الجديدة</label><input type="password" id="newPassword" class="form-control" placeholder="اتركها فارغة"></div>
        <div class="grid-2">
            <button class="btn btn-primary" onclick="saveAdminId()">💾 حفظ Chat ID</button>
            <button class="btn btn-secondary" onclick="changePassword()">🔑 تغيير كلمة المرور</button>
        </div>
    </div>
    
    <!-- الإحصائيات -->
    <div class="section">
        <div class="section-title"><span class="icon">📊</span> إحصائيات المنصات</div>
        {% for platform, count in platform_stats %}
        <div class="platform-stat">
            <span class="name">{{ platform }}</span>
            <span class="count">{{ count }}</span>
        </div>
        {% endfor %}
    </div>
    
    <a href="/" class="back-link">🔙 العودة للموقع</a>
</div>

<script>
async function saveTexts() {
    const data = {
        site_title: document.getElementById('siteTitle').value,
        site_subtitle: document.getElementById('siteSubtitle').value,
        btn_get_number: document.getElementById('btnGetNumber').value,
        footer_text: document.getElementById('footerText').value,
        ticker_text: document.getElementById('tickerText').value
    };
    await fetch('/admin/api/save_texts', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    alert('✅ تم الحفظ!');
}

async function saveColors() {
    const data = {
        main_color: document.getElementById('mainColor').value,
        secondary_color: document.getElementById('secondaryColor').value,
        background_color: document.getElementById('bgColor').value,
        text_color: document.getElementById('textColor').value
    };
    await fetch('/admin/api/save_settings', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    alert('✅ تم الحفظ!');
}

async function saveSettings() {
    const data = {
        falling_numbers_enabled: document.getElementById('fallingToggle').checked ? '1' : '0',
        matrix_enabled: document.getElementById('matrixToggle').checked ? '1' : '0',
        notification_enabled: document.getElementById('notifToggle').checked ? '1' : '0'
    };
    await fetch('/admin/api/save_settings', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    alert('✅ تم الحفظ!');
}

async function saveLinks() {
    const links = {};
    document.querySelectorAll('[id^="link-"]').forEach(inp => {
        const key = inp.dataset.key;
        const icon = document.getElementById('icon-' + key).value;
        if(key) links[key] = {value: inp.value, icon: icon};
    });
    await fetch('/admin/api/save_links', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(links)});
    alert('✅ تم الحفظ!');
}

async function addLink() {
    const icon = document.getElementById('newIcon').value.trim();
    const value = document.getElementById('newLink').value.trim();
    if(!value) { alert('اكتب الرابط!'); return; }
    await fetch('/admin/api/add_link', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({key: 'custom_' + Date.now(), value, icon: icon || '🔗'})});
    location.reload();
}

async function deleteLink(key) {
    if(!confirm('حذف هذا الرابط؟')) return;
    await fetch('/admin/api/delete_link', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({key})});
    location.reload();
}

async function saveAdminId() {
    const val = document.getElementById('adminChatId').value.trim();
    await fetch('/admin/api/save_admin_id', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({admin_telegram_id: val})});
    alert('✅ تم الحفظ!');
}

async function changePassword() {
    const pwd = document.getElementById('newPassword').value.trim();
    if(!pwd) { alert('اكتب كلمة المرور الجديدة!'); return; }
    await fetch('/admin/api/change_password', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({password: pwd})});
    alert('✅ تم التغيير!');
}
</script>
</body>
</html>
''', total_visitors=total_visitors, today_visitors=today_visitors, 
       total_otps=total_otps, today_otps=today_otps, total_users=total_users, total_pulls=total_pulls,
       platform_stats=platform_stats, links=links, combos=combos, 
       announcements=announcements, pending_requests=pending_requests,
       all_texts=all_texts, 
       main_color=get_setting('main_color') or '#00ffc8',
       secondary_color=get_setting('secondary_color') or '#8b5cf6',
       bg_color=get_setting('background_color') or '#0a0e1a',
       text_color=get_setting('text_color') or '#ffffff',
       falling_enabled=get_setting('falling_numbers_enabled') or '1',
       matrix_enabled=get_setting('matrix_enabled') or '1',
       notification_enabled=get_setting('notification_enabled') or '1',
       admin_chat_id=get_admin_setting('admin_telegram_id', ''))

# ========== Admin API Routes ==========
@app.route('/admin/api/save_texts', methods=['POST'])
def admin_api_save_texts():
    data = request.json
    for key, value in data.items():
        update_text(key, value)
    return jsonify({'ok': True})

@app.route('/admin/api/save_settings', methods=['POST'])
def admin_api_save_settings():
    data = request.json
    for key, value in data.items():
        set_setting(key, value)
    return jsonify({'ok': True})

@app.route('/admin/api/save_links', methods=['POST'])
def admin_api_save_links():
    data = request.json
    for key, val in data.items():
        if isinstance(val, dict):
            update_link(key, val['value'], val.get('icon'))
        else:
            update_link(key, val)
    return jsonify({'ok': True})

@app.route('/admin/api/add_link', methods=['POST'])
def admin_api_add_link():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO site_links (key, value, icon) VALUES (?, ?, ?)",
              (data.get('key'), data.get('value'), data.get('icon', '🔗')))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/admin/api/delete_link', methods=['POST'])
def admin_api_delete_link():
    key = request.json.get('key')
    if key:
        delete_link(key)
    return jsonify({'ok': True})

@app.route('/admin/api/save_admin_id', methods=['POST'])
def admin_api_save_admin_id():
    admin_id = request.json.get('admin_telegram_id')
    if admin_id:
        set_admin_setting('admin_telegram_id', admin_id)
    return jsonify({'ok': True})

@app.route('/admin/api/change_password', methods=['POST'])
def admin_api_change_password():
    global ADMIN_PASSWORD
    new_pwd = request.json.get('password')
    if new_pwd:
        ADMIN_PASSWORD = new_pwd
    return jsonify({'ok': True})

@app.route('/admin/upload_combo', methods=['POST'])
def admin_upload_combo():
    platform = request.form.get('platform')
    file = request.files.get('file')
    if not file or not file.filename.endswith('.txt'):
        return redirect(url_for('admin_dashboard'))
    content = file.read().decode('utf-8')
    numbers = [line.strip() for line in content.splitlines() if line.strip()]
    if not numbers:
        return redirect(url_for('admin_dashboard'))
    first = numbers[0]
    codes = sorted(COUNTRY_DATA.keys(), key=len, reverse=True)
    cc = None
    for c in codes:
        if first.startswith(c):
            cc = c
            break
    if cc:
        name, flag = get_country_info(cc)
        save_combo(platform, cc, name, flag, numbers)
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_combo', methods=['POST'])
def admin_delete_combo():
    platform = request.form.get('platform')
    country_code = request.form.get('country_code')
    if platform and country_code:
        delete_combo(platform, country_code)
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_announcement', methods=['POST'])
def admin_add_announcement():
    content = request.form.get('content', '').strip()
    button_text = request.form.get('button_text', '').strip()
    button_url = request.form.get('button_url', '').strip()
    if content:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO announcements (type, content, button_text, button_url, created_at) VALUES (?, ?, ?, ?, ?)",
                  ('info', content, button_text, button_url, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_announcement', methods=['POST'])
def admin_delete_announcement():
    ann_id = request.form.get('id')
    if ann_id:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM announcements WHERE id=?", (ann_id,))
        conn.commit()
        conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/resolve_request', methods=['POST'])
def admin_resolve_request():
    req_id = request.form.get('id')
    if req_id:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE help_requests SET status='resolved' WHERE id=?", (req_id,))
        conn.commit()
        conn.close()
    return redirect(url_for('admin_dashboard'))

# ========== Telegram Bot ==========
def monitor_channel():
    last_update_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {"timeout": 10, "offset": last_update_id + 1}
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if data.get('ok'):
                    for upd in data.get('result', []):
                        last_update_id = upd['update_id']
                        if 'channel_post' in upd:
                            text = upd['channel_post'].get('text', '')
                            if not text: continue
                            clean = re.sub(r'[\u200B-\u200F\u202A-\u202E]', '', text)
                            all_numbers = re.findall(r'\b\d{8,15}\b', clean)
                            user_number = max(all_numbers, key=len) if all_numbers else None
                            last_digits = user_number[-4:] if user_number else None
                            all_codes = [c for c in re.findall(r'\b\d{4,8}\b', clean) if not (last_digits and c.endswith(last_digits))]
                            otp = all_codes[0] if all_codes else None
                            platform = "غير معروف"
                            for name in platform_names.keys():
                                if name in clean.lower():
                                    platform = name
                                    break
                            if otp:
                                conn = sqlite3.connect(DB_PATH)
                                conn.cursor().execute(
                                    "INSERT INTO otp_logs (number, otp, timestamp, platform) VALUES (?, ?, ?, ?)",
                                    (last_digits or "0000", otp, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), platform)
                                )
                                conn.commit()
                                conn.close()
                                print(f"✅ [{platform}] {otp}")
        except Exception as e:
            print(f"❌ {e}")
        time.sleep(5)

threading.Thread(target=monitor_channel, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
