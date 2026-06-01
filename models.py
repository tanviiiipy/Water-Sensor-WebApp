# backend/models.py
from db import fetchall, fetchone, execute, update
import json
import pandas as pd
import numpy as np
import random
from datetime import datetime

# --- Sensors ---
def add_sensor(name, room, active=True, data=None):
    if data is None:
        data = simulate_data().to_dict("records")
    data_json = json.dumps(data)
    return execute("INSERT INTO sensors (name, room, active, data) VALUES (?, ?, ?, ?)",
                   (name, room, int(active), data_json))

def list_sensors():
    rows = fetchall("SELECT * FROM sensors ORDER BY id")
    for r in rows:
        r['active'] = bool(r['active'])
        r['data'] = json.loads(r['data']) if r['data'] else []
    return rows

def get_sensor(sensor_id):
    row = fetchone("SELECT * FROM sensors WHERE id = ?", (sensor_id,))
    if not row:
        return None
    row['active'] = bool(row['active'])
    row['data'] = json.loads(row['data']) if row['data'] else []
    return row

def update_sensor(sensor_id, name=None, room=None, active=None, data=None):
    s = get_sensor(sensor_id)
    if not s:
        return None
    name = name if name is not None else s['name']
    room = room if room is not None else s['room']
    active = int(active) if active is not None else int(s['active'])
    data_json = json.dumps(data) if data is not None else json.dumps(s['data'])
    update("UPDATE sensors SET name=?, room=?, active=?, data=? WHERE id=?", (name, room, active, data_json, sensor_id))
    return get_sensor(sensor_id)

def delete_sensor(sensor_id):
    update("DELETE FROM sensors WHERE id=?", (sensor_id,))
    return True

def simulate_data(days=30):
    dates = pd.date_range(end=pd.Timestamp.today(), periods=days)
    usage = np.random.randint(10, 100, size=days)
    leak_day = random.choice(range(days))
    usage[leak_day] = random.randint(100, 160)
    df = pd.DataFrame({"date": dates.strftime('%Y-%m-%d'), "usage": usage})
    return df

def resimulate_sensor(sensor_id, days=30):
    df = simulate_data(days)
    update_sensor(sensor_id, data=df.to_dict("records"))
    return get_sensor(sensor_id)

# --- Notifications ---
def list_notifications():
    return fetchall("SELECT * FROM notifications ORDER BY id DESC")

def add_notification(msg):
    return execute("INSERT INTO notifications (msg) VALUES (?)", (msg,))

def clear_notifications():
    update("DELETE FROM notifications")
    return True

# --- Settings ---
def get_settings():
    row = fetchone("SELECT * FROM settings WHERE id=1")
    return row

def set_settings(theme=None, refresh=None, enable_notif=None):
    s = get_settings()
    theme = theme if theme is not None else s['theme']
    refresh = refresh if refresh is not None else s['refresh']
    enable_notif = int(enable_notif) if enable_notif is not None else s['enable_notif']
    update("UPDATE settings SET theme=?, refresh=?, enable_notif=? WHERE id=1", (theme, refresh, enable_notif))
    return get_settings()

# --- Checklist ---
def list_checklist():
    return fetchall("SELECT name, done FROM checklist")

def set_checklist_item(name, done):
    update("UPDATE checklist SET done=? WHERE name=?", (int(done), name))
    return fetchone("SELECT name, done FROM checklist WHERE name=?", (name,))

# --- Game ---
def get_game_state():
    row = fetchone("SELECT * FROM game_state WHERE id=1")
    return row

def save_game_state(score, missed, bucket, drop_col):
    update("UPDATE game_state SET score=?, missed=?, bucket=?, drop_col=? WHERE id=1", (score, missed, bucket, drop_col))
    return get_game_state()

def reset_game_state():
    update("UPDATE game_state SET score=0, missed=0, bucket='middle', drop_col='middle' WHERE id=1")
    return get_game_state()

def push_game_history(score):
    execute("INSERT INTO game_history (score) VALUES (?)", (score,))

def list_game_history():
    return fetchall("SELECT * FROM game_history ORDER BY id DESC")

# --- Analytics helpers ---
def compute_totals():
    sensors = list_sensors()
    total_usage = 0
    for s in sensors:
        if s['data']:
            total_usage += sum([d['usage'] for d in s['data']])
    return {"total_usage": total_usage, "sensor_count": len(sensors)}

# --- Badges/Leaderboard ---
def get_badges_and_leaderboard():
    sensors = list_sensors()
    total_usage = sum([sum([d['usage'] for d in s['data']]) for s in sensors if s['data']])
    badges = []
    if total_usage < 1000:
        badges.append("Saved < 1000L")
    if len(sensors) >= 3:
        badges.append("Added 3+ sensors")
    if any(s['data'] and max([d['usage'] for d in s['data']]) > 95 for s in sensors):
        badges.append("Fixed a leak")
    leaderboard = [{"user": "You", "usage": total_usage, "badges": badges}]
    return {"badges": badges, "leaderboard": leaderboard}
