import streamlit as st
import json
import os
import random
import time
from datetime import datetime
import plotly.graph_objects as go
import pandas as pd

# ====================== CONFIG ======================
CONFIG = {
    "storage_file": "spins_history.json",
    "max_history": 200,
    "analysis_window": 30,
    "wheel_order": [
        19, 1, 8, 15, 4,
        11, 18, 7, 14, 3,
        10, 17, 6, 13, 2,
        9, 16, 5, 12
    ],
    "colors": {
        "Red": "#ff4757",
        "Black": "#2f3542",
        "Grey": "#747d8c",
        "Yellow": "#f39c12"
    },
    "number_map": {
        1:  {"color": "Black",  "parity": "Odd"},
        2:  {"color": "Grey",   "parity": "Even"},
        3:  {"color": "Red",    "parity": "Odd"},
        4:  {"color": "Black",  "parity": "Even"},
        5:  {"color": "Grey",   "parity": "Odd"},
        6:  {"color": "Red",    "parity": "Even"},
        7:  {"color": "Black",  "parity": "Odd"},
        8:  {"color": "Grey",   "parity": "Even"},
        9:  {"color": "Red",    "parity": "Odd"},
        10: {"color": "Black",  "parity": "Even"},
        11: {"color": "Grey",   "parity": "Odd"},
        12: {"color": "Red",    "parity": "Even"},
        13: {"color": "Black",  "parity": "Odd"},
        14: {"color": "Grey",   "parity": "Even"},
        15: {"color": "Red",    "parity": "Odd"},
        16: {"color": "Black",  "parity": "Even"},
        17: {"color": "Grey",   "parity": "Odd"},
        18: {"color": "Red",    "parity": "Even"},
        19: {"color": "Yellow", "parity": "Odd"}
    }
}

SEED_NUMBERS = [
    4, 4, 2, 12, 11, 11, 9, 3, 4, 7,
    2, 14, 6, 14, 8, 3, 3, 13, 13, 9,
    17, 17, 11, 18, 2, 14, 16, 7, 9, 13
]

def create_spin(number: int) -> dict:
    info = CONFIG["number_map"][number]
    return {
        "number": number,
        "color": info["color"],
        "parity": info["parity"],
        "timestamp": datetime.now().isoformat()
    }

def load_data() -> list:
    if os.path.exists(CONFIG["storage_file"]):
        try:
            with open(CONFIG["storage_file"], "r") as f:
                data = json.load(f)
                if isinstance(data, list) and data:
                    return data
        except Exception:
            pass
    return [create_spin(n) for n in SEED_NUMBERS]

def save_data(spins: list):
    try:
        with open(CONFIG["storage_file"], "w") as f:
            json.dump(spins[:CONFIG["max_history"]], f, indent=2)
    except Exception:
        pass

def get_range(number: int) -> str:
    if 1 <= number <= 6: return "1-6"
    if 7 <= number <= 12: return "7-12"
    if 13 <= number <= 18: return "13-18"
    return "19"

def get_market(number: int) -> str:
    if number == 19: return "Jackpot"
    return "Under 9.5" if number <= 9 else "Over 9.5"

def number_counts(history: list) -> dict:
    counts = {i: 0 for i in range(1, 20)}
    for spin in history:
        counts[spin["number"]] += 1
    return counts

def get_neighbours(number: int, distance: int = 2) -> list:
    order = CONFIG["wheel_order"]
    try:
        idx = order.index(number)
    except ValueError:
        return []
    neighbours = []
    for offset in range(1, distance + 1):
        neighbours.append(order[(idx + offset) % len(order)])
        neighbours.append(order[(idx - offset) % len(order)])
    return list(set(neighbours))

def calculate_hot_cold(history: list):
    window = history[:CONFIG["analysis_window"]]
    counts = number_counts(window)
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    hot = [item for item in sorted_counts if item[1] > 0][:3]
    cold = [item for item in sorted_counts if item[1] == 0][:3]
    return {"counts": counts, "hot": hot, "cold": cold, "window_size": len(window)}

def calculate_repeat_stats(history: list):
    if len(history) < 2:
        return {"repeat_count": 0, "repeat_rate": 0.0, "longest_repeat": 0}
    repeats = 0
    longest = 1
    current = 1
    for i in range(1, len(history)):
        if history[i]["number"] == history[i-1]["number"]:
            repeats += 1
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    rate = (repeats / (len(history) - 1)) * 100
    return {"repeat_count": repeats, "repeat_rate": rate, "longest_repeat": longest}

def calculate_markets(history: list):
    eligible = [s for s in history if s["number"] != 19]
    odd = sum(1 for s in eligible if s["parity"] == "Odd")
    even = sum(1 for s in eligible if s["parity"] == "Even")
    under = sum(1 for s in eligible if s["number"] <= 9)
    over = sum(1 for s in eligible if s["number"] >= 10)
    return {"odd": odd, "even": even, "under": under, "over": over, "eligible": len(eligible)}

