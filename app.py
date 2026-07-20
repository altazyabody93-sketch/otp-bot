from flask import Flask, request, render_template_string, jsonify, redirect, url_for, session, send_file
import sqlite3
import json
import random
import os
import re
import requests
import threading
import time
import csv
import io
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = "supersecretkey_change_this_to_random"
DB_PATH = "almatry_otp.db"

# ========== الإعدادات الأساسية ==========
ADMIN_PASSWORD = "admin123"
ADMIN_USERNAME = "admin"
ADMIN_SECRET_PATH = "admin_secret_77"

WHATSAPP_GROUP_LINK = "https://chat.whatsapp.com/IeK2gNS64fd8YSnenzt4WR"
OWNER_PHONE = "967733723953"
OWNER_LINK = f"https://wa.me/{OWNER_PHONE}"

TELEGRAM_BOT_TOKEN = "8814038881:AAGyuACUYA4YPKlJQhAyUMkpRNiV0u1gNuU"
CHANNEL_USERNAME = "@jsjsgsjsvh"
ASSISTANT_BOT_TOKEN = "8845420882:AAHZ-7qhCL3_ddDT3am4zWNtBRBy3mVDgws"
OWNER_TELEGRAM_ID = "@ABOD_90N"

# ========== بيانات الدول ==========
COUNTRY_DATA = {
    "966": {"n": "السعودية", "f": "🇸🇦"},
    "971": {"n": "الإمارات", "f": "🇦🇪"},
    "20": {"n": "مصر", "f": "🇪🇬"},
    "1": {"n": "الولايات المتحدة", "f": "🇺🇸"},
    "44": {"n": "بريطانيا", "f": "🇬🇧"},
    "90": {"n": "تركيا", "f": "🇹🇷"},
    "91": {"n": "الهند", "f": "🇮🇳"},
    "49": {"n": "ألمانيا", "f": "🇩🇪"},
    "7": {"n": "روسيا", "f": "🇷🇺"},
    "33": {"n": "فرنسا", "f": "🇫🇷"},
    "212": {"n": "المغرب", "f": "🇲🇦"},
    "213": {"n": "الجزائر", "f": "🇩🇿"},
    "961": {"n": "لبنان", "f": "🇱🇧"},
    "962": {"n": "الأردن", "f": "🇯🇴"},
    "963": {"n": "سوريا", "f": "🇸🇾"},
    "964": {"n": "العراق", "f": "🇮🇶"},
    "965": {"n": "الكويت", "f": "🇰🇼"},
    "967": {"n": "اليمن", "f": "🇾🇪"},
    "968": {"n": "عمان", "f": "🇴🇲"},
    "973": {"n": "البحرين", "f": "🇧🇭"},
    "974": {"n": "قطر", "f": "🇶🇦"},
}

def get_country_info(code):
    info = COUNTRY_DATA.get(code)
    return (info["n"], info["f"]) if info else ("أخرى", "🌍")

