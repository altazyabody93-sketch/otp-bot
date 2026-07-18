# ===========================================
# 🚀 موقع المطري OTP - التطبيق الرئيسي
# ===========================================
# إعادة بناء شاملة مع لوحة تحكم متكاملة
# ===========================================

from flask import Flask, request, render_template, jsonify, redirect, url_for, session, flash
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
app.secret_key = os.urandom(24)
DB_PATH = "bot.db"

# ===========================================
# 📱 التوكنات المطلوبة
# ===========================================
TELEGRAM_BOT_TOKEN = "8814038881:AAGyuACUYA4YPKlJQhAyUMkpRNiV0u1gNuU"
NOTIFY_BOT_TOKEN = "8845420882:AAHZ-7qhCL3_ddDT3am4zWNtBRBy3mVDgws"
CHANNEL_USERNAME = "@jsjsgsjsvh"

# ===========================================
# 🗄️ قاعدة البيانات
# ===========================================
def init_db():
    """إنشاء جداول قاعدة البيانات"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # جدول الكومبوهات (منصات + دول + أرقام)
    c.execute('''CREATE TABLE IF NOT EXISTS combos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        country_code TEXT NOT NULL,
        country_name TEXT,
        country_flag TEXT,
        numbers TEXT,
        sort_order INTEGER DEFAULT 0,
        UNIQUE(platform, country_code)
    )''')
    
    # جدول الأكواد المسحوبة
    c.execute('''CREATE TABLE IF NOT EXISTS otp_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        number TEXT,
        otp TEXT,
        timestamp TEXT,
        platform TEXT
    )''')
    
    # جدول الإعدادات
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE,
        value TEXT
    )''')
    
    # جدول المستخدمين
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE,
        created_at TEXT,
        banned INTEGER DEFAULT 0,
        codes_count INTEGER DEFAULT 0
    )''')
    
    # جدول الإعلانات
    c.execute('''CREATE TABLE IF NOT EXISTS ads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        content TEXT,
        link TEXT,
        button_text TEXT,
        active INTEGER DEFAULT 1,
        created_at TEXT
    )''')
    
    # جدول سجلات الأدمن
    c.execute('''CREATE TABLE IF NOT EXISTS admin_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        details TEXT,
        timestamp TEXT
    )''')
    
    # جدول النسخ الاحتياطية
    c.execute('''CREATE TABLE IF NOT EXISTS backups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        data TEXT,
        created_at TEXT
    )''')
    
    conn.commit()
    conn.close()
    
    # إضافة الإعدادات الافتراضية
    init_default_settings()

def init_default_settings():
    """إضافة الإعدادات الافتراضية"""
    defaults = {
        "site_title": "🚀 موقع المطري OTP 🚀",
        "site_description": "أرقام واتساب سحب أكواد تطوير مطري 👑",
        "btn_get_number": "🚀 جلب رقم",
        "btn_switch": "🔄 تبديل",
        "btn_start": "📡 بدء السحب",
        "btn_stop": "⏹️ إيقاف",
        "news_ticker": "🎉 مرحباً بكم في موقع المطري OTP | ⚡ أرقام وهمية لجميع المنصات | 📱 خدمة 24/7 | 🔥 جودة عالية",
        "whatsapp_dev": "https://wa.me/967733723953",
        "whatsapp_group": "https://chat.whatsapp.com/IeK2gNS64fd8YSnenzt4WR",
        "telegram_channel": "@jsjsgsjsvh",
        "social_links": json.dumps({"instagram": "", "tiktok": "", "facebook": ""}),
        "matrix_rain": "true",
        "news_ticker_enabled": "true",
        "bg_color": "#0a0e1a",
        "text_color": "#ffffff",
        "button_color": "#00ffc8",
        "admin_password": "",
        "primary_color": "#00ffc8",
        "secondary_color": "#8b5cf6",
        "accent_color": "#ec4899"
    }
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for key, value in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

# تشغيل إنشاء قاعدة البيانات
init_db()

# ===========================================
# 📊 بيانات الدول (أكثر من 195 دولة)
# ===========================================
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
    "880": {"n": "بنغلاديش", "f": "🇧🇩"},
    "886": {"n": "تايوان", "f": "🇹🇼"},
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
    "501": {"n": "بليز", "f": "🇧🇿"},
    "502": {"n": "غواتيمالا", "f": "🇬🇹"},
    "503": {"n": "السلفادور", "f": "🇸🇻"},
    "504": {"n": "هندوراس", "f": "🇭🇳"},
    "505": {"n": "نيكاراغوا", "f": "🇳🇮"},
    "506": {"n": "كوستاريكا", "f": "🇨🇷"},
    "507": {"n": "بنما", "f": "🇵🇦"},
    "509": {"n": "هايتي", "f": "🇭🇹"},
    "591": {"n": "بوليفيا", "f": "🇧🇴"},
    "592": {"n": "غيانا", "f": "🇬🇾"},
    "593": {"n": "الإكوادور", "f": "🇪🇨"},
    "595": {"n": "باراغواي", "f": "🇵🇾"},
    "597": {"n": "سورينام", "f": "🇸🇷"},
    "598": {"n": "أوروغواي", "f": "🇺🇾"},
    "670": {"n": "تيمور الشرقية", "f": "🇹🇱"},
    "673": {"n": "بروناي", "f": "🇧🇳"},
    "675": {"n": "بابوا غينيا الجديدة", "f": "🇵🇬"},
    "677": {"n": "جزر سليمان", "f": "🇸🇧"},
    "678": {"n": "فانواتو", "f": "🇻🇺"},
    "679": {"n": "فيجي", "f": "🇫🇯"},
    "680": {"n": "بالاو", "f": "🇵🇼"},
    "682": {"n": "جزر كوك", "f": "🇨🇰"},
    "685": {"n": "ساموا", "f": "🇼🇸"},
    "686": {"n": "كيريباتي", "f": "🇰🇮"},
    "850": {"n": "كوريا الشمالية", "f": "🇰🇵"},
    "852": {"n": "هونغ كونغ", "f": "🇭🇰"},
    "853": {"n": "ماكاو", "f": "🇲🇴"},
}

def get_country_info(code):
    """الحصول على معلومات الدولة"""
    info = COUNTRY_DATA.get(code)
    return (info["n"], info["f"]) if info else ("أخرى", "🌍")

# ===========================================
# 📱 أسماء المنصات
# ===========================================
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

# ===========================================
# 🎨 شعارات المنصات (SVG Base64)
# ===========================================
PLATFORM_LOGOS = {
    "whatsapp": '''data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%2325D366'/><path fill='%23fff' d='M50 18c-17.6 0-32 14.4-32 32 0 6 1.7 11.8 4.8 16.8L18 82l15.6-4.7C38.6 80.1 44.2 82 50 82c17.6 0 32-14.4 32-32S67.6 18 50 18zm18.6 45.6c-.8 2.2-4.6 4.2-6.4 4.5-1.6.3-3.7.4-5.9-.4-1.4-.5-3.1-1.1-5.4-2.2-9.5-4.1-15.7-13.7-16.2-14.3-.5-.7-3.9-5.1-3.9-9.7s2.4-6.9 3.3-7.9c.9-.9 1.9-1.2 2.6-1.2.6 0 1.2 0 1.7 0 .6 0 1.3-.2 2 .1 1.6.7 2.6 3 2.9 3.9.3.9.5 1.5 0 2.4-.4.9-1.5 2.4-2.2 3.4 0 0 .7.7 1.4 1.5 2.4 2.7 5.3 5.5 9.6 7.1 1.5.5 2.3.6 3-.4.6-1 2.5-3 3.2-4 .7-1 1.4-.8 2.3-.5.9.3 5.8 2.7 6.8 3.2 1 .5 1.6.7 1.8 1.1.2.5.2 2.5-.6 4.7z'/></svg>''',
    "telegram": '''data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%2326A5E4'/><path fill='%23fff' d='M22 50l50-22-7 48-18-8-7 12-3-17 31-26-37 24-9-4z'/></svg>''',
    "tiktok": '''data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%23000'/><path fill='%2325F4EE' d='M62 22c2 8 8 14 16 15v9c-6 0-12-2-16-5v22c0 12-9 20-20 20s-20-8-20-20 9-21 20-21v9c-6 0-11 5-11 12s5 12 11 12 12-6 12-12V22h8z'/><path fill='%23FE2C55' d='M70 22c2 8 8 14 16 15v9c-6 0-12-2-16-5v22c0 12-9 20-20 20v-9c6 0 12-6 12-12V22h8z'/></svg>''',
    "facebook": '''data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%231877F2'/><path fill='%23fff' d='M58 84V52h10l1-12H58v-7c0-3 1-5 5-5h6V17h-9c-10 0-15 6-15 14v9H36v12h9v32h13z'/></svg>''',
    "instagram": '''data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><defs><radialGradient id='ig' cx='30%25' cy='30%25' r='80%25'><stop offset='0%25' stop-color='%23FEDA75'/><stop offset='50%25' stop-color='%23FA7E1E'/><stop offset='100%25' stop-color='%23D62976'/></radialGradient></defs><rect width='100' height='100' rx='22' fill='url(%23ig)'/><rect x='22' y='22' width='56' height='56' rx='14' fill='none' stroke='%23fff' stroke-width='5'/><circle cx='50' cy='50' r='13' fill='none' stroke='%23fff' stroke-width='5'/><circle cx='72' cy='28' r='4' fill='%23fff'/></svg>''',
    "snapchat": '''data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%23FFFC00'/><path fill='%23000' d='M50 16c-13 0-23 9-23 21 0 6 1 11 2 16-2 1-4 2-7 2-1 0-2 1-2 2 0 4 8 5 11 7 1 1 1 4 2 6 1 3 4 5 8 5 3 0 5-1 7-1 3 0 6 6 13 6 7 0 10-6 13-6 2 0 4 1 7 1 4 0 7-2 8-5 1-2 1-5 2-6 3-2 11-3 11-7 0-1-1-2-2-2-3 0-5-1-7-2 1-5 2-10 2-16 0-12-10-21-23-21-3 0-6 1-8 2-2-1-5-2-8-2z'/></svg>''',
    "google": '''data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%23fff'/><path fill='%234285F4' d='M58 50c0-1-.1-2-.2-3H50v6h5.5c-.5 2-2 4-4.5 5l4 3c3-2 5-6 5-10 0-1 0-1-.5-1z'/><path fill='%2334A853' d='M40 56c1 4 4 7 9 7 3 0 5-1 7-3l-4-3c-1 1-2 1-4 1-3 0-5-2-6-4l-4 2z'/><path fill='%23FBBC04' d='M40 44l-4 2c-1 1-1 3-1 4s0 3 1 4l4-2c-.5-1-.5-2-.5-3s0-4 0-4z'/><path fill='%23EA4335' d='M50 36c3 0 5 1 6 2l-3 3c-1-1-2-1-4-1-5 0-9 4-9 4l-4-2c0-3 4-6 14-6z'/></svg>''',
    "twitter": '''data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%23000'/><path fill='%23fff' d='M70 35c-2 1-4 1-6 1 2-1 4-3 5-5-2 1-4 2-7 2-2-2-5-3-8-3-6 0-11 5-11 11 0 1 0 2 .3 3-9 0-17-5-22-12-1 2-1 4-1 6 0 4 2 7 5 9-2 0-4-1-5-2v.1c0 5 4 10 9 11-1 0-3 .5-4 .5-1 0-2 0-3-.1 2 4 6 7 11 7-4 3-9 5-15 5-1 0-2 0-3-.1 5 3 11 5 18 5 21 0 33-18 33-33v-1c2-2 4-3 6-6z'/></svg>''',
}

# ===========================================
# 🌈 تدرجات ألوان المنصات
# ===========================================
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

# ===========================================
# 🔧 دوال قاعدة البيانات
# ===========================================
def get_setting(key, default=""):
    """الحصول على إعداد"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(key, value):
    """تحديث إعداد"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def log_admin_action(action, details):
    """تسجيل فعل الأدمن"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO admin_logs (action, details, timestamp) VALUES (?, ?, ?)",
              (action, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# ===========================================
# 📦 دوال الكومبوهات
# ===========================================
def get_platforms():
    """الحصول على قائمة المنصات"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT platform, sort_order FROM combos ORDER BY sort_order, platform")
    platforms = [row[0] for row in c.fetchall()]
    conn.close()
    # إذا لا توجد منصات، أرجع المنصات الافتراضية
    return platforms if platforms else list(platform_names.keys())

def get_countries_by_platform(platform):
    """الحصول على الدول حسب المنصة"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT country_code, country_name, country_flag FROM combos WHERE platform=? ORDER BY country_name", (platform,))
    countries = [{'code': row[0], 'name': row[1], 'flag': row[2]} for row in c.fetchall()]
    conn.close()
    return countries

