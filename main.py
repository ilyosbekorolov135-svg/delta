"""
Delta MMT Telegram Bot — Sodiqlik dasturi to'liq yangilangan
Python 3.13+ uchun

YANGILANISHLAR v2.0:
- Sodiqlik: FAQAT to'langan FOIZ summasidan ball (1000 so'm foiz = 1 ball)
- Kalkulyator: har bir variantda foiz summasi va shundan hisoblangan ball
- Darajalar rasmdagidek: Bronze → Silver → Gold → Platinum → VIP
- Sodiqlik amal qiladigan va qilmaydigan bo'limlar ajratildi
- Kredit olish shartlari (hujjatdan) qo'shildi
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    FSInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage


# ============================================================
# KONFIGURATSIYA
# ============================================================
BOT_TOKEN = "8919956688:AAHvTZ67aV3aB-oJChauXZSxY85R11XGR8Y"
ADMIN_ID = 969070334

COMPANY_NAME = "AJ «Delta Mikromoliya Tashkiloti»"
SLOGAN = "Hamma bilan birgalikda, har kim bilan shaxsan!"
REG_NUMBER = "00263201"
FOUNDED = 2009
ADDRESS = "Toshkent sh., Uchtepa tumani, Kichik halqa yo'li ko'chasi, 6a"
EMAIL = "info@mfodelta.uz"
WEBSITE = "mfodelta.uz"
WORK_HOURS = "09:00 - 18:00 (Dush-Juma)"

PHONE_1_DISPLAY = "+998 (55) 520-50-00"
PHONE_1_RAW = "+998555205000"
PHONE_2_DISPLAY = "+998 (55) 516-50-00"
PHONE_2_RAW = "+998555165000"

LOGO_PATH = "logo.png"

DATA_DIR = "data"
USERS_FILE = "data/users.json"
LOYALTY_FILE = "data/loyalty.json"


# ============================================================
# DATA MANAGER
# ============================================================
def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_json(filepath: str, default=None):
    if default is None:
        default = {}
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"load_json xato: {e}")
    return default


def save_json(filepath: str, data):
    try:
        ensure_data_dir()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"save_json xato: {e}")
        return False


def register_user(user_id: int, first_name: str, last_name: str = "", username: str = ""):
    users = load_json(USERS_FILE, {})
    str_id = str(user_id)
    is_new = str_id not in users

    if is_new:
        users[str_id] = {
            "id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "registered_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "visits": 1,
            "blocked": False,
            "referred_by": None,
            "ref_code": f"DELTA{user_id}",
        }
    else:
        users[str_id]["last_seen"] = datetime.now().isoformat()
        users[str_id]["first_name"] = first_name
        users[str_id]["last_name"] = last_name
        users[str_id]["username"] = username
        users[str_id]["visits"] = users[str_id].get("visits", 0) + 1

    save_json(USERS_FILE, users)
    return is_new


def get_all_users():
    return load_json(USERS_FILE, {})


def get_users_count():
    return len(get_all_users())


def get_today_users_count():
    users = load_json(USERS_FILE, {})
    today = datetime.now().date().isoformat()
    return sum(1 for u in users.values() if u.get("registered_at", "").startswith(today))


# ============================================================
# SODIQLIK DASTURI — FAQAT FOIZ SUMMASIDAN BALL
# ============================================================
def get_loyalty_data(user_id: int) -> dict:
    """Foydalanuvchining sodiqlik ma'lumotlarini olish"""
    loyalty = load_json(LOYALTY_FILE, {})
    str_id = str(user_id)
    if str_id not in loyalty:
        loyalty[str_id] = {
            "user_id": user_id,
            "points": 0,
            "total_interest_paid": 0,   # FAQAT to'langan foiz summasi
            "total_paid": 0,            # Umumiy to'lovlar (ma'lumot uchun)
            "invited_friends": [],
            "joined_at": datetime.now().isoformat(),
        }
        save_json(LOYALTY_FILE, loyalty)
    return loyalty[str_id]


def add_points(user_id: int, points: int, reason: str = ""):
    """Ball qo'shish (referal va bonus uchun)"""
    loyalty = load_json(LOYALTY_FILE, {})
    str_id = str(user_id)
    if str_id not in loyalty:
        loyalty[str_id] = {
            "user_id": user_id,
            "points": 0,
            "total_interest_paid": 0,
            "total_paid": 0,
            "invited_friends": [],
            "joined_at": datetime.now().isoformat(),
        }
    loyalty[str_id]["points"] = loyalty[str_id].get("points", 0) + points
    save_json(LOYALTY_FILE, loyalty)
    logger.info(f"Ball qo'shildi: {user_id} +{points} ({reason})")