# ========== قاعدة البيانات ==========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS combos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT,
        country_code TEXT,
        country_name TEXT,
        country_flag TEXT,
        numbers TEXT,
        UNIQUE(platform, country_code)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS otp_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        number TEXT,
        otp TEXT,
        timestamp TEXT,
        platform TEXT,
        country_code TEXT,
        country_flag TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        content TEXT,
        media_url TEXT,
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS site_texts (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS site_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS site_links (
        key TEXT PRIMARY KEY,
        value TEXT,
        icon TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS admin_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        details TEXT,
        created_at TEXT
    )''')
    
    # النصوص الافتراضية
    default_texts = {
        'site_title': '✨ المطري OTP ✨',
        'site_subtitle': '👑 أسرع موقع لسحب أكواد التطوير 👑',
        'btn_get_number': '🎯 جلب رقم',
        'btn_refresh': '🔄 رقم آخر',
        'btn_start_monitor': '📡 مراقبة الأكواد',
        'btn_stop_monitor': '⏸️ إيقاف',
        'footer_text': '💎 صُنع بعناية فائقة ⚡',
        'ticker_text': '🚀 المطري OTP - الأسرع والأموثق 💎'
    }
    for key, value in default_texts.items():
        c.execute("INSERT OR IGNORE INTO site_texts (key, value) VALUES (?, ?)", (key, value))
    
    # الروابط الافتراضية
    default_links = [
        ('whatsapp_developer', OWNER_LINK, '💬'),
        ('whatsapp_group', WHATSAPP_GROUP_LINK, '👥'),
        ('telegram_channel', 'https://t.me/jsjsgsjsvh', '✈️'),
        ('telegram_group', 'https://t.me/jsjsgsjsvh', '👥'),
        ('instagram', 'https://instagram.com/', '📸'),
        ('tiktok', 'https://tiktok.com/', '🎵'),
        ('facebook', 'https://facebook.com/', '📘'),
    ]
    for key, value, icon in default_links:
        c.execute("INSERT OR IGNORE INTO site_links (key, value, icon) VALUES (?, ?, ?)", (key, value, icon))
    
    # إعدادات الموقع
    default_settings = {
        'matrix_enabled': '1',
        'ticker_enabled': '1',
        'sound_enabled': '0',  # مخفي
        'add_btn_enabled': '0',  # مخفي
        'minus_btn_enabled': '0',  # مخفي
        'code_received_section': '0',  # مخفي
        'harvested_codes_section': '0',  # مخفي
        'main_color': '#00ff88',
        'secondary_color': '#00d4ff',
        'background_color': '#0a0e1a',
        'text_color': '#e6f1ff',
        'admin_bg_color': '#1a1f2e',
        'admin_primary_color': '#00ff88',
    }
    for key, value in default_settings.items():
        c.execute("INSERT OR IGNORE INTO site_settings (key, value) VALUES (?, ?)", (key, value))
    
    conn.commit()
    conn.close()

init_db()

# ========== دوال قاعدة البيانات ==========
def get_text(key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM site_texts WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else ''

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

def get_link(key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value, icon FROM site_links WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row if row else ('', '')

def get_all_links():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT key, value, icon FROM site_links")
    rows = c.fetchall()
    conn.close()
    return rows

def update_link(key, value, icon=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if icon is not None:
        c.execute("REPLACE INTO site_links (key, value, icon) VALUES (?, ?, ?)", (key, value, icon))
    else:
        c.execute("UPDATE site_links SET value=? WHERE key=?", (value, key))
    conn.commit()
    conn.close()

def admin_log(action, details=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO admin_logs (action, details, created_at) VALUES (?, ?, ?)",
              (action, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# ========== دوال الأرقام والأكواد ==========
def get_platforms():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT platform FROM combos ORDER BY platform")
    platforms = [row[0] for row in c.fetchall()]
    conn.close()
    return platforms

def get_countries_by_platform(platform):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT country_code, country_name, country_flag FROM combos WHERE platform=? ORDER BY country_name", (platform,))
    countries = c.fetchall()
    conn.close()
    return countries

def get_numbers_by_platform_country(platform, country_code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT numbers FROM combos WHERE platform=? AND country_code=?", (platform, country_code))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0].split(',')
    return []

def add_otp_log(number, otp, platform, country_code='', country_flag=''):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO otp_logs (number, otp, timestamp, platform, country_code, country_flag) VALUES (?, ?, ?, ?, ?, ?)",
              (number, otp, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), platform, country_code, country_flag))
    conn.commit()
    conn.close()

def get_recent_otps(limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM otp_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    otps = c.fetchall()
    conn.close()
    return otps

# ========== Middleware المصادقة ==========
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ========== الواجهة الرئيسية ==========
MAIN_PAGE_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ site_title }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: {{ bg_color }};
            color: {{ text_color }};
            overflow-x: hidden;
        }
        
        /* مطر الأرقام خلفية */
        .matrix-background {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 1;
            overflow: hidden;
            opacity: 0.1;
        }
        
        .matrix-char {
            position: absolute;
            color: {{ main_color }};
            font-size: 20px;
            font-weight: bold;
        }
        
        .ticker {
            background: linear-gradient(90deg, {{ main_color }}, {{ secondary_color }});
            color: {{ bg_color }};
            padding: 15px;
            text-align: center;
            font-weight: bold;
            animation: scroll 20s linear infinite;
            overflow: hidden;
            white-space: nowrap;
        }
        
        @keyframes scroll {
            0% { transform: translateX(100%); }
            100% { transform: translateX(-100%); }
        }
        
        .container {
            position: relative;
            z-index: 2;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 30px 0;
            background: linear-gradient(135deg, {{ main_color }}20, {{ secondary_color }}20);
            border-radius: 20px;
            border: 2px solid {{ main_color }}40;
        }
        
        .site-title {
            font-size: 48px;
            font-weight: bold;
            margin-bottom: 10px;
            background: linear-gradient(135deg, {{ main_color }}, {{ secondary_color }});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .site-subtitle {
            font-size: 18px;
            color: {{ text_color }};
            opacity: 0.8;
        }
        
        .platforms-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        
        .platform-btn {
            padding: 20px;
            border: 2px solid {{ main_color }};
            background: {{ bg_color }};
            color: {{ text_color }};
            border-radius: 15px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 16px;
            font-weight: bold;
        }
        
        .platform-btn:hover {
            background: {{ main_color }};
            color: {{ bg_color }};
            transform: translateY(-5px);
            box-shadow: 0 10px 30px {{ main_color }}40;
        }
        
        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: {{ bg_color }};
            border: 2px solid {{ main_color }}40;
            border-radius: 15px;
            padding: 25px;
            transition: all 0.3s;
        }
        
        .card:hover {
            border-color: {{ main_color }};
            box-shadow: 0 0 20px {{ main_color }}20;
        }
        
        .card-title {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 15px;
            color: {{ main_color }};
        }
        
        .dropdown {
            width: 100%;
            padding: 12px;
            background: {{ bg_color }};
            border: 2px solid {{ secondary_color }};
            color: {{ text_color }};
            border-radius: 10px;
            margin-bottom: 10px;
            cursor: pointer;
            font-size: 14px;
        }
        
        .number-box {
            background: {{ bg_color }};
            border: 3px solid {{ main_color }};
            border-radius: 15px;
            padding: 20px;
            margin: 15px 0;
            text-align: center;
            font-size: 28px;
            font-weight: bold;
            color: {{ main_color }};
            letter-spacing: 3px;
            word-break: break-all;
        }
        
        .code-box {
            background: {{ bg_color }};
            border: 3px solid {{ secondary_color }};
            border-radius: 15px;
            padding: 20px;
            margin: 15px 0;
            text-align: center;
            font-size: 28px;
            font-weight: bold;
            color: {{ secondary_color }};
            letter-spacing: 3px;
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        
        .btn {
            flex: 1;
            padding: 15px;
            border: none;
            border-radius: 10px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 14px;
        }
        
        .btn-primary {
            background: {{ main_color }};
            color: {{ bg_color }};
        }
        
        .btn-primary:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px {{ main_color }}40;
        }
        
        .btn-secondary {
            background: {{ secondary_color }};
            color: {{ bg_color }};
        }
        
        .btn-secondary:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px {{ secondary_color }}40;
        }
        
        .btn-small {
            padding: 8px 12px;
            font-size: 12px;
        }
        
        .links-section {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .link-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 15px;
            background: {{ bg_color }};
            border: 2px solid {{ secondary_color }};
            color: {{ text_color }};
            text-decoration: none;
            border-radius: 10px;
            transition: all 0.3s;
            font-weight: bold;
        }
        
        .link-btn:hover {
            background: {{ secondary_color }};
            color: {{ bg_color }};
            transform: translateY(-5px);
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            color: {{ text_color }};
            opacity: 0.7;
            margin-top: 30px;
            border-top: 1px solid {{ main_color }}40;
        }
        
        .control-buttons {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-top: 20px;
        }
        
        .control-btn {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            border: 2px solid {{ main_color }};
            background: {{ bg_color }};
            color: {{ main_color }};
            font-size: 24px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .control-btn:hover {
            background: {{ main_color }};
            color: {{ bg_color }};
        }
        
        .admin-link {
            position: fixed;
            bottom: 20px;
            left: 20px;
            padding: 12px 20px;
            background: {{ main_color }};
            color: {{ bg_color }};
            text-decoration: none;
            border-radius: 10px;
            font-weight: bold;
            transition: all 0.3s;
            z-index: 100;
        }
        
        .admin-link:hover {
            transform: scale(1.05);
            box-shadow: 0 10px 25px {{ main_color }}40;
        }
        
        @media (max-width: 768px) {
            .main-content {
                grid-template-columns: 1fr;
            }
            .site-title {
                font-size: 32px;
            }
            .platforms-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
    </style>
</head>
<body>
    <div class="matrix-background" id="matrixBg"></div>
    
    {% if ticker_enabled %}
    <div class="ticker">{{ ticker_text }}</div>
    {% endif %}
    
    <div class="container">
        <div class="header">
            <div class="site-title">{{ site_title }}</div>
            <div class="site-subtitle">{{ site_subtitle }}</div>
        </div>
        
        <div class="platforms-grid" id="platformsContainer"></div>
        
        <div class="main-content">
            <div class="card">
                <div class="card-title">📱 المنصات</div>
                <select class="dropdown" id="platformSelect" onchange="updateCountries()">
                    <option value="">اختر المنصة...</option>
                </select>
            </div>
            
            <div class="card">
                <div class="card-title">🌍 الدول</div>
                <select class="dropdown" id="countrySelect" onchange="getNumber()">
                    <option value="">اختر الدولة...</option>
                </select>
            </div>
        </div>
        
        <div class="card">
            <div class="card-title">📞 رقمك</div>
            <div class="number-box" id="numberDisplay">الرجاء اختيار منصة ودولة</div>
            <div class="button-group">
                <button class="btn btn-primary" onclick="copyNumber()">📋 نسخ الرقم</button>
                <button class="btn btn-secondary" onclick="getNumber()">🔄 رقم آخر</button>
            </div>
        </div>
        
        <div class="card" style="display: none;" id="codeReceivedSection">
            <div class="card-title">✅ تم استلام كود</div>
            <div class="code-box" id="codeDisplay"></div>
            <div class="button-group">
                <button class="btn btn-primary btn-small" onclick="copyCode()">📋 نسخ</button>
            </div>
        </div>
        
        <div class="card" style="display: none;" id="harvestedCodesSection">
            <div class="card-title">📊 الأكواد المسحوبة</div>
            <div id="harvestedCodesList"></div>
        </div>
        
        <div class="card">
            <div class="card-title">🔗 روابط التواصل</div>
            <div class="links-section" id="linksContainer"></div>
        </div>
        
        <div class="control-buttons">
            <button class="control-btn" onclick="startMonitoring()" title="بدء المراقبة">▶️</button>
            <button class="control-btn" onclick="stopMonitoring()" title="إيقاف">⏹️</button>
        </div>
        
        <div class="footer">{{ footer_text }}</div>
    </div>
    
    <a href="/admin/{{ admin_secret_path }}/login" class="admin-link">⚙️ الأدمن</a>
    
    <script>
        const ADMIN_SECRET = "{{ admin_secret_path }}";
        const mainColor = "{{ main_color }}";
        const secondaryColor = "{{ secondary_color }}";
        const bgColor = "{{ bg_color }}";
        
        let currentPlatform = '';
        let currentCountry = '';
        let currentNumber = '';
        let isMonitoring = false;
        
        // إنشاء مطر الأرقام
        function createMatrix() {
            const bg = document.getElementById('matrixBg');
            if (!bg) return;
            
            for (let i = 0; i < 50; i++) {
                const char = document.createElement('div');
                char.className = 'matrix-char';
                char.textContent = Math.random() > 0.5 ? Math.floor(Math.random() * 10) : String.fromCharCode(0x0621 + Math.random() * 32);
                char.style.left = Math.random() * 100 + '%';
                char.style.top = Math.random() * 100 + '%';
                char.style.animation = 'fall ' + (3 + Math.random() * 5) + 's linear infinite';
                char.style.animationDelay = Math.random() * 5 + 's';
                bg.appendChild(char);
            }
        }
        
        const style = document.createElement('style');
        style.textContent = `
            @keyframes fall {
                0% {
                    opacity: 1;
                    transform: translateY(-100vh) rotate(0deg);
                }
                100% {
                    opacity: 0;
                    transform: translateY(100vh) rotate(360deg);
                }
            }
        `;
        document.head.appendChild(style);
        
        createMatrix();
        
        // تحديث المنصات
        function updatePlatforms() {
            fetch('/api/platforms')
                .then(r => r.json())
                .then(data => {
                    const container = document.getElementById('platformsContainer');
                    const select = document.getElementById('platformSelect');
                    container.innerHTML = '';
                    select.innerHTML = '<option value="">اختر المنصة...</option>';
                    
                    data.platforms.forEach(p => {
                        // زر في الشبكة
                        const btn = document.createElement('button');
                        btn.className = 'platform-btn';
                        btn.textContent = p;
                        btn.onclick = () => {
                            currentPlatform = p;
                            document.getElementById('platformSelect').value = p;
                            updateCountries();
                        };
                        container.appendChild(btn);
                        
                        // خيار في الـ select
                        const option = document.createElement('option');
                        option.value = p;
                        option.textContent = p;
                        select.appendChild(option);
                    });
                });
        }
        
        // تحديث الدول
        function updateCountries() {
            currentPlatform = document.getElementById('platformSelect').value;
            if (!currentPlatform) return;
            
            fetch('/api/countries/' + encodeURIComponent(currentPlatform))
                .then(r => r.json())
                .then(data => {
                    const select = document.getElementById('countrySelect');
                    select.innerHTML = '<option value="">اختر الدولة...</option>';
                    
                    data.countries.forEach(c => {
                        const option = document.createElement('option');
                        option.value = c[0];
                        option.textContent = c[2] + ' ' + c[1];
                        select.appendChild(option);
                    });
                });
        }
        
        // جلب الرقم
        function getNumber() {
            currentPlatform = document.getElementById('platformSelect').value;
            currentCountry = document.getElementById('countrySelect').value;
            
            if (!currentPlatform || !currentCountry) {
                alert('الرجاء اختيار منصة ودولة');
                return;
            }
            
            fetch('/api/number', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    platform: currentPlatform,
                    country: currentCountry
                })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    currentNumber = data.number;
                    document.getElementById('numberDisplay').textContent = currentNumber;
                } else {
                    alert('❌ ' + (data.error || 'خطأ'));
                }
            });
        }
        
        // نسخ الرقم
        function copyNumber() {
            if (!currentNumber) return;
            navigator.clipboard.writeText(currentNumber);
            alert('✅ تم نسخ الرقم');
        }
        
        // نسخ الكود
        function copyCode() {
            const code = document.getElementById('codeDisplay').textContent;
            if (code) {
                navigator.clipboard.writeText(code);
                alert('✅ تم نسخ الكود');
            }
        }
        
        // بدء المراقبة
        function startMonitoring() {
            isMonitoring = true;
            alert('📡 بدأت مراقبة الأكواد');
        }
        
        // إيقاف المراقبة
        function stopMonitoring() {
            isMonitoring = false;
            alert('⏹️ توقفت المراقبة');
        }
        
        // تحديث الروابط
        function updateLinks() {
            fetch('/api/links')
                .then(r => r.json())
                .then(data => {
                    const container = document.getElementById('linksContainer');
                    container.innerHTML = '';
                    
                    data.links.forEach(link => {
                        const a = document.createElement('a');
                        a.className = 'link-btn';
                        a.href = link[1];
                        a.target = '_blank';
                        a.innerHTML = link[2] + ' ' + link[0];
                        container.appendChild(a);
                    });
                });
        }
        
        // التحميل الأولي
        updatePlatforms();
        updateLinks();
    </script>
</body>
</html>
"""

# ========== لوحة الأدمن ==========
ADMIN_LOGIN_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تسجيل الدخول - الأدمن</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', sans-serif;
            background: {{ admin_bg }};
            color: {{ text_color }};
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }
        
        .login-container {
            background: {{ admin_bg }};
            border: 3px solid {{ admin_color }};
            border-radius: 20px;
            padding: 40px;
            width: 90%;
            max-width: 400px;
            box-shadow: 0 0 50px {{ admin_color }}40;
        }
        
        .login-title {
            text-align: center;
            font-size: 32px;
            margin-bottom: 10px;
            color: {{ admin_color }};
        }
        
        .login-subtitle {
            text-align: center;
            color: {{ text_color }};
            opacity: 0.7;
            margin-bottom: 30px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: {{ admin_color }};
        }
        
        input {
            width: 100%;
            padding: 12px;
            background: rgba(255, 255, 255, 0.1);
            border: 2px solid {{ admin_color }};
            color: {{ text_color }};
            border-radius: 10px;
            font-size: 14px;
            transition: all 0.3s;
        }
        
        input:focus {
            outline: none;
            background: rgba(255, 255, 255, 0.15);
            box-shadow: 0 0 20px {{ admin_color }}40;
        }
        
        .login-btn {
            width: 100%;
            padding: 15px;
            background: {{ admin_color }};
            color: {{ admin_bg }};
            border: none;
            border-radius: 10px;
            font-weight: bold;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .login-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 30px {{ admin_color }}40;
        }
        
        .error {
            background: #ff4444;
            color: white;
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-title">🔐 الأدمن</div>
        <div class="login-subtitle">لوحة التحكم</div>
        
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        
        <form method="POST">
            <div class="form-group">
                <label>👤 اسم المستخدم</label>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>🔑 كلمة السر</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit" class="login-btn">دخول</button>
        </form>
    </div>
</body>
</html>
"""

ADMIN_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة التحكم</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', sans-serif;
            background: {{ admin_bg }};
            color: {{ text_color }};
        }
        
        .navbar {
            background: linear-gradient(135deg, {{ admin_color }}, {{ admin_color }}dd);
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 3px solid {{ admin_color }};
        }
        
        .navbar-title {
            font-size: 28px;
            font-weight: bold;
        }
        
        .navbar-buttons {
            display: flex;
            gap: 10px;
        }
        
        .nav-btn {
            padding: 10px 20px;
            background: rgba(255, 255, 255, 0.1);
            color: {{ text_color }};
            text-decoration: none;
            border-radius: 10px;
            transition: all 0.3s;
            border: 2px solid transparent;
        }
        
        .nav-btn:hover {
            background: rgba(255, 255, 255, 0.2);
            border-color: {{ text_color }};
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 30px 20px;
        }
        
        .menu-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        
        .menu-item {
            background: {{ admin_bg }};
            border: 2px solid {{ admin_color }};
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            text-decoration: none;
            color: {{ text_color }};
            transition: all 0.3s;
        }
        
        .menu-item:hover {
            transform: translateY(-10px);
            background: {{ admin_color }}20;
            box-shadow: 0 10px 30px {{ admin_color }}40;
        }
        
        .menu-icon {
            font-size: 40px;
            margin-bottom: 10px;
        }
        
        .menu-title {
            font-size: 18px;
            font-weight: bold;
            color: {{ admin_color }};
        }
        
        .settings-section {
            background: {{ admin_bg }};
            border: 2px solid {{ admin_color }}40;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
        }
        
        .section-title {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 20px;
            color: {{ admin_color }};
            border-bottom: 2px solid {{ admin_color }}40;
            padding-bottom: 10px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: {{ admin_color }};
        }
        
        input, select, textarea {
            width: 100%;
            padding: 12px;
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid {{ admin_color }}40;
            color: {{ text_color }};
            border-radius: 10px;
            font-size: 14px;
            font-family: inherit;
            transition: all 0.3s;
        }
        
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: {{ admin_color }};
            background: rgba(255, 255, 255, 0.1);
        }
        
        .toggle-group {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }
        
        .toggle-item {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .toggle-switch {
            width: 50px;
            height: 30px;
            background: {{ admin_color }}40;
            border: 2px solid {{ admin_color }};
            border-radius: 20px;
            cursor: pointer;
            position: relative;
            transition: all 0.3s;
        }
        
        .toggle-switch.active {
            background: {{ admin_color }};
        }
        
        .toggle-switch::after {
            content: '';
            position: absolute;
            width: 22px;
            height: 22px;
            background: white;
            border-radius: 50%;
            top: 2px;
            left: 2px;
            transition: all 0.3s;
        }
        
        .toggle-switch.active::after {
            left: 24px;
        }
        
        .btn {
            padding: 12px 25px;
            background: {{ admin_color }};
            color: {{ admin_bg }};
            border: none;
            border-radius: 10px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px {{ admin_color }}40;
        }
        
        .btn-danger {
            background: #ff4444;
        }
        
        .btn-danger:hover {
            box-shadow: 0 10px 25px rgba(255, 68, 68, 0.4);
        }
        
        .success {
            background: #44ff44;
            color: #000;
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        
        .info-box {
            background: {{ admin_color }}20;
            border-left: 4px solid {{ admin_color }};
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="navbar">
        <div class="navbar-title">🔐 لوحة التحكم</div>
        <div class="navbar-buttons">
            <a href="/" class="nav-btn">← العودة للموقع</a>
            <a href="/admin/{{ admin_secret }}/logout" class="nav-btn">تسجيل خروج</a>
        </div>
    </div>
    
    <div class="container">
        <div class="info-box">
            👋 مرحباً، أنت الآن في لوحة التحكم. استخدم الخيارات أدناه لإدارة الموقع.
        </div>
        
        <div class="menu-grid">
            <a href="/admin/{{ admin_secret }}/settings" class="menu-item">
                <div class="menu-icon">⚙️</div>
                <div class="menu-title">الإعدادات</div>
            </a>
            <a href="/admin/{{ admin_secret }}/texts" class="menu-item">
                <div class="menu-icon">📝</div>
                <div class="menu-title">النصوص</div>
            </a>
            <a href="/admin/{{ admin_secret }}/links" class="menu-item">
                <div class="menu-icon">🔗</div>
                <div class="menu-title">الروابط</div>
            </a>
            <a href="/admin/{{ admin_secret }}/combos" class="menu-item">
                <div class="menu-icon">📱</div>
                <div class="menu-title">الأرقام</div>
            </a>
            <a href="/admin/{{ admin_secret }}/codes" class="menu-item">
                <div class="menu-icon">🔐</div>
                <div class="menu-title">الأكواد</div>
            </a>
            <a href="/admin/{{ admin_secret }}/logs" class="menu-item">
                <div class="menu-icon">📊</div>
                <div class="menu-title">السجلات</div>
            </a>
        </div>
    </div>
</body>
</html>
"""

ADMIN_SETTINGS_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>الإعدادات</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: {{ admin_bg }};
            color: {{ text_color }};
        }
        .navbar {
            background: linear-gradient(135deg, {{ admin_color }}, {{ admin_color }}dd);
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 3px solid {{ admin_color }};
        }
        .navbar-title { font-size: 28px; font-weight: bold; }
        .navbar-buttons {
            display: flex;
            gap: 10px;
        }
        .nav-btn {
            padding: 10px 20px;
            background: rgba(255, 255, 255, 0.1);
            color: {{ text_color }};
            text-decoration: none;
            border-radius: 10px;
            transition: all 0.3s;
        }
        .nav-btn:hover { background: rgba(255, 255, 255, 0.2); }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 30px 20px;
        }
        .section {
            background: {{ admin_bg }};
            border: 2px solid {{ admin_color }}40;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
        }
        .section-title {
            font-size: 22px;
            font-weight: bold;
            margin-bottom: 20px;
            color: {{ admin_color }};
            border-bottom: 2px solid {{ admin_color }}40;
            padding-bottom: 10px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: {{ admin_color }};
        }
        input, select {
            width: 100%;
            padding: 12px;
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid {{ admin_color }}40;
            color: {{ text_color }};
            border-radius: 10px;
            font-size: 14px;
        }
        input:focus, select:focus {
            outline: none;
            border-color: {{ admin_color }};
        }
        .toggle-item {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
        }
        .toggle-switch {
            width: 50px;
            height: 30px;
            background: {{ admin_color }}40;
            border: 2px solid {{ admin_color }};
            border-radius: 20px;
            cursor: pointer;
            position: relative;
        }
        .toggle-switch.active { background: {{ admin_color }}; }
        .toggle-switch::after {
            content: '';
            position: absolute;
            width: 22px;
            height: 22px;
            background: white;
            border-radius: 50%;
            top: 2px;
            left: 2px;
            transition: left 0.3s;
        }
        .toggle-switch.active::after { left: 24px; }
        .btn {
            padding: 12px 25px;
            background: {{ admin_color }};
            color: {{ admin_bg }};
            border: none;
            border-radius: 10px;
            font-weight: bold;
            cursor: pointer;
        }
        .btn:hover { transform: translateY(-3px); }
    </style>
</head>
<body>
    <div class="navbar">
        <div class="navbar-title">⚙️ الإعدادات</div>
        <div class="navbar-buttons">
            <a href="/admin/{{ admin_secret }}" class="nav-btn">← العودة</a>
            <a href="/" class="nav-btn">← الموقع</a>
        </div>
    </div>
    
    <div class="container">
        <form method="POST">
            <div class="section">
                <div class="section-title">🎨 الألوان</div>
                
                <div class="form-group">
                    <label>اللون الأساسي</label>
                    <input type="color" name="main_color" value="{{ main_color }}" style="height: 50px;">
                </div>
                
                <div class="form-group">
                    <label>اللون الثانوي</label>
                    <input type="color" name="secondary_color" value="{{ secondary_color }}" style="height: 50px;">
                </div>
                
                <div class="form-group">
                    <label>لون الخلفية</label>
                    <input type="color" name="background_color" value="{{ background_color }}" style="height: 50px;">
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">✨ الميزات</div>
                
                <div class="toggle-item">
                    <label>مطر الأرقام خلفية</label>
                    <div class="toggle-switch {% if matrix_enabled %}active{% endif %}" 
                         onclick="toggleFeature(this, 'matrix_enabled')"></div>
                    <input type="hidden" name="matrix_enabled" value="{{ matrix_enabled }}">
                </div>
                
                <div class="toggle-item">
                    <label>شريط الأخبار</label>
                    <div class="toggle-switch {% if ticker_enabled %}active{% endif %}" 
                         onclick="toggleFeature(this, 'ticker_enabled')"></div>
                    <input type="hidden" name="ticker_enabled" value="{{ ticker_enabled }}">
                </div>
                
                <div class="toggle-item">
                    <label>مكبر الصوت</label>
                    <div class="toggle-switch {% if sound_enabled %}active{% endif %}" 
                         onclick="toggleFeature(this, 'sound_enabled')"></div>
                    <input type="hidden" name="sound_enabled" value="{{ sound_enabled }}">
                </div>
                
                <div class="toggle-item">
                    <label>زر الإضافة</label>
                    <div class="toggle-switch {% if add_btn_enabled %}active{% endif %}" 
                         onclick="toggleFeature(this, 'add_btn_enabled')"></div>
                    <input type="hidden" name="add_btn_enabled" value="{{ add_btn_enabled }}">
                </div>
                
                <div class="toggle-item">
                    <label>زر الطرح</label>
                    <div class="toggle-switch {% if minus_btn_enabled %}active{% endif %}" 
                         onclick="toggleFeature(this, 'minus_btn_enabled')"></div>
                    <input type="hidden" name="minus_btn_enabled" value="{{ minus_btn_enabled }}">
                </div>
                
                <div class="toggle-item">
                    <label>قسم الأكواد المستقبلة</label>
                    <div class="toggle-switch {% if code_received_section %}active{% endif %}" 
                         onclick="toggleFeature(this, 'code_received_section')"></div>
                    <input type="hidden" name="code_received_section" value="{{ code_received_section }}">
                </div>
                
                <div class="toggle-item">
                    <label>قسم الأكواد المسحوبة</label>
                    <div class="toggle-switch {% if harvested_codes_section %}active{% endif %}" 
                         onclick="toggleFeature(this, 'harvested_codes_section')"></div>
                    <input type="hidden" name="harvested_codes_section" value="{{ harvested_codes_section }}">
                </div>
            </div>
            
            <button type="submit" class="btn">💾 حفظ التغييرات</button>
        </form>
    </div>
    
    <script>
        function toggleFeature(el, name) {
            el.classList.toggle('active');
            const input = document.querySelector(`input[name="${name}"]`);
            input.value = el.classList.contains('active') ? '1' : '0';
        }
    </script>
</body>
</html>
"""

# ========== المسارات ==========
@app.route('/admin/' + ADMIN_SECRET_PATH + '/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = '❌ بيانات غير صحيحة'
    
    admin_color = get_setting('admin_primary_color')
    admin_bg = get_setting('admin_bg_color')
    text_color = get_setting('text_color')
    
    return render_template_string(ADMIN_LOGIN_HTML, error=error, admin_color=admin_color, admin_bg=admin_bg, text_color=text_color)

@app.route('/admin/' + ADMIN_SECRET_PATH + '/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/admin/' + ADMIN_SECRET_PATH)
@admin_required
def admin_dashboard():
    admin_color = get_setting('admin_primary_color')
    admin_bg = get_setting('admin_bg_color')
    text_color = get_setting('text_color')
    admin_secret = ADMIN_SECRET_PATH
    
    return render_template_string(ADMIN_DASHBOARD_HTML, admin_color=admin_color, admin_bg=admin_bg, text_color=text_color, admin_secret=admin_secret)

@app.route('/admin/' + ADMIN_SECRET_PATH + '/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    if request.method == 'POST':
        colors = ['main_color', 'secondary_color', 'background_color']
        features = ['matrix_enabled', 'ticker_enabled', 'sound_enabled', 'add_btn_enabled', 'minus_btn_enabled', 'code_received_section', 'harvested_codes_section']
        
        for color in colors:
            value = request.form.get(color)
            if value:
                set_setting(color, value)
        
        for feature in features:
            value = request.form.get(feature, '0')
            set_setting(feature, value)
        
        admin_log('settings_update', 'تحديث الإعدادات')
    
    admin_color = get_setting('admin_primary_color')
    admin_bg = get_setting('admin_bg_color')
    text_color = get_setting('text_color')
    
    return render_template_string(ADMIN_SETTINGS_HTML,
                                  admin_secret=ADMIN_SECRET_PATH,
                                  admin_color=admin_color,
                                  admin_bg=admin_bg,
                                  text_color=text_color,
                                  main_color=get_setting('main_color'),
                                  secondary_color=get_setting('secondary_color'),
                                  background_color=get_setting('background_color'),
                                  matrix_enabled=get_setting('matrix_enabled'),
                                  ticker_enabled=get_setting('ticker_enabled'),
                                  sound_enabled=get_setting('sound_enabled'),
                                  add_btn_enabled=get_setting('add_btn_enabled'),
                                  minus_btn_enabled=get_setting('minus_btn_enabled'),
                                  code_received_section=get_setting('code_received_section'),
                                  harvested_codes_section=get_setting('harvested_codes_section'))

# ========== الواجهة الرئيسية ==========
@app.route('/')
def index():
    site_title = get_text('site_title')
    site_subtitle = get_text('site_subtitle')
    footer_text = get_text('footer_text')
    ticker_text = get_text('ticker_text')
    
    main_color = get_setting('main_color')
    secondary_color = get_setting('secondary_color')
    bg_color = get_setting('background_color')
    text_color = get_setting('text_color')
    ticker_enabled = get_setting('ticker_enabled')
    
    return render_template_string(MAIN_PAGE_HTML,
                                  site_title=site_title,
                                  site_subtitle=site_subtitle,
                                  footer_text=footer_text,
                                  ticker_text=ticker_text,
                                  main_color=main_color,
                                  secondary_color=secondary_color,
                                  bg_color=bg_color,
                                  text_color=text_color,
                                  ticker_enabled=ticker_enabled,
                                  admin_secret_path=ADMIN_SECRET_PATH)

# ========== API ==========
@app.route('/api/platforms')
def api_platforms():
    return jsonify({'platforms': get_platforms()})

@app.route('/api/countries/<platform>')
def api_countries(platform):
    countries = get_countries_by_platform(platform)
    return jsonify({'countries': countries})

@app.route('/api/number', methods=['POST'])
def api_get_number():
    data = request.json
    platform = data.get('platform')
    country = data.get('country')
    
    if not platform or not country:
        return jsonify({'success': False, 'error': 'بيانات ناقصة'})
    
    numbers = get_numbers_by_platform_country(platform, country)
    if not numbers:
        return jsonify({'success': False, 'error': 'لا توجد أرقام متاحة'})
    
    number = random.choice(numbers)
    return jsonify({'success': True, 'number': number})

@app.route('/api/links')
def api_links():
    links = get_all_links()
    return jsonify({'links': links})

# ========== البوت ==========
def monitor_telegram():
    last_update_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            r = requests.get(url, params={"timeout": 15, "offset": last_update_id + 1}, timeout=20)
            if r.status_code != 200:
                time.sleep(5)
                continue
            
            data = r.json()
            if not data.get('ok'):
                time.sleep(5)
                continue
            
            for upd in data.get('result', []):
                last_update_id = upd['update_id']
                msg = upd.get('message') or upd.get('channel_post')
                if not msg:
                    continue
                
                text = msg.get('text', '') or msg.get('caption', '')
                # معالجة الأكواد من الرسائل
                if text:
                    codes = re.findall(r'\d{4,6}', text)
                    for code in codes:
                        add_otp_log('', code, 'telegram')
                        print(f"✅ [Telegram] {code}")
        
        except Exception as e:
            print(f"❌ خطأ في البوت: {e}")
        
        time.sleep(3)

threading.Thread(target=monitor_telegram, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"""
╔═══════════════════════════════════════════════╗
║   ✨ المطري OTP - شغّال الآن                  ║
║   🌐 http://localhost:{port}                   ║
║   🔧 /admin/{ADMIN_SECRET_PATH}/login        ║
║   👤 admin / admin123                        ║
╚═══════════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=port, debug=False)
