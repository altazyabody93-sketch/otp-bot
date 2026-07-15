from flask import Flask, request, render_template_string, jsonify, redirect, url_for
import sqlite3
import json
import random
import os
import re
import requests
import threading
import time
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "secret_key_for_session_123"
DB_PATH = "bot.db"

# ========== إعدادات الأمان ==========
ADMIN_PASSWORD = "123"
ADMIN_SECRET_PATH = "admin_secret_77"

WHATSAPP_GROUP_LINK = "https://chat.whatsapp.com/IeK2gNS64fd8YSnenzt4WR"
OWNER_PHONE = "967733723953"
OWNER_LINK = f"https://wa.me/{OWNER_PHONE}"

TELEGRAM_BOT_TOKEN = "8814038881:AAGyuACUYA4YPKlJQhAyUMkpRNiV0u1gNuU"
CHANNEL_USERNAME = "@jsjsgsjsvh"
ASSISTANT_BOT_TOKEN = "8845420882:AAHZ-7qhCL3_ddDT3am4zWNtBRBy3mVDgws"
OWNER_TELEGRAM_ID = "@ABOD_90N"
TELEGRAM_GROUP_INVITE = "https://t.me/ABOD_90N"
TELEGRAM_GROUP_CHAT_ID = "AUTO_DETECT"

# ========== قاعدة البيانات ==========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS combos (id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, country_code TEXT, country_name TEXT, country_flag TEXT, numbers TEXT, UNIQUE(platform, country_code))''')
    c.execute('''CREATE TABLE IF NOT EXISTS otp_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT, otp TEXT, timestamp TEXT, platform TEXT, country_code TEXT, country_flag TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS announcements (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, content TEXT, media_url TEXT, button_text TEXT, button_url TEXT, source_msg_id INTEGER, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS help_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, message TEXT, source TEXT, status TEXT DEFAULT 'pending', created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS known_chats (chat_id TEXT PRIMARY KEY, chat_type TEXT, chat_title TEXT, last_seen TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS admin_settings (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)''')
    conn.commit()
    conn.close()
init_db()

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
    c.execute(
        "INSERT INTO admin_settings (key, value, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (key, value, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

def notify_admin(text):
    admin_id = get_admin_setting('admin_telegram_id')
    if not admin_id:
        return False
    try:
        requests.post(
            f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/sendMessage",
            json={'chat_id': admin_id, 'text': text, 'parse_mode': 'HTML'},
            timeout=10
        )
        return True
    except Exception as e:
        print(f"⚠️ فشل إشعار الأدمن: {e}")
        return False

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
    "355": {"n": "ألبانيا", "f": "🇦🇱"},
    "356": {"n": "مالطا", "f": "🇲🇹"},
    "357": {"n": "قبرص", "f": "🇨🇾"},
    "358": {"n": "فنلندا", "f": "🇫🇮"},
    "359": {"n": "بلغاريا", "f": "🇧🇬"},
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
    "880": {"n": "بنغلاديش", "f": "🇧🇩"},
    "886": {"n": "تايوان", "f": "🇹🇼"},
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
    "whatsapp": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%2325D366'/><path fill='%23fff' d='M50 18c-17.6 0-32 14.4-32 32 0 6 1.7 11.8 4.8 16.8L18 82l15.6-4.7C38.6 80.1 44.2 82 50 82c17.6 0 32-14.4 32-32S67.6 18 50 18zm18.6 45.6c-.8 2.2-4.6 4.2-6.4 4.5-1.6.3-3.7.4-5.9-.4-1.4-.5-3.1-1.1-5.4-2.2-9.5-4.1-15.7-13.7-16.2-14.3-.5-.7-3.9-5.1-3.9-9.7s2.4-6.9 3.3-7.9c.9-.9 1.9-1.2 2.6-1.2.6 0 1.2 0 1.7 0 .6 0 1.3-.2 2 .1 1.6.7 2.6 3 2.9 3.9.3.9.5 1.5 0 2.4-.4.9-1.5 2.4-2.2 3.4 0 0 .7.7 1.4 1.5 2.4 2.7 5.3 5.5 9.6 7.1 1.5.5 2.3.6 3-.4.6-1 2.5-3 3.2-4 .7-1 1.4-.8 2.3-.5.9.3 5.8 2.7 6.8 3.2 1 .5 1.6.7 1.8 1.1.2.5.2 2.5-.6 4.7z'/></svg>",
    "facebook": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%231877F2'/><path fill='%23fff' d='M58 84V52h10l1-12H58v-7c0-3 1-5 5-5h6V17h-9c-10 0-15 6-15 14v9H36v12h9v32h13z'/></svg>",
    "snapchat": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%23FFFC00'/><path fill='%23000' d='M50 16c-13 0-23 9-23 21 0 6 1 11 2 16-2 1-4 2-7 2-1 0-2 1-2 2 0 4 8 5 11 7 1 1 1 4 2 6 1 3 4 5 8 5 3 0 5-1 7-1 3 0 6 6 13 6 7 0 10-6 13-6 2 0 4 1 7 1 4 0 7-2 8-5 1-2 1-5 2-6 3-2 11-3 11-7 0-1-1-2-2-2-3 0-5-1-7-2 1-5 2-10 2-16 0-12-10-21-23-21-3 0-6 1-8 2-2-1-5-2-8-2z'/></svg>",
    "instagram": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><defs><radialGradient id='ig' cx='30%25' cy='30%25' r='80%25'><stop offset='0%25' stop-color='%23FEDA75'/><stop offset='50%25' stop-color='%23FA7E1E'/><stop offset='100%25' stop-color='%23D62976'/></radialGradient></defs><rect width='100' height='100' rx='22' fill='url(%23ig)'/><rect x='22' y='22' width='56' height='56' rx='14' fill='none' stroke='%23fff' stroke-width='5'/><circle cx='50' cy='50' r='13' fill='none' stroke='%23fff' stroke-width='5'/><circle cx='72' cy='28' r='4' fill='%23fff'/></svg>",
    "telegram": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%2326A5E4'/><path fill='%23fff' d='M22 50l50-22-7 48-18-8-7 12-3-17 31-26-37 24-9-4z'/></svg>",
    "tiktok": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%23000'/><path fill='%2325F4EE' d='M62 22c2 8 8 14 16 15v9c-6 0-12-2-16-5v22c0 12-9 20-20 20s-20-8-20-20 9-21 20-21v9c-6 0-11 5-11 12s5 12 11 12 12-6 12-12V22h8z'/><path fill='%23FE2C55' d='M70 22c2 8 8 14 16 15v9c-6 0-12-2-16-5v22c0 12-9 20-20 20v-9c6 0 12-6 12-12V22h8z'/></svg>",
    "google": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%23fff'/><path fill='%234285F4' d='M58 50c0-1-.1-2-.2-3H50v6h5.5c-.5 2-2 4-4.5 5l4 3c3-2 5-6 5-10 0-1 0-1-.5-1z'/><path fill='%2334A853' d='M40 56c1 4 4 7 9 7 3 0 5-1 7-3l-4-3c-1 1-2 1-4 1-3 0-5-2-6-4l-4 2z'/><path fill='%23FBBC04' d='M40 44l-4 2c-1 1-1 3-1 4s0 3 1 4l4-2c-.5-1-.5-2-.5-3s0-4 0-4z'/><path fill='%23EA4335' d='M50 36c3 0 5 1 6 2l-3 3c-1-1-2-1-4-1-5 0-9 4-9 4l-4-2c0-3 4-6 14-6z'/></svg>",
    "twitter": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%23000'/><path fill='%23fff' d='M70 35c-2 1-4 1-6 1 2-1 4-3 5-5-2 1-4 2-7 2-2-2-5-3-8-3-6 0-11 5-11 11 0 1 0 2 .3 3-9 0-17-5-22-12-1 2-1 4-1 6 0 4 2 7 5 9-2 0-4-1-5-2v.1c0 5 4 10 9 11-1 0-3 .5-4 .5-1 0-2 0-3-.1 2 4 6 7 11 7-4 3-9 5-15 5-1 0-2 0-3-.1 5 3 11 5 18 5 21 0 33-18 33-33v-1c2-2 4-3 6-6z'/></svg>",
}

PLATFORM_LOGOS_SMALL = PLATFORM_LOGOS

PLATFORM_GRADIENTS = {
    "whatsapp": "linear-gradient(135deg, #25D366, #128C7E, #075E54)",
    "facebook": "linear-gradient(135deg, #1877F2, #0a4cb8, #003580)",
    "snapchat": "linear-gradient(135deg, #FFFC00, #FFD700, #FFA500)",
    "instagram": "linear-gradient(135deg, #F58529, #DD2A7B, #8134AF, #515BD4)",
    "telegram": "linear-gradient(135deg, #0088cc, #005f8c, #003d5c)",
    "tiktok": "linear-gradient(135deg, #FE2C55, #000000, #25F4EE)",
    "google": "linear-gradient(135deg, #4285F4, #34A853, #FBBC04, #EA4335)",
    "twitter": "linear-gradient(135deg, #000000, #1a1a1a, #333333)"
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
    'tiktok': '#000000',
    'facebook': '#1877f2',
    'instagram': '#E4405F',
    'snapchat': '#FFFC00',
    'google': '#4285F4',
    'twitter': '#1DA1F2'
}