def add_interest_payment(user_id: int, interest_amount: float):
    """
    FOIZ to'lovidan ball hisoblash.
    QOIDA: har 1000 so'm to'langan FOIZ summasi = 1 ball
    Misol: 2 500 000 so'm foiz to'langan = 2500 ball
    """
    points = int(interest_amount // 1000)
    
    loyalty = load_json(LOYALTY_FILE, {})
    str_id = str(user_id)
    if str_id not in loyalty:
        loyalty[str_id] = {
            "user_id": user_id,
            "points": 0,
            "total_interest_paid": 0,
            "total_paid": 0,
            "invited_friends": [],
            "joined_at": datetime.now().isoformat(),
        }
    
    loyalty[str_id]["points"] = loyalty[str_id].get("points", 0) + points
    loyalty[str_id]["total_interest_paid"] = loyalty[str_id].get("total_interest_paid", 0) + interest_amount
    loyalty[str_id]["total_paid"] = loyalty[str_id].get("total_paid", 0) + interest_amount
    save_json(LOYALTY_FILE, loyalty)
    
    logger.info(f"Foiz to'lovi: {user_id} - {interest_amount} so'm → {points} ball")
    return points


def get_loyalty_level(points: int) -> dict:
    """Ball miqdoriga qarab daraja aniqlash (rasmdagidek)"""
    if points >= 20000:
        return {
            "name": "VIP",
            "icon": "👑",
            "discount": "5%",
            "min_points": 20000,
            "bonus": "navbatsiz + shaxsiy maslahatchi",
            "color": "#8B0000"
        }
    elif points >= 15000:
        return {
            "name": "PLATINUM",
            "icon": "💎",
            "discount": "3%",
            "min_points": 15000,
            "bonus": "navbatsiz",
            "color": "#E5E4E2"
        }
    elif points >= 10000:
        return {
            "name": "GOLD",
            "icon": "🥇",
            "discount": "2%",
            "min_points": 10000,
            "bonus": "",
            "color": "#FFD700"
        }
    elif points >= 5000:
        return {
            "name": "SILVER",
            "icon": "🥈",
            "discount": "1%",
            "min_points": 5000,
            "bonus": "",
            "color": "#C0C0C0"
        }
    else:
        return {
            "name": "BRONZE",
            "icon": "🥉",
            "discount": "0%",
            "min_points": 0,
            "bonus": "",
            "color": "#CD7F32"
        }


def get_loyalty_text(user_id: int) -> str:
    """Foydalanuvchi sodiqlik ma'lumotlari matni"""
    data = get_loyalty_data(user_id)
    points = data.get("points", 0)
    level = get_loyalty_level(points)

    levels = [
        (5000, "SILVER", "🥈", "1%"),
        (10000, "GOLD", "🥇", "2%"),
        (15000, "PLATINUM", "💎", "3%"),
        (20000, "VIP", "👑", "5%"),
    ]
    
    next_info = ""
    for threshold, name, icon, disc in levels:
        if points < threshold:
            need = threshold - points
            next_info = (
                f"\n\n🎯 <b>Keyingi daraja:</b> {icon} <b>{name}</b>\n"
                f"   Kerak: <b>{need:,}</b> ball\n"
                f"   Chegirma: <b>{disc}</b>"
            )
            break
    else:
        next_info = "\n\n🏆 Siz eng yuqori darajaga erishdingiz!"

    text = (
        f"⭐ <b>MENING BALLARIM</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏅 <b>Darajangiz:</b> {level['icon']} <b>{level['name']}</b>\n"
        f"💰 <b>Chegirmangiz:</b> <b>{level['discount']}</b>\n"
        f"⭐ <b>Ballaringiz:</b> <b>{points:,}</b> ball\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>To'lov statistikasi:</b>\n"
        f"  • To'langan foiz: <b>{data.get('total_interest_paid', 0):,.0f}</b> so'm\n"
        f"  • Jami to'lov: <b>{data.get('total_paid', 0):,.0f}</b> so'm\n"
        f"  • Taklif qilgan do'stlar: <b>{len(data.get('invited_friends', []))}</b> ta"
        f"{next_info}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <b>Ballar qanday hisoblanadi?</b>\n\n"
        f"💰 <b>Foiz to'lovlaridan:</b>\n"
        f"   Har <b>1000 so'm foiz</b> to'lovi = <b>1 ball</b>\n"
        f"   <i>Misol: 2 500 000 so'm foiz = 2500 ball</i>\n\n"
        f"👥 <b>Do'st taklif qilishdan:</b>\n"
        f"   Har bir do'st = <b>1000 ball</b>"
    )
    return text


def get_loyalty_main_text() -> str:
    """Sodiqlik dasturi haqida umumiy ma'lumot (rasmdagidek)"""
    return (
        f"🎁 <b>SODIQLIK DASTURI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<i>«{SLOGAN}»</i>\n\n"
        f"Delta MMT sodiqlik dasturi bilan to'plangan "
        f"ballaringizdan foydalaning!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏅 <b>DARAJALAR</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🥉 <b>BRONZE</b> — DELTA MMT mijoziga aylaning\n"
        f"🥈 <b>SILVER</b> — 5 000 ball + yillik 1% chegirma\n"
        f"🥇 <b>GOLD</b> — 10 000 ball + yillik 2% chegirma\n"
        f"💎 <b>PLATINUM</b> — 15 000 ball + yillik 3% chegirma + navbatsiz\n"
        f"👑 <b>VIP</b> — 20 000 ball + yillik 5% chegirma + navbatsiz + shaxsiy maslahatchi\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>4 QADAM</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>1-QADAM:</b> DELTA MMTda kredit rasmiylashtiring\n"
        f"<b>2-QADAM:</b> Ballarga ega bo'ling va ularni yig'ing\n"
        f"<b>3-QADAM:</b> Do'stlaringiz, qo'shnilaringiz va "
        f"yaqin tanishlaringizni taklif qiling\n"
        f"<b>4-QADAM:</b> Yillik stavkalar uchun chegirmalarga ega bo'ling\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <b>BALLAR QANDAY HISOBLANADI?</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>1. Foiz to'lovlaridan:</b>\n"
        f"   Har <b>1000 so'm foiz to'lovi</b> = <b>1 ball</b>\n"
        f"   <i>Misol: 100 000 000 so'm kredit olib, 2 500 000 so'm "
        f"foiz to'lagan bo'lsangiz = 2500 ball</i>\n\n"
        f"👥 <b>2. Do'st taklif qilishdan:</b>\n"
        f"   Har bir taklif qilingan do'st = <b>1000 ball</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Muhim eslatma:</b> Ballar kreditning asosiy "
        f"summasidan emas, faqat <b>to'langan foiz summasidan</b> "
        f"hisoblanadi!"
    )


# ============================================================
# LOGGING & BOT
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)


# ============================================================
# FSM
# ============================================================
class States(StatesGroup):
    broadcast_text = State()
    calc_amount = State()


# ============================================================
# MAHSULOTLAR
# ============================================================
CATEGORIES = {
    "mikroqarzlar": {"name": "MIKROQARZLAR", "icon": "💰",
                     "products": ["hamkor", "madad", "fayz", "ishonch", "baraka", "sahovat", "nasiya_1", "komak", "umid"]},
    "mikrokreditlar": {"name": "MIKROKREDITLAR", "icon": "💼",
                       "products": ["kredit_liniyasi", "rivoj", "tezkor", "tadbirkor", "samara", "nasiya_2", "maqsad"]},
    "istemol": {"name": "ISTE'MOL KREDITI", "icon": "🛒",
                "products": ["avtokredit", "davr"]},
}

