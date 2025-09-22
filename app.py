# frontend/app.py
import streamlit as st
import pandas as pd
import numpy as np
import random
import requests
import json
from pathlib import Path

# ------------------- CONFIG -------------------
BACKEND_URL = "http://127.0.0.1:8000"
APP_NAME = "💧 WaterSense"
TEAM_NAME = "Pseudocoders"

WATER_FACTS = [
    "A single leaky faucet can waste over 3,000 gallons per year. 💦",
    "97% of the earth’s water is salt water. 🌊",
    "Freshwater makes up only about 2.5% of all water on Earth. 💧",
    "It takes about 2,000 gallons of water to produce one pound of beef. 🥩",
    "Turning off the tap while brushing teeth saves up to 8 gallons a day. 🪥"
]

TEAM_MEMBERS = ["Tanvi", "Neha", "Riya", "Nikhita"]

# ------------------- HELPERS: API wrappers -------------------
def api_get(path):
    return requests.get(BACKEND_URL + path).json()

def api_post(path, data=None, files=None):
    if files:
        return requests.post(BACKEND_URL + path, files=files).json()
    return requests.post(BACKEND_URL + path, data=data).json()

def api_put(path, json_payload):
    return requests.put(BACKEND_URL + path, json=json_payload).json()

def api_delete(path):
    return requests.delete(BACKEND_URL + path).json()

# ------------------- STATE INIT in frontend session_state (for UI) ---
if "local_game_feedback" not in st.session_state:
    st.session_state["local_game_feedback"] = ""

# --------------- SENSORS (calls backend) ----------------
def sensors_page():
    st.title("🛠️ Manage Sensors")
    st.info("Add sensors for different rooms or fixtures! 🏠")

    sensors = api_get("/sensors")
    if sensors:
        df = pd.DataFrame([{
            "ID": s["id"],
            "Name": s["name"],
            "Room": s["room"],
            "Active": "✅" if s.get("active") else "❌",
            "Last Update": (s["data"][-1]["date"] if s["data"] else "N/A")
        } for s in sensors])
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No sensors yet. Add one below. ⚠️")

    with st.expander("➕ Add Sensor", expanded=True):
        with st.form("add_sensor_form"):
            new_name = st.text_input("Sensor Name", placeholder="e.g. Kitchen Tap")
            room = st.text_input("Room", placeholder="e.g. Kitchen")
            active = st.checkbox("Active", value=True)
            submit = st.form_submit_button("Add Sensor")
            if submit and new_name:
                res = api_post("/sensors", data={"name": new_name, "room": room, "active": str(int(active))})
                st.success(f"Sensor '{new_name}' added! 🎉")
                st.experimental_rerun()

    if sensors:
        st.markdown("---")
        st.write("Edit / Delete sensors")
        sid = st.selectbox("Select sensor by ID", [s["id"] for s in sensors])
        s = next(filter(lambda x: x["id"] == sid, sensors))
        st.write("Selected:", s["name"], "in", s["room"])
        new_room = st.text_input("Edit Room", value=s["room"])
        new_active = st.checkbox("Active", value=s["active"])
        if st.button("Update Sensor"):
            api_put(f"/sensors/{sid}", json_payload={"room": new_room, "active": new_active})
            st.success("Sensor updated.")
            st.experimental_rerun()
        if st.button("Delete Sensor"):
            api_delete(f"/sensors/{sid}")
            st.success("Sensor deleted.")
            st.experimental_rerun()

        st.divider()
        st.write("Sensor Data")
        if s["data"]:
            df = pd.DataFrame(s["data"])
            st.dataframe(df, use_container_width=True)
            if st.button("Resimulate Data"):
                api_post(f"/sensors/{sid}/resimulate", data={"days": "30"})
                st.success("Resimulated.")
                st.experimental_rerun()
        uploaded = st.file_uploader("Upload Data CSV", type="csv")
        if uploaded:
            df = pd.read_csv(uploaded)
            api_put(f"/sensors/{sid}", json_payload={"data": df.to_dict("records")})
            st.success("Sensor data updated from CSV.")
            st.experimental_rerun()

