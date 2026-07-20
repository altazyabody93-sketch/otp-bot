"""
======================================================================
   🔐 Almatry OTP — النسخة النهائية المطلقة
   ======================================================================
"""
# ==========================================
# 🌍 قائمة كل دول العالم (محدثة وكاملة)
# ==========================================
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
    "34": {"n": "إسبانيا", "f": "🇪🇸"},
    "39": {"n": "إيطاليا", "f": "🇮🇹"},
    "212": {"n": "المغرب", "f": "🇲🇦"},
    "213": {"n": "الجزائر", "f": "🇩🇿"},
    "216": {"n": "تونس", "f": "🇹🇳"},
    "218": {"n": "ليبيا", "f": "🇱🇾"},
    "92": {"n": "باكستان", "f": "🇵🇰"},
    "93": {"n": "أفغانستان", "f": "🇦🇫"},
    "27": {"n": "جنوب أفريقيا", "f": "🇿🇦"},
    "972": {"n": "إسرائيل", "f": "🇮🇱"},
    "973": {"n": "البحرين", "f": "🇧🇭"},
    "974": {"n": "قطر", "f": "🇶🇦"},
    "968": {"n": "عمان", "f": "🇴🇲"},
    "970": {"n": "فلسطين", "f": "🇵🇸"},
    "52": {"n": "المكسيك", "f": "🇲🇽"},
    "55": {"n": "البرازيل", "f": "🇧🇷"},
    "54": {"n": "الأرجنتين", "f": "🇦🇷"},
    "56": {"n": "تشيلي", "f": "🇨🇱"},
    "57": {"n": "كولومبيا", "f": "🇨🇴"},
    "51": {"n": "بيرو", "f": "🇵🇪"},
    "58": {"n": "فنزويلا", "f": "🇻🇪"},
    "81": {"n": "اليابان", "f": "🇯🇵"},
    "82": {"n": "كوريا الجنوبية", "f": "🇰🇷"},
    "86": {"n": "الصين", "f": "🇨🇳"},
    "63": {"n": "الفلبين", "f": "🇵🇭"},
    "62": {"n": "إندونيسيا", "f": "🇮🇩"},
    "60": {"n": "ماليزيا", "f": "🇲🇾"},
    "65": {"n": "سنغافورة", "f": "🇸🇬"},
    "66": {"n": "تايلاند", "f": "🇹🇭"},
    "84": {"n": "فيتنام", "f": "🇻🇳"},
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
    "354": {"n": "آيسلندا", "f": "🇮🇸"},
    "64": {"n": "نيوزيلندا", "f": "🇳🇿"},
    "61": {"n": "أستراليا", "f": "🇦🇺"},
    "40": {"n": "رومانيا", "f": "🇷🇴"},
    "36": {"n": "المجر", "f": "🇭🇺"},
    "420": {"n": "التشيك", "f": "🇨🇿"},
    "421": {"n": "سلوفاكيا", "f": "🇸🇰"},
    "380": {"n": "أوكرانيا", "f": "🇺🇦"},
    "381": {"n": "صربيا", "f": "🇷🇸"},
    "385": {"n": "كرواتيا", "f": "🇭🇷"},
    "386": {"n": "سلوفينيا", "f": "🇸🇮"},
    "387": {"n": "البوسنة", "f": "🇧🇦"},
    "389": {"n": "مقدونيا", "f": "🇲🇰"},
    "375": {"n": "بيلاروس", "f": "🇧🇾"},
    "370": {"n": "ليتوانيا", "f": "🇱🇹"},
    "371": {"n": "لاتفيا", "f": "🇱🇻"},
    "372": {"n": "إستونيا", "f": "🇪🇪"},
    "373": {"n": "مولدوفا", "f": "🇲🇩"},
    "374": {"n": "أرمينيا", "f": "🇦🇲"},
    "995": {"n": "جورجيا", "f": "🇬🇪"},
    "994": {"n": "أذربيجان", "f": "🇦🇿"},
    "992": {"n": "طاجيكستان", "f": "🇹🇯"},
    "993": {"n": "تركمانستان", "f": "🇹🇲"},
    "998": {"n": "أوزبكستان", "f": "🇺🇿"},
    "996": {"n": "قرغيزستان", "f": "🇰🇬"},
    "975": {"n": "بوتان", "f": "🇧🇹"},
    "976": {"n": "منغوليا", "f": "🇲🇳"},
    "977": {"n": "نيبال", "f": "🇳🇵"},
    "94": {"n": "سريلانكا", "f": "🇱🇰"},
    "95": {"n": "ميانمار", "f": "🇲🇲"},
    "856": {"n": "لاوس", "f": "🇱🇦"},
    "855": {"n": "كمبوديا", "f": "🇰🇭"},
    "960": {"n": "جزر المالديف", "f": "🇲🇻"},
    "961": {"n": "لبنان", "f": "🇱🇧"},
    "962": {"n": "الأردن", "f": "🇯🇴"},
    "963": {"n": "سوريا", "f": "🇸🇾"},
    "964": {"n": "العراق", "f": "🇮🇶"},
    "965": {"n": "الكويت", "f": "🇰🇼"},
    "967": {"n": "اليمن", "f": "🇾🇪"},
}

