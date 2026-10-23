"""Cipher Arcade: a small game room for learning and using cryptography."""

from __future__ import annotations

import streamlit as st

from cipher_core import get_missions


MISSIONS = get_missions()

st.set_page_config(
    page_title="密码局 · Cipher Arcade",
    page_icon=":material/sports_esports:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.session_state.setdefault("arcade_xp", 0)
st.session_state.setdefault("arcade_unlocked", 0)
st.session_state.setdefault("arcade_completed", [])
st.session_state.setdefault("arcade_attempts", {})
st.session_state.setdefault("arcade_hints", [])
st.session_state.setdefault("arcade_streak", 0)


def reset_campaign() -> None:
    st.session_state["arcade_xp"] = 0
    st.session_state["arcade_unlocked"] = 0
    st.session_state["arcade_completed"] = []
    st.session_state["arcade_attempts"] = {}
    st.session_state["arcade_hints"] = []
    st.session_state["arcade_streak"] = 0
    st.session_state["selected_mission"] = 0
    for mission in MISSIONS:
        st.session_state.pop(f"guess_{mission.id}", None)


pages = [
    st.Page(
        "app_pages/mission.py",
        title="开始闯关",
        icon=":material/sports_esports:",
        default=True,
    ),
    st.Page(
        "app_pages/tools.py",
        title="密码工具",
        icon=":material/handyman:",
    ),
    st.Page(
        "app_pages/lab.py",
        title="视觉实验室",
        icon=":material/science:",
    ),
]

page = st.navigation(pages, position="top")
page.run()

score = int(st.session_state["arcade_xp"])
completed = len(st.session_state["arcade_completed"])
progress = completed / len(MISSIONS)
if score >= 700:
    rank = "密码局王牌"
elif score >= 400:
    rank = "密钥猎手"
elif score >= 150:
    rank = "见习译码员"
else:
    rank = "新来的译码员"

with st.sidebar:
    st.title("密码局")
    st.caption("CIPHER ARCADE · 本次会话")
    st.metric("行动积分", f"{score} XP")
    st.badge(rank, icon=":material/military_tech:", color="violet")
    st.progress(progress, text=f"已通关 {completed} / {len(MISSIONS)} 关")
    st.caption(f"当前连胜：{st.session_state['arcade_streak']}")
    st.button(
        "重开本次行动",
        icon=":material/restart_alt:",
        on_click=reset_campaign,
        help="清除本次浏览器会话里的关卡积分。",
        width="stretch",
    )
    st.caption("关卡进度只保存在当前浏览器会话中。")