# -------------- DASHBOARD ----------------
def dashboard_page():
    st.title("📊 Water Usage Dashboard")
    st.info("Your analytics update every time you visit! 📈")
    sensors = api_get("/sensors")
    if not sensors:
        st.warning("No sensors yet. Add from Sensors tab. ⚠️")
        st.image("https://images.unsplash.com/photo-1464983953574-0892a716854b?auto=format&fit=crop&w=600&q=80", use_column_width=True)
        return
    total = 0
    chart_df = pd.DataFrame()
    for s in sensors:
        if s["data"]:
            usage = [x["usage"] for x in s["data"]]
            total += sum(usage)
            chart_df[s["name"]] = usage
    if not chart_df.empty:
        st.subheader("Usage Trends 📉")
        st.line_chart(chart_df)
        st.metric("💧 Total Water Usage (Liters)", total)
        st.metric("📊 Average Daily Usage (Liters)", round(total / len(chart_df), 2))
        st.subheader("🔥 Sensor Highlights")
        cols = st.columns(len(chart_df.columns))
        for i, name in enumerate(chart_df.columns):
            cols[i].metric(label=name, value=f"{chart_df[name].sum()} L", delta=f"Peak {chart_df[name].max()} L")
        st.subheader("Heatmap")
        st.dataframe(chart_df)
        st.info("All readings are randomly simulated for prototype. ⚡")
    else:
        st.warning("No data yet.")

    st.divider()
    st.subheader("💡 Tips to Reduce Water Usage")
    st.markdown("- Fix leaks immediately 🔧\n- Turn off taps when not needed 🚰\n- Use water-saving fixtures 💧")
    st.success("Check out Water Saving Challenge in the sidebar! 🏆")
    st.markdown(f"**Fun Water Fact:** {random.choice(WATER_FACTS)}")

# --------------- ANALYTICS ----------------
def analytics_page():
    st.title("📈 Analytics & Reports")
    sensors = api_get("/sensors")
    for s in sensors:
        with st.expander(f"{s['name']} ({s['room']})"):
            if s['data']:
                df = pd.DataFrame(s['data'])
                st.line_chart(df.set_index('date')['usage'])
                st.write("Peak Usage:", df['usage'].max())
                st.write("Lowest Usage:", df['usage'].min())
                leak_days = df[df['usage'] > 95]['date'].tolist()
                if leak_days:
                    st.warning(f"Possible leaks on: {', '.join(leak_days)}")
            else:
                st.warning("No data yet.")

    comp_df = pd.DataFrame()
    for s in sensors:
        if s['data']:
            comp_df[s['name']] = [d['usage'] for d in s['data']]
    if not comp_df.empty:
        st.bar_chart(comp_df)
    if sensors and st.button("Download CSV (all)"):
        all_df = pd.concat([pd.DataFrame(s['data']) for s in sensors if s['data']], ignore_index=True)
        st.download_button("Download all sensor data as CSV", all_df.to_csv(index=False), "sensor_data.csv")

# --------------- GAMIFICATION ----------------
def gamification_page():
    st.title("🏅 Achievements & Leaderboard")
    badges_resp = api_get("/badges")
    badges = badges_resp['badges']
    leaderboard = badges_resp['leaderboard']
    st.write("Your Badges:", badges or "No badges yet.")
    st.progress(min(len(badges)/3, 1.0), text=f"{len(badges)} badges earned")
    st.subheader("Leaderboard")
    st.table(leaderboard)
    st.markdown("- Save more water to earn 'Water Saver'\n- Add more sensors for 'Sensor Master'\n- Fix leaks for 'Leak Fixer'")
    if st.button("Check for new badges"):
        st.success(f"Checked! You currently have {len(badges)} badges.")