LOAN_PRODUCTS = {
    "hamkor": {
        "name": "HAMKOR", "category": "Mikroqarzlar", "icon": "🤝",
        "amount_range": "2 mln – 100 mln so'm",
        "amount_tiers": [
            {"range": "2-7.9 mln", "months": "13 oy", "rate": "65,9%"},
            {"range": "8-20 mln", "months": "19 oy", "rate": "59,9%"},
            {"range": "20.1-100 mln", "months": "37 oy", "rate": "54,9%"},
        ],
        "grace_period": "3 oygacha",
        "collateral": "Zargarlik buyumlari (100%)",
        "rate_numeric": 0.659,
        "min_amount": 2_000_000, "max_amount": 100_000_000, "max_months": 37,
        "loyalty": True,
    },
    "madad": {
        "name": "MADAD", "category": "Mikroqarzlar", "icon": "🆘",
        "amount_range": "2 mln – 25 mln so'm",
        "amount_tiers": [{"range": "2-25 mln", "months": "18 oy", "rate": "61,9%"}],
        "grace_period": "3 oygacha",
        "collateral": "Kafillik yoki garovsiz",
        "rate_numeric": 0.619,
        "min_amount": 2_000_000, "max_amount": 25_000_000, "max_months": 18,
        "loyalty": True,
    },
    "fayz": {
        "name": "FAYZ", "category": "Mikroqarzlar", "icon": "✨",
        "amount_range": "15 mln – 100 mln so'm",
        "amount_tiers": [{"range": "15-100 mln", "months": "36 oy", "rate": "41,9% / 53,9%"}],
        "grace_period": "3 oygacha",
        "collateral": "Avtomobil",
        "rate_numeric": 0.539,
        "min_amount": 15_000_000, "max_amount": 100_000_000, "max_months": 36,
        "loyalty": True,
    },
    "ishonch": {
        "name": "ISHONCH", "category": "Mikroqarzlar", "icon": "💎",
        "amount_range": "2 mln – 50 mln so'm",
        "amount_tiers": [{"range": "2-50 mln", "months": "25 oy", "rate": "59,9%"}],
        "grace_period": "3 oygacha",
        "collateral": "Garovsiz, sug'urta polisi",
        "rate_numeric": 0.599,
        "min_amount": 2_000_000, "max_amount": 50_000_000, "max_months": 25,
        "loyalty": True,
    },
    "baraka": {
        "name": "BARAKA", "category": "Mikroqarzlar", "icon": "🌟",
        "amount_range": "5 mln – 50 mln so'm",
        "amount_tiers": [{"range": "5-50 mln", "months": "25 oy", "rate": "55,9%"}],
        "grace_period": "3 oygacha",
        "collateral": "3 shaxs kafilligi",
        "rate_numeric": 0.559,
        "min_amount": 5_000_000, "max_amount": 50_000_000, "max_months": 25,
        "loyalty": True,
    },
    "sahovat": {
        "name": "SAHOVAT", "category": "Mikroqarzlar", "icon": "🎁",
        "amount_range": "2 mln so'm (yangi mijozlar)",
        "amount_tiers": [{"range": "2 mln", "months": "19 oy", "rate": "47,9%"}],
        "grace_period": "3 oygacha",
        "collateral": "3 shaxs kafilligi",
        "rate_numeric": 0.479,
        "min_amount": 2_000_000, "max_amount": 2_000_000, "max_months": 19,
        "loyalty": True,
    },
    "nasiya_1": {
        "name": "NASIYA-1", "category": "Mikroqarzlar", "icon": "🛍️",
        "amount_range": "1 mln – 10 mln so'm",
        "amount_tiers": [{"range": "1-10 mln", "months": "37 oy", "rate": "Shartnoma"}],
        "grace_period": "Yo'q",
        "collateral": "Avtomobil, zargarlik, ko'chmas mulk",
        "rate_numeric": 0.50,
        "min_amount": 1_000_000, "max_amount": 10_000_000, "max_months": 37,
        "loyalty": False,
    },
    "komak": {
        "name": "KO'MAK", "category": "Mikroqarzlar", "icon": "🤲",
        "amount_range": "1 mln – 15 mln so'm",
        "amount_tiers": [{"range": "1-15 mln", "months": "12 oy", "rate": "66,9%"}],
        "grace_period": "Yo'q",
        "collateral": "Garovsiz, sug'urta",
        "rate_numeric": 0.669,
        "min_amount": 1_000_000, "max_amount": 15_000_000, "max_months": 12,
        "loyalty": True,
    },
    "umid": {
        "name": "UMID", "category": "Mikroqarzlar", "icon": "🌈",
        "amount_range": "10 mln – 100 mln so'm",
        "amount_tiers": [{"range": "10-100 mln", "months": "6 oy", "rate": "62,9%"}],
        "grace_period": "5 oygacha",
        "collateral": "Zargarlik (90%)",
        "rate_numeric": 0.629,
        "min_amount": 10_000_000, "max_amount": 100_000_000, "max_months": 6,
        "loyalty": True,
    },
    "kredit_liniyasi": {
        "name": "KREDIT LINIYASI", "category": "Mikrokreditlar", "icon": "💳",
        "amount_range": "10 mln – 300 mln so'm",
        "amount_tiers": [{"range": "10-300 mln", "months": "49 oy", "rate": "54,9%"}],
        "grace_period": "—",
        "collateral": "Avtomobil, zargarlik, ko'chmas mulk",
        "rate_numeric": 0.549,
        "min_amount": 10_000_000, "max_amount": 300_000_000, "max_months": 49,
        "loyalty": True,
    },
    "rivoj": {
        "name": "RIVOJ", "category": "Mikrokreditlar", "icon": "📈",
        "amount_range": "10 mln – 300 mln so'm",
        "amount_tiers": [{"range": "10-300 mln", "months": "37 oy", "rate": "48%"}],
        "grace_period": "6 oygacha",
        "collateral": "Avtomobil, zargarlik, ko'chmas mulk",
        "rate_numeric": 0.48,
        "min_amount": 10_000_000, "max_amount": 300_000_000, "max_months": 37,
        "loyalty": True,
    },
    "tezkor": {
        "name": "TEZKOR", "category": "Mikrokreditlar", "icon": "⚡",
        "amount_range": "3 mln – 50 mln so'm",
        "amount_tiers": [{"range": "3-50 mln", "months": "25 oy", "rate": "59,9%"}],
        "grace_period": "3 oygacha",
        "collateral": "Garovsiz, sug'urta",
        "rate_numeric": 0.599,
        "min_amount": 3_000_000, "max_amount": 50_000_000, "max_months": 25,
        "loyalty": True,
    },
    "tadbirkor": {
        "name": "TADBIRKOR", "category": "Mikrokreditlar", "icon": "💼",
        "amount_range": "10 mln – 300 mln so'm",
        "amount_tiers": [
            {"range": "10-100 mln", "months": "37 oy", "rate": "44,9%"},
            {"range": "100-300 mln", "months": "37 oy", "rate": "52,9%"},
        ],
        "grace_period": "6 oygacha",
        "collateral": "Avtomobil, zargarlik, kafillik",
        "rate_numeric": 0.529,
        "min_amount": 10_000_000, "max_amount": 300_000_000, "max_months": 37,
        "loyalty": True,
    },
    "samara": {
        "name": "SAMARA", "category": "Mikrokreditlar", "icon": "🏆",
        "amount_range": "10 mln – 300 mln so'm",
        "amount_tiers": [
            {"range": "10-100 mln", "months": "49 oy", "rate": "44,9%"},
            {"range": "100-300 mln", "months": "49 oy", "rate": "52,9%"},
        ],
        "grace_period": "6 oygacha",
        "collateral": "Avtomobil, zargarlik, kafillik",
        "rate_numeric": 0.529,
        "min_amount": 10_000_000, "max_amount": 300_000_000, "max_months": 49,
        "loyalty": True,
    },
    "nasiya_2": {
        "name": "NASIYA-2", "category": "Mikrokreditlar", "icon": "🛒",
        "amount_range": "10 mln – 300 mln so'm",
        "amount_tiers": [{"range": "10-300 mln", "months": "37 oy", "rate": "Shartnoma"}],
        "grace_period": "Yo'q",
        "collateral": "Avtomobil, zargarlik, ko'chmas mulk",
        "rate_numeric": 0.50,
        "min_amount": 10_000_000, "max_amount": 300_000_000, "max_months": 37,
        "loyalty": False,
    },
    "maqsad": {
        "name": "MAQSAD", "category": "Mikrokreditlar", "icon": "🎯",
        "amount_range": "10 mln – 300 mln so'm",
        "amount_tiers": [
            {"range": "10-100 mln", "months": "60 oy", "rate": "24%"},
            {"range": "100-300 mln", "months": "60 oy", "rate": "48%"},
        ],
        "grace_period": "24 oygacha",
        "collateral": "Garovsiz / ko'chmas mulk",
        "rate_numeric": 0.48,
        "min_amount": 10_000_000, "max_amount": 300_000_000, "max_months": 60,
        "loyalty": True,
    },
    "avtokredit": {
        "name": "AVTOKREDIT", "category": "Iste'mol", "icon": "🚗",
        "amount_range": "300 mln so'mgacha",
        "amount_tiers": [{"range": "300 mln gacha", "months": "60 oy", "rate": "48%"}],
        "grace_period": "3 oygacha",
        "collateral": "Avtomobil",
        "rate_numeric": 0.48,
        "min_amount": 5_000_000, "max_amount": 300_000_000, "max_months": 60,
        "loyalty": True,
    },
    "davr": {
        "name": "DAVR", "category": "Iste'mol", "icon": "🕐",
        "amount_range": "25 mln so'mgacha",
        "amount_tiers": [{"range": "25 mln gacha", "months": "25 oy", "rate": "52%"}],
        "grace_period": "3 oygacha",
        "collateral": "Xarid qilinayotgan tovar",
        "rate_numeric": 0.52,
        "min_amount": 1_000_000, "max_amount": 25_000_000, "max_months": 25,
        "loyalty": True,
    },
}