def get_numbers(platform, country_code):
    """الحصول على أرقام كومبو معين"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT numbers FROM combos WHERE platform=? AND country_code=?", (platform, country_code))
    row = c.fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row[0])
        except:
            return []
    return []

def save_combo(platform, country_code, country_name, country_flag, numbers):
    """حفظ كومبو جديد"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("REPLACE INTO combos (platform, country_code, country_name, country_flag, numbers) VALUES (?, ?, ?, ?, ?)",
              (platform, country_code, country_name, country_flag, json.dumps(numbers)))
    conn.commit()
    conn.close()

def delete_combo(platform, country_code):
    """حذف كومبو"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM combos WHERE platform=? AND country_code=?", (platform, country_code))
    conn.commit()
    conn.close()

def get_all_combos():
    """الحصول على جميع الكومبوهات"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, platform, country_code, country_name, country_flag FROM combos ORDER BY platform, country_name")
    combos = [{'id': row[0], 'platform': row[1], 'code': row[2], 'name': row[3], 'flag': row[4]} for row in c.fetchall()]
    conn.close()
    return combos

# ===========================================
# 📊 دوال الإحصائيات
# ===========================================
def get_stats():
    """الحصول على إحصائيات الموقع"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # إجمالي الأكواد
    c.execute("SELECT COUNT(*) FROM otp_logs")
    total_codes = c.fetchone()[0]
    
    # أكواد اليوم
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM otp_logs WHERE timestamp LIKE ?", (f"{today}%",))
    today_codes = c.fetchone()[0]
    
    # عدد المنصات
    c.execute("SELECT COUNT(DISTINCT platform) FROM combos")
    platforms_count = c.fetchone()[0]
    
    # عدد الدول
    c.execute("SELECT COUNT(*) FROM combos")
    countries_count = c.fetchone()[0]
    
    # عدد المستخدمين
    c.execute("SELECT COUNT(*) FROM users")
    users_count = c.fetchone()[0]
    
    # المستخدمين النشطين (آخر 7 أيام)
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(DISTINCT number) FROM otp_logs WHERE timestamp > ?", (week_ago,))
    active_users = c.fetchone()[0]
    
    conn.close()
    
    return {
        'total_codes': total_codes,
        'today_codes': today_codes,
        'platforms': platforms_count,
        'countries': countries_count,
        'users': users_count,
        'active_users': active_users
    }

def get_codes_chart(days=7):
    """الحصول على بيانات الرسم البياني"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    chart_data = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=days-i-1)).strftime("%Y-%m-%d")
        c.execute("SELECT COUNT(*) FROM otp_logs WHERE timestamp LIKE ?", (f"{date}%",))
        count = c.fetchone()[0]
        chart_data.append({'date': date, 'count': count})
    
    conn.close()
    return chart_data