# --------------- NOTIFICATIONS ----------------
def notifications_page():
    st.title("🔔 Notifications & Alerts")
    notifs = api_get("/notifications")
    for n in notifs:
        st.info(n['msg'])
    if st.button("Send test alert"):
        api_post("/notifications", data={"msg": "Test alert: Water usage update!"})
        st.success("Alert sent.")
    if st.button("Send leak alert"):
        api_post("/notifications", data={"msg": "🚨 Leak detected in one of your sensors!"})
        st.warning("Leak alert sent!")
    if st.button("Clear notifications"):
        api_post("/notifications/clear")
        st.info("Notifications cleared.")

# --------------- COMMUNITY ----------------
def community_page():
    st.title("🌐 Community")
    st.write("Share your achievements (simulated).")
    st.button("Share on social (simulated)")
    leaderboard = api_get("/badges")['leaderboard']
    st.table(leaderboard)
    st.markdown("- Save the most water this week!\n- Fix leaks fastest!\n- Add the most sensors!")

# --------------- SETTINGS ----------------
def settings_page():
    st.title("⚙️ App Settings")
    s = api_get("/settings")
    theme = st.selectbox("Theme", ["Light","Dark"], index=["Light","Dark"].index(s['theme']))
    refresh = st.slider("Sensor refresh interval (mins)", 1, 60, value=int(s['refresh']))
    enable_notif = st.checkbox("Enable notifications", value=bool(s['enable_notif']))
    if st.button("Save Settings"):
        api_post("/settings", data={"theme": theme, "refresh": str(refresh), "enable_notif": str(int(enable_notif))})
        st.success("Settings updated.")
        st.experimental_rerun()

# --------------- DATA ----------------
def data_page():
    st.title("🗂️ Data Management")
    uploaded = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded:
        st.success("File uploaded (demo - attach sensor manually via Sensors).")
    if st.button("Reset all data (simulated)"):
        # reset by deleting sensors
        sensors = api_get("/sensors")
        for s in sensors:
            api_delete(f"/sensors/{s['id']}")
        st.success("All sensor data reset (demo only).")
        st.experimental_rerun()
    if st.button("Download sample data"):
        sample_df = pd.DataFrame({
            "date": pd.date_range(end=pd.Timestamp.today(), periods=10).strftime('%Y-%m-%d'),
            "usage": np.random.randint(10,80,size=10)
        })
        st.download_button("Download sample CSV", sample_df.to_csv(index=False), "sample_sensor.csv")

# --------------- CHALLENGE ----------------
def challenge_page():
    st.title("🏆 Water Saving Challenge")
    checklist = api_get("/checklist")
    changed = False
    for item in checklist:
        val = bool(item['done'])
        new_val = st.checkbox(item['name'], value=val, key=item['name'])
        if new_val != val:
            api_post("/checklist", data={"name": item['name'], "done": str(int(new_val))})
            changed = True
    if changed:
        st.success("Progress updated!")
    completed = sum([int(i['done']) for i in checklist])
    st.progress(completed / len(checklist), text=f"{completed} of {len(checklist)} tips completed")
    if completed == len(checklist):
        st.balloons()
        st.success("Congratulations! You completed the Water Saving Challenge.")

# --------------- HELP ----------------
def help_page():
    st.title("❓ Help & About")
    st.markdown(f"## Welcome to {APP_NAME}!\nBuilt for Hackathon by Team **{TEAM_NAME}**.")
    st.write("- Track water usage\n- Detect leaks\n- Earn badges\n- Export reports")
    for f in WATER_FACTS:
        st.info(f)

