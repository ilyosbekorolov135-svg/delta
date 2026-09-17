"""
Delta MMT Telegram Bot — Ariza qoldirish olib tashlangan
Python 3.13+ uchun
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

import os
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")

DATA_DIR = "/tmp/data"
USERS_FILE = "/tmp/data/users.json"


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
            "blocked": False
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
    },
    "madad": {
        "name": "MADAD", "category": "Mikroqarzlar", "icon": "🆘",
        "amount_range": "2 mln – 25 mln so'm",
        "amount_tiers": [{"range": "2-25 mln", "months": "18 oy", "rate": "61,9%"}],
        "grace_period": "3 oygacha",
        "collateral": "Kafillik yoki garovsiz",
        "rate_numeric": 0.619,
        "min_amount": 2_000_000, "max_amount": 25_000_000, "max_months": 18,
    },
    "fayz": {
        "name": "FAYZ", "category": "Mikroqarzlar", "icon": "✨",
        "amount_range": "15 mln – 100 mln so'm",
        "amount_tiers": [{"range": "15-100 mln", "months": "36 oy", "rate": "41,9% / 53,9%"}],
        "grace_period": "3 oygacha",
        "collateral": "Avtomobil",
        "rate_numeric": 0.539,
        "min_amount": 15_000_000, "max_amount": 100_000_000, "max_months": 36,
    },
    "ishonch": {
        "name": "ISHONCH", "category": "Mikroqarzlar", "icon": "💎",
        "amount_range": "2 mln – 50 mln so'm",
        "amount_tiers": [{"range": "2-50 mln", "months": "25 oy", "rate": "59,9%"}],
        "grace_period": "3 oygacha",
        "collateral": "Garovsiz, sug'urta polisi",
        "rate_numeric": 0.599,
        "min_amount": 2_000_000, "max_amount": 50_000_000, "max_months": 25,
    },
    "baraka": {
        "name": "BARAKA", "category": "Mikroqarzlar", "icon": "🌟",
        "amount_range": "5 mln – 50 mln so'm",
        "amount_tiers": [{"range": "5-50 mln", "months": "25 oy", "rate": "55,9%"}],
        "grace_period": "3 oygacha",
        "collateral": "3 shaxs kafilligi",
        "rate_numeric": 0.559,
        "min_amount": 5_000_000, "max_amount": 50_000_000, "max_months": 25,
    },
    "sahovat": {
        "name": "SAHOVAT", "category": "Mikroqarzlar", "icon": "🎁",
        "amount_range": "2 mln so'm (yangi mijozlar)",
        "amount_tiers": [{"range": "2 mln", "months": "19 oy", "rate": "47,9%"}],
        "grace_period": "3 oygacha",
        "collateral": "3 shaxs kafilligi",
        "rate_numeric": 0.479,
        "min_amount": 2_000_000, "max_amount": 2_000_000, "max_months": 19,
    },
    "nasiya_1": {
        "name": "NASIYA-1", "category": "Mikroqarzlar", "icon": "🛍️",
        "amount_range": "1 mln – 10 mln so'm",
        "amount_tiers": [{"range": "1-10 mln", "months": "37 oy", "rate": "Shartnoma"}],
        "grace_period": "Yo'q",
        "collateral": "Avtomobil, zargarlik, ko'chmas mulk",
        "rate_numeric": 0.50,
        "min_amount": 1_000_000, "max_amount": 10_000_000, "max_months": 37,
    },
    "komak": {
        "name": "KO'MAK", "category": "Mikroqarzlar", "icon": "🤲",
        "amount_range": "1 mln – 15 mln so'm",
        "amount_tiers": [{"range": "1-15 mln", "months": "12 oy", "rate": "66,9%"}],
        "grace_period": "Yo'q",
        "collateral": "Garovsiz, sug'urta",
        "rate_numeric": 0.669,
        "min_amount": 1_000_000, "max_amount": 15_000_000, "max_months": 12,
    },
    "umid": {
        "name": "UMID", "category": "Mikroqarzlar", "icon": "🌈",
        "amount_range": "10 mln – 100 mln so'm",
        "amount_tiers": [{"range": "10-100 mln", "months": "6 oy", "rate": "62,9%"}],
        "grace_period": "5 oygacha",
        "collateral": "Zargarlik (90%)",
        "rate_numeric": 0.629,
        "min_amount": 10_000_000, "max_amount": 100_000_000, "max_months": 6,
    },
    "kredit_liniyasi": {
        "name": "KREDIT LINIYASI", "category": "Mikrokreditlar", "icon": "💳",
        "amount_range": "10 mln – 300 mln so'm",
        "amount_tiers": [{"range": "10-300 mln", "months": "49 oy", "rate": "54,9%"}],
        "grace_period": "—",
        "collateral": "Avtomobil, zargarlik, ko'chmas mulk",
        "rate_numeric": 0.549,
        "min_amount": 10_000_000, "max_amount": 300_000_000, "max_months": 49,
    },
    "rivoj": {
        "name": "RIVOJ", "category": "Mikrokreditlar", "icon": "📈",
        "amount_range": "10 mln – 300 mln so'm",
        "amount_tiers": [{"range": "10-300 mln", "months": "37 oy", "rate": "48%"}],
        "grace_period": "6 oygacha",
        "collateral": "Avtomobil, zargarlik, ko'chmas mulk",
        "rate_numeric": 0.48,
        "min_amount": 10_000_000, "max_amount": 300_000_000, "max_months": 37,
    },
    "tezkor": {
        "name": "TEZKOR", "category": "Mikrokreditlar", "icon": "⚡",
        "amount_range": "3 mln – 50 mln so'm",
        "amount_tiers": [{"range": "3-50 mln", "months": "25 oy", "rate": "59,9%"}],
        "grace_period": "3 oygacha",
        "collateral": "Garovsiz, sug'urta",
        "rate_numeric": 0.599,
        "min_amount": 3_000_000, "max_amount": 50_000_000, "max_months": 25,
    },
    "tadbirkor": {
        "name": "TADBIRKOR", "category": "Mikrokreditlar", "icon": "💼",
        "amount_range": "10 mln – 300 mln so'm",
        "amount_tiers": [{"range": "10-300 mln", "months": "37 oy", "rate": "44,9% / 52,9%"}],
        "grace_period": "6 oygacha",
        "collateral": "Avtomobil, zargarlik, kafillik",
        "rate_numeric": 0.529,
        "min_amount": 10_000_000, "max_amount": 300_000_000, "max_months": 37,
    },
    "samara": {
        "name": "SAMARA", "category": "Mikrokreditlar", "icon": "🏆",
        "amount_range": "10 mln – 300 mln so'm",
        "amount_tiers": [{"range": "10-300 mln", "months": "49 oy", "rate": "44,9% / 52,9%"}],
        "grace_period": "6 oygacha",
        "collateral": "Avtomobil, zargarlik, kafillik",
        "rate_numeric": 0.529,
        "min_amount": 10_000_000, "max_amount": 300_000_000, "max_months": 49,
    },
    "nasiya_2": {
        "name": "NASIYA-2", "category": "Mikrokreditlar", "icon": "🛒",
        "amount_range": "10 mln – 300 mln so'm",
        "amount_tiers": [{"range": "10-300 mln", "months": "37 oy", "rate": "Shartnoma"}],
        "grace_period": "Yo'q",
        "collateral": "Avtomobil, zargarlik, ko'chmas mulk",
        "rate_numeric": 0.50,
        "min_amount": 10_000_000, "max_amount": 300_000_000, "max_months": 37,
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
    },
    "avtokredit": {
        "name": "AVTOKREDIT", "category": "Iste'mol", "icon": "🚗",
        "amount_range": "300 mln so'mgacha",
        "amount_tiers": [{"range": "300 mln gacha", "months": "60 oy", "rate": "48%"}],
        "grace_period": "3 oygacha",
        "collateral": "Avtomobil",
        "rate_numeric": 0.48,
        "min_amount": 5_000_000, "max_amount": 300_000_000, "max_months": 60,
    },
    "davr": {
        "name": "DAVR", "category": "Iste'mol", "icon": "🕐",
        "amount_range": "25 mln so'mgacha",
        "amount_tiers": [{"range": "25 mln gacha", "months": "25 oy", "rate": "52%"}],
        "grace_period": "3 oygacha",
        "collateral": "Xarid qilinayotgan tovar",
        "rate_numeric": 0.52,
        "min_amount": 1_000_000, "max_amount": 25_000_000, "max_months": 25,
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
    {"id": "andijon", "name": "Andijon", "region": "Andijon viloyati",
     "address": "Milliy Tiklanish, 21", "lat": 40.7829, "lng": 72.3442, "is_main": False},
    {"id": "buxoro", "name": "Buxoro", "region": "Buxoro viloyati",
     "address": "Navoiy, ko'chasi", "lat": 39.7675, "lng": 64.4231, "is_main": False},
    {"id": "samarqand", "name": "Samarqand", "region": "Samarqand viloyati",
     "address": "Registon, 8", "lat": 39.6270, "lng": 66.9750, "is_main": False},
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


# ============================================================
# KLAVIATURALAR
# ============================================================
def main_menu_kb(is_adm: bool = False) -> ReplyKeyboardMarkup:
    """Asosiy menyu — Ariza qoldirish olib tashlandi"""
    rows = [
        [KeyboardButton(text="💼 Kreditlar"), KeyboardButton(text="🧮 Kalkulyator")],
        [KeyboardButton(text="📍 Filiallar"), KeyboardButton(text="📞 Aloqa")],
        [KeyboardButton(text="ℹ️ Kompaniya")],
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
        [InlineKeyboardButton(text="📢 Broadcast", callback_data="ADMIN_BROADCAST")],
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
    
    welcome = (
        f"👋 Assalomu alaykum, <b>{user.first_name}</b>!\n\n"
        f"<b>{COMPANY_NAME}</b> rasmiy botiga xush kelibsiz!\n\n"
        f"<i>«{SLOGAN}»</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💼 18 ta kredit mahsuloti\n"
        f"🧮 Kredit kalkulyatori\n"
        f"📍 {len(BRANCHES)} ta filial\n"
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


@router.message(F.text == "🧮 Kalkulyator")
async def menu_calc(message: Message, state: FSMContext):
    await state.clear()
    buttons = []
    for cid, cat in CATEGORIES.items():
        buttons.append([InlineKeyboardButton(
            text=f"{cat['icon']} {cat['name']}",
            callback_data=f"CALCCAT_{cid}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="NAV_MAIN")])
    await message.answer(
        "🧮 <b>Kalkulyator</b>\n\nKategoriyani tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
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
        buttons.append([InlineKeyboardButton(
            text=f"{p['icon']} {p['name']}",
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
    
    cat_id = None
    for cid, c in CATEGORIES.items():
        if pid in c["products"]:
            cat_id = cid
            break
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧮 Kalkulyator", callback_data=f"CALC_{pid}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"CAT_{cat_id}")]
    ])
    
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


# ============================================================
# KALKULYATOR
# ============================================================
@router.callback_query(F.data.startswith("CALCCAT_"))
async def cb_calccat(call: CallbackQuery):
    cid = call.data[8:]
    if cid not in CATEGORIES:
        await call.answer("❌", show_alert=True)
        return
    
    cat = CATEGORIES[cid]
    buttons = []
    for pid in cat["products"]:
        p = LOAN_PRODUCTS[pid]
        buttons.append([InlineKeyboardButton(
            text=f"{p['icon']} {p['name']}",
            callback_data=f"CALC_{pid}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="NAV_CALC")])
    
    await call.message.edit_text(
        f"{cat['icon']} <b>{cat['name']}</b>\n\nMahsulotni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await call.answer()


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
        total = monthly * m
        text += f"  • <b>{m} oy</b> — {format_money(monthly)} so'm/oy\n"
        text += f"    Jami: {format_money(total)}\n"
    
    text += f"\n💡 {PHONE_1_DISPLAY}"
    
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


@router.callback_query(F.data == "NAV_CALC")
async def cb_nav_calc(call: CallbackQuery):
    buttons = []
    for cid, cat in CATEGORIES.items():
        buttons.append([InlineKeyboardButton(
            text=f"{cat['icon']} {cat['name']}",
            callback_data=f"CALCCAT_{cid}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Asosiy", callback_data="NAV_MAIN")])
    await call.message.edit_text(
        "🧮 <b>Kalkulyator</b>",
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
    
    text = (
        f"📊 <b>Statistika</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Foydalanuvchilar:</b>\n"
        f"  • Jami: <b>{get_users_count()}</b>\n"
        f"  • Bugun: <b>{get_today_users_count()}</b>\n\n"
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