# ===========================================
# 🛡️ حماية لوحة التحكم
# ===========================================
def admin_required(f):
    """مصمم للتحقق من تسجيل دخول الأدمن"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # إذا لا توجد كلمة سر، سمح بالوصول
        if not get_setting('admin_password'):
            return f(*args, **kwargs)
        
        # تحقق من تسجيل الدخول
        if session.get('admin_logged_in'):
            return f(*args, **kwargs)
        
        return redirect(url_for('admin_login'))
    return decorated_function

# ===========================================
# 🌐 Routes الرئيسية
# ===========================================
@app.route('/')
def home():
    """الصفحة الرئيسية"""
    # الحصول على الإعدادات
    settings = {
        'site_title': get_setting('site_title', '🚀 موقع المطري OTP 🚀'),
        'site_description': get_setting('site_description'),
        'btn_get_number': get_setting('btn_get_number', '🚀 جلب رقم'),
        'btn_switch': get_setting('btn_switch', '🔄 تبديل'),
        'btn_start': get_setting('btn_start', '📡 بدء السحب'),
        'btn_stop': get_setting('btn_stop', '⏹️ إيقاف'),
        'news_ticker': get_setting('news_ticker'),
        'whatsapp_dev': get_setting('whatsapp_dev'),
        'whatsapp_group': get_setting('whatsapp_group'),
        'telegram_channel': get_setting('telegram_channel'),
        'social_links': get_setting('social_links'),
        'matrix_rain': get_setting('matrix_rain', 'true') == 'true',
        'news_ticker_enabled': get_setting('news_ticker_enabled', 'true') == 'true',
        'bg_color': get_setting('bg_color', '#0a0e1a'),
        'text_color': get_setting('text_color', '#ffffff'),
        'button_color': get_setting('button_color', '#00ffc8'),
    }
    
    # الحصول على الإعلانات النشطة
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT type, content, link, button_text FROM ads WHERE active=1 ORDER BY created_at DESC LIMIT 3")
    ads = [{'type': row[0], 'content': row[1], 'link': row[2], 'button_text': row[3]} for row in c.fetchall()]
    conn.close()
    
    return render_template('index.html', 
                          settings=settings,
                          ads=ads,
                          platforms=list(platform_names.keys()),
                          platform_names=platform_names,
                          platform_logos=PLATFORM_LOGOS,
                          platform_gradients=PLATFORM_GRADIENTS)

# ===========================================
# 🔗 API Routes
# ===========================================
@app.route('/api/countries', methods=['POST'])
def api_countries():
    """API لجلب الدول حسب المنصة"""
    platform = request.json.get('platform')
    countries = get_countries_by_platform(platform)
    return jsonify(countries)

@app.route('/api/get_number', methods=['POST'])
def api_get_number():
    """API لجلب رقم عشوائي"""
    platform = request.json.get('platform')
    country = request.json.get('country')
    numbers = get_numbers(platform, country)
    
    if numbers:
        number = random.choice(numbers)
        # تسجيل المستخدم
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (phone, created_at) VALUES (?, ?)",
                  (number, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return jsonify({'number': number})
    
    return jsonify({'number': None})

@app.route('/api/get_otp', methods=['POST'])
def api_get_otp():
    """API لجلب الأكواد"""
    num = request.json.get('number')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT otp, timestamp, platform FROM otp_logs WHERE number LIKE ? ORDER BY id DESC LIMIT 10",
              (f"%{num[-4:]}",))
    rows = c.fetchall()
    conn.close()
    
    codes = [{'otp': row[0], 'timestamp': row[1], 'platform': row[2]} for row in rows]
    return jsonify({'codes': codes})

@app.route('/api/check_new_otp', methods=['POST'])
def api_check_new_otp():
    """فحص أكواد جديدة"""
    num = request.json.get('number')
    last_check = request.json.get('last_check')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if last_check:
        c.execute("SELECT otp, timestamp, platform FROM otp_logs WHERE number LIKE ? AND timestamp > ? ORDER BY id DESC",
                  (f"%{num[-4:]}", last_check))
    else:
        c.execute("SELECT otp, timestamp, platform FROM otp_logs WHERE number LIKE ? ORDER BY id DESC LIMIT 5",
                  (f"%{num[-4:]}",))
    
    rows = c.fetchall()
    conn.close()
    
    codes = [{'otp': row[0], 'timestamp': row[1], 'platform': row[2]} for row in rows]
    return jsonify({'codes': codes})

# ===========================================
# 🔐 Routes لوحة التحكم
# ===========================================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """صفحة تسجيل الدخول"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == get_setting('admin_password') or not get_setting('admin_password'):
            session['admin_logged_in'] = True
            log_admin_action('login', 'تسجيل دخول')
            return redirect(url_for('admin_panel'))
        else:
            flash('كلمة السر غير صحيحة', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """تسجيل الخروج"""
    log_admin_action('logout', 'تسجيل خروج')
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))

