#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════
  MTR NUMBERS  —  المطري Numbers
  Virtual Numbers & SMS Platform
  v1.0.0
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import re
import io
import csv
import json
import hmac
import time
import uuid
import math
import asyncio
import sqlite3
import hashlib
import logging
import secrets
import threading
import traceback
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

# ─── Telegram (aiogram 3.31+) ─────────────────────────────
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, BufferedInputFile,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# ─── FastAPI / Uvicorn ────────────────────────────────────
from fastapi import FastAPI, Request, Response, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn


# ══════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════
class Config:
    # ─── Branding ──────────────────────────────────────
    BRAND_AR = "المطري Numbers"
    BRAND_EN = "MTR NUMBERS"
    VERSION  = "1.0.0"

    # ─── Telegram ──────────────────────────────────────
    BOT_TOKEN = "8935860202:AAHSzllEnQIA5RtX1jVmt4UUhHueBNvkWBQ"
    OWNER_ID  = 7325566792

    # ─── Server ────────────────────────────────────────
    WEB_HOST  = "0.0.0.0"
    WEB_PORT  = 8090
    SECRET_KEY = secrets.token_hex(32)

    # ─── Database ──────────────────────────────────────
    BASE_DIR = Path(__file__).resolve().parent
    DATA_DIR = BASE_DIR / "data"
    DB_PATH  = DATA_DIR / "mtr.db"

    # ─── Business Rules ────────────────────────────────
    MIN_DEPOSIT       = 1.0
    MAX_ORDER_AMOUNT  = 1000.0
    ORDER_TIMEOUT_MIN = 20
    RATE_PER_MIN      = 30
    CURRENCY          = "USD"

    # ─── 🎨 ألوان الأزرار الحقيقية (Telegram Bot API 9.4) ──
    # القيم المدعومة رسمياً: primary / success / danger
    BTN_PRIMARY = "primary"   # 🔵 أزرق - العمليات الرئيسية
    BTN_SUCCESS = "success"   # 🟢 أخضر - التأكيد والنجاح
    BTN_DANGER  = "danger"    # 🔴 أحمر - الحذف وإلغاء

    # ─── 🎨 ألوان WebApp (CSS) ────────────────────────
    COLOR_PRIMARY  = "#3b82f6"   # 🔵 أزرق
    COLOR_SUCCESS  = "#22c55e"   # 🟢 أخضر
    COLOR_DANGER   = "#ef4444"   # 🔴 أحمر
    COLOR_WARNING  = "#f59e0b"   # 🟡 برتقالي
    COLOR_INFO     = "#06b6d4"   # سماوي
    COLOR_PURPLE   = "#8b5cf6"   # بنفسجي
    COLOR_BG       = "#0a0e1a"
    COLOR_CARD     = "#1e293b"
    COLOR_TEXT     = "#f1f5f9"
    COLOR_MUTED    = "#94a3b8"
    COLOR_BORDER   = "#334155"

    @classmethod
    def ensure_dirs(cls):
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN or ":" not in cls.BOT_TOKEN:
            print("[!] BOT_TOKEN غير صالح")
            raise SystemExit(1)
        if not cls.OWNER_ID:
            print("[!] OWNER_ID مطلوب")
            raise SystemExit(1)


Config.ensure_dirs()


# ══════════════════════════════════════════════════════════════
#  LOGGER
# ══════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("mtr")
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("aiogram").setLevel(logging.WARNING)


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_ts() -> float:
    return time.time()


