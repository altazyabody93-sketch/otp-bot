from flask import Flask, request, render_template_string, jsonify, redirect, url_for, session
from functools import wraps
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
app.secret_key = os.environ.get("SECRET_KEY", "matari_otp_secret_2025_xyz")
DB_PATH = "bot.db"

# ========== الإعدادات الأساسية ==========
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "123")
ADMIN_SECRET_PATH = os.environ.get("ADMIN_PATH", "admin_secret_77")

WHATSAPP_GROUP_LINK = "https://chat.whatsapp.com/IeK2gNS64fd8YSnenzt4WR"
OWNER_PHONE = "967733723953"
OWNER_LINK = f"https://wa.me/{OWNER_PHONE}"

TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN", "8814038881:AAGyuACUYA4YPKlJQhAyUMkpRNiV0u1gNuU")
ASSISTANT_BOT_TOKEN = os.environ.get("ASSISTANT_BOT_TOKEN", "8845420882:AAHZ-7qhCL3_ddDT3am4zWNtBRBy3mVDgws")
OWNER_TELEGRAM_USERNAME = "ABOD_90N"

# ⏱️ مدة صلاحية الكود 60 ثانية
OTP_COUNTDOWN = 60

# ========== قاعدة البيانات ==========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS combos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT, country_code TEXT, country_name TEXT, country_flag TEXT,
        numbers TEXT, UNIQUE(platform, country_code)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS otp_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        number TEXT, otp TEXT, timestamp TEXT, platform TEXT,
        country_code TEXT, country_flag TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS admin_settings (
        key TEXT PRIMARY KEY, value TEXT, updated_at TEXT
    )''')
    # ✅ ترحيل الأعمدة الناقصة في الجداول القديمة
    def ensure_column(table, col, col_def):
        c.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in c.fetchall()]
        if col not in cols:
            try:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
            except: pass
    ensure_column("otp_logs", "country_code", "TEXT")
    ensure_column("otp_logs", "country_flag", "TEXT")
    conn.commit()
    conn.close()
init_db()

def get_setting(key, default=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM admin_settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else default

def set_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO admin_settings (key, value, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (key, value, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

# ========== جميع الدول ==========
COUNTRY_DATA = {
    "966": {"n": "السعودية", "f": "🇸🇦"}, "971": {"n": "الإمارات", "f": "🇦🇪"},
    "20": {"n": "مصر", "f": "🇪🇬"}, "1": {"n": "أمريكا", "f": "🇺🇸"},
    "44": {"n": "بريطانيا", "f": "🇬🇧"}, "90": {"n": "تركيا", "f": "🇹🇷"},
    "91": {"n": "الهند", "f": "🇮🇳"}, "49": {"n": "ألمانيا", "f": "🇩🇪"},
    "7": {"n": "روسيا", "f": "🇷🇺"}, "33": {"n": "فرنسا", "f": "🇫🇷"},
    "34": {"n": "إسبانيا", "f": "🇪🇸"}, "39": {"n": "إيطاليا", "f": "🇮🇹"},
    "212": {"n": "المغرب", "f": "🇲🇦"}, "213": {"n": "الجزائر", "f": "🇩🇿"},
    "216": {"n": "تونس", "f": "🇹🇳"}, "218": {"n": "ليبيا", "f": "🇱🇾"},
    "92": {"n": "باكستان", "f": "🇵🇰"}, "93": {"n": "أفغانستان", "f": "🇦🇫"},
    "27": {"n": "جنوب أفريقيا", "f": "🇿🇦"}, "972": {"n": "إسرائيل", "f": "🇮🇱"},
    "973": {"n": "البحرين", "f": "🇧🇭"}, "974": {"n": "قطر", "f": "🇶🇦"},
    "968": {"n": "عمان", "f": "🇴🇲"}, "970": {"n": "فلسطين", "f": "🇵🇸"},
    "52": {"n": "المكسيك", "f": "🇲🇽"}, "55": {"n": "البرازيل", "f": "🇧🇷"},
    "54": {"n": "الأرجنتين", "f": "🇦🇷"}, "56": {"n": "تشيلي", "f": "🇨🇱"},
    "57": {"n": "كولومبيا", "f": "🇨🇴"}, "51": {"n": "بيرو", "f": "🇵🇪"},
    "58": {"n": "فنزويلا", "f": "🇻🇪"}, "81": {"n": "اليابان", "f": "🇯🇵"},
    "82": {"n": "كوريا الجنوبية", "f": "🇰🇷"}, "86": {"n": "الصين", "f": "🇨🇳"},
    "63": {"n": "الفلبين", "f": "🇵🇭"}, "62": {"n": "إندونيسيا", "f": "🇮🇩"},
    "60": {"n": "ماليزيا", "f": "🇲🇾"}, "65": {"n": "سنغافورة", "f": "🇸🇬"},
    "66": {"n": "تايلاند", "f": "🇹🇭"}, "84": {"n": "فيتنام", "f": "🇻🇳"},
    "31": {"n": "هولندا", "f": "🇳🇱"}, "32": {"n": "بلجيكا", "f": "🇧🇪"},
    "41": {"n": "سويسرا", "f": "🇨🇭"}, "43": {"n": "النمسا", "f": "🇦🇹"},
    "45": {"n": "الدنمارك", "f": "🇩🇰"}, "46": {"n": "السويد", "f": "🇸🇪"},
    "47": {"n": "النرويج", "f": "🇳🇴"}, "48": {"n": "بولندا", "f": "🇵🇱"},
    "30": {"n": "اليونان", "f": "🇬🇷"}, "351": {"n": "البرتغال", "f": "🇵🇹"},
    "353": {"n": "أيرلندا", "f": "🇮🇪"}, "354": {"n": "آيسلندا", "f": "🇮🇸"},
    "64": {"n": "نيوزيلندا", "f": "🇳🇿"}, "61": {"n": "أستراليا", "f": "🇦🇺"},
    "40": {"n": "رومانيا", "f": "🇷🇴"}, "36": {"n": "المجر", "f": "🇭🇺"},
    "420": {"n": "التشيك", "f": "🇨🇿"}, "421": {"n": "سلوفاكيا", "f": "🇸🇰"},
    "380": {"n": "أوكرانيا", "f": "🇺🇦"}, "381": {"n": "صربيا", "f": "🇷🇸"},
    "385": {"n": "كرواتيا", "f": "🇭🇷"}, "386": {"n": "سلوفينيا", "f": "🇸🇮"},
    "387": {"n": "البوسنة", "f": "🇧🇦"}, "389": {"n": "مقدونيا", "f": "🇲🇰"},
    "375": {"n": "بيلاروس", "f": "🇧🇾"}, "370": {"n": "ليتوانيا", "f": "🇱🇹"},
    "371": {"n": "لاتفيا", "f": "🇱🇻"}, "372": {"n": "إستونيا", "f": "🇪🇪"},
    "373": {"n": "مولدوفا", "f": "🇲🇩"}, "374": {"n": "أرمينيا", "f": "🇦🇲"},
    "995": {"n": "جورجيا", "f": "🇬🇪"}, "994": {"n": "أذربيجان", "f": "🇦🇿"},
    "992": {"n": "طاجيكستان", "f": "🇹🇯"}, "993": {"n": "تركمانستان", "f": "🇹🇲"},
    "998": {"n": "أوزبكستان", "f": "🇺🇿"}, "996": {"n": "قرغيزستان", "f": "🇰🇬"},
    "975": {"n": "بوتان", "f": "🇧🇹"}, "976": {"n": "منغوليا", "f": "🇲🇳"},
    "977": {"n": "نيبال", "f": "🇳🇵"}, "94": {"n": "سريلانكا", "f": "🇱🇰"},
    "95": {"n": "ميانمار", "f": "🇲🇲"}, "856": {"n": "لاوس", "f": "🇱🇦"},
    "855": {"n": "كمبوديا", "f": "🇰🇭"}, "960": {"n": "المالديف", "f": "🇲🇻"},
    "961": {"n": "لبنان", "f": "🇱🇧"}, "962": {"n": "الأردن", "f": "🇯🇴"},
    "963": {"n": "سوريا", "f": "🇸🇾"}, "964": {"n": "العراق", "f": "🇮🇶"},
    "965": {"n": "الكويت", "f": "🇰🇼"}, "967": {"n": "اليمن", "f": "🇾🇪"},
    "355": {"n": "ألبانيا", "f": "🇦🇱"}, "356": {"n": "مالطا", "f": "🇲🇹"},
    "357": {"n": "قبرص", "f": "🇨🇾"}, "358": {"n": "فنلندا", "f": "🇫🇮"},
    "359": {"n": "بلغاريا", "f": "🇧🇬"}, "350": {"n": "جبل طارق", "f": "🇬🇮"},
    "352": {"n": "لوكسمبورغ", "f": "🇱🇺"}, "423": {"n": "ليختنشتاين", "f": "🇱🇮"},
    "377": {"n": "موناكو", "f": "🇲🇨"}, "378": {"n": "سان مارينو", "f": "🇸🇲"},
    "501": {"n": "بليز", "f": "🇧🇿"}, "502": {"n": "غواتيمالا", "f": "🇬🇹"},
    "503": {"n": "السلفادور", "f": "🇸🇻"}, "504": {"n": "هندوراس", "f": "🇭🇳"},
    "505": {"n": "نيكاراغوا", "f": "🇳🇮"}, "506": {"n": "كوستاريكا", "f": "🇨🇷"},
    "507": {"n": "بنما", "f": "🇵🇦"}, "509": {"n": "هايتي", "f": "🇭🇹"},
    "591": {"n": "بوليفيا", "f": "🇧🇴"}, "592": {"n": "غيانا", "f": "🇬🇾"},
    "593": {"n": "الإكوادور", "f": "🇪🇨"}, "595": {"n": "باراغواي", "f": "🇵🇾"},
    "597": {"n": "سورينام", "f": "🇸🇷"}, "598": {"n": "أوروغواي", "f": "🇺🇾"},
    "670": {"n": "تيمور الشرقية", "f": "🇹🇱"}, "673": {"n": "بروناي", "f": "🇧🇳"},
    "675": {"n": "بابوا غينيا", "f": "🇵🇬"}, "676": {"n": "تونغا", "f": "🇹🇴"},
    "677": {"n": "جزر سليمان", "f": "🇸🇧"}, "678": {"n": "فانواتو", "f": "🇻🇺"},
    "679": {"n": "فيجي", "f": "🇫🇯"}, "680": {"n": "بالاو", "f": "🇵🇼"},
    "685": {"n": "ساموا", "f": "🇼🇸"}, "686": {"n": "كيريباتي", "f": "🇰🇮"},
    "691": {"n": "ميكرونيسيا", "f": "🇫🇲"}, "850": {"n": "كوريا الشمالية", "f": "🇰🇵"},
    "852": {"n": "هونغ كونغ", "f": "🇭🇰"}, "853": {"n": "ماكاو", "f": "🇲🇴"},
    "880": {"n": "بنغلاديش", "f": "🇧🇩"}, "886": {"n": "تايوان", "f": "🇹🇼"},
}

def get_country_info(code):
    info = COUNTRY_DATA.get(code)
    return (info["n"], info["f"]) if info else ("أخرى", "🌍")

# ========== دوال الكومبو ==========
def get_countries_by_platform(platform):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT country_code, country_name, country_flag FROM combos WHERE platform=? ORDER BY country_name", (platform,))
    countries = [{'code': r[0], 'name': r[1], 'flag': r[2]} for r in c.fetchall()]
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

def get_all_combos_list():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT platform, country_code, country_name, country_flag FROM combos ORDER BY platform, country_name")
    rows = c.fetchall()
    conn.close()
    return rows

# ========== شعارات المنصات SVG ==========
PLATFORM_LOGOS = {
    "whatsapp": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%2325D366'/><path fill='%23fff' d='M50 18c-17.6 0-32 14.4-32 32 0 6 1.7 11.8 4.8 16.8L18 82l15.6-4.7C38.6 80.1 44.2 82 50 82c17.6 0 32-14.4 32-32S67.6 18 50 18zm18.6 45.6c-.8 2.2-4.6 4.2-6.4 4.5-1.6.3-3.7.4-5.9-.4-1.4-.5-3.1-1.1-5.4-2.2-9.5-4.1-15.7-13.7-16.2-14.3-.5-.7-3.9-5.1-3.9-9.7s2.4-6.9 3.3-7.9c.9-.9 1.9-1.2 2.6-1.2.6 0 1.2 0 1.7 0 .6 0 1.3-.2 2 .1 1.6.7 2.6 3 2.9 3.9.3.9.5 1.5 0 2.4-.4.9-1.5 2.4-2.2 3.4 0 0 .7.7 1.4 1.5 2.4 2.7 5.3 5.5 9.6 7.1 1.5.5 2.3.6 3-.4.6-1 2.5-3 3.2-4 .7-1 1.4-.8 2.3-.5.9.3 5.8 2.7 6.8 3.2 1 .5 1.6.7 1.8 1.1.2.5.2 2.5-.6 4.7z'/></svg>",
    "telegram": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%2326A5E4'/><path fill='%23fff' d='M22 50l50-22-7 48-18-8-7 12-3-17 31-26-37 24-9-4z'/></svg>",
    "tiktok": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%23000'/><path fill='%2325F4EE' d='M62 22c2 8 8 14 16 15v9c-6 0-12-2-16-5v22c0 12-9 20-20 20s-20-8-20-20 9-21 20-21v9c-6 0-11 5-11 12s5 12 11 12 12-6 12-12V22h8z'/><path fill='%23FE2C55' d='M70 22c2 8 8 14 16 15v9c-6 0-12-2-16-5v22c0 12-9 20-20 20v-9c6 0 12-6 12-12V22h8z'/></svg>",
    "facebook": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%231877F2'/><path fill='%23fff' d='M58 84V52h10l1-12H58v-7c0-3 1-5 5-5h6V17h-9c-10 0-15 6-15 14v9H36v12h9v32h13z'/></svg>",
    "instagram": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><defs><radialGradient id='ig' cx='30%25' cy='30%25' r='80%25'><stop offset='0%25' stop-color='%23FEDA75'/><stop offset='50%25' stop-color='%23FA7E1E'/><stop offset='100%25' stop-color='%23D62976'/></radialGradient></defs><rect width='100' height='100' rx='22' fill='url(%23ig)'/><rect x='22' y='22' width='56' height='56' rx='14' fill='none' stroke='%23fff' stroke-width='5'/><circle cx='50' cy='50' r='13' fill='none' stroke='%23fff' stroke-width='5'/><circle cx='72' cy='28' r='4' fill='%23fff'/></svg>",
    "snapchat": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%23FFFC00'/><path fill='%23000' d='M50 16c-13 0-23 9-23 21 0 6 1 11 2 16-2 1-4 2-7 2-1 0-2 1-2 2 0 4 8 5 11 7 1 1 1 4 2 6 1 3 4 5 8 5 3 0 5-1 7-1 3 0 6 6 13 6 7 0 10-6 13-6 2 0 4 1 7 1 4 0 7-2 8-5 1-2 1-5 2-6 3-2 11-3 11-7 0-1-1-2-2-2-3 0-5-1-7-2 1-5 2-10 2-16 0-12-10-21-23-21-3 0-6 1-8 2-2-1-5-2-8-2z'/></svg>",
    "google": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%23fff'/><path fill='%234285F4' d='M58 50c0-1-.1-2-.2-3H50v6h5.5c-.5 2-2 4-4.5 5l4 3c3-2 5-6 5-10 0-1 0-1-.5-1z'/><path fill='%2334A853' d='M40 56c1 4 4 7 9 7 3 0 5-1 7-3l-4-3c-1 1-2 1-4 1-3 0-5-2-6-4l-4 2z'/><path fill='%23FBBC04' d='M40 44l-4 2c-1 1-1 3-1 4s0 3 1 4l4-2c-.5-1-.5-2-.5-3s0-4 0-4z'/><path fill='%23EA4335' d='M50 36c3 0 5 1 6 2l-3 3c-1-1-2-1-4-1-5 0-9 4-9 4l-4-2c0-3 4-6 14-6z'/></svg>",
    "twitter": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%23000'/><path fill='%23fff' d='M70 35c-2 1-4 1-6 1 2-1 4-3 5-5-2 1-4 2-7 2-2-2-5-3-8-3-6 0-11 5-11 11 0 1 0 2 .3 3-9 0-17-5-22-12-1 2-1 4-1 6 0 4 2 7 5 9-2 0-4-1-5-2v.1c0 5 4 10 9 11-1 0-3 .5-4 .5-1 0-2 0-3-.1 2 4 6 7 11 7-4 3-9 5-15 5-1 0-2 0-3-.1 5 3 11 5 18 5 21 0 33-18 33-33v-1c2-2 4-3 6-6z'/></svg>",
}

platform_names = {
    'whatsapp': 'واتساب', 'telegram': 'تيليجرام', 'tiktok': 'تيك توك',
    'facebook': 'فيسبوك', 'instagram': 'انستقرام', 'snapchat': 'سناب شات',
    'google': 'جوجل', 'twitter': 'تويتر/X'
}

platform_colors = {
    'whatsapp': '#25D366', 'telegram': '#0088cc', 'tiktok': '#FE2C55',
    'facebook': '#1877F2', 'instagram': '#E4405F', 'snapchat': '#FFFC00',
    'google': '#4285F4', 'twitter': '#1DA1F2'
}

PLATFORMS_ORDER = ['whatsapp', 'telegram', 'facebook', 'instagram', 'tiktok', 'snapchat', 'google', 'twitter']

# ========== HTML الرئيسي ==========
main_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>المطري OTP - الموقع الرسمي</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@500;700;800;900&display=swap" rel="stylesheet">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
        :root {
            --bg: #07090d;
            --card: #0d1117;
            --card2: #161b22;
            --border: #30363d;
            --text: #e6edf3;
            --text2: #8b949e;
            --primary: #1f6feb;
            --success: #238636;
            --danger: #da3633;
        }
        html, body { font-family:'Cairo',sans-serif; background:var(--bg); color:var(--text); overflow-x:hidden; }
        body { min-height:100vh; position:relative; }

        /* خلفية المطر الرقمي - يتم تحميلها lazy */
        #matrixCanvas {
            position:fixed; top:0; left:0; width:100%; height:100%;
            z-index:0; opacity:0.15; pointer-events:none;
        }

        .app {
            position:relative; z-index:10;
            max-width:480px; margin:0 auto;
            background:rgba(7,9,13,0.85); backdrop-filter:blur(4px);
            min-height:100vh; display:flex; flex-direction:column;
        }

        /* ============= HEADER ============= */
        .top-bar {
            background:var(--card); padding:12px 16px;
            display:flex; align-items:center; justify-content:space-between;
            border-bottom:1px solid var(--border);
            position:sticky; top:0; z-index:50;
        }
        .brand { display:flex; align-items:center; gap:10px; }
        .brand-icon {
            width:36px; height:36px; border-radius:10px;
            background:linear-gradient(135deg, #1f6feb, #388bfd);
            display:flex; align-items:center; justify-content:center;
            font-size:18px; animation:logoFloat 3s ease-in-out infinite;
        }
        @keyframes logoFloat {
            0%,100% { transform:translateY(0) rotate(0); }
            50% { transform:translateY(-3px) rotate(5deg); }
        }
        .brand-text { font-size:16px; font-weight:800; color:#fff; }
        .top-actions { display:flex; gap:6px; align-items:center; }
        .icon-btn {
            background:transparent; border:1px solid var(--border); color:var(--text2);
            padding:6px 10px; border-radius:8px; cursor:pointer; font-size:16px;
            transition:all 0.2s; font-family:inherit;
        }
        .icon-btn:hover { color:var(--primary); border-color:var(--primary); }

        /* ============= القائمة الجانبية ============= */
        .menu-overlay {
            display:none; position:fixed; inset:0;
            background:rgba(0,0,0,0.6); backdrop-filter:blur(3px);
            z-index:999; opacity:0; transition:opacity 0.3s;
        }
        .menu-overlay.show { display:block; opacity:1; }
        .side-menu {
            position:fixed; top:0; right:-280px; width:280px; height:100vh;
            background:var(--card); border-left:1px solid var(--border);
            z-index:1000; padding:20px 16px;
            display:flex; flex-direction:column; gap:8px;
            transition:right 0.35s cubic-bezier(0.4,0,0.2,1);
            overflow-y:auto;
        }
        .side-menu.show { right:0; }
        .side-menu-header {
            display:flex; justify-content:space-between; align-items:center;
            margin-bottom:16px; padding-bottom:12px; border-bottom:1px solid var(--border);
        }
        .side-menu-title { font-size:18px; font-weight:800; color:#fff; }
        .side-menu-close {
            background:transparent; border:none; color:var(--text2);
            font-size:24px; cursor:pointer; padding:0; line-height:1;
        }
        .side-section-title {
            font-size:12px; color:var(--primary); font-weight:800;
            padding:8px 12px 4px; letter-spacing:0.5px;
        }
        .side-link {
            display:flex; align-items:center; gap:12px;
            color:var(--text); text-decoration:none;
            padding:10px 12px; border-radius:10px;
            font-size:14px; font-weight:600;
            transition:all 0.2s; border:1px solid transparent;
        }
        .side-link:hover {
            background:rgba(31,111,235,0.1); color:var(--primary);
            border-color:rgba(31,111,235,0.2);
            transform:translateX(-4px);
        }
        .side-link .ico {
            font-size:16px; width:32px; height:32px;
            display:flex; align-items:center; justify-content:center;
            background:rgba(31,111,235,0.12); border-radius:8px; flex-shrink:0;
        }
        .side-divider {
            height:1px; background:linear-gradient(90deg, transparent, var(--border), transparent);
            margin:6px 0;
        }

        /* ============= MAIN CONTENT ============= */
        .main { padding:14px 14px 8px; flex:1; }

        .hero { text-align:center; padding:8px 8px 4px; }
        .hero h1 { font-size:20px; font-weight:800; color:#fff; margin-bottom:4px; }
        .hero p { font-size:13px; color:var(--text2); line-height:1.4; }

        .section-title {
            font-size:14px; font-weight:700; color:#fff;
            margin:14px 4px 8px; display:flex; align-items:center; gap:6px;
        }
        .section-title .icon { color:var(--primary); font-size:16px; }

        /* ============= PLATFORMS GRID (صفين) ============= */
        .platforms {
            display:grid; grid-template-columns:repeat(2, 1fr);
            gap:8px; margin-bottom:4px;
        }
        .platform-btn {
            display:flex; align-items:center; gap:8px;
            padding:10px 12px;
            background:var(--card2); border:1.5px solid var(--border);
            border-radius:12px; color:var(--text);
            cursor:pointer; transition:all 0.2s;
            font-size:13px; font-weight:600; font-family:inherit;
            position:relative; overflow:hidden;
        }
        .platform-btn::before {
            content:''; position:absolute; inset:0;
            background:linear-gradient(135deg, var(--pcolor, #1f6feb), transparent);
            opacity:0; transition:opacity 0.3s; z-index:0;
        }
        .platform-btn:hover {
            border-color:var(--pcolor, #1f6feb);
            transform:translateY(-2px);
        }
        .platform-btn:hover::before { opacity:0.15; }
        .platform-btn:active { transform:scale(0.97); }
        .platform-btn.active {
            background:linear-gradient(135deg, var(--pcolor, #1f6feb)22, var(--card2));
            border-color:var(--pcolor, #1f6feb);
            box-shadow:0 0 20px var(--pcolor, #1f6feb)66;
        }
        .platform-btn img {
            width:30px; height:30px; object-fit:contain;
            border-radius:8px; background:#fff; padding:2px;
            position:relative; z-index:1; flex-shrink:0;
        }
        .platform-btn span { position:relative; z-index:1; }

        /* ============= SELECT & BUTTONS ============= */
        .form-control {
            width:100%; padding:12px 14px; border-radius:10px;
            border:1px solid var(--border); background:var(--card);
            color:var(--text); outline:none;
            font-family:inherit; font-size:14px; font-weight:600;
            appearance:none; -webkit-appearance:none;
            background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'><path fill='%238b949e' d='M6 9L1 4h10z'/></svg>");
            background-repeat:no-repeat; background-position:left 14px center;
            padding-left:36px;
        }
        .form-control:focus { border-color:var(--primary); }
        .form-control:disabled { opacity:0.5; cursor:not-allowed; }

        .btn {
            width:100%; padding:12px; border:none; border-radius:10px;
            color:#fff; font-size:14px; font-weight:700;
            cursor:pointer; margin-top:8px; font-family:inherit;
            transition:all 0.2s; display:flex; align-items:center; justify-content:center; gap:6px;
        }
        .btn-primary { background:linear-gradient(135deg, #238636, #2ea043); }
        .btn-primary:hover:not(:disabled) { transform:translateY(-1px); box-shadow:0 4px 12px rgba(35,134,54,0.3); }
        .btn-blue { background:linear-gradient(135deg, #1f6feb, #388bfd); }
        .btn-blue:hover:not(:disabled) { transform:translateY(-1px); box-shadow:0 4px 12px rgba(31,111,235,0.3); }
        .btn-danger { background:linear-gradient(135deg, #da3633, #b91c1c); }
        .btn-danger:hover:not(:disabled) { transform:translateY(-1px); }
        .btn:disabled { opacity:0.5; cursor:not-allowed; }
        .btn:active:not(:disabled) { transform:scale(0.98); }

        /* ============= NUMBER CARD ============= */
        .number-card {
            background:linear-gradient(135deg, var(--card), var(--card2));
            border:1.5px solid var(--ncolor, var(--success));
            border-radius:14px; padding:18px; margin:12px 0;
            text-align:center; position:relative; overflow:hidden;
            box-shadow:0 0 24px var(--ncolor, var(--success))33;
        }
        .number-label {
            font-size:11px; color:var(--text2); font-weight:600; margin-bottom:4px;
        }
        .number {
            font-family:'Courier New',monospace; font-size:26px; font-weight:900;
            color:var(--ncolor, #3fb950); letter-spacing:2px;
            text-shadow:0 0 10px var(--ncolor, #3fb950);
            direction:ltr; display:inline-block;
        }
        .number .digit {
            display:inline-block; opacity:0;
            transform:translateY(-15px) scale(0.6);
            animation:digitIn 0.4s cubic-bezier(0.34,1.56,0.64,1) forwards;
        }
        @keyframes digitIn {
            to { opacity:1; transform:translateY(0) scale(1); }
        }
        .copy-btn-mini {
            background:transparent; border:1px solid var(--border); color:var(--text2);
            padding:5px 12px; border-radius:8px; cursor:pointer;
            font-size:12px; margin-top:8px; font-family:inherit; font-weight:600;
        }
        .copy-btn-mini:hover { color:var(--ncolor, #3fb950); border-color:var(--ncolor, #3fb950); }
        .copy-btn-mini.copied { background:var(--ncolor, #3fb950); color:#fff; border-color:transparent; }

        /* Countdown bar */
        .countdown {
            margin-top:10px; height:6px; background:var(--card);
            border-radius:3px; overflow:hidden; position:relative;
        }
        .countdown-bar {
            height:100%; background:linear-gradient(90deg, var(--primary), #3fb950);
            transition:width 1s linear, background 0.3s;
            border-radius:3px;
        }
        .countdown-bar.warn { background:linear-gradient(90deg, #f0b429, #f85149); }
        .countdown-bar.expired { background:#da3633; width:0% !important; }
        .countdown-text {
            text-align:center; font-size:12px; font-weight:700;
            color:var(--text2); margin-top:4px;
        }
        .countdown-text.warn { color:#f0b429; }
        .countdown-text.expired { color:#f85149; }

        /* ============= OTP LIST ============= */
        .otp-list { display:flex; flex-direction:column; gap:6px; margin-top:10px; }
        .otp-item {
            background:var(--card2); border:1px solid var(--border);
            border-radius:10px; padding:10px 12px;
            display:flex; justify-content:space-between; align-items:center;
            transition:all 0.2s; animation:slideIn 0.3s ease;
        }
        @keyframes slideIn { from{opacity:0; transform:translateX(20px);} to{opacity:1; transform:translateX(0);} }
        .otp-item.fresh { border-color:#3fb950; box-shadow:0 0 12px rgba(63,185,80,0.2); }
        .otp-item .otp-code {
            font-family:'Courier New',monospace; font-size:15px; font-weight:900;
            color:#3fb950; letter-spacing:1px;
        }
        .otp-item .otp-info { font-size:10px; color:var(--text2); margin-top:2px; }
        .otp-item-btns { display:flex; gap:4px; }
        .otp-btn {
            background:transparent; border:1px solid var(--border); color:var(--text2);
            padding:4px 10px; border-radius:6px; cursor:pointer;
            font-size:11px; font-weight:600; font-family:inherit;
        }
        .otp-btn:hover { color:var(--primary); border-color:var(--primary); }
        .otp-btn.delete:hover { color:#f85149; border-color:#f85149; }
        .otp-btn.delete.working { color:#f0b429; border-color:#f0b429; }
        .empty-state { text-align:center; padding:24px 12px; color:var(--text2); font-size:13px; }

        /* ============= STATUS ============= */
        .status {
            background:var(--card2); border:1px solid var(--border);
            border-radius:10px; padding:10px 14px;
            text-align:center; margin-top:10px;
            color:var(--text2); font-size:13px; font-weight:600;
        }
        .status.success { color:#3fb950; border-color:#23863644; }
        .status.error { color:#f85149; border-color:#da363344; }

        /* ============= FOOTER + TICKER ============= */
        .footer-section { margin-top:14px; }
        .ticker-wrap {
            background:var(--card); border:1px solid var(--border);
            border-radius:10px; padding:8px 0; overflow:hidden;
            display:flex; align-items:center; gap:8px;
            position:relative;
        }
        .ticker-label {
            background:linear-gradient(135deg, #f85149, #da3633);
            color:#fff; font-weight:800; font-size:10px;
            padding:3px 8px; border-radius:4px;
            margin:0 6px; white-space:nowrap; flex-shrink:0;
            box-shadow:0 0 8px rgba(248,81,73,0.4);
        }
        .ticker-viewport {
            flex:1; overflow:hidden; position:relative;
            -webkit-mask-image:linear-gradient(90deg, transparent 0%, #000 4%, #000 96%, transparent 100%);
            mask-image:linear-gradient(90deg, transparent 0%, #000 4%, #000 96%, transparent 100%);
        }
        .ticker {
            display:inline-block; white-space:nowrap;
            animation:tickerScroll 25s linear infinite;
            color:var(--text); font-weight:600; font-size:12px;
        }
        .ticker span { margin:0 20px; }
        .ticker .name {
            background:linear-gradient(90deg, #58a6ff, #a371f7, #f78166, #58a6ff);
            background-size:300% 300%;
            -webkit-background-clip:text; background-clip:text;
            -webkit-text-fill-color:transparent;
            animation:gradShift 4s ease infinite;
            font-weight:800;
        }
        @keyframes gradShift {
            0%,100% { background-position:0% 50%; }
            50% { background-position:100% 50%; }
        }
        @keyframes tickerScroll {
            0% { transform:translateX(0); }
            100% { transform:translateX(-50%); }
        }
        .footer-info {
            text-align:center; padding:10px 12px 16px;
            color:var(--text2); font-size:11px;
        }

        /* ============= LIGHT MODE ============= */
        body.light {
            --bg:#f6f8fa; --card:#fff; --card2:#f6f8fa;
            --border:#d0d7de; --text:#1f2328; --text2:#656d76;
        }
        body.light .app { background:rgba(246,248,250,0.92); }
        body.light .form-control { background:#fff; }
        body.light .ticker-wrap { background:#fff; }
        body.light .footer-info { color:#656d76; }

        /* ============= RESPONSIVE ============= */
        @media (max-width:380px) {
            .hero h1 { font-size:18px; }
            .platform-btn { font-size:12px; padding:9px 10px; }
            .number { font-size:22px; }
        }

        /* Loading state */
        .loading { display:inline-block; width:14px; height:14px; border:2px solid #fff3; border-top-color:#fff; border-radius:50%; animation:spin 0.6s linear infinite; }
        @keyframes spin { to { transform:rotate(360deg); } }
    </style>
</head>
<body>
    <canvas id="matrixCanvas"></canvas>

    <div class="app">
        <!-- HEADER -->
        <div class="top-bar">
            <div class="brand">
                <div class="brand-icon">🚀</div>
                <div class="brand-text">المطري OTP</div>
            </div>
            <div class="top-actions">
                <button class="icon-btn" id="themeToggle" onclick="toggleTheme()" title="الوضع الليلي">🌙</button>
                <button class="icon-btn" onclick="toggleMenu()" title="القائمة">☰</button>
            </div>
        </div>

        <!-- القائمة الجانبية -->
        <div class="menu-overlay" id="menuOverlay" onclick="toggleMenu()"></div>
        <div class="side-menu" id="sideMenu">
            <div class="side-menu-header">
                <div class="side-menu-title">🚀 القائمة</div>
                <button class="side-menu-close" onclick="toggleMenu()">✕</button>
            </div>

            <div class="side-section-title">📞 التواصل معي</div>
            <a href="{{ owner_link }}" target="_blank" class="side-link">
                <span class="ico">💬</span><span>واتساب المطور</span>
            </a>
            <a href="{{ wa_group }}" target="_blank" class="side-link">
                <span class="ico">👥</span><span>جروب واتساب</span>
            </a>
            <a href="https://t.me/jsjsgsjsvh" target="_blank" class="side-link">
                <span class="ico">✈️</span><span>قناة تليجرام</span>
            </a>
            <a href="https://t.me/{{ owner_tg }}" target="_blank" class="side-link">
                <span class="ico">🤖</span><span>حساب المطور</span>
            </a>

            <div class="side-divider"></div>
            <div class="side-section-title">🛠️ خدمات</div>
            <a href="/announcements" class="side-link">
                <span class="ico">📢</span><span>إعلانات الموقع</span>
            </a>
            <a href="#" onclick="openHelpModal(); return false;" class="side-link">
                <span class="ico">🆘</span><span>طلب مساعدة</span>
            </a>
        </div>

        <!-- MAIN -->
        <div class="main">
            <div class="hero">
                <h1>🚀 موقع المطري OTP</h1>
                <p>👑 أرقام سحب أكواد تطوير المطري 👑</p>
            </div>

            <div class="section-title"><span class="icon">🎯</span> اختر المنصة</div>
            <div class="platforms" id="platformSelector">
                {% for p in platforms_list %}
                <button type="button" class="platform-btn" data-platform="{{ p }}"
                    style="--pcolor: {{ platform_colors[p] }};">
                    <img src="{{ platform_logos[p] }}" alt="{{ platform_names[p] }}">
                    <span>{{ platform_names[p] }}</span>
                </button>
                {% endfor %}
            </div>

            <div class="section-title"><span class="icon">🌍</span> اختر الدولة</div>
            <div class="select-wrap">
                <select id="country" class="form-control" disabled>
                    <option value="">-- اختر المنصة أولاً --</option>
                </select>
            </div>

            <button class="btn btn-primary" id="getNumberBtn" onclick="getNumber()" disabled>🚀 جلب رقم</button>

            <div id="numberContainer" style="display:none;" dir="ltr">
                <div class="number-card" id="numberCard">
                    <div class="number-label">📞 الرقم المختار</div>
                    <div class="number" id="numberDisplay">+</div>
                    <button class="copy-btn-mini" id="copyNumBtn" onclick="copyNumber()">📋 نسخ الرقم</button>
                    <div class="countdown">
                        <div class="countdown-bar" id="countdownBar" style="width:100%;"></div>
                    </div>
                    <div class="countdown-text" id="countdownText">⏱️ صلاحية الرقم: <strong id="countdownValue">60</strong> ثانية</div>
                </div>
                <button class="btn btn-blue" id="refreshBtn" onclick="refreshNumber()">🔄 تبديل الرقم</button>
            </div>

            <div class="section-title" style="margin-top:18px;">📜 الأكواد المسحوبة <span style="margin-right:auto;font-size:11px;color:var(--text2);">الأحدث أولاً</span></div>
            <div class="otp-list" id="otpHistory">
                <div class="empty-state">⏳ في انتظار الأكواد...</div>
            </div>

            <div class="status" id="status">⚡ اختر المنصة والدولة للبدء</div>
        </div>

        <!-- FOOTER + TICKER -->
        <div class="footer-section">
            <div class="ticker-wrap">
                <span class="ticker-label">📢 مباشر</span>
                <div class="ticker-viewport">
                    <div class="ticker" id="tickerEl">
                        <span>🚀 مرحباً بك في <span class="name">المطري OTP</span></span>
                        <span>⚡ أسرع موقع سحب أكواد</span>
                        <span>👑 صُنع بحب بواسطة <span class="name">المطري</span></span>
                        <span>🌍 دعم 195+ دولة</span>
                        <span>📱 كل المنصات الاجتماعية</span>
                        <span>🔥 أكواد حقيقية وفورية</span>
                        <!-- مكرر للتمرير المستمر -->
                        <span>🚀 مرحباً بك في <span class="name">المطري OTP</span></span>
                        <span>⚡ أسرع موقع سحب أكواد</span>
                        <span>👑 صُنع بحب بواسطة <span class="name">المطري</span></span>
                        <span>🌍 دعم 195+ دولة</span>
                        <span>📱 كل المنصات الاجتماعية</span>
                        <span>🔥 أكواد حقيقية وفورية</span>
                    </div>
                </div>
            </div>
            <div class="footer-info">
                💎 صُنع بحب ⚡ بواسطة <strong>المطري</strong> 🔥
                <br><span style="opacity:0.6;">جميع الحقوق محفوظة © 2025</span>
            </div>
        </div>
    </div>

    <!-- مودال طلب المساعدة -->
    <div class="menu-overlay" id="helpOverlay" style="display:none;z-index:2000;" onclick="if(event.target===this) closeHelpModal()"></div>
    <div id="helpModal" style="display:none; position:fixed; inset:0; z-index:2001; align-items:center; justify-content:center; padding:20px;">
        <div style="background:var(--card); border:1px solid var(--border); border-radius:16px; padding:20px; max-width:400px; width:100%; max-height:80vh; overflow-y:auto;">
            <h2 style="color:#fff; margin-bottom:8px;">🆘 طلب مساعدة</h2>
            <p style="color:var(--text2); font-size:13px; margin-bottom:12px;">اشرح مشكلتك وسنرد عليك بأسرع وقت</p>
            <textarea id="helpMessage" placeholder="اكتب رسالتك هنا..."
                style="width:100%; min-height:100px; padding:10px; border-radius:8px; border:1px solid var(--border); background:var(--card2); color:var(--text); font-family:inherit; font-size:14px; resize:vertical;"></textarea>
            <div style="display:flex; gap:8px; margin-top:12px;">
                <button class="btn btn-blue" style="flex:1; margin:0;" onclick="closeHelpModal()">إلغاء</button>
                <button class="btn btn-primary" id="sendHelpBtn" style="flex:1; margin:0;" onclick="sendHelpRequest()">إرسال</button>
            </div>
            <div id="helpSuccess" style="display:none; margin-top:10px; padding:8px; background:#23863622; border:1px solid #238636; border-radius:8px; color:#3fb950; text-align:center; font-size:13px;">
                ✅ تم إرسال رسالتك! سنرد عليك قريباً
            </div>
        </div>
    </div>

    <script>
        // ========== إعدادات عامة ==========
        const OTP_COUNTDOWN = {{ otp_countdown }};
        const platformLogos = {{ platform_logos | tojson }};
        const platformNames = {{ platform_names | tojson }};
        const platformColors = {{ platform_colors | tojson }};
        const OWNER_LINK = "{{ owner_link }}";
        const WA_GROUP = "{{ wa_group }}";

        // ========== المطر الرقمي - lazy load ==========
        function initMatrix() {
            try {
                const canvas = document.getElementById('matrixCanvas');
                if (!canvas || !canvas.getContext) return;
                const ctx = canvas.getContext('2d');
                let w, h, cols, drops;
                function resize() {
                    w = canvas.width = window.innerWidth;
                    h = canvas.height = window.innerHeight;
                    cols = Math.max(20, Math.floor(w / 18));
                    drops = Array(cols).fill(0).map(()=>Math.random()*-50);
                }
                resize();
                let resizeTimer;
                window.addEventListener('resize', ()=>{
                    clearTimeout(resizeTimer);
                    resizeTimer = setTimeout(resize, 200);
                });
                const chars = '0123456789';
                let isVisible = true;
                document.addEventListener('visibilitychange', ()=>{
                    isVisible = !document.hidden;
                    if (isVisible) draw();
                });
                function draw() {
                    if (!isVisible) return;
                    try {
                        ctx.fillStyle = 'rgba(7, 9, 13, 0.08)';
                        ctx.fillRect(0, 0, w, h);
                        ctx.font = '15px monospace';
                        for (let i = 0; i < drops.length; i++) {
                            const text = chars[Math.floor(Math.random()*chars.length)];
                            const b = Math.random();
                            ctx.fillStyle = b > 0.95 ? '#ffffff' : b > 0.7 ? '#3fb950' : '#1f6feb';
                            ctx.fillText(text, i*18, drops[i]*18);
                            if (drops[i]*18 > h && Math.random() > 0.975) drops[i] = 0;
                            drops[i]++;
                        }
                    } catch(e) { return; }
                    requestAnimationFrame(draw);
                }
                draw();
            } catch(e) { console.warn('Matrix failed:', e); }
        }
        // lazy - بعد تحميل الصفحة
        if (window.requestIdleCallback) {
            requestIdleCallback(initMatrix, {timeout: 1500});
        } else {
            setTimeout(initMatrix, 300);
        }

        // ========== القائمة الجانبية ==========
        function toggleMenu() {
            const menu = document.getElementById('sideMenu');
            const overlay = document.getElementById('menuOverlay');
            const isOpen = menu.classList.contains('show');
            if (isOpen) {
                menu.classList.remove('show');
                overlay.classList.remove('show');
                document.body.style.overflow = '';
            } else {
                menu.classList.add('show');
                overlay.classList.add('show');
                document.body.style.overflow = 'hidden';
            }
        }

        // ========== الثيم ==========
        function toggleTheme() {
            const isLight = document.body.classList.toggle('light');
            document.getElementById('themeToggle').textContent = isLight ? '☀️' : '🌙';
            try { localStorage.setItem('theme', isLight ? 'light' : 'dark'); } catch(e) {}
        }
        function loadTheme() {
            try {
                if (localStorage.getItem('theme') === 'light') {
                    document.body.classList.add('light');
                    document.getElementById('themeToggle').textContent = '☀️';
                }
            } catch(e) {}
        }
        loadTheme();

        // ========== مودال المساعدة ==========
        function openHelpModal() {
            document.getElementById('helpModal').style.display = 'flex';
            document.getElementById('helpOverlay').style.display = 'block';
            document.getElementById('helpMessage').value = '';
            document.getElementById('helpSuccess').style.display = 'none';
        }
        function closeHelpModal() {
            document.getElementById('helpModal').style.display = 'none';
            document.getElementById('helpOverlay').style.display = 'none';
        }
        async function sendHelpRequest() {
            const msg = document.getElementById('helpMessage').value.trim();
            if (!msg) { alert('الرجاء كتابة رسالتك'); return; }
            const btn = document.getElementById('sendHelpBtn');
            btn.disabled = true; btn.innerHTML = '<span class="loading"></span> جاري الإرسال...';
            try {
                const res = await fetch('/api/help', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: msg})
                });
                const data = await res.json();
                if (data.ok) {
                    document.getElementById('helpSuccess').style.display = 'block';
                    document.getElementById('helpMessage').value = '';
                    setTimeout(closeHelpModal, 2000);
                } else {
                    alert('❌ فشل الإرسال: ' + (data.error || 'حاول مرة أخرى'));
                }
            } catch(e) {
                alert('❌ فشل الاتصال بالخادم');
            }
            btn.disabled = false; btn.innerHTML = 'إرسال';
        }

        // ========== نسخ ==========
        async function copyNumber() {
            const num = document.getElementById('numberDisplay').textContent;
            try { await navigator.clipboard.writeText(num); } catch(e) {}
            const btn = document.getElementById('copyNumBtn');
            btn.classList.add('copied');
            btn.innerHTML = '✅ تم النسخ';
            setTimeout(() => {
                btn.classList.remove('copied');
                btn.innerHTML = '📋 نسخ الرقم';
            }, 1500);
        }

        // ========== Countdown ==========
        let countdownTimer = null;
        function startCountdown() {
            const bar = document.getElementById('countdownBar');
            const text = document.getElementById('countdownText');
            const val = document.getElementById('countdownValue');
            if (countdownTimer) clearInterval(countdownTimer);
            bar.classList.remove('warn', 'expired');
            bar.style.width = '100%';
            text.classList.remove('warn', 'expired');
            val.textContent = OTP_COUNTDOWN;
            let remaining = OTP_COUNTDOWN;
            countdownTimer = setInterval(() => {
                remaining--;
                val.textContent = remaining;
                const pct = (remaining / OTP_COUNTDOWN) * 100;
                bar.style.width = pct + '%';
                if (remaining <= 15) {
                    bar.classList.add('warn');
                    text.classList.add('warn');
                }
                if (remaining <= 0) {
                    clearInterval(countdownTimer);
                    countdownTimer = null;
                    bar.classList.add('expired');
                    text.classList.add('expired');
                    val.textContent = '0';
                    document.getElementById('status').textContent = '⏰ انتهت صلاحية الرقم';
                    document.getElementById('status').className = 'status error';
                }
            }, 1000);
        }
        function stopCountdown() {
            if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null; }
        }

        // ========== صوت الإشعار ==========
        function playNotificationSound() {
            try {
                const Ctx = window.AudioContext || window.webkitAudioContext;
                if (!Ctx) return;
                const ctx = new Ctx();
                const now = ctx.currentTime;
                const notes = [
                    {f: 880, d: 0.15}, {f: 1108, d: 0.15}, {f: 1318, d: 0.25}
                ];
                notes.forEach((n, i) => {
                    const o = ctx.createOscillator();
                    const g = ctx.createGain();
                    o.connect(g); g.connect(ctx.destination);
                    o.type = 'sine';
                    o.frequency.setValueAtTime(n.f, now + i*0.15);
                    g.gain.setValueAtTime(0, now + i*0.15);
                    g.gain.linearRampToValueAtTime(0.25, now + i*0.15 + 0.02);
                    g.gain.linearRampToValueAtTime(0, now + i*0.15 + n.d);
                    o.start(now + i*0.15);
                    o.stop(now + i*0.15 + n.d);
                });
            } catch(e) {}
        }

        // ========== المنصات ==========
        let currentPlatform = '';
        let currentNumber = '';
        let autoMonitorTimer = null;
        let autoMonitorSeconds = 0;
        let usedNumbers = new Set();

        function initPlatformSelector() {
            document.querySelectorAll('.platform-btn').forEach(btn => {
                const platform = btn.getAttribute('data-platform');
                btn.onclick = () => selectPlatform(platform, btn);
            });
        }

        function selectPlatform(platform, btn) {
            currentPlatform = platform;
            document.querySelectorAll('.platform-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const color = platformColors[platform] || '#3fb950';
            const card = document.getElementById('numberCard');
            if (card) {
                card.style.setProperty('--ncolor', color);
            }
            loadCountries();
        }

        async function loadCountries() {
            const sel = document.getElementById('country');
            if (!currentPlatform) {
                sel.innerHTML = '<option value="">-- اختر المنصة أولاً --</option>';
                sel.disabled = true;
                document.getElementById('getNumberBtn').disabled = true;
                return;
            }
            sel.disabled = true;
            sel.innerHTML = '<option value="">جاري التحميل...</option>';
            try {
                const res = await fetch('/api/countries', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({platform: currentPlatform})
                });
                const data = await res.json();
                let options = '<option value="">-- اختر الدولة --</option>';
                data.forEach(c => {
                    options += `<option value="${c.code}">${c.flag} ${c.name}</option>`;
                });
                sel.innerHTML = options;
                sel.disabled = false;
            } catch(e) {
                sel.innerHTML = '<option value="">-- خطأ في التحميل --</option>';
            }
        }

        document.getElementById('country').addEventListener('change', function() {
            document.getElementById('getNumberBtn').disabled = !this.value;
        });

        async function getNumber() {
            const country = document.getElementById('country').value;
            if (!currentPlatform || !country) return;
            const btn = document.getElementById('getNumberBtn');
            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span> جاري الجلب...';
            try {
                const res = await fetch('/api/get_number', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({platform: currentPlatform, country})
                });
                const data = await res.json();
                if (data.number) {
                    showNumber(data.number);
                    setStatus('✅ الرقم جاهز! يبدأ العد التنازلي', 'success');
                } else {
                    setStatus('❌ لا توجد أرقام متاحة', 'error');
                }
            } catch(e) {
                setStatus('❌ خطأ في الاتصال', 'error');
            }
            btn.disabled = false;
            btn.innerHTML = '🚀 جلب رقم';
        }

        async function refreshNumber() {
            const country = document.getElementById('country').value;
            if (!currentPlatform || !country) return;
            const btn = document.getElementById('refreshBtn');
            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span> جاري التبديل...';
            try {
                const res = await fetch('/api/get_number', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({platform: currentPlatform, country})
                });
                const data = await res.json();
                if (data.number && data.number !== currentNumber) {
                    showNumber(data.number);
                    setStatus('🔄 تم التبديل!', 'success');
                } else {
                    setStatus('⚠️ لا يوجد رقم آخر متاح', 'error');
                }
            } catch(e) {
                setStatus('❌ خطأ', 'error');
            }
            btn.disabled = false;
            btn.innerHTML = '🔄 تبديل الرقم';
        }

        function showNumber(num) {
            currentNumber = num;
            const display = document.getElementById('numberDisplay');
            display.textContent = '';
            const full = '+' + num;
            [...full].forEach((ch, i) => {
                const span = document.createElement('span');
                span.className = 'digit';
                span.textContent = ch;
                span.style.animationDelay = (i * 0.06) + 's';
                display.appendChild(span);
            });
            document.getElementById('numberContainer').style.display = 'block';
            startCountdown();
            startAutoMonitor();
        }

        function setStatus(text, type) {
            const el = document.getElementById('status');
            el.textContent = text;
            el.className = 'status' + (type ? ' ' + type : '');
        }

        // ========== المراقبة التلقائية للأكواد ==========
        function startAutoMonitor() {
            stopAutoMonitor();
            autoMonitorSeconds = 0;
            setStatus('🔄 جاري المراقبة التلقائية للأكواد...', '');
            autoMonitorTimer = setInterval(async () => {
                autoMonitorSeconds += 5;
                if (autoMonitorSeconds >= OTP_COUNTDOWN) {
                    stopAutoMonitor();
                    return;
                }
                if (!currentNumber) return;
                try {
                    const res = await fetch('/api/get_otp', {
                        method: 'POST', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({number: currentNumber})
                    });
                    const data = await res.json();
                    if (data.otp) {
                        addOtpToHistory(currentNumber, data.otp, currentPlatform);
                        setStatus('✅ تم العثور على كود!', 'success');
                        playNotificationSound();
                        stopCountdown();
                        stopAutoMonitor();
                    }
                } catch(e) {}
            }, 5000);
        }
        function stopAutoMonitor() {
            if (autoMonitorTimer) { clearInterval(autoMonitorTimer); autoMonitorTimer = null; }
        }

        // ========== إدارة الأكواد ==========
        function addOtpToHistory(number, otp, platform) {
            const container = document.getElementById('otpHistory');
            if (container.querySelector('.empty-state')) container.innerHTML = '';
            const div = document.createElement('div');
            div.className = 'otp-item fresh';
            const now = new Date().toLocaleString('ar-YE', {timeZone:'Asia/Aden'});
            const color = platformColors[platform] || '#3fb950';
            const icon = platformLogos[platform] || '';
            div.innerHTML = `
                <div style="flex:1; min-width:0;">
                    <div class="otp-code" style="color:${color};text-shadow:0 0 6px ${color};">🔑 ${otp}</div>
                    <div class="otp-info">📞 +${number} • 🕒 ${now} • ${icon} ${platformNames[platform] || ''}</div>
                </div>
                <div class="otp-item-btns">
                    <button class="otp-btn copy-otp" data-otp="${otp}">نسخ</button>
                    <button class="otp-btn delete delete-otp" data-otp="${otp}">🗑️</button>
                </div>
            `;
            // ربط الأحداث
            div.querySelector('.copy-otp').onclick = function() {
                copyOtp(this.getAttribute('data-otp'), this);
            };
            const delBtn = div.querySelector('.delete-otp');
            delBtn.onclick = function() {
                deleteOtpFromList(this, this.getAttribute('data-otp'));
            };
            container.prepend(div);
            if (container.children.length > 30) container.removeChild(container.lastChild);
            setTimeout(()=>div.classList.remove('fresh'), 4000);
        }

        function copyOtp(otp, btn) {
            try { navigator.clipboard.writeText(otp); } catch(e) {}
            const orig = btn.textContent;
            btn.textContent = '✅';
            btn.style.color = '#3fb950';
            btn.style.borderColor = '#3fb950';
            setTimeout(() => {
                btn.textContent = orig;
                btn.style.color = '';
                btn.style.borderColor = '';
            }, 1500);
        }

        // ✅ الحذف الحقيقي - يمسح من السيرفر فوراً
        async function deleteOtpFromList(btn, otp) {
            if (!confirm('هل تريد حذف هذا الكود نهائياً؟')) return;
            btn.classList.add('working');
            btn.disabled = true;
            const origHtml = btn.innerHTML;
            btn.innerHTML = '<span class="loading"></span>';
            try {
                // حذف بصرياً أولاً
                const item = btn.closest('.otp-item');
                item.style.transition = 'all 0.3s';
                item.style.opacity = '0';
                item.style.transform = 'translateX(20px)';
                setTimeout(() => item.remove(), 300);

                // حذف حقيقي من السيرفر
                const res = await fetch('/api/delete_otp', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({otp: otp})
                });
                const data = await res.json();
                if (!data.ok) {
                    console.warn('Delete failed:', data.error);
                } else {
                    console.log('✅ OTP deleted:', data.deleted);
                }
            } catch(e) {
                btn.classList.remove('working');
                btn.disabled = false;
                btn.innerHTML = origHtml;
                alert('❌ فشل الحذف');
            }
        }

        // ========== تحميل أولي للأكواد ==========
        async function loadInitialOtps() {
            try {
                const res = await fetch('/api/all_otps');
                const list = await res.json();
                if (list && list.length) {
                    const container = document.getElementById('otpHistory');
                    container.innerHTML = '';
                    list.slice(0, 30).forEach(item => {
                        const div = document.createElement('div');
                        div.className = 'otp-item';
                        const platform = (item.platform || '').toLowerCase();
                        const color = platformColors[platform] || '#3fb950';
                        const icon = platformLogos[platform] || '';
                        const pname = platformNames[platform] || item.platform || '';
                        div.innerHTML = `
                            <div style="flex:1; min-width:0;">
                                <div class="otp-code" style="color:${color};text-shadow:0 0 6px ${color};">🔑 ${item.otp}</div>
                                <div class="otp-info">📞 ${item.number} • 🕒 ${item.timestamp} • ${icon} ${pname}</div>
                            </div>
                            <div class="otp-item-btns">
                                <button class="otp-btn copy-otp" data-otp="${item.otp}">نسخ</button>
                                <button class="otp-btn delete delete-otp" data-otp="${item.otp}">🗑️</button>
                            </div>
                        `;
                        div.querySelector('.copy-otp').onclick = function() {
                            copyOtp(this.getAttribute('data-otp'), this);
                        };
                        const delBtn = div.querySelector('.delete-otp');
                        delBtn.onclick = function() {
                            deleteOtpFromList(this, this.getAttribute('data-otp'));
                        };
                        container.appendChild(div);
                    });
                }
            } catch(e) { console.warn('Load OTPs failed:', e); }
        }

        // ========== التهيئة عند التحميل ==========
        document.addEventListener('DOMContentLoaded', () => {
            initPlatformSelector();
            loadInitialOtps();
        });
    </script>
</body>
</html>
"""

# ========== صفحة الأدمن ==========
admin_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>⚙️ لوحة تحكم المطري</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body {
    font-family:'Cairo',sans-serif;
    background:linear-gradient(135deg, #0a0e1a, #1a1f2e);
    color:#fff; min-height:100vh; padding:20px;
}
.container {
    background:rgba(17, 24, 39, 0.85); backdrop-filter:blur(20px);
    padding:30px; border-radius:25px; width:100%; max-width:480px;
    margin:0 auto; border:1px solid rgba(139, 92, 246, 0.3);
    box-shadow:0 0 50px rgba(139, 92, 246, 0.3);
}
h1 {
    text-align:center;
    background:linear-gradient(90deg, #00ffc8, #8b5cf6);
    -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
    margin-bottom:25px; font-size:26px; font-weight:900;
}
h3 { color:#cbd5e1; margin:18px 0 12px; font-size:15px; }
.form-group { margin-bottom:15px; }
.form-group label { display:block; margin-bottom:6px; color:#cbd5e1; font-weight:700; font-size:13px; }
.form-control {
    width:100%; padding:12px; border-radius:12px;
    border:2px solid rgba(255,255,255,0.1);
    background:rgba(31, 41, 55, 0.7); color:#fff;
    font-family:inherit; font-size:14px;
    transition:all 0.3s;
}
.form-control:focus { border-color:#00ffc8; box-shadow:0 0 20px rgba(0,255,200,0.3); outline:none; }
.btn {
    width:100%; padding:14px; border:none; border-radius:12px;
    color:#0a0e1a; cursor:pointer; margin-top:10px;
    font-weight:900; font-size:15px; font-family:inherit;
    transition:all 0.3s; display:block; text-align:center; text-decoration:none;
}
.btn-primary {
    background:linear-gradient(135deg, #00ff88, #00d2ff);
    box-shadow:0 0 20px rgba(0,255,136,0.4);
}
.btn-primary:hover { transform:translateY(-2px); box-shadow:0 5px 30px rgba(0,255,136,0.6); }
.btn-danger {
    background:linear-gradient(135deg, #ef4444, #b91c1c);
    color:#fff; box-shadow:0 0 20px rgba(239, 68, 68, 0.4);
    padding:8px 14px; font-size:13px; margin:0; width:auto; display:inline-block;
}
.btn-danger:hover { transform:translateY(-1px); }
.btn-secondary {
    background:linear-gradient(135deg, #374151, #4b5563);
    color:#fff;
}
.btn-secondary:hover { transform:translateY(-2px); }
.btn-home {
    background:linear-gradient(135deg, #1f6feb, #388bfd);
    color:#fff;
}
hr { border:1px solid rgba(255,255,255,0.1); margin:20px 0; }
.combo-item {
    display:flex; justify-content:space-between; align-items:center; gap:10px;
    background:rgba(31, 41, 55, 0.7); padding:12px;
    border-radius:12px; margin-bottom:10px;
    border:1px solid rgba(139, 92, 246, 0.3);
}
.combo-item .info { flex:1; min-width:0; }
.combo-item span { color:#fff; font-weight:600; font-size:14px; }
.combo-item .meta { color:#94a3b8; font-size:11px; margin-top:2px; }
.empty { color:#64748b; text-align:center; padding:20px; }
.stats {
    display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:20px;
}
.stat-card {
    background:rgba(31, 41, 55, 0.7); border:1px solid rgba(139, 92, 246, 0.3);
    border-radius:12px; padding:14px; text-align:center;
}
.stat-value { font-size:22px; font-weight:900; color:#00ffc8; }
.stat-label { font-size:11px; color:#94a3b8; margin-top:4px; }
.danger-form { display:inline; }
</style>
</head>
<body>
<div class="container">
    <h1>⚙️ لوحة تحكم المطري</h1>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-value">{{ combos|length }}</div>
            <div class="stat-label">📦 كومبو مرفوع</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" id="otpCount">0</div>
            <div class="stat-label">🔑 كود في السجل</div>
        </div>
    </div>

    <h3>📤 رفع كومبو جديد</h3>
    <form method="POST" enctype="multipart/form-data">
        <div class="form-group">
            <label>📱 المنصة</label>
            <select name="platform" class="form-control" required>
                <option value="whatsapp">📱 واتساب</option>
                <option value="telegram">✈️ تيليجرام</option>
                <option value="tiktok">🎵 تيك توك</option>
                <option value="facebook">📘 فيسبوك</option>
                <option value="instagram">📸 انستقرام</option>
                <option value="snapchat">👻 سناب شات</option>
                <option value="google">🔍 جوجل</option>
                <option value="twitter">🐦 تويتر/X</option>
            </select>
        </div>
        <div class="form-group">
            <label>📁 ارفع ملف الأرقام (.txt)</label>
            <input type="file" name="file" accept=".txt" class="form-control" required>
        </div>
        <button type="submit" class="btn btn-primary">📤 رفع الكومبو</button>
    </form>

    <hr>

    <h3>🗑️ حذف كومبو</h3>
    {% if combos %}
        {% for platform, code, name, flag in combos %}
        <div class="combo-item">
            <div class="info">
                <span>{{ flag }} {{ name }}</span>
                <div class="meta">{{ platform }} • {{ code }}</div>
            </div>
            <form method="POST" class="danger-form">
                <input type="hidden" name="action" value="delete">
                <input type="hidden" name="platform" value="{{ platform }}">
                <input type="hidden" name="country_code" value="{{ code }}">
                <button type="submit" class="btn btn-danger" onclick="return confirm('حذف كومبو {{ name }}؟')">🗑️</button>
            </form>
        </div>
        {% endfor %}
    {% else %}
        <p class="empty">🤷‍♂️ لا توجد كومبوهات حالياً</p>
    {% endif %}

    <hr>

    <h3>⚠️ منطقة الخطر</h3>
    <form method="POST" onsubmit="return confirm('هل أنت متأكد من حذف جميع الأكواد؟')">
        <input type="hidden" name="action" value="clear_otps">
        <button type="submit" class="btn" style="background:linear-gradient(135deg, #f59e0b, #d97706); color:#fff;">🧹 مسح كل الأكواد من السجل</button>
    </form>

    <hr>

    <a href="/" class="btn btn-home">🔙 العودة للصفحة الرئيسية</a>
</div>

<script>
    fetch('/api/otp_count').then(r=>r.json()).then(d=>{
        document.getElementById('otpCount').textContent = d.count || 0;
    }).catch(()=>{});
</script>
</body>
</html>
"""

# ========== صفحة الإعلانات ==========
announcements_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>إعلانات الموقع</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Cairo',system-ui,sans-serif; background:#07090d; color:#c9d1d9; min-height:100vh; padding:16px; }
.container { max-width:480px; margin:0 auto; }
h1 { color:#fff; text-align:center; margin-bottom:20px; font-size:22px; }
.back { display:inline-block; background:#1f6feb; color:#fff; padding:10px 18px; border-radius:8px; text-decoration:none; font-weight:700; margin-bottom:16px; }
.card { background:#1c2128; border:1px solid #30363d; border-radius:12px; padding:16px; margin-bottom:12px; }
.empty { text-align:center; color:#8b949e; padding:40px 20px; }
</style>
</head>
<body>
<div class="container">
    <a href="/" class="back">← العودة</a>
    <h1>📢 إعلانات الموقع</h1>
    <div id="content" class="empty">جاري التحميل...</div>
</div>
<script>
fetch('/api/all_otps').then(r=>r.json()).then(d=>{
    const c = document.getElementById('content');
    if (!d.length) { c.className = 'empty'; c.innerHTML = 'لا توجد إعلانات حالياً'; return; }
    c.className = '';
    c.innerHTML = d.slice(0, 20).map(item => `
        <div class="card">
            <div style="font-size:14px; color:#fff; font-weight:700;">🔑 ${item.otp}</div>
            <div style="font-size:11px; color:#8b949e; margin-top:4px;">📞 ${item.number} • 🕒 ${item.timestamp}</div>
        </div>
    `).join('');
}).catch(()=>{
    document.getElementById('content').innerHTML = '❌ خطأ في التحميل';
});
</script>
</body>
</html>
"""

# ========== المساعد: login required ==========
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/admin_login')
        return f(*args, **kwargs)
    return decorated_function

# ========== Routes ==========
@app.route('/')
def home():
    return render_template_string(
        main_html,
        owner_link=OWNER_LINK,
        wa_group=WHATSAPP_GROUP_LINK,
        owner_tg=OWNER_TELEGRAM_USERNAME,
        platform_logos=PLATFORM_LOGOS,
        platform_names=platform_names,
        platform_colors=platform_colors,
        platforms_list=PLATFORMS_ORDER,
        otp_countdown=OTP_COUNTDOWN
    )

@app.route('/announcements')
def announcements():
    return render_template_string(announcements_html)

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(f'/{ADMIN_SECRET_PATH}')
        return "❌ كلمة المرور خاطئة", 401
    return '''
    <div dir="rtl" style="text-align:center; margin-top:100px; font-family:'Cairo',sans-serif; background:#0d1117; color:#fff; padding:50px; border-radius:20px; max-width:400px; margin:100px auto;">
        <h2>🔐 دخول الأدمن</h2>
        <form method="POST">
            <input type="password" name="password" placeholder="كلمة المرور" style="padding:12px; border-radius:8px; border:1px solid #30363d; background:#161b22; color:#fff; width:100%; margin-bottom:10px; box-sizing:border-box;">
            <button type="submit" style="padding:12px 25px; background:#238636; color:#fff; border:none; border-radius:8px; cursor:pointer; font-weight:bold; width:100%;">دخول</button>
        </form>
    </div>
    '''

@app.route(f'/{ADMIN_SECRET_PATH}', methods=['GET', 'POST'])
@login_required
def admin():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'delete':
            platform = request.form.get('platform')
            code = request.form.get('country_code')
            if platform and code:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("DELETE FROM combos WHERE platform=? AND country_code=?", (platform, code))
                conn.commit()
                conn.close()
                invalidate_cache()
        elif action == 'clear_otps':
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM otp_logs")
            conn.commit()
            conn.close()
            invalidate_cache()
        else:
            platform = request.form.get('platform')
            file = request.files.get('file')
            if file and file.filename.endswith('.txt'):
                content = file.read().decode('utf-8')
                numbers = [line.strip() for line in content.splitlines() if line.strip()]
                if numbers:
                    first = numbers[0].lstrip('+')
                    codes = sorted(COUNTRY_DATA.keys(), key=len, reverse=True)
                    cc = None
                    for c in codes:
                        if first.startswith(c):
                            cc = c
                            break
                    if cc:
                        name, flag = get_country_info(cc)
                        save_combo(platform, cc, name, flag, numbers)
        return redirect(f'/{ADMIN_SECRET_PATH}')

    combos = get_all_combos_list()
    return render_template_string(admin_html, combos=combos)

# ========== APIs ==========
@app.route('/api/countries', methods=['POST'])
def api_countries():
    return jsonify(get_countries_by_platform(request.json.get('platform')))

@app.route('/api/get_number', methods=['POST'])
def api_get_number():
    d = request.json
    nums = get_numbers(d['platform'], d['country'])
    if not nums:
        return jsonify({'number': None})
    return jsonify({'number': random.choice(nums)})

@app.route('/api/get_otp', methods=['POST'])
def api_get_otp():
    num = request.json.get('number')
    if not num:
        return jsonify({'otp': None})
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # جلب الكود من آخر دقيقتين فقط
    c.execute(
        "SELECT otp FROM otp_logs WHERE number=? AND timestamp >= datetime('now', '-2 minutes') ORDER BY id DESC LIMIT 1",
        (num[-10:],)
    )
    row = c.fetchone()
    if not row:
        c.execute("SELECT otp FROM otp_logs WHERE number=? ORDER BY id DESC LIMIT 1", (num[-10:],))
        row = c.fetchone()
    conn.close()
    return jsonify({'otp': row[0] if row else None})

# كاش للأكواد
_otp_cache = {'data': None, 'time': 0}
CACHE_DURATION = 5  # قصير جداً حتى التحديثات تنعكس بسرعة

def invalidate_cache():
    global _otp_cache
    _otp_cache['data'] = None
    _otp_cache['time'] = 0

@app.route('/api/all_otps', methods=['GET'])
def api_all_otps():
    now = time.time()
    if _otp_cache['data'] is not None and (now - _otp_cache['time']) < CACHE_DURATION:
        return jsonify(_otp_cache['data'])
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, number, otp, timestamp, platform, country_code, country_flag FROM otp_logs ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    result = [{
        'id': r[0], 'number': r[1], 'otp': r[2], 'timestamp': r[3],
        'platform': (r[4] or 'unknown').lower(), 'country_code': r[5] or '', 'country_flag': r[6] or '🌍'
    } for r in rows]
    _otp_cache['data'] = result
    _otp_cache['time'] = now
    return jsonify(result)

# ✅ الحذف الحقيقي للـ OTP
@app.route('/api/delete_otp', methods=['POST'])
def api_delete_otp():
    data = request.json or {}
    otp = data.get('otp')
    if not otp:
        return jsonify({'ok': False, 'error': 'OTP required'}), 400
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # حذف كل الأكواد المطابقة (في حالة التكرار)
        c.execute("DELETE FROM otp_logs WHERE otp=?", (otp,))
        deleted = c.rowcount
        conn.commit()
        conn.close()
        invalidate_cache()
        return jsonify({'ok': True, 'deleted': deleted})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/otp_count', methods=['GET'])
def api_otp_count():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM otp_logs")
    count = c.fetchone()[0]
    conn.close()
    return jsonify({'count': count})

# ========== طلب المساعدة ==========
@app.route('/api/help', methods=['POST'])
def api_help():
    msg = (request.json.get('message') or '').strip()
    if not msg:
        return jsonify({'ok': False, 'error': 'الرسالة فارغة'}), 400
    user_id = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown')
    # إرسال للتلجرام
    try:
        admin_id = get_setting('admin_telegram_id', '').strip()
        targets = []
        if admin_id: targets.append(admin_id)
        targets.append(f"@{OWNER_TELEGRAM_USERNAME}")
        help_text = f"🆘 <b>طلب مساعدة</b>\n👤 <code>{user_id}</code>\n💬 {msg}\n🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        for t in targets:
            try:
                r = requests.post(
                    f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/sendMessage",
                    json={'chat_id': t, 'text': help_text, 'parse_mode': 'HTML'},
                    timeout=8
                )
                if r.status_code == 200:
                    break
            except: continue
    except Exception as e:
        print(f"⚠️ Help notify error: {e}")
    return jsonify({'ok': True})

# ========== مراقب القناة (يحفظ الأكواد الجديدة) ==========
def monitor_channel():
    last_update_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            r = requests.get(url, params={"timeout": 10, "offset": last_update_id + 1}, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if data.get('ok'):
                    for upd in data.get('result', []):
                        last_update_id = upd['update_id']
                        if 'channel_post' in upd:
                            text = upd['channel_post'].get('text', '')
                            if not text: continue
                            clean = re.sub(r'[\u200B-\u200F\u202A-\u202E‏‎]', '', text)
                            
                            user_number = None
                            last_digits = None
                            
                            hidden = re.search(r'(\d{3,4})[•*]{2,6}(\d{3,4})', clean)
                            if hidden:
                                user_number = hidden.group(1) + hidden.group(2)
                                last_digits = user_number[-4:]
                            
                            if not user_number:
                                all_nums = re.findall(r'\b\d{8,15}\b', clean)
                                if all_nums:
                                    user_number = max(all_nums, key=len)
                                    last_digits = user_number[-4:]
                            
                            if not user_number:
                                star = re.search(r'(\d{3})\*{2,6}(\d{3,4})', clean)
                                if star:
                                    user_number = star.group(1) + star.group(2)
                                    last_digits = user_number[-4:]
                            
                            otp = None
                            dash = re.search(r'(\d{3})-(\d{3,4})', clean)
                            if dash:
                                otp = dash.group(1) + dash.group(2)
                            
                            if not otp:
                                codes = re.findall(r'\b\d{4,8}\b', clean)
                                if codes:
                                    for c in codes:
                                        if last_digits and c.endswith(last_digits): continue
                                        if len(c) >= 4:
                                            otp = c
                                            break
                            
                            if not otp:
                                patterns = [
                                    r'(?:كود|رمز|code|otp)[:\s\-]*[‎]?(\d{3,8})',
                                    r'#(\d{3,8})',
                                    r'(\d{6,8})\s*(?:هو|هذا|كود)',
                                ]
                                for p in patterns:
                                    m = re.search(p, clean, re.IGNORECASE)
                                    if m:
                                        otp = m.group(1)
                                        break
                            
                            platform = "غير معروف"
                            tl = clean.lower()
                            platforms = {
                                "whatsapp": ["wa", "whatsapp", "واتساب"],
                                "facebook": ["fb", "facebook", "فيسبوك"],
                                "telegram": ["tg", "telegram", "تيليجرام", "تلجرام"],
                                "tiktok": ["tt", "tiktok", "تيك توك"],
                                "instagram": ["ig", "instagram", "انستقرام"],
                                "snapchat": ["sc", "snapchat", "سناب"],
                                "google": ["gg", "google", "جوجل"],
                                "twitter": ["tw", "twitter", "تويتر"]
                            }
                            for name, kws in platforms.items():
                                if any(kw in tl for kw in kws):
                                    platform = name
                                    break
                            
                            if otp:
                                conn = sqlite3.connect(DB_PATH)
                                c = conn.cursor()
                                num_to_store = last_digits or "0000"
                                # استخراج كود الدولة إن أمكن
                                cc = None
                                if num_to_store != "0000" and len(num_to_store) >= 4:
                                    for code in sorted(COUNTRY_DATA.keys(), key=len, reverse=True):
                                        if num_to_store.startswith(code):
                                            cc = code
                                            break
                                flag = "🌍"
                                if cc:
                                    _, flag = get_country_info(cc)
                                c.execute(
                                    "INSERT INTO otp_logs (number, otp, timestamp, platform, country_code, country_flag) VALUES (?, ?, ?, ?, ?, ?)",
                                    (num_to_store, otp, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), platform, cc, flag)
                                )
                                conn.commit()
                                conn.close()
                                invalidate_cache()
                                print(f"✅ [{platform}] {otp} | {num_to_store}")
        except Exception as e:
            print(f"❌ Monitor error: {e}")
        time.sleep(5)

threading.Thread(target=monitor_channel, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
