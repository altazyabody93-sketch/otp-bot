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
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, username TEXT, first_name TEXT, last_name TEXT, join_date TEXT)''')
    conn.commit()
    conn.close()
init_db()

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

# ========== دوال الإحصائيات ==========
def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # إجمالي الأكواد
    c.execute("SELECT COUNT(*) FROM otp_logs")
    total_otps = c.fetchone()[0]
    
    # أكواد اليوم
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM otp_logs WHERE timestamp LIKE ?", (today + '%',))
    today_otps = c.fetchone()[0]
    
    # عدد المستخدمين
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    # عدد الدول
    c.execute("SELECT COUNT(DISTINCT country_code) FROM combos")
    total_countries = c.fetchone()[0]
    
    conn.close()
    return {
        'total_otps': total_otps,
        'today_otps': today_otps,
        'total_users': total_users,
        'total_countries': total_countries
    }

def get_last_7_days_otps():
    """أكواد آخر 7 أيام للرسم البياني"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    data = []
    for i in range(6, -1, -1):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        c.execute("SELECT COUNT(*) FROM otp_logs WHERE timestamp LIKE ?", (date + '%',))
        count = c.fetchone()[0]
        data.append({'date': date, 'count': count})
    conn.close()
    return data

# ========== دوال المستخدم ==========
def save_user(user_id, username="", first_name="", last_name=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE user_id=?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, username, first_name, last_name, join_date) VALUES (?, ?, ?, ?, ?)",
                  (user_id, username, first_name, last_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    conn.close()

# ========== أيقونات SVG ==========
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

# ========== قائمة الدول الكاملة ==========
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

# ========== HTML الجديد (مع كل الميزات) ==========
main_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 موقع المطري OTP</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        :root {
            --bg: #0a0e1a;
            --container-bg: rgba(17, 24, 39, 0.85);
            --text: #fff;
            --border: rgba(139, 92, 246, 0.3);
            --glow: #00ffc8;
        }
        body.dark-mode {
            --bg: #f0f0f0;
            --container-bg: rgba(255, 255, 255, 0.85);
            --text: #111;
            --border: rgba(0, 0, 0, 0.2);
            --glow: #0088cc;
        }
        html, body { font-family:'Cairo',sans-serif; background:var(--bg); color:var(--text); transition:0.3s; }
        #canvas { position:fixed; top:0; left:0; width:100%; height:100%; z-index:-1; }
        .container { max-width:500px; margin:20px auto; background:var(--container-bg); backdrop-filter:blur(20px); border-radius:30px; padding:25px; border:1px solid var(--border); box-shadow:0 8px 32px rgba(0,0,0,0.3); position:relative; z-index:1; }
        .header h1 { font-size:28px; font-weight:900; background:linear-gradient(90deg,#00ffc8,#8b5cf6,#ec4899,#00ffc8); background-size:300%; -webkit-background-clip:text; -webkit-text-fill-color:transparent; animation:glow 4s infinite; text-align:center; }
        @keyframes glow { 0%,100%{background-position:0%} 50%{background-position:100%} }
        .section-title { display:flex; align-items:center; gap:10px; margin:20px 0 10px; color:var(--glow); font-weight:700; }
        .section-title::after { content:''; flex:1; height:2px; background:linear-gradient(90deg,var(--glow),transparent); }
        .platform-selector { display:grid; grid-template-columns:repeat(2,1fr); gap:10px; }
        .platform-btn { display:flex; align-items:center; gap:10px; padding:12px; border-radius:14px; border:2px solid rgba(255,255,255,0.1); background:rgba(31,41,55,0.7); color:var(--text); cursor:pointer; transition:0.3s; font-weight:700; position:relative; overflow:hidden; }
        .platform-btn img { width:36px; height:36px; border-radius:10px; background:#fff; padding:3px; }
        .platform-btn.active { border-color:var(--glow); box-shadow:0 0 25px var(--glow); transform:scale(1.02); }
        .form-control { width:100%; padding:14px; border-radius:14px; border:2px solid rgba(255,255,255,0.1); background:rgba(31,41,55,0.7); color:var(--text); font-family:'Cairo'; font-size:15px; }
        .btn-primary { width:100%; padding:16px; border:none; border-radius:16px; background:linear-gradient(135deg,#00ff88,#00d2ff); color:#000; font-weight:900; font-size:17px; cursor:pointer; margin-top:10px; box-shadow:0 0 25px rgba(0,255,136,0.4); transition:0.3s; animation:neonPulse 2s infinite; }
        @keyframes neonPulse { 0%,100%{box-shadow:0 0 15px rgba(0,255,136,0.4)} 50%{box-shadow:0 0 30px rgba(0,255,136,0.7)} }
        .btn-primary:hover { transform:translateY(-3px); }
        .btn-blue { width:100%; padding:16px; border:none; border-radius:16px; background:linear-gradient(135deg,#3b82f6,#1d4ed8); color:#fff; font-weight:800; cursor:pointer; margin-top:8px; }
        .btn-danger { background:linear-gradient(135deg,#ef4444,#b91c1c)!important; }
        .number-box { display:flex; align-items:center; justify-content:space-between; background:linear-gradient(135deg,#000,#0f172a); border:2px solid var(--glow); border-radius:16px; padding:16px; margin:15px 0; box-shadow:0 0 30px rgba(0,255,136,0.3); animation:glowPulse 2s infinite; }
        @keyframes glowPulse { 0%,100%{box-shadow:0 0 30px rgba(0,255,136,0.3)} 50%{box-shadow:0 0 50px rgba(0,255,136,0.6)} }
        .number-box .number { font-family:'Courier New'; font-size:22px; color:var(--glow); text-align:center; flex:1; }
        .copy-number-btn { background:rgba(0,255,136,0.15); border:1px solid var(--glow); border-radius:10px; padding:8px 12px; color:var(--glow); cursor:pointer; }
        .otp-container { max-height:400px; overflow-y:auto; border:1px solid var(--border); border-radius:16px; padding:12px; background:rgba(0,0,0,0.2); margin-top:15px; }
        .otp-item { background:linear-gradient(135deg,#0f172a,#1e293b); border:1px solid var(--glow); border-radius:14px; padding:14px; margin-bottom:10px; animation:slideIn 0.4s; transition:0.3s; }
        .otp-item:hover { transform:scale(1.01); box-shadow:0 0 20px rgba(0,255,136,0.2); }
        @keyframes slideIn { from{opacity:0;transform:translateX(30px)} to{opacity:1;transform:translateX(0)} }
        .otp-item .copy-btn { background:rgba(0,255,136,0.2); border:1px solid var(--glow); border-radius:8px; padding:4px 12px; color:var(--glow); cursor:pointer; }
        .otp-item .info { color:#94a3b8; font-size:12px; display:block; margin-top:6px; }
        .stats-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:10px; margin:15px 0; }
        .stat-card { background:rgba(31,41,55,0.6); border-radius:14px; padding:12px; text-align:center; border:1px solid var(--border); }
        .stat-card .num { font-size:24px; font-weight:900; color:var(--glow); }
        .stat-card .label { font-size:12px; color:#94a3b8; }
        .filter-buttons { display:flex; gap:8px; flex-wrap:wrap; margin:10px 0; }
        .filter-btn { padding:6px 14px; border-radius:20px; border:1px solid var(--border); background:transparent; color:var(--text); cursor:pointer; transition:0.3s; font-size:13px; }
        .filter-btn.active { background:var(--glow); color:#000; border-color:var(--glow); }
        .mode-toggle { position:fixed; top:15px; left:15px; z-index:999; background:var(--container-bg); border:1px solid var(--border); border-radius:30px; padding:10px 16px; color:var(--text); cursor:pointer; backdrop-filter:blur(10px); font-size:20px; }
        .search-box { display:flex; gap:8px; margin:10px 0; }
        .search-box input { flex:1; padding:10px; border-radius:12px; border:2px solid var(--border); background:rgba(31,41,55,0.7); color:var(--text); font-family:'Cairo'; }
        .search-box button { padding:10px 18px; border-radius:12px; border:none; background:var(--glow); color:#000; font-weight:700; cursor:pointer; }
        .countdown { font-size:12px; color:#94a3b8; margin-top:4px; }
        @media (max-width:480px) { .container { margin:10px; padding:18px; } .stats-grid { grid-template-columns:1fr 1fr; } }
    </style>
</head>
<body>
    <canvas id="canvas"></canvas>
    <button class="mode-toggle" onclick="toggleMode()">🌙</button>
    
    <div class="container">
        <div class="header"><h1>🚀 موقع المطري OTP</h1></div>
        
        <!-- الإحصائيات -->
        <div class="stats-grid" id="statsGrid">
            <div class="stat-card"><div class="num" id="totalOtps">0</div><div class="label">📊 إجمالي الأكواد</div></div>
            <div class="stat-card"><div class="num" id="todayOtps">0</div><div class="label">📅 أكواد اليوم</div></div>
            <div class="stat-card"><div class="num" id="totalUsers">0</div><div class="label">👥 المستخدمين</div></div>
            <div class="stat-card"><div class="num" id="totalCountries">0</div><div class="label">🌍 الدول</div></div>
        </div>
        
        <!-- الرسم البياني -->
        <div style="margin:15px 0; background:rgba(0,0,0,0.2); border-radius:14px; padding:10px;">
            <canvas id="chart" height="120"></canvas>
        </div>
        
        <!-- اختيار المنصة والدولة -->
        <div class="section-title">🎯 اختر المنصة</div>
        <div class="platform-selector" id="platformSelector"></div>
        
        <div class="section-title">🌍 اختر الدولة</div>
        <select id="country" class="form-control" disabled><option>🚀 -- اختر المنصة أولاً --</option></select>
        
        <button class="btn-primary" id="getNumberBtn" onclick="getNumber()" disabled>🚀 جلب رقم</button>
        <button class="btn-blue" id="refreshBtn" onclick="refreshNumber()" disabled>🔄 تبديل</button>
        
        <div id="numberContainer" style="display:none;">
            <div class="number-box">
                <button class="copy-number-btn" onclick="copyNumber()">📋</button>
                <div class="number" id="numberDisplay">+</div>
            </div>
            <div style="display:flex;gap:10px;">
                <button class="btn-primary" onclick="startMonitoring()">📡 بدء السحب</button>
                <button class="btn-blue btn-danger" onclick="stopMonitoring()">⏹️ إيقاف</button>
            </div>
        </div>
        
        <!-- بحث وتصفية -->
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="🔍 بحث عن كود..." oninput="filterOtps()">
            <button onclick="filterOtps()">بحث</button>
        </div>
        <div class="filter-buttons" id="filterButtons">
            <button class="filter-btn active" data-platform="all" onclick="filterByPlatform('all')">الكل</button>
        </div>
        
        <!-- الأكواد -->
        <div class="otp-container" id="otpHistory">
            <div style="text-align:center;color:#64748b;padding:30px;">⏳ في انتظار الأكواد...</div>
        </div>
        
        <div class="status" id="status" style="margin-top:15px;padding:12px;text-align:center;background:rgba(31,41,55,0.5);border-radius:14px;color:#94a3b8;">⚡ اختر المنصة والدولة للبدء</div>
        <div style="text-align:center;margin-top:20px;color:#64748b;font-size:12px;">💎 صُنع بحب بواسطة المطري</div>
    </div>

    <script>
        // ========== النجوم ==========
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        let W,H,stars=[];
        function resize(){ W=canvas.width=window.innerWidth; H=canvas.height=window.innerHeight; }
        resize(); window.addEventListener('resize',resize);
        for(let i=0;i<200;i++) stars.push({x:Math.random()*W,y:Math.random()*H,r:Math.random()*1.5+0.5,s:Math.random()*0.5+0.2,o:Math.random()*0.5+0.3,t:Math.random()*0.02+0.01});
        function drawStars(){ ctx.clearRect(0,0,W,H); stars.forEach(s=>{ s.x+=s.s*0.1; if(s.x>W)s.x=0; const o=s.o+Math.sin(Date.now()*s.t)*0.2; ctx.beginPath(); ctx.arc(s.x,s.y,s.r,0,Math.PI*2); ctx.fillStyle=`rgba(255,255,255,${Math.max(0,Math.min(1,o))})`; ctx.fill(); }); requestAnimationFrame(drawStars); }
        drawStars();

        // ========== البيانات ==========
        const platformLogos = {{ platform_logos | tojson }};
        const platformGradients = {{ platform_gradients | tojson }};
        const platformNames = {{ platform_names | tojson }};
        let currentPlatform='', currentNumber='', monitorInterval=null, allOtps=[], currentFilter='all';

        // ========== الإحصائيات ==========
        async function loadStats() {
            const res = await fetch('/api/stats');
            const data = await res.json();
            document.getElementById('totalOtps').textContent = data.total_otps;
            document.getElementById('todayOtps').textContent = data.today_otps;
            document.getElementById('totalUsers').textContent = data.total_users;
            document.getElementById('totalCountries').textContent = data.total_countries;
        }
        loadStats();

        // ========== الرسم البياني ==========
        let chart;
        async function loadChart() {
            const res = await fetch('/api/chart');
            const data = await res.json();
            const ctx = document.getElementById('chart').getContext('2d');
            if(chart) chart.destroy();
            chart = new Chart(ctx, {
                type: 'bar',
                data: { labels: data.map(d=>d.date), datasets: [{ label: 'الأكواد', data: data.map(d=>d.count), backgroundColor: '#00ffc8', borderRadius: 6 }] },
                options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' } }, x: { grid: { display: false } } } }
            });
        }
        loadChart();

        // ========== المنصات ==========
        function initPlatforms() {
            const sel = document.getElementById('platformSelector');
            sel.innerHTML = '';
            Object.keys(platformNames).forEach(p => {
                const btn = document.createElement('button');
                btn.className = 'platform-btn';
                btn.onclick = (e) => selectPlatform(p, e);
                const g = platformGradients[p];
                const c = g.match(/#[0-9A-F]{6}/gi)?.[0] || '#00ffc8';
                btn.style.setProperty('--bg-gradient', g);
                btn.style.setProperty('--glow-color', c + '80');
                btn.innerHTML = `<img src="${platformLogos[p]}" alt="${platformNames[p]}"><span>${platformNames[p]}</span>`;
                sel.appendChild(btn);
            });
        }

        function selectPlatform(platform, event) {
            currentPlatform = platform;
            document.querySelectorAll('.platform-btn').forEach(b=>b.classList.remove('active'));
            (event.currentTarget || event.target.closest('.platform-btn')).classList.add('active');
            loadCountries();
        }

        async function loadCountries() {
            const sel = document.getElementById('country');
            if (!currentPlatform) { sel.innerHTML='<option>🚀 -- اختر المنصة أولاً --</option>'; sel.disabled=true; return; }
            sel.disabled=true; sel.innerHTML='<option>⏳ جاري التحميل...</option>';
            const res = await fetch('/api/countries', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({platform:currentPlatform})});
            const data = await res.json();
            sel.innerHTML = '<option value="">🌍 -- اختر الدولة --</option>' + data.map(c=>`<option value="${c.code}">${c.flag} ${c.name}</option>`).join('');
            sel.disabled=false;
        }

        document.getElementById('country').addEventListener('change', function() {
            const has = this.value !== '';
            document.getElementById('getNumberBtn').disabled = !has;
            document.getElementById('refreshBtn').disabled = !has;
        });

        // ========== جلب الرقم ==========
        async function getNumber() {
            const platform = currentPlatform, country = document.getElementById('country').value;
            if (!platform || !country) return;
            document.getElementById('status').innerHTML = '⏳ جاري جلب رقم...';
            const res = await fetch('/api/get_number', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({platform, country})});
            const data = await res.json();
            if (data.number) {
                currentNumber = data.number;
                document.getElementById('numberDisplay').textContent = '+' + data.number;
                document.getElementById('numberContainer').style.display = 'block';
                document.getElementById('status').innerHTML = '✅ الرقم جاهز!';
                showToast('🎉 تم جلب رقم جديد!');
            } else {
                document.getElementById('status').innerHTML = '❌ لا توجد أرقام متاحة.';
            }
        }

        async function refreshNumber() {
            const platform = currentPlatform, country = document.getElementById('country').value;
            if (!platform || !country) return;
            document.getElementById('status').innerHTML = '⏳ جاري تبديل الرقم...';
            const res = await fetch('/api/get_number', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({platform, country})});
            const data = await res.json();
            if (data.number && data.number !== currentNumber) {
                currentNumber = data.number;
                document.getElementById('numberDisplay').textContent = '+' + data.number;
                document.getElementById('status').innerHTML = '🔄 تم تبديل الرقم!';
                showToast('🔄 تم التبديل!');
            }
        }

        // ========== الأكواد ==========
        function addOtpToHistory(number, otp, timestamp, platform) {
            const container = document.getElementById('otpHistory');
            if (container.children.length === 1 && container.textContent.includes('في انتظار')) container.innerHTML = '';
            const div = document.createElement('div');
            div.className = 'otp-item';
            div.dataset.platform = platform || 'غير معروف';
            const countdown = 60;
            div.innerHTML = `
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <strong style="color:#00ffc8;">🔑 ${otp}</strong>
                    <button class="copy-btn" onclick="copyText('${otp}')">📋 نسخ</button>
                </div>
                <span class="info">📞 +${number}  •  🕒 ${timestamp}  •  📱 ${platform || 'غير معروف'}</span>
                <div class="countdown" id="countdown_${Date.now()}">⏳ 60 ثانية متبقية</div>
            `;
            container.prepend(div);
            if (container.children.length > 25) container.removeChild(container.lastChild);
            showToast('🎉 كود جديد: ' + otp);
            
            // تنبيه صوتي
            const audio = new Audio('data:audio/wav;base64,UklGRnoAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoAAACBhYqFhYW...');
            audio.play().catch(()=>{});
            
            // عداد تنازلي
            let sec = 60;
            const cd = div.querySelector('.countdown');
            const interval = setInterval(() => {
                sec--;
                cd.textContent = `⏳ ${sec} ثانية متبقية`;
                if (sec <= 0) { clearInterval(interval); cd.textContent = '⏳ انتهى الوقت'; }
            }, 1000);
            
            // تحديث الفلاتر
            updateFilterButtons();
            allOtps.push({otp, number, timestamp, platform});
        }

        function copyText(text) { navigator.clipboard.writeText(text); showToast('✅ تم نسخ الكود!'); }
        function showToast(msg) {
            const t = document.createElement('div');
            t.textContent = msg;
            t.style.cssText = 'position:fixed;top:20px;left:50%;transform:translateX(-50%);background:linear-gradient(135deg,#00ff88,#00d2ff);color:#000;padding:14px 28px;border-radius:14px;font-weight:bold;z-index:9999;box-shadow:0 0 30px rgba(0,255,136,0.6);animation:slideIn 0.4s;';
            document.body.appendChild(t);
            setTimeout(() => t.remove(), 2500);
        }

        // ========== بحث وتصفية ==========
        function filterOtps() {
            const q = document.getElementById('searchInput').value.toLowerCase();
            const items = document.querySelectorAll('.otp-item');
            items.forEach(el => {
                const text = el.textContent.toLowerCase();
                el.style.display = text.includes(q) ? '' : 'none';
            });
        }

        function filterByPlatform(platform) {
            currentFilter = platform;
            document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
            document.querySelector(`.filter-btn[data-platform="${platform}"]`).classList.add('active');
            const items = document.querySelectorAll('.otp-item');
            items.forEach(el => {
                if (platform === 'all') { el.style.display = ''; return; }
                el.style.display = el.dataset.platform === platform ? '' : 'none';
            });
        }

        function updateFilterButtons() {
            const container = document.getElementById('filterButtons');
            const platforms = [...new Set(allOtps.map(o=>o.platform).filter(Boolean))];
            container.innerHTML = `<button class="filter-btn active" data-platform="all" onclick="filterByPlatform('all')">الكل</button>`;
            platforms.forEach(p => {
                container.innerHTML += `<button class="filter-btn" data-platform="${p}" onclick="filterByPlatform('${p}')">${p}</button>`;
            });
        }

        // ========== المراقبة ==========
        function startMonitoring() {
            if (!currentNumber) return;
            if (monitorInterval) clearInterval(monitorInterval);
            document.getElementById('status').innerHTML = '🔄 بدأ السحب التلقائي...';
            monitorInterval = setInterval(() => {
                fetch('/api/get_otp', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({number:currentNumber})})
                .then(res => res.json()).then(data => {
                    if (data.otp) {
                        const now = new Date().toLocaleString('ar-YE', {timeZone: 'Asia/Aden'});
                        addOtpToHistory(currentNumber, data.otp, now, data.platform || 'غير معروف');
                        document.getElementById('status').innerHTML = '✅ تم العثور على كود!';
                        stopMonitoring();
                    }
                });
            }, 5000);
            showToast('📡 بدأ المراقبة!');
        }

        function stopMonitoring() {
            if (monitorInterval) { clearInterval(monitorInterval); monitorInterval = null; }
            document.getElementById('status').innerHTML = '⏹️ تم إيقاف السحب.';
        }

        // ========== وضع ليلي/نهاري ==========
        function toggleMode() {
            document.body.classList.toggle('dark-mode');
            const btn = document.querySelector('.mode-toggle');
            btn.textContent = document.body.classList.contains('dark-mode') ? '☀️' : '🌙';
        }

        // ========== تحميل الأكواد القديمة ==========
        async function loadOldOtps() {
            const res = await fetch('/api/old_otps');
            const data = await res.json();
            data.forEach(o => {
                const container = document.getElementById('otpHistory');
                if (container.children.length === 1 && container.textContent.includes('في انتظار')) container.innerHTML = '';
                const div = document.createElement('div');
                div.className = 'otp-item';
                div.dataset.platform = o.platform || 'غير معروف';
                div.innerHTML = `
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                        <strong style="color:#00ffc8;">🔑 ${o.otp}</strong>
                        <button class="copy-btn" onclick="copyText('${o.otp}')">📋 نسخ</button>
                    </div>
                    <span class="info">📞 +${o.number}  •  🕒 ${o.timestamp}  •  📱 ${o.platform || 'غير معروف'}</span>
                `;
                container.appendChild(div);
                allOtps.push(o);
            });
            updateFilterButtons();
        }
        loadOldOtps();

        // ========== بدء ==========
        initPlatforms();
    </script>
</body>
</html>
"""

# ========== Routes جديدة ==========
@app.route('/api/stats')
def api_stats():
    return jsonify(get_stats())

@app.route('/api/chart')
def api_chart():
    return jsonify(get_last_7_days_otps())

@app.route('/api/old_otps')
def api_old_otps():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT number, otp, timestamp, platform FROM otp_logs ORDER BY id DESC LIMIT 30")
    rows = c.fetchall()
    conn.close()
    return jsonify([{'number': r[0], 'otp': r[1], 'timestamp': r[2], 'platform': r[3]} for r in rows])

@app.route('/api/get_otp', methods=['POST'])
def api_get_otp():
    num = request.json.get('number')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT otp, platform FROM otp_logs WHERE number LIKE ? ORDER BY id DESC LIMIT 1", (f"%{num[-4:]}",))
    row = c.fetchone()
    conn.close()
    return jsonify({'otp': row[0] if row else None, 'platform': row[1] if row else None})

@app.route('/')
def home():
    return render_template_string(main_html, platform_logos=PLATFORM_LOGOS, platform_logos_small=PLATFORM_LOGOS, platform_names=platform_names, platform_gradients=PLATFORM_GRADIENTS)

# ========== بقية الـ Routes (admin, etc) ==========
# ... (نفس الكود القديم للـ admin و monitor_channel)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)