BRANCHES = [
    {"id": "bosh_ofis", "name": "Bosh ofis", "region": "Toshkent shahri",
     "address": "Uchtepa tumani, Kichik Halqa Yo'li, 6A",
     "lat": 41.2995, "lng": 69.2401, "is_main": True},
    {"id": "yunusobod", "name": "Yunusobod", "region": "Toshkent shahri",
     "address": "13-mavze, 1a", "lat": 41.3566, "lng": 69.2878, "is_main": False},
    {"id": "aviasozlar", "name": "Aviasozlar", "region": "Toshkent shahri",
     "address": "Beshariq ko'chasi, 40", "lat": 41.2835, "lng": 69.3240, "is_main": False},
    {"id": "ttz", "name": "TTZ", "region": "Toshkent shahri",
     "address": "TTZ-2, 52/18", "lat": 41.3155, "lng": 69.3210, "is_main": False},
    {"id": "sirgali", "name": "Sirg'ali", "region": "Toshkent shahri",
     "address": "Sergeli-2, Yangi Sergeli, 52", "lat": 41.2135, "lng": 69.2245, "is_main": False},
    {"id": "chilonzor", "name": "Chilonzor", "region": "Toshkent shahri",
     "address": "Bunyodkor shoh ko'chasi, 12", "lat": 41.2760, "lng": 69.2040, "is_main": False},
    {"id": "yakkasaroy", "name": "Yakkasaroy", "region": "Toshkent shahri",
     "address": "Shota Rustaveli, 45", "lat": 41.2890, "lng": 69.2560, "is_main": False},
    {"id": "mirabad", "name": "Mirabad", "region": "Toshkent shahri",
     "address": "Mirabad tumani, Afrosiyob, 12", "lat": 41.2830, "lng": 69.2730, "is_main": False},
    {"id": "olmaliq", "name": "Olmaliq", "region": "Toshkent viloyati",
     "address": "Amir Temur, 29", "lat": 40.8447, "lng": 69.5983, "is_main": False},
    {"id": "boka", "name": "Bo'ka", "region": "Toshkent viloyati",
     "address": "Magistral, 562", "lat": 40.8100, "lng": 69.1900, "is_main": False},
    {"id": "angren", "name": "Angren", "region": "Toshkent viloyati",
     "address": "Bunyodkor, 5/2", "lat": 41.0167, "lng": 70.1436, "is_main": False},
    {"id": "chirchiq", "name": "Chirchiq", "region": "Toshkent viloyati",
     "address": "Navoiy prospekti", "lat": 41.4689, "lng": 69.5822, "is_main": False},
    {"id": "qoqon", "name": "Qo'qon", "region": "Farg'ona viloyati",
     "address": "Mustaqillik, 45", "lat": 40.5286, "lng": 70.9425, "is_main": False},
    {"id": "fargona", "name": "Farg'ona", "region": "Farg'ona viloyati",
     "address": "Ma'rifat, 22v", "lat": 40.3864, "lng": 71.7864, "is_main": False},
    {"id": "margilon", "name": "Marg'ilon", "region": "Farg'ona viloyati",
     "address": "Mustaqillik, 78", "lat": 40.4711, "lng": 71.7243, "is_main": False},
    {"id": "andijon", "name": "Andijon", "region": "Andijon viloyati",
     "address": "Milliy Tiklanish, 21", "lat": 40.7829, "lng": 72.3442, "is_main": False},
    {"id": "buxoro", "name": "Buxoro", "region": "Buxoro viloyati",
     "address": "Navoiy, ko'chasi", "lat": 39.7675, "lng": 64.4231, "is_main": False},
    {"id": "samarqand", "name": "Samarqand", "region": "Samarqand viloyati",
     "address": "Registon, 8", "lat": 39.6270, "lng": 66.9750, "is_main": False},
    {"id": "kattaqorgon", "name": "Kattaqo'rg'on", "region": "Samarqand viloyati",
     "address": "Amir Temur, 15", "lat": 39.8986, "lng": 66.2561, "is_main": False},
    {"id": "navoiy", "name": "Navoiy", "region": "Navoiy viloyati",
     "address": "O'zbekiston, 12", "lat": 40.0844, "lng": 65.3792, "is_main": False},
    {"id": "urganch", "name": "Urganch", "region": "Xorazm viloyati",
     "address": "Hakim Obidov", "lat": 41.5500, "lng": 60.6333, "is_main": False},
    {"id": "nukus", "name": "Nukus", "region": "Qoraqalpog'iston",
     "address": "A.Dosnazarov, 37/5", "lat": 42.4531, "lng": 59.6103, "is_main": False},
    {"id": "jizzax", "name": "Jizzax", "region": "Jizzax viloyati",
     "address": "Sharof Rashidov, 1/141", "lat": 40.1158, "lng": 67.8422, "is_main": False},
    {"id": "guliston", "name": "Guliston", "region": "Sirdaryo viloyati",
     "address": "Sayxun, 69", "lat": 40.4897, "lng": 68.7842, "is_main": False},
    {"id": "bekobod", "name": "Bekobod", "region": "Toshkent viloyati",
     "address": "Buyuk Ipak yo'li, 2/48", "lat": 40.2206, "lng": 69.2681, "is_main": False},
    {"id": "qarshi", "name": "Qarshi", "region": "Qashqadaryo viloyati",
     "address": "Mustaqillik, 35", "lat": 38.8606, "lng": 65.7887, "is_main": False},
    
]


# ============================================================
# YORDAMCHI
# ============================================================
def format_money(v: float) -> str:
    return f"{int(round(v)):,}".replace(",", " ")


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def calc_monthly(principal: float, months: int, annual_rate: float) -> float:
    if months <= 0:
        return 0
    mr = annual_rate / 12
    if mr == 0:
        return principal / months
    return principal * (mr * (1 + mr) ** months) / ((1 + mr) ** months - 1)


def calc_interest_total(principal: float, months: int, annual_rate: float) -> float:
    """
    Kredit bo'yicha jami to'lanadigan FOIZ summasi.
    Annuitet to'lovlarida: jami to'lov - asosiy qarz
    """
    monthly = calc_monthly(principal, months, annual_rate)
    total_payment = monthly * months
    return total_payment - principal


# ============================================================
# KLAVIATURALAR
# ============================================================
def main_menu_kb(is_adm: bool = False) -> ReplyKeyboardMarkup:
    """Asosiy menyu — Kalkulyator olib tashlandi, Sodiqlik qo'shildi"""
    rows = [
        [KeyboardButton(text="💼 Kreditlar"), KeyboardButton(text="🎁 Sodiqlik dasturi")],
        [KeyboardButton(text="📍 Filiallar"), KeyboardButton(text="📞 Aloqa")],
        [KeyboardButton(text="ℹ️ Kompaniya"), KeyboardButton(text="📋 Kredit shartlari")],
    ]
    if is_adm:
        rows.append([KeyboardButton(text="🎛️ Admin panel")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def call_center_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"📋 Nusxalash: {PHONE_1_DISPLAY}",
            copy_text={"text": PHONE_1_RAW}
        )],
        [InlineKeyboardButton(
            text=f"📋 Nusxalash: {PHONE_2_DISPLAY}",
            copy_text={"text": PHONE_2_RAW}
        )],
        [InlineKeyboardButton(text="🌐 Rasmiy sayt", url="https://mfodelta.uz")],
        [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="NAV_MAIN")]
    ])


def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Statistika", callback_data="ADMIN_STATS"),
            InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="ADMIN_USERS")
        ],
        [InlineKeyboardButton(text="🎁 Sodiqlik statistikasi", callback_data="ADMIN_LOYALTY")],
        [InlineKeyboardButton(text="📢 Broadcast", callback_data="ADMIN_BROADCAST")],
        [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="NAV_MAIN")]
    ])


