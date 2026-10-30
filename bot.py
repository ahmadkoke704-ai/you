#!/usr/bin/env python3
"""
=============================================================================
 DAHIHA THANWI TELEGRAM SUITE • IN-PM GROUPHELP CONTROL CENTER
 Application Focus: Egyptian 3rd Secondary Curriculum (Thanaweya Amma)
 Framework: Asynchronous Python (Telethon MTProto Framework)
=============================================================================
 Core Systems:
   1. Advanced Arabic Text Normalization (أدمن/ادمن/أدمين، همسة/همسه، إلخ)
   2. Interactive Whisper via Private Chat (همسة بالرد -> رابط الخاص -> نشر بالمجموعة)
   3. Exact Image 2 Whisper Layout ("وصلتك همسه جديده من" + فتح الهمسه + حذف الهمسه)
   4. Strict Owner-Only Permissions Check ("لازم تكون المالك عشان تقدر تستخدم هذا الأمر 👑")
   5. Rich Egyptian Group Dictionary (انا مين، زهقت، قرفت، نكتة، تحفيز، بوت)
   6. Owner Admin Actions (رفع ادمن، تنزيل ادمن، قفل/فتح الدردشة، كتم، طرد، حظر، مسح)
   7. Forced Add Engine (الإضافة الإجبارية) with Native Contact Picker Share
   8. In-PM Interactive Settings Center (100% In-Chat PM Settings, Pages 1 & 2)
=============================================================================
"""

import os
import sys
import time
import json
import re
import secrets
import random
import asyncio
import logging
import sqlite3
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from telethon import TelegramClient, events
from telethon.tl.custom import Button
from telethon.tl.types import (
    MessageActionChatAddUser,
    MessageActionChatJoinedByLink,
    ChannelParticipantsAdmins,
    ChatBannedRights,
    ChatAdminRights,
    ChannelParticipantCreator,
    User,
    Channel,
    Chat,
)
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.tl.functions.channels import EditBannedRequest, EditAdminRequest
from telethon.errors import (
    MessageDeleteForbiddenError,
    ChatAdminRequiredError,
    UserAdminInvalidError,
    FloodWaitError,
)
from aiohttp import web

