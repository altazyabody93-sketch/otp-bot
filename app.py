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
DB_PATH = "bot.db"

WHATSAPP_GROUP_LINK = "https://chat.whatsapp.com/IeK2gNS64fd8YSnenzt4WR"
OWNER_PHONE = "967733723953"
OWNER_LINK = f"https://wa.me/{OWNER_PHONE}"

TELEGRAM_BOT_TOKEN = "8814038881:AAGyuACUYA4YPKlJQhAyUMkpRNiV0u1gNuU"
CHANNEL_USERNAME = "@jsjsgsjsvh"

# ========== قاعدة البيانات ==========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS combos (id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, country_code TEXT, country_name TEXT, country_flag TEXT, numbers TEXT, UNIQUE(platform, country_code))''')
    c.execute('''CREATE TABLE IF NOT EXISTS otp_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT, otp TEXT, timestamp TEXT, platform TEXT)''')
    # [ميزة 2] تتبع المستخدمين الفريدين
    c.execute('''CREATE TABLE IF NOT EXISTS visitors (id INTEGER PRIMARY KEY AUTOINCREMENT, ip TEXT, last_visit TEXT)''')
    conn.commit()
    conn.close()
init_db()

# ========== جميع دول العالم ==========
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

# ========== دوال الكومبو ==========
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

