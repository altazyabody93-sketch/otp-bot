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
# ✅ [جديد] ID الأدمن اللي بنرسل له طلبات المساعدة والإعلانات الجديدة
OWNER_TELEGRAM_ID = "ABOD_90N"  # username الأدمن
# ✅ [جديد] ID جروب تيليجرام للمراقبة (سالب للقروبات)
TELEGRAM_GROUP_CHAT_ID = "-1001234567890"  # لازم تحدد الـ chat_id الحقيقي للجروب

# ========== قاعدة البيانات ==========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS combos (id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, country_code TEXT, country_name TEXT, country_flag TEXT, numbers TEXT, UNIQUE(platform, country_code))''')
    c.execute('''CREATE TABLE IF NOT EXISTS otp_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT, otp TEXT, timestamp TEXT, platform TEXT)''')
    # ✅ [جديد] جدول الإعلانات اللي بنرسلها من البوت
    c.execute('''CREATE TABLE IF NOT EXISTS announcements (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, content TEXT, media_url TEXT, button_text TEXT, button_url TEXT, source_msg_id INTEGER, created_at TEXT)''')
    # ✅ [جديد] جدول طلبات المساعدة من الموقع
    c.execute('''CREATE TABLE IF NOT EXISTS help_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, message TEXT, source TEXT, status TEXT DEFAULT 'pending', created_at TEXT)''')
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

