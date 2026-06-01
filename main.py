# backend/main.py
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import models as M
import db
import random

app = FastAPI(title="WaterSense Backend")

# Allow frontend (Streamlit) to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # OK for hackathon/prototype. Restrict in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB on startup
@app.on_event("startup")
def startup():
    db.init_db()

# --- Pydantic models for request/response ---
class SensorIn(BaseModel):
    name: str
    room: Optional[str] = ""
    active: Optional[bool] = True

class SensorUpdate(BaseModel):
    name: Optional[str] = None
    room: Optional[str] = None
    active: Optional[bool] = None
    data: Optional[list] = None

class GameAction(BaseModel):
    action: str  # "move" or "catch" or "reset"
    bucket: Optional[str] = None

# --- Sensors endpoints ---
@app.post("/sensors")
def api_add_sensor(payload: SensorIn):
    sid = M.add_sensor(payload.name, payload.room, payload.active)
    return {"id": sid, "message": "Sensor added."}

@app.get("/sensors")
def api_list_sensors():
    return M.list_sensors()

@app.get("/sensors/{sensor_id}")
def api_get_sensor(sensor_id: int):
    s = M.get_sensor(sensor_id)
    if not s:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return s

@app.put("/sensors/{sensor_id}")
def api_update_sensor(sensor_id: int, payload: SensorUpdate):
    updated = M.update_sensor(sensor_id, name=payload.name, room=payload.room, active=payload.active, data=payload.data)
    if not updated:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return updated

@app.delete("/sensors/{sensor_id}")
def api_delete_sensor(sensor_id: int):
    M.delete_sensor(sensor_id)
    return {"message": "Deleted"}

@app.post("/sensors/{sensor_id}/resimulate")
def api_resimulate(sensor_id: int, days: int = 30):
    s = M.resimulate_sensor(sensor_id, days)
    return s

# --- Notifications ---
@app.get("/notifications")
def api_list_notifs():
    return M.list_notifications()

@app.post("/notifications")
def api_add_notif(msg: str = Form(...)):
    M.add_notification(msg)
    return {"message": "Notification added"}

@app.post("/notifications/clear")
def api_clear_notifs():
    M.clear_notifications()
    return {"message": "Cleared"}

# --- Settings ---
@app.get("/settings")
def api_get_settings():
    return M.get_settings()

@app.post("/settings")
def api_set_settings(theme: Optional[str] = Form(None), refresh: Optional[int] = Form(None), enable_notif: Optional[int] = Form(None)):
    return M.set_settings(theme=theme, refresh=refresh, enable_notif=enable_notif)

# --- Checklist ---
@app.get("/checklist")
def api_get_checklist():
    return M.list_checklist()

@app.post("/checklist")
def api_set_checklist(name: str = Form(...), done: int = Form(...)):
    return M.set_checklist_item(name, done)

# --- Game endpoints ---
@app.get("/game")
def api_get_game():
    return M.get_game_state()

@app.post("/game/action")
def api_game_action(payload: GameAction):
    state = M.get_game_state()
    score = state['score']
    missed = state['missed']
    bucket = state['bucket']
    drop_col = state['drop_col']
    if payload.action == "move":
        bucket = payload.bucket or bucket
        M.save_game_state(score, missed, bucket, drop_col)
        return M.get_game_state()
    elif payload.action == "catch":
        # compare
        if payload.bucket is not None:
            bucket = payload.bucket
        if bucket == drop_col:
            score += 1
            msg = "caught"
        else:
            missed += 1
            msg = "missed"
        # new drop
        drop_col = random.choice(["left", "middle", "right"])
        M.save_game_state(score, missed, bucket, drop_col)
        # push to history if finished
        if score >= 20 or missed > 10:
            M.push_game_history(score)
        return {"state": M.get_game_state(), "result": msg}
    elif payload.action == "reset":
        M.reset_game_state()
        return M.get_game_state()
    else:
        raise HTTPException(status_code=400, detail="Unknown action")

@app.get("/game/history")
def api_game_history():
    return M.list_game_history()

# --- Analytics & badges ---
@app.get("/analytics")
def api_analytics():
    return M.compute_totals()

@app.get("/badges")
def api_badges():
    return M.get_badges_and_leaderboard()