def calculate_colours(history: list):
    return {
        "Red": sum(1 for s in history if s["color"] == "Red"),
        "Black": sum(1 for s in history if s["color"] == "Black"),
        "Grey": sum(1 for s in history if s["color"] == "Grey"),
        "Yellow": sum(1 for s in history if s["color"] == "Yellow")
    }

def calculate_ranges(history: list):
    result = {"1-6": 0, "7-12": 0, "13-18": 0, "19": 0}
    for spin in history:
        result[get_range(spin["number"])] += 1
    return result

def calculate_signal(history: list):
    if len(history) < 5:
        return {
            "number": None,
            "strength": "NEUTRAL",
            "score": 0,
            "factors": {
                "frequency": "--", "recency": "--", "neighbour": "--",
                "colour": "--", "parity": "--", "market": "--"
            }
        }

    recent = history[:30]
    counts = number_counts(recent)
    scores = {i: 0 for i in range(1, 20)}

    for num in range(1, 20):
        scores[num] += counts[num] * 2
        try:
            recency_idx = next(i for i, s in enumerate(recent) if s["number"] == num)
            scores[num] += max(0, 8 - recency_idx)
        except StopIteration:
            pass

        if history:
            last = history[0]["number"]
            if num in get_neighbours(last, 2):
                scores[num] += 4

    best_number = max(scores, key=scores.get)
    best_score = scores[best_number]
    info = CONFIG["number_map"][best_number]

    agreement = 0
    if counts[best_number] > 0: agreement += 1
    if best_number in get_neighbours(history[0]["number"], 2): agreement += 1

    strength = "NEUTRAL"
    if agreement >= 2: strength = "MODERATE"
    if agreement >= 3 or best_score > 15: strength = "STRONG"

    return {
        "number": best_number,
        "strength": strength,
        "score": best_score,
        "factors": {
            "frequency": f"{counts[best_number]} hits",
            "recency": "Recent" if counts[best_number] > 0 else "Not recent",
            "neighbour": "Wheel neighbour" if best_number in get_neighbours(history[0]["number"], 2) else "No adjacency",
            "colour": info["color"],
            "parity": info["parity"],
            "market": get_market(best_number)
        }
    }

def draw_wheel():
    order = CONFIG["wheel_order"]
    n = len(order)
    theta = [i * (360 / n) for i in range(n)]
    width = [360 / n] * n
    colors = [CONFIG["colors"][CONFIG["number_map"][num]["color"]] for num in order]
    text = [str(num) for num in order]

    fig = go.Figure(go.Barpolar(
        r=[1] * n,
        theta=theta,
        width=width,
        marker_color=colors,
        marker_line_color="white",
        marker_line_width=1.5,
        opacity=0.95,
        text=text,
        hoverinfo="text"
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=False, range=[0, 1.15]),
            angularaxis=dict(visible=False)
        ),
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
        height=400,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig

