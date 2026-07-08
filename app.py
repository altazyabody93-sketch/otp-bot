from flask import Flask, request, render_template_string, jsonify, redirect, url_for
import sqlite3
import json
import random
import os
import re
import requests
import threading
import time
from datetime import datetime

app = Flask(__name__)
DB_PATH = "bot.db"

WHATSAPP_GROUP_LINK = "https://chat.whatsapp.com/IeK2gNS64fd8YSnenzt4WR"
OWNER_PHONE = "967733723953"
OWNER_LINK = f"https://wa.me/{OWNER_PHONE}"

TELEGRAM_BOT_TOKEN = "8814038881:AAGyuACUYA4YPKlJQhAyUMkpRNiV0u1gNuU"
CHANNEL_USERNAME = "@jsjsgsjsvh"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS combos (id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, country_code TEXT, country_name TEXT, country_flag TEXT, numbers TEXT, UNIQUE(platform, country_code))''')
    c.execute('''CREATE TABLE IF NOT EXISTS otp_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT, otp TEXT, timestamp TEXT, platform TEXT)''')
    conn.commit()
    conn.close()
init_db()

# ========== جميع دول العالم (أكثر من 195 دولة) ==========
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
    "380": {"n": "أوكرانिया", "f": "🇺🇦"},
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
    "355": {"n": "ألبانيا", "f": "🇦🇱"},
    "356": {"n": "مالطا", "f": "🇲🇹"},
    "357": {"n": "قبرص", "f": "🇨🇾"},
    "358": {"n": "فنلندا", "f": "🇫🇮"},
    "359": {"n": "بلغارיה", "f": "🇧🇬"},
    "350": {"n": "جبل طارق", "f": "🇬🇮"},
    "352": {"n": "لوكسمبورغ", "f": "🇱🇺"},
    "423": {"n": "ليختنشتاين", "f": "🇱🇮"},
    "377": {"n": "موناكو", "f": "🇲🇨"},
    "378": {"n": "سان مارينو", "f": "🇸🇲"},
    "379": {"n": "الفاتيكان", "f": "🇻🇦"},
    "500": {"n": "جزر فوكلاند", "f": "🇫🇰"},
    "501": {"n": "بليز", "f": "🇧🇿"},
    "502": {"n": "غواتيمالا", "f": "🇬🇹"},
    "503": {"n": "السلفادور", "f": "🇸🇻"},
    "504": {"n": "هندوراس", "f": "🇭🇳"},
    "505": {"n": "نيكاراغوا", "f": "🇳🇮"},
    "506": {"n": "كوستاريكا", "f": "🇨🇷"},
    "507": {"n": "بنما", "f": "🇵🇦"},
    "509": {"n": "هايتي", "f": "🇭🇹"},
    "590": {"n": "غوادلوب", "f": "🇬🇵"},
    "591": {"n": "بوليفيا", "f": "🇧🇴"},
    "592": {"n": "غيانا", "f": "🇬🇾"},
    "593": {"n": "الإكوادور", "f": "🇪🇨"},
    "594": {"n": "غويانا الفرنسية", "f": "🇬🇫"},
    "595": {"n": "باراغواي", "f": "🇵🇾"},
    "596": {"n": "مارتينيك", "f": "🇲🇶"},
    "597": {"n": "سورينام", "f": "🇸🇷"},
    "598": {"n": "أوروغواي", "f": "🇺🇾"},
    "670": {"n": "تيمور الشرقية", "f": "🇹🇱"},
    "673": {"n": "بروناي", "f": "🇧🇳"},
    "674": {"n": "ناورو", "f": "🇳🇷"},
    "675": {"n": "بابوا غينيا الجديدة", "f": "🇵🇬"},
    "676": {"n": "تونغا", "f": "🇹🇴"},
    "677": {"n": "جزر سليمان", "f": "🇸🇧"},
    "678": {"n": "فانواتو", "f": "🇻🇺"},
    "679": {"n": "فيجي", "f": "🇫🇯"},
    "680": {"n": "بالاو", "f": "🇵🇼"},
    "682": {"n": "جزر كوك", "f": "🇨🇰"},
    "685": {"n": "ساموا", "f": "🇼🇸"},
    "686": {"n": "كيريباتي", "f": "🇰🇮"},
    "687": {"n": "كاليدونيا الجديدة", "f": "🇳🇨"},
    "688": {"n": "توفالو", "f": "🇹🇻"},
    "689": {"n": "بولينيزيا الفرنسية", "f": "🇵🇫"},
    "691": {"n": "ولايات ميكرونيسيا", "f": "🇫🇲"},
    "692": {"n": "جزر مارشال", "f": "🇲🇭"},
    "850": {"n": "كوريا الشمالية", "f": "🇰🇵"},
    "852": {"n": "هونغ كونغ", "f": "🇭🇰"},
    "853": {"n": "ماكاو", "f": "🇲🇴"},
    "855": {"n": "كمبوديا", "f": "🇰🇭"},
    "856": {"n": "لاوس", "f": "🇱🇦"},
    "880": {"n": "بنغلاديش", "f": "🇧🇩"},
    "886": {"n": "تايوان", "f": "🇹🇼"},
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
    c.execute("REPLACE INTO combos (platform, country_code, country_name, country_flag, numbers) VALUES (?, ?, ?, ?, ?)", (platform, country_code, country_name, country_flag, json.dumps(numbers)))
    conn.commit()
    conn.close()

PLATFORM_LOGOS = {
    "whatsapp": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/WhatsApp.svg/48px-WhatsApp.svg.png",
    "telegram": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Telegram_logo.svg/48px-Telegram_logo.svg.png",
    "tiktok": "https://upload.wikimedia.org/wikipedia/en/thumb/a/a9/TikTok_logo.svg/48px-TikTok_logo.svg.png",
    "facebook": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Facebook_Logo_%282019%29.png/48px-Facebook_Logo_%282019%29.png",
    "instagram": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/Instagram_logo_2016.svg/48px-Instagram_logo_2016.svg.png",
    "snapchat": "https://upload.wikimedia.org/wikipedia/en/thumb/c/c4/Snapchat_logo.svg/48px-Snapchat_logo.svg.png",
    "google": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Google_%22G%22_Logo.svg/48px-Google_%22G%22_Logo.svg.png",
    "twitter": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/X_logo_2023.svg/48px-X_logo_2023.svg.png",
}

platform_names = {'whatsapp': 'واتساب', 'telegram': 'تيليجرام', 'tiktok': 'تيك توك', 'facebook': 'فيسبوك', 'instagram': 'انستقرام', 'snapchat': 'سناب شات', 'google': 'جوجل', 'twitter': 'تويتر/X'}

# ===== ألوان المنصات (عند النقر) =====
platform_colors = {
    "whatsapp": "#25D366",
    "telegram": "#0088cc",
    "tiktok": "#000000",
    "facebook": "#1877f2",
    "instagram": "#E4405F",
    "snapchat": "#FFFC00",
    "google": "#4285F4",
    "twitter": "#1DA1F2"
}

main_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>🚀بوت المطري OTP🚀</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap" rel="stylesheet">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family:'Cairo',sans-serif; background:#0b0e17; color:#fff; display:flex; justify-content:center; align-items:center; min-height:100vh; }
        .container { background:#111827; padding:30px; border-radius:25px; width:100%; max-width:100%; min-height:100vh; border:1px solid #1f2937; }
        .top-bar { display:flex; justify-content:flex-end; margin-bottom:15px; position:relative; }
        .menu-btn { background:#1f2937; border:none; border-radius:10px; padding:10px 15px; color:#fff; font-size:20px; cursor:pointer; }
        .dropdown-menu { display:none; position:absolute; top:50px; right:0; background:#1f2937; border:1px solid #374151; border-radius:10px; padding:10px; min-width:150px; z-index:100; box-shadow:0 5px 15px rgba(0,0,0,0.5); }
        .dropdown-menu a { display:block; color:#fff; text-decoration:none; padding:8px 10px; border-radius:8px; }
        .dropdown-menu a:hover { background:#374151; }
        .dropdown-menu.show { display:block; }
        .header { text-align:center; margin-bottom:25px; }
        .header h1 { color:#00d2ff; font-size:26px; }
        .header p { color:#9ca3af; font-size:16px; margin-top:5px; }
        .form-group { margin-bottom:20px; }
        .form-group label { display:block; margin-bottom:8px; color:#9ca3af; font-weight:600; }
        
        .platform-selector { display:grid; grid-template-columns:repeat(auto-fit, minmax(120px, 1fr)); gap:10px; margin-bottom:15px; }
        .platform-btn {
            display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px;
            padding:15px; border:2px solid #374151; border-radius:12px; background:#1f2937; color:#fff;
            cursor:pointer; transition:all 0.3s ease; font-size:13px; font-family:'Cairo',sans-serif;
        }
        .platform-btn:hover { border-color:#00ff88; background:#2a3f4f; }
        .platform-btn.active {
            border-color: #00ff88;
            background: {{ platform_colors[platform] }} !important;
            color: #fff;
            box-shadow: 0 0 20px {{ platform_colors[platform] }}50;
        }
        .platform-btn img { width:32px; height:32px; object-fit:contain; }
        
        .form-control { width:100%; padding:14px; border-radius:15px; border:1px solid #374151; background:#1f2937; color:#fff; outline:none; font-family:'Cairo',sans-serif; font-size:15px; }
        .form-control:focus { border-color:#00ff88; }
        .form-control:disabled { opacity:0.5; cursor:not-allowed; }
        
        .btn-primary { width:100%; padding:16px; border:none; border-radius:15px; background:#00ff88; color:#0b0e17; font-size:18px; cursor:pointer; margin-top:10px; font-weight:700; font-family:'Cairo',sans-serif; }
        .btn-primary:hover { background:#00dd77; }
        .btn-blue { width:100%; padding:16px; border:none; border-radius:15px; background:#3b82f6; color:#fff; cursor:pointer; margin-top:10px; font-weight:700; font-family:'Cairo',sans-serif; }
        .btn-blue:hover { background:#2563eb; }
        
        .number-box { display:flex; align-items:center; justify-content:space-between; background:#000; border:2px solid #00ff88; border-radius:15px; padding:12px 15px; margin:20px 0; }
        .number-box .number { font-family:'Courier New',monospace; font-size:24px; color:#00ff88; flex-grow:1; text-align:center; }
        .copy-number-btn { background:#1f2937; border:none; border-radius:8px; padding:8px 12px; color:#fff; cursor:pointer; font-size:18px; margin-right:10px; }
        
        .otp-container { margin-top:20px; max-height:400px; overflow-y:auto; border:1px solid #1f2937; border-radius:15px; padding:10px; }
        .otp-item { background:#0f172a; border:1px solid #00ff88; border-radius:10px; padding:12px; margin-bottom:10px; font-family:'Courier New'; font-size:15px; color:#00ff88; line-height:1.6; }
        .otp-item .copy-btn { background:#1f2937; border:none; border-radius:8px; padding:4px 10px; color:#fff; cursor:pointer; font-size:12px; float:left; }
        .otp-item .info { color:#9ca3af; font-size:13px; display:block; margin-top:5px; }
        .status { background:#1f2937; padding:12px; border-radius:15px; text-align:center; margin-top:20px; color:#9ca3af; font-size:15px; }
        .admin-link { display:block; text-align:center; margin-top:15px; color:#00d2ff; text-decoration:none; display:none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="top-bar">
            <button class="menu-btn" onclick="toggleMenu()">☰</button>
            <div class="dropdown-menu" id="contactMenu">
                <a href="{{ owner_link }}" target="_blank">تواصل معي📞</a>
                <a href="{{ wa_group }}" target="_blank">💬 جروب واتساب</a>
            </div>
        </div>

        <div class="header">
            <h1>🚀موقع المطريOTP🚀</h1>
            <p>👑ارقام واتساب سحب اكواد تطوير مطري 👑</p>
        </div>

        <div class="form-group">
            <label>اختر المنصة:</label>
            <div class="platform-selector" id="platformSelector"></div>
        </div>

        <div class="form-group">
            <label>اختر الدولة:</label>
            <select id="country" class="form-control" disabled>
                <option value="">-- اختر المنصة أولاً --</option>
            </select>
        </div>

        <button class="btn-primary" id="getNumberBtn" onclick="getNumber()" disabled>🚀 جلب رقم</button>
        <button class="btn-blue" id="refreshBtn" onclick="refreshNumber()" disabled>🔄 تبديل</button>

        <div id="numberContainer" style="display:none;">
            <div class="number-box">
                <button class="copy-number-btn" onclick="copyNumber()">📋</button>
                <div class="number" id="numberDisplay">+</div>
            </div>
            <div style="display:flex; gap:10px; margin-top:10px;">
                <button class="btn-primary" onclick="startMonitoring()">📡 بدء السحب</button>
                <button class="btn-blue" onclick="stopMonitoring()" style="background:#ef4444;">⏹️ إيقاف</button>
            </div>
        </div>

        <div class="otp-container" id="otpHistory">
            <div style="text-align:center; color:#9ca3af; padding:20px;">⏳الاكواد المسحوبه📣</div>
        </div>

        <div class="status" id="status">⏳ اختر المنصة والدولة للبدء</div>
        <a href="/admin" class="admin-link">⚙️ لوحة التحكم</a>
    </div>

    <script>
        const platformLogos = {{ platform_logos | tojson }};
        const platformNames = {{ platform_names | tojson }};
        const platformColors = {{ platform_colors | tojson }};

        function initPlatformSelector() {
            const selector = document.getElementById('platformSelector');
            selector.innerHTML = '';
            Object.keys(platformNames).forEach(platform => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'platform-btn';
                btn.onclick = () => selectPlatform(platform);
                btn.innerHTML = `
                    <img src="${platformLogos[platform]}" alt="${platformNames[platform]}" onerror="this.style.display='none'">
                    <span>${platformNames[platform]}</span>
                `;
                selector.appendChild(btn);
            });
        }

        function toggleMenu() {
            const menu = document.getElementById('contactMenu');
            menu.classList.toggle('show');
        }
        document.addEventListener('click', function(event) {
            const menu = document.getElementById('contactMenu');
            const btn = document.querySelector('.menu-btn');
            if (!menu.contains(event.target) && !btn.contains(event.target)) {
                menu.classList.remove('show');
            }
        });

        async function copyNumber() {
            const num = document.getElementById('numberDisplay').textContent;
            await navigator.clipboard.writeText(num);
            alert('✅ تم نسخ الرقم: ' + num);
        }

        let currentPlatform = '';
        let currentNumber = '';
        let monitorInterval = null;

        function selectPlatform(platform) {
            currentPlatform = platform;
            document.querySelectorAll('.platform-btn').forEach(btn => {
                btn.classList.remove('active');
                btn.style.background = '#1f2937';
                btn.style.borderColor = '#374151';
                btn.style.boxShadow = 'none';
            });
            const btn = event.target.closest('.platform-btn');
            btn.classList.add('active');
            btn.style.background = platformColors[platform];
            btn.style.borderColor = platformColors[platform];
            btn.style.boxShadow = `0 0 20px ${platformColors[platform]}80`;
            loadCountries();
        }

        async function loadCountries() {
            const platform = currentPlatform;
            const countrySelect = document.getElementById('country');
            if (!platform) {
                countrySelect.innerHTML = '<option value="">-- اختر المنصة أولاً --</option>';
                countrySelect.disabled = true;
                document.getElementById('numberContainer').style.display = 'none';
                document.getElementById('getNumberBtn').disabled = true;
                document.getElementById('refreshBtn').disabled = true;
                return;
            }
            countrySelect.disabled = true;
            countrySelect.innerHTML = '<option value="">جاري التحميل...</option>';
            const res = await fetch('/api/countries', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({platform}) });
            const data = await res.json();
            let options = '<option value="">-- اختر الدولة --</option>';
            data.forEach(c => { options += `<option value="${c.code}">${c.flag} ${c.name}</option>`; });
            countrySelect.innerHTML = options;
            countrySelect.disabled = false;
        }

        document.getElementById('country').addEventListener('change', function() {
            const hasSelection = this.value !== '';
            document.getElementById('getNumberBtn').disabled = !hasSelection;
            document.getElementById('refreshBtn').disabled = !hasSelection;
        });

        async function getNumber() {
            const platform = currentPlatform;
            const country = document.getElementById('country').value;
            if (!platform || !country) { document.getElementById('status').innerHTML = '⚠️ يرجى اختيار المنصة والدولة'; return; }
            document.getElementById('status').innerHTML = '⏳ جاري جلب رقم...';
            const res = await fetch('/api/get_number', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({platform, country}) });
            const data = await res.json();
            if (data.number) {
                currentNumber = data.number;
                document.getElementById('numberDisplay').textContent = '+' + data.number;
                document.getElementById('numberContainer').style.display = 'block';
                document.getElementById('status').innerHTML = '✅ الرقم جاهز!';
            } else {
                document.getElementById('status').innerHTML = '❌ لا توجد أرقام متاحة.';
            }
        }

        async function refreshNumber() {
            const platform = currentPlatform;
            const country = document.getElementById('country').value;
            if (!platform || !country) return;
            document.getElementById('status').innerHTML = '⏳ جاري تبديل الرقم...';
            const res = await fetch('/api/get_number', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({platform, country}) });
            const data = await res.json();
            if (data.number && data.number !== currentNumber) {
                currentNumber = data.number;
                document.getElementById('numberDisplay').textContent = '+' + data.number;
                document.getElementById('status').innerHTML = '🔄 تم تبديل الرقم!';
            }
        }

        function addOtpToHistory(number, otp, timestamp) {
            const container = document.getElementById('otpHistory');
            const msg = `🔑 ${otp}`;
            const info = `📞 الرقم: +${number}  •  🕒 ${timestamp}`;
            const div = document.createElement('div');
            div.className = 'otp-item';
            div.innerHTML = `<span style="float:left;"><button class="copy-btn" onclick="copyText(\`${otp}\`)">📋 نسخ الكود</button></span><br>${msg}<span class="info">${info}</span>`;
            container.prepend(div);
            if (container.children.length > 20) container.removeChild(container.lastChild);
        }

        function copyText(text) { navigator.clipboard.writeText(text); alert('✅ تم نسخ الكود!'); }

        function startMonitoring() {
            if (!currentNumber) return;
            if (monitorInterval) clearInterval(monitorInterval);
            document.getElementById('status').innerHTML = '🔄 بدأ السحب التلقائي...';

            monitorInterval = setInterval(() => {
                fetch('/api/get_otp', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({number:currentNumber}) })
                .then(res => res.json()).then(data => {
                    if (data.otp) {
                        const now = new Date().toLocaleString('ar-YE', { timeZone: 'Asia/Aden' });
                        addOtpToHistory(currentNumber, data.otp, now);
                        document.getElementById('status').innerHTML = '✅ تم العثور على كود!';
                        stopMonitoring();
                    }
                });
            }, 5000);
        }

        function stopMonitoring() {
            if (monitorInterval) {
                clearInterval(monitorInterval);
                monitorInterval = null;
            }
            document.getElementById('status').innerHTML = '⏹️ تم إيقاف السحب.';
        }

        document.addEventListener('DOMContentLoaded', initPlatformSelector);
    </script>
</body>
</html>
"""

admin_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>لوحة التحكم</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Cairo',sans-serif; background:#0b0e17; color:#fff; display:flex; justify-content:center; align-items:center; min-height:100vh; }
.container { background:#111827; padding:30px; border-radius:25px; width:100%; max-width:450px; border:1px solid #1f2937; }
h1 { text-align:center; color:#00d2ff; margin-bottom:20px; }
.form-group { margin-bottom:15px; }
.form-group label { display:block; margin-bottom:5px; color:#9ca3af; }
.form-control { width:100%; padding:12px; border-radius:10px; border:1px solid #374151; background:#1f2937; color:#fff; }
.btn-primary { width:100%; padding:14px; border:none; border-radius:10px; background:#00ff88; color:#0b0e17; cursor:pointer; margin-top:15px; }
.btn-danger { width:100%; padding:14px; border:none; border-radius:10px; background:#ef4444; color:#fff; cursor:pointer; margin-top:10px; }
.btn-secondary { width:100%; padding:14px; border:none; border-radius:10px; background:#374151; color:#fff; cursor:pointer; margin-top:15px; }
.flash { padding:15px; border-radius:10px; margin:10px 0; text-align:center; }
.flash-success { background:#00ff88; color:#0b0e17; }
.flash-error { background:#ff4444; color:#fff; }
hr { border: 1px solid #374151; margin: 20px 0; }
</style>
</head>
<body>
<div class="container">
    <h1>⚙️ لوحة التحكم</h1>

    <!-- قسم رفع الكومبو -->
    <h3 style="color:#9ca3af;">📤 رفع ملف جديد</h3>
    <form method="POST" enctype="multipart/form-data">
        <div class="form-group"><label>المنصة</label>
        <select name="platform" class="form-control" required>
            <option value="whatsapp">واتساب</option><option value="telegram">تيليجرام</option>
            <option value="tiktok">تيك توك</option><option value="facebook">فيسبوك</option>
            <option value="instagram">انستقرام</option><option value="snapchat">سناب شات</option>
            <option value="google">جوجل</option><option value="twitter">تويتر</option>
        </select></div>
        <div class="form-group"><label>ارفع ملف الأرقام (.txt)</label><input type="file" name="file" accept=".txt" class="form-control" required></div>
        <button type="submit" class="btn-primary">📤 رفع الكومبو</button>
    </form>

    <hr>

    <!-- قسم حذف الكومبو -->
    <h3 style="color:#ef4444;">🗑️ حذف كومبو قديم</h3>
    <form method="POST">
        <input type="hidden" name="action" value="delete">
        <div class="form-group"><label>المنصة (للحذف)</label>
        <select name="platform" class="form-control" required>
            <option value="whatsapp">واتساب</option><option value="telegram">تيليجرام</option>
            <option value="tiktok">تيك توك</option><option value="facebook">فيسبوك</option>
            <option value="instagram">انستقرام</option><option value="snapchat">سناب شات</option>
            <option value="google">جوجل</option><option value="twitter">تويتر</option>
        </select></div>
        <div class="form-group"><label>كود الدولة (للحذف)</label>
        <input type="text" name="country_code" class="form-control" placeholder="مثال: 966" required></div>
        <button type="submit" class="btn-danger">🗑️ حذف</button>
    </form>

    <hr>
    <a href="/"><button class="btn-secondary">🔙 العودة للصفحة الرئيسية</button></a>
</div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(main_html, owner_link=OWNER_LINK, wa_group=WHATSAPP_GROUP_LINK, platform_logos=PLATFORM_LOGOS, platform_names=platform_names, platform_colors=platform_colors)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # ===== معالجة حذف الكومبو =====
    if request.method == 'POST' and request.form.get('action') == 'delete':
        platform = request.form.get('platform')
        country_code = request.form.get('country_code')
        if platform and country_code:
            delete_combo(platform, country_code)
            return render_template_string(admin_html)

    # ===== معالجة رفع الكومبو =====
    if request.method == 'POST' and request.form.get('action') != 'delete':
        platform = request.form.get('platform')
        file = request.files.get('file')
        if file and file.filename.endswith('.txt'):
            content = file.read().decode('utf-8')
            numbers = [line.strip() for line in content.splitlines() if line.strip()]
            if numbers:
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
                    return redirect(url_for('home'))
    return render_template_string(admin_html)

@app.route('/api/countries', methods=['POST'])
def api_countries():
    return jsonify(get_countries_by_platform(request.json.get('platform')))

@app.route('/api/get_number', methods=['POST'])
def api_get_number():
    d = request.json
    nums = get_numbers(d['platform'], d['country'])
    return jsonify({'number': random.choice(nums) if nums else None})

@app.route('/api/get_otp', methods=['POST'])
def api_get_otp():
    num = request.json.get('number')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT otp FROM otp_logs WHERE number LIKE ? ORDER BY id DESC LIMIT 1", (f"%{num[-4:]}",))
    row = c.fetchone()
    conn.close()
    return jsonify({'otp': row[0] if row else None})

def monitor_channel():
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates", timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get('ok'):
                    for upd in data.get('result', []):
                        if 'channel_post' in upd:
                            text = upd['channel_post'].get('text', '')
                            if text:
                                clean = re.sub(r'[\u200B-\u200F\u202A-\u202E‏‎]', '', text)
                                last4 = None
                                h = re.findall(r'•+(\d{4})', clean)
                                if h:
                                    last4 = h[0]
                                else:
                                    fl = clean.split('\n')[0]
                                    nums = re.findall(r'\b\d{4}\b', fl)
                                    if nums:
                                        last4 = nums[0]
                                if last4:
                                    otp = None
                                    d = re.search(r'\b(\d{3}-\d{3})\b', clean)
                                    if d:
                                        otp = d.group(1).replace('-', '')
                                    if not otp:
                                        m = re.search(r'(?:رمز|كود|code|otp|verification)[:\s\-]*(\d{4,8})', clean, re.IGNORECASE)
                                        if m:
                                            otp = m.group(1)
                                    if not otp:
                                        ln = re.findall(r'\b\d{5,8}\b', clean)
                                        if ln:
                                            otp = ln[0]
                                    if not otp:
                                        af = re.findall(r'\b\d{4}\b', clean)
                                        for n in af:
                                            if n != last4:
                                                otp = n
                                                break
                                    if otp:
                                        conn = sqlite3.connect(DB_PATH)
                                        conn.cursor().execute("INSERT INTO otp_logs (number, otp, timestamp, platform) VALUES (?, ?, ?, ?)", (last4, otp, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "قناة"))
                                        conn.commit()
                                        conn.close()
        except:
            pass
        time.sleep(5)

threading.Thread(target=monitor_channel, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