# ---------------------------------------------------------------------------
# Core Configurations
# ---------------------------------------------------------------------------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9170444919:AAFn5ukIgdNxNZzqsZ8eoYN0RCF_CDTH778")
API_ID = int(os.getenv("TELEGRAM_API_ID", "2040"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "b18441a1ff607e10a989891a5462e627")
INTERNAL_API_PORT = int(os.getenv("BOT_API_PORT", "5005"))
DB_PATH = os.path.join(os.path.dirname(__file__), "storage.db")

# Anti-Link Scanner Pattern (http, https, www, t.me, shorteners, @usernames)
LINK_REGEX = re.compile(
    r"(https?://\S+|t\.me/\S+|telegram\.me/\S+|telegram\.dog/\S+|bit\.ly/\S+|tinyurl\.com/\S+|goo\.gl/\S+|youtu\.be/\S+|wa\.me/\S+|www\.\S+|@[a-zA-Z0-9_]{4,})",
    re.IGNORECASE
)

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("DahihaThanwiSuite")

# ---------------------------------------------------------------------------
# Arabic Text Normalizer (Normalizes Hamza, Ta Marbuta, Ya, and letter repeats)
# ---------------------------------------------------------------------------
def normalize_arabic(text: str) -> str:
    if not text:
        return ""
    # Strip diacritics / tashkeel & tatweel
    t = re.sub(r"[\u064B-\u0652\u0670\u0640]", "", text)
    # Normalize Alef: أ, إ, آ, ٱ -> ا
    t = re.sub(r"[إأآٱا]", "ا", t)
    # Normalize Ta Marbuta: ة -> ه
    t = re.sub(r"ة", "ه", t)
    # Normalize Ya: ى -> ي
    t = re.sub(r"ى", "ي", t)
    # Collapse repeated letters: بووووت -> بوت, زهقتتتت -> زهقت
    t = re.sub(r"(.)\1{2,}", r"\1", t)
    # Normalize multiple whitespace
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t

# ---------------------------------------------------------------------------
# SQLite3 WAL-Mode Datastore
# ---------------------------------------------------------------------------
class StorageManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _init_database(self):
        with self.get_connection() as conn:
            cur = conn.cursor()

            # Groups Table with comprehensive GroupHelp settings
            cur.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    chat_id INTEGER PRIMARY KEY,
                    group_title TEXT,
                    owner_id INTEGER DEFAULT 0,
                    required_adds INTEGER DEFAULT 1,
                    warning_timeout INTEGER DEFAULT 15,
                    force_add_enabled INTEGER DEFAULT 1,
                    anti_link INTEGER DEFAULT 1,
                    anti_spam INTEGER DEFAULT 1,
                    anti_forward INTEGER DEFAULT 0,
                    chat_locked INTEGER DEFAULT 0,
                    welcome_enabled INTEGER DEFAULT 1,
                    goodbye_enabled INTEGER DEFAULT 0,
                    captcha_enabled INTEGER DEFAULT 0,
                    night_mode INTEGER DEFAULT 0,
                    clean_service INTEGER DEFAULT 1,
                    anti_tag INTEGER DEFAULT 0,
                    block_media INTEGER DEFAULT 0,
                    block_photos INTEGER DEFAULT 0,
                    block_videos INTEGER DEFAULT 0,
                    block_stickers INTEGER DEFAULT 0,
                    block_voice INTEGER DEFAULT 0,
                    block_badwords INTEGER DEFAULT 1,
                    block_anonymous INTEGER DEFAULT 0,
                    warn_limit INTEGER DEFAULT 3,
                    report_admin INTEGER DEFAULT 1,
                    nsfw_filter INTEGER DEFAULT 1,
                    guardian_bot INTEGER DEFAULT 0,
                    approval_mode INTEGER DEFAULT 0,
                    long_msgs_lock INTEGER DEFAULT 0,
                    alphabet_filter INTEGER DEFAULT 0,
                    rules_enabled INTEGER DEFAULT 1,
                    topics_enabled INTEGER DEFAULT 0,
                    custom_cmds INTEGER DEFAULT 1,
                    channel_manage INTEGER DEFAULT 0,
                    log_channel INTEGER DEFAULT 0,
                    admin_perms INTEGER DEFAULT 1,
                    rules_text TEXT DEFAULT '📜 قوانين المجموعة:\n1. الاحترام المتبادل بين جميع الطلاب.\n2. ممنوع نشر الروابط والإعلانات والمعرفات.\n3. ممنوع التكرار والسبام.\n4. الالتزام بالهدف التعليمي للمجموعة.',
                    invite_link TEXT,
                    custom_warning_msg TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Ensure owner_id and extra columns exist
            cur.execute("PRAGMA table_info(groups)")
            columns = [row["name"] for row in cur.fetchall()]
            if "owner_id" not in columns:
                try:
                    cur.execute("ALTER TABLE groups ADD COLUMN owner_id INTEGER DEFAULT 0")
                except Exception:
                    pass

            extra_cols = [
                ("welcome_enabled", "INTEGER DEFAULT 1"),
                ("goodbye_enabled", "INTEGER DEFAULT 0"),
                ("captcha_enabled", "INTEGER DEFAULT 0"),
                ("night_mode", "INTEGER DEFAULT 0"),
                ("clean_service", "INTEGER DEFAULT 1"),
                ("anti_tag", "INTEGER DEFAULT 0"),
                ("block_media", "INTEGER DEFAULT 0"),
                ("block_photos", "INTEGER DEFAULT 0"),
                ("block_videos", "INTEGER DEFAULT 0"),
                ("block_stickers", "INTEGER DEFAULT 0"),
                ("block_voice", "INTEGER DEFAULT 0"),
                ("block_badwords", "INTEGER DEFAULT 1"),
                ("block_anonymous", "INTEGER DEFAULT 0"),
                ("warn_limit", "INTEGER DEFAULT 3"),
                ("report_admin", "INTEGER DEFAULT 1"),
                ("nsfw_filter", "INTEGER DEFAULT 1"),
                ("guardian_bot", "INTEGER DEFAULT 0"),
                ("approval_mode", "INTEGER DEFAULT 0"),
                ("long_msgs_lock", "INTEGER DEFAULT 0"),
                ("alphabet_filter", "INTEGER DEFAULT 0"),
                ("rules_enabled", "INTEGER DEFAULT 1"),
                ("topics_enabled", "INTEGER DEFAULT 0"),
                ("custom_cmds", "INTEGER DEFAULT 1"),
                ("channel_manage", "INTEGER DEFAULT 0"),
                ("log_channel", "INTEGER DEFAULT 0"),
                ("admin_perms", "INTEGER DEFAULT 1"),
                ("rules_text", "TEXT"),
            ]
            for col_name, col_type in extra_cols:
                if col_name not in columns:
                    try:
                        cur.execute(f"ALTER TABLE groups ADD COLUMN {col_name} {col_type}")
                    except Exception:
                        pass

            # Pre-seed primary group if empty
            cur.execute("SELECT COUNT(*) as count FROM groups")
            if cur.fetchone()["count"] == 0:
                cur.execute("""
                    INSERT INTO groups (
                        chat_id, group_title, required_adds, force_add_enabled, 
                        anti_link, anti_spam, welcome_enabled, invite_link
                    ) VALUES (
                        -1002345678901, 'تالتة ثانوي (ازهر _ عام)', 1, 1, 1, 1, 1,
                        'https://t.me/joinchat/ThanaweyaAmma2026'
                    )
                """)

            # Users Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    chat_id INTEGER,
                    user_name TEXT,
                    invite_balance INTEGER DEFAULT 0,
                    is_whitelisted INTEGER DEFAULT 0,
                    warnings_count INTEGER DEFAULT 0,
                    message_count INTEGER DEFAULT 0,
                    last_message_at TIMESTAMP,
                    UNIQUE(user_id, chat_id)
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_users_chat_uid ON users(chat_id, user_id)")

            # Invites Ledger
            cur.execute("""
                CREATE TABLE IF NOT EXISTS invites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    inviter_id INTEGER,
                    inviter_name TEXT,
                    invited_id INTEGER,
                    invited_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(chat_id, invited_id)
                )
            """)

            # Whispers System Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS whispers (
                    whisper_id TEXT PRIMARY KEY,
                    chat_id INTEGER,
                    sender_id INTEGER,
                    sender_name TEXT,
                    target_identifier TEXT,
                    target_id INTEGER DEFAULT 0,
                    target_name TEXT DEFAULT '',
                    secret_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Pending Whispers Session Table (Private Chat flow)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pending_whispers (
                    token TEXT PRIMARY KEY,
                    chat_id INTEGER,
                    reply_to_msg_id INTEGER,
                    sender_id INTEGER,
                    sender_name TEXT,
                    target_id INTEGER,
                    target_name TEXT,
                    target_username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Activity Logs
            cur.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    chat_title TEXT,
                    user_id INTEGER,
                    user_name TEXT,
                    action_type TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Counters
            cur.execute("DROP TABLE IF EXISTS counters")
            cur.execute("""
                CREATE TABLE counters (
                    key TEXT PRIMARY KEY,
                    val INTEGER DEFAULT 0
                )
            """)
            cur.executemany("""
                INSERT OR IGNORE INTO counters (key, val) VALUES (?, 0)
            """, [
                ("deleted_messages",),
                ("warnings_sent",),
                ("links_blocked",),
                ("spam_blocked",),
                ("forwards_blocked",),
                ("whispers_sent",),
                ("dictionary_replies",)
            ])

            # Educational Quizzes Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS quizzes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT,
                    chapter TEXT,
                    question TEXT,
                    option_a TEXT,
                    option_b TEXT,
                    option_c TEXT,
                    option_d TEXT,
                    correct_option TEXT,
                    explanation TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("SELECT COUNT(*) as count FROM quizzes")
            if cur.fetchone()["count"] == 0:
                cur.executemany("""
                    INSERT INTO quizzes (subject, chapter, question, option_a, option_b, option_c, option_d, correct_option, explanation)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    ("الفيزياء", "قوانين كيرشوف", "في الدائرة الكهربية الموضحة، مجموع التيارات الكهربية الداخلة عند أي نقطة تفرع يساوي مجموع التيارات الخارجة، هذا يعبر عن قانون:", "كيرشوف الأول (حفظ الشحنة)", "كيرشوف الثاني (حفظ الطاقة)", "قانون أوم للدائرة المغلقة", "قانون فاراداي للحث", "كيرشوف الأول (حفظ الشحنة)", "ينص قانون كيرشوف الأول على حفظ الشحنة الكهربية: Σ I_in = Σ I_out."),
                    ("الكيمياء", "العناصر الانتقالية", "جميع المركبات التالية بارامغناطيسية وملونة ما عدا:", "FeCl3", "CuSO4", "ZnSO4", "Cr2O3", "ZnSO4", "أيون الخارصين Zn²⁺ توزيعه [Ar] 3d¹⁰، جميع أوربيتالات d ممتلئة تماماً لذا فهو دايامغناطيسي وغير ملون."),
                    ("اللغة العربية", "الوحدة الثانية - النحو", "المتفوقون هم الأعلون شأناً. حكم اسم التفضيل (الأعلون) من حيث المطابقة للمفضل:", "يجب مطابقته للمفضل", "يلزم الإفراد والتذكير", "يجوز المطابقة وعدمها", "يمتنع التذكير", "يجب مطابقته للمفضل", "اسم التفضيل المعرّف بـ (أل) يجب أن يطابق المفضل في النوع والعدد ولا يذكر بعده المفضل عليه."),
                    ("الأحياء", "البيولوجيا الجزيئية - DNA", "إذا كانت نسبة الأدينين (A) في عينة من لولب مزدوج لـ DNA تساوي 28%، فإن نسبة الجوانين (G) تكون:", "22%", "28%", "24%", "36%", "22%", "بما أن A=28% فإن T=28% (المجموع=56%). المتبقي لـ G+C هو 44%، إذن G=22% و C=22%.")
                ])

            conn.commit()

    # -------------------------------------------------------------
    # Group Helpers
    # -------------------------------------------------------------
    def get_group(self, chat_id: int, title_if_new: str = "مجموعة ثانوية عامة") -> Dict[str, Any]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM groups WHERE chat_id = ?", (chat_id,))
            row = cur.fetchone()
            if row:
                return dict(row)

            cur.execute("""
                INSERT INTO groups (chat_id, group_title, required_adds, force_add_enabled, anti_link, anti_spam)
                VALUES (?, ?, 1, 1, 1, 1)
            """, (chat_id, title_if_new))
            conn.commit()

            cur.execute("SELECT * FROM groups WHERE chat_id = ?", (chat_id,))
            return dict(cur.fetchone())

    def update_group_settings(self, chat_id: int, **kwargs):
        if not kwargs:
            return
        fields = []
        vals = []
        for k, v in kwargs.items():
            fields.append(f"{k} = ?")
            vals.append(v)
        vals.append(chat_id)
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"UPDATE groups SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE chat_id = ?", vals)
            conn.commit()

    def get_all_groups(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM groups ORDER BY updated_at DESC")
            return [dict(r) for r in cur.fetchall()]

    # -------------------------------------------------------------
    # Users & Invites
    # -------------------------------------------------------------
    def get_or_create_user(self, chat_id: int, user_id: int, user_name: str) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
            row = cur.fetchone()
            if row:
                cur.execute("""
                    UPDATE users 
                    SET user_name = ?, message_count = message_count + 1, last_message_at = CURRENT_TIMESTAMP 
                    WHERE chat_id = ? AND user_id = ?
                """, (user_name, chat_id, user_id))
                conn.commit()
                return dict(row)

            cur.execute("""
                INSERT INTO users (chat_id, user_id, user_name, message_count, last_message_at)
                VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
            """, (chat_id, user_id, user_name))
            conn.commit()
            cur.execute("SELECT * FROM users WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
            return dict(cur.fetchone())

    def get_user_invites(self, chat_id: int, user_id: int) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT invite_balance FROM users WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
            row = cur.fetchone()
            return row["invite_balance"] if row else 0

    def record_invite(self, chat_id: int, inviter_id: int, inviter_name: str, invited_id: int, invited_name: str) -> bool:
        if inviter_id == invited_id:
            return False
        with self.get_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO invites (chat_id, inviter_id, inviter_name, invited_id, invited_name)
                    VALUES (?, ?, ?, ?, ?)
                """, (chat_id, inviter_id, inviter_name, invited_id, invited_name))

                cur.execute("""
                    INSERT INTO users (chat_id, user_id, user_name, invite_balance)
                    VALUES (?, ?, ?, 1)
                    ON CONFLICT(chat_id, user_id) DO UPDATE SET 
                        invite_balance = invite_balance + 1,
                        user_name = excluded.user_name
                """, (chat_id, inviter_id, inviter_name))

                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def is_whitelisted(self, chat_id: int, user_id: int) -> bool:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT is_whitelisted FROM users WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
            row = cur.fetchone()
            return bool(row["is_whitelisted"]) if row else False

    # -------------------------------------------------------------
    # Whispers System
    # -------------------------------------------------------------
    def save_whisper(self, whisper_id: str, chat_id: int, sender_id: int, sender_name: str, target_identifier: str, target_id: int, target_name: str, secret_text: str):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO whispers (whisper_id, chat_id, sender_id, sender_name, target_identifier, target_id, target_name, secret_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (whisper_id, chat_id, sender_id, sender_name, target_identifier, target_id, target_name, secret_text))
            cur.execute("UPDATE counters SET val = val + 1 WHERE key = 'whispers_sent'")
            conn.commit()

    def get_whisper(self, whisper_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM whispers WHERE whisper_id = ?", (whisper_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    # Pending whispers (Private Chat Creation Flow)
    def save_pending_whisper(self, token: str, chat_id: int, reply_to_msg_id: int, sender_id: int, sender_name: str, target_id: int, target_name: str, target_username: str):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO pending_whispers (token, chat_id, reply_to_msg_id, sender_id, sender_name, target_id, target_name, target_username)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (token, chat_id, reply_to_msg_id, sender_id, sender_name, target_id, target_name, target_username))
            conn.commit()

    def get_pending_whisper(self, token: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM pending_whispers WHERE token = ?", (token,))
            row = cur.fetchone()
            return dict(row) if row else None

    def delete_pending_whisper(self, token: str):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM pending_whispers WHERE token = ?", (token,))
            conn.commit()

    # -------------------------------------------------------------
    # Activity & Metrics
    # -------------------------------------------------------------
    def log_activity(self, chat_id: int, chat_title: str, user_id: int, user_name: str, action_type: str, details: str):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO activity_logs (chat_id, chat_title, user_id, user_name, action_type, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (chat_id, chat_title, user_id, user_name, action_type, details))

            counter_map = {
                "MESSAGE_DELETED": "deleted_messages",
                "WARNING_SENT": "warnings_sent",
                "LINK_BLOCKED": "links_blocked",
                "SPAM_BLOCKED": "spam_blocked",
                "FORWARD_BLOCKED": "forwards_blocked",
                "WHISPER_SENT": "whispers_sent",
                "DICT_REPLY": "dictionary_replies"
            }
            if action_type in counter_map:
                cur.execute("UPDATE counters SET val = val + 1 WHERE key = ?", (counter_map[action_type],))

            conn.commit()

    def get_metrics(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT key, val FROM counters")
            metrics = {row["key"]: row["val"] for row in cur.fetchall()}
            cur.execute("SELECT COUNT(*) as count FROM groups")
            metrics["active_groups"] = cur.fetchone()["count"]
            cur.execute("SELECT COUNT(*) as count FROM invites")
            metrics["total_invites"] = cur.fetchone()["count"]
            cur.execute("SELECT COUNT(*) as count FROM whispers")
            metrics["total_whispers"] = cur.fetchone()["count"]
            return metrics

    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM activity_logs ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cur.fetchall()]

    def get_random_quiz(self) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM quizzes ORDER BY RANDOM() LIMIT 1")
            row = cur.fetchone()
            return dict(row) if row else None


db = StorageManager(DB_PATH)

# ---------------------------------------------------------------------------
# Rich Egyptian Group Chat Dictionary (Humor, Motivation, Complaints, Life)
# ---------------------------------------------------------------------------
BOT_REPLIES_EGYPTIAN = [
    "نعمين يا سكر، البوت تحت أمرك! 🌺",
    "معاك يا بطل تالتة ثانوي! شد حيلك وفالك المجموع العالي والقمة إن شاء الله 📚✨",
    "تحت أمرك يا كابتن، شغال 24 ساعة لخدمتك وحماية الجروب 🫡",
    "سيبك من الشات وقوم راجع الفيزياء واللغات! الوقت بيجري يا دحيح 🤓📖",
    "لبيك وسعديك! أنا في خدمتك، اكتب `الاوامر` وشوف كل مميزاتي ⚡",
    "يا عيون البوت، تحب أساعدك في إيه النهاردة؟ ❤️",
    "البوت شغال بأعلى سرعة لحماية الجروب وتنظيمه، أؤمرني! 🚀",
    "أيوة يا فندم معاك، اتفضل طلبك مجاب بإذن الله 🌟",
    "يا باشا نورت الشات! اكتب `انا مين` عشان تشوف رتبتك ورصيد إضافاتك 👑",
    "صاحي ومصحصح معاك يا دحيح.. اطلب واتمنى! 🎯"
]

FRUSTRATION_REPLIES = [
    "سلامتك من القرف والزهق يا غالي! 🤍 هون على نفسك، قوم اغسل وشك واشرب كوباية شاي أو قهوة، فتره وتعدي وتفرح بنتيجتك وتدخل الكلية اللي نفسك فيها ☕✨",
    "معلش يا بطل، كلنا بنمر بلحظات ضغط وخنقة في تالتة ثانوي.. بس البطل الحقيقي هو اللي بيصبر ويكمل! خد راحة ساعة وارجع تاني أقوى 💪",
    "حقك تزهق والله، سنة طويلة ومتعبة.. بس افتكر فرحة أمك وأبوك يوم النتيجة! التعب ده كله هيهون في لحظة واحدة لما تجيب المجموع 🌟",
    "صل على النبي واستعيذ بالله من الشيطان الرجيم 🌿.. ريح دماغك شوية من الكتب، وخلي يقينك بربنا كبير إنه مش هيضيع تعبك أبدًا ❤️",
    "عارف إن المواد تقيلة والفيزياء مش راحمة، بس والله اللي بيتعب دلوقتي بيستريح بعدين! شد حيلك ولا تستسلم يا باشا 🩺⚡"
]

EGYPTIAN_JOKES = [
    "😂 مرة مدرس فيزياء خلف ولدين سمى الأول 'فولت' والتاني 'أمبير'.. لما بيكبروا بيعملوا 'قفلة' في البيت!",
    "🤣 طالب تالتة ثانوي بيسألوه: إيه هي أحسن مادة عندك؟ قالهم: المادة اللي بلغي درسها وأنام مكانها!",
    "😆 مدرس كيمياء دخل الامتحان لقى الورقة بيضاء.. قال للطلاب: ما هذا؟ قالوا له: غاز عديم اللون والرائحة يا مستر!",
    "😂 واحد سأل دحيح: بتعمل إيه لما يجيلك اكتئاب؟ قاله: بذاكر عشان أنسى الاكتئاب.. ده إحنا كدة هنتشل يا جماعة!",
    "🤣 طالب بيقول لأبوه: أنا جبت 99% في الثانوية! أبوه قاله: وفين الـ 1% الباقية يا فاشل؟! ثقافة الأب المصري الأصيل 😂",
    "😆 مدرس لغة عربية بيسأل طالب: ما إعراب كلمة 'صرصور'؟ قاله: فاعل مرفوع بالشبشب وعلامة رفعه الجدار!"
]

MOTIVATIONAL_QUOTES = [
    "💡 **تذكر دائماً:** التعب اللي أنت فيه دلوقتي هو تمن الفرحة الكبيرة اللي هتعيشها يوم النتيجة مع أهلك! ربنا مش هيضيع تعبك أبداً.. كمّل وسيب الباقي على الله. 🌟",
    "🎯 **نصيحة دحيح:** الثانوية مش معركة ذكاء خارق، الثانوية معركة نفَس طويل والتزام يومي.. صفحة ورا صفحة ومسألة ورا مسألة بتوصل لحلمك! 📚",
    "✨ **خليك واثق:** كل ساعة مذاكرة وتعب في عز السهر بتتبني بيها مستقبلك واسمك اللي هتفتخر بيه قدام الناس.. شد حيلك واصبر، هانت جداً! 🩺⚡",
    "🏆 **رسالة اليوم:** مش مهم بدأت إزاي، المهم هتنهي السنة إزاي.. كل دقيقة دلوقتي بتفرق في مجموعك، قفل تليفونك وابدأ مذاكرة حالا! 🚀",
    "🌿 **آية كريمة تريح قلبك:** {وَأَن لَّيْسَ لِلْإِنسَانِ إِلَّا مَا سَعَىٰ * وَأَنَّ سَعْيَهُ سَوْفَ يُرَىٰ}. اجتهد بس واسعى وربنا كفيل يراضيك باللي يفرحك."
]

STUDY_TIPS = [
    "⏱️ **طريقة بومودورو:** ذاكر 50 دقيقة بتركيز تام بدون موبايل، وخد 10 دقايق راحة، هتلاقي إنتاجيتك تضاعفت 3 مرات!",
    "📝 **التلخيص باليد:** كتابة القوانين والملاحظات المهمة بإيدك في كشكول خاص بترسخ المعلومة في الذاكرة طويلة المدى.",
    "🔄 **المراجعة التراكمية:** خصص أول نصف ساعة من يومك لمراجعة اللي ذاكرته بالأمس قبل ما تبدأ أي درس جديد.",
    "❓ **حل الامتحانات الشاملة:** حل الأسئلة بيدك هو المقياس الحقيقي لمستواك، مش مجرد قراءة الملازم والشرح!"
]

# ---------------------------------------------------------------------------
# Telegram Telethon Suite Engine (100% In-Chat PM Settings Center)
# ---------------------------------------------------------------------------
class DahihaThanwiEngine:
    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.api_id = API_ID
        self.api_hash = API_HASH
        self.client: Optional[TelegramClient] = None
        self.me = None
        self.start_time = time.time()
        self.is_running = False

        self.last_warning_time: Dict[str, float] = {}
        self.admin_cache: Dict[str, tuple[bool, float]] = {}
        self.user_message_times: Dict[str, List[float]] = {}
        self.group_links: Dict[int, str] = {}
        self.user_whisper_sessions: Dict[int, str] = {}  # user_id -> pending_whisper_token

    async def initialize(self):
        logger.info(f"Connecting Telethon to Telegram with Token: {self.bot_token[:10]}...")
        session_name = "storage_session"
        self.client = TelegramClient(session_name, self.api_id, self.api_hash)
        self._register_handlers()
        await self.client.start(bot_token=self.bot_token)
        self.me = await self.client.get_me()
        self.is_running = True
        logger.info(f"Online: @{self.me.username} (ID: {self.me.id}, Name: {self.me.first_name})")

    def _register_handlers(self):
        @self.client.on(events.ChatAction)
        async def on_chat_action(event: events.ChatAction.Event):
            await self._handle_chat_action(event)

        @self.client.on(events.NewMessage)
        async def on_new_message(event: events.NewMessage.Event):
            await self._handle_new_message(event)

        @self.client.on(events.CallbackQuery)
        async def on_callback(event: events.CallbackQuery.Event):
            await self._handle_callback(event)

    # -------------------------------------------------------------------------
    # Strict Owner Verification (المالك فقط)
    # -------------------------------------------------------------------------
    async def is_owner(self, chat_id: int, user_id: int) -> bool:
        cache_key = f"owner:{chat_id}:{user_id}"
        now = time.time()
        if cache_key in self.admin_cache:
            is_own, cached_at = self.admin_cache[cache_key]
            if now - cached_at < 60:
                return is_own

        # Check DB cached owner
        cfg = db.get_group(chat_id)
        cached_owner = cfg.get("owner_id", 0)
        if cached_owner and int(cached_owner) == user_id:
            self.admin_cache[cache_key] = (True, now)
            return True

        # Check Telethon Permissions (is_creator or add_admins permission)
        try:
            permissions = await self.client.get_permissions(chat_id, user_id)
            if permissions:
                if permissions.is_creator:
                    db.update_group_settings(chat_id, owner_id=user_id)
                    self.admin_cache[cache_key] = (True, now)
                    return True
                if hasattr(permissions, 'add_admins') and permissions.add_admins:
                    db.update_group_settings(chat_id, owner_id=user_id)
                    self.admin_cache[cache_key] = (True, now)
                    return True
        except Exception:
            pass

        # Inspect Admin list for Creator
        try:
            async for p in self.client.iter_participants(chat_id, filter=ChannelParticipantsAdmins):
                if isinstance(p.participant, ChannelParticipantCreator):
                    db.update_group_settings(chat_id, owner_id=p.id)
                    is_c = (p.id == user_id)
                    self.admin_cache[cache_key] = (is_c, now)
                    return is_c
        except Exception:
            pass

        # Fallback: If group owner is not yet set (owner_id == 0), the admin running commands is set as owner
        if not cached_owner or cached_owner == 0:
            try:
                permissions = await self.client.get_permissions(chat_id, user_id)
                if permissions and (permissions.is_admin or permissions.is_creator):
                    db.update_group_settings(chat_id, owner_id=user_id)
                    self.admin_cache[cache_key] = (True, now)
                    return True
            except Exception:
                pass

        self.admin_cache[cache_key] = (False, now)
        return False

    async def is_admin_or_owner(self, chat_id: int, user_id: int) -> bool:
        cache_key = f"adm:{chat_id}:{user_id}"
        now = time.time()
        if cache_key in self.admin_cache:
            is_adm, cached_at = self.admin_cache[cache_key]
            if now - cached_at < 60:
                return is_adm

        try:
            permissions = await self.client.get_permissions(chat_id, user_id)
            is_admin = bool(permissions.is_admin or permissions.is_creator)
            self.admin_cache[cache_key] = (is_admin, now)
            return is_admin
        except Exception:
            try:
                chat = await self.client.get_entity(chat_id)
                if hasattr(chat, 'creator') and chat.creator:
                    return True
            except Exception:
                pass
            return False

    async def get_or_export_invite_link(self, chat_id: int, chat_obj=None) -> str:
        if chat_id in self.group_links:
            return self.group_links[chat_id]

        group_cfg = db.get_group(chat_id)
        if group_cfg.get("invite_link"):
            self.group_links[chat_id] = group_cfg["invite_link"]
            return group_cfg["invite_link"]

        if chat_obj and hasattr(chat_obj, 'username') and chat_obj.username:
            link = f"https://t.me/{chat_obj.username}"
            self.group_links[chat_id] = link
            db.update_group_settings(chat_id, invite_link=link)
            return link

        try:
            exported = await self.client(ExportChatInviteRequest(chat_id))
            if hasattr(exported, 'link'):
                link = exported.link
                self.group_links[chat_id] = link
                db.update_group_settings(chat_id, invite_link=link)
                return link
        except Exception as e:
            logger.debug(f"Unable to export link for chat {chat_id}: {e}")

        fallback = f"https://t.me/{self.me.username}?startgroup=true"
        return fallback

    # =========================================================================
    # GroupHelp Interactive Private Chat Menus (Images 1, 2, 3 Parity)
    # =========================================================================

    def _build_start_pm_markup(self, user_id: int) -> tuple[str, list]:
        """Builds Image 1 Screen: Instructions + Group Selection Buttons"""
        text = (
            "**إعدادات المجموعة**\n\n"
            "ar\n\n"
            "إذا لم تظهر المجموعة التي أنت مشرف بها أو تملكها بالأسفل:\n"
            "• قم بإرسال الأمر `/reload` في المجموعة ثم أعد المحاولة.\n"
            f"• تأكد من وجود هذا البوت مُفعّل في مجموعتك: @{self.me.username}\n"
            "• ثم أرسل `/settings` في المجموعة ثم أضغط على \"فتح في دردشة خاصة\""
        )

        all_groups = db.get_all_groups()
        buttons = []
        for grp in all_groups:
            c_id = grp["chat_id"]
            title = grp.get("group_title") or f"مجموعة {c_id}"
            buttons.append([Button.inline(f"👥 {title}", data=f"grp_{c_id}")])

        if not buttons:
            buttons.append([Button.inline("👥 تالتة ثانوي (ازهر _ عام)", data="grp_-1002345678901")])

        return text, buttons

    def _build_page1_menu(self, chat_id: int) -> tuple[str, list]:
        """Builds Image 2 Screen: Settings Page 1 (Exact 12 Rows)"""
        group_cfg = db.get_group(chat_id)
        title = group_cfg.get("group_title") or f"Chat {chat_id}"

        text = f"**إعدادات المجموعة: {title}**\n\nاختر الإعدادات التي تريد تعديلها:"

        buttons = [
            # Row 1: مانع الرسائل المزعجة | القوانين
            [
                Button.inline("مانع الرسائل المزعجة 📨", data=f"sub_spam_{chat_id}"),
                Button.inline("القوانين 📜", data=f"sub_rules_{chat_id}")
            ],
            # Row 2: مانع الرسائل المكررة | الترحيب
            [
                Button.inline("مانع الرسائل المكررة 🗣️", data=f"sub_flood_{chat_id}"),
                Button.inline("الترحيب 💬", data=f"sub_welcome_{chat_id}")
            ],
            # Row 3: الحروف الهجائية | وداعًا
            [
                Button.inline("الحروف الهجائية 🕉️", data=f"sub_alphabet_{chat_id}"),
                Button.inline("وداعًا 👋", data=f"sub_goodbye_{chat_id}")
            ],
            # Row 4: القيود | التحقق Captcha
            [
                Button.inline("القيود 🔦", data=f"sub_restrict_{chat_id}"),
                Button.inline("التحقق Captcha 🧠", data=f"sub_captcha_{chat_id}")
            ],
            # Row 5: حظر | تقرير admin@
            [
                Button.inline("حظر 🔐", data=f"sub_ban_{chat_id}"),
                Button.inline("تقرير admin@ 🆘", data=f"sub_report_{chat_id}")
            ],
            # Row 6: إباحية | الوسائط
            [
                Button.inline("إباحية 🔞", data=f"sub_nsfw_{chat_id}"),
                Button.inline("الوسائط 📸", data=f"sub_media_{chat_id}")
            ],
            # Row 7: الوضع الليلي | الإنذارات
            [
                Button.inline("الوضع الليلي 🌘", data=f"sub_night_{chat_id}"),
                Button.inline("الإنذارات ❗", data=f"sub_warn_{chat_id}")
            ],
            # Row 8: رابط المجموعة | تنبيه Tag
            [
                Button.inline("رابط المجموعة 🔗", data=f"sub_link_{chat_id}"),
                Button.inline("تنبيه Tag 🔔", data=f"sub_tag_{chat_id}")
            ],
            # Row 9: البوت الحارس NEW
            [
                Button.inline("👮‍♂️ البوت الحارس NEW", data=f"sub_guardian_{chat_id}")
            ],
            # Row 10: وضع الموافقة
            [
                Button.inline("📭 وضع الموافقة", data=f"sub_approval_{chat_id}")
            ],
            # Row 11: حذف الرسائل
            [
                Button.inline("🗑️ حذف الرسائل", data=f"sub_delmsgs_{chat_id}")
            ],
            # Row 12 (Nav): أخرى ◀️ | إغلاق ✅ | Lang 🇸🇦
            [
                Button.inline("Lang 🇸🇦", data="nav_lang"),
                Button.inline("إغلاق ✅", data="nav_close"),
                Button.inline("أخرى ◀️", data=f"nav_p2_{chat_id}")
            ]
        ]
        return text, buttons

    def _build_page2_menu(self, chat_id: int) -> tuple[str, list]:
        """Builds Image 3 Screen: Settings Page 2 (Exact 12 Rows)"""
        group_cfg = db.get_group(chat_id)
        title = group_cfg.get("group_title") or f"Chat {chat_id}"

        text = f"**إعدادات المجموعة: {title}**\n\nاختر الإعدادات التي تريد تعديلها:"

        buttons = [
            # Row 1: الموضوع
            [Button.inline("الموضوع 📦", data=f"sub_topics_{chat_id}")],
            # Row 2: الكلمات المحظورة
            [Button.inline("الكلمات المحظورة 🔤", data=f"sub_badwords_{chat_id}")],
            # Row 3: تكرار الرسائل
            [Button.inline("تكرار الرسائل 🗣️", data=f"sub_repetition_{chat_id}")],
            # Row 4: إدارة الأعضاء (Forced Add is here!)
            [Button.inline("إدارة الأعضاء 👥", data=f"sub_members_{chat_id}")],
            # Row 5: المستخدمون المتخفون
            [Button.inline("المستخدمون المتخفون 👻", data=f"sub_anon_{chat_id}")],
            # Row 6: مجموعة المناقشة NEW
            [Button.inline("📢 مجموعة المناقشة NEW", data=f"sub_discussion_{chat_id}")],
            # Row 7: الأوامر الشخصية
            [Button.inline("الأوامر الشخصية 📱", data=f"sub_customcmds_{chat_id}")],
            # Row 8: ملصقات سحرية وصور متحركة
            [Button.inline("ملصقات سحرية وصور متحركة 🎭", data=f"sub_stickers_{chat_id}")],
            # Row 9: الرسائل الطويلة
            [Button.inline("الرسائل الطويلة ✏️", data=f"sub_longmsgs_{chat_id}")],
            # Row 10: إدارة القنوات NEW
            [Button.inline("📢 إدارة القنوات NEW", data=f"sub_channels_{chat_id}")],
            # Row 11: أذونات | قناة سجل المجموعة
            [
                Button.inline("أذونات 🪄", data=f"sub_perms_{chat_id}"),
                Button.inline("قناة سجل المجموعة 🔍", data=f"sub_logchan_{chat_id}")
            ],
            # Row 12 (Nav): العودة ◀️ | إغلاق ✅ | Lang 🇸🇦
            [
                Button.inline("Lang 🇸🇦", data="nav_lang"),
                Button.inline("إغلاق ✅", data="nav_close"),
                Button.inline("العودة ◀️", data=f"nav_p1_{chat_id}")
            ]
        ]
        return text, buttons

    # =========================================================================
    # Sub-Menu Renderers & Handlers
    # =========================================================================

    def _build_members_submenu(self, chat_id: int) -> tuple[str, list]:
        """Sub-menu for إدارة الأعضاء 👥 (Forced Add Control)"""
        cfg = db.get_group(chat_id)
        fa_status = "مفعل ✅" if cfg.get("force_add_enabled", 1) else "معطل ❌"
        req = cfg.get("required_adds", 1)
        timeout = cfg.get("warning_timeout", 15)

        text = (
            f"👥 **إدارة الأعضاء ونظام الإضافة الإجبارية (Forced Add)**\n"
            f"📍 المجموعة: `{cfg.get('group_title')}`\n\n"
            f"🛡️ **حالة الإضافة الإجبارية:** {fa_status}\n"
            f"👥 **عدد الإضافات المطلوبة من كل عضو:** {req} أصدقاء\n"
            f"⏳ **مدة بقاء رسالة التحذير قبل الحذف:** {timeout} ثانية\n"
            f"🗑️ **حذف رسائل غير المضيفين:** فوري وتلقائي لحين الإضافة\n\n"
            f"اضغط على الأزرار بالأسفل للتعديل الفوري:"
        )

        buttons = [
            [Button.inline(f"الإضافة الإجبارية: {fa_status}", data=f"tog_fa_{chat_id}")],
            [
                Button.inline("1️⃣ المطلوب: 1", data=f"req_1_{chat_id}"),
                Button.inline("2️⃣ المطلوب: 2", data=f"req_2_{chat_id}"),
                Button.inline("3️⃣ المطلوب: 3", data=f"req_3_{chat_id}"),
                Button.inline("5️⃣ المطلوب: 5", data=f"req_5_{chat_id}")
            ],
            [
                Button.inline("⏳ 10 ثوان", data=f"tout_10_{chat_id}"),
                Button.inline("⏳ 15 ثانية", data=f"tout_15_{chat_id}"),
                Button.inline("⏳ 30 ثانية", data=f"tout_30_{chat_id}")
            ],
            [Button.inline("◀️ رجوع للقائمة", data=f"nav_p2_{chat_id}")]
        ]
        return text, buttons

    def _build_spam_submenu(self, chat_id: int) -> tuple[str, list]:
        """Sub-menu for مانع الرسائل المزعجة 📨"""
        cfg = db.get_group(chat_id)
        link_st = "مفعل ✅" if cfg.get("anti_link", 1) else "معطل ❌"
        fwd_st = "مفعل ✅" if cfg.get("anti_forward", 0) else "معطل ❌"

        text = (
            f"📨 **مانع الرسائل المزعجة والإعلانات (Anti-Spam / Anti-Link)**\n"
            f"📍 المجموعة: `{cfg.get('group_title')}`\n\n"
            f"🚫 **قفل الروابط والإعلانات والمعرفات (@):** {link_st}\n"
            f"🚫 **قفل الرسائل المحولة والتوجيه:** {fwd_st}\n\n"
            f"اضغط للتفعيل أو التعطيل:"
        )

        buttons = [
            [Button.inline(f"قفل الروابط والمعرفات: {link_st}", data=f"tog_link_{chat_id}")],
            [Button.inline(f"قفل إعادة التوجيه (Forward): {fwd_st}", data=f"tog_fwd_{chat_id}")],
            [Button.inline("◀️ رجوع للقائمة", data=f"nav_p1_{chat_id}")]
        ]
        return text, buttons

    def _build_rules_submenu(self, chat_id: int) -> tuple[str, list]:
        """Sub-menu for القوانين 📜"""
        cfg = db.get_group(chat_id)
        r_st = "مفعل ✅" if cfg.get("rules_enabled", 1) else "معطل ❌"
        rules_preview = cfg.get("rules_text") or "القوانين الافتراضية محددة."

        text = (
            f"📜 **قوانين المجموعة (Rules Settings)**\n"
            f"📍 المجموعة: `{cfg.get('group_title')}`\n\n"
            f"حالة عرض القوانين: **{r_st}**\n\n"
            f"📝 **نص القوانين الحالي:**\n{rules_preview}"
        )

        buttons = [
            [Button.inline(f"تفعيل/تعطيل القوانين: {r_st}", data=f"tog_rules_{chat_id}")],
            [Button.inline("◀️ رجوع للقائمة", data=f"nav_p1_{chat_id}")]
        ]
        return text, buttons

    def _build_flood_submenu(self, chat_id: int) -> tuple[str, list]:
        """Sub-menu for مانع الرسائل المكررة 🗣️"""
        cfg = db.get_group(chat_id)
        fl_st = "مفعل ✅" if cfg.get("anti_spam", 1) else "معطل ❌"

        text = (
            f"🗣️ **مانع التكرار والفيضان (Anti-Flood Control)**\n"
            f"📍 المجموعة: `{cfg.get('group_title')}`\n\n"
            f"⚡ **الحالة:** {fl_st}\n"
            f"⏱️ **الحساسية:** حد أقصى 4 رسائل خلال 5 ثوانٍ.\n"
            f"عند التجاوز يتم حذف الرسائل وحظر التكرار تلقائياً."
        )

        buttons = [
            [Button.inline(f"مانع التكرار: {fl_st}", data=f"tog_flood_{chat_id}")],
            [Button.inline("◀️ رجوع للقائمة", data=f"nav_p1_{chat_id}")]
        ]
        return text, buttons

    def _build_welcome_submenu(self, chat_id: int) -> tuple[str, list]:
        """Sub-menu for الترحيب 💬"""
        cfg = db.get_group(chat_id)
        w_st = "مفعل ✅" if cfg.get("welcome_enabled", 1) else "معطل ❌"

        text = (
            f"💬 **إعدادات رسالة الترحيب بالأعضاء الجدد**\n"
            f"📍 المجموعة: `{cfg.get('group_title')}`\n\n"
            f"الحالة: **{w_st}**\n"
            f"تتضمن رسالة الترحيب ترحيباً بالعضو مع زر مدمج وسريع لفتح جهات الاتصال وإضافة الأصدقاء فوراً."
        )

        buttons = [
            [Button.inline(f"رسالة الترحيب: {w_st}", data=f"tog_welcome_{chat_id}")],
            [Button.inline("◀️ رجوع للقائمة", data=f"nav_p1_{chat_id}")]
        ]
        return text, buttons

    def _build_media_submenu(self, chat_id: int) -> tuple[str, list]:
        """Sub-menu for الوسائط 📸"""
        cfg = db.get_group(chat_id)
        p_st = "مفعل ✅" if cfg.get("block_photos", 0) else "معطل ❌"
        v_st = "مفعل ✅" if cfg.get("block_videos", 0) else "معطل ❌"
        s_st = "مفعل ✅" if cfg.get("block_stickers", 0) else "معطل ❌"
        a_st = "مفعل ✅" if cfg.get("block_voice", 0) else "معطل ❌"

        text = (
            f"📸 **إعدادات قفل وحظر الوسائط**\n"
            f"📍 المجموعة: `{cfg.get('group_title')}`\n\n"
            f"اختر نوع الوسائط التي ترغب بقفلها داخل المجموعة:"
        )

        buttons = [
            [
                Button.inline(f"الصور: {p_st}", data=f"tog_photo_{chat_id}"),
                Button.inline(f"الفيديوهات: {v_st}", data=f"tog_video_{chat_id}")
            ],
            [
                Button.inline(f"الملصقات: {s_st}", data=f"tog_stick_{chat_id}"),
                Button.inline(f"الصوتيات: {a_st}", data=f"tog_voice_{chat_id}")
            ],
            [Button.inline("◀️ رجوع للقائمة", data=f"nav_p1_{chat_id}")]
        ]
        return text, buttons

    def _build_restrictions_submenu(self, chat_id: int) -> tuple[str, list]:
        """Sub-menu for القيود 🔦 (قفل الدردشة بالكامل)"""
        cfg = db.get_group(chat_id)
        lock_st = "🔒 مقفلة (للمشرفين فقط)" if cfg.get("chat_locked", 0) else "🔓 مفتوحة للجميع"

        text = (
            f"🔦 **قيود المحادثة وقفل الدردشة**\n"
            f"📍 المجموعة: `{cfg.get('group_title')}`\n\n"
            f"حالة الدردشة الحالية: **{lock_st}**\n\n"
            f"عند قفل الدردشة، يتم حذف رسائل جميع الأعضاء العاديين فورياً ولا يمكن لأحد إرسال الرسائل سوى المشرفين."
        )

        buttons = [
            [Button.inline(f"تبديل حالة الدردشة: {lock_st}", data=f"tog_chatlock_{chat_id}")],
            [Button.inline("◀️ رجوع للقائمة", data=f"nav_p1_{chat_id}")]
        ]
        return text, buttons

    def _build_simple_submenu(self, chat_id: int, title: str, status_key: str, desc: str, page: int = 1) -> tuple[str, list]:
        """Generic interactive sub-menu builder with live toggle state"""
        cfg = db.get_group(chat_id)
        curr_val = cfg.get(status_key, 0)
        st_text = "مفعل ✅" if curr_val else "معطل ❌"

        text = (
            f"⚙️ **{title}**\n"
            f"📍 المجموعة: `{cfg.get('group_title')}`\n\n"
            f"{desc}\n\n"
            f"الحالة الحالية: **{st_text}**"
        )

        back_target = f"nav_p1_{chat_id}" if page == 1 else f"nav_p2_{chat_id}"
        buttons = [
            [Button.inline(f"تبديل الحالة: {st_text}", data=f"tog_gen_{status_key}_{chat_id}_{page}")],
            [Button.inline("◀️ رجوع للقائمة", data=back_target)]
        ]
        return text, buttons

    # =========================================================================
    # Callback Query Router (Whisper Open / Delete / Settings Navigation)
    # =========================================================================

    async def _handle_callback(self, event: events.CallbackQuery.Event):
        try:
            data = (event.data or b"").decode("utf-8")
            caller_id = event.sender_id

            # ---------------------------------------------------------------
            # 1. WHISPER OPEN MODAL (Exact Image 2: "فتح الهمسه")
            # ---------------------------------------------------------------
            if data.startswith("wh_open_") or data.startswith("wh_"):
                whisper_id = data.replace("wh_open_", "").replace("wh_", "")
                whisper = db.get_whisper(whisper_id)
                if not whisper:
                    await event.answer("⚠️ هذه الهمسة السرية غير متوفرة أو تم حذفها.", alert=True)
                    return

                caller_user = await event.get_sender()
                caller_username = (getattr(caller_user, "username", "") or "").lower()

                sender_id = whisper["sender_id"]
                target_raw = str(whisper.get("target_identifier", "")).lower().strip().replace("@", "")
                target_id = whisper.get("target_id", 0)
                target_uname = str(whisper.get("target_name", "")).lower().strip().replace("@", "")

                is_sender = (caller_id == sender_id)
                is_target_id = (caller_id == target_id or str(caller_id) == target_raw)
                is_target_uname = bool(caller_username and (caller_username == target_raw or caller_username == target_uname))
                is_own = await self.is_owner(whisper["chat_id"], caller_id)

                if is_sender:
                    await event.answer(f"🔒 نص همستك السرية المرسلة:\n\n{whisper['secret_text']}", alert=True)
                elif is_target_id or is_target_uname:
                    sender_label = whisper.get("sender_name", "المرسل")
                    await event.answer(f"💌 همسة سرية موجهة إليك من [{sender_label}]:\n\n{whisper['secret_text']}", alert=True)
                elif is_own:
                    await event.answer(f"👑 [معاينة مالك المجموعة]:\n\n{whisper['secret_text']}", alert=True)
                else:
                    target_label = whisper.get("target_name") or whisper.get("target_identifier") or "المستلم"
                    await event.answer(f"🚫 عذراً! هذه الهمسة سرية وموجهة إلى ({target_label}) فقط ولا يمكنك فتحها.", alert=True)
                return

            # ---------------------------------------------------------------
            # 2. WHISPER DELETE (Exact Image 2: "حذف الهمسه")
            # ---------------------------------------------------------------
            if data.startswith("wh_del_"):
                whisper_id = data.replace("wh_del_", "")
                whisper = db.get_whisper(whisper_id)
                if not whisper:
                    try:
                        await event.delete()
                    except Exception:
                        pass
                    await event.answer("تم حذف الرسالة", alert=False)
                    return

                caller_user = await event.get_sender()
                caller_username = (getattr(caller_user, "username", "") or "").lower()

                sender_id = whisper["sender_id"]
                target_raw = str(whisper.get("target_identifier", "")).lower().strip().replace("@", "")
                target_id = whisper.get("target_id", 0)

                is_sender = (caller_id == sender_id)
                is_target = (caller_id == target_id or str(caller_id) == target_raw)
                is_own = await self.is_owner(whisper["chat_id"], caller_id)

                if is_sender or is_target or is_own:
                    try:
                        await event.delete()
                        await event.answer("🗑️ تم حذف الهمسة بنجاح.", alert=False)
                    except Exception:
                        await event.answer("⚠️ تعذر حذف الهمسة، تأكد من صلاحيات البوت.", alert=True)
                else:
                    await event.answer("🚫 لا يمكنك حذف هذه الهمسة لأنها ليست لك!", alert=True)
                return

            # ---------------------------------------------------------------
            # 3. Navigation Actions
            # ---------------------------------------------------------------
            if data == "nav_close":
                await event.edit("✅ تم إغلاق لوحة الإعدادات وحفظ كافة التعديلات بنجاح.\nيمكنك فتحها في أي وقت عبر إرسال `/start` في الخاص.")
                await event.answer("تم الإغلاق بنجاح")
                return

            if data == "nav_lang":
                await event.answer("🇸🇦 لغة لوحة التحكم: العربية (مفعلة تلقائياً)", alert=True)
                return

            # Group Selection -> Page 1
            if data.startswith("grp_"):
                chat_id = int(data[4:])
                text, buttons = self._build_page1_menu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer()
                return

            # Nav Page 1 / Page 2
            if data.startswith("nav_p1_"):
                chat_id = int(data[7:])
                text, buttons = self._build_page1_menu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer()
                return

            if data.startswith("nav_p2_"):
                chat_id = int(data[7:])
                text, buttons = self._build_page2_menu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer()
                return

            # Sub-Menus Router
            if data.startswith("sub_members_"):
                chat_id = int(data[12:])
                text, buttons = self._build_members_submenu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer()
                return

            if data.startswith("sub_spam_"):
                chat_id = int(data[9:])
                text, buttons = self._build_spam_submenu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer()
                return

            if data.startswith("sub_rules_"):
                chat_id = int(data[10:])
                text, buttons = self._build_rules_submenu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer()
                return

            if data.startswith("sub_flood_"):
                chat_id = int(data[10:])
                text, buttons = self._build_flood_submenu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer()
                return

            if data.startswith("sub_welcome_"):
                chat_id = int(data[12:])
                text, buttons = self._build_welcome_submenu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer()
                return

            if data.startswith("sub_media_"):
                chat_id = int(data[10:])
                text, buttons = self._build_media_submenu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer()
                return

            if data.startswith("sub_restrict_"):
                chat_id = int(data[13:])
                text, buttons = self._build_restrictions_submenu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer()
                return

            menu_meta = {
                "sub_alphabet_": ("الحروف الهجائية 🕉️", "alphabet_filter", "فلترة الحروف لمنع اللغات الفارسية والعبرية والرموز المشبوهة.", 1),
                "sub_goodbye_": ("وداعًا 👋", "goodbye_enabled", "إرسال رسالة وداع عند مغادرة أي عضو للمجموعة.", 1),
                "sub_captcha_": ("التحقق Captcha 🧠", "captcha_enabled", "طلب التحقق البشري من العضو الجديد قبل السماح له بالكتابة.", 1),
                "sub_ban_": ("حظر 🔐", "admin_perms", "إدارة قائمة المحظورين وإلغاء الحظر عن الأعضاء.", 1),
                "sub_report_": ("تقرير admin@ 🆘", "report_admin", "تنبيه المشرفين فورياً عند كتابة @admin في الشات.", 1),
                "sub_nsfw_": ("إباحية 🔞", "nsfw_filter", "فلترة الصور والملصقات غير اللائقة وحذفها فوراً.", 1),
                "sub_night_": ("الوضع الليلي 🌘", "night_mode", "قفل المجموعة تلقائياً خلال فترة الليل للمحافظة على الهدوء.", 1),
                "sub_warn_": ("الإنذارات ❗", "warn_limit", "نظام الإنذارات التلقائي (3 إنذارات تؤدي لكتم العضو).", 1),
                "sub_link_": ("رابط المجموعة 🔗", "clean_service", "تصدير وتثبيت رابط دعوة المجموعة للأعضاء.", 1),
                "sub_tag_": ("تنبيه Tag 🔔", "anti_tag", "منع الإشارات الجماعية والتاجات المزعجة (@all).", 1),
                "sub_guardian_": ("👮‍♂️ البوت الحارس NEW", "guardian_bot", "ميزة الحماية المتقدمة ضد هجمات التفليش والحسابات الوهمية.", 1),
                "sub_approval_": ("📭 وضع الموافقة", "approval_mode", "طلب موافقة المشرفين لانضمام أي عضو جديد للمجموعة.", 1),
                "sub_delmsgs_": ("🗑️ حذف الرسائل", "clean_service", "تنظيف رسائل الخدمة (انضمام، مغادرة، وتثبيت رسائل).", 1),
                "sub_topics_": ("الموضوع 📦", "topics_enabled", "إدارة وتصنيف أقسام وموضوعات المجموعة.", 2),
                "sub_badwords_": ("الكلمات المحظورة 🔤", "block_badwords", "فلترة وحذف الكلمات البذيئة والشتائم تلقائياً.", 2),
                "sub_repetition_": ("تكرار الرسائل 🗣️", "anti_spam", "ضبط حساسية منع تكرار نفس الرسالة من نفس العضو.", 2),
                "sub_anon_": ("المستخدمون المتخفون 👻", "block_anonymous", "منع التحدث بأسماء القنوات وإلزام الأعضاء بحساباتهم الشخصية.", 2),
                "sub_discussion_": ("📢 مجموعة المناقشة NEW", "topics_enabled", "ربط المجموعة بقناة النشر التعليمية الرسمية.", 2),
                "sub_customcmds_": ("الأوامر الشخصية 📱", "custom_cmds", "إدارة وتفعيل الردود التلقائية والأوامر المخصصة.", 2),
                "sub_stickers_": ("ملصقات سحرية وصور متحركة 🎭", "block_stickers", "قفل الملصقات والصور المتحركة الثقيلة في الشات.", 2),
                "sub_longmsgs_": ("الرسائل الطويلة ✏️", "long_msgs_lock", "قفل الرسائل الطويلة جداً التي تتجاوز 800 حرف.", 2),
                "sub_channels_": ("📢 إدارة القنوات NEW", "channel_manage", "إدارة وتوجيه رسائل القنوات المرتبطة.", 2),
                "sub_perms_": ("أذونات 🪄", "admin_perms", "تحديد صلاحيات المشرفين وتعيين رتب الإدارة.", 2),
                "sub_logchan_": ("قناة سجل المجموعة 🔍", "log_channel", "إرسال تقارير الحذف والحظر إلى قناة سجل خاصة.", 2)
            }

            for prefix, (t_title, col, desc, p_num) in menu_meta.items():
                if data.startswith(prefix):
                    chat_id = int(data[len(prefix):])
                    text, buttons = self._build_simple_submenu(chat_id, t_title, col, desc, p_num)
                    await event.edit(text, buttons=buttons)
                    await event.answer()
                    return

            # Specific Toggles
            if data.startswith("tog_fa_"):
                chat_id = int(data[7:])
                cfg = db.get_group(chat_id)
                new_v = 0 if cfg.get("force_add_enabled", 1) else 1
                db.update_group_settings(chat_id, force_add_enabled=new_v)
                text, buttons = self._build_members_submenu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer(f"تم {'تفعيل' if new_v else 'تعطيل'} الإضافة الإجبارية")
                return

            if data.startswith("req_"):
                parts = data.split("_")
                val = int(parts[1])
                chat_id = int(parts[2])
                db.update_group_settings(chat_id, required_adds=val)
                text, buttons = self._build_members_submenu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer(f"تم تعيين المطلوب: {val} أصدقاء")
                return

            if data.startswith("tout_"):
                parts = data.split("_")
                val = int(parts[1])
                chat_id = int(parts[2])
                db.update_group_settings(chat_id, warning_timeout=val)
                text, buttons = self._build_members_submenu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer(f"تم تعيين وقت التحذير: {val} ثوان")
                return

            if data.startswith("tog_link_"):
                chat_id = int(data[9:])
                cfg = db.get_group(chat_id)
                new_v = 0 if cfg.get("anti_link", 1) else 1
                db.update_group_settings(chat_id, anti_link=new_v)
                text, buttons = self._build_spam_submenu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer(f"تم {'تفعيل' if new_v else 'تعطيل'} قفل الروابط")
                return

            if data.startswith("tog_fwd_"):
                chat_id = int(data[8:])
                cfg = db.get_group(chat_id)
                new_v = 0 if cfg.get("anti_forward", 0) else 1
                db.update_group_settings(chat_id, anti_forward=new_v)
                text, buttons = self._build_spam_submenu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer(f"تم {'تفعيل' if new_v else 'تعطيل'} قفل التوجيه")
                return

            if data.startswith("tog_rules_"):
                chat_id = int(data[10:])
                cfg = db.get_group(chat_id)
                new_v = 0 if cfg.get("rules_enabled", 1) else 1
                db.update_group_settings(chat_id, rules_enabled=new_v)
                text, buttons = self._build_rules_submenu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer(f"تم {'تفعيل' if new_v else 'تعطيل'} القوانين")
                return

            if data.startswith("tog_flood_"):
                chat_id = int(data[10:])
                cfg = db.get_group(chat_id)
                new_v = 0 if cfg.get("anti_spam", 1) else 1
                db.update_group_settings(chat_id, anti_spam=new_v)
                text, buttons = self._build_flood_submenu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer(f"تم {'تفعيل' if new_v else 'تعطيل'} مانع التكرار")
                return

            if data.startswith("tog_welcome_"):
                chat_id = int(data[12:])
                cfg = db.get_group(chat_id)
                new_v = 0 if cfg.get("welcome_enabled", 1) else 1
                db.update_group_settings(chat_id, welcome_enabled=new_v)
                text, buttons = self._build_welcome_submenu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer(f"تم {'تفعيل' if new_v else 'تعطيل'} الترحيب")
                return

            if data.startswith("tog_chatlock_"):
                chat_id = int(data[13:])
                cfg = db.get_group(chat_id)
                new_v = 0 if cfg.get("chat_locked", 0) else 1
                db.update_group_settings(chat_id, chat_locked=new_v)
                text, buttons = self._build_restrictions_submenu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer(f"تم {'قفل الدردشة' if new_v else 'فتح الدردشة'}")
                return

            if data.startswith(("tog_photo_", "tog_video_", "tog_stick_", "tog_voice_")):
                prefix = data[:10]
                chat_id = int(data[10:])
                col_map = {
                    "tog_photo_": "block_photos",
                    "tog_video_": "block_videos",
                    "tog_stick_": "block_stickers",
                    "tog_voice_": "block_voice"
                }
                col = col_map[prefix]
                cfg = db.get_group(chat_id)
                new_v = 0 if cfg.get(col, 0) else 1
                db.update_group_settings(chat_id, **{col: new_v})
                text, buttons = self._build_media_submenu(chat_id)
                await event.edit(text, buttons=buttons)
                await event.answer("تم تحديث إعداد الوسائط")
                return

            if data.startswith("tog_gen_"):
                parts = data.split("_")
                col = parts[2]
                chat_id = int(parts[3])
                page_num = int(parts[4])
                cfg = db.get_group(chat_id)
                new_v = 0 if cfg.get(col, 0) else 1
                db.update_group_settings(chat_id, **{col: new_v})

                text, buttons = self._build_simple_submenu(chat_id, f"إعداد {col}", col, "تم تحديث الإعداد وحفظه بنجاح.", page_num)
                await event.edit(text, buttons=buttons)
                await event.answer("تم حفظ التعديل")
                return

        except Exception as e:
            logger.error(f"Callback error: {e}", exc_info=True)

    # =========================================================================
    # Group Member Events (Invites & Welcome)
    # =========================================================================

    async def _handle_chat_action(self, event: events.ChatAction.Event):
        try:
            chat = await event.get_chat()
            chat_id = event.chat_id
            chat_title = getattr(chat, 'title', f"Chat {chat_id}")
            group_cfg = db.get_group(chat_id, chat_title)

            # Auto Clean Service Messages if enabled
            if group_cfg.get("clean_service", 1):
                try:
                    await event.delete()
                except Exception:
                    pass

            # Member adds friend -> record invite & notify
            if event.user_added:
                inviter = await event.get_added_by()
                inviter_id = inviter.id if inviter else None
                inviter_name = (inviter.first_name or "") if inviter else "Unknown"

                added_users = await event.get_users()
                for user in added_users:
                    if not user or user.bot:
                        continue
                    invited_id = user.id
                    invited_name = user.first_name or user.username or f"User {user.id}"

                    if inviter_id and inviter_id != invited_id:
                        recorded = db.record_invite(chat_id, inviter_id, inviter_name, invited_id, invited_name)
                        if recorded:
                            current_invites = db.get_user_invites(chat_id, inviter_id)
                            required = group_cfg.get("required_adds", 1)
                            db.log_activity(
                                chat_id, chat_title, inviter_id, inviter_name, 
                                "INVITE_ADDED", 
                                f"أضاف {invited_name} (رصيده: {current_invites}/{required})"
                            )

                            mention = f"[{inviter_name}](tg://user?id={inviter_id})"
                            status_note = "🎉 يمكنك الآن التحدث بحرية تامة داخل المجموعة!" if current_invites >= required else f"تبقى لك {required - current_invites} إضافات لتأكيد أهليتك."
                            confirm_msg = await event.respond(
                                f"🌟 **شكراً لك يا {mention}!**\n"
                                f"✅ تم بنجاح احتساب إضافة صديقك: `{invited_name}`.\n"
                                f"📊 رصيد إضافاتك الحالي: **{current_invites}** من أصل **{required}**.\n"
                                f"{status_note}"
                            )
                            asyncio.create_task(self._auto_delete_message(confirm_msg, 15))

            # New member welcome with Quick-Add Native Contact Share
            if (event.user_joined or event.user_added) and group_cfg.get("welcome_enabled", 1):
                new_users = await event.get_users()
                for user in new_users:
                    if user and not user.bot:
                        u_name = user.first_name or user.username or "عزيزي الطالب"
                        u_mention = f"[{u_name}](tg://user?id={user.id})"
                        req = group_cfg.get("required_adds", 1)
                        group_link = await self.get_or_export_invite_link(chat_id, chat)
                        encoded_title = urllib.parse.quote(chat_title)
                        share_url = f"https://t.me/share/url?url={group_link}&text=انضم%20معنا%20إلى%20مجموعة%20{encoded_title}"

                        buttons = [
                            [Button.url("➕ اضغط هنا لإضافة أصدقائك الآن", share_url)]
                        ]
                        welcome_text = (
                            f"👋 **أهلاً بك {u_mention} في {chat_title}!**\n\n"
                            f"📚 دفعة الثانوية العامة 2026\n"
                            f"🛡️ **تنبيه:** المجموعة محمية بنظام **الإضافة الإجبارية**.\n"
                            f"👥 يتوجب عليك إضافة على الأقل **({req})** أصدقاء لتتمكن من التفاعل والمشاركة."
                        )
                        welcome_msg = await event.respond(welcome_text, buttons=buttons)
                        asyncio.create_task(self._auto_delete_message(welcome_msg, 20))

        except Exception as e:
            logger.error(f"ChatAction error: {e}", exc_info=True)

    # =========================================================================
    # Group & Private Messages Router
    # =========================================================================

    async def _handle_new_message(self, event: events.NewMessage.Event):
        try:
            # 1. Private Chat Handler (/start & typing secret whisper)
            if event.is_private:
                await self._handle_private_message(event)
                return

            if not event.is_group:
                return

            chat = await event.get_chat()
            chat_id = event.chat_id
            chat_title = getattr(chat, 'title', f"Chat {chat_id}")
            sender = await event.get_sender()

            if not sender or not hasattr(sender, 'id'):
                return

            sender_id = sender.id
            sender_name = getattr(sender, 'first_name', '') or getattr(sender, 'username', '') or f"User {sender_id}"

            if sender_id == self.me.id:
                return

            raw_text = (event.raw_text or "").strip()
            norm_text = normalize_arabic(raw_text)
            db.get_or_create_user(chat_id, sender_id, sender_name)
            group_cfg = db.get_group(chat_id, chat_title)

            # ---------------------------------------------------------------
            # 2. IN-LINE WHISPER SYSTEM (همسة/همسه بالرد -> رابط الخاص -> نشر بالمجموعة)
            # ---------------------------------------------------------------
            whisper_handled = await self._handle_whisper_trigger(event, raw_text, norm_text, chat_id, chat_title, sender_id, sender_name)
            if whisper_handled:
                return

            # ---------------------------------------------------------------
            # 3. INTERACTIVE BOT DICTIONARY & STRICT OWNER-ONLY COMMANDS
            # ---------------------------------------------------------------
            dict_or_cmd_handled = await self._handle_group_dictionary_and_commands(
                event, chat_id, chat_title, sender, sender_id, sender_name, raw_text, norm_text, group_cfg
            )
            if dict_or_cmd_handled:
                return

            # Exemption: Group Admins and Whitelisted users bypass moderation
            is_adm = await self.is_admin_or_owner(chat_id, sender_id)
            if is_adm:
                return

            if db.is_whitelisted(chat_id, sender_id):
                return

            # ---------------------------------------------------------------
            # 4. Moderation Enforcements
            # ---------------------------------------------------------------

            # Chat Locked
            if group_cfg.get("chat_locked", 0) == 1:
                try:
                    await event.delete()
                except Exception:
                    pass
                return

            # Anti-Forward
            if group_cfg.get("anti_forward", 0) == 1 and event.message.fwd_from:
                try:
                    await event.delete()
                except Exception:
                    pass
                db.log_activity(chat_id, chat_title, sender_id, sender_name, "FORWARD_BLOCKED", "حذف رسالة محولة/توجيه")
                return

            # Anti-Link
            if group_cfg.get("anti_link", 1) == 1 and LINK_REGEX.search(raw_text):
                try:
                    await event.delete()
                except Exception:
                    pass
                db.log_activity(chat_id, chat_title, sender_id, sender_name, "LINK_BLOCKED", f"حذف رابط: {raw_text[:40]}")
                warn = await event.respond(f"🚫 عذراً يا [{sender_name}](tg://user?id={sender_id})! نشر الروابط والإعلانات والمعرفات ممنوع في هذه المجموعة.")
                asyncio.create_task(self._auto_delete_message(warn, 10))
                return

            # Media Blocking
            if group_cfg.get("block_photos", 0) and event.message.photo:
                try:
                    await event.delete()
                except Exception:
                    pass
                return

            if group_cfg.get("block_stickers", 0) and (event.message.sticker or event.message.gif):
                try:
                    await event.delete()
                except Exception:
                    pass
                return

            if group_cfg.get("block_voice", 0) and (event.message.voice or event.message.audio):
                try:
                    await event.delete()
                except Exception:
                    pass
                return

            # Long Message Blocker (>800 chars)
            if group_cfg.get("long_msgs_lock", 0) and len(raw_text) > 800:
                try:
                    await event.delete()
                except Exception:
                    pass
                warn = await event.respond(f"⚠️ عذراً يا [{sender_name}](tg://user?id={sender_id})! الرسائل الطويلة جداً محظورة للحفاظ على ترتيب المجموعة.")
                asyncio.create_task(self._auto_delete_message(warn, 10))
                return

            # Anti-Spam (Burst: max 4 msgs / 5s)
            if group_cfg.get("anti_spam", 1) == 1:
                user_key = f"{chat_id}:{sender_id}"
                now = time.time()
                times = self.user_message_times.setdefault(user_key, [])
                times.append(now)
                self.user_message_times[user_key] = [t for t in times if now - t <= 5]
                if len(self.user_message_times[user_key]) > 4:
                    try:
                        await event.delete()
                    except Exception:
                        pass
                    db.log_activity(chat_id, chat_title, sender_id, sender_name, "SPAM_BLOCKED", "تكرار رسائل سريع")
                    return

            # ---------------------------------------------------------------
            # 5. FORCED ADD ENFORCEMENT (الإضافة الإجبارية)
            # ---------------------------------------------------------------
            if group_cfg.get("force_add_enabled", 1) == 1:
                required_adds = group_cfg.get("required_adds", 1)
                user_invites = db.get_user_invites(chat_id, sender_id)

                if user_invites < required_adds:
                    try:
                        await event.delete()
                    except MessageDeleteForbiddenError:
                        logger.warning(f"Bot lacks delete permissions in {chat_id}")
                    except Exception as e:
                        logger.error(f"Delete failed: {e}")

                    db.log_activity(chat_id, chat_title, sender_id, sender_name, "MESSAGE_DELETED", f"حذف رسالة لعدم استيفاء الإضافة ({user_invites}/{required_adds})")

                    throttle_key = f"{chat_id}:{sender_id}"
                    now = time.time()
                    last_sent = self.last_warning_time.get(throttle_key, 0)

                    if now - last_sent > 12:
                        self.last_warning_time[throttle_key] = now
                        warning_timeout = group_cfg.get("warning_timeout", 15)
                        group_link = await self.get_or_export_invite_link(chat_id, chat)

                        encoded_title = urllib.parse.quote(chat_title)
                        share_url = f"https://t.me/share/url?url={group_link}&text=انضم%20معنا%20إلى%20مجموعة%20{encoded_title}"

                        buttons = [
                            [Button.url("👥 أضف أصدقاءك الآن للمجموعة", share_url)]
                        ]

                        mention = f"[{sender_name}](tg://user?id={sender_id})"
                        warning_text = (
                            f"⚠️ **عذراً يا {mention}!**\n\n"
                            f"🚫 لا يمكنك إرسال الرسائل في هذه المجموعة حتى تقوم بإضافة **{required_adds}** أصدقاء على الأقل.\n"
                            f"📊 **رصيد إضافاتك الحالي:** **{user_invites}** من أصل **{required_adds}**.\n\n"
                            f"اضغط على الزر بالأسفل لاختيار أصدقائك وإضافتهم فوراً! 👇\n\n"
                            f"⏳ *سيتم حذف هذا التنبيه تلقائياً بعد {warning_timeout} ثانية.*"
                        )

                        try:
                            sent_warning = await event.respond(warning_text, buttons=buttons)
                            asyncio.create_task(self._auto_delete_message(sent_warning, warning_timeout))
                        except Exception as warn_err:
                            logger.warning(f"Failed to dispatch warning: {warn_err}")

        except Exception as e:
            logger.error(f"Message handling error: {e}", exc_info=True)

    # =========================================================================
    # In-Private Chat Handler (/start & writing secret whisper in PM)
    # =========================================================================

    async def _handle_private_message(self, event: events.NewMessage.Event):
        raw_text = (event.raw_text or "").strip()
        sender = await event.get_sender()
        sender_id = sender.id if sender else 0
        sender_name = sender.first_name if sender else "User"

        # Check if user is currently replying with their secret whisper text in PM!
        if sender_id in self.user_whisper_sessions and not raw_text.startswith("/start"):
            token = self.user_whisper_sessions.pop(sender_id, None)
            if token:
                pending = db.get_pending_whisper(token)
                if pending:
                    secret_payload = raw_text
                    whisper_id = secrets.token_hex(4)
                    chat_id = pending["chat_id"]
                    reply_to_msg_id = pending["reply_to_msg_id"]
                    target_id = pending["target_id"]
                    target_name = pending["target_name"]

                    # Save whisper in DB
                    db.save_whisper(
                        whisper_id, chat_id, sender_id, pending["sender_name"],
                        str(target_id), target_id, target_name, secret_payload
                    )
                    db.delete_pending_whisper(token)

                    # Confirm to sender in PM
                    await event.respond("✅ **تم إرسال الهمسة السرية بنجاح إلى المجموعة!**\nيمكنك العودة للمجموعة الآن لمشاهدتها.")

                    # Post exact Image 2 Card in the Group!
                    try:
                        whisper_text = f"وصلتك همسه جديده من\n{pending['sender_name']}"
                        buttons = [
                            [Button.inline("فتح الهمسه", data=f"wh_open_{whisper_id}")],
                            [Button.inline("حذف الهمسه", data=f"wh_del_{whisper_id}")]
                        ]
                        await self.client.send_message(
                            chat_id,
                            whisper_text,
                            reply_to=reply_to_msg_id,
                            buttons=buttons
                        )
                        db.log_activity(chat_id, f"Chat {chat_id}", sender_id, sender_name, "WHISPER_SENT", f"إرسال همسة سرية عبر الخاص إلى {target_name}")
                    except Exception as send_err:
                        logger.error(f"Failed to post whisper card in group: {send_err}")
                    return

        # /start or /start wh_{token} or /start settings_{chat_id}
        if raw_text.startswith(("/start", "start", "البداية")):
            parts = raw_text.split()
            if len(parts) > 1:
                arg = parts[1]

                # Direct jump to group settings Page 1
                if arg.startswith("settings_"):
                    try:
                        c_id = int(arg.replace("settings_", ""))
                        out_text, buttons = self._build_page1_menu(c_id)
                        await event.respond(out_text, buttons=buttons)
                        return
                    except Exception:
                        pass

                # Whisper in PM entry: /start wh_{token}
                if arg.startswith("wh_"):
                    token = arg.replace("wh_", "")
                    pending = db.get_pending_whisper(token)
                    if pending:
                        self.user_whisper_sessions[sender_id] = token
                        target_name = pending["target_name"]
                        prompt_text = (
                            f"🔒 **كتابة الهمسة السرية:**\n\n"
                            f"👤 **المستلم:** {target_name}\n\n"
                            f"✍️ **أرسل الآن نص الهمسة هنا في الخاص وسأقوم بنشرها له في المجموعة فوراً!**\n"
                            f"*(رسالتك مشفرة ولن تظهر في الشات العام، فقط عبر زر تفاعلي)*"
                        )
                        await event.respond(prompt_text)
                        return
                    else:
                        await event.respond("⚠️ رابط الهمسة انتهت صلاحيته أو تم استخدامه بالفعل.")
                        return

            out_text, buttons = self._build_start_pm_markup(sender_id)
            await event.respond(out_text, buttons=buttons)
            return

    # =========================================================================
    # Secret Whisper Logic (همسة/همسه بالرد -> رابط الخاص -> إرسال بالمجموعة)
    # =========================================================================

    async def _handle_whisper_trigger(self, event, raw_text: str, norm_text: str, chat_id: int, chat_title: str, sender_id: int, sender_name: str) -> bool:
        """Processes whisper triggers: by reply (opening PM link) or inline args with normalized text"""
        whisper_keywords = ("همسه", "/whisper")
        first_token = norm_text.split()[0] if norm_text else ""

        if not any(first_token == k or first_token.startswith(k) for k in whisper_keywords):
            return False

        # Case A: User replies to another message with "همسة" or "همسه"
        if event.is_reply:
            reply_msg = None
            try:
                reply_msg = await event.get_reply_message()
            except Exception:
                pass

            if not reply_msg and event.message.reply_to:
                try:
                    reply_msg = await self.client.get_messages(chat_id, ids=event.message.reply_to.reply_to_msg_id)
                except Exception:
                    pass

            if reply_msg:
                target_id = reply_msg.sender_id or 0
                target_name = "صديقك"
                target_uname = ""
                try:
                    r_user = await reply_msg.get_sender()
                    if r_user:
                        target_id = r_user.id
                        target_name = getattr(r_user, 'first_name', '') or getattr(r_user, 'title', '') or f"User {target_id}"
                        target_uname = getattr(r_user, 'username', '') or ''
                except Exception:
                    pass

                # Extract secret if typed directly after "همسة" in the reply
                parts = raw_text.split(maxsplit=1)
                secret_payload = parts[1].strip() if len(parts) > 1 else ""

                if secret_payload:
                    try:
                        await event.delete()
                    except Exception:
                        pass
                    whisper_id = secrets.token_hex(4)
                    db.save_whisper(whisper_id, chat_id, sender_id, sender_name, str(target_id), target_id, target_name, secret_payload)

                    # Post exact Image 2 Card!
                    whisper_text = f"وصلتك همسه جديده من\n{sender_name}"
                    buttons = [
                        [Button.inline("فتح الهمسه", data=f"wh_open_{whisper_id}")],
                        [Button.inline("حذف الهمسه", data=f"wh_del_{whisper_id}")]
                    ]
                    await event.respond(whisper_text, reply_to=reply_msg.id, buttons=buttons)
                    db.log_activity(chat_id, chat_title, sender_id, sender_name, "WHISPER_SENT", f"إرسال همسة مباشرة إلى {target_name}")
                    return True
                else:
                    # User sent just "همسة" or "همسه" on reply: create pending token and prompt with private button!
                    try:
                        await event.delete()
                    except Exception:
                        pass

                    token = secrets.token_hex(6)
                    db.save_pending_whisper(token, chat_id, reply_msg.id, sender_id, sender_name, target_id, target_name, target_uname)

                    pm_url = f"https://t.me/{self.me.username}?start=wh_{token}"
                    buttons = [
                        [Button.url("🔒 اضغط هنا لكتابة الهمسة في الخاص", pm_url)]
                    ]
                    prompt = await event.respond(
                        f"🤫 **يا [{sender_name}](tg://user?id={sender_id})**\n"
                        f"اضغط على الزر بالأسفل لكتابة همستك السرية إلى [{target_name}](tg://user?id={target_id}) في الخاص: 👇",
                        reply_to=reply_msg.id,
                        buttons=buttons
                    )
                    asyncio.create_task(self._auto_delete_message(prompt, 60))
                    return True

        # Case B: Inline syntax in group: "همسة @username <النص>"
        match = re.match(r"^(همسة|همسه|/whisper)\s+(?:لـ|ل)?\s*(@[a-zA-Z0-9_]+|\d+)\s+(.+)$", raw_text, re.IGNORECASE | re.DOTALL)
        if match:
            target_arg = match.group(2).strip()
            secret_payload = match.group(3).strip()
            target_id = int(target_arg) if target_arg.isdigit() else 0
            target_uname = target_arg[1:] if target_arg.startswith("@") else ""
            target_display = target_arg

            try:
                await event.delete()
            except Exception:
                pass

            whisper_id = secrets.token_hex(4)
            db.save_whisper(whisper_id, chat_id, sender_id, sender_name, target_arg, target_id, target_display, secret_payload)

            whisper_text = f"وصلتك همسه جديده من\n{sender_name}"
            buttons = [
                [Button.inline("فتح الهمسه", data=f"wh_open_{whisper_id}")],
                [Button.inline("حذف الهمسه", data=f"wh_del_{whisper_id}")]
            ]
            await event.respond(whisper_text, buttons=buttons)
            db.log_activity(chat_id, chat_title, sender_id, sender_name, "WHISPER_SENT", f"إرسال همسة سرية إلى {target_arg}")
            return True

        # Case C: Standalone "همسة" without replying to any message
        if norm_text in ("همسه", "/whisper"):
            try:
                await event.delete()
            except Exception:
                pass
            hint = await event.respond(
                f"🤫 **يا [{sender_name}](tg://user?id={sender_id})، طريقة إرسال الهمسة السرية:**\n\n"
                f"1️⃣ **عبر الرد:** قم بالرد على رسالة العضو واكتب `همسة`، وسيظهر لك زر خاص لفتح المحادثة السرية.\n\n"
                f"2️⃣ **عبر المعرف:** اكتب مباشرة في الشات:\n"
                f"`همسة @username نص الهمسة هنا`"
            )
            asyncio.create_task(self._auto_delete_message(hint, 20))
            return True

        return False

    # =========================================================================
    # Interactive Bot Dictionary & Strict Owner Commands Engine
    # =========================================================================

    async def _handle_group_dictionary_and_commands(self, event, chat_id: int, chat_title: str, sender: User, sender_id: int, sender_name: str, raw_text: str, norm_text: str, group_cfg: Dict[str, Any]) -> bool:
        parts = norm_text.split()
        cmd = parts[0] if parts else ""

        # -------------------------------------------------------------
        # 1. OWNER-ONLY CONTROL COMMANDS (Normalized: أدمن/ادمن/مشرف)
        # -------------------------------------------------------------
        is_promote = any(norm_text == p or norm_text.startswith(p + " ") for p in ("رفع ادمن", "رفع مشرف", "ترقيه ادمن", "ترقيه مشرف"))
        is_demote = any(norm_text == d or norm_text.startswith(d + " ") for d in ("تنزيل ادمن", "تنزيل مشرف", "عزل ادمن", "عزل مشرف", "تجريد مشرف"))
        is_lock_chat = any(norm_text == l for l in ("قفل الدردشه", "قفل الشات", "/lock"))
        is_unlock_chat = any(norm_text == u for u in ("فتح الدردشه", "فتح الشات", "/unlock"))
        is_lock_links = norm_text in ("قفل الروابط", "منع الروابط")
        is_unlock_links = norm_text in ("فتح الروابط", "سماح الروابط")
        is_lock_fwd = norm_text in ("قفل التوجيه", "منع التوجيه")
        is_unlock_fwd = norm_text in ("فتح التوجيه", "سماح التوجيه")
        is_lock_photos = norm_text in ("قفل الصور", "منع الصور")
        is_unlock_photos = norm_text in ("فتح الصور", "سماح الصور")
        is_lock_stickers = norm_text in ("قفل الملصقات", "منع الملصقات")
        is_unlock_stickers = norm_text in ("فتح الملصقات", "سماح الملصقات")
        is_mute = any(norm_text == m or norm_text.startswith(m + " ") for m in ("كتم", "/mute"))
        is_unmute = any(norm_text == um or norm_text.startswith(um + " ") for um in ("الغاء الكتم", "فك الكتم", "/unmute"))
        is_kick = any(norm_text == k or norm_text.startswith(k + " ") for k in ("طرد", "/kick"))
        is_ban = any(norm_text == b or norm_text.startswith(b + " ") for b in ("حظر", "/ban"))
        is_unban = any(norm_text == ub or norm_text.startswith(ub + " ") for ub in ("الغاء الحظر", "فك الحظر", "/unban"))
        is_pin = any(norm_text == p or norm_text.startswith(p + " ") for p in ("تثبيت", "/pin"))
        is_clean = norm_text.startswith(("مسح ", "/clean ", "حذف "))
        is_settings = cmd in ("/settings", "الاعدادات", "اعدادات", "/setting")
        is_reload = cmd in ("/reload", "تحديث", "/refresh")

        is_owner_cmd = any([
            is_promote, is_demote, is_lock_chat, is_unlock_chat,
            is_lock_links, is_unlock_links, is_lock_fwd, is_unlock_fwd,
            is_lock_photos, is_unlock_photos, is_lock_stickers, is_unlock_stickers,
            is_mute, is_unmute, is_kick, is_ban, is_unban, is_pin,
            is_clean, is_settings, is_reload
        ])

        if is_owner_cmd:
            is_own = await self.is_owner(chat_id, sender_id)
            if not is_own:
                warn_msg = await event.reply("⚠️ لازم تكون المالك عشان تقدر تستخدم هذا الأمر 👑")
                asyncio.create_task(self._auto_delete_message(warn_msg, 12))
                return True

            # ---------------------------------------------------------
            # Owner Commands Execution:
            # ---------------------------------------------------------

            # A. Promote Admin (رفع أدمن / رفع مشرف)
            if is_promote and event.is_reply:
                reply_m = await event.get_reply_message()
                r_user = await reply_m.get_sender() if reply_m else None
                if r_user:
                    try:
                        admin_rights = ChatAdminRights(
                            change_info=True,
                            post_messages=True,
                            edit_messages=True,
                            delete_messages=True,
                            ban_users=True,
                            invite_users=True,
                            pin_messages=True,
                            add_admins=False,
                            anonymous=False,
                            manage_call=True
                        )
                        await self.client(EditAdminRequest(chat_id, r_user.id, admin_rights, rank="مشرف 🛡️"))
                        await event.reply(f"👑 تم رفع [{r_user.first_name}](tg://user?id={r_user.id}) مشرف في المجموعة بنجاح.")
                    except Exception as prom_err:
                        await event.reply("⚠️ تعذر رفع المشرف: تأكد من صلاحيات البوت.")
                return True

            # B. Demote Admin (تنزيل أدمن / تنزيل مشرف)
            if is_demote and event.is_reply:
                reply_m = await event.get_reply_message()
                r_user = await reply_m.get_sender() if reply_m else None
                if r_user:
                    try:
                        empty_rights = ChatAdminRights(
                            change_info=False,
                            post_messages=False,
                            edit_messages=False,
                            delete_messages=False,
                            ban_users=False,
                            invite_users=False,
                            pin_messages=False,
                            add_admins=False,
                            anonymous=False,
                            manage_call=False
                        )
                        await self.client(EditAdminRequest(chat_id, r_user.id, empty_rights, rank=""))
                        await event.reply(f"📉 تم تنزيل رتبة المشرف [{r_user.first_name}](tg://user?id={r_user.id}) بنجاح.")
                    except Exception:
                        await event.reply("⚠️ تعذر تنزيل المشرف.")
                return True

            # C. Settings in Private Chat
            if is_settings:
                pm_url = f"https://t.me/{self.me.username}?start=settings_{chat_id}"
                buttons = [[Button.url("📩 فتح لوحة التحكم في الخاص", pm_url)]]
                reply_msg = await event.reply(
                    f"⚙️ **إعدادات المجموعة ({chat_title}):**\n\n"
                    f"أهلاً بك يا مالك المجموعة 👑\nاضغط على الزر بالأسفل لفتح لوحة التحكم الكاملة في الخاص:",
                    buttons=buttons
                )
                asyncio.create_task(self._auto_delete_message(reply_msg, 30))
                return True

            # D. Reload Group & Cache Owner
            if is_reload:
                db.get_group(chat_id, chat_title)
                db.update_group_settings(chat_id, owner_id=sender_id)
                cache_key = f"owner:{chat_id}:{sender_id}"
                self.admin_cache[cache_key] = (True, time.time())

                reply_msg = await event.reply(
                    f"🔄 **تم تحديث بيانات المجموعة وتأكيد مالك المجموعة بنجاح!**\n\n"
                    f"• اسم المجموعة: **{chat_title}**\n"
                    f"• معرف المجموعة: `{chat_id}`\n"
                    f"• المالك: [{sender_name}](tg://user?id={sender_id}) 👑\n\n"
                    f"يمكنك الآن فتح الخاص وضبط الإعدادات: @{self.me.username}"
                )
                asyncio.create_task(self._auto_delete_message(reply_msg, 20))
                return True

            # E. Chat Lock / Unlock
            if is_lock_chat:
                db.update_group_settings(chat_id, chat_locked=1)
                await event.reply("🔒 **تم قفل الدردشة بنجاح من قبل المالك.**\nلن يتمكن الأعضاء من إرسال الرسائل حتى يتم الفتح.")
                return True

            if is_unlock_chat:
                db.update_group_settings(chat_id, chat_locked=0)
                await event.reply("🔓 **تم فتح الدردشة بنجاح من قبل المالك.**\nيمكن للجميع المشاركة الآن.")
                return True

            # F. Anti-Link Toggle
            if is_lock_links:
                db.update_group_settings(chat_id, anti_link=1)
                await event.reply("🚫 **تم تفعيل قفل الروابط والمعرفات بنجاح.**")
                return True

            if is_unlock_links:
                db.update_group_settings(chat_id, anti_link=0)
                await event.reply("✅ **تم السماح بالروابط في المجموعة.**")
                return True

            # G. Mute / Unmute
            if is_mute and event.is_reply:
                reply_m = await event.get_reply_message()
                r_sender = await reply_m.get_sender() if reply_m else None
                if r_sender:
                    try:
                        await self.client.edit_permissions(chat_id, r_sender.id, send_messages=False)
                        await event.reply(f"🤐 تم كتم العضو [{r_sender.first_name}](tg://user?id={r_sender.id}) بنجاح.")
                    except Exception:
                        await event.reply("⚠️ تعذر كتم العضو.")
                return True

            if is_unmute and event.is_reply:
                reply_m = await event.get_reply_message()
                r_sender = await reply_m.get_sender() if reply_m else None
                if r_sender:
                    try:
                        await self.client.edit_permissions(chat_id, r_sender.id, send_messages=True, send_media=True)
                        await event.reply(f"🗣️ تم إلغاء الكتم عن العضو [{r_sender.first_name}](tg://user?id={r_sender.id}) بنجاح.")
                    except Exception:
                        await event.reply("⚠️ تعذر إلغاء الكتم.")
                return True

            # H. Kick / Ban
            if is_kick and event.is_reply:
                reply_m = await event.get_reply_message()
                r_sender = await reply_m.get_sender() if reply_m else None
                if r_sender:
                    try:
                        await self.client.kick_participant(chat_id, r_sender.id)
                        await event.reply(f"👞 تم طرد العضو [{r_sender.first_name}](tg://user?id={r_sender.id}) من المجموعة.")
                    except Exception:
                        await event.reply("⚠️ تعذر طرد العضو.")
                return True

            if is_ban and event.is_reply:
                reply_m = await event.get_reply_message()
                r_sender = await reply_m.get_sender() if reply_m else None
                if r_sender:
                    try:
                        await self.client.edit_permissions(chat_id, r_sender.id, view_messages=False)
                        await event.reply(f"🚫 تم حظر العضو [{r_sender.first_name}](tg://user?id={r_sender.id}) بنجاح.")
                    except Exception:
                        await event.reply("⚠️ تعذر حظر العضو.")
                return True

            if is_unban and event.is_reply:
                reply_m = await event.get_reply_message()
                r_sender = await reply_m.get_sender() if reply_m else None
                if r_sender:
                    try:
                        await self.client.edit_permissions(chat_id, r_sender.id, view_messages=True, send_messages=True)
                        await event.reply(f"✅ تم فك الحظر عن العضو [{r_sender.first_name}](tg://user?id={r_sender.id}).")
                    except Exception:
                        await event.reply("⚠️ تعذر فك الحظر.")
                return True

            # I. Pin Message
            if is_pin and event.is_reply:
                reply_m = await event.get_reply_message()
                try:
                    await self.client.pin_message(chat_id, reply_m.id)
                    await event.reply("📌 تم تثبيت الرسالة بنجاح.")
                except Exception:
                    await event.reply("⚠️ تعذر التثبيت.")
                return True

            # J. Clean Messages
            if is_clean:
                num_str = parts[1] if len(parts) > 1 else "5"
                if num_str.isdigit():
                    count = min(int(num_str), 50)
                    try:
                        msgs_to_del = [event.id]
                        async for m in self.client.iter_messages(chat_id, limit=count):
                            msgs_to_del.append(m.id)
                        await self.client.delete_messages(chat_id, msgs_to_del)
                        conf = await event.respond(f"🗑️ تم مسح **{len(msgs_to_del)}** رسائل بنجاح.")
                        asyncio.create_task(self._auto_delete_message(conf, 5))
                        return True
                    except Exception as e:
                        logger.error(f"Clean error: {e}")

        # -------------------------------------------------------------
        # 2. GENERAL GROUP CHAT DICTIONARY & STUDENT COMMANDS
        # -------------------------------------------------------------

        # Profile / Identity Card ("انا مين", "مين انا", etc.)
        if any(norm_text == id_cmd for id_cmd in ("انا مين", "مين انا", "من انا", "معلوماتي", "بروفايلي", "رتبتي", "كشف حسابي", "ايدي", "id", "/id", "/me", "بطاقتي")):
            is_own = await self.is_owner(chat_id, sender_id)
            is_adm = await self.is_admin_or_owner(chat_id, sender_id)

            rank_title = "مالك المجموعة 👑" if is_own else ("مشرف المجموعة 🛡️" if is_adm else "طالب دحيح 🎓")
            invites = db.get_user_invites(chat_id, sender_id)
            req = group_cfg.get("required_adds", 1)
            u_info = db.get_or_create_user(chat_id, sender_id, sender_name)
            msg_count = u_info.get("message_count", 1)
            uname = f"@{sender.username}" if sender.username else "لا يوجد"
            status_txt = "✅ مسموح لك بالمشاركة والتحدث" if (invites >= req or is_adm) else f"⚠️ يلزمك إضافة {req - invites} أصدقاء"

            card = (
                f"👤 **بطاقة تعريف المستخدم:**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🏷️ **الاسم:** {sender_name}\n"
                f"🆔 **الايدي:** `{sender_id}`\n"
                f"🔖 **المعرف:** {uname}\n"
                f"🎖️ **الرتبة:** **{rank_title}**\n"
                f"👥 **رصيد الإضافات:** **{invites}** من أصل **{req}**\n"
                f"💬 **عدد الرسائل:** **{msg_count}** رسالة\n"
                f"🎓 **اللقب:** دفعة الثانوية العامة 2026 🎯\n"
                f"📌 **حالة التفاعل:** {status_txt}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✨ *مع تمنياتنا لك بأعلى الدرجات والتفوق!*"
            )
            await event.reply(card)
            db.log_activity(chat_id, chat_title, sender_id, sender_name, "DICT_REPLY", "عرض بطاقة انا مين")
            return True

        # Mood & Complaints ("زهقت", "قرفت", "انا قرفت", etc.)
        if any(norm_text.startswith(fr) or norm_text == fr for fr in (
            "زهقت", "قرفت", "انا قرفت", "تعبت", "مخنوق", "مش طايق المذاكره",
            "مش قادر", "فقدت الشغف", "حاسس بضغط", "مش فاهم حاجه", "عايز انام", "الامتحانات قربت"
        )):
            reply_fr = random.choice(FRUSTRATION_REPLIES)
            await event.reply(reply_fr)
            db.log_activity(chat_id, chat_title, sender_id, sender_name, "DICT_REPLY", "مواساة وتشجيع الطالب")
            return True

        # Jokes & Humor ("نكتة", "نكته", "ضحكني")
        if any(norm_text == jk or norm_text.startswith(jk + " ") for jk in ("نكته", "ضحكني", "روق عليا", "عايز اضحك", "فكها شويه", "افشات")):
            joke = random.choice(EGYPTIAN_JOKES)
            await event.reply(joke)
            db.log_activity(chat_id, chat_title, sender_id, sender_name, "DICT_REPLY", "إلقاء نكتة مصرية")
            return True

        # Motivation & Encouragement ("تحفيز", "شجعني")
        if any(norm_text == mot or norm_text.startswith(mot + " ") for mot in (
            "تحفيز", "حفزني", "شجعني", "اديني طاقه", "طاقه ايجابيه", "خايف من الامتحانات",
            "نفسي في طب", "نفسي في هندسه", "/motivation"
        )):
            quote = random.choice(MOTIVATIONAL_QUOTES)
            await event.reply(quote)
            db.log_activity(chat_id, chat_title, sender_id, sender_name, "DICT_REPLY", "إرسال تحفيز")
            return True

        # Calling the Bot ("بوت", "يا بوت", etc.)
        if any(norm_text == b_call for b_call in ("بوت", "يا بوت", "البوت", "bot", "يا دحيح", "دحيحه", "يا دحيحه", "يا عم البوت")):
            reply_quote = random.choice(BOT_REPLIES_EGYPTIAN)
            await event.reply(f"{reply_quote}")
            db.log_activity(chat_id, chat_title, sender_id, sender_name, "DICT_REPLY", "رد على بوت")
            return True

        # Affection & Compliments ("بحبك", "يا عسل", "تسلم", "شكرا")
        if any(norm_text.startswith(af) for af in ("بحبك", "يا عسل", "يا سكر", "حبيبي", "تسلم", "شكرا", "عاش", "جامد", "شاطر", "كفو")):
            sweets = [
                "حبيبي يا غالي تسلم، كلك ذوق ❤️",
                "العفو يا دحيح! في خدمتك دايماً وربنا يوفقك 🌹",
                "قلبي يا باشا، شد حيلك وفالك الامتياز بإذن الله ✨"
            ]
            await event.reply(random.choice(sweets))
            return True

        # Greetings
        if any(norm_text.startswith(g) for g in ("سلام عليكم", "السلام عليكم", "سلامو عليكم")):
            await event.reply("وعليكم السلام ورحمة الله وبركاته يا غالي! أهلاً بيك نورت الشات 🌺")
            return True

        if any(norm_text == m_greet for m_greet in ("صباح الخير", "صباح النور", "صباح الورد")):
            await event.reply("صباح الورد والنشاط والتوفيق في يومك ومذاكرتك يا بطل! ☀️📚")
            return True

        if any(norm_text == e_greet for e_greet in ("مساء الخير", "مساء النور", "مساء الورد")):
            await event.reply("مساء النور والسرور والسعادة، متنساش تراجع دروسك بتركيز الليلة 🌙✨")
            return True

        # Study Tips
        if any(norm_text == tp or norm_text.startswith(tp + " ") for tp in ("نصيحه", "نصائح", "/tip")):
            tip = random.choice(STUDY_TIPS)
            await event.reply(f"💡 **نصيحة اليوم للمذاكرة والتفوق:**\n\n{tip}")
            return True

        # Cairo Time
        if any(norm_text == tm for tm in ("الوقت", "الساعه", "/time")):
            cairo_tz = timezone(timedelta(hours=2))
            now_cairo = datetime.now(cairo_tz)
            time_str = now_cairo.strftime("%I:%M %p").replace("AM", "صباحاً").replace("PM", "مساءً")
            date_str = now_cairo.strftime("%Y-%m-%d")
            await event.reply(f"⏰ **التوقيت الآن في جمهورية مصر العربية (القاهرة):**\n\n🕐 الساعة: **{time_str}**\n📅 التاريخ: `{date_str}`")
            return True

        # Rules
        if any(norm_text == r_cmd for r_cmd in ("/rules", "القوانين", "قوانين")):
            cfg = db.get_group(chat_id, chat_title)
            rules = cfg.get("rules_text") or "📜 قوانين المجموعة:\n1. الاحترام المتبادل.\n2. ممنوع نشر الروابط والإعلانات.\n3. الالتزام بالهدف التعليمي."
            msg = await event.reply(rules)
            asyncio.create_task(self._auto_delete_message(msg, 30))
            return True

        # Invites Status
        if any(norm_text == inv for inv in ("/myinvites", "رصيدي", "اضافاتي", "/invites")):
            count = db.get_user_invites(chat_id, sender_id)
            req = group_cfg.get("required_adds", 1)
            status = "✅ مؤهل للتحدث بحرية" if count >= req else f"❌ متبقي لك {req - count} إضافات لتفعيل حسابك"
            name = sender.first_name or "صديقي"
            msg = await event.reply(
                f"📊 **رصيد إضافاتك يا {name}:**\n"
                f"👥 لقد قمت بإضافة: **{count}** أصدقاء.\n"
                f"🎯 المطلوب في المجموعة: **{req}** أصدقاء.\n"
                f"📌 الحالة: **{status}**"
            )
            asyncio.create_task(self._auto_delete_message(msg, 20))
            return True

        # Full Command List
        if any(norm_text == h_cmd for h_cmd in ("/help", "الاوامر", "اوامر", "مساعده", "help")):
            help_text = (
                f"📖 **قائمة أوامر بوت دحيحة ثانوي (@{self.me.username}):**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🌟 **أوامر الطلاب والأعضاء:**\n"
                f"• `انا مين` ┋ بطاقة بياناتك ورتبتك ورصيد إضافاتك\n"
                f"• `انا قرفت` / `زهقت` ┋ تشجيع ومواساة لضغط المذاكرة\n"
                f"• `نكتة` ┋ نكت ومواقف طريفة عن ثانوية عامة\n"
                f"• `تحفيز` ┋ اقتباس تشجيعي للمذاكرة والتفوق\n"
                f"• `نصيحة` ┋ نصائح تنظيم الوقت الفعالة\n"
                f"• `همسة` (بالرد) ┋ كتابة همسة سرية عبر الخاص وإرسالها\n"
                f"• `همسة @username النص` ┋ إرسال همسة مباشرة\n"
                f"• `بوت` ┋ الرد التفاعلي والترحيب\n"
                f"• `رصيدي` ┋ معرفة عدد إضافاتك ونظام الإضافة الإجبارية\n"
                f"• `سؤال` ┋ اختبار ثانوية عامة تفاعلي بابل شيت\n"
                f"• `الوقت` ┋ معرفة توقيت القاهرة الحالي\n"
                f"• `القوانين` ┋ عرض القوانين المعتمدة\n\n"
                f"👑 **أوامر مالك المجموعة فقط (مقفولة لغير المالك):**\n"
                f"• `رفع ادمن` / `تنزيل ادمن` (بالرد)\n"
                f"• `قفل الدردشة` / `فتح الدردشة`\n"
                f"• `قفل الروابط` / `فتح الروابط`\n"
                f"• `كتم` / `فك الكتم` (بالرد)\n"
                f"• `طرد` / `حظر` / `فك الحظر` (بالرد)\n"
                f"• `تثبيت` (بالرد)\n"
                f"• `مسح [عدد]` (مثال: `مسح 5`)\n"
                f"• `الاعدادات` ┋ فتح لوحة الخاص الكاملة\n"
                f"• `تحديث` ┋ تسجيل المجموعة وتأكيد المالك\n"
                f"━━━━━━━━━━━━━━━━━━"
            )
            await event.reply(help_text)
            return True

        # Educational Quiz
        if any(norm_text == q_cmd for q_cmd in ("/quiz", "سؤال", "كويز")):
            q = db.get_random_quiz()
            if q:
                quiz_card = (
                    f"📝 **سؤال ثانوية عامة ({q['subject']} - {q['chapter']}):**\n\n"
                    f"❓ **{q['question']}**\n\n"
                    f"1️⃣ {q['option_a']}\n"
                    f"2️⃣ {q['option_b']}\n"
                    f"3️⃣ {q['option_c']}\n"
                    f"4️⃣ {q['option_d']}\n\n"
                    f"💡 *الإجابة الصحيحة:* ||{q['correct_option']}||\n"
                    f"📌 *التفسير العلمي:* ||{q['explanation']}||"
                )
                await event.reply(quiz_card)
                return True

        return False

    async def _auto_delete_message(self, message, delay: int):
        try:
            await asyncio.sleep(delay)
            await message.delete()
        except Exception:
            pass


# -------------------------------------------------------------
# Lightweight Internal IPC Server (Port 5005)
# -------------------------------------------------------------
async def start_internal_api(engine: DahihaThanwiEngine):
    app = web.Application()

    async def handle_status(request):
        uptime = int(time.time() - engine.start_time)
        metrics = db.get_metrics()
        return web.json_response({
            "status": "online" if engine.is_running else "offline",
            "bot": {
                "id": engine.me.id if engine.me else 9170444919,
                "username": engine.me.username if engine.me else "Dahiha_Thanwi_bot",
                "first_name": engine.me.first_name if engine.me else "دحيحة ثانوي"
            },
            "token": f"{BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}",
            "uptime_seconds": uptime,
            "metrics": metrics
        })

    async def handle_groups(request):
        return web.json_response({"groups": db.get_all_groups()})

    async def handle_logs(request):
        limit = int(request.query.get("limit", 50))
        return web.json_response({"logs": db.get_recent_logs(limit)})

    app.router.add_get("/api/status", handle_status)
    app.router.add_get("/api/groups", handle_groups)
    app.router.add_get("/api/logs", handle_logs)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", INTERNAL_API_PORT)
    await site.start()
    logger.info(f"Internal Telemetry IPC Server listening on http://127.0.0.1:{INTERNAL_API_PORT}")


# -------------------------------------------------------------
# Main Asynchronous Runner
# -------------------------------------------------------------
async def main():
    logger.info("Initializing Dahiha Thanwi In-PM GroupHelp Suite...")
    engine = DahihaThanwiEngine()
    await engine.initialize()
    await start_internal_api(engine)
    logger.info("Telethon Engine Running 24/7. Listening for events...")
    await engine.client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Terminated by user.")
    except Exception as e:
        logger.critical(f"Fatal Engine Crash: {e}", exc_info=True)