@app.route('/admin')
@admin_required
def admin_panel():
    """لوحة التحكم الرئيسية"""
    stats = get_stats()
    combos = get_all_combos()
    recent_codes = get_recent_codes(20)
    
    # الحصول على الإعدادات
    settings = {
        'site_title': get_setting('site_title'),
        'site_description': get_setting('site_description'),
        'btn_get_number': get_setting('btn_get_number'),
        'btn_switch': get_setting('btn_switch'),
        'btn_start': get_setting('btn_start'),
        'btn_stop': get_setting('btn_stop'),
        'news_ticker': get_setting('news_ticker'),
        'news_ticker_enabled': get_setting('news_ticker_enabled', 'true'),
        'whatsapp_dev': get_setting('whatsapp_dev'),
        'whatsapp_group': get_setting('whatsapp_group'),
        'telegram_channel': get_setting('telegram_channel'),
        'bg_color': get_setting('bg_color', '#0a0e1a'),
        'text_color': get_setting('text_color', '#ffffff'),
        'button_color': get_setting('button_color', '#00ffc8'),
        'primary_color': get_setting('primary_color', '#00ffc8'),
        'secondary_color': get_setting('secondary_color', '#8b5cf6'),
        'accent_color': get_setting('accent_color', '#ec4899'),
        'matrix_rain': get_setting('matrix_rain', 'true'),
        'social_links': json.loads(get_setting('social_links', '{}'))
    }
    
    return render_template('admin.html',
                          stats=stats,
                          combos=combos,
                          recent_codes=recent_codes,
                          settings=settings,
                          platform_names=platform_names)