def loyalty_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Mening ballarim", callback_data="LOYALTY_MY")],
        [InlineKeyboardButton(text="🏅 Darajalar", callback_data="LOYALTY_LEVELS")],
        [InlineKeyboardButton(text="👥 Do'stni taklif qilish", callback_data="LOYALTY_REF")],
        [InlineKeyboardButton(text="💼 Kreditlar", callback_data="NAV_CATS")],
        [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="NAV_MAIN")]
    ])


# ============================================================
# MATN
# ============================================================
def get_about_text() -> str:
    return (
        f"ℹ️ <b>{COMPANY_NAME}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<i>«{SLOGAN}»</i>\n\n"
        f"📋 <b>Ro'yxat raqami:</b> {REG_NUMBER}\n"
        f"📅 <b>Tashkil topgan:</b> {FOUNDED} yil\n"
        f"🏢 <b>Bosh ofis:</b>\n{ADDRESS}\n\n"
        f"🕐 <b>Ish vaqti:</b> {WORK_HOURS}\n\n"
        f"✉️ <b>Email:</b> {EMAIL}\n"
        f"🌐 <b>Sayt:</b> {WEBSITE}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>🏦 Bank rekvizitlari:</b>\n"
        f"  • H/r: <code>20216000904748133005</code>\n"
        f"  • MFO: <code>01033</code>\n"
        f"  • STIR: <code>301031980</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>📊 Ko'rsatkichlar:</b>\n"
        f"  • Bozorda: 15+ yil\n"
        f"  • Mijozlar: 150 000+\n"
        f"  • Filiallar: {len(BRANCHES)} ta\n"
        f"  • Mahsulotlar: 18 ta"
    )


def get_call_text() -> str:
    return (
        f"📞 <b>ALOQA</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>{COMPANY_NAME}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Telefon raqamlar:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📱 <b>{PHONE_1_DISPLAY}</b>\n"
        f"     <code>{PHONE_1_RAW}</code>\n\n"
        f"📱 <b>{PHONE_2_DISPLAY}</b>\n"
        f"     <code>{PHONE_2_RAW}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 <b>Ish vaqti:</b> {WORK_HOURS}\n\n"
        f"🏢 <b>Bosh ofis:</b>\n{ADDRESS}\n\n"
        f"✉️ <b>Email:</b> {EMAIL}\n"
        f"🌐 <b>Sayt:</b> {WEBSITE}\n\n"
        f"💡 <i>Raqamni bosib nusxalashingiz mumkin 👇</i>"
    )


def get_credit_terms_text() -> str:
    """Kredit olish shartlari (hujjatdan)"""
    return (
        f"📋 <b>KREDIT OLISH SHARTLARI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>👤 QARZ OLUVCHIGA QO'YILADIGAN TALABLAR:</b>\n\n"
        f"✅ Yoshi <b>25 yoshdan katta</b> bo'lgan O'zbekiston "
        f"Respublikasi fuqarolari\n"
        f"✅ O'zbekistonda yashash va faoliyat yuritish huquqiga ega "
        f"norezidentlar\n"
        f"✅ Tadbirkorlik sub'ektlari\n"
        f"⚠️ 25 yoshdan kichik bo'lsa — ota-onasining yozma roziligi kerak\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>❌ KREDIT BERISH TAQIQLANADI:</b>\n\n"
        f"• Yomon kredit tarixi bo'lsa\n"
        f"• To'lov qobiliyati yetarli bo'lmasa\n"
        f"• Daromad manbai aniqlanmasa\n"
        f"• Muddati o'tgan majburiyatlar bo'lsa\n"
        f"• 300 mln+ kredit uchun biznes-reja bo'lmasa\n"
        f"• Likvid garov ta'minoti bo'lmasa\n"
        f"• Qarz yuki yuqori bo'lsa\n"
        f"• Kredit uchinchi shaxslar uchun olinayotgan bo'lsa\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>🏠 GAROV TURLARI:</b>\n\n"
        f"♦️ Zargarlik buyumlari\n"
        f"♦️ Transport vositalari\n"
        f"♦️ Uchinchi shaxslarning kafilligi\n"
        f"♦️ Yangi mebel va maishiy texnika\n"
        f"♦️ Sug'urta polisi\n"
        f"♦️ Mahalla qo'mitasining kafilligi\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>💰 KREDIT BERISH USULLARI:</b>\n\n"
        f"• Kassa orqali naqd pul\n"
        f"• Bank hisob raqamiga o'tkazma\n"
        f"• Plastik kartaga o'tkazma\n"
        f"• Yetkazib beruvchi hisobiga (iste'mol krediti)\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>📅 FOIZ HISOBLASH:</b>\n\n"
        f"Foizlar kredit berilgan kundan boshlab hisoblanadi. "
        f"Yillik qarz summasining yarmidan ko'p foiz, komissiya "
        f"yoki jarima undirilishi taqiqlanadi.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>⚠️ KECHIKTIRILGAN TO'LOV UCHUN JARIMA:</b>\n\n"
        f"• 1-5 kun: kunlik <b>0,5%</b>\n"
        f"• 6-30 kun: kunlik <b>1,0%</b>\n"
        f"• 31-90 kun: kunlik <b>2,0%</b>\n"
        f"• 90+ kun: jarima hisoblash to'xtatiladi\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>👤 QARZ OLUVCHINING HUQUQLARI:</b>\n\n"
        f"✅ Kredit shartnomasini imzolashdan oldin o'qib chiqish\n"
        f"✅ Shartnomani o'zi bilan olib ketish\n"
        f"✅ To'lov shaklini o'zi tanlash\n"
        f"✅ Yashash joyidan qat'i nazar murojaat qilish\n"
        f"✅ Bepul ma'lumot olish (oyda 1 marta)\n"
        f"✅ Kreditni muddatidan oldin qaytarish\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>📄 KERAKLI HUJJATLAR:</b>\n\n"
        f"• Pasport va nusxasi\n"
        f"• Daromad to'g'risida ma'lumot\n"
        f"• Birgalikda qarz oluvchi pasporti (bo'lsa)\n"
        f"• Yuridik shaxslar uchun balans hisoboti\n"
        f"• Biznes-reja (tadbirkorlar uchun)\n"
        f"• Garov hujjatlari\n"
        f"• Kafil pasporti\n\n"
        f"💡 <i>Batafsil ma'lumot uchun Call-markazga murojaat qiling</i>"
    )