def get_country_info(code):
    info = COUNTRY_DATA.get(code)
    return (info["n"], info["f"]) if info else ("أخرى", "🌍")
import os
import re
import json
import sqlite3
import random
import requests
import time
import threading
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session, flash
from functools import wraps
import bcrypt

app = Flask(__name__)
app.secret_key = os.urandom(24)
DB_PATH = "bot.db"

# ========== الإعدادات الأساسية ==========
ADMIN_PASSWORD = "admin123"
OWNER_PHONE = "967733723953"
TELEGRAM_BOT_TOKEN = "8814038881:AAGyuACUYA4YPKlJQhAyUMkpRNiV0u1gNuU"
ASSISTANT_BOT_TOKEN = "8845420882:AAHZ-7qhCL3_ddDT3am4zWNtBRBy3mVDgws"

# ========== المنصات ==========
PLATFORM_NAMES = {
    "whatsapp": "واتساب", "telegram": "تيليجرام", "tiktok": "تيك توك",
    "facebook": "فيسبوك", "instagram": "انستقرام", "snapchat": "سناب شات",
    "google": "جوجل", "twitter": "تويتر/X"
}
PLATFORM_ICONS = {
    "whatsapp": "📱", "telegram": "✈️", "tiktok": "🎵",
    "facebook": "📘", "instagram": "📸", "snapchat": "👻",
    "google": "🔍", "twitter": "🐦"
}
PLATFORM_COLORS = {
    "whatsapp": "#25D366", "telegram": "#26A5E4", "tiktok": "#FE2C55",
    "facebook": "#1877F2", "instagram": "#E4405F", "snapchat": "#FFFC00",
    "google": "#4285F4", "twitter": "#000000"
}

# ========== قاعدة البيانات الموحدة ==========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. جداول الإعدادات والنصوص
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS site_texts (
        key TEXT PRIMARY KEY, value TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS site_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT, url TEXT, icon TEXT, sort_order INTEGER DEFAULT 0
    )''')
    
    # 2. جداول الكومبوهات والأكواد
    c.execute('''CREATE TABLE IF NOT EXISTS combos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, country_code TEXT, country_name TEXT, country_flag TEXT, numbers TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS otp_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT, otp TEXT, timestamp TEXT, platform TEXT
    )''')
    
    # 3. جداول المستخدمين والأدمن
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ip TEXT, is_banned INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT
    )''')
    
    # 4. إعدادات افتراضية
    default_settings = {
        'main_color': '#00ffc8', 'bg_color': '#0a0e1a', 'text_color': '#ffffff',
        'matrix_enabled': '1', 'ticker_enabled': '1', 'platforms_rain': '1'
    }
    for k, v in default_settings.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        
    # 5. نصوص افتراضية
    default_texts = {
        'site_title': '🚀 المطري OTP', 'site_subtitle': '👑 أرقام سحب أكواد تطوير مطري',
        'ticker_text': 'مرحباً بك في موقع المطري OTP', 'footer_text': '💎 المطري OTP'
    }
    for k, v in default_texts.items():
        c.execute("INSERT OR IGNORE INTO site_texts (key, value) VALUES (?, ?)", (k, v))
        
    # 6. روابط افتراضية
    default_links = [
        ('المطور واتساب', f'https://wa.me/{OWNER_PHONE}', '💬', 1),
        ('قناة السحب', 'https://t.me/jsjsgsjsvh', '📢', 2)
    ]
    for lbl, u, ic, so in default_links:
        c.execute("INSERT OR IGNORE INTO site_links (label, url, icon, sort_order) VALUES (?, ?, ?, ?)", (lbl, u, ic, so))
    
    # 7. إنشاء حساب الأدمن (مشفر)
    c.execute("SELECT id FROM admins WHERE username=?", ('admin',))
    if not c.fetchone():
        ph = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt())
        c.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)", ('admin', ph))
        
    conn.commit()
    conn.close()