# ====================== APP ======================
st.set_page_config(page_title="Wheel of Fortune Analytics Matrix", layout="wide", page_icon="🎡")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #fafafa; }
</style>
""", unsafe_allow_html=True)

if "spins" not in st.session_state:
    st.session_state.spins = load_data()

spins = st.session_state.spins

st.title("🎡 Wheel of Fortune • Analytics Matrix")

col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
with col_h2:
    if st.button("↩️ Undo Last", use_container_width=True):
        if spins:
            spins.pop(0)
            st.session_state.spins = spins
            save_data(spins)
            st.rerun()
with col_h3:
    if st.button("🗑️ Reset Session", use_container_width=True):
        st.session_state.spins = []
        save_data([])
        st.rerun()

left, center, right = st.columns([1.15, 1.25, 1.15])

with left:
    st.subheader("Live Wheel")
    st.plotly_chart(draw_wheel(), use_container_width=True)

    if spins:
        last = spins[0]
        st.markdown(f"### Last Result: **{last['number']}**")
    else:
        st.markdown("### Last Result: --")

    st.markdown("---")
    st.markdown("#### Manual Input")
    with st.form("add_form", clear_on_submit=True):
        number = st.number_input("Number (1-19)", min_value=1, max_value=19, step=1, value=1)
        submitted = st.form_submit_button("➕ Add Spin", use_container_width=True)
        if submitted:
            spins.insert(0, create_spin(int(number)))
            st.session_state.spins = spins[:CONFIG["max_history"]]
            save_data(st.session_state.spins)
            st.rerun()

    if st.button("🎲 Simulate Random Spin", use_container_width=True, type="primary"):
        random_num = random.choice(CONFIG["wheel_order"])
        spins.insert(0, create_spin(random_num))
        st.session_state.spins = spins[:CONFIG["max_history"]]
        save_data(st.session_state.spins)
        st.rerun()

    st.markdown("#### Recent Stream")
    if spins:
        recent = " → ".join([str(s["number"]) for s in spins[:15]])
        st.code(recent)
    else:
        st.info("No spins recorded yet")

with center:
    st.subheader("Number Matrix")
    hot_cold = calculate_hot_cold(spins)
    counts = hot_cold["counts"]

    cols = st.columns(5)
    for i, num in enumerate(range(1, 20)):
        with cols[i % 5]:
            count = counts.get(num, 0)
            if st.button(f"**{num}**\n{count} hits", key=f"n{num}", use_container_width=True):
                spins.insert(0, create_spin(num))
                st.session_state.spins = spins[:CONFIG["max_history"]]
                save_data(st.session_state.spins)
                st.rerun()

    st.markdown("---")
    st.subheader("Statistical Signal Engine")
    signal = calculate_signal(spins)

    if signal["number"]:
        st.metric("Recommended Number", signal["number"], signal["strength"])
        info = CONFIG["number_map"][signal["number"]]
        st.write(f"**{info['color']}** • **{info['parity']}** • **{get_range(signal['number'])}**")
        st.caption(f"Score: {signal['score']}")
        with st.expander("Signal Factors"):
            st.json(signal["factors"])
    else:
        st.info("Need at least 5 spins to generate a signal")

with right:
    st.subheader("Market & Metrics")

    markets = calculate_markets(spins)
    total = markets["eligible"] or 1

    st.markdown("**Parity**")
    st.progress(markets["odd"] / total, text=f"Odd  {markets['odd']}  ({markets['odd']/total*100:.1f}%)")
    st.progress(markets["even"] / total, text=f"Even  {markets['even']}  ({markets['even']/total*100:.1f}%)")

    st.markdown("**Under / Over 9.5**")
    st.progress(markets["under"] / total, text=f"Under  {markets['under']}  ({markets['under']/total*100:.1f}%)")
    st.progress(markets["over"] / total, text=f"Over  {markets['over']}  ({markets['over']/total*100:.1f}%)")

    st.markdown("**Colours**")
    colours = calculate_colours(spins)
    st.write(f"🔴 Red: **{colours['Red']}**   ⚫ Black: **{colours['Black']}**")
    st.write(f"⚪ Grey: **{colours['Grey']}**   🟡 Yellow: **{colours['Yellow']}**")

    st.markdown("**Ranges**")
    ranges = calculate_ranges(spins)
    total_spins = len(spins) or 1
    r1, r2 = st.columns(2)
    r1.metric("1-6", f"{ranges['1-6']/total_spins*100:.1f}%")
    r2.metric("7-12", f"{ranges['7-12']/total_spins*100:.1f}%")
    r1.metric("13-18", f"{ranges['13-18']/total_spins*100:.1f}%")
    r2.metric("Jackpot 19", f"{ranges['19']/total_spins*100:.1f}%")

    st.markdown("**Session Summary**")
    repeat = calculate_repeat_stats(spins)
    st.write(f"Total Spins: **{len(spins)}**")
    st.write(f"Unique Numbers: **{len(set(s['number'] for s in spins))}**")
    st.write(f"Repeat Rate: **{repeat['repeat_rate']:.1f}%**")
    st.write(f"Longest Streak: **{repeat['longest_repeat']}**")

    if hot_cold["hot"]:
        st.success(f"Hottest: **{hot_cold['hot'][0][0]}** ({hot_cold['hot'][0][1]} hits)")
    if hot_cold["cold"]:
        st.warning(f"Coldest: **{hot_cold['cold'][0][0]}**")

st.markdown("---")
st.subheader("Pattern Intelligence")

if spins:
    last = spins[0]
    neighbours = get_neighbours(last["number"], 2)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Last Hit", last["number"])
    c2.metric("Neighbours", ", ".join(map(str, neighbours[:4])))
    c3.metric("Repeat?", "YES" if len(spins) > 1 and spins[0]["number"] == spins[1]["number"] else "NO")

    streak = 1
    for i in range(1, len(spins)):
        if spins[i]["parity"] == last["parity"]:
            streak += 1
        else:
            break
    c4.metric("Parity Streak", f"{streak} × {last['parity']}")

    st.info(f"Wheel neighbours of **{last['number']}**: {', '.join(map(str, neighbours))}")
else:
    st.write("No data yet.")

if spins:
    df = pd.DataFrame(spins)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Export History to CSV",
        data=csv,
        file_name="wheel_spins_history.csv",
        mime="text/csv",
        use_container_width=True
    )
