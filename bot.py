#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
المطري Bot  —  ملف واحد كامل (bot.py)
=====================================================================
تحليل ثابت (AST) وتخصيص آمن لمشاريع بوتات تيليجرام (.py / .zip) دون تشغيل أي كود للمستخدم.

المتطلبات (Python 3.11+):
    pip install "aiogram>=3.4" sqlalchemy aiosqlite pydantic-settings libcst
    # اختياري لدعم PostgreSQL:  pip install asyncpg
    #   DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname

متغيرات البيئة (.env):
    BOT_TOKEN=YOUR_TOKEN
    OWNER_ID=123456789
    DATABASE_URL=sqlite+aiosqlite:///matri.db

التشغيل:       python bot.py
الاختبار الذاتي: python bot.py --self-test

ملاحظات هندسية وقيود Telegram (موثّقة داخل الكود أيضًا):
  * لا يُنفَّذ كود المستخدم أبدًا: لا exec/eval/subprocess/os.system ولا استيراد للمشروع المرفوع.
  * ألوان الأزرار (أخضر/أحمر/أزرق) هنا "أنماط دلالية" تُخزَّن في قاعدة بيانات المشروع فقط؛
    Telegram لا يتيح تغيير لون خلفية InlineKeyboardButton.
  * إيموجي Unicode فقط؛ Custom Emoji لا يمكن وضعها في نص الأزرار/الرسائل العادية.
  * التعديل يتم عبر LibCST فقط. إن لم تكن مثبتة يعمل التحليل كاملًا ويُعطَّل التعديل (بدل تعديل خطر).
"""
from __future__ import annotations

import ast
import asyncio
import contextlib
import dataclasses
import hashlib
import html
import json
import logging
import logging.handlers
import os
import re
import secrets
import shutil
import stat
import sys
import tempfile
import time
import traceback
import zipfile
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

# ─────────────────────────────────────────────────────────────────────────────
# اعتماديات اختيارية: محمية حتى يعمل `--self-test` ويُبلغ عمّا ينقص بدل الانهيار
# ─────────────────────────────────────────────────────────────────────────────
MISSING_DEPS: list[str] = []

try:
    import libcst as cst
    from libcst.metadata import MetadataWrapper, PositionProvider

    HAVE_LIBCST = True
except Exception:  # pragma: no cover
    cst = None  # type: ignore[assignment]
    MetadataWrapper = PositionProvider = None  # type: ignore[assignment]
    HAVE_LIBCST = False

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    HAVE_PYDANTIC = True
except ImportError:  # pragma: no cover
    HAVE_PYDANTIC = False
    MISSING_DEPS.append("pydantic-settings")

    class BaseSettings:  # type: ignore[no-redef]
        pass

    def SettingsConfigDict(**kw: Any) -> dict:  # type: ignore[no-redef]
        return kw

try:
    from sqlalchemy import (
        BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text,
        UniqueConstraint, delete, event, func, select,
    )
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

    HAVE_SA = True
except ImportError:  # pragma: no cover
    HAVE_SA = False
    MISSING_DEPS.append("sqlalchemy")

    class DeclarativeBase:  # type: ignore[no-redef]
        pass

    class Mapped:  # type: ignore[no-redef]
        pass

    AsyncSession = Any  # type: ignore[misc,assignment]

    def mapped_column(*a: Any, **k: Any) -> None:  # type: ignore[no-redef]
        return None

    def ForeignKey(*a: Any, **k: Any) -> None:  # type: ignore[no-redef]
        return None

    def UniqueConstraint(*a: Any, **k: Any) -> None:  # type: ignore[no-redef]
        return None

    BigInteger = Boolean = DateTime = Float = Integer = String = Text = lambda *a, **k: None  # type: ignore

try:
    from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from aiogram.exceptions import (
        TelegramAPIError, TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter,
    )
    from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.types import (
        BotCommand as TgBotCommand, BotCommandScopeChat, CallbackQuery, ErrorEvent,
        FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message,
    )

    HAVE_AIOGRAM = True
except ImportError:  # pragma: no cover
    HAVE_AIOGRAM = False
    MISSING_DEPS.append("aiogram")

    class BaseMiddleware:  # type: ignore[no-redef]
        pass

    class StatesGroup:  # type: ignore[no-redef]
        pass

    class State:  # type: ignore[no-redef]
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

    class TelegramAPIError(Exception):  # type: ignore[no-redef]
        pass

    class TelegramBadRequest(TelegramAPIError):  # type: ignore[no-redef]
        pass

    class TelegramForbiddenError(TelegramAPIError):  # type: ignore[no-redef]
        pass

    class TelegramRetryAfter(TelegramAPIError):  # type: ignore[no-redef]
        retry_after = 1

    class Message:  # type: ignore[no-redef]
        pass

    class CallbackQuery:  # type: ignore[no-redef]
        pass

try:
    import importlib.util as _ilu

    if _ilu.find_spec("aiosqlite") is None:
        MISSING_DEPS.append("aiosqlite")
except Exception:  # pragma: no cover
    pass

# ─────────────────────────────────────────────────────────────────────────────
# ثوابت عامة
# ─────────────────────────────────────────────────────────────────────────────
APP_NAME = "المطري Bot"
APP_VERSION = "1.0.0"
MB = 1024 * 1024
BASE_DIR = Path(__file__).resolve().parent
log = logging.getLogger("matri")

# أنماط دلالية (Semantic Styles) — لا تغيّر لون أزرار Telegram (انظر ترويسة الملف)
COLOR_OPTIONS = [
    ("green", "🟢 أخضر", "success"),
    ("red", "🔴 أحمر", "danger"),
    ("blue", "🔵 أزرق", "primary"),
    ("none", "⚫ بدون", None),
]


def style_label(key: str) -> str:
    return next((label for k, label, _ in COLOR_OPTIONS if k == key), "⚫ بدون")


def style_semantic(key: str) -> Optional[str]:
    return next((sem for k, _, sem in COLOR_OPTIONS if k == key), None)


def is_valid_style(key: str) -> bool:
    return any(k == key for k, _, _ in COLOR_OPTIONS)


class Paths:
    """مجلدات وقت التشغيل (runtime) — الكود نفسه كله داخل bot.py."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.projects = root / "projects"
        self.backups = root / "backups"
        self.exports = root / "exports"
        self.logs = root / "logs"
        self.tmp = root / "tmp"

    def ensure(self) -> None:
        for p in (self.root, self.projects, self.backups, self.exports, self.logs, self.tmp):
            p.mkdir(parents=True, exist_ok=True)


PATHS = Paths(BASE_DIR / "data")

# ─────────────────────────────────────────────────────────────────────────────
# أدوات نصية / وقت
# ─────────────────────────────────────────────────────────────────────────────


def utcnow() -> datetime:
    """UTC ساذج (naive) ليتوافق مع SQLite."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def fmt_dt(dt: Optional[datetime]) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else "—"


def esc(value: Any) -> str:
    return html.escape(str(value), quote=False)


def clip(text: str, limit: int) -> str:
    text = str(text)
    return text if len(text) <= limit else text[: max(0, limit - 1)] + "…"


def clip_message(text: str, limit: int = 3900) -> str:
    """قصّ الرسالة عند نهاية سطر كامل كي لا تُقطع وسوم HTML."""
    if len(text) <= limit:
        return text
    cut = text.rfind("\n", 0, limit)
    return text[: cut if cut > 0 else limit] + "\n…"


def one_line(text: str, limit: int = 60) -> str:
    return clip(re.sub(r"\s+", " ", str(text)).strip(), limit)


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"


def new_ref_code() -> str:
    return secrets.token_hex(4)


def safe_filename(name: str, default: str = "project.py") -> str:
    base = Path(str(name).replace("\\", "/")).name
    base = re.sub(r"[^\w.\-\u0600-\u06FF]+", "_", base).strip("._")
    return base[:80] or default


# ─────────────────────────────────────────────────────────────────────────────
# Rate limiting (في الذاكرة، نافذة منزلقة)
# ─────────────────────────────────────────────────────────────────────────────
class RateLimiter:
    """(الحد الأقصى للطلبات، مدة النافذة بالثواني) لكل إجراء."""

    RULES: dict[str, tuple[int, int]] = {
        "global": (30, 10),
        "upload": (5, 300),
        "analysis": (10, 300),
        "edit": (20, 600),
        "export": (8, 300),
        "broadcast": (3, 3600),
        "support": (5, 3600),
    }

    def __init__(self) -> None:
        self._hits: dict[tuple[int, str], deque[float]] = defaultdict(deque)

    def check(self, user_id: int, action: str) -> int:
        """يسجّل محاولة ويُرجع 0 إن كانت مسموحة، وإلا عدد الثواني المتبقية للانتظار."""
        limit, window = self.RULES.get(action, (30, 10))
        now = time.monotonic()
        q = self._hits[(user_id, action)]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return max(1, int(window - (now - q[0])) + 1)
        q.append(now)
        return 0

    def purge(self) -> None:
        now = time.monotonic()
        for key in list(self._hits):
            window = self.RULES.get(key[1], (30, 10))[1]
            q = self._hits[key]
            while q and now - q[0] > window:
                q.popleft()
            if not q:
                del self._hits[key]


# ─────────────────────────────────────────────────────────────────────────────
# Pagination عام + Callback data منظمة
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Page:
    items: list
    page: int
    pages: int
    total: int


def page_bounds(total: int, page: int, per_page: int) -> tuple[int, int, int]:
    pages = max(1, -(-total // per_page))
    page = min(max(1, page), pages)
    return page, pages, (page - 1) * per_page


def paginate(items: Sequence[Any], page: int, per_page: int = 8) -> Page:
    page, pages, start = page_bounds(len(items), page, per_page)
    return Page(list(items[start:start + per_page]), page, pages, len(items))


def pagination_row(cb_fmt: str, page: int, pages: int) -> list[tuple[str, str]]:
    """⬅️ السابق | 📄 1/5 | التالي ➡️ — الزر لا يقود أبدًا إلى صفحة غير موجودة.
    cb_fmt مثل 'page:buttons:{page}:12'. عند الحدود يصبح الزر noop."""
    prev_cb = cb_fmt.format(page=page - 1) if page > 1 else "noop:first"
    next_cb = cb_fmt.format(page=page + 1) if page < pages else "noop:last"
    return [("⬅️ السابق", prev_cb), (f"📄 {page}/{pages}", "noop:page"), ("التالي ➡️", next_cb)]


CB_RE = re.compile(r"^[A-Za-z0-9_:\-]{1,64}$")


def parse_cb(data: Optional[str]) -> Optional[list[str]]:
    """Callback validation: يقبل فقط محارف آمنة وطولًا ≤ 64."""
    if not data or not CB_RE.match(data) or len(data.encode()) > 64:
        return None
    return data.split(":")


def to_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    return int(value) if isinstance(value, str) and re.fullmatch(r"-?\d{1,18}", value) else default


# ─────────────────────────────────────────────────────────────────────────────
# الإعدادات (Pydantic Settings) وحدود الرفع
# ─────────────────────────────────────────────────────────────────────────────
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    BOT_TOKEN: str
    OWNER_ID: int
    DATABASE_URL: str = "sqlite+aiosqlite:///matri.db"
    MAX_UPLOAD_MB: int = 10
    ZIP_MAX_FILES: int = 300
    ZIP_MAX_TOTAL_MB: int = 40
    ANALYSIS_WORKERS: int = 2
    LOG_LEVEL: str = "INFO"


@dataclass
class Limits:
    max_upload_bytes: int = 10 * MB
    zip_max_files: int = 300
    zip_max_entries: int = 3000
    zip_max_total_bytes: int = 40 * MB
    zip_max_file_bytes: int = 5 * MB
    zip_max_ratio: int = 200
    zip_max_depth: int = 12
    max_path_len: int = 200


TELEGRAM_DOWNLOAD_CAP = 20 * MB  # حد تنزيل الملفات عبر Bot API


def _fatal(message: str) -> None:
    print(f"\n❌ {message}\n", file=sys.stderr)
    raise SystemExit(2)


def load_settings() -> Settings:
    if not HAVE_PYDANTIC:
        _fatal("المكتبة pydantic-settings غير مثبتة.\nثبّت المتطلبات: pip install aiogram sqlalchemy aiosqlite pydantic-settings libcst")
    try:
        cfg = Settings()  # type: ignore[call-arg]
    except Exception as exc:
        names: list[str] = []
        errors = getattr(exc, "errors", None)
        if callable(errors):
            for err in errors():
                loc = err.get("loc") or ("?",)
                names.append(str(loc[0]))
        _fatal(
            "متغيرات البيئة ناقصة أو غير صالحة: " + (", ".join(names) or str(exc)) +
            "\nأنشئ ملف .env بجانب bot.py:\n  BOT_TOKEN=YOUR_TOKEN\n  OWNER_ID=123456789\n"
            "  DATABASE_URL=sqlite+aiosqlite:///matri.db"
        )
    if not re.fullmatch(r"\d{5,}:[A-Za-z0-9_-]{30,}", cfg.BOT_TOKEN.strip()):
        _fatal("BOT_TOKEN يبدو غير صالح. انسخه من @BotFather كما هو (مثال: 123456:ABC-DEF...).")
    if cfg.OWNER_ID <= 0:
        _fatal("OWNER_ID يجب أن يكون رقم حسابك في تيليجرام (رقم موجب). يمكنك معرفته من @userinfobot.")
    return cfg


# ═════════════════════════════════════════════════════════════════════════════
# أمن الملفات: رفع .py / ZIP آمن (Zip Slip / Zip Bomb / Symlinks) + إخفاء الأسرار
# ═════════════════════════════════════════════════════════════════════════════
class UploadError(Exception):
    """خطأ رفع/استخراج برسالة عربية آمنة تُعرض للمستخدم."""


ALLOWED_EXT = {
    ".py", ".pyi", ".txt", ".md", ".rst", ".json", ".yml", ".yaml", ".toml", ".cfg", ".ini",
    ".csv", ".ftl", ".po", ".pot", ".html", ".css", ".xml", ".sql",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".ogg", ".mp3", ".wav", ".mp4", ".pdf",
}
ALLOWED_NAMES = {"dockerfile", "procfile", "makefile", "license", ".gitignore", ".dockerignore",
                 ".python-version", ".env.example", ".env.sample", ".env.template"}
DANGEROUS_EXT = {
    ".exe", ".dll", ".so", ".dylib", ".bat", ".cmd", ".sh", ".ps1", ".msi", ".apk", ".jar", ".com",
    ".scr", ".vbs", ".pyc", ".pyo", ".pyd", ".whl", ".egg", ".bin", ".pkl", ".pickle",
}
SKIP_DIRS = {"__pycache__", ".git", ".hg", ".svn", ".venv", "venv", "node_modules", ".idea",
             ".vscode", "site-packages", ".mypy_cache", ".pytest_cache", "__macosx", ".tox"}
SECRET_EXACT = {".env", "credentials.json", "secrets.json", "secrets.yml", "secrets.yaml",
                "secrets.toml", "secrets.txt", "token.txt", "tokens.txt", "id_rsa", "id_ed25519"}
SECRET_SUFFIX = (".pem", ".key", ".p12", ".pfx", ".session", ".session-journal")


def is_secret_name(rel: str) -> bool:
    name = rel.replace("\\", "/").rsplit("/", 1)[-1].lower()
    if name in ALLOWED_NAMES:
        return False
    if name in SECRET_EXACT or name.endswith(SECRET_SUFFIX):
        return True
    return name.startswith(".env") or (name.startswith("service_account") and name.endswith(".json"))


def classify_member(rel: str) -> Optional[str]:
    """None = يُحتفظ به، وإلا سبب التخطي."""
    parts = rel.split("/")
    name = parts[-1].lower()
    if any(p.lower() in SKIP_DIRS for p in parts[:-1]):
        return "مجلد غير ضروري"
    if is_secret_name(name):
        return "ملف أسرار"
    if name in ALLOWED_NAMES:
        return None
    ext = Path(name).suffix
    if ext in DANGEROUS_EXT:
        return "امتداد خطر"
    if ext in ALLOWED_EXT:
        return None
    return "نوع غير مدعوم"


@dataclass
class ExtractResult:
    files: list[tuple[str, int]]
    skipped: list[tuple[str, str]]
    total_bytes: int


def normalize_member(name: str, limits: Limits) -> str:
    n = name.replace("\\", "/")
    if "\x00" in n or n.startswith("/") or re.match(r"^[A-Za-z]:", n):
        raise UploadError("الأرشيف يحتوي مسارات مطلقة أو خطرة (Zip Slip) وتم رفضه.")
    parts = [p for p in n.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise UploadError("الأرشيف يحتوي مسارات تخرج من المجلد (Path Traversal) وتم رفضه.")
    if len(n) > limits.max_path_len or len(parts) > limits.zip_max_depth:
        raise UploadError("الأرشيف يحتوي مسارًا طويلًا أو عميقًا أكثر من المسموح.")
    return "/".join(parts)


def safe_extract_zip(zip_path: Path, dest: Path, limits: Limits) -> ExtractResult:
    """يستخرج ZIP بأمان: حماية Zip Slip، الروابط الرمزية، القنابل، حدود العدد والحجم."""
    dest.mkdir(parents=True, exist_ok=True)
    dest_res = dest.resolve()
    try:
        zf = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise UploadError("ملف ZIP تالف أو غير صالح.") from exc
    try:
        with zf:
            infos = zf.infolist()
            if len(infos) > limits.zip_max_entries:
                raise UploadError(f"عدد عناصر الأرشيف كبير جدًا (الحد {limits.zip_max_entries}).")
            plan: list[tuple[zipfile.ZipInfo, str]] = []
            skipped: list[tuple[str, str]] = []
            seen: set[str] = set()
            declared = 0
            for info in infos:
                rel = normalize_member(info.filename, limits)  # صارم: يُطبَّق على كل العناصر
                if info.is_dir() or not rel:
                    continue
                if stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF):
                    raise UploadError("الأرشيف يحتوي روابط رمزية (symlinks) وهي غير مسموحة.")
                if info.flag_bits & 0x1:
                    raise UploadError("الأرشيف مشفّر بكلمة مرور وهذا غير مدعوم.")
                reason = classify_member(rel)
                if reason:
                    skipped.append((rel, reason))
                    continue
                if rel in seen:
                    skipped.append((rel, "مكرر"))
                    continue
                seen.add(rel)
                if info.file_size > limits.zip_max_file_bytes:
                    raise UploadError(f"الملف «{clip(rel, 60)}» أكبر من الحد المسموح ({human_size(limits.zip_max_file_bytes)}).")
                if info.file_size > MB and info.compress_size and info.file_size / info.compress_size > limits.zip_max_ratio:
                    raise UploadError("نسبة ضغط مشبوهة (Zip Bomb) وتم رفض الأرشيف.")
                declared += info.file_size
                plan.append((info, rel))
            if not plan:
                raise UploadError("لا يحتوي الأرشيف على ملفات مدعومة.")
            if len(plan) > limits.zip_max_files:
                raise UploadError(f"عدد الملفات ({len(plan)}) يتجاوز الحد المسموح ({limits.zip_max_files}).")
            if declared > limits.zip_max_total_bytes:
                raise UploadError(f"حجم الاستخراج الكلي يتجاوز {human_size(limits.zip_max_total_bytes)}.")
            written: list[tuple[str, int]] = []
            total = 0
            for info, rel in plan:
                target = dest_res / rel
                resolved = target.resolve()
                if resolved != dest_res and dest_res not in resolved.parents:
                    raise UploadError("محاولة كتابة خارج المجلد المسموح (Path Traversal).")
                target.parent.mkdir(parents=True, exist_ok=True)
                size = 0
                with zf.open(info) as src, open(target, "wb") as out:
                    while True:
                        chunk = src.read(64 * 1024)
                        if not chunk:
                            break
                        size += len(chunk)
                        total += len(chunk)
                        # العدّ الفعلي للبايتات (لا نثق بالحجم المُعلن داخل الأرشيف)
                        if size > limits.zip_max_file_bytes or total > limits.zip_max_total_bytes:
                            raise UploadError("حجم الملفات بعد الاستخراج يتجاوز الحد المسموح.")
                        out.write(chunk)
                written.append((rel, size))
            return ExtractResult(written, skipped, total)
    except UploadError:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    except (zipfile.BadZipFile, RuntimeError, OSError, EOFError, NotImplementedError) as exc:
        shutil.rmtree(dest, ignore_errors=True)
        raise UploadError("تعذّر استخراج الأرشيف (ملف تالف أو غير مدعوم).") from exc


def stage_py_upload(src: Path, dest_dir: Path, filename: str, limits: Limits) -> ExtractResult:
    data = src.read_bytes()
    if len(data) > limits.zip_max_file_bytes:
        raise UploadError(f"ملف بايثون أكبر من {human_size(limits.zip_max_file_bytes)}.")
    if b"\x00" in data:
        raise UploadError("الملف يبدو ثنائيًا وليس نص بايثون.")
    try:
        data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UploadError("الملف ليس بترميز UTF-8.") from exc
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = safe_filename(filename)
    if not name.lower().endswith(".py"):
        name += ".py"
    (dest_dir / name).write_bytes(data)
    return ExtractResult([(name, len(data))], [], len(data))


# ── إخفاء الأسرار عند التصدير ─────────────────────────────────────────────────
SECRET_PATTERNS = [
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,50}\b"),   # Telegram bot token
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),             # AWS access key id
    re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),          # GitHub token
    re.compile(r"\bsk-[A-Za-z0-9_-]{32,}\b"),        # API secret keys
]
TEXT_EXPORT_EXT = {".py", ".pyi", ".txt", ".md", ".rst", ".json", ".yml", ".yaml", ".toml",
                   ".cfg", ".ini", ".csv", ".ftl", ".po", ".pot", ".html", ".css", ".xml", ".sql"}


def redact_secrets(text: str) -> tuple[str, int]:
    total = 0
    for pat in SECRET_PATTERNS:
        text, n = pat.subn("REDACTED_SECRET", text)
        total += n
    return text, total


def build_export_zip(root: Path, out_path: Path) -> tuple[int, int]:
    """يبني ZIP للمشروع بلا .env أو توكنات أو مفاتيح. يُرجع (عدد الملفات، عدد الأسرار المخفاة)."""
    files = redactions = 0
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(root.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if is_secret_name(rel):
                continue
            data = path.read_bytes()
            if path.suffix.lower() in TEXT_EXPORT_EXT:
                try:
                    text, n = redact_secrets(data.decode("utf-8"))
                    if n:
                        data, redactions = text.encode("utf-8"), redactions + n
                except UnicodeDecodeError:
                    pass
            z.writestr(rel, data)
            files += 1
    return files, redactions


# ═════════════════════════════════════════════════════════════════════════════
# ANALYZER — تحليل ثابت بالكامل (AST). لا exec/eval/import لكود المستخدم.
# ═════════════════════════════════════════════════════════════════════════════
STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}

FRAMEWORK_MODULES = {
    "aiogram": "aiogram", "telegram": "python-telegram-bot", "telebot": "pyTelegramBotAPI (telebot)",
    "pyrogram": "Pyrogram", "pyrofork": "Pyrofork", "hydrogram": "Hydrogram", "telethon": "Telethon",
    "discord": "discord.py", "nextcord": "nextcord", "disnake": "disnake", "slack_bolt": "Slack Bolt",
    "vkbottle": "vkbottle", "flask": "Flask", "fastapi": "FastAPI", "django": "Django",
}
REQ_TO_FRAMEWORK = {
    "aiogram": "aiogram", "python-telegram-bot": "python-telegram-bot",
    "pytelegrambotapi": "pyTelegramBotAPI (telebot)", "pyrogram": "Pyrogram", "pyrofork": "Pyrofork",
    "hydrogram": "Hydrogram", "telethon": "Telethon", "discord.py": "discord.py", "nextcord": "nextcord",
    "disnake": "disnake", "slack-bolt": "Slack Bolt", "vkbottle": "vkbottle",
}
BUTTON_CLASSES = {"InlineKeyboardButton": "inline", "KeyboardButton": "reply"}
MARKUP_CLASSES = {"InlineKeyboardMarkup", "ReplyKeyboardMarkup", "ReplyKeyboardRemove", "ForceReply"}
ACTION_KWS = ("callback_data", "url", "web_app", "switch_inline_query",
              "switch_inline_query_current_chat", "login_url", "request_contact", "request_location")
MARKER_ATTRS = {"message_handler", "callback_query_handler", "inline_handler", "start_polling",
                "run_polling", "infinity_polling", "executor"}
DANGEROUS_NAMES = {"exec", "eval", "compile", "__import__"}
DANGEROUS_DOTTED = {"os.system", "os.popen", "pickle.loads", "pickle.load", "marshal.loads"}
TEXT_METHODS: dict[str, tuple[Optional[int], tuple[str, ...]]] = {
    "reply_text": (0, ("text",)), "reply": (0, ("text",)), "answer": (0, ("text",)),
    "edit_text": (0, ("text",)), "edit_message_text": (0, ("text",)),
    "send_message": (1, ("text",)), "reply_to": (1, ("text",)),
    "edit_caption": (0, ("caption",)), "edit_message_caption": (None, ("caption",)),
    "answer_callback_query": (1, ("text",)), "send_poll": (1, ("question",)),
    "send_photo": (2, ("caption",)), "send_document": (2, ("caption",)), "send_video": (2, ("caption",)),
    "send_audio": (2, ("caption",)), "send_animation": (2, ("caption",)), "send_voice": (2, ("caption",)),
    "reply_photo": (1, ("caption",)), "reply_document": (1, ("caption",)), "reply_video": (1, ("caption",)),
    "answer_photo": (1, ("caption",)), "answer_document": (1, ("caption",)), "answer_video": (1, ("caption",)),
}
CONFIG_WORDS = {"TOKEN", "KEY", "SECRET", "PASSWORD", "PASSWD", "URL", "URI", "PATH", "HOST", "DSN",
                "DATABASE", "SALT", "HASH", "PORT", "REGEX", "PATTERN", "FORMAT", "LEVEL"}
MAX_BUTTONS, MAX_TEXTS, MAX_SOURCE_BYTES = 2000, 3000, MB


@dataclass
class AnalysisResult:
    project_name: str = ""
    bot_name: str = ""
    bot_username: str = ""
    description: str = ""
    python_version: str = ""
    frameworks: list[str] = field(default_factory=list)
    libraries: list[str] = field(default_factory=list)
    commands: list[dict] = field(default_factory=list)
    buttons: list[dict] = field(default_factory=list)
    texts: list[dict] = field(default_factory=list)
    files: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    callbacks: dict[str, dict] = field(default_factory=dict)
    patterns: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def to_json(self, light: bool = True) -> str:
        data = dataclasses.asdict(self)
        if light:  # الأزرار والنصوص تُحفظ في جداول buttons/texts
            data["buttons"], data["texts"] = [], []
        return json.dumps(data, ensure_ascii=False)

    @staticmethod
    def from_json(raw: str) -> "AnalysisResult":
        try:
            data = json.loads(raw or "{}")
        except json.JSONDecodeError:
            data = {}
        known = {f.name for f in dataclasses.fields(AnalysisResult)}
        return AnalysisResult(**{k: v for k, v in data.items() if k in known})


class _Acc:
    """مُجمّع نتائج التحليل عبر كل الملفات."""

    def __init__(self) -> None:
        self.imports: set[str] = set()
        self.import_paths: set[str] = set()
        self.import_from_names: set[str] = set()
        self.markers: set[str] = set()
        self.buttons: list[dict] = []
        self.texts: list[dict] = []
        self.commands: dict[str, dict] = {}
        self.cb_button: dict[str, list] = defaultdict(list)
        self.cb_handler: dict[str, list] = defaultdict(list)
        self.patterns: list[str] = []
        self.const_counts: Counter = Counter()
        self.danger: dict[str, list[str]] = defaultdict(list)
        self.warnings: list[str] = []
        self.markups: Counter = Counter()
        self.min_py = (3, 0)
        self.bot_name = ""
        self.bot_desc = ""
        self.entry_doc = ""


# ── فهرسة الثوابت النصية: (سطر، رقم التكرار) لتحديد الموضع بدقة بين ast و LibCST ──
def _iter_str_nodes(tree: ast.AST) -> list[ast.Constant]:
    """كل ثوابت str الخارجية؛ لا ندخل داخل f-strings (مطابق لسلوك جامع LibCST)."""
    out: list[ast.Constant] = []
    stack: list[ast.AST] = [tree]
    while stack:
        node = stack.pop()
        if isinstance(node, ast.JoinedStr):
            continue
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append(node)
        stack.extend(ast.iter_child_nodes(node))
    out.sort(key=lambda n: (n.lineno, n.col_offset))
    return out


def index_str_constants(tree: ast.AST) -> dict[int, tuple[int, int]]:
    seen: dict[tuple[int, str], int] = defaultdict(int)
    idx: dict[int, tuple[int, int]] = {}
    for node in _iter_str_nodes(tree):
        key = (node.lineno, node.value)
        idx[id(node)] = (node.lineno, seen[key])
        seen[key] += 1
    return idx


def str_node_map(tree: ast.AST) -> dict[tuple[int, str, int], ast.Constant]:
    seen: dict[tuple[int, str], int] = defaultdict(int)
    out: dict[tuple[int, str, int], ast.Constant] = {}
    for node in _iter_str_nodes(tree):
        key = (node.lineno, node.value)
        out[(node.lineno, node.value, seen[key])] = node
        seen[key] += 1
    return out


def func_name(f: ast.AST) -> str:
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


def safe_unparse(node: ast.AST, limit: int = 120) -> str:
    try:
        return clip(ast.unparse(node), limit)
    except Exception:  # pragma: no cover
        return "<expr>"


def hint_key(node: ast.AST) -> str:
    """مفتاح مُرشَّح للبحث اليدوي: t("settings") / TEXTS["settings"] / SETTINGS_TEXT / texts.settings"""
    if isinstance(node, ast.Call):
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            return node.args[0].value
        return ""
    if isinstance(node, ast.Subscript):
        sl = node.slice
        return sl.value if isinstance(sl, ast.Constant) and isinstance(sl.value, str) else ""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def classify_value(node: ast.AST, idx: dict) -> dict:
    """ثابت نصي صريح = قابل للتعديل، غير ذلك = ديناميكي (لا يُعدَّل عشوائيًا)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) in idx:
        line, occ = idx[id(node)]
        return {"value": node.value, "dynamic": False, "expr": "", "hint": "", "line": line, "occ": occ}
    return {"value": None, "dynamic": True, "expr": safe_unparse(node), "hint": hint_key(node),
            "line": None, "occ": None}