# ============================================================
# START
# ============================================================
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    is_new = register_user(
        user.id,
        user.first_name or "",
        user.last_name or "",
        user.username or ""
    )
    
    # Referal tekshirish
    if message.text and "ref" in message.text:
        try:
            ref_id = int(message.text.split("ref")[-1].split()[0])
            if ref_id != user.id:
                add_points(ref_id, 1000, "referral")
                
                try:
                    await bot.send_message(
                        ref_id,
                        f"🎉 <b>Do'stingiz qo'shildi!</b>\n\n"
                        f"👤 {user.first_name}\n"
                        f"⭐ +1000 ball sizning hisobingizga qo'shildi!",
                        parse_mode="HTML"
                    )
                except:
                    pass
                
                logger.info(f"Referal: {ref_id} +1000 ball ({user.id})")
        except:
            pass
    
    welcome = (
        f"👋 Assalomu alaykum, <b>{user.first_name}</b>!\n\n"
        f"<b>{COMPANY_NAME}</b> rasmiy botiga xush kelibsiz!\n\n"
        f"<i>«{SLOGAN}»</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💼 18 ta kredit mahsuloti\n"
        f"🎁 Sodiqlik dasturi (ballar tizimi)\n"
        f"📍 {len(BRANCHES)} ta filial\n"
        f"📋 Kredit olish shartlari\n"
        f"📞 Aloqa ma'lumotlari\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 Kerakli bo'limni tanlang:"
    )
    
    if is_new and is_admin(user.id):
        welcome += "\n\n🎛️ <b>Siz adminsiz!</b>"
    
    logo_file = Path(LOGO_PATH)
    if logo_file.exists():
        try:
            await message.answer_photo(
                photo=FSInputFile(LOGO_PATH),
                caption=welcome,
                reply_markup=main_menu_kb(is_admin(user.id)),
                parse_mode="HTML"
            )
            return
        except Exception as e:
            logger.error(f"Logo xato: {e}")
    
    await message.answer(
        welcome,
        reply_markup=main_menu_kb(is_admin(user.id)),
        parse_mode="HTML"
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Siz admin emassiz!")
        return
    
    await message.answer(
        f"🎛️ <b>Admin Panel</b>\n\nBo'limni tanlang:",
        reply_markup=admin_main_kb(),
        parse_mode="HTML"
    )


# ============================================================
# REPLY MENU
# ============================================================
@router.message(F.text == "💼 Kreditlar")
async def menu_credits(message: Message, state: FSMContext):
    await state.clear()
    buttons = []
    for cid, cat in CATEGORIES.items():
        buttons.append([InlineKeyboardButton(
            text=f"{cat['icon']} {cat['name']} ({len(cat['products'])})",
            callback_data=f"CAT_{cid}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="NAV_MAIN")])
    await message.answer(
        "💼 <b>Kredit mahsulotlari</b>\n\nKategoriyani tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )


@router.message(F.text == "🎁 Sodiqlik dasturi")
async def menu_loyalty(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    get_loyalty_data(user_id)
    
    await message.answer(
        get_loyalty_main_text(),
        reply_markup=loyalty_menu_kb(),
        parse_mode="HTML"
    )


@router.message(F.text == "📍 Filiallar")
async def menu_branches(message: Message, state: FSMContext):
    await state.clear()
    regions = {}
    for b in BRANCHES:
        regions[b["region"]] = regions.get(b["region"], 0) + 1
    
    buttons = []
    for region, count in sorted(regions.items()):
        buttons.append([InlineKeyboardButton(
            text=f"📍 {region} ({count})",
            callback_data=f"REG_{region}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="NAV_MAIN")])
    await message.answer(
        f"📍 <b>Filiallar</b>\n\nJami {len(BRANCHES)} ta:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )


@router.message(F.text == "📞 Aloqa")
async def menu_call(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(get_call_text(), reply_markup=call_center_kb(), parse_mode="HTML")


@router.message(F.text == "ℹ️ Kompaniya")
async def menu_about(message: Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Aloqa", callback_data="NAV_CALL")],
        [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="NAV_MAIN")]
    ])
    await message.answer(get_about_text(), reply_markup=kb, parse_mode="HTML")


@router.message(F.text == "📋 Kredit shartlari")
async def menu_credit_terms(message: Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💼 Kreditlar", callback_data="NAV_CATS")],
        [InlineKeyboardButton(text="📞 Aloqa", callback_data="NAV_CALL")],
        [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="NAV_MAIN")]
    ])
    await message.answer(get_credit_terms_text(), reply_markup=kb, parse_mode="HTML")


@router.message(F.text == "🎛️ Admin panel")
async def menu_admin(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        await message.answer("❌ Siz admin emassiz!")
        return
    await message.answer(
        "🎛️ <b>Admin Panel</b>\n\nBo'limni tanlang:",
        reply_markup=admin_main_kb(),
        parse_mode="HTML"
    )


# ============================================================
# CALLBACK: CATEGORIES
# ============================================================
@router.callback_query(F.data.startswith("CAT_"))
async def cb_cat(call: CallbackQuery):
    cid = call.data[4:]
    if cid not in CATEGORIES:
        await call.answer("❌", show_alert=True)
        return
    
    cat = CATEGORIES[cid]
    buttons = []
    for pid in cat["products"]:
        p = LOAN_PRODUCTS[pid]
        loyalty_mark = "🎁" if p.get("loyalty") else ""
        buttons.append([InlineKeyboardButton(
            text=f"{p['icon']} {p['name']} {loyalty_mark}",
            callback_data=f"PROD_{pid}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="NAV_CATS")])
    
    await call.message.edit_text(
        f"{cat['icon']} <b>{cat['name']}</b>\n\nMahsulotni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("PROD_"))
async def cb_prod(call: CallbackQuery):
    pid = call.data[5:]
    if pid not in LOAN_PRODUCTS:
        await call.answer("❌", show_alert=True)
        return
    
    p = LOAN_PRODUCTS[pid]
    text = f"{p['icon']} <b>{p['name']}</b>\n<i>{p['category']}</i>\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"💰 <b>Summa:</b> {p['amount_range']}\n\n"
    if p.get("amount_tiers"):
        text += "<b>📊 Shartlar:</b>\n"
        for t in p["amount_tiers"]:
            text += f"  • {t['range']} → {t['months']}, <b>{t['rate']}</b>\n"
        text += "\n"
    text += f"🎁 <b>Imtiyozli:</b> {p['grace_period']}\n"
    text += f"🏠 <b>Garov:</b> {p['collateral']}\n"
    
    # Sodiqlik dasturi haqida
    if p.get("loyalty"):
        text += (
            f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎁 <b>SODIQLIK DASTURI AMAL QILADI</b>\n"
            f"   Har <b>1000 so'm to'langan foiz</b> = <b>1 ball</b>\n"
            f"   <i>Asosiy qarzdan emas, faqat foiz summasidan</i>\n"
            f"   Misol: 100 mln kredit, 36 oy, foiz ~50 mln\n"
            f"   → ~50 000 ball to'playsiz!\n"
        )
    else:
        text += (
            f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <b>SODIQLIK DASTURI AMAL QILMAYDI</b>\n"
            f"   Bu mahsulot bo'yicha ballar hisoblanmaydi\n"
            f"   <i>(Shartnoma asosida)</i>\n"
        )
    
    cat_id = None
    for cid, c in CATEGORIES.items():
        if pid in c["products"]:
            cat_id = cid
            break
    
    kb_buttons = [[InlineKeyboardButton(text="🧮 Kalkulyator", callback_data=f"CALC_{pid}")]]
    if p.get("loyalty"):
        kb_buttons.append([InlineKeyboardButton(text="🎁 Sodiqlik dasturi", callback_data="NAV_LOYALTY")])
    kb_buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"CAT_{cat_id}")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


# ============================================================
# SODIQLIK CALLBACK
# ============================================================
@router.callback_query(F.data == "NAV_LOYALTY")
async def cb_nav_loyalty(call: CallbackQuery):
    user_id = call.from_user.id
    get_loyalty_data(user_id)
    try:
        await call.message.edit_text(
            get_loyalty_main_text(),
            reply_markup=loyalty_menu_kb(),
            parse_mode="HTML"
        )
    except:
        await call.message.answer(
            get_loyalty_main_text(),
            reply_markup=loyalty_menu_kb(),
            parse_mode="HTML"
        )
    await call.answer()


@router.callback_query(F.data == "LOYALTY_MY")
async def cb_loyalty_my(call: CallbackQuery):
    user_id = call.from_user.id
    text = get_loyalty_text(user_id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="LOYALTY_MY")],
        [InlineKeyboardButton(text="🔙 Sodiqlik", callback_data="NAV_LOYALTY")]
    ])
    
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except:
        await call.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "LOYALTY_REF")
async def cb_loyalty_ref(call: CallbackQuery):
    user_id = call.from_user.id
    data = get_loyalty_data(user_id)
    bot_username = "Delta_MMT_bot"
    
    text = (
        f"👥 <b>DO'STNI TAKLIF QILISH</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎁 Har bir taklif qilingan do'st uchun\n"
        f"siz <b>1000 ball</b> olasiz!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📤 <b>Sizning havolangiz:</b>\n\n"
        f"<code>https://t.me/{bot_username}?start=ref{user_id}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Statistika:</b>\n"
        f"  • Taklif qilganlar: <b>{len(data.get('invited_friends', []))}</b> ta\n"
        f"  • Ballaringiz: <b>{data.get('points', 0):,}</b> ball\n\n"
        f"💡 <i>Havolani nusxalab do'stlaringizga yuboring!</i>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📋 Havolani nusxalash",
            copy_text={"text": f"https://t.me/{bot_username}?start=ref{user_id}"}
        )],
        [InlineKeyboardButton(text="🔙 Sodiqlik", callback_data="NAV_LOYALTY")]
    ])
    
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except:
        await call.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "LOYALTY_LEVELS")
async def cb_loyalty_levels(call: CallbackQuery):
    text = (
        f"🏅 <b>DARAJALAR VA CHEGIRMALAR</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🥉 <b>BRONZE</b> — DELTA MMT mijoziga aylaning\n"
        f"   Chegirma: 0%\n\n"
        f"🥈 <b>SILVER</b>\n"
        f"   Ball: 5 000+ | Chegirma: 1% (yillik)\n\n"
        f"🥇 <b>GOLD</b>\n"
        f"   Ball: 10 000+ | Chegirma: 2% (yillik)\n\n"
        f"💎 <b>PLATINUM</b>\n"
        f"   Ball: 15 000+ | Chegirma: 3% (yillik)\n"
        f"   + navbatsiz xizmat\n\n"
        f"👑 <b>VIP</b>\n"
        f"   Ball: 20 000+ | Chegirma: 5% (yillik)\n"
        f"   + navbatsiz xizmat\n"
        f"   + shaxsiy maslahatchi\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <b>QANDAY BALL TO'PLASH MUMKIN?</b>\n\n"
        f"💰 <b>Foiz to'lovlaridan:</b>\n"
        f"   Har 1000 so'm foiz = 1 ball\n"
        f"   <i>Misol: 2 500 000 so'm foiz = 2500 ball</i>\n\n"
        f"👥 <b>Do'st taklif qilishdan:</b>\n"
        f"   Har bir do'st = 1000 ball\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Muhim:</b> Ballar faqat <b>to'langan foiz "
        f"summasidan</b> hisoblanadi, asosiy qarzdan emas!"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Sodiqlik", callback_data="NAV_LOYALTY")]
    ])
    
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except:
        await call.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


# ============================================================
# KALKULYATOR (YANGILANGAN — FOIZ + BALL)
# ============================================================
@router.callback_query(F.data.startswith("CALC_"))
async def cb_calc(call: CallbackQuery, state: FSMContext):
    pid = call.data[5:]
    if pid not in LOAN_PRODUCTS:
        await call.answer("❌", show_alert=True)
        return
    
    p = LOAN_PRODUCTS[pid]
    await state.update_data(calc_pid=pid)
    await state.set_state(States.calc_amount)
    
    await call.message.edit_text(
        f"🧮 <b>{p['name']} kalkulyatori</b>\n\n"
        f"💰 Summa: {p['amount_range']}\n\n"
        f"📝 Summani kiriting:\n"
        f"<i>Masalan: 10000000</i>",
        parse_mode="HTML"
    )
    await call.answer()


@router.message(States.calc_amount)
async def process_calc(message: Message, state: FSMContext):
    data = await state.get_data()
    pid = data.get("calc_pid")
    
    if not pid or pid not in LOAN_PRODUCTS:
        await state.clear()
        return
    
    digits = "".join(c for c in message.text if c.isdigit())
    if not digits:
        await message.answer("⚠️ Faqat raqam!")
        return
    
    amount = int(digits)
    p = LOAN_PRODUCTS[pid]
    
    if amount < p["min_amount"]:
        await message.answer(f"⚠️ Min: {format_money(p['min_amount'])}")
        return
    if amount > p["max_amount"]:
        await message.answer(f"⚠️ Maks: {format_money(p['max_amount'])}")
        return
    
    rate = p["rate_numeric"]
    months_opts = [m for m in [3, 6, 12, 18, 24, 36, 49, 60] if m <= p["max_months"]]
    
    text = f"💰 <b>{format_money(amount)} so'm</b>\n\n📅 <b>Variantlar:</b>\n\n"
    
    for m in months_opts:
        monthly = calc_monthly(amount, m, rate)
        total_payment = monthly * m
        interest = total_payment - amount  # FAQAT FOIZ
        points = int(interest // 1000) if p.get("loyalty") else 0
        
        text += f"  • <b>{m} oy</b> — {format_money(monthly)} so'm/oy\n"
        text += f"    Jami: {format_money(total_payment)} so'm\n"
        text += f"    📈 <b>Foiz:</b> {format_money(interest)} so'm\n"
        if p.get("loyalty"):
            text += f"    ⭐ <b>Ball:</b> {points:,} ball\n\n"
        else:
            text += f"    ⚠️ Sodiqlik: <i>hisoblanmaydi</i>\n\n"
    
    if p.get("loyalty"):
        text += (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎁 <b>Sodiqlik dasturi:</b>\n"
            f"Ballar <b>faqat to'langan foiz summasidan</b> hisoblanadi:\n"
            f"Har <b>1000 so'm foiz = 1 ball</b>\n\n"
            f"💡 {PHONE_1_DISPLAY}"
        )
    else:
        text += (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <b>Bu mahsulotda sodiqlik dasturi amal qilmaydi</b>\n\n"
            f"💡 {PHONE_1_DISPLAY}"
        )
    
    await state.clear()
    await message.answer(text, reply_markup=call_center_kb(), parse_mode="HTML")


# ============================================================
# FILIALLAR
# ============================================================
@router.callback_query(F.data.startswith("REG_"))
async def cb_region(call: CallbackQuery):
    region = call.data[4:]
    rb = [b for b in BRANCHES if b["region"] == region]
    
    buttons = []
    for b in rb:
        icon = "🏢" if b["is_main"] else "📍"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {b['name']}",
            callback_data=f"BR_{b['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="NAV_BRANCHES")])
    
    await call.message.edit_text(
        f"📍 <b>{region}</b> ({len(rb)}):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("BR_"))
async def cb_branch(call: CallbackQuery):
    bid = call.data[3:]
    b = next((x for x in BRANCHES if x["id"] == bid), None)
    if not b:
        await call.answer("❌", show_alert=True)
        return
    
    text = (
        f"🏢 <b>{b['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📍 {b['region']}\n"
        f"🏠 {b['address']}\n\n"
        f"🕐 09:00 – 18:00\n"
        f"📅 Dushanba – Juma"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗺️ Yandex", url=f"https://yandex.uz/maps/?pt={b['lng']},{b['lat']}&z=17&l=map")],
        [InlineKeyboardButton(text="🗺️ Google", url=f"https://www.google.com/maps/search/?api=1&query={b['lat']},{b['lng']}")],
        [InlineKeyboardButton(text="📞 Aloqa", callback_data="NAV_CALL")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"REG_{b['region']}")]
    ])
    
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except:
        await call.message.answer(text, reply_markup=kb, parse_mode="HTML")
    
    try:
        await call.message.answer_location(latitude=b["lat"], longitude=b["lng"])
    except:
        pass
    
    await call.answer()


# ============================================================
# NAVIGATSIYA
# ============================================================
@router.callback_query(F.data == "NAV_MAIN")
async def cb_nav_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer(
        "🏠 <b>Asosiy menyu</b>",
        reply_markup=main_menu_kb(is_admin(call.from_user.id)),
        parse_mode="HTML"
    )
    try:
        await call.message.delete()
    except:
        pass
    await call.answer()


@router.callback_query(F.data == "NAV_CATS")
async def cb_nav_cats(call: CallbackQuery):
    buttons = []
    for cid, cat in CATEGORIES.items():
        buttons.append([InlineKeyboardButton(
            text=f"{cat['icon']} {cat['name']} ({len(cat['products'])})",
            callback_data=f"CAT_{cid}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Asosiy", callback_data="NAV_MAIN")])
    await call.message.edit_text(
        "💼 <b>Kategoriyalar</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "NAV_BRANCHES")
async def cb_nav_branches(call: CallbackQuery):
    regions = {}
    for b in BRANCHES:
        regions[b["region"]] = regions.get(b["region"], 0) + 1
    
    buttons = []
    for region, count in sorted(regions.items()):
        buttons.append([InlineKeyboardButton(
            text=f"📍 {region} ({count})",
            callback_data=f"REG_{region}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Asosiy", callback_data="NAV_MAIN")])
    await call.message.edit_text(
        f"📍 <b>Filiallar</b>\n\n{len(BRANCHES)} ta:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "NAV_CALL")
async def cb_nav_call(call: CallbackQuery):
    try:
        await call.message.edit_text(
            get_call_text(),
            reply_markup=call_center_kb(),
            parse_mode="HTML"
        )
    except:
        await call.message.answer(
            get_call_text(),
            reply_markup=call_center_kb(),
            parse_mode="HTML"
        )
    await call.answer("✅ Raqamlar yuborildi!")


# ============================================================
# ADMIN PANEL
# ============================================================
@router.callback_query(F.data == "ADMIN_PANEL")
async def cb_admin_panel(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌", show_alert=True)
        return
    await call.message.edit_text(
        "🎛️ <b>Admin Panel</b>",
        reply_markup=admin_main_kb(),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "ADMIN_STATS")
async def cb_admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    
    loyalty = load_json(LOYALTY_FILE, {})
    total_points = sum(d.get("points", 0) for d in loyalty.values())
    
    text = (
        f"📊 <b>Statistika</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Foydalanuvchilar:</b>\n"
        f"  • Jami: <b>{get_users_count()}</b>\n"
        f"  • Bugun: <b>{get_today_users_count()}</b>\n\n"
        f"🎁 <b>Sodiqlik dasturi:</b>\n"
        f"  • Ishtirokchilar: <b>{len(loyalty)}</b>\n"
        f"  • Jami ballar: <b>{total_points:,}</b>\n\n"
        f"📞 <b>Call-markaz:</b>\n"
        f"  • {PHONE_1_DISPLAY}\n"
        f"  • {PHONE_2_DISPLAY}"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="ADMIN_STATS")],
        [InlineKeyboardButton(text="🔙 Admin panel", callback_data="ADMIN_PANEL")]
    ])
    
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer("📊")


@router.callback_query(F.data == "ADMIN_USERS")
async def cb_admin_users(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    
    users = get_all_users()
    text = f"👥 <b>Foydalanuvchilar</b> ({len(users)})\n\n"
    
    sorted_users = sorted(users.values(), key=lambda x: x.get("last_seen", ""), reverse=True)
    
    for i, u in enumerate(sorted_users[:15], 1):
        name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or "Noma'lum"
        username = f"@{u['username']}" if u.get("username") else "—"
        text += f"{i}. <b>{name}</b>\n"
        text += f"   🆔 <code>{u['id']}</code> | {username}\n"
        text += f"   👁 {u.get('visits', 0)}\n\n"
    
    if len(sorted_users) > 15:
        text += f"<i>... yana {len(sorted_users) - 15} ta</i>"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin panel", callback_data="ADMIN_PANEL")]
    ])
    
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "ADMIN_LOYALTY")
async def cb_admin_loyalty(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    
    loyalty = load_json(LOYALTY_FILE, {})
    total_users = len(loyalty)
    total_points = sum(d.get("points", 0) for d in loyalty.values())
    total_interest = sum(d.get("total_interest_paid", 0) for d in loyalty.values())
    
    text = (
        f"🎁 <b>Sodiqlik statistikasi</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Ishtirokchilar:</b> {total_users} ta\n"
        f"⭐ <b>Jami ballar:</b> {total_points:,}\n"
        f"💰 <b>Jami foiz to'lovlari:</b> {total_interest:,.0f} so'm\n\n"
        f"🏆 <b>TOP-10 mijozlar:</b>\n"
    )
    
    sorted_loyalty = sorted(loyalty.values(), key=lambda x: x.get("points", 0), reverse=True)
    
    for i, d in enumerate(sorted_loyalty[:10], 1):
        level = get_loyalty_level(d.get("points", 0))
        text += f"{i}. 🆔 <code>{d['user_id']}</code> — {d.get('points', 0):,} ball {level['icon']}\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="ADMIN_LOYALTY")],
        [InlineKeyboardButton(text="🔙 Admin panel", callback_data="ADMIN_PANEL")]
    ])
    
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "ADMIN_BROADCAST")
async def cb_admin_broadcast(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    
    await state.set_state(States.broadcast_text)
    await call.message.edit_text(
        f"📢 <b>Broadcast</b>\n\n"
        f"👥 {get_users_count()} foydalanuvchiga yuboriladi.\n\n"
        f"📝 Xabar matnini kiriting:",
        parse_mode="HTML"
    )
    await call.answer()


@router.message(States.broadcast_text)
async def process_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    text = message.text
    users = get_all_users()
    
    status_msg = await message.answer(f"📤 Yuborilmoqda... 0/{len(users)}")
    
    success = 0
    failed = 0
    
    for i, u in enumerate(users.values(), 1):
        try:
            await bot.send_message(
                u["id"],
                f"📢 <b>Delta MMT</b>\n\n{text}",
                parse_mode="HTML"
            )
            success += 1
        except:
            failed += 1
        
        if i % 10 == 0:
            try:
                await status_msg.edit_text(f"📤 {i}/{len(users)}")
            except:
                pass
        
        await asyncio.sleep(0.05)
    
    await status_msg.edit_text(
        f"✅ <b>Yuborildi!</b>\n\n✅ {success}\n❌ {failed}",
        parse_mode="HTML"
    )


# ============================================================
# FALLBACK
# ============================================================
@router.message()
async def fallback(message: Message, state: FSMContext):
    cur = await state.get_state()
    if cur:
        return
    await message.answer(
        "🤔 Tushunmadim. Menyudan foydalaning 👇",
        reply_markup=main_menu_kb(is_admin(message.from_user.id))
    )


# ============================================================
# MAIN
# ============================================================
async def main():
    logger.info("🚀 Delta MMT bot ishga tushmoqda...")
    logger.info(f"👤 Admin: {ADMIN_ID}")
    ensure_data_dir()
    
    if Path(LOGO_PATH).exists():
        logger.info(f"✅ Logo: {LOGO_PATH}")
    else:
        logger.warning(f"⚠️ Logo topilmadi: {LOGO_PATH}")
    
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Tayyor!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⛔ To'xtatildi")
    except Exception as e:
        logger.error(f"❌ {e}")