# [ميزة 2] تسجيل الزائر
def track_visitor(ip):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id FROM visitors WHERE ip=?", (ip,))
        if c.fetchone():
            c.execute("UPDATE visitors SET last_visit=? WHERE ip=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ip))
        else:
            c.execute("INSERT INTO visitors (ip, last_visit) VALUES (?, ?)", (ip, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Visitor track error: {e}")

# [ميزة 2] جلب الإحصائيات الحية
def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # إجمالي الأكواد
    c.execute("SELECT COUNT(*) FROM otp_logs")
    total = c.fetchone()[0]
    # أكواد اليوم
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM otp_logs WHERE timestamp LIKE ?", (f"{today}%",))
    today_count = c.fetchone()[0]
    # عدد المستخدمين الفريدين
    c.execute("SELECT COUNT(*) FROM visitors")
    users = c.fetchone()[0]
    # عدد الدول (من الكومبوهات)
    c.execute("SELECT COUNT(DISTINCT country_code) FROM combos")
    countries = c.fetchone()[0]
    conn.close()
    return {'total': total, 'today': today_count, 'users': users, 'countries': countries}

# [ميزة 7] إحصائيات آخر 7 أيام للرسم البياني
def get_last_7_days_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    result = []
    for i in range(6, -1, -1):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        c.execute("SELECT COUNT(*) FROM otp_logs WHERE timestamp LIKE ?", (f"{day}%",))
        count = c.fetchone()[0]
        result.append({'date': day, 'count': count})
    conn.close()
    return result

# ============= شعارات SVG =============
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

platform_keys = {
    'الكل': 'all',
    'واتساب': 'whatsapp',
    'فيسبوك': 'facebook',
    'تيليجرام': 'telegram',
    'تيك توك': 'tiktok',
    'انستقرام': 'instagram',
    'سناب شات': 'snapchat',
    'جوجل': 'google',
    'تويتر/X': 'twitter'
}

main_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>🚀 موقع المطري OTP 🚀</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        /* ============ [ميزة 5] متغيرات الألوان - الوضع الليلي/النهاري ============ */
        :root {
            --bg-base: #0a0e1a;
            --bg-container: rgba(17, 24, 39, 0.85);
            --bg-card: rgba(31, 41, 55, 0.7);
            --bg-card-solid: #1f2937;
            --text-main: #fff;
            --text-muted: #cbd5e1;
            --text-soft: #94a3b8;
            --border-soft: rgba(255,255,255,0.1);
            --accent: #00ffc8;
            --accent-2: #8b5cf6;
            --accent-3: #ec4899;
            --otp-glow: rgba(0, 255, 136, 0.4);
            --star-color: #fff;
            --stat-card-bg: linear-gradient(135deg, rgba(31, 41, 55, 0.7), rgba(15, 23, 42, 0.7));
        }
        body.light-mode {
            --bg-base: #f0f4f8;
            --bg-container: rgba(255, 255, 255, 0.85);
            --bg-card: rgba(255, 255, 255, 0.9);
            --bg-card-solid: #ffffff;
            --text-main: #0f172a;
            --text-muted: #475569;
            --text-soft: #64748b;
            --border-soft: rgba(0,0,0,0.1);
            --accent: #0891b2;
            --accent-2: #7c3aed;
            --accent-3: #db2777;
            --otp-glow: rgba(8, 145, 178, 0.3);
            --star-color: #facc15;
            --stat-card-bg: linear-gradient(135deg, #ffffff, #e0f2fe);
        }

        * { margin:0; padding:0; box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
        html, body { font-family:'Cairo',sans-serif; background:var(--bg-base); color:var(--text-main); overflow-x:hidden; transition: background 0.5s, color 0.5s; }
        
        body::before {
            content:''; position:fixed; inset:0; z-index:-2;
            background: radial-gradient(circle at 20% 20%, rgba(0, 255, 200, 0.15), transparent 40%),
                        radial-gradient(circle at 80% 70%, rgba(139, 92, 246, 0.15), transparent 40%),
                        radial-gradient(circle at 50% 50%, rgba(236, 72, 153, 0.1), transparent 50%);
            animation: bgShift 12s ease-in-out infinite alternate;
        }
        body.light-mode::before {
            background: radial-gradient(circle at 20% 20%, rgba(8, 145, 178, 0.15), transparent 40%),
                        radial-gradient(circle at 80% 70%, rgba(124, 58, 237, 0.15), transparent 40%),
                        radial-gradient(circle at 50% 50%, rgba(219, 39, 119, 0.1), transparent 50%);
        }
        @keyframes bgShift { 0%{ transform:scale(1) rotate(0deg);} 100%{ transform:scale(1.1) rotate(5deg);} }
        
        .stars { position:fixed; inset:0; z-index:-1; pointer-events:none; }
        .star { position:absolute; background:var(--star-color); border-radius:50%; animation: twinkle 3s infinite; box-shadow: 0 0 8px var(--star-color); }
        @keyframes twinkle { 0%,100%{ opacity:0; transform:scale(0);} 50%{ opacity:1; transform:scale(1);} }
        
        .container { background:var(--bg-container); backdrop-filter:blur(20px); padding:25px 18px 40px; width:100%; min-height:100vh; border-inline:1px solid rgba(139, 92, 246, 0.3); transition: background 0.5s; }
        
        .top-bar { display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; position:relative; }
        .top-actions { display:flex; gap:8px; }
        .menu-btn, .theme-btn, .notify-btn { 
            background:var(--stat-card-bg); border:1px solid rgba(0,255,200,0.4);
            border-radius:12px; padding:10px 14px; color:var(--accent); font-size:18px; cursor:pointer;
            box-shadow: 0 0 15px rgba(0,255,200,0.2);
            transition:all 0.3s;
        }
        .menu-btn:hover, .theme-btn:hover, .notify-btn:hover { box-shadow: 0 0 25px rgba(0,255,200,0.6); transform:translateY(-2px); }
        .theme-btn.active { background: var(--accent); color: #0a0e1a; }
        .dropdown-menu { 
            display:none; position:absolute; top:55px; right:0; 
            background:var(--bg-container); backdrop-filter:blur(15px);
            border:1px solid rgba(0,255,200,0.3); border-radius:14px; padding:8px; 
            min-width:180px; z-index:100; box-shadow:0 5px 25px rgba(0,255,200,0.3); 
        }
        .dropdown-menu a { 
            display:flex; align-items:center; gap:10px; color:var(--text-main); text-decoration:none; 
            padding:10px 14px; border-radius:10px; font-weight:600; transition:all 0.3s; 
        }
        .dropdown-menu a:hover { background:rgba(0,255,200,0.15); color:var(--accent); transform:translateX(-5px); }
        .dropdown-menu.show { display:block; animation: slideDown 0.3s ease; }
        @keyframes slideDown { from{ opacity:0; transform:translateY(-10px);} to{ opacity:1; transform:translateY(0);} }
        
        .header { text-align:center; margin:20px 0 25px; position:relative; }
        .header h1 { 
            font-size:30px; font-weight:900; 
            background: linear-gradient(90deg, var(--accent), var(--accent-2), var(--accent-3), var(--accent));
            background-size: 300% 300%;
            -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
            animation: glow 4s ease infinite;
            text-shadow: 0 0 30px rgba(0,255,200,0.5);
            margin-bottom:8px;
        }
        @keyframes glow { 0%,100%{ background-position:0% 50%; } 50%{ background-position:100% 50%; } }
        .header p { color:var(--text-muted); font-size:15px; font-weight:600; }
        .header p .crown { display:inline-block; animation: bounce 1.5s infinite; }
        @keyframes bounce { 0%,100%{ transform:translateY(0);} 50%{ transform:translateY(-5px);} }

        /* ============ [ميزة 2] بطاقات الإحصائيات الحية ============ */
        .stats-grid {
            display:grid; grid-template-columns:repeat(2, 1fr); gap:10px; margin:18px 0 20px;
        }
        .stat-card {
            background:var(--stat-card-bg); border:1px solid var(--border-soft);
            border-radius:14px; padding:14px 10px; text-align:center;
            transition:all 0.3s; position:relative; overflow:hidden;
        }
        .stat-card::before {
            content:''; position:absolute; inset:0; opacity:0.1;
            background:linear-gradient(135deg, var(--accent), var(--accent-2));
        }
        .stat-card:hover { transform:translateY(-3px); box-shadow: 0 5px 20px var(--otp-glow); }
        .stat-card .stat-icon { font-size:24px; margin-bottom:4px; display:block; }
        .stat-card .stat-value { 
            font-size:22px; font-weight:900; color:var(--accent); 
            font-family:'Courier New', monospace; display:block;
        }
        .stat-card .stat-label { 
            font-size:12px; color:var(--text-muted); font-weight:600; margin-top:2px; 
        }

        /* ============ [ميزة 7] رسم بياني ============ */
        .chart-container {
            background:var(--stat-card-bg); border:1px solid var(--border-soft);
            border-radius:16px; padding:16px; margin-bottom:20px;
        }
        .chart-container h3 {
            color:var(--accent); font-size:15px; margin-bottom:12px; display:flex; align-items:center; gap:8px;
        }
        #weeklyChart { max-height:200px; }

        .section-title { 
            display:flex; align-items:center; gap:10px; margin:25px 0 15px; 
            color:var(--accent); font-size:17px; font-weight:700;
        }
        .section-title .emoji { font-size:22px; animation: pulse 2s infinite; }
        @keyframes pulse { 0%,100%{ transform:scale(1);} 50%{ transform:scale(1.2);} }
        .section-title::after { content:''; flex:1; height:2px; background:linear-gradient(90deg, var(--accent), transparent); border-radius:2px; }

        /* ============ [ميزة 3] شريط البحث ============ */
        .search-box {
            position:relative; margin-bottom:15px;
        }
        .search-box input {
            width:100%; padding:12px 44px 12px 16px; border-radius:14px;
            border:2px solid var(--border-soft); background:var(--bg-card);
            color:var(--text-main); font-family:'Cairo',sans-serif; font-size:14px; font-weight:600;
            outline:none; transition:all 0.3s;
        }
        .search-box input:focus { 
            border-color:var(--accent); box-shadow: 0 0 15px var(--otp-glow);
        }
        .search-box .search-icon {
            position:absolute; right:14px; top:50%; transform:translateY(-50%);
            color:var(--accent); font-size:16px;
        }

        /* ============ [ميزة 6] أزرار تصفية المنصات ============ */
        .filter-bar {
            display:flex; gap:8px; overflow-x:auto; padding:4px 2px 12px;
            scrollbar-width:thin; -webkit-overflow-scrolling:touch;
        }
        .filter-bar::-webkit-scrollbar { height:4px; }
        .filter-bar::-webkit-scrollbar-thumb { background:var(--accent); border-radius:10px; }
        .filter-btn {
            flex-shrink:0; padding:8px 16px; border-radius:20px;
            background:var(--bg-card); border:1px solid var(--border-soft);
            color:var(--text-muted); font-family:'Cairo',sans-serif; font-size:13px; font-weight:700;
            cursor:pointer; transition:all 0.3s; white-space:nowrap;
        }
        .filter-btn:hover { color:var(--accent); border-color:var(--accent); }
        .filter-btn.active {
            background:linear-gradient(135deg, var(--accent), var(--accent-2));
            color:#0a0e1a; border-color:transparent;
            box-shadow: 0 0 15px var(--otp-glow);
        }

        .platform-selector { display:grid; grid-template-columns:repeat(2, 1fr); gap:12px; margin-bottom:10px; }
        .platform-btn {
            display:flex; align-items:center; gap:12px; padding:14px 12px;
            border:2px solid var(--border-soft); border-radius:16px;
            background:var(--bg-card); color:var(--text-main);
            cursor:pointer; transition:all 0.4s cubic-bezier(0.4, 0, 0.2, 1); 
            font-size:14px; font-weight:700; font-family:'Cairo',sans-serif;
            position:relative; overflow:hidden;
        }
        .platform-btn::before {
            content:''; position:absolute; inset:0; opacity:0; transition:opacity 0.4s;
            background:var(--bg-gradient);
            z-index:0;
        }
        .platform-btn:hover { 
            transform:translateY(-3px) scale(1.02); 
            border-color:transparent;
            box-shadow: 0 8px 25px rgba(0,0,0,0.5);
        }
        .platform-btn:hover::before { opacity:1; }
        .platform-btn.active { 
            border-color:transparent;
            box-shadow: 0 0 25px var(--glow-color), 0 0 50px var(--glow-color);
            transform:translateY(-2px);
        }
        .platform-btn.active::before { opacity:1; }
        .platform-btn img { 
            width:42px; height:42px; object-fit:contain; 
            border-radius:12px;
            position:relative; z-index:1;
            box-shadow: 0 4px 14px rgba(0,0,0,0.4);
            transition:transform 0.4s;
            background: rgba(255,255,255,0.95);
            padding: 3px;
        }
        .platform-btn.active img { transform: rotate(360deg) scale(1.15); }
        .platform-btn span { position:relative; z-index:1; }

        .form-group { margin-bottom:18px; }
        .form-group label { display:flex; align-items:center; gap:8px; margin-bottom:10px; color:var(--text-muted); font-weight:700; font-size:14px; }
        .form-control { 
            width:100%; padding:14px 16px; border-radius:14px; 
            border:2px solid var(--border-soft); 
            background:var(--bg-card); color:var(--text-main); 
            outline:none; font-family:'Cairo',sans-serif; font-size:15px; font-weight:600;
            transition:all 0.3s;
        }
        .form-control:focus { 
            border-color:var(--accent); 
            box-shadow: 0 0 20px var(--otp-glow);
        }
        .form-control:disabled { opacity:0.4; cursor:not-allowed; }

        .btn-primary { 
            width:100%; padding:16px; border:none; border-radius:16px; 
            background: linear-gradient(135deg, #00ff88, #00d2ff);
            color:#0a0e1a; font-size:18px; font-weight:900;
            cursor:pointer; margin-top:12px; 
            font-family:'Cairo',sans-serif;
            box-shadow: 0 0 25px rgba(0, 255, 136, 0.5);
            transition:all 0.3s;
            position:relative; overflow:hidden;
        }
        .btn-primary::before {
            content:''; position:absolute; top:0; left:-100%;
            width:100%; height:100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
            transition:left 0.6s;
        }
        .btn-primary:hover::before { left:100%; }
        .btn-primary:hover { transform:translateY(-3px); box-shadow: 0 5px 35px rgba(0, 255, 136, 0.7); }
        .btn-primary:disabled { opacity:0.4; cursor:not-allowed; box-shadow:none; transform:none; }
        
        .btn-blue { 
            width:100%; padding:16px; border:none; border-radius:16px; 
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            color:#fff; font-size:16px; font-weight:800;
            cursor:pointer; margin-top:10px; 
            font-family:'Cairo',sans-serif;
            box-shadow: 0 0 20px rgba(59, 130, 246, 0.5);
            transition:all 0.3s;
            display:flex; align-items:center; justify-content:center; gap:8px;
        }
        .btn-blue:hover { transform:translateY(-3px); box-shadow: 0 5px 30px rgba(59, 130, 246, 0.7); }
        .btn-blue:disabled { opacity:0.4; cursor:not-allowed; }
        
        .btn-danger { 
            background: linear-gradient(135deg, #ef4444, #b91c1c) !important;
            box-shadow: 0 0 20px rgba(239, 68, 68, 0.5) !important;
        }
        .btn-danger:hover { box-shadow: 0 5px 30px rgba(239, 68, 68, 0.7) !important; }
        
        .number-box { 
            display:flex; align-items:center; justify-content:space-between; 
            background: linear-gradient(135deg, #000, #0f172a);
            border:2px solid #00ff88; border-radius:16px; padding:16px; margin:18px 0;
            box-shadow: 0 0 30px var(--otp-glow), inset 0 0 20px rgba(0, 255, 136, 0.1);
            animation: glowPulse 2s infinite;
        }
        @keyframes glowPulse { 0%,100%{ box-shadow: 0 0 30px var(--otp-glow), inset 0 0 20px rgba(0, 255, 136, 0.1);} 50%{ box-shadow: 0 0 40px rgba(0, 255, 136, 0.7), inset 0 0 30px rgba(0, 255, 136, 0.2);} }
        .number-box .number { 
            font-family:'Courier New',monospace; font-size:22px; 
            color:#00ff88; flex-grow:1; text-align:center; font-weight:bold;
            text-shadow: 0 0 10px #00ff88;
            letter-spacing:1px;
        }
        .copy-number-btn { 
            background:rgba(0, 255, 136, 0.15); border:1px solid #00ff88;
            border-radius:10px; padding:8px 12px; color:#00ff88; 
            cursor:pointer; font-size:18px; margin-right:10px;
            transition:all 0.3s;
        }
        .copy-number-btn:hover { background:#00ff88; color:#000; transform:rotate(15deg); }
        
        .otp-container { 
            margin-top:20px; max-height:380px; overflow-y:auto; 
            border:1px solid rgba(139, 92, 246, 0.3); border-radius:16px; padding:12px; 
            background:var(--bg-card);
        }
        .otp-container::-webkit-scrollbar { width:6px; }
        .otp-container::-webkit-scrollbar-track { background:rgba(255,255,255,0.05); border-radius:10px; }
        .otp-container::-webkit-scrollbar-thumb { background:linear-gradient(180deg, var(--accent), var(--accent-2)); border-radius:10px; }
        .otp-item { 
            background: linear-gradient(135deg, #0f172a, #1e293b);
            border:1px solid #00ff88; border-radius:14px; 
            padding:14px; margin-bottom:12px; 
            font-family:'Courier New'; font-size:15px; 
            color:#00ff88; line-height:1.7;
            box-shadow: 0 0 15px var(--otp-glow);
            animation: slideIn 0.4s ease;
            position:relative;
        }
        @keyframes slideIn { from{opacity:0; transform:translateX(20px);} to{opacity:1; transform:translateX(0);} }
        .otp-item .copy-btn { 
            background:rgba(0, 255, 136, 0.2); border:1px solid #00ff88;
            border-radius:8px; padding:5px 12px; color:#00ff88; 
            cursor:pointer; font-size:12px; font-weight:bold;
            transition:all 0.3s;
        }
        .otp-item .copy-btn:hover { background:#00ff88; color:#000; }
        .otp-item .info { color:var(--text-soft); font-size:12px; display:block; margin-top:6px; }
        
        /* ============ [ميزة 1] عداد تنازلي 60 ثانية ============ */
        .countdown-timer {
            display:inline-block; margin-right:10px; padding:3px 10px;
            background:rgba(0, 255, 136, 0.15); border:1px solid #00ff88;
            border-radius:20px; font-size:12px; font-weight:bold;
            color:#00ff88; font-family:'Courier New', monospace;
        }
        .countdown-timer.expired {
            background:rgba(239, 68, 68, 0.15); border-color:#ef4444; color:#ef4444;
        }
        .countdown-timer.warning {
            background:rgba(245, 158, 11, 0.15); border-color:#f59e0b; color:#f59e0b;
        }

        /* ============ [ميزة 9] قسم الأكواد القديمة ============ */
        .old-otp-item {
            opacity:0.7;
            background: linear-gradient(135deg, #1a1f2e, #0f172a) !important;
            border:1px solid #475569 !important;
            color:#94a3b8 !important;
        }
        .old-otp-item .countdown-timer { display:none; }
        .old-section-title {
            color:#94a3b8 !important;
        }
        .old-section-title::after { background: linear-gradient(90deg, #94a3b8, transparent) !important; }

        .status { 
            background: var(--stat-card-bg);
            padding:14px; border-radius:14px; text-align:center; 
            margin-top:20px; color:var(--text-muted); font-size:14px; font-weight:600;
            border:1px solid var(--border-soft);
        }
        .status .icon { font-size:18px; margin-left:8px; }
        
        .pulse-emoji { display:inline-block; animation: pulse 1.5s infinite; }
        .spin-emoji { display:inline-block; animation: spin 3s linear infinite; }
        @keyframes spin { from{transform:rotate(0);} to{transform:rotate(360deg);} }
        
        @media (min-width: 768px) {
            .container { max-width:480px; margin:0 auto; min-height:100vh; }
            .platform-selector { grid-template-columns:repeat(2, 1fr); }
        }
        @media (max-width: 380px) {
            .header h1 { font-size:24px; }
            .platform-btn img { width:32px; height:32px; }
            .platform-btn span { font-size:12px; }
            .stat-card .stat-value { font-size:18px; }
        }
    </style>
</head>
<body>
    <div class="stars" id="stars"></div>
    
    <div class="container">
        <div class="top-bar">
            <div class="top-actions">
                <!-- [ميزة 5] زر تبديل الوضع -->
                <button class="theme-btn" id="themeBtn" onclick="toggleTheme()" title="تبديل الوضع">🌙</button>
                <!-- [ميزة 8] زر تفعيل الإشعارات -->
                <button class="notify-btn" id="notifyBtn" onclick="requestNotificationPermission()" title="تفعيل الإشعارات">🔔</button>
            </div>
            <button class="menu-btn" onclick="toggleMenu()">☰</button>
            <div class="dropdown-menu" id="contactMenu">
                <a href="{{ owner_link }}" target="_blank">📞 تواصل معي</a>
                <a href="{{ wa_group }}" target="_blank">💬 جروب واتساب</a>
            </div>
        </div>

        <div class="header">
            <h1>🚀 موقع المطري OTP 🚀</h1>
            <p><span class="crown">👑</span> أرقام واتساب سحب أكواد تطوير مطري <span class="crown">👑</span></p>
        </div>

        <!-- [ميزة 2] بطاقات الإحصائيات الحية -->
        <div class="stats-grid">
            <div class="stat-card">
                <span class="stat-icon">📊</span>
                <span class="stat-value" id="statTotal">0</span>
                <span class="stat-label">إجمالي الأكواد</span>
            </div>
            <div class="stat-card">
                <span class="stat-icon">📅</span>
                <span class="stat-value" id="statToday">0</span>
                <span class="stat-label">أكواد اليوم</span>
            </div>
            <div class="stat-card">
                <span class="stat-icon">👥</span>
                <span class="stat-value" id="statUsers">0</span>
                <span class="stat-label">عدد المستخدمين</span>
            </div>
            <div class="stat-card">
                <span class="stat-icon">🌍</span>
                <span class="stat-value" id="statCountries">0</span>
                <span class="stat-label">عدد الدول</span>
            </div>
        </div>

        <!-- [ميزة 7] رسم بياني لآخر 7 أيام -->
        <div class="chart-container">
            <h3>📈 إحصائيات آخر 7 أيام</h3>
            <canvas id="weeklyChart"></canvas>
        </div>

        <div class="section-title">
            <span class="emoji">🎯</span>
            <span>اختر المنصة</span>
        </div>
        <div class="form-group">
            <div class="platform-selector" id="platformSelector"></div>
        </div>

        <div class="section-title">
            <span class="emoji">🌍</span>
            <span>اختر الدولة</span>
        </div>
        <div class="form-group">
            <select id="country" class="form-control" disabled>
                <option value="">🚀 -- اختر المنصة أولاً -- 🚀</option>
            </select>
        </div>

        <button class="btn-primary" id="getNumberBtn" onclick="getNumber()" disabled>
            🚀 جلب رقم
        </button>
        <button class="btn-blue" id="refreshBtn" onclick="refreshNumber()" disabled>
            🔄 تبديل
        </button>

        <div id="numberContainer" style="display:none;">
            <div class="number-box">
                <button class="copy-number-btn" onclick="copyNumber()" title="نسخ">📋</button>
                <div class="number" id="numberDisplay">+</div>
            </div>
            <div style="display:flex; gap:10px; margin-top:12px;">
                <button class="btn-primary" onclick="startMonitoring()">📡 بدء السحب</button>
                <button class="btn-blue btn-danger" onclick="stopMonitoring()">⏹️ إيقاف</button>
            </div>
        </div>

        <!-- [ميزة 3] شريط البحث -->
        <div class="search-box" id="searchBox" style="display:none;">
            <span class="search-icon">🔍</span>
            <input type="text" id="searchInput" placeholder="ابحث في الأكواد (رقم، كود، منصة...)" oninput="filterOtpList()">
        </div>

        <!-- [ميزة 6] أزرار تصفية المنصات -->
        <div class="filter-bar" id="filterBar" style="display:none;"></div>

        <div class="section-title">
            <span class="emoji">🔑</span>
            <span>الأكواد الجديدة</span>
        </div>
        <div class="otp-container" id="otpHistory">
            <div style="text-align:center; color:#64748b; padding:25px;">
                <div style="font-size:40px; margin-bottom:10px;">⏳</div>
                <div>في انتظار الأكواد...</div>
            </div>
        </div>

        <!-- [ميزة 9] قسم الأكواد القديمة -->
        <div class="section-title old-section-title" id="oldSectionTitle" style="display:none;">
            <span class="emoji">📜</span>
            <span>الأكواد القديمة (منتهية الصلاحية)</span>
        </div>
        <div class="otp-container" id="oldOtpHistory" style="display:none; max-height:250px;"></div>

        <div class="status" id="status">
            <span class="icon">⚡</span>
            اختر المنصة والدولة للبدء
        </div>

        <div style="text-align:center; margin-top:25px; color:#64748b; font-size:13px;">
            <span class="pulse-emoji">💎</span> صُنع بحب <span class="spin-emoji">⚡</span> بواسطة المطري
        </div>
    </div>

    <script>
        const platformLogos = {{ platform_logos | tojson }};
        const platformLogosSmall = {{ platform_logos_small | tojson }};
        const platformNames = {{ platform_names | tojson }};
        const platformGradients = {{ platform_gradients | tojson }};
        const platformKeysMap = {{ platform_keys | tojson }};

        function createStars() {
            const stars = document.getElementById('stars');
            for(let i=0; i<30; i++) {
                const star = document.createElement('div');
                star.className = 'star';
                const size = Math.random() * 3 + 1;
                star.style.width = size + 'px';
                star.style.height = size + 'px';
                star.style.left = Math.random() * 100 + '%';
                star.style.top = Math.random() * 100 + '%';
                star.style.animationDelay = Math.random() * 3 + 's';
                star.style.opacity = Math.random() * 0.7 + 0.3;
                stars.appendChild(star);
            }
        }
        createStars();

        function initPlatformSelector() {
            const selector = document.getElementById('platformSelector');
            selector.innerHTML = '';
            Object.keys(platformNames).forEach(platform => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'platform-btn';
                btn.onclick = (e) => selectPlatform(platform, e);
                
                const gradient = platformGradients[platform];
                const colorMatch = gradient.match(/#[0-9A-F]{6}/gi);
                const glowColor = colorMatch ? colorMatch[0] : '#00ffc8';
                
                btn.style.setProperty('--bg-gradient', gradient);
                btn.style.setProperty('--glow-color', glowColor + '80');
                
                btn.innerHTML = `
                    <img src="${platformLogos[platform]}" alt="${platformNames[platform]}" onerror="this.src='${platformLogosSmall[platform]}'">
                    <span>${platformNames[platform]} ✨</span>
                `;
                selector.appendChild(btn);
            });
        }

        // ============ [ميزة 5] الوضع الليلي/النهاري ============
        function toggleTheme() {
            document.body.classList.toggle('light-mode');
            const btn = document.getElementById('themeBtn');
            const isLight = document.body.classList.contains('light-mode');
            btn.textContent = isLight ? '☀️' : '🌙';
            btn.classList.toggle('active', isLight);
            localStorage.setItem('theme', isLight ? 'light' : 'dark');
            // إعادة رسم الشارت بألوان جديدة
            if (weeklyChart) updateChartColors();
        }
        // استرجاع الوضع المحفوظ
        (function() {
            const saved = localStorage.getItem('theme');
            if (saved === 'light') {
                document.body.classList.add('light-mode');
                document.addEventListener('DOMContentLoaded', () => {
                    const btn = document.getElementById('themeBtn');
                    btn.textContent = '☀️'; btn.classList.add('active');
                });
            }
        })();

        // ============ [ميزة 8] إشعارات المتصفح ============
        function requestNotificationPermission() {
            if (!('Notification' in window)) {
                showToast('❌ المتصفح لا يدعم الإشعارات');
                return;
            }
            if (Notification.permission === 'granted') {
                showToast('✅ الإشعارات مفعلة بالفعل');
                return;
            }
            Notification.requestPermission().then(permission => {
                const btn = document.getElementById('notifyBtn');
                if (permission === 'granted') {
                    btn.classList.add('active');
                    btn.textContent = '🔔✓';
                    new Notification('🎉 تم تفعيل الإشعارات', {
                        body: 'ستصلك إشعارات عند وصول كل كود جديد',
                        icon: 'https://cdn-icons-png.flaticon.com/512/1828/1828884.png'
                    });
                    showToast('✅ تم تفعيل الإشعارات!');
                } else {
                    showToast('❌ تم رفض الإشعارات');
                }
            });
        }

        function showBrowserNotification(title, body) {
            if (Notification.permission === 'granted') {
                const n = new Notification(title, {
                    body: body,
                    icon: 'https://cdn-icons-png.flaticon.com/512/1828/1828884.png',
                    badge: 'https://cdn-icons-png.flaticon.com/512/1828/1828884.png',
                    tag: 'otp-notification',
                    requireInteraction: false
                });
                setTimeout(() => n.close(), 8000);
            }
        }

        // ============ [ميزة 4] صوت تنبيه ============
        const notificationSound = (function() {
            // صوت تنبيه مدمج (Web Audio API) - لا يحتاج ملف خارجي
            let audioCtx = null;
            function getCtx() {
                if (!audioCtx) {
                    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                }
                return audioCtx;
            }
            return function play() {
                try {
                    const ctx = getCtx();
                    // نغمة 1
                    const osc1 = ctx.createOscillator();
                    const gain1 = ctx.createGain();
                    osc1.connect(gain1); gain1.connect(ctx.destination);
                    osc1.frequency.value = 800;
                    osc1.type = 'sine';
                    gain1.gain.setValueAtTime(0, ctx.currentTime);
                    gain1.gain.linearRampToValueAtTime(0.3, ctx.currentTime + 0.05);
                    gain1.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.2);
                    osc1.start(ctx.currentTime);
                    osc1.stop(ctx.currentTime + 0.2);
                    // نغمة 2
                    const osc2 = ctx.createOscillator();
                    const gain2 = ctx.createGain();
                    osc2.connect(gain2); gain2.connect(ctx.destination);
                    osc2.frequency.value = 1200;
                    osc2.type = 'sine';
                    gain2.gain.setValueAtTime(0, ctx.currentTime + 0.15);
                    gain2.gain.linearRampToValueAtTime(0.3, ctx.currentTime + 0.2);
                    gain2.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.45);
                    osc2.start(ctx.currentTime + 0.15);
                    osc2.stop(ctx.currentTime + 0.45);
                } catch (e) { console.log('Audio play failed:', e); }
            };
        })();

        // ============ [ميزة 6] تهيئة أزرار التصفية ============
        function initFilterBar() {
            const bar = document.getElementById('filterBar');
            bar.innerHTML = '';
            Object.entries(platformNames).forEach(([key, arName]) => {
                const btn = document.createElement('button');
                btn.className = 'filter-btn';
                btn.textContent = arName;
                btn.dataset.platform = key;
                btn.onclick = () => {
                    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    filterOtpList();
                };
                bar.appendChild(btn);
            });
            // زر "الكل" أولاً
            const allBtn = document.createElement('button');
            allBtn.className = 'filter-btn active';
            allBtn.textContent = '🔎 الكل';
            allBtn.dataset.platform = 'all';
            allBtn.onclick = () => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                allBtn.classList.add('active');
                filterOtpList();
            };
            bar.prepend(allBtn);
        }

        let currentFilter = 'all';
        function filterOtpList() {
            const query = document.getElementById('searchInput').value.toLowerCase().trim();
            const activeBtn = document.querySelector('.filter-btn.active');
            currentFilter = activeBtn ? activeBtn.dataset.platform : 'all';

            // تصفية الأكواد الجديدة
            document.querySelectorAll('#otpHistory .otp-item').forEach(item => {
                const text = item.textContent.toLowerCase();
                const matchesSearch = !query || text.includes(query);
                const matchesFilter = currentFilter === 'all' || (item.dataset.platform === currentFilter);
                item.style.display = (matchesSearch && matchesFilter) ? '' : 'none';
            });
            // تصفية الأكواد القديمة
            document.querySelectorAll('#oldOtpHistory .old-otp-item').forEach(item => {
                const text = item.textContent.toLowerCase();
                const matchesSearch = !query || text.includes(query);
                const matchesFilter = currentFilter === 'all' || (item.dataset.platform === currentFilter);
                item.style.display = (matchesSearch && matchesFilter) ? '' : 'none';
            });
        }

        function toggleMenu() {
            document.getElementById('contactMenu').classList.toggle('show');
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
            showToast('✅ تم نسخ الرقم! ' + num);
        }

        function showToast(msg) {
            const t = document.createElement('div');
            t.textContent = msg;
            t.style.cssText = 'position:fixed;top:20px;left:50%;transform:translateX(-50%);background:linear-gradient(135deg,#00ff88,#00d2ff);color:#000;padding:14px 28px;border-radius:14px;font-weight:bold;z-index:9999;box-shadow:0 0 30px rgba(0,255,136,0.6);animation:slideIn 0.4s;';
            document.body.appendChild(t);
            setTimeout(() => t.remove(), 2500);
        }

        let currentPlatform = '';
        let currentNumber = '';
        let monitorInterval = null;
        let lastOtpId = 0;
        let chartRefreshInterval = null;

        // ============ [ميزة 1] تخزين العدادات التنازلية ============
        const otpCountdowns = new Map();

        function selectPlatform(platform, event) {
            currentPlatform = platform;
            document.querySelectorAll('.platform-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            const btn = event.currentTarget || event.target.closest('.platform-btn');
            btn.classList.add('active');
            loadCountries();
        }

        async function loadCountries() {
            const platform = currentPlatform;
            const countrySelect = document.getElementById('country');
            if (!platform) {
                countrySelect.innerHTML = '<option value="">🚀 -- اختر المنصة أولاً -- 🚀</option>';
                countrySelect.disabled = true;
                document.getElementById('numberContainer').style.display = 'none';
                document.getElementById('getNumberBtn').disabled = true;
                document.getElementById('refreshBtn').disabled = true;
                return;
            }
            countrySelect.disabled = true;
            countrySelect.innerHTML = '<option value="">⏳ جاري التحميل...</option>';
            const res = await fetch('/api/countries', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({platform})});
            const data = await res.json();
            let options = '<option value="">🌍 -- اختر الدولة -- 🌍</option>';
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
            if (!platform || !country) {
                document.getElementById('status').innerHTML = '<span class="icon">⚠️</span>يرجى اختيار المنصة والدولة';
                return;
            }
            document.getElementById('status').innerHTML = '<span class="icon">⏳</span>جاري جلب رقم...';
            const res = await fetch('/api/get_number', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({platform, country})});
            const data = await res.json();
            if (data.number) {
                currentNumber = data.number;
                document.getElementById('numberDisplay').textContent = '+' + data.number;
                document.getElementById('numberContainer').style.display = 'block';
                document.getElementById('status').innerHTML = '<span class="icon">✅</span>الرقم جاهز!';
                showToast('🎉 تم جلب رقم جديد!');
            } else {
                document.getElementById('status').innerHTML = '<span class="icon">❌</span>لا توجد أرقام متاحة.';
            }
        }

        async function refreshNumber() {
            const platform = currentPlatform;
            const country = document.getElementById('country').value;
            if (!platform || !country) return;
            document.getElementById('status').innerHTML = '<span class="icon">⏳</span>جاري تبديل الرقم...';
            const res = await fetch('/api/get_number', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({platform, country})});
            const data = await res.json();
            if (data.number && data.number !== currentNumber) {
                currentNumber = data.number;
                document.getElementById('numberDisplay').textContent = '+' + data.number;
                document.getElementById('status').innerHTML = '<span class="icon">🔄</span>تم تبديل الرقم!';
                showToast('🔄 تم التبديل!');
            }
        }

        // ============ [ميزة 1] تحديث العداد التنازلي ============
        function updateCountdowns() {
            const now = Date.now();
            otpCountdowns.forEach((endTime, otpId) => {
                const timerEl = document.getElementById('timer-' + otpId);
                if (!timerEl) return;
                const remaining = Math.max(0, Math.floor((endTime - now) / 1000));
                if (remaining <= 0) {
                    timerEl.textContent = '⏱️ منتهي';
                    timerEl.classList.add('expired');
                    timerEl.classList.remove('warning');
                    // نقل الكود إلى قسم الأكواد القديمة
                    moveToOld(otpId);
                } else {
                    timerEl.textContent = '⏱️ ' + remaining + 'ث';
                    timerEl.classList.remove('expired');
                    if (remaining <= 10) timerEl.classList.add('warning');
                    else timerEl.classList.remove('warning');
                }
            });
        }
        setInterval(updateCountdowns, 1000);

        // ============ [ميزة 9 + 10] إضافة كود للأكواد الجديدة في الأعلى ============
        function addOtpToHistory(otp, platform, number, timestamp, isNew=true) {
            const container = isNew ? document.getElementById('otpHistory') : document.getElementById('oldOtpHistory');
            
            // تنظيف رسالة "في انتظار"
            if (container.children.length === 1 && container.textContent.includes('في انتظار')) {
                container.innerHTML = '';
            }
            // إظهار شريط البحث والفلاتر وقسم الأكواد القديمة
            if (isNew) {
                document.getElementById('searchBox').style.display = 'block';
                document.getElementById('filterBar').style.display = 'flex';
            } else {
                document.getElementById('oldSectionTitle').style.display = 'flex';
                document.getElementById('oldOtpHistory').style.display = 'block';
            }

            const div = document.createElement('div');
            div.className = isNew ? 'otp-item' : 'otp-item old-otp-item';
            const otpId = 'otp-' + Date.now() + '-' + Math.random().toString(36).substr(2,5);
            div.id = otpId;
            div.dataset.platform = platformKeysMap[platform] || '';
            
            if (isNew) {
                // [ميزة 1] عداد تنازلي 60 ثانية
                otpCountdowns.set(otpId, Date.now() + 60000);
            }

            const platformColor = {
                'واتساب': '#25D366', 'فيسبوك': '#1877F2', 'تيليجرام': '#26A5E4',
                'تيك توك': '#FE2C55', 'انستقرام': '#E1306C', 'سناب شات': '#FFFC00',
                'جوجل': '#4285F4', 'تويتر/X': '#1da1f2'
            }[platform] || '#00ffc8';

            div.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; flex-wrap:wrap; gap:6px;">
                    <strong style="color:#00ff88;">🔑 ${otp}</strong>
                    <div style="display:flex; gap:6px; align-items:center;">
                        ${isNew ? `<span class="countdown-timer" id="timer-${otpId}">⏱️ 60ث</span>` : '<span class="countdown-timer expired">⏱️ منتهي</span>'}
                        <button class="copy-btn" onclick="copyText('${otp}')">📋 نسخ</button>
                    </div>
                </div>
                <span class="info">📞 +${number} • 📱 ${platform} • 🕒 ${timestamp}</span>
            `;
            // [ميزة 10] الجديد في الأعلى
            container.prepend(div);
            // أقصى عدد 30 كود
            while (container.children.length > 30) container.removeChild(container.lastChild);
            
            // تطبيق الفلتر الحالي
            filterOtpList();
        }

        // نقل كود منتهي إلى قسم الأكواد القديمة
        function moveToOld(otpId) {
            const el = document.getElementById(otpId);
            if (!el || el.classList.contains('old-otp-item')) return;
            otpCountdowns.delete(otpId);
            const newContainer = document.getElementById('oldOtpHistory');
            document.getElementById('oldSectionTitle').style.display = 'flex';
            document.getElementById('oldOtpHistory').style.display = 'block';
            // تنظيف رسالة "في انتظار" في القسم القديم إن وُجدت
            if (newContainer.textContent.includes('لا توجد أكواد قديمة')) {
                newContainer.innerHTML = '';
            }
            el.classList.add('old-otp-item');
            // استبدال العداد بعلامة "منتهي"
            const timerEl = el.querySelector('.countdown-timer');
            if (timerEl) {
                timerEl.classList.add('expired');
                timerEl.classList.remove('warning');
                timerEl.textContent = '⏱️ منتهي';
            }
            newContainer.prepend(el);
            // حذف العداد من الخريطة
            filterOtpList();
        }

        function copyText(text) { 
            navigator.clipboard.writeText(text); 
            showToast('✅ تم نسخ الكود!');
        }

        // ============ [ميزة 2] تحديث الإحصائيات ============
        async function refreshStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                animateNumber('statTotal', data.total);
                animateNumber('statToday', data.today);
                animateNumber('statUsers', data.users);
                animateNumber('statCountries', data.countries);
            } catch(e) { console.log('Stats error:', e); }
        }
        function animateNumber(id, target) {
            const el = document.getElementById(id);
            const current = parseInt(el.textContent) || 0;
            if (current === target) return;
            const step = target > current ? 1 : -1;
            let val = current;
            const interval = setInterval(() => {
                val += step;
                el.textContent = val;
                if (val === target) clearInterval(interval);
            }, 30);
        }
        setInterval(refreshStats, 10000);
        refreshStats();

        // ============ [ميزة 7] الرسم البياني ============
        let weeklyChart = null;
        async function initChart() {
            const res = await fetch('/api/weekly_stats');
            const data = await res.json();
            const labels = data.map(d => {
                const dt = new Date(d.date);
                return dt.toLocaleDateString('ar-YE', {weekday: 'short'});
            });
            const values = data.map(d => d.count);
            const ctx = document.getElementById('weeklyChart').getContext('2d');
            const isLight = document.body.classList.contains('light-mode');
            const textColor = isLight ? '#475569' : '#cbd5e1';
            const gridColor = isLight ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)';

            weeklyChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'عدد الأكواد',
                        data: values,
                        borderColor: '#00ffc8',
                        backgroundColor: 'rgba(0,255,200,0.2)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: '#8b5cf6',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 5,
                        pointHoverRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(0,0,0,0.85)',
                            titleColor: '#00ffc8', bodyColor: '#fff',
                            padding: 10, cornerRadius: 10,
                            rtl: true, textDirection: 'rtl'
                        }
                    },
                    scales: {
                        y: { 
                            beginAtZero: true, ticks: { color: textColor, precision: 0 },
                            grid: { color: gridColor }
                        },
                        x: { 
                            ticks: { color: textColor },
                            grid: { color: gridColor }
                        }
                    }
                }
            });
        }

        function updateChartColors() {
            if (!weeklyChart) return;
            const isLight = document.body.classList.contains('light-mode');
            const textColor = isLight ? '#475569' : '#cbd5e1';
            const gridColor = isLight ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)';
            weeklyChart.options.scales.y.ticks.color = textColor;
            weeklyChart.options.scales.x.ticks.color = textColor;
            weeklyChart.options.scales.y.grid.color = gridColor;
            weeklyChart.options.scales.x.grid.color = gridColor;
            weeklyChart.update();
        }

        async function refreshChart() {
            const res = await fetch('/api/weekly_stats');
            const data = await res.json();
            if (weeklyChart) {
                weeklyChart.data.labels = data.map(d => {
                    const dt = new Date(d.date);
                    return dt.toLocaleDateString('ar-YE', {weekday: 'short'});
                });
                weeklyChart.data.datasets[0].data = data.map(d => d.count);
                weeklyChart.update();
            }
        }
        setInterval(refreshChart, 30000);

        // ============ سحب الأكواد من السيرفر ============
        function startMonitoring() {
            if (!currentNumber) return;
            if (monitorInterval) clearInterval(monitorInterval);
            document.getElementById('status').innerHTML = '<span class="icon">🔄</span>بدأ السحب التلقائي...';

            monitorInterval = setInterval(() => {
                fetch('/api/get_otp', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({number:currentNumber})})
                .then(res => res.json()).then(data => {
                    if (data.otp) {
                        const now = new Date().toLocaleString('ar-YE', {timeZone: 'Asia/Aden'});
                        addOtpToHistory(data.otp, 'واتساب', currentNumber, now, true);
                        document.getElementById('status').innerHTML = '<span class="icon">✅</span>تم العثور على كود!';
                        // [ميزة 4 + 8] صوت + إشعار متصفح
                        notificationSound();
                        showBrowserNotification('🔑 كود جديد!', 'الكود: ' + data.otp);
                        refreshStats();
                        stopMonitoring();
                    }
                });
            }, 5000);
            showToast('📡 بدأ المراقبة!');
        }

        function stopMonitoring() {
            if (monitorInterval) {
                clearInterval(monitorInterval);
                monitorInterval = null;
            }
            document.getElementById('status').innerHTML = '<span class="icon">⏹️</span>تم إيقاف السحب.';
        }

        // ============ [ميزة 4 + 8] مراقب عام للأكواد الجديدة (يعمل في الخلفية) ============
        let globalMonitorInterval = null;
        async function checkForNewOtps() {
            try {
                const res = await fetch('/api/latest_otp?since_id=' + lastOtpId);
                const data = await res.json();
                if (data.otp) {
                    lastOtpId = Math.max(lastOtpId, data.id);
                    // لا نضيف الكود إذا كان للرقم الحالي (تمت إضافته بالفعل في startMonitoring)
                    if (data.number !== currentNumber || !monitorInterval) {
                        addOtpToHistory(data.otp, data.platform || 'غير معروف', data.number, data.timestamp, true);
                        notificationSound();
                        showBrowserNotification('🔑 كود جديد!', 'الكود: ' + data.otp + ' • ' + (data.platform || ''));
                        refreshStats();
                        refreshChart();
                    }
                }
            } catch(e) { console.log('Global monitor error:', e); }
        }
        function startGlobalMonitor() {
            if (globalMonitorInterval) clearInterval(globalMonitorInterval);
            globalMonitorInterval = setInterval(checkForNewOtps, 5000);
            checkForNewOtps();
        }

        // ============ تحميل الأكواد القديمة عند البدء ============
        async function loadOldOtps() {
            try {
                const res = await fetch('/api/recent_otps?limit=15');
                const data = await res.json();
                data.reverse().forEach(o => {
                    addOtpToHistory(o.otp, o.platform, o.number, o.timestamp, false);
                });
            } catch(e) { console.log('Load old otps error:', e); }
        }

        document.addEventListener('DOMContentLoaded', () => {
            initPlatformSelector();
            initFilterBar();
            initChart();
            loadOldOtps();
            startGlobalMonitor();
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
body { 
    font-family:'Cairo',sans-serif; 
    background: linear-gradient(135deg, #0a0e1a, #1a1f2e);
    color:#fff; min-height:100vh; display:flex; justify-content:center; align-items:center;
    padding:20px;
}
.container { 
    background:rgba(17, 24, 39, 0.85); backdrop-filter:blur(20px);
    padding:30px; border-radius:25px; width:100%; max-width:480px; 
    border:1px solid rgba(139, 92, 246, 0.3);
    box-shadow: 0 0 50px rgba(139, 92, 246, 0.3);
}
h1 { 
    text-align:center; 
    background: linear-gradient(90deg, #00ffc8, #8b5cf6);
    -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
    margin-bottom:25px; font-size:28px; font-weight:900;
}
h3 { color:#cbd5e1; margin-bottom:12px; margin-top:18px; }
.form-group { margin-bottom:15px; }
.form-group label { display:block; margin-bottom:6px; color:#cbd5e1; font-weight:700; }
.form-control { 
    width:100%; padding:12px; border-radius:12px; 
    border:2px solid rgba(255,255,255,0.1); 
    background:rgba(31, 41, 55, 0.7); color:#fff; 
    font-family:'Cairo',sans-serif;
    transition:all 0.3s;
}
.form-control:focus { border-color:#00ffc8; box-shadow: 0 0 20px rgba(0,255,200,0.3); }
.btn-primary { 
    width:100%; padding:14px; border:none; border-radius:12px; 
    background: linear-gradient(135deg, #00ff88, #00d2ff);
    color:#0a0e1a; cursor:pointer; margin-top:15px; 
    font-weight:900; font-size:16px; font-family:'Cairo',sans-serif;
    box-shadow: 0 0 20px rgba(0,255,136,0.4);
    transition:all 0.3s;
}
.btn-primary:hover { transform:translateY(-2px); box-shadow: 0 5px 30px rgba(0,255,136,0.6); }
.btn-danger { 
    width:100%; padding:14px; border:none; border-radius:12px; 
    background: linear-gradient(135deg, #ef4444, #b91c1c);
    color:#fff; cursor:pointer; margin-top:10px; 
    font-weight:800; font-size:15px; font-family:'Cairo',sans-serif;
    box-shadow: 0 0 20px rgba(239, 68, 68, 0.4);
    transition:all 0.3s;
}
.btn-danger:hover { transform:translateY(-2px); }
.btn-secondary { 
    width:100%; padding:14px; border:none; border-radius:12px; 
    background: linear-gradient(135deg, #374151, #4b5563);
    color:#fff; cursor:pointer; margin-top:10px; 
    font-weight:800; font-size:15px; font-family:'Cairo',sans-serif;
    transition:all 0.3s;
}
.btn-secondary:hover { transform:translateY(-2px); }
hr { border: 1px solid rgba(255,255,255,0.1); margin: 20px 0; }
.combo-item { 
    display:flex; justify-content:space-between; align-items:center; 
    background:rgba(31, 41, 55, 0.7); padding:12px; border-radius:12px; 
    margin-bottom:10px; border:1px solid rgba(139, 92, 246, 0.3);
}
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

    <h3>🗑️ حذف كومبو</h3>
    {% if combos %}
        {% for platform, code, name, flag in combos %}
        <div class="combo-item">
            <span>{{ flag }} {{ name }} ({{ platform }})</span>
            <form method="POST" style="display:inline;">
                <input type="hidden" name="action" value="delete">
                <input type="hidden" name="platform" value="{{ platform }}">
                <input type="hidden" name="country_code" value="{{ code }}">
                <button type="submit" class="btn-danger">🗑️ حذف</button>
            </form>
        </div>
        {% endfor %}
    {% else %}
        <p style="color:#64748b; text-align:center; padding:20px;">🤷‍♂️ لا توجد كومبوهات حالياً</p>
    {% endif %}

    <hr>
    <a href="/"><button class="btn-secondary">🔙 العودة للصفحة الرئيسية</button></a>
</div>
</body>
</html>
"""

# ========== المسارات (Routes) ==========
@app.route('/')
def home():
    # [ميزة 2] تسجيل الزائر
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()
    track_visitor(ip)
    return render_template_string(
        main_html,
        owner_link=OWNER_LINK,
        wa_group=WHATSAPP_GROUP_LINK,
        platform_logos=PLATFORM_LOGOS,
        platform_logos_small=PLATFORM_LOGOS_SMALL,
        platform_names=platform_names,
        platform_gradients=PLATFORM_GRADIENTS,
        platform_keys=platform_keys
    )

def get_all_combos_list():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT platform, country_code, country_name, country_flag FROM combos")
    rows = c.fetchall()
    conn.close()
    return rows

@app.route('/admin', methods=['GET', 'POST'])
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
                return redirect(url_for('admin'))
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

# [ميزة 2] API الإحصائيات
@app.route('/api/stats')
def api_stats():
    return jsonify(get_stats())

# [ميزة 7] API إحصائيات آخر 7 أيام
@app.route('/api/weekly_stats')
def api_weekly_stats():
    return jsonify(get_last_7_days_stats())

# [ميزة 8] API آخر كود (للمراقب العام)
@app.route('/api/latest_otp')
def api_latest_otp():
    since_id = request.args.get('since_id', 0, type=int)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, number, otp, timestamp, platform FROM otp_logs WHERE id > ? ORDER BY id DESC LIMIT 1", (since_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({'id': row[0], 'number': row[1], 'otp': row[2], 'timestamp': row[3], 'platform': row[4]})
    return jsonify({})

# [ميزة 9] API جلب الأكواد القديمة
@app.route('/api/recent_otps')
def api_recent_otps():
    limit = request.args.get('limit', 15, type=int)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, number, otp, timestamp, platform FROM otp_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return jsonify([{'id': r[0], 'number': r[1], 'otp': r[2], 'timestamp': r[3], 'platform': r[4]} for r in rows])

# ========== مراقب قناة تيليجرام ==========
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