def looks_like_text(value: str) -> bool:
    s = value.strip()
    if len(s) < 2 or len(s) > 4000:
        return False
    if re.match(r"^(https?://|/|\./|\.\./)", s) or SECRET_PATTERNS[0].search(s):
        return False
    if any(ord(c) > 127 for c in s):
        return True
    if re.fullmatch(r"[\w.\-:/@#$%^&*+=|,;]+", s) and len(s) < 20:
        return False
    return True


def is_data_expr(node: ast.AST) -> bool:
    if isinstance(node, ast.Attribute):
        return node.attr in {"data", "callback_data"}
    return isinstance(node, ast.Name) and node.id in {"data", "callback_data", "cb_data", "cbdata", "cd"}


def is_text_expr(node: ast.AST) -> bool:
    if isinstance(node, ast.Attribute):
        return node.attr in {"text", "message_text"}
    return isinstance(node, ast.Name) and node.id in {"text", "msg_text", "message_text", "txt"}


def pattern_matches(pattern: str, value: str) -> bool:
    if not pattern:
        return False
    if value.startswith(pattern):
        return True
    try:
        return re.search(pattern, value) is not None
    except re.error:
        return False


class _Visitor(ast.NodeVisitor):
    def __init__(self, rel: str, idx: dict, acc: _Acc) -> None:
        self.rel, self.idx, self.acc = rel, idx, acc
        self.reply_vars: set[str] = set()
        self._ord: dict[tuple[int, str], int] = defaultdict(int)

    # ── مساعدات ──
    @staticmethod
    def _kw(node: ast.Call, name: str) -> Optional[ast.AST]:
        for kw in node.keywords:
            if kw.arg == name:
                return kw.value
        return None

    @staticmethod
    def _strs(node: Optional[ast.AST]) -> list[str]:
        if node is None:
            return []
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return [node.value]
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            return [e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
        return []

    def _const_locs(self, node: ast.AST) -> list[tuple[str, int, int]]:
        elts = node.elts if isinstance(node, (ast.Tuple, ast.List, ast.Set)) else [node]
        out = []
        for e in elts:
            if isinstance(e, ast.Constant) and isinstance(e.value, str) and id(e) in self.idx:
                line, occ = self.idx[id(e)]
                out.append((e.value, line, occ))
        return out

    def _add_command(self, raw: str, node: ast.AST, source: str, desc: str = "") -> None:
        name = str(raw).strip().lstrip("/").split("@")[0].lower()
        if not re.fullmatch(r"[a-z0-9_]{1,32}", name):
            return
        entry = self.acc.commands.setdefault(
            name, {"name": name, "file": self.rel, "line": getattr(node, "lineno", 0), "source": source, "description": ""})
        if desc and not entry["description"]:
            entry["description"] = desc

    # ── الاستيرادات ──
    def visit_Import(self, node: ast.Import) -> None:
        for a in node.names:
            self.acc.imports.add(a.name.split(".")[0])
            self.acc.import_paths.add(a.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level == 0 and node.module:
            self.acc.imports.add(node.module.split(".")[0])
            self.acc.import_paths.add(node.module)
            for a in node.names:
                self.acc.import_from_names.add(a.name)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in MARKER_ATTRS:
            self.acc.markers.add(node.attr)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for kw in node.keywords:  # class X(CallbackData, prefix="x")
            if kw.arg == "prefix" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                self.acc.patterns.append(kw.value.value)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if isinstance(node.value, ast.Call) and func_name(node.value.func) == "ReplyKeyboardMarkup":
            for t in node.targets:
                if isinstance(t, ast.Name):
                    self.reply_vars.add(t.id)
        self.generic_visit(node)

    # ── مقارنات: معالجات callback والأوامر ──
    def visit_Compare(self, node: ast.Compare) -> None:
        operands = [node.left, *node.comparators]
        consts = [c for o in operands for c in self._const_locs(o)]
        if any(is_data_expr(o) for o in operands):
            for value, line, occ in consts:
                self.acc.cb_handler[value].append((self.rel, line, occ))
        if any(is_text_expr(o) for o in operands):
            for value, _l, _o in consts:
                if re.fullmatch(r"/\w+(@\w+)?", value):
                    self._add_command(value, node, "مقارنة نص")
        self.generic_visit(node)

    # ── الاستدعاءات ──
    def visit_Call(self, node: ast.Call) -> None:
        fname = func_name(node.func)
        if fname in BUTTON_CLASSES:
            self._button(node, BUTTON_CLASSES[fname])
        elif fname == "button" and isinstance(node.func, ast.Attribute) and self._kw(node, "text") is not None:
            self._button(node, "builder")
        elif fname in MARKUP_CLASSES:
            self.acc.markups[fname] += 1
            if fname == "ReplyKeyboardMarkup":
                self._reply_strings(node)
        elif (isinstance(node.func, ast.Attribute) and fname in ("add", "row")
              and isinstance(node.func.value, ast.Name) and node.func.value.id in self.reply_vars):
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    self._reply_button(arg)
        if fname in TEXT_METHODS:
            self._text(node, fname)
        self._commands(node, fname)
        self._patterns(node, fname)
        self._danger(node, fname)
        self.generic_visit(node)

    def _button(self, node: ast.Call, kind: str) -> None:
        if len(self.acc.buttons) >= MAX_BUTTONS:
            return
        text_node = self._kw(node, "text")
        if text_node is None and node.args:
            text_node = node.args[0]
        if text_node is None:
            return
        t = classify_value(text_node, self.idx)
        cb_node = self._kw(node, "callback_data")
        cb = classify_value(cb_node, self.idx) if cb_node is not None else None
        key = (node.lineno, kind)
        ordinal = self._ord[key]
        self._ord[key] += 1
        self.acc.buttons.append({
            "file": self.rel, "line": node.lineno, "kind": kind, "ordinal": ordinal,
            "text": t["value"], "text_dynamic": t["dynamic"], "text_expr": t["expr"], "text_hint": t["hint"],
            "text_line": t["line"], "text_occ": t["occ"],
            "callback": cb["value"] if cb else None, "cb_dynamic": bool(cb and cb["dynamic"]),
            "cb_expr": cb["expr"] if cb else "", "cb_line": cb["line"] if cb else None,
            "cb_occ": cb["occ"] if cb else None,
            "action": next((k for k in ACTION_KWS if self._kw(node, k) is not None), ""),
        })
        if cb and not cb["dynamic"]:
            self.acc.cb_button[cb["value"]].append((self.rel, cb["line"], cb["occ"]))

    def _reply_button(self, const: ast.Constant) -> None:
        if len(self.acc.buttons) >= MAX_BUTTONS:
            return
        t = classify_value(const, self.idx)
        key = (const.lineno, "reply")
        ordinal = self._ord[key]
        self._ord[key] += 1
        self.acc.buttons.append({
            "file": self.rel, "line": const.lineno, "kind": "reply", "ordinal": ordinal,
            "text": t["value"], "text_dynamic": t["dynamic"], "text_expr": t["expr"], "text_hint": t["hint"],
            "text_line": t["line"], "text_occ": t["occ"], "callback": None, "cb_dynamic": False,
            "cb_expr": "", "cb_line": None, "cb_occ": None, "action": "",
        })

    def _reply_strings(self, node: ast.Call) -> None:
        kb = self._kw(node, "keyboard") or (node.args[0] if node.args else None)

        def walk(n: Optional[ast.AST]) -> None:
            if isinstance(n, (ast.List, ast.Tuple)):
                for e in n.elts:
                    walk(e)
            elif isinstance(n, ast.Constant) and isinstance(n.value, str):
                self._reply_button(n)
        walk(kb)

    def _text(self, node: ast.Call, fname: str) -> None:
        if len(self.acc.texts) >= MAX_TEXTS:
            return
        pos, kws = TEXT_METHODS[fname]
        arg = None
        for k in kws:
            arg = self._kw(node, k)
            if arg is not None:
                break
        if arg is None and pos is not None and len(node.args) > pos:
            arg = node.args[pos]
        if arg is None:
            return
        info = classify_value(arg, self.idx)
        if not info["dynamic"] and not info["value"].strip():
            return
        self.acc.texts.append({
            "file": self.rel, "line": info["line"] or node.lineno, "occ": info["occ"], "method": fname,
            "kind": "call", "text": info["value"], "dynamic": info["dynamic"],
            "expr": info["expr"], "hint": info["hint"],
        })

    def _commands(self, node: ast.Call, fname: str) -> None:
        if fname == "Command":
            for a in node.args:
                for s in self._strs(a):
                    self._add_command(s, node, "Command")
        elif fname == "CommandStart":
            self._add_command("start", node, "CommandStart")
        elif fname in ("CommandHandler", "command") and node.args:
            for s in self._strs(node.args[0]):
                self._add_command(s, node, fname)
        elif fname == "BotCommand":
            name = self._kw(node, "command") or (node.args[0] if node.args else None)
            desc = self._kw(node, "description") or (node.args[1] if len(node.args) > 1 else None)
            for s in self._strs(name):
                self._add_command(s, node, "BotCommand", (self._strs(desc) or [""])[0])
        elif fname == "NewMessage":
            for s in self._strs(self._kw(node, "pattern")):
                m = re.match(r"\^?\\?/(\w+)", s)
                if m:
                    self._add_command(m.group(1), node, "NewMessage")
        elif fname in ("set_my_name",):
            self.acc.bot_name = self.acc.bot_name or (self._strs(self._kw(node, "name") or (node.args[0] if node.args else None)) or [""])[0]
        elif fname in ("set_my_description", "set_my_short_description"):
            self.acc.bot_desc = self.acc.bot_desc or (self._strs(self._kw(node, "description") or (node.args[0] if node.args else None)) or [""])[0]
        for kw in node.keywords:
            if kw.arg == "commands":
                for s in self._strs(kw.value):
                    self._add_command(s, node, "commands=")

    def _patterns(self, node: ast.Call, fname: str) -> None:
        if fname == "startswith" and node.args:
            for s in self._strs(node.args[0]):
                self.acc.patterns.append(s)
                if isinstance(node.func, ast.Attribute) and is_text_expr(node.func.value) and re.fullmatch(r"/\w+", s):
                    self._add_command(s, node, "startswith")
        for kw in node.keywords:
            if kw.arg in ("pattern", "regexp", "regex"):
                self.acc.patterns.extend(self._strs(kw.value))
        if (fname in ("compile", "match", "search", "fullmatch") and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "re" and node.args):
            self.acc.patterns.extend(self._strs(node.args[0]))

    def _danger(self, node: ast.Call, fname: str) -> None:
        label = ""
        if isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_NAMES:
            label = f"{node.func.id}()"
        else:
            dotted = safe_unparse(node.func, 60)
            if dotted in DANGEROUS_DOTTED or dotted.startswith("subprocess."):
                label = f"{dotted}()"
        if label:
            self.acc.danger[label].append(f"{self.rel}:{node.lineno}")


def _collect_constants(tree: ast.Module, rel: str, idx: dict, acc: _Acc) -> None:
    """ثوابت الرسائل على مستوى الملف/الصنف وقواميس الترجمة (اسم = "نص")."""

    def add(label: str, node: ast.Constant) -> None:
        loc = idx.get(id(node))
        if loc is None or len(acc.texts) >= MAX_TEXTS or not looks_like_text(node.value):
            return
        acc.texts.append({"file": rel, "line": loc[0], "occ": loc[1], "method": label, "kind": "const",
                          "text": node.value, "dynamic": False, "expr": "", "hint": ""})

    def walk_value(label: str, node: ast.AST, depth: int) -> None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            add(label, node)
        elif isinstance(node, ast.Dict) and depth < 3:
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and isinstance(k.value, (str, int)) and not isinstance(k.value, bool):
                    walk_value(f"{label}[{k.value!r}]", v, depth + 1)

    def handle(stmt: ast.stmt, prefix: str = "") -> None:
        if isinstance(stmt, ast.Assign):
            names = [t.id for t in stmt.targets if isinstance(t, ast.Name)]
            value = stmt.value
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.value is not None:
            names, value = [stmt.target.id], stmt.value
        else:
            return
        if not names or any(tok in CONFIG_WORDS for tok in names[0].upper().split("_")):
            return
        walk_value(prefix + names[0], value, 0)

    for stmt in tree.body:
        if isinstance(stmt, ast.ClassDef):
            for inner in stmt.body:
                handle(inner, stmt.name + ".")
        else:
            handle(stmt)


def _syntax_min_version(tree: ast.AST) -> tuple[int, int]:
    best = (3, 0)
    for node in ast.walk(tree):
        if isinstance(node, ast.Match):
            best = max(best, (3, 10))
        elif hasattr(ast, "TryStar") and isinstance(node, ast.TryStar):
            best = max(best, (3, 11))
        elif hasattr(ast, "TypeAlias") and isinstance(node, ast.TypeAlias):
            best = max(best, (3, 12))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and getattr(node, "type_params", None):
            best = max(best, (3, 12))
        elif isinstance(node, ast.NamedExpr):
            best = max(best, (3, 8))
    return best


def analyze_python_source(rel: str, source: str, acc: _Acc) -> Optional[ast.Module]:
    if len(source.encode("utf-8", "ignore")) > MAX_SOURCE_BYTES:
        acc.warnings.append(f"⚠️ الملف {rel} كبير جدًا وتم تخطيه في التحليل.")
        return None
    try:
        tree = ast.parse(source, filename=rel)
    except SyntaxError as exc:
        hint = " (يبدو كود Python 2)" if "print" in str(exc.msg) and "parenthes" in str(exc.msg) else ""
        acc.warnings.append(f"❌ خطأ صياغة في {rel}:{exc.lineno or '?'} — {exc.msg}{hint}")
        return None
    except (ValueError, RecursionError, MemoryError) as exc:
        acc.warnings.append(f"❌ تعذّر تحليل {rel}: {type(exc).__name__}")
        return None
    idx = index_str_constants(tree)
    for node in _iter_str_nodes(tree):
        acc.const_counts[node.value] += 1
    _Visitor(rel, idx, acc).visit(tree)
    _collect_constants(tree, rel, idx, acc)
    acc.min_py = max(acc.min_py, _syntax_min_version(tree))
    doc = ast.get_docstring(tree)
    if doc and not acc.entry_doc:
        acc.entry_doc = doc.strip().splitlines()[0]
    return tree


def _req_names(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if line and not line.startswith(("-", "git+", "http")):
            name = re.split(r"[<>=!~\[; ]", line, maxsplit=1)[0].strip().lower()
            if name:
                out.append(name)
    return out


def _parse_config_files(misc: dict[str, str]) -> dict[str, Any]:
    info: dict[str, Any] = {"name": "", "python": "", "reqs": [], "desc": ""}
    for rel, text in misc.items():
        low = rel.lower()
        base = low.rsplit("/", 1)[-1]
        if base.startswith("requirements") and base.endswith(".txt"):
            info["reqs"] += _req_names(text)
        elif base == "pyproject.toml":
            try:
                import tomllib
                data = tomllib.loads(text)
            except Exception:
                continue
            proj = data.get("project", {}) or {}
            poetry = (data.get("tool", {}) or {}).get("poetry", {}) or {}
            info["name"] = info["name"] or proj.get("name") or poetry.get("name") or ""
            info["desc"] = info["desc"] or proj.get("description") or poetry.get("description") or ""
            info["python"] = info["python"] or proj.get("requires-python") or (poetry.get("dependencies", {}) or {}).get("python", "") or ""
            info["reqs"] += _req_names("\n".join(str(d) for d in proj.get("dependencies", []) or []))
            info["reqs"] += [str(k).lower() for k in (poetry.get("dependencies", {}) or {}) if str(k).lower() != "python"]
        elif base == ".python-version":
            info["python"] = info["python"] or text.strip().splitlines()[0] if text.strip() else info["python"]
        elif base == "runtime.txt":
            m = re.search(r"python-?(\d+\.\d+(?:\.\d+)?)", text)
            info["python"] = info["python"] or (m.group(1) if m else "")
        elif base == "dockerfile":
            m = re.search(r"(?im)^\s*FROM\s+python:(\d+\.\d+)", text)
            info["python"] = info["python"] or (m.group(1) if m else "")
        elif base in ("readme.md", "readme.rst", "readme.txt"):
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            head = next((ln.lstrip("# ").strip() for ln in lines if ln.startswith("#")), "")
            info["name"] = info["name"] or head
            para = next((ln for ln in lines if not ln.startswith(("#", "=", "-", "!", "[", "```"))), "")
            info["desc"] = info["desc"] or clip(para, 200)
    return info


def _framework_labels(acc: _Acc, reqs: list[str]) -> list[str]:
    imp, names, paths = acc.imports, acc.import_from_names, acc.import_paths
    labels: list[str] = []
    if "aiogram" in imp:
        v3 = bool(names & {"Router", "F", "DefaultBotProperties", "CommandStart"}) or any(
            p.startswith(("aiogram.filters", "aiogram.fsm", "aiogram.enums")) for p in paths)
        v2 = "executor" in names or "executor" in acc.markers or "message_handler" in acc.markers or any(
            p.startswith("aiogram.dispatcher") for p in paths)
        labels.append("aiogram 3.x" if v3 and not v2 else "aiogram 2.x" if v2 and not v3 else "aiogram")
    if "telegram" in imp:
        if names & {"Application", "ApplicationBuilder"}:
            labels.append("python-telegram-bot 20+")
        elif "Updater" in names:
            labels.append("python-telegram-bot 13 أو أقدم")
        else:
            labels.append("python-telegram-bot")
    if "telebot" in imp:
        labels.append("pyTelegramBotAPI (telebot)")
    for mod, label in FRAMEWORK_MODULES.items():
        if mod in imp and mod not in ("aiogram", "telegram", "telebot"):
            labels.append(label)
    for req in reqs:
        label = REQ_TO_FRAMEWORK.get(req)
        if label and not any(x.startswith(label.split()[0]) for x in labels):
            labels.append(label + " (من requirements)")
    return labels


def analyze_directory(root: Path, fallback_name: str = "") -> AnalysisResult:
    """تحليل مجلد مشروع بالكامل — Static Analysis فقط."""
    acc = _Acc()
    res = AnalysisResult()
    py_sources: dict[str, str] = {}
    misc: dict[str, str] = {}
    all_text: dict[str, str] = {}
    config_names = {"dockerfile", "runtime.txt", ".python-version"}
    config_ext = {".txt", ".md", ".toml", ".cfg", ".ini", ".yml", ".yaml", ".json", ".rst"}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        size = path.stat().st_size
        is_py = rel.endswith(".py")
        info = {"path": rel, "size": size, "lines": 0, "python": is_py}
        base = rel.lower().rsplit("/", 1)[-1]
        if size <= MB and (is_py or Path(base).suffix in config_ext or base in config_names):
            try:
                text = path.read_bytes().decode("utf-8-sig")
            except UnicodeDecodeError:
                acc.warnings.append(f"⚠️ الملف {rel} ليس بترميز UTF-8 وتم تخطيه.")
                text = None
            if text is not None:
                info["lines"] = text.count("\n") + 1
                all_text[rel] = text
                if is_py:
                    py_sources[rel] = text
                else:
                    misc[rel] = text
        res.files.append(info)

    trees: dict[str, ast.Module] = {}
    for rel, src in py_sources.items():
        tree = analyze_python_source(rel, src, acc)
        if tree is not None:
            trees[rel] = tree

    cfg = _parse_config_files(misc)
    local = {r.split("/")[0].removesuffix(".py") for r in py_sources}
    third = sorted(m for m in acc.imports if m not in STDLIB and m not in local)
    res.libraries = third + [r for r in dict.fromkeys(cfg["reqs"]) if r not in {t.lower() for t in third}]
    res.frameworks = _framework_labels(acc, cfg["reqs"])
    res.project_name = cfg["name"] or fallback_name or "مشروع بلا اسم"
    res.bot_name = acc.bot_name or (cfg["name"] if cfg["name"] else "")
    res.description = acc.bot_desc or cfg["desc"] or acc.entry_doc
    all_blob = "\n".join(all_text.values())
    handles = Counter(m.group(1) for m in re.finditer(r"(?<![\w/])@([A-Za-z]\w{3,30}[bB][oO][Tt])\b", all_blob))
    handles.update(m.group(1) for m in re.finditer(r"t\.me/([A-Za-z]\w{3,30}[bB][oO][Tt])\b", all_blob))
    res.bot_username = f"@{handles.most_common(1)[0][0]}" if handles else ""
    declared = str(cfg["python"]).strip()
    if declared:
        res.python_version = f"{declared} (معلن في ملفات المشروع)"
    elif acc.min_py > (3, 0):
        res.python_version = f"‎3.{acc.min_py[1]}+ (مُستنتج من صياغة الكود)"
    else:
        res.python_version = "غير محدد"

    res.commands = sorted(acc.commands.values(), key=lambda c: c["name"])
    res.buttons, res.texts = acc.buttons, acc.texts
    res.patterns = list(dict.fromkeys(p for p in acc.patterns if p))[:200]

    # سلامة تعديل callback_data: كل المواضع المصنّفة (زر/معالج) فقط، ولا مواضع أخرى بنفس النص
    for value in {b["callback"] for b in acc.buttons if b["callback"]}:
        targets = list(dict.fromkeys(acc.cb_button[value] + acc.cb_handler[value]))
        other = acc.const_counts[value] - len(acc.cb_button[value]) - len(acc.cb_handler[value])
        if other > 0:
            safe, reason = False, f"النص يظهر في {other} موضع آخر غير مصنّف"
        elif any(pattern_matches(p, value) for p in res.patterns):
            safe, reason = False, "يطابق نمط معالج (startswith/regex/prefix)"
        else:
            safe, reason = True, ""
        res.callbacks[value] = {"safe": safe, "reason": reason, "targets": [list(t) for t in targets]}

    # تحذيرات
    warnings = list(acc.warnings)
    for rel, text in all_text.items():
        for m in SECRET_PATTERNS[0].finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            warnings.append(f"🔑 يبدو أن {rel}:{line} يحتوي Bot Token ({m.group(0)[:4]}…). لن يُضمَّن في التصدير.")
    for label, locs in acc.danger.items():
        warnings.append(f"⚠️ يستخدم {label} في {', '.join(locs[:3])}{'…' if len(locs) > 3 else ''} (لم يُنفَّذ — تحليل ثابت فقط).")
    dyn_b = sum(1 for b in acc.buttons if b["text_dynamic"])
    dyn_t = sum(1 for t in acc.texts if t["dynamic"])
    if dyn_b:
        warnings.append(f"⚠️ {dyn_b} زر بنص ديناميكي (متغيّر/ترجمة) — لا يُعدَّل تلقائيًا.")
    if dyn_t:
        warnings.append(f"⚠️ {dyn_t} رسالة بنص ديناميكي — لا تُعدَّل تلقائيًا.")
    if any(b["cb_dynamic"] for b in acc.buttons):
        warnings.append("⚠️ توجد أزرار بـ callback_data ديناميكي؛ يُمنع تعديل callback المرتبط بأنماط.")
    if len(res.frameworks) > 1:
        warnings.append("ℹ️ اكتُشف أكثر من إطار عمل: " + "، ".join(res.frameworks))
    if not res.frameworks:
        warnings.append("ℹ️ لم يُكتشف إطار عمل بوت معروف (aiogram/PTB/telebot/…).")
    if any(Path(f["path"]).suffix.lower() in {".json", ".yml", ".yaml", ".ftl", ".po"} and "loc" in f["path"].lower() for f in res.files):
        warnings.append("ℹ️ توجد ملفات ترجمة؛ التعديل التلقائي يدعم ملفات Python فقط.")
    if len(acc.buttons) >= MAX_BUTTONS or len(acc.texts) >= MAX_TEXTS:
        warnings.append("ℹ️ تم اقتصار القوائم على الحد الأقصى المسموح.")
    if not HAVE_LIBCST:
        warnings.append("ℹ️ LibCST غير مثبتة على الخادم: التحليل يعمل والتعديل معطّل.")
    res.warnings = warnings
    res.stats = {
        "py_files": len(py_sources), "files": len(res.files), "buttons": len(acc.buttons),
        "buttons_dynamic": dyn_b, "texts": len(acc.texts), "texts_dynamic": dyn_t,
        "commands": len(res.commands), "markups": dict(acc.markups),
    }
    return res


# ── البحث اليدوي الآمن عن موضع نص ديناميكي (مفتاح قاموس / اسم ثابت / نص مطابق) ──
def find_candidates(sources: dict[str, str], query: str, limit: int = 12) -> list[dict]:
    q = query.strip()
    out: list[dict] = []
    seen: set[tuple[str, int, int]] = set()
    if not q:
        return out
    for rel, src in sources.items():
        try:
            tree = ast.parse(src)
        except (SyntaxError, ValueError, RecursionError):
            continue
        idx = index_str_constants(tree)

        def add(node: Optional[ast.AST], how: str) -> None:
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str) or id(node) not in idx:
                return
            line, occ = idx[id(node)]
            if (rel, line, occ) in seen or len(out) >= limit:
                return
            seen.add((rel, line, occ))
            out.append({"file": rel, "line": line, "occ": occ, "value": node.value,
                        "label": f"{rel}:{line} — {how}: {one_line(node.value, 40)}"})

        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for k, v in zip(node.keys, node.values):
                    if isinstance(k, ast.Constant) and k.value == q:
                        add(v, f"مفتاح «{clip(q, 20)}»")
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in targets:
                    if isinstance(t, ast.Name) and t.id in (q, q.upper()):
                        add(node.value, f"ثابت {t.id}")
                    elif isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) and t.slice.value == q:
                        add(node.value, f"عنصر [{clip(q, 20)}]")
            elif isinstance(node, ast.Constant) and node.value == q:
                add(node, "نص مطابق")
    return out


# ═════════════════════════════════════════════════════════════════════════════
# DATABASE — SQLAlchemy Async (SQLite افتراضيًا، PostgreSQL اختياريًا)
# ═════════════════════════════════════════════════════════════════════════════
class Base(DeclarativeBase):
    pass


class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    description: Mapped[str] = mapped_column(String(200), default="")
    price: Mapped[float] = mapped_column(Float, default=0.0)
    duration_days: Mapped[int] = mapped_column(Integer, default=30)  # 0 = دائمة
    max_projects: Mapped[int] = mapped_column(Integer, default=3)
    max_edits_per_day: Mapped[int] = mapped_column(Integer, default=15)
    max_upload_mb: Mapped[int] = mapped_column(Integer, default=5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    referral_code: Mapped[str] = mapped_column(String(16), unique=True, default=new_ref_code)
    referred_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    plan_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("plans.id"), nullable=True)
    plan_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    pending_promo: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("plans.id"))
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending|active|rejected|expired
    price: Mapped[float] = mapped_column(Float, default=0.0)
    promo_code: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class PromoCode(Base):
    __tablename__ = "promo_codes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    discount_type: Mapped[str] = mapped_column(String(10), default="percent")  # percent|fixed|days
    value: Mapped[float] = mapped_column(Float, default=0.0)
    plan_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("plans.id"), nullable=True)
    max_uses: Mapped[int] = mapped_column(Integer, default=0)  # 0 = بلا حد
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SettingRow(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class Admin(Base):
    __tablename__ = "admins"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    added_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Ban(Base):
    __tablename__ = "bans"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    reason: Mapped[str] = mapped_column(String(300), default="")
    banned_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Referral(Base):
    __tablename__ = "referrals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referrer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    referred_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class StatRow(Base):
    __tablename__ = "statistics"
    __table_args__ = (UniqueConstraint("key", "day"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(40))
    day: Mapped[str] = mapped_column(String(10))
    count: Mapped[int] = mapped_column(Integer, default=0)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    original_filename: Mapped[str] = mapped_column(String(200), default="")
    kind: Mapped[str] = mapped_column(String(4), default="py")
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    framework: Mapped[str] = mapped_column(String(200), default="")
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    analysis_json: Mapped[str] = mapped_column(Text, default="")
    pending_json: Mapped[str] = mapped_column(Text, default="[]")


class ProjectFile(Base):
    __tablename__ = "project_files"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    path: Mapped[str] = mapped_column(String(500))
    size: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    is_python: Mapped[bool] = mapped_column(Boolean, default=False)


class ButtonRow(Base):
    __tablename__ = "buttons"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    file_path: Mapped[str] = mapped_column(String(500))
    line: Mapped[int] = mapped_column(Integer, default=0)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    kind: Mapped[str] = mapped_column(String(10), default="inline")
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text_dynamic: Mapped[bool] = mapped_column(Boolean, default=False)
    text_expr: Mapped[str] = mapped_column(Text, default="")
    text_hint: Mapped[str] = mapped_column(String(200), default="")
    text_line: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    text_occ: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    callback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cb_dynamic: Mapped[bool] = mapped_column(Boolean, default=False)
    cb_expr: Mapped[str] = mapped_column(Text, default="")
    action: Mapped[str] = mapped_column(String(40), default="")
    style: Mapped[str] = mapped_column(String(8), default="none")  # نمط دلالي فقط


class TextRow(Base):
    __tablename__ = "texts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    file_path: Mapped[str] = mapped_column(String(500))
    line: Mapped[int] = mapped_column(Integer, default=0)
    occ: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    method: Mapped[str] = mapped_column(String(120), default="")
    kind: Mapped[str] = mapped_column(String(8), default="call")
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dynamic: Mapped[bool] = mapped_column(Boolean, default=False)
    expr: Mapped[str] = mapped_column(Text, default="")
    hint: Mapped[str] = mapped_column(String(200), default="")


class VersionRow(Base):
    __tablename__ = "versions"
    __table_args__ = (UniqueConstraint("project_id", "number"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    changed_files: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LogRow(Base):
    __tablename__ = "logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(40), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    subject: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(8), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class TicketMessage(Base):
    __tablename__ = "ticket_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickets.id"), index=True)
    sender_id: Mapped[int] = mapped_column(BigInteger)
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


REQUIRED_TABLES = ["users", "projects", "project_files", "buttons", "texts", "versions", "logs", "tickets",
                   "ticket_messages", "subscriptions", "plans", "promo_codes", "settings", "admins",
                   "bans", "referrals", "statistics"]
# (الاسم، الوصف، السعر، المدة بالأيام، أقصى مشاريع، عمليات تعديل/يوم، حجم الرفع MB)
DEFAULT_PLANS = [
    ("Free", "الخطة المجانية", 0.0, 0, 3, 15, 5),
    ("Pro", "للمستخدم النشط", 5.0, 30, 15, 100, 10),
    ("Premium", "بلا قيود عملية", 12.0, 30, 100, 1000, 20),
]
DEFAULT_SETTINGS = {"maintenance": "0", "welcome_text": "", "max_upload_mb": "10"}


class Database:
    def __init__(self, url: str) -> None:
        if not HAVE_SA:
            raise RuntimeError("SQLAlchemy غير مثبتة")
        self.url = url
        kwargs: dict[str, Any] = {}
        is_sqlite = url.startswith("sqlite")
        if is_sqlite:
            kwargs["connect_args"] = {"timeout": 30}
        self.engine = create_async_engine(url, **kwargs)
        if is_sqlite:
            @event.listens_for(self.engine.sync_engine, "connect")
            def _pragmas(dbapi_conn: Any, _rec: Any) -> None:  # pragma: no cover
                cur = dbapi_conn.cursor()
                try:
                    cur.execute("PRAGMA foreign_keys=ON")
                    cur.execute("PRAGMA journal_mode=WAL")
                except Exception:
                    pass
                finally:
                    cur.close()
        self.maker = async_sessionmaker(self.engine, expire_on_commit=False)

    def session(self) -> "AsyncSession":
        return self.maker()

    async def init(self) -> None:
        """إنشاء الجداول + الإعدادات الافتراضية + الخطط (Free/Pro/Premium)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.session() as s:
            for key, value in DEFAULT_SETTINGS.items():
                if await s.get(SettingRow, key) is None:
                    s.add(SettingRow(key=key, value=value))
            existing = {n for (n,) in (await s.execute(select(Plan.name))).all()}
            for name, desc, price, days, mp, me, mu in DEFAULT_PLANS:
                if name not in existing:
                    s.add(Plan(name=name, description=desc, price=price, duration_days=days,
                               max_projects=mp, max_edits_per_day=me, max_upload_mb=mu))
            await s.commit()

    async def close(self) -> None:
        await self.engine.dispose()


@dataclass
class AnalysisJob:
    project_id: int
    chat_id: int
    message_id: Optional[int]
    user_id: int


class App:
    """حاوية حالة التطبيق (بدل المتغيرات العامة المتناثرة)."""

    def __init__(self) -> None:
        self.cfg: Optional[Settings] = None
        self.db: Optional[Database] = None
        self.bot: Any = None
        self.owner_id: int = 0
        self.bot_username: str = ""
        self.limits = Limits()
        self.limiter = RateLimiter()
        self.queue: Optional[asyncio.Queue] = None
        self.tasks: list[asyncio.Task] = []
        self.broadcasting = False

    def session(self) -> "AsyncSession":
        assert self.db is not None, "قاعدة البيانات غير مهيأة"
        return self.db.session()


APP = App()


# ── Repositories: دوال وصول للبيانات ─────────────────────────────────────────
async def get_setting(key: str, default: str = "") -> str:
    async with APP.session() as s:
        row = await s.get(SettingRow, key)
        return row.value if row else default


async def set_setting(key: str, value: str) -> None:
    async with APP.session() as s:
        row = await s.get(SettingRow, key)
        if row:
            row.value = value
        else:
            s.add(SettingRow(key=key, value=value))
        await s.commit()


async def log_event(action: str, user_id: Optional[int] = None, project_id: Optional[int] = None,
                    details: Any = "") -> None:
    try:
        async with APP.session() as s:
            s.add(LogRow(user_id=user_id, action=action, project_id=project_id, details=str(details)[:4000]))
            await s.commit()
    except Exception:  # التسجيل يجب ألا يُسقط العملية الأصلية
        log.exception("log_event failed: %s", action)


async def bump_stat(key: str, n: int = 1) -> None:
    day = utcnow().strftime("%Y-%m-%d")
    try:
        async with APP.session() as s:
            row = (await s.execute(select(StatRow).where(StatRow.key == key, StatRow.day == day))).scalar_one_or_none()
            if row:
                row.count += n
            else:
                s.add(StatRow(key=key, day=day, count=n))
            await s.commit()
    except Exception:
        log.exception("bump_stat failed: %s", key)


async def count_rows(s: "AsyncSession", model: Any, *where: Any) -> int:
    stmt = select(func.count()).select_from(model)
    if where:
        stmt = stmt.where(*where)
    return int((await s.execute(stmt)).scalar_one())


async def get_plan_by_name(s: "AsyncSession", name: str) -> Optional[Plan]:
    return (await s.execute(select(Plan).where(Plan.name == name))).scalar_one_or_none()


async def effective_plan(s: "AsyncSession", user: User) -> Plan:
    plan = None
    if user.plan_id and (user.plan_expires_at is None or user.plan_expires_at > utcnow()):
        plan = await s.get(Plan, user.plan_id)
    if plan is None:
        plan = await get_plan_by_name(s, "Free")
    return plan or Plan(name="Free", description="", price=0.0, duration_days=0, max_projects=3,
                        max_edits_per_day=15, max_upload_mb=5, is_active=True)


async def upsert_user(tg: Any) -> tuple[User, bool]:
    async with APP.session() as s:
        user = await s.get(User, tg.id)
        name = " ".join(x for x in (tg.first_name, getattr(tg, "last_name", None)) if x)[:200]
        is_new = user is None
        if user is None:
            free = await get_plan_by_name(s, "Free")
            user = User(id=tg.id, username=tg.username, full_name=name, plan_id=free.id if free else None)
            s.add(user)
        else:
            user.username, user.full_name, user.last_seen = tg.username, name, utcnow()
        await s.commit()
        return user, is_new


async def is_admin_id(uid: int) -> bool:
    if uid == APP.owner_id:
        return True
    async with APP.session() as s:
        return await s.get(Admin, uid) is not None


async def admin_ids() -> list[int]:
    async with APP.session() as s:
        ids = {row for (row,) in (await s.execute(select(Admin.user_id))).all()}
    ids.add(APP.owner_id)
    return sorted(i for i in ids if i)


async def collect_stats() -> dict[str, int]:
    async with APP.session() as s:
        active_since = utcnow() - timedelta(days=7)
        files = int((await s.execute(
            select(func.count()).select_from(ProjectFile).join(Project, Project.id == ProjectFile.project_id)
            .where(ProjectFile.version == Project.current_version))).scalar_one())
        totals: dict[str, int] = {}
        for key, n in (await s.execute(select(StatRow.key, func.sum(StatRow.count)).group_by(StatRow.key))).all():
            totals[key] = int(n or 0)
        return {
            "users": await count_rows(s, User),
            "active": await count_rows(s, User, User.last_seen >= active_since),
            "projects": await count_rows(s, Project),
            "files": files,
            "analyses": totals.get("analysis", 0),
            "edits": totals.get("edit", 0),
            "exports": totals.get("export", 0),
            "tickets": await count_rows(s, Ticket),
            "errors": await count_rows(s, LogRow, LogRow.action == "error"),
        }


def stats_text(st: dict[str, int]) -> str:
    return (
        "📊 <b>الإحصائيات</b>\n\n"
        f"👥 المستخدمون: <b>{st['users']}</b>\n🟢 النشطون (7 أيام): <b>{st['active']}</b>\n"
        f"📁 المشاريع: <b>{st['projects']}</b>\n📂 الملفات: <b>{st['files']}</b>\n"
        f"🔍 التحليلات: <b>{st['analyses']}</b>\n🛠 التعديلات: <b>{st['edits']}</b>\n"
        f"📦 التصديرات: <b>{st['exports']}</b>\n🎫 التذاكر: <b>{st['tickets']}</b>\n❗ الأخطاء: <b>{st['errors']}</b>"
    )


# ═════════════════════════════════════════════════════════════════════════════
# EDITOR (LibCST) — تعديل آمن: Backup → تعديل → ast.parse() تحقق → Rollback عند الفشل
# ═════════════════════════════════════════════════════════════════════════════
@dataclass
class EditOp:
    file: str
    line: int
    occ: int
    old: str
    new: str
    kind: str  # button_text | callback_data | message_text | const


class EditError(Exception):
    pass


if HAVE_LIBCST:
    class _StrReplacer(cst.CSTTransformer):
        """يستبدل ثابت str عند (سطر، رقم تكرار) محدد فقط — أقل تغيير ممكن، بلا مساس بالتنسيق."""

        METADATA_DEPENDENCIES = (PositionProvider,)

        def __init__(self, targets: dict[tuple[int, int], str]) -> None:
            super().__init__()
            self.targets = targets
            self._seen: dict[int, int] = defaultdict(int)
            self.applied: set[tuple[int, int]] = set()

        def leave_SimpleString(self, original: "cst.SimpleString", updated: "cst.SimpleString") -> "cst.BaseExpression":
            return self._maybe(original, updated)

        def leave_ConcatenatedString(self, original: "cst.ConcatenatedString", updated: "cst.ConcatenatedString") -> "cst.BaseExpression":
            return self._maybe(original, updated)

        def _maybe(self, original: Any, updated: Any) -> Any:
            pos = self.get_metadata(PositionProvider, original)
            line = pos.start.line
            key = (line, original.evaluated_value)
            occ = self._seen[hash(key)]
            self._seen[hash(key)] += 1
            target = self.targets.get((line, occ))
            if target is None or original.evaluated_value != _dummy_lookup(self.targets, line, occ):
                return updated
            prefix = original.prefix if isinstance(original, cst.SimpleString) else ""
            quote = original.quote if isinstance(original, cst.SimpleString) else '"'
            self.applied.add((line, occ))
            escaped = target.replace("\\", "\\\\").replace(quote, "\\" + quote).replace("\n", "\\n")
            return cst.SimpleString(value=f"{prefix}{quote}{escaped}{quote}")

    def _dummy_lookup(targets: dict, line: int, occ: int) -> Any:
        return _EDIT_EXPECTED.get((line, occ))


_EDIT_EXPECTED: dict[tuple[int, int], str] = {}


def apply_edits_to_source(source: str, ops: list[EditOp]) -> str:
    """يطبّق مجموعة تعديلات (سطر، تكرار) → قيمة جديدة على ملف واحد عبر LibCST."""
    if not HAVE_LIBCST:
        raise EditError("LibCST غير متوفرة على الخادم؛ التعديل التلقائي معطّل.")
    global _EDIT_EXPECTED
    targets = {(op.line, op.occ): op.new for op in ops}
    _EDIT_EXPECTED = {(op.line, op.occ): op.old for op in ops}
    try:
        tree = cst.parse_module(source)
        wrapper = MetadataWrapper(tree)
        transformer = _StrReplacer(targets)
        new_tree = wrapper.visit(transformer)
        missing = set(targets) - transformer.applied
        if missing:
            raise EditError(f"تعذّر إيجاد {len(missing)} من المواضع المطلوب تعديلها (قد يكون الملف تغيّر).")
        return new_tree.code
    except EditError:
        raise
    except Exception as exc:
        raise EditError(f"فشل تعديل LibCST: {exc}") from exc
    finally:
        _EDIT_EXPECTED = {}


def backup_project(proj_dir: Path, project_id: int) -> Path:
    ts = utcnow().strftime("%Y%m%d_%H%M%S_%f")
    dest = PATHS.backups / f"project_{project_id}" / ts
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(proj_dir, dest)
    return dest


def apply_project_edits(proj_dir: Path, ops_by_file: dict[str, list[EditOp]]) -> list[str]:
    """يطبّق كل التعديلات على نسخة العمل؛ يتحقق بـ ast.parse بعد كل ملف ويسترجع الأصل عند الفشل."""
    changed: list[str] = []
    originals: dict[str, str] = {}
    try:
        for rel, ops in ops_by_file.items():
            target = proj_dir / rel
            original = target.read_text("utf-8")
            originals[rel] = original
            new_source = apply_edits_to_source(original, ops)
            try:
                ast.parse(new_source)
            except SyntaxError as exc:
                raise EditError(f"التعديل على {rel} أنتج كودًا غير صالح: {exc.msg}") from exc
            target.write_text(new_source, "utf-8")
            changed.append(rel)
        return changed
    except EditError:
        for rel, original in originals.items():
            with contextlib.suppress(Exception):
                (proj_dir / rel).write_text(original, "utf-8")
        raise


# ═════════════════════════════════════════════════════════════════════════════
# مساعدات مشروع: مسارات، حفظ نتيجة تحليل، حذف
# ═════════════════════════════════════════════════════════════════════════════
def project_dir(project_id: int, version: int) -> Path:
    return PATHS.projects / f"project_{project_id}" / f"v{version}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


async def save_analysis(s: "AsyncSession", project: Project, res: AnalysisResult) -> None:
    version = project.current_version
    await s.execute(delete(ButtonRow).where(ButtonRow.project_id == project.id, ButtonRow.version == version))
    await s.execute(delete(TextRow).where(TextRow.project_id == project.id, TextRow.version == version))
    for b in res.buttons[:MAX_BUTTONS]:
        s.add(ButtonRow(project_id=project.id, version=version, file_path=b["file"], line=b["line"],
                         ordinal=b["ordinal"], kind=b["kind"], text=b["text"], text_dynamic=b["text_dynamic"],
                         text_expr=b["text_expr"], text_hint=b["text_hint"], text_line=b["text_line"],
                         text_occ=b["text_occ"], callback=b["callback"], cb_dynamic=b["cb_dynamic"],
                         cb_expr=b["cb_expr"], action=b["action"]))
    for t in res.texts[:MAX_TEXTS]:
        s.add(TextRow(project_id=project.id, version=version, file_path=t["file"], line=t["line"],
                       occ=t["occ"], method=t["method"], kind=t["kind"], text=t["text"],
                       dynamic=t["dynamic"], expr=t["expr"], hint=t["hint"]))
    project.analysis_json = res.to_json(light=True)
    project.framework = "، ".join(res.frameworks)[:200]
    project.status = "analyzed"
    project.updated_at = utcnow()
    await s.commit()


def load_result_light(project: Project) -> AnalysisResult:
    return AnalysisResult.from_json(project.analysis_json)


async def run_analysis(project_id: int) -> AnalysisResult:
    async with APP.session() as s:
        project = await s.get(Project, project_id)
        if project is None:
            raise UploadError("المشروع غير موجود.")
        pdir = project_dir(project.id, project.current_version)
        res = await asyncio.to_thread(analyze_directory, pdir, project.name)
        await save_analysis(s, project, res)
        await bump_stat("analysis")
        await log_event("analysis", project.user_id, project.id, f"{res.stats}")
        return res


async def full_project_delete(project_id: int) -> None:
    shutil.rmtree(PATHS.projects / f"project_{project_id}", ignore_errors=True)
    shutil.rmtree(PATHS.backups / f"project_{project_id}", ignore_errors=True)
    async with APP.session() as s:
        for model in (ButtonRow, TextRow, VersionRow, ProjectFile):
            await s.execute(delete(model).where(model.project_id == project_id))
        await s.execute(delete(Project).where(Project.id == project_id))
        await s.commit()


def notify_text(project: Project, res: AnalysisResult) -> str:
    return (
        f"📤 <b>مشروع جديد</b>\n👤 المستخدم: <code>{project.user_id}</code>\n"
        f"📦 الاسم: {esc(project.name)}\n🤖 Framework: {esc(project.framework or '—')}\n"
        f"📂 الملفات: {len(res.files)} | 🐍 {esc(res.python_version)}"
    )


# ═════════════════════════════════════════════════════════════════════════════
# AIOGRAM — Router/FSM/Keyboards/Handlers  (يُبنى فقط إن كانت aiogram متوفرة)
# ═════════════════════════════════════════════════════════════════════════════
if HAVE_AIOGRAM:
    router = Router()

    class UploadState(StatesGroup):
        waiting_file = State()
        naming = State()

    class CustomizeState(StatesGroup):
        waiting_value = State()
        waiting_manual_pick = State()

    class TicketState(StatesGroup):
        subject = State()
        message = State()
        reply = State()

    class BroadcastState(StatesGroup):
        waiting_content = State()

    class AdminState(StatesGroup):
        ban_user = State()
        unban_user = State()
        add_admin = State()
        promo_create = State()
        plan_edit = State()

    PENDING_UPLOAD_NAME: dict[int, dict] = {}  # user_id -> {"path","kind","filename"}

    # ── لوحات المفاتيح ──
    def kb(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t, callback_data=d) for t, d in row] for row in rows])

    def main_menu_kb(is_admin: bool) -> InlineKeyboardMarkup:
        rows = [
            [("📁 مشاريعي", "menu:projects"), ("📤 رفع مشروع", "menu:upload")],
            [("🛠 تخصيص مشروع", "menu:customize"), ("📊 إحصائياتي", "menu:mystats")],
            [("💎 الاشتراك", "menu:sub"), ("🎫 الدعم", "menu:support")],
            [("ℹ️ حول البوت", "menu:about")],
        ]
        if is_admin:
            rows.append([("👑 لوحة الإدارة", "admin:home")])
        return kb(rows)

    def back_row(cb: str = "menu:home") -> list[tuple[str, str]]:
        return [("🔙 رجوع", cb)]

    def confirm_row(yes: str, no: str) -> list[tuple[str, str]]:
        return [("✅ تأكيد", yes), ("❌ إلغاء", no)]

    def welcome_text(name: str) -> str:
        return (f"👋 أهلًا بك {esc(name)} في <b>{APP_NAME}</b>!\n\n"
                "ارفع مشروع بوت تيليجرام (.py أو .zip) وسأحلّله وأساعدك على تخصيصه بأمان،\n"
                "دون تشغيل كودك مطلقًا — تحليل ثابت (Static) فقط.")

    async def send_or_edit(target: Any, text: str, markup: Optional[InlineKeyboardMarkup] = None) -> None:
        text = clip_message(text)
        if isinstance(target, CallbackQuery):
            with contextlib.suppress(TelegramBadRequest):
                await target.message.edit_text(text, reply_markup=markup)
        else:
            await target.answer(text, reply_markup=markup)

    def require_owner(handler: Any) -> Any:
        async def wrapped(event: Any, *a: Any, **kw: Any) -> Any:
            uid = event.from_user.id
            if not await is_admin_id(uid):
                if isinstance(event, CallbackQuery):
                    await event.answer("🚫 هذا القسم للمالك فقط.", show_alert=True)
                else:
                    await event.answer("🚫 هذا القسم مخصص لمالك البوت فقط.")
                return None
            return await handler(event, *a, **kw)
        return wrapped

    async def check_ban(uid: int) -> bool:
        async with APP.session() as s:
            return await s.get(Ban, uid) is not None

    async def rl_guard(event: Any, action: str) -> bool:
        uid = event.from_user.id
        wait = APP.limiter.check(uid, action) or APP.limiter.check(uid, "global")
        if wait:
            msg = f"⏳ عدد الطلبات كبير، حاول بعد {wait} ثانية."
            if isinstance(event, CallbackQuery):
                await event.answer(msg, show_alert=True)
            else:
                await event.answer(msg)
            return False
        return True

    # ── /start ──
    @router.message(CommandStart())
    async def cmd_start(m: Message, command: CommandObject, state: FSMContext) -> None:
        await state.clear()
        if await check_ban(m.from_user.id):
            await m.answer("🚫 تم حظرك من استخدام هذا البوت.")
            return
        user, is_new = await upsert_user(m.from_user)
        arg = (command.args or "").strip()
        if is_new and arg.startswith("ref_"):
            code = arg[4:]
            async with APP.session() as s:
                ref = (await s.execute(select(User).where(User.referral_code == code))).scalar_one_or_none()
                if ref and ref.id != user.id:
                    exists = (await s.execute(select(Referral).where(Referral.referred_id == user.id))).scalar_one_or_none()
                    if not exists:
                        s.add(Referral(referrer_id=ref.id, referred_id=user.id))
                        await s.commit()
                        await log_event("referral", ref.id, details=f"referred={user.id}")
        is_admin = await is_admin_id(m.from_user.id)
        await m.answer(welcome_text(user.full_name or "صديقنا"), reply_markup=main_menu_kb(is_admin))

    @router.callback_query(F.data == "menu:home")
    async def cb_home(c: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        is_admin = await is_admin_id(c.from_user.id)
        await send_or_edit(c, welcome_text(c.from_user.first_name or "صديقنا"), main_menu_kb(is_admin))
        await c.answer()

    @router.callback_query(F.data.startswith("noop"))
    async def cb_noop(c: CallbackQuery) -> None:
        await c.answer()

    @router.callback_query(F.data == "menu:about")
    async def cb_about(c: CallbackQuery) -> None:
        text = (f"ℹ️ <b>{APP_NAME}</b> v{APP_VERSION}\n\n"
                "أرفع مشروع بوت تيليجرام فأحلّله بتحليل ثابت (AST) بدون تشغيل كودك،\n"
                "ثم أساعدك على تخصيص النصوص والأزرار بأمان مع نسخ احتياطية وسجل إصدارات.")
        await send_or_edit(c, text, kb([back_row()]))
        await c.answer()

    # ── رفع مشروع ──
    @router.callback_query(F.data == "menu:upload")
    async def cb_upload(c: CallbackQuery, state: FSMContext) -> None:
        if not await rl_guard(c, "upload"):
            return
        await state.set_state(UploadState.waiting_file)
        await send_or_edit(c, "📤 أرسل الآن ملف <b>.py</b> أو أرشيف <b>.zip</b> لمشروعك.", kb([back_row()]))
        await c.answer()

    @router.message(StateFilter(UploadState.waiting_file), F.document)
    async def on_upload_doc(m: Message, state: FSMContext) -> None:
        if await check_ban(m.from_user.id):
            return
        if not await rl_guard(m, "upload"):
            return
        doc = m.document
        name = doc.file_name or "project"
        ext = Path(name).suffix.lower()
        if ext not in (".py", ".zip"):
            await m.answer("❌ الامتداد غير مدعوم. أرسل ملف .py أو .zip فقط.")
            return
        async with APP.session() as s:
            user = await s.get(User, m.from_user.id)
            plan = await effective_plan(s, user)
            n = await count_rows(s, Project, Project.user_id == m.from_user.id)
            if n >= plan.max_projects:
                await m.answer(f"🚫 وصلت للحد الأقصى لعدد المشاريع في خطتك ({plan.max_projects}). ترقّ عبر «💎 الاشتراك».")
                return
            max_mb = plan.max_upload_mb
        if doc.file_size and doc.file_size > max_mb * MB:
            await m.answer(f"❌ حجم الملف يتجاوز الحد المسموح لخطتك ({max_mb} MB).")
            return
        if doc.file_size and doc.file_size > TELEGRAM_DOWNLOAD_CAP:
            await m.answer("❌ حجم الملف كبير جدًا لتنزيله عبر Bot API.")
            return
        status = await m.answer("⏳ جاري استلام الملف...")
        tmp_dir = Path(tempfile.mkdtemp(dir=PATHS.tmp))
        try:
            raw = tmp_dir / safe_filename(name)
            file = await m.bot.get_file(doc.file_id)
            await m.bot.download_file(file.file_path, destination=raw)
            PENDING_UPLOAD_NAME[m.from_user.id] = {"path": str(raw), "kind": "zip" if ext == ".zip" else "py",
                                                   "filename": name, "tmp_dir": str(tmp_dir)}
            await state.set_state(UploadState.naming)
            await status.edit_text("✅ استُلم الملف. أرسل الآن اسمًا لهذا المشروع (أو أرسل /skip لاستخدام اسم الملف).")
        except Exception:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            log.exception("upload receive failed")
            await status.edit_text("❌ تعذّر استلام الملف. حاول مجددًا.")

    @router.message(StateFilter(UploadState.waiting_file))
    async def on_upload_wrong_type(m: Message) -> None:
        await m.answer("📎 أرسل الملف كـ Document (.py أو .zip)، وليس نصًا.")

    async def _finish_upload(m: Message, state: FSMContext, project_name: str) -> None:
        info = PENDING_UPLOAD_NAME.pop(m.from_user.id, None)
        await state.clear()
        if not info:
            await m.answer("❌ لا يوجد رفع معلّق. ابدأ من «📤 رفع مشروع».")
            return
        tmp_dir = Path(info["tmp_dir"])
        raw = Path(info["path"])
        status = await m.answer("⏳ جاري الفحص والاستخراج الآمن...")
        try:
            async with APP.session() as s:
                s.add(project := Project(user_id=m.from_user.id, name=safe_filename(project_name, "مشروع"),
                                         original_filename=info["filename"], kind=info["kind"]))
                await s.flush()
                pdir = project_dir(project.id, 1)
                pdir.mkdir(parents=True, exist_ok=True)
                if info["kind"] == "zip":
                    result = await asyncio.to_thread(safe_extract_zip, raw, pdir, APP.limits)
                else:
                    result = await asyncio.to_thread(stage_py_upload, raw, pdir, info["filename"], APP.limits)
                for rel, size in result.files:
                    fp = pdir / rel
                    s.add(ProjectFile(project_id=project.id, version=1, path=rel, size=size,
                                      sha256=sha256_file(fp), is_python=rel.endswith(".py")))
                project.size_bytes = sum(sz for _, sz in result.files)
                s.add(VersionRow(project_id=project.id, number=1, user_id=m.from_user.id,
                                 description="الرفع الأولي", changed_files=json.dumps([r for r, _ in result.files])))
                await s.commit()
                pid = project.id
            await log_event("upload", m.from_user.id, pid, f"files={len(result.files)} skipped={len(result.skipped)}")
            await bump_stat("uploads")
            skip_note = f"\nℹ️ تم تجاهل {len(result.skipped)} عنصر غير مدعوم/خطر." if result.skipped else ""
            await status.edit_text(f"✅ تم رفع المشروع بنجاح (#{pid}).{skip_note}\n⏳ جاري بدء التحليل...")
            try:
                res = await run_analysis(pid)
                await status.edit_text(f"✅ اكتمل التحليل.\n\n{clip_message(report_summary(res))}",
                                       reply_markup=project_menu_kb(pid))
            except Exception:
                log.exception("initial analysis failed pid=%s", pid)
                await status.edit_text("✅ تم الرفع، لكن حدث خطأ أثناء التحليل. جرّب «🔍 تحليل» من قائمة المشروع.",
                                       reply_markup=project_menu_kb(pid))
            for admin_id in await admin_ids():
                with contextlib.suppress(TelegramAPIError):
                    await m.bot.send_message(admin_id, notify_text(project, AnalysisResult.from_json(project.analysis_json)))
                    if raw.stat().st_size <= TELEGRAM_DOWNLOAD_CAP:
                        await m.bot.send_document(admin_id, FSInputFile(raw, filename=info["filename"]))
        except UploadError as exc:
            await status.edit_text(f"❌ {exc}")
        except Exception:
            log.exception("upload finish failed")
            await status.edit_text("❌ حدث خطأ غير متوقع أثناء معالجة الرفع.")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    @router.message(StateFilter(UploadState.naming), Command("skip"))
    async def on_naming_skip(m: Message, state: FSMContext) -> None:
        info = PENDING_UPLOAD_NAME.get(m.from_user.id) or {}
        await _finish_upload(m, state, Path(info.get("filename", "مشروع")).stem)

    @router.message(StateFilter(UploadState.naming))
    async def on_naming(m: Message, state: FSMContext) -> None:
        await _finish_upload(m, state, one_line(m.text or "مشروع", 60))

    # ── تقرير التحليل + Pagination ──
    def report_summary(res: AnalysisResult) -> str:
        return (
            "📊 <b>نتيجة التحليل</b>\n\n"
            f"📦 المشروع: {esc(res.project_name)}\n🐍 Python: {esc(res.python_version)}\n"
            f"🤖 Framework: {esc('، '.join(res.frameworks) or 'غير معروف')}\n"
            f"⚡ Commands: {len(res.commands)} | 🔘 Buttons: {len(res.buttons)} | "
            f"📝 Texts: {len(res.texts)} | 📂 Files: {len(res.files)}\n"
            f"⚠️ Warnings: {len(res.warnings)}"
        )

    SECTIONS = {
        "commands": ("⚡ Commands", lambda r: [f"/{c['name']} — {esc(c['description'] or c['source'])}" for c in r.commands]),
        "buttons": ("🔘 Buttons", lambda r: [
            f"{'⚠️ ' if b['text_dynamic'] else ''}[{b['kind']}] {esc(b['text']) if not b['text_dynamic'] else esc(b['text_hint'] or b['text_expr'])}"
            f"{' → ' + esc(b['callback']) if b['callback'] else ''} <i>({esc(b['file'])}:{b['line']})</i>" for b in r.buttons]),
        "texts": ("📝 Texts", lambda r: [
            f"{'⚠️ ' if t['dynamic'] else ''}{esc(clip(t['text'], 70)) if not t['dynamic'] else esc(t['hint'] or t['expr'])}"
            f" <i>({esc(t['file'])}:{t['line']})</i>" for t in r.texts]),
        "files": ("📂 Files", lambda r: [f"{esc(f['path'])} — {human_size(f['size'])}" for f in r.files]),
        "warnings": ("⚠️ Warnings", lambda r: [esc(w) for w in r.warnings]),
    }

    def report_menu_kb(pid: int) -> InlineKeyboardMarkup:
        return kb([
            [("⚡ Commands", f"rep:{pid}:commands:1"), ("🔘 Buttons", f"rep:{pid}:buttons:1")],
            [("📝 Texts", f"rep:{pid}:texts:1"), ("📂 Files", f"rep:{pid}:files:1")],
            [("⚠️ Warnings", f"rep:{pid}:warnings:1")],
            [("🔙 لوحة المشروع", f"proj:open:{pid}")],
        ])

    async def render_section(c: CallbackQuery, pid: int, section: str, page: int) -> None:
        async with APP.session() as s:
            project = await s.get(Project, pid)
        if not project or project.user_id != c.from_user.id:
            await c.answer("❌ المشروع غير موجود.", show_alert=True)
            return
        res = load_result_light(project)
        title, getter = SECTIONS[section]
        items = getter(res)
        pg = paginate(items, page, 8)
        body = "\n".join(f"• {it}" for it in pg.items) if pg.items else "لا توجد عناصر."
        text = f"{title} ({pg.total})\n\n{body}"
        rows = [pagination_row(f"rep:{pid}:{section}:{{page}}", pg.page, pg.pages),
                [("🔙 التقرير", f"proj:report:{pid}")]]
        await send_or_edit(c, text, kb(rows))

    @router.callback_query(F.data.regexp(r"^rep:\d+:\w+:\d+$"))
    async def cb_report_section(c: CallbackQuery) -> None:
        _, pid_s, section, page_s = c.data.split(":")
        await render_section(c, int(pid_s), section, int(page_s))
        await c.answer()

    @router.callback_query(F.data.regexp(r"^proj:report:\d+$"))
    async def cb_report_home(c: CallbackQuery) -> None:
        pid = int(c.data.split(":")[2])
        async with APP.session() as s:
            project = await s.get(Project, pid)
        if not project or project.user_id != c.from_user.id:
            await c.answer("❌ غير موجود.", show_alert=True)
            return
        res = load_result_light(project)
        await send_or_edit(c, report_summary(res), report_menu_kb(pid))
        await c.answer()

    # ── قائمة المشاريع + لوحة كل مشروع ──
    STATUS_LABEL = {"uploaded": "⏳ بانتظار التحليل", "analyzed": "✅ محلَّل", "error": "❌ خطأ"}

    async def list_projects_text_kb(uid: int, page: int) -> tuple[str, InlineKeyboardMarkup]:
        async with APP.session() as s:
            rows = (await s.execute(select(Project).where(Project.user_id == uid).order_by(Project.updated_at.desc()))).scalars().all()
            versions = {}
            for p in rows:
                versions[p.id] = (await s.execute(select(func.count()).select_from(VersionRow).where(VersionRow.project_id == p.id))).scalar_one()
        pg = paginate(rows, page, 6)
        if not pg.items:
            return "📁 لا توجد مشاريع بعد. استخدم «📤 رفع مشروع».", kb([[("📤 رفع مشروع", "menu:upload")], back_row()])
        lines = [f"📦 <b>{esc(p.name)}</b> (#{p.id})\n   📅 {fmt_dt(p.created_at)} | ✏️ {fmt_dt(p.updated_at)} | "
                f"📜 إصدارات: {versions[p.id]} | {STATUS_LABEL.get(p.status, p.status)}" for p in pg.items]
        text = f"📁 <b>مشاريعي</b> ({pg.total})\n\n" + "\n\n".join(lines)
        rows_kb = [[(f"📦 {clip(p.name, 20)} (#{p.id})", f"proj:open:{p.id}")] for p in pg.items]
        rows_kb.append(pagination_row("menu:projects:{page}", pg.page, pg.pages))
        rows_kb.append(back_row())
        return text, kb(rows_kb)

    @router.callback_query(F.data.regexp(r"^menu:projects(:\d+)?$"))
    async def cb_projects(c: CallbackQuery) -> None:
        page = int(c.data.split(":")[2]) if c.data.count(":") == 2 else 1
        text, markup = await list_projects_text_kb(c.from_user.id, page)
        await send_or_edit(c, text, markup)
        await c.answer()

    def project_menu_kb(pid: int) -> InlineKeyboardMarkup:
        return kb([
            [("🔍 تحليل", f"proj:analyze:{pid}"), ("🛠 تخصيص", f"cust:open:{pid}")],
            [("👁 Preview", f"proj:preview:{pid}"), ("📜 الإصدارات", f"proj:versions:{pid}:1")],
            [("📦 تصدير", f"proj:export:{pid}"), ("🗑 حذف", f"proj:delconfirm:{pid}")],
            [("📊 التقرير", f"proj:report:{pid}")],
            [("🔙 مشاريعي", "menu:projects")],
        ])

    async def open_project(c: CallbackQuery, pid: int) -> None:
        async with APP.session() as s:
            project = await s.get(Project, pid)
        if not project or project.user_id != c.from_user.id:
            await c.answer("❌ المشروع غير موجود.", show_alert=True)
            return
        text = (f"📦 <b>{esc(project.name)}</b> (#{project.id})\n{STATUS_LABEL.get(project.status, project.status)}\n"
                f"🤖 {esc(project.framework or '—')}\n📅 رُفع: {fmt_dt(project.created_at)} | "
                f"✏️ آخر تعديل: {fmt_dt(project.updated_at)}\n📌 الإصدار الحالي: v{project.current_version}")
        await send_or_edit(c, text, project_menu_kb(pid))
        await c.answer()

    @router.callback_query(F.data.regexp(r"^proj:open:\d+$"))
    async def cb_open_project(c: CallbackQuery) -> None:
        await open_project(c, int(c.data.split(":")[2]))

    @router.callback_query(F.data.regexp(r"^proj:analyze:\d+$"))
    async def cb_analyze(c: CallbackQuery) -> None:
        if not await rl_guard(c, "analysis"):
            return
        pid = int(c.data.split(":")[2])
        async with APP.session() as s:
            project = await s.get(Project, pid)
        if not project or project.user_id != c.from_user.id:
            await c.answer("❌ غير موجود.", show_alert=True)
            return
        await send_or_edit(c, "⏳ جاري التحليل...", None)
        try:
            res = await run_analysis(pid)
            await send_or_edit(c, f"✅ اكتمل التحليل.\n\n{report_summary(res)}", report_menu_kb(pid))
        except Exception:
            log.exception("analyze failed pid=%s", pid)
            await send_or_edit(c, "❌ فشل التحليل.", project_menu_kb(pid))
        await c.answer()

    @router.callback_query(F.data.regexp(r"^proj:preview:\d+$"))
    async def cb_preview(c: CallbackQuery) -> None:
        pid = int(c.data.split(":")[2])
        async with APP.session() as s:
            project = await s.get(Project, pid)
            if not project or project.user_id != c.from_user.id:
                await c.answer("❌ غير موجود.", show_alert=True)
                return
            pending = json.loads(project.pending_json or "[]")
        if not pending:
            body = "لا توجد تغييرات معلّقة بعد. استخدم «🛠 تخصيص» لإجراء تعديلات."
        else:
            lines = []
            for ch in pending:
                label = {"button_text": "تغيير نص زر", "callback_data": "تغيير callback_data",
                         "message_text": "تغيير رسالة"}.get(ch["kind"], "تغيير")
                lines.append(f"• {label}:\n  {esc(clip(ch['old'], 40))} → {esc(clip(ch['new'], 40))}")
            body = "📝 <b>التغييرات المعلّقة:</b>\n\n" + "\n".join(lines)
        rows = [[("📦 تصدير الآن", f"proj:export:{pid}")]] if pending else []
        rows.append(back_row(f"proj:open:{pid}"))
        await send_or_edit(c, body, kb(rows))
        await c.answer()

    @router.callback_query(F.data.regexp(r"^proj:delconfirm:\d+$"))
    async def cb_del_confirm(c: CallbackQuery) -> None:
        pid = int(c.data.split(":")[2])
        await send_or_edit(c, "⚠️ هل تريد حذف هذا المشروع نهائيًا؟ لا يمكن التراجع.",
                           kb([confirm_row(f"proj:delyes:{pid}", f"proj:open:{pid}")]))
        await c.answer()

    @router.callback_query(F.data.regexp(r"^proj:delyes:\d+$"))
    async def cb_del_yes(c: CallbackQuery) -> None:
        pid = int(c.data.split(":")[2])
        async with APP.session() as s:
            project = await s.get(Project, pid)
            if not project or project.user_id != c.from_user.id:
                await c.answer("❌ غير موجود.", show_alert=True)
                return
        await full_project_delete(pid)
        await log_event("delete", c.from_user.id, pid)
        text, markup = await list_projects_text_kb(c.from_user.id, 1)
        await send_or_edit(c, "🗑 تم الحذف.\n\n" + text, markup)
        await c.answer()

    # ── سجل الإصدارات + استعادة ──
    @router.callback_query(F.data.regexp(r"^proj:versions:\d+:\d+$"))
    async def cb_versions(c: CallbackQuery) -> None:
        _, _, pid_s, page_s = c.data.split(":")
        pid, page = int(pid_s), int(page_s)
        async with APP.session() as s:
            project = await s.get(Project, pid)
            if not project or project.user_id != c.from_user.id:
                await c.answer("❌ غير موجود.", show_alert=True)
                return
            rows = (await s.execute(select(VersionRow).where(VersionRow.project_id == pid).order_by(VersionRow.number.desc()))).scalars().all()
        pg = paginate(rows, page, 6)
        lines = [f"📜 v{v.number}{' (الحالي)' if v.number == project.current_version else ''} — "
                f"{fmt_dt(v.created_at)}\n   {esc(clip(v.description, 60))}" for v in pg.items]
        text = f"📜 <b>إصدارات {esc(project.name)}</b>\n\n" + ("\n\n".join(lines) if lines else "لا توجد إصدارات.")
        rows_kb = [[(f"↩️ استعادة v{v.number}", f"proj:restore:{pid}:{v.number}")] for v in pg.items
                  if v.number != project.current_version]
        rows_kb.append(pagination_row(f"proj:versions:{pid}:{{page}}", pg.page, pg.pages))
        rows_kb.append(back_row(f"proj:open:{pid}"))
        await send_or_edit(c, text, kb(rows_kb))
        await c.answer()

    @router.callback_query(F.data.regexp(r"^proj:restore:\d+:\d+$"))
    async def cb_restore(c: CallbackQuery) -> None:
        _, _, pid_s, ver_s = c.data.split(":")
        pid, ver = int(pid_s), int(ver_s)
        async with APP.session() as s:
            project = await s.get(Project, pid)
            if not project or project.user_id != c.from_user.id:
                await c.answer("❌ غير موجود.", show_alert=True)
                return
            if not (project_dir(pid, ver)).exists():
                await c.answer("❌ ملفات هذا الإصدار غير متوفرة.", show_alert=True)
                return
            new_num = project.current_version + 1
            new_dir = project_dir(pid, new_num)
            shutil.copytree(project_dir(pid, ver), new_dir)
            project.current_version = new_num
            project.status = "uploaded"
            project.updated_at = utcnow()
            s.add(VersionRow(project_id=pid, number=new_num, user_id=c.from_user.id,
                             description=f"استعادة من v{ver}", changed_files="[]"))
            await s.commit()
        await log_event("restore", c.from_user.id, pid, f"from_v={ver}")
        await open_project(c, pid)
        await c.answer("↩️ تمت الاستعادة كإصدار جديد.")

    # ── التصدير ──
    @router.callback_query(F.data.regexp(r"^proj:export:\d+$"))
    async def cb_export(c: CallbackQuery) -> None:
        if not await rl_guard(c, "export"):
            return
        pid = int(c.data.split(":")[2])
        async with APP.session() as s:
            project = await s.get(Project, pid)
            if not project or project.user_id != c.from_user.id:
                await c.answer("❌ غير موجود.", show_alert=True)
                return
            pdir = project_dir(pid, project.current_version)
            out = PATHS.exports / f"project_{pid}_v{project.current_version}.zip"
        try:
            files, redactions = await asyncio.to_thread(build_export_zip, pdir, out)
            note = f"\n🔒 تم إخفاء {redactions} قيمة حساسة." if redactions else ""
            await c.message.answer_document(FSInputFile(out, filename=out.name),
                                            caption=f"📦 {out.name} — {files} ملف.{note}")
            await log_event("export", c.from_user.id, pid, f"files={files} redactions={redactions}")
            await bump_stat("exports")
        except Exception:
            log.exception("export failed pid=%s", pid)
            await c.message.answer("❌ فشل التصدير.")
        await c.answer()

    # ── Customizer ──
    STYLE_ROW = [(label, f"style:pick:{key}") for key, label, _ in COLOR_OPTIONS]

    async def customize_project_list(c: CallbackQuery, page: int) -> None:
        text, _ = await list_projects_text_kb(c.from_user.id, page)
        async with APP.session() as s:
            rows = (await s.execute(select(Project).where(Project.user_id == c.from_user.id)
                                    .order_by(Project.updated_at.desc()))).scalars().all()
        pg = paginate(rows, page, 6)
        rows_kb = [[(f"🛠 {clip(p.name, 22)} (#{p.id})", f"cust:open:{p.id}")] for p in pg.items]
        rows_kb.append(pagination_row("menu:customize:{page}", pg.page, pg.pages))
        rows_kb.append(back_row())
        head = "🛠 <b>اختر مشروعًا للتخصيص</b>" if pg.items else "لا توجد مشاريع بعد. استخدم «📤 رفع مشروع»."
        await send_or_edit(c, head, kb(rows_kb))

    @router.callback_query(F.data.regexp(r"^menu:customize(:\d+)?$"))
    async def cb_customize_entry(c: CallbackQuery) -> None:
        page = int(c.data.split(":")[2]) if c.data.count(":") == 2 else 1
        await customize_project_list(c, page)
        await c.answer()

    def customizer_home_kb(pid: int) -> InlineKeyboardMarkup:
        return kb([
            [("🔘 تعديل الأزرار", f"cust:btns:{pid}:1"), ("📝 تعديل النصوص", f"cust:txts:{pid}:1")],
            [("👁 معاينة التغييرات", f"proj:preview:{pid}"), ("📦 تصدير", f"proj:export:{pid}")],
            [("🔙 لوحة المشروع", f"proj:open:{pid}")],
        ])

    @router.callback_query(F.data.regexp(r"^cust:open:\d+$"))
    async def cb_customize_open(c: CallbackQuery) -> None:
        pid = int(c.data.split(":")[2])
        if not HAVE_LIBCST:
            await c.answer("⚠️ التعديل التلقائي معطّل: مكتبة LibCST غير مثبتة على الخادم.", show_alert=True)
            return
        async with APP.session() as s:
            project = await s.get(Project, pid)
        if not project or project.user_id != c.from_user.id:
            await c.answer("❌ غير موجود.", show_alert=True)
            return
        if project.status != "analyzed":
            await c.answer("⚠️ حلّل المشروع أولًا («🔍 تحليل»).", show_alert=True)
            return
        await send_or_edit(c, f"🛠 <b>تخصيص {esc(project.name)}</b>\nاختر ما تريد تعديله:", customizer_home_kb(pid))
        await c.answer()

    async def list_buttons_kb(pid: int, page: int) -> tuple[str, InlineKeyboardMarkup]:
        async with APP.session() as s:
            project = await s.get(Project, pid)
            rows = (await s.execute(select(ButtonRow).where(ButtonRow.project_id == pid,
                    ButtonRow.version == project.current_version).order_by(ButtonRow.id))).scalars().all()
        pg = paginate(rows, page, 6)
        rows_kb = []
        for b in pg.items:
            label = f"⚠️ {clip(b.text_hint or b.text_expr or '?', 22)}" if b.text_dynamic else f"{clip(b.text or '?', 24)}"
            rows_kb.append([(label, f"btn:open:{b.id}")])
        rows_kb.append(pagination_row(f"cust:btns:{pid}:{{page}}", pg.page, pg.pages))
        rows_kb.append(back_row(f"cust:open:{pid}"))
        return f"🔘 <b>الأزرار</b> ({pg.total}) — اضغط زرًا لتعديله:", kb(rows_kb)

    @router.callback_query(F.data.regexp(r"^cust:btns:\d+:\d+$"))
    async def cb_list_buttons(c: CallbackQuery) -> None:
        _, _, pid_s, page_s = c.data.split(":")
        text, markup = await list_buttons_kb(int(pid_s), int(page_s))
        await send_or_edit(c, text, markup)
        await c.answer()

    def button_detail_kb(b: "ButtonRow") -> InlineKeyboardMarkup:
        rows = []
        if not b.text_dynamic:
            rows.append([("✏️ تعديل النص", f"btn:edittext:{b.id}")])
        else:
            rows.append([("📍 تحديد الموضع يدويًا", f"btn:manual:{b.id}")])
        if b.callback and not b.cb_dynamic:
            rows.append([("✏️ تعديل callback_data", f"btn:editcb:{b.id}")])
        rows.append([(label, f"btn:style:{b.id}:{key}") for key, label, _ in COLOR_OPTIONS[:2]])
        rows.append([(label, f"btn:style:{b.id}:{key}") for key, label, _ in COLOR_OPTIONS[2:]])
        rows.append(back_row(f"cust:btns:{b.project_id}:1"))
        return kb(rows)

    @router.callback_query(F.data.regexp(r"^btn:open:\d+$"))
    async def cb_button_open(c: CallbackQuery) -> None:
        bid = int(c.data.split(":")[2])
        async with APP.session() as s:
            b = await s.get(ButtonRow, bid)
            project = await s.get(Project, b.project_id) if b else None
        if not b or not project or project.user_id != c.from_user.id:
            await c.answer("❌ غير موجود.", show_alert=True)
            return
        lines = [f"🔘 <b>زر</b> ({esc(b.kind)}) — {esc(b.file_path)}:{b.line}",
                 f"النص: {'⚠️ ديناميكي' if b.text_dynamic else esc(b.text)}",
                 f"callback_data: {esc(b.callback) if b.callback else '—'}"
                 f"{' (⚠️ ديناميكي/غير آمن)' if b.cb_dynamic else ''}",
                 f"النمط الحالي: {style_label(b.style)}"]
        if b.text_dynamic:
            lines.append(f"\n⚠️ نص ديناميكي: <code>{esc(b.text_expr)}</code>")
        await send_or_edit(c, "\n".join(lines), button_detail_kb(b))
        await c.answer()

    @router.callback_query(F.data.regexp(r"^btn:style:\d+:\w+$"))
    async def cb_button_style(c: CallbackQuery) -> None:
        _, _, bid_s, key = c.data.split(":")
        if not is_valid_style(key):
            await c.answer("❌ نمط غير صالح.", show_alert=True)
            return
        async with APP.session() as s:
            b = await s.get(ButtonRow, int(bid_s))
            project = await s.get(Project, b.project_id) if b else None
            if not b or not project or project.user_id != c.from_user.id:
                await c.answer("❌ غير موجود.", show_alert=True)
                return
            b.style = key
            await s.commit()
        await c.answer(f"تم ضبط النمط: {style_label(key)} (دلالي داخل النظام فقط)")
        await cb_button_open_redirect(c, b.id)

    async def cb_button_open_redirect(c: CallbackQuery, bid: int) -> None:
        async with APP.session() as s:
            b = await s.get(ButtonRow, bid)
        await send_or_edit(c, f"🔘 تم التحديث.", button_detail_kb(b))

    PENDING_EDIT: dict[int, dict] = {}  # user_id -> {"kind","id","old","file","line","occ"}

    @router.callback_query(F.data.regexp(r"^btn:edittext:\d+$"))
    async def cb_button_edittext(c: CallbackQuery, state: FSMContext) -> None:
        bid = int(c.data.split(":")[2])
        async with APP.session() as s:
            b = await s.get(ButtonRow, bid)
            project = await s.get(Project, b.project_id) if b else None
        if not b or not project or project.user_id != c.from_user.id or b.text_dynamic:
            await c.answer("❌ غير متاح.", show_alert=True)
            return
        PENDING_EDIT[c.from_user.id] = {"kind": "button_text", "pid": project.id, "file": b.file_path,
                                        "line": b.text_line, "occ": b.text_occ, "old": b.text, "row_id": b.id}
        await state.set_state(CustomizeState.waiting_value)
        await send_or_edit(c, f"✏️ القيمة الحالية: <b>{esc(b.text)}</b>\nأرسل القيمة الجديدة:", kb([back_row(f"btn:open:{bid}")]))
        await c.answer()

    @router.callback_query(F.data.regexp(r"^btn:editcb:\d+$"))
    async def cb_button_editcb(c: CallbackQuery, state: FSMContext) -> None:
        bid = int(c.data.split(":")[2])
        async with APP.session() as s:
            b = await s.get(ButtonRow, bid)
            project = await s.get(Project, b.project_id) if b else None
        if not b or not project or project.user_id != c.from_user.id or not b.callback or b.cb_dynamic:
            await c.answer("❌ غير متاح أو غير آمن للتعديل.", show_alert=True)
            return
        async with APP.session() as s:
            proj_res = load_result_light(project)
        safety = proj_res.callbacks.get(b.callback, {"safe": False, "reason": "غير معروف"})
        if not safety.get("safe"):
            await c.answer(f"⚠️ غير آمن: {safety.get('reason')}", show_alert=True)
            return
        PENDING_EDIT[c.from_user.id] = {"kind": "callback_data", "pid": project.id, "file": b.file_path,
                                        "line": b.line, "occ": None, "old": b.callback, "row_id": b.id,
                                        "targets": safety["targets"]}
        await state.set_state(CustomizeState.waiting_value)
        await send_or_edit(c, f"✏️ callback_data الحالي: <code>{esc(b.callback)}</code>\nأرسل القيمة الجديدة "
                            "(أحرف/أرقام/underscore/colon فقط، حتى 64 بايت):", kb([back_row(f"btn:open:{bid}")]))
        await c.answer()

    async def list_texts_kb(pid: int, page: int) -> tuple[str, InlineKeyboardMarkup]:
        async with APP.session() as s:
            project = await s.get(Project, pid)
            rows = (await s.execute(select(TextRow).where(TextRow.project_id == pid,
                    TextRow.version == project.current_version).order_by(TextRow.id))).scalars().all()
        pg = paginate(rows, page, 6)
        rows_kb = []
        for t in pg.items:
            label = f"⚠️ {clip(t.hint or t.expr or '?', 22)}" if t.dynamic else clip(t.text or "?", 26)
            rows_kb.append([(label, f"txt:open:{t.id}")])
        rows_kb.append(pagination_row(f"cust:txts:{pid}:{{page}}", pg.page, pg.pages))
        rows_kb.append(back_row(f"cust:open:{pid}"))
        return f"📝 <b>النصوص</b> ({pg.total}) — اضغط نصًا لتعديله:", kb(rows_kb)

    @router.callback_query(F.data.regexp(r"^cust:txts:\d+:\d+$"))
    async def cb_list_texts(c: CallbackQuery) -> None:
        _, _, pid_s, page_s = c.data.split(":")
        text, markup = await list_texts_kb(int(pid_s), int(page_s))
        await send_or_edit(c, text, markup)
        await c.answer()

    @router.callback_query(F.data.regexp(r"^txt:open:\d+$"))
    async def cb_text_open(c: CallbackQuery) -> None:
        tid = int(c.data.split(":")[2])
        async with APP.session() as s:
            t = await s.get(TextRow, tid)
            project = await s.get(Project, t.project_id) if t else None
        if not t or not project or project.user_id != c.from_user.id:
            await c.answer("❌ غير موجود.", show_alert=True)
            return
        lines = [f"📝 <b>نص</b> — {esc(t.file_path)}:{t.line} ({esc(t.method)})",
                 f"القيمة: {'⚠️ ديناميكي' if t.dynamic else esc(clip(t.text or '', 300))}"]
        rows = [] if t.dynamic else [[("✏️ تعديل", f"txt:edit:{tid}")]]
        if t.dynamic:
            lines.append(f"\n⚠️ نص ديناميكي: <code>{esc(t.expr)}</code>")
            rows.append([("📍 تحديد الموضع يدويًا", f"txt:manual:{tid}")])
        rows.append(back_row(f"cust:txts:{project.id}:1"))
        await send_or_edit(c, "\n".join(lines), kb(rows))
        await c.answer()

    @router.callback_query(F.data.regexp(r"^txt:edit:\d+$"))
    async def cb_text_edit(c: CallbackQuery, state: FSMContext) -> None:
        tid = int(c.data.split(":")[2])
        async with APP.session() as s:
            t = await s.get(TextRow, tid)
            project = await s.get(Project, t.project_id) if t else None
        if not t or not project or project.user_id != c.from_user.id or t.dynamic:
            await c.answer("❌ غير متاح.", show_alert=True)
            return
        PENDING_EDIT[c.from_user.id] = {"kind": "message_text", "pid": project.id, "file": t.file_path,
                                        "line": t.line, "occ": t.occ, "old": t.text, "row_id": t.id}
        await state.set_state(CustomizeState.waiting_value)
        await send_or_edit(c, f"✏️ القيمة الحالية:\n<i>{esc(clip(t.text or '', 300))}</i>\n\nأرسل القيمة الجديدة:",
                           kb([back_row(f"txt:open:{tid}")]))
        await c.answer()

    @router.message(StateFilter(CustomizeState.waiting_value))
    async def on_customize_value(m: Message, state: FSMContext) -> None:
        pend = PENDING_EDIT.get(m.from_user.id)
        if not pend:
            await state.clear()
            await m.answer("❌ لا يوجد تعديل معلّق.")
            return
        new_value = (m.text or "").strip()
        if not new_value:
            await m.answer("❌ القيمة فارغة. أرسل نصًا صالحًا.")
            return
        if pend["kind"] == "callback_data":
            if not CB_RE.match(new_value) or len(new_value.encode()) > 64:
                await m.answer("❌ callback_data غير صالح (أحرف/أرقام/_/: فقط، حتى 64 بايت).")
                return
            async with APP.session() as s:
                project = await s.get(Project, pend["pid"])
                clash = (await s.execute(select(ButtonRow).where(ButtonRow.project_id == pend["pid"],
                        ButtonRow.version == project.current_version, ButtonRow.callback == new_value))).scalar_one_or_none()
            if clash:
                await m.answer("❌ هذه القيمة مستخدمة بالفعل لزر آخر.")
                return
        await state.set_state(None)
        pend["new"] = new_value
        label = {"button_text": "نص زر", "callback_data": "callback_data", "message_text": "نص رسالة"}[pend["kind"]]
        await m.answer(f"📝 <b>معاينة</b>\n{label}:\n{esc(clip(str(pend['old']), 200))} → {esc(clip(new_value, 200))}",
                       reply_markup=kb([confirm_row("edit:confirm", "edit:cancel")]))

    @router.callback_query(F.data == "edit:cancel")
    async def cb_edit_cancel(c: CallbackQuery, state: FSMContext) -> None:
        PENDING_EDIT.pop(c.from_user.id, None)
        await state.clear()
        await send_or_edit(c, "❌ تم إلغاء التعديل.", kb([back_row()]))
        await c.answer()

    @router.callback_query(F.data == "edit:confirm")
    async def cb_edit_confirm(c: CallbackQuery, state: FSMContext) -> None:
        if not await rl_guard(c, "edit"):
            return
        pend = PENDING_EDIT.pop(c.from_user.id, None)
        await state.clear()
        if not pend:
            await c.answer("❌ لا يوجد تعديل معلّق.", show_alert=True)
            return
        pid = pend["pid"]
        async with APP.session() as s:
            project = await s.get(Project, pid)
        if not project or project.user_id != c.from_user.id:
            await c.answer("❌ غير موجود.", show_alert=True)
            return
        pdir = project_dir(pid, project.current_version)
        try:
            if pend["kind"] == "callback_data":
                ops_by_file: dict[str, list[EditOp]] = defaultdict(list)
                for f, line, occ in pend["targets"]:
                    ops_by_file[f].append(EditOp(f, line, occ, pend["old"], pend["new"], "callback_data"))
            else:
                ops_by_file = {pend["file"]: [EditOp(pend["file"], pend["line"], pend["occ"],
                                                     str(pend["old"]), pend["new"], pend["kind"])]}
            backup_project(pdir, pid)
            changed = await asyncio.to_thread(apply_project_edits, pdir, dict(ops_by_file))
            async with APP.session() as s:
                project = await s.get(Project, pid)
                new_ver = project.current_version + 1
                new_dir = project_dir(pid, new_ver)
                shutil.copytree(pdir, new_dir)
                for rel, size in ((p.relative_to(new_dir).as_posix(), p.stat().st_size)
                                  for p in new_dir.rglob("*") if p.is_file()):
                    s.add(ProjectFile(project_id=pid, version=new_ver, path=rel, size=size,
                                      sha256=sha256_file(new_dir / rel), is_python=rel.endswith(".py")))
                project.current_version = new_ver
                project.updated_at = utcnow()
                s.add(VersionRow(project_id=pid, number=new_ver, user_id=c.from_user.id,
                                 description=f"تعديل: {pend['kind']}", changed_files=json.dumps(changed)))
                await s.commit()
            try:
                res = await run_analysis(pid)
                _ = res
            except Exception:
                log.exception("re-analyze after edit failed pid=%s", pid)
            await log_event("edit", c.from_user.id, pid, f"kind={pend['kind']} v={new_ver}")
            await send_or_edit(c, f"✅ تم التعديل وحُفظ كإصدار جديد (v{new_ver}).", customizer_home_kb(pid))
        except EditError as exc:
            await send_or_edit(c, f"❌ فشل التعديل: {exc}\nلم تُحفظ أي نسخة جديدة.", customizer_home_kb(pid))
        except Exception:
            log.exception("apply edit failed pid=%s", pid)
            await send_or_edit(c, "❌ حدث خطأ غير متوقع أثناء التعديل.", customizer_home_kb(pid))
        await c.answer()

    # ── تحديد الموضع يدويًا للعناصر الديناميكية ──
    @router.callback_query(F.data.regexp(r"^(btn|txt):manual:\d+$"))
    async def cb_manual_pick(c: CallbackQuery, state: FSMContext) -> None:
        kind, _, rid_s = c.data.split(":")
        rid = int(rid_s)
        model = ButtonRow if kind == "btn" else TextRow
        async with APP.session() as s:
            row = await s.get(model, rid)
            project = await s.get(Project, row.project_id) if row else None
        if not row or not project or project.user_id != c.from_user.id:
            await c.answer("❌ غير موجود.", show_alert=True)
            return
        hint = (row.text_hint if kind == "btn" else row.hint) or ""
        PENDING_EDIT[c.from_user.id] = {"kind": "manual_search", "pid": project.id, "row_kind": kind, "row_id": rid}
        await state.set_state(CustomizeState.waiting_manual_pick)
        await send_or_edit(c, f"📍 هذا العنصر ديناميكي. أرسل اسم المفتاح/الثابت للبحث عنه "
                           f"(اقتراح: <code>{esc(hint)}</code>) أو أرسل النص الحالي بالضبط:", kb([back_row()]))
        await c.answer()

    @router.message(StateFilter(CustomizeState.waiting_manual_pick))
    async def on_manual_search(m: Message, state: FSMContext) -> None:
        pend = PENDING_EDIT.get(m.from_user.id)
        if not pend or pend.get("kind") != "manual_search":
            await state.clear()
            return
        pid = pend["pid"]
        async with APP.session() as s:
            project = await s.get(Project, pid)
        pdir = project_dir(pid, project.current_version)
        sources = {p.relative_to(pdir).as_posix(): p.read_text("utf-8", "ignore")
                  for p in pdir.rglob("*.py") if p.is_file()}
        cands = await asyncio.to_thread(find_candidates, sources, (m.text or "").strip())
        if not cands:
            await m.answer("❌ لم يُعثر على مواضع آمنة مطابقة. جرّب نصًا/مفتاحًا آخر أو ألغِ.")
            return
        rows = [[(c["label"], f"manual:pick:{i}")] for i, c in enumerate(cands[:8])]
        rows.append(back_row())
        PENDING_EDIT[m.from_user.id] = {**pend, "candidates": cands}
        await state.clear()
        await m.answer("📍 اختر الموضع الصحيح:", reply_markup=kb(rows))

    @router.callback_query(F.data.regexp(r"^manual:pick:\d+$"))
    async def cb_manual_confirm(c: CallbackQuery, state: FSMContext) -> None:
        idx = int(c.data.split(":")[2])
        pend = PENDING_EDIT.get(c.from_user.id)
        if not pend or "candidates" not in pend or idx >= len(pend["candidates"]):
            await c.answer("❌ منتهي الصلاحية.", show_alert=True)
            return
        cand = pend["candidates"][idx]
        PENDING_EDIT[c.from_user.id] = {"kind": "button_text" if pend["row_kind"] == "btn" else "message_text",
                                        "pid": pend["pid"], "file": cand["file"], "line": cand["line"],
                                        "occ": cand["occ"], "old": cand["value"], "row_id": pend["row_id"]}
        await state.set_state(CustomizeState.waiting_value)
        await send_or_edit(c, f"✏️ القيمة الحالية: <b>{esc(cand['value'])}</b>\nأرسل القيمة الجديدة:", kb([back_row()]))
        await c.answer()

    # ── الاشتراك ──
    @router.callback_query(F.data == "menu:sub")
    async def cb_sub(c: CallbackQuery) -> None:
        async with APP.session() as s:
            user = await s.get(User, c.from_user.id)
            plan = await effective_plan(s, user)
            plans = (await s.execute(select(Plan).where(Plan.is_active == True))).scalars().all()  # noqa: E712
        lines = [f"💎 خطتك الحالية: <b>{esc(plan.name)}</b>"
                f"{' (تنتهي ' + fmt_dt(user.plan_expires_at) + ')' if user.plan_expires_at else ''}",
                f"  📁 مشاريع حتى {plan.max_projects} | 🛠 تعديلات/يوم حتى {plan.max_edits_per_day} | ⬆️ رفع حتى {plan.max_upload_mb}MB",
                "\n📋 <b>الخطط المتاحة:</b>"]
        for p in plans:
            lines.append(f"• {esc(p.name)} — {p.price:g}$ / {p.duration_days or '∞'} يوم — {esc(p.description)}")
        rows = [[(f"طلب ترقية إلى {p.name}", f"sub:req:{p.id}")] for p in plans if p.name != plan.name]
        rows.append([("🎟 لدي كود خصم", "sub:promo")])
        rows.append(back_row())
        await send_or_edit(c, "\n".join(lines), kb(rows))
        await c.answer()

    @router.callback_query(F.data.regexp(r"^sub:req:\d+$"))
    async def cb_sub_request(c: CallbackQuery) -> None:
        plan_id = int(c.data.split(":")[2])
        async with APP.session() as s:
            plan = await s.get(Plan, plan_id)
            if not plan:
                await c.answer("❌ خطة غير موجودة.", show_alert=True)
                return
            s.add(Subscription(user_id=c.from_user.id, plan_id=plan_id, status="pending", price=plan.price))
            await s.commit()
        await log_event("subscription", c.from_user.id, details=f"requested plan={plan.name}")
        for admin_id in await admin_ids():
            with contextlib.suppress(TelegramAPIError):
                await c.bot.send_message(admin_id, f"💎 طلب ترقية جديد من <code>{c.from_user.id}</code> "
                                         f"إلى خطة <b>{esc(plan.name)}</b>. راجع «لوحة الإدارة → الاشتراكات».")
        await send_or_edit(c, "✅ أُرسل طلبك وسيراجعه المالك قريبًا.", kb([back_row()]))
        await c.answer()

    class PromoState(StatesGroup):
        waiting_code = State()

    @router.callback_query(F.data == "sub:promo")
    async def cb_sub_promo(c: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(PromoState.waiting_code)
        await send_or_edit(c, "🎟 أرسل كود الخصم:", kb([back_row()]))
        await c.answer()

    @router.message(StateFilter(PromoState.waiting_code))
    async def on_promo_code(m: Message, state: FSMContext) -> None:
        await state.clear()
        code = one_line(m.text or "", 40).upper()
        async with APP.session() as s:
            promo = (await s.execute(select(PromoCode).where(PromoCode.code == code))).scalar_one_or_none()
            valid = (promo and promo.active and (promo.expires_at is None or promo.expires_at > utcnow())
                    and (promo.max_uses == 0 or promo.used_count < promo.max_uses))
            if not valid:
                await m.answer("❌ الكود غير صالح أو منتهي.")
                return
            user = await s.get(User, m.from_user.id)
            user.pending_promo = code
            await s.commit()
        await m.answer(f"✅ كود صالح: خصم {promo.value:g}"
                       f"{'%' if promo.discount_type == 'percent' else (' يوم' if promo.discount_type == 'days' else '$')}."
                       " سيُطبَّق تلقائيًا عند مراجعة طلب الترقية القادم.")

    # ── الدعم (Tickets) ──
    @router.callback_query(F.data == "menu:support")
    async def cb_support(c: CallbackQuery) -> None:
        async with APP.session() as s:
            tickets = (await s.execute(select(Ticket).where(Ticket.user_id == c.from_user.id)
                                       .order_by(Ticket.created_at.desc()).limit(10))).scalars().all()
        lines = [f"• #{t.id} {esc(t.subject)} — {'🟢 مفتوحة' if t.status == 'open' else '🔴 مغلقة'}" for t in tickets]
        text = "🎫 <b>الدعم</b>\n\n" + ("\n".join(lines) if lines else "لا توجد تذاكر سابقة.")
        rows = [[(f"عرض #{t.id}", f"tk:open:{t.id}")] for t in tickets]
        rows.append([("➕ فتح تذكرة جديدة", "tk:new")])
        rows.append(back_row())
        await send_or_edit(c, text, kb(rows))
        await c.answer()

    @router.callback_query(F.data == "tk:new")
    async def cb_ticket_new(c: CallbackQuery, state: FSMContext) -> None:
        if not await rl_guard(c, "support"):
            return
        await state.set_state(TicketState.subject)
        await send_or_edit(c, "🎫 اكتب عنوانًا مختصرًا للمشكلة:", kb([back_row()]))
        await c.answer()

    @router.message(StateFilter(TicketState.subject))
    async def on_ticket_subject(m: Message, state: FSMContext) -> None:
        await state.update_data(subject=one_line(m.text or "بدون عنوان", 100))
        await state.set_state(TicketState.message)
        await m.answer("✍️ اكتب وصف المشكلة بالتفصيل:")

    @router.message(StateFilter(TicketState.message))
    async def on_ticket_message(m: Message, state: FSMContext) -> None:
        data = await state.get_data()
        await state.clear()
        async with APP.session() as s:
            s.add(ticket := Ticket(user_id=m.from_user.id, subject=data.get("subject", "بدون عنوان")))
            await s.flush()
            s.add(TicketMessage(ticket_id=ticket.id, sender_id=m.from_user.id, is_staff=False, text=m.text or ""))
            await s.commit()
            tid = ticket.id
        await log_event("support", m.from_user.id, details=f"ticket={tid}")
        await m.answer(f"✅ تم فتح التذكرة #{tid}. سيتم الرد عليك قريبًا.")
        for admin_id in await admin_ids():
            with contextlib.suppress(TelegramAPIError):
                await m.bot.send_message(admin_id, f"🎫 تذكرة جديدة #{tid} من <code>{m.from_user.id}</code>: "
                                         f"{esc(data.get('subject',''))}\nاستخدم /tickets للرد.")

    async def render_ticket(c_or_m: Any, tid: int, viewer_id: int, is_staff_view: bool) -> tuple[str, InlineKeyboardMarkup]:
        async with APP.session() as s:
            ticket = await s.get(Ticket, tid)
            msgs = (await s.execute(select(TicketMessage).where(TicketMessage.ticket_id == tid)
                                    .order_by(TicketMessage.created_at))).scalars().all()
        lines = [f"🎫 <b>#{ticket.id} — {esc(ticket.subject)}</b> ({'🟢 مفتوحة' if ticket.status=='open' else '🔴 مغلقة'})\n"]
        for msg in msgs[-15:]:
            who = "👑 الدعم" if msg.is_staff else "👤 أنت" if not is_staff_view else f"👤 {msg.sender_id}"
            lines.append(f"{who}: {esc(clip(msg.text, 300))}")
        rows = []
        if ticket.status == "open":
            rows.append([("✍️ رد", f"tk:reply:{tid}")])
            if is_staff_view:
                rows.append([("🔒 إغلاق", f"tk:close:{tid}")])
        rows.append(back_row("admin:tickets:1" if is_staff_view else "menu:support"))
        return "\n".join(lines), kb(rows)

    @router.callback_query(F.data.regexp(r"^tk:open:\d+$"))
    async def cb_ticket_open(c: CallbackQuery) -> None:
        tid = int(c.data.split(":")[2])
        async with APP.session() as s:
            ticket = await s.get(Ticket, tid)
        is_staff = await is_admin_id(c.from_user.id)
        if not ticket or (ticket.user_id != c.from_user.id and not is_staff):
            await c.answer("❌ غير موجودة.", show_alert=True)
            return
        text, markup = await render_ticket(c, tid, c.from_user.id, is_staff)
        await send_or_edit(c, text, markup)
        await c.answer()

    @router.callback_query(F.data.regexp(r"^tk:reply:\d+$"))
    async def cb_ticket_reply(c: CallbackQuery, state: FSMContext) -> None:
        tid = int(c.data.split(":")[2])
        await state.set_state(TicketState.reply)
        await state.update_data(ticket_id=tid)
        await send_or_edit(c, "✍️ اكتب ردّك:", kb([back_row(f"tk:open:{tid}")]))
        await c.answer()

    @router.message(StateFilter(TicketState.reply))
    async def on_ticket_reply(m: Message, state: FSMContext) -> None:
        data = await state.get_data()
        tid = data.get("ticket_id")
        await state.clear()
        is_staff = await is_admin_id(m.from_user.id)
        async with APP.session() as s:
            ticket = await s.get(Ticket, tid)
            if not ticket or (ticket.user_id != m.from_user.id and not is_staff) or ticket.status != "open":
                await m.answer("❌ لا يمكن الرد على هذه التذكرة.")
                return
            s.add(TicketMessage(ticket_id=tid, sender_id=m.from_user.id, is_staff=is_staff, text=m.text or ""))
            await s.commit()
            notify_id = ticket.user_id if is_staff else APP.owner_id
        with contextlib.suppress(TelegramAPIError):
            await m.bot.send_message(notify_id, f"🎫 رد جديد على تذكرة #{tid}." + ("" if is_staff else " استخدم /tickets."))
        text, markup = await render_ticket(m, tid, m.from_user.id, is_staff)
        await m.answer(text, reply_markup=markup)

    @router.callback_query(F.data.regexp(r"^tk:close:\d+$"))
    async def cb_ticket_close(c: CallbackQuery) -> None:
        if not await is_admin_id(c.from_user.id):
            await c.answer("🚫 للمالك فقط.", show_alert=True)
            return
        tid = int(c.data.split(":")[2])
        async with APP.session() as s:
            ticket = await s.get(Ticket, tid)
            ticket.status, ticket.closed_at = "closed", utcnow()
            await s.commit()
            uid = ticket.user_id
        with contextlib.suppress(TelegramAPIError):
            await c.bot.send_message(uid, f"🔒 تم إغلاق تذكرتك #{tid}.")
        await send_or_edit(c, "🔒 تم إغلاق التذكرة.", kb([back_row("admin:tickets:1")]))
        await c.answer()

    # ── إحصائياتي + الإحالة ──
    @router.callback_query(F.data == "menu:mystats")
    async def cb_mystats(c: CallbackQuery) -> None:
        async with APP.session() as s:
            user = await s.get(User, c.from_user.id)
            plan = await effective_plan(s, user)
            n_proj = await count_rows(s, Project, Project.user_id == c.from_user.id)
            n_ref = await count_rows(s, Referral, Referral.referrer_id == c.from_user.id)
        me = await c.bot.me()
        link = f"https://t.me/{me.username}?start=ref_{user.referral_code}"
        text = (f"📊 <b>إحصائياتك</b>\n\n💎 الخطة: {esc(plan.name)}\n📁 المشاريع: {n_proj}/{plan.max_projects}\n"
                f"🔗 الإحالات: {n_ref}\nكود إحالتك: <code>{esc(user.referral_code)}</code>\n"
                f"رابطك: {esc(link)}")
        await send_or_edit(c, text, kb([back_row()]))
        await c.answer()

    # ═════════════════════════════════════════════════════════════════════
    # لوحة الإدارة (OWNER_ID / admins فقط)
    # ═════════════════════════════════════════════════════════════════════
    def admin_home_kb() -> InlineKeyboardMarkup:
        return kb([
            [("👥 المستخدمون", "admin:users:1"), ("📊 الإحصائيات", "admin:stats")],
            [("📁 المشاريع", "admin:projects:1"), ("📢 Broadcast", "admin:broadcast")],
            [("🚫 الحظر", "admin:bans:1"), ("💎 الاشتراكات", "admin:subs:1")],
            [("🎟 Promo Codes", "admin:promos:1"), ("🎫 الدعم", "admin:tickets:1")],
            [("⚙️ الإعدادات", "admin:settings"), ("📜 Logs", "admin:logs:1")],
            [("🔙 القائمة الرئيسية", "menu:home")],
        ])

    @router.callback_query(F.data == "admin:home")
    @require_owner
    async def cb_admin_home(c: CallbackQuery) -> None:
        await send_or_edit(c, "👑 <b>لوحة الإدارة</b>", admin_home_kb())
        await c.answer()

    @router.callback_query(F.data == "admin:stats")
    @require_owner
    async def cb_admin_stats(c: CallbackQuery) -> None:
        await send_or_edit(c, stats_text(await collect_stats()), kb([back_row("admin:home")]))
        await c.answer()

    @router.callback_query(F.data.regexp(r"^admin:users:\d+$"))
    @require_owner
    async def cb_admin_users(c: CallbackQuery) -> None:
        page = int(c.data.split(":")[2])
        async with APP.session() as s:
            rows = (await s.execute(select(User).order_by(User.created_at.desc()))).scalars().all()
        pg = paginate(rows, page, 8)
        lines = [f"• <code>{u.id}</code> {esc(u.username or u.full_name or '—')} — "
                f"{'🚫' if False else ''}آخر ظهور {fmt_dt(u.last_seen)}" for u in pg.items]
        rows_kb = [pagination_row("admin:users:{page}", pg.page, pg.pages), back_row("admin:home")]
        await send_or_edit(c, f"👥 <b>المستخدمون</b> ({pg.total})\n\n" + "\n".join(lines), kb(rows_kb))
        await c.answer()

    @router.callback_query(F.data.regexp(r"^admin:projects:\d+$"))
    @require_owner
    async def cb_admin_projects(c: CallbackQuery) -> None:
        page = int(c.data.split(":")[2])
        async with APP.session() as s:
            rows = (await s.execute(select(Project).order_by(Project.created_at.desc()))).scalars().all()
        pg = paginate(rows, page, 8)
        lines = [f"#{p.id} {esc(p.name)} — 👤<code>{p.user_id}</code> — {STATUS_LABEL.get(p.status, p.status)}"
                for p in pg.items]
        rows_kb = [pagination_row("admin:projects:{page}", pg.page, pg.pages), back_row("admin:home")]
        await send_or_edit(c, f"📁 <b>كل المشاريع</b> ({pg.total})\n\n" + "\n".join(lines), kb(rows_kb))
        await c.answer()

    # ── Broadcast ──
    @router.callback_query(F.data == "admin:broadcast")
    @require_owner
    async def cb_admin_broadcast(c: CallbackQuery, state: FSMContext) -> None:
        if not await rl_guard(c, "broadcast"):
            return
        await state.set_state(BroadcastState.waiting_content)
        await send_or_edit(c, "📢 أرسل نص/رسالة الـ Broadcast الآن:", kb([back_row("admin:home")]))
        await c.answer()

    _BROADCAST_PENDING: dict[int, Message] = {}

    @router.message(StateFilter(BroadcastState.waiting_content))
    async def on_broadcast_content(m: Message, state: FSMContext) -> None:
        await state.clear()
        if not await is_admin_id(m.from_user.id):
            return
        _BROADCAST_PENDING[m.from_user.id] = m
        preview = clip_message(m.text or m.caption or "<وسائط بلا نص>")
        await m.answer(f"📢 <b>معاينة الإرسال:</b>\n\n{esc(preview)}",
                       reply_markup=kb([confirm_row("bc:send", "bc:cancel")]))

    @router.callback_query(F.data == "bc:cancel")
    @require_owner
    async def cb_bc_cancel(c: CallbackQuery) -> None:
        _BROADCAST_PENDING.pop(c.from_user.id, None)
        await send_or_edit(c, "❌ أُلغي البث.", kb([back_row("admin:home")]))
        await c.answer()

    @router.callback_query(F.data == "bc:send")
    @require_owner
    async def cb_bc_send(c: CallbackQuery) -> None:
        src = _BROADCAST_PENDING.pop(c.from_user.id, None)
        if not src:
            await c.answer("❌ لا يوجد بث معلّق.", show_alert=True)
            return
        if APP.broadcasting:
            await c.answer("⏳ يوجد بث قيد التنفيذ بالفعل.", show_alert=True)
            return
        APP.broadcasting = True
        await send_or_edit(c, "⏳ جاري الإرسال...", None)
        await c.answer()
        asyncio.create_task(_run_broadcast(src, c.message.chat.id))

    async def _run_broadcast(src: Message, notify_chat: int) -> None:
        sent = failed = 0
        try:
            async with APP.session() as s:
                ids = [uid for (uid,) in (await s.execute(select(User.id))).all()]
            for uid in ids:
                try:
                    await src.copy_to(uid)
                    sent += 1
                except TelegramRetryAfter as exc:
                    await asyncio.sleep(getattr(exc, "retry_after", 2) + 1)
                    with contextlib.suppress(TelegramAPIError):
                        await src.copy_to(uid)
                        sent += 1
                except (TelegramForbiddenError, TelegramBadRequest):
                    failed += 1
                except TelegramAPIError:
                    failed += 1
                await asyncio.sleep(0.05)
        finally:
            APP.broadcasting = False
            await log_event("broadcast", src.from_user.id, details=f"sent={sent} failed={failed}")
            with contextlib.suppress(TelegramAPIError):
                await APP.bot.send_message(notify_chat, f"✅ اكتمل البث: نجح {sent} / فشل {failed}.")

    # ── الحظر ──
    @router.callback_query(F.data.regexp(r"^admin:bans:\d+$"))
    @require_owner
    async def cb_admin_bans(c: CallbackQuery) -> None:
        page = int(c.data.split(":")[2])
        async with APP.session() as s:
            rows = (await s.execute(select(Ban).order_by(Ban.created_at.desc()))).scalars().all()
        pg = paginate(rows, page, 8)
        lines = [f"• <code>{b.user_id}</code> — {esc(b.reason or '—')}" for b in pg.items]
        text = f"🚫 <b>المحظورون</b> ({pg.total})\n\n" + ("\n".join(lines) if lines else "لا يوجد.")
        rows_kb = [[("➕ حظر مستخدم", "admin:ban:new"), ("➖ فك حظر", "admin:ban:remove")],
                  pagination_row("admin:bans:{page}", pg.page, pg.pages), back_row("admin:home")]
        await send_or_edit(c, text, kb(rows_kb))
        await c.answer()

    @router.callback_query(F.data == "admin:ban:new")
    @require_owner
    async def cb_ban_new(c: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(AdminState.ban_user)
        await send_or_edit(c, "🚫 أرسل: <code>user_id سبب الحظر</code>", kb([back_row("admin:bans:1")]))
        await c.answer()

    @router.message(StateFilter(AdminState.ban_user))
    async def on_ban_input(m: Message, state: FSMContext) -> None:
        await state.clear()
        if not await is_admin_id(m.from_user.id):
            return
        parts = (m.text or "").split(maxsplit=1)
        uid = to_int(parts[0]) if parts else None
        if uid is None:
            await m.answer("❌ صيغة غير صحيحة.")
            return
        async with APP.session() as s:
            if await s.get(Ban, uid) is None:
                s.add(Ban(user_id=uid, reason=parts[1] if len(parts) > 1 else "", banned_by=m.from_user.id))
                await s.commit()
        await log_event("ban", m.from_user.id, details=f"target={uid}")
        await m.answer(f"✅ تم حظر <code>{uid}</code>.")

    @router.callback_query(F.data == "admin:ban:remove")
    @require_owner
    async def cb_ban_remove(c: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(AdminState.unban_user)
        await send_or_edit(c, "➖ أرسل user_id لفك الحظر عنه:", kb([back_row("admin:bans:1")]))
        await c.answer()

    @router.message(StateFilter(AdminState.unban_user))
    async def on_unban_input(m: Message, state: FSMContext) -> None:
        await state.clear()
        if not await is_admin_id(m.from_user.id):
            return
        uid = to_int((m.text or "").strip())
        if uid is None:
            await m.answer("❌ رقم غير صالح.")
            return
        async with APP.session() as s:
            await s.execute(delete(Ban).where(Ban.user_id == uid))
            await s.commit()
        await log_event("unban", m.from_user.id, details=f"target={uid}")
        await m.answer(f"✅ تم فك الحظر عن <code>{uid}</code>.")

    # ── الاشتراكات (مراجعة طلبات) ──
    @router.callback_query(F.data.regexp(r"^admin:subs:\d+$"))
    @require_owner
    async def cb_admin_subs(c: CallbackQuery) -> None:
        page = int(c.data.split(":")[2])
        async with APP.session() as s:
            rows = (await s.execute(select(Subscription).where(Subscription.status == "pending")
                                    .order_by(Subscription.created_at))).scalars().all()
        pg = paginate(rows, page, 6)
        rows_kb = [[(f"مراجعة #{sub.id} (u{sub.user_id})", f"admin:subopen:{sub.id}")] for sub in pg.items]
        rows_kb.append(pagination_row("admin:subs:{page}", pg.page, pg.pages))
        rows_kb.append(back_row("admin:home"))
        text = f"💎 <b>طلبات ترقية معلّقة</b> ({pg.total})"
        await send_or_edit(c, text, kb(rows_kb))
        await c.answer()

    @router.callback_query(F.data.regexp(r"^admin:subopen:\d+$"))
    @require_owner
    async def cb_admin_sub_open(c: CallbackQuery) -> None:
        sid = int(c.data.split(":")[2])
        async with APP.session() as s:
            sub = await s.get(Subscription, sid)
            plan = await s.get(Plan, sub.plan_id) if sub else None
        if not sub or not plan:
            await c.answer("❌ غير موجود.", show_alert=True)
            return
        text = f"💎 طلب #{sid}\n👤 <code>{sub.user_id}</code>\n📦 خطة: {esc(plan.name)} ({plan.price:g}$)"
        await send_or_edit(c, text, kb([confirm_row(f"admin:subyes:{sid}", f"admin:subno:{sid}"),
                                        back_row("admin:subs:1")]))
        await c.answer()

    @router.callback_query(F.data.regexp(r"^admin:sub(yes|no):\d+$"))
    @require_owner
    async def cb_admin_sub_decide(c: CallbackQuery) -> None:
        approve = ":subyes:" in c.data
        sid = int(c.data.split(":")[2])
        async with APP.session() as s:
            sub = await s.get(Subscription, sid)
            plan = await s.get(Plan, sub.plan_id) if sub else None
            user = await s.get(User, sub.user_id) if sub else None
            if not sub or sub.status != "pending":
                await c.answer("❌ غير متاح.", show_alert=True)
                return
            if approve:
                days = plan.duration_days or 3650
                if user.pending_promo:
                    promo = (await s.execute(select(PromoCode).where(PromoCode.code == user.pending_promo))).scalar_one_or_none()
                    if promo and promo.discount_type == "days":
                        days += int(promo.value)
                    if promo:
                        promo.used_count += 1
                        sub.promo_code = promo.code
                    user.pending_promo = None
                user.plan_id, user.plan_expires_at = plan.id, utcnow() + timedelta(days=days)
                sub.status, sub.started_at, sub.expires_at = "active", utcnow(), user.plan_expires_at
            else:
                sub.status = "rejected"
            await s.commit()
            uid, pname = sub.user_id, plan.name
        with contextlib.suppress(TelegramAPIError):
            await c.bot.send_message(uid, f"{'✅ تمت الموافقة على ترقيتك إلى ' + pname + '!' if approve else '❌ رُفض طلب الترقية.'}")
        await log_event("subscription", c.from_user.id, details=f"decide sub={sid} approve={approve}")
        await send_or_edit(c, "✅ تم." , kb([back_row("admin:subs:1")]))
        await c.answer()

    # ── Promo Codes ──
    @router.callback_query(F.data.regexp(r"^admin:promos:\d+$"))
    @require_owner
    async def cb_admin_promos(c: CallbackQuery) -> None:
        page = int(c.data.split(":")[2])
        async with APP.session() as s:
            rows = (await s.execute(select(PromoCode).order_by(PromoCode.created_at.desc()))).scalars().all()
        pg = paginate(rows, page, 6)
        lines = [f"• <code>{esc(p.code)}</code> — {p.value:g}{'%' if p.discount_type=='percent' else ('د' if p.discount_type=='days' else '$')} "
                f"— استُخدم {p.used_count}/{p.max_uses or '∞'} — {'🟢' if p.active else '🔴'}" for p in pg.items]
        text = f"🎟 <b>Promo Codes</b> ({pg.total})\n\n" + ("\n".join(lines) if lines else "لا يوجد.")
        rows_kb = [[("➕ إنشاء كود", "admin:promo:new")], pagination_row("admin:promos:{page}", pg.page, pg.pages),
                  back_row("admin:home")]
        await send_or_edit(c, text, kb(rows_kb))
        await c.answer()

    @router.callback_query(F.data == "admin:promo:new")
    @require_owner
    async def cb_promo_new(c: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(AdminState.promo_create)
        await send_or_edit(c, "🎟 أرسل: <code>الكود النوع(percent|fixed|days) القيمة [أقصى_استخدام] [أيام_الصلاحية]</code>\n"
                           "مثال: <code>MATRI50 percent 50 100 30</code>", kb([back_row("admin:promos:1")]))
        await c.answer()

    @router.message(StateFilter(AdminState.promo_create))
    async def on_promo_create(m: Message, state: FSMContext) -> None:
        await state.clear()
        if not await is_admin_id(m.from_user.id):
            return
        parts = (m.text or "").split()
        if len(parts) < 3 or parts[1] not in ("percent", "fixed", "days"):
            await m.answer("❌ صيغة غير صحيحة.")
            return
        code = parts[0].upper()
        try:
            value = float(parts[2])
            max_uses = int(parts[3]) if len(parts) > 3 else 0
            expires = utcnow() + timedelta(days=int(parts[4])) if len(parts) > 4 else None
        except ValueError:
            await m.answer("❌ قيم رقمية غير صالحة.")
            return
        async with APP.session() as s:
            if (await s.execute(select(PromoCode).where(PromoCode.code == code))).scalar_one_or_none():
                await m.answer("❌ الكود موجود مسبقًا.")
                return
            s.add(PromoCode(code=code, discount_type=parts[1], value=value, max_uses=max_uses, expires_at=expires))
            await s.commit()
        await log_event("admin", m.from_user.id, details=f"promo_created {code}")
        await m.answer(f"✅ أُنشئ الكود <code>{esc(code)}</code>.")

    # ── الإعدادات ──
    @router.callback_query(F.data == "admin:settings")
    @require_owner
    async def cb_admin_settings(c: CallbackQuery) -> None:
        maintenance = await get_setting("maintenance", "0")
        text = f"⚙️ <b>الإعدادات</b>\n\nوضع الصيانة: {'🟢 مفعّل' if maintenance == '1' else '🔴 متوقف'}"
        rows = [[("🔁 تبديل وضع الصيانة", "admin:togglemaint")], back_row("admin:home")]
        await send_or_edit(c, text, kb(rows))
        await c.answer()

    @router.callback_query(F.data == "admin:togglemaint")
    @require_owner
    async def cb_toggle_maint(c: CallbackQuery) -> None:
        cur = await get_setting("maintenance", "0")
        await set_setting("maintenance", "0" if cur == "1" else "1")
        await cb_admin_settings(c)

    # ── Logs ──
    @router.callback_query(F.data.regexp(r"^admin:logs:\d+$"))
    @require_owner
    async def cb_admin_logs(c: CallbackQuery) -> None:
        page = int(c.data.split(":")[2])
        async with APP.session() as s:
            rows = (await s.execute(select(LogRow).order_by(LogRow.created_at.desc()).limit(300))).scalars().all()
        pg = paginate(rows, page, 10)
        lines = [f"• {fmt_dt(l.created_at)} <code>{l.user_id}</code> {esc(l.action)} "
                f"{'#' + str(l.project_id) if l.project_id else ''} {esc(clip(l.details, 50))}" for l in pg.items]
        text = f"📜 <b>Logs</b> (آخر {pg.total})\n\n" + "\n".join(lines)
        rows_kb = [pagination_row("admin:logs:{page}", pg.page, pg.pages), back_row("admin:home")]
        await send_or_edit(c, text, kb(rows_kb))
        await c.answer()

    @router.callback_query(F.data.regexp(r"^admin:tickets:\d+$"))
    @require_owner
    async def cb_admin_tickets(c: CallbackQuery) -> None:
        page = int(c.data.split(":")[2])
        async with APP.session() as s:
            rows = (await s.execute(select(Ticket).where(Ticket.status == "open")
                                    .order_by(Ticket.created_at))).scalars().all()
        pg = paginate(rows, page, 8)
        rows_kb = [[(f"#{t.id} {clip(t.subject, 20)}", f"tk:open:{t.id}")] for t in pg.items]
        rows_kb.append(pagination_row("admin:tickets:{page}", pg.page, pg.pages))
        rows_kb.append(back_row("admin:home"))
        text = f"🎫 <b>التذاكر المفتوحة</b> ({pg.total})"
        await send_or_edit(c, text, kb(rows_kb))
        await c.answer()

    # ── أوامر المالك (Slash Commands) ──
    @router.message(Command("admin"))
    async def cmd_admin(m: Message) -> None:
        if not await is_admin_id(m.from_user.id):
            return
        await m.answer("👑 لوحة الإدارة", reply_markup=admin_home_kb())

    @router.message(Command("stats"))
    async def cmd_stats(m: Message) -> None:
        if not await is_admin_id(m.from_user.id):
            return
        await m.answer(stats_text(await collect_stats()))

    @router.message(Command("broadcast"))
    async def cmd_broadcast(m: Message, state: FSMContext) -> None:
        if not await is_admin_id(m.from_user.id):
            return
        await state.set_state(BroadcastState.waiting_content)
        await m.answer("📢 أرسل محتوى البث الآن:")

    @router.message(Command("users"))
    async def cmd_users(m: Message) -> None:
        if not await is_admin_id(m.from_user.id):
            return
        async with APP.session() as s:
            n = await count_rows(s, User)
        await m.answer(f"👥 عدد المستخدمين: {n}\nاستخدم /admin لعرض القائمة كاملة.")

    @router.message(Command("logs"))
    async def cmd_logs(m: Message) -> None:
        if not await is_admin_id(m.from_user.id):
            return
        async with APP.session() as s:
            rows = (await s.execute(select(LogRow).order_by(LogRow.created_at.desc()).limit(15))).scalars().all()
        text = "\n".join(f"{fmt_dt(l.created_at)} {esc(l.action)} u{l.user_id}" for l in rows) or "لا يوجد."
        await m.answer(f"📜 آخر السجلات:\n{text}")

    @router.message(Command("tickets"))
    async def cmd_tickets(m: Message) -> None:
        if not await is_admin_id(m.from_user.id):
            return
        async with APP.session() as s:
            n = await count_rows(s, Ticket, Ticket.status == "open")
        await m.answer(f"🎫 التذاكر المفتوحة: {n}\nاستخدم /admin → الدعم.")

    @router.message(Command("projects"))
    async def cmd_projects(m: Message) -> None:
        if not await is_admin_id(m.from_user.id):
            return
        async with APP.session() as s:
            n = await count_rows(s, Project)
        await m.answer(f"📁 إجمالي المشاريع: {n}\nاستخدم /admin → المشاريع.")

    @router.message(Command("settings"))
    async def cmd_settings(m: Message) -> None:
        if not await is_admin_id(m.from_user.id):
            return
        await m.answer("⚙️ استخدم /admin → الإعدادات.")

    # ── Middleware: حظر شامل على الرسائل/الاستدعاءات ──
    class BanMiddleware(BaseMiddleware):
        async def __call__(self, handler: Any, event: Any, data: dict) -> Any:
            user = getattr(event, "from_user", None)
            if user and await check_ban(user.id) and not isinstance(event, ErrorEvent):
                if isinstance(event, CallbackQuery):
                    await event.answer("🚫 محظور.", show_alert=True)
                elif isinstance(event, Message):
                    await event.answer("🚫 تم حظرك من استخدام هذا البوت.")
                return None
            return await handler(event, data)

    # ── معالج الأخطاء العام ──
    @router.errors()
    async def on_error(event: ErrorEvent) -> bool:
        exc = event.exception
        log.error("Unhandled error: %s", exc, exc_info=exc)
        upd = event.update
        uid = None
        chat_id = None
        with contextlib.suppress(Exception):
            src = upd.message or upd.callback_query
            uid = src.from_user.id
            chat_id = (upd.message.chat.id if upd.message else upd.callback_query.message.chat.id)
        await log_event("error", uid, details=f"{type(exc).__name__}: {clip(str(exc), 300)}")
        if chat_id:
            with contextlib.suppress(TelegramAPIError):
                await APP.bot.send_message(chat_id, "⚠️ حدث خطأ غير متوقع. تم تسجيله وسيتم النظر فيه، حاول لاحقًا.")
        if APP.owner_id and chat_id != APP.owner_id:
            tb = clip("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)), 3500)
            with contextlib.suppress(TelegramAPIError):
                await APP.bot.send_message(APP.owner_id, f"❗ <b>خطأ</b>\n<code>{esc(tb)}</code>")
        return True

# ═════════════════════════════════════════════════════════════════════════════
# Web Server — للـ Health Check والمراقبة (UptimeRobot / Render)
# ═════════════════════════════════════════════════════════════════════════════
from aiohttp import web

WEB_PORT = int(os.getenv("PORT", "8080"))


async def web_health(request: web.Request) -> web.Response:
    """صفحة Health Check — UptimeRobot يستخدمها للمراقبة."""
    uptime = time.time() - APP.start_time if hasattr(APP, "start_time") else 0
    bot_info = "غير متصل"
    try:
        if APP.bot:
            me = await APP.bot.get_me()
            bot_info = f"@{me.username}"
    except Exception:
        pass
    data = {
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
        "bot": bot_info,
        "uptime_seconds": int(uptime),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return web.json_response(data)


async def web_root(request: web.Request) -> web.Response:
    """الصفحة الرئيسية."""
    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>{APP_NAME}</title>
<style>
body {{ font-family: Arial, sans-serif; background: #0f172a; color: #e2e8f0;
       display: flex; justify-content: center; align-items: center;
       min-height: 100vh; margin: 0; }}
.card {{ background: #1e293b; padding: 40px 60px; border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.5); text-align: center; }}
h1 {{ color: #38bdf8; margin: 0 0 10px; }}
.status {{ color: #22c55e; font-size: 20px; margin: 15px 0; }}
.info {{ color: #94a3b8; font-size: 14px; }}
a {{ color: #38bdf8; text-decoration: none; }}
</style>
</head>
<body>
<div class="card">
  <h1>🤖 {APP_NAME}</h1>
  <div class="status">✅ البوت يعمل</div>
  <div class="info">الإصدار: {APP_VERSION}</div>
  <div class="info">الحالة: <a href="/health">/health</a></div>
</div>
</body>
</html>"""
    return web.Response(text=html, content_type="text/html")


async def start_web_server() -> None:
    """يشغّل Web Server في الخلفية."""
    app = web.Application()
    app.router.add_get("/", web_root)
    app.router.add_get("/health", web_health)
    app.router.add_get("/healthz", web_health)
    app.router.add_get("/ping", web_health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEB_PORT)
    await site.start()
    log.info("🌐 Web server started on port %s", WEB_PORT)
    print(f"🌐 Web Server: http://0.0.0.0:{WEB_PORT}")
    print(f"✅ Health: http://0.0.0.0:{WEB_PORT}/health")
    
# ═════════════════════════════════════════════════════════════════════════════
# Workers + Entrypoint
# ═════════════════════════════════════════════════════════════════════════════
async def cleanup_worker() -> None:
    """ينظّف tmp/ الدوري ويطهّر عدّادات Rate Limiter — لا يمس نسخ الإصدارات."""
    while True:
        try:
            cutoff = time.time() - 3600
            for p in PATHS.tmp.glob("*"):
                with contextlib.suppress(OSError):
                    if p.stat().st_mtime < cutoff:
                        shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
            APP.limiter.purge()
        except Exception:
            log.exception("cleanup_worker error")
        await asyncio.sleep(600)


def setup_logging(level: str) -> None:
    PATHS.ensure()
    handler = logging.handlers.RotatingFileHandler(PATHS.logs / "matri.log", maxBytes=5 * MB, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.addHandler(handler)
    root.addHandler(console)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


async def _amain() -> None:
    if MISSING_DEPS:
        _fatal("مكتبات ناقصة: " + ", ".join(MISSING_DEPS) +
               "\nثبّت المتطلبات: pip install aiogram sqlalchemy aiosqlite pydantic-settings libcst aiohttp")
    cfg = load_settings()
    setup_logging(cfg.LOG_LEVEL)
    PATHS.ensure()
    APP.cfg = cfg
    APP.start_time = time.time()  # ⭐ للـ uptime
    APP.owner_id = cfg.OWNER_ID
    APP.limits = Limits(max_upload_bytes=cfg.MAX_UPLOAD_MB * MB, zip_max_files=cfg.ZIP_MAX_FILES,
                        zip_max_total_bytes=cfg.ZIP_MAX_TOTAL_MB * MB)

    # ⭐ تشغيل Web Server أولاً (قبل البوت)
    await start_web_server()

    APP.db = Database(cfg.DATABASE_URL)
    await APP.db.init()
    log.info("Database ready: %s", cfg.DATABASE_URL)

    bot = Bot(token=cfg.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    APP.bot = bot
    me = await bot.get_me()
    APP.bot_username = me.username or ""
    dp = Dispatcher(storage=MemoryStorage())
    router.message.middleware(BanMiddleware())
    router.callback_query.middleware(BanMiddleware())
    dp.include_router(router)

    await bot.set_my_commands([
        TgBotCommand(command="start", description="ابدأ استخدام البوت"),
    ])
    for admin_id in await admin_ids():
        with contextlib.suppress(TelegramAPIError):
            await bot.set_my_commands([
                TgBotCommand(command="start", description="ابدأ"),
                TgBotCommand(command="admin", description="لوحة الإدارة"),
                TgBotCommand(command="stats", description="الإحصائيات"),
                TgBotCommand(command="broadcast", description="بث رسالة"),
                TgBotCommand(command="users", description="المستخدمون"),
                TgBotCommand(command="logs", description="السجلات"),
                TgBotCommand(command="tickets", description="التذاكر"),
                TgBotCommand(command="projects", description="المشاريع"),
                TgBotCommand(command="settings", description="الإعدادات"),
            ], scope=BotCommandScopeChat(chat_id=admin_id))

    log.info("%s v%s starting — bot=@%s owner=%s", APP_NAME, APP_VERSION, APP.bot_username, APP.owner_id)
    await log_event("startup", APP.owner_id, details=f"bot=@{APP.bot_username}")
    APP.tasks.append(asyncio.create_task(cleanup_worker()))
    try:
        await dp.start_polling(bot)
    finally:
        for t in APP.tasks:
            t.cancel()
        await bot.session.close()
        await APP.db.close()


# ═════════════════════════════════════════════════════════════════════════════
# SELF-TEST — `python bot.py --self-test`  (بلا أي اتصال حقيقي بتيليجرام)
# ═════════════════════════════════════════════════════════════════════════════
class SelfTestFailure(AssertionError):
    pass


def _check(label: str, cond: bool, detail: str = "") -> None:
    if not cond:
        raise SelfTestFailure(f"{label}{': ' + detail if detail else ''}")
    print(f"  ✅ {label}")


def test_pagination() -> None:
    print("▶ Pagination")
    items = list(range(23))
    pg = paginate(items, 1, 8)
    _check("صفحة أولى صحيحة", pg.page == 1 and pg.pages == 3 and pg.items == items[:8])
    pg2 = paginate(items, 99, 8)
    _check("تجاوز الحد يُقيَّد على آخر صفحة", pg2.page == 3 and pg2.items == items[16:23])
    row = pagination_row("page:x:{page}", 1, 3)
    _check("زر السابق معطَّل في الصفحة الأولى", row[0][1] == "noop:first")
    _check("زر التالي يعمل", row[2][1] == "page:x:2")
    row_last = pagination_row("page:x:{page}", 3, 3)
    _check("زر التالي معطَّل في الصفحة الأخيرة", row_last[2][1] == "noop:last")
    _check("تسمية الصفحة صحيحة", row_last[1][0] == "📄 3/3")


def test_zip_security() -> None:
    print("▶ ZIP security")
    limits = Limits()
    tmp = Path(tempfile.mkdtemp())
    try:
        evil = tmp / "evil.zip"
        with zipfile.ZipFile(evil, "w") as z:
            z.writestr("../../etc/passwd", "x")
        try:
            safe_extract_zip(evil, tmp / "out1", limits)
            raise SelfTestFailure("لم يُرفض Zip Slip")
        except UploadError:
            print("  ✅ رفض Path Traversal (../)")

        bomb = tmp / "bomb.zip"
        with zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("a.txt", "0" * (3 * MB))
        small_limits = Limits(zip_max_file_bytes=1 * MB)
        try:
            safe_extract_zip(bomb, tmp / "out2", small_limits)
            raise SelfTestFailure("لم يُرفض ملف أكبر من الحد")
        except UploadError:
            print("  ✅ رفض ملف يتجاوز حجم الحد")

        good = tmp / "good.zip"
        with zipfile.ZipFile(good, "w") as z:
            z.writestr("main.py", "print(1)")
            z.writestr("secrets.env", "TOKEN=x")
            z.writestr("__pycache__/x.pyc", "junk")
        res = safe_extract_zip(good, tmp / "out3", limits)
        _check("يستخرج الملفات الآمنة فقط", [f for f, _ in res.files] == ["main.py"])
        _check("يتجاهل الأسرار والمجلدات غير الضرورية", len(res.skipped) == 2)

        absolute = tmp / "abs.zip"
        with zipfile.ZipFile(absolute, "w") as z:
            zi = zipfile.ZipInfo("/etc/passwd")
            z.writestr(zi, "x")
        try:
            safe_extract_zip(absolute, tmp / "out4", limits)
            raise SelfTestFailure("لم يُرفض مسار مطلق")
        except UploadError:
            print("  ✅ رفض مسار مطلق")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_ast_and_detection() -> None:
    print("▶ AST parsing + Button/Text detection")
    tmp = Path(tempfile.mkdtemp())
    try:
        (tmp / "main.py").write_text(
            'from aiogram import Router\n'
            'from aiogram.filters import CommandStart, Command\n'
            'from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup\n'
            'router = Router()\n'
            'GREETING = "أهلاً"\n'
            '@router.message(CommandStart())\n'
            'async def start(m):\n'
            '    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="الإعدادات", callback_data="settings")]])\n'
            '    await m.answer("مرحبا", reply_markup=kb)\n'
            '    await m.answer(some_var)\n'
            '@router.message(Command("help"))\n'
            'async def h(m):\n'
            '    eval("1")\n', encoding="utf-8")
        res = analyze_directory(tmp, "test")
        _check("اكتشاف aiogram", "aiogram" in "".join(res.frameworks) or any("aiogram" in f for f in res.frameworks))
        _check("اكتشاف الأوامر /start و /help", {"start", "help"} <= {c["name"] for c in res.commands})
        _check("اكتشاف زر Inline", any(b["text"] == "الإعدادات" and b["kind"] == "inline" for b in res.buttons))
        _check("اكتشاف نص ثابت", any(t["text"] == "مرحبا" for t in res.texts))
        _check("اكتشاف نص ديناميكي وعدم اعتباره ثابتًا", any(t["dynamic"] for t in res.texts))
        _check("تحذير من eval() دون تنفيذه", any("eval" in w for w in res.warnings))
        _check("callback_data settings يُعتبر آمنًا (موضع وحيد)", res.callbacks.get("settings", {}).get("safe") is True)

        bad = tmp / "broken.py"
        bad.write_text("def f(:\n", encoding="utf-8")
        res2 = analyze_directory(tmp, "test2")
        _check("خطأ صياغة يُسجَّل كتحذير ولا يُسقط التحليل", any("خطأ صياغة" in w for w in res2.warnings))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_db_init() -> None:
    print("▶ Database initialization")
    if not HAVE_SA:
        print("  ⚠️ SQLAlchemy غير مثبتة — تخطّي (متوقع في بيئات بلا اعتماديات).")
        return

    async def run() -> None:
        tmp = Path(tempfile.mkdtemp())
        db = Database(f"sqlite+aiosqlite:///{tmp / 'test.db'}")
        await db.init()
        async with db.session() as s:
            names = {n for (n,) in (await s.execute(select(Plan.name))).all()}
            _check("خطط افتراضية أُنشئت (Free/Pro/Premium)", {"Free", "Pro", "Premium"} <= names)
            setting = await s.get(SettingRow, "maintenance")
            _check("إعدادات افتراضية أُنشئت", setting is not None)
        await db.init()  # يجب ألا يكرر الخطط
        async with db.session() as s:
            n = int((await s.execute(select(func.count()).select_from(Plan))).scalar_one())
            _check("لا تكرار عند إعادة init()", n == 3)
        await db.close()
        shutil.rmtree(tmp, ignore_errors=True)
    asyncio.run(run())


def test_style_options() -> None:
    print("▶ Style options (Semantic — لا تغيّر ألوان Telegram الفعلية)")
    _check("4 أنماط معرَّفة", len(COLOR_OPTIONS) == 4)
    _check("style_label يعمل", style_label("green") == "🟢 أخضر")
    _check("is_valid_style يرفض قيمة غير معروفة", is_valid_style("purple") is False)
    _check("style_semantic('none') = None", style_semantic("none") is None)


def test_version_numbering() -> None:
    print("▶ Version numbering")
    tmp = Path(tempfile.mkdtemp())
    try:
        v1 = tmp / "v1"
        v1.mkdir()
        (v1 / "a.py").write_text("x=1", encoding="utf-8")
        bpath = backup_project(v1, 999)
        _check("تُنشأ نسخة احتياطية بـ timestamp", bpath.exists() and (bpath / "a.py").exists())
        _check("الأصل لم يُمس", (v1 / "a.py").read_text() == "x=1")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_editor_validation() -> None:
    print("▶ Editor (LibCST) validation")
    if not HAVE_LIBCST:
        print("  ⚠️ LibCST غير مثبتة — يُتحقق فقط من أن EditError تُرفع بدل الانهيار.")
        try:
            apply_edits_to_source("x=1", [EditOp("a.py", 1, 0, "1", "2", "const")])
            raise SelfTestFailure("كان يجب رفع EditError دون LibCST")
        except EditError:
            print("  ✅ EditError تُرفع بأمان بدل الانهيار عند غياب LibCST")
        return
    src = 'TEXTS = {"a": "قديم", "b": "قديم"}\n'
    new_src = apply_edits_to_source(src, [EditOp("f.py", 1, 0, "قديم", "جديد", "const")])
    _check("تعديل تكرار أول فقط بدقة عبر (سطر، رقم تكرار)", new_src.count("جديد") == 1 and new_src.count("قديم") == 1)
    ast.parse(new_src)
    print("  ✅ الكود الناتج صالح (ast.parse نجح)")
    try:
        apply_edits_to_source(src, [EditOp("f.py", 1, 5, "قديم", "جديد", "const")])
        raise SelfTestFailure("كان يجب فشل تعديل موضع غير موجود")
    except EditError:
        print("  ✅ فشل تعديل بموضع غير صحيح يُرفع كـ EditError (بلا كتابة جزئية)")


def run_self_tests() -> int:
    print(f"🧪 {APP_NAME} — Self Test (لا يُرسل أي رسائل Telegram حقيقية)\n")
    tests = [test_pagination, test_zip_security, test_ast_and_detection, test_db_init,
             test_style_options, test_version_numbering, test_editor_validation]
    failed = 0
    for test in tests:
        try:
            test()
        except SelfTestFailure as exc:
            failed += 1
            print(f"  ❌ فشل: {exc}")
        except Exception as exc:  # pragma: no cover
            failed += 1
            print(f"  ❌ خطأ غير متوقع: {type(exc).__name__}: {exc}")
        print()
    if MISSING_DEPS:
        print(f"ℹ️ ملاحظة: مكتبات غير مثبتة في بيئة الاختبار هذه: {', '.join(MISSING_DEPS)} — "
              "بعض الاختبارات تعمل بالـ fallback الآمن بدلًا من التنفيذ الكامل.\n")
    if failed:
        print(f"❌ فشل {failed} من {len(tests)} مجموعة اختبارات.")
        return 1
    print(f"✅ نجحت كل مجموعات الاختبار ({len(tests)}).")
    return 0


# ═════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(run_self_tests())
    if not HAVE_AIOGRAM:
        _fatal("مكتبة aiogram غير مثبتة.\nثبّت المتطلبات: pip install aiogram sqlalchemy aiosqlite pydantic-settings libcst")
    try:
        asyncio.run(_amain())
    except (KeyboardInterrupt, SystemExit):
        pass