@app.route('/admin/settings', methods=['POST'])
@admin_required
def admin_save_settings():
    """حفظ إعدادات النصوص"""
    set_setting('site_title', request.form.get('site_title', ''))
    set_setting('site_description', request.form.get('site_description', ''))
    set_setting('btn_get_number', request.form.get('btn_get_number', ''))
    set_setting('btn_switch', request.form.get('btn_switch', ''))
    set_setting('btn_start', request.form.get('btn_start', ''))
    set_setting('btn_stop', request.form.get('btn_stop', ''))
    set_setting('news_ticker', request.form.get('news_ticker', ''))
    
    log_admin_action('settings', 'تحديث إعدادات النصوص')
    flash('تم حفظ الإعدادات بنجاح', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/links', methods=['POST'])
@admin_required
def admin_save_links():
    """حفظ إعدادات الروابط"""
    set_setting('whatsapp_dev', request.form.get('whatsapp_dev', ''))
    set_setting('whatsapp_group', request.form.get('whatsapp_group', ''))
    set_setting('telegram_channel', request.form.get('telegram_channel', ''))
    
    social = {
        'instagram': request.form.get('instagram', ''),
        'tiktok': request.form.get('tiktok', ''),
        'facebook': request.form.get('facebook', ''),
    }
    set_setting('social_links', json.dumps(social))
    
    log_admin_action('links', 'تحديث الروابط')
    flash('تم حفظ الروابط بنجاح', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/appearance', methods=['POST'])
@admin_required
def admin_save_appearance():
    """حفظ إعدادات المظهر"""
    set_setting('bg_color', request.form.get('bg_color', '#0a0e1a'))
    set_setting('text_color', request.form.get('text_color', '#ffffff'))
    set_setting('button_color', request.form.get('button_color', '#00ffc8'))
    set_setting('primary_color', request.form.get('primary_color', '#00ffc8'))
    set_setting('secondary_color', request.form.get('secondary_color', '#8b5cf6'))
    set_setting('accent_color', request.form.get('accent_color', '#ec4899'))
    set_setting('matrix_rain', 'true' if request.form.get('matrix_rain') else 'false')
    set_setting('news_ticker_enabled', 'true' if request.form.get('news_ticker_enabled') else 'false')
    
    log_admin_action('appearance', 'تحديث إعدادات المظهر')
    flash('تم حفظ إعدادات المظهر بنجاح', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/upload_combo', methods=['POST'])
@admin_required
def admin_upload_combo():
    """رفع ملف كومبو جديد"""
    platform = request.form.get('platform')
    country_code = request.form.get('country_code')
    file = request.files.get('file')
    
    if file and file.filename.endswith('.txt'):
        content = file.read().decode('utf-8')
        numbers = [line.strip() for line in content.splitlines() if line.strip()]
        
        if numbers:
            name, flag = get_country_info(country_code)
            save_combo(platform, country_code, name, flag, numbers)
            log_admin_action('upload_combo', f'رفع كومبو: {platform} - {name}')
            flash(f'تم رفع {len(numbers)} رقم بنجاح', 'success')
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_combo', methods=['POST'])
@admin_required
def admin_delete_combo():
    """حذف كومبو"""
    combo_id = request.form.get('id')
    if combo_id:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM combos WHERE id=?", (combo_id,))
        conn.commit()
        conn.close()
        log_admin_action('delete_combo', f'حذف كومبو: {combo_id}')
        flash('تم حذف الكومبو بنجاح', 'success')
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_code', methods=['POST'])
@admin_required
def admin_delete_code():
    """حذف كود معين"""
    code_id = request.form.get('id')
    if code_id:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM otp_logs WHERE id=?", (code_id,))
        conn.commit()
        conn.close()
        log_admin_action('delete_code', f'حذف كود: {code_id}')
        flash('تم حذف الكود بنجاح', 'success')
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/clear_codes', methods=['POST'])
@admin_required
def admin_clear_codes():
    """مسح جميع الأكواد"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM otp_logs")
    conn.commit()
    conn.close()
    log_admin_action('clear_codes', 'مسح جميع الأكواد')
    flash('تم مسح جميع الأكواد بنجاح', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/add_ad', methods=['POST'])
@admin_required
def admin_add_ad():
    """إضافة إعلان جديد"""
    ad_type = request.form.get('type', 'text')
    content = request.form.get('content', '')
    link = request.form.get('link', '')
    button_text = request.form.get('button_text', '')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO ads (type, content, link, button_text, active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
              (ad_type, content, link, button_text, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    
    log_admin_action('add_ad', 'إضافة إعلان جديد')
    flash('تم إضافة الإعلان بنجاح', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_ad', methods=['POST'])
@admin_required
def admin_delete_ad():
    """حذف إعلان"""
    ad_id = request.form.get('id')
    if ad_id:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM ads WHERE id=?", (ad_id,))
        conn.commit()
        conn.close()
        log_admin_action('delete_ad', f'حذف إعلان: {ad_id}')
        flash('تم حذف الإعلان بنجاح', 'success')
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/ban_user', methods=['POST'])
@admin_required
def admin_ban_user():
    """حظر مستخدم"""
    user_id = request.form.get('id')
    if user_id:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE users SET banned=1 WHERE id=?", (user_id,))
        conn.commit()
        conn.close()
        log_admin_action('ban_user', f'حظر مستخدم: {user_id}')
        flash('تم حظر المستخدم بنجاح', 'success')
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/unban_user', methods=['POST'])
@admin_required
def admin_unban_user():
    """فك حظر مستخدم"""
    user_id = request.form.get('id')
    if user_id:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE users SET banned=0 WHERE id=?", (user_id,))
        conn.commit()
        conn.close()
        log_admin_action('unban_user', f'فك حظر مستخدم: {user_id}')
        flash('تم فك حظر المستخدم بنجاح', 'success')
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/change_password', methods=['POST'])
@admin_required
def admin_change_password():
    """تغيير كلمة السر"""
    new_password = request.form.get('new_password', '')
    set_setting('admin_password', new_password)
    log_admin_action('change_password', 'تغيير كلمة السر')
    flash('تم تغيير كلمة السر بنجاح', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/backup', methods=['POST'])
@admin_required
def admin_backup():
    """إنشاء نسخة احتياطية"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # جمع كل البيانات
    c.execute("SELECT key, value FROM settings")
    settings = dict(c.fetchall())
    
    c.execute("SELECT platform, country_code, country_name, country_flag, numbers FROM combos")
    combos = [list(row) for row in c.fetchall()]
    
    c.execute("SELECT * FROM ads")
    ads = [list(row) for row in c.fetchall()]
    
    backup_data = {
        'settings': settings,
        'combos': combos,
        'ads': ads,
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # حفظ النسخة
    c.execute("INSERT INTO backups (name, data, created_at) VALUES (?, ?, ?)",
              (f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
               json.dumps(backup_data),
               datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    
    log_admin_action('backup', 'إنشاء نسخة احتياطية')
    flash('تم إنشاء النسخة الاحتياطية بنجاح', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/restore', methods=['POST'])
@admin_required
def admin_restore():
    """استعادة نسخة احتياطية"""
    backup_id = request.form.get('backup_id')
    if backup_id:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT data FROM backups WHERE id=?", (backup_id,))
        row = c.fetchone()
        
        if row:
            backup_data = json.loads(row[0])
            
            # استعادة الإعدادات
            for key, value in backup_data.get('settings', {}).items():
                set_setting(key, value)
            
            # استعادة الكومبوهات
            for combo in backup_data.get('combos', []):
                c.execute("INSERT OR REPLACE INTO combos (platform, country_code, country_name, country_flag, numbers) VALUES (?, ?, ?, ?, ?)",
                         (combo[0], combo[1], combo[2], combo[3], combo[4]))
            
            conn.commit()
        
        conn.close()
        log_admin_action('restore', f'استعادة نسخة: {backup_id}')
        flash('تم استعادة النسخة الاحتياطية بنجاح', 'success')
    
    return redirect(url_for('admin_panel'))

# ===========================================
# 📋 دوال مساعدة
# ===========================================
def get_recent_codes(limit=20):
    """الحصول على آخر الأكواد"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, number, otp, timestamp, platform FROM otp_logs ORDER BY id DESC LIMIT ?", (limit,))
    codes = [{'id': row[0], 'number': row[1], 'otp': row[2], 'timestamp': row[3], 'platform': row[4]} for row in c.fetchall()]
    conn.close()
    return codes

def get_users():
    """الحصول على قائمة المستخدمين"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, phone, created_at, banned, codes_count FROM users ORDER BY created_at DESC")
    users = [{'id': row[0], 'phone': row[1], 'created_at': row[2], 'banned': row[3], 'codes_count': row[4]} for row in c.fetchall()]
    conn.close()
    return users

def get_ads():
    """الحصول على قائمة الإعلانات"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, type, content, link, button_text, active, created_at FROM ads ORDER BY created_at DESC")
    ads = [{'id': row[0], 'type': row[1], 'content': row[2], 'link': row[3], 'button_text': row[4], 'active': row[5], 'created_at': row[6]} for row in c.fetchall()]
    conn.close()
    return ads

def get_backups():
    """الحصول على قائمة النسخ الاحتياطية"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, created_at FROM backups ORDER BY created_at DESC")
    backups = [{'id': row[0], 'name': row[1], 'created_at': row[2]} for row in c.fetchall()]
    conn.close()
    return backups

def get_admin_logs(limit=50):
    """الحصول على سجلات الأدمن"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, action, details, timestamp FROM admin_logs ORDER BY id DESC LIMIT ?", (limit,))
    logs = [{'id': row[0], 'action': row[1], 'details': row[2], 'timestamp': row[3]} for row in c.fetchall()]
    conn.close()
    return logs

# ===========================================
# 📋 API للأدمن
# ===========================================
@app.route('/api/codes', methods=['GET'])
@admin_required
def api_get_codes():
    """API لجلب جميع الأكواد"""
    platform = request.args.get('platform', '')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if platform:
        c.execute("SELECT id, number, otp, timestamp, platform FROM otp_logs WHERE platform=? ORDER BY id DESC LIMIT 500", (platform,))
    else:
        c.execute("SELECT id, number, otp, timestamp, platform FROM otp_logs ORDER BY id DESC LIMIT 500")
    
    rows = c.fetchall()
    conn.close()
    
    codes = [{'id': row[0], 'number': row[1], 'otp': row[2], 'timestamp': row[3], 'platform': row[4]} for row in rows]
    return jsonify(codes)

@app.route('/api/users', methods=['GET'])
@admin_required
def api_get_users():
    """API لجلب المستخدمين"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, phone, created_at, banned, codes_count FROM users ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    
    users = [{'id': row[0], 'phone': row[1], 'created_at': row[2], 'banned': row[3], 'codes_count': row[4]} for row in rows]
    return jsonify(users)

@app.route('/api/backups', methods=['GET'])
@admin_required
def api_get_backups():
    """API لجلب النسخ الاحتياطية"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, created_at FROM backups ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    
    backups = [{'id': row[0], 'name': row[1], 'created_at': row[2]} for row in rows]
    return jsonify(backups)

@app.route('/api/ads', methods=['GET'])
@admin_required
def api_get_ads():
    """API لجلب الإعلانات"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, type, content, link, button_text, active, created_at FROM ads ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    
    ads = [{'id': row[0], 'type': row[1], 'content': row[2], 'link': row[3], 'button_text': row[4], 'active': row[5], 'created_at': row[6]} for row in rows]
    return jsonify(ads)

# ===========================================
# 📡 مراقبة قناة تيليجرام
# ===========================================
def monitor_channel():
    """مراقبة قناة تيليجرام للأكواد"""
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
                            
                            clean = re.sub(r'[\u200B-\u200F\u202A-\u202E]', '', text)
                            lines = clean.split('\n')
                            
                            # استخراج الرقم
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
                            
                            # استخراج الكود
                            otp = None
                            
                            dash_code = re.search(r'(\d{3})-(\d{3,4})', clean)
                            if dash_code:
                                otp = dash_code.group(1) + dash_code.group(2)
                            
                            if not otp:
                                all_codes = re.findall(r'\b\d{4,8}\b', clean)
                                for c in all_codes:
                                    if last_digits and c.endswith(last_digits):
                                        continue
                                    if len(c) >= 4:
                                        otp = c
                                        break
                            
                            # تحديد المنصة
                            platform = "غير معروف"
                            text_lower = clean.lower()
                            
                            platforms_map = {
                                "واتساب": ["wa", "whatsapp", "واتساب"],
                                "فيسبوك": ["fb", "facebook", "فيسبوك"],
                                "تيليجرام": ["tg", "telegram", "تيليجرام"],
                                "تيك توك": ["tt", "tiktok", "تيك توك"],
                                "انستقرام": ["ig", "instagram", "انستقرام"],
                                "سناب شات": ["sc", "snapchat", "سناب"],
                                "جوجل": ["gg", "google", "جوجل"],
                            }
                            
                            for name, keywords in platforms_map.items():
                                if any(kw in text_lower for kw in keywords):
                                    platform = name
                                    break
                            
                            # حفظ الكود
                            if otp:
                                conn = sqlite3.connect(DB_PATH)
                                c = conn.cursor()
                                c.execute("INSERT INTO otp_logs (number, otp, timestamp, platform) VALUES (?, ?, ?, ?)",
                                         (last_digits or "0000", otp, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), platform))
                                conn.commit()
                                conn.close()
                                
                                print(f"✅ [{platform}] {otp} | الرقم: {last_digits}")
                                
                                # إرسال إشعار للأدمن
                                if NOTIFY_BOT_TOKEN:
                                    try:
                                        notify_msg = f"🎉 كود جديد!\n\n📱 المنصة: {platform}\n🔑 الكود: {otp}\n📞 الرقم: {last_digits}\n🕐 الوقت: {datetime.now().strftime('%H:%M:%S')}"
                                        requests.get(f"https://api.telegram.org/bot{NOTIFY_BOT_TOKEN}/sendMessage",
                                                    params={"chat_id": "me", "text": notify_msg}, timeout=10)
                                    except:
                                        pass
                                
        except Exception as e:
            print(f"❌ خطأ في المراقبة: {e}")
        
        time.sleep(5)

# بدء مراقبة تيليجرام
threading.Thread(target=monitor_channel, daemon=True).start()

# ===========================================
# 🚀 تشغيل التطبيق
# ===========================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
