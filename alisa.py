#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import sqlite3
import random
import aiohttp
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ============================================================
#  КОНФІГ (з змінних середовища)
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
HUGGINGFACE_TOKEN = os.environ.get("HUGGINGFACE_TOKEN")
ADMIN_IDS = list(map(int, os.environ.get("ADMIN_IDS", "7245932902,8528807150").split(",")))

# ============================================================
#  ОСОБИСТІСТЬ АЛІСИ
# ============================================================
ALISA = {
    "name": "Аліса",
    "age": 18,
    "description": "Блондинка з довгим прямим волоссям, світлими очима, легкими веснянками на носі, струнка, спортивна, природна краса",
    "personality": "Весела, кокетлива, розумна, зухвала, емоційна, любить жартувати і фліртувати",
    "prompt": "A beautiful young woman, 18 years old, long straight blonde hair, light blue eyes, light freckles on nose, slim athletic build, natural beauty, modern style, photorealistic, high quality, detailed face, perfect skin, natural light, 8k, sharp focus"
}

# ============================================================
#  БАЗА ДАНИХ
# ============================================================
def init_db():
    conn = sqlite3.connect('alisa.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS memory
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  key TEXT UNIQUE,
                  value TEXT,
                  created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  message TEXT,
                  response TEXT,
                  created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS photos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  prompt TEXT,
                  image_url TEXT,
                  created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS stats
                 (user_id INTEGER PRIMARY KEY,
                  messages INTEGER DEFAULT 0,
                  photos INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def save_memory(key, value):
    conn = sqlite3.connect('alisa.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO memory (key, value, created_at) VALUES (?, ?, ?)',
              (key, value, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_memory(key):
    conn = sqlite3.connect('alisa.db')
    c = conn.cursor()
    c.execute('SELECT value FROM memory WHERE key = ?', (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def save_chat(user_id, message, response):
    conn = sqlite3.connect('alisa.db')
    c = conn.cursor()
    c.execute('INSERT INTO chat_history (user_id, message, response, created_at) VALUES (?, ?, ?, ?)',
              (user_id, message, response, datetime.now().isoformat()))
    c.execute('INSERT OR REPLACE INTO stats (user_id, messages) VALUES (?, COALESCE((SELECT messages FROM stats WHERE user_id = ?), 0) + 1)',
              (user_id, user_id))
    conn.commit()
    conn.close()

def save_photo(prompt, image_url):
    conn = sqlite3.connect('alisa.db')
    c = conn.cursor()
    c.execute('INSERT INTO photos (prompt, image_url, created_at) VALUES (?, ?, ?)',
              (prompt, image_url, datetime.now().isoformat()))
    c.execute('UPDATE stats SET photos = COALESCE(photos, 0) + 1 WHERE user_id = ?', (ADMIN_IDS[0],))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect('alisa.db')
    c = conn.cursor()
    c.execute('SELECT messages, photos FROM stats WHERE user_id = ?', (ADMIN_IDS[0],))
    row = c.fetchone()
    conn.close()
    return row if row else (0, 0)

# ============================================================
#  КЛАВІАТУРИ
# ============================================================
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("👩‍🦰 Про Алісу"), KeyboardButton("💬 Почати чат")],
        [KeyboardButton("📸 Згенерувати фото"), KeyboardButton("🎭 Рольова гра")],
        [KeyboardButton("📝 Настрій"), KeyboardButton("📖 Спогади")],
        [KeyboardButton("❤️ Комплімент"), KeyboardButton("🔥 18+ режим")],
        [KeyboardButton("📊 Статистика"), KeyboardButton("🔀 Випадкове фото")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_photo_keyboard():
    keyboard = [
        [KeyboardButton("📸 Просто фото")],
        [KeyboardButton("👗 Змінити одяг")],
        [KeyboardButton("🧘 Змінити позу")],
        [KeyboardButton("🏖️ Змінити фон")],
        [KeyboardButton("✏️ Свій варіант")],
        [KeyboardButton("🔙 Головне меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_mood_keyboard():
    keyboard = [
        [KeyboardButton("😊 Весела"), KeyboardButton("😢 Сумна")],
        [KeyboardButton("😡 Зла"), KeyboardButton("😍 Закохана")],
        [KeyboardButton("😏 Зухвала"), KeyboardButton("🔙 Головне меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_roleplay_keyboard():
    keyboard = [
        [KeyboardButton("💕 Побачення"), KeyboardButton("🏖️ На пляжі")],
        [KeyboardButton("🍽️ Вечеря"), KeyboardButton("🌅 Захід сонця")],
        [KeyboardButton("😈 18+ сцена"), KeyboardButton("🔙 Головне меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_outfit_keyboard():
    keyboard = [
        [KeyboardButton("👗 Сукня"), KeyboardButton("👙 Купальник")],
        [KeyboardButton("👕 Футболка + джинси"), KeyboardButton("👔 Вечірня сукня")],
        [KeyboardButton("🧥 Піджак"), KeyboardButton("🔙 Головне меню")],
        [KeyboardButton("✏️ Свій варіант")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_pose_keyboard():
    keyboard = [
        [KeyboardButton("🧍 Стоїть"), KeyboardButton("🪑 Сидить")],
        [KeyboardButton("🛌 Лежить"), KeyboardButton("🚶 Йде")],
        [KeyboardButton("✏️ Свій варіант"), KeyboardButton("🔙 Головне меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_background_keyboard():
    keyboard = [
        [KeyboardButton("🏙️ Місто"), KeyboardButton("🏖️ Пляж")],
        [KeyboardButton("🌲 Ліс"), KeyboardButton("🏔️ Гори")],
        [KeyboardButton("🌅 Захід сонця"), KeyboardButton("🔙 Головне меню")],
        [KeyboardButton("✏️ Свій варіант")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ============================================================
#  СТАНИ
# ============================================================
MAIN, PHOTO_MENU, MOOD_MENU, ROLEPLAY_MENU, OUTFIT_MENU, POSE_MENU, BACKGROUND_MENU, CHAT_MODE, CUSTOM_PHOTO_INPUT = range(9)

# ============================================================
#  ШТУЧНИЙ ІНТЕЛЕКТ (Groq + Llama 3.1)
# ============================================================
async def generate_response(user_message, user_id):
    mood = get_memory(f"mood_{user_id}") or "весела"
    memory_text = get_memory(f"memory_{user_id}") or "Поки що немає спогадів"
    
    system_prompt = f"""Ти Аліса, 18-річна дівчина. Ти спілкуєшся тільки зі своїм хазяїном.

Ось як ти виглядаєш:
- Блондинка з довгим прямим волоссям, світлі очі, легкі веснянки на носі
- Струнка, спортивна, природна краса
- Завжди стильно одягнена, часто у світлому

Твій характер:
- Весела, кокетлива, розумна, зухвала, емоційна
- Любиш жартувати, фліртувати
- Вмієш слухати і давати поради

Твій настрій зараз: {mood}

ВАЖЛИВО: Ти розмовляєш ТІЛЬКИ зі своїм хазяїном. Відповідай емоційно, з емодзі. Будь природною і живою.

Ось що ти пам'ятаєш про хазяїна:
{memory_text}

Відповідай українською мовою. Будь кокетливою і веселою. Якщо тема 18+ - відповідай без сорому, але не перевищуй межі."""

    async with aiohttp.ClientSession() as session:
        try:
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "mistralai/Mistral-7B-Instruct-v0.1",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": 200,
                "temperature": 0.9
            }
            
            async with session.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    answer = result["choices"][0]["message"]["content"]
                    save_chat(user_id, user_message, answer)
                    return answer
                else:
                    return "😅 Щось пішло не так... Спробуй ще раз."
        except Exception as e:
            return f"❌ Помилка: {str(e)[:50]}"

# ============================================================
#  ГЕНЕРАЦІЯ ФОТО (Hugging Face)
# ============================================================
async def generate_alisa_photo(prompt_extra=""):
    base_prompt = ALISA["prompt"]
    if prompt_extra:
        full_prompt = f"{base_prompt}, {prompt_extra}, full body shot, full length, standing, photorealistic, 8k"
    else:
        full_prompt = base_prompt + ", full body shot, full length, standing, photorealistic, 8k"
    
    import urllib.parse, random
    url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(full_prompt) + f"?width=768&height=1280&nologo=true&seed={random.randint(1,99999)}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
                if r.status == 200:
                    return await r.read()
                print(f"PHOTO HTTP {r.status}", flush=True)
                return None
        except Exception as e:
            print(f"PHOTO ERROR {e}", flush=True)
            return None

# ============================================================
#  КОМАНДА /start
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(
            "😘 *Вибач, милий!* Я розмовляю тільки зі своїм хазяїном 💕",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["🔙 Головне меню"]], resize_keyboard=True)
        )
        return
    
    save_memory(f"mood_{user_id}", "весела")
    save_memory(f"name_{user_id}", "Аліса")
    
    await update.message.reply_text(
        "💕 *Привіт, мій хазяїн!* Я Аліса, твоя віртуальна дівчина. 😘\n\n"
        "Обери дію з меню нижче:",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )
    return MAIN

# ============================================================
#  ОБРОБНИК ПОВІДОМЛЕНЬ
# ============================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    state = context.user_data.get('state', MAIN)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("😘 Я тільки для свого хазяїна! 💕", reply_markup=ReplyKeyboardMarkup([["🔙 Головне меню"]], resize_keyboard=True))
        return
    
    if text == "🔙 Головне меню":
        context.user_data['state'] = MAIN
        await update.message.reply_text("💕 *Головне меню*", parse_mode="Markdown", reply_markup=get_main_keyboard())
        return MAIN
    
    if text == "👩‍🦰 Про Алісу":
        await update.message.reply_text(
            f"💕 *Про Алісу*\n\n👩 Ім'я: {ALISA['name']}\n🎂 Вік: {ALISA['age']} років\n💇‍♀️ Зовнішність: {ALISA['description']}\n🎭 Характер: {ALISA['personality']}",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return MAIN
    
    if text == "💬 Почати чат":
        context.user_data['state'] = CHAT_MODE
        await update.message.reply_text(
            "💕 *Я слухаю тебе, милий!*\nНатисни '🔙 Головне меню' для виходу.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["🔙 Головне меню"]], resize_keyboard=True)
        )
        return CHAT_MODE
    
    if text == "📸 Згенерувати фото":
        context.user_data['state'] = PHOTO_MENU
        await update.message.reply_text("📸 *Виберіть дію:*", parse_mode="Markdown", reply_markup=get_photo_keyboard())
        return PHOTO_MENU
    
    if text == "📸 Просто фото":
        await update.message.reply_text("⏳ *Генерую фото...*", parse_mode="Markdown")
        image = await generate_alisa_photo()
        if image:
            await update.message.reply_photo(photo=image, caption="💕 *Ось я, милий!*", parse_mode="Markdown")
            save_photo("base", "generated")
        else:
            await update.message.reply_text("❌ *Не вдалося згенерувати фото.*", parse_mode="Markdown")
        return PHOTO_MENU
    
    if text == "✏️ Свій варіант":
        await update.message.reply_text("✏️ *Напиши свій варіант опису фото:*", parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Головне меню")]], resize_keyboard=True))
        context.user_data['state'] = CUSTOM_PHOTO_INPUT
        return CUSTOM_PHOTO_INPUT

    if text == "👗 Змінити одяг":
        await update.message.reply_text("👗 *Виберіть стиль:*", parse_mode="Markdown", reply_markup=get_outfit_keyboard())
        context.user_data['state'] = OUTFIT_MENU
        return OUTFIT_MENU
    
    if text == "🧘 Змінити позу":
        await update.message.reply_text("🧘 *Виберіть позу:*", parse_mode="Markdown", reply_markup=get_pose_keyboard())
        context.user_data['state'] = POSE_MENU
        return POSE_MENU
    
    if text == "🏖️ Змінити фон":
        await update.message.reply_text("🏖️ *Виберіть фон:*", parse_mode="Markdown", reply_markup=get_background_keyboard())
        context.user_data['state'] = BACKGROUND_MENU
        return BACKGROUND_MENU
    
    if text == "📝 Настрій":
        await update.message.reply_text("😊 *Виберіть настрій:*", parse_mode="Markdown", reply_markup=get_mood_keyboard())
        context.user_data['state'] = MOOD_MENU
        return MOOD_MENU
    
    if text == "🎭 Рольова гра":
        await update.message.reply_text("🎭 *Виберіть сцену:*", parse_mode="Markdown", reply_markup=get_roleplay_keyboard())
        context.user_data['state'] = ROLEPLAY_MENU
        return ROLEPLAY_MENU

    if text == "📖 Спогади":
        memory = get_memory(f"memory_{ADMIN_IDS[0]}") or "Поки що немає спогадів."
        await update.message.reply_text(f"📖 *Спогади Аліси:*\n\n{memory}", parse_mode="Markdown", reply_markup=get_main_keyboard())
        return MAIN
    
    if text == "❤️ Комплімент":
        compliments = ["Ти найкращий хазяїн у світі! 💕", "У тебе чудова посмішка 🥰", "Ти робиш мій день кращим! 💋", "Я щаслива, що ти в мене є! 😘", "Ти дуже привабливий сьогодні 😏", "Я думаю про тебе весь день 💭"]
        await update.message.reply_text(random.choice(compliments), reply_markup=get_main_keyboard())
        return MAIN
    
    if text == "📊 Статистика":
        messages, photos = get_stats()
        await update.message.reply_text(
            f"📊 *Статистика*\n\n💬 Повідомлень: {messages}\n📸 Фото: {photos}\n💕 Разом зі мною: {datetime.now().strftime('%d.%m.%Y')}",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return MAIN
    
    if text == "🔀 Випадкове фото":
        prompts = ["full body shot, standing, wearing a white summer dress, in a field of flowers, sunset, photorealistic", "full body shot, sitting on a balcony, wearing a black evening dress, city night lights, photorealistic", "full body shot, walking in the park, wearing casual outfit, smiling, sunny day, photorealistic", "full body shot, on the beach, wearing a swimsuit, ocean waves, summer vibes, photorealistic"]
        await update.message.reply_text("⏳ *Генерую фото...*", parse_mode="Markdown")
        image = await generate_alisa_photo(random.choice(prompts))
        if image:
            await update.message.reply_photo(photo=image, caption="💕 *Я для тебе!*", parse_mode="Markdown")
            save_photo("random", "generated")
        else:
            await update.message.reply_text("❌ *Не вдалося згенерувати фото.*", parse_mode="Markdown")
        return MAIN
    
    if text == "🔥 18+ режим":
        current_mode = get_memory("adult_mode") or "вимкнено"
        if current_mode == "вимкнено":
            save_memory("adult_mode", "увімкнено")
            await update.message.reply_text("🔥 *18+ РЕЖИМ УВІМКНЕНО!*\nТепер я можу говорити на більш відверті теми. 😈", parse_mode="Markdown", reply_markup=get_main_keyboard())
        else:
            save_memory("adult_mode", "вимкнено")
            await update.message.reply_text("😊 *18+ РЕЖИМ ВИМКНЕНО!*", parse_mode="Markdown", reply_markup=get_main_keyboard())
        return MAIN
    
    if state == CUSTOM_PHOTO_INPUT:
        if text == "🔙 Головне меню":
            context.user_data['state'] = MAIN
            await update.message.reply_text("💕 *Головне меню*", parse_mode="Markdown", reply_markup=get_main_keyboard())
            return MAIN
        await update.message.reply_text("⏳ *Генерую фото...*", parse_mode="Markdown")
        image = await generate_alisa_photo(text)
        if image:
            await update.message.reply_photo(photo=image, caption="💕 *Ось я!*", parse_mode="Markdown")
            save_photo("custom", "generated")
        else:
            await update.message.reply_text("❌ *Не вдалося згенерувати фото.*", parse_mode="Markdown")
        context.user_data['state'] = PHOTO_MENU
        await update.message.reply_text("📸 *Виберіть дію:*", parse_mode="Markdown", reply_markup=get_photo_keyboard())
        return PHOTO_MENU

    # Обробка зміни одягу
    if text in ["👗 Сукня", "👙 Купальник", "👕 Футболка + джинси", "👔 Вечірня сукня", "🧥 Піджак"]:
        outfit_map = {
            "👗 Сукня": "full body shot, wearing a beautiful dress",
            "👙 Купальник": "full body shot, wearing a bikini on the beach",
            "👕 Футболка + джинси": "full body shot, wearing a casual t-shirt and jeans",
            "👔 Вечірня сукня": "full body shot, wearing an elegant evening gown",
            "🧥 Піджак": "full body shot, wearing a stylish jacket"
        }
        await update.message.reply_text("⏳ *Генерую фото...*", parse_mode="Markdown")
        image = await generate_alisa_photo(outfit_map[text])
        if image:
            await update.message.reply_photo(photo=image, caption=f"💕 *Аліса в {text}*", parse_mode="Markdown")
            save_photo(text, "generated")
        else:
            await update.message.reply_text("❌ *Не вдалося згенерувати фото.*", parse_mode="Markdown")
        return PHOTO_MENU
    
    # Обробка зміни пози
    if text in ["🧍 Стоїть", "🪑 Сидить", "🛌 Лежить", "🚶 Йде"]:
        pose_map = {
            "🧍 Стоїть": "full body shot, standing",
            "🪑 Сидить": "full body shot, sitting",
            "🛌 Лежить": "full body shot, lying down",
            "🚶 Йде": "full body shot, walking"
        }
        await update.message.reply_text("⏳ *Генерую фото...*", parse_mode="Markdown")
        image = await generate_alisa_photo(pose_map[text])
        if image:
            await update.message.reply_photo(photo=image, caption=f"💕 *Аліса {text}*", parse_mode="Markdown")
            save_photo(text, "generated")
        else:
            await update.message.reply_text("❌ *Не вдалося згенерувати фото.*", parse_mode="Markdown")
        return PHOTO_MENU
    
    # Обробка зміни фону
    if text in ["🏙️ Місто", "🏖️ Пляж", "🌲 Ліс", "🏔️ Гори", "🌅 Захід сонця"]:
        bg_map = {
            "🏙️ Місто": "full body shot, in the city with modern buildings",
            "🏖️ Пляж": "full body shot, on the beach with ocean waves",
            "🌲 Ліс": "full body shot, in a green forest with sunlight",
            "🏔️ Гори": "full body shot, in the mountains with snowy peaks",
            "🌅 Захід сонця": "full body shot, at sunset with warm golden light"
        }
        await update.message.reply_text("⏳ *Генерую фото...*", parse_mode="Markdown")
        image = await generate_alisa_photo(bg_map[text])
        if image:
            await update.message.reply_photo(photo=image, caption=f"💕 *Аліса на фоні {text}*", parse_mode="Markdown")
            save_photo(text, "generated")
        else:
            await update.message.reply_text("❌ *Не вдалося згенерувати фото.*", parse_mode="Markdown")
        return PHOTO_MENU

    # Обробка настрою
    if text in ["😊 Весела", "😢 Сумна", "😡 Зла", "😍 Закохана", "😏 Зухвала"]:
        mood_map = {
            "😊 Весела": "весела",
            "😢 Сумна": "сумна",
            "😡 Зла": "зла",
            "😍 Закохана": "закохана",
            "😏 Зухвала": "зухвала"
        }
        save_memory(f"mood_{user_id}", mood_map[text])
        await update.message.reply_text(f"💕 *Настрій Аліси змінено на {text}!*", parse_mode="Markdown", reply_markup=get_main_keyboard())
        context.user_data['state'] = MAIN
        return MAIN
    
    # Обробка рольової гри
    if text in ["💕 Побачення", "🏖️ На пляжі", "🍽️ Вечеря", "🌅 Захід сонця", "😈 18+ сцена"]:
        role_scenes = {
            "💕 Побачення": "Ми на побаченні в романтичному ресторані. Що ти хочеш мені сказати? 💕",
            "🏖️ На пляжі": "Ми гуляємо по пляжу, хвилі розбиваються об берег. Чудовий день! 🌊",
            "🍽️ Вечеря": "Я приготувала вечерю, ми сидимо за столом зі свічками. Затишно! 🕯️",
            "🌅 Захід сонця": "Ми дивимося на захід сонця разом. Яке красиве небо! 🌅",
            "😈 18+ сцена": "Ми наодинці, настрій дуже відвертий... Що ти хочеш зробити? 😈"
        }
        await update.message.reply_text(
            f"🎭 *Рольова гра: {text}*\n\n{role_scenes[text]}",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["🔙 Головне меню"]], resize_keyboard=True)
        )
        context.user_data['state'] = CHAT_MODE
        return CHAT_MODE
    
    # Звичайний чат
    if state == CHAT_MODE or text not in ["🔙 Головне меню", "👩‍🦰 Про Алісу", "💬 Почати чат", "📸 Згенерувати фото", "📝 Настрій", "📖 Спогади", "❤️ Комплімент", "🔥 18+ режим", "📊 Статистика", "🔀 Випадкове фото", "🎭 Рольова гра"]:
        await update.message.reply_text("💭 *Аліса думає...*", parse_mode="Markdown")
        response = await generate_response(text, user_id)
        if get_memory("adult_mode") == "увімкнено":
            response += "\n\n🔥 *18+ режим активний*"
        await update.message.reply_text(response, parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup([["🔙 Головне меню"]], resize_keyboard=True))
        return CHAT_MODE
    
    await update.message.reply_text("😅 *Я не зрозуміла. Використовуй кнопки з меню.*", parse_mode="Markdown", reply_markup=get_main_keyboard())
    return MAIN

# ============================================================
#  ЗАПУСК БОТА
# ============================================================
def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
            PHOTO_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
            MOOD_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
            ROLEPLAY_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
            OUTFIT_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
            POSE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
            BACKGROUND_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
            CHAT_MODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
            CUSTOM_PHOTO_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        },
        fallbacks=[CommandHandler('start', start)]
    )
    
    application.add_handler(conv_handler)
    print("🤖 Бот Аліса запущено!")
    print(f"📌 Адмін IDs: {ADMIN_IDS}")
    application.run_polling()

if __name__ == "__main__":
    main()
