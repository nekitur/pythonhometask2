import logging
import requests

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

import db

STATE_WEIGHT, STATE_HEIGHT, STATE_AGE, STATE_ACTIVITY, STATE_CITY = range(5)


def init():
    db.init_db()


def get_weather_temperature(city: str) -> float:
    api_key = ""    
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        temp = data['main']['temp']
        return temp
    else:
        return -900


def calculate_water_goal(weight: float, activity_minutes: int, temperature: float) -> int:
    base = weight * 30
    activity_bonus = (activity_minutes // 30) * 500
    weather_bonus = 500 if temperature > 25 else 0
    return int(base + activity_bonus + weather_bonus)


def calculate_calorie_goal(weight: float, height: float, age: float, activity_minutes: int) -> int:
    bmr = 10 * weight + 6.25 * height - 5 * age
    activity_bonus = (activity_minutes // 30) * 100
    return int(bmr + activity_bonus)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я бот для расчёта нормы воды и калорий.\n"
        "Используйте /set_profile, чтобы настроить ваш профиль."
    )


async def set_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите ваш вес (в кг):")
    return STATE_WEIGHT


async def set_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    weight_text = update.message.text.strip()
    try:
        weight = float(weight_text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число (например, 80). Повторите ввод:")
        return STATE_WEIGHT

    user_data = db.get_user_data(user_id)
    user_data["weight"] = weight
    db.save_user_data(user_data)

    await update.message.reply_text("Введите ваш рост (в см):")
    return STATE_HEIGHT


async def set_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    height_text = update.message.text.strip()
    try:
        height = float(height_text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число (например, 180). Повторите ввод:")
        return STATE_HEIGHT

    user_data = db.get_user_data(user_id)
    user_data["height"] = height
    db.save_user_data(user_data)

    await update.message.reply_text("Введите ваш возраст (целое число):")
    return STATE_AGE


async def set_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    age_text = update.message.text.strip()
    try:
        age = int(age_text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите целое число (например, 26). Повторите ввод:")
        return STATE_AGE

    user_data = db.get_user_data(user_id)
    user_data["age"] = age
    db.save_user_data(user_data)

    await update.message.reply_text("Сколько минут активности у вас в день?")
    return STATE_ACTIVITY


async def set_activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    act_text = update.message.text.strip()
    try:
        activity = int(act_text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите целое число (например, 45). Повторите ввод:")
        return STATE_ACTIVITY

    user_data = db.get_user_data(user_id)
    user_data["activity"] = activity
    db.save_user_data(user_data)

    await update.message.reply_text("В каком городе вы находитесь?")
    return STATE_CITY


async def set_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    city_text = update.message.text.strip()

    user_data = db.get_user_data(user_id)
    user_data["city"] = city_text

    temperature = get_weather_temperature(city_text)
    if temperature == -900:
        await update.message.reply_text(
        "К сожалению, Ваш город мне найти не удалось. Попробуйте пожалуйста указать его еще раз."
        )
    user_data["water_goal"] = calculate_water_goal(
        user_data["weight"] or 0.0,
        user_data["activity"] or 0,
        temperature
    )
    user_data["calorie_goal"] = calculate_calorie_goal(
        user_data["weight"] or 0.0,
        user_data["height"] or 0.0,
        user_data["age"] or 0,
        user_data["activity"] or 0
    )
    user_data["logged_water"] = 0
    user_data["logged_calories"] = 0
    user_data["burned_calories"] = 0
    db.save_user_data(user_data)

    await update.message.reply_text(
        "Ваш профиль сохранён!\n"
        f"Цель по воде: {user_data['water_goal']} мл в день\n"
        f"Цель по калориям: {user_data['calorie_goal']} ккал в день\n"
        "Можете начать логировать воду, еду и тренировки."
    )

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Настройка отменена.")
    return ConversationHandler.END


async def log_water(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_data = db.get_user_data(user_id)

    args = context.args
    if not args:
        await update.message.reply_text("Использование: /log_water <количество в мл>")
        return

    try:
        amount = float(args[0].replace(",", "."))
    except ValueError:
        await update.message.reply_text("Пожалуйста, укажите число (в мл). Например: /log_water 250")
        return

    user_data["logged_water"] += amount
    remaining = user_data["water_goal"] - user_data["logged_water"]
    if remaining < 0:
        remaining = 0

    db.save_user_data(user_data)

    await update.message.reply_text(
        f"Записано {amount} мл воды.\n"
        f"Всего выпито: {user_data['logged_water']} мл.\n"
        f"Осталось: {remaining} мл до цели."
    )

def get_food_info(product_name: str):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&search_terms={product_name}&json=true"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        products = data.get('products', [])
        if products:
            first_product = products[0]
            return {
                'name': first_product.get('product_name', 'Неизвестно'),
                'calories': first_product.get('nutriments', {}).get('energy-kcal_100g', 0)
            }
        return None
    print(f"Ошибка API: {response.status_code}")
    return None 

async def log_food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Использование: /log_food <название продукта>")
        return

    product_name = " ".join(context.args)

    food_info = get_food_info(product_name)

    if food_info:
        product_name = food_info['name']
        cals_per_100g = food_info['calories']
    else:
        await update.message.reply_text(f"Не удалось найти информацию о продукте '{product_name}'. Попробуйте снова.")
        return

    context.user_data["temp_food"] = {
        "product_name": product_name,
        "calories_per_100g": cals_per_100g
    }

    await update.message.reply_text(
        f"Вы указали продукт: {product_name}\n"
        f"Калорийность: {cals_per_100g} ккал на 100 г.\n"
        "Сколько грамм вы съели? Ответьте числом:"
    )

async def handle_food_grams(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if "temp_food" not in context.user_data:
        return

    grams_text = update.message.text.strip()
    try:
        grams = float(grams_text.replace(",", "."))
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите число (граммы). Попробуйте снова /log_food."
        )
        context.user_data.pop("temp_food", None)
        return

    product_info = context.user_data["temp_food"]
    cals_per_100g = product_info["calories_per_100g"]

    total_calories = cals_per_100g * (grams / 100.0)

    user_id = update.effective_user.id
    user_data = db.get_user_data(user_id)

    user_data["logged_calories"] += total_calories
    db.save_user_data(user_data)

    await update.message.reply_text(
        f"Записано: {product_info['product_name']} — {total_calories:.1f} ккал.\n"
        f"Всего сегодня съедено: {user_data['logged_calories']:.1f} ккал."
    )

    context.user_data.pop("temp_food", None)

async def log_workout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_data = db.get_user_data(user_id)

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Использование: /log_workout <тип> <минуты>")
        return

    workout_type = args[0]
    try:
        minutes = int(args[1])
    except ValueError:
        await update.message.reply_text("Пожалуйста, укажите целое число минут. Пример: /log_workout бег 30")
        return

    workout_map = {
        "бег": 10, 
        "ходьба": 5,
        "силовая": 8,
    }
    rate = workout_map.get(workout_type.lower(), 6)
    burned = rate * minutes

    user_data["burned_calories"] += burned
    db.save_user_data(user_data)

    additional_water = (minutes // 30) * 200

    await update.message.reply_text(
        f"Тренировка: {workout_type} {minutes} мин — {burned} ккал.\n"
        f"Рекомендуется дополнительно выпить {additional_water} мл воды."
    )

async def check_progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_data = db.get_user_data(user_id)

    water_drunk = user_data["logged_water"]
    water_goal = user_data["water_goal"]
    water_left = max(water_goal - water_drunk, 0)

    cals_eaten = user_data["logged_calories"]
    cals_goal = user_data["calorie_goal"]
    cals_burned = user_data["burned_calories"]
    balance = cals_eaten - cals_burned
    cals_left = max(cals_goal - balance, 0)

    await update.message.reply_text(
        f"📊 Прогресс:\n\n"
        f"Вода:\n"
        f"- Выпито: {water_drunk:.0f} мл из {water_goal} мл\n"
        f"- Осталось: {water_left:.0f} мл\n\n"
        f"Калории:\n"
        f"- Потреблено: {cals_eaten:.0f} ккал\n"
        f"- Сожжено: {cals_burned:.0f} ккал\n"
        f"- Цель: {cals_goal} ккал\n"
        f"- Баланс (съедено - сожжено): {balance:.0f} ккал\n"
        f"- Осталось до цели: {cals_left:.0f} ккал"
    )


async def log_user_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg_text = update.message.text if update.message else "Нет текста"
    logging.info(
        f"[LOG_USER_MESSAGE] User ID: {user.id}, "
        f"Username: {user.username}, "
        f"Message: {msg_text}"
    )


def main():
    init() 

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        filename=r"logs.log", 
        filemode='a' 
    )

    TOKEN = ""
    app = ApplicationBuilder().token(TOKEN).build()
    logging.info("=== Starting the bot ===")

    log_handler = MessageHandler(filters.ALL, log_user_messages)
    app.add_handler(log_handler, group=0)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("set_profile", set_profile)],
        states={
            STATE_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_weight)],
            STATE_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_height)],
            STATE_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_age)],
            STATE_ACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_activity)],
            STATE_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_city)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler, group=1)

    app.add_handler(CommandHandler("start", start), group=1)
    app.add_handler(CommandHandler("log_water", log_water), group=1)
    app.add_handler(CommandHandler("log_food", log_food), group=1)
    app.add_handler(CommandHandler("log_workout", log_workout), group=1)
    app.add_handler(CommandHandler("check_progress", check_progress), group=1)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_food_grams), group=1)

    app.run_polling()


if __name__ == "__main__":
    main()