# ألوان المنصات (hex) لاستخدامها في CSS/JavaScript
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
        html, body { font-family:'Cairo',sans-serif; background:#07090d; color:#c9d1d9; overflow-x:hidden; }
        body { min-height:100vh; }
        /* [تقليل الإضاءة] overlay يخفف السطوع على العيون */
        body::before {
            content:''; position:fixed; inset:0; z-index:9999; pointer-events:none;
            background: radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.4) 100%);
        }

        .app { max-width:480px; margin:0 auto; background:#0d1117; min-height:100vh; display:flex; flex-direction:column; }

        /* ============= HEADER ============= */
        .top-bar { background:#0d1117; padding:14px 16px; display:flex; align-items:center; justify-content:flex-start; gap:12px; border-bottom:1px solid #21262d; position:sticky; top:0; z-index:50; }
        .brand { display:flex; align-items:center; gap:10px; flex:0 0 auto; }
        .brand-icon { width:36px; height:36px; border-radius:10px; background:linear-gradient(135deg, #1f6feb, #388bfd); display:flex; align-items:center; justify-content:center; font-size:18px; }
        .brand-text { font-size:16px; font-weight:700; color:#fff; }
        .top-actions { display:flex; gap:6px; margin-right:auto; }
        .menu-btn { background:transparent; border:none; color:#8b949e; font-size:22px; cursor:pointer; padding:4px 8px; }

        /* ============= [شريط الأخبار] يتحرك تحت الشريط العلوي ============= */
        .news-ticker {
            background: linear-gradient(90deg, #1c2128, #21262d, #1c2128);
            border-bottom: 1px solid #30363d;
            padding: 8px 0;
            overflow: hidden;
            position: relative;
            direction: ltr;
        }
        .news-ticker::before, .news-ticker::after {
            content: ''; position: absolute; top: 0; bottom: 0; width: 40px; z-index: 2; pointer-events: none;
        }
        .news-ticker::before { left: 0; background: linear-gradient(90deg, #1c2128, transparent); }
        .news-ticker::after  { right: 0; background: linear-gradient(-90deg, #1c2128, transparent); }
        .ticker-label {
            position: absolute; top: 0; right: 0; bottom: 0; left: 0;
            display: none;
        }
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
        body.light .news-ticker { background: linear-gradient(90deg, #f6f8fa, #eaeef2, #f6f8fa); border-bottom-color: #d0d7de; }
        body.light .ticker-content { color: #1f2328; }
        /* ============= [القائمة المنسدلة] بتصميم احترافي مع أيقونات SVG ============= */
        .dropdown-menu { 
            display:none; 
            position:absolute; 
            top:55px; 
            left:16px; 
            right:16px; 
            background:linear-gradient(180deg, #1c2128 0%, #161b22 100%);
            border:1px solid #30363d; 
            border-radius:14px; 
            padding:10px; 
            z-index:100; 
            box-shadow:0 12px 32px rgba(0,0,0,0.6), 0 0 0 1px rgba(88,166,255,0.08); 
            flex-direction:column; 
            gap:4px;
            max-width:340px;
            margin:0 auto;
            animation: menuSlide 0.25s ease;
        }
        .dropdown-menu.show { display:flex; }
        @keyframes menuSlide {
            from { opacity:0; transform:translateY(-8px); }
            to   { opacity:1; transform:translateY(0); }
        }
        .dropdown-menu a { 
            display:flex; 
            align-items:center; 
            gap:12px; 
            color:#e6e6e6; 
            text-decoration:none; 
            padding:12px 14px; 
            border-radius:10px; 
            font-size:14px; 
            font-weight:600; 
            white-space:nowrap; 
            transition:all 0.15s ease;
            border:1px solid transparent;
            width:100%;
        }
        .dropdown-menu a:hover { 
            background:linear-gradient(135deg, #21262d 0%, #1c2128 100%); 
            color:#58a6ff; 
            border-color:#30363d;
            transform:translateX(-3px);
        }
        .dropdown-menu a .ico { 
            font-size:20px; 
            width:32px; 
            height:32px; 
            display:flex; 
            align-items:center; 
            justify-content:center;
            background:rgba(88,166,255,0.1);
            border-radius:8px;
            flex-shrink:0;
        }
        .dropdown-menu a:hover .ico {
            background:rgba(88,166,255,0.2);
        }
        .dropdown-menu .menu-divider {
            height:1px;
            background:linear-gradient(90deg, transparent, #30363d, transparent);
            margin:6px 0;
        }
        .dropdown-menu .menu-header {
            font-size:11px;
            color:#8b949e;
            font-weight:700;
            padding:6px 14px 2px;
            text-transform:uppercase;
            letter-spacing:0.5px;
        }

        /* ============= MAIN CONTENT ============= */
        .main { padding:16px; flex:1; }

        .hero { text-align:center; padding:24px 12px 20px; }
        .hero h1 { font-size:24px; font-weight:800; color:#fff; margin-bottom:6px; }
        .hero p { font-size:14px; color:#8b949e; line-height:1.5; }
        .hero p .crown { display:inline-block; animation:bounce 1.5s infinite; }
        @keyframes bounce { 0%,100%{ transform:translateY(0);} 50%{ transform:translateY(-3px);} }
        /* [إيموجي متحركة] بشكل مبهر */
        .emoji-float { display:inline-block; animation: emojiFloat 3s ease-in-out infinite; }
        .emoji-float:nth-of-type(2) { animation-delay: 0.4s; }
        @keyframes emojiFloat {
            0%,100% { transform: translateY(0) rotate(0deg) scale(1); }
            25%     { transform: translateY(-5px) rotate(-10deg) scale(1.1); }
            50%     { transform: translateY(-2px) rotate(0deg) scale(0.95); }
            75%     { transform: translateY(-6px) rotate(10deg) scale(1.12); }
        }
        .emoji-wave { display:inline-block; animation: emojiWave 2.2s ease-in-out infinite; transform-origin: 70% 70%; }
        @keyframes emojiWave {
            0%,100% { transform: rotate(0deg); }
            15%     { transform: rotate(15deg); }
            30%     { transform: rotate(-10deg); }
            45%     { transform: rotate(15deg); }
            60%,100%{ transform: rotate(0deg); }
        }
        .emoji-spin { display:inline-block; animation: emojiSpin 5s linear infinite; }
        @keyframes emojiSpin {
            0%   { transform: rotate(0deg) scale(1); }
            50%  { transform: rotate(180deg) scale(1.2); }
            100% { transform: rotate(360deg) scale(1); }
        }
        .emoji-pulse-soft { display:inline-block; animation: emojiPulseSoft 2.5s ease-in-out infinite; }
        @keyframes emojiPulseSoft {
            0%,100% { transform: scale(1); }
            50%     { transform: scale(1.18); }
        }

        .section-title { font-size:15px; font-weight:700; color:#fff; margin:18px 4px 12px; display:flex; align-items:center; gap:8px; }
        .section-title .icon { color:#58a6ff; }

        /* ============= PLATFORMS GRID ============= */
        .platforms { display:grid; grid-template-columns:repeat(2, 1fr); gap:10px; margin-bottom:8px; }
        .platform-btn {
            display:flex; align-items:center; gap:10px; padding:12px 14px;
            background:#1c2128; border:1px solid #30363d; border-radius:10px;
            color:#e6e6e6; cursor:pointer; transition:all 0.15s ease;
            font-size:14px; font-weight:600; font-family:'Cairo',sans-serif;
        }
        .platform-btn:hover { background:#21262d; border-color:#484f58; }
        .platform-btn:active { transform:scale(0.98); }
        .platform-btn.active { background:var(--platform-color, #1f6feb); border-color:var(--platform-color, #1f6feb); color:#fff; box-shadow:0 0 0 1px var(--platform-color, #1f6feb), 0 0 12px rgba(31,111,235,0.15); }
        .platform-btn img { width:32px; height:32px; object-fit:contain; border-radius:8px; background:#fff; padding:2px; }

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
        .form-control:focus { border-color:#1f6feb; }
        .form-control:disabled { opacity:0.5; cursor:not-allowed; }

        .btn-primary {
            width:100%; padding:14px; border:none; border-radius:10px;
            background:#238636; color:#fff; font-size:15px; font-weight:700;
            cursor:pointer; margin-top:10px; font-family:'Cairo',sans-serif;
            transition:all 0.15s ease;
        }
        .btn-primary:hover:not(:disabled) { background:#2ea043; }
        .btn-primary:active:not(:disabled) { transform:scale(0.98); }
        .btn-primary:disabled { opacity:0.5; cursor:not-allowed; }

        .btn-blue {
            width:100%; padding:14px; border:none; border-radius:10px;
            background:#1f6feb; color:#fff; font-size:15px; font-weight:700;
            cursor:pointer; margin-top:8px; font-family:'Cairo',sans-serif;
            transition:all 0.15s ease;
        }
        .btn-blue:hover { background:#388bfd; }

        /* ============= [الرقم] بخط حلو + زر نسخ بارز ============= */
        .number-card {
            background: linear-gradient(135deg, #0d1117, #161b22);
            border:1px solid #238636; border-radius:14px;
            padding:20px 18px; margin:16px 0; text-align:center;
            box-shadow:0 0 0 1px rgba(35, 134, 54, 0.15), 0 0 18px rgba(35, 134, 54, 0.08);
            position: relative;
        }
        .number-card .number {
            font-family: 'Courier New', monospace;
            font-size: 28px;
            font-weight: 900;
            color: #3fb950;
            letter-spacing: 3px;
            text-shadow: 0 0 8px rgba(63, 185, 80, 0.4);
            padding: 6px 0;
        }
        .number-card .number .digit {
            display: inline-block;
            opacity: 0;
            transform: translateY(10px) scale(0.7);
            animation: digitDrop 0.4s ease forwards;
        }
        @keyframes digitDrop {
            to { opacity: 1; transform: translateY(0) scale(1); }
        }
        .copy-btn-mini {
            background: linear-gradient(135deg, #1f6feb, #388bfd);
            border: 1px solid #388bfd;
            color: #fff;
            padding: 6px 12px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 700;
            margin-top: 4px;
            transition: all 0.2s;
            box-shadow: 0 0 10px rgba(31, 111, 235, 0.3);
        }
        .copy-btn-mini:hover {
            background: linear-gradient(135deg, #388bfd, #58a6ff);
            transform: translateY(-1px);
            box-shadow: 0 0 16px rgba(31, 111, 235, 0.5);
        }
        .copy-btn-mini.copied {
            background: linear-gradient(135deg, #238636, #2ea043);
            border-color: #2ea043;
            box-shadow: 0 0 16px rgba(35, 134, 54, 0.5);
        }

        /* ============= AUTO MONITOR STATUS ============= */
        .auto-monitor { display:flex; align-items:center; gap:8px; padding:10px 14px; background:#0d1117; border:1px solid #21262d; border-radius:10px; margin-top:8px; font-size:12px; color:#8b949e; font-weight:600; }
        .auto-monitor .dot { width:8px; height:8px; border-radius:50%; background:#3fb950; animation:pulse-dot 1.5s infinite; }
        @keyframes pulse-dot { 0%,100%{ opacity:1; transform:scale(1);} 50%{ opacity:0.4; transform:scale(1.3);} }
        .auto-monitor.done { color:#3fb950; }
        .auto-monitor.done .dot { background:#3fb950; animation:none; }

        /* ============= OTP COUNTDOWN 120s ============= */
        .otp-countdown { display:inline-block; padding:2px 8px; background:rgba(63, 185, 80, 0.15); border:1px solid #3fb950; color:#3fb950; border-radius:6px; font-size:10px; font-weight:bold; font-family:'Courier New',monospace; margin-right:6px; }
        .otp-countdown.warn { background:rgba(210, 153, 34, 0.15); border-color:#d29922; color:#d29922; }
        .otp-countdown.expired { background:rgba(248, 81, 73, 0.15); border-color:#f85149; color:#f85149; }

        /* ============= OTP PLATFORM SECTIONS ============= */
        .otp-section { margin-bottom:14px; }
        .otp-section-header { display:flex; align-items:center; gap:8px; padding:8px 12px; background:#1c2128; border:1px solid #30363d; border-radius:8px; margin-bottom:6px; cursor:pointer; transition:background 0.15s; }
        .otp-section-header:hover { background:#21262d; border-color:#484f58; }
        .otp-section-header .platform-icon { width:24px; height:24px; border-radius:6px; padding:2px; background:#fff; }
        .otp-section-header .platform-name { font-size:13px; font-weight:700; color:#fff; }
        .otp-section-header .platform-count { font-size:11px; color:#8b949e; margin-right:auto; }
        .otp-section-header .toggle-arrow { color:#8b949e; font-size:12px; transition:transform 0.2s; }
        .otp-section-header.collapsed .toggle-arrow { transform:rotate(-90deg); }
        .otp-section-items { display:flex; flex-direction:column; gap:6px; }
        .otp-section-items.hidden { display:none; }
        body.light .otp-section-header { background:#f6f8fa; border-color:#d0d7de; }
        body.light .otp-section-header .platform-name { color:#1f2328; }

        /* ============= OTP LIST ============= */
        .otp-list { display:flex; flex-direction:column; gap:8px; margin-top:12px; }
        .otp-item {
            background:#1c2128; border:1px solid #30363d; border-radius:10px;
            padding:12px 14px; display:flex; justify-content:space-between; align-items:center;
        }
        .otp-item .otp-code { font-family:'Courier New',monospace; font-size:16px; font-weight:bold; color:#3fb950; }
        .otp-item .otp-info { font-size:11px; color:#8b949e; margin-top:2px; }
        .otp-item .copy-btn { background:transparent; border:1px solid #30363d; color:#58a6ff; padding:4px 10px; border-radius:6px; cursor:pointer; font-size:11px; font-weight:600; }

        .empty-state { text-align:center; padding:30px 16px; color:#8b949e; font-size:13px; }
        .empty-state .icon { font-size:36px; margin-bottom:8px; opacity:0.6; }

        /* ============= STATUS BAR ============= */
        .status { background:#1c2128; border:1px solid #30363d; border-radius:10px; padding:12px 16px; text-align:center; margin-top:14px; color:#8b949e; font-size:13px; font-weight:600; }

        /* ============= THEME TOGGLE ============= */
        .theme-toggle { background:transparent; border:1px solid #30363d; color:#8b949e; padding:6px 10px; border-radius:8px; cursor:pointer; font-size:14px; }
        .theme-toggle:hover { color:#58a6ff; }

        /* ============= LIGHT MODE ============= */
        body.light { background:#f6f8fa !important; color:#1f2328 !important; }
        body.light .app { background:#ffffff !important; }
        body.light .top-bar { background:#ffffff !important; border-bottom-color:#d0d7de !important; }
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
        body.light .number-card { background:#f6f8fa; border-color:#1a7f37; }
        body.light .number-card .number { color:#1a7f37; }

        .footer { text-align:center; padding:20px 16px; color:#484f58; font-size:12px; border-top:1px solid #21262d; }
        body.light .footer { color:#656d76; border-top-color:#d0d7de; }

        /* ============= [الفوتر] تذييل الصفحة ============= */
        .footer-section {
            background: linear-gradient(180deg, #0d1117, #07090d);
            border-top: 1px solid #21262d;
            padding: 0;
            margin-top: 20px;
        }
        .footer-info {
            text-align:center;
            padding: 18px 16px;
            color: #8b949e;
            font-size: 12px;
            font-weight: 600;
        }
        .footer-info strong { color: #58a6ff; }
        body.light .footer-section { background: linear-gradient(180deg, #ffffff, #f6f8fa); border-top-color: #d0d7de; }
        body.light .footer-info { color: #656d76; }

        /* ============= [مودال طلب المساعدة] ============= */
        .modal-overlay {
            display: none;
            position: fixed; inset: 0;
            background: rgba(0,0,0,0.7);
            backdrop-filter: blur(8px);
            z-index: 10000;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .modal-overlay.show { display: flex; animation: fadeIn 0.2s ease; }
        @keyframes fadeIn { from { opacity:0; } to { opacity:1; } }
        .modal-box {
            background: linear-gradient(180deg, #1c2128, #161b22);
            border: 1px solid #30363d;
            border-radius: 16px;
            padding: 24px;
            max-width: 420px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            animation: slideUp 0.3s ease;
        }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        .modal-box h2 { color: #fff; font-size: 18px; margin-bottom: 8px; text-align: center; }
        .modal-box p { color: #8b949e; font-size: 13px; text-align: center; margin-bottom: 18px; }
        .modal-box textarea {
            width: 100%; min-height: 100px;
            background: #0d1117; color: #e6e6e6;
            border: 1px solid #30363d; border-radius: 10px;
            padding: 12px; font-family: 'Cairo', sans-serif; font-size: 14px;
            resize: vertical; outline: none;
        }
        .modal-box textarea:focus { border-color: #1f6feb; }
        .modal-box .modal-actions { display: flex; gap: 10px; margin-top: 16px; }
        .modal-box button {
            flex: 1; padding: 12px; border: none; border-radius: 10px;
            font-family: 'Cairo', sans-serif; font-size: 14px; font-weight: 700; cursor: pointer;
            transition: all 0.2s;
        }
        .modal-box .btn-send { background: linear-gradient(135deg, #238636, #2ea043); color: #fff; }
        .modal-box .btn-send:hover { transform: translateY(-1px); }
        .modal-box .btn-send:disabled { opacity: 0.5; cursor: not-allowed; }
        .modal-box .btn-cancel { background: #30363d; color: #e6e6e6; }
        .modal-box .btn-cancel:hover { background: #484f58; }
        .modal-box .success-msg {
            background: rgba(35, 134, 54, 0.15);
            border: 1px solid #238636;
            color: #3fb950;
            padding: 12px;
            border-radius: 10px;
            text-align: center;
            font-size: 14px;
            margin-top: 12px;
        }

        /* ============= RESPONSIVE ============= */
        @media (max-width:380px) {
            .hero h1 { font-size:20px; }
            .platform-btn { font-size:13px; padding:10px 12px; }
        }
    </style>
</head>
<body>
    <div class="app">
        <!-- HEADER -->
        <div class="top-bar">
            <div class="brand">
                <div class="brand-icon">🚀</div>
                <div class="brand-text">المطري OTP</div>
            </div>
            <div class="top-actions" style="position:relative;">
                <button class="theme-toggle" id="themeToggle" onclick="toggleTheme()">🌙</button>
                <button class="menu-btn" onclick="toggleMenu()">☰</button>
                <div class="dropdown-menu" id="contactMenu">
                    <div class="menu-header">📞 تواصل معنا</div>
                    <a href="{{ owner_link }}" target="_blank">
                        <span class="ico">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="#25D366"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                        </span>
                        <span>تواصل معي على واتساب</span>
                    </a>
                    <a href="{{ wa_group }}" target="_blank">
                        <span class="ico">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="#25D366"><path d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38a9.95 9.95 0 004.74 1.21h.01c5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01A9.825 9.825 0 0012.04 2zm5.45 13.91c-.23.64-1.36 1.24-1.86 1.31-.47.07-1.07.1-1.73-.1-.4-.13-.92-.31-1.59-.62-2.79-1.21-4.61-4.02-4.75-4.21-.14-.18-1.13-1.5-1.13-2.86 0-1.36.71-2.03.96-2.31.25-.28.55-.35.74-.35.19 0 .37 0 .53.01.17.01.4-.06.62.47.23.55.79 1.91.86 2.05.07.14.12.31.02.49-.1.18-.14.29-.28.45-.14.16-.3.36-.42.48-.14.14-.29.3-.12.58.16.28.72 1.19 1.55 1.93 1.07.95 1.97 1.25 2.25 1.39.28.14.44.12.6-.07.16-.19.7-.81.88-1.09.18-.28.37-.23.62-.14.25.09 1.6.75 1.87.89.28.14.46.21.53.32.07.11.07.65-.16 1.29z"/></svg>
                        </span>
                        <span>جروب واتساب الرسمي</span>
                    </a>
                    <a href="https://t.me/jsjsgsjsvh" target="_blank">
                        <span class="ico">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="#26A5E4"><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.479.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>
                        </span>
                        <span>قناة تليجرام</span>
                    </a>
                    <div class="menu-divider"></div>
                    <a href="/learn-more">
                        <span class="ico">📰</span>
                        <span>اعرف المزيد عن الموقع</span>
                    </a>
                    <a href="/announcements">
                        <span class="ico">📢</span>
                        <span>إعلانات الموقع</span>
                    </a>
                    <a href="#" onclick="openHelpModal(); return false;">
                        <span class="ico">🆘</span>
                        <span>طلب مساعدة</span>
                    </a>
                </div>
            </div>
        </div>

        <!-- ✅ [الإصلاح] تم حذف شريط الأخبار من هنا ونقله إلى الفوتر -->

        <!-- MAIN -->
        <div class="main">
            <div class="hero">
                <h1><span class="emoji-float">🚀</span> موقع المطري OTP</h1>
                <p><span class="emoji-wave crown">👑</span> أرقام واتساب سحب أكواد تطوير مطري <span class="emoji-wave crown">👑</span></p>
            </div>

            <div class="section-title"><span class="icon emoji-float">🎯</span> اختر المنصة</div>
            <div class="platforms" id="platformSelector"></div>

            <div class="section-title"><span class="icon emoji-spin">🌍</span> اختر الدولة</div>
            <div class="select-wrap">
                <select id="country" class="form-control" disabled>
                    <option value="">-- اختر المنصة أولاً --</option>
                </select>
            </div>

            <button class="btn-primary" id="getNumberBtn" onclick="getNumber()" disabled>🚀 جلب رقم</button>
            <button class="btn-blue" id="refreshBtn" onclick="refreshNumber()" disabled>🔄 تبديل</button>

            <div id="numberContainer" style="display:none;">
                <div class="number-card">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <span style="font-size:11px; color:#8b949e; font-weight:600;">📞 الرقم</span>
                        <button class="copy-btn-mini" onclick="copyNumber()" id="copyNumBtn">📋 نسخ</button>
                    </div>
                    <div class="number" id="numberDisplay">+</div>
                </div>
                <div id="autoMonitorStatus" class="auto-monitor">
                    <span class="dot"></span> جاري المراقبة التلقائية...
                </div>
            </div>

            <div class="section-title" style="margin-top:24px;"><span class="icon emoji-pulse-soft">📜</span> الأكواد المسحوبة</div>
            <div class="otp-list" id="otpHistory">
                <div class="empty-state">
                    <div class="icon">⏳</div>
                    <div>في انتظار الأكواد...</div>
                </div>
            </div>

            <div class="status" id="status">⚡ اختر المنصة والدولة للبدء</div>
        </div>

        <!-- ✅ [الإصلاح] شريط الأخبار الاحترافي في الفوتر -->
        <div class="footer-section">
            <div class="news-ticker">
                <div class="ticker-content">
                    <span class="ticker-item"><span class="ticker-emoji">🚀</span> مرحباً بك في موقع المطري OTP</span>
                    <span class="ticker-item"><span class="ticker-emoji">⚡</span> أسرع موقع للحصول على الأكواد</span>
                    <span class="ticker-item"><span class="ticker-emoji">💎</span> صُنع بحب بواسطة</span>
                    <span class="ticker-item"><span class="ticker-name">المطري</span> 🔥</span>
                    <span class="ticker-item"><span class="ticker-emoji">🌍</span> دعم 195+ دولة حول العالم</span>
                    <span class="ticker-item"><span class="ticker-emoji">📱</span> واتساب • تيليجرام • فيسبوك • تيك توك</span>
                    <span class="ticker-item"><span class="ticker-emoji">🔔</span> إشعارات فورية لحظة بلحظة</span>
                    <span class="ticker-item"><span class="ticker-emoji">🎯</span> المطور المطري يقدّم لك أفضل تجربة</span>
                    <span class="ticker-item"><span class="ticker-emoji">⭐</span> شكراً لزيارتك</span>
                    <!-- مكرر للتمرير السلس -->
                    <span class="ticker-item"><span class="ticker-emoji">🚀</span> مرحباً بك في موقع المطري OTP</span>
                    <span class="ticker-item"><span class="ticker-emoji">⚡</span> أسرع موقع للحصول على الأكواد</span>
                    <span class="ticker-item"><span class="ticker-emoji">💎</span> صُنع بحب بواسطة</span>
                    <span class="ticker-item"><span class="ticker-name">المطري</span> 🔥</span>
                    <span class="ticker-item"><span class="ticker-emoji">🌍</span> دعم 195+ دولة حول العالم</span>
                    <span class="ticker-item"><span class="ticker-emoji">📱</span> واتساب • تيليجرام • فيسبوك • تيك توك</span>
                    <span class="ticker-item"><span class="ticker-emoji">🔔</span> إشعارات فورية لحظة بلحظة</span>
                    <span class="ticker-item"><span class="ticker-emoji">🎯</span> المطور المطري يقدّم لك أفضل تجربة</span>
                    <span class="ticker-item"><span class="ticker-emoji">⭐</span> شكراً لزيارتك</span>
                </div>
            </div>
            <div class="footer-info">
                <span class="emoji-pulse-soft">💎</span> صُنع بحب <span class="emoji-spin">⚡</span> بواسطة <strong>المطري</strong> <span class="emoji-wave">🔥</span>
                <br><span style="color:#484f58; font-size:11px;">جميع الحقوق محفوظة © 2025</span>
            </div>
        </div>
    </div>

    <!-- ✅ [مودال طلب المساعدة] -->
    <div class="modal-overlay" id="helpModal" onclick="if(event.target===this) closeHelpModal()">
        <div class="modal-box">
            <h2>🆘 طلب مساعدة</h2>
            <p>اشرح مشكلتك وسنرد عليك في أسرع وقت</p>
            <textarea id="helpMessage" placeholder="اكتب رسالتك هنا... مثلاً: أحتاج رقم واتساب سعودي لكن الأرقام لا تظهر"></textarea>
            <div class="modal-actions">
                <button class="btn-cancel" onclick="closeHelpModal()">إلغاء</button>
                <button class="btn-send" id="sendHelpBtn" onclick="sendHelpRequest()">إرسال</button>
            </div>
            <div class="success-msg" id="helpSuccess" style="display:none;">
                ✅ تم إرسال رسالتك بنجاح! سنرد عليك قريباً
            </div>
        </div>
    </div>

    <script>
        const platformLogos = {{ platform_logos | tojson }};
        const platformLogosSmall = {{ platform_logos_small | tojson }};
        const platformNames = {{ platform_names | tojson }};
        const platformGradients = {{ platform_gradients | tojson }};

        function toggleMenu() {
            document.getElementById('contactMenu').classList.toggle('show');
        }

        // ✅ [مودال طلب المساعدة]
        function openHelpModal() {
            document.getElementById('helpModal').classList.add('show');
            document.getElementById('helpMessage').value = '';
            document.getElementById('helpSuccess').style.display = 'none';
        }
        function closeHelpModal() {
            document.getElementById('helpModal').classList.remove('show');
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
        document.addEventListener('click', function(event) {
            const menu = document.getElementById('contactMenu');
            const btn = document.querySelector('.menu-btn');
            if (!menu.contains(event.target) && !btn.contains(event.target)) {
                menu.classList.remove('show');
            }
        });

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

        // [تأثير typewriter] للرقم - يظهر حرف حرف
        function animateNumber(element, text) {
            element.innerHTML = '';
            const chars = text.split('');
            chars.forEach((ch, i) => {
                const span = document.createElement('span');
                span.className = 'digit';
                span.textContent = ch;
                span.style.animationDelay = (i * 0.08) + 's';
                element.appendChild(span);
            });
        }

        async function copyNumber() {
            const num = document.getElementById('numberDisplay').textContent;
            try {
                await navigator.clipboard.writeText(num);
            } catch(e) {}
            const btn = document.getElementById('copyNumBtn');
            btn.classList.add('copied');
            btn.innerHTML = '✅ تم النسخ';
            setTimeout(() => {
                btn.classList.remove('copied');
                btn.innerHTML = '📋 نسخ';
            }, 1800);
        }

        function copyText(text, btn) {
            navigator.clipboard.writeText(text);
            if (btn) {
                const orig = btn.textContent;
                btn.textContent = '✅';
                setTimeout(() => btn.textContent = orig, 1200);
            }
        }

        // 🔔 صوت تنبيه أجمل وأوضح (نغمتين: A5 ثم C6)
        function playNotificationSound() {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const now = ctx.currentTime;
                // نغمة أولى
                const o1 = ctx.createOscillator();
                const g1 = ctx.createGain();
                o1.connect(g1); g1.connect(ctx.destination);
                o1.type = 'sine';
                o1.frequency.setValueAtTime(880, now);
                g1.gain.setValueAtTime(0.0001, now);
                g1.gain.exponentialRampToValueAtTime(0.4, now + 0.02);
                g1.gain.exponentialRampToValueAtTime(0.0001, now + 0.25);
                o1.start(now); o1.stop(now + 0.3);
                // نغمة ثانية (أعلى)
                const o2 = ctx.createOscillator();
                const g2 = ctx.createGain();
                o2.connect(g2); g2.connect(ctx.destination);
                o2.type = 'sine';
                o2.frequency.setValueAtTime(1318, now + 0.18);
                g2.gain.setValueAtTime(0.0001, now + 0.18);
                g2.gain.exponentialRampToValueAtTime(0.4, now + 0.2);
                g2.gain.exponentialRampToValueAtTime(0.0001, now + 0.5);
                o2.start(now + 0.18); o2.stop(now + 0.55);
            } catch(e) {}
        }

        let currentPlatform = '';
        let currentNumber = '';
        let monitorInterval = null;
        let countdownIntervals = {};   // تتبع العدادات
        let allOtpsCache = [];          // أكواد مخزنة محلياً

        function initPlatformSelector() {
            const selector = document.getElementById('platformSelector');
            selector.innerHTML = '';
            // ألوان المنصات
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
                document.getElementById('refreshBtn').disabled = true;
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
                currentNumber = data.number;
                // [تأثير typewriter] يظهر الرقم حرف حرف بخط كبير حلو
                animateNumber(document.getElementById('numberDisplay'), data.number);
                document.getElementById('numberContainer').style.display = 'block';
                document.getElementById('status').textContent = '✅ الرقم جاهز!';
                // 🎯 تشغيل المراقبة التلقائية فوراً
                startMonitoring();
            } else {
                document.getElementById('status').textContent = '❌ لا توجد أرقام متاحة';
            }
        }

        async function refreshNumber() {
            const country = document.getElementById('country').value;
            if (!currentPlatform || !country) return;
            // إيقاف المراقبة القديمة
            stopMonitoring();
            document.getElementById('status').textContent = '⏳ جاري التبديل...';
            const res = await fetch('/api/get_number', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({platform:currentPlatform, country})});
            const data = await res.json();
            if (data.number && data.number !== currentNumber) {
                currentNumber = data.number;
                // [تأثير typewriter] للرقم الجديد
                animateNumber(document.getElementById('numberDisplay'), data.number);
                document.getElementById('status').textContent = '🔄 تم التبديل!';
                // إعادة تشغيل المراقبة
                startMonitoring();
            }
        }

        // 🎯 مراقبة تلقائية (تبدأ بعد جلب الرقم مباشرة)
        function startMonitoring() {
            if (!currentNumber) return;
            if (monitorInterval) clearInterval(monitorInterval);
            const status = document.getElementById('autoMonitorStatus');
            if (status) { status.classList.remove('done'); status.innerHTML = '<span class="dot"></span> جاري المراقبة التلقائية...'; }
            monitorInterval = setInterval(() => {
                fetch('/api/get_otp', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({number:currentNumber})})
                .then(res => res.json()).then(data => {
                    if (data.otp) {
                        const now = new Date().toLocaleString('ar-YE', {timeZone:'Asia/Aden'});
                        addOtpToHistory(currentNumber, data.otp, now, currentPlatform);
                        if (status) { status.classList.add('done'); status.innerHTML = '<span class="dot"></span> ✅ تم استلام الكود!'; }
                        // تشغيل الصوت
                        playNotificationSound();
                        // إيقاف المراقبة (الكود وصل)
                        stopMonitoring();
                    }
                }).catch(()=>{});
            }, 5000);
        }

        function stopMonitoring() {
            if (monitorInterval) { clearInterval(monitorInterval); monitorInterval = null; }
        }

        // ✅ إضافة كود للقائمة (الأحدث أولاً، يحفظ في localStorage)
        function addOtpToHistory(number, otp, timestamp, platform) {
            const container = document.getElementById('otpHistory');
            if (container.querySelector('.empty-state')) container.innerHTML = '';
            const otpId = Date.now() + '_' + Math.random().toString(36).slice(2,8);
            const otpData = {id: otpId, number, otp, timestamp, platform: platform || currentPlatform || 'unknown', otpTime: Date.now()};
            allOtpsCache.unshift(otpData);
            // حفظ في localStorage
            try {
                localStorage.setItem('allOtps', JSON.stringify(allOtpsCache.slice(0, 50)));
            } catch(e) {}
            renderOtpSections();
            startAllCountdowns();
        }

        // 🎯 عداد 120 ثانية لكل كود
        function startAllCountdowns() {
            Object.values(countdownIntervals).forEach(clearInterval);
            countdownIntervals = {};
            document.querySelectorAll('.otp-countdown').forEach(el => {
                if (el.dataset.started) return;
                el.dataset.started = '1';
                const otpId = el.dataset.otpid;
                const otpData = allOtpsCache.find(o => o.id === otpId);
                if (!otpData) return;
                const tick = () => {
                    const elapsed = Math.floor((Date.now() - otpData.otpTime) / 1000);
                    const remaining = 120 - elapsed;
                    if (remaining <= 0) {
                        el.textContent = '⌛ انتهت';
                        el.classList.add('expired');
                        clearInterval(countdownIntervals[otpId]);
                    } else if (remaining <= 30) {
                        el.textContent = `⏱️ ${remaining}s`;
                        el.classList.add('warn');
                    } else {
                        el.textContent = `⏱️ ${remaining}s`;
                    }
                };
                tick();
                countdownIntervals[otpId] = setInterval(tick, 1000);
            });
        }

        // 📂 عرض الأكواد مقسّمة حسب المنصة
        function renderOtpSections() {
            const container = document.getElementById('otpHistory');
            if (!allOtpsCache.length) {
                container.innerHTML = '<div class="empty-state"><div class="icon">⏳</div><div>في انتظار الأكواد...</div></div>';
                return;
            }
            // تجميع حسب المنصة
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
                <div class="otp-section">
                    <div class="otp-section-header" onclick="toggleSection(this)">
                        <img src="${logoUrl}" class="platform-icon" onerror="this.style.display='none'">
                        <span class="platform-name">${name}</span>
                        <span class="platform-count">${items.length} كود</span>
                        <span class="toggle-arrow">▼</span>
                    </div>
                    <div class="otp-section-items">
                        ${items.map(o => `
                        <div class="otp-item">
                            <div>
                                <div class="otp-code">
                                    <span class="otp-countdown" data-otpid="${o.id}">⏱️ 120</span>
                                    🔑 ${o.otp}
                                </div>
                                <div class="otp-info">📞 ${o.number}  •  🕒 ${o.timestamp}</div>
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
            items.classList.toggle('hidden');
            header.classList.toggle('collapsed');
        }

        // تحميل الأكواد المحفوظة من localStorage
        function loadCachedOtps() {
            try {
                const cached = localStorage.getItem('allOtps');
                if (cached) {
                    allOtpsCache = JSON.parse(cached);
                    // فلترة الأكواد اللي عمرها أقل من 24 ساعة
                    const dayAgo = Date.now() - 24*60*60*1000;
                    allOtpsCache = allOtpsCache.filter(o => o.otpTime > dayAgo);
                    if (allOtpsCache.length) renderOtpSections();
                }
            } catch(e) {}
        }

        document.addEventListener('DOMContentLoaded', () => {
            initPlatformSelector();
            loadCachedOtps();
            startAllCountdowns();
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
    font-weight:800; font-size:15px; font-family:'Cairo',sans-serif';
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

@app.route('/')
# ======================
# 🔹 استبدل من هنا 👇
# ======================

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

# ========== الحصول على قائمة الكومبوهات للحذف ==========
def get_all_combos_list():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT platform, country_code, country_name, country_flag FROM combos")
    rows = c.fetchall()
    conn.close()
    return rows

# ========== صفحة الأدمن الجديدة ==========
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        # ===== حذف كومبو =====
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

        # ===== رفع كومبو =====
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
    
    # جلب قائمة الكومبوهات الحالية
    combos = get_all_combos_list()
    return render_template_string(admin_html, combos=combos)

@app.route('/api/countries', methods=['POST'])
def api_countries():
    return jsonify(get_countries_by_platform(request.json.get('platform')))

@app.route('/api/get_number', methods=['POST'])
def api_get_number():
    d = request.json
    nums = get_numbers(d['platform'], d['country'])
    if not nums:
        return jsonify({'number': None})
    # ✅ [الإصلاح] نرجّع الرقم كما هو بدون أي عكس أو تعديل
    return jsonify({'number': nums[0] if nums else None})

@app.route('/api/get_otp', methods=['POST'])
def api_get_otp():
    num = request.json.get('number')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT otp FROM otp_logs WHERE number LIKE ? ORDER BY id DESC LIMIT 1", (f"%{num[-4:]}",))
    row = c.fetchone()
    conn.close()
    return jsonify({'otp': row[0] if row else None})

# ========== ✅ API واحد فقط: جلب جميع الأكواد مرة واحدة (مع caching في المتصفح) ==========
_otp_cache = {'data': None, 'time': 0}
CACHE_DURATION = 30  # ثواني

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
                            full_text = ' '.join(lines)
                            
                            # =============================================
                            # 🧠 الذكاء 1: استخراج الرقم (أي شكل)
                            # =============================================
                            user_number = None
                            last_digits = None
                            country_code = None
                            
                            # 1️⃣ البحث عن أرقام مخفية بصيغة 9567•••••966
                            hidden_match = re.search(r'(\d{3,4})[•*]{2,6}(\d{3,4})', clean)
                            if hidden_match:
                                user_number = hidden_match.group(1) + hidden_match.group(2)
                                last_digits = user_number[-4:]
                                country_code = user_number[:3] if len(user_number) > 3 else None
                            
                            # 2️⃣ البحث عن أي رقم طويل (8-15 رقم)
                            if not user_number:
                                all_numbers = re.findall(r'\b\d{8,15}\b', clean)
                                if all_numbers:
                                    user_number = max(all_numbers, key=len)
                                    last_digits = user_number[-4:]
                                    country_code = user_number[:3] if len(user_number) > 3 else None
                            
                            # 3️⃣ البحث عن أرقام بصيغة 966*****0038
                            if not user_number:
                                star_match = re.search(r'(\d{3})\*{2,6}(\d{3,4})', clean)
                                if star_match:
                                    user_number = star_match.group(1) + star_match.group(2)
                                    last_digits = user_number[-4:]
                                    country_code = user_number[:3]
                            
                            # 4️⃣ البحث عن أرقام بعد الاختصار (WA | 216•••••4642)
                            if not user_number:
                                pipe_match = re.search(r'[A-Z]{2,4}\s*[|]\s*(\d{3,4})[•*]{2,6}(\d{3,4})', clean)
                                if pipe_match:
                                    user_number = pipe_match.group(1) + pipe_match.group(2)
                                    last_digits = user_number[-4:]
                                    country_code = user_number[:3]
                            
                            # 5️⃣ البحث عن أرقام بصيغة #رقم
                            if not user_number:
                                hash_num = re.search(r'#\s*(\d{8,12})', clean)
                                if hash_num:
                                    user_number = hash_num.group(1)
                                    last_digits = user_number[-4:]
                                    country_code = user_number[:3]
                            
                            # =============================================
                            # 🧠 الذكاء 2: استخراج الكود (أي شكل)
                            # =============================================
                            otp = None
                            
                            # 1️⃣ البحث عن كود بصيغة 303-441
                            dash_code = re.search(r'(\d{3})-(\d{3,4})', clean)
                            if dash_code:
                                otp = dash_code.group(1) + dash_code.group(2)
                            
                            # 2️⃣ البحث عن كود مكون من 4-8 أرقام (ذكي)
                            if not otp:
                                all_codes = re.findall(r'\b\d{4,8}\b', clean)
                                if all_codes:
                                    for c in all_codes:
                                        # تجاهل الأرقام التي تشبه الرقم المستخدم
                                        if last_digits and c.endswith(last_digits):
                                            continue
                                        if country_code and c.startswith(country_code):
                                            continue
                                        # تجاهل الأرقام القصيرة جداً
                                        if len(c) >= 4:
                                            otp = c
                                            break
                            
                            # 3️⃣ البحث عن كود بعد "كود" أو "رمز"
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
                            
                            # 4️⃣ البحث عن أي أرقام طويلة (6-8 أرقام) بعد السطر الأول
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
                                    # البحث في كل النص
                                    all_long = re.findall(r'\b\d{6,8}\b', clean)
                                    if all_long:
                                        for n in all_long:
                                            if last_digits and n.endswith(last_digits):
                                                continue
                                            otp = n
                                            break
                            
                            # =============================================
                            # 🧠 الذكاء 3: تحديد المنصة
                            # =============================================
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
                            
                            # محاولة استخراج المنصة من الاختصار الأول
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
                            
                            # =============================================
                            # 🧠 الذكاء 4: حفظ الكود
                            # =============================================
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

# ========== ✅ [بوت تيليجرام] يراقب الجروب ويستقبل الإعلانات ==========
def monitor_telegram_group():
    """يراقب الجروب ويستقبل الإعلانات + أوامر الأدمن"""
    last_update_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
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
                # 📨 رسالة في الجروب (إعلان جديد)
                if chat_type in ('group', 'supergroup', 'channel'):
                    if not text and not msg.get('photo') and not msg.get('video'):
                        continue
                    # تحديد نوع الإعلان
                    ann_type = 'text'
                    media_url = None
                    content = text or ''
                    button_text = None
                    button_url = None
                    # إذا في صورة
                    if msg.get('photo'):
                        ann_type = 'image'
                        # جلب أكبر صورة
                        photo = msg['photo'][-1]
                        file_id = photo['file_id']
                        # جلب رابط الصورة
                        try:
                            file_info = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
                            if file_info.get('ok'):
                                media_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_info['result']['file_path']}"
                        except: pass
                    # إذا في فيديو
                    elif msg.get('video'):
                        ann_type = 'video'
                        try:
                            file_id = msg['video']['file_id']
                            file_info = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
                            if file_info.get('ok'):
                                media_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_info['result']['file_path']}"
                        except: pass
                    # البحث عن زر في النص (صيغة: 🔗 زر | URL)
                    if text:
                        btn_match = re.search(r'\[(.+?)\|(https?://[^\s\]]+)\]', text)
                        if btn_match:
                            button_text = btn_match.group(1)
                            button_url = btn_match.group(2)
                            content = text.replace(btn_match.group(0), '').strip()
                    # حفظ في قاعدة البيانات
                    if content or media_url:
                        conn = sqlite3.connect(DB_PATH)
                        conn.cursor().execute(
                            "INSERT INTO announcements (type, content, media_url, button_text, button_url, source_msg_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (ann_type, content, media_url, button_text, button_url, msg.get('message_id'), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        )
                        conn.commit()
                        conn.close()
                        print(f"✅ [إعلان جديد] {ann_type} | {content[:30]}...")
                        # إرسال إشعار للقروب بأن الإعلان تم نشره في الموقع
                        try:
                            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                                'chat_id': chat_id,
                                'text': f'✅ تم نشر الإعلان في الموقع بنجاح!',
                                'reply_to_message_id': msg.get('message_id')
                            }, timeout=10)
                        except: pass
                # 📩 رسالة خاصة للبوت من الأدمن
                elif chat_type == 'private':
                    if not text:
                        continue
                    if text == '/start':
                        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                            'chat_id': chat_id,
                            'text': '🤖 <b>مرحباً بك في بوت المطري OTP</b>\n\nهذا البوت مربوط بموقع المطري OTP. الإعلانات التي تنشرها في الجروب الرسمي ستظهر تلقائياً في الموقع.\n\n✅ أرسل إعلانك في الجروب وسيظهر فوراً!'
                        }, timeout=10)
                    elif text == '/announcements':
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute("SELECT COUNT(*) FROM announcements")
                        count = c.fetchone()[0]
                        conn.close()
                        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                            'chat_id': chat_id,
                            'text': f'📊 عدد الإعلانات المنشورة في الموقع: <b>{count}</b>'
                        }, timeout=10)
        except Exception as e:
            print(f"❌ خطأ في بوت تيليجرام: {e}")
        time.sleep(3)

threading.Thread(target=monitor_telegram_group, daemon=True).start()

# ========== ✅ نظام الإعلانات (مربوط بالبوت والجروب) ==========
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

# ========== ✅ API طلب مساعدة ==========
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
    # إرسال الرسالة إلى البوت عبر تيليجرام
    try:
        help_text = (
            f"🆘 <b>طلب مساعدة جديد #{help_id}</b>\n\n"
            f"👤 المستخدم: <code>{user_id}</code>\n"
            f"💬 الرسالة:\n{msg}\n\n"
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={
            'chat_id': OWNER_TELEGRAM_ID,
            'text': help_text,
            'parse_mode': 'HTML'
        }, timeout=10)
    except Exception as e:
        print(f"❌ فشل إرسال طلب المساعدة للبوت: {e}")
    return jsonify({'ok': True, 'id': help_id})

# ========== ✅ صفحة الإعلانات ==========
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
.header {
    background: linear-gradient(135deg, #1f6feb, #388bfd);
    padding: 24px 20px; border-radius: 14px; margin-bottom: 20px;
    box-shadow: 0 4px 20px rgba(31, 111, 235, 0.3);
    text-align: center;
}
.header h1 { color:#fff; font-size: 22px; font-weight: 900; margin-bottom: 4px; }
.header p { color: rgba(255,255,255,0.85); font-size: 13px; }
.ann-card {
    background: #1c2128; border: 1px solid #30363d; border-radius: 12px;
    padding: 16px; margin-bottom: 12px;
    transition: all 0.2s;
}
.ann-card:hover { border-color: #58a6ff; transform: translateY(-2px); }
.ann-type {
    display: inline-block; padding: 3px 10px; border-radius: 6px;
    font-size: 11px; font-weight: 700; margin-bottom: 8px;
}
.ann-type.text { background: #1f6feb; color: #fff; }
.ann-type.image { background: #238636; color: #fff; }
.ann-type.video { background: #d29922; color: #fff; }
.ann-content { color: #e6e6e6; font-size: 14px; line-height: 1.6; margin-bottom: 10px; }
.ann-media { max-width: 100%; border-radius: 8px; margin-bottom: 10px; }
.ann-btn {
    display: inline-block; padding: 10px 20px; background: linear-gradient(135deg, #238636, #2ea043);
    color: #fff; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 14px;
}
.ann-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(35, 134, 54, 0.4); }
.ann-time { color: #6e7681; font-size: 11px; margin-top: 8px; }
.empty { text-align: center; padding: 40px 16px; color: #6e7681; }
.back-btn {
    display: inline-block; padding: 10px 20px; background: #30363d; color: #fff;
    text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 14px; margin-bottom: 16px;
}
.back-btn:hover { background: #484f58; }
</style>
</head>
<body>
<div class="container">
    <a href="/" class="back-btn">🔙 العودة للرئيسية</a>
    <div class="header">
        <h1>📢 إعلانات الموقع</h1>
        <p>تابع آخر الإعلانات والتحديثات</p>
    </div>
    <div id="annList">
        <div class="empty">⏳ جاري التحميل...</div>
    </div>
</div>
<script>
async function loadAnnouncements() {
    try {
        const res = await fetch('/api/announcements');
        const data = await res.json();
        const container = document.getElementById('annList');
        if (!data.length) {
            container.innerHTML = '<div class="empty">📭 لا توجد إعلانات حالياً</div>';
            return;
        }
        container.innerHTML = data.map(a => {
            let media = '';
            if (a.type === 'image' && a.media_url) {
                media = `<img src="${a.media_url}" class="ann-media" alt="">`;
            } else if (a.type === 'video' && a.media_url) {
                media = `<video src="${a.media_url}" class="ann-media" controls></video>`;
            }
            const btn = a.button_url ? `<a href="${a.button_url}" target="_blank" class="ann-btn">${a.button_text || 'افتح الرابط'}</a>` : '';
            return `
                <div class="ann-card">
                    <span class="ann-type ${a.type}">${a.type === 'text' ? '📝' : a.type === 'image' ? '🖼️' : '🎥'} ${a.type}</span>
                    ${media}
                    <div class="ann-content">${a.content || ''}</div>
                    ${btn}
                    <div class="ann-time">🕒 ${a.created_at}</div>
                </div>
            `;
        }).join('');
    } catch(e) {
        document.getElementById('annList').innerHTML = '<div class="empty">❌ فشل تحميل الإعلانات</div>';
    }
}
loadAnnouncements();
</script>
</body>
</html>
"""

@app.route('/announcements')
def announcements_page():
    return render_template_string(announcements_html)

# ========== ✅ صفحة "اعرف المزيد عن الموقع" ==========
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
.back-btn {
    display: inline-block; padding: 10px 20px; background: #30363d; color: #fff;
    text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 14px; margin-bottom: 16px;
}
.back-btn:hover { background: #484f58; }
.hero-card {
    background: linear-gradient(135deg, #1f6feb 0%, #6e40c9 100%);
    padding: 30px 24px; border-radius: 16px; margin-bottom: 20px;
    text-align: center; box-shadow: 0 8px 30px rgba(31, 111, 235, 0.4);
}
.hero-card h1 { color: #fff; font-size: 26px; font-weight: 900; margin-bottom: 8px; }
.hero-card p { color: rgba(255,255,255,0.9); font-size: 14px; line-height: 1.6; }
.section { background: #0d1117; border: 1px solid #21262d; border-radius: 14px; padding: 20px; margin-bottom: 16px; }
.section h2 { color: #fff; font-size: 17px; font-weight: 800; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }
.feature { display: flex; gap: 12px; padding: 12px 0; border-bottom: 1px solid #21262d; }
.feature:last-child { border-bottom: none; }
.feature-icon {
    width: 40px; height: 40px; border-radius: 10px;
    background: linear-gradient(135deg, #1f6feb, #388bfd);
    display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0;
}
.feature-text h3 { color: #fff; font-size: 14px; font-weight: 700; margin-bottom: 2px; }
.feature-text p { color: #8b949e; font-size: 12px; line-height: 1.5; }
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 8px; }
.stat { text-align: center; padding: 14px 8px; background: #161b22; border-radius: 10px; }
.stat-num { font-size: 22px; font-weight: 900; color: #58a6ff; }
.stat-label { font-size: 11px; color: #8b949e; margin-top: 2px; }
.cta-box {
    background: linear-gradient(135deg, #238636, #2ea043);
    padding: 20px; border-radius: 14px; text-align: center; margin-bottom: 16px;
}
.cta-box a {
    display: inline-block; padding: 12px 28px; background: #fff; color: #238636;
    text-decoration: none; border-radius: 10px; font-weight: 800; font-size: 15px; margin-top: 8px;
}
</style>
</head>
<body>
<div class="container">
    <a href="/" class="back-btn">🔙 العودة للرئيسية</a>
    <div class="hero-card">
        <h1>🚀 المطري OTP</h1>
        <p>أسرع وأقوى منصة لاستقبال أكواد التحقق من جميع المنصات العالمية</p>
    </div>

    <div class="section">
        <h2>⭐ مميزات الموقع</h2>
        <div class="feature">
            <div class="feature-icon">🌍</div>
            <div class="feature-text">
                <h3>195+ دولة حول العالم</h3>
                <p>نغطي جميع دول العالم بأرقام موثوقة وسريعة</p>
            </div>
        </div>
        <div class="feature">
            <div class="feature-icon">⚡</div>
            <div class="feature-text">
                <h3>استلام فوري للأكواد</h3>
                <p>الأكواد توصلك خلال ثوانٍ من وصولها</p>
            </div>
        </div>
        <div class="feature">
            <div class="feature-icon">🔒</div>
            <div class="feature-text">
                <h3>خصوصية وأمان عالي</h3>
                <p>حماية كاملة لبياناتك بدون تسجيل</p>
            </div>
        </div>
        <div class="feature">
            <div class="feature-icon">📱</div>
            <div class="feature-text">
                <h3>دعم 8 منصات رئيسية</h3>
                <p>واتساب، تيليجرام، فيسبوك، تيك توك، انستقرام، سناب، جوجل، تويتر</p>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>📊 إحصائيات</h2>
        <div class="stats">
            <div class="stat"><div class="stat-num">195+</div><div class="stat-label">دولة</div></div>
            <div class="stat"><div class="stat-num">8</div><div class="stat-label">منصات</div></div>
            <div class="stat"><div class="stat-num">24/7</div><div class="stat-label">دعم</div></div>
        </div>
    </div>

    <div class="cta-box">
        <h2 style="color:#fff; font-size:18px;">🎯 جاهز للبدء؟</h2>
        <p style="color:rgba(255,255,255,0.9); font-size:13px; margin-top:6px;">اختر منصتك واحصل على رقمك الآن</p>
        <a href="/">🚀 ابدأ الآن</a>
    </div>
</div>
</body>
</html>
"""

@app.route('/learn-more')
def learn_more_page():
    return render_template_string(learn_more_html)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)