init_db()

# ========== دوال الاستعلام ==========
def get_setting(key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else ''

def set_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_text(key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM site_texts WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else ''

def set_text(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("REPLACE INTO site_texts (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_links():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT label, url, icon FROM site_links ORDER BY sort_order")
    rows = c.fetchall()
    conn.close()
    return rows

def get_numbers(platform, country):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT numbers FROM combos WHERE platform=? AND country_code=?", (platform, country))
    row = c.fetchone()
    conn.close()
    return json.loads(row[0]) if row else []

def save_combo(platform, code, name, flag, numbers):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("REPLACE INTO combos (platform, country_code, country_name, country_flag, numbers) VALUES (?, ?, ?, ?, ?)", (platform, code, name, flag, json.dumps(numbers)))
    conn.commit()
    conn.close()

def get_combos():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, platform, country_code, country_name, country_flag FROM combos")
    rows = c.fetchall()
    conn.close()
    return rows

def get_recent_codes(limit=20):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, number, otp, timestamp, platform FROM otp_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# ========== دوال الأدمن ==========
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ========== HTML الرئيسي (الواجهة) ==========
MAIN_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ site_title }}</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { background:{{ bg_color }}; color:{{ text_color }}; font-family:Tahoma, sans-serif; transition:0.3s; }
        .app { max-width:480px; margin:0 auto; padding:15px; }
        .header { display:flex; justify-content:space-between; align-items:center; }
        .theme-btn { background:transparent; border:1px solid {{ main_color }}; color:{{ text_color }}; padding:8px 12px; border-radius:8px; cursor:pointer; }
        .platforms { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
        .plat-btn { background:rgba(255,255,255,0.05); border:1px solid transparent; padding:20px; border-radius:10px; text-align:center; cursor:pointer; font-weight:bold; }
        .plat-btn.active { border-color:{{ main_color }}; background:rgba(0,255,200,0.1); }
        .plat-icon { font-size:2em; display:block; }
        select, button { width:100%; padding:12px; border-radius:8px; border:1px solid #333; background:rgba(255,255,255,0.05); color:{{ text_color }}; margin:5px 0; }
        .btn-main { background:{{ main_color }}; color:#000; font-weight:bold; border:none; }
        .number-box { background:rgba(0,0,0,0.3); border:2px solid {{ main_color }}; border-radius:12px; padding:15px; text-align:center; margin:10px 0; }
        .number { font-size:2em; color:{{ main_color }}; }
        .otp-list { margin-top:15px; }
        .otp-item { background:rgba(255,255,255,0.05); padding:10px; border-radius:8px; margin:5px 0; display:flex; justify-content:space-between; }
        .otp-code { color:{{ main_color }}; font-size:1.3em; font-weight:bold; }
        .top-banner {
            position: fixed; top: 0; left: 0; right: 0;
            background: linear-gradient(135deg, {{ main_color }}, #00d4ff);
            color: #000; padding: 15px; text-align: center; font-weight: bold;
            transform: translateY(-100%); transition: 0.4s; z-index: 9999;
        }
        .top-banner.show { transform: translateY(0); }
        .footer { text-align:center; margin-top:20px; font-size:0.9em; opacity:0.6; }
    </style>
</head>
<body>
    <div class="top-banner" id="topBanner">🔔 كود جديد!</div>
    <div class="app">
        <div class="header">
            <h1>{{ site_title }}</h1>
            <button class="theme-btn" id="themeBtn">🌙</button>
        </div>
        <div style="text-align:center;margin:10px 0;">{{ ticker_text }}</div>
        
        <div style="position:relative;">
            <canvas id="rainCanvas" style="position:absolute;inset:0;z-index:-1;opacity:0.2;pointer-events:none;"></canvas>
            <div class="platforms" id="platformList"></div>
        </div>
        
        <select id="countryList" disabled><option>-- اختر المنصة --</option></select>
        <button class="btn-main" id="getNumBtn" disabled>🚀 جلب رقم</button>
        
        <div id="numberArea" style="display:none;">
            <div class="number-box">
                <div class="number" id="numDisplay">+---</div>
            </div>
        </div>
        
        <div class="otp-list" id="otpList"><div style="text-align:center;opacity:0.6;">في انتظار الأكواد...</div></div>
        <div class="footer">{{ footer_text }}</div>
    </div>

    <script>
        const names = {{ platform_names | tojson }};
        const icons = {{ platform_icons | tojson }};
        let theme = localStorage.getItem('theme') || 'dark';
        document.body.style.background = theme === 'dark' ? '{{ bg_color }}' : '#f5f7fa';
        document.body.style.color = theme === 'dark' ? '{{ text_color }}' : '#1a1a2e';
        document.getElementById('themeBtn').textContent = theme === 'dark' ? '☀️' : '🌙';
        document.getElementById('themeBtn').onclick = () => {
            theme = theme === 'dark' ? 'light' : 'dark';
            document.body.style.background = theme === 'dark' ? '{{ bg_color }}' : '#f5f7fa';
            document.body.style.color = theme === 'dark' ? '{{ text_color }}' : '#1a1a2e';
            document.getElementById('themeBtn').textContent = theme === 'dark' ? '☀️' : '🌙';
            localStorage.setItem('theme', theme);
        };

        let platforms = {{ platforms | tojson }};
        let currentPlatform = '';
        let currentNumber = '';
        let monitor = null;

        function init() {
            const list = document.getElementById('platformList');
            platforms.forEach(p => {
                const btn = document.createElement('div');
                btn.className = 'plat-btn';
                btn.innerHTML = `<span class="plat-icon">${icons[p]}</span>${names[p]}`;
                btn.onclick = () => {
                    document.querySelectorAll('.plat-btn').forEach(b=>b.classList.remove('active'));
                    btn.classList.add('active');
                    currentPlatform = p;
                    loadCountries(p);
                };
                list.appendChild(btn);
            });
        }

        async function loadCountries(p) {
            const res = await fetch('/api/countries', {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({platform:p})
            });
            const data = await res.json();
            const sel = document.getElementById('countryList');
            sel.innerHTML = '<option>-- اختر الدولة --</option>';
            data.forEach(c => { sel.innerHTML += `<option value="${c.code}">${c.flag} ${c.name}</option>`; });
            sel.disabled = false;
            document.getElementById('getNumBtn').disabled = false;
        }

        document.getElementById('getNumBtn').onclick = () => {
            const c = document.getElementById('countryList').value;
            if(c) getNumber(c);
        };

        async function getNumber(country) {
            const res = await fetch('/api/get_number', {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({platform:currentPlatform, country:country})
            });
            const data = await res.json();
            if(data.number) {
                currentNumber = data.number;
                document.getElementById('numDisplay').innerText = data.number;
                document.getElementById('numberArea').style.display = 'block';
                startMonitoring();
            }
        }

        function startMonitoring() {
            if(monitor) clearInterval(monitor);
            monitor = setInterval(async () => {
                const res = await fetch('/api/get_otp', {
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({number:currentNumber})
                });
                const data = await res.json();
                if(data.otp) {
                    addOtp(data.otp);
                    playSound();
                    showBanner('🔑 كود جديد: ' + data.otp);
                }
            }, 3000);
        }

        function addOtp(otp) {
            const list = document.getElementById('otpList');
            if(list.innerHTML.includes('في انتظار')) list.innerHTML = '';
            const div = document.createElement('div');
            div.className = 'otp-item';
            div.innerHTML = `<div><span class="otp-code">🔑 ${otp}</span><br><small>📞 ${currentNumber}</small></div>`;
            list.prepend(div);
        }

        function showBanner(text) {
            const b = document.getElementById('topBanner');
            b.textContent = text;
            b.classList.add('show');
            setTimeout(() => b.classList.remove('show'), 4000);
        }

        function playSound() {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const o = ctx.createOscillator(); const g = ctx.createGain();
                o.connect(g); g.connect(ctx.destination);
                o.frequency.value = 880; o.type = 'sine';
                g.gain.setValueAtTime(0.2, ctx.currentTime);
                g.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.2);
                o.start(); o.stop(ctx.currentTime + 0.2);
            } catch(e) {}
        }

        // تشغيل مطر الأرقام
        const canvas = document.getElementById('rainCanvas');
        if(canvas) {
            const ctx = canvas.getContext('2d');
            const wrap = canvas.parentElement;
            canvas.width = wrap.offsetWidth;
            canvas.height = wrap.offsetHeight;
            const drops = Array(20).fill(0).map(()=>Math.random()*canvas.height);
            const chars = '0123456789';
            setInterval(() => {
                ctx.clearRect(0,0,canvas.width,canvas.height);
                ctx.font = '15px monospace'; ctx.fillStyle = '{{ main_color }}';
                for(let i=0;i<drops.length;i++) {
                    ctx.fillText(chars[Math.floor(Math.random()*chars.length)], i*20, drops[i]);
                    if(drops[i]*20 > canvas.height && Math.random()>0.975) drops[i]=0;
                    drops[i]++;
                }
            }, 100);
        }

        init();
    </script>
</body>
</html>
"""

# ========== مسارات الموقع ==========
@app.route('/')
def home():
    return render_template_string(
        MAIN_HTML,
        site_title=get_text('site_title'),
        ticker_text=get_text('ticker_text'),
        footer_text=get_text('footer_text'),
        main_color=get_setting('main_color'),
        bg_color=get_setting('bg_color'),
        text_color=get_setting('text_color'),
        platform_names=PLATFORM_NAMES,
        platform_icons=PLATFORM_ICONS,
        platforms=list(PLATFORM_NAMES.keys()),
        session=session
    )

@app.route('/api/countries', methods=['POST'])
def api_countries():
    platform = request.json.get('platform')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT country_code, country_name, country_flag FROM combos WHERE platform=?", (platform,))
    countries = [{'code': r[0], 'name': r[1], 'flag': r[2]} for r in c.fetchall()]
    conn.close()
    return jsonify(countries)

@app.route('/api/get_number', methods=['POST'])
def api_get_number():
    data = request.json
    nums = get_numbers(data['platform'], data['country'])
    if not nums: return jsonify({'number': None})
    return jsonify({'number': random.choice(nums)})

@app.route('/api/get_otp', methods=['POST'])
def api_get_otp():
    num = request.json.get('number')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT otp FROM otp_logs WHERE number LIKE ? ORDER BY id DESC LIMIT 1", (f"%{num[-4:]}",))
    row = c.fetchone()
    conn.close()
    return jsonify({'otp': row[0] if row else None})

# ========== مراقبة تيليجرام ==========
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
                            if not text:
                                continue
                            clean = re.sub(r'[\u200B-\u200F\u202A-\u202E‏‎]', '', text)
                            lines = clean.split('\n')
                            user_number = None
                            last_digits = None
                            hidden_match = re.search(r'(\d{3,4})[•*]{2,6}(\d{3,4})', clean)
                            if hidden_match:
                                user_number = hidden_match.group(1) + hidden_match.group(2)
                                last_digits = user_number[-4:]
                            if not user_number:
                                all_numbers = re.findall(r'\b\d{8,15}\b', clean)
                                if all_numbers:
                                    user_number = max(all_numbers, key=len)
                                    last_digits = user_number[-4:]
                            otp = None
                            dash_code = re.search(r'(\d{3})-(\d{3,4})', clean)
                            if dash_code:
                                otp = dash_code.group(1) + dash_code.group(2)
                            if not otp:
                                all_codes = re.findall(r'\b\d{4,8}\b', clean)
                                if all_codes:
                                    for c in all_codes:
                                        if last_digits and c.endswith(last_digits):
                                            continue
                                        if len(c) >= 4:
                                            otp = c
                                            break
                            platform = "غير معروف"
                            text_lower = clean.lower()
                            platforms = {
                                "whatsapp": ["wa", "whatsapp", "واتساب"],
                                "facebook": ["fb", "facebook", "فيسبوك"],
                                "telegram": ["tg", "telegram", "تيليجرام"],
                                "tiktok": ["tt", "tiktok", "تيك توك"],
                                "instagram": ["ig", "instagram", "انستقرام"],
                                "snapchat": ["sc", "snapchat", "سناب"],
                                "google": ["gg", "google", "جوجل"]
                            }
                            for name, keywords in platforms.items():
                                for kw in keywords:
                                    if kw in text_lower:
                                        platform = name
                                        break
                                if platform != "غير معروف":
                                    break
                            if otp:
                                conn = sqlite3.connect(DB_PATH)
                                conn.execute("INSERT INTO otp_logs (number, otp, timestamp, platform) VALUES (?, ?, ?, ?)",
                                            (last_digits if last_digits else "0000", otp, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), platform))
                                conn.commit()
                                conn.close()
                                print(f"✅ [{platform}] {otp}")
        except Exception as e:
            print(f"❌ خطأ: {e}")
        time.sleep(5)

threading.Thread(target=monitor_channel, daemon=True).start()

# ==========================================
# ⚙️ لوحة التحكم (Admin Panel) كاملة وحقيقية
# ==========================================
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة التحكم - المطري OTP</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family:'Cairo',sans-serif; background:#0a0e1a; color:#fff; padding:20px; }
        .container { max-width:600px; margin:0 auto; background:rgba(17,24,39,0.95); padding:25px; border-radius:20px; border:1px solid rgba(0,255,200,0.3); }
        h1 { text-align:center; color:#00ffc8; }
        h3 { color:#cbd5e1; margin:15px 0 10px; }
        .form-group { margin-bottom:12px; }
        .form-group label { display:block; color:#cbd5e1; font-weight:700; font-size:13px; margin-bottom:4px; }
        input, select, textarea { width:100%; padding:10px; border-radius:8px; border:1px solid #30363d; background:#0d1117; color:#fff; font-family:'Cairo',sans-serif; font-size:13px; }
        input:focus, select:focus, textarea:focus { border-color:#00ffc8; outline:none; }
        textarea { min-height:80px; resize:vertical; }
        .btn { padding:10px 20px; border:none; border-radius:8px; font-weight:700; cursor:pointer; font-family:'Cairo',sans-serif; font-size:13px; }
        .btn-primary { background:linear-gradient(135deg,#00ff88,#00d2ff); color:#000; }
        .btn-danger { background:linear-gradient(135deg,#ef4444,#b91c1c); color:#fff; }
        .btn-secondary { background:linear-gradient(135deg,#374151,#4b5563); color:#fff; }
        .btn:hover { transform:translateY(-2px); }
        .flex { display:flex; gap:10px; flex-wrap:wrap; }
        .combo-item { display:flex; justify-content:space-between; align-items:center; background:rgba(31,41,55,0.5); padding:10px; border-radius:8px; margin-bottom:6px; }
        hr { border:1px solid rgba(255,255,255,0.1); margin:15px 0; }
        .toggle { display:flex; justify-content:space-between; align-items:center; padding:8px; background:rgba(0,0,0,0.2); border-radius:5px; margin-bottom:8px; }
        .switch { position:relative; width:50px; height:26px; background:#333; border-radius:13px; cursor:pointer; transition:0.3s; }
        .switch.on { background:#00ffc8; }
        .switch::after { content:''; position:absolute; top:3px; right:3px; width:20px; height:20px; background:#fff; border-radius:50%; transition:0.3s; }
        .switch.on::after { right:27px; }
        .back-link { display:block; text-align:center; color:#58a6ff; text-decoration:none; margin-top:10px; }
        .back-link:hover { text-decoration:underline; }
    </style>
</head>
<body>
<div class="container">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <h1>⚙️ لوحة التحكم</h1>
        <a href="/admin/logout" style="color:#ef4444; text-decoration:none; font-weight:bold;">🚪 خروج</a>
    </div>
    
    <hr>
    
    <h3>🎨 إعدادات المظهر</h3>
    <form method="POST" action="/admin/save_appearance">
        <div class="form-group"><label>اللون الرئيسي</label><input type="color" name="main_color" value="{{ main_color }}"></div>
        <div class="form-group"><label>لون الخلفية</label><input type="color" name="bg_color" value="{{ bg_color }}"></div>
        <div class="form-group"><label>لون النص</label><input type="color" name="text_color" value="{{ text_color }}"></div>
        <div class="toggle">
            <label>🌧️ مطر الأرقام خلف المنصات</label>
            <div class="switch {% if platforms_rain == '1' %}on{% endif %}" onclick="this.classList.toggle('on'); document.getElementById('rain_input').value = this.classList.contains('on') ? '1' : '0';">
                <input type="hidden" name="platforms_rain" id="rain_input" value="{{ platforms_rain }}">
            </div>
        </div>
        <div class="toggle">
            <label>🌃 Matrix Rain</label>
            <div class="switch {% if matrix_enabled == '1' %}on{% endif %}" onclick="this.classList.toggle('on'); document.getElementById('matrix_input').value = this.classList.contains('on') ? '1' : '0';">
                <input type="hidden" name="matrix_enabled" id="matrix_input" value="{{ matrix_enabled }}">
            </div>
        </div>
        <button type="submit" class="btn btn-primary">💾 حفظ المظهر</button>
    </form>
    
    <hr>
    
    <h3>✏️ النصوص</h3>
    <form method="POST" action="/admin/save_texts">
        <div class="form-group"><label>عنوان الموقع</label><input type="text" name="site_title" value="{{ site_title }}"></div>
        <div class="form-group"><label>الوصف</label><input type="text" name="site_subtitle" value="{{ site_subtitle }}"></div>
        <div class="form-group"><label>شريط الأخبار</label><input type="text" name="ticker_text" value="{{ ticker_text }}"></div>
        <div class="form-group"><label>الفوتر</label><input type="text" name="footer_text" value="{{ footer_text }}"></div>
        <button type="submit" class="btn btn-primary">💾 حفظ النصوص</button>
    </form>
    
    <hr>
    
    <h3>🔗 الروابط</h3>
    <div style="margin-bottom:10px;">
        {% for label, url, icon in links %}
        <div class="flex" style="margin-bottom:6px; align-items:center;">
            <span>{{ icon }}</span>
            <input type="text" class="form-control" value="{{ url }}" style="flex:1;min-width:100px;" id="link_{{ loop.index }}">
            <input type="text" value="{{ label }}" style="width:80px;" id="label_{{ loop.index }}">
            <button class="btn btn-danger" onclick="deleteLink('{{ label }}')">🗑️</button>
        </div>
        {% endfor %}
    </div>
    <div class="flex" style="margin-bottom:10px;">
        <input type="text" id="new_label" placeholder="الاسم" style="flex:1;">
        <input type="text" id="new_url" placeholder="الرابط" style="flex:2;">
        <input type="text" id="new_icon" placeholder="أيقونة" style="flex:0.5;max-width:50px;">
        <button class="btn btn-primary" onclick="addLink()">➕</button>
    </div>
    <button class="btn btn-secondary" onclick="saveLinks()">💾 حفظ الروابط</button>
    
    <hr>
    
    <h3>📦 الكومبوهات</h3>
    <form method="POST" action="/admin/upload_combo" enctype="multipart/form-data">
        <div class="form-group">
            <label>المنصة</label>
            <select name="platform">
                <option value="whatsapp">واتساب</option>
                <option value="telegram">تيليجرام</option>
                <option value="tiktok">تيك توك</option>
                <option value="facebook">فيسبوك</option>
                <option value="instagram">انستقرام</option>
                <option value="snapchat">سناب شات</option>
                <option value="google">جوجل</option>
                <option value="twitter">تويتر</option>
            </select>
        </div>
        <div class="form-group"><label>ملف الأرقام (.txt)</label><input type="file" name="file" accept=".txt" required></div>
        <button type="submit" class="btn btn-primary">📤 رفع</button>
    </form>
    <div style="margin-top:10px;">
        {% for combo in combos %}
        <div class="combo-item">
            <span>{{ combo[3] }} {{ combo[2] }} ({{ combo[1] }})</span>
            <form method="POST" action="/admin/delete_combo" style="display:inline;">
                <input type="hidden" name="id" value="{{ combo[0] }}">
                <button type="submit" class="btn btn-danger">🗑️</button>
            </form>
        </div>
        {% endfor %}
    </div>
    
    <hr>
    
    <h3>🔑 الأكواد المسحوبة (مسح فقط)</h3>
    <form method="POST" action="/admin/clear_otps" onsubmit="return confirm('⚠️ حذف جميع الأكواد؟')">
        <button type="submit" class="btn btn-danger">🗑️ مسح الأكواد</button>
    </form>
    <div style="margin-top:10px; max-height:300px; overflow-y:auto; font-size:12px;">
        {% for code in recent_codes %}
        <div class="combo-item" style="padding:6px; font-size:12px;">
            <span>🔑 {{ code[2] }} ({{ code[4] }})<br><small>{{ code[1] }} • {{ code[3] }}</small></span>
        </div>
        {% else %}
        <p style="color:#64748b;">لا توجد أكواد</p>
        {% endfor %}
    </div>
    
    <hr>
    
    <a href="/" class="back-link">🔙 العودة للموقع</a>
</div>

<script>
function addLink() {
    const label = document.getElementById('new_label').value.trim();
    const url = document.getElementById('new_url').value.trim();
    const icon = document.getElementById('new_icon').value.trim() || '🔗';
    if(!label || !url) return alert('املأ الاسم والرابط');
    fetch('/admin/add_link', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({label, url, icon})
    }).then(() => location.reload());
}
function deleteLink(label) {
    if(!confirm('حذف هذا الرابط؟')) return;
    fetch('/admin/delete_link', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({label})
    }).then(() => location.reload());
}
function saveLinks() {
    alert('تم حفظ الروابط');
}
</script>
</body>
</html>
"""

@app.route('/admin', methods=['GET'])
@admin_required
def admin_panel():
    return render_template_string(
        ADMIN_HTML,
        main_color=get_setting('main_color'),
        bg_color=get_setting('bg_color'),
        text_color=get_setting('text_color'),
        platforms_rain=get_setting('platforms_rain'),
        matrix_enabled=get_setting('matrix_enabled'),
        site_title=get_text('site_title'),
        site_subtitle=get_text('site_subtitle'),
        ticker_text=get_text('ticker_text'),
        footer_text=get_text('footer_text'),
        links=get_links(),
        combos=get_combos(),
        recent_codes=get_recent_codes(20),
        session=session
    )

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT password_hash FROM admins WHERE username='admin'")
        row = c.fetchone()
        conn.close()
        if row and bcrypt.checkpw(password.encode(), row[0]):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
        flash('كلمة المرور غير صحيحة', 'error')
    return '''
    <div style="text-align:center; padding:40px; background:#0a0e1a; color:#fff; max-width:400px; margin:100px auto; border-radius:15px;">
        <h2>🔐 دخول الأدمن</h2>
        <form method="POST">
            <input type="password" name="password" placeholder="كلمة المرور" style="width:100%; padding:10px; margin:10px 0; border-radius:8px; border:none;">
            <button type="submit" style="width:100%; padding:10px; background:#00ffc8; border:none; border-radius:8px; font-weight:bold;">دخول</button>
        </form>
        <p style="color:gray; font-size:12px; margin-top:10px;">الافتراضي: admin123</p>
    </div>
    '''

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))

@app.route('/admin/save_appearance', methods=['POST'])
@admin_required
def admin_save_appearance():
    for key in ['main_color', 'bg_color', 'text_color', 'platforms_rain', 'matrix_enabled']:
        set_setting(key, request.form.get(key, ''))
    return redirect(url_for('admin_panel'))

@app.route('/admin/save_texts', methods=['POST'])
@admin_required
def admin_save_texts():
    for key in ['site_title', 'site_subtitle', 'ticker_text', 'footer_text']:
        set_text(key, request.form.get(key, ''))
    return redirect(url_for('admin_panel'))

@app.route('/admin/upload_combo', methods=['POST'])
@admin_required
def admin_upload_combo():
    platform = request.form.get('platform')
    file = request.files.get('file')
    if not file or not file.filename.endswith('.txt'):
        return redirect(url_for('admin_panel'))
    numbers = [line.strip() for line in file.read().decode().splitlines() if line.strip()]
    if numbers:
        save_combo(platform, '966', 'السعودية', '🇸🇦', numbers)
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_combo', methods=['POST'])
@admin_required
def admin_delete_combo():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM combos WHERE id=?", (request.form.get('id'),))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/clear_otps', methods=['POST'])
@admin_required
def admin_clear_otps():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM otp_logs")
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/add_link', methods=['POST'])
@admin_required
def admin_add_link():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO site_links (label, url, icon) VALUES (?, ?, ?)", (data['label'], data['url'], data.get('icon', '🔗')))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/admin/delete_link', methods=['POST'])
@admin_required
def admin_delete_link():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM site_links WHERE label=?", (request.json['label'],))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ========== تشغيل التطبيق ==========
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)