# --------------- GAME (smooth + backed) ----------------
def game_page():
    st.title("🎮 Catch the Water Drops!")
    st.markdown("Move your bucket to catch falling drops. Catch 20 drops to win! If you miss more than 10 drops, you lose.")
    state = api_get("/game")
    score = state['score']
    missed = state['missed']
    bucket = state['bucket']
    drop_col = state['drop_col']

    cols = st.columns(3)
    for i, pos in enumerate(["left","middle","right"]):
        drop_here = (drop_col == pos)
        bucket_here = (bucket == pos)
        if drop_here and bucket_here:
            cols[i].markdown("💧💦🪣", unsafe_allow_html=True)
        elif drop_here:
            cols[i].markdown("💧", unsafe_allow_html=True)
        elif bucket_here:
            cols[i].markdown("🪣", unsafe_allow_html=True)
        else:
            cols[i].markdown("&nbsp;", unsafe_allow_html=True)

    st.write(f"🌊 **Caught:** {score}    ❌ **Missed:** {missed}/10")
    if st.session_state["local_game_feedback"]:
        st.info(st.session_state["local_game_feedback"])

    # controls
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("⬅️ Left"):
        api_post("/game/action", json={"action": "move", "bucket": "left"})
        st.experimental_rerun()
    if c2.button("⬆️ Middle"):
        api_post("/game/action", json={"action": "move", "bucket": "middle"})
        st.experimental_rerun()
    if c3.button("➡️ Right"):
        api_post("/game/action", json={"action": "move", "bucket": "right"})
        st.experimental_rerun()
    if c4.button("Catch!"):
        res = api_post("/game/action", json={"action":"catch", "bucket":bucket})
        if res.get("result") == "caught":
            st.session_state["local_game_feedback"] = "💧 You caught the drop!"
        else:
            st.session_state["local_game_feedback"] = "💦 Missed the drop!"
        st.experimental_rerun()

    # win/lose check via state
    state = api_get("/game")
    if state['score'] >= 20:
        st.balloons()
        st.success("🏆 You win! Water saved!")
        api_post("/game/action", json={"action":"reset"})  # reset for next run if desired
    elif state['missed'] > 10:
        st.error("💧 Game over! Too much water wasted.")
        api_post("/game/action", json={"action":"reset"})

# ------------------- MAIN ROUTER -------------------
st.set_page_config(page_title=APP_NAME, layout="wide", initial_sidebar_state="expanded")
with st.sidebar:
    st.image("https://cdn.pixabay.com/photo/2016/04/01/09/24/water-1296123_960_720.png", width=80)
    st.title(APP_NAME)
    st.caption(f"by Team {TEAM_NAME}")
    pages = [
        "🏠 Home", "📊 Dashboard", "🛠️ Sensors", "📈 Analytics", "🏅 Gamification",
        "🔔 Notifications", "🌐 Community", "⚙️ Settings", "🗂️ Data", "🏆 Water Saving Challenge", "🎮 Water Drop Game", "❓ Help"
    ]
    choice = st.radio("Navigate", pages)

page_map = {
    "🏠 Home": lambda: (st.title(f"{APP_NAME} 🚰"), st.write("Smart Water Management for Everyone"), help_page()) if False else None,
    "📊 Dashboard": dashboard_page,
    "🛠️ Sensors": sensors_page,
    "📈 Analytics": analytics_page,
    "🏅 Gamification": gamification_page,
    "🔔 Notifications": notifications_page,
    "🌐 Community": community_page,
    "⚙️ Settings": settings_page,
    "🗂️ Data": data_page,
    "🏆 Water Saving Challenge": challenge_page,
    "🎮 Water Drop Game": game_page,
    "❓ Help": help_page
}

# Home special: render full home layout
if choice == "🏠 Home":
    st.title(f"{APP_NAME} 🚰")
    st.markdown("<div style='text-align:center'><h2>Welcome to WaterSense</h2></div>", unsafe_allow_html=True)
    st.divider()
    st.markdown("### What can you do here?\n- Add sensors\n- Monitor water usage\n- Detect leaks\n- Earn badges")
    st.info(random.choice(WATER_FACTS))
    st.divider()
    st.subheader("Meet Team Pseudocoders")
    cols = st.columns(len(TEAM_MEMBERS))
    for i, member in enumerate(TEAM_MEMBERS):
        cols[i].markdown(f"**{member}**")
else:
    page_map[choice]()
