from flask import Flask, request, render_template_string, jsonify, redirect, url_for, session
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
app.secret_key = "supersecretkey_change_this"
DB_PATH = "bot.db"

# ========== الإعدادات الأساسية ==========
ADMIN_PASSWORD = "admin123"  # كلمة السر للدخول للوحة التحكم
ADMIN_SECRET_PATH = "admin_secret_77" # الرابط السري سيكون /admin_secret_77

WHATSAPP_GROUP_LINK = "https://chat.whatsapp.com/IeK2gNS64fd8YSnenzt4WR"
OWNER_PHONE = "967733723953"
OWNER_LINK = f"https://wa.me/{OWNER_PHONE}"

TELEGRAM_BOT_TOKEN = "8814038881:AAGyuACUYA4YPKlJQhAyUMkpRNiV0u1gNuU"
CHANNEL_USERNAME = "@jsjsgsjsvh"
ASSISTANT_BOT_TOKEN = "8845420882:AAHZ-7qhCL3_ddDT3am4zWNtBRBy3mVDgws"
OWNER_TELEGRAM_ID = "@ABOD_90N"
TELEGRAM_GROUP_INVITE = "https://t.me/ABOD_90N"
ANNOUNCEMENTS_CHANNEL = "https://t.me/ABOD_90N"

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
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, username TEXT, first_name TEXT, last_name TEXT, country_code TEXT, assigned_number TEXT, is_banned INTEGER DEFAULT 0, join_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS site_texts (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS site_links (key TEXT PRIMARY KEY, value TEXT, icon TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS site_settings (key TEXT PRIMARY KEY, value TEXT)''')

    # ========== [جدول التفاعلات] ==========
    c.execute('''CREATE TABLE IF NOT EXISTS announcement_reactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        announcement_id INTEGER NOT NULL,
        user_token TEXT NOT NULL,
        user_name TEXT,
        reaction TEXT NOT NULL,
        created_at TEXT,
        UNIQUE(announcement_id, user_token, reaction)
)''')

    # ========== [جدول التعليقات] ==========
    c.execute('''CREATE TABLE IF NOT EXISTS announcement_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        announcement_id INTEGER NOT NULL,
        user_token TEXT NOT NULL,
        user_name TEXT,
        content TEXT NOT NULL,
        parent_id INTEGER DEFAULT 0,
        is_deleted INTEGER DEFAULT 0,
        created_at TEXT
)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_comments_ann ON announcement_comments(announcement_id, created_at)''')
    
    # إدخال النصوص الافتراضية
    default_texts = {
        'site_title': '🚀 المطري OTP',
        'site_subtitle': '👑 أرقام واتساب سحب أكواد تطوير مطري 👑',
        'btn_get_number': '🚀 جلب رقم',
        'btn_refresh': '🔄 تبديل',
        'btn_start_monitor': '📡 بدء السحب',
        'btn_stop_monitor': '⏹️ إيقاف',
        'footer_text': '💎 صُنع بحب ⚡ بواسطة المطري',
        'ticker_text': '🚀 المطري OTP - أسرع موقع للحصول على الأكواد 💎'
    }
    for key, value in default_texts.items():
        c.execute("INSERT OR IGNORE INTO site_texts (key, value) VALUES (?, ?)", (key, value))
    
    # إدخال الروابط الافتراضية - شعارات SVG رسمية
    default_links = [
        ('whatsapp_developer', OWNER_LINK, 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="48" fill="%2325D366"/><path fill="%23fff" d="M50 18c-17.6 0-32 14.4-32 32 0 6 1.7 11.8 4.8 16.8L18 82l15.6-4.7C38.6 80.1 44.2 82 50 82c17.6 0 32-14.4 32-32S67.6 18 50 18zm18.6 45.6c-.8 2.2-4.6 4.2-6.4 4.5-1.6.3-3.7.4-5.9-.4-1.4-.5-3.1-1.1-5.4-2.2-9.5-4.1-15.7-13.7-16.2-14.3-.5-.7-3.9-5.1-3.9-9.7s2.4-6.9 3.3-7.9c.9-.9 1.9-1.2 2.6-1.2.6 0 1.2 0 1.7 0 .6 0 1.3-.2 2 .1 1.6.7 2.6 3 2.9 3.9.3.9.5 1.5 0 2.4-.4.9-1.5 2.4-2.2 3.4 0 0 .7.7 1.4 1.5 2.4 2.7 5.3 5.5 9.6 7.1 1.5.5 2.3.6 3-.4.6-1 2.5-3 3.2-4 .7-1 1.4-.8 2.3-.5.9.3 5.8 2.7 6.8 3.2 1 .5 1.6.7 1.8 1.1.2.5.2 2.5-.6 4.7z"/></svg>'),
        ('whatsapp_group', WHATSAPP_GROUP_LINK, 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="48" fill="%2325D366"/><path fill="%23fff" d="M50 18c-17.6 0-32 14.4-32 32 0 6 1.7 11.8 4.8 16.8L18 82l15.6-4.7C38.6 80.1 44.2 82 50 82c17.6 0 32-14.4 32-32S67.6 18 50 18zm18.6 45.6c-.8 2.2-4.6 4.2-6.4 4.5-1.6.3-3.7.4-5.9-.4-1.4-.5-3.1-1.1-5.4-2.2-9.5-4.1-15.7-13.7-16.2-14.3-.5-.7-3.9-5.1-3.9-9.7s2.4-6.9 3.3-7.9c.9-.9 1.9-1.2 2.6-1.2.6 0 1.2 0 1.7 0 .6 0 1.3-.2 2 .1 1.6.7 2.6 3 2.9 3.9.3.9.5 1.5 0 2.4-.4.9-1.5 2.4-2.2 3.4 0 0 .7.7 1.4 1.5 2.4 2.7 5.3 5.5 9.6 7.1 1.5.5 2.3.6 3-.4.6-1 2.5-3 3.2-4 .7-1 1.4-.8 2.3-.5.9.3 5.8 2.7 6.8 3.2 1 .5 1.6.7 1.8 1.1.2.5.2 2.5-.6 4.7z"/></svg>'),
        ('telegram_channel', 'https://t.me/jsjsgsjsvh', 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="48" fill="%2326A5E4"/><path fill="%23fff" d="M22 50l50-22-7 48-18-8-7 12-3-17 31-26-37 24-9-4z"/></svg>'),
        ('telegram_group', 'https://t.me/', 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="48" fill="%2326A5E4"/><path fill="%23fff" d="M22 50l50-22-7 48-18-8-7 12-3-17 31-26-37 24-9-4z"/></svg>'),
        ('instagram', 'https://instagram.com/', 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><radialGradient id="ig" cx="30%25" cy="30%25" r="80%25"><stop offset="0%25" stop-color="%23FEDA75"/><stop offset="50%25" stop-color="%23FA7E1E"/><stop offset="100%25" stop-color="%23D62976"/></radialGradient></defs><rect width="100" height="100" rx="22" fill="url(%23ig)"/><rect x="22" y="22" width="56" height="56" rx="14" fill="none" stroke="%23fff" stroke-width="5"/><circle cx="50" cy="50" r="13" fill="none" stroke="%23fff" stroke-width="5"/><circle cx="72" cy="28" r="4" fill="%23fff"/></svg>'),
        ('tiktok', 'https://tiktok.com/', 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="48" fill="%23000"/><path fill="%2325F4EE" d="M62 22c2 8 8 14 16 15v9c-6 0-12-2-16-5v22c0 12-9 20-20 20s-20-8-20-20 9-21 20-21v9c-6 0-11 5-11 12s5 12 11 12 12-6 12-12V22h8z"/><path fill="%23FE2C55" d="M70 22c2 8 8 14 16 15v9c-6 0-12-2-16-5v22c0 12-9 20-20 20v-9c6 0 12-6 12-12V22h8z"/></svg>'),
        ('facebook', 'https://facebook.com/', 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="48" fill="%231877F2"/><path fill="%23fff" d="M58 84V52h10l1-12H58v-7c0-3 1-5 5-5h6V17h-9c-10 0-15 6-15 14v9H36v12h9v32h13z"/></svg>'),
    ]
    for key, value, icon in default_links:
        c.execute("INSERT OR IGNORE INTO site_links (key, value, icon) VALUES (?, ?, ?)", (key, value, icon))
    
    # إدخال إعدادات الموقع
    default_settings = {
        'matrix_enabled': '1',
        'ticker_enabled': '1',
        'main_color': '#00ffc8',
        'secondary_color': '#8b5cf6',
        'background_color': '#0a0e1a',
        'text_color': '#ffffff',
        'sound_enabled': '1',
        'theme_mode': 'dark',
        'platform_order': 'whatsapp,telegram,tiktok,facebook,instagram,snapchat,google,twitter'
    }
    for key, value in default_settings.items():
        c.execute("INSERT OR IGNORE INTO site_settings (key, value) VALUES (?, ?)", (key, value))
    
    # جدول ترتيب المنصات (للحفظ من لوحة التحكم)
    c.execute('''CREATE TABLE IF NOT EXISTS platform_order (platform TEXT PRIMARY KEY, sort_order INTEGER)''')
    
    conn.commit()
    conn.close()
init_db()

def get_text(key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM site_texts WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else ''

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

def get_platform_order():
    """استرجاع ترتيب المنصات من DB"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT platform, sort_order FROM platform_order ORDER BY sort_order ASC")
    rows = c.fetchall()
    conn.close()
    if rows:
        return [r[0] for r in rows]
    # الترتيب الافتراضي
    return ['whatsapp', 'telegram', 'tiktok', 'facebook', 'instagram', 'snapchat', 'google', 'twitter']

def save_platform_order(ordered_list):
    """حفظ ترتيب المنصات في DB"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM platform_order")
    for idx, p in enumerate(ordered_list):
        c.execute("INSERT INTO platform_order (platform, sort_order) VALUES (?, ?)", (p, idx))
    # حفظ نسخة نصية في site_settings للاستخدام من Frontend
    c.execute("REPLACE INTO site_settings (key, value) VALUES (?, ?)", ('platform_order', ','.join(ordered_list)))
    conn.commit()
    conn.close()

def delete_otp(otp_id=None, otp_value=None, all_otps=False):
    """حذف كود واحد أو جميع الأكواد"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        if all_otps:
            c.execute("DELETE FROM otp_logs")
        elif otp_id is not None:
            c.execute("DELETE FROM otp_logs WHERE id=?", (otp_id,))
        elif otp_value is not None:
            # قد يكون هناك عدة سجلات بنفس الكود - نحذف الأحدث فقط
            c.execute("DELETE FROM otp_logs WHERE id IN (SELECT id FROM otp_logs WHERE otp=? ORDER BY id DESC LIMIT 1)", (otp_value,))
        conn.commit()
        # تنظيف الكاش
        global _otp_cache
        if '_otp_cache' in globals():
            _otp_cache['data'] = None
            _otp_cache['time'] = 0
        return True
    except Exception as e:
        print(f"❌ خطأ حذف OTP: {e}")
        return False
    finally:
        conn.close()

def delete_announcement(ann_id):
    """حذف إعلان من جدول الإعلانات"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("DELETE FROM announcements WHERE id=?", (ann_id,))
        # حذف التفاعلات المرتبطة بالإعلان
        c.execute("DELETE FROM announcement_reactions WHERE announcement_id=?", (ann_id,))
        # حذف التعليقات المرتبطة بالإعلان
        c.execute("DELETE FROM announcement_comments WHERE announcement_id=?", (ann_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ خطأ حذف إعلان: {e}")
        return False
    finally:
        conn.close()

# ========== [دوال التفاعلات] ==========
def get_reactions_for_announcement(ann_id):
    """استرجاع كل التفاعلات لإعلان معين + عدد كل نوع"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT reaction, user_token, user_name, created_at FROM announcement_reactions WHERE announcement_id=? ORDER BY id ASC", (ann_id,))
    rows = c.fetchall()
    conn.close()
    return [{'reaction': r[0], 'user_token': r[1], 'user_name': r[2] or 'زائر', 'created_at': r[3]} for r in rows]

def get_reactions_summary(ann_ids):
    """إرجاع ملخص التفاعلات لعدة إعلانات: {ann_id: {reaction: count}}"""
    if not ann_ids:
        return {}
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    placeholder = ','.join('?' for _ in ann_ids)
    c.execute(f"SELECT announcement_id, reaction, COUNT(*) FROM announcement_reactions WHERE announcement_id IN ({placeholder}) GROUP BY announcement_id, reaction", ann_ids)
    rows = c.fetchall()
    conn.close()
    summary = {}
    for ann_id, reaction, count in rows:
        summary.setdefault(ann_id, {})[reaction] = count
    return summary

def toggle_reaction(ann_id, user_token, user_name, reaction):
    """إضافة/إزالة تفاعل. يُرجع True إذا أُضيف، False إذا أُزيل"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT id FROM announcement_reactions WHERE announcement_id=? AND user_token=? AND reaction=?",
                  (ann_id, user_token, reaction))
        existing = c.fetchone()
        if existing:
            c.execute("DELETE FROM announcement_reactions WHERE id=?", (existing[0],))
            conn.commit()
            return False
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO announcement_reactions (announcement_id, user_token, user_name, reaction, created_at) VALUES (?, ?, ?, ?, ?)",
                      (ann_id, user_token, user_name or 'زائر', reaction, now))
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ خطأ تبديل تفاعل: {e}")
        return None
    finally:
        conn.close()

# ========== [دوال التعليقات] ==========
def get_comments_for_announcement(ann_id, include_deleted=False):
    """استرجاع كل تعليقات إعلان (تشمل الردود مرتبة أب+ابن)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if include_deleted:
        c.execute("SELECT id, user_token, user_name, content, parent_id, is_deleted, created_at FROM announcement_comments WHERE announcement_id=? ORDER BY id ASC", (ann_id,))
    else:
        c.execute("SELECT id, user_token, user_name, content, parent_id, is_deleted, created_at FROM announcement_comments WHERE announcement_id=? AND is_deleted=0 ORDER BY id ASC", (ann_id,))
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'user_token': r[1], 'user_name': r[2] or 'زائر', 'content': r[3], 'parent_id': r[4] or 0, 'is_deleted': r[5], 'created_at': r[6]} for r in rows]

def get_comments_summary(ann_ids):
    """عدد التعليقات لكل إعلان: {ann_id: count}"""
    if not ann_ids:
        return {}
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    placeholder = ','.join('?' for _ in ann_ids)
    c.execute(f"SELECT announcement_id, COUNT(*) FROM announcement_comments WHERE announcement_id IN ({placeholder}) AND is_deleted=0 GROUP BY announcement_id", ann_ids)
    rows = c.fetchall()
    conn.close()
    return {ann_id: count for ann_id, count in rows}

def add_comment(ann_id, user_token, user_name, content, parent_id=0):
    """إضافة تعليق جديد. يُرجع ID التعليق أو None عند الفشل"""
    content = (content or '').strip()
    if not content:
        return None
    if len(content) > 500:
        content = content[:500]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO announcement_comments (announcement_id, user_token, user_name, content, parent_id, is_deleted, created_at) VALUES (?, ?, ?, ?, ?, 0, ?)",
                  (ann_id, user_token, user_name or 'زائر', content, int(parent_id or 0), now))
        conn.commit()
        return c.lastrowid
    except Exception as e:
        print(f"❌ خطأ إضافة تعليق: {e}")
        return None
    finally:
        conn.close()

def delete_comment(comment_id, user_token, is_admin=False):
    """حذف تعليق (ناعم). المالك أو الأدمن فقط."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        if is_admin:
            c.execute("SELECT id FROM announcement_comments WHERE id=?", (comment_id,))
            existing = c.fetchone()
            if not existing:
                return False
            c.execute("UPDATE announcement_comments SET is_deleted=1, content='[تم حذف التعليق]' WHERE id=?", (comment_id,))
            conn.commit()
            return True
        else:
            c.execute("SELECT user_token FROM announcement_comments WHERE id=? AND is_deleted=0", (comment_id,))
            row = c.fetchone()
            if not row:
                return False
            if row[0] != user_token:
                return False
            c.execute("UPDATE announcement_comments SET is_deleted=1, content='[تم حذف التعليق]' WHERE id=?", (comment_id,))
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ خطأ حذف تعليق: {e}")
        return False
    finally:
        conn.close()

def is_admin_logged_in():
    return bool(session.get('logged_in'))

def update_text(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("REPLACE INTO site_texts (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def update_link(key, value, icon=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if icon is not None:
        c.execute("REPLACE INTO site_links (key, value, icon) VALUES (?, ?, ?)", (key, value, icon))
    else:
        c.execute("UPDATE site_links SET value=? WHERE key=?", (value, key))
    conn.commit()
    conn.close()

def delete_link(key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM site_links WHERE key=?", (key,))
    conn.commit()
    conn.close()

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

def delete_combo(platform, country_code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM combos WHERE platform=? AND country_code=?", (platform, country_code))
    conn.commit()
    conn.close()

def get_all_combos():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT platform, country_code, country_name, country_flag FROM combos")
    rows = c.fetchall()
    conn.close()
    return rows

# ========== دوال المستخدمين ==========
def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY id DESC")
    users = c.fetchall()
    conn.close()
    return users

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def save_user(user_id, username="", first_name="", last_name="", country_code=None, assigned_number=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    existing = get_user(user_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if existing:
        c.execute("UPDATE users SET last_active=? WHERE user_id=?", (now, user_id))
    else:
        c.execute("INSERT INTO users (user_id, username, first_name, last_name, country_code, assigned_number, join_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (user_id, username, first_name, last_name, country_code, assigned_number, now))
    conn.commit()
    conn.close()

def ban_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_user_otps(user_id, limit=50):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT number, otp, timestamp, platform FROM otp_logs WHERE number IN (SELECT assigned_number FROM users WHERE user_id=?) ORDER BY id DESC LIMIT ?", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

# ========== شعارات SVG ==========
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

platform_colors = {
    'whatsapp': '#25D366',
    'telegram': '#0088cc',
    'tiktok': '#FE2C55',
    'facebook': '#1877F2',
    'instagram': '#E4405F',
    'snapchat': '#FFFC00',
    'google': '#4285F4',
    'twitter': '#000000'
}

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
    c.execute("REPLACE INTO admin_settings (key, value, updated_at) VALUES (?, ?, ?)",
              (key, value, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
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

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ========== HTML الرئيسي ==========
main_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>{{ site_title }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
        html, body { font-family:'Cairo',sans-serif; background:#07090d; color:#c9d1d9; overflow-x:hidden; }
        body { min-height:100vh; }

        /* ============ [ألوان الموقع من قاعدة البيانات] ============ */
        :root {
            --main-color: {{ settings.main_color }};
            --secondary-color: {{ settings.secondary_color }};
            --bg-color: {{ settings.background_color }};
            --text-color: {{ settings.text_color }};
            --card-bg: #1c2128;
            --border-color: #30363d;
            --top-bar-bg: #0d1117;
            --muted-color: #8b949e;
        }
        /* ============ [وضع الليل] ============ */
        body.theme-dark {
            --bg-color: #0a0e1a;
            --text-color: #ffffff;
            --card-bg: #1c2128;
            --border-color: #30363d;
            --top-bar-bg: #0d1117;
            --muted-color: #8b949e;
        }
        /* ============ [وضع النهار] ============ */
        body.theme-light {
            --bg-color: #f5f7fa;
            --text-color: #1a202c;
            --card-bg: #ffffff;
            --border-color: #d1d5db;
            --top-bar-bg: #ffffff;
            --muted-color: #4a5568;
        }
        body.theme-light .brand-text { color: #1a202c !important; }
        body.theme-light .menu-btn { color: #4a5568; border-color: #d1d5db; }
        body.theme-light .dropdown-menu { background: #ffffff; border-color: #d1d5db; }
        body.theme-light .dropdown-menu a { color: #1a202c; }
        body.theme-light .dropdown-menu a:hover { background: rgba(31,111,235,0.08); }
        body.theme-light .platform-btn { background: #ffffff; color: #1a202c; border-color: #d1d5db; }
        body.theme-light .platform-btn:hover { background: #f9fafb; }
        body.theme-light .number-card { background: linear-gradient(135deg, #f0f9ff, #e0e7ff); }
        body.theme-light .otp-item { background: #f9fafb; color: #1a202c; }
        body.theme-light .form-control { background: #ffffff; color: #1a202c; border-color: #d1d5db; }
        body.theme-light .section-title { color: #1a202c; }
        body.theme-light .hero h1 { color: #1a202c; }
        body.theme-light .footer-info { color: #4a5568; }
        body.theme-light .empty-state { color: #4a5568; }
        
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
        }

        .app { 
            max-width:480px; margin:0 auto; 
            background:rgba(13, 17, 23, 0.5); 
            backdrop-filter:blur(2px); 
            min-height:100vh; display:flex; flex-direction:column; 
            position:relative; 
            z-index: 1;
        }

        .top-bar { background:#0d1117; padding:12px 16px; display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid #21262d; position:sticky; top:0; z-index:50; }
        .brand { display:flex; align-items:center; gap:10px; }
        .brand-icon { width:36px; height:36px; border-radius:10px; background:linear-gradient(135deg, #1f6feb, #388bfd); display:flex; align-items:center; justify-content:center; font-size:18px; }
        .brand-text { font-size:16px; font-weight:700; color:#fff; }
        .top-actions { display:flex; gap:8px; align-items:center; }
        .menu-btn { background:transparent; border:1px solid #30363d; color:#8b949e; padding:6px 12px; border-radius:8px; cursor:pointer; font-size:16px; }
        .menu-btn:hover { color:#58a6ff; border-color:#58a6ff; }

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
            gap:6px;
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
            display:flex; align-items:center; gap:10px; color:#c9d1d9; text-decoration:none;
            padding:10px 14px; border-radius:8px; font-size:13px; font-weight:600;
            transition:all 0.3s ease; border:1px solid transparent;
        }
        /* ============ [شعارات القائمة الجانبية] ============ */
        .dropdown-menu .menu-logo {
            width: 22px; height: 22px; object-fit: contain;
            border-radius: 4px; display: block;
            background: #fff; padding: 1px;
        }
        .dropdown-menu a .menu-text { flex: 1; line-height: 1.2; }
        .dropdown-menu a:hover { background:rgba(88,166,255,0.1); color:#58a6ff; border-color:rgba(88,166,255,0.2); }
        .dropdown-menu a .ico { font-size:16px; width:24px; height:24px; display:flex; align-items:center; justify-content:center; background:rgba(88,166,255,0.1); border-radius:4px; flex-shrink:0; }
        .dropdown-menu .menu-divider { height:1px; background:linear-gradient(90deg, transparent, #30363d, transparent); margin:4px 0; }
        .dropdown-menu .menu-header { font-size:10px; color:#8b949e; font-weight:700; padding:4px 12px 2px; text-transform:uppercase; letter-spacing:0.5px; }

        .main { padding:12px 16px; flex:1; }
        .hero { text-align:center; padding:4px 0 8px; }
        .hero h1 { font-size:20px; font-weight:800; color:#fff; }
        .hero p { font-size:12px; color:#8b949e; }

        .section-title { font-size:13px; font-weight:700; color:#fff; margin:8px 0 6px; display:flex; align-items:center; gap:6px; }
        .section-title .icon { color:#58a6ff; }

        .platforms { display:grid; grid-template-columns:repeat(2, 1fr); gap:10px; margin-bottom:4px; }
        .platform-btn {
            display:flex; align-items:center; gap:10px; padding:16px 14px;
            background:#1c2128; border:1px solid #30363d; border-radius:12px;
            color:#e6e6e6; cursor:pointer; transition:all 0.2s ease;
            font-size:15px; font-weight:700; font-family:'Cairo',sans-serif;
            min-height: 60px;
        }
        .platform-btn:hover { background:#21262d; border-color:#484f58; transform:translateY(-2px); }
        .platform-btn:active { transform:scale(0.97); }
        .platform-btn.active { background:var(--platform-color, #1f6feb); border-color:var(--platform-color, #1f6feb); color:#fff; box-shadow:0 0 0 1px var(--platform-color, #1f6feb), 0 0 20px rgba(31,111,235,0.4); transform:translateY(-2px); }
        .platform-btn img { width:38px; height:38px; object-fit:contain; border-radius:8px; background:#fff; padding:3px; }
        .platform-btn .platform-label { flex:1; }
        /* [drag & drop] - للأدمن فقط */
        .platform-btn.dragging { opacity: 0.4; transform: scale(0.95); }
        .platform-btn.drag-over { border-style: dashed; transform: scale(1.05); }
        .admin-mode .platform-btn { cursor: move; position: relative; }
        .admin-mode .platform-btn::after { content: '⋮⋮'; position: absolute; top: 4px; left: 4px; color: rgba(255,255,255,0.4); font-size: 12px; }
        .platform-btn.align-center { justify-content: center; text-align: center; }
        .platform-btn.align-right { justify-content: flex-end; text-align: right; }

        .form-control {
            width:100%; padding:10px 14px; border-radius:8px;
            border:1px solid #30363d; background:#0d1117; color:#e6e6e6;
            outline:none; font-family:'Cairo',sans-serif; font-size:13px; font-weight:600;
            appearance:none; -webkit-appearance:none;
            background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'><path fill='%238b949e' d='M6 9L1 4h10z'/></svg>");
            background-repeat:no-repeat; background-position:left 14px center; padding-left:36px;
        }

        /* ============ [شريط البحث + زر الثيم] ============ */
        .search-row {
            display: flex;
            gap: 8px;
            align-items: stretch;
            margin-bottom: 10px;
        }
        .search-row .form-control {
            flex: 1;
            margin: 0;
        }
        .theme-toggle-btn {
            flex-shrink: 0;
            width: 46px;
            height: 46px;
            border-radius: 12px;
            border: 1px solid #30363d;
            background: linear-gradient(135deg, #1c2128, #21262d);
            color: #ffd54a;
            font-size: 22px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }
        .theme-toggle-btn::before {
            content: '';
            position: absolute;
            inset: 0;
            background: linear-gradient(135deg, rgba(255,213,74,0.15), rgba(139,92,246,0.15));
            opacity: 0;
            transition: opacity 0.3s;
        }
        .theme-toggle-btn:hover { transform: scale(1.06); border-color: #ffd54a; box-shadow: 0 0 14px rgba(255,213,74,0.35); }
        .theme-toggle-btn:hover::before { opacity: 1; }
        .theme-toggle-btn:active { transform: scale(0.95); }
        .theme-toggle-btn .icon-sun { display: none; }
        .theme-toggle-btn .icon-moon { display: block; }
        body.theme-light .theme-toggle-btn {
            background: linear-gradient(135deg, #e0e7ff, #c7d2fe);
            border-color: #6366f1;
            color: #4338ca;
        }
        body.theme-light .theme-toggle-btn .icon-sun { display: block; }
        body.theme-light .theme-toggle-btn .icon-moon { display: none; }
        body.theme-light .theme-toggle-btn:hover { box-shadow: 0 0 14px rgba(99,102,241,0.35); border-color: #4338ca; }
        .theme-toggle-btn .icon { line-height: 1; transition: transform 0.4s ease; }
        .theme-toggle-btn:hover .icon { transform: rotate(20deg) scale(1.1); }
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

        .number-card {
            background: linear-gradient(135deg, #0d1117, #161b22);
            border:1px solid #238636; border-radius:12px;
            padding:14px; margin:10px 0; text-align:center;
        }
        .number-card .number {
            font-family: 'Courier New', monospace;
            font-size: 24px;
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
        .copy-btn-mini.copied { background: linear-gradient(135deg, #238636, #2ea043); border-color: #2ea043; }

        .otp-list { display:flex; flex-direction:column; gap:6px; margin-top:8px; }
        .otp-item {
            background:#1c2128; border:1px solid #30363d; border-radius:8px;
            padding:8px 10px; display:flex; justify-content:space-between; align-items:center;
            gap:4px; flex-wrap:wrap;
        }
        .otp-item .otp-code {
            font-family: 'Courier New', monospace;
            font-size: 15px;
            font-weight: 900;
            color: #ff6b9d;
            background: linear-gradient(135deg, #ff6b9d 0%, #c084fc 50%, #38bdf8 100%);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 1px;
        }
        .otp-item .otp-info { font-size:10px; color:#8b949e; }
        .otp-item .copy-btn { background:transparent; border:1px solid #30363d; color:#58a6ff; padding:3px 8px; border-radius:4px; cursor:pointer; font-size:10px; font-weight:600; }


        .empty-state { text-align:center; padding:20px; color:#8b949e; font-size:12px; }
        .empty-state .icon { font-size:30px; margin-bottom:4px; opacity:0.5; }

        .status { background:#1c2128; border:1px solid #30363d; border-radius:8px; padding:8px 12px; text-align:center; margin-top:8px; color:#8b949e; font-size:12px; font-weight:600; }

        .footer-section { margin-top:10px; padding:0; border-top:1px solid #21262d; }
        .footer-info { text-align:center; padding:10px 16px; color:#8b949e; font-size:11px; font-weight:600; }
        .footer-info strong { color:#58a6ff; }
        
        .news-ticker {
            background: linear-gradient(135deg, #1c2128 0%, #21262d 50%, #1c2128 100%);
            border: 1px solid #30363d;
            padding: 4px 0;
            overflow: hidden;
            position: relative;
            direction: ltr;
            border-radius: 6px;
            margin: 0 16px 4px 16px;
            max-width: calc(100% - 32px);
        }
        .news-ticker::before, .news-ticker::after {
            content: ''; position: absolute; top: 0; bottom: 0; width: 30px; z-index: 2; pointer-events: none;
        }
        .news-ticker::before { left: 0; background: linear-gradient(90deg, #1c2128, transparent); border-radius: 6px 0 0 6px; }
        .news-ticker::after  { right: 0; background: linear-gradient(-90deg, #1c2128, transparent); border-radius: 0 6px 6px 0; }
        .ticker-content {
            display: flex; gap: 40px;
            padding: 0 20px;
            white-space: nowrap;
            animation: tickerScroll 30s linear infinite;
            font-weight: 600; font-size: 11px; color: #c9d1d9;
            align-items: center;
        }
        .ticker-content:hover { animation-play-state: paused; }
        @keyframes tickerScroll {
            0%   { transform: translateX(0); }
            100% { transform: translateX(-50%); }
        }
        .ticker-item { display: inline-flex; align-items: center; gap: 4px; }
        .ticker-emoji { font-size: 12px; }
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
        .modal-overlay.show { display: flex; }
        .modal-box {
            background: linear-gradient(180deg, #1c2128, #161b22);
            border: 1px solid #30363d;
            border-radius: 14px;
            padding: 20px;
            max-width: 380px;
            width: 100%;
        }
        .modal-box h2 { color: #fff; font-size: 17px; margin-bottom: 6px; text-align: center; }
        .modal-box p { color: #8b949e; font-size: 12px; text-align: center; margin-bottom: 12px; }
        .modal-box textarea {
            width: 100%; min-height: 80px;
            background: #0d1117; color: #e6e6e6;
            border: 1px solid #30363d; border-radius: 8px;
            padding: 10px; font-family: 'Cairo', sans-serif; font-size: 13px;
            resize: vertical; outline: none;
        }
        .modal-box textarea:focus { border-color: #1f6feb; }
        .modal-box .modal-actions { display: flex; gap: 8px; margin-top: 12px; }
        .modal-box button {
            flex: 1; padding: 10px; border: none; border-radius: 8px;
            font-family: 'Cairo', sans-serif; font-size: 13px; font-weight: 700; cursor: pointer;
        }
        .modal-box .btn-send { background: linear-gradient(135deg, #238636, #2ea043); color: #fff; }
        .modal-box .btn-cancel { background: #30363d; color: #e6e6e6; }
        .modal-box .success-msg {
            background: rgba(35, 134, 54, 0.15);
            border: 1px solid #238636;
            color: #3fb950;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            font-size: 13px;
            margin-top: 8px;
            display:none;
        }

        @media (max-width:380px) {
            .hero h1 { font-size:17px; }
            .platform-btn { font-size:13px; padding:12px 10px; }
            .platform-btn img { width:32px; height:32px; }
            .number-card .number { font-size:20px; }
        }

        /* ============ [أرقام متساقطة خلف المنصات] قابلة للتشغيل/الإيقاف ============ */
        #platforms-rain-canvas {
            position: absolute;
            inset: 0;
            z-index: -1;
            pointer-events: none;
            opacity: 0.15;
        }

        /* ============ [إشعار رأسي] يظهر من أعلى الشاشة ============ */
        .top-notification {
            position: fixed;
            top: 60px;
            left: 50%;
            transform: translateX(-50%) translateY(-150px);
            background: linear-gradient(135deg, #238636, #2ea043);
            color: #fff;
            padding: 14px 24px;
            border-radius: 12px;
            font-weight: 800;
            font-size: 14px;
            box-shadow: 0 8px 25px rgba(35, 134, 54, 0.5);
            z-index: 100000;
            opacity: 0;
            transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
            pointer-events: none;
            display: flex;
            align-items: center;
            gap: 10px;
            max-width: 90vw;
        }
        .top-notification.show {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
        }
        .top-notification .notif-emoji { font-size: 20px; animation: notifBounce 0.6s ease; }
        @keyframes notifBounce {
            0%,100% { transform: scale(1) rotate(0); }
            50%     { transform: scale(1.3) rotate(15deg); }
        }

        /* ============ [تكبير/تصغير الخط] ============ */
        body.font-small { font-size: 14px; }
        body.font-medium { font-size: 16px; }
        body.font-large { font-size: 18px; }
        body.font-xlarge { font-size: 20px; }

        /* ============ [إعدادات صوت وإشعارات] ============ */
        .font-controls {
            position: fixed;
            bottom: 80px;
            left: 16px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            z-index: 999;
        }


        /* [تايمر تحت الرقم] */
        .otp-timer-below {
            font-size: 12px;
            color: #8b949e;
            margin-top: 4px;
            font-weight: 600;
        }
        .otp-timer-below .blink { animation: timerBlink 1s infinite; }
        @keyframes timerBlink {
            0%,100% { opacity: 1; }
            50%     { opacity: 0.3; }
        }
    </style>
</head>
<body>
    <canvas id="matrix-bg"></canvas>
    <div class="app">
        <div class="top-bar">
            <div class="brand"><div class="brand-icon">🚀</div><div class="brand-text">{{ site_title }}</div></div>
            <div class="top-actions">
                <button class="menu-btn" onclick="toggleMenu()">☰</button>
                <div class="menu-overlay" id="menuOverlay" onclick="toggleMenu()"></div>
                <div class="dropdown-menu" id="contactMenu">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; padding:0 10px;">
                        <div style="font-weight:900; color:#fff; font-size:15px;">🚀 القائمة</div>
                        <button onclick="toggleMenu()" style="background:none; border:none; color:#8b949e; font-size:18px; cursor:pointer;">✕</button>
                    </div>
                    <div class="menu-header">📞 تواصل معنا</div>
                    {% for key, value, icon in links %}
                    <a href="{{ value }}" target="_blank"><span class="ico">{% if icon.startswith('data:image') %}<img src="{{ icon }}" alt="" class="menu-logo">{% else %}{{ icon }}{% endif %}</span><span class="menu-text">{{ key.replace('_', ' ').title() }}</span></a>
                    {% endfor %}
                    <div class="menu-divider"></div>
                    <a href="/announcements"><span class="ico">📢</span><span class="menu-text">إعلانات الموقع</span></a>
                    <a href="#" onclick="openHelpModal(); return false;"><span class="ico">🆘</span><span class="menu-text">طلب مساعدة</span></a>
                </div>
            </div>
        </div>

        <div class="main">
            <div class="hero">
                <h1>{{ site_title }}</h1>
                <p>{{ site_subtitle }}</p>
            </div>

            <div class="section-title"><span class="icon">🎯</span> اختر المنصة</div>
            <div style="position:relative;">
                <canvas id="platforms-rain-canvas"></canvas>
                <div class="platforms" id="platformSelector"></div>
            </div>

            <div class="section-title"><span class="icon">🌍</span> اختر الدولة</div>
            <div class="search-row">
                <select id="country" class="form-control" disabled>
                    <option value="">-- اختر المنصة أولاً --</option>
                </select>
                <button type="button" class="theme-toggle-btn" id="themeToggleBtn" onclick="toggleTheme()" title="تبديل الوضع" aria-label="تبديل الوضع">
                    <span class="icon icon-moon">🌙</span>
                    <span class="icon icon-sun">☀️</span>
                </button>
            </div>

            <button class="btn-primary" id="getNumberBtn" onclick="getNumber()" disabled>{{ btn_get_number }}</button>

            <div id="numberContainer" style="display:none;">
                <div class="number-card">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <span style="font-size:10px; color:#8b949e; font-weight:600;">📞 الرقم</span>
                        <button class="copy-btn-mini" onclick="copyNumber()" id="copyNumBtn">📋 نسخ</button>
                    </div>
                    <div class="number" id="numberDisplay">+</div>
                    <div class="number-countdown-wrap" id="numberCountdown" style="display:flex; align-items:center; justify-content:center; gap:4px; margin-top:6px; padding:4px 10px; background:rgba(99,102,241,0.15); border:1px solid rgba(139,92,246,0.4); border-radius:999px; font-size:11px; font-weight:700; color:#c4b5fd; width:fit-content; margin-left:auto; margin-right:auto; cursor:pointer;" onclick="refreshNumber()">
                        <span>🔄</span> <span>تبديل الرقم التالي</span>
                    </div>
                </div>
                <div id="autoMonitorStatus" style="display:flex; align-items:center; gap:6px; padding:6px 10px; background:#0d1117; border:1px solid #21262d; border-radius:6px; margin-top:6px; font-size:11px; color:#8b949e;">
                    <span class="dot" style="width:6px; height:6px; border-radius:50%; background:#3fb950; animation:pulse-dot 1.5s infinite; display:inline-block;"></span>
                    جاري المراقبة التلقائية...
                </div>
            </div>

            <div class="section-title" style="margin-top:14px;"><span class="icon">📜</span> الأكواد المسحوبة</div>
            <div class="otp-list" id="otpHistory">
                <div class="empty-state"><div class="icon">⏳</div><div>في انتظار الأكواد...</div></div>
            </div>

            <div class="status" id="status">⚡ اختر المنصة والدولة للبدء</div>
        </div>

        <div class="footer-section">
            <div class="news-ticker" id="tickerContainer">
                <div class="ticker-content" id="tickerContent">
                    {{ ticker_text }}
                </div>
            </div>
            <div class="footer-info">{{ footer_text }}</div>
        </div>
    </div>

    <div class="modal-overlay" id="helpModal" onclick="if(event.target===this) closeHelpModal()">
        <div class="modal-box">
            <h2>🆘 طلب مساعدة</h2>
            <p>اشرح مشكلتك وسنرد عليك</p>
            <textarea id="helpMessage" placeholder="اكتب رسالتك هنا..."></textarea>
            <div class="modal-actions">
                <button class="btn-cancel" onclick="closeHelpModal()">إلغاء</button>
                <button class="btn-send" id="sendHelpBtn" onclick="sendHelpRequest()">إرسال</button>
            </div>
            <div class="success-msg" id="helpSuccess">✅ تم إرسال رسالتك!</div>
        </div>
    </div>

    <script>
        const platformLogos = {{ platform_logos | tojson }};
        const platformNames = {{ platform_names | tojson }};
        const platformGradients = {{ platform_gradients | tojson }};
        const platformColors = {{ platform_colors | tojson }};
        const OTP_VALID_SECONDS = 120;

        function toggleMenu() {
            document.getElementById('contactMenu').classList.toggle('show');
            document.getElementById('menuOverlay').classList.toggle('show');
            document.body.style.overflow = document.getElementById('contactMenu').classList.contains('show') ? 'hidden' : '';
        }

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
        document.addEventListener('click', function(event) {
            const menu = document.getElementById('contactMenu');
            const btn = document.querySelector('.menu-btn');
            if (!menu.contains(event.target) && !btn.contains(event.target)) {
                menu.classList.remove('show');
            }
        });

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
        // [نقل تشغيل initMatrix] إلى DOMContentLoaded في الأسفل

        let currentPlatform = '';
        let currentNumber = '';
        let currentNumberIndex = 0;
        let monitorInterval = null;
        let allOtpsCache = [];

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
            // [ترتيب المنصات] - للأدمن تُحفظ في DB، للزوار من الموقع
            let order = ['whatsapp', 'telegram', 'tiktok', 'facebook', 'instagram', 'snapchat', 'google', 'twitter'];
            const serverOrder = '{{ settings.platform_order_csv }}';
            if (serverOrder) order = serverOrder.split(',').map(s => s.trim()).filter(Boolean);
            // محاذاة محفوظة في localStorage (تأثير شخصي للزوار فقط)
            const align = localStorage.getItem('platformAlign') || 'start';
            if (align === 'center') selector.style.justifyItems = 'center';
            else if (align === 'end') selector.style.justifyItems = 'end';

            // [isAdmin] من الخادم (موثوق)، مع تحديث localStorage
            const isAdmin = {{ 'true' if is_admin else 'false' }};
            localStorage.setItem('isAdmin', isAdmin ? '1' : '0');
            if (isAdmin) document.body.classList.add('admin-mode');

            order.filter(p => platformNames[p]).forEach((platform, idx) => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'platform-btn';
                if (align === 'center') btn.classList.add('align-center');
                else if (align === 'end') btn.classList.add('align-right');
                btn.dataset.platform = platform;
                btn.draggable = isAdmin;
                btn.onclick = () => selectPlatform(platform, btn);
                btn.style.setProperty('--platform-color', platformColors[platform] || '#1f6feb');
                btn.innerHTML = `<img src="${platformLogos[platform]}" alt="${platformNames[platform]}"><span class="platform-label">${platformNames[platform]}</span>`;
                // [drag & drop] للأدمن فقط + حفظ في DB
                if (isAdmin) {
                    btn.addEventListener('dragstart', e => {
                        e.dataTransfer.setData('text/plain', platform);
                        e.dataTransfer.effectAllowed = 'move';
                        btn.classList.add('dragging');
                    });
                    btn.addEventListener('dragend', () => {
                        btn.classList.remove('dragging');
                        document.querySelectorAll('.platform-btn.drag-over').forEach(b => b.classList.remove('drag-over'));
                    });
                    btn.addEventListener('dragover', e => {
                        e.preventDefault();
                        e.dataTransfer.dropEffect = 'move';
                        document.querySelectorAll('.platform-btn.drag-over').forEach(b => b.classList.remove('drag-over'));
                        btn.classList.add('drag-over');
                    });
                    btn.addEventListener('dragleave', () => btn.classList.remove('drag-over'));
                    btn.addEventListener('drop', async e => {
                        e.preventDefault();
                        btn.classList.remove('drag-over');
                        const srcPlatform = e.dataTransfer.getData('text/plain');
                        if (srcPlatform && srcPlatform !== platform) {
                            await reorderPlatforms(srcPlatform, platform, selector);
                        }
                    });
                    // [سحب باللمس] للموبايل - ضغط مطوّل ثم سحب
                    attachTouchDrag(btn, selector);
                }
                selector.appendChild(btn);
            });
            // تشغيل الأرقام المتساقطة بعد بناء الأزرار
            if (window.startPlatformsRain) window.startPlatformsRain();
        }

        // ============ [إعادة ترتيب المنصات] (موحّد بين السحب واللمس) ============
        async function reorderPlatforms(srcPlatform, dstPlatform, selector) {
            const cur = Array.from(selector.querySelectorAll('.platform-btn')).map(b => b.dataset.platform);
            const srcIdx = cur.indexOf(srcPlatform);
            const dstIdx = cur.indexOf(dstPlatform);
            if (srcIdx === -1 || dstIdx === -1) return;
            cur.splice(srcIdx, 1);
            cur.splice(dstIdx, 0, srcPlatform);
            // [حفظ في DB] بدلاً من localStorage فقط
            try {
                const res = await fetch('/api/save_platform_order', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({order: cur})
                });
                const data = await res.json();
                if (data.ok) {
                    localStorage.setItem('platformOrder', JSON.stringify(cur));
                    initPlatformSelector();
                    showTopNotification && showTopNotification('✅ تم حفظ ترتيب المنصات');
                } else {
                    alert('❌ فشل حفظ الترتيب: ' + (data.error || ''));
                }
            } catch(err) {
                // fallback لـ localStorage
                localStorage.setItem('platformOrder', JSON.stringify(cur));
                initPlatformSelector();
            }
        }

        // ============ [سحب باللمس للموبايل] (ضغط مطوّل ثم سحب) ============
        function attachTouchDrag(btn, selector) {
            let longPressTimer = null;
            let startX = 0, startY = 0;
            let draggingBtn = null;
            let placeholder = null;
            const LONG_PRESS_MS = 350;

            btn.addEventListener('touchstart', e => {
                if (e.touches.length !== 1) return;
                const t = e.touches[0];
                startX = t.clientX;
                startY = t.clientY;
                longPressTimer = setTimeout(() => {
                    draggingBtn = btn;
                    btn.classList.add('dragging');
                    if (navigator.vibrate) navigator.vibrate(40);
                }, LONG_PRESS_MS);
            }, {passive: true});

            btn.addEventListener('touchmove', e => {
                if (!draggingBtn) {
                    // إلغاء الضغط المطوّل عند التحرّك كثيراً
                    const t = e.touches[0];
                    if (Math.abs(t.clientX - startX) > 8 || Math.abs(t.clientY - startY) > 8) {
                        clearTimeout(longPressTimer);
                    }
                    return;
                }
                e.preventDefault();
                const t = e.touches[0];
                // تحديد الزر الواقع تحته الإصبع
                const elBelow = document.elementFromPoint(t.clientX, t.clientY);
                const targetBtn = elBelow ? elBelow.closest('.platform-btn') : null;
                document.querySelectorAll('.platform-btn.drag-over').forEach(b => b.classList.remove('drag-over'));
                if (targetBtn && targetBtn !== draggingBtn) {
                    targetBtn.classList.add('drag-over');
                }
            }, {passive: false});

            const endDrag = (e) => {
                clearTimeout(longPressTimer);
                if (!draggingBtn) return;
                const t = (e.changedTouches && e.changedTouches[0]) || null;
                let targetBtn = null;
                if (t) {
                    const elBelow = document.elementFromPoint(t.clientX, t.clientY);
                    targetBtn = elBelow ? elBelow.closest('.platform-btn') : null;
                }
                const src = draggingBtn.dataset.platform;
                draggingBtn.classList.remove('dragging');
                document.querySelectorAll('.platform-btn.drag-over').forEach(b => b.classList.remove('drag-over'));
                if (targetBtn && targetBtn !== draggingBtn) {
                    reorderPlatforms(src, targetBtn.dataset.platform, selector);
                }
                draggingBtn = null;
            };
            btn.addEventListener('touchend', endDrag);
            btn.addEventListener('touchcancel', endDrag);
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
            const otpData = {id: Date.now() + '_' + Math.random().toString(36).slice(2,6), number, otp, timestamp, platform: platform || currentPlatform || 'unknown', otpTime: Date.now()};
            allOtpsCache.unshift(otpData);
            try { localStorage.setItem('allOtps', JSON.stringify(allOtpsCache.slice(0, 30))); } catch(e) {}
            renderOtpSections();
            // [إشعار + صوت] عند وصول كود جديد
            try { if (typeof playNotificationSound === 'function') playNotificationSound(); } catch(e) {}
            try { if (typeof showTopNotification === 'function') showTopNotification('كود جديد: ' + otp); } catch(e) {}
        }

        function renderOtpSections() {
            const container = document.getElementById('otpHistory');
            const isAdmin = {{ 'true' if is_admin else 'false' }};
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
                // [زر مسح كل الأكواد] للأدمن فقط
                const clearAllBtn = isAdmin ? `<button onclick="clearAllOtps()" class="clear-all-btn" style="margin-right:auto; background:rgba(239,68,68,0.15); border:1px solid #ef4444; color:#ef4444; padding:2px 6px; border-radius:4px; font-size:10px; cursor:pointer;" title="مسح جميع الأكواد عند كل الزوار">🗑️ مسح الكل</button>` : '';
                html += `
                <div style="margin-bottom:8px;">
                    <div style="display:flex; align-items:center; gap:4px; padding:4px 8px; background:#1c2128; border:1px solid #30363d; border-radius:6px; margin-bottom:4px;">
                        <img src="${logoUrl}" style="width:18px; height:18px; border-radius:4px; padding:2px; background:#fff;" onerror="this.style.display='none'">
                        <span style="font-size:12px; font-weight:700; color:#fff;">${name}</span>
                        <span style="font-size:10px; color:#8b949e; margin-right:auto;">${items.length}</span>
                        ${clearAllBtn}
                    </div>
                    ${items.map(o => {
                        // [زر حذف] للأدمن فقط - ينحذف من كل الأجهزة
                        const deleteBtn = isAdmin ? `<button onclick="deleteOtpFromCache('${o.id || ''}','${o.otp}', this)" class="delete-otp-btn" style="background:rgba(239,68,68,0.15); border:1px solid #ef4444; color:#ef4444; padding:3px 6px; border-radius:4px; font-size:10px; cursor:pointer;" title="حذف من السيرفر وكل الأجهزة">🗑️</button>` : '';
                        return `
                    <div class="otp-item">
                        <div>
                            <div class="otp-code" dir="ltr" style="direction:ltr; unicode-bidi:bidi-override; text-align:left; font-size:14px;">🔑 ${o.otp}</div>
                            <div class="otp-info">📞 ${o.number}</div>
                            <div class="otp-info" style="margin-top:4px;">🕒 ${o.timestamp}</div>
                        </div>
                        <div style="display:flex; gap:4px;">
                            <button class="copy-btn" onclick="copyText('${o.otp}', this)">نسخ</button>
                            <!-- تمت إزالة زر الحذف -->
                        </div>
                    </div>
                    `;}).join('')}
                </div>`;
            });
            container.innerHTML = html;
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

        // ============ [نظام المزامنة مع السيرفر] - يحل مشكلة الأكواد القديمة ============
        // كل 8 ثواني، الزائر يجلب أحدث الأكواد من DB ويتطابق مع localStorage
        // هذا يضمن أن حذف الأدمن ينعكس على كل الأجهزة فورياً
        let syncInterval = null;
        async function syncOtpsWithServer() {
            try {
                const res = await fetch('/api/otps_for_visitor', {cache: 'no-store'});
                const data = await res.json();
                if (!data.ok || !Array.isArray(data.otps)) return;
                // قائمة الأكواد الحالية في السيرفر (الأرقام الفريدة)
                const serverOtps = data.otps.map(o => ({otp: o.otp, id: o.id, number: o.number, platform: o.platform, timestamp: o.timestamp}));
                // قائمة الأكواد المحلية
                const localOtps = allOtpsCache || [];
                if (!localOtps.length && !serverOtps.length) return;
                // خوارزمية المزامنة: اجمع كل الكودات من الاثنين، لكن أزل المكرر الفديم
                // نعتبر المحلي "الرئيسي" لأن فيه otpTime (أحدث) - نضيف الجديد من السيرفر
                const localOtpValues = new Set(localOtps.map(o => o.otp));
                let changed = false;
                // 1) أضف الأكواد الجديدة من السيرفر التي ليست محلية
                serverOtps.forEach(s => {
                    if (!localOtpValues.has(s.otp) && !s.otp.includes('TEST')) {
                        allOtpsCache.unshift({
                            id: 'srv_' + s.id,
                            number: s.number,
                            otp: s.otp,
                            timestamp: s.timestamp,
                            platform: s.platform,
                            otpTime: Date.now()
                        });
                        changed = true;
                    }
                });
                // 2) أزل الأكواد المحلية التي حُذفت من السيرفر (أكثر من 15 ثانية)
                // يعني: إذا كود موجود محلياً وغير موجود في السيرفر = حُذف
                // لكن نعطي هامش 5 ثواني لتأخير التزامن
                const serverOtpValues = new Set(serverOtps.map(o => o.otp));
                const beforeFilter = allOtpsCache.length;
                allOtpsCache = allOtpsCache.filter(o => {
                    // إذا الكود محلي فقط (بدأ بـ id نصي وليس srv_) ولا يوجد في السيرفر = احذفه
                    if (typeof o.id === 'string' && !o.id.startsWith('srv_')) {
                        // كود محلي بحت - فقط احذفه إذا مر أكثر من 20 ثانية ولم يظهر في السيرفر
                        // (يعني: على الأرجح السيرفر أضافه ثم حذفه)
                        if (!serverOtpValues.has(o.otp) && (Date.now() - (o.otpTime || 0)) > 20000) {
                            return false;
                        }
                    }
                    return true;
                });
                if (allOtpsCache.length !== beforeFilter) changed = true;
                // 3) قص لـ 30 كود
                if (allOtpsCache.length > 30) {
                    allOtpsCache = allOtpsCache.slice(0, 30);
                    changed = true;
                }
                if (changed) {
                    try { localStorage.setItem('allOtps', JSON.stringify(allOtpsCache)); } catch(e) {}
                    renderOtpSections();
                }
            } catch(e) { /* صامت - سنحاول مرة أخرى */ }
        }
        function startSyncLoop() {
            if (syncInterval) clearInterval(syncInterval);
            // مزامنة فورية + كل 8 ثواني
            syncOtpsWithServer();
            syncInterval = setInterval(syncOtpsWithServer, 8000);
        }

        // ============ [حذف كود من الواجهة + السيرفر] للأدمن فقط ============
        async function deleteOtpFromCache(otpId, otpValue, btn) {
            if (!confirm('🗑️ حذف هذا الكود من السيرفر وكل الأجهزة؟')) return;
            const original = btn.innerHTML;
            btn.disabled = true; btn.innerHTML = '⏳';
            try {
                // [استخراج id حقيقي] - id قد يكون srv_123 أو رقم
                let realId = null;
                if (otpId && otpId !== 'undefined' && !String(otpId).startsWith('srv_')) {
                    realId = parseInt(otpId);
                } else if (typeof otpId === 'string' && otpId.startsWith('srv_')) {
                    realId = parseInt(otpId.replace('srv_', ''));
                }
                const payload = realId ? {id: realId} : {otp: otpValue};
                const res = await fetch('/api/delete_otp', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.ok) {
                    // حذف فوري محلياً (بدون انتظار المزامنة)
                    allOtpsCache = allOtpsCache.filter(o => o.otp !== otpValue);
                    try { localStorage.setItem('allOtps', JSON.stringify(allOtpsCache.slice(0, 30))); } catch(e) {}
                    renderOtpSections();
                    // تشغيل المزامنة فوراً لتعكس الحذف على الأجهزة الأخرى
                    setTimeout(syncOtpsWithServer, 500);
                } else {
                    alert('❌ فشل الحذف: ' + (data.error || 'غير معروف'));
                    btn.disabled = false; btn.innerHTML = original;
                }
            } catch(e) {
                alert('❌ خطأ في الاتصال');
                btn.disabled = false; btn.innerHTML = original;
            }
        }

        // ============ [مسح جميع الأكواد] للأدمن فقط ============
        async function clearAllOtps() {
            if (!confirm('⚠️ سيتم حذف جميع الأكواد من السيرفر وكل الأجهزة فوراً. متابعة؟')) return;
            try {
                const res = await fetch('/api/clear_all_otps', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                });
                const data = await res.json();
                if (data.ok) {
                    allOtpsCache = [];
                    try { localStorage.removeItem('allOtps'); } catch(e) {}
                    renderOtpSections();
                    // تشغيل المزامنة فوراً
                    setTimeout(syncOtpsWithServer, 500);
                    alert('✅ تم مسح جميع الأكواد من السيرفر');
                } else {
                    alert('❌ فشل: ' + (data.error || 'غير معروف'));
                }
            } catch(e) {
                alert('❌ خطأ في الاتصال');
            }
        }

        // ============ [حذف كود من الواجهة + السيرفر] للأدمن فقط ============
        async function deleteOtpFromCache(otpId, otpValue, btn) {
            if (!confirm('🗑️ حذف هذا الكود؟')) return;
            const original = btn.innerHTML;
            btn.disabled = true; btn.innerHTML = '⏳';
            try {
                const payload = otpId && otpId !== 'undefined' ? {id: parseInt(otpId)} : {otp: otpValue};
                const res = await fetch('/api/delete_otp', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.ok) {
                    allOtpsCache = allOtpsCache.filter(o => o.otp !== otpValue);
                    try { localStorage.setItem('allOtps', JSON.stringify(allOtpsCache.slice(0, 30))); } catch(e) {}
                    renderOtpSections();
                } else {
                    alert('❌ فشل الحذف: ' + (data.error || 'غير معروف'));
                    btn.disabled = false; btn.innerHTML = original;
                }
            } catch(e) {
                alert('❌ خطأ في الاتصال');
                btn.disabled = false; btn.innerHTML = original;
            }
        }

        // ============ [مسح جميع الأكواد] للأدمن فقط ============
        async function clearAllOtps() {
            if (!confirm('⚠️ سيتم حذف جميع الأكواد نهائياً. متابعة؟')) return;
            try {
                const res = await fetch('/api/clear_all_otps', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                });
                const data = await res.json();
                if (data.ok) {
                    allOtpsCache = [];
                    try { localStorage.removeItem('allOtps'); } catch(e) {}
                    renderOtpSections();
                    alert('✅ تم مسح جميع الأكواد');
                } else {
                    alert('❌ فشل: ' + (data.error || 'غير معروف'));
                }
            } catch(e) {
                alert('❌ خطأ في الاتصال');
            }
        }

        // ============ [تبديل الثيم: داكن/فاتح] ============
        const SERVER_THEME = '{{ settings.theme_mode }}';
        let currentTheme = localStorage.getItem('themeMode') || SERVER_THEME || 'dark';
        function applyTheme(t) {
            currentTheme = t;
            document.body.classList.remove('theme-dark', 'theme-light');
            document.body.classList.add('theme-' + t);
            localStorage.setItem('themeMode', t);
            // الزر الجديد (شريط البحث) - الأيقونات تظهر/تختفي تلقائياً عبر CSS
            const btn = document.getElementById('themeToggleBtn');
            if (btn) btn.setAttribute('title', t === 'dark' ? 'التبديل للوضع النهاري' : 'التبديل للوضع الليلي');
        }
        function toggleTheme() {
            applyTheme(currentTheme === 'dark' ? 'light' : 'dark');
        }
        // تطبيق الثيم عند التحميل
        applyTheme(currentTheme);

        // ============ [الصوت] (محفوظ في JS فقط - لم يُطلب نقله للقائمة) ============
        let soundEnabled = localStorage.getItem('soundEnabled') !== '0' && ('{{ settings.sound_enabled }}' !== '0');
        function toggleSound() {
            soundEnabled = !soundEnabled;
            localStorage.setItem('soundEnabled', soundEnabled ? '1' : '0');
            if (soundEnabled && typeof playNotificationSound === 'function') {
                try { playNotificationSound(); } catch(e) {}
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            initPlatformSelector();
            loadCachedOtps();
            initMatrix();
            if (typeof startPlatformsRainSafe === 'function') startPlatformsRainSafe();
            // [نظام المزامنة مع السيرفر] - يحل مشكلة الأكواد القديمة
            startSyncLoop();
        });
    </script>

    <script>
    // ============ [صوت إشعارات] Web Audio API - نغمة مميزة ============
    // [تم نقل تعريف soundEnabled إلى أعلى الكود] (يُعرّف مرة واحدة)
    const audioCtx = (function() {
        try { return new (window.AudioContext || window.webkitAudioContext)(); }
        catch(e) { return null; }
    })();

    function playNotificationSound() {
        if (!soundEnabled || !audioCtx) return;
        try {
            const ctx = audioCtx;
            const now = ctx.currentTime;
            // نغمة 1: 880Hz
            let osc = ctx.createOscillator();
            let gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            osc.frequency.value = 880;
            osc.type = 'sine';
            gain.gain.setValueAtTime(0, now);
            gain.gain.linearRampToValueAtTime(0.2, now + 0.03);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.2);
            osc.start(now); osc.stop(now + 0.22);
            // نغمة 2: 1320Hz بعد 0.12s
            osc = ctx.createOscillator();
            gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            osc.frequency.value = 1320;
            osc.type = 'sine';
            gain.gain.setValueAtTime(0, now + 0.12);
            gain.gain.linearRampToValueAtTime(0.22, now + 0.15);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
            osc.start(now + 0.12); osc.stop(now + 0.37);
            // نغمة 3: 1760Hz بعد 0.25s
            osc = ctx.createOscillator();
            gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            osc.frequency.value = 1760;
            osc.type = 'triangle';
            gain.gain.setValueAtTime(0, now + 0.25);
            gain.gain.linearRampToValueAtTime(0.25, now + 0.28);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.55);
            osc.start(now + 0.25); osc.stop(now + 0.57);
        } catch(e) {}
    }



    // ============ [إشعار رأسي] يظهر من أعلى الشاشة ============
    function showTopNotification(text) {
        const n = document.getElementById('topNotification');
        document.getElementById('topNotifText').textContent = text;
        n.classList.add('show');
        clearTimeout(n._t);
        n._t = setTimeout(() => n.classList.remove('show'), 4000);
    }

    // ============ [تكبير/تصغير الخط] ============
    const fontSizes = ['font-small', 'font-medium', 'font-large', 'font-xlarge'];
    let fontIndex = 1;
    const savedFont = localStorage.getItem('fontSize');
    if (savedFont) {
        fontIndex = fontSizes.indexOf(savedFont);
        if (fontIndex === -1) fontIndex = 1;
    }
    document.body.classList.add(fontSizes[fontIndex]);

    // ============ [أرقام متساقطة خلف المنصات] قابلة للتشغيل/الإيقاف ============
    let platformsRainEnabled = localStorage.getItem('platformsRain') !== '0';
    let rainCanvas, rainCtx, rainDrops = [], rainAnimId;

    function startPlatformsRain() {
        rainCanvas = document.getElementById('platforms-rain-canvas');
        if (!rainCanvas) return;
        const wrap = rainCanvas.parentElement;
        rainCanvas.width = wrap.offsetWidth || 400;
        rainCanvas.height = wrap.offsetHeight || 300;
        rainCtx = rainCanvas.getContext('2d');
        if (rainDrops.length === 0) {
            for (let i = 0; i < 12; i++) {
                rainDrops.push({
                    x: Math.random() * rainCanvas.width,
                    y: Math.random() * rainCanvas.height,
                    speed: 0.3 + Math.random() * 0.7,
                    size: 12 + Math.random() * 8,
                    char: Math.floor(Math.random() * 10)
                });
            }
        }
        if (rainAnimId) cancelAnimationFrame(rainAnimId);
        function draw() {
            if (!platformsRainEnabled) {
                rainCtx.clearRect(0, 0, rainCanvas.width, rainCanvas.height);
                return;
            }
            rainCtx.fillStyle = 'rgba(13, 17, 23, 0.15)';
            rainCtx.fillRect(0, 0, rainCanvas.width, rainCanvas.height);
            rainCtx.fillStyle = '#58a6ff';
            rainCtx.font = '14px Courier New';
            rainDrops.forEach(d => {
                rainCtx.fillText(d.char, d.x, d.y);
                d.y += d.speed;
                if (d.y > rainCanvas.height) {
                    d.y = -10;
                    d.x = Math.random() * rainCanvas.width;
                    d.char = Math.floor(Math.random() * 10);
                }
            });
            rainAnimId = requestAnimationFrame(draw);
        }
        draw();
    }
    // [نقل تشغيل startPlatformsRain] إلى DOMContentLoaded لتجنّب null canvas
    function startPlatformsRainSafe() {
        if (document.getElementById('platforms-rain-canvas')) startPlatformsRain();
    }

    function togglePlatformsRain() {
        platformsRainEnabled = !platformsRainEnabled;
        localStorage.setItem('platformsRain', platformsRainEnabled ? '1' : '0');
        if (platformsRainEnabled) startPlatformsRainSafe();
        else if (rainCtx) rainCtx.clearRect(0, 0, rainCanvas.width, rainCanvas.height);
    }

    // ============ [إشعار + صوت] عند وصول كود جديد ============
    // [تم نقل الاستدعاء داخل addOtpToHistory] - لا حاجة لمنطق window.addOtpToHistory المعقّد
    // (الدالة الأصلية أصبحت تستدعي playNotificationSound و showTopNotification مباشرة)
    </script>

    <!-- [إشعار رأسي] يظهر من أعلى الشاشة عند كود جديد -->
    <div class="top-notification" id="topNotification">
        <span class="notif-emoji">🔔</span>
        <span id="topNotifText">كود جديد!</span>
    </div>

    <!-- [أدوات التحكم] -->
    <div class="font-controls">
    </div>
</body>
</html>
"""

# ========== مسارات الموقع ==========
@app.route('/')
def home():
    site_title = get_text('site_title')
    site_subtitle = get_text('site_subtitle')
    btn_get_number = get_text('btn_get_number')
    btn_refresh = get_text('btn_refresh')
    btn_start_monitor = get_text('btn_start_monitor')
    btn_stop_monitor = get_text('btn_stop_monitor')
    footer_text = get_text('footer_text')
    ticker_text = get_text('ticker_text')
    
    links = get_all_links()
    platforms = get_platforms() or list(platform_names.keys())
    
    # تمرير الإعدادات والألوان والأدمن للقالب
    settings = {
        'main_color': get_setting('main_color') or '#00ffc8',
        'secondary_color': get_setting('secondary_color') or '#8b5cf6',
        'background_color': get_setting('background_color') or '#0a0e1a',
        'text_color': get_setting('text_color') or '#ffffff',
        'sound_enabled': get_setting('sound_enabled') or '1',
        'theme_mode': get_setting('theme_mode') or 'dark',
        'matrix_enabled': get_setting('matrix_enabled') or '1',
        'ticker_enabled': get_setting('ticker_enabled') or '1',
        'platform_order_csv': get_setting('platform_order') or 'whatsapp,telegram,tiktok,facebook,instagram,snapchat,google,twitter'
    }
    is_admin = is_admin_logged_in()
    
    return render_template_string(
        main_html,
        site_title=site_title,
        site_subtitle=site_subtitle,
        btn_get_number=btn_get_number,
        btn_refresh=btn_refresh,
        btn_start_monitor=btn_start_monitor,
        btn_stop_monitor=btn_stop_monitor,
        footer_text=footer_text,
        ticker_text=ticker_text,
        links=links,
        platforms=platforms,
        platform_logos=PLATFORM_LOGOS,
        platform_names=platform_names,
        platform_gradients=PLATFORM_GRADIENTS,
        platform_colors=platform_colors,
        settings=settings,
        is_admin=is_admin
    )

# ========== صفحة الإعلانات ==========
announcements_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>إعلانات الموقع</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Cairo',sans-serif; background:#07090d; color:#c9d1d9; min-height:100vh; }
.container { max-width:480px; margin:0 auto; padding:16px; }
.header { background:linear-gradient(135deg, #1f6feb, #388bfd); padding:20px; border-radius:14px; margin-bottom:16px; text-align:center; }
.header h1 { color:#fff; font-size:20px; font-weight:900; }
.header p { color:rgba(255,255,255,0.85); font-size:12px; }
.ann-card { background:#1c2128; border:1px solid #30363d; border-radius:12px; padding:14px; margin-bottom:10px; }
.ann-card:hover { border-color:#58a6ff; }
.ann-type { display:inline-block; padding:2px 8px; border-radius:4px; font-size:10px; font-weight:700; margin-bottom:6px; }
.ann-type.text { background:#1f6feb; color:#fff; }
.ann-type.image { background:#238636; color:#fff; }
.ann-type.video { background:#d29922; color:#fff; }
.ann-content { color:#e6e6e6; font-size:13px; line-height:1.6; margin-bottom:8px; }
.ann-media { max-width:100%; max-height:200px; border-radius:8px; margin-bottom:8px; object-fit:contain; display:block; margin-left:auto; margin-right:auto; }
.ann-video-wrap video { width:100%; max-height:200px; border-radius:8px; display:block; }
.ann-btn { display:inline-block; padding:8px 16px; background:linear-gradient(135deg, #238636, #2ea043); color:#fff; text-decoration:none; border-radius:8px; font-weight:700; font-size:12px; }
.ann-btn:hover { transform:translateY(-1px); }
.ann-time { color:#6e7681; font-size:10px; margin-top:6px; }
.empty { text-align:center; padding:30px 16px; color:#6e7681; }
.back-btn { display:inline-block; padding:8px 16px; background:#30363d; color:#fff; text-decoration:none; border-radius:8px; font-weight:700; font-size:12px; margin-bottom:12px; }
.back-btn:hover { background:#484f58; }
.ann-delete-btn { position:absolute; top:8px; left:8px; background:rgba(239,68,68,0.15); border:1px solid #ef4444; color:#ef4444; padding:4px 8px; border-radius:6px; font-size:12px; cursor:pointer; font-weight:700; transition:all 0.2s; z-index:5; }
.ann-delete-btn:hover { background:#ef4444; color:#fff; }

/* ============ [أزرار التفاعل] ============ */
.reactions-bar {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid #30363d;
}
.reaction-btn {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 999px;
    padding: 5px 10px;
    font-size: 14px;
    cursor: pointer;
    color: #c9d1d9;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    transition: all 0.2s ease;
    user-select: none;
    -webkit-tap-highlight-color: transparent;
}
.reaction-btn:hover { background:#161b22; border-color:#58a6ff; transform:translateY(-1px); }
.reaction-btn:active { transform:scale(0.92); }
.reaction-btn .emo { font-size:16px; line-height:1; }
.reaction-btn .cnt { font-size:11px; font-weight:700; color:#8b949e; }
.reaction-btn.active {
    background: linear-gradient(135deg, rgba(88,166,255,0.25), rgba(139,92,246,0.18));
    border-color: #58a6ff;
    box-shadow: 0 0 0 1px rgba(88,166,255,0.4), 0 0 10px rgba(88,166,255,0.25);
}
.reaction-btn.active .cnt { color: #58a6ff; }
.reaction-btn.bump { animation: bump 0.4s ease; }
@keyframes bump {
    0% { transform:scale(1); }
    40% { transform:scale(1.25); }
    100% { transform:scale(1); }
}

/* ============ [نافذة كشف المتفاعلين] ============ */
.reactors-modal {
    display: none;
    position: fixed; inset:0;
    background: rgba(0,0,0,0.75);
    backdrop-filter: blur(8px);
    z-index: 10000;
    align-items: center;
    justify-content: center;
    padding: 20px;
}
.reactors-modal.show { display: flex; }
.reactors-box {
    background: linear-gradient(180deg, #1c2128, #161b22);
    border: 1px solid #30363d;
    border-radius: 14px;
    max-width: 380px; width: 100%;
    max-height: 70vh;
    display: flex; flex-direction: column;
    overflow: hidden;
}
.reactors-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 14px 16px;
    border-bottom: 1px solid #30363d;
    background: linear-gradient(135deg, rgba(31,111,235,0.15), transparent);
}
.reactors-header h3 { color:#fff; font-size:15px; font-weight:900; }
.reactors-close {
    background:none; border:none; color:#8b949e;
    font-size:20px; cursor:pointer; padding:0; width:28px; height:28px;
}
.reactors-tabs {
    display: flex; gap: 4px; padding: 8px 12px;
    border-bottom: 1px solid #30363d;
    overflow-x: auto;
    background: #0d1117;
}
.reactors-tab {
    background: transparent;
    border: 1px solid transparent;
    color: #8b949e;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px; font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
    display: inline-flex; align-items: center; gap: 4px;
}
.reactors-tab.active {
    background: rgba(88,166,255,0.15);
    color: #58a6ff;
    border-color: rgba(88,166,255,0.4);
}
.reactors-list {
    padding: 8px;
    overflow-y: auto;
    max-height: 50vh;
}
.reactor-row {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 10px;
    border-radius: 8px;
    transition: background 0.2s;
}
.reactor-row:hover { background: rgba(88,166,255,0.08); }
.reactor-avatar {
    width: 36px; height: 36px;
    border-radius: 50%;
    background: linear-gradient(135deg, #1f6feb, #8b5cf6);
    color: #fff;
    display: flex; align-items: center; justify-content: center;
    font-weight: 900; font-size: 14px;
    flex-shrink: 0;
}
.reactor-info { flex: 1; min-width: 0; }
.reactor-name { color: #fff; font-size: 13px; font-weight: 700; }
.reactor-time { color: #6e7681; font-size: 10px; }
.reactor-emo { font-size: 20px; }
.reactors-empty { text-align:center; padding: 30px; color: #6e7681; font-size: 13px; }

/* ============ [حقل اسم الزائر - أول مرة فقط] ============ */
.name-modal {
    display: none;
    position: fixed; inset:0;
    background: rgba(0,0,0,0.75);
    backdrop-filter: blur(8px);
    z-index: 10001;
    align-items: center; justify-content: center;
    padding: 20px;
}
.name-modal.show { display: flex; }
.name-box {
    background: linear-gradient(180deg, #1c2128, #161b22);
    border: 1px solid #30363d;
    border-radius: 14px;
    padding: 20px;
    max-width: 340px; width: 100%;
    text-align: center;
}
.name-box h3 { color: #fff; font-size: 16px; margin-bottom: 6px; }
.name-box p { color: #8b949e; font-size: 12px; margin-bottom: 12px; }
.name-box input {
    width: 100%; padding: 10px;
    background: #0d1117; color: #fff;
    border: 1px solid #30363d; border-radius: 8px;
    font-family: 'Cairo', sans-serif; font-size: 13px;
    outline: none; text-align: center;
}
.name-box input:focus { border-color: #58a6ff; }
.name-box .name-actions { display: flex; gap: 8px; margin-top: 12px; }
.name-box button {
    flex: 1; padding: 10px; border: none; border-radius: 8px;
    font-family: 'Cairo', sans-serif; font-size: 13px; font-weight: 700; cursor: pointer;
}
.name-box .btn-save { background: linear-gradient(135deg, #238636, #2ea043); color: #fff; }
.name-box .btn-skip { background: #30363d; color: #c9d1d9; }

/* ============ [بطاقة التعليقات] ============ */
.comments-section { margin-top: 10px; padding-top: 10px; border-top: 1px solid #30363d; }
.comments-header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 8px;
}
.comments-header h4 {
    color: #fff; font-size: 13px; font-weight: 800;
    display: flex; align-items: center; gap: 6px;
}
.comments-toggle-btn {
    background: transparent; border: 1px solid #30363d;
    color: #58a6ff; padding: 3px 8px; border-radius: 6px;
    font-size: 11px; font-weight: 700; cursor: pointer;
    display: inline-flex; align-items: center; gap: 4px;
}
.comments-toggle-btn:hover { background: rgba(88,166,255,0.1); }
.comments-count-badge {
    background: rgba(88,166,255,0.15);
    color: #58a6ff;
    border-radius: 999px;
    padding: 1px 8px;
    font-size: 11px;
    font-weight: 800;
    margin-right: 4px;
}
.comment-compose {
    display: flex; gap: 6px; align-items: stretch;
    margin-bottom: 10px;
}
.comment-compose textarea {
    flex: 1; resize: none; min-height: 38px; max-height: 120px;
    background: #0d1117; color: #e6e6e6;
    border: 1px solid #30363d; border-radius: 8px;
    padding: 8px 10px; font-family: 'Cairo', sans-serif; font-size: 12px;
    outline: none;
}
.comment-compose textarea:focus { border-color: #58a6ff; }
.comment-send-btn {
    background: linear-gradient(135deg, #238636, #2ea043);
    color: #fff; border: none; border-radius: 8px;
    padding: 0 14px; font-size: 12px; font-weight: 800;
    cursor: pointer; font-family: 'Cairo', sans-serif;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}
.comment-send-btn:hover:not(:disabled) { filter: brightness(1.1); }
.comment-send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.comments-list { display: flex; flex-direction: column; gap: 6px; }
.comment-item {
    background: #0d1117; border: 1px solid #30363d; border-radius: 8px;
    padding: 8px 10px; display: flex; gap: 8px; align-items: flex-start;
}
.comment-item.is-reply {
    margin-right: 28px;
    background: #11161d;
    border-color: #21262d;
}
.comment-avatar {
    width: 30px; height: 30px; border-radius: 50%;
    background: linear-gradient(135deg, #1f6feb, #8b5cf6);
    color: #fff; font-weight: 900; font-size: 12px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}
.comment-body { flex: 1; min-width: 0; }
.comment-meta { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
.comment-author { color: #fff; font-size: 12px; font-weight: 800; }
.comment-time { color: #6e7681; font-size: 10px; }
.comment-text { color: #c9d1d9; font-size: 12px; line-height: 1.5; word-wrap: break-word; }
.comment-text.deleted { color: #6e7681; font-style: italic; }
.comment-actions {
    display: flex; gap: 8px; margin-top: 4px;
}
.comment-action-btn {
    background: none; border: none; color: #58a6ff;
    font-size: 10px; font-weight: 700; cursor: pointer;
    padding: 0; font-family: 'Cairo', sans-serif;
}
.comment-action-btn:hover { text-decoration: underline; }
.comment-action-btn.danger { color: #ef4444; }
.comment-reply-form { margin-top: 6px; display: none; }
.comment-reply-form.show { display: flex; gap: 6px; }
.comment-reply-form input {
    flex: 1; background: #0d1117; color: #e6e6e6;
    border: 1px solid #30363d; border-radius: 6px;
    padding: 6px 8px; font-family: 'Cairo', sans-serif; font-size: 11px;
    outline: none;
}
.comment-reply-form input:focus { border-color: #58a6ff; }
.comment-reply-form button {
    background: linear-gradient(135deg, #1f6feb, #388bfd);
    color: #fff; border: none; border-radius: 6px;
    padding: 0 10px; font-size: 11px; font-weight: 700;
    cursor: pointer; font-family: 'Cairo', sans-serif;
}
.comment-reply-form button.cancel { background: #30363d; }
.comments-empty {
    text-align: center; color: #6e7681; font-size: 11px;
    padding: 12px; background: rgba(13,17,23,0.4);
    border: 1px dashed #30363d; border-radius: 8px;
}
.comments-loading { text-align: center; color: #6e7681; font-size: 11px; padding: 8px; }
</style>
</head>
<body>
<div class="container">
    <a href="/" class="back-btn">🔙 العودة</a>
    <div class="header"><h1>📢 إعلانات الموقع</h1><p>آخر الإعلانات والتحديثات</p></div>
    <div id="annList"><div class="empty">⏳ جاري التحميل...</div></div>
</div>

<!-- نافذة كشف المتفاعلين -->
<div class="reactors-modal" id="reactorsModal" onclick="if(event.target===this) closeReactors()">
    <div class="reactors-box">
        <div class="reactors-header">
            <h3 id="reactorsTitle">❤️ المتفاعلون</h3>
            <button class="reactors-close" onclick="closeReactors()">✕</button>
        </div>
        <div class="reactors-tabs" id="reactorsTabs"></div>
        <div class="reactors-list" id="reactorsList"></div>
    </div>
</div>

<!-- نافذة طلب الاسم (أول تفاعل فقط) -->
<div class="name-modal" id="nameModal" onclick="if(event.target===this) cancelNamePrompt()">
    <div class="name-box">
        <h3>👋 مرحباً!</h3>
        <p>أدخل اسمك ليظهر مع تفاعلك (اختياري)</p>
        <input type="text" id="nameInput" placeholder="مثلاً: أحمد" maxlength="30">
        <div class="name-actions">
            <button class="btn-skip" onclick="cancelNamePrompt()">تخطي</button>
            <button class="btn-save" onclick="saveNameAndReact()">حفظ وتفاعل</button>
        </div>
    </div>
</div>

<script>
const isAdmin = {{ 'true' if is_admin else 'false' }};

// ============ [معرّف الزائر] (يُحفظ في localStorage) ============
function getUserToken() {
    let token = localStorage.getItem('userToken');
    if (!token) {
        token = 'u_' + Date.now() + '_' + Math.random().toString(36).slice(2, 10);
        localStorage.setItem('userToken', token);
    }
    return token;
}
function getUserName() {
    return localStorage.getItem('userName') || '';
}

// ============ [تعريفات التفاعلات] ============
const REACTION_DEFS = {
    heart: { emoji: '❤️', label: 'حب' },
    fire:  { emoji: '🔥', label: 'رائع' },
    star:  { emoji: '⭐', label: 'مميز' },
    like:  { emoji: '👍', label: 'إعجاب' },
    clap:  { emoji: '👏', label: 'تصفيق' },
    wow:   { emoji: '😮', label: 'واو' }
};

// ============ [كاش التفاعلات] ============
const reactionsCache = {}; // {ann_id: {reaction: count, my: ['heart', ...], users: [...]}}

// ============ [كاش التعليقات] ============
const commentsCache = {};        // {ann_id: [comments]}
const commentsCountCache = {};   // {ann_id: number}
const openComments = {};         // {ann_id: true/false}
const replyOpen = {};            // {comment_id: true/false}

function getMyReactions(annId) {
    const c = reactionsCache[annId];
    return c ? (c.my || []) : [];
}

function getReactionCount(annId, type) {
    const c = reactionsCache[annId];
    return c && c.counts ? (c.counts[type] || 0) : 0;
}

// ============ [تحميل الإعلانات] ============
async function loadAnnouncements() {
    try {
        const res = await fetch('/api/announcements');
        const data = await res.json();
        const container = document.getElementById('annList');
        if (!data.length) { container.innerHTML = '<div class="empty">📭 لا توجد إعلانات</div>'; return; }
        // جلب التفاعلات وعدّاد التعليقات لكل إعلان بالتوازي
        await Promise.all(data.map(a => Promise.all([loadReactions(a.id), loadCommentsCount(a.id)])));
        container.innerHTML = data.map(renderAnnouncement).join('');
    } catch(e) { document.getElementById('annList').innerHTML = '<div class="empty">❌ فشل التحميل</div>'; }
}

async function loadReactions(annId) {
    try {
        const res = await fetch('/api/reactions?announcement_id=' + annId);
        const data = await res.json();
        if (data.ok) {
            const myToken = getUserToken();
            const reactions = data.reactions || [];
            const counts = {};
            const my = [];
            reactions.forEach(r => {
                counts[r.reaction] = (counts[r.reaction] || 0) + 1;
                if (r.user_token === myToken) my.push(r.reaction);
            });
            reactionsCache[annId] = { counts, my, users: reactions };
        }
    } catch(e) {}
}

function renderAnnouncement(a) {
    let media = '';
    if (a.type === 'image' && a.media_url) {
        media = `<img src="${a.media_url}" class="ann-media" loading="lazy">`;
    } else if (a.type === 'video' && a.media_url) {
        media = `<div class="ann-video-wrap"><video src="${a.media_url}" controls preload="metadata"></video></div>`;
    }
    const btn = a.button_url ? `<a href="${a.button_url}" target="_blank" class="ann-btn">${a.button_text || 'افتح'}</a>` : '';
    const deleteBtn = isAdmin ? `<button onclick="deleteAnn(${a.id})" class="ann-delete-btn" title="حذف">🗑️</button>` : '';

    // أزرار التفاعل
    const reactionBtns = Object.keys(REACTION_DEFS).map(key => {
        const def = REACTION_DEFS[key];
        const count = getReactionCount(a.id, key);
        const isActive = getMyReactions(a.id).includes(key);
        return `<button class="reaction-btn ${isActive ? 'active' : ''}" data-ann="${a.id}" data-reaction="${key}" onclick="onReactionClick(${a.id}, '${key}', this)"><span class="emo">${def.emoji}</span>${count > 0 ? `<span class="cnt">${count}</span>` : ''}</button>`;
    }).join('');

    const totalReactions = Object.values(reactionsCache[a.id]?.counts || {}).reduce((s, v) => s + v, 0);
    const seeAll = totalReactions > 0 ? `<button class="reaction-btn" onclick="openReactors(${a.id})" style="background:transparent; border-color:transparent; color:#58a6ff; padding:5px 8px;" title="عرض المتفاعلين">عرض الكل (${totalReactions}) 👀</button>` : '';

    // [التعليقات] - عدّاد + زر الفتح
    const commentsCount = commentsCountCache[a.id] || 0;
    const isOpen = openComments[a.id] === true;

    return `<div class="ann-card" id="ann-${a.id}" style="position:relative;"><span class="ann-type ${a.type}">${a.type}</span>${media}<div class="ann-content">${a.content || ''}</div>${btn}<div class="ann-time">🕒 ${a.created_at}</div>${deleteBtn}<div class="reactions-bar">${reactionBtns}${seeAll}<button class="reaction-btn comments-toggle-btn" onclick="toggleCommentsSection(${a.id})" style="margin-right:auto;"><span>💬</span><span>تعليقات</span>${commentsCount > 0 ? `<span class="comments-count-badge">${commentsCount}</span>` : ''}</button></div><div class="comments-section" id="comments-section-${a.id}" style="display:${isOpen ? 'block' : 'none'};"><div class="comment-compose"><textarea id="comment-input-${a.id}" placeholder="اكتب تعليقاً..." maxlength="500" rows="1"></textarea><button class="comment-send-btn" onclick="submitComment(${a.id}, this)">إرسال</button></div><div class="comments-list" id="comments-list-${a.id}">${isOpen ? '<div class="comments-loading">⏳ جاري التحميل...</div>' : ''}</div></div></div>`;
}

// ============ [التعامل مع ضغط التفاعل] ============
let pendingReaction = null; // {annId, type, btn}

function onReactionClick(annId, type, btn) {
    const myName = getUserName();
    if (!myName) {
        // أول مرة - نطلب الاسم
        pendingReaction = { annId, type, btn };
        document.getElementById('nameModal').classList.add('show');
        setTimeout(() => document.getElementById('nameInput').focus(), 200);
        return;
    }
    submitReaction(annId, type, btn, myName);
}

async function submitReaction(annId, type, btn, userName) {
    if (btn) btn.disabled = true;
    try {
        const res = await fetch('/api/reaction', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                announcement_id: annId,
                reaction: type,
                user_token: getUserToken(),
                user_name: userName || 'زائر'
            })
        });
        const data = await res.json();
        if (data.ok && data.reactions) {
            // تحديث الكاش
            const myToken = getUserToken();
            const counts = {};
            const my = [];
            data.reactions.forEach(r => {
                counts[r.reaction] = (counts[r.reaction] || 0) + 1;
                if (r.user_token === myToken) my.push(r.reaction);
            });
            reactionsCache[annId] = { counts, my, users: data.reactions };
            // إعادة رسم البطاقة بشكل كامل (أبسط وأضمن)
            const card = document.getElementById('ann-' + annId);
            if (card) {
                // نبض على الزر الحالي قبل الاستبدال
                if (btn && btn.parentNode) {
                    btn.classList.add('bump');
                    setTimeout(() => { try { btn.classList.remove('bump'); } catch(e){} }, 400);
                }
                // إعادة بناء البطاقة
                const annType = card.querySelector('.ann-type')?.textContent.trim() || 'text';
                const annContent = card.querySelector('.ann-content')?.innerHTML || '';
                const annMedia = card.querySelector('img, video')?.src || '';
                const annTime = card.querySelector('.ann-time')?.textContent.replace('🕒 ','') || '';
                const annBtn = card.querySelector('.ann-btn');
                const newHtml = renderAnnouncement({
                    id: annId,
                    type: annType,
                    content: annContent,
                    media_url: annMedia,
                    created_at: annTime,
                    button_url: annBtn?.getAttribute('href') || '',
                    button_text: annBtn?.textContent || ''
                });
                // إدراج البديل
                const tmp = document.createElement('div');
                tmp.innerHTML = newHtml;
                const newCard = tmp.firstElementChild;
                if (newCard) card.replaceWith(newCard);
            }
        } else {
            alert('❌ فشل: ' + (data.error || 'غير معروف'));
        }
    } catch(e) { alert('❌ خطأ في الاتصال'); }
    if (btn) btn.disabled = false;
}

function saveNameAndReact() {
    const name = document.getElementById('nameInput').value.trim();
    if (name) localStorage.setItem('userName', name);
    document.getElementById('nameModal').classList.remove('show');
    document.getElementById('nameInput').value = '';
    if (pendingReaction) {
        submitReaction(pendingReaction.annId, pendingReaction.type, pendingReaction.btn, name || 'زائر');
        pendingReaction = null;
    }
}
function cancelNamePrompt() {
    document.getElementById('nameModal').classList.remove('show');
    document.getElementById('nameInput').value = '';
    if (pendingReaction) {
        submitReaction(pendingReaction.annId, pendingReaction.type, pendingReaction.btn, 'زائر');
        pendingReaction = null;
    }
}

// ============ [نافذة كشف المتفاعلين] ============
let currentReactorsAnn = null;
let currentFilter = 'all';

async function openReactors(annId) {
    currentReactorsAnn = annId;
    currentFilter = 'all';
    await loadReactions(annId);
    const cache = reactionsCache[annId];
    if (!cache) return;
    // بناء التبويبات
    const tabsEl = document.getElementById('reactorsTabs');
    let tabsHtml = `<button class="reactors-tab active" data-filter="all" onclick="filterReactors('all')">الكل (${cache.users.length})</button>`;
    Object.keys(cache.counts).forEach(key => {
        const def = REACTION_DEFS[key];
        if (def) {
            tabsHtml += `<button class="reactors-tab" data-filter="${key}" onclick="filterReactors('${key}')">${def.emoji} ${cache.counts[key]}</button>`;
        }
    });
    tabsEl.innerHTML = tabsHtml;
    document.getElementById('reactorsTitle').textContent = '👀 المتفاعلون';
    renderReactors();
    document.getElementById('reactorsModal').classList.add('show');
}
function closeReactors() {
    document.getElementById('reactorsModal').classList.remove('show');
    currentReactorsAnn = null;
}
function filterReactors(filter) {
    currentFilter = filter;
    document.querySelectorAll('.reactors-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.filter === filter);
    });
    renderReactors();
}
function renderReactors() {
    const list = document.getElementById('reactorsList');
    if (!currentReactorsAnn) return;
    const cache = reactionsCache[currentReactorsAnn];
    if (!cache || !cache.users.length) {
        list.innerHTML = '<div class="reactors-empty">لا يوجد متفاعلون بعد 😔</div>';
        return;
    }
    let users = cache.users;
    if (currentFilter !== 'all') {
        users = users.filter(u => u.reaction === currentFilter);
    }
    if (!users.length) {
        list.innerHTML = '<div class="reactors-empty">لا يوجد متفاعلون بهذا التفاعل</div>';
        return;
    }
    list.innerHTML = users.map(u => {
        const def = REACTION_DEFS[u.reaction] || { emoji: '✨' };
        const initials = (u.user_name || 'زائر').slice(0, 2);
        return `<div class="reactor-row">
            <div class="reactor-avatar">${escapeHtml(initials)}</div>
            <div class="reactor-info">
                <div class="reactor-name">${escapeHtml(u.user_name || 'زائر')}</div>
                <div class="reactor-time">${u.created_at || ''}</div>
            </div>
            <div class="reactor-emo">${def.emoji}</div>
        </div>`;
    }).join('');
}
function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// ============ [التعليقات] - كاش + دوال ============
async function loadCommentsCount(annId) {
    try {
        const res = await fetch('/api/comments?announcement_id=' + annId);
        const data = await res.json();
        if (data.ok) {
            commentsCache[annId] = data.comments || [];
            commentsCountCache[annId] = (data.comments || []).filter(c => !c.is_deleted).length;
        }
    } catch(e) {}
}

async function loadComments(annId) {
    const list = document.getElementById('comments-list-' + annId);
    if (!list) return;
    list.innerHTML = '<div class="comments-loading">⏳ جاري التحميل...</div>';
    try {
        const res = await fetch('/api/comments?announcement_id=' + annId);
        const data = await res.json();
        if (data.ok) {
            commentsCache[annId] = data.comments || [];
            commentsCountCache[annId] = (data.comments || []).filter(c => !c.is_deleted).length;
            renderComments(annId);
            updateCommentsBadge(annId);
        } else {
            list.innerHTML = '<div class="comments-empty">❌ فشل التحميل</div>';
        }
    } catch(e) {
        list.innerHTML = '<div class="comments-empty">❌ خطأ في الاتصال</div>';
    }
}

function renderComments(annId) {
    const list = document.getElementById('comments-list-' + annId);
    if (!list) return;
    const all = commentsCache[annId] || [];
    if (!all.length) {
        list.innerHTML = '<div class="comments-empty">💬 لا توجد تعليقات بعد. كن أول من يعلق!</div>';
        return;
    }
    // افصل الآباء عن الردود
    const parents = all.filter(c => !c.parent_id);
    const replies = all.filter(c => c.parent_id);
    const myToken = getUserToken();
    let html = '';
    parents.forEach(p => {
        html += renderCommentItem(p, myToken, false);
        // الردود على هذا التعليق
        const childReplies = replies.filter(r => r.parent_id === p.id);
        childReplies.forEach(r => {
            html += renderCommentItem(r, myToken, true);
        });
    });
    list.innerHTML = html;
}

function renderCommentItem(c, myToken, isReply) {
    const def = REACTION_DEFS.like;
    const initials = (c.user_name || 'زائر').slice(0, 2);
    const isMine = c.user_token === myToken;
    const canDelete = isMine || isAdmin;
    const deletedClass = c.is_deleted ? 'deleted' : '';
    const replyFormId = 'reply-form-' + c.id;
    const isReplyOpen = replyOpen[c.id] === true;
    return `<div class="comment-item ${isReply ? 'is-reply' : ''}" id="comment-${c.id}">
        <div class="comment-avatar">${escapeHtml(initials)}</div>
        <div class="comment-body">
            <div class="comment-meta">
                <span class="comment-author">${escapeHtml(c.user_name || 'زائر')}</span>
                <span class="comment-time">${escapeHtml(c.created_at || '')}</span>
            </div>
            <div class="comment-text ${deletedClass}">${escapeHtml(c.content)}</div>
            ${c.is_deleted ? '' : `
            <div class="comment-actions">
                ${!isReply ? `<button class="comment-action-btn" onclick="toggleReplyForm(${c.announcement_id || 0}, ${c.id})">↩️ رد</button>` : ''}
                ${canDelete ? `<button class="comment-action-btn danger" onclick="deleteComment(${c.announcement_id || 0}, ${c.id})">🗑️ حذف</button>` : ''}
            </div>
            <div class="comment-reply-form ${isReplyOpen ? 'show' : ''}" id="${replyFormId}">
                <input type="text" id="reply-input-${c.id}" placeholder="اكتب رداً..." maxlength="500" onkeydown="if(event.key==='Enter')submitReply(${c.announcement_id || 0}, ${c.id})">
                <button onclick="submitReply(${c.announcement_id || 0}, ${c.id})">إرسال</button>
                <button class="cancel" onclick="toggleReplyForm(0, ${c.id})">✕</button>
            </div>`}
        </div>
    </div>`;
}

function updateCommentsBadge(annId) {
    // إيجاد زر التعليقات في بطاقة الإعلان وتحديث العدّاد
    const card = document.getElementById('ann-' + annId);
    if (!card) return;
    const btn = card.querySelector('.comments-toggle-btn');
    if (!btn) return;
    // تنظيف badges قديمة
    const oldBadge = btn.querySelector('.comments-count-badge');
    if (oldBadge) oldBadge.remove();
    const count = commentsCountCache[annId] || 0;
    if (count > 0) {
        const badge = document.createElement('span');
        badge.className = 'comments-count-badge';
        badge.textContent = count;
        btn.appendChild(badge);
    }
}

function toggleCommentsSection(annId) {
    const sec = document.getElementById('comments-section-' + annId);
    if (!sec) return;
    const isOpen = sec.style.display !== 'none';
    if (isOpen) {
        sec.style.display = 'none';
        openComments[annId] = false;
    } else {
        sec.style.display = 'block';
        openComments[annId] = true;
        loadComments(annId);
        // تركيز على حقل الإدخال
        setTimeout(() => {
            const ta = document.getElementById('comment-input-' + annId);
            if (ta) ta.focus();
        }, 100);
    }
}

async function submitComment(annId, btn) {
    const ta = document.getElementById('comment-input-' + annId);
    if (!ta) return;
    const content = (ta.value || '').trim();
    if (!content) { alert('⚠️ اكتب تعليقاً أولاً'); return; }
    const origText = btn.textContent;
    btn.disabled = true; btn.textContent = '⏳';
    const myName = getUserName() || 'زائر';
    try {
        const res = await fetch('/api/comment', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                announcement_id: annId,
                content: content,
                user_name: myName,
                user_token: getUserToken(),
                parent_id: 0
            })
        });
        const data = await res.json();
        if (data.ok) {
            commentsCache[annId] = data.comments || [];
            commentsCountCache[annId] = commentsCache[annId].filter(c => !c.is_deleted).length;
            ta.value = '';
            renderComments(annId);
            updateCommentsBadge(annId);
        } else {
            alert('❌ فشل: ' + (data.error || 'غير معروف'));
        }
    } catch(e) { alert('❌ خطأ في الاتصال'); }
    btn.disabled = false; btn.textContent = origText;
}

function toggleReplyForm(annId, commentId) {
    const form = document.getElementById('reply-form-' + commentId);
    if (!form) return;
    const isOpen = form.classList.contains('show');
    document.querySelectorAll('.comment-reply-form.show').forEach(f => f.classList.remove('show'));
    replyOpen[commentId] = !isOpen;
    if (!isOpen) {
        form.classList.add('show');
        setTimeout(() => {
            const inp = document.getElementById('reply-input-' + commentId);
            if (inp) inp.focus();
        }, 100);
    } else {
        form.classList.remove('show');
    }
}

async function submitReply(annId, commentId) {
    const inp = document.getElementById('reply-input-' + commentId);
    if (!inp) return;
    const content = (inp.value || '').trim();
    if (!content) { alert('⚠️ اكتب رداً أولاً'); return; }
    const myName = getUserName() || 'زائر';
    try {
        const res = await fetch('/api/comment', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                announcement_id: annId,
                content: content,
                user_name: myName,
                user_token: getUserToken(),
                parent_id: commentId
            })
        });
        const data = await res.json();
        if (data.ok) {
            commentsCache[annId] = data.comments || [];
            commentsCountCache[annId] = commentsCache[annId].filter(c => !c.is_deleted).length;
            inp.value = '';
            replyOpen[commentId] = false;
            renderComments(annId);
            updateCommentsBadge(annId);
        } else {
            alert('❌ فشل: ' + (data.error || 'غير معروف'));
        }
    } catch(e) { alert('❌ خطأ في الاتصال'); }
}

async function deleteComment(annId, commentId) {
    if (!confirm('🗑️ حذف هذا التعليق؟')) return;
    try {
        const res = await fetch('/api/delete_comment', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                id: commentId,
                announcement_id: annId,
                user_token: getUserToken()
            })
        });
        const data = await res.json();
        if (data.ok) {
            if (data.comments) {
                commentsCache[annId] = data.comments;
                commentsCountCache[annId] = commentsCache[annId].filter(c => !c.is_deleted).length;
                renderComments(annId);
            } else {
                // إعادة تحميل من السيرفر
                await loadCommentsCount(annId);
                renderComments(annId);
            }
            updateCommentsBadge(annId);
        } else {
            alert('❌ فشل: ' + (data.error || 'ليس لديك صلاحية'));
        }
    } catch(e) { alert('❌ خطأ في الاتصال'); }
}

// Ctrl+Enter لإرسال التعليق
document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        const ta = e.target;
        if (ta && ta.id && ta.id.startsWith('comment-input-')) {
            const annId = ta.id.replace('comment-input-', '');
            const btn = ta.parentElement.querySelector('.comment-send-btn');
            if (btn) submitComment(parseInt(annId), btn);
        }
    }
});



// Enter في حقل الاسم = حفظ
document.getElementById('nameInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') saveNameAndReact();
});

loadAnnouncements();
</script>
</body>
</html>
"""

@app.route('/announcements')
def announcements_page():
    return render_template_string(announcements_html, is_admin=is_admin_logged_in())

# ========== مسارات API ==========
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, number, otp, timestamp, platform FROM otp_logs ORDER BY id DESC LIMIT 100")
    rows = c.fetchall()
    conn.close()
    return jsonify([{'id': r[0], 'number': r[1], 'otp': r[2], 'timestamp': r[3], 'platform': r[4]} for r in rows])

# ========== [مزامنة الأكواد للزوار] - مفتاح حل المشكلة ==========
# هذا الـ endpoint هو "المرجع" لما يجب أن يكون عند الزائر
# يستدعيه كل 8 ثواني ليتطابق localStorage مع DB
@app.route('/api/otps_for_visitor', methods=['GET'])
def api_otps_for_visitor():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # آخر 50 كود فقط (كافي للعرض)
        c.execute("SELECT id, number, otp, timestamp, platform, country_code, country_flag FROM otp_logs ORDER BY id DESC LIMIT 50")
        rows = c.fetchall()
        conn.close()
        now_ts = int(time.time())
        return jsonify({
            'ok': True,
            'server_time': now_ts,
            'otp_count': len(rows),
            'otps': [{
                'id': r[0], 'number': r[1], 'otp': r[2], 'timestamp': r[3],
                'platform': r[4] or 'unknown',
                'country_code': r[5] or '',
                'country_flag': r[6] or ''
            } for r in rows]
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ========== [حذف كود لزائر محدد] ==========
# يحذف كل الأكواد المرتبطة بـ device_id أو session_id محدد
# (مفيد إذا تبي حذف أكواد جهاز معيّن)
@app.route('/api/clear_device_otps', methods=['POST'])
def api_clear_device_otps():
    """حذف الأكواد لـ device_id أو platform محدد (لإدارة متقدمة)"""
    if not is_admin_logged_in():
        return jsonify({'ok': False, 'error': 'غير مصرح'}), 403
    data = request.json or {}
    device_id = data.get('device_id')
    platform = data.get('platform')
    if not device_id and not platform:
        return jsonify({'ok': False, 'error': 'حدد device_id أو platform'}), 400
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        if device_id:
            # حذف الأكواد الخاصة بـ device معين
            c.execute("DELETE FROM otp_logs WHERE number IN (SELECT assigned_number FROM users WHERE user_id=?)", (device_id,))
        if platform:
            c.execute("DELETE FROM otp_logs WHERE platform=?", (platform,))
        deleted = c.rowcount
        conn.commit()
        # تنظيف الكاش
        global _otp_cache
        if '_otp_cache' in globals():
            _otp_cache['data'] = None
            _otp_cache['time'] = 0
        conn.close()
        return jsonify({'ok': True, 'deleted': deleted})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ========== [حذف كود واحد] ==========
@app.route('/api/delete_otp', methods=['POST'])
def api_delete_otp():
    if not is_admin_logged_in():
        return jsonify({'ok': False, 'error': 'غير مصرح'}), 403
    data = request.json or {}
    otp_id = data.get('id')
    otp_value = data.get('otp')
    if otp_id is not None:
        if delete_otp(otp_id=otp_id):
            return jsonify({'ok': True})
    elif otp_value is not None:
        if delete_otp(otp_value=otp_value):
            return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'بيانات غير مكتملة'}), 400

# ========== [مسح جميع الأكواد] ==========
@app.route('/api/clear_all_otps', methods=['POST'])
def api_clear_all_otps():
    if not is_admin_logged_in():
        return jsonify({'ok': False, 'error': 'غير مصرح'}), 403
    if delete_otp(all_otps=True):
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'فشل الحذف'}), 500

# ========== [حذف إعلان] (للأدمن فقط) ==========
@app.route('/api/delete_announcement', methods=['POST'])
def api_delete_announcement():
    if not is_admin_logged_in():
        return jsonify({'ok': False, 'error': 'غير مصرح'}), 403
    data = request.json or {}
    ann_id = data.get('id')
    if not ann_id:
        return jsonify({'ok': False, 'error': 'معرّف الإعلان مفقود'}), 400
    if delete_announcement(ann_id):
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'فشل الحذف'}), 500

# ========== [API التفاعلات على الإعلانات] ==========
ALLOWED_REACTIONS = {'heart', 'fire', 'star', 'like', 'clap', 'wow'}

@app.route('/api/reaction', methods=['POST'])
def api_reaction():
    """إضافة أو إزالة تفاعل على إعلان"""
    data = request.json or {}
    ann_id = data.get('announcement_id')
    reaction = data.get('reaction')
    user_name = (data.get('user_name') or '').strip()[:30]
    # معرّف فريد للزائر (مجهول الهوية)
    user_token = (data.get('user_token') or request.headers.get('X-User-Token') or '').strip()
    if not user_token:
        # توليد token من IP + UA كتعريف مؤقت
        user_token = (request.remote_addr or 'anon') + '_' + (request.headers.get('User-Agent', '')[:30])
    if not ann_id or reaction not in ALLOWED_REACTIONS:
        return jsonify({'ok': False, 'error': 'بيانات غير صالحة'}), 400
    added = toggle_reaction(ann_id, user_token, user_name or 'زائر', reaction)
    if added is None:
        return jsonify({'ok': False, 'error': 'فشل الحفظ'}), 500
    return jsonify({'ok': True, 'added': added, 'reactions': get_reactions_for_announcement(ann_id)})

@app.route('/api/reactions', methods=['GET'])
def api_reactions():
    """استرجاع كل التفاعلات لإعلان"""
    ann_id = request.args.get('announcement_id')
    if not ann_id:
        return jsonify({'ok': False, 'error': 'معرّف الإعلان مفقود'}), 400
    return jsonify({'ok': True, 'reactions': get_reactions_for_announcement(ann_id)})

# ========== [API التعليقات على الإعلانات] ==========
@app.route('/api/comments', methods=['GET'])
def api_comments():
    """استرجاع كل تعليقات إعلان"""
    ann_id = request.args.get('announcement_id')
    if not ann_id:
        return jsonify({'ok': False, 'error': 'معرّف الإعلان مفقود'}), 400
    return jsonify({'ok': True, 'comments': get_comments_for_announcement(ann_id, include_deleted=is_admin_logged_in())})

@app.route('/api/comment', methods=['POST'])
def api_add_comment():
    """إضافة تعليق جديد على إعلان"""
    data = request.json or {}
    ann_id = data.get('announcement_id')
    content = (data.get('content') or '').strip()
    user_name = (data.get('user_name') or '').strip()[:30]
    parent_id = int(data.get('parent_id') or 0)
    user_token = (data.get('user_token') or request.headers.get('X-User-Token') or '').strip()
    if not user_token:
        user_token = (request.remote_addr or 'anon') + '_' + (request.headers.get('User-Agent', '')[:30])
    if not ann_id or not content:
        return jsonify({'ok': False, 'error': 'التعليق أو معرّف الإعلان فارغ'}), 400
    # التحقق من وجود الإعلان
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM announcements WHERE id=?", (ann_id,))
    if not c.fetchone():
        conn.close()
        return jsonify({'ok': False, 'error': 'الإعلان غير موجود'}), 404
    conn.close()
    new_id = add_comment(ann_id, user_token, user_name or 'زائر', content, parent_id)
    if not new_id:
        return jsonify({'ok': False, 'error': 'فشل حفظ التعليق'}), 500
    # إرجاع التعليق الجديد ضمن القائمة المحدّثة
    return jsonify({'ok': True, 'comment_id': new_id, 'comments': get_comments_for_announcement(ann_id, include_deleted=is_admin_logged_in())})

@app.route('/api/delete_comment', methods=['POST'])
def api_delete_comment():
    """حذف تعليق (مالك التعليق أو الأدمن)"""
    data = request.json or {}
    comment_id = data.get('id')
    user_token = (data.get('user_token') or request.headers.get('X-User-Token') or '').strip()
    if not user_token:
        user_token = (request.remote_addr or 'anon') + '_' + (request.headers.get('User-Agent', '')[:30])
    if not comment_id:
        return jsonify({'ok': False, 'error': 'معرّف التعليق مفقود'}), 400
    admin_flag = is_admin_logged_in()
    ok = delete_comment(comment_id, user_token, is_admin=admin_flag)
    if ok:
        ann_id = data.get('announcement_id')
        if ann_id:
            return jsonify({'ok': True, 'comments': get_comments_for_announcement(ann_id, include_deleted=admin_flag)})
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'فشل الحذف أو ليس لديك صلاحية'}), 403

# ========== [حفظ ترتيب المنصات] (للأدمن فقط) ==========
@app.route('/api/save_platform_order', methods=['POST'])
def api_save_platform_order():
    if not is_admin_logged_in():
        return jsonify({'ok': False, 'error': 'غير مصرح'}), 403
    data = request.json or {}
    order = data.get('order', [])
    if not isinstance(order, list) or not order:
        return jsonify({'ok': False, 'error': 'ترتيب غير صالح'}), 400
    # فلترة القيم المسموحة فقط
    valid = [p for p in order if p in platform_names]
    if valid:
        save_platform_order(valid)
        return jsonify({'ok': True, 'order': valid})
    return jsonify({'ok': False, 'error': 'لا توجد منصات صالحة'}), 400

# ========== [تبديل إعدادات الموقع] (صوت، ثيم، ألوان) ==========
@app.route('/api/update_setting', methods=['POST'])
def api_update_setting():
    if not is_admin_logged_in():
        return jsonify({'ok': False, 'error': 'غير مصرح'}), 403
    data = request.json or {}
    key = data.get('key')
    value = data.get('value')
    if not key:
        return jsonify({'ok': False, 'error': 'مفتاح الإعداد مفقود'}), 400
    # قائمة الإعدادات المسموح بتغييرها
    allowed = {'sound_enabled', 'theme_mode', 'main_color', 'secondary_color', 'background_color', 'text_color', 'matrix_enabled', 'ticker_enabled'}
    if key not in allowed:
        return jsonify({'ok': False, 'error': 'إعداد غير مسموح'}), 400
    set_setting(key, str(value))
    return jsonify({'ok': True, 'key': key, 'value': value})

# ========== [إرجاع الإعدادات] للصفحة العامة ==========
@app.route('/api/public_settings', methods=['GET'])
def api_public_settings():
    """إرجاع الإعدادات العامة (آمن للزوار) - لا يشمل الإعدادات الحساسة"""
    return jsonify({
        'sound_enabled': get_setting('sound_enabled') or '1',
        'theme_mode': get_setting('theme_mode') or 'dark',
        'main_color': get_setting('main_color') or '#00ffc8',
        'secondary_color': get_setting('secondary_color') or '#8b5cf6',
        'background_color': get_setting('background_color') or '#0a0e1a',
        'text_color': get_setting('text_color') or '#ffffff',
        'matrix_enabled': get_setting('matrix_enabled') or '1',
        'ticker_enabled': get_setting('ticker_enabled') or '1',
        'platform_order': get_setting('platform_order') or 'whatsapp,telegram,tiktok,facebook,instagram,snapchat,google,twitter'
    })

# ========== [مسار الأدمن السري] ==========
@app.route('/' + ADMIN_SECRET_PATH)
@login_required
def admin_secret():
    return redirect(url_for('admin_dashboard'))

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

@app.route('/api/help', methods=['POST'])
def api_help():
    msg = request.json.get('message', '').strip()
    if not msg:
        return jsonify({'ok': False, 'error': 'الرسالة فارغة'}), 400
    user_id = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO help_requests (user_id, message, source, created_at) VALUES (?, ?, ?, ?)",
              (user_id, msg, 'website', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    saved_admin_id = get_admin_setting('admin_telegram_id')
    try:
        help_text = f"🆘 <b>طلب مساعدة جديد</b>\n\n👤 المستخدم: <code>{user_id}</code>\n💬 الرسالة:\n{msg}\n\n🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        if saved_admin_id:
            requests.post(f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/sendMessage", 
                         json={'chat_id': saved_admin_id, 'text': help_text, 'parse_mode': 'HTML'}, timeout=10)
        else:
            requests.post(f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/sendMessage", 
                         json={'chat_id': f"@{OWNER_TELEGRAM_ID.lstrip('@')}", 'text': help_text, 'parse_mode': 'HTML'}, timeout=10)
    except Exception as e:
        print(f"❌ فشل إرسال طلب المساعدة: {e}")
    return jsonify({'ok': True})

# ========== لوحة التحكم ==========
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return "❌ كلمة المرور خاطئة!"
    return '''
    <div style="text-align:center; margin-top:100px; font-family:sans-serif; background:#0d1117; color:#fff; padding:40px; border-radius:20px; max-width:400px; margin-left:auto; margin-right:auto;">
        <h2>🔐 دخول الأدمن</h2>
        <form method="POST">
            <input type="password" name="password" placeholder="كلمة المرور" style="padding:12px; border-radius:8px; border:1px solid #30363d; background:#161b22; color:#fff; width:100%; margin:10px 0;">
            <button type="submit" style="padding:12px 25px; background:#238636; color:#fff; border:none; border-radius:8px; cursor:pointer; font-weight:bold; width:100%;">دخول</button>
        </form>
        <p style="color:#8b949e; font-size:12px; margin-top:10px;">كلمة المرور الافتراضية: admin123</p>
    </div>
    '''

@app.route('/admin')
@login_required
def admin_dashboard():
    return render_template_string('''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚙️ لوحة التحكم</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family:'Cairo',sans-serif; background:#0a0e1a; color:#fff; min-height:100vh; padding:20px; }
        .container { max-width:500px; margin:0 auto; background:rgba(17,24,39,0.95); backdrop-filter:blur(20px); padding:25px; border-radius:20px; border:1px solid rgba(0,255,200,0.3); }
        h1 { text-align:center; background:linear-gradient(90deg,#00ffc8,#8b5cf6); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:20px; font-size:24px; }
        h3 { color:#cbd5e1; margin:15px 0 10px; }
        .form-group { margin-bottom:12px; }
        .form-group label { display:block; margin-bottom:4px; color:#cbd5e1; font-weight:700; font-size:13px; }
        .form-control { width:100%; padding:10px; border-radius:8px; border:1px solid #30363d; background:#0d1117; color:#fff; font-family:'Cairo',sans-serif; font-size:13px; }
        .form-control:focus { border-color:#00ffc8; outline:none; }
        .btn { padding:10px 20px; border:none; border-radius:8px; font-weight:700; cursor:pointer; font-family:'Cairo',sans-serif; font-size:13px; }
        .btn-primary { background:linear-gradient(135deg,#00ff88,#00d2ff); color:#000; }
        .btn-danger { background:linear-gradient(135deg,#ef4444,#b91c1c); color:#fff; }
        .btn-secondary { background:linear-gradient(135deg,#374151,#4b5563); color:#fff; }
        .btn:hover { transform:translateY(-2px); }
        .combo-item { display:flex; justify-content:space-between; align-items:center; background:rgba(31,41,55,0.7); padding:10px; border-radius:8px; margin-bottom:6px; }
        .combo-item button { padding:4px 10px; font-size:11px; }
        hr { border:1px solid rgba(255,255,255,0.1); margin:15px 0; }
        .link-item { display:flex; gap:8px; align-items:center; margin-bottom:6px; flex-wrap:wrap; }
        .link-item input { flex:1; min-width:120px; }
        .link-item button { padding:4px 10px; font-size:11px; }
        .status { display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:700; }
        .status.active { background:#238636; }
        .status.banned { background:#da3633; }
        .user-item { display:flex; justify-content:space-between; align-items:center; background:rgba(31,41,55,0.5); padding:6px 10px; border-radius:6px; margin-bottom:4px; font-size:12px; }
        .user-item button { padding:2px 8px; font-size:10px; margin:0; }
        .otp-log-item { background:rgba(31,41,55,0.5); padding:8px 10px; border-radius:6px; margin-bottom:4px; display:flex; justify-content:space-between; align-items:center; font-size:12px; }
        .otp-log-item button { padding:2px 8px; font-size:10px; }
        .section { background:rgba(0,0,0,0.2); padding:12px; border-radius:10px; margin-bottom:10px; }
        .grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
        .stat-card { background:rgba(31,41,55,0.5); padding:12px; border-radius:8px; text-align:center; }
        .stat-card .num { font-size:22px; font-weight:900; color:#00ffc8; }
        .stat-card .label { font-size:11px; color:#8b949e; }
        .back-link { display:block; text-align:center; color:#58a6ff; text-decoration:none; margin-top:10px; }
        .back-link:hover { text-decoration:underline; }
        @media (max-width:480px) { .grid-2 { grid-template-columns:1fr; } }
    </style>
</head>
<body>
<div class="container">
    <h1>⚙️ لوحة التحكم</h1>
    
    <!-- إحصائيات -->
    <div class="grid-2" id="statsGrid">
        <div class="stat-card"><div class="num" id="statUsers">0</div><div class="label">👥 المستخدمين</div></div>
        <div class="stat-card"><div class="num" id="statOtps">0</div><div class="label">🔑 الأكواد</div></div>
        <div class="stat-card"><div class="num" id="statToday">0</div><div class="label">📅 أكواد اليوم</div></div>
        <div class="stat-card"><div class="num" id="statCombos">0</div><div class="label">📦 الكومبوهات</div></div>
    </div>
    
    <hr>
    
    <!-- مدير النصوص -->
    <h3>✏️ مدير النصوص</h3>
    <div class="section">
        <div class="form-group"><label>عنوان الموقع</label><input type="text" id="siteTitle" class="form-control" value="{{ site_title }}"></div>
        <div class="form-group"><label>الوصف</label><input type="text" id="siteSubtitle" class="form-control" value="{{ site_subtitle }}"></div>
        <div class="form-group"><label>شريط الأخبار</label><input type="text" id="tickerText" class="form-control" value="{{ ticker_text }}"></div>
        <button class="btn btn-primary" onclick="saveTexts()">💾 حفظ النصوص</button>
    </div>
    
    <hr>
    
    <!-- مدير الروابط -->
    <h3>🔗 مدير الروابط</h3>
    <div class="section" id="linksSection">
        {% for key, value, icon in links %}
        <div class="link-item">
            <span>{{ icon }}</span>
            <input type="text" class="form-control" value="{{ value }}" data-key="{{ key }}" style="flex:1;min-width:100px;">
            <button class="btn btn-danger" onclick="deleteLink('{{ key }}')">🗑️</button>
        </div>
        {% endfor %}
        <div style="display:flex;gap:6px;margin-top:6px;">
            <input type="text" id="newLinkKey" class="form-control" placeholder="المفتاح (مثال: instagram)" style="flex:1;">
            <input type="text" id="newLinkValue" class="form-control" placeholder="الرابط" style="flex:2;">
            <input type="text" id="newLinkIcon" class="form-control" placeholder="الأيقونة" style="flex:0.5;max-width:50px;">
            <button class="btn btn-primary" onclick="addLink()">➕</button>
        </div>
        <button class="btn btn-secondary" onclick="saveLinks()" style="margin-top:6px;">💾 حفظ الروابط</button>
    </div>
    
    <hr>
    
    <!-- الكومبوهات -->
    <h3>📦 الكومبوهات</h3>
    <div class="section">
        <form method="POST" enctype="multipart/form-data" action="/admin/upload_combo">
            <div class="form-group"><label>المنصة</label>
            <select name="platform" class="form-control">
                <option value="whatsapp">واتساب</option>
                <option value="telegram">تيليجرام</option>
                <option value="tiktok">تيك توك</option>
                <option value="facebook">فيسبوك</option>
                <option value="instagram">انستقرام</option>
                <option value="snapchat">سناب شات</option>
                <option value="google">جوجل</option>
                <option value="twitter">تويتر</option>
            </select></div>
            <div class="form-group"><label>ملف الأرقام (.txt)</label><input type="file" name="file" accept=".txt" class="form-control" required></div>
            <button type="submit" class="btn btn-primary">📤 رفع</button>
        </form>
        <div id="combosList" style="margin-top:10px;">
            {% for platform, code, name, flag in combos %}
            <div class="combo-item">
                <span>{{ flag }} {{ name }} ({{ platform }})</span>
                <form method="POST" action="/admin/delete_combo" style="display:inline;">
                    <input type="hidden" name="platform" value="{{ platform }}">
                    <input type="hidden" name="country_code" value="{{ code }}">
                    <button type="submit" class="btn btn-danger">🗑️</button>
                </form>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <hr>
    
    <!-- الأكواد المسحوبة -->
    <h3>🔑 الأكواد المسحوبة <button class="btn btn-danger" onclick="clearAllOtpsAdmin()" style="padding:4px 10px; font-size:11px; margin-right:8px;">🗑️ مسح الكل</button></h3>
    <div class="section" id="otpLogsList">
        <div style="text-align:center;color:#64748b;padding:10px;">⏳ جاري التحميل...</div>
    </div>
    
    <hr>
    
    <!-- إدارة الأجهزة/الزيارات -->
    <h3>📱 إدارة الأجهزة والزيارات</h3>
    <div class="section" id="devicesListSection">
        <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;">
            <input type="text" id="deviceSearchInput" class="form-control" placeholder="🔍 بحث بالاسم/الرقم/User ID" style="flex:1;min-width:180px;">
            <button class="btn btn-secondary" onclick="loadDevicesList()" style="padding:4px 12px;font-size:11px;">🔄 تحديث</button>
        </div>
        <div id="devicesStats" style="font-size:11px;color:#8b949e;margin-bottom:6px;"></div>
        <div id="devicesList">
            <div style="text-align:center;color:#64748b;padding:10px;">⏳ جاري التحميل...</div>
        </div>
    </div>
    
    <hr>
    
    <!-- الإعلانات -->
    <h3>📢 إدارة الإعلانات</h3>
    <div class="section" id="announcementsAdminList">
        <div style="text-align:center;color:#64748b;padding:10px;">⏳ جاري التحميل...</div>
    </div>
    
    <hr>
    
    <!-- المستخدمين -->
    <h3>👥 المستخدمين</h3>
    <div class="section" id="usersList">
        <div style="text-align:center;color:#64748b;padding:10px;">⏳ جاري التحميل...</div>
    </div>
    
    <hr>
    
    <!-- إعدادات الموقع والصوت والثيم -->
    <h3>🎨 إعدادات الموقع والصوت</h3>
    <div class="section">
        <div class="form-group">
            <label>🔔 صوت الإشعار</label>
            <div style="display:flex;gap:6px;align-items:center;">
                <button class="btn" id="soundToggleBtn" onclick="toggleSoundAdmin()" style="flex:1;">—</button>
            </div>
        </div>
        <div class="form-group">
            <label>🌙/☀️ وضع الموقع</label>
            <div style="display:flex;gap:6px;">
                <button class="btn" id="themeDarkBtn" onclick="setThemeAdmin('dark')" style="flex:1;">🌙 ليلي</button>
                <button class="btn" id="themeLightBtn" onclick="setThemeAdmin('light')" style="flex:1;">☀️ نهاري</button>
            </div>
        </div>
        <div class="form-group">
            <label>🎨 اللون الأساسي</label>
            <input type="color" id="adminMainColor" class="form-control" value="{{ main_color }}" style="height:40px;padding:4px;">
        </div>
        <div class="form-group">
            <label>🎨 لون الخلفية</label>
            <input type="color" id="adminBgColor" class="form-control" value="{{ background_color }}" style="height:40px;padding:4px;">
        </div>
        <div class="form-group">
            <label>📝 لون النص</label>
            <input type="color" id="adminTextColor" class="form-control" value="{{ text_color }}" style="height:40px;padding:4px;">
        </div>
        <div class="form-group">
            <label>🎨 لون ثانوي</label>
            <input type="color" id="adminSecondaryColor" class="form-control" value="{{ secondary_color }}" style="height:40px;padding:4px;">
        </div>
        <button class="btn btn-primary" onclick="saveColors()" style="margin-top:6px;">💾 حفظ الألوان</button>
    </div>
    
    <hr>
    
    <!-- إعدادات الأدمن -->
    <h3>⚙️ إعدادات الأدمن</h3>
    <div class="section">
        <div class="form-group"><label>🆔 Chat ID الخاص بك</label>
        <input type="text" id="adminChatId" class="form-control" value="{{ admin_chat_id }}">
        <button class="btn btn-primary" onclick="saveAdminId()" style="margin-top:6px;">💾 حفظ</button>
        </div>
        <div class="form-group"><label>🔑 كلمة المرور الجديدة</label>
        <input type="password" id="newPassword" class="form-control" placeholder="اتركها فارغة للإبقاء على الحالية">
        <button class="btn btn-primary" onclick="changePassword()" style="margin-top:6px;">🔑 تغيير كلمة المرور</button>
        </div>
    </div>
    
    <hr>
    
    <div style="display:flex;gap:8px;">
        <a href="/" class="btn btn-secondary" style="flex:1;text-align:center;text-decoration:none;">🔙 الرئيسية</a>
    </div>
</div>

<script>
async function loadStats() {
    try {
        const res = await fetch('/admin/api/stats');
        const data = await res.json();
        document.getElementById('statUsers').textContent = data.users || 0;
        document.getElementById('statOtps').textContent = data.otps || 0;
        document.getElementById('statToday').textContent = data.today || 0;
        document.getElementById('statCombos').textContent = data.combos || 0;
    } catch(e) {}
}

async function loadOtps() {
    try {
        const res = await fetch('/api/all_otps');
        const data = await res.json();
        const box = document.getElementById('otpLogsList');
        if (!data.length) { box.innerHTML = '<div style="text-align:center;color:#64748b;padding:10px;">📭 لا توجد أكواد</div>'; return; }
        box.innerHTML = data.slice(0, 30).map(o => `
            <div class="otp-log-item">
                <div><span style="color:#00ffc8;font-weight:900;">${o.otp}</span> <span style="color:#8b949e;font-size:10px;">(${o.platform})</span><br><span style="color:#64748b;font-size:10px;">📞 ${o.number} • ${o.timestamp}</span></div>
                <button class="btn btn-danger" onclick="deleteOtp('${o.id}','${o.otp}')" style="padding:2px 8px;font-size:10px;">🗑️</button>
            </div>
        `).join('');
    } catch(e) {}
}

async function deleteOtp(otpId, otpValue) {
    if(!confirm('🗑️ حذف هذا الكود؟')) return;
    try {
        const payload = otpId && otpId !== 'undefined' ? {id: parseInt(otpId)} : {otp: otpValue};
        const res = await fetch('/api/delete_otp', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if(data.ok) { loadOtps(); loadStats(); }
        else { alert('❌ فشل الحذف: ' + (data.error || '')); }
    } catch(e) { alert('❌ خطأ'); }
}

async function clearAllOtpsAdmin() {
    if(!confirm('⚠️ سيتم حذف جميع الأكواد نهائياً. متابعة؟')) return;
    try {
        const res = await fetch('/api/clear_all_otps', {method: 'POST', headers: {'Content-Type': 'application/json'}});
        const data = await res.json();
        if(data.ok) { loadOtps(); loadStats(); alert('✅ تم مسح جميع الأكواد'); }
        else { alert('❌ فشل: ' + (data.error || '')); }
    } catch(e) { alert('❌ خطأ'); }
}

async function loadAnnouncementsAdmin() {
    try {
        const res = await fetch('/api/announcements');
        const data = await res.json();
        const box = document.getElementById('announcementsAdminList');
        if (!data.length) { box.innerHTML = '<div style="text-align:center;color:#64748b;padding:10px;">📭 لا توجد إعلانات</div>'; return; }
        box.innerHTML = data.slice(0, 20).map(a => {
            const typeLabel = a.type === 'text' ? '📝 نص' : a.type === 'image' ? '🖼️ صورة' : '🎬 فيديو';
            const contentPreview = (a.content || '').substring(0, 80);
            return `
            <div class="combo-item" style="flex-wrap:wrap;">
                <div style="flex:1;min-width:200px;">
                    <div><span class="status active">${typeLabel}</span> <span style="color:#8b949e;font-size:10px;">${a.id}</span></div>
                    <div style="font-size:12px;color:#cbd5e1;margin-top:4px;">${contentPreview}${contentPreview.length >= 80 ? '...' : ''}</div>
                    <div style="color:#64748b;font-size:10px;margin-top:2px;">🕒 ${a.created_at}</div>
                </div>
                <button class="btn btn-danger" onclick="deleteAnnouncementAdmin(${a.id})" style="padding:4px 8px; font-size:11px;">🗑️</button>
            </div>`;
        }).join('');
    } catch(e) {}
}

async function deleteAnnouncementAdmin(id) {
    if (!confirm('🗑️ حذف هذا الإعلان نهائياً؟')) return;
    try {
        const res = await fetch('/api/delete_announcement', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({id: id})
        });
        const data = await res.json();
        if (data.ok) { loadAnnouncementsAdmin(); alert('✅ تم الحذف'); }
        else { alert('❌ فشل: ' + (data.error || '')); }
    } catch(e) { alert('❌ خطأ'); }
}

let adminSoundEnabled = '{{ sound_enabled }}' !== '0';
let adminThemeMode = '{{ theme_mode }}' || 'dark';
function updateAdminSoundUi() {
    const btn = document.getElementById('soundToggleBtn');
    if (btn) {
        btn.textContent = adminSoundEnabled ? '🔔 الصوت: تشغيل' : '🔕 الصوت: إيقاف';
        btn.className = 'btn ' + (adminSoundEnabled ? 'btn-primary' : 'btn-danger');
    }
}
function updateAdminThemeUi() {
    const darkBtn = document.getElementById('themeDarkBtn');
    const lightBtn = document.getElementById('themeLightBtn');
    if (darkBtn) {
        darkBtn.className = 'btn ' + (adminThemeMode === 'dark' ? 'btn-primary' : 'btn-secondary');
    }
    if (lightBtn) {
        lightBtn.className = 'btn ' + (adminThemeMode === 'light' ? 'btn-primary' : 'btn-secondary');
    }
}
async function toggleSoundAdmin() {
    adminSoundEnabled = !adminSoundEnabled;
    updateAdminSoundUi();
    await fetch('/api/update_setting', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({key: 'sound_enabled', value: adminSoundEnabled ? '1' : '0'})
    });
}
async function setThemeAdmin(mode) {
    adminThemeMode = mode;
    updateAdminThemeUi();
    await fetch('/api/update_setting', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({key: 'theme_mode', value: mode})
    });
}
async function saveColors() {
    const main = document.getElementById('adminMainColor').value;
    const bg = document.getElementById('adminBgColor').value;
    const text = document.getElementById('adminTextColor').value;
    const secondary = document.getElementById('adminSecondaryColor').value;
    const updates = [
        {key: 'main_color', value: main},
        {key: 'background_color', value: bg},
        {key: 'text_color', value: text},
        {key: 'secondary_color', value: secondary}
    ];
    try {
        for (const u of updates) {
            await fetch('/api/update_setting', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(u)
            });
        }
        alert('✅ تم حفظ الألوان');
        location.reload();
    } catch(e) {
        alert('❌ فشل الحفظ');
    }
}

async function loadUsers() {
    try {
        const res = await fetch('/admin/api/users');
        const data = await res.json();
        const box = document.getElementById('usersList');
        if (!data.length) { box.innerHTML = '<div style="text-align:center;color:#64748b;padding:10px;">👤 لا توجد مستخدمين</div>'; return; }
        box.innerHTML = data.map(u => `
            <div class="user-item">
                <div><span style="font-weight:700;">${u.username || 'مستخدم'}</span> <span class="status ${u.is_banned ? 'banned' : 'active'}">${u.is_banned ? 'محظور' : 'نشط'}</span><br><span style="color:#64748b;font-size:10px;">🆔 ${u.user_id} • 📞 ${u.assigned_number || '—'}</span></div>
                <div>
                    <button class="btn btn-secondary" onclick="toggleBan('${u.user_id}', ${u.is_banned})" style="padding:2px 8px;font-size:10px;">${u.is_banned ? '🔓' : '🔒'}</button>
                </div>
            </div>
        `).join('');
    } catch(e) {}
}

async function toggleBan(user_id, current) {
    if(!confirm(current ? '🔓 فك حظر هذا المستخدم؟' : '🔒 حظر هذا المستخدم؟')) return;
    try {
        const res = await fetch('/admin/api/toggle_ban', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({user_id: user_id, ban: !current})
        });
        const data = await res.json();
        if(data.ok) { loadUsers(); loadStats(); alert('✅ تم'); }
        else { alert('❌ فشل'); }
    } catch(e) { alert('❌ خطأ'); }
}

async function saveTexts() {
    const data = {
        site_title: document.getElementById('siteTitle').value,
        site_subtitle: document.getElementById('siteSubtitle').value,
        ticker_text: document.getElementById('tickerText').value
    };
    try {
        const res = await fetch('/admin/api/save_texts', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if(result.ok) alert('✅ تم الحفظ');
        else alert('❌ فشل الحفظ');
    } catch(e) { alert('❌ خطأ'); }
}

async function saveLinks() {
    const links = {};
    document.querySelectorAll('#linksSection .link-item input[type="text"]').forEach(inp => {
        const key = inp.dataset.key;
        if(key) links[key] = inp.value;
    });
    try {
        const res = await fetch('/admin/api/save_links', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(links)
        });
        const result = await res.json();
        if(result.ok) alert('✅ تم الحفظ');
        else alert('❌ فشل الحفظ');
    } catch(e) { alert('❌ خطأ'); }
}

async function addLink() {
    const key = document.getElementById('newLinkKey').value.trim();
    const value = document.getElementById('newLinkValue').value.trim();
    const icon = document.getElementById('newLinkIcon').value.trim() || '🔗';
    if(!key || !value) { alert('⚠️ اكتب المفتاح والرابط'); return; }
    try {
        const res = await fetch('/admin/api/add_link', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({key, value, icon})
        });
        const result = await res.json();
        if(result.ok) { alert('✅ تم الإضافة'); location.reload(); }
        else { alert('❌ فشل الإضافة'); }
    } catch(e) { alert('❌ خطأ'); }
}

async function deleteLink(key) {
    if(!confirm('🗑️ حذف هذا الرابط؟')) return;
    try {
        const res = await fetch('/admin/api/delete_link', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({key})
        });
        const result = await res.json();
        if(result.ok) { alert('✅ تم الحذف'); location.reload(); }
        else { alert('❌ فشل الحذف'); }
    } catch(e) { alert('❌ خطأ'); }
}

async function saveAdminId() {
    const val = document.getElementById('adminChatId').value.trim();
    if(!val) { alert('⚠️ اكتب Chat ID'); return; }
    try {
        const res = await fetch('/admin/api/save_admin_id', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_telegram_id: val})
        });
        const result = await res.json();
        if(result.ok) alert('✅ تم الحفظ');
        else alert('❌ فشل الحفظ');
    } catch(e) { alert('❌ خطأ'); }
}

async function changePassword() {
    const pwd = document.getElementById('newPassword').value.trim();
    if(!pwd) { alert('⚠️ اكتب كلمة المرور الجديدة'); return; }
    if(!confirm('🔑 تغيير كلمة المرور؟')) return;
    try {
        const res = await fetch('/admin/api/change_password', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({password: pwd})
        });
        const result = await res.json();
        if(result.ok) alert('✅ تم تغيير كلمة المرور');
        else alert('❌ فشل');
    } catch(e) { alert('❌ خطأ'); }
}

// ============ [إدارة الأجهزة] ============
let allDevicesCache = [];
async function loadDevicesList() {
    try {
        const res = await fetch('/admin/api/devices_otps');
        const data = await res.json();
        if (!data.ok) { document.getElementById('devicesList').innerHTML = '<div style="text-align:center;color:#ef4444;padding:10px;">❌ فشل التحميل</div>'; return; }
        allDevicesCache = data.devices || [];
        renderDevicesList();
        // إحصائيات
        const statsBox = document.getElementById('devicesStats');
        if (statsBox && data.by_platform) {
            const platforms = Object.entries(data.by_platform).map(([p, c]) => `${p}: ${c}`).join(' • ');
            statsBox.innerHTML = `📊 إجمالي الأجهزة: <b style="color:#00ffc8;">${allDevicesCache.length}</b> | ${platforms || 'لا توجد أكواد'}`;
        }
    } catch(e) {
        document.getElementById('devicesList').innerHTML = '<div style="text-align:center;color:#ef4444;padding:10px;">❌ خطأ في الاتصال</div>';
    }
}
function renderDevicesList() {
    const box = document.getElementById('devicesList');
    const search = (document.getElementById('deviceSearchInput')?.value || '').toLowerCase().trim();
    const filtered = !search ? allDevicesCache : allDevicesCache.filter(d =>
        (d.username || '').toLowerCase().includes(search) ||
        (d.first_name || '').toLowerCase().includes(search) ||
        (d.user_id || '').toLowerCase().includes(search) ||
        (d.number || '').toLowerCase().includes(search) ||
        (d.last_otp_value || '').toLowerCase().includes(search)
    );
    if (!filtered.length) {
        box.innerHTML = '<div style="text-align:center;color:#64748b;padding:14px;">📭 لا توجد نتائج</div>';
        return;
    }
    box.innerHTML = filtered.map(d => `
        <div class="combo-item" style="flex-wrap:wrap;gap:6px;">
            <div style="flex:1;min-width:200px;">
                <div style="font-weight:700;color:#fff;font-size:13px;">${d.first_name || d.username || 'مستخدم'} <span style="color:#8b949e;font-size:10px;">(${d.user_id})</span></div>
                <div style="font-size:11px;color:#8b949e;margin-top:2px;">📞 ${d.number || '—'} ${d.country_code ? '| ' + d.country_code : ''}</div>
                <div style="font-size:10px;color:#64748b;margin-top:2px;">🔑 <b style="color:#00ffc8;">${d.otp_count}</b> كود مسحوب${d.last_otp ? ' • آخر: ' + d.last_otp : ''}</div>
                ${d.last_otp_value ? `<div style="font-size:10px;color:#3fb950;margin-top:2px;">آخر كود: <b>${d.last_otp_value}</b></div>` : ''}
            </div>
            <div style="display:flex;flex-direction:column;gap:4px;">
                <button class="btn btn-danger" onclick="clearDeviceOtps('${d.user_id}','${d.first_name || d.username}')" style="padding:4px 8px;font-size:10px;">🗑️ حذف أكواده</button>
            </div>
        </div>
    `).join('');
}
async function clearDeviceOtps(userId, name) {
    if (!confirm(`🗑️ حذف جميع الأكواد الخاصة بـ "${name}" (${userId})؟`)) return;
    try {
        const res = await fetch('/api/clear_device_otps', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({device_id: userId})
        });
        const data = await res.json();
        if (data.ok) {
            alert('✅ تم حذف ' + (data.deleted || 0) + ' كود من هذا الجهاز');
            loadDevicesList();
            loadOtps();
        } else {
            alert('❌ فشل: ' + (data.error || ''));
        }
    } catch(e) { alert('❌ خطأ في الاتصال'); }
}
// البحث المباشر
document.addEventListener('input', e => {
    if (e.target.id === 'deviceSearchInput') renderDevicesList();
});

loadStats();
loadOtps();
loadUsers();
loadAnnouncementsAdmin();
loadDevicesList();
updateAdminSoundUi();
updateAdminThemeUi();
setInterval(loadStats, 30000);
setInterval(loadOtps, 30000);
setInterval(loadAnnouncementsAdmin, 60000);
setInterval(loadDevicesList, 45000);
</script>
</body>
</html>
''', site_title=get_text('site_title'), site_subtitle=get_text('site_subtitle'), ticker_text=get_text('ticker_text'),
       links=get_all_links(), combos=get_all_combos(), admin_chat_id=get_admin_setting('admin_telegram_id', ''),
       main_color=get_setting('main_color') or '#00ffc8', background_color=get_setting('background_color') or '#0a0e1a',
       text_color=get_setting('text_color') or '#ffffff', secondary_color=get_setting('secondary_color') or '#8b5cf6',
       sound_enabled=get_setting('sound_enabled') or '1', theme_mode=get_setting('theme_mode') or 'dark')

# ========== مسارات API الخاصة بالأدمن ==========
@app.route('/admin/api/devices_otps', methods=['GET'])
def admin_api_devices_otps():
    """قائمة الأجهزة/المستخدمين الذين سحبوا أكواد (لإدارة الحذف)"""
    if not is_admin_logged_in():
        return jsonify({'ok': False, 'error': 'غير مصرح'}), 403
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # آخر المستخدمين الذين تم تعيين أرقام لهم مع أكواد حديثة
        c.execute("""
            SELECT u.user_id, u.username, u.first_name, u.assigned_number, u.country_code,
                   (SELECT COUNT(*) FROM otp_logs WHERE number=u.assigned_number) as otp_count,
                   (SELECT MAX(timestamp) FROM otp_logs WHERE number=u.assigned_number) as last_otp,
                   (SELECT otp FROM otp_logs WHERE number=u.assigned_number ORDER BY id DESC LIMIT 1) as last_otp_value
            FROM users u
            WHERE u.assigned_number IS NOT NULL AND u.assigned_number != ''
            ORDER BY u.id DESC
            LIMIT 100
        """)
        rows = c.fetchall()
        # منصة-إلى-عدد
        c.execute("SELECT platform, COUNT(*) FROM otp_logs GROUP BY platform")
        by_platform = {p: cnt for p, cnt in c.fetchall()}
        conn.close()
        return jsonify({
            'ok': True,
            'devices': [{
                'user_id': r[0], 'username': r[1] or '', 'first_name': r[2] or '',
                'number': r[3], 'country_code': r[4] or '',
                'otp_count': r[5], 'last_otp': r[6] or '', 'last_otp_value': r[7] or ''
            } for r in rows],
            'by_platform': by_platform
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/admin/api/stats')
def admin_api_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM otp_logs")
    otps = c.fetchone()[0]
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM otp_logs WHERE timestamp LIKE ?", (today + '%',))
    today_otps = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM combos")
    combos = c.fetchone()[0]
    conn.close()
    return jsonify({'users': users, 'otps': otps, 'today': today_otps, 'combos': combos})

@app.route('/admin/api/users')
def admin_api_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, assigned_number, is_banned FROM users ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    return jsonify([{'user_id': r[0], 'username': r[1] or r[2] or 'مستخدم', 'assigned_number': r[3], 'is_banned': r[4]} for r in rows])

@app.route('/admin/api/toggle_ban', methods=['POST'])
def admin_api_toggle_ban():
    data = request.json
    user_id = data.get('user_id')
    ban = data.get('ban')
    if not user_id:
        return jsonify({'ok': False})
    if ban:
        ban_user(user_id)
    else:
        unban_user(user_id)
    return jsonify({'ok': True})

@app.route('/admin/api/save_texts', methods=['POST'])
def admin_api_save_texts():
    data = request.json
    for key, value in data.items():
        update_text(key, value)
    return jsonify({'ok': True})

@app.route('/admin/api/save_links', methods=['POST'])
def admin_api_save_links():
    data = request.json
    for key, value in data.items():
        update_link(key, value)
    return jsonify({'ok': True})

@app.route('/admin/api/add_link', methods=['POST'])
def admin_api_add_link():
    data = request.json
    key = data.get('key')
    value = data.get('value')
    icon = data.get('icon', '🔗')
    if not key or not value:
        return jsonify({'ok': False})
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO site_links (key, value, icon) VALUES (?, ?, ?)", (key, value, icon))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/admin/api/delete_link', methods=['POST'])
def admin_api_delete_link():
    key = request.json.get('key')
    if key:
        delete_link(key)
        return jsonify({'ok': True})
    return jsonify({'ok': False})

@app.route('/admin/api/save_admin_id', methods=['POST'])
def admin_api_save_admin_id():
    admin_id = request.json.get('admin_telegram_id')
    if admin_id:
        set_admin_setting('admin_telegram_id', admin_id)
        return jsonify({'ok': True})
    return jsonify({'ok': False})

@app.route('/admin/api/change_password', methods=['POST'])
def admin_api_change_password():
    global ADMIN_PASSWORD
    new_pwd = request.json.get('password')
    if new_pwd:
        ADMIN_PASSWORD = new_pwd
        return jsonify({'ok': True})
    return jsonify({'ok': False})

@app.route('/admin/upload_combo', methods=['POST'])
def admin_upload_combo():
    platform = request.form.get('platform')
    file = request.files.get('file')
    if not file or not file.filename.endswith('.txt'):
        return redirect(url_for('admin_dashboard'))
    content = file.read().decode('utf-8')
    numbers = [line.strip() for line in content.splitlines() if line.strip()]
    if not numbers:
        return redirect(url_for('admin_dashboard'))
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
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_combo', methods=['POST'])
def admin_delete_combo():
    platform = request.form.get('platform')
    country_code = request.form.get('country_code')
    if platform and country_code:
        delete_combo(platform, country_code)
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/clear_otps', methods=['POST'])
def admin_clear_otps():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM otp_logs")
    conn.commit()
    conn.close()
    _otp_cache['data'] = None
    _otp_cache['time'] = 0
    return redirect(url_for('admin_dashboard'))

# ========== مراقبة القناة ==========
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

# ========== بوت المساعد والإعلانات ==========
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
                if chat_id:
                    try:
                        conn_k = sqlite3.connect(DB_PATH)
                        conn_k.execute(
                            "INSERT OR REPLACE INTO known_chats (chat_id, chat_type, chat_title, last_seen) VALUES (?, ?, ?, ?)",
                            (str(chat_id), chat_type, chat.get('title') or chat.get('username') or chat.get('first_name') or 'unknown', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        )
                        conn_k.commit()
                        conn_k.close()
                    except Exception as e:
                        print(f"⚠️ فشل حفظ chat_id: {e}")
                if text and text.strip() == '/chatid':
                    try:
                        requests.post(f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/sendMessage", json={
                            'chat_id': chat_id,
                            'text': f"📋 <b>معلومات الدردشة</b>\n\n🆔 Chat ID: <code>{chat_id}</code>\n📌 النوع: <b>{chat_type}</b>",
                            'parse_mode': 'HTML'
                        }, timeout=10)
                    except: pass
                    continue
                if text and text.strip() == '/start' and chat_type == 'private':
                    try:
                        requests.post(f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/sendMessage", json={
                            'chat_id': chat_id,
                            'text': '🤖 <b>مرحباً بك في بوت المطري OTP</b>\n\nهذا البوت مربوط بموقع المطري OTP.',
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
                elif chat_type == 'private':
                    if not text:
                        continue
                    if text == '/start':
                        requests.post(f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/sendMessage", json={
                            'chat_id': chat_id,
                            'text': '🤖 <b>مرحباً بك في بوت المطري OTP</b>\n\nهذا البوت مربوط بموقع المطري OTP.'
                        }, timeout=10)
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
                        requests.post(f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/sendMessage", json={
                            'chat_id': chat_id,
                            'text': '🆘 <b>تم استلام طلب المساعدة!</b>\n\n✅ تم إشعار الأدمن بطلبك.'
                        }, timeout=10)
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
                            requests.post(f"https://api.telegram.org/bot{ASSISTANT_BOT_TOKEN}/sendMessage", json={
                                'chat_id': chat_id,
                                'text': '✅ <b>تم إرسال رسالتك للإدمن.</b>'
                            }, timeout=10)
        except Exception as e:
            print(f"❌ خطأ في بوت تيليجرام: {e}")
        time.sleep(3)

threading.Thread(target=monitor_telegram_group, daemon=True).start()
# ========== 📡 API للأكواد (التطبيق يقرأ من هنا) ==========

@app.route('/api/latest-code', methods=['GET'])
def api_latest_code():
    """API يجيب آخر كود"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT number, otp, timestamp, platform FROM otp_logs ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        
        if row:
            return jsonify({
                'success': True,
                'number': row[0],
                'code': row[1],
                'timestamp': row[2],
                'platform': row[3]
            })
        return jsonify({'success': False, 'message': 'لا توجد أكواد'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/all-codes', methods=['GET'])
def api_all_codes():
    """API يجيب كل الأكواد"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT number, otp, timestamp, platform FROM otp_logs ORDER BY id DESC LIMIT 20")
        rows = c.fetchall()
        conn.close()
        
        codes = [{'number': r[0], 'code': r[1], 'timestamp': r[2], 'platform': r[3]} for r in rows]
        return jsonify({'success': True, 'codes': codes})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/test-otp', methods=['GET'])
def test_otp():
    """اختبار - يحط كود عشوائي"""
    import random
    test_code = str(random.randint(100000, 999999))
    test_number = "967" + str(random.randint(10000000, 99999999))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO otp_logs (number, otp, timestamp, platform) VALUES (?, ?, ?, ?)",
              (test_number, test_code, now, "whatsapp"))
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'code': test_code,
        'number': test_number,
        'message': 'كود تجريبي تم إنشاؤه!'
    })

# ========== تشغيل التطبيق ==========
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)