def safe_int(v, default=0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def safe_float(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def money(v: float) -> str:
    return f"${v:.4f}"


def mask_secret(s: str, keep: int = 4) -> str:
    """يخفي الأسرار في السجلات"""
    if not s:
        return "***"
    s = str(s)
    if len(s) <= keep * 2:
        return "*" * len(s)
    return s[:keep] + "*" * (len(s) - keep * 2) + s[-keep:]


def validate_phone(num: str) -> bool:
    num = re.sub(r"[^\d+]", "", str(num))
    return bool(re.match(r"^\+\d{7,15}$", num))


def normalize_phone(num: str) -> str:
    num = re.sub(r"[^\d]", "", str(num))
    return "+" + num if num else ""


def svg_icon(name: str, color: str = "currentColor", size: int = 20) -> str:
    """أيقونات SVG حقيقية"""
    icons = {
        "dashboard": '<path d="M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z"/>',
        "users": '<circle cx="9" cy="7" r="4"/><path d="M3 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2M16 3.13a4 4 0 0 1 0 7.75M21 21v-2a4 4 0 0 0-3-3.87"/>',
        "inventory": '<path d="M20 7l-8-4-8 4 8 4 8-4z"/><path d="M4 12l8 4 8-4M4 17l8 4 8-4"/>',
        "orders": '<path d="M9 11H3v10h6zM21 3h-6v18h6zM15 7H9v14h6z"/>',
        "providers": '<path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>',
        "wallet": '<path d="M21 12V7H5a2 2 0 0 1 0-4h14v4M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4z"/>',
        "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
        "chart": '<path d="M18 20V10M12 20V4M6 20v-6"/>',
        "check": '<path d="M20 6L9 17l-5-5"/>',
        "x": '<circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/>',
        "plus": '<path d="M12 5v14M5 12h14"/>',
        "edit": '<path d="M11 4H4v16h16v-7M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
        "trash": '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>',
        "search": '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
        "copy": '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
        "refresh": '<path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 4v5h-5"/>',
        "globe": '<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/>',
        "tag": '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><circle cx="7" cy="7" r="1" fill="currentColor"/>',
        "server": '<rect x="2" y="3" width="20" height="7" rx="2"/><rect x="2" y="14" width="20" height="7" rx="2"/><path d="M6 6.5h.01M6 17.5h.01"/>',
        "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
        "bell": '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
        "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
        "backup": '<path d="M21 12a9 9 0 1 1-9-9"/><path d="M21 3v6h-6"/>',
        "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
        "lock": '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    }
    path = icons.get(name, icons["file"])
    return f'<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="{size}" height="{size}">{path}</svg>'


# ══════════════════════════════════════════════════════════════
#  ▓▓▓ نهاية الجزء 1 ▓▓▓
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  DATABASE — Schema (20 جدول)
# ══════════════════════════════════════════════════════════════
class Database:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        self._init_schema()
        log.info(f"[DB] Ready: {path.name}")

    def _conn(self):
        c = sqlite3.connect(str(self.path), timeout=15.0, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=15000")
        return c

    def _init_schema(self):
        with self._lock, self._conn() as c:
            c.executescript("""

            -- ═══ 1. USERS ═══
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id           INTEGER UNIQUE,
                username        TEXT,
                first_name      TEXT,
                last_name       TEXT,
                balance         REAL DEFAULT 0.0,
                total_spent     REAL DEFAULT 0.0,
                total_deposited REAL DEFAULT 0.0,
                total_refunded  REAL DEFAULT 0.0,
                status          TEXT DEFAULT 'active',
                role_id         INTEGER,
                language        TEXT DEFAULT 'ar',
                notes           TEXT,
                created_at      TEXT NOT NULL,
                last_seen       TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_users_tg ON users(tg_id);

            -- ═══ 2. ROLES ═══
            CREATE TABLE IF NOT EXISTS roles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                slug        TEXT UNIQUE NOT NULL,
                name_ar     TEXT NOT NULL,
                name_en     TEXT,
                is_system   INTEGER DEFAULT 0,
                created_at  TEXT NOT NULL
            );

            -- ═══ 3. PERMISSIONS ═══
            CREATE TABLE IF NOT EXISTS permissions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                slug        TEXT UNIQUE NOT NULL,
                name_ar     TEXT NOT NULL,
                category    TEXT
            );

            -- ═══ 4. ROLE_PERMISSIONS ═══
            CREATE TABLE IF NOT EXISTS role_permissions (
                role_id         INTEGER NOT NULL,
                permission_id   INTEGER NOT NULL,
                PRIMARY KEY(role_id, permission_id),
                FOREIGN KEY(role_id) REFERENCES roles(id) ON DELETE CASCADE,
                FOREIGN KEY(permission_id) REFERENCES permissions(id) ON DELETE CASCADE
            );

            -- ═══ 5. COUNTRIES ═══
            CREATE TABLE IF NOT EXISTS countries (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                iso         TEXT UNIQUE NOT NULL,
                name_ar     TEXT NOT NULL,
                name_en     TEXT NOT NULL,
                dial_code   TEXT NOT NULL,
                flag        TEXT,
                status      TEXT DEFAULT 'active',
                sort_order  INTEGER DEFAULT 100,
                created_at  TEXT NOT NULL
            );

            -- ═══ 6. SERVICES ═══
            CREATE TABLE IF NOT EXISTS services (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                slug        TEXT UNIQUE NOT NULL,
                name_ar     TEXT NOT NULL,
                name_en     TEXT NOT NULL,
                icon        TEXT,
                color       TEXT DEFAULT '#3b82f6',
                status      TEXT DEFAULT 'active',
                sort_order  INTEGER DEFAULT 100,
                created_at  TEXT NOT NULL
            );

            -- ═══ 7. PROVIDERS ═══
            CREATE TABLE IF NOT EXISTS providers (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                slug            TEXT UNIQUE NOT NULL,
                name            TEXT NOT NULL,
                adapter         TEXT NOT NULL,
                api_url         TEXT,
                api_key         TEXT,
                api_secret      TEXT,
                username        TEXT,
                password        TEXT,
                email           TEXT,
                extra_config    TEXT,
                status          TEXT DEFAULT 'active',
                priority        INTEGER DEFAULT 100,
                timeout_sec     INTEGER DEFAULT 30,
                retry_count     INTEGER DEFAULT 3,
                balance         REAL DEFAULT 0.0,
                currency        TEXT DEFAULT 'USD',
                last_ping       TEXT,
                last_success    TEXT,
                latency_ms      INTEGER DEFAULT 0,
                success_count   INTEGER DEFAULT 0,
                error_count     INTEGER DEFAULT 0,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            );

            -- ═══ 8. PROVIDER_COUNTRIES ═══
            CREATE TABLE IF NOT EXISTS provider_countries (
                provider_id     INTEGER NOT NULL,
                country_id      INTEGER NOT NULL,
                provider_code   TEXT,
                PRIMARY KEY(provider_id, country_id),
                FOREIGN KEY(provider_id) REFERENCES providers(id) ON DELETE CASCADE,
                FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
            );

            -- ═══ 9. PROVIDER_SERVICES ═══
            CREATE TABLE IF NOT EXISTS provider_services (
                provider_id     INTEGER NOT NULL,
                service_id      INTEGER NOT NULL,
                provider_code   TEXT,
                cost            REAL DEFAULT 0.0,
                PRIMARY KEY(provider_id, service_id),
                FOREIGN KEY(provider_id) REFERENCES providers(id) ON DELETE CASCADE,
                FOREIGN KEY(service_id) REFERENCES services(id) ON DELETE CASCADE
            );

            -- ═══ 10. INVENTORY (أرقام المزودين) ═══
            CREATE TABLE IF NOT EXISTS inventory (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                number          TEXT NOT NULL,
                country_id      INTEGER,
                service_id      INTEGER,
                provider_id     INTEGER,
                cost            REAL DEFAULT 0.0,
                status          TEXT DEFAULT 'available',
                reserved_until  TEXT,
                order_id        INTEGER,
                imported_at     TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                UNIQUE(number, country_id, service_id, provider_id),
                FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE SET NULL,
                FOREIGN KEY(service_id) REFERENCES services(id) ON DELETE SET NULL,
                FOREIGN KEY(provider_id) REFERENCES providers(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_inv_status ON inventory(status);
            CREATE INDEX IF NOT EXISTS idx_inv_cs ON inventory(country_id, service_id);

            -- ═══ 11. PRICES ═══
            CREATE TABLE IF NOT EXISTS prices (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                country_id      INTEGER,
                service_id      INTEGER,
                provider_id     INTEGER,
                cost            REAL DEFAULT 0.0,
                profit_fixed    REAL DEFAULT 0.0,
                profit_percent  REAL DEFAULT 0.0,
                sell_price      REAL DEFAULT 0.0,
                min_price       REAL DEFAULT 0.0,
                status          TEXT DEFAULT 'active',
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE,
                FOREIGN KEY(service_id) REFERENCES services(id) ON DELETE CASCADE,
                FOREIGN KEY(provider_id) REFERENCES providers(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_prices_cs ON prices(country_id, service_id);

            -- ═══ 12. ORDERS ═══
            CREATE TABLE IF NOT EXISTS orders (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                order_code      TEXT UNIQUE NOT NULL,
                user_id         INTEGER NOT NULL,
                country_id      INTEGER,
                service_id      INTEGER,
                provider_id     INTEGER,
                inventory_id    INTEGER,
                number          TEXT,
                cost            REAL DEFAULT 0.0,
                sell_price      REAL DEFAULT 0.0,
                profit          REAL DEFAULT 0.0,
                status          TEXT DEFAULT 'pending',
                otp_code        TEXT,
                otp_text        TEXT,
                idempotency_key TEXT UNIQUE,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                completed_at    TEXT,
                expires_at      TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE SET NULL,
                FOREIGN KEY(service_id) REFERENCES services(id) ON DELETE SET NULL,
                FOREIGN KEY(provider_id) REFERENCES providers(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
            CREATE INDEX IF NOT EXISTS idx_orders_code ON orders(order_code);

            -- ═══ 13. ORDER_EVENTS ═══
            CREATE TABLE IF NOT EXISTS order_events (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id        INTEGER NOT NULL,
                event_type      TEXT NOT NULL,
                message         TEXT,
                payload         TEXT,
                created_at      TEXT NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_events_order ON order_events(order_id);

            -- ═══ 14. TRANSACTIONS ═══
            CREATE TABLE IF NOT EXISTS transactions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tx_code         TEXT UNIQUE NOT NULL,
                user_id         INTEGER NOT NULL,
                type            TEXT NOT NULL,
                amount          REAL NOT NULL,
                balance_before  REAL NOT NULL,
                balance_after   REAL NOT NULL,
                reference       TEXT,
                note            TEXT,
                created_at      TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id);

            -- ═══ 15. PAYMENTS ═══
            CREATE TABLE IF NOT EXISTS payments (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_code    TEXT UNIQUE NOT NULL,
                user_id         INTEGER NOT NULL,
                amount          REAL NOT NULL,
                method          TEXT,
                provider_tx     TEXT,
                status          TEXT DEFAULT 'pending',
                proof           TEXT,
                note            TEXT,
                verified_by     INTEGER,
                created_at      TEXT NOT NULL,
                verified_at     TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_pay_user ON payments(user_id);
            CREATE INDEX IF NOT EXISTS idx_pay_status ON payments(status);

            -- ═══ 16. AUDIT_LOGS ═══
            CREATE TABLE IF NOT EXISTS audit_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id        INTEGER,
                actor_name      TEXT,
                action          TEXT NOT NULL,
                target_type     TEXT,
                target_id       INTEGER,
                before_data     TEXT,
                after_data      TEXT,
                ip              TEXT,
                user_agent      TEXT,
                created_at      TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor_id);
            CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_logs(created_at);

            -- ═══ 17. NOTIFICATIONS ═══
            CREATE TABLE IF NOT EXISTS notifications (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                kind            TEXT NOT NULL,
                severity        TEXT DEFAULT 'info',
                title           TEXT NOT NULL,
                message         TEXT,
                target_role     TEXT,
                target_user     INTEGER,
                is_read         INTEGER DEFAULT 0,
                created_at      TEXT NOT NULL
            );

            -- ═══ 18. SETTINGS ═══
            CREATE TABLE IF NOT EXISTS settings (
                key     TEXT PRIMARY KEY,
                value   TEXT,
                category TEXT DEFAULT 'general',
                updated_at TEXT NOT NULL
            );

            -- ═══ 19. MENUS (Menu Builder) ═══
            CREATE TABLE IF NOT EXISTS menus (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                menu_key        TEXT UNIQUE NOT NULL,
                name_ar         TEXT NOT NULL,
                is_default      INTEGER DEFAULT 0,
                status          TEXT DEFAULT 'active',
                created_at      TEXT NOT NULL
            );

            -- ═══ 20. BUTTONS (Button Builder) ═══
            CREATE TABLE IF NOT EXISTS buttons (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                menu_id         INTEGER,
                parent_id       INTEGER,
                label           TEXT NOT NULL,
                icon            TEXT,
                btype           TEXT DEFAULT 'callback',
                action          TEXT,
                row_pos         INTEGER DEFAULT 0,
                col_pos         INTEGER DEFAULT 0,
                sort_order      INTEGER DEFAULT 100,
                style           TEXT DEFAULT 'primary',
                permission      TEXT,
                status          TEXT DEFAULT 'active',
                FOREIGN KEY(menu_id) REFERENCES menus(id) ON DELETE CASCADE
            );

            -- ═══ 21. TRANSLATIONS (Text Manager) ═══
            CREATE TABLE IF NOT EXISTS translations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                lang        TEXT NOT NULL,
                key         TEXT NOT NULL,
                value       TEXT NOT NULL,
                updated_at  TEXT NOT NULL,
                UNIQUE(lang, key)
            );

            -- ═══ 22. BACKUPS ═══
            CREATE TABLE IF NOT EXISTS backups (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                filename    TEXT NOT NULL,
                size_bytes  INTEGER DEFAULT 0,
                created_by  INTEGER,
                created_at  TEXT NOT NULL
            );

            """)
            self._seed_defaults(c)

    def _seed_defaults(self, c):
        now = now_iso()

        # ── 8 Roles افتراضية ──
        roles = [
            ("owner",             "المالك",          1),
            ("super_admin",       "مدير عام",        1),
            ("admin",             "مشرف",            1),
            ("finance",           "مالية",           1),
            ("inventory_manager", "مدير مخزون",      1),
            ("provider_manager",  "مدير مزودين",     1),
            ("support",           "دعم فني",         1),
            ("analyst",           "محلل",            1),
            ("moderator",         "مشرف مستخدمين",   1),
        ]
        for slug, name, sys in roles:
            c.execute("INSERT OR IGNORE INTO roles(slug, name_ar, is_system, created_at) VALUES(?,?,?,?)",
                      (slug, name, sys, now))

        # ── Permissions ──
        perms = [
            ("users.view","عرض المستخدمين","users"),
            ("users.edit","تعديل المستخدمين","users"),
            ("users.block","حظر المستخدمين","users"),
            ("users.balance","تعديل الرصيد","users"),
            ("providers.view","عرض المزودين","providers"),
            ("providers.edit","تعديل المزودين","providers"),
            ("providers.credentials","عرض بيانات الاعتماد","providers"),
            ("inventory.view","عرض المخزون","inventory"),
            ("inventory.import","استيراد المخزون","inventory"),
            ("inventory.delete","حذف المخزون","inventory"),
            ("orders.view","عرض الطلبات","orders"),
            ("orders.cancel","إلغاء الطلبات","orders"),
            ("orders.refund","استرجاع الطلبات","orders"),
            ("finance.view","عرض المالية","finance"),
            ("finance.refund","الاسترجاع المالي","finance"),
            ("finance.adjust","تعديل الرصيد","finance"),
            ("settings.view","عرض الإعدادات","settings"),
            ("settings.edit","تعديل الإعدادات","settings"),
            ("panels.manage","إدارة اللوحات","admin"),
            ("backups.manage","إدارة النسخ","admin"),
            ("audit.view","عرض السجل","admin"),
        ]
        for slug, name, cat in perms:
            c.execute("INSERT OR IGNORE INTO permissions(slug, name_ar, category) VALUES(?,?,?)",
                      (slug, name, cat))

        # ── Owner يأخذ كل الصلاحيات ──
        c.execute("""
            INSERT OR IGNORE INTO role_permissions(role_id, permission_id)
            SELECT r.id, p.id FROM roles r, permissions p WHERE r.slug='owner'
        """)

        # ── 8 Countries افتراضية ──
        countries = [
            ("YE","اليمن","Yemen","+967","🇾🇪",1),
            ("SA","السعودية","Saudi Arabia","+966","🇸🇦",2),
            ("EG","مصر","Egypt","+20","🇪🇬",3),
            ("AE","الإمارات","UAE","+971","🇦🇪",4),
            ("MA","المغرب","Morocco","+212","🇲🇦",5),
            ("DZ","الجزائر","Algeria","+213","🇩🇿",6),
            ("IQ","العراق","Iraq","+964","🇮🇶",7),
            ("JO","الأردن","Jordan","+962","🇯🇴",8),
        ]
        for iso, ar, en, dial, flag, sort in countries:
            c.execute("""INSERT OR IGNORE INTO countries(iso, name_ar, name_en, dial_code, flag, sort_order, created_at)
                         VALUES(?,?,?,?,?,?,?)""",
                      (iso, ar, en, dial, flag, sort, now))

        # ── 8 Services افتراضية ──
        services = [
            ("whatsapp","واتساب","WhatsApp","#25d366",1),
            ("telegram","تلجرام","Telegram","#229ED9",2),
            ("facebook","فيسبوك","Facebook","#1877F2",3),
            ("instagram","إنستجرام","Instagram","#E4405F",4),
            ("google","جوجل","Google","#4285F4",5),
            ("discord","ديسكورد","Discord","#5865F2",6),
            ("tiktok","تيك توك","TikTok","#000000",7),
            ("twitter","تويتر","Twitter","#1DA1F2",8),
        ]
        for slug, ar, en, color, sort in services:
            c.execute("""INSERT OR IGNORE INTO services(slug, name_ar, name_en, color, sort_order, created_at)
                         VALUES(?,?,?,?,?,?)""",
                      (slug, ar, en, color, sort, now))

        # ── Settings ──
        defaults = [
            ("brand_ar", Config.BRAND_AR, "branding"),
            ("brand_en", Config.BRAND_EN, "branding"),
            ("currency", Config.CURRENCY, "business"),
            ("min_deposit", str(Config.MIN_DEPOSIT), "business"),
            ("order_timeout", str(Config.ORDER_TIMEOUT_MIN), "business"),
            ("color_primary", Config.COLOR_PRIMARY, "appearance"),
            ("color_success", Config.COLOR_SUCCESS, "appearance"),
            ("color_danger",  Config.COLOR_DANGER,  "appearance"),
        ]
        for k, v, cat in defaults:
            c.execute("INSERT OR IGNORE INTO settings(key, value, category, updated_at) VALUES(?,?,?,?)",
                      (k, v, cat, now))

        # ── Menu افتراضي ──
        c.execute("INSERT OR IGNORE INTO menus(menu_key, name_ar, is_default, created_at) VALUES(?,?,?,?)",
                  ("main", "القائمة الرئيسية", 1, now))

        # ── Translations أساسية ──
        trans = [
            ("ar", "welcome",  "🌐 أهلاً بك في المطري Numbers"),
            ("ar", "buy",      "🛒 شراء رقم"),
            ("ar", "my_orders","📦 طلباتي"),
            ("ar", "balance",  "💰 رصيدي"),
            ("ar", "deposit",  "➕ إيداع"),
            ("ar", "support",  "💬 الدعم الفني"),
            ("en", "welcome",  "🌐 Welcome to MTR Numbers"),
            ("en", "buy",      "🛒 Buy Number"),
            ("en", "my_orders","📦 My Orders"),
            ("en", "balance",  "💰 Balance"),
            ("en", "deposit",  "➕ Deposit"),
            ("en", "support",  "💬 Support"),
        ]
        for lang, k, v in trans:
            c.execute("INSERT OR IGNORE INTO translations(lang, key, value, updated_at) VALUES(?,?,?,?)",
                      (lang, k, v, now))

        log.info("[DB] Seed complete: 9 roles, 21 perms, 8 countries, 8 services")


# ══════════════════════════════════════════════════════════════
#  ▓▓▓ نهاية الجزء 2 ▓▓▓
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  DB ACCESS LAYER — CRUD لكل الجداول
#  يستخدم نفس اتصال Database
# ══════════════════════════════════════════════════════════════
class DB:
    """طبقة CRUD موحدة — كل المكونات تستخدمها"""

    def __init__(self, database: Database):
        self.db = database
        self._lock = database._lock

    def _conn(self):
        return self.db._conn()

    # ══════════════════════════════════════════════════════
    #  USERS
    # ══════════════════════════════════════════════════════
    def user_upsert(self, tg_id: int, username: str = "",
                    first_name: str = "", last_name: str = "") -> int:
        now = now_iso()
        with self._lock, self._conn() as c:
            row = c.execute("SELECT id FROM users WHERE tg_id=?", (tg_id,)).fetchone()
            if row:
                c.execute("""UPDATE users SET username=?, first_name=?, last_name=?, last_seen=?
                             WHERE tg_id=?""",
                          (username, first_name, last_name, now, tg_id))
                return row["id"]
            # أول مستخدم = Owner
            is_owner = (tg_id == Config.OWNER_ID)
            role_id = 1 if is_owner else None
            cur = c.execute("""INSERT INTO users(tg_id, username, first_name, last_name,
                                role_id, created_at, last_seen)
                               VALUES(?,?,?,?,?,?,?)""",
                            (tg_id, username, first_name, last_name, role_id, now, now))
            return cur.lastrowid

    def user_get(self, uid: int) -> Optional[dict]:
        with self._lock, self._conn() as c:
            r = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
            return dict(r) if r else None

    def user_get_by_tg(self, tg_id: int) -> Optional[dict]:
        with self._lock, self._conn() as c:
            r = c.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)).fetchone()
            return dict(r) if r else None

    def user_list(self, limit: int = 100, offset: int = 0,
                  status: str = None, search: str = None) -> list[dict]:
        q = "SELECT * FROM users WHERE 1=1"
        p = []
        if status:
            q += " AND status=?"; p.append(status)
        if search:
            q += " AND (username LIKE ? OR first_name LIKE ? OR CAST(tg_id AS TEXT) LIKE ?)"
            s = f"%{search}%"; p += [s, s, s]
        q += " ORDER BY id DESC LIMIT ? OFFSET ?"
        p += [limit, offset]
        with self._lock, self._conn() as c:
            return [dict(r) for r in c.execute(q, p).fetchall()]

    def user_count(self) -> int:
        with self._lock, self._conn() as c:
            return c.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]

    def user_set_status(self, uid: int, status: str) -> bool:
        with self._lock, self._conn() as c:
            cur = c.execute("UPDATE users SET status=? WHERE id=?", (status, uid))
            return cur.rowcount > 0

    def user_set_role(self, uid: int, role_id: int) -> bool:
        with self._lock, self._conn() as c:
            cur = c.execute("UPDATE users SET role_id=? WHERE id=?", (role_id, uid))
            return cur.rowcount > 0

    def user_set_language(self, uid: int, lang: str) -> bool:
        with self._lock, self._conn() as c:
            cur = c.execute("UPDATE users SET language=? WHERE id=?", (lang, uid))
            return cur.rowcount > 0

    def user_set_notes(self, uid: int, notes: str) -> bool:
        with self._lock, self._conn() as c:
            cur = c.execute("UPDATE users SET notes=? WHERE id=?", (notes, uid))
            return cur.rowcount > 0

    # ══════════════════════════════════════════════════════
    #  COUNTRIES
    # ══════════════════════════════════════════════════════
    def country_list(self, status: str = None) -> list[dict]:
        q = "SELECT * FROM countries"
        p = []
        if status:
            q += " WHERE status=?"; p.append(status)
        q += " ORDER BY sort_order, name_ar"
        with self._lock, self._conn() as c:
            return [dict(r) for r in c.execute(q, p).fetchall()]

    def country_get(self, cid: int) -> Optional[dict]:
        with self._lock, self._conn() as c:
            r = c.execute("SELECT * FROM countries WHERE id=?", (cid,)).fetchone()
            return dict(r) if r else None

    def country_get_by_iso(self, iso: str) -> Optional[dict]:
        with self._lock, self._conn() as c:
            r = c.execute("SELECT * FROM countries WHERE iso=?", (iso,)).fetchone()
            return dict(r) if r else None

    def country_add(self, iso: str, name_ar: str, name_en: str,
                    dial: str, flag: str, sort: int = 100) -> Optional[int]:
        now = now_iso()
        with self._lock, self._conn() as c:
            try:
                cur = c.execute("""INSERT INTO countries(iso, name_ar, name_en, dial_code,
                                    flag, sort_order, created_at)
                                   VALUES(?,?,?,?,?,?,?)""",
                                (iso, name_ar, name_en, dial, flag, sort, now))
                return cur.lastrowid
            except sqlite3.IntegrityError:
                return None

    def country_update(self, cid: int, **fields) -> bool:
        allowed = {"name_ar", "name_en", "dial_code", "flag", "status", "sort_order"}
        u = {k: v for k, v in fields.items() if k in allowed}
        if not u: return False
        cols = ", ".join(f"{k}=?" for k in u)
        vals = list(u.values()) + [cid]
        with self._lock, self._conn() as c:
            return c.execute(f"UPDATE countries SET {cols} WHERE id=?", vals).rowcount > 0

    def country_delete(self, cid: int) -> bool:
        with self._lock, self._conn() as c:
            return c.execute("DELETE FROM countries WHERE id=?", (cid,)).rowcount > 0

    # ══════════════════════════════════════════════════════
    #  SERVICES
    # ══════════════════════════════════════════════════════
    def service_list(self, status: str = None) -> list[dict]:
        q = "SELECT * FROM services"
        p = []
        if status:
            q += " WHERE status=?"; p.append(status)
        q += " ORDER BY sort_order, name_ar"
        with self._lock, self._conn() as c:
            return [dict(r) for r in c.execute(q, p).fetchall()]

    def service_get(self, sid: int) -> Optional[dict]:
        with self._lock, self._conn() as c:
            r = c.execute("SELECT * FROM services WHERE id=?", (sid,)).fetchone()
            return dict(r) if r else None

    def service_get_by_slug(self, slug: str) -> Optional[dict]:
        with self._lock, self._conn() as c:
            r = c.execute("SELECT * FROM services WHERE slug=?", (slug,)).fetchone()
            return dict(r) if r else None

    def service_add(self, slug: str, name_ar: str, name_en: str,
                    icon: str = "", color: str = "#3b82f6", sort: int = 100) -> Optional[int]:
        now = now_iso()
        with self._lock, self._conn() as c:
            try:
                cur = c.execute("""INSERT INTO services(slug, name_ar, name_en, icon,
                                    color, sort_order, created_at)
                                   VALUES(?,?,?,?,?,?,?)""",
                                (slug, name_ar, name_en, icon, color, sort, now))
                return cur.lastrowid
            except sqlite3.IntegrityError:
                return None

    def service_update(self, sid: int, **fields) -> bool:
        allowed = {"name_ar", "name_en", "icon", "color", "status", "sort_order"}
        u = {k: v for k, v in fields.items() if k in allowed}
        if not u: return False
        cols = ", ".join(f"{k}=?" for k in u)
        vals = list(u.values()) + [sid]
        with self._lock, self._conn() as c:
            return c.execute(f"UPDATE services SET {cols} WHERE id=?", vals).rowcount > 0

    def service_delete(self, sid: int) -> bool:
        with self._lock, self._conn() as c:
            return c.execute("DELETE FROM services WHERE id=?", (sid,)).rowcount > 0

    # ══════════════════════════════════════════════════════
    #  PROVIDERS
    # ══════════════════════════════════════════════════════
    def provider_list(self, status: str = None) -> list[dict]:
        q = "SELECT * FROM providers"
        p = []
        if status:
            q += " WHERE status=?"; p.append(status)
        q += " ORDER BY priority, name"
        with self._lock, self._conn() as c:
            return [dict(r) for r in c.execute(q, p).fetchall()]

    def provider_get(self, pid: int) -> Optional[dict]:
        with self._lock, self._conn() as c:
            r = c.execute("SELECT * FROM providers WHERE id=?", (pid,)).fetchone()
            return dict(r) if r else None

    def provider_get_by_slug(self, slug: str) -> Optional[dict]:
        with self._lock, self._conn() as c:
            r = c.execute("SELECT * FROM providers WHERE slug=?", (slug,)).fetchone()
            return dict(r) if r else None

    def provider_add(self, slug: str, name: str, adapter: str,
                     api_url: str = "", api_key: str = "",
                     username: str = "", password: str = "",
                     priority: int = 100, timeout: int = 30) -> Optional[int]:
        now = now_iso()
        with self._lock, self._conn() as c:
            try:
                cur = c.execute("""INSERT INTO providers(slug, name, adapter, api_url,
                                    api_key, username, password, priority, timeout_sec,
                                    created_at, updated_at)
                                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                                (slug, name, adapter, api_url, api_key,
                                 username, password, priority, timeout, now, now))
                return cur.lastrowid
            except sqlite3.IntegrityError:
                return None

    def provider_update(self, pid: int, **fields) -> bool:
        allowed = {"name", "adapter", "api_url", "api_key", "api_secret",
                   "username", "password", "email", "extra_config",
                   "status", "priority", "timeout_sec", "retry_count",
                   "balance", "currency"}
        u = {k: v for k, v in fields.items() if k in allowed}
        if not u: return False
        u["updated_at"] = now_iso()
        cols = ", ".join(f"{k}=?" for k in u)
        vals = list(u.values()) + [pid]
        with self._lock, self._conn() as c:
            return c.execute(f"UPDATE providers SET {cols} WHERE id=?", vals).rowcount > 0

    def provider_delete(self, pid: int) -> bool:
        with self._lock, self._conn() as c:
            return c.execute("DELETE FROM providers WHERE id=?", (pid,)).rowcount > 0

    def provider_update_health(self, pid: int, latency: int,
                                success: bool = True) -> None:
        now = now_iso()
        with self._lock, self._conn() as c:
            if success:
                c.execute("""UPDATE providers SET latency_ms=?, last_ping=?, last_success=?,
                             success_count=success_count+1 WHERE id=?""",
                          (latency, now, now, pid))
            else:
                c.execute("""UPDATE providers SET latency_ms=?, last_ping=?,
                             error_count=error_count+1 WHERE id=?""",
                          (latency, now, pid))

    # ══════════════════════════════════════════════════════
    #  SETTINGS
    # ══════════════════════════════════════════════════════
    def setting_get(self, key: str, default: str = "") -> str:
        with self._lock, self._conn() as c:
            r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return r["value"] if r else default

    def setting_set(self, key: str, value: str, category: str = "general") -> None:
        now = now_iso()
        with self._lock, self._conn() as c:
            c.execute("""INSERT INTO settings(key, value, category, updated_at)
                         VALUES(?,?,?,?)
                         ON CONFLICT(key) DO UPDATE SET value=excluded.value,
                             category=excluded.category, updated_at=excluded.updated_at""",
                      (key, str(value), category, now))

    def setting_list(self, category: str = None) -> list[dict]:
        q = "SELECT * FROM settings"
        p = []
        if category:
            q += " WHERE category=?"; p.append(category)
        with self._lock, self._conn() as c:
            return [dict(r) for r in c.execute(q, p).fetchall()]

    # ══════════════════════════════════════════════════════
    #  STATS (للداشبورد)
    # ══════════════════════════════════════════════════════
    def stats_overview(self) -> dict:
        with self._lock, self._conn() as c:
            return {
                "users":          c.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"],
                "users_active":   c.execute("SELECT COUNT(*) AS n FROM users WHERE status='active'").fetchone()["n"],
                "orders":         c.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"],
                "orders_pending": c.execute("SELECT COUNT(*) AS n FROM orders WHERE status='pending'").fetchone()["n"],
                "orders_done":    c.execute("SELECT COUNT(*) AS n FROM orders WHERE status='completed'").fetchone()["n"],
                "orders_failed":  c.execute("SELECT COUNT(*) AS n FROM orders WHERE status='failed'").fetchone()["n"],
                "inventory_avail":c.execute("SELECT COUNT(*) AS n FROM inventory WHERE status='available'").fetchone()["n"],
                "inventory_used": c.execute("SELECT COUNT(*) AS n FROM inventory WHERE status!='available'").fetchone()["n"],
                "providers":      c.execute("SELECT COUNT(*) AS n FROM providers").fetchone()["n"],
                "providers_online":c.execute("SELECT COUNT(*) AS n FROM providers WHERE status='active'").fetchone()["n"],
                "revenue":        c.execute("SELECT COALESCE(SUM(sell_price),0) AS s FROM orders WHERE status='completed'").fetchone()["s"],
                "profit":         c.execute("SELECT COALESCE(SUM(profit),0) AS s FROM orders WHERE status='completed'").fetchone()["s"],
            }


# ══════════════════════════════════════════════════════════════
#  ▓▓▓ نهاية الجزء 3 ▓▓▓
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  WALLET — نظام المحفظة + المعاملات
#  يستخدم Database Transactions لضمان عدم تضارب الرصيد
# ══════════════════════════════════════════════════════════════
class WalletError(Exception):
    pass


class Wallet:
    """محفظة المستخدم — كل عملية لها transaction"""

    def __init__(self, db: DB):
        self.db = db
        self._lock = db._lock

    # ══════════════════════════════════════════════════════
    #  CORE — تنفيذ عملية ذرّية
    # ══════════════════════════════════════════════════════
    def _atomic_tx(self, uid: int, tx_type: str, amount: float,
                   reference: str = "", note: str = "") -> dict:
        """
        عملية ذرّية — BEGIN IMMEDIATE لضمان عدم التضارب.
        ترجع dict فيها:
          tx_code, balance_before, balance_after, amount
        """
        if amount == 0:
            raise WalletError("Amount لا يمكن يكون 0")

        tx_code = "TX" + uuid.uuid4().hex[:12].upper()
        now = now_iso()

        with self._lock, self.db._conn() as c:
            try:
                # BEGIN IMMEDIATE يقفل الجدول
                c.execute("BEGIN IMMEDIATE")

                # جلب المستخدم مع القفل
                r = c.execute("SELECT id, balance, status FROM users WHERE id=?", (uid,)).fetchone()
                if not r:
                    raise WalletError(f"المستخدم {uid} غير موجود")

                if r["status"] == "blocked":
                    raise WalletError("المستخدم محظور")

                before = float(r["balance"] or 0.0)
                after = before + amount

                if after < 0:
                    raise WalletError(f"رصيد غير كافٍ: {money(before)} (المطلوب: {money(abs(amount))})")

                # تحديث الرصيد
                c.execute("UPDATE users SET balance=? WHERE id=?", (after, uid))

                # تحديث الإحصائيات حسب النوع
                if tx_type == "deposit":
                    c.execute("UPDATE users SET total_deposited=total_deposited+? WHERE id=?",
                              (amount, uid))
                elif tx_type == "purchase":
                    c.execute("UPDATE users SET total_spent=total_spent+? WHERE id=?",
                              (abs(amount), uid))
                elif tx_type == "refund":
                    c.execute("UPDATE users SET total_refunded=total_refunded+? WHERE id=?",
                              (amount, uid))

                # تسجيل المعاملة
                c.execute("""INSERT INTO transactions(tx_code, user_id, type, amount,
                                balance_before, balance_after, reference, note, created_at)
                             VALUES(?,?,?,?,?,?,?,?,?)""",
                          (tx_code, uid, tx_type, amount, before, after,
                           reference, note, now))

                c.execute("COMMIT")

                return {
                    "tx_code": tx_code,
                    "balance_before": before,
                    "balance_after": after,
                    "amount": amount,
                    "type": tx_type,
                }
            except WalletError:
                c.execute("ROLLBACK")
                raise
            except Exception as e:
                c.execute("ROLLBACK")
                log.error(f"[Wallet] tx error: {e}")
                raise WalletError(str(e))

    # ══════════════════════════════════════════════════════
    #  PUBLIC API
    # ══════════════════════════════════════════════════════
    def deposit(self, uid: int, amount: float,
                reference: str = "", note: str = "") -> dict:
        """إيداع — يزيد الرصيد"""
        if amount <= 0:
            raise WalletError("الإيداع لازم > 0")
        if amount > Config.MAX_ORDER_AMOUNT:
            raise WalletError(f"الحد الأقصى للإيداع {money(Config.MAX_ORDER_AMOUNT)}")
        return self._atomic_tx(uid, "deposit", amount, reference, note or "إيداع")

    def purchase(self, uid: int, amount: float,
                 reference: str = "", note: str = "") -> dict:
        """شراء — يخصم من الرصيد"""
        if amount <= 0:
            raise WalletError("المبلغ لازم > 0")
        return self._atomic_tx(uid, "purchase", -abs(amount), reference, note or "شراء")

    def refund(self, uid: int, amount: float,
               reference: str = "", note: str = "") -> dict:
        """استرجاع — يزيد الرصيد"""
        if amount <= 0:
            raise WalletError("المبلغ لازم > 0")
        return self._atomic_tx(uid, "refund", amount, reference, note or "استرجاع")

    def adjust(self, uid: int, amount: float,
               note: str = "تعديل من الإدارة") -> dict:
        """تعديل يدوي من الإدارة (موجب أو سالب)"""
        return self._atomic_tx(uid, "adjustment", amount, "ADMIN", note)

    def balance(self, uid: int) -> float:
        """رصيد المستخدم الحالي"""
        with self._lock, self.db._conn() as c:
            r = c.execute("SELECT balance FROM users WHERE id=?", (uid,)).fetchone()
            return float(r["balance"] or 0.0) if r else 0.0

    # ══════════════════════════════════════════════════════
    #  HISTORY
    # ══════════════════════════════════════════════════════
    def history(self, uid: int, limit: int = 20,
                offset: int = 0, tx_type: str = None) -> list[dict]:
        q = "SELECT * FROM transactions WHERE user_id=?"
        p = [uid]
        if tx_type:
            q += " AND type=?"; p.append(tx_type)
        q += " ORDER BY id DESC LIMIT ? OFFSET ?"
        p += [limit, offset]
        with self._lock, self.db._conn() as c:
            return [dict(r) for r in c.execute(q, p).fetchall()]

    def history_count(self, uid: int = None) -> int:
        with self._lock, self.db._conn() as c:
            if uid:
                r = c.execute("SELECT COUNT(*) AS n FROM transactions WHERE user_id=?",
                              (uid,)).fetchone()
            else:
                r = c.execute("SELECT COUNT(*) AS n FROM transactions").fetchone()
            return r["n"]

    def stats(self, uid: int) -> dict:
        """إحصائيات محفظة المستخدم"""
        with self._lock, self.db._conn() as c:
            r = c.execute("""SELECT
                    COALESCE(balance,0) AS balance,
                    COALESCE(total_deposited,0) AS deposited,
                    COALESCE(total_spent,0) AS spent,
                    COALESCE(total_refunded,0) AS refunded
                FROM users WHERE id=?""", (uid,)).fetchone()
            if not r:
                return {"balance": 0, "deposited": 0, "spent": 0, "refunded": 0}
            return dict(r)


# ══════════════════════════════════════════════════════════════
#  PAYMENTS — طلبات الإيداع
# ══════════════════════════════════════════════════════════════
class PaymentStatus:
    PENDING   = "pending"
    PAID      = "paid"
    FAILED    = "failed"
    CANCELLED = "cancelled"
    REFUNDED  = "refunded"


class Payments:
    """إدارة طلبات الإيداع اليدوية"""

    def __init__(self, db: DB, wallet: Wallet):
        self.db = db
        self.wallet = wallet
        self._lock = db._lock

    def create_request(self, uid: int, amount: float,
                       method: str = "manual", note: str = "") -> dict:
        """المستخدم يطلب إيداع"""
        if amount < Config.MIN_DEPOSIT:
            raise WalletError(f"الحد الأدنى {money(Config.MIN_DEPOSIT)}")

        code = "PAY" + uuid.uuid4().hex[:10].upper()
        now = now_iso()

        with self._lock, self.db._conn() as c:
            c.execute("""INSERT INTO payments(payment_code, user_id, amount, method,
                            status, note, created_at)
                         VALUES(?,?,?,?,?,?,?)""",
                      (code, uid, amount, method, PaymentStatus.PENDING, note, now))
            pid = c.lastrowid

        return {"id": pid, "code": code, "amount": amount,
                "status": PaymentStatus.PENDING}

    def verify(self, pid: int, admin_id: int) -> dict:
        """الإدارة توافق على الإيداع"""
        with self._lock, self.db._conn() as c:
            r = c.execute("SELECT * FROM payments WHERE id=?", (pid,)).fetchone()
            if not r:
                raise WalletError("الطلب غير موجود")
            if r["status"] != PaymentStatus.PENDING:
                raise WalletError(f"الطلب مو في حالة pending — حالياً: {r['status']}")

            amount = float(r["amount"])
            uid = int(r["user_id"])

        # إيداع في المحفظة
        tx = self.wallet.deposit(uid, amount,
                                  reference=r["payment_code"],
                                  note=f"دفعة معتمدة #{r['payment_code']}")

        now = now_iso()
        with self._lock, self.db._conn() as c:
            c.execute("""UPDATE payments SET status=?, verified_by=?, verified_at=?
                         WHERE id=?""",
                      (PaymentStatus.PAID, admin_id, now, pid))

        return {"ok": True, "tx": tx, "amount": amount}

    def reject(self, pid: int, admin_id: int, reason: str = "") -> bool:
        """الإدارة ترفض الإيداع"""
        now = now_iso()
        with self._lock, self.db._conn() as c:
            cur = c.execute("""UPDATE payments SET status=?, verified_by=?, verified_at=?,
                                note=COALESCE(note,'') || ?
                                WHERE id=? AND status=?""",
                            (PaymentStatus.FAILED, admin_id, now,
                             f" | رُفض: {reason}", pid, PaymentStatus.PENDING))
            return cur.rowcount > 0

    def list(self, status: str = None, limit: int = 50) -> list[dict]:
        q = "SELECT p.*, u.username, u.first_name FROM payments p LEFT JOIN users u ON u.id=p.user_id"
        params = []
        if status:
            q += " WHERE p.status=?"; params.append(status)
        q += " ORDER BY p.id DESC LIMIT ?"
        params.append(limit)
        with self._lock, self.db._conn() as c:
            return [dict(r) for r in c.execute(q, params).fetchall()]

    def get(self, pid: int) -> Optional[dict]:
        with self._lock, self.db._conn() as c:
            r = c.execute("SELECT * FROM payments WHERE id=?", (pid,)).fetchone()
            return dict(r) if r else None


# ══════════════════════════════════════════════════════════════
#  ▓▓▓ نهاية الجزء 4 ▓▓▓
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  COUNTRY MANAGER
# ══════════════════════════════════════════════════════════════
class CountryManager:
    """إدارة الدول — كل شي من لوحة التحكم"""

    def __init__(self, db: DB):
        self.db = db

    def list_all(self, status: str = None) -> list[dict]:
        return self.db.country_list(status)

    def get(self, cid: int) -> Optional[dict]:
        return self.db.country_get(cid)

    def get_by_iso(self, iso: str) -> Optional[dict]:
        return self.db.country_get_by_iso(iso)

    def add(self, iso: str, name_ar: str, name_en: str,
            dial_code: str, flag: str = "") -> Optional[int]:
        iso = iso.upper().strip()[:3]
        dial_code = dial_code.strip()
        if not dial_code.startswith("+"):
            dial_code = "+" + dial_code.lstrip("+")
        return self.db.country_add(iso, name_ar.strip(), name_en.strip(),
                                    dial_code, flag, sort=100)

    def update(self, cid: int, **fields) -> bool:
        return self.db.country_update(cid, **fields)

    def disable(self, cid: int) -> bool:
        return self.db.country_update(cid, status="disabled")

    def enable(self, cid: int) -> bool:
        return self.db.country_update(cid, status="active")

    def delete(self, cid: int) -> bool:
        return self.db.country_delete(cid)

    def available_for_service(self, service_id: int) -> list[dict]:
        """الدول المتوفرة لخدمة معينة (فيها أرقام متاحة)"""
        q = """
            SELECT DISTINCT c.* FROM countries c
            JOIN inventory i ON i.country_id = c.id
            WHERE i.service_id = ? AND i.status = 'available'
                AND c.status = 'active'
            ORDER BY c.sort_order, c.name_ar
        """
        with self.db._lock, self.db._conn() as conn:
            return [dict(r) for r in conn.execute(q, (service_id,)).fetchall()]

    def stats(self) -> dict:
        """إحصائيات الدول"""
        with self.db._lock, self.db._conn() as c:
            total = c.execute("SELECT COUNT(*) AS n FROM countries").fetchone()["n"]
            active = c.execute("SELECT COUNT(*) AS n FROM countries WHERE status='active'").fetchone()["n"]
            return {"total": total, "active": active}


# ══════════════════════════════════════════════════════════════
#  SERVICE MANAGER
# ══════════════════════════════════════════════════════════════
class ServiceManager:
    """إدارة الخدمات — كل شي من لوحة التحكم"""

    def __init__(self, db: DB):
        self.db = db

    def list_all(self, status: str = None) -> list[dict]:
        return self.db.service_list(status)

    def get(self, sid: int) -> Optional[dict]:
        return self.db.service_get(sid)

    def get_by_slug(self, slug: str) -> Optional[dict]:
        return self.db.service_get_by_slug(slug)

    def add(self, slug: str, name_ar: str, name_en: str,
            icon: str = "", color: str = "#3b82f6") -> Optional[int]:
        slug = re.sub(r"[^a-z0-9_]", "_", slug.lower().strip())[:30]
        return self.db.service_add(slug, name_ar.strip(), name_en.strip(),
                                    icon, color, sort=100)

    def update(self, sid: int, **fields) -> bool:
        return self.db.service_update(sid, **fields)

    def disable(self, sid: int) -> bool:
        return self.db.service_update(sid, status="disabled")

    def enable(self, sid: int) -> bool:
        return self.db.service_update(sid, status="active")

    def delete(self, sid: int) -> bool:
        return self.db.service_delete(sid)

    def available_for_country(self, country_id: int) -> list[dict]:
        """الخدمات المتوفرة لدولة معينة"""
        q = """
            SELECT DISTINCT s.* FROM services s
            JOIN inventory i ON i.service_id = s.id
            WHERE i.country_id = ? AND i.status = 'available'
                AND s.status = 'active'
            ORDER BY s.sort_order, s.name_ar
        """
        with self.db._lock, self.db._conn() as conn:
            return [dict(r) for r in conn.execute(q, (country_id,)).fetchall()]

    def stats(self) -> dict:
        with self.db._lock, self.db._conn() as c:
            total = c.execute("SELECT COUNT(*) AS n FROM services").fetchone()["n"]
            active = c.execute("SELECT COUNT(*) AS n FROM services WHERE status='active'").fetchone()["n"]
            return {"total": total, "active": active}


# ══════════════════════════════════════════════════════════════
#  PROVIDER ADAPTER — Base Class
# ══════════════════════════════════════════════════════════════
class ProviderError(Exception):
    """خطأ من المزود"""
    pass


class ProviderBase:
    """
    الواجهة الأساسية لكل Provider Adapter.

    ⚠️ مهم: كل مزود له API مختلف — كل Adapter يورث من هذا ويطبق الدوال.
    لا يوجد 'تنفيذ عام' — كل provider له منطق خاص حسب وثائقه.

    ⚠️ نحن لا ندّعي دعم أي مزود بدون وثائق رسمية.
    """

    name: str = "base"
    slug: str = "base"

    def __init__(self, provider_row: dict):
        """
        provider_row: dict من DB فيه:
            api_url, api_key, api_secret, username, password, email,
            timeout_sec, retry_count, extra_config
        """
        self.row = provider_row or {}
        self.api_url = (self.row.get("api_url") or "").rstrip("/")
        self.api_key = self.row.get("api_key") or ""
        self.api_secret = self.row.get("api_secret") or ""
        self.username = self.row.get("username") or ""
        self.password = self.row.get("password") or ""
        self.email = self.row.get("email") or ""
        self.timeout = safe_int(self.row.get("timeout_sec"), 30)
        self.retry = safe_int(self.row.get("retry_count"), 3)
        try:
            self.extra = json.loads(self.row.get("extra_config") or "{}")
        except Exception:
            self.extra = {}

    # ══════════════════════════════════════════════════════
    #  القاعدة: كل Adapter يطبق هذي الدوال
    # ══════════════════════════════════════════════════════
    def get_balance(self) -> dict:
        """
        يرجع: {"balance": float, "currency": str}
        ⚠️ الافتراضي: غير مدعوم — كل Adapter يطبقه حسب وثائق المزود.
        """
        raise ProviderError(
            f"[{self.slug}] get_balance() غير مطبق. "
            "يجب تنفيذه حسب وثائق API المزود."
        )

    def get_countries(self) -> list[dict]:
        """
        يرجع: [{"code": str, "name": str}, ...]
        ⚠️ الافتراضي: غير مدعوم.
        """
        raise ProviderError(
            f"[{self.slug}] get_countries() غير مطبق. "
            "يجب تنفيذه حسب وثائق API المزود."
        )

    def get_services(self) -> list[dict]:
        """
        يرجع: [{"code": str, "name": str}, ...]
        ⚠️ الافتراضي: غير مدعوم.
        """
        raise ProviderError(
            f"[{self.slug}] get_services() غير مطبق."
        )

    def get_inventory(self, country: str, service: str) -> dict:
        """
        يرجع: {"available": int, "price": float}
        ⚠️ الافتراضي: غير مدعوم.
        """
        raise ProviderError(
            f"[{self.slug}] get_inventory() غير مطبق."
        )

    def request_number(self, country: str, service: str,
                       idempotency_key: str) -> dict:
        """
        يرجع: {
            "provider_order_id": str,
            "number": str,
            "expires_at": str (ISO),
            "cost": float
        }
        ⚠️ idempotency_key: لمنع الشراء المزدوج.
        ⚠️ الافتراضي: غير مدعوم.
        """
        raise ProviderError(
            f"[{self.slug}] request_number() غير مطبق."
        )

    def get_order_status(self, provider_order_id: str) -> dict:
        """
        يرجع: {
            "status": "pending"|"waiting"|"completed"|"cancelled"|"failed",
            "otp": str|None,
            "otp_text": str|None
        }
        ⚠️ OTP يُرجع فقط لو وصل فعلاً من المزود.
        ⚠️ لا نخمّن OTP.
        """
        raise ProviderError(
            f"[{self.slug}] get_order_status() غير مطبق."
        )

    def get_sms(self, provider_order_id: str) -> Optional[dict]:
        """
        يرجع رسالة SMS كاملة إن وصلت:
            {"code": str, "text": str, "received_at": str}
        أو None إذا لم تصل بعد.
        ⚠️ لا تخمين — فقط من المزود.
        """
        raise ProviderError(
            f"[{self.slug}] get_sms() غير مطبق."
        )

    def cancel_order(self, provider_order_id: str) -> bool:
        """
        إلغاء طلب — يرجع True/False.
        """
        raise ProviderError(
            f"[{self.slug}] cancel_order() غير مطبق."
        )

    def refund_order(self, provider_order_id: str) -> bool:
        """
        استرجاع مالي للطلب — يرجع True/False.
        """
        raise ProviderError(
            f"[{self.slug}] refund_order() غير مطبق."
        )

    # ══════════════════════════════════════════════════════
    #  Helpers للـ Adapters
    # ══════════════════════════════════════════════════════
    def _http_get(self, path: str, params: dict = None,
                  headers: dict = None) -> dict:
        """GET مع retry + timeout"""
        url = f"{self.api_url}/{path.lstrip('/')}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", f"MTR-Numbers/{Config.VERSION}")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)

        last_err = None
        for attempt in range(self.retry):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
                    try:
                        return json.loads(body)
                    except json.JSONDecodeError:
                        return {"raw": body}
            except Exception as e:
                last_err = e
                wait = min(2 ** attempt, 10)
                time.sleep(wait)

        raise ProviderError(f"HTTP GET فشل: {last_err}")

    def _http_post(self, path: str, data: dict = None,
                   headers: dict = None, json_body: bool = True) -> dict:
        """POST مع retry + timeout"""
        url = f"{self.api_url}/{path.lstrip('/')}"

        if json_body:
            body = json.dumps(data or {}).encode("utf-8")
            content_type = "application/json"
        else:
            body = urllib.parse.urlencode(data or {}).encode("utf-8")
            content_type = "application/x-www-form-urlencoded"

        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", content_type)
        req.add_header("User-Agent", f"MTR-Numbers/{Config.VERSION}")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)

        last_err = None
        for attempt in range(self.retry):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    resp_body = resp.read().decode("utf-8", errors="replace")
                    try:
                        return json.loads(resp_body)
                    except json.JSONDecodeError:
                        return {"raw": resp_body}
            except Exception as e:
                last_err = e
                wait = min(2 ** attempt, 10)
                time.sleep(wait)

        raise ProviderError(f"HTTP POST فشل: {last_err}")


# ══════════════════════════════════════════════════════════════
#  GENERIC ADAPTER — للاختبار فقط
#  (لا يدّعي دعم أي مزود حقيقي)
# ══════════════════════════════════════════════════════════════
class GenericManualAdapter(ProviderBase):
    """
    Adapter للأرقام التي تُدار يدوياً (مخزون داخلي).
    يُستخدم لاختبار النظام بدون مزود خارجي.
    ⚠️ لا يتصل بأي API خارجي.
    """
    name = "Manual"
    slug = "manual"

    def get_balance(self) -> dict:
        # رصيد وهمي من جدول providers
        return {"balance": float(self.row.get("balance") or 0), "currency": "USD"}

    def get_countries(self) -> list[dict]:
        return []

    def get_services(self) -> list[dict]:
        return []

    def get_inventory(self, country: str, service: str) -> dict:
        return {"available": 0, "price": 0.0}

    def request_number(self, country: str, service: str,
                       idempotency_key: str) -> dict:
        # ⚠️ Manual Adapter لا يمكنه إصدار أرقام — يعتمد على المخزون الداخلي
        raise ProviderError("Manual Adapter لا يدعم request_number — استخدم المخزون الداخلي")


# ══════════════════════════════════════════════════════════════
#  ADAPTER REGISTRY
# ══════════════════════════════════════════════════════════════
class AdapterRegistry:
    """
    سجل Adapters — كل provider له adapter حسب slug.
    لإضافة مزود جديد: أنشئ class يورث ProviderBase وسجّله هنا.
    """
    _adapters: dict[str, type] = {
        "manual": GenericManualAdapter,
    }

    @classmethod
    def register(cls, slug: str, adapter_cls: type):
        if not issubclass(adapter_cls, ProviderBase):
            raise ValueError(f"{adapter_cls} يجب أن يورث ProviderBase")
        cls._adapters[slug] = adapter_cls
        log.info(f"[Adapter] Registered: {slug}")

    @classmethod
    def get(cls, slug: str) -> Optional[type]:
        return cls._adapters.get(slug)

    @classmethod
    def list_available(cls) -> list[str]:
        return list(cls._adapters.keys())

    @classmethod
    def create(cls, provider_row: dict) -> ProviderBase:
        slug = provider_row.get("adapter") or provider_row.get("slug") or "manual"
        adapter_cls = cls._adapters.get(slug)
        if not adapter_cls:
            raise ProviderError(f"Adapter '{slug}' غير مسجل. المتوفر: {cls.list_available()}")
        return adapter_cls(provider_row)


# ══════════════════════════════════════════════════════════════
#  ▓▓▓ نهاية الجزء 5 ▓▓▓
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  INVENTORY MANAGER
#  إدارة مخزون الأرقام + استيراد TXT/CSV
# ══════════════════════════════════════════════════════════════
class InventoryError(Exception):
    pass


class InventoryManager:
    """إدارة مخزون الأرقام — كل شي من لوحة التحكم"""

    def __init__(self, db: DB):
        self.db = db
        self._lock = db._lock

    # ══════════════════════════════════════════════════════
    #  QUERY
    # ══════════════════════════════════════════════════════
    def get(self, iid: int) -> Optional[dict]:
        with self._lock, self.db._conn() as c:
            r = c.execute("SELECT * FROM inventory WHERE id=?", (iid,)).fetchone()
            return dict(r) if r else None

    def list(self, status: str = None, country_id: int = None,
             service_id: int = None, provider_id: int = None,
             search: str = None, limit: int = 100, offset: int = 0) -> list[dict]:
        q = """SELECT i.*, c.name_ar AS country_name, c.flag AS country_flag,
                      c.dial_code AS country_dial,
                      s.name_ar AS service_name, s.color AS service_color,
                      p.name AS provider_name
               FROM inventory i
               LEFT JOIN countries c ON c.id = i.country_id
               LEFT JOIN services  s ON s.id = i.service_id
               LEFT JOIN providers p ON p.id = i.provider_id
               WHERE 1=1"""
        p = []
        if status:
            q += " AND i.status=?"; p.append(status)
        if country_id:
            q += " AND i.country_id=?"; p.append(country_id)
        if service_id:
            q += " AND i.service_id=?"; p.append(service_id)
        if provider_id:
            q += " AND i.provider_id=?"; p.append(provider_id)
        if search:
            q += " AND i.number LIKE ?"; p.append(f"%{search}%")
        q += " ORDER BY i.id DESC LIMIT ? OFFSET ?"
        p += [limit, offset]
        with self._lock, self.db._conn() as c:
            return [dict(r) for r in c.execute(q, p).fetchall()]

    def count(self, status: str = None, country_id: int = None,
              service_id: int = None) -> int:
        q = "SELECT COUNT(*) AS n FROM inventory WHERE 1=1"
        p = []
        if status:
            q += " AND status=?"; p.append(status)
        if country_id:
            q += " AND country_id=?"; p.append(country_id)
        if service_id:
            q += " AND service_id=?"; p.append(service_id)
        with self._lock, self.db._conn() as c:
            return c.execute(q, p).fetchone()["n"]

    def available_count(self, country_id: int, service_id: int) -> int:
        """عدد الأرقام المتاحة لدولة+خدمة"""
        with self._lock, self.db._conn() as c:
            return c.execute("""SELECT COUNT(*) AS n FROM inventory
                                WHERE country_id=? AND service_id=? AND status='available'""",
                             (country_id, service_id)).fetchone()["n"]

    def stats(self) -> dict:
        with self._lock, self.db._conn() as c:
            total = c.execute("SELECT COUNT(*) AS n FROM inventory").fetchone()["n"]
            avail = c.execute("SELECT COUNT(*) AS n FROM inventory WHERE status='available'").fetchone()["n"]
            reserved = c.execute("SELECT COUNT(*) AS n FROM inventory WHERE status='reserved'").fetchone()["n"]
            sold = c.execute("SELECT COUNT(*) AS n FROM inventory WHERE status='sold'").fetchone()["n"]
            return {"total": total, "available": avail,
                    "reserved": reserved, "sold": sold}

    # ══════════════════════════════════════════════════════
    #  ADD / UPDATE
    # ══════════════════════════════════════════════════════
    def add_one(self, number: str, country_id: int, service_id: int,
                provider_id: int = None, cost: float = 0.0) -> Optional[int]:
        """إضافة رقم واحد"""
        number = normalize_phone(number)
        if not validate_phone(number):
            raise InventoryError(f"رقم غير صالح: {number}")

        now = now_iso()
        with self._lock, self.db._conn() as c:
            try:
                cur = c.execute("""INSERT INTO inventory(number, country_id, service_id,
                                    provider_id, cost, status, imported_at, updated_at)
                                   VALUES(?,?,?,?,?,'available',?,?)""",
                                (number, country_id, service_id, provider_id,
                                 cost, now, now))
                return cur.lastrowid
            except sqlite3.IntegrityError:
                return None  # duplicate

    def add_bulk(self, numbers: list[str], country_id: int, service_id: int,
                 provider_id: int = None, cost: float = 0.0) -> dict:
        """
        إضافة مجموعة أرقام دفعة واحدة.
        يرجع: {imported, duplicates, invalid, total}
        """
        result = {"imported": 0, "duplicates": 0, "invalid": 0, "total": len(numbers)}
        now = now_iso()

        with self._lock, self.db._conn() as c:
            for num in numbers:
                clean = normalize_phone(num)
                if not validate_phone(clean):
                    result["invalid"] += 1
                    continue
                try:
                    c.execute("""INSERT INTO inventory(number, country_id, service_id,
                                    provider_id, cost, status, imported_at, updated_at)
                                 VALUES(?,?,?,?,?,'available',?,?)""",
                              (clean, country_id, service_id, provider_id, cost, now, now))
                    result["imported"] += 1
                except sqlite3.IntegrityError:
                    result["duplicates"] += 1

        return result

    def update(self, iid: int, **fields) -> bool:
        allowed = {"number", "country_id", "service_id", "provider_id",
                   "cost", "status", "order_id", "reserved_until"}
        u = {k: v for k, v in fields.items() if k in allowed}
        if not u:
            return False
        u["updated_at"] = now_iso()
        cols = ", ".join(f"{k}=?" for k in u)
        vals = list(u.values()) + [iid]
        with self._lock, self.db._conn() as c:
            return c.execute(f"UPDATE inventory SET {cols} WHERE id=?", vals).rowcount > 0

    def set_status(self, iid: int, status: str) -> bool:
        return self.update(iid, status=status)

    # ══════════════════════════════════════════════════════
    #  DELETE
    # ══════════════════════════════════════════════════════
    def delete(self, iid: int) -> bool:
        with self._lock, self.db._conn() as c:
            return c.execute("DELETE FROM inventory WHERE id=?", (iid,)).rowcount > 0

    def delete_bulk(self, ids: list[int]) -> int:
        if not ids:
            return 0
        placeholders = ",".join("?" * len(ids))
        with self._lock, self.db._conn() as c:
            cur = c.execute(f"DELETE FROM inventory WHERE id IN ({placeholders})", ids)
            return cur.rowcount

    def delete_by_filter(self, status: str = None, country_id: int = None,
                         service_id: int = None, provider_id: int = None) -> int:
        q = "DELETE FROM inventory WHERE 1=1"
        p = []
        if status:
            q += " AND status=?"; p.append(status)
        if country_id:
            q += " AND country_id=?"; p.append(country_id)
        if service_id:
            q += " AND service_id=?"; p.append(service_id)
        if provider_id:
            q += " AND provider_id=?"; p.append(provider_id)
        with self._lock, self.db._conn() as c:
            return c.execute(q, p).rowcount

    def bulk_disable(self, ids: list[int]) -> int:
        if not ids:
            return 0
        placeholders = ",".join("?" * len(ids))
        now = now_iso()
        with self._lock, self.db._conn() as c:
            cur = c.execute(f"""UPDATE inventory SET status='disabled', updated_at=?
                                WHERE id IN ({placeholders})""",
                            [now] + ids)
            return cur.rowcount

    # ══════════════════════════════════════════════════════
    #  RESERVE / RELEASE (للطلبات)
    # ══════════════════════════════════════════════════════
    def reserve(self, country_id: int, service_id: int,
                order_id: int, timeout_min: int = None) -> Optional[dict]:
        """
        يحجز رقم متاح للطلب — ذرّي.
        يرجع dict الرقم أو None إذا ما فيه متاح.
        """
        timeout = timeout_min or Config.ORDER_TIMEOUT_MIN
        until = (datetime.now(timezone.utc) + timedelta(minutes=timeout)).isoformat()
        now = now_iso()

        with self._lock, self.db._conn() as c:
            try:
                c.execute("BEGIN IMMEDIATE")
                row = c.execute("""SELECT * FROM inventory
                                   WHERE country_id=? AND service_id=?
                                     AND status='available'
                                   ORDER BY id ASC LIMIT 1""",
                                (country_id, service_id)).fetchone()

                if not row:
                    c.execute("ROLLBACK")
                    return None

                c.execute("""UPDATE inventory SET status='reserved', order_id=?,
                                reserved_until=?, updated_at=?
                             WHERE id=?""",
                          (order_id, until, now, row["id"]))

                c.execute("COMMIT")

                result = dict(row)
                result["status"] = "reserved"
                result["order_id"] = order_id
                result["reserved_until"] = until
                return result
            except Exception as e:
                c.execute("ROLLBACK")
                log.error(f"[Inventory] reserve error: {e}")
                return None

    def mark_sold(self, iid: int) -> bool:
        return self.set_status(iid, "sold")

    def release(self, iid: int) -> bool:
        """يفك الحجز"""
        with self._lock, self.db._conn() as c:
            return c.execute("""UPDATE inventory
                                SET status='available', order_id=NULL,
                                    reserved_until=NULL, updated_at=?
                                WHERE id=?""",
                             (now_iso(), iid)).rowcount > 0

    def cleanup_expired_reservations(self) -> int:
        """يحرر الحجوزات المنتهية"""
        now = now_iso()
        with self._lock, self.db._conn() as c:
            cur = c.execute("""UPDATE inventory
                                SET status='available', order_id=NULL,
                                    reserved_until=NULL, updated_at=?
                                WHERE status='reserved' AND reserved_until < ?""",
                            (now, now))
            return cur.rowcount

    # ══════════════════════════════════════════════════════
    #  IMPORT — TXT / CSV
    # ══════════════════════════════════════════════════════
    @staticmethod
    def parse_txt(content: str) -> list[str]:
        """
        يحلل ملف TXT.
        كل سطر فيه رقم، أو "number,country,service"
        """
        numbers = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # أول جزء من السطر
            num = line.split(",")[0].strip()
            numbers.append(num)
        return numbers

    @staticmethod
    def parse_csv(content: str, number_col: str = "number") -> list[str]:
        """
        يحلل CSV — يبحث عن عمود number.
        """
        numbers = []
        try:
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                if number_col in row and row[number_col]:
                    numbers.append(row[number_col].strip())
        except Exception:
            # لو ما كان فيه header، اعتبر كل سطر
            reader = csv.reader(io.StringIO(content))
            for row in reader:
                if row:
                    numbers.append(row[0].strip())
        return numbers

    def import_from_text(self, content: str, country_id: int,
                         service_id: int, provider_id: int = None,
                         cost: float = 0.0, fmt: str = "auto") -> dict:
        """
        يستورد من نص مباشرة (TXT أو CSV).
        """
        if fmt == "txt":
            numbers = self.parse_txt(content)
        elif fmt == "csv":
            numbers = self.parse_csv(content)
        else:
            # auto
            if content.count(",") > content.count("\n") * 0.5:
                numbers = self.parse_csv(content)
            else:
                numbers = self.parse_txt(content)

        return self.add_bulk(numbers, country_id, service_id, provider_id, cost)

    # ══════════════════════════════════════════════════════
    #  EXPORT
    # ══════════════════════════════════════════════════════
    def export_txt(self, status: str = None, country_id: int = None,
                   service_id: int = None) -> str:
        """يصدّر الأرقام كنص"""
        items = self.list(status=status, country_id=country_id,
                          service_id=service_id, limit=100000)
        lines = []
        for it in items:
            lines.append(it["number"])
        return "\n".join(lines)

    def export_csv(self, status: str = None, country_id: int = None,
                   service_id: int = None) -> str:
        """يصدّر CSV كامل"""
        items = self.list(status=status, country_id=country_id,
                          service_id=service_id, limit=100000)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["id", "number", "country", "service", "provider",
                    "cost", "status", "imported_at"])
        for it in items:
            w.writerow([
                it["id"], it["number"],
                it.get("country_name", ""), it.get("service_name", ""),
                it.get("provider_name", ""), it["cost"],
                it["status"], it["imported_at"],
            ])
        return buf.getvalue()

    # ══════════════════════════════════════════════════════
    #  BULK ASSIGN
    # ══════════════════════════════════════════════════════
    def bulk_assign_provider(self, ids: list[int], provider_id: int) -> int:
        if not ids:
            return 0
        placeholders = ",".join("?" * len(ids))
        now = now_iso()
        with self._lock, self.db._conn() as c:
            cur = c.execute(f"""UPDATE inventory SET provider_id=?, updated_at=?
                                WHERE id IN ({placeholders})""",
                            [provider_id, now] + ids)
            return cur.rowcount

    def bulk_assign_country(self, ids: list[int], country_id: int) -> int:
        if not ids:
            return 0
        placeholders = ",".join("?" * len(ids))
        now = now_iso()
        with self._lock, self.db._conn() as c:
            cur = c.execute(f"""UPDATE inventory SET country_id=?, updated_at=?
                                WHERE id IN ({placeholders})""",
                            [country_id, now] + ids)
            return cur.rowcount

    def bulk_assign_service(self, ids: list[int], service_id: int) -> int:
        if not ids:
            return 0
        placeholders = ",".join("?" * len(ids))
        now = now_iso()
        with self._lock, self.db._conn() as c:
            cur = c.execute(f"""UPDATE inventory SET service_id=?, updated_at=?
                                WHERE id IN ({placeholders})""",
                            [service_id, now] + ids)
            return cur.rowcount

    # ══════════════════════════════════════════════════════
    #  AGGREGATION (للداشبورد)
    # ══════════════════════════════════════════════════════
    def by_country_service(self) -> list[dict]:
        """يجمّع: كم رقم متاح لكل دولة+خدمة"""
        with self._lock, self.db._conn() as c:
            rows = c.execute("""
                SELECT i.country_id, i.service_id,
                       c.name_ar AS country, c.flag,
                       s.name_ar AS service, s.color,
                       COUNT(*) AS total,
                       SUM(CASE WHEN i.status='available' THEN 1 ELSE 0 END) AS available
                FROM inventory i
                LEFT JOIN countries c ON c.id = i.country_id
                LEFT JOIN services  s ON s.id = i.service_id
                WHERE i.status = 'available'
                GROUP BY i.country_id, i.service_id
                ORDER BY available DESC
            """).fetchall()
            return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════
#  ▓▓▓ نهاية الجزء 6 ▓▓▓
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  PRICING ENGINE
#  يحسب سعر البيع بناءً على: cost + profit - discount
# ══════════════════════════════════════════════════════════════
class PricingError(Exception):
    pass


class PricingEngine:
    """
    محرك التسعير — يدعم:
    - Fixed Profit
    - Percentage Profit
    - Country/Service/Provider price
    - Min price
    """

    def __init__(self, db: DB):
        self.db = db

    # ══════════════════════════════════════════════════════
    #  GET PRICE
    # ══════════════════════════════════════════════════════
    def get_price_row(self, country_id: int, service_id: int,
                      provider_id: int = None) -> Optional[dict]:
        """يجيب صف التسعير الأخصّ"""
        with self.db._lock, self.db._conn() as c:
            # 1) جرّب (country + service + provider) محدد
            if provider_id:
                r = c.execute("""SELECT * FROM prices
                                 WHERE country_id=? AND service_id=? AND provider_id=?
                                   AND status='active'""",
                              (country_id, service_id, provider_id)).fetchone()
                if r:
                    return dict(r)

            # 2) جرّب (country + service) عام
            r = c.execute("""SELECT * FROM prices
                             WHERE country_id=? AND service_id=?
                               AND provider_id IS NULL
                               AND status='active'""",
                          (country_id, service_id)).fetchone()
            if r:
                return dict(r)

            # 3) جرّب (service) عام
            r = c.execute("""SELECT * FROM prices
                             WHERE service_id=? AND country_id IS NULL
                               AND provider_id IS NULL
                               AND status='active'""",
                          (service_id,)).fetchone()
            if r:
                return dict(r)

            return None

    def compute(self, country_id: int, service_id: int,
                provider_id: int = None, provider_cost: float = None,
                promo_discount: float = 0.0) -> dict:
        """
        يحسب السعر النهائي.
        يرجع:
          {
            cost, profit_fixed, profit_percent, profit,
            discount, sell_price, min_price, final_price
          }
        """
        row = self.get_price_row(country_id, service_id, provider_id)

        if not row:
            # لا يوجد تسعير محدد — استخدم cost كسعر
            cost = float(provider_cost or 0.0)
            sell = cost
            return {
                "cost": cost,
                "profit_fixed": 0.0,
                "profit_percent": 0.0,
                "profit": 0.0,
                "discount": 0.0,
                "sell_price": sell,
                "min_price": 0.0,
                "final_price": sell,
                "has_rule": False,
            }

        cost = float(provider_cost if provider_cost is not None else row["cost"])
        profit_fixed = float(row.get("profit_fixed") or 0.0)
        profit_percent = float(row.get("profit_percent") or 0.0)
        min_price = float(row.get("min_price") or 0.0)

        profit = profit_fixed + (cost * profit_percent / 100.0)
        sell_price = cost + profit
        final_price = max(0.0, sell_price - promo_discount)

        # منع أقل من الحد الأدنى
        if min_price > 0 and final_price < min_price:
            final_price = min_price

        # منع صفر أو سالب
        if final_price <= 0:
            final_price = cost

        return {
            "cost": round(cost, 4),
            "profit_fixed": round(profit_fixed, 4),
            "profit_percent": round(profit_percent, 2),
            "profit": round(profit, 4),
            "discount": round(promo_discount, 4),
            "sell_price": round(sell_price, 4),
            "min_price": round(min_price, 4),
            "final_price": round(final_price, 4),
            "has_rule": True,
        }

    # ══════════════════════════════════════════════════════
    #  CRUD
    # ══════════════════════════════════════════════════════
    def list_all(self, country_id: int = None,
                 service_id: int = None) -> list[dict]:
        q = """SELECT pr.*, c.name_ar AS country_name, c.flag,
                      s.name_ar AS service_name, s.color,
                      p.name AS provider_name
               FROM prices pr
               LEFT JOIN countries c ON c.id = pr.country_id
               LEFT JOIN services  s ON s.id = pr.service_id
               LEFT JOIN providers p ON p.id = pr.provider_id
               WHERE 1=1"""
        params = []
        if country_id:
            q += " AND pr.country_id=?"; params.append(country_id)
        if service_id:
            q += " AND pr.service_id=?"; params.append(service_id)
        q += " ORDER BY pr.id DESC"
        with self.db._lock, self.db._conn() as c:
            return [dict(r) for r in c.execute(q, params).fetchall()]

    def get(self, pid: int) -> Optional[dict]:
        with self.db._lock, self.db._conn() as c:
            r = c.execute("SELECT * FROM prices WHERE id=?", (pid,)).fetchone()
            return dict(r) if r else None

    def upsert(self, country_id: int, service_id: int,
               provider_id: int = None, cost: float = 0.0,
               profit_fixed: float = 0.0, profit_percent: float = 0.0,
               min_price: float = 0.0) -> int:
        """إضافة/تحديث تسعير"""
        now = now_iso()

        with self.db._lock, self.db._conn() as c:
            # ابحث عن صف مطابق
            if provider_id:
                r = c.execute("""SELECT id FROM prices
                                 WHERE country_id=? AND service_id=? AND provider_id=?""",
                              (country_id, service_id, provider_id)).fetchone()
            else:
                r = c.execute("""SELECT id FROM prices
                                 WHERE country_id=? AND service_id=?
                                   AND provider_id IS NULL""",
                              (country_id, service_id)).fetchone()

            if r:
                c.execute("""UPDATE prices SET cost=?, profit_fixed=?, profit_percent=?,
                                min_price=?, updated_at=?
                             WHERE id=?""",
                          (cost, profit_fixed, profit_percent, min_price, now, r["id"]))
                return r["id"]

            cur = c.execute("""INSERT INTO prices(country_id, service_id, provider_id,
                                    cost, profit_fixed, profit_percent, min_price,
                                    status, created_at, updated_at)
                               VALUES(?,?,?,?,?,?,?,'active',?,?)""",
                            (country_id, service_id, provider_id, cost,
                             profit_fixed, profit_percent, min_price, now, now))
            return cur.lastrowid

    def update(self, pid: int, **fields) -> bool:
        allowed = {"cost", "profit_fixed", "profit_percent",
                   "min_price", "sell_price", "status"}
        u = {k: v for k, v in fields.items() if k in allowed}
        if not u: return False
        u["updated_at"] = now_iso()
        cols = ", ".join(f"{k}=?" for k in u)
        vals = list(u.values()) + [pid]
        with self.db._lock, self.db._conn() as c:
            return c.execute(f"UPDATE prices SET {cols} WHERE id=?", vals).rowcount > 0

    def delete(self, pid: int) -> bool:
        with self.db._lock, self.db._conn() as c:
            return c.execute("DELETE FROM prices WHERE id=?", (pid,)).rowcount > 0


# ══════════════════════════════════════════════════════════════
#  ORDERS ENGINE
#  طلبات الشراء + الحجز + OTP
# ══════════════════════════════════════════════════════════════
class OrderStatus:
    PENDING   = "pending"      # تم الحجز، في انتظار OTP
    WAITING   = "waiting"      # الرقم جاهز
    COMPLETED = "completed"    # OTP وصل
    FAILED    = "failed"       # فشل
    CANCELLED = "cancelled"    # ألغى المستخدم
    EXPIRED   = "expired"      # انتهى الوقت
    REFUNDED  = "refunded"     # استرجع


class OrderError(Exception):
    pass


class OrdersEngine:
    """إدارة الطلبات — ذرّي + idempotency"""

    def __init__(self, db: DB, wallet: Wallet, inventory: InventoryManager,
                 pricing: PricingEngine):
        self.db = db
        self.wallet = wallet
        self.inventory = inventory
        self.pricing = pricing
        self._lock = db._lock

    # ══════════════════════════════════════════════════════
    #  CREATE
    # ══════════════════════════════════════════════════════
    def create(self, user_id: int, country_id: int, service_id: int,
               idempotency_key: str = None) -> dict:
        """
        ينشئ طلب جديد:
          1. idempotency check
          2. حساب السعر
          3. خصم الرصيد (atomic)
          4. حجز الرقم (atomic)
          5. إنشاء order
        """
        # ─── 1. idempotency
        if idempotency_key:
            with self._lock, self.db._conn() as c:
                r = c.execute("SELECT * FROM orders WHERE idempotency_key=?",
                              (idempotency_key,)).fetchone()
                if r:
                    return {"order": dict(r), "idempotent": True}

        # ─── 2. حساب السعر
        price_info = self.pricing.compute(country_id, service_id)
        sell_price = price_info["final_price"]
        cost = price_info["cost"]
        profit = sell_price - cost

        if sell_price <= 0:
            raise OrderError("سعر البيع غير صالح")

        if sell_price > Config.MAX_ORDER_AMOUNT:
            raise OrderError(f"السعر يتجاوز الحد {money(Config.MAX_ORDER_AMOUNT)}")

        # ─── 3. تأكد من توفر رقم
        avail = self.inventory.available_count(country_id, service_id)
        if avail <= 0:
            raise OrderError("لا يوجد أرقام متاحة لهذه الدولة والخدمة")

        # ─── 4. إنشاء الطلب أولاً (بحالة pending)
        order_code = "ORD" + uuid.uuid4().hex[:10].upper()
        now = now_iso()
        expires = (datetime.now(timezone.utc) +
                   timedelta(minutes=Config.ORDER_TIMEOUT_MIN)).isoformat()

        with self._lock, self.db._conn() as c:
            cur = c.execute("""INSERT INTO orders(order_code, user_id, country_id,
                                    service_id, cost, sell_price, profit, status,
                                    idempotency_key, created_at, updated_at, expires_at)
                               VALUES(?,?,?,?,?,?,?,'pending',?,?,?,?)""",
                            (order_code, user_id, country_id, service_id,
                             cost, sell_price, profit, idempotency_key,
                             now, now, expires))
            order_id = cur.lastrowid

        # ─── 5. خصم الرصيد (atomic)
        try:
            tx = self.wallet.purchase(user_id, sell_price,
                                       reference=order_code,
                                       note=f"شراء {order_code}")
        except WalletError as e:
            # فشل — احذف الطلب
            with self._lock, self.db._conn() as c:
                c.execute("DELETE FROM orders WHERE id=?", (order_id,))
            raise OrderError(f"فشل الخصم: {e}")

        # ─── 6. حجز رقم
        reserved = self.inventory.reserve(country_id, service_id, order_id)
        if not reserved:
            # فشل — استرجع الرصيد واحذف الطلب
            try:
                self.wallet.refund(user_id, sell_price, reference=order_code,
                                    note=f"استرجاع فشل شراء {order_code}")
            except WalletError:
                pass
            with self._lock, self.db._conn() as c:
                c.execute("DELETE FROM orders WHERE id=?", (order_id,))
            raise OrderError("لا يوجد أرقام متاحة — تم استرجاع المبلغ")

        # ─── 7. تحديث الطلب بالرقم
        with self._lock, self.db._conn() as c:
            c.execute("""UPDATE orders SET inventory_id=?, number=?, status='waiting',
                            updated_at=? WHERE id=?""",
                      (reserved["id"], reserved["number"], now_iso(), order_id))

        # ─── 8. تسجيل الحدث
        self._log_event(order_id, "created",
                        f"تم إنشاء الطلب — رقم {reserved['number']}")

        return self.get(order_id)

    # ══════════════════════════════════════════════════════
    #  UPDATE OTP
    # ══════════════════════════════════════════════════════
    def set_otp(self, order_id: int, otp_code: str,
                otp_text: str = "") -> bool:
        """يسجل وصول OTP (من المزود فقط)"""
        now = now_iso()
        with self._lock, self.db._conn() as c:
            cur = c.execute("""UPDATE orders SET otp_code=?, otp_text=?,
                                status='completed', completed_at=?, updated_at=?
                               WHERE id=?""",
                            (otp_code, otp_text, now, now, order_id))
            if cur.rowcount > 0:
                # علامة الرقم كمباع
                r = c.execute("SELECT inventory_id FROM orders WHERE id=?",
                              (order_id,)).fetchone()
                if r and r["inventory_id"]:
                    c.execute("UPDATE inventory SET status='sold', updated_at=? WHERE id=?",
                              (now, r["inventory_id"]))
            return cur.rowcount > 0

    def add_event(self, order_id: int, event_type: str, message: str = "") -> None:
        self._log_event(order_id, event_type, message)

    def _log_event(self, order_id: int, event_type: str, message: str) -> None:
        now = now_iso()
        with self._lock, self.db._conn() as c:
            c.execute("""INSERT INTO order_events(order_id, event_type, message, created_at)
                         VALUES(?,?,?,?)""",
                      (order_id, event_type, message, now))

    # ══════════════════════════════════════════════════════
    #  CANCEL / REFUND
    # ══════════════════════════════════════════════════════
    def cancel(self, order_id: int, by_user: bool = False,
               reason: str = "") -> dict:
        """
        إلغاء الطلب:
          1. تحقق من الحالة
          2. حرر الرقم
          3. استرجع المبلغ
          4. علّم الطلب cancelled
        """
        with self._lock, self.db._conn() as c:
            r = c.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
            if not r:
                raise OrderError("الطلب غير موجود")
            order = dict(r)

        if order["status"] in (OrderStatus.COMPLETED, OrderStatus.CANCELLED,
                                OrderStatus.REFUNDED):
            raise OrderError(f"لا يمكن إلغاء طلب بحالة {order['status']}")

        # حرر الرقم
        if order.get("inventory_id"):
            self.inventory.release(order["inventory_id"])

        # استرجع المبلغ
        refund_tx = None
        try:
            refund_tx = self.wallet.refund(
                order["user_id"], order["sell_price"],
                reference=order["order_code"],
                note=f"استرجاع {order['order_code']} — {reason or 'إلغاء'}"
            )
        except WalletError as e:
            log.error(f"[Orders] refund failed: {e}")

        now = now_iso()
        new_status = OrderStatus.CANCELLED if by_user else OrderStatus.REFUNDED
        with self._lock, self.db._conn() as c:
            c.execute("""UPDATE orders SET status=?, updated_at=? WHERE id=?""",
                      (new_status, now, order_id))

        self._log_event(order_id, "cancelled",
                        f"أُلغي — {reason or 'بدون سبب'} (تم الاسترجاع)")

        return {"ok": True, "status": new_status, "refund": refund_tx}

    # ══════════════════════════════════════════════════════
    #  QUERY
    # ══════════════════════════════════════════════════════
    def get(self, order_id: int) -> Optional[dict]:
        with self._lock, self.db._conn() as c:
            r = c.execute("""SELECT o.*, c.name_ar AS country_name, c.flag,
                                    s.name_ar AS service_name, s.color
                             FROM orders o
                             LEFT JOIN countries c ON c.id=o.country_id
                             LEFT JOIN services  s ON s.id=o.service_id
                             WHERE o.id=?""", (order_id,)).fetchone()
            return dict(r) if r else None

    def get_by_code(self, code: str) -> Optional[dict]:
        with self._lock, self.db._conn() as c:
            r = c.execute("SELECT * FROM orders WHERE order_code=?", (code,)).fetchone()
            return dict(r) if r else None

    def get_user_orders(self, user_id: int, limit: int = 20,
                        offset: int = 0, status: str = None) -> list[dict]:
        q = """SELECT o.*, c.name_ar AS country_name, c.flag,
                      s.name_ar AS service_name
               FROM orders o
               LEFT JOIN countries c ON c.id=o.country_id
               LEFT JOIN services  s ON s.id=o.service_id
               WHERE o.user_id=?"""
        p = [user_id]
        if status:
            q += " AND o.status=?"; p.append(status)
        q += " ORDER BY o.id DESC LIMIT ? OFFSET ?"
        p += [limit, offset]
        with self._lock, self.db._conn() as c:
            return [dict(r) for r in c.execute(q, p).fetchall()]

    def list_all(self, status: str = None, user_id: int = None,
                 country_id: int = None, service_id: int = None,
                 limit: int = 100, offset: int = 0) -> list[dict]:
        q = """SELECT o.*, u.username, u.first_name,
                      c.name_ar AS country_name, c.flag,
                      s.name_ar AS service_name
               FROM orders o
               LEFT JOIN users u ON u.id=o.user_id
               LEFT JOIN countries c ON c.id=o.country_id
               LEFT JOIN services  s ON s.id=o.service_id
               WHERE 1=1"""
        p = []
        if status:
            q += " AND o.status=?"; p.append(status)
        if user_id:
            q += " AND o.user_id=?"; p.append(user_id)
        if country_id:
            q += " AND o.country_id=?"; p.append(country_id)
        if service_id:
            q += " AND o.service_id=?"; p.append(service_id)
        q += " ORDER BY o.id DESC LIMIT ? OFFSET ?"
        p += [limit, offset]
        with self._lock, self.db._conn() as c:
            return [dict(r) for r in c.execute(q, p).fetchall()]

    def events(self, order_id: int) -> list[dict]:
        with self._lock, self.db._conn() as c:
            rows = c.execute("""SELECT * FROM order_events WHERE order_id=?
                                ORDER BY id ASC""", (order_id,)).fetchall()
            return [dict(r) for r in rows]

    def stats(self) -> dict:
        with self._lock, self.db._conn() as c:
            def q1(sql, p=()):
                return c.execute(sql, p).fetchone()["n"]
            return {
                "total":     q1("SELECT COUNT(*) AS n FROM orders"),
                "pending":   q1("SELECT COUNT(*) AS n FROM orders WHERE status='pending'"),
                "waiting":   q1("SELECT COUNT(*) AS n FROM orders WHERE status='waiting'"),
                "completed": q1("SELECT COUNT(*) AS n FROM orders WHERE status='completed'"),
                "failed":    q1("SELECT COUNT(*) AS n FROM orders WHERE status='failed'"),
                "cancelled": q1("SELECT COUNT(*) AS n FROM orders WHERE status='cancelled'"),
            }

    def cleanup_expired(self) -> int:
        """يلغي الطلبات المنتهية"""
        now = now_iso()
        with self._lock, self.db._conn() as c:
            rows = c.execute("""SELECT id FROM orders
                                WHERE status IN ('pending','waiting')
                                  AND expires_at < ?""", (now,)).fetchall()
            ids = [r["id"] for r in rows]

        count = 0
        for oid in ids:
            try:
                self.cancel(oid, by_user=False, reason="انتهت المدة")
                count += 1
            except Exception as e:
                log.error(f"[Orders] cleanup {oid}: {e}")
        return count


# ══════════════════════════════════════════════════════════════
#  ▓▓▓ نهاية الجزء 7 ▓▓▓
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  RBAC — Roles & Permissions
# ══════════════════════════════════════════════════════════════
class RBAC:
    """نظام الصلاحيات — يعتمد على permissions مو role فقط"""

    def __init__(self, db: DB):
        self.db = db
        self._cache = {}
        self._lock = threading.Lock()

    # ══════════════════════════════════════════════════════
    #  ROLES
    # ══════════════════════════════════════════════════════
    def list_roles(self) -> list[dict]:
        with self.db._lock, self.db._conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM roles ORDER BY id").fetchall()]

    def get_role(self, role_id: int) -> Optional[dict]:
        with self.db._lock, self.db._conn() as c:
            r = c.execute("SELECT * FROM roles WHERE id=?", (role_id,)).fetchone()
            return dict(r) if r else None

    def get_role_by_slug(self, slug: str) -> Optional[dict]:
        with self.db._lock, self.db._conn() as c:
            r = c.execute("SELECT * FROM roles WHERE slug=?", (slug,)).fetchone()
            return dict(r) if r else None

    def add_role(self, slug: str, name_ar: str, name_en: str = "") -> Optional[int]:
        now = now_iso()
        slug = re.sub(r"[^a-z0-9_]", "_", slug.lower().strip())[:40]
        with self.db._lock, self.db._conn() as c:
            try:
                cur = c.execute("""INSERT INTO roles(slug, name_ar, name_en, created_at)
                                   VALUES(?,?,?,?)""",
                                (slug, name_ar.strip(), name_en.strip(), now))
                return cur.lastrowid
            except sqlite3.IntegrityError:
                return None

    def delete_role(self, role_id: int) -> bool:
        with self.db._lock, self.db._conn() as c:
            r = c.execute("SELECT is_system FROM roles WHERE id=?", (role_id,)).fetchone()
            if not r or r["is_system"]:
                return False
            return c.execute("DELETE FROM roles WHERE id=?", (role_id,)).rowcount > 0

    # ══════════════════════════════════════════════════════
    #  PERMISSIONS
    # ══════════════════════════════════════════════════════
    def list_permissions(self, category: str = None) -> list[dict]:
        q = "SELECT * FROM permissions"
        p = []
        if category:
            q += " WHERE category=?"; p.append(category)
        q += " ORDER BY category, slug"
        with self.db._lock, self.db._conn() as c:
            return [dict(r) for r in c.execute(q, p).fetchall()]

    def get_permissions_for_role(self, role_id: int) -> list[str]:
        """يرجع قائمة slugs الصلاحيات للدور"""
        cache_key = f"role_perms:{role_id}"
        with self._lock:
            if cache_key in self._cache:
                return self._cache[cache_key]

        with self.db._lock, self.db._conn() as c:
            rows = c.execute("""SELECT p.slug FROM permissions p
                                JOIN role_permissions rp ON rp.permission_id=p.id
                                WHERE rp.role_id=?""", (role_id,)).fetchall()
            slugs = [r["slug"] for r in rows]

        with self._lock:
            self._cache[cache_key] = slugs
        return slugs

    def grant_permission(self, role_id: int, perm_slug: str) -> bool:
        with self.db._lock, self.db._conn() as c:
            r = c.execute("SELECT id FROM permissions WHERE slug=?", (perm_slug,)).fetchone()
            if not r:
                return False
            try:
                c.execute("""INSERT OR IGNORE INTO role_permissions(role_id, permission_id)
                             VALUES(?,?)""", (role_id, r["id"]))
                self._invalidate_cache(role_id)
                return True
            except Exception:
                return False

    def revoke_permission(self, role_id: int, perm_slug: str) -> bool:
        with self.db._lock, self.db._conn() as c:
            r = c.execute("SELECT id FROM permissions WHERE slug=?", (perm_slug,)).fetchone()
            if not r:
                return False
            cur = c.execute("""DELETE FROM role_permissions
                               WHERE role_id=? AND permission_id=?""",
                            (role_id, r["id"]))
            self._invalidate_cache(role_id)
            return cur.rowcount > 0

    def _invalidate_cache(self, role_id: int = None) -> None:
        with self._lock:
            if role_id:
                self._cache.pop(f"role_perms:{role_id}", None)
            else:
                self._cache.clear()

    # ══════════════════════════════════════════════════════
    #  CHECK — التحقق
    # ══════════════════════════════════════════════════════
    def has_permission(self, user_id: int, perm_slug: str) -> bool:
        """هل للمستخدم صلاحية معينة؟"""
        u = self.db.user_get(user_id)
        if not u:
            return False
        if u.get("status") == "blocked":
            return False

        # Owner له كل الصلاحيات
        if u.get("tg_id") == Config.OWNER_ID:
            return True

        role_id = u.get("role_id")
        if not role_id:
            return False

        perms = self.get_permissions_for_role(role_id)
        return perm_slug in perms

    def require(self, user_id: int, perm_slug: str) -> None:
        """يرفع خطأ إذا ما عنده صلاحية"""
        if not self.has_permission(user_id, perm_slug):
            raise PermissionError(f"صلاحية مرفوضة: {perm_slug}")

    def is_admin(self, user_id: int) -> bool:
        """هل المستخدم إداري (أي دور غير عادي)"""
        u = self.db.user_get(user_id)
        if not u:
            return False
        if u.get("tg_id") == Config.OWNER_ID:
            return True
        return bool(u.get("role_id"))

    def is_owner(self, user_id: int) -> bool:
        u = self.db.user_get(user_id)
        return bool(u and u.get("tg_id") == Config.OWNER_ID)


# ══════════════════════════════════════════════════════════════
#  AUDIT LOGS
# ══════════════════════════════════════════════════════════════
class Audit:
    """سجل التدقيق — من فعل ماذا ومتى"""

    # حقول لا تُسجّل أبداً
    FORBIDDEN_KEYS = {
        "api_key", "api_secret", "password", "token",
        "otp", "otp_code", "secret", "access_token",
    }

    def __init__(self, db: DB):
        self.db = db

    def _clean_data(self, data: dict) -> dict:
        """يحذف الحقول الحساسة"""
        if not isinstance(data, dict):
            return data
        out = {}
        for k, v in data.items():
            if k.lower() in self.FORBIDDEN_KEYS:
                out[k] = "***REDACTED***"
            elif isinstance(v, dict):
                out[k] = self._clean_data(v)
            else:
                out[k] = v
        return out

    def log(self, actor_id: int, actor_name: str, action: str,
            target_type: str = "", target_id: int = None,
            before: dict = None, after: dict = None,
            ip: str = "", user_agent: str = "") -> int:
        """يسجل عملية"""
        now = now_iso()

        before_json = json.dumps(self._clean_data(before) if before else {}, ensure_ascii=False)
        after_json = json.dumps(self._clean_data(after) if after else {}, ensure_ascii=False)

        with self.db._lock, self.db._conn() as c:
            cur = c.execute("""INSERT INTO audit_logs(actor_id, actor_name, action,
                                    target_type, target_id, before_data, after_data,
                                    ip, user_agent, created_at)
                               VALUES(?,?,?,?,?,?,?,?,?,?)""",
                            (actor_id, actor_name or "", action,
                             target_type or "", target_id,
                             before_json, after_json,
                             ip or "", user_agent or "", now))
            return cur.lastrowid

    def list(self, actor_id: int = None, action: str = None,
             target_type: str = None, limit: int = 100,
             offset: int = 0) -> list[dict]:
        q = "SELECT * FROM audit_logs WHERE 1=1"
        p = []
        if actor_id:
            q += " AND actor_id=?"; p.append(actor_id)
        if action:
            q += " AND action=?"; p.append(action)
        if target_type:
            q += " AND target_type=?"; p.append(target_type)
        q += " ORDER BY id DESC LIMIT ? OFFSET ?"
        p += [limit, offset]
        with self.db._lock, self.db._conn() as c:
            return [dict(r) for r in c.execute(q, p).fetchall()]

    def count(self) -> int:
        with self.db._lock, self.db._conn() as c:
            return c.execute("SELECT COUNT(*) AS n FROM audit_logs").fetchone()["n"]

    def cleanup(self, keep_days: int = 90) -> int:
        """يحذف السجلات القديمة"""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).isoformat()
        with self.db._lock, self.db._conn() as c:
            return c.execute("DELETE FROM audit_logs WHERE created_at < ?",
                             (cutoff,)).rowcount


# ══════════════════════════════════════════════════════════════
#  NOTIFICATIONS
# ══════════════════════════════════════════════════════════════
class NotificationSeverity:
    INFO    = "info"
    WARNING = "warning"
    ERROR   = "error"
    SUCCESS = "success"


class Notifications:
    """مركز الإشعارات"""

    def __init__(self, db: DB):
        self.db = db

    def add(self, kind: str, title: str, message: str = "",
            severity: str = NotificationSeverity.INFO,
            target_role: str = None, target_user: int = None) -> int:
        now = now_iso()
        with self.db._lock, self.db._conn() as c:
            cur = c.execute("""INSERT INTO notifications(kind, severity, title, message,
                                    target_role, target_user, created_at)
                               VALUES(?,?,?,?,?,?,?)""",
                            (kind, severity, title, message,
                             target_role, target_user, now))
            return cur.lastrowid

    def list_for_role(self, role_slug: str = None,
                      target_user: int = None,
                      unread_only: bool = False,
                      limit: int = 50) -> list[dict]:
        q = "SELECT * FROM notifications WHERE 1=1"
        p = []
        if role_slug:
            q += " AND (target_role=? OR target_role IS NULL)"
            p.append(role_slug)
        if target_user:
            q += " AND (target_user=? OR target_user IS NULL)"
            p.append(target_user)
        if unread_only:
            q += " AND is_read=0"
        q += " ORDER BY id DESC LIMIT ?"
        p.append(limit)
        with self.db._lock, self.db._conn() as c:
            return [dict(r) for r in c.execute(q, p).fetchall()]

    def mark_read(self, nid: int) -> bool:
        with self.db._lock, self.db._conn() as c:
            return c.execute("UPDATE notifications SET is_read=1 WHERE id=?",
                             (nid,)).rowcount > 0

    def mark_all_read(self) -> int:
        with self.db._lock, self.db._conn() as c:
            return c.execute("UPDATE notifications SET is_read=1 WHERE is_read=0").rowcount

    def count_unread(self) -> int:
        with self.db._lock, self.db._conn() as c:
            return c.execute("SELECT COUNT(*) AS n FROM notifications WHERE is_read=0").fetchone()["n"]

    # ══════════════════════════════════════════════════════
    #  ALERTS — تنبيهات جاهزة
    # ══════════════════════════════════════════════════════
    def alert_provider_offline(self, provider_name: str) -> int:
        return self.add("provider_offline",
                        f"⚠️ مزود متوقف: {provider_name}",
                        "المزود لا يستجيب — تحقق من الحالة",
                        NotificationSeverity.ERROR,
                        target_role="owner")

    def alert_low_balance(self, provider_name: str, balance: float) -> int:
        return self.add("low_provider_balance",
                        f"💰 رصيد منخفض: {provider_name}",
                        f"الرصيد الحالي: {money(balance)}",
                        NotificationSeverity.WARNING,
                        target_role="owner")

    def alert_low_inventory(self, country: str, service: str, count: int) -> int:
        return self.add("low_inventory",
                        f"📦 مخزون منخفض: {country} / {service}",
                        f"المتبقي: {count} رقم فقط",
                        NotificationSeverity.WARNING,
                        target_role="inventory_manager")

    def alert_payment_error(self, payment_code: str, reason: str) -> int:
        return self.add("payment_error",
                        f"❌ خطأ دفع #{payment_code}",
                        reason,
                        NotificationSeverity.ERROR,
                        target_role="finance")

    def alert_large_order(self, order_code: str, amount: float) -> int:
        return self.add("large_order",
                        f"🔔 طلب كبير: {order_code}",
                        f"المبلغ: {money(amount)}",
                        NotificationSeverity.INFO,
                        target_role="owner")


# ══════════════════════════════════════════════════════════════
#  RATE LIMITER
# ══════════════════════════════════════════════════════════════
class RateLimiter:
    """محدد الطلبات — Thread-safe"""

    def __init__(self, max_per_min: int = None):
        self.max = max_per_min or Config.RATE_PER_MIN
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            b = self._hits.setdefault(key, [])
            b[:] = [t for t in b if now - t < 60.0]
            if len(b) >= self.max:
                return False
            b.append(now)
            return True

    def remaining(self, key: str) -> int:
        now = time.time()
        with self._lock:
            b = self._hits.get(key, [])
            b[:] = [t for t in b if now - t < 60.0]
            return max(0, self.max - len(b))

    def cleanup(self) -> None:
        now = time.time()
        with self._lock:
            for k in list(self._hits.keys()):
                self._hits[k] = [t for t in self._hits[k] if now - t < 60.0]
                if not self._hits[k]:
                    del self._hits[k]


# ══════════════════════════════════════════════════════════════
#  ▓▓▓ نهاية الجزء 8 ▓▓▓
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  WEBAPP HTML
# ══════════════════════════════════════════════════════════════
WEBAPP_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<meta name="theme-color" content="#0a0e1a">
<title>MTR NUMBERS — لوحة التحكم</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>__CSS__</style>
</head>
<body>
<div class="app">
<!-- ═══ Sidebar ═══ -->
<aside class="sidebar" id="sidebar">
  <div class="sb-brand">
    <div class="sb-logo">
      <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#3b82f6"/>
            <stop offset="50%" stop-color="#22c55e"/>
            <stop offset="100%" stop-color="#ef4444"/>
          </linearGradient>
        </defs>
        <rect x="6" y="6" width="52" height="52" rx="14" fill="none" stroke="url(#lg)" stroke-width="3"/>
        <text x="32" y="42" text-anchor="middle" font-family="Arial Black" font-size="22" font-weight="900" fill="url(#lg)">MTR</text>
      </svg>
    </div>
    <div class="sb-title">
      <div class="sb-ar">المطري</div>
      <div class="sb-en">NUMBERS</div>
    </div>
  </div>

  <nav class="sb-nav" id="sbNav">
    <a class="sb-item active" data-page="dashboard">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z"/></svg>
      <span>الرئيسية</span>
    </a>
    <a class="sb-item" data-page="users">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="9" cy="7" r="4"/><path d="M3 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2M16 3.13a4 4 0 0 1 0 7.75M21 21v-2a4 4 0 0 0-3-3.87"/></svg>
      <span>المستخدمون</span>
    </a>
    <a class="sb-item" data-page="orders">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M9 11H3v10h6zM21 3h-6v18h6zM15 7H9v14h6z"/></svg>
      <span>الطلبات</span>
    </a>
    <a class="sb-item" data-page="inventory">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M20 7l-8-4-8 4 8 4 8-4z"/><path d="M4 12l8 4 8-4M4 17l8 4 8-4"/></svg>
      <span>المخزون</span>
    </a>
    <a class="sb-item" data-page="providers">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
      <span>المزودون</span>
    </a>
    <a class="sb-item" data-page="countries">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/></svg>
      <span>الدول</span>
    </a>
    <a class="sb-item" data-page="services">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><circle cx="7" cy="7" r="1" fill="currentColor"/></svg>
      <span>الخدمات</span>
    </a>
    <a class="sb-item" data-page="wallet">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12V7H5a2 2 0 0 1 0-4h14v4M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4z"/></svg>
      <span>المحفظة</span>
    </a>
    <a class="sb-item" data-page="pricing">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
      <span>التسعير</span>
    </a>
    <a class="sb-item" data-page="audit">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
      <span>السجل</span>
    </a>
    <a class="sb-item" data-page="settings">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
      <span>الإعدادات</span>
    </a>
  </nav>

  <div class="sb-user" id="sbUser">
    <div class="sb-avatar">A</div>
    <div class="sb-user-info">
      <div class="sb-user-name">Admin</div>
      <div class="sb-user-role">Owner</div>
    </div>
  </div>
</aside>

<!-- ═══ Main ═══ -->
<main class="main">
  <!-- Topbar -->
  <header class="topbar">
    <button class="menu-toggle" id="menuToggle" aria-label="قائمة">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
    </button>
    <h1 class="topbar-title" id="pageTitle">لوحة التحكم</h1>
    <div class="topbar-actions">
      <button class="icon-btn" id="notifBtn" title="الإشعارات">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
        <span class="notif-badge" id="notifBadge" style="display:none">0</span>
      </button>
      <button class="icon-btn" id="refreshBtn" title="تحديث">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 4v5h-5"/></svg>
      </button>
    </div>
  </header>

  <!-- Pages container -->
  <div class="pages" id="pages">

    <!-- ═══ DASHBOARD ═══ -->
    <section class="page active" data-page="dashboard">
      <div class="stat-grid" id="statGrid">
        <div class="stat-card" data-color="blue">
          <div class="stat-icon blue">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="7" r="4"/><path d="M3 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/></svg>
          </div>
          <div class="stat-info">
            <div class="stat-value" id="sUsers">0</div>
            <div class="stat-label">المستخدمون</div>
          </div>
        </div>
        <div class="stat-card" data-color="green">
          <div class="stat-icon green">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11H3v10h6zM21 3h-6v18h6zM15 7H9v14h6z"/></svg>
          </div>
          <div class="stat-info">
            <div class="stat-value" id="sOrders">0</div>
            <div class="stat-label">الطلبات</div>
          </div>
        </div>
        <div class="stat-card" data-color="red">
          <div class="stat-icon red">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 7l-8-4-8 4 8 4 8-4z"/><path d="M4 12l8 4 8-4"/></svg>
          </div>
          <div class="stat-info">
            <div class="stat-value" id="sInv">0</div>
            <div class="stat-label">أرقام متاحة</div>
          </div>
        </div>
        <div class="stat-card" data-color="purple">
          <div class="stat-icon purple">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12V7H5a2 2 0 0 1 0-4h14v4M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4z"/></svg>
          </div>
          <div class="stat-info">
            <div class="stat-value" id="sRevenue">$0</div>
            <div class="stat-label">الإيرادات</div>
          </div>
        </div>
        <div class="stat-card" data-color="amber">
          <div class="stat-icon amber">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 20V10M12 20V4M6 20v-6"/></svg>
          </div>
          <div class="stat-info">
            <div class="stat-value" id="sProfit">$0</div>
            <div class="stat-label">الأرباح</div>
          </div>
        </div>
        <div class="stat-card" data-color="cyan">
          <div class="stat-icon cyan">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/></svg>
          </div>
          <div class="stat-info">
            <div class="stat-value" id="sProviders">0</div>
            <div class="stat-label">مزودون</div>
          </div>
        </div>
      </div>

      <div class="filter-bar">
        <button class="filter-btn active" data-range="today">اليوم</button>
        <button class="filter-btn" data-range="yesterday">أمس</button>
        <button class="filter-btn" data-range="7d">7 أيام</button>
        <button class="filter-btn" data-range="30d">30 يوم</button>
        <button class="filter-btn" data-range="all">الكل</button>
      </div>

      <div class="card-chart">
        <div class="card-head">
          <h3>الطلبات</h3>
          <span class="badge blue">Charts</span>
        </div>
        <div class="chart-bars" id="chartOrders"></div>
      </div>

      <div class="card-chart">
        <div class="card-head">
          <h3>الدول الأكثر استخداماً</h3>
        </div>
        <div class="top-list" id="topCountries"></div>
      </div>

      <div class="card-chart">
        <div class="card-head">
          <h3>حالة المزودين</h3>
        </div>
        <div class="provider-status" id="providersStatus"></div>
      </div>
    </section>

    <!-- ═══ USERS ═══ -->
    <section class="page" data-page="users">
      <div class="page-head">
        <div class="search-box">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
          <input type="text" id="usersSearch" placeholder="ابحث باسم أو ID...">
        </div>
        <button class="btn btn-primary" id="usersRefresh">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 4v5h-5"/></svg>
          تحديث
        </button>
      </div>
      <div class="table-wrap">
        <table class="data-table" id="usersTable">
          <thead>
            <tr>
              <th>ID</th><th>المستخدم</th><th>الرصيد</th><th>الطلبات</th><th>الحالة</th><th>إجراءات</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </section>

    <!-- ═══ ORDERS ═══ -->
    <section class="page" data-page="orders">
      <div class="page-head">
        <div class="filter-chips" id="ordersFilters">
          <button class="chip active" data-status="">الكل</button>
          <button class="chip" data-status="pending">معلقة</button>
          <button class="chip" data-status="waiting">انتظار</button>
          <button class="chip" data-status="completed">مكتملة</button>
          <button class="chip" data-status="cancelled">ملغاة</button>
        </div>
        <button class="btn btn-primary" id="ordersRefresh">تحديث</button>
      </div>
      <div class="table-wrap">
        <table class="data-table" id="ordersTable">
          <thead>
            <tr>
              <th>#</th><th>المستخدم</th><th>الدولة</th><th>الخدمة</th><th>الرقم</th><th>السعر</th><th>الحالة</th><th>التاريخ</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </section>

    <!-- ═══ INVENTORY ═══ -->
    <section class="page" data-page="inventory">
      <div class="page-head">
        <div class="filter-chips" id="invFilters">
          <button class="chip active" data-status="">الكل</button>
          <button class="chip" data-status="available">متاح</button>
          <button class="chip" data-status="reserved">محجوز</button>
          <button class="chip" data-status="sold">مباع</button>
        </div>
        <button class="btn btn-success" id="invImportBtn">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
          استيراد
        </button>
      </div>
      <div class="table-wrap">
        <table class="data-table" id="inventoryTable">
          <thead>
            <tr><th>#</th><th>الرقم</th><th>الدولة</th><th>الخدمة</th><th>الحالة</th><th>السعر</th></tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </section>

    <!-- ═══ PROVIDERS ═══ -->
    <section class="page" data-page="providers">
      <div class="page-head">
        <h2 class="page-h2">المزودون</h2>
        <button class="btn btn-primary" id="addProviderBtn">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
          إضافة مزود
        </button>
      </div>
      <div class="cards-grid" id="providersGrid"></div>
    </section>

    <!-- ═══ COUNTRIES ═══ -->
    <section class="page" data-page="countries">
      <div class="page-head">
        <h2 class="page-h2">الدول</h2>
        <button class="btn btn-primary" id="addCountryBtn">إضافة دولة</button>
      </div>
      <div class="cards-grid" id="countriesGrid"></div>
    </section>

    <!-- ═══ SERVICES ═══ -->
    <section class="page" data-page="services">
      <div class="page-head">
        <h2 class="page-h2">الخدمات</h2>
        <button class="btn btn-primary" id="addServiceBtn">إضافة خدمة</button>
      </div>
      <div class="cards-grid" id="servicesGrid"></div>
    </section>

    <!-- ═══ WALLET ═══ -->
    <section class="page" data-page="wallet">
      <h2 class="page-h2">المحفظة والمدفوعات</h2>
      <div class="stat-grid" style="grid-template-columns:repeat(auto-fit,minmax(180px,1fr))">
        <div class="stat-card"><div class="stat-info"><div class="stat-value" id="wTotalIn">$0</div><div class="stat-label">إجمالي الإيداعات</div></div></div>
        <div class="stat-card"><div class="stat-info"><div class="stat-value" id="wTotalOut">$0</div><div class="stat-label">إجمالي المشتريات</div></div></div>
        <div class="stat-card"><div class="stat-info"><div class="stat-value" id="wRefunds">$0</div><div class="stat-label">الاسترجاعات</div></div></div>
      </div>
      <div class="page-head"><h3>طلبات الإيداع المعلقة</h3></div>
      <div class="table-wrap">
        <table class="data-table" id="paymentsTable">
          <thead><tr><th>#</th><th>المستخدم</th><th>المبلغ</th><th>الحالة</th><th>التاريخ</th><th>إجراء</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </section>

    <!-- ═══ PRICING ═══ -->
    <section class="page" data-page="pricing">
      <div class="page-head">
        <h2 class="page-h2">التسعير</h2>
        <button class="btn btn-primary" id="addPriceBtn">إضافة تسعير</button>
      </div>
      <div class="table-wrap">
        <table class="data-table" id="pricingTable">
          <thead><tr><th>الدولة</th><th>الخدمة</th><th>التكلفة</th><th>ربح ثابت</th><th>ربح %</th><th>سعر البيع</th><th>إجراءات</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </section>

    <!-- ═══ AUDIT ═══ -->
    <section class="page" data-page="audit">
      <h2 class="page-h2">سجل التدقيق</h2>
      <div class="table-wrap">
        <table class="data-table" id="auditTable">
          <thead><tr><th>#</th><th>المستخدم</th><th>الإجراء</th><th>الهدف</th><th>التاريخ</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </section>

    <!-- ═══ SETTINGS ═══ -->
    <section class="page" data-page="settings">
      <h2 class="page-h2">الإعدادات</h2>
      <div class="settings-list" id="settingsList"></div>
    </section>

  </div>
</main>

<!-- ═══ Toast ═══ -->
<div class="toast" id="toast"></div>

<!-- ═══ Loading ═══ -->
<div class="loading" id="loading">
  <div class="spinner"></div>
  <div class="loading-text">جارٍ التحميل...</div>
</div>

<!-- ═══ Modal ═══ -->
<div class="modal" id="modal">
  <div class="modal-content">
    <div class="modal-head">
      <h3 id="modalTitle">عنوان</h3>
      <button class="icon-btn" id="modalClose">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
      </button>
    </div>
    <div class="modal-body" id="modalBody"></div>
    <div class="modal-foot">
      <button class="btn btn-outline" id="modalCancel">إلغاء</button>
      <button class="btn btn-primary" id="modalConfirm">تأكيد</button>
    </div>
  </div>
</div>

</div>
<script>__JS__</script>
</body>
</html>"""


# ══════════════════════════════════════════════════════════════
#  ▓▓▓ نهاية الجزء 9 ▓▓▓
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  WEBAPP CSS  (ألوان حقيقية)
# ══════════════════════════════════════════════════════════════
WEBAPP_CSS = """
/* ═══ Root Variables ═══ */
:root{
  --bg:#0a0e1a;--bg2:#0f1629;--card:#1e293b;--card2:#252f47;
  --border:#334155;--border2:#475569;
  --text:#f1f5f9;--muted:#94a3b8;--muted2:#64748b;

  /* 🎨 الألوان الحقيقية */
  --blue:#3b82f6;--blue-light:rgba(59,130,246,.15);--blue-glow:rgba(59,130,246,.4);
  --green:#22c55e;--green-light:rgba(34,197,94,.15);--green-glow:rgba(34,197,94,.4);
  --red:#ef4444;--red-light:rgba(239,68,68,.15);--red-glow:rgba(239,68,68,.4);
  --amber:#f59e0b;--amber-light:rgba(245,158,11,.15);--amber-glow:rgba(245,158,11,.4);
  --purple:#8b5cf6;--purple-light:rgba(139,92,246,.15);--purple-glow:rgba(139,92,246,.4);
  --cyan:#06b6d4;--cyan-light:rgba(6,182,212,.15);--cyan-glow:rgba(6,182,212,.4);
  --pink:#ec4899;--pink-light:rgba(236,72,153,.15);

  --radius:14px;--radius-sm:10px;--radius-lg:20px;
  --t:.25s cubic-bezier(.4,0,.2,1);
  --shadow:0 10px 30px rgba(0,0,0,.3);
  --sidebar-w:260px;
}

[data-theme="light"]{
  --bg:#f1f5f9;--bg2:#e2e8f0;--card:#ffffff;--card2:#f8fafc;
  --border:#cbd5e1;--border2:#94a3b8;
  --text:#0f172a;--muted:#475569;--muted2:#64748b;
  --shadow:0 10px 30px rgba(0,0,0,.08);
}

/* ═══ Reset ═══ */
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{height:100%;overflow-x:hidden}
body{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans Arabic',sans-serif;
  background:var(--bg);color:var(--text);
  line-height:1.6;font-size:15px;
  transition:background var(--t),color var(--t);
}
button,input,select,textarea{font-family:inherit}

/* ═══ App Layout ═══ */
.app{display:flex;min-height:100vh;position:relative}

/* ═══ Sidebar ═══ */
.sidebar{
  position:fixed;top:0;right:0;bottom:0;
  width:var(--sidebar-w);
  background:linear-gradient(180deg,var(--bg2),var(--bg));
  border-left:1px solid var(--border);
  display:flex;flex-direction:column;
  z-index:100;transition:transform var(--t);
}
.sb-brand{
  display:flex;align-items:center;gap:12px;
  padding:20px 18px;border-bottom:1px solid var(--border);
}
.sb-logo{width:44px;height:44px;flex-shrink:0}
.sb-logo svg{width:100%;height:100%;filter:drop-shadow(0 0 12px var(--blue-glow))}
.sb-title{line-height:1.1}
.sb-ar{font-size:18px;font-weight:900;background:linear-gradient(90deg,var(--blue),var(--green),var(--red));-webkit-background-clip:text;background-clip:text;color:transparent}
.sb-en{font-size:10px;font-weight:800;letter-spacing:2.5px;color:var(--muted)}

.sb-nav{flex:1;overflow-y:auto;padding:14px 10px}
.sb-nav::-webkit-scrollbar{width:6px}
.sb-nav::-webkit-scrollbar-thumb{background:var(--border);border-radius:99px}
.sb-item{
  display:flex;align-items:center;gap:12px;
  padding:11px 14px;border-radius:var(--radius-sm);
  color:var(--muted);font-size:14px;font-weight:600;
  cursor:pointer;text-decoration:none;
  transition:all var(--t);margin-bottom:4px;
}
.sb-item svg{width:20px;height:20px;flex-shrink:0}
.sb-item:hover{background:var(--card);color:var(--text)}
.sb-item.active{
  background:linear-gradient(90deg,var(--blue-light),var(--purple-light));
  color:var(--text);box-shadow:inset 3px 0 0 var(--blue);
}

.sb-user{
  display:flex;align-items:center;gap:10px;
  padding:14px 18px;border-top:1px solid var(--border);
  background:rgba(0,0,0,.2);
}
.sb-avatar{
  width:38px;height:38px;border-radius:50%;
  background:linear-gradient(135deg,var(--blue),var(--purple));
  display:flex;align-items:center;justify-content:center;
  font-weight:900;font-size:16px;color:#fff;flex-shrink:0;
}
.sb-user-info{line-height:1.2;min-width:0}
.sb-user-name{font-size:13px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sb-user-role{font-size:11px;color:var(--muted)}

/* ═══ Main ═══ */
.main{
  flex:1;margin-right:var(--sidebar-w);
  min-width:0;display:flex;flex-direction:column;
}

/* ═══ Topbar ═══ */
.topbar{
  position:sticky;top:0;z-index:50;
  display:flex;align-items:center;gap:14px;
  padding:14px 22px;
  background:rgba(10,14,26,.75);
  backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
  border-bottom:1px solid var(--border);
}
[data-theme="light"] .topbar{background:rgba(241,245,249,.85)}
.menu-toggle{
  display:none;background:var(--card);border:1px solid var(--border);
  color:var(--text);width:40px;height:40px;border-radius:10px;
  cursor:pointer;align-items:center;justify-content:center;
}
.menu-toggle svg{width:20px;height:20px}
.topbar-title{font-size:20px;font-weight:800;flex:1}
.topbar-actions{display:flex;gap:8px}

.icon-btn{
  position:relative;
  background:var(--card);border:1px solid var(--border);
  color:var(--text);width:40px;height:40px;border-radius:10px;
  cursor:pointer;display:flex;align-items:center;justify-content:center;
  transition:all var(--t);
}
.icon-btn:hover{border-color:var(--blue);transform:translateY(-1px)}
.icon-btn:active{transform:scale(.95)}
.icon-btn svg{width:20px;height:20px}
.notif-badge{
  position:absolute;top:-4px;right:-4px;
  background:var(--red);color:#fff;font-size:10px;font-weight:800;
  padding:2px 6px;border-radius:99px;min-width:18px;text-align:center;
}

/* ═══ Pages ═══ */
.pages{padding:22px;flex:1}
.page{display:none;animation:fadeUp .3s ease}
.page.active{display:block}
@keyframes fadeUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}

.page-h2{font-size:22px;font-weight:900;margin-bottom:18px}
.page-head{
  display:flex;align-items:center;justify-content:space-between;
  gap:14px;margin-bottom:18px;flex-wrap:wrap;
}

/* ═══ Buttons ═══ */
.btn{
  display:inline-flex;align-items:center;justify-content:center;gap:8px;
  padding:11px 20px;border-radius:var(--radius-sm);
  border:1.5px solid transparent;
  font-size:14px;font-weight:700;cursor:pointer;
  transition:all var(--t);text-decoration:none;white-space:nowrap;
}
.btn svg{width:18px;height:18px;flex-shrink:0}
.btn:active{transform:scale(.97)}

/* 🎨 ألوان حقيقية */
.btn-primary{background:var(--blue);color:#fff;box-shadow:0 6px 18px var(--blue-glow)}
.btn-primary:hover{background:#2563eb;transform:translateY(-1px)}

.btn-success{background:var(--green);color:#fff;box-shadow:0 6px 18px var(--green-glow)}
.btn-success:hover{background:#16a34a;transform:translateY(-1px)}

.btn-danger{background:var(--red);color:#fff;box-shadow:0 6px 18px var(--red-glow)}
.btn-danger:hover{background:#dc2626;transform:translateY(-1px)}

.btn-warning{background:var(--amber);color:#fff;box-shadow:0 6px 18px var(--amber-glow)}
.btn-warning:hover{background:#d97706}

.btn-outline{background:transparent;color:var(--text);border-color:var(--border)}
.btn-outline:hover{border-color:var(--blue);color:var(--blue)}

/* ═══ Stat Grid ═══ */
.stat-grid{
  display:grid;gap:14px;margin-bottom:22px;
  grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
}
.stat-card{
  background:var(--card);border:1px solid var(--border);
  border-radius:var(--radius);padding:18px;
  display:flex;align-items:center;gap:14px;
  transition:all var(--t);position:relative;overflow:hidden;
}
.stat-card:hover{transform:translateY(-2px);border-color:var(--border2)}

.stat-icon{
  width:52px;height:52px;border-radius:14px;
  display:flex;align-items:center;justify-content:center;
  flex-shrink:0;
}
.stat-icon svg{width:26px;height:26px}

/* 🔵 أزرق */
.stat-icon.blue{background:var(--blue-light);color:var(--blue);box-shadow:0 0 20px var(--blue-light)}
/* 🟢 أخضر */
.stat-icon.green{background:var(--green-light);color:var(--green);box-shadow:0 0 20px var(--green-light)}
/* 🔴 أحمر */
.stat-icon.red{background:var(--red-light);color:var(--red);box-shadow:0 0 20px var(--red-light)}
/* 🟡 برتقالي */
.stat-icon.amber{background:var(--amber-light);color:var(--amber);box-shadow:0 0 20px var(--amber-light)}
/* بنفسجي */
.stat-icon.purple{background:var(--purple-light);color:var(--purple);box-shadow:0 0 20px var(--purple-light)}
/* سماوي */
.stat-icon.cyan{background:var(--cyan-light);color:var(--cyan);box-shadow:0 0 20px var(--cyan-light)}

.stat-info{flex:1;min-width:0}
.stat-value{font-size:22px;font-weight:900;line-height:1.1;margin-bottom:4px}
.stat-label{font-size:12px;color:var(--muted);font-weight:600}

/* ═══ Filter Bar ═══ */
.filter-bar{
  display:flex;gap:8px;margin-bottom:18px;flex-wrap:wrap;
  padding:10px;background:var(--card);border-radius:var(--radius);
  border:1px solid var(--border);
}
.filter-btn{
  padding:8px 16px;border-radius:var(--radius-sm);
  background:transparent;border:1px solid transparent;
  color:var(--muted);font-size:13px;font-weight:700;
  cursor:pointer;transition:all var(--t);
}
.filter-btn:hover{color:var(--text);background:var(--card2)}
.filter-btn.active{background:var(--blue);color:#fff;box-shadow:0 4px 12px var(--blue-glow)}

.filter-chips{display:flex;gap:8px;flex-wrap:wrap}
.chip{
  padding:8px 14px;border-radius:99px;
  background:var(--card);border:1px solid var(--border);
  color:var(--muted);font-size:13px;font-weight:600;
  cursor:pointer;transition:all var(--t);
}
.chip:hover{border-color:var(--border2);color:var(--text)}
.chip.active{background:var(--blue);color:#fff;border-color:var(--blue)}

/* ═══ Card Chart ═══ */
.card-chart{
  background:var(--card);border:1px solid var(--border);
  border-radius:var(--radius);padding:20px;margin-bottom:18px;
}
.card-head{
  display:flex;align-items:center;justify-content:space-between;
  margin-bottom:16px;
}
.card-head h3{font-size:16px;font-weight:800}
.badge{
  padding:4px 10px;border-radius:99px;
  font-size:11px;font-weight:800;text-transform:uppercase;
  letter-spacing:.5px;
}
.badge.blue{background:var(--blue-light);color:var(--blue)}
.badge.green{background:var(--green-light);color:var(--green)}
.badge.red{background:var(--red-light);color:var(--red)}

.chart-bars{
  display:flex;align-items:flex-end;gap:6px;height:120px;padding:8px 0;
}
.chart-bar{
  flex:1;background:linear-gradient(180deg,var(--blue),var(--blue-light));
  border-radius:6px 6px 0 0;min-height:6px;
  transition:all .3s ease;position:relative;
}
.chart-bar:hover{filter:brightness(1.2)}
.chart-bar.green{background:linear-gradient(180deg,var(--green),var(--green-light))}
.chart-bar.red{background:linear-gradient(180deg,var(--red),var(--red-light))}

/* ═══ Top List ═══ */
.top-list{display:flex;flex-direction:column;gap:10px}
.top-item{
  display:flex;align-items:center;gap:12px;
  padding:10px;border-radius:var(--radius-sm);
  background:var(--card2);border:1px solid var(--border);
}
.top-rank{
  width:30px;height:30px;border-radius:50%;
  background:var(--blue);color:#fff;
  display:flex;align-items:center;justify-content:center;
  font-size:13px;font-weight:900;flex-shrink:0;
}
.top-rank.g1{background:var(--amber);box-shadow:0 0 12px var(--amber-glow)}
.top-rank.g2{background:var(--muted2)}
.top-rank.g3{background:var(--red)}
.top-name{flex:1;font-weight:700}
.top-value{font-weight:900;color:var(--blue)}

/* ═══ Provider Status ═══ */
.provider-status{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}
.provider-item{
  display:flex;align-items:center;gap:10px;
  padding:12px;border-radius:var(--radius-sm);
  background:var(--card2);border:1px solid var(--border);
}
.status-dot{
  width:10px;height:10px;border-radius:50%;flex-shrink:0;
  animation:pulse 2s ease-in-out infinite;
}
.status-dot.online{background:var(--green);box-shadow:0 0 10px var(--green)}
.status-dot.degraded{background:var(--amber);box-shadow:0 0 10px var(--amber)}
.status-dot.offline{background:var(--red);box-shadow:0 0 10px var(--red)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}

/* ═══ Tables ═══ */
.table-wrap{
  background:var(--card);border:1px solid var(--border);
  border-radius:var(--radius);overflow:hidden;
}
.data-table{width:100%;border-collapse:collapse}
.data-table thead{background:var(--card2)}
.data-table th{
  padding:14px 16px;text-align:right;
  font-size:12px;font-weight:800;color:var(--muted);
  text-transform:uppercase;letter-spacing:.5px;
  border-bottom:1px solid var(--border);
}
.data-table td{
  padding:12px 16px;font-size:14px;
  border-bottom:1px solid var(--border);
}
.data-table tbody tr{transition:background var(--t)}
.data-table tbody tr:hover{background:var(--card2)}
.data-table tbody tr:last-child td{border-bottom:none}

/* ═══ Status Badges ═══ */
.status-badge{
  display:inline-block;padding:4px 12px;border-radius:99px;
  font-size:11px;font-weight:800;text-transform:uppercase;
  letter-spacing:.5px;
}
.status-badge.active,
.status-badge.completed,
.status-badge.available{background:var(--green-light);color:var(--green)}
.status-badge.pending,
.status-badge.waiting,
.status-badge.reserved{background:var(--amber-light);color:var(--amber)}
.status-badge.blocked,
.status-badge.cancelled,
.status-badge.failed,
.status-badge.disabled{background:var(--red-light);color:var(--red)}
.status-badge.sold{background:var(--blue-light);color:var(--blue)}

/* ═══ Cards Grid ═══ */
.cards-grid{
  display:grid;gap:14px;
  grid-template-columns:repeat(auto-fill,minmax(260px,1fr));
}
.item-card{
  background:var(--card);border:1px solid var(--border);
  border-radius:var(--radius);padding:18px;
  transition:all var(--t);position:relative;overflow:hidden;
}
.item-card:hover{transform:translateY(-2px);border-color:var(--border2)}
.item-card::before{
  content:'';position:absolute;top:0;right:0;width:60px;height:60px;
  background:radial-gradient(circle at top right,var(--blue-light),transparent 70%);
  pointer-events:none;
}
.item-head{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.item-icon{
  width:44px;height:44px;border-radius:12px;
  display:flex;align-items:center;justify-content:center;
  font-size:20px;flex-shrink:0;
}
.item-info{flex:1;min-width:0}
.item-name{font-weight:800;font-size:15px;margin-bottom:2px}
.item-sub{font-size:12px;color:var(--muted)}
.item-body{display:flex;flex-direction:column;gap:6px;margin-bottom:12px}
.item-row{display:flex;justify-content:space-between;font-size:13px}
.item-row span:first-child{color:var(--muted)}
.item-actions{display:flex;gap:8px}
.item-actions .btn{flex:1;padding:8px 12px;font-size:13px}

/* ═══ Search Box ═══ */
.search-box{
  display:flex;align-items:center;gap:8px;
  background:var(--card);border:1px solid var(--border);
  border-radius:var(--radius-sm);padding:10px 14px;
  flex:1;min-width:220px;
}
.search-box svg{width:18px;height:18px;color:var(--muted);flex-shrink:0}
.search-box input{
  flex:1;background:transparent;border:none;
  color:var(--text);font-size:14px;outline:none;
}
.search-box input::placeholder{color:var(--muted)}

/* ═══ Settings List ═══ */
.settings-list{display:flex;flex-direction:column;gap:10px}
.setting-item{
  display:flex;align-items:center;justify-content:space-between;
  gap:14px;padding:16px;
  background:var(--card);border:1px solid var(--border);
  border-radius:var(--radius);
}
.setting-info{flex:1}
.setting-key{font-size:12px;color:var(--muted);font-family:monospace}
.setting-label{font-weight:700;font-size:14px;margin-bottom:2px}
.setting-value{
  background:var(--card2);border:1px solid var(--border);
  color:var(--text);padding:8px 14px;border-radius:var(--radius-sm);
  font-size:13px;font-family:monospace;min-width:120px;
  text-align:center;
}

/* ═══ Toast ═══ */
.toast{
  position:fixed;bottom:24px;left:50%;
  transform:translateX(-50%) translateY(120px);
  padding:14px 22px;border-radius:var(--radius-sm);
  background:var(--card);border:1px solid var(--border);
  color:var(--text);font-size:14px;font-weight:700;
  box-shadow:var(--shadow);z-index:9999;
  transition:transform .35s cubic-bezier(.4,0,.2,1);
  display:flex;align-items:center;gap:10px;max-width:90vw;
}
.toast.show{transform:translateX(-50%) translateY(0)}
.toast.success{border-color:var(--green);color:var(--green)}
.toast.error{border-color:var(--red);color:var(--red)}
.toast.warning{border-color:var(--amber);color:var(--amber)}

/* ═══ Loading ═══ */
.loading{
  position:fixed;inset:0;z-index:9998;
  background:rgba(10,14,26,.75);backdrop-filter:blur(8px);
  display:none;align-items:center;justify-content:center;
  flex-direction:column;gap:18px;
}
.loading.show{display:flex}
.spinner{
  width:52px;height:52px;border-radius:50%;
  border:4px solid var(--blue-light);border-top-color:var(--blue);
  animation:spin .8s linear infinite;
}
@keyframes spin{to{transform:rotate(360deg)}}
.loading-text{font-size:14px;font-weight:700;color:var(--muted)}

/* ═══ Modal ═══ */
.modal{
  position:fixed;inset:0;z-index:9997;
  background:rgba(0,0,0,.7);backdrop-filter:blur(4px);
  display:none;align-items:center;justify-content:center;
  padding:20px;
}
.modal.show{display:flex;animation:fadeUp .25s ease}
.modal-content{
  background:var(--bg2);border:1px solid var(--border);
  border-radius:var(--radius-lg);width:100%;max-width:520px;
  box-shadow:var(--shadow);overflow:hidden;
}
.modal-head{
  display:flex;align-items:center;justify-content:space-between;
  padding:18px 22px;border-bottom:1px solid var(--border);
}
.modal-head h3{font-size:17px;font-weight:800}
.modal-body{padding:22px;max-height:60vh;overflow-y:auto}
.modal-foot{
  display:flex;gap:10px;justify-content:flex-end;
  padding:16px 22px;border-top:1px solid var(--border);
  background:var(--card);
}

/* ═══ Form Inputs ═══ */
.form-group{margin-bottom:14px}
.form-group label{
  display:block;margin-bottom:6px;font-size:13px;
  font-weight:700;color:var(--muted);
}
.form-input,
.form-select,
.form-textarea{
  width:100%;padding:11px 14px;
  background:var(--card);border:1px solid var(--border);
  border-radius:var(--radius-sm);color:var(--text);
  font-size:14px;transition:all var(--t);
}
.form-input:focus,
.form-select:focus,
.form-textarea:focus{
  outline:none;border-color:var(--blue);
  box-shadow:0 0 0 3px var(--blue-light);
}
.form-textarea{min-height:100px;resize:vertical;font-family:inherit}

/* ═══ Empty State ═══ */
.empty-state{
  grid-column:1/-1;padding:50px 20px;text-align:center;
  color:var(--muted);
}
.empty-state svg{
  width:60px;height:60px;opacity:.3;margin-bottom:16px;
}
.empty-state p{font-size:14px}

/* ═══ Responsive ═══ */
@media (max-width:900px){
  .sidebar{transform:translateX(100%);box-shadow:-10px 0 40px rgba(0,0,0,.5)}
  .sidebar.open{transform:translateX(0)}
  .main{margin-right:0}
  .menu-toggle{display:flex}
  .pages{padding:16px}
  .topbar{padding:12px 16px}
  .stat-grid{grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
  .stat-value{font-size:18px}
  .page-h2{font-size:18px}
}

@media (max-width:600px){
  .stat-icon{width:44px;height:44px}
  .stat-icon svg{width:22px;height:22px}
  .data-table th,.data-table td{padding:10px 12px;font-size:13px}
  .btn{padding:9px 16px;font-size:13px}
}

/* ═══ Scrollbar ═══ */
::-webkit-scrollbar{width:8px;height:8px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:99px}
::-webkit-scrollbar-thumb:hover{background:var(--border2)}
"""


# ══════════════════════════════════════════════════════════════
#  ▓▓▓ نهاية الجزء 10 ▓▓▓
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  WEBAPP JS
# ══════════════════════════════════════════════════════════════
WEBAPP_JS = """
(function(){
'use strict';

/* ═══ Telegram WebApp ═══ */
const TWA = window.Telegram?.WebApp;
let INIT_DATA = '';
if (TWA) {
  try {
    TWA.ready();
    TWA.expand();
    INIT_DATA = TWA.initData || '';
    if (TWA.colorScheme === 'light') {
      document.documentElement.setAttribute('data-theme','light');
    }
  } catch(e){ console.warn('TWA:', e); }
}

/* ═══ State ═══ */
const state = {
  page: 'dashboard',
  users: [],
  orders: [],
  inventory: [],
  providers: [],
  countries: [],
  services: [],
  payments: [],
  prices: [],
  audit: [],
  settings: [],
  stats: {},
  ordersFilter: '',
  invFilter: '',
  usersSearch: '',
  dashboardRange: 'today',
  user: null,
};

/* ═══ Helpers ═══ */
const $  = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));

function esc(s) {
  const d = document.createElement('div');
  d.textContent = String(s ?? '');
  return d.innerHTML;
}

function fmtMoney(v) {
  return '$' + (Number(v) || 0).toFixed(2);
}

function fmtNum(v) {
  return (Number(v) || 0).toLocaleString('en-US');
}

function fmtDate(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    const y = d.getFullYear();
    const m = String(d.getMonth()+1).padStart(2,'0');
    const day = String(d.getDate()).padStart(2,'0');
    const hh = String(d.getHours()).padStart(2,'0');
    const mm = String(d.getMinutes()).padStart(2,'0');
    return `${y}-${m}-${day} ${hh}:${mm}`;
  } catch(e) { return iso; }
}

/* ═══ Toast ═══ */
let toastT;
function toast(msg, type='success') {
  const el = $('#toast');
  el.textContent = msg;
  el.className = 'toast show ' + type;
  clearTimeout(toastT);
  toastT = setTimeout(() => el.className = 'toast ' + type, 2600);
}

/* ═══ Loading ═══ */
function showLoading() { $('#loading').classList.add('show'); }
function hideLoading() { $('#loading').classList.remove('show'); }

/* ═══ Modal ═══ */
let modalAction = null;
function openModal({title, body, confirmText, onConfirm}) {
  $('#modalTitle').textContent = title || 'تأكيد';
  if (typeof body === 'string') $('#modalBody').innerHTML = body;
  else $('#modalBody').innerHTML = '';
  $('#modalConfirm').textContent = confirmText || 'تأكيد';
  modalAction = onConfirm;
  $('#modal').classList.add('show');
}
function closeModal() {
  $('#modal').classList.remove('show');
  modalAction = null;
}
async function handleModalConfirm() {
  if (typeof modalAction === 'function') {
    try { await modalAction(); }
    catch(e){ toast('خطأ: ' + e.message, 'error'); }
  }
  closeModal();
}

/* ═══ API ═══ */
async function api(path, opts={}) {
  const o = {
    ...opts,
    headers: {
      'Content-Type':'application/json',
      'X-Init-Data': INIT_DATA,
      ...(opts.headers || {}),
    },
  };
  if (o.body && typeof o.body === 'object') {
    o.body = JSON.stringify(o.body);
  }
  const res = await fetch(path, o);
  if (!res.ok) {
    let msg = 'HTTP ' + res.status;
    try { const j = await res.json(); msg = j.error || j.detail || msg; } catch(e){}
    throw new Error(msg);
  }
  return res.json();
}

/* ═══ Navigation ═══ */
function switchPage(page) {
  state.page = page;
  $$('.sb-item').forEach(el => el.classList.toggle('active', el.dataset.page === page));
  $$('.page').forEach(el => el.classList.toggle('active', el.dataset.page === page));

  const titles = {
    dashboard: 'لوحة التحكم',
    users: 'المستخدمون',
    orders: 'الطلبات',
    inventory: 'المخزون',
    providers: 'المزودون',
    countries: 'الدول',
    services: 'الخدمات',
    wallet: 'المحفظة',
    pricing: 'التسعير',
    audit: 'سجل التدقيق',
    settings: 'الإعدادات',
  };
  $('#pageTitle').textContent = titles[page] || page;
  $('#sidebar').classList.remove('open');

  // Lazy load
  const loaders = {
    dashboard: loadDashboard,
    users: loadUsers,
    orders: loadOrders,
    inventory: loadInventory,
    providers: loadProviders,
    countries: loadCountries,
    services: loadServices,
    wallet: loadWallet,
    pricing: loadPricing,
    audit: loadAudit,
    settings: loadSettings,
  };
  if (loaders[page]) loaders[page]();
}

/* ═══════════════════════════════════════════
   DASHBOARD
   ═══════════════════════════════════════════ */
async function loadDashboard() {
  try {
    const d = await api('/api/dashboard?range=' + state.dashboardRange);
    state.stats = d.stats || {};

    $('#sUsers').textContent     = fmtNum(d.stats.users || 0);
    $('#sOrders').textContent    = fmtNum(d.stats.orders || 0);
    $('#sInv').textContent       = fmtNum(d.stats.inventory_available || 0);
    $('#sRevenue').textContent   = fmtMoney(d.stats.revenue || 0);
    $('#sProfit').textContent    = fmtMoney(d.stats.profit || 0);
    $('#sProviders').textContent = fmtNum(d.stats.providers || 0);

    renderOrdersChart(d.chart || []);
    renderTopCountries(d.top_countries || []);
    renderProviderStatus(d.providers || []);
  } catch(e) {
    toast('فشل تحميل الرئيسية: ' + e.message, 'error');
  }
}

function renderOrdersChart(data) {
  const el = $('#chartOrders');
  if (!data.length) {
    el.innerHTML = '<div style="color:var(--muted);padding:20px;text-align:center;font-size:13px">لا بيانات</div>';
    return;
  }
  const max = Math.max(...data.map(x => x.value), 1);
  el.innerHTML = data.map(x => {
    const h = Math.max(6, Math.round((x.value / max) * 110));
    const cls = x.value > max * 0.7 ? 'green' : (x.value < max * 0.3 ? 'red' : '');
    return `<div class="chart-bar ${cls}" style="height:${h}px" title="${esc(x.label)}: ${x.value}"></div>`;
  }).join('');
}

function renderTopCountries(data) {
  const el = $('#topCountries');
  if (!data.length) {
    el.innerHTML = '<div style="color:var(--muted);padding:16px;text-align:center;font-size:13px">لا بيانات</div>';
    return;
  }
  el.innerHTML = data.map((x, i) => `
    <div class="top-item">
      <div class="top-rank ${i===0?'g1':i===1?'g2':i===2?'g3':''}">${i+1}</div>
      <div class="top-name">${esc(x.name || x.country || '—')}</div>
      <div class="top-value">${fmtNum(x.count || x.value || 0)}</div>
    </div>
  `).join('');
}

function renderProviderStatus(data) {
  const el = $('#providersStatus');
  if (!data.length) {
    el.innerHTML = '<div style="color:var(--muted);padding:16px;text-align:center;font-size:13px">لا مزودين</div>';
    return;
  }
  el.innerHTML = data.map(p => {
    const status = p.status === 'active' ? 'online'
                 : p.status === 'degraded' ? 'degraded' : 'offline';
    const label = status === 'online' ? 'متصل'
                : status === 'degraded' ? 'بطيء' : 'متوقف';
    return `
      <div class="provider-item">
        <span class="status-dot ${status}"></span>
        <div style="flex:1;min-width:0">
          <div style="font-weight:700;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(p.name)}</div>
          <div style="font-size:11px;color:var(--muted)">${label} • رصيد ${fmtMoney(p.balance || 0)}</div>
        </div>
      </div>
    `;
  }).join('');
}

/* ═══════════════════════════════════════════
   USERS
   ═══════════════════════════════════════════ */
async function loadUsers() {
  try {
    const q = state.usersSearch ? '?search=' + encodeURIComponent(state.usersSearch) : '';
    const d = await api('/api/users' + q);
    state.users = d.users || [];
    renderUsers();
  } catch(e) {
    toast('فشل تحميل المستخدمين: ' + e.message, 'error');
  }
}

function renderUsers() {
  const tb = $('#usersTable tbody');
  if (!state.users.length) {
    tb.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:30px;color:var(--muted)">لا مستخدمين</td></tr>';
    return;
  }
  tb.innerHTML = state.users.map(u => {
    const status = u.status === 'blocked' ? 'blocked' : 'active';
    const label = status === 'active' ? 'نشط' : 'محظور';
    return `
      <tr>
        <td><code style="color:var(--muted)">#${u.id}</code></td>
        <td>
          <div style="font-weight:700">${esc(u.first_name || u.username || 'مستخدم')}</div>
          <div style="font-size:12px;color:var(--muted)">ID: ${u.tg_id}</div>
        </td>
        <td><b style="color:var(--green)">${fmtMoney(u.balance)}</b></td>
        <td>${fmtNum(u.orders_count || 0)}</td>
        <td><span class="status-badge ${status}">${label}</span></td>
        <td>
          <button class="icon-btn" onclick="window.mtrViewUser(${u.id})" title="عرض">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

window.mtrViewUser = async function(uid) {
  try {
    const d = await api('/api/user?id=' + uid);
    const u = d.user;
    openModal({
      title: 'مستخدم #' + uid,
      body: `
        <div class="form-group"><label>الاسم</label><div>${esc(u.first_name || '—')}</div></div>
        <div class="form-group"><label>Username</label><div>${esc(u.username || '—')}</div></div>
        <div class="form-group"><label>Telegram ID</label><div><code>${u.tg_id}</code></div></div>
        <div class="form-group"><label>الرصيد</label><div><b style="color:var(--green)">${fmtMoney(u.balance)}</b></div></div>
        <div class="form-group"><label>إجمالي المشتريات</label><div>${fmtMoney(u.total_spent)}</div></div>
        <div class="form-group"><label>الحالة</label><div>${u.status === 'blocked' ? 'محظور' : 'نشط'}</div></div>
        <div style="display:flex;gap:8px;margin-top:14px">
          <button class="btn ${u.status === 'blocked' ? 'btn-success' : 'btn-danger'}" style="flex:1" onclick="window.mtrToggleUser(${uid})">
            ${u.status === 'blocked' ? 'إلغاء الحظر' : 'حظر'}
          </button>
        </div>
      `,
      confirmText: 'إغلاق',
      onConfirm: () => {},
    });
  } catch(e) {
    toast('فشل: ' + e.message, 'error');
  }
};

window.mtrToggleUser = async function(uid) {
  try {
    await api('/api/user/toggle-block', {method:'POST', body:{user_id: uid}});
    toast('تم التحديث ✓');
    closeModal();
    loadUsers();
  } catch(e) {
    toast('فشل: ' + e.message, 'error');
  }
};

/* ═══════════════════════════════════════════
   ORDERS
   ═══════════════════════════════════════════ */
async function loadOrders() {
  try {
    const q = state.ordersFilter ? '?status=' + state.ordersFilter : '';
    const d = await api('/api/orders' + q);
    state.orders = d.orders || [];
    renderOrders();
  } catch(e) {
    toast('فشل تحميل الطلبات', 'error');
  }
}

function renderOrders() {
  const tb = $('#ordersTable tbody');
  if (!state.orders.length) {
    tb.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:30px;color:var(--muted)">لا طلبات</td></tr>';
    return;
  }
  tb.innerHTML = state.orders.map(o => {
    const stMap = {
      pending:   ['pending','معلق'],
      waiting:   ['waiting','انتظار'],
      completed: ['completed','مكتمل'],
      failed:    ['failed','فشل'],
      cancelled: ['cancelled','ملغى'],
      refunded:  ['completed','مسترجع'],
      expired:   ['failed','منتهي'],
    };
    const [cls, lbl] = stMap[o.status] || ['pending', o.status];
    return `
      <tr>
        <td><code>#${o.id}</code></td>
        <td>${esc(o.username || o.first_name || '—')}</td>
        <td>${esc(o.country_name || '—')}</td>
        <td>${esc(o.service_name || '—')}</td>
        <td><code style="font-size:12px">${esc(o.number || '—')}</code></td>
        <td>${fmtMoney(o.sell_price)}</td>
        <td><span class="status-badge ${cls}">${lbl}</span></td>
        <td>${fmtDate(o.created_at)}</td>
      </tr>
    `;
  }).join('');
}

/* ═══════════════════════════════════════════
   INVENTORY
   ═══════════════════════════════════════════ */
async function loadInventory() {
  try {
    const q = state.invFilter ? '?status=' + state.invFilter : '';
    const d = await api('/api/inventory' + q);
    state.inventory = d.items || [];
    renderInventory();
  } catch(e) {
    toast('فشل تحميل المخزون', 'error');
  }
}

function renderInventory() {
  const tb = $('#inventoryTable tbody');
  if (!state.inventory.length) {
    tb.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:30px;color:var(--muted)">لا أرقام</td></tr>';
    return;
  }
  tb.innerHTML = state.inventory.map(it => {
    const stMap = {
      available: ['available','متاح'],
      reserved:  ['reserved','محجوز'],
      sold:      ['sold','مباع'],
      disabled:  ['disabled','معطل'],
    };
    const [cls, lbl] = stMap[it.status] || ['available', it.status];
    return `
      <tr>
        <td>${it.id}</td>
        <td><code>${esc(it.number)}</code></td>
        <td>${esc(it.country_name || '—')}</td>
        <td>${esc(it.service_name || '—')}</td>
        <td><span class="status-badge ${cls}">${lbl}</span></td>
        <td>${fmtMoney(it.cost)}</td>
      </tr>
    `;
  }).join('');
}

/* ═══════════════════════════════════════════
   PROVIDERS
   ═══════════════════════════════════════════ */
async function loadProviders() {
  try {
    const d = await api('/api/providers');
    state.providers = d.providers || [];
    renderProviders();
  } catch(e) {
    toast('فشل تحميل المزودين', 'error');
  }
}

function renderProviders() {
  const el = $('#providersGrid');
  if (!state.providers.length) {
    el.innerHTML = '<div class="empty-state"><p>لا مزودين</p></div>';
    return;
  }
  el.innerHTML = state.providers.map(p => {
    const stCls = p.status === 'active' ? 'active'
                 : p.status === 'degraded' ? 'pending' : 'failed';
    const stLbl = p.status === 'active' ? 'نشط'
                 : p.status === 'degraded' ? 'بطيء' : 'متوقف';
    return `
      <div class="item-card">
        <div class="item-head">
          <div class="item-icon" style="background:var(--blue-light);color:var(--blue)">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/></svg>
          </div>
          <div class="item-info">
            <div class="item-name">${esc(p.name)}</div>
            <div class="item-sub">${esc(p.adapter)}</div>
          </div>
          <span class="status-badge ${stCls}">${stLbl}</span>
        </div>
        <div class="item-body">
          <div class="item-row"><span>الرصيد</span><b style="color:var(--green)">${fmtMoney(p.balance || 0)}</b></div>
          <div class="item-row"><span>الاستجابة</span><b>${p.latency_ms || 0}ms</b></div>
          <div class="item-row"><span>نجاح / فشل</span><b>${p.success_count || 0} / ${p.error_count || 0}</b></div>
        </div>
        <div class="item-actions">
          <button class="btn btn-primary" onclick="window.mtrPingProvider(${p.id})">اختبار</button>
          <button class="btn btn-outline" onclick="window.mtrEditProvider(${p.id})">تعديل</button>
        </div>
      </div>
    `;
  }).join('');
}

window.mtrPingProvider = async function(pid) {
  try {
    showLoading();
    const d = await api('/api/provider/ping', {method:'POST', body:{provider_id:pid}});
    hideLoading();
    if (d.ok) toast('متصل ✓ — تأخير: ' + d.latency + 'ms', 'success');
    else toast('فشل الاتصال: ' + (d.error || ''), 'error');
    loadProviders();
  } catch(e) {
    hideLoading();
    toast('فشل: ' + e.message, 'error');
  }
};

window.mtrEditProvider = function(pid) {
  toast('تعديل المزود #' + pid + ' — قريباً', 'warning');
};

/* ═══════════════════════════════════════════
   COUNTRIES
   ═══════════════════════════════════════════ */
async function loadCountries() {
  try {
    const d = await api('/api/countries');
    state.countries = d.countries || [];
    renderCountries();
  } catch(e) {
    toast('فشل تحميل الدول', 'error');
  }
}

function renderCountries() {
  const el = $('#countriesGrid');
  if (!state.countries.length) {
    el.innerHTML = '<div class="empty-state"><p>لا دول</p></div>';
    return;
  }
  el.innerHTML = state.countries.map(c => {
    const stCls = c.status === 'active' ? 'active' : 'disabled';
    const stLbl = c.status === 'active' ? 'نشطة' : 'معطلة';
    return `
      <div class="item-card">
        <div class="item-head">
          <div class="item-icon" style="background:var(--blue-light);color:var(--blue);font-size:24px">${esc(c.flag || '🌐')}</div>
          <div class="item-info">
            <div class="item-name">${esc(c.name_ar)}</div>
            <div class="item-sub">${esc(c.name_en)} • ${esc(c.dial_code)}</div>
          </div>
        </div>
        <div style="margin-top:10px">
          <span class="status-badge ${stCls}">${stLbl}</span>
        </div>
      </div>
    `;
  }).join('');
}

/* ═══════════════════════════════════════════
   SERVICES
   ═══════════════════════════════════════════ */
async function loadServices() {
  try {
    const d = await api('/api/services');
    state.services = d.services || [];
    renderServices();
  } catch(e) {
    toast('فشل تحميل الخدمات', 'error');
  }
}

function renderServices() {
  const el = $('#servicesGrid');
  if (!state.services.length) {
    el.innerHTML = '<div class="empty-state"><p>لا خدمات</p></div>';
    return;
  }
  el.innerHTML = state.services.map(s => {
    const stCls = s.status === 'active' ? 'active' : 'disabled';
    const stLbl = s.status === 'active' ? 'نشطة' : 'معطلة';
    return `
      <div class="item-card">
        <div class="item-head">
          <div class="item-icon" style="background:${s.color}22;color:${s.color}">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v8M8 12h8"/></svg>
          </div>
          <div class="item-info">
            <div class="item-name">${esc(s.name_ar)}</div>
            <div class="item-sub">${esc(s.slug)}</div>
          </div>
        </div>
        <div style="margin-top:10px">
          <span class="status-badge ${stCls}">${stLbl}</span>
        </div>
      </div>
    `;
  }).join('');
}

/* ═══════════════════════════════════════════
   WALLET / PAYMENTS
   ═══════════════════════════════════════════ */
async function loadWallet() {
  try {
    const d = await api('/api/wallet/overview');
    $('#wTotalIn').textContent  = fmtMoney(d.total_deposited || 0);
    $('#wTotalOut').textContent = fmtMoney(d.total_spent || 0);
    $('#wRefunds').textContent  = fmtMoney(d.total_refunded || 0);
    state.payments = d.payments || [];
    renderPayments();
  } catch(e) {
    toast('فشل تحميل المحفظة', 'error');
  }
}

function renderPayments() {
  const tb = $('#paymentsTable tbody');
  if (!state.payments.length) {
    tb.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:30px;color:var(--muted)">لا طلبات إيداع</td></tr>';
    return;
  }
  tb.innerHTML = state.payments.map(p => {
    const stCls = p.status === 'paid' ? 'completed'
                 : p.status === 'pending' ? 'pending'
                 : 'failed';
    const stLbl = p.status === 'paid' ? 'مدفوع'
                 : p.status === 'pending' ? 'معلق' : 'مرفوض';
    const actions = p.status === 'pending'
      ? `<button class="btn btn-success" style="padding:6px 12px;font-size:12px" onclick="window.mtrVerifyPay(${p.id},true)">موافقة</button>
         <button class="btn btn-danger"  style="padding:6px 12px;font-size:12px" onclick="window.mtrVerifyPay(${p.id},false)">رفض</button>`
      : '—';
    return `
      <tr>
        <td>#${p.id}</td>
        <td>${esc(p.username || p.first_name || '—')}</td>
        <td><b>${fmtMoney(p.amount)}</b></td>
        <td><span class="status-badge ${stCls}">${stLbl}</span></td>
        <td>${fmtDate(p.created_at)}</td>
        <td style="display:flex;gap:6px">${actions}</td>
      </tr>
    `;
  }).join('');
}

window.mtrVerifyPay = async function(pid, approve) {
  try {
    await api('/api/wallet/verify-payment', {
      method:'POST',
      body:{ payment_id: pid, approve: approve },
    });
    toast(approve ? 'تم القبول ✓' : 'تم الرفض', approve ? 'success' : 'warning');
    loadWallet();
  } catch(e) {
    toast('فشل: ' + e.message, 'error');
  }
};

/* ═══════════════════════════════════════════
   PRICING
   ═══════════════════════════════════════════ */
async function loadPricing() {
  try {
    const d = await api('/api/prices');
    state.prices = d.prices || [];
    renderPricing();
  } catch(e) {
    toast('فشل تحميل التسعير', 'error');
  }
}

function renderPricing() {
  const tb = $('#pricingTable tbody');
  if (!state.prices.length) {
    tb.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:30px;color:var(--muted)">لا تسعير</td></tr>';
    return;
  }
  tb.innerHTML = state.prices.map(p => {
    const total = (p.cost || 0) + (p.profit_fixed || 0) + (p.cost || 0) * (p.profit_percent || 0) / 100;
    return `
      <tr>
        <td>${esc(p.country_name || '—')}</td>
        <td>${esc(p.service_name || '—')}</td>
        <td>${fmtMoney(p.cost)}</td>
        <td>${fmtMoney(p.profit_fixed)}</td>
        <td>${(p.profit_percent || 0).toFixed(1)}%</td>
        <td><b style="color:var(--green)">${fmtMoney(total)}</b></td>
        <td>
          <button class="icon-btn" onclick="window.mtrEditPrice(${p.id})" title="تعديل">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4v16h16v-7M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

window.mtrEditPrice = function(pid) {
  toast('تعديل التسعير #' + pid + ' — قريباً', 'warning');
};

/* ═══════════════════════════════════════════
   AUDIT
   ═══════════════════════════════════════════ */
async function loadAudit() {
  try {
    const d = await api('/api/audit');
    state.audit = d.logs || [];
    renderAudit();
  } catch(e) {
    toast('فشل تحميل السجل', 'error');
  }
}

function renderAudit() {
  const tb = $('#auditTable tbody');
  if (!state.audit.length) {
    tb.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:30px;color:var(--muted)">لا سجلات</td></tr>';
    return;
  }
  tb.innerHTML = state.audit.map(a => `
    <tr>
      <td><code>#${a.id}</code></td>
      <td>${esc(a.actor_name || ('#' + a.actor_id))}</td>
      <td><span class="badge blue">${esc(a.action)}</span></td>
      <td>${esc(a.target_type || '—')} ${a.target_id ? '#' + a.target_id : ''}</td>
      <td>${fmtDate(a.created_at)}</td>
    </tr>
  `).join('');
}

/* ═══════════════════════════════════════════
   SETTINGS
   ═══════════════════════════════════════════ */
async function loadSettings() {
  try {
    const d = await api('/api/settings');
    state.settings = d.settings || [];
    renderSettings();
  } catch(e) {
    toast('فشل تحميل الإعدادات', 'error');
  }
}

function renderSettings() {
  const el = $('#settingsList');
  if (!state.settings.length) {
    el.innerHTML = '<div class="empty-state"><p>لا إعدادات</p></div>';
    return;
  }
  el.innerHTML = state.settings.map(s => `
    <div class="setting-item">
      <div class="setting-info">
        <div class="setting-label">${esc(s.key)}</div>
        <div class="setting-key">${esc(s.category || 'general')}</div>
      </div>
      <input class="setting-value" value="${esc(s.value)}"
             onchange="window.mtrSaveSetting('${esc(s.key)}', this.value)">
    </div>
  `).join('');
}

window.mtrSaveSetting = async function(key, value) {
  try {
    await api('/api/settings/save', {method:'POST', body:{key, value}});
    toast('تم الحفظ ✓');
  } catch(e) {
    toast('فشل الحفظ: ' + e.message, 'error');
  }
};

/* ═══════════════════════════════════════════
   EVENTS
   ═══════════════════════════════════════════ */
function bindEvents() {
  // Sidebar navigation
  $$('.sb-item').forEach(el => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      switchPage(el.dataset.page);
    });
  });

  // Mobile menu
  $('#menuToggle').addEventListener('click', () => {
    $('#sidebar').classList.toggle('open');
  });

  // Refresh
  $('#refreshBtn').addEventListener('click', () => {
    switchPage(state.page);
    toast('تم التحديث');
  });

  // Notifications
  $('#notifBtn').addEventListener('click', async () => {
    try {
      const d = await api('/api/notifications');
      const list = d.notifications || [];
      if (!list.length) {
        toast('لا إشعارات جديدة');
        return;
      }
      openModal({
        title: 'الإشعارات',
        body: list.map(n => `
          <div class="setting-item" style="margin-bottom:8px">
            <div class="setting-info">
              <div class="setting-label">${esc(n.title)}</div>
              <div class="setting-key">${esc(n.message || '')}</div>
            </div>
          </div>
        `).join(''),
        confirmText: 'إغلاق',
        onConfirm: () => {},
      });
    } catch(e){ toast('فشل: ' + e.message, 'error'); }
  });

  // Modal
  $('#modalClose').addEventListener('click', closeModal);
  $('#modalCancel').addEventListener('click', closeModal);
  $('#modalConfirm').addEventListener('click', handleModalConfirm);
  $('#modal').addEventListener('click', (e) => {
    if (e.target === $('#modal')) closeModal();
  });

  // Dashboard filters
  $$('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      $$('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.dashboardRange = btn.dataset.range;
      loadDashboard();
    });
  });

  // Users search
  let searchT;
  $('#usersSearch')?.addEventListener('input', (e) => {
    clearTimeout(searchT);
    searchT = setTimeout(() => {
      state.usersSearch = e.target.value;
      loadUsers();
    }, 300);
  });
  $('#usersRefresh')?.addEventListener('click', loadUsers);

  // Orders filters
  $$('#ordersFilters .chip').forEach(c => {
    c.addEventListener('click', () => {
      $$('#ordersFilters .chip').forEach(x => x.classList.remove('active'));
      c.classList.add('active');
      state.ordersFilter = c.dataset.status;
      loadOrders();
    });
  });
  $('#ordersRefresh')?.addEventListener('click', loadOrders);

  // Inventory filters
  $$('#invFilters .chip').forEach(c => {
    c.addEventListener('click', () => {
      $$('#invFilters .chip').forEach(x => x.classList.remove('active'));
      c.classList.add('active');
      state.invFilter = c.dataset.status;
      loadInventory();
    });
  });
  $('#invImportBtn')?.addEventListener('click', () => {
    openModal({
      title: 'استيراد أرقام',
      body: `
        <div class="form-group"><label>الدولة</label>
          <select class="form-select" id="impCountry">${state.countries.map(c => `<option value="${c.id}">${esc(c.name_ar)}</option>`).join('')}</select>
        </div>
        <div class="form-group"><label>الخدمة</label>
          <select class="form-select" id="impService">${state.services.map(s => `<option value="${s.id}">${esc(s.name_ar)}</option>`).join('')}</select>
        </div>
        <div class="form-group"><label>الأرقام (سطر لكل رقم)</label>
          <textarea class="form-textarea" id="impNumbers" placeholder="+967771234567&#10;+967772345678"></textarea>
        </div>
      `,
      confirmText: 'استيراد',
      onConfirm: async () => {
        const text = $('#impNumbers').value;
        const country = safeInt($('#impCountry').value);
        const service = safeInt($('#impService').value);
        if (!text.trim()) throw new Error('أدخل أرقام');
        const d = await api('/api/inventory/import', {
          method:'POST',
          body:{ text, country_id: country, service_id: service },
        });
        toast(`تم: ${d.imported} ✓ | مكرر: ${d.duplicates} | خطأ: ${d.invalid}`, 'success');
        loadInventory();
      },
    });
  });

  // Providers / Countries / Services
  $('#addProviderBtn')?.addEventListener('click', () => {
    toast('إضافة مزود — استخدم /admin في البوت', 'warning');
  });
  $('#addCountryBtn')?.addEventListener('click', () => {
    toast('إضافة دولة — استخدم /admin في البوت', 'warning');
  });
  $('#addServiceBtn')?.addEventListener('click', () => {
    toast('إضافة خدمة — استخدم /admin في البوت', 'warning');
  });
  $('#addPriceBtn')?.addEventListener('click', () => {
    toast('إضافة تسعير — قريباً', 'warning');
  });
}

function safeInt(v){ return parseInt(v) || 0; }

/* ═══ Init ═══ */
async function init() {
  bindEvents();
  try {
    const me = await api('/api/me');
    if (me.user) {
      $('#sbUser .sb-user-name').textContent = me.user.first_name || me.user.username || 'Admin';
      $('#sbUser .sb-avatar').textContent = (me.user.first_name || 'A').charAt(0).toUpperCase();
      const roleLabel = me.user.role_name || (me.user.is_owner ? 'Owner' : 'Admin');
      $('#sbUser .sb-user-role').textContent = roleLabel;
    }
  } catch(e){}

  // Load initial data for filters (countries, services)
  try {
    const [c, s] = await Promise.all([api('/api/countries'), api('/api/services')]);
    state.countries = c.countries || [];
    state.services = s.services || [];
  } catch(e){}

  switchPage('dashboard');

  // Polling for notifications every 60s
  setInterval(async () => {
    try {
      const d = await api('/api/notifications/count');
      const n = d.unread || 0;
      const badge = $('#notifBadge');
      if (n > 0) { badge.textContent = n; badge.style.display = ''; }
      else { badge.style.display = 'none'; }
    } catch(e){}
  }, 60000);
}

document.addEventListener('DOMContentLoaded', init);
})();
"""


# ══════════════════════════════════════════════════════════════
#  ▓▓▓ نهاية الجزء 11 ▓▓▓
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  WEBAPP AUTH — التحقق من Telegram initData
# ══════════════════════════════════════════════════════════════
class WebAppAuth:
    """يتحقق من initData عبر HMAC-SHA256"""

    @staticmethod
    def verify(init_data: str, bot_token: str, max_age: int = 86400) -> Optional[dict]:
        if not init_data or not bot_token:
            return None
        try:
            parsed = dict(urllib.parse.parse_qsl(init_data, strict_parsing=False))
        except Exception:
            return None

        received = parsed.pop("hash", None)
        if not received:
            return None

        check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        calc = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(calc, received):
            return None

        try:
            auth_date = int(parsed.get("auth_date", "0"))
        except ValueError:
            return None

        if auth_date <= 0 or (time.time() - auth_date) > max_age:
            return None

        user = None
        if parsed.get("user"):
            try:
                user = json.loads(parsed["user"])
            except Exception:
                user = None

        return {"user": user, "auth_date": auth_date}


# ══════════════════════════════════════════════════════════════
#  SERVER — FastAPI
# ══════════════════════════════════════════════════════════════
class Server:
    """FastAPI server — WebApp + API endpoints"""

    def __init__(self, db: DB, wallet: Wallet, payments: Payments,
                 rbac: RBAC, audit: Audit, notifications: Notifications,
                 countries: CountryManager, services: ServiceManager,
                 inventory: InventoryManager, pricing: PricingEngine,
                 orders: OrdersEngine):
        self.db = db
        self.wallet = wallet
        self.payments = payments
        self.rbac = rbac
        self.audit = audit
        self.notifications = notifications
        self.countries = countries
        self.services = services
        self.inventory = inventory
        self.pricing = pricing
        self.orders = orders
        self.token = Config.BOT_TOKEN
        self.app = self._build()

    # ══════════════════════════════════════════════════════
    #  AUTH HELPER
    # ══════════════════════════════════════════════════════
    def _auth(self, x_init_data: str) -> Optional[dict]:
        """يحقق المستخدم من X-Init-Data header"""
        v = WebAppAuth.verify(x_init_data, self.token)
        if not v or not v.get("user"):
            return None
        tg_id = int(v["user"].get("id", 0) or 0)
        if not tg_id:
            return None
        uid = self.db.user_upsert(
            tg_id,
            v["user"].get("username") or "",
            v["user"].get("first_name") or "",
            v["user"].get("last_name") or "",
        )
        return self.db.user_get(uid)

    def _require_admin(self, user: dict, perm: str = None) -> None:
        """يتحقق أن المستخدم إداري + عنده صلاحية"""
        if not user:
            raise HTTPException(401, "غير مصرح")
        if user.get("status") == "blocked":
            raise HTTPException(403, "محظور")
        if not self.rbac.is_admin(user["id"]):
            raise HTTPException(403, "للمشرفين فقط")
        if perm and not self.rbac.has_permission(user["id"], perm):
            raise HTTPException(403, f"تحتاج صلاحية: {perm}")

    def _current(self, x_init_data: str = Header(None, alias="X-Init-Data")) -> dict:
        user = self._auth(x_init_data or "")
        if not user:
            raise HTTPException(401, "غير مصرح")
        return user

    # ══════════════════════════════════════════════════════
    #  APP
    # ══════════════════════════════════════════════════════
    def _build(self) -> FastAPI:
        app = FastAPI(title="MTR NUMBERS API", version=Config.VERSION,
                      docs_url=None, redoc_url=None)

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # ─────────── Root / Health ───────────
        @app.get("/", response_class=HTMLResponse)
        @app.get("/webapp", response_class=HTMLResponse)
        async def root():
            html = WEBAPP_HTML.replace("__CSS__", WEBAPP_CSS).replace("__JS__", WEBAPP_JS)
            return HTMLResponse(html)

        @app.get("/health")
        async def health():
            return {"ok": True, "v": Config.VERSION, "ts": time.time()}

        # ─────────── /api/me ───────────
        @app.get("/api/me")
        async def api_me(user: dict = Depends(self._current)):
            role = None
            if user.get("role_id"):
                role = self.rbac.get_role(user["role_id"])
            return {
                "user": {
                    "id": user["id"],
                    "tg_id": user["tg_id"],
                    "first_name": user.get("first_name"),
                    "username": user.get("username"),
                    "balance": user.get("balance", 0),
                    "is_owner": self.rbac.is_owner(user["id"]),
                    "role_name": role["name_ar"] if role else None,
                }
            }

        # ─────────── DASHBOARD ───────────
        @app.get("/api/dashboard")
        async def api_dashboard(range: str = "today",
                                user: dict = Depends(self._current)):
            self._require_admin(user, "users.view")
            stats = self.db.stats_overview()

            # Chart — بيانات آخر 7 أيام
            with self.db._lock, self.db._conn() as c:
                rows = c.execute("""
                    SELECT DATE(created_at) AS d, COUNT(*) AS n
                    FROM orders
                    WHERE created_at >= datetime('now', '-7 days')
                    GROUP BY DATE(created_at)
                    ORDER BY d ASC
                """).fetchall()
                chart = [{"label": r["d"], "value": r["n"]} for r in rows]

                # Top countries
                tc = c.execute("""
                    SELECT co.name_ar AS name, COUNT(*) AS count
                    FROM orders o
                    LEFT JOIN countries co ON co.id=o.country_id
                    GROUP BY o.country_id
                    ORDER BY count DESC LIMIT 5
                """).fetchall()
                top_countries = [dict(r) for r in tc]

            providers = self.db.provider_list()

            return {
                "stats": stats,
                "chart": chart,
                "top_countries": top_countries,
                "providers": providers[:6],
            }

        # ─────────── USERS ───────────
        @app.get("/api/users")
        async def api_users(search: str = "", user: dict = Depends(self._current)):
            self._require_admin(user, "users.view")
            users = self.db.user_list(limit=100, search=search or None)
            # أضف عدد الطلبات لكل مستخدم
            with self.db._lock, self.db._conn() as c:
                for u in users:
                    r = c.execute("SELECT COUNT(*) AS n FROM orders WHERE user_id=?",
                                  (u["id"],)).fetchone()
                    u["orders_count"] = r["n"]
            return {"users": users}

        @app.get("/api/user")
        async def api_user(id: int, user: dict = Depends(self._current)):
            self._require_admin(user, "users.view")
            u = self.db.user_get(id)
            if not u:
                raise HTTPException(404, "غير موجود")
            return {"user": u}

        @app.post("/api/user/toggle-block")
        async def api_toggle_block(req: Request,
                                    user: dict = Depends(self._current)):
            self._require_admin(user, "users.block")
            body = await req.json()
            uid = safe_int(body.get("user_id"))
            target = self.db.user_get(uid)
            if not target:
                raise HTTPException(404, "المستخدم غير موجود")
            new_status = "active" if target["status"] == "blocked" else "blocked"
            self.db.user_set_status(uid, new_status)
            self.audit.log(user["id"], user.get("first_name") or "admin",
                            "user.toggle_block", "user", uid,
                            before={"status": target["status"]},
                            after={"status": new_status})
            return {"ok": True, "status": new_status}

        # ─────────── ORDERS ───────────
        @app.get("/api/orders")
        async def api_orders(status: str = "",
                             user: dict = Depends(self._current)):
            self._require_admin(user, "orders.view")
            orders = self.orders.list_all(status=status or None, limit=100)
            return {"orders": orders}

        # ─────────── INVENTORY ───────────
        @app.get("/api/inventory")
        async def api_inventory(status: str = "",
                                user: dict = Depends(self._current)):
            self._require_admin(user, "inventory.view")
            items = self.inventory.list(status=status or None, limit=100)
            return {"items": items}

        @app.post("/api/inventory/import")
        async def api_inventory_import(req: Request,
                                        user: dict = Depends(self._current)):
            self._require_admin(user, "inventory.import")
            body = await req.json()
            text = str(body.get("text", ""))
            country_id = safe_int(body.get("country_id"))
            service_id = safe_int(body.get("service_id"))
            if not text or not country_id or not service_id:
                raise HTTPException(400, "بيانات ناقصة")

            result = self.inventory.import_from_text(
                text, country_id, service_id,
                provider_id=None, cost=0.0, fmt="auto"
            )
            self.audit.log(user["id"], user.get("first_name") or "admin",
                            "inventory.import", "inventory", None,
                            after=result)
            return result

        # ─────────── PROVIDERS ───────────
        @app.get("/api/providers")
        async def api_providers(user: dict = Depends(self._current)):
            self._require_admin(user, "providers.view")
            return {"providers": self.db.provider_list()}

        @app.post("/api/provider/ping")
        async def api_provider_ping(req: Request,
                                     user: dict = Depends(self._current)):
            self._require_admin(user, "providers.view")
            body = await req.json()
            pid = safe_int(body.get("provider_id"))
            p = self.db.provider_get(pid)
            if not p:
                raise HTTPException(404, "المزود غير موجود")

            t0 = time.time()
            try:
                adapter = AdapterRegistry.create(p)
                adapter.get_balance()
                latency = int((time.time() - t0) * 1000)
                self.db.provider_update_health(pid, latency, success=True)
                return {"ok": True, "latency": latency}
            except Exception as e:
                latency = int((time.time() - t0) * 1000)
                self.db.provider_update_health(pid, latency, success=False)
                return {"ok": False, "error": str(e)[:200], "latency": latency}

        # ─────────── COUNTRIES ───────────
        @app.get("/api/countries")
        async def api_countries(user: dict = Depends(self._current)):
            self._require_admin(user, "settings.view")
            return {"countries": self.countries.list_all()}

        # ─────────── SERVICES ───────────
        @app.get("/api/services")
        async def api_services(user: dict = Depends(self._current)):
            self._require_admin(user, "settings.view")
            return {"services": self.services.list_all()}

        # ─────────── WALLET ───────────
        @app.get("/api/wallet/overview")
        async def api_wallet_overview(user: dict = Depends(self._current)):
            self._require_admin(user, "finance.view")
            with self.db._lock, self.db._conn() as c:
                totals = c.execute("""
                    SELECT
                        (SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='deposit') AS total_deposited,
                        (SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='purchase') AS total_spent,
                        (SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='refund') AS total_refunded
                """).fetchone()
            payments = self.payments.list(limit=50)
            return {
                "total_deposited": abs(totals["total_deposited"] or 0),
                "total_spent": abs(totals["total_spent"] or 0),
                "total_refunded": abs(totals["total_refunded"] or 0),
                "payments": payments,
            }

        @app.post("/api/wallet/verify-payment")
        async def api_verify_payment(req: Request,
                                      user: dict = Depends(self._current)):
            self._require_admin(user, "finance.view")
            body = await req.json()
            pid = safe_int(body.get("payment_id"))
            approve = bool(body.get("approve"))

            if approve:
                result = self.payments.verify(pid, user["id"])
            else:
                ok = self.payments.reject(pid, user["id"], reason="رفض إداري")
                result = {"ok": ok}

            self.audit.log(user["id"], user.get("first_name") or "admin",
                            "payment.verify" if approve else "payment.reject",
                            "payment", pid,
                            after={"approve": approve})
            return result

        # ─────────── PRICING ───────────
        @app.get("/api/prices")
        async def api_prices(user: dict = Depends(self._current)):
            self._require_admin(user, "settings.view")
            return {"prices": self.pricing.list_all()}

        # ─────────── AUDIT ───────────
        @app.get("/api/audit")
        async def api_audit(user: dict = Depends(self._current)):
            self._require_admin(user, "audit.view")
            return {"logs": self.audit.list(limit=100)}

        # ─────────── SETTINGS ───────────
        @app.get("/api/settings")
        async def api_settings(user: dict = Depends(self._current)):
            self._require_admin(user, "settings.view")
            return {"settings": self.db.setting_list()}

        @app.post("/api/settings/save")
        async def api_settings_save(req: Request,
                                     user: dict = Depends(self._current)):
            self._require_admin(user, "settings.edit")
            body = await req.json()
            key = str(body.get("key", ""))[:80]
            value = str(body.get("value", ""))[:2000]
            if not key:
                raise HTTPException(400, "key مطلوب")

            old = self.db.setting_get(key, "")
            self.db.setting_set(key, value)
            self.audit.log(user["id"], user.get("first_name") or "admin",
                            "settings.change", "setting", None,
                            before={"key": key, "value": old},
                            after={"key": key, "value": value})
            return {"ok": True}

        # ─────────── NOTIFICATIONS ───────────
        @app.get("/api/notifications")
        async def api_notifications(user: dict = Depends(self._current)):
            self._require_admin(user, "settings.view")
            return {"notifications": self.notifications.list_for_role(limit=30)}

        @app.get("/api/notifications/count")
        async def api_notifications_count(user: dict = Depends(self._current)):
            self._require_admin(user, "settings.view")
            return {"unread": self.notifications.count_unread()}

        # ─────────── ERROR HANDLER ───────────
        @app.exception_handler(Exception)
        async def generic_error(request: Request, exc: Exception):
            log.error(f"[API] {exc}\n{traceback.format_exc()}")
            return JSONResponse(
                {"ok": False, "error": "خطأ في السيرفر"},
                status_code=500,
            )

        return app

    # ══════════════════════════════════════════════════════
    #  RUN
    # ══════════════════════════════════════════════════════
    def run_in_thread(self) -> threading.Thread:
        def _run():
            try:
                uvicorn.run(
                    self.app,
                    host=Config.WEB_HOST,
                    port=Config.WEB_PORT,
                    log_level="warning",
                    access_log=False,
                )
            except Exception as e:
                log.error(f"[Server] crashed: {e}")

        t = threading.Thread(target=_run, name="web", daemon=True)
        t.start()
        log.info(f"[✓] Web Server: http://{Config.WEB_HOST}:{Config.WEB_PORT}")
        return t


# ══════════════════════════════════════════════════════════════
#  ▓▓▓ نهاية الجزء 12 ▓▓▓
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  TELEGRAM BOT — aiogram 3.31
#  مع ألوان حقيقية: primary 🔵 / success 🟢 / danger 🔴
# ══════════════════════════════════════════════════════════════
class BotApp:
    """بوت تلجرام — واجهة المستخدم"""

    def __init__(self, db: DB, wallet: Wallet, payments: Payments,
                 countries: CountryManager, services: ServiceManager,
                 inventory: InventoryManager, pricing: PricingEngine,
                 orders: OrdersEngine, rbac: RBAC, notifications: Notifications,
                 rate: RateLimiter):
        self.db = db
        self.wallet = wallet
        self.payments = payments
        self.countries = countries
        self.services = services
        self.inventory = inventory
        self.pricing = pricing
        self.orders = orders
        self.rbac = rbac
        self.notifications = notifications
        self.rate = rate

        self.bot = Bot(
            token=Config.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self.dp = Dispatcher()
        self.router = Router()
        self.dp.include_router(self.router)

        self.sessions: dict[int, dict] = {}
        self._lock = threading.Lock()

        self.bot_username = ""
        self._register()

    # ══════════════════════════════════════════════════════
    #  SESSIONS
    # ══════════════════════════════════════════════════════
    def _sess(self, uid: int) -> dict:
        with self._lock:
            return self.sessions.setdefault(uid, {})

    def _clear(self, uid: int) -> None:
        with self._lock:
            self.sessions.pop(uid, None)

    def _rate_ok(self, uid: int) -> bool:
        return self.rate.allow(f"tg:{uid}")

    async def _get_user(self, tg_user) -> dict:
        uid = self.db.user_upsert(
            tg_user.id,
            tg_user.username or "",
            tg_user.first_name or "",
            tg_user.last_name or "",
        )
        return self.db.user_get(uid)

    # ══════════════════════════════════════════════════════
    #  KEYBOARDS — بألوان حقيقية 🔵🟢🔴
    # ══════════════════════════════════════════════════════
    def _kb_main(self, webapp_url: str = "") -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        # 🔵 Primary
        kb.button(text="🛒 شراء رقم", callback_data="buy:start",
                  style=Config.BTN_PRIMARY)
        # 🔵 Primary
        kb.button(text="📦 طلباتي", callback_data="orders:list",
                  style=Config.BTN_PRIMARY)
        # 🟢 Success
        kb.button(text="💰 رصيدي", callback_data="wallet:show",
                  style=Config.BTN_SUCCESS)
        # 🟢 Success
        kb.button(text="➕ إيداع", callback_data="deposit:start",
                  style=Config.BTN_SUCCESS)
        # 🔵 Primary
        kb.button(text="💬 الدعم", callback_data="support:show",
                  style=Config.BTN_PRIMARY)
        # 🔵 Primary
        kb.button(text="⚙️ حسابي", callback_data="account:show",
                  style=Config.BTN_PRIMARY)

        if webapp_url and webapp_url.startswith("https://"):
            kb.button(text="🌐 المنصة",
                      web_app=WebAppInfo(url=webapp_url),
                      style=Config.BTN_PRIMARY)

        kb.adjust(2, 2, 2, 1)
        return kb.as_markup()

    def _kb_back(self, target: str = "menu:main") -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        kb.button(text="🔙 رجوع", callback_data=target, style=Config.BTN_PRIMARY)
        return kb.as_markup()

    def _kb_cancel_order(self, order_id: int) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        # 🔵 Primary — نسخ الرقم
        kb.button(text="📋 نسخ الرقم", callback_data=f"ord:copy:{order_id}",
                  style=Config.BTN_PRIMARY)
        # 🔵 Primary — تحديث
        kb.button(text="🔄 تحديث", callback_data=f"ord:refresh:{order_id}",
                  style=Config.BTN_PRIMARY)
        # 🔴 Danger — إلغاء
        kb.button(text="❌ إلغاء الطلب", callback_data=f"ord:cancel:{order_id}",
                  style=Config.BTN_DANGER)
        # 🔵 Primary — رجوع
        kb.button(text="🔙 القائمة", callback_data="menu:main",
                  style=Config.BTN_PRIMARY)
        kb.adjust(2, 1, 1)
        return kb.as_markup()

    def _kb_countries(self, countries_list: list) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        for c in countries_list[:20]:
            kb.button(
                text=f"{c['flag']} {c['name_ar']}",
                callback_data=f"buy:country:{c['id']}",
                style=Config.BTN_PRIMARY,  # 🔵
            )
        kb.button(text="🔙 رجوع", callback_data="menu:main",
                  style=Config.BTN_PRIMARY)
        kb.adjust(2)
        return kb.as_markup()

    def _kb_services(self, services_list: list, country_id: int) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        for s in services_list[:20]:
            kb.button(
                text=f"{s['name_ar']}",
                callback_data=f"buy:service:{country_id}:{s['id']}",
                style=Config.BTN_PRIMARY,
            )
        kb.button(text="🔙 رجوع", callback_data="buy:start",
                  style=Config.BTN_PRIMARY)
        kb.adjust(2)
        return kb.as_markup()

    def _kb_confirm_buy(self, country_id: int, service_id: int,
                        price: float) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        # 🟢 Success — تأكيد
        kb.button(text=f"✅ تأكيد الشراء ({money(price)})",
                  callback_data=f"buy:confirm:{country_id}:{service_id}",
                  style=Config.BTN_SUCCESS)
        # 🔴 Danger — إلغاء
        kb.button(text="❌ إلغاء", callback_data="menu:main",
                  style=Config.BTN_DANGER)
        kb.adjust(1, 1)
        return kb.as_markup()

    def _kb_deposit_methods(self) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        for method, label in [("usdt", "USDT"), ("vodafone", "Vodafone Cash"),
                                ("bank", "تحويل بنكي")]:
            kb.button(text=f"💳 {label}", callback_data=f"deposit:method:{method}",
                      style=Config.BTN_PRIMARY)
        kb.button(text="🔙 رجوع", callback_data="menu:main",
                  style=Config.BTN_PRIMARY)
        kb.adjust(1)
        return kb.as_markup()

    # ══════════════════════════════════════════════════════
    #  HANDLERS
    # ══════════════════════════════════════════════════════
    def _register(self):
        bot = self.bot
        router = self.router

        # ─── /start ────────────────────────────────────
        @router.message(CommandStart())
        async def cmd_start(m: Message):
            user = await self._get_user(m.from_user)
            self._clear(user["id"])

            text = (
                f"<b>🌐 {Config.BRAND_AR}</b>\n"
                f"<i>{Config.BRAND_EN}</i>\n\n"
                f"أهلاً <b>{m.from_user.first_name or 'صديقي'}</b> 👋\n\n"
                "منصة الأرقام الافتراضية و SMS.\n"
                "اختر رقمك المفضل واحصل عليه خلال ثواني.\n\n"
                "<blockquote>"
                "• أرقام من جميع الدول\n"
                "• تسليم فوري\n"
                "• أسعار تنافسية\n"
                "</blockquote>"
            )
            await m.answer(text, reply_markup=self._kb_main(Config.WEBAPP_URL))

        # ─── /help ─────────────────────────────────────
        @router.message(Command("help"))
        async def cmd_help(m: Message):
            text = (
                "<b>📚 المساعدة</b>\n\n"
                "<b>الأوامر:</b>\n"
                "• /start — القائمة\n"
                "• /buy — شراء رقم\n"
                "• /orders — طلباتي\n"
                "• /balance — رصيدي\n"
                "• /cancel — إلغاء العملية\n\n"
                "<b>كيف أشتري؟</b>\n"
                "1. اضغط 🛒 شراء رقم\n"
                "2. اختر الدولة\n"
                "3. اختر الخدمة\n"
                "4. تأكيد الشراء\n"
                "5. استلم الرقم وانتظر OTP"
            )
            await m.answer(text, reply_markup=self._kb_back())

        # ─── /cancel ───────────────────────────────────
        @router.message(Command("cancel"))
        async def cmd_cancel(m: Message):
            user = await self._get_user(m.from_user)
            self._clear(user["id"])
            await m.answer("✓ تم الإلغاء", reply_markup=self._kb_main(Config.WEBAPP_URL))

        # ─── /buy ──────────────────────────────────────
        @router.message(Command("buy"))
        async def cmd_buy(m: Message):
            await self._show_countries(m, await self._get_user(m.from_user))

        # ─── /orders ───────────────────────────────────
        @router.message(Command("orders"))
        async def cmd_orders(m: Message):
            await self._show_user_orders(m, await self._get_user(m.from_user))

        # ─── /balance ──────────────────────────────────
        @router.message(Command("balance"))
        async def cmd_balance(m: Message):
            await self._show_wallet(m, await self._get_user(m.from_user))

        # ─── Callback router ───────────────────────────
        @router.callback_query(F.data == "menu:main")
        async def cb_menu(c: CallbackQuery):
            user = await self._get_user(c.from_user)
            self._clear(user["id"])
            text = (
                f"<b>🌐 {Config.BRAND_AR}</b>\n\n"
                f"👋 أهلاً <b>{c.from_user.first_name or 'صديقي'}</b>\n\n"
                "اختر من القائمة:"
            )
            try:
                await c.message.edit_text(text,
                                          reply_markup=self._kb_main(Config.WEBAPP_URL))
            except TelegramBadRequest:
                await c.message.answer(text,
                                        reply_markup=self._kb_main(Config.WEBAPP_URL))
            await c.answer()

        # ─── BUY ───────────────────────────────────────
        @router.callback_query(F.data == "buy:start")
        async def cb_buy_start(c: CallbackQuery):
            user = await self._get_user(c.from_user)
            await self._show_countries(c, user, edit=True)

        @router.callback_query(F.data.startswith("buy:country:"))
        async def cb_buy_country(c: CallbackQuery):
            try:
                cid = int(c.data.split(":")[2])
            except (ValueError, IndexError):
                await c.answer("خطأ", show_alert=True)
                return
            await self._show_services(c, cid)

        @router.callback_query(F.data.startswith("buy:service:"))
        async def cb_buy_service(c: CallbackQuery):
            parts = c.data.split(":")
            try:
                cid = int(parts[2]); sid = int(parts[3])
            except (ValueError, IndexError):
                await c.answer("خطأ", show_alert=True)
                return
            await self._show_confirm(c, cid, sid)

        @router.callback_query(F.data.startswith("buy:confirm:"))
        async def cb_buy_confirm(c: CallbackQuery):
            parts = c.data.split(":")
            try:
                cid = int(parts[2]); sid = int(parts[3])
            except (ValueError, IndexError):
                await c.answer("خطأ", show_alert=True)
                return
            await self._do_buy(c, cid, sid)

        # ─── ORDERS ────────────────────────────────────
        @router.callback_query(F.data == "orders:list")
        async def cb_orders_list(c: CallbackQuery):
            user = await self._get_user(c.from_user)
            await self._show_user_orders(c, user, edit=True)

        @router.callback_query(F.data.startswith("ord:copy:"))
        async def cb_ord_copy(c: CallbackQuery):
            try:
                oid = int(c.data.split(":")[2])
            except (ValueError, IndexError):
                await c.answer()
                return
            o = self.orders.get(oid)
            if not o:
                await c.answer("غير موجود", show_alert=True)
                return
            await c.answer(f"رقمك: {o['number']}", show_alert=True)

        @router.callback_query(F.data.startswith("ord:refresh:"))
        async def cb_ord_refresh(c: CallbackQuery):
            try:
                oid = int(c.data.split(":")[2])
            except (ValueError, IndexError):
                await c.answer()
                return
            o = self.orders.get(oid)
            if not o:
                await c.answer("غير موجود", show_alert=True)
                return
            if o["otp_code"]:
                await c.answer(f"✅ OTP: {o['otp_code']}", show_alert=True)
            else:
                await c.answer("⏳ لم يصل OTP بعد", show_alert=True)

        @router.callback_query(F.data.startswith("ord:cancel:"))
        async def cb_ord_cancel(c: CallbackQuery):
            try:
                oid = int(c.data.split(":")[2])
            except (ValueError, IndexError):
                await c.answer()
                return
            user = await self._get_user(c.from_user)
            o = self.orders.get(oid)
            if not o or o["user_id"] != user["id"]:
                await c.answer("غير مصرح", show_alert=True)
                return
            try:
                result = self.orders.cancel(oid, by_user=True, reason="إلغاء المستخدم")
                await c.answer("✓ تم الإلغاء والاسترجاع")
                await self._show_user_orders(c, user, edit=True)
            except OrderError as e:
                await c.answer(f"❌ {e}", show_alert=True)

        # ─── WALLET ────────────────────────────────────
        @router.callback_query(F.data == "wallet:show")
        async def cb_wallet(c: CallbackQuery):
            user = await self._get_user(c.from_user)
            await self._show_wallet(c, user, edit=True)

        # ─── DEPOSIT ───────────────────────────────────
        @router.callback_query(F.data == "deposit:start")
        async def cb_deposit_start(c: CallbackQuery):
            user = await self._get_user(c.from_user)
            self._sess(user["id"])["await"] = "deposit_amount"
            text = (
                "<b>➕ إيداع رصيد</b>\n\n"
                f"الحد الأدنى: <b>{money(Config.MIN_DEPOSIT)}</b>\n\n"
                "أرسل المبلغ الذي تريد إيداعه (مثال: <code>10</code>)"
            )
            try:
                await c.message.edit_text(text, reply_markup=self._kb_back())
            except TelegramBadRequest:
                await c.message.answer(text, reply_markup=self._kb_back())
            await c.answer()

        @router.callback_query(F.data.startswith("deposit:method:"))
        async def cb_deposit_method(c: CallbackQuery):
            method = c.data.split(":")[2]
            user = await self._get_user(c.from_user)
            sess = self._sess(user["id"])
            amount = sess.get("deposit_amount", 0)
            if amount <= 0:
                await c.answer("المبلغ غير صالح", show_alert=True)
                return
            pay = self.payments.create_request(user["id"], amount, method=method,
                                                note=f"إيداع عبر {method}")
            self._clear(user["id"])

            text = (
                f"<b>✅ تم إنشاء طلب الإيداع</b>\n\n"
                f"<blockquote>"
                f"📌 رقم الطلب: <code>{pay['code']}</code>\n"
                f"💰 المبلغ: <b>{money(amount)}</b>\n"
                f"💳 الطريقة: <b>{method}</b>\n"
                f"⏳ الحالة: <b>في انتظار المراجعة</b>\n"
                f"</blockquote>\n\n"
                "سيتم إشعارك بعد الموافقة."
            )
            try:
                await c.message.edit_text(text, reply_markup=self._kb_back())
            except TelegramBadRequest:
                await c.message.answer(text, reply_markup=self._kb_back())
            await c.answer()

        # ─── SUPPORT / ACCOUNT ─────────────────────────
        @router.callback_query(F.data == "support:show")
        async def cb_support(c: CallbackQuery):
            text = (
                "<b>💬 الدعم الفني</b>\n\n"
                "للاستفسارات والمشاكل:\n"
                f"👤 Owner: <code>{Config.OWNER_ID}</code>\n\n"
                "<i>سيتم الرد خلال 24 ساعة</i>"
            )
            try:
                await c.message.edit_text(text, reply_markup=self._kb_back())
            except TelegramBadRequest:
                await c.message.answer(text, reply_markup=self._kb_back())
            await c.answer()

        @router.callback_query(F.data == "account:show")
        async def cb_account(c: CallbackQuery):
            user = await self._get_user(c.from_user)
            role = None
            if user.get("role_id"):
                role = self.rbac.get_role(user["role_id"])
            text = (
                f"<b>⚙️ حسابي</b>\n\n"
                f"<blockquote>"
                f"🆔 ID: <code>{user['id']}</code>\n"
                f"👤 الاسم: <b>{user.get('first_name') or '—'}</b>\n"
                f"📛 Username: @{user.get('username') or '—'}\n"
                f"💰 الرصيد: <b>{money(user.get('balance', 0))}</b>\n"
                f"📊 المشتريات: <b>{money(user.get('total_spent', 0))}</b>\n"
                f"👑 الدور: <b>{role['name_ar'] if role else 'مستخدم'}</b>\n"
                f"</blockquote>"
            )
            try:
                await c.message.edit_text(text, reply_markup=self._kb_back())
            except TelegramBadRequest:
                await c.message.answer(text, reply_markup=self._kb_back())
            await c.answer()

        # ─── TEXT HANDLER ──────────────────────────────
        @router.message(F.text & ~F.text.startswith("/"))
        async def on_text(m: Message):
            user = await self._get_user(m.from_user)
            sess = self._sess(user["id"])

            if sess.get("await") == "deposit_amount":
                await self._handle_deposit_amount(m, user, m.text)
                return

            await m.answer(
                "🤔 لم أفهم. اختر من القائمة:",
                reply_markup=self._kb_main(Config.WEBAPP_URL),
            )

    # ══════════════════════════════════════════════════════
    #  FLOW HANDLERS
    # ══════════════════════════════════════════════════════
    async def _show_countries(self, event, user, edit: bool = False):
        countries = self.countries.list_all("active")
        # فلتر — فقط الدول اللي فيها أرقام
        with self.db._lock, self.db._conn() as c:
            rows = c.execute("""SELECT DISTINCT country_id FROM inventory
                                WHERE status='available'""").fetchall()
            available_ids = {r["country_id"] for r in rows}
        countries = [c for c in countries if c["id"] in available_ids]

        if not countries:
            text = "⚠️ لا يوجد أرقام متاحة حالياً."
            if edit:
                try:
                    await event.message.edit_text(text, reply_markup=self._kb_back())
                    return
                except TelegramBadRequest:
                    pass
            await event.message.answer(text, reply_markup=self._kb_back())
            return

        text = (
            "<b>🛒 شراء رقم</b>\n\n"
            "اختر الدولة:"
        )
        kb = self._kb_countries(countries)
        if edit:
            try:
                await event.message.edit_text(text, reply_markup=kb)
                await event.answer()
                return
            except TelegramBadRequest:
                pass
        await event.message.answer(text, reply_markup=kb)
        if not edit and hasattr(event, "answer"):
            try:
                await event.answer()
            except Exception:
                pass

    async def _show_services(self, c: CallbackQuery, country_id: int):
        country = self.countries.get(country_id)
        if not country:
            await c.answer("دولة غير موجودة", show_alert=True)
            return
        # الخدمات المتوفرة لهذه الدولة
        with self.db._lock, self.db._conn() as conn:
            rows = conn.execute("""SELECT DISTINCT service_id FROM inventory
                                    WHERE country_id=? AND status='available'""",
                                (country_id,)).fetchall()
            service_ids = [r["service_id"] for r in rows]
        all_services = {s["id"]: s for s in self.services.list_all("active")}
        services_list = [all_services[sid] for sid in service_ids if sid in all_services]

        if not services_list:
            await c.answer("لا خدمات متاحة لهذه الدولة", show_alert=True)
            return

        text = (
            f"<b>{country['flag']} {country['name_ar']}</b>\n\n"
            "اختر الخدمة:"
        )
        try:
            await c.message.edit_text(text, reply_markup=self._kb_services(services_list, country_id))
        except TelegramBadRequest:
            pass
        await c.answer()

    async def _show_confirm(self, c: CallbackQuery, country_id: int, service_id: int):
        country = self.countries.get(country_id)
        service = self.services.get(service_id)
        if not country or not service:
            await c.answer("خطأ", show_alert=True)
            return

        avail = self.inventory.available_count(country_id, service_id)
        price_info = self.pricing.compute(country_id, service_id)
        price = price_info["final_price"]

        user = await self._get_user(c.from_user)
        balance = user.get("balance", 0)

        text = (
            f"<b>🛒 تأكيد الشراء</b>\n\n"
            f"<blockquote>"
            f"🌍 الدولة: <b>{country['flag']} {country['name_ar']}</b>\n"
            f"💬 الخدمة: <b>{service['name_ar']}</b>\n"
            f"📦 المتاح: <b>{avail}</b>\n"
            f"💵 السعر: <b>{money(price)}</b>\n"
            f"💰 رصيدك: <b>{money(balance)}</b>\n"
            f"</blockquote>\n\n"
        )
        if balance < price:
            text += f"⚠️ <b>رصيدك غير كافٍ!</b>\nتحتاج {money(price - balance)} إضافية."
            kb = InlineKeyboardBuilder()
            kb.button(text="➕ إيداع", callback_data="deposit:start",
                      style=Config.BTN_SUCCESS)
            kb.button(text="🔙 رجوع", callback_data="menu:main",
                      style=Config.BTN_PRIMARY)
            kb.adjust(1, 1)
            try:
                await c.message.edit_text(text, reply_markup=kb.as_markup())
            except TelegramBadRequest:
                pass
        else:
            try:
                await c.message.edit_text(text,
                                          reply_markup=self._kb_confirm_buy(country_id, service_id, price))
            except TelegramBadRequest:
                pass
        await c.answer()

    async def _do_buy(self, c: CallbackQuery, country_id: int, service_id: int):
        user = await self._get_user(c.from_user)
        if not self._rate_ok(user["id"]):
            await c.answer("⏳ تمهّل", show_alert=True)
            return

        await c.answer("⏳ جارٍ الشراء...")

        # idempotency — مفتاح فريد
        idemp = f"tg:{user['id']}:{country_id}:{service_id}:{int(time.time())}"

        try:
            order = self.orders.create(user["id"], country_id, service_id,
                                        idempotency_key=idemp)
        except OrderError as e:
            await c.message.answer(f"❌ <b>فشل الشراء</b>\n\n{e}",
                                    reply_markup=self._kb_back())
            return
        except Exception as e:
            log.error(f"[Bot] buy error: {e}")
            await c.message.answer("❌ حدث خطأ غير متوقع")
            return

        text = (
            f"✅ <b>تم الشراء بنجاح!</b>\n\n"
            f"<blockquote>"
            f"🆔 الطلب: <code>{order['order_code']}</code>\n"
            f"📞 الرقم: <code>{order['number']}</code>\n"
            f"💵 السعر: <b>{money(order['sell_price'])}</b>\n"
            f"⏳ الحالة: <b>في انتظار OTP</b>\n"
            f"</blockquote>\n\n"
            "📲 <i>أرسل الكود على هذا الرقم، وسيصلك هنا فوراً.</i>\n"
            f"⏱️ ينتهي الطلب بعد {Config.ORDER_TIMEOUT_MIN} دقيقة."
        )
        await c.message.answer(text, reply_markup=self._kb_cancel_order(order["id"]))

    async def _show_user_orders(self, event, user, edit: bool = False):
        orders = self.orders.get_user_orders(user["id"], limit=5)
        if not orders:
            text = (
                "<b>📦 طلباتي</b>\n\n"
                "لا يوجد طلبات بعد.\n"
                "ابدأ بشراء أول رقم!"
            )
            kb = InlineKeyboardBuilder()
            kb.button(text="🛒 شراء رقم", callback_data="buy:start",
                      style=Config.BTN_PRIMARY)
            kb.button(text="🔙 رجوع", callback_data="menu:main",
                      style=Config.BTN_PRIMARY)
            kb.adjust(1, 1)
            if edit:
                try:
                    await event.message.edit_text(text, reply_markup=kb.as_markup())
                    await event.answer()
                    return
                except TelegramBadRequest:
                    pass
            await event.message.answer(text, reply_markup=kb.as_markup())
            if not edit:
                try: await event.answer()
                except: pass
            return

        status_map = {
            "pending": "⏳ معلق", "waiting": "⏳ في انتظار OTP",
            "completed": "✅ مكتمل", "cancelled": "❌ ملغى",
            "failed": "❌ فشل", "refunded": "💸 مسترجع", "expired": "⌛ منتهي",
        }

        lines = ["<b>📦 آخر طلباتك</b>\n"]
        for o in orders:
            st = status_map.get(o["status"], o["status"])
            otp = f" | OTP: <code>{o['otp_code']}</code>" if o.get("otp_code") else ""
            lines.append(
                f"<blockquote>"
                f"🆔 <code>{o['order_code']}</code>\n"
                f"📞 <code>{o['number']}</code>{otp}\n"
                f"🌍 {o.get('country_name', '—')} | 💬 {o.get('service_name', '—')}\n"
                f"💰 {money(o['sell_price'])} | {st}\n"
                f"</blockquote>"
            )

        kb = InlineKeyboardBuilder()
        kb.button(text="🛒 شراء جديد", callback_data="buy:start",
                  style=Config.BTN_PRIMARY)
        kb.button(text="🔙 رجوع", callback_data="menu:main",
                  style=Config.BTN_PRIMARY)
        kb.adjust(1, 1)

        text = "\n".join(lines)
        if edit:
            try:
                await event.message.edit_text(text, reply_markup=kb.as_markup())
                await event.answer()
                return
            except TelegramBadRequest:
                pass
        await event.message.answer(text, reply_markup=kb.as_markup())
        if not edit:
            try: await event.answer()
            except: pass

    async def _show_wallet(self, event, user, edit: bool = False):
        stats = self.wallet.stats(user["id"])
        text = (
            f"<b>💰 محفظتي</b>\n\n"
            f"<blockquote>"
            f"💵 الرصيد الحالي: <b>{money(stats['balance'])}</b>\n"
            f"📥 إجمالي الإيداعات: <b>{money(stats['deposited'])}</b>\n"
            f"📤 إجمالي المشتريات: <b>{money(stats['spent'])}</b>\n"
            f"💸 إجمالي الاسترجاعات: <b>{money(stats['refunded'])}</b>\n"
            f"</blockquote>"
        )
        kb = InlineKeyboardBuilder()
        kb.button(text="➕ إيداع", callback_data="deposit:start",
                  style=Config.BTN_SUCCESS)
        kb.button(text="📋 السجل", callback_data="wallet:history",
                  style=Config.BTN_PRIMARY)
        kb.button(text="🔙 رجوع", callback_data="menu:main",
                  style=Config.BTN_PRIMARY)
        kb.adjust(2, 1)

        if edit:
            try:
                await event.message.edit_text(text, reply_markup=kb.as_markup())
                await event.answer()
                return
            except TelegramBadRequest:
                pass
        await event.message.answer(text, reply_markup=kb.as_markup())
        if not edit:
            try: await event.answer()
            except: pass

    async def _handle_deposit_amount(self, m: Message, user: dict, text: str):
        try:
            amount = float(text.strip())
        except ValueError:
            await m.answer("❌ رقم غير صالح. أرسل مبلغاً رقمياً.")
            return

        if amount < Config.MIN_DEPOSIT:
            await m.answer(f"❌ الحد الأدنى {money(Config.MIN_DEPOSIT)}")
            return
        if amount > Config.MAX_ORDER_AMOUNT:
            await m.answer(f"❌ الحد الأقصى {money(Config.MAX_ORDER_AMOUNT)}")
            return

        self._sess(user["id"])["deposit_amount"] = amount
        text = (
            f"<b>💳 اختر طريقة الدفع</b>\n\n"
            f"المبلغ: <b>{money(amount)}</b>\n\n"
            "اختر الطريقة:"
        )
        await m.answer(text, reply_markup=self._kb_deposit_methods())

    # ══════════════════════════════════════════════════════
    #  RUN
    # ══════════════════════════════════════════════════════
    async def _setup(self):
        try:
            me = await self.bot.get_me()
            self.bot_username = me.username or ""
            log.info(f"[Bot] @{self.bot_username} ready")
        except Exception as e:
            log.error(f"[Bot] get_me: {e}")

        try:
            await self.bot.delete_webhook(drop_pending_updates=True)
        except Exception:
            pass

    async def run_async(self):
        await self._setup()
        log.info("[Bot] Starting polling...")
        await self.dp.start_polling(
            self.bot,
            allowed_updates=["message", "callback_query"],
        )

    def run(self):
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            log.info("[Bot] stopped")
        except Exception as e:
            log.error(f"[Bot] crashed: {e}\n{traceback.format_exc()}")


# ══════════════════════════════════════════════════════════════
#  ▓▓▓ نهاية الجزء 13 ▓▓▓
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  CLOUDFLARE TUNNEL — رابط HTTPS للـ WebApp
# ══════════════════════════════════════════════════════════════
class Tunnel:
    """يشغّل Cloudflare Quick Tunnel للحصول على HTTPS"""

    _proc = None
    _url = ""

    @classmethod
    def _asset(cls):
        import platform
        m = platform.machine().lower()
        if m in ("aarch64", "arm64"): return "cloudflared-linux-arm64"
        if m in ("x86_64", "amd64"):  return "cloudflared-linux-amd64"
        if m in ("armv7l", "armv7", "arm"): return "cloudflared-linux-arm"
        if m in ("i386", "i686", "x86"): return "cloudflared-linux-386"
        return None

    @classmethod
    def ensure(cls):
        exe = shutil.which("cloudflared")
        if exe: return exe
        asset = cls._asset()
        if not asset: return None
        cache = Config.BASE_DIR / ".cache"
        cache.mkdir(parents=True, exist_ok=True)
        target = cache / "cloudflared"
        if target.is_file() and os.access(str(target), os.X_OK):
            return str(target)
        url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/{asset}"
        try:
            log.info("[Tunnel] Downloading cloudflared...")
            urllib.request.urlretrieve(url, str(target))
            target.chmod(0o755)
            if target.is_file() and os.access(str(target), os.X_OK):
                log.info("[Tunnel] cloudflared ready")
                return str(target)
        except Exception as e:
            log.warning(f"[Tunnel] download: {e}")
        return None

    @classmethod
    def start(cls, port: int) -> Optional[str]:
        if Config.WEBAPP_URL.startswith("https://"):
            return Config.WEBAPP_URL
        exe = cls.ensure()
        if not exe:
            log.warning("[Tunnel] cloudflared غير متوفر")
            return None
        try:
            cls._proc = subprocess.Popen(
                [exe, "tunnel", "--url", f"http://127.0.0.1:{port}", "--no-autoupdate"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, encoding="utf-8", errors="replace",
            )
            deadline = time.time() + 40
            pat = re.compile(r"https://[-a-zA-Z0-9]+\.trycloudflare\.com")
            while time.time() < deadline:
                if cls._proc.poll() is not None:
                    break
                line = cls._proc.stdout.readline() if cls._proc.stdout else ""
                if not line:
                    time.sleep(0.1)
                    continue
                m = pat.search(line)
                if m:
                    cls._url = m.group(0)
                    log.info(f"[Tunnel] URL: {cls._url}")
                    return cls._url
            log.warning("[Tunnel] لم يصل رابط")
            return None
        except Exception as e:
            log.warning(f"[Tunnel] start: {e}")
            return None

    @classmethod
    def stop(cls):
        if cls._proc and cls._proc.poll() is None:
            try:
                cls._proc.terminate()
                cls._proc.wait(timeout=5)
            except Exception:
                try: cls._proc.kill()
                except Exception: pass


# ══════════════════════════════════════════════════════════════
#  BACKGROUND WORKERS
# ══════════════════════════════════════════════════════════════
class Workers:
    """عمليات خلفية — تنظيف الطلبات المنتهية + مراقبة المزودين"""

    def __init__(self, orders: OrdersEngine, inventory: InventoryManager,
                 providers: DB, notifications: Notifications, db: DB):
        self.orders = orders
        self.inventory = inventory
        self.db = db
        self.notifications = notifications
        self._running = False
        self._threads: list[threading.Thread] = []

    def start(self):
        self._running = True
        self._threads = [
            threading.Thread(target=self._order_cleanup_loop,
                             name="worker-orders", daemon=True),
            threading.Thread(target=self._reservation_cleanup_loop,
                             name="worker-reservations", daemon=True),
            threading.Thread(target=self._provider_health_loop,
                             name="worker-health", daemon=True),
        ]
        for t in self._threads:
            t.start()
        log.info("[Workers] Started 3 background loops")

    def stop(self):
        self._running = False

    def _order_cleanup_loop(self):
        """كل دقيقة — يلغي الطلبات المنتهية"""
        while self._running:
            try:
                time.sleep(60)
                n = self.orders.cleanup_expired()
                if n > 0:
                    log.info(f"[Workers] cancelled {n} expired orders")
            except Exception as e:
                log.error(f"[Workers] orders cleanup: {e}")

    def _reservation_cleanup_loop(self):
        """كل دقيقتين — يفك الحجوزات المنتهية"""
        while self._running:
            try:
                time.sleep(120)
                n = self.inventory.cleanup_expired_reservations()
                if n > 0:
                    log.info(f"[Workers] released {n} reservations")
            except Exception as e:
                log.error(f"[Workers] reservations cleanup: {e}")

    def _provider_health_loop(self):
        """كل 5 دقائق — يفحص المزودين"""
        while self._running:
            try:
                time.sleep(300)
                providers = self.db.provider_list()
                for p in providers:
                    if p.get("status") != "active":
                        continue
                    t0 = time.time()
                    try:
                        adapter = AdapterRegistry.create(p)
                        adapter.get_balance()
                        latency = int((time.time() - t0) * 1000)
                        self.db.provider_update_health(p["id"], latency, success=True)
                    except Exception as e:
                        latency = int((time.time() - t0) * 1000)
                        self.db.provider_update_health(p["id"], latency, success=False)
                        log.warning(f"[Workers] provider {p['name']}: {str(e)[:80]}")
            except Exception as e:
                log.error(f"[Workers] health loop: {e}")


# ══════════════════════════════════════════════════════════════
#  APP — المنسّق الرئيسي
# ══════════════════════════════════════════════════════════════
class App:
    """يربط كل المكونات ويشغّلها"""

    def __init__(self):
        print("═" * 60)
        print(f"  🌐 {Config.BRAND_EN}")
        print(f"  {Config.BRAND_AR}")
        print(f"  v{Config.VERSION}")
        print("═" * 60)

        Config.validate()

        # ─── Database
        self.database = Database(Config.DB_PATH)
        self.db = DB(self.database)
        log.info("[✓] Database ready")

        # ─── Core Managers
        self.rbac = RBAC(self.db)
        self.audit = Audit(self.db)
        self.notifications = Notifications(self.db)
        self.countries = CountryManager(self.db)
        self.services = ServiceManager(self.db)
        self.inventory = InventoryManager(self.db)
        self.pricing = PricingEngine(self.db)
        self.wallet = Wallet(self.db)
        self.payments = Payments(self.db, self.wallet)
        self.orders = OrdersEngine(self.db, self.wallet, self.inventory, self.pricing)
        self.rate = RateLimiter()
        log.info("[✓] Core managers ready")

        # ─── Server
        self.server = Server(
            self.db, self.wallet, self.payments, self.rbac, self.audit,
            self.notifications, self.countries, self.services,
            self.inventory, self.pricing, self.orders,
        )
        log.info("[✓] Server configured")

        # ─── Workers
        self.workers = Workers(self.orders, self.inventory, self.db,
                                self.notifications, self.db)

        # ─── Bot (يُهيأ بعد Tunnel)
        self.bot: Optional[BotApp] = None

        # ─── Ensure owner exists
        if Config.OWNER_ID:
            owner_uid = self.db.user_upsert(Config.OWNER_ID, "", "Owner", "")
            owner = self.db.user_get(owner_uid)
            if owner and not owner.get("role_id"):
                owner_role = self.rbac.get_role_by_slug("owner")
                if owner_role:
                    self.db.user_set_role(owner_uid, owner_role["id"])
            log.info(f"[✓] Owner ensured (tg_id={Config.OWNER_ID})")

    def _banner(self):
        s = self.db.stats_overview()
        print()
        print("═" * 60)
        print(f"  🌐 {Config.BRAND_AR}")
        print(f"     {Config.BRAND_EN} — v{Config.VERSION}")
        print("═" * 60)
        print(f"  📁 DB:        {Config.DB_PATH.name}")
        print(f"  👥 Users:     {s['users']}")
        print(f"  📦 Orders:    {s['orders']}")
        print(f"  📞 Available: {s['inventory_avail']}")
        print(f"  🏢 Providers: {s['providers']}")
        print(f"  💵 Revenue:   {money(s['revenue'])}")
        print(f"  📈 Profit:    {money(s['profit'])}")
        print(f"  🌐 Web:       http://{Config.WEB_HOST}:{Config.WEB_PORT}")
        if Config.WEBAPP_URL:
            print(f"  🔗 WebApp:    {Config.WEBAPP_URL}")
        else:
            print(f"  ⚠️  WebApp:    local only")
        print(f"  🤖 Bot:       {Config.BOT_TOKEN[:12]}...")
        print(f"  👑 Owner:     {Config.OWNER_ID}")
        print("═" * 60)
        print()

    def run(self):
        # ─── 1. Web Server
        log.info("[→] Starting Web Server...")
        self.server.run_in_thread()
        time.sleep(2)

        # ─── 2. Tunnel
        log.info("[→] Starting Cloudflare Tunnel...")
        public_url = Tunnel.start(Config.WEB_PORT)
        if public_url:
            Config.WEBAPP_URL = f"{public_url}/webapp"
            log.info(f"[✓] WebApp URL: {Config.WEBAPP_URL}")
        else:
            log.warning("[!] لا رابط عام — WebApp محلي فقط")

        # ─── 3. Workers
        self.workers.start()

        # ─── 4. Bot
        try:
            self.bot = BotApp(
                self.db, self.wallet, self.payments,
                self.countries, self.services, self.inventory,
                self.pricing, self.orders, self.rbac,
                self.notifications, self.rate,
            )
            log.info("[✓] Bot ready")
        except Exception as e:
            log.error(f"[!] Bot init: {e}")
            log.error(traceback.format_exc())
            return

        # ─── 5. Banner
        self._banner()

        # ─── 6. Run (blocking)
        try:
            self.bot.run()
        except KeyboardInterrupt:
            log.info("\n[←] Ctrl+C")
        except Exception as e:
            log.error(f"[!] Bot crashed: {e}")
            log.error(traceback.format_exc())
        finally:
            self.shutdown()

    def shutdown(self):
        log.info("[←] Shutting down...")
        try: self.workers.stop()
        except Exception: pass
        try: Tunnel.stop()
        except Exception: pass
        log.info("[✓] Bye")


# ══════════════════════════════════════════════════════════════
#  HTTP SERVER — مطلوب لـ Render Web Service
# ══════════════════════════════════════════════════════════════
from http.server import HTTPServer, BaseHTTPRequestHandler


class _HealthHandler(BaseHTTPRequestHandler):
    """HTTP بسيط — يرضي Render ويخلي البوت شغال"""

    def do_GET(self):
        body = (
            f"<html><head><title>{Config.BRAND_EN}</title></head>"
            f"<body style='font-family:system-ui;background:#0a0e1a;color:#f1f5f9;"
            f"display:flex;align-items:center;justify-content:center;"
            f"height:100vh;margin:0'>"
            f"<div style='text-align:center'>"
            f"<h1 style='color:#3b82f6'>{Config.BRAND_AR}</h1>"
            f"<p>🤖 Bot is running 24/7 on Render</p>"
            f"<p style='color:#94a3b8;font-size:14px'>v{Config.VERSION}</p>"
            f"</div></body></html>"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, fmt, *args):
        # صامت — ما نطبع access logs
        pass


def _start_http_keepalive():
    """يشغّل HTTP server في thread — مطلوب لـ Render"""
    port = int(os.getenv("PORT", str(Config.WEB_PORT)))
    try:
        httpd = HTTPServer(("0.0.0.0", port), _HealthHandler)
        t = threading.Thread(target=httpd.serve_forever,
                              name="http-keepalive", daemon=True)
        t.start()
        log.info(f"[✓] HTTP keepalive on port {port}")
    except OSError as e:
        log.warning(f"[!] HTTP server: {e}")


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════
def main():
    # شغّل HTTP server أول شي — لـ Render
    _start_http_keepalive()

    try:
        app = App()
        app.run()
    except KeyboardInterrupt:
        print("\n[+] Stopped.")
    except Exception as e:
        log.error(f"[!] Fatal: {e}")
        log.error(traceback.format_exc())
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()


# ══════════════════════════════════════════════════════════════
#  ▓▓▓ نهاية الملف ▓▓▓
# ══════════════════════════════════════════════════════════════
