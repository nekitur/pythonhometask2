import sqlite3
from typing import Dict, Any

DB_NAME = "bot_data.db"

def init_db() -> None:
    """
    Создаёт таблицу user_data, если её нет.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_data (
        user_id INTEGER PRIMARY KEY,
        weight REAL,
        height REAL,
        age INTEGER,
        activity INTEGER,
        city TEXT,
        water_goal INTEGER,
        calorie_goal INTEGER,
        logged_water REAL,
        logged_calories REAL,
        burned_calories REAL
    )
    """)
    conn.commit()
    conn.close()


def get_user_data(user_id: int) -> Dict[str, Any]:
    """
    Возвращает словарь с данными пользователя из базы.
    Если записи нет, создаёт "пустую" запись со значениями None или 0.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_data WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row is None:
        empty_data = {
            "user_id": user_id,
            "weight": None,
            "height": None,
            "age": None,
            "activity": None,
            "city": None,
            "water_goal": 0,
            "calorie_goal": 0,
            "logged_water": 0,
            "logged_calories": 0,
            "burned_calories": 0,
        }
        insert_user_data(empty_data)
        conn.close()
        return empty_data
    else:
        data = {
            "user_id": row[0],
            "weight": row[1],
            "height": row[2],
            "age": row[3],
            "activity": row[4],
            "city": row[5],
            "water_goal": row[6],
            "calorie_goal": row[7],
            "logged_water": row[8],
            "logged_calories": row[9],
            "burned_calories": row[10],
        }
        conn.close()
        return data


def insert_user_data(data: Dict[str, Any]) -> None:
    """
    Вставляет запись в таблицу user_data.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO user_data (user_id, weight, height, age, activity, city, water_goal, calorie_goal,
                           logged_water, logged_calories, burned_calories)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["user_id"],
        data["weight"],
        data["height"],
        data["age"],
        data["activity"],
        data["city"],
        data["water_goal"],
        data["calorie_goal"],
        data["logged_water"],
        data["logged_calories"],
        data["burned_calories"],
    ))
    conn.commit()
    conn.close()


def save_user_data(data: Dict[str, Any]) -> None:
    """
    Обновляет запись в таблице user_data. Предполагаем, что она уже есть (создаётся в get_user_data при необходимости).
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE user_data
    SET
        weight = ?,
        height = ?,
        age = ?,
        activity = ?,
        city = ?,
        water_goal = ?,
        calorie_goal = ?,
        logged_water = ?,
        logged_calories = ?,
        burned_calories = ?
    WHERE user_id = ?
    """, (
        data["weight"],
        data["height"],
        data["age"],
        data["activity"],
        data["city"],
        data["water_goal"],
        data["calorie_goal"],
        data["logged_water"],
        data["logged_calories"],
        data["burned_calories"],
        data["user_id"],
    ))
    conn.commit()
    conn.close()
