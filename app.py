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

# ========== Telegram token (ننصح لاحقاً بنقله لمتغير بيئة) ==========
TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN", "8814038881:AAGYuACUYA4YPKlJQhAyUMkpRNiV0u1gNuU")
CHANNEL_USERNAME = "@jsjsgsjsvh"

# ⏱️ المدة الجديدة للـ OTP
OTP_VALID_SECONDS = 60

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
        platform TEXT
    )''')
    # جدول سجل "التواصل معي" (يظهر للقائمة)
    c.execute('''CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        link TEXT,
        icon TEXT
    )''')
    # جدول المجموعات
    c.execute('''CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        link TEXT,
        icon TEXT
    )''')
    # إدخال بيانات افتراضية إذا الجداول فاضية
    c.execute("SELECT COUNT(*) FROM contacts")
    if c.fetchone()[0] == 0:
        for c_row in [
            ("واتساب المطور", OWNER_LINK, "📞"),
            ("تلجرام المطور", "https://t.me/", "✈️"),
            ("انستقرام", "https://instagram.com/", "📸"),
            ("تيك توك", "https://tiktok.com/", "🎵"),
        ]:
            c.execute("INSERT INTO contacts (name, link, icon) VALUES (?, ?, ?)", c_row)
    c.execute("SELECT COUNT(*) FROM groups")
    if c.fetchone()[0] == 0:
        for g_row in [
            ("جروب واتساب الدعم", WHATSAPP_GROUP_LINK, "💬"),
            ("قناة تيليجرام", "https://t.me/jsjsgsjsvh", "📢"),
            ("جروب تيليجرام", "https://t.me/", "👥"),
            ("قناة واتساب", "https://whatsapp.com/channel/", "📣"),
        ]:
            c.execute("INSERT INTO groups (name, link, icon) VALUES (?, ?, ?)", g_row)
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
    c.execute("REPLACE INTO combos (platform, country_code, country_name, country_flag, numbers) VALUES (?, ?, ?, ?, ?)",
              (platform, country_code, country_name, country_flag, json.dumps(numbers)))
    conn.commit()
    conn.close()

def get_contacts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, link, icon FROM contacts ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()
    return [{"name": r[0], "link": r[1], "icon": r[2]} for r in rows]

def get_groups():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, link, icon FROM groups ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()
    return [{"name": r[0], "link": r[1], "icon": r[2]} for r in rows]

# ============= شعارات SVG (نفس الأصلية) =============
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
    'tiktok': '#FE2C55',
    'facebook': '#1877f2',
    'instagram': '#E4405F',
    'snapchat': '#FFFC00',
    'google': '#4285F4',
    'twitter': '#1DA1F2'
}

# ========== HTML الصفحة الرئيسية ==========
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
        html, body { font-family:'Cairo',sans-serif; background:#0a0e14; color:#e6e6e6; overflow-x:hidden; }
        body { min-height:100vh; position:relative; }

        /* ============= خلفية المطر الرقمي (Matrix) ============= */
        #matrixCanvas {
            position:fixed; top:0; left:0; width:100%; height:100%;
            z-index:0; opacity:0.18; pointer-events:none;
        }
        .app { position:relative; z-index:1; max-width:480px; margin:0 auto; background:rgba(22,27,34,0.78); backdrop-filter:blur(6px); min-height:100vh; display:flex; flex-direction:column; }

        /* ============= HEADER ============= */
        .top-bar { background:rgba(22,27,34,0.95); padding:14px 16px; display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid #21262d; position:sticky; top:0; z-index:50; }
        .brand { display:flex; align-items:center; gap:10px; }
        .brand-icon { width:36px; height:36px; border-radius:10px; background:linear-gradient(135deg, #1f6feb, #388bfd); display:flex; align-items:center; justify-content:center; font-size:18px; animation:logoSpin 6s linear infinite; }
        @keyframes logoSpin { 0%,100%{transform:rotate(0);} 50%{transform:rotate(15deg) scale(1.08);} }
        .brand-text { font-size:16px; font-weight:700; color:#fff; }
        .menu-btn { background:transparent; border:none; color:#8b949e; font-size:22px; cursor:pointer; padding:4px 8px; }
        .menu-btn:hover { color:#58a6ff; }
        .dropdown-menu { display:none; position:absolute; top:55px; left:16px; right:16px; background:#1c2128; border:1px solid #30363d; border-radius:12px; padding:6px; z-index:100; box-shadow:0 8px 24px rgba(0,0,0,0.6); max-height:70vh; overflow-y:auto; }
        .dropdown-menu.show { display:block; animation:menuSlide 0.25s ease; }
        @keyframes menuSlide { from{opacity:0; transform:translateY(-8px);} to{opacity:1; transform:translateY(0);} }
        .dropdown-menu .menu-section-title { padding:8px 12px 4px; color:#58a6ff; font-size:12px; font-weight:800; border-bottom:1px solid #21262d; margin-bottom:4px; }
        .dropdown-menu a { display:flex; align-items:center; gap:10px; color:#e6e6e6; text-decoration:none; padding:10px 12px; border-radius:8px; font-size:14px; font-weight:600; transition:all 0.15s; }
        .dropdown-menu a:hover { background:#21262d; color:#58a6ff; transform:translateX(-4px); }
        .dropdown-menu a .icon { font-size:18px; }

        /* ============= MAIN ============= */
        .main { padding:16px; flex:1; }

        .hero { text-align:center; padding:24px 12px 20px; }
        .hero h1 { font-size:24px; font-weight:800; color:#fff; margin-bottom:6px; text-shadow:0 0 18px rgba(31,111,235,0.45); }
        .hero p { font-size:14px; color:#8b949e; line-height:1.5; }

        .floating-emoji { position:absolute; font-size:20px; pointer-events:none; animation:floatEmoji 5s ease-in-out infinite; opacity:0.85; }
        @keyframes floatEmoji {
            0%,100% { transform:translate(0,0) rotate(0deg); }
            25% { transform:translate(20px,-15px) rotate(20deg); }
            50% { transform:translate(-10px,-25px) rotate(-15deg); }
            75% { transform:translate(15px,10px) rotate(10deg); }
        }

        .section-title { font-size:15px; font-weight:700; color:#fff; margin:18px 4px 12px; display:flex; align-items:center; gap:8px; }
        .section-title .icon { color:#58a6ff; }

        /* ============= PLATFORMS GRID ============= */
        .platforms { display:grid; grid-template-columns:repeat(2, 1fr); gap:10px; margin-bottom:8px; }
        .platform-btn {
            display:flex; align-items:center; gap:10px; padding:12px 14px;
            background:#1c2128; border:1px solid #30363d; border-radius:12px;
            color:#e6e6e6; cursor:pointer; transition:all 0.2s ease;
            font-size:14px; font-weight:600; font-family:'Cairo',sans-serif;
            position:relative; overflow:hidden;
        }
        .platform-btn::before {
            content:''; position:absolute; inset:0; opacity:0; transition:opacity 0.3s;
            background:radial-gradient(circle at center, var(--glow, #1f6feb) 0%, transparent 70%);
        }
        .platform-btn:hover { background:#21262d; border-color:var(--glow, #1f6feb); transform:translateY(-2px); }
        .platform-btn:hover::before { opacity:0.25; }
        .platform-btn:active { transform:scale(0.96); }
        .platform-btn.active {
            background:linear-gradient(135deg, var(--glow, #1f6feb), #161b22);
            border-color:var(--glow, #1f6feb); color:#fff;
            box-shadow:0 0 24px var(--glow, #1f6feb), 0 0 48px rgba(31,111,235,0.4);
            animation:platformPulse 1.4s ease-in-out infinite;
        }
        @keyframes platformPulse {
            0%,100% { box-shadow:0 0 24px var(--glow, #1f6feb), 0 0 48px rgba(31,111,235,0.4); }
            50% { box-shadow:0 0 32px var(--glow, #1f6feb), 0 0 64px rgba(31,111,235,0.6); }
        }
        .platform-btn img { width:32px; height:32px; object-fit:contain; border-radius:8px; background:#fff; padding:2px; position:relative; z-index:2; }
        .platform-btn span { position:relative; z-index:2; }

        /* ============= SELECT & BUTTONS ============= */
        .select-wrap { position:relative; }
        .form-control {
            width:100%; padding:14px 16px; border-radius:10px;
            border:1px solid #30363d; background:#0d1117; color:#e6e6e6;
            outline:none; font-family:'Cairo',sans-serif; font-size:14px; font-weight:600;
            appearance:none; -webkit-appearance:none;
            background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'><path fill='%238b949e' d='M6 9L1 4h10z'/></svg>");
            background-repeat:no-repeat; background-position:left 16px center; padding-left:40px;
        }
        .form-control:focus { border-color:#1f6feb; box-shadow:0 0 0 3px rgba(31,111,235,0.18); }
        .form-control:disabled { opacity:0.5; cursor:not-allowed; }

        .btn-primary {
            width:100%; padding:14px; border:none; border-radius:10px;
            background:linear-gradient(135deg, #238636, #2ea043); color:#fff; font-size:15px; font-weight:700;
            cursor:pointer; margin-top:10px; font-family:'Cairo',sans-serif;
            transition:all 0.2s; box-shadow:0 4px 14px rgba(35,134,54,0.35);
        }
        .btn-primary:hover:not(:disabled) { background:linear-gradient(135deg, #2ea043, #3fb950); transform:translateY(-2px); box-shadow:0 6px 20px rgba(35,134,54,0.5); }
        .btn-primary:active:not(:disabled) { transform:scale(0.98); }
        .btn-primary:disabled { opacity:0.5; cursor:not-allowed; box-shadow:none; }

        .btn-blue {
            width:100%; padding:14px; border:none; border-radius:10px;
            background:linear-gradient(135deg, #1f6feb, #388bfd); color:#fff; font-size:15px; font-weight:700;
            cursor:pointer; margin-top:8px; font-family:'Cairo',sans-serif;
            transition:all 0.2s; box-shadow:0 4px 14px rgba(31,111,235,0.35);
        }
        .btn-blue:hover { background:linear-gradient(135deg, #388bfd, #58a6ff); transform:translateY(-2px); }

        /* ============= NUMBER BOX ============= */
        .number-card {
            background:linear-gradient(135deg, #0d1117, #161b22);
            border:1px solid var(--num-glow, #238636);
            border-radius:14px;
            padding:20px; margin:16px 0; text-align:center;
            box-shadow:0 0 28px var(--num-glow-shadow, rgba(35,134,54,0.3));
            transition:border-color 0.3s, box-shadow 0.3s;
            position:relative; overflow:hidden;
        }
        .number-card::after {
            content:''; position:absolute; top:-50%; left:-50%;
            width:200%; height:200%;
            background:linear-gradient(45deg, transparent 40%, rgba(255,255,255,0.04) 50%, transparent 60%);
            animation:shine 3.5s linear infinite;
            pointer-events:none;
        }
        @keyframes shine { 0%{transform:translateX(-30%) translateY(-30%);} 100%{transform:translateX(30%) translateY(30%);} }
        .number-label { font-size:12px; color:#8b949e; margin-bottom:6px; font-weight:700; }
        .number {
            font-family:'Courier New',monospace; font-size:26px; font-weight:bold;
            color:var(--num-color, #3fb950); letter-spacing:1.5px;
            text-shadow:0 0 12px var(--num-glow, #3fb950);
            animation:numAppear 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        @keyframes numAppear {
            0% { transform:scale(0.5) rotateX(90deg); opacity:0; }
            100% { transform:scale(1) rotateX(0); opacity:1; }
        }
        .number-platform { font-size:13px; color:#8b949e; margin-top:8px; font-weight:600; }
        .copy-btn-mini {
            background:transparent; border:1px solid #30363d; color:#8b949e;
            padding:6px 12px; border-radius:8px; cursor:pointer; font-size:12px; margin-top:10px;
            font-family:'Cairo',sans-serif; font-weight:600;
        }
        .copy-btn-mini:hover { color:#3fb950; border-color:#3fb950; }

        /* ============= OTP TIMER ============= */
        .otp-timer {
            text-align:center; margin:10px 0; padding:10px;
            background:rgba(31,111,235,0.08); border:1px solid #1f6feb;
            border-radius:10px; font-weight:700; font-size:14px;
            color:#58a6ff;
        }
        .otp-timer.urgent { color:#f85149; border-color:#f85149; background:rgba(248,81,73,0.1); animation:timerPulse 1s ease infinite; }
        .otp-timer.expired { color:#8b949e; border-color:#30363d; background:#0d1117; }
        @keyframes timerPulse { 0%,100%{transform:scale(1);} 50%{transform:scale(1.02);} }
        .progress-bar-wrap { height:4px; background:#0d1117; border-radius:4px; overflow:hidden; margin-top:8px; }
        .progress-bar { height:100%; background:linear-gradient(90deg, #1f6feb, #3fb950); transition:width 1s linear, background 0.3s; }

        /* ============= OTP LIST ============= */
        .otp-list { display:flex; flex-direction:column; gap:8px; margin-top:12px; max-height:400px; overflow-y:auto; padding-left:4px; }
        .otp-list::-webkit-scrollbar { width:4px; }
        .otp-list::-webkit-scrollbar-thumb { background:#30363d; border-radius:2px; }
        .otp-item {
            background:#1c2128; border:1px solid #30363d; border-radius:10px;
            padding:12px 14px; display:flex; justify-content:space-between; align-items:center;
            transition:all 0.2s; animation:slideInRight 0.4s ease;
        }
        .otp-item:hover { border-color:#3fb950; transform:translateX(-3px); }
        .otp-item.fresh { border-color:#3fb950; box-shadow:0 0 12px rgba(63,185,80,0.3); }
        @keyframes slideInRight { from{opacity:0; transform:translateX(20px);} to{opacity:1; transform:translateX(0);} }
        .otp-item .otp-code { font-family:'Courier New',monospace; font-size:17px; font-weight:bold; color:#3fb950; letter-spacing:1px; }
        .otp-item .otp-info { font-size:11px; color:#8b949e; margin-top:4px; }
        .otp-item .copy-btn { background:transparent; border:1px solid #30363d; color:#58a6ff; padding:5px 12px; border-radius:6px; cursor:pointer; font-size:11px; font-weight:600; font-family:'Cairo',sans-serif; }
        .otp-item .copy-btn:hover { background:#1f6feb; color:#fff; }

        .empty-state { text-align:center; padding:30px 16px; color:#8b949e; font-size:13px; }
        .empty-state .icon { font-size:36px; margin-bottom:8px; opacity:0.6; }

        /* ============= STATUS BAR ============= */
        .status { background:#1c2128; border:1px solid #30363d; border-radius:10px; padding:12px 16px; text-align:center; margin-top:14px; color:#8b949e; font-size:13px; font-weight:600; }

        /* ============= THEME TOGGLE ============= */
        .theme-toggle { background:transparent; border:1px solid #30363d; color:#8b949e; padding:6px 10px; border-radius:8px; cursor:pointer; font-size:14px; }
        .theme-toggle:hover { color:#58a6ff; border-color:#58a6ff; }

        /* ============= LIGHT MODE ============= */
        body.light { background:#f6f8fa !important; color:#1f2328 !important; }
        body.light .app { background:rgba(255,255,255,0.85) !important; }
        body.light .top-bar { background:rgba(255,255,255,0.95) !important; border-bottom-color:#d0d7de !important; }
        body.light .brand-text, body.light .hero h1, body.light .section-title { color:#1f2328 !important; }
        body.light .hero p, body.light .status, body.light .empty-state { color:#656d76 !important; }
        body.light .platform-btn { background:#f6f8fa; border-color:#d0d7de; color:#1f2328; }
        body.light .platform-btn:hover { background:#eaeef2; }
        body.light .form-control { background:#ffffff; border-color:#d0d7de; color:#1f2328; }
        body.light .otp-item { background:#f6f8fa; border-color:#d0d7de; }
        body.light .otp-item .otp-code { color:#1a7f37; }
        body.light .dropdown-menu { background:#ffffff; border-color:#d0d7de; }
        body.light .dropdown-menu a { color:#1f2328; }
        body.light .status { background:#f6f8fa; border-color:#d0d7de; }
        body.light .number-card { background:#f6f8fa; }
        body.light .number { color:#1a7f37; }

        /* ============= TICKER (شريط إخباري متحرك) ============= */
        .ticker-wrap {
            position:sticky; bottom:0; left:0; right:0; z-index:40;
            background:linear-gradient(90deg, #0d1117, #161b22, #0d1117);
            border-top:1px solid #21262d; padding:8px 0; overflow:hidden;
            box-shadow:0 -4px 20px rgba(0,0,0,0.4);
        }
        .ticker {
            display:inline-block; white-space:nowrap;
            animation:tickerScroll 25s linear infinite;
            color:#58a6ff; font-weight:700; font-size:14px;
            padding-left:100%;
        }
        .ticker span { margin:0 24px; }
        .ticker .accent { color:#3fb950; }
        .ticker .warn { color:#f0b429; }
        .ticker .pulse { animation:textPulse 2s ease infinite; }
        @keyframes tickerScroll { 0%{transform:translateX(0);} 100%{transform:translateX(-100%);} }
        @keyframes textPulse { 0%,100%{opacity:1;} 50%{opacity:0.5;} }

        /* ============= إيموجيات متحركة ============= */
        .emoji-bg-layer {
            position:fixed; top:0; left:0; width:100%; height:100%;
            pointer-events:none; z-index:0; overflow:hidden;
        }
        .emoji-float {
            position:absolute; font-size:24px; opacity:0.5;
            animation:emojiRise linear infinite;
        }
        @keyframes emojiRise {
            0% { transform:translateY(110vh) translateX(0) rotate(0deg); opacity:0; }
            10% { opacity:0.6; }
            90% { opacity:0.6; }
            100% { transform:translateY(-20vh) translateX(60px) rotate(360deg); opacity:0; }
        }

        .footer { text-align:center; padding:14px 16px 8px; color:#484f58; font-size:12px; }

        @media (max-width:380px) {
            .hero h1 { font-size:20px; }
            .platform-btn { font-size:13px; padding:10px 12px; }
            .number { font-size:22px; }
        }
    </style>
</head>
<body>
    <canvas id="matrixCanvas"></canvas>
    <div class="emoji-bg-layer" id="emojiLayer"></div>

    <div class="app">
        <!-- HEADER -->
        <div class="top-bar">
            <div class="brand">
                <div class="brand-icon">🚀</div>
                <div class="brand-text">المطري OTP</div>
            </div>
            <div style="display:flex; gap:6px; position:relative;">
                <button class="theme-toggle" id="themeToggle" onclick="toggleTheme()">🌙</button>
                <button class="menu-btn" onclick="toggleMenu()">☰</button>
                <div class="dropdown-menu" id="contactMenu">
                    <div class="menu-section-title">📞 التواصل معي</div>
                    {% for c in contacts %}
                    <a href="{{ c.link }}" target="_blank"><span class="icon">{{ c.icon }}</span>{{ c.name }}</a>
                    {% endfor %}
                    <div class="menu-section-title">👥 مجموعاتي</div>
                    {% for g in groups %}
                    <a href="{{ g.link }}" target="_blank"><span class="icon">{{ g.icon }}</span>{{ g.name }}</a>
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- MAIN -->
        <div class="main">
            <div class="hero">
                <h1>🚀 موقع المطري OTP</h1>
                <p><span class="floating-emoji" style="position:relative;display:inline-block;animation:floatEmoji 4s ease-in-out infinite;">👑</span> أرقام سحب أكواد مطري <span class="floating-emoji" style="position:relative;display:inline-block;animation:floatEmoji 4s ease-in-out infinite;animation-delay:0.5s;">👑</span></p>
            </div>

            <div class="section-title"><span class="icon">🎯</span> اختر المنصة</div>
            <div class="platforms" id="platformSelector">
                {% for p in platforms_list %}
                <button type="button" class="platform-btn" data-platform="{{ p }}" style="--glow: {{ platform_colors[p] }};">
                    <img src="{{ platform_logos[p] }}" alt="{{ platform_names[p] }}"><span>{{ platform_names[p] }}</span>
                </button>
                {% endfor %}
            </div>

            <div class="section-title"><span class="icon">🌍</span> اختر الدولة</div>
            <div class="select-wrap">
                <select id="country" class="form-control" disabled>
                    <option value="">-- اختر المنصة أولاً --</option>
                </select>
            </div>

            <button class="btn-primary" id="getNumberBtn" onclick="getNumber()" disabled>🚀 جلب رقم</button>
            <button class="btn-blue" id="refreshBtn" onclick="refreshNumber()" disabled>🔄 تبديل</button>

            <div id="numberContainer" style="display:none;">
                <div class="number-card" id="numberCard">
                    <div class="number-label">📱 الرقم المختار</div>
                    <div class="number" id="numberDisplay">+</div>
                    <div class="number-platform" id="numberPlatform"></div>
                    <button class="copy-btn-mini" onclick="copyNumber()">📋 نسخ الرقم</button>
                </div>
                <div class="otp-timer" id="otpTimer" style="display:none;">
                    <span id="timerText">⏱️ صلاحية الكود: <strong id="timerCount">60</strong> ثانية</span>
                    <div class="progress-bar-wrap">
                        <div class="progress-bar" id="progressBar" style="width:100%;"></div>
                    </div>
                </div>
                <div style="display:flex; gap:8px;">
                    <button class="btn-primary" onclick="startMonitoring()">📡 بدء السحب</button>
                    <button class="btn-blue" onclick="stopMonitoring()" style="background:linear-gradient(135deg,#da3633,#b91c1c);">⏹️ إيقاف</button>
                </div>
            </div>

            <div class="section-title" style="margin-top:24px;"><span class="icon">📜</span> الأكواد المسحوبة <span style="margin-right:auto;font-size:12px;color:#8b949e;">(الأحدث أولاً)</span></div>
            <div class="otp-list" id="otpHistory">
                <div class="empty-state">
                    <div class="icon">⏳</div>
                    <div>في انتظار الأكواد...</div>
                </div>
            </div>

            <div class="status" id="status">⚡ اختر المنصة والدولة للبدء</div>
        </div>

        <!-- شريط إخباري متحرك -->
        <div class="ticker-wrap">
            <div class="ticker">
                <span>🚀 المطري OTP</span>
                <span class="accent">⚡ أسرع موقع سحب أكواد</span>
                <span class="warn">👑 صُنع بحب</span>
                <span class="pulse">🔥 أكواد حقيقية</span>
                <span class="accent">📱 كل المنصات</span>
                <span class="warn">🌍 كل الدول</span>
                <span>💎 المطري OTP - أحمد المطري</span>
                <span class="pulse">⚡ جرب الآن!</span>
            </div>
        </div>

        <div class="footer">💎 صُنع بحب ⚡ بواسطة المطري</div>
    </div>

    <!-- أصوات الإشعار (سأضع ملفين: افتراضي + بديل) -->
    <!-- يمكن للمستخدم تبديل الصوت من الزر -->
    <audio id="notifSoundA" preload="auto" src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"></audio>
    <audio id="notifSoundB" preload="auto" src="https://assets.mixkit.co/active_storage/sfx/2354/2354-preview.mp3"></audio>
    <audio id="notifSoundC" preload="auto" src="https://assets.mixkit.co/active_storage/sfx/2702/2702-preview.mp3"></audio>

    <script>
        // ========== بيانات من السيرفر ==========
        const platformLogos = {{ platform_logos | tojson }};
        const platformNames = {{ platform_names | tojson }};
        const platformGradients = {{ platform_gradients | tojson }};
        const platformColors = {{ platform_colors | tojson }};
        const OTP_VALID_SECONDS = {{ otp_seconds | tojson }};
        const OWNER_PHONE = "{{ owner_phone }}";
        const WA_GROUP = "{{ wa_group }}";

        // ========== Matrix Rain (أرقام متساقطة) ==========
        (function initMatrix() {
            try {
                const canvas = document.getElementById('matrixCanvas');
                if (!canvas) return;
                const ctx = canvas.getContext('2d');
                let w, h, cols, drops;
                function resize() {
                    w = canvas.width = window.innerWidth;
                    h = canvas.height = window.innerHeight;
                    cols = Math.floor(w / 18);
                    drops = Array(cols).fill(0).map(()=>Math.random()*-50);
                }
                resize();
                window.addEventListener('resize', resize);
                const chars = '0123456789';
                function draw() {
                    try {
                        ctx.fillStyle = 'rgba(10, 14, 20, 0.08)';
                        ctx.fillRect(0, 0, w, h);
                        ctx.font = '16px monospace';
                        for (let i = 0; i < drops.length; i++) {
                            const text = chars[Math.floor(Math.random()*chars.length)];
                            const brightness = Math.random();
                            if (brightness > 0.95) ctx.fillStyle = '#ffffff';
                            else if (brightness > 0.7) ctx.fillStyle = '#3fb950';
                            else ctx.fillStyle = '#1f6feb';
                            ctx.fillText(text, i*18, drops[i]*18);
                            if (drops[i]*18 > h && Math.random() > 0.975) drops[i] = 0;
                            drops[i]++;
                        }
                    } catch(e) { return; }
                    requestAnimationFrame(draw);
                }
                draw();
            } catch(e) { console.warn('Matrix init failed:', e); }
        })();

        // ========== إيموجيات طايرة بالخلفية ==========
        (function spawnEmojis() {
            try {
                const layer = document.getElementById('emojiLayer');
                if (!layer) return;
                const emojis = ['🚀','⚡','💎','🔑','👑','🎯','🔥','💫','✨','🌟','📱','🌍'];
                setInterval(() => {
                    try {
                        const el = document.createElement('div');
                        el.className = 'emoji-float';
                        el.textContent = emojis[Math.floor(Math.random()*emojis.length)];
                        el.style.left = Math.random()*100 + '%';
                        el.style.fontSize = (16 + Math.random()*16) + 'px';
                        el.style.animationDuration = (8 + Math.random()*8) + 's';
                        layer.appendChild(el);
                        setTimeout(()=>el.remove(), 16000);
                    } catch(e) {}
                }, 1500);
            } catch(e) { console.warn('Emoji init failed:', e); }
        })();

        // ========== القائمة ==========
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

        // ========== ثيم ==========
        function toggleTheme() {
            const isLight = document.body.classList.toggle('light');
            document.getElementById('themeToggle').textContent = isLight ? '☀️' : '🌙';
            localStorage.setItem('theme', isLight ? 'light' : 'dark');
        }
        function loadTheme() {
            if (localStorage.getItem('theme') === 'light') {
                document.body.classList.add('light');
                document.getElementById('themeToggle').textContent = '☀️';
            }
        }
        loadTheme();

        // ========== نسخ ==========
        async function copyNumber() {
            const num = document.getElementById('numberDisplay').textContent;
            await navigator.clipboard.writeText(num);
            const btn = event.target;
            const orig = btn.textContent;
            btn.textContent = '✅ تم النسخ';
            setTimeout(() => btn.textContent = orig, 1500);
        }
        function copyText(text, btn) {
            navigator.clipboard.writeText(text);
            if (btn) {
                const orig = btn.textContent;
                btn.textContent = '✅';
                setTimeout(()=>btn.textContent = orig, 1500);
            }
        }

        // ========== المنصات ==========
        let currentPlatform = '';
        let currentNumber = '';
        let monitorInterval = null;
        let timerInterval = null;
        let timeLeft = OTP_VALID_SECONDS;
        let usedSounds = [false, false, false];
        let soundIdx = 0;

        function pickSound() {
            // يختار الصوت اللي ما استخدمته قبل (عشان كل مرة صوت مختلف)
            for (let i = 0; i < usedSounds.length; i++) {
                if (!usedSounds[i]) {
                    usedSounds[i] = true;
                    soundIdx = i;
                    // بعد فترة يرجع متاح
                    setTimeout(()=>{ usedSounds[i] = false; }, 30000);
                    return i;
                }
            }
            return Math.floor(Math.random() * 3);
        }

        function playNotif() {
            const idx = pickSound();
            const ids = ['notifSoundA','notifSoundB','notifSoundC'];
            const a = document.getElementById(ids[idx]);
            a.currentTime = 0;
            a.volume = 0.7;
            a.play().catch(()=>{});
        }

        function initPlatformSelector() {
            const selector = document.getElementById('platformSelector');
            // أضف event listeners للأزرار الموجودة من السيرفر
            selector.querySelectorAll('.platform-btn').forEach(btn => {
                const platform = btn.getAttribute('data-platform');
                btn.onclick = () => selectPlatform(platform, btn);
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
                document.getElementById('refreshBtn').disabled = true;
                return;
            }
            countrySelect.disabled = true;
            countrySelect.innerHTML = '<option value="">جاري التحميل...</option>';
            const res = await fetch('/api/countries', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({platform:currentPlatform}));
            const data = await res.json();
            let options = '<option value="">-- اختر الدولة --</option>';
            data.forEach(c => { options += `<option value="${c.code}">${c.flag} ${c.name}</option>`; });
            countrySelect.innerHTML = options;
            countrySelect.disabled = false;
        }

        document.getElementById('country').addEventListener('change', function() {
            const has = this.value !== '';
            document.getElementById('getNumberBtn').disabled = !has;
            document.getElementById('refreshBtn').disabled = !has;
        });

        async function getNumber() {
            const country = document.getElementById('country').value;
            if (!currentPlatform || !country) {
                document.getElementById('status').textContent = '⚠️ يرجى اختيار المنصة والدولة';
                return;
            }
            document.getElementById('status').textContent = '⏳ جاري جلب رقم...';
            const res = await fetch('/api/get_number', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({platform:currentPlatform, country})});
            const data = await res.json();
            if (data.number) {
                showNumber(data.number);
                document.getElementById('status').textContent = '✅ الرقم جاهز! اضغط بدء السحب';
            } else {
                document.getElementById('status').textContent = '❌ لا توجد أرقام متاحة';
            }
        }

        async function refreshNumber() {
            const country = document.getElementById('country').value;
            if (!currentPlatform || !country) return;
            document.getElementById('status').textContent = '⏳ جاري التبديل...';
            const res = await fetch('/api/get_number', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({platform:currentPlatform, country})});
            const data = await res.json();
            if (data.number && data.number !== currentNumber) {
                showNumber(data.number);
                document.getElementById('status').textContent = '🔄 تم التبديل!';
            }
        }

        function showNumber(num) {
            currentNumber = num;
            // تلوين بطاقة الرقم بلون المنصة
            const card = document.getElementById('numberCard');
            const color = platformColors[currentPlatform] || '#3fb950';
            card.style.setProperty('--num-glow', color);
            card.style.setProperty('--num-color', color);
            card.style.setProperty('--num-glow-shadow', color + '55');
            // عرض الرقم بطريقة مميزة
            const display = document.getElementById('numberDisplay');
            display.textContent = '';
            const full = '+' + num;
            // أنيميشن ظهور الأرقام واحد واحد
            [...full].forEach((ch, i) => {
                const span = document.createElement('span');
                span.textContent = ch;
                span.style.display = 'inline-block';
                span.style.opacity = '0';
                span.style.transform = 'translateY(-20px) rotate(20deg)';
                span.style.transition = `all 0.4s cubic-bezier(0.34,1.56,0.64,1) ${i*0.05}s`;
                display.appendChild(span);
                setTimeout(() => {
                    span.style.opacity = '1';
                    span.style.transform = 'translateY(0) rotate(0)';
                }, 50);
            });
            document.getElementById('numberPlatform').textContent = '🎯 ' + (platformNames[currentPlatform] || '');
            document.getElementById('numberContainer').style.display = 'block';
        }

        function startTimer() {
            const timerEl = document.getElementById('otpTimer');
            const countEl = document.getElementById('timerCount');
            const bar = document.getElementById('progressBar');
            timerEl.style.display = 'block';
            timerEl.classList.remove('expired');
            timeLeft = OTP_VALID_SECONDS;
            countEl.textContent = timeLeft;
            bar.style.width = '100%';
            bar.style.background = 'linear-gradient(90deg, #1f6feb, #3fb950)';
            if (timerInterval) clearInterval(timerInterval);
            timerInterval = setInterval(() => {
                timeLeft--;
                countEl.textContent = timeLeft;
                const pct = (timeLeft / OTP_VALID_SECONDS) * 100;
                bar.style.width = pct + '%';
                if (timeLeft <= 15) {
                    timerEl.classList.add('urgent');
                    bar.style.background = 'linear-gradient(90deg, #f85149, #f0b429)';
                }
                if (timeLeft <= 0) {
                    clearInterval(timerInterval);
                    timerInterval = null;
                    timerEl.classList.remove('urgent');
                    timerEl.classList.add('expired');
                    countEl.textContent = '0';
                    document.getElementById('status').textContent = '⏰ انتهت صلاحية الكود - أعد جلب رقم';
                    stopMonitoring();
                }
            }, 1000);
        }

        function startMonitoring() {
            if (!currentNumber) return;
            if (monitorInterval) clearInterval(monitorInterval);
            startTimer();
            document.getElementById('status').textContent = '🔄 جاري المراقبة...';
            monitorInterval = setInterval(() => {
                fetch('/api/get_otp', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({number:currentNumber})})
                .then(res => res.json()).then(data => {
                    if (data.otp) {
                        const now = new Date().toLocaleString('ar-YE', {timeZone:'Asia/Aden'});
                        addOtpToHistory(currentNumber, data.otp, now, currentPlatform);
                        document.getElementById('status').textContent = '✅ تم العثور على كود!';
                        playNotif();
                        if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }
                        document.getElementById('otpTimer').classList.add('expired');
                        stopMonitoring();
                    }
                });
            }, 5000);
        }

        function stopMonitoring() {
            if (monitorInterval) { clearInterval(monitorInterval); monitorInterval = null; }
            if (!document.getElementById('status').textContent.includes('كود')) {
                document.getElementById('status').textContent = '⏹️ تم الإيقاف';
            }
        }

        function addOtpToHistory(number, otp, timestamp, platform) {
            const container = document.getElementById('otpHistory');
            if (container.querySelector('.empty-state')) container.innerHTML = '';
            const div = document.createElement('div');
            div.className = 'otp-item fresh';
            const color = platformColors[platform] || '#3fb950';
            const icon = platformLogos[platform] || '';
            div.innerHTML = `
                <div style="flex:1;">
                    <div class="otp-code" style="color:${color};text-shadow:0 0 8px ${color};">🔑 ${otp}</div>
                    <div class="otp-info">📞 +${number}  •  🕒 ${timestamp}  •  ${icon} ${platformNames[platform] || ''}</div>
                </div>
                <button class="copy-btn">نسخ</button>
            `;
            const btn = div.querySelector('.copy-btn');
            btn.onclick = () => copyText(otp, btn);
            container.prepend(div);
            if (container.children.length > 30) container.removeChild(container.lastChild);
            // إزالة الـ fresh بعد فترة
            setTimeout(()=>div.classList.remove('fresh'), 4000);
        }

        // تحميل أولي للأكواد الموجودة
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
                            <div style="flex:1;">
                                <div class="otp-code" style="color:${color};text-shadow:0 0 8px ${color};">🔑 ${item.otp}</div>
                                <div class="otp-info">📞 ${item.number}  •  🕒 ${item.timestamp}  •  ${icon} ${pname}</div>
                            </div>
                            <button class="copy-btn">نسخ</button>
                        `;
                        const btn = div.querySelector('.copy-btn');
                        btn.onclick = () => copyText(item.otp, btn);
                        container.appendChild(div);
                    });
                }
            } catch(e) { /* ignore */ }
        }

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

@app.route('/')
def home():
    return render_template_string(
        main_html,
        owner_link=OWNER_LINK,
        wa_group=WHATSAPP_GROUP_LINK,
        owner_phone=OWNER_PHONE,
        platform_logos=PLATFORM_LOGOS,
        platform_logos_small=PLATFORM_LOGOS,
        platform_names=platform_names,
        platform_gradients=PLATFORM_GRADIENTS,
        platform_colors=platform_colors,
        otp_seconds=OTP_VALID_SECONDS,
        contacts=get_contacts(),
        groups=get_groups(),
        platforms_list=list(platform_names.keys())
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
    # جلب أحدث كود للرقم خلال آخر دقيقتين فقط
    c.execute("SELECT otp FROM otp_logs WHERE number=? AND timestamp >= datetime('now', '-2 minutes') ORDER BY id DESC LIMIT 1", (num,))
    row = c.fetchone()
    if not row:
        # fallback: أي كود حديث للرقم
        c.execute("SELECT otp FROM otp_logs WHERE number=? ORDER BY id DESC LIMIT 1", (num,))
        row = c.fetchone()
    conn.close()
    return jsonify({'otp': row[0] if row else None})

# ========== API جميع الأكواد (مع caching) ==========
_otp_cache = {'data': None, 'time': 0}
CACHE_DURATION = 30

@app.route('/api/all_otps', methods=['GET'])
def api_all_otps():
    now = time.time()
    if _otp_cache['data'] is not None and (now - _otp_cache['time']) < CACHE_DURATION:
        return jsonify(_otp_cache['data'])
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, number, otp, timestamp, platform FROM otp_logs ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    result = [{
        'id': r[0], 'number': r[1], 'otp': r[2], 'timestamp': r[3], 'platform': r[4] or 'Unknown'
    } for r in rows]
    _otp_cache['data'] = result
    _otp_cache['time'] = now
    return jsonify(result)

# ========== API إدارة جهات الاتصال والمجموعات ==========
@app.route('/api/contacts', methods=['GET', 'POST'])
def api_contacts():
    if request.method == 'POST':
        data = request.json
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO contacts (name, link, icon) VALUES (?, ?, ?)",
                  (data.get('name'), data.get('link'), data.get('icon', '📞')))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})
    return jsonify(get_contacts())

@app.route('/api/groups', methods=['GET', 'POST'])
def api_groups():
    if request.method == 'POST':
        data = request.json
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO groups (name, link, icon) VALUES (?, ?, ?)",
                  (data.get('name'), data.get('link'), data.get('icon', '👥')))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})
    return jsonify(get_groups())

# ========== مراقب القناة (نفس منطق الكود الأصلي) ==========
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
                                "whatsapp": ["wa", "whatsapp", "واتساب"],
                                "facebook": ["fb", "facebook", "فيسبوك"],
                                "telegram": ["tg", "telegram", "تيليجرام", "تلجرام"],
                                "tiktok": ["tt", "tiktok", "تيك توك"],
                                "instagram": ["ig", "instagram", "انستقرام"],
                                "snapchat": ["sc", "snapchat", "سناب"],
                                "google": ["gg", "google", "جوجل"],
                                "twitter": ["tw", "twitter", "تويتر", "x.com"]
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
                                # تخزين الرقم كامل (نزيل آخر 4 بس للتوافق)
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
                                # مسح الكاش
                                _otp_cache['data'] = None
                                
        except Exception as e:
            print(f"❌ خطأ: {e}")
        time.sleep(5)

threading.Thread(target=monitor_channel, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