main_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>المطري OTP</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
        html, body { font-family:'Cairo',sans-serif; background:#07090d; color:#c9d1d9; overflow-x:hidden; min-height:100vh; }
        
        /* خلفية الأرقام المتساقطة (Digital Cyber Background) */
        #matrix-bg {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -999;
            opacity: 0.85;
            pointer-events: none;
            background: #07090d;
            display: block;
        }

        .app { 
            max-width:480px; margin:0 auto; 
            background:rgba(13, 17, 23, 0.45); 
            backdrop-filter:blur(2px); 
            min-height:100vh; display:flex; flex-direction:column; 
            position:relative; 
            z-index: 1;
        }

        /* ============= HEADER ============= */
        .top-bar { 
            background:rgba(13, 17, 23, 0.9); 
            padding:12px 16px; 
            display:flex; 
            align-items:center; 
            justify-content:space-between; 
            border-bottom:1px solid #21262d; 
            position:sticky; 
            top:0; 
            z-index:50;
        }
        .brand { display:flex; align-items:center; gap:10px; }
        .brand-icon { 
            width:36px; height:36px; border-radius:10px; 
            background:linear-gradient(135deg, #1f6feb, #388bfd); 
            display:flex; align-items:center; justify-content:center; font-size:18px;
            animation: rocketFly 4s ease-in-out infinite;
        }
        @keyframes rocketFly {
            0%, 100% { transform: translateY(0) rotate(0deg); }
            25% { transform: translateY(-3px) rotate(-5deg); }
            50% { transform: translateY(2px) rotate(5deg); }
            75% { transform: translateY(-4px) rotate(-2deg); }
        }
        .brand-text { font-size:16px; font-weight:700; color:#fff; }
        .top-actions { display:flex; gap:8px; align-items:center; }
        .menu-btn { 
            background:transparent; border:1px solid #30363d; color:#8b949e; 
            padding:6px 12px; border-radius:8px; cursor:pointer; font-size:16px;
            transition:all 0.2s;
        }
        .menu-btn:hover { color:#58a6ff; border-color:#58a6ff; }

        /* ============= شريط الأخبار ============= */
        .news-ticker {
            background: linear-gradient(135deg, #1c2128 0%, #21262d 50%, #1c2128 100%);
            border: 1px solid #30363d;
            padding: 5px 0;
            overflow: hidden;
            position: relative;
            direction: ltr;
            border-radius: 8px;
            margin: 0 16px 5px 16px;
            max-width: calc(100% - 32px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }
        .news-ticker::before, .news-ticker::after {
            content: ''; position: absolute; top: 0; bottom: 0; width: 40px; z-index: 2; pointer-events: none;
        }
        .news-ticker::before { left: 0; background: linear-gradient(90deg, #1c2128, transparent); border-radius: 8px 0 0 8px; }
        .news-ticker::after  { right: 0; background: linear-gradient(-90deg, #1c2128, transparent); border-radius: 0 8px 8px 0; }
        .ticker-content {
            display: flex; gap: 60px;
            padding: 0 30px;
            white-space: nowrap;
            animation: tickerScroll 35s linear infinite;
            font-weight: 600; font-size: 12px; color: #c9d1d9;
            align-items: center;
        }
        .ticker-content:hover { animation-play-state: paused; }
        @keyframes tickerScroll {
            0%   { transform: translateX(0); }
            100% { transform: translateX(-50%); }
        }
        .ticker-item { display: inline-flex; align-items: center; gap: 6px; }
        .ticker-emoji { font-size: 14px; display: inline-block; }
        .ticker-name {
            background: linear-gradient(90deg, #58a6ff, #a371f7, #f78166, #58a6ff);
            background-size: 300% 300%;
            -webkit-background-clip: text; background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: nameScroll 4s ease infinite;
            display: inline-block; font-weight: 800;
        }
        @keyframes nameScroll {
            0%,100% { background-position: 0% 50%; }
            50%     { background-position: 100% 50%; }
        }

        /* ============= القائمة المنسدلة ============= */
        .dropdown-menu { 
            position:fixed; 
            top:0;
            left:-280px; 
            width: 260px;
            height: 100vh;
            background: #0d1117;
            border-right:1px solid #30363d; 
            padding:20px 10px; 
            z-index:10000; 
            box-shadow:10px 0 30px rgba(0,0,0,0.8); 
            flex-direction:column; 
            gap:8px;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            visibility: hidden;
            overflow-y:auto;
        }
        .dropdown-menu.show { left:0; visibility: visible; }
        .menu-overlay {
            display:none;
            position:fixed;
            inset:0;
            background:rgba(0,0,0,0.7);
            backdrop-filter:blur(4px);
            z-index:9999;
        }
        .menu-overlay.show { display:block; }
        .dropdown-menu a { 
            display:flex; 
            align-items:center; 
            gap:12px; 
            color:#c9d1d9; 
            text-decoration:none; 
            padding:10px 14px; 
            border-radius:10px; 
            font-size:13px; 
            font-weight:600; 
            transition:all 0.3s ease;
            border:1px solid transparent;
        }
        .dropdown-menu a:hover { 
            background: rgba(88,166,255,0.1);
            color:#58a6ff; 
            border-color: rgba(88,166,255,0.2);
        }
        .dropdown-menu a .ico { 
            font-size:16px; 
            width:28px; 
            height:28px; 
            display:flex; 
            align-items:center; 
            justify-content:center;
            background:rgba(88,166,255,0.1);
            border-radius:6px;
            flex-shrink:0;
        }
        .dropdown-menu .menu-divider {
            height:1px;
            background:linear-gradient(90deg, transparent, #30363d, transparent);
            margin:6px 0;
        }
        .dropdown-menu .menu-header {
            font-size:10px;
            color:#8b949e;
            font-weight:700;
            padding:6px 14px 2px;
            text-transform:uppercase;
            letter-spacing:0.5px;
        }

        /* ============= MAIN CONTENT ============= */
        .main { padding:12px 16px; flex:1; }

        .hero { text-align:center; padding:10px 0 5px; margin-bottom:5px; }
        .hero h1 { font-size:20px; font-weight:800; color:#fff; }
        .hero p { font-size:12px; color:#8b949e; }

        .section-title { 
            font-size:13px; font-weight:700; color:#fff; 
            margin:10px 0 6px; 
            display:flex; align-items:center; gap:8px; 
        }
        .section-title .icon { color:#58a6ff; }

        /* ============= PLATFORMS GRID ============= */
        .platforms { 
            display:grid; 
            grid-template-columns:repeat(2, 1fr); 
            gap:6px; 
            margin-bottom:5px; 
        }
        .platform-btn {
            display:flex; align-items:center; gap:8px; padding:8px 10px;
            background:#1c2128; border:1px solid #30363d; border-radius:8px;
            color:#e6e6e6; cursor:pointer; transition:all 0.15s ease;
            font-size:12px; font-weight:600; font-family:'Cairo',sans-serif;
        }
        .platform-btn:hover { background:#21262d; border-color:#484f58; }
        .platform-btn:active { transform:scale(0.97); }
        .platform-btn.active { 
            background:var(--platform-color, #1f6feb); 
            border-color:var(--platform-color, #1f6feb); 
            color:#fff; 
            box-shadow:0 0 0 1px var(--platform-color, #1f6feb), 0 0 12px rgba(31,111,235,0.15); 
        }
        .platform-btn img { width:28px; height:28px; object-fit:contain; border-radius:6px; background:#fff; padding:2px; }

        /* ============= SELECT & BUTTONS ============= */
        .form-control {
            width:100%; padding:10px 14px; border-radius:8px;
            border:1px solid #30363d; background:#0d1117; color:#e6e6e6;
            outline:none; font-family:'Cairo',sans-serif; font-size:13px; font-weight:600;
            appearance:none; -webkit-appearance:none;
            background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'><path fill='%238b949e' d='M6 9L1 4h10z'/></svg>");
            background-repeat:no-repeat; background-position:left 14px center; padding-left:36px;
        }
        .form-control:focus { border-color:#1f6feb; }
        .form-control:disabled { opacity:0.5; cursor:not-allowed; }

        .btn-primary {
            width:100%; padding:10px; border:none; border-radius:8px;
            background:#238636; color:#fff; font-size:13px; font-weight:700;
            cursor:pointer; margin-top:6px; font-family:'Cairo',sans-serif;
            transition:all 0.15s ease;
        }
        .btn-primary:hover:not(:disabled) { background:#2ea043; }
        .btn-primary:disabled { opacity:0.5; cursor:not-allowed; }

        /* ============= NUMBER CARD ============= */
        .number-card {
            background: linear-gradient(135deg, #0d1117, #161b22);
            border:1px solid #238636; border-radius:12px;
            padding:16px; margin:12px 0; text-align:center;
            box-shadow:0 0 0 1px rgba(35, 134, 54, 0.15), 0 0 18px rgba(35, 134, 54, 0.08);
        }
        .number-card .number {
            font-family: 'Courier New', monospace;
            font-size: 26px;
            font-weight: 900;
            color: #3fb950;
            letter-spacing: 2px;
            text-shadow: 0 0 8px rgba(63, 185, 80, 0.4);
            padding: 4px 0;
            direction: ltr;
            unicode-bidi: bidi-override;
            display: inline-block;
        }
        .number-card .number .digit {
            display: inline-block;
            opacity: 0;
            transform: translateY(8px) scale(0.7);
            animation: digitDrop 0.3s ease forwards;
        }
        @keyframes digitDrop {
            to { opacity: 1; transform: translateY(0) scale(1); }
        }
        .copy-btn-mini {
            background: linear-gradient(135deg, #1f6feb, #388bfd);
            border: 1px solid #388bfd;
            color: #fff;
            padding: 4px 10px;
            border-radius:6px;
            cursor: pointer;
            font-size:11px;
            font-weight:700;
            transition:all 0.2s;
        }
        .copy-btn-mini:hover { background:linear-gradient(135deg, #388bfd, #58a6ff); }
        .copy-btn-mini.copied {
            background: linear-gradient(135deg, #238636, #2ea043);
            border-color: #2ea043;
        }
        .number-countdown-wrap {
            display:flex;
            align-items:center;
            justify-content:center;
            gap:4px;
            margin-top:6px;
            padding:4px 10px;
            background:rgba(99,102,241,0.15);
            border:1px solid rgba(139,92,246,0.4);
            border-radius:999px;
            font-size:11px;
            font-weight:700;
            color:#c4b5fd;
            width:fit-content;
            margin-left:auto;
            margin-right:auto;
            cursor:pointer;
        }
        .number-countdown-wrap .countdown-value {
            font-family:'Courier New',monospace;
            color:#fbbf24;
            font-weight:900;
            min-width:24px;
            text-align:center;
        }
        .number-countdown-wrap.warn {
            border-color:rgba(245,158,11,0.6);
            background:linear-gradient(135deg, rgba(245,158,11,0.15), rgba(239,68,68,0.15));
        }
        .number-countdown-wrap.warn .countdown-value { color:#fbbf24; }
        .number-countdown-wrap.expired {
            border-color:rgba(239,68,68,0.6);
            background:linear-gradient(135deg, rgba(239,68,68,0.2), rgba(220,38,38,0.2));
        }
        .number-countdown-wrap.expired .countdown-value { color:#ef4444; }

        /* ============= OTP LIST ============= */
        .otp-list { display:flex; flex-direction:column; gap:6px; margin-top:8px; }
        .otp-item {
            background:#1c2128; border:1px solid #30363d; border-radius:8px;
            padding:10px 12px; display:flex; justify-content:space-between; align-items:center;
        }
        .otp-item .otp-code {
            font-family: 'Courier New', monospace;
            font-size: 16px;
            font-weight: 900;
            color: #ff6b9d;
            background: linear-gradient(135deg, #ff6b9d 0%, #c084fc 50%, #38bdf8 100%);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 1px;
        }
        .otp-item .otp-info { font-size:10px; color:#8b949e; margin-top:2px; }
        .otp-item .copy-btn { 
            background:transparent; border:1px solid #30363d; 
            color:#58a6ff; padding:3px 8px; border-radius:4px; 
            cursor:pointer; font-size:10px; font-weight:600; 
        }
        .otp-item .copy-btn:hover { background:#1f6feb; color:#fff; }

        .empty-state { text-align:center; padding:20px; color:#8b949e; font-size:12px; }
        .empty-state .icon { font-size:30px; margin-bottom:4px; opacity:0.5; }

        .status { 
            background:#1c2128; border:1px solid #30363d; border-radius:8px; 
            padding:8px 12px; text-align:center; margin-top:8px; 
            color:#8b949e; font-size:12px; font-weight:600; 
        }

        .footer-section {
            margin-top:10px;
            padding:0;
            border-top:1px solid #21262d;
        }
        .footer-info {
            text-align:center;
            padding:12px 16px;
            color:#8b949e;
            font-size:11px;
            font-weight:600;
        }
        .footer-info strong { color:#58a6ff; }

        /* ============= RESPONSIVE ============= */
        @media (max-width:380px) {
            .hero h1 { font-size:17px; }
            .platform-btn { font-size:11px; padding:6px 8px; }
            .platform-btn img { width:22px; height:22px; }
            .number-card .number { font-size:22px; }
        }
    </style>
</head>
<body>
    <canvas id="matrix-bg"></canvas>
    
    <div class="app">
        <!-- HEADER -->
        <div class="top-bar">
            <div class="brand">
                <div class="brand-icon">🚀</div>
                <div class="brand-text">المطري OTP</div>
            </div>
            <div class="top-actions">
                <button class="menu-btn" onclick="toggleMenu()">☰</button>
                <div class="menu-overlay" id="menuOverlay" onclick="toggleMenu()"></div>
                <div class="dropdown-menu" id="contactMenu">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; padding:0 10px;">
                        <div style="font-weight:900; color:#fff; font-size:16px;">🚀 القائمة</div>
                        <button onclick="toggleMenu()" style="background:none; border:none; color:#8b949e; font-size:18px; cursor:pointer;">✕</button>
                    </div>
                    <div class="menu-header">📞 تواصل معنا</div>
                    <a href="{{ owner_link }}" target="_blank"><span class="ico">💬</span> واتساب المطور</a>
                    <a href="{{ wa_group }}" target="_blank"><span class="ico">👥</span> جروب واتساب</a>
                    <a href="https://t.me/jsjsgsjsvh" target="_blank"><span class="ico">✈️</span> قناة تليجرام</a>
                    <div class="menu-divider"></div>
                    <a href="/learn-more"><span class="ico">📰</span> اعرف المزيد</a>
                    <a href="/announcements"><span class="ico">📢</span> إعلانات الموقع</a>
                    <a href="#" onclick="openHelpModal(); return false;"><span class="ico">🆘</span> طلب مساعدة</a>
                </div>
            </div>
        </div>

        <!-- شريط الأخبار -->
        <div class="news-ticker">
            <div class="ticker-content">
                <span class="ticker-item"><span class="ticker-emoji">🚀</span> مرحباً بك في موقع المطري OTP</span>
                <span class="ticker-item"><span class="ticker-emoji">⚡</span> أسرع موقع للحصول على الأكواد</span>
                <span class="ticker-item"><span class="ticker-emoji">💎</span> صُنع بحب بواسطة <span class="ticker-name">المطري</span> 🔥</span>
                <span class="ticker-item"><span class="ticker-emoji">🌍</span> دعم 195+ دولة</span>
                <span class="ticker-item"><span class="ticker-emoji">📱</span> واتساب • تيليجرام • فيسبوك • تيك توك</span>
                <span class="ticker-item"><span class="ticker-emoji">🔔</span> إشعارات فورية</span>
                <span class="ticker-item"><span class="ticker-emoji">⭐</span> شكراً لزيارتك</span>
                <!-- مكرر -->
                <span class="ticker-item"><span class="ticker-emoji">🚀</span> مرحباً بك في موقع المطري OTP</span>
                <span class="ticker-item"><span class="ticker-emoji">⚡</span> أسرع موقع للحصول على الأكواد</span>
                <span class="ticker-item"><span class="ticker-emoji">💎</span> صُنع بحب بواسطة <span class="ticker-name">المطري</span> 🔥</span>
            </div>
        </div>

        <!-- MAIN -->
        <div class="main">
            <div class="hero">
                <h1>🚀 موقع المطري OTP</h1>
                <p>👑 أرقام واتساب سحب أكواد تطوير مطري 👑</p>
            </div>

            <div class="section-title"><span class="icon">🎯</span> اختر المنصة</div>
            <div class="platforms" id="platformSelector"></div>

            <div class="section-title"><span class="icon">🌍</span> اختر الدولة</div>
            <select id="country" class="form-control" disabled>
                <option value="">-- اختر المنصة أولاً --</option>
            </select>

            <button class="btn-primary" id="getNumberBtn" onclick="getNumber()" disabled>🚀 جلب رقم</button>

            <div id="numberContainer" style="display:none;">
                <div class="number-card">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <span style="font-size:11px; color:#8b949e; font-weight:600;">📞 الرقم</span>
                        <button class="copy-btn-mini" onclick="copyNumber()" id="copyNumBtn">📋 نسخ</button>
                    </div>
                    <div class="number" id="numberDisplay">+</div>
                    <div class="number-countdown-wrap" id="numberCountdown" style="display:none; cursor:pointer;" onclick="refreshNumber()">
                        <span>🔄</span>
                        <span>تبديل الرقم التالي</span>
                    </div>
                </div>
                <div id="autoMonitorStatus" class="auto-monitor" style="display:flex; align-items:center; gap:6px; padding:6px 10px; background:#0d1117; border:1px solid #21262d; border-radius:6px; margin-top:6px; font-size:11px; color:#8b949e;">
                    <span class="dot" style="width:6px; height:6px; border-radius:50%; background:#3fb950; animation:pulse-dot 1.5s infinite; display:inline-block;"></span>
                    جاري المراقبة التلقائية...
                </div>
            </div>

            <div class="section-title" style="margin-top:16px;"><span class="icon">📜</span> الأكواد المسحوبة</div>
            <div class="otp-list" id="otpHistory">
                <div class="empty-state">
                    <div class="icon">⏳</div>
                    <div>في انتظار الأكواد...</div>
                </div>
            </div>

            <div class="status" id="status">⚡ اختر المنصة والدولة للبدء</div>
        </div>

        <!-- FOOTER -->
        <div class="footer-section">
            <div class="footer-info">
                <span>💎</span> صُنع بحب <span>⚡</span> بواسطة <strong>المطري</strong>
                <br><span style="color:#484f58; font-size:10px;">جميع الحقوق محفوظة © 2025</span>
            </div>
        </div>
    </div>

    <!-- مودال طلب المساعدة -->
    <div class="modal-overlay" id="helpModal" onclick="if(event.target===this) closeHelpModal()">
        <div class="modal-box" style="background:linear-gradient(180deg, #1c2128, #161b22); border:1px solid #30363d; border-radius:14px; padding:20px; max-width:380px; width:100%;">
            <h2 style="color:#fff; font-size:17px; margin-bottom:6px; text-align:center;">🆘 طلب مساعدة</h2>
            <p style="color:#8b949e; font-size:12px; text-align:center; margin-bottom:12px;">اشرح مشكلتك وسنرد عليك</p>
            <textarea id="helpMessage" style="width:100%; min-height:80px; background:#0d1117; color:#e6e6e6; border:1px solid #30363d; border-radius:8px; padding:10px; font-family:'Cairo',sans-serif; font-size:13px; resize:vertical; outline:none;"></textarea>
            <div style="display:flex; gap:8px; margin-top:12px;">
                <button class="btn-cancel" onclick="closeHelpModal()" style="flex:1; padding:10px; border:none; border-radius:8px; background:#30363d; color:#e6e6e6; font-weight:700; cursor:pointer;">إلغاء</button>
                <button class="btn-send" id="sendHelpBtn" onclick="sendHelpRequest()" style="flex:1; padding:10px; border:none; border-radius:8px; background:linear-gradient(135deg, #238636, #2ea043); color:#fff; font-weight:700; cursor:pointer;">إرسال</button>
            </div>
            <div class="success-msg" id="helpSuccess" style="display:none; background:rgba(35,134,54,0.15); border:1px solid #238636; color:#3fb950; padding:10px; border-radius:8px; text-align:center; margin-top:8px; font-size:13px;">
                ✅ تم إرسال رسالتك!
            </div>
        </div>
    </div>

    <script>
        const platformLogos = {{ platform_logos | tojson }};
        const platformLogosSmall = {{ platform_logos_small | tojson }};
        const platformNames = {{ platform_names | tojson }};
        const platformGradients = {{ platform_gradients | tojson }};

        // ========== خلفية الأرقام المتساقطة ==========
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
                ctx.fillStyle = "rgba(7, 9, 13, 0.07)";
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.font = "bold " + fontSize + "px monospace";
                for (let i = 0; i < drops.length; i++) {
                    const text = digits.charAt(Math.floor(Math.random() * digits.length));
                    ctx.shadowBlur = 10;
                    ctx.shadowColor = "#00ffc8";
                    ctx.fillStyle = Math.random() > 0.92 ? "#ffffff" : "#00ffc8";
                    ctx.fillText(text, i * fontSize, drops[i] * fontSize);
                    ctx.shadowBlur = 0;
                    if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0;
                    drops[i] += 0.8;
                }
            }
            setInterval(draw, 50);
            window.addEventListener('resize', () => {
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
            });
        }
        initMatrix();

        // ========== القائمة ==========
        function toggleMenu() {
            document.getElementById('contactMenu').classList.toggle('show');
            document.getElementById('menuOverlay').classList.toggle('show');
            document.body.style.overflow = document.getElementById('contactMenu').classList.contains('show') ? 'hidden' : '';
        }

        // ========== مودال المساعدة ==========
        function openHelpModal() {
            document.getElementById('helpModal').style.display = 'flex';
            document.getElementById('helpMessage').value = '';
            document.getElementById('helpSuccess').style.display = 'none';
        }
        function closeHelpModal() {
            document.getElementById('helpModal').style.display = 'none';
        }
        async function sendHelpRequest() {
            const msg = document.getElementById('helpMessage').value.trim();
            if (!msg) { alert('الرجاء كتابة رسالتك'); return; }
            const btn = document.getElementById('sendHelpBtn');
            btn.disabled = true; btn.textContent = '⏳ جاري الإرسال...';
            try {
                const res = await fetch('/api/help', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: msg})
                });
                const data = await res.json();
                if (data.ok) {
                    document.getElementById('helpSuccess').style.display = 'block';
                    document.getElementById('helpMessage').value = '';
                    setTimeout(() => closeHelpModal(), 2000);
                } else {
                    alert('❌ فشل الإرسال: ' + (data.error || 'حاول مرة أخرى'));
                }
            } catch(e) {
                alert('❌ فشل الاتصال بالخادم');
            }
            btn.disabled = false; btn.textContent = 'إرسال';
        }

        // ========== نسخ ==========
        async function copyNumber() {
            const num = document.getElementById('numberDisplay').textContent;
            try { await navigator.clipboard.writeText(num); } catch(e) {}
            const btn = document.getElementById('copyNumBtn');
            btn.classList.add('copied');
            btn.innerHTML = '✅ تم النسخ';
            setTimeout(() => { btn.classList.remove('copied'); btn.innerHTML = '📋 نسخ'; }, 1800);
        }
        function copyText(text, btn) {
            navigator.clipboard.writeText(text);
            if (btn) {
                const orig = btn.textContent;
                btn.textContent = '✅';
                setTimeout(() => btn.textContent = orig, 1200);
            }
        }

        // ========== صوت التنبيه ==========
        function playNotificationSound() {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const now = ctx.currentTime;
                const o1 = ctx.createOscillator();
                const g1 = ctx.createGain();
                o1.connect(g1); g1.connect(ctx.destination);
                o1.type = 'sine';
                o1.frequency.setValueAtTime(880, now);
                g1.gain.setValueAtTime(0.0001, now);
                g1.gain.exponentialRampToValueAtTime(0.3, now + 0.02);
                g1.gain.exponentialRampToValueAtTime(0.0001, now + 0.25);
                o1.start(now); o1.stop(now + 0.3);
                const o2 = ctx.createOscillator();
                const g2 = ctx.createGain();
                o2.connect(g2); g2.connect(ctx.destination);
                o2.type = 'sine';
                o2.frequency.setValueAtTime(1318, now + 0.18);
                g2.gain.setValueAtTime(0.0001, now + 0.18);
                g2.gain.exponentialRampToValueAtTime(0.3, now + 0.2);
                g2.gain.exponentialRampToValueAtTime(0.0001, now + 0.5);
                o2.start(now + 0.18); o2.stop(now + 0.55);
            } catch(e) {}
        }

        // ========== تأثير ظهور الرقم ==========
        function animateNumber(element, text) {
            element.innerHTML = '';
            element.setAttribute('dir', 'ltr');
            element.style.direction = 'ltr';
            element.style.unicodeBidi = 'bidi-override';
            const chars = text.split('');
            chars.forEach((ch, i) => {
                const span = document.createElement('span');
                span.className = 'digit';
                span.textContent = ch;
                span.style.animationDelay = (i * 0.06) + 's';
                element.appendChild(span);
            });
        }

        // ========== متغيرات ==========
        let currentPlatform = '';
        let currentNumber = '';
        let currentNumberIndex = 0;
        let monitorInterval = null;
        let allOtpsCache = [];

        // ========== تهيئة المنصات ==========
        function initPlatformSelector() {
            const selector = document.getElementById('platformSelector');
            selector.innerHTML = '';
            const platformColors = {
                whatsapp: '#25D366',
                telegram: '#26A5E4',
                facebook: '#1877F2',
                instagram: '#E4405F',
                tiktok: '#FE2C55',
                snapchat: '#FFFC00',
                google: '#4285F4',
                twitter: '#1DA1F2'
            };
            Object.keys(platformNames).forEach(platform => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'platform-btn';
                btn.onclick = () => selectPlatform(platform, btn);
                btn.style.setProperty('--platform-color', platformColors[platform] || '#1f6feb');
                btn.innerHTML = `<img src="${platformLogos[platform]}" alt="${platformNames[platform]}" onerror="this.src='${platformLogosSmall[platform]}'"><span>${platformNames[platform]}</span>`;
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
            data.forEach(c => { options += `<option value="${c.code}">${c.flag} ${c.name}</option>`; });
            countrySelect.innerHTML = options;
            countrySelect.disabled = false;
        }

        document.getElementById('country').addEventListener('change', function() {
            document.getElementById('getNumberBtn').disabled = !this.value;
        });

        async function getNumber() {
            const country = document.getElementById('country').value;
            if (!currentPlatform || !country) {
                document.getElementById('status').textContent = '⚠️ يرجى اختيار المنصة والدولة';
                return;
            }
            currentNumberIndex = 0;
            document.getElementById('status').textContent = '⏳ جاري جلب رقم...';
            const res = await fetch('/api/get_number', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({platform:currentPlatform, country, index: currentNumberIndex})});
            const data = await res.json();
            if (data.number) {
                currentNumber = data.number;
                animateNumber(document.getElementById('numberDisplay'), data.number);
                document.getElementById('numberContainer').style.display = 'block';
                document.getElementById('status').textContent = '✅ الرقم جاهز!';
                document.getElementById('numberCountdown').style.display = 'flex';
                startMonitoring();
            } else {
                document.getElementById('status').textContent = '❌ لا توجد أرقام متاحة';
            }
        }

        async function refreshNumber() {
            const country = document.getElementById('country').value;
            if (!currentPlatform || !country) return;
            const refreshBtn = document.getElementById('numberCountdown');
            refreshBtn.innerHTML = '⏳ جاري التبديل...';
            refreshBtn.style.pointerEvents = 'none';
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
                        document.getElementById('status').textContent = 'ℹ️ العودة للأول...';
                    }
                }
                startMonitoring();
            } catch(e) {
                document.getElementById('status').textContent = '❌ فشل التبديل';
            }
            refreshBtn.innerHTML = '<span>🔄</span> <span>تبديل الرقم التالي</span>';
            refreshBtn.style.pointerEvents = 'auto';
            refreshBtn.style.display = 'flex';
        }

        function startMonitoring() {
            if (!currentNumber) return;
            if (monitorInterval) clearInterval(monitorInterval);
            const status = document.getElementById('autoMonitorStatus');
            if (status) status.innerHTML = '<span class="dot"></span> جاري المراقبة التلقائية...';
            let lastSeenOtpTime = 0;
            monitorInterval = setInterval(() => {
                if (!currentNumber) { stopMonitoring(); return; }
                fetch('/api/get_otp', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({number:currentNumber})})
                .then(res => res.json()).then(data => {
                    if (data.otp && data.otp !== lastSeenOtpTime) {
                        const now = new Date().toLocaleString('en-US', {timeZone:'Asia/Aden', hour12: true});
                        addOtpToHistory(currentNumber, data.otp, now, currentPlatform);
                        lastSeenOtpTime = data.otp;
                        if (status) status.innerHTML = `<span class="dot"></span> ✅ تم استلام كود!`;
                        playNotificationSound();
                    }
                }).catch(()=>{});
            }, 4000);
        }

        function stopMonitoring() {
            if (monitorInterval) { clearInterval(monitorInterval); monitorInterval = null; }
        }

        function addOtpToHistory(number, otp, timestamp, platform) {
            const container = document.getElementById('otpHistory');
            if (container.querySelector('.empty-state')) container.innerHTML = '';
            const otpId = Date.now() + '_' + Math.random().toString(36).slice(2,6);
            const otpData = {id: otpId, number, otp, timestamp, platform: platform || currentPlatform || 'unknown', otpTime: Date.now()};
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
            const grouped = {};
            allOtpsCache.forEach(o => {
                const p = o.platform || 'unknown';
                if (!grouped[p]) grouped[p] = [];
                grouped[p].push(o);
            });
            let html = '';
            Object.keys(grouped).forEach(platform => {
                const items = grouped[platform];
                const logoUrl = platformLogos[platform] || '';
                const name = platformNames[platform] || platform;
                html += `
                <div style="margin-bottom:10px;">
                    <div style="display:flex; align-items:center; gap:6px; padding:4px 8px; background:#1c2128; border:1px solid #30363d; border-radius:6px; margin-bottom:4px; cursor:pointer;" onclick="toggleSection(this)">
                        <img src="${logoUrl}" style="width:20px; height:20px; border-radius:4px; padding:2px; background:#fff;" onerror="this.style.display='none'">
                        <span style="font-size:12px; font-weight:700; color:#fff;">${name}</span>
                        <span style="font-size:10px; color:#8b949e; margin-right:auto;">${items.length} كود</span>
                        <span style="color:#8b949e; font-size:10px;">▼</span>
                    </div>
                    <div class="otp-section-items" style="display:flex; flex-direction:column; gap:4px;">
                        ${items.map(o => `
                        <div class="otp-item">
                            <div>
                                <div class="otp-code" dir="ltr" style="direction:ltr; unicode-bidi:bidi-override; text-align:left; font-size:14px;">
                                    🔑 ${o.otp}
                                </div>
                                <div class="otp-info">📞 ${o.number} • 🕒 ${o.timestamp}</div>
                            </div>
                            <button class="copy-btn" onclick="copyText('${o.otp}', this)">نسخ</button>
                        </div>
                        `).join('')}
                    </div>
                </div>`;
            });
            container.innerHTML = html;
        }

        function toggleSection(header) {
            const items = header.nextElementSibling;
            items.style.display = items.style.display === 'none' ? 'flex' : 'none';
            const arrow = header.querySelector('span:last-child');
            if (arrow) arrow.textContent = items.style.display === 'none' ? '▶' : '▼';
        }

        function loadCachedOtps() {
            try {
                const cached = localStorage.getItem('allOtps');
                if (cached) {
                    allOtpsCache = JSON.parse(cached);
                    const dayAgo = Date.now() - 24*60*60*1000;
                    allOtpsCache = allOtpsCache.filter(o => o.otpTime > dayAgo);
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

admin_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>⚙️ لوحة التحكم</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Cairo',sans-serif; background: linear-gradient(135deg, #0a0e1a, #1a1f2e); color:#fff; min-height:100vh; display:flex; justify-content:center; align-items:center; padding:20px; }
.container { background:rgba(17, 24, 39, 0.95); backdrop-filter:blur(20px); padding:30px; border-radius:25px; width:100%; max-width:500px; border:1px solid rgba(0, 255, 200, 0.3); box-shadow: 0 0 60px rgba(0, 255, 200, 0.15); margin:20px auto; }
h1 { text-align:center; background: linear-gradient(90deg, #00ffc8, #8b5cf6); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:25px; font-size:28px; font-weight:900; }
h3 { color:#cbd5e1; margin-bottom:12px; margin-top:18px; }
.form-group { margin-bottom:15px; }
.form-group label { display:block; margin-bottom:6px; color:#cbd5e1; font-weight:700; }
.form-control { width:100%; padding:12px; border-radius:12px; border:2px solid rgba(255,255,255,0.1); background:rgba(31, 41, 55, 0.7); color:#fff; font-family:'Cairo',sans-serif; transition:all 0.3s; }
.form-control:focus { border-color:#00ffc8; box-shadow: 0 0 20px rgba(0,255,200,0.3); }
.btn-primary { width:100%; padding:14px; border:none; border-radius:12px; background: linear-gradient(135deg, #00ff88, #00d2ff); color:#0a0e1a; cursor:pointer; margin-top:15px; font-weight:900; font-size:16px; font-family:'Cairo',sans-serif; box-shadow: 0 0 20px rgba(0,255,136,0.4); transition:all 0.3s; }
.btn-primary:hover { transform:translateY(-2px); box-shadow: 0 5px 30px rgba(0,255,136,0.6); }
.btn-danger { width:100%; padding:14px; border:none; border-radius:12px; background: linear-gradient(135deg, #ef4444, #b91c1c); color:#fff; cursor:pointer; margin-top:10px; font-weight:800; font-size:15px; font-family:'Cairo',sans-serif'; box-shadow: 0 0 20px rgba(239, 68, 68, 0.4); transition:all 0.3s; }
.btn-danger:hover { transform:translateY(-2px); }
.btn-secondary { width:100%; padding:14px; border:none; border-radius:12px; background: linear-gradient(135deg, #374151, #4b5563); color:#fff; cursor:pointer; margin-top:10px; font-weight:800; font-size:15px; font-family:'Cairo',sans-serif; transition:all 0.3s; }
.btn-secondary:hover { transform:translateY(-2px); }
hr { border: 1px solid rgba(255,255,255,0.1); margin: 20px 0; }
.combo-item { display:flex; justify-content:space-between; align-items:center; background:rgba(31, 41, 55, 0.7); padding:12px; border-radius:12px; margin-bottom:10px; border:1px solid rgba(139, 92, 246, 0.3); }
.combo-item span { color:#fff; font-weight:600; }
.combo-item button { padding:6px 14px; font-size:13px; margin-top:0 !important; }
</style>
</head>
<body>
<div class="container">
    <h1>⚙️ لوحة التحكم ⚙️</h1>

    <h3>📤 رفع ملف جديد</h3>
    <form method="POST" enctype="multipart/form-data">
        <div class="form-group"><label>📱 المنصة</label>
        <select name="platform" class="form-control" required>
            <option value="whatsapp">📱 واتساب</option>
            <option value="telegram">✈️ تيليجرام</option>
            <option value="tiktok">🎵 تيك توك</option>
            <option value="facebook">📘 فيسبوك</option>
            <option value="instagram">📸 انستقرام</option>
            <option value="snapchat">👻 سناب شات</option>
            <option value="google">🔍 جوجل</option>
            <option value="twitter">🐦 تويتر/X</option>
        </select></div>
        <div class="form-group"><label>📁 ارفع ملف الأرقام (.txt)</label>
        <input type="file" name="file" accept=".txt" class="form-control" required></div>
        <button type="submit" class="btn-primary">📤 رفع الكومبو</button>
    </form>

    <hr>

    <h3>🗂️ قائمة الكومبوهات</h3>
    <div style="max-height:250px; overflow-y:auto; background:rgba(0,0,0,0.2); padding:10px; border-radius:12px; margin-bottom:10px;">
    {% if combos %}
        {% for platform, code, name, flag in combos %}
        <div class="combo-item">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:20px;">{{ flag }}</span>
                <div><div style="font-weight:700; color:#fff;">{{ name }}</div><div style="font-size:10px; color:#8b949e;">{{ platform }}</div></div>
            </div>
            <form method="POST" style="display:inline;" onsubmit="return confirm('حذف هذا الكومبو؟')">
                <input type="hidden" name="action" value="delete">
                <input type="hidden" name="platform" value="{{ platform }}">
                <input type="hidden" name="country_code" value="{{ code }}">
                <button type="submit" class="btn-danger" style="padding:6px 12px; font-size:11px;">🗑️ حذف</button>
            </form>
        </div>
        {% endfor %}
    {% else %}
        <p style="color:#64748b; text-align:center; padding:20px;">🤷‍♂️ لا توجد كومبوهات</p>
    {% endif %}
    </div>

    <hr>

    <div style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(239, 68, 68, 0.15)); padding:14px; border-radius:12px; border:1px solid rgba(245, 158, 11, 0.4); margin-bottom:10px;">
        <h3 style="margin-top:0; color:#fbbf24;">📢 إدارة الإعلانات</h3>
        <a href="/admin/announcements_manager" style="text-decoration:none; display:block;">
            <button class="btn-danger" style="background: linear-gradient(135deg, #f59e0b, #d97706); box-shadow: 0 0 20px rgba(245, 158, 11, 0.4); margin-top:0;">🗑️ افتح صفحة حذف الإعلانات</button>
        </a>
    </div>

    <hr>

    <h3>🆘 طلبات المساعدة (<span id="helpCount">0</span>)</h3>
    <div id="helpList" style="max-height:200px; overflow-y:auto; margin-bottom:10px;">
        <p style="color:#64748b; text-align:center; padding:10px; font-size:13px;">⏳ جاري التحميل...</p>
    </div>

    <hr>

    <div style="background:rgba(0,0,0,0.2); padding:20px; border-radius:15px; border:1px solid rgba(0,255,200,0.2); margin-bottom:20px;">
        <h3 style="margin-top:0; color:#00ffc8;">📋 سجل الأكواد المسحوبة</h3>
        <div id="otpLogsList" style="max-height:400px; overflow-y:auto;">
            <p style="color:#64748b; text-align:center; padding:10px; font-size:13px;">⏳ جاري التحميل...</p>
        </div>
    </div>

    <hr>

    <h3>⚙️ إعدادات البوت</h3>
    <div class="form-group">
        <label>🆔 Chat ID الخاص بك</label>
        <div style="display:flex; gap:6px;">
            <input type="text" id="adminTelegramId" class="form-control" placeholder="مثال: 123456789">
            <button type="button" onclick="saveAdminId()" class="btn-primary" style="width:auto; padding:12px 18px; margin-top:0;">💾</button>
        </div>
    </div>

    <hr>
    <a href="/"><button class="btn-secondary">🔙 العودة للرئيسية</button></a>
</div>

<script>
async function loadHelpRequests() {
    try {
        const res = await fetch('/api/admin/help_requests');
        const data = await res.json();
        document.getElementById('helpCount').textContent = data.length;
        const box = document.getElementById('helpList');
        if (!data.length) { box.innerHTML = '<p style="color:#64748b; text-align:center; padding:10px; font-size:13px;">📭 لا توجد طلبات</p>'; return; }
        box.innerHTML = data.slice(0, 8).map(h => `
            <div style="background:rgba(31,41,55,0.5); padding:8px 10px; border-radius:8px; margin-bottom:6px; font-size:12px; border-right:3px solid #f59e0b;">
                <div style="display:flex; justify-content:space-between; color:#cbd5e1;">
                    <span>👤 <code>${h.user_id}</code></span>
                    <span style="color:#64748b;">${h.created_at}</span>
                </div>
                <div style="color:#e2e8f0; margin-top:4px;">${h.message || ''}</div>
            </div>
        `).join('');
    } catch(e) {}
}

async function loadOtpLogs() {
    try {
        const res = await fetch('/api/all_otps');
        const data = await res.json();
        const box = document.getElementById('otpLogsList');
        if (!data.length) { box.innerHTML = '<p style="color:#64748b; text-align:center; padding:10px; font-size:13px;">📭 لا توجد أكواد</p>'; return; }
        box.innerHTML = data.map(o => `
            <div style="background:rgba(31,41,55,0.8); padding:12px; border-radius:12px; margin-bottom:10px; border:1px solid rgba(255,255,255,0.1); display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="color:#00ffc8; font-weight:900; font-size:16px;">🔑 ${o.otp}</div>
                    <div style="color:#fff; margin-top:4px; font-weight:600;">📞 ${o.number} <span style="color:#8b949e; font-size:11px;">(${o.platform})</span></div>
                    <div style="color:#8b949e; font-size:10px; margin-top:4px;">🕒 ${o.timestamp}</div>
                </div>
                <button onclick="deleteOtp(${o.id})" style="background:linear-gradient(135deg, #ef4444, #b91c1c); border:none; color:#fff; padding:8px 15px; border-radius:8px; cursor:pointer; font-size:12px; font-weight:800;">🗑️ حذف</button>
            </div>
        `).join('');
    } catch(e) {}
}

async function deleteOtp(id) {
    if(!confirm('🗑️ حذف هذا الكود؟')) return;
    try {
        const res = await fetch('/api/admin/delete_otp', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({id: id})
        });
        const data = await res.json();
        if(data.ok) { loadOtpLogs(); alert('✅ تم الحذف'); }
        else { alert('❌ فشل الحذف'); }
    } catch(e) { alert('❌ خطأ'); }
}

async function loadAdminSettings() {
    try {
        const res = await fetch('/api/admin/settings');
        const data = await res.json();
        document.getElementById('adminTelegramId').value = data.admin_telegram_id || '';
    } catch(e) {}
}

async function saveAdminId() {
    const v = document.getElementById('adminTelegramId').value.trim();
    if (!v) { alert('⚠️ اكتب Chat ID'); return; }
    const res = await fetch('/api/admin/settings', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({admin_telegram_id: v})
    });
    const data = await res.json();
    if (data.ok) { alert('✅ تم الحفظ'); } else { alert('❌ فشل الحفظ'); }
}

loadHelpRequests();
loadOtpLogs();
loadAdminSettings();
setInterval(loadHelpRequests, 15000);
</script>
</body>
</html>
"""

from functools import wraps
from flask import session

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(f"/{ADMIN_SECRET_PATH}")
        return "❌ كلمة المرور خاطئة!"
    return '''
    <div dir="rtl" style="text-align:center; margin-top:100px; font-family:sans-serif; background:#0d1117; color:#fff; padding:50px; border-radius:20px;">
        <h2>🔐 دخول الأدمن</h2>
        <form method="POST">
            <input type="password" name="password" placeholder="كلمة المرور" style="padding:12px; border-radius:8px; border:1px solid #30363d; background:#161b22; color:#fff;">
            <button type="submit" style="padding:12px 25px; background:#238636; color:#fff; border:none; border-radius:8px; cursor:pointer; font-weight:bold;">دخول</button>
        </form>
    </div>
    '''

@app.route(f'/{ADMIN_SECRET_PATH}', methods=['GET', 'POST'])
@login_required
def admin():
    if request.method == 'POST':
        if request.form.get('action') == 'delete':
            platform = request.form.get('platform')
            country_code = request.form.get('country_code')
            if platform and country_code:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("DELETE FROM combos WHERE platform=? AND country_code=?", (platform, country_code))
                conn.commit()
                conn.close()
                return redirect(f"/{ADMIN_SECRET_PATH}")
        elif request.form.get('action') == 'clear_otps':
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM otp_logs")
            conn.commit()
            conn.close()
            global _otp_cache, _otp_cache_time
            _otp_cache = None
            _otp_cache_time = 0
            return redirect(f"/{ADMIN_SECRET_PATH}")
        else:
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
    combos = get_all_combos_list()
    return render_template_string(admin_html, combos=combos)

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
    return jsonify({'number': nums[index]})

@app.route('/api/get_otp', methods=['POST'])
def api_get_otp():
    num = request.json.get('number')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT otp FROM otp_logs WHERE number LIKE ? ORDER BY id DESC LIMIT 1", (f"%{num[-4:]}",))
    row = c.fetchone()
    conn.close()
    return jsonify({'otp': row[0] if row else None})

_otp_cache = {'data': None, 'time': 0}
CACHE_DURATION = 30

@app.route('/api/all_otps', methods=['GET'])
def api_all_otps():
    now = time.time()
    if _otp_cache['data'] is not None and (now - _otp_cache['time']) < CACHE_DURATION:
        return jsonify(_otp_cache['data'])
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, number, otp, timestamp, platform, country_code, country_flag FROM otp_logs ORDER BY id DESC LIMIT 100")
    rows = c.fetchall()
    conn.close()
    result = [{
        'id': r[0], 'number': r[1], 'otp': r[2], 'timestamp': r[3],
        'platform': r[4] or 'Unknown', 'country_code': r[5] or '', 'country_flag': r[6] or '🌍'
    } for r in rows]
    _otp_cache['data'] = result
    _otp_cache['time'] = now
    return jsonify(result)

@app.route('/api/admin/delete_otp', methods=['POST'])
@login_required
def api_admin_delete_otp():
    otp_id = request.json.get('id')
    if otp_id:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM otp_logs WHERE id=?", (otp_id,))
            conn.commit()
            conn.close()
            _otp_cache['data'] = None
            _otp_cache['time'] = 0
            return jsonify({'ok': True})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)})
    return jsonify({'ok': False})

@app.route('/api/admin/help_requests', methods=['GET'])
@login_required
def api_help_requests():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, user_id, message, source, status, created_at FROM help_requests ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    return jsonify([{
        'id': r[0], 'user_id': r[1], 'message': r[2],
        'source': r[3], 'status': r[4], 'created_at': r[5]
    } for r in rows])

@app.route('/api/admin/settings', methods=['GET', 'POST'])
@login_required
def api_admin_settings():
    if request.method == 'GET':
        return jsonify({
            'admin_telegram_id': get_admin_setting('admin_telegram_id', ''),
            'site_url': get_admin_setting('site_url', 'https://otp-bot-7-0b93.onrender.com')
        })
    data = request.json or {}
    if 'admin_telegram_id' in data:
        set_admin_setting('admin_telegram_id', str(data['admin_telegram_id']).strip())
    if 'site_url' in data:
        set_admin_setting('site_url', data['site_url'].strip())
    return jsonify({'ok': True})

@app.route('/api/announcements', methods=['GET'])
def api_get_announcements():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, type, content, media_url, button_text, button_url, created_at FROM announcements ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    return jsonify([{
        'id': r[0], 'type': r[1], 'content': r[2], 'media_url': r[3],
        'button_text': r[4], 'button_url': r[5], 'created_at': r[6]
    } for r in rows])

@app.route('/api/announcement/delete', methods=['POST'])
@login_required
def api_delete_announcement():
    data = request.json or {}
    ann_id = data.get('id')
    if not ann_id:
        return jsonify({'ok': False, 'error': 'id required'}), 400
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM announcements WHERE id=?", (ann_id,))
    conn.commit()
    deleted = c.rowcount > 0
    conn.close()
    return jsonify({'ok': deleted})

@app.route('/api/announcement/delete_all', methods=['POST'])
@login_required
def api_delete_all_announcements():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM announcements")
    conn.commit()
    count = c.rowcount
    conn.close()
    return jsonify({'ok': True, 'deleted': count})

@app.route('/api/help', methods=['POST'])
def api_help():
    d = request.json
    msg = (d.get('message') or '').strip()
    if not msg:
        return jsonify({'ok': False, 'error': 'الرسالة فارغة'}), 400
    user_id = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO help_requests (user_id, message, source, created_at) VALUES (?, ?, ?, ?)",
              (user_id, msg, 'website', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    help_id = c.lastrowid
    conn.commit()
    conn.close()
    saved_admin_id = get_admin_setting('admin_telegram_id')
    try:
        help_text = (
            f"🆘 <b>طلب مساعدة جديد #{help_id}</b>\n\n"
            f"👤 المستخدم: <code>{user_id}</code>\n"
            f"💬 الرسالة:\n{msg}\n\n"
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        url = f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/sendMessage"
        if saved_admin_id:
            requests.post(url, json={'chat_id': saved_admin_id, 'text': help_text, 'parse_mode': 'HTML'}, timeout=10)
        else:
            requests.post(url, json={'chat_id': f"@{OWNER_TELEGRAM_ID.lstrip('@')}", 'text': help_text, 'parse_mode': 'HTML'}, timeout=10)
    except Exception as e:
        print(f"❌ فشل إرسال طلب المساعدة: {e}")
    return jsonify({'ok': True, 'id': help_id})

announcements_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>إعلانات الموقع - المطري OTP</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Cairo',sans-serif; background:#07090d; color:#c9d1d9; min-height:100vh; }
.container { max-width:480px; margin:0 auto; padding:16px; }
.header { background: linear-gradient(135deg, #1f6feb, #388bfd); padding:24px 20px; border-radius:14px; margin-bottom:20px; box-shadow: 0 4px 20px rgba(31, 111, 235, 0.3); text-align:center; }
.header h1 { color:#fff; font-size:22px; font-weight:900; margin-bottom:4px; }
.header p { color:rgba(255,255,255,0.85); font-size:13px; }
.ann-card { background:#1c2128; border:1px solid #30363d; border-radius:12px; padding:16px; margin-bottom:12px; }
.ann-card:hover { border-color:#58a6ff; }
.ann-type { display:inline-block; padding:3px 10px; border-radius:6px; font-size:11px; font-weight:700; margin-bottom:8px; }
.ann-type.text { background:#1f6feb; color:#fff; }
.ann-type.image { background:#238636; color:#fff; }
.ann-type.video { background:#d29922; color:#fff; }
.ann-content { color:#e6e6e6; font-size:14px; line-height:1.6; margin-bottom:10px; }
.ann-media { max-width:100%; max-height:180px; width:auto; border-radius:8px; margin-bottom:10px; object-fit:contain; display:block; margin-left:auto; margin-right:auto; }
.ann-video-wrap { position:relative; max-height:180px; border-radius:8px; overflow:hidden; margin-bottom:10px; background:#000; }
.ann-video-wrap video { width:100%; max-height:180px; display:block; }
.ann-btn { display:inline-block; padding:10px 20px; background:linear-gradient(135deg, #238636, #2ea043); color:#fff; text-decoration:none; border-radius:8px; font-weight:700; font-size:14px; }
.ann-btn:hover { transform:translateY(-1px); box-shadow:0 4px 12px rgba(35,134,54,0.4); }
.ann-time { color:#6e7681; font-size:11px; margin-top:8px; }
.empty { text-align:center; padding:40px 16px; color:#6e7681; }
.back-btn { display:inline-block; padding:10px 20px; background:#30363d; color:#fff; text-decoration:none; border-radius:8px; font-weight:700; font-size:14px; margin-bottom:16px; }
.back-btn:hover { background:#484f58; }
</style>
</head>
<body>
<div class="container">
    <a href="/" class="back-btn">🔙 العودة للرئيسية</a>
    <div class="header"><h1>📢 إعلانات الموقع</h1><p>تابع آخر الإعلانات والتحديثات</p></div>
    <div id="annList"><div class="empty">⏳ جاري التحميل...</div></div>
</div>
<script>
async function loadAnnouncements() {
    try {
        const res = await fetch('/api/announcements');
        const data = await res.json();
        const container = document.getElementById('annList');
        if (!data.length) { container.innerHTML = '<div class="empty">📭 لا توجد إعلانات</div>'; return; }
        container.innerHTML = data.map(a => {
            let media = '';
            if (a.type === 'image' && a.media_url) {
                media = `<img src="${a.media_url}" class="ann-media" alt="" loading="lazy" onclick="window.open('${a.media_url}','_blank')">`;
            } else if (a.type === 'video' && a.media_url) {
                media = `<div class="ann-video-wrap"><video src="${a.media_url}" controls preload="metadata"></video></div>`;
            }
            const btn = a.button_url ? `<a href="${a.button_url}" target="_blank" class="ann-btn">${a.button_text || 'افتح الرابط'}</a>` : '';
            return `<div class="ann-card"><span class="ann-type ${a.type}">${a.type === 'text' ? '📝' : a.type === 'image' ? '🖼️' : '🎥'} ${a.type}</span>${media}<div class="ann-content">${a.content || ''}</div>${btn}<div class="ann-time">🕒 ${a.created_at}</div></div>`;
        }).join('');
    } catch(e) { document.getElementById('annList').innerHTML = '<div class="empty">❌ فشل تحميل الإعلانات</div>'; }
}
loadAnnouncements();
</script>
</body>
</html>
"""

@app.route('/announcements')
def announcements_page():
    return render_template_string(announcements_html)

announcements_manager_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>إدارة الإعلانات - المطري OTP</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Cairo',sans-serif; background: linear-gradient(135deg, #0a0e1a, #1a1f2e); color:#fff; min-height:100vh; display:flex; justify-content:center; align-items:flex-start; padding:20px; }
.container { background:rgba(17, 24, 39, 0.85); backdrop-filter:blur(20px); padding:24px; border-radius:20px; width:100%; max-width:480px; border:1px solid rgba(245, 158, 11, 0.3); box-shadow: 0 0 50px rgba(245, 158, 11, 0.2); margin-top:20px; }
h1 { text-align:center; background: linear-gradient(90deg, #f59e0b, #ef4444); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:18px; font-size:24px; font-weight:900; }
.toolbar { display:flex; gap:8px; margin-bottom:16px; }
.btn { flex:1; padding:10px; border:none; border-radius:10px; font-family:'Cairo',sans-serif; font-weight:800; font-size:14px; cursor:pointer; transition:all 0.2s; }
.btn-refresh { background: linear-gradient(135deg, #00ffc8, #00d2ff); color:#0a0e1a; }
.btn-delete-all { background: linear-gradient(135deg, #ef4444, #b91c1c); color:#fff; }
.btn-back { background: linear-gradient(135deg, #374151, #4b5563); color:#fff; text-decoration:none; display:flex; align-items:center; justify-content:center; }
.btn:hover { transform:translateY(-2px); }
.ann-item { background:rgba(31, 41, 55, 0.7); padding:12px; border-radius:12px; margin-bottom:10px; border:1px solid rgba(245, 158, 11, 0.2); display:flex; gap:10px; align-items:center; }
.ann-thumb { width:60px; height:60px; border-radius:8px; object-fit:cover; background:#000; flex-shrink:0; }
.ann-thumb-text { width:60px; height:60px; border-radius:8px; background: linear-gradient(135deg, #1f6feb, #388bfd); display:flex; align-items:center; justify-content:center; font-size:24px; flex-shrink:0; }
.ann-info { flex:1; min-width:0; }
.ann-type-badge { display:inline-block; padding:2px 8px; border-radius:4px; font-size:10px; font-weight:700; margin-bottom:4px; }
.badge-text { background:#1f6feb; }
.badge-image { background:#238636; }
.badge-video { background:#d29922; }
.ann-content { font-size:12px; color:#cbd5e1; overflow:hidden; text-overflow:ellipsis; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; }
.ann-time { font-size:10px; color:#64748b; margin-top:4px; }
.btn-delete { background: linear-gradient(135deg, #ef4444, #b91c1c); color:#fff; border:none; padding:8px 12px; border-radius:8px; cursor:pointer; font-family:'Cairo',sans-serif; font-weight:800; font-size:12px; }
.empty { text-align:center; padding:40px 16px; color:#64748b; }
</style>
</head>
<body>
<div class="container">
    <h1>🗑️ إدارة الإعلانات</h1>
    <div class="toolbar">
        <button class="btn btn-refresh" onclick="loadList()">🔄 تحديث</button>
        <button class="btn btn-delete-all" onclick="deleteAll()">🗑️ حذف الكل</button>
    </div>
    <a href="/admin" class="btn btn-back" style="margin-bottom:16px; text-align:center;">🔙 لوحة التحكم</a>
    <div id="list"><div class="empty">⏳ جاري التحميل...</div></div>
</div>
<script>
async function loadList() {
    const box = document.getElementById('list');
    box.innerHTML = '<div class="empty">⏳ جاري التحميل...</div>';
    try {
        const res = await fetch('/api/announcements');
        const data = await res.json();
        if (!data.length) { box.innerHTML = '<div class="empty">📭 لا توجد إعلانات</div>'; return; }
        box.innerHTML = data.map(a => {
            let thumb = '';
            if (a.type === 'image' && a.media_url) { thumb = `<img src="${a.media_url}" class="ann-thumb">`; }
            else if (a.type === 'video' && a.media_url) { thumb = `<div class="ann-thumb-text">🎥</div>`; }
            else { thumb = `<div class="ann-thumb-text">📝</div>`; }
            return `<div class="ann-item">${thumb}<div class="ann-info"><span class="ann-type-badge badge-${a.type}">${a.type}</span><div class="ann-content">${a.content || '(بدون نص)'}</div><div class="ann-time">🕒 ${a.created_at}</div></div><button class="btn-delete" onclick="delOne(${a.id})">🗑️</button></div>`;
        }).join('');
    } catch(e) { box.innerHTML = '<div class="empty">❌ فشل التحميل</div>'; }
}
async function delOne(id) {
    if (!confirm('🗑️ حذف هذا الإعلان؟')) return;
    const res = await fetch('/api/announcement/delete', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: id})
    });
    const data = await res.json();
    if (data.ok) loadList(); else alert('❌ فشل الحذف');
}
async function deleteAll() {
    if (!confirm('⚠️ حذف جميع الإعلانات؟')) return;
    const res = await fetch('/api/announcement/delete_all', {method: 'POST'});
    const data = await res.json();
    alert('✅ تم حذف ' + (data.deleted || 0) + ' إعلان');
    loadList();
}
loadList();
</script>
</body>
</html>
"""

@app.route('/admin/announcements_manager')
def admin_announcements_manager():
    return render_template_string(announcements_manager_html)

learn_more_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>اعرف المزيد - المطري OTP</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Cairo',sans-serif; background:#07090d; color:#c9d1d9; min-height:100vh; }
.container { max-width:480px; margin:0 auto; padding:16px; }
.back-btn { display:inline-block; padding:10px 20px; background:#30363d; color:#fff; text-decoration:none; border-radius:8px; font-weight:700; font-size:14px; margin-bottom:16px; }
.back-btn:hover { background:#484f58; }
.hero-card { background:linear-gradient(135deg, #1f6feb 0%, #6e40c9 100%); padding:30px 24px; border-radius:16px; margin-bottom:20px; text-align:center; box-shadow:0 8px 30px rgba(31,111,235,0.4); }
.hero-card h1 { color:#fff; font-size:26px; font-weight:900; margin-bottom:8px; }
.hero-card p { color:rgba(255,255,255,0.9); font-size:14px; line-height:1.6; }
.section { background:#0d1117; border:1px solid #21262d; border-radius:14px; padding:20px; margin-bottom:16px; }
.section h2 { color:#fff; font-size:17px; font-weight:800; margin-bottom:14px; display:flex; align-items:center; gap:8px; }
.feature { display:flex; gap:12px; padding:12px 0; border-bottom:1px solid #21262d; }
.feature:last-child { border-bottom:none; }
.feature-icon { width:40px; height:40px; border-radius:10px; background:linear-gradient(135deg, #1f6feb, #388bfd); display:flex; align-items:center; justify-content:center; font-size:20px; flex-shrink:0; }
.feature-text h3 { color:#fff; font-size:14px; font-weight:700; margin-bottom:2px; }
.feature-text p { color:#8b949e; font-size:12px; line-height:1.5; }
.stats { display:grid; grid-template-columns:repeat(3, 1fr); gap:10px; margin-top:8px; }
.stat { text-align:center; padding:14px 8px; background:#161b22; border-radius:10px; }
.stat-num { font-size:22px; font-weight:900; color:#58a6ff; }
.stat-label { font-size:11px; color:#8b949e; margin-top:2px; }
.cta-box { background:linear-gradient(135deg, #238636, #2ea043); padding:20px; border-radius:14px; text-align:center; margin-bottom:16px; }
.cta-box a { display:inline-block; padding:12px 28px; background:#fff; color:#238636; text-decoration:none; border-radius:10px; font-weight:800; font-size:15px; margin-top:8px; }
</style>
</head>
<body>
<div class="container">
    <a href="/" class="back-btn">🔙 العودة للرئيسية</a>
    <div class="hero-card"><h1>🚀 المطري OTP</h1><p>أسرع وأقوى منصة لاستقبال أكواد التحقق من جميع المنصات العالمية</p></div>
    <div class="section">
        <h2>⭐ مميزات الموقع</h2>
        <div class="feature"><div class="feature-icon">🌍</div><div class="feature-text"><h3>195+ دولة حول العالم</h3><p>نغطي جميع دول العالم بأرقام موثوقة وسريعة</p></div></div>
        <div class="feature"><div class="feature-icon">⚡</div><div class="feature-text"><h3>استلام فوري للأكواد</h3><p>الأكواد توصلك خلال ثوانٍ من وصولها</p></div></div>
        <div class="feature"><div class="feature-icon">🔒</div><div class="feature-text"><h3>خصوصية وأمان عالي</h3><p>حماية كاملة لبياناتك بدون تسجيل</p></div></div>
        <div class="feature"><div class="feature-icon">📱</div><div class="feature-text"><h3>دعم 8 منصات رئيسية</h3><p>واتساب، تيليجرام، فيسبوك، تيك توك، انستقرام، سناب، جوجل، تويتر</p></div></div>
    </div>
    <div class="section"><h2>📊 إحصائيات</h2><div class="stats"><div class="stat"><div class="stat-num">195+</div><div class="stat-label">دولة</div></div><div class="stat"><div class="stat-num">8</div><div class="stat-label">منصات</div></div><div class="stat"><div class="stat-num">24/7</div><div class="stat-label">دعم</div></div></div></div>
    <div class="cta-box"><h2 style="color:#fff; font-size:18px;">🎯 جاهز للبدء؟</h2><p style="color:rgba(255,255,255,0.9); font-size:13px; margin-top:6px;">اختر منصتك واحصل على رقمك الآن</p><a href="/">🚀 ابدأ الآن</a></div>
</div>
</body>
</html>
"""

@app.route('/learn-more')
def learn_more_page():
    return render_template_string(learn_more_html)

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
                            country_code = None
                            hidden_match = re.search(r'(\d{3,4})[•*]{2,6}(\d{3,4})', clean)
                            if hidden_match:
                                user_number = hidden_match.group(1) + hidden_match.group(2)
                                last_digits = user_number[-4:]
                                country_code = user_number[:3] if len(user_number) > 3 else None
                            if not user_number:
                                all_numbers = re.findall(r'\b\d{8,15}\b', clean)
                                if all_numbers:
                                    user_number = max(all_numbers, key=len)
                                    last_digits = user_number[-4:]
                                    country_code = user_number[:3] if len(user_number) > 3 else None
                            if not user_number:
                                star_match = re.search(r'(\d{3})\*{2,6}(\d{3,4})', clean)
                                if star_match:
                                    user_number = star_match.group(1) + star_match.group(2)
                                    last_digits = user_number[-4:]
                                    country_code = user_number[:3]
                            if not user_number:
                                pipe_match = re.search(r'[A-Z]{2,4}\s*[|]\s*(\d{3,4})[•*]{2,6}(\d{3,4})', clean)
                                if pipe_match:
                                    user_number = pipe_match.group(1) + pipe_match.group(2)
                                    last_digits = user_number[-4:]
                                    country_code = user_number[:3]
                            if not user_number:
                                hash_num = re.search(r'#\s*(\d{8,12})', clean)
                                if hash_num:
                                    user_number = hash_num.group(1)
                                    last_digits = user_number[-4:]
                                    country_code = user_number[:3]
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
                                        if country_code and c.startswith(country_code):
                                            continue
                                        if len(c) >= 4:
                                            otp = c
                                            break
                            if not otp:
                                patterns = [
                                    r'(?:كود|رمز|code|otp|verification)[:\s\-]*[‎]?(\d{3,8})',
                                    r'#(\d{3,8})',
                                    r'(\d{3,4})[-\s](\d{3,4})',
                                    r'(\d{6,8})\s*(?:هو|هذا|كود|رمز)',
                                ]
                                for pattern in patterns:
                                    match = re.search(pattern, clean, re.IGNORECASE)
                                    if match:
                                        if len(match.groups()) > 1:
                                            otp = ''.join(match.groups())
                                        else:
                                            otp = match.group(1)
                                        break
                            if not otp:
                                for line in lines[1:]:
                                    nums = re.findall(r'\b\d{6,8}\b', line)
                                    if nums:
                                        for n in nums:
                                            if last_digits and n.endswith(last_digits):
                                                continue
                                            otp = n
                                            break
                                if not otp:
                                    all_long = re.findall(r'\b\d{6,8}\b', clean)
                                    if all_long:
                                        for n in all_long:
                                            if last_digits and n.endswith(last_digits):
                                                continue
                                            otp = n
                                            break
                            platform = "غير معروف"
                            text_lower = clean.lower()
                            platforms = {
                                "واتساب": ["wa", "whatsapp", "واتساب"],
                                "فيسبوك": ["fb", "facebook", "فيسبوك"],
                                "تيليجرام": ["tg", "telegram", "تيليجرام", "تلجرام"],
                                "تيك توك": ["tt", "tiktok", "تيك توك"],
                                "انستقرام": ["ig", "instagram", "انستقرام"],
                                "سناب شات": ["sc", "snapchat", "سناب"],
                                "جوجل": ["gg", "google", "جوجل"],
                                "تويتر": ["tw", "twitter", "تويتر", "x.com"]
                            }
                            for name, keywords in platforms.items():
                                for kw in keywords:
                                    if kw in text_lower:
                                        platform = name
                                        break
                                if platform != "غير معروف":
                                    break
                            if platform == "غير معروف" and lines:
                                first_line = lines[0]
                                platform_match = re.search(r'([A-Z]{2,4})\s*[|]', first_line)
                                if platform_match:
                                    short = platform_match.group(1).upper()
                                    short_map = {
                                        "WA": "واتساب", "FB": "فيسبوك", "TG": "تيليجرام",
                                        "TT": "تيك توك", "IG": "انستقرام", "SC": "سناب شات",
                                        "GG": "جوجل", "TW": "تويتر", "OT": "اخرى"
                                    }
                                    platform = short_map.get(short, short)
                            if otp:
                                conn = sqlite3.connect(DB_PATH)
                                if last_digits:
                                    conn.cursor().execute(
                                        "INSERT INTO otp_logs (number, otp, timestamp, platform) VALUES (?, ?, ?, ?)",
                                        (last_digits, otp, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), platform)
                                    )
                                    print(f"✅ [{platform}] {otp} | الرقم: {last_digits}")
                                else:
                                    conn.cursor().execute(
                                        "INSERT INTO otp_logs (number, otp, timestamp, platform) VALUES (?, ?, ?, ?)",
                                        ("0000", otp, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), platform)
                                    )
                                    print(f"✅ [{platform}] {otp} | بدون رقم")
                                conn.commit()
                                conn.close()
        except Exception as e:
            print(f"❌ خطأ: {e}")
        time.sleep(5)

threading.Thread(target=monitor_channel, daemon=True).start()

def monitor_telegram_group():
    last_update_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/getUpdates"
            params = {"timeout": 15, "offset": last_update_id + 1, "allowed_updates": ["message", "channel_post"]}
            r = requests.get(url, params=params, timeout=20)
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
                chat = msg.get('chat', {})
                chat_id = chat.get('id')
                chat_type = chat.get('type', '')
                text = msg.get('text', '') or msg.get('caption', '')
                chat_username = chat.get('username', '')
                if chat_id:
                    try:
                        conn_k = sqlite3.connect(DB_PATH)
                        conn_k.execute(
                            "INSERT OR REPLACE INTO known_chats (chat_id, chat_type, chat_title, last_seen) VALUES (?, ?, ?, ?)",
                            (str(chat_id), chat_type, chat.get('title') or chat.get('username') or chat.get('first_name') or 'unknown', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        )
                        conn_k.commit()
                        conn_k.close()
                        print(f"📌 [chat_id] {chat_id} | {chat_type} | {chat.get('title') or chat_username}")
                    except Exception as e:
                        print(f"⚠️ فشل حفظ chat_id: {e}")
                if text and text.strip() == '/chatid':
                    try:
                        requests.post(f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/sendMessage", json={
                            'chat_id': chat_id,
                            'text': f"📋 <b>معلومات الدردشة</b>\n\n🆔 Chat ID: <code>{chat_id}</code>\n📌 النوع: <b>{chat_type}</b>\n📝 الاسم: {chat.get('title') or chat.get('username') or chat.get('first_name') or '—'}",
                            'parse_mode': 'HTML'
                        }, timeout=10)
                    except: pass
                    continue
                if text and text.strip() == '/start' and chat_type == 'private':
                    try:
                        requests.post(f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/sendMessage", json={
                            'chat_id': chat_id,
                            'text': '🤖 <b>مرحباً بك في بوت المطري OTP</b>\n\n✅ هذا البوت مربوط بموقع المطري OTP.\n🆘 لطلب المساعدة من الموقع: ادخل الموقع واضغط "طلب مساعدة" في القائمة',
                            'parse_mode': 'HTML'
                        }, timeout=10)
                    except: pass
                    continue
                if chat_type in ('group', 'supergroup', 'channel'):
                    if not text and not msg.get('photo') and not msg.get('video'):
                        continue
                    ann_type = 'text'
                    media_url = None
                    content = text or ''
                    button_text = None
                    button_url = None
                    if msg.get('photo'):
                        ann_type = 'image'
                        photo = msg['photo'][-1]
                        file_id = photo['file_id']
                        try:
                            file_info = requests.get(f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
                            if file_info.get('ok'):
                                media_url = f"https://api.telegram.org/file/bot{ASSISTANT_BOT_TOKEN}/{file_info['result']['file_path']}"
                        except: pass
                    elif msg.get('video'):
                        ann_type = 'video'
                        try:
                            file_id = msg['video']['file_id']
                            file_info = requests.get(f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
                            if file_info.get('ok'):
                                media_url = f"https://api.telegram.org/file/bot{ASSISTANT_BOT_TOKEN}/{file_info['result']['file_path']}"
                        except: pass
                    if text:
                        btn_match = re.search(r'\[(.+?)\|(https?://[^\s\]]+)\]', text)
                        if btn_match:
                            button_text = btn_match.group(1)
                            button_url = btn_match.group(2)
                            content = text.replace(btn_match.group(0), '').strip()
                    if content or media_url:
                        conn = sqlite3.connect(DB_PATH)
                        conn.cursor().execute(
                            "INSERT INTO announcements (type, content, media_url, button_text, button_url, source_msg_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (ann_type, content, media_url, button_text, button_url, msg.get('message_id'), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        )
                        conn.commit()
                        conn.close()
                        print(f"✅ [إعلان جديد] {ann_type} | {content[:30]}...")
                        try:
                            requests.post(f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/sendMessage", json={
                                'chat_id': chat_id,
                                'text': f'✅ تم نشر الإعلان في الموقع!',
                                'reply_to_message_id': msg.get('message_id')
                            }, timeout=10)
                        except: pass
                        if TELEGRAM_GROUP_CHAT_ID == 'AUTO_DETECT':
                            TELEGRAM_GROUP_CHAT_ID = str(chat_id)
                            print(f"🎯 [تحديث] تم حفظ chat_id الجروب: {chat_id}")
                elif chat_type == 'private':
                    if not text:
                        continue
                    if text == '/start':
                        requests.post(f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/sendMessage", json={'chat_id': chat_id, 'text': '🤖 <b>مرحباً بك في بوت المطري OTP</b>\n\nهذا البوت مربوط بموقع المطري OTP. الإعلانات التي تنشرها في الجروب الرسمي ستظهر تلقائياً في الموقع.\n\n✅ أرسل إعلانك في الجروب وسيظهر فوراً!'}, timeout=10)
                    elif text == '/announcements':
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute("SELECT COUNT(*) FROM announcements")
                        count = c.fetchone()[0]
                        conn.close()
                        requests.post(f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/sendMessage", json={'chat_id': chat_id, 'text': f'📊 عدد الإعلانات المنشورة في الموقع: <b>{count}</b>'}, timeout=10)
                    elif text and text.strip() in ('مساعد', 'مساعدة', 'help', '/help', 'المساعد'):
                        conn = sqlite3.connect(DB_PATH)
                        conn.cursor().execute(
                            "INSERT INTO help_requests (user_id, message, source, status, created_at) VALUES (?, ?, ?, ?, ?)",
                            (str(chat_id), 'طلب تفعيل محادثة مع الأدمن', 'telegram', 'pending', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        )
                        conn.commit()
                        conn.close()
                        user_info = chat.get('first_name') or chat.get('username') or 'مستخدم'
                        notify_admin(
                            f"🆘 <b>طلب مساعدة جديد!</b>\n\n👤 الاسم: {user_info}\n🆔 Chat ID: <code>{chat_id}</code>\n🕒 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        requests.post(f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/sendMessage", json={'chat_id': chat_id, 'text': '🆘 <b>تم استلام طلب المساعدة!</b>\n\n✅ تم إشعار الأدمن بطلبك. اكتب رسالتك الآن وسيتم توصيلها للإدمن.\n\n⏰ الرد خلال دقائق.'}, timeout=10)
                    else:
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute("SELECT COUNT(*) FROM help_requests WHERE user_id=? AND status='pending'", (str(chat_id),))
                        has_pending = c.fetchone()[0] > 0
                        conn.close()
                        if has_pending:
                            user_info = chat.get('first_name') or chat.get('username') or 'مستخدم'
                            notify_admin(
                                f"💬 <b>رسالة جديدة من زبون</b>\n\n👤 {user_info} (<code>{chat_id}</code>):\n\n📝 {text}"
                            )
                            requests.post(f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/sendMessage", json={'chat_id': chat_id, 'text': '✅ <b>تم إرسال رسالتك للإدمن.</b>\n\nسيتم الرد عليك قريباً.'}, timeout=10)
        except Exception as e:
            print(f"❌ خطأ في بوت تيليجرام: {e}")
        time.sleep(3)

threading.Thread(target=monitor_telegram_group, daemon=True).start()

@app.route('/api/admin/chats', methods=['GET'])
@login_required
def api_admin_chats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT chat_id, chat_type, chat_title, last_seen FROM known_chats ORDER BY last_seen DESC LIMIT 30")
    rows = c.fetchall()
    conn.close()
    return jsonify([{'chat_id': r[0], 'type': r[1], 'title': r[2], 'last_seen': r[3]} for r in rows])

@app.route('/api/chats', methods=['GET'])
def api_get_chats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT chat_id, chat_type, chat_title, last_seen FROM known_chats ORDER BY last_seen DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    return jsonify([{'chat_id': r[0], 'chat_type': r[1], 'chat_title': r[2], 'last_seen': r[3]} for r in rows])

@app.route('/')
def home():
    return render_template_string(
        main_html,
        owner_link=OWNER_LINK,
        wa_group=WHATSAPP_GROUP_LINK,
        platform_logos=PLATFORM_LOGOS,
        platform_logos_small=PLATFORM_LOGOS,
        platform_names=platform_names,
        platform_gradients=PLATFORM_GRADIENTS
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)