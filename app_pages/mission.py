"""Playable, progressive cryptography challenges."""

from __future__ import annotations

import streamlit as st

from cipher_core import Mission, get_missions, normalize_answer


MISSIONS = get_missions()
st.session_state.setdefault("selected_mission", 0)


def move_to_next_mission() -> None:
    current = int(st.session_state.get("selected_mission", 0))
    furthest = int(st.session_state.get("arcade_unlocked", 0))
    if current < furthest:
        st.session_state["selected_mission"] = current + 1


def answer_is_correct(mission: Mission, guess: str) -> bool:
    if mission.is_multiple_choice:
        return guess == mission.answer
    return normalize_answer(guess) == normalize_answer(mission.answer)


st.title("先破译一条，再学会一招")
st.caption("每关约一分钟。提交答案就能看到解法和原理；答错不扣分，提示会减少通关积分。")

furthest = min(
    max(int(st.session_state.get("arcade_unlocked", 0)), 0),
    len(MISSIONS) - 1,
)
available_levels = list(range(furthest + 1))
if st.session_state.get("selected_mission", 0) not in available_levels:
    st.session_state["selected_mission"] = furthest

selected_index = st.selectbox(
    "选择已解锁的任务",
    options=available_levels,
    format_func=lambda index: f"{index + 1:02d}  ·  {MISSIONS[index].title}",
    key="selected_mission",
    persist_state="session",
)
mission = MISSIONS[selected_index]
completed_ids: list[str] = st.session_state["arcade_completed"]
hinted_ids: list[str] = st.session_state["arcade_hints"]
attempt_counts: dict[str, int] = st.session_state["arcade_attempts"]
solved = mission.id in completed_ids
hint_used = mission.id in hinted_ids
tries = int(attempt_counts.get(mission.id, 0))

left, right = st.columns([1.7, 1], gap="large")
with left:
    with st.container(border=True):
        st.badge(mission.category, icon=":material/key:", color="violet")
        st.subheader(mission.title)
        st.write(mission.story)
        st.caption(mission.prompt)
        st.code(mission.ciphertext, language=None)

        with st.form(f"mission_form_{mission.id}"):
            if mission.is_multiple_choice:
                guess = st.selectbox(
                    "你的判断",
                    options=mission.choices,
                    index=None,
                    placeholder="先想一想，再选答案",
                    key=f"guess_{mission.id}",
                )
            else:
                guess = st.text_input(
                    "输入还原后的明文",
                    placeholder="在这里输入你的答案",
                    key=f"guess_{mission.id}",
                )
            submitted = st.form_submit_button(
                "提交破译",
                type="primary",
                icon=":material/lock_open:",
                disabled=solved,
                width="stretch",
            )

        if submitted and not solved:
            if not guess or not str(guess).strip():
                st.warning("先输入答案，或者选择一个判断。")
            else:
                tries += 1
                attempt_counts[mission.id] = tries
                st.session_state["arcade_attempts"] = attempt_counts
                if answer_is_correct(mission, str(guess)):
                    reward = max(
                        25,
                        mission.points - (tries - 1) * 15 - (25 if hint_used else 0),
                    )
                    completed_ids.append(mission.id)
                    st.session_state["arcade_completed"] = completed_ids
                    st.session_state["arcade_xp"] += reward
                    st.session_state["arcade_streak"] += 1
                    st.session_state["arcade_unlocked"] = max(
                        int(st.session_state["arcade_unlocked"]),
                        min(selected_index + 1, len(MISSIONS) - 1),
                    )
                    solved = True
                    st.toast(f"破译成功，获得 {reward} XP", icon=":material/verified:")
                    st.balloons()
                else:
                    st.session_state["arcade_streak"] = 0
                    st.warning("还差一点。检查位移方向、密钥顺序，或再看一眼提示。")

        if solved:
            reward_note = "这关已经记录在本次行动中。"
            st.success(f"任务完成。{reward_note}", icon=":material/task_alt:")
            st.info(mission.lesson, icon=":material/lightbulb:")
            if selected_index < len(MISSIONS) - 1:
                st.button(
                    "进入下一关",
                    type="primary",
                    icon=":material/arrow_forward:",
                    on_click=move_to_next_mission,
                    width="stretch",
                )
            else:
                st.success("全部行动完成。去工具箱试试真正的加密与解密。")
        else:
            st.caption(f"本关尝试：{tries} 次 · 基础奖励：{mission.points} XP")
            if st.button(
                "给我一个提示",
                icon=":material/lightbulb:",
                disabled=hint_used,
                key=f"hint_button_{mission.id}",
            ):
                if not hint_used:
                    hinted_ids.append(mission.id)
                    st.session_state["arcade_hints"] = hinted_ids
                    hint_used = True
                    st.toast("提示已打开；本关奖励会减少 25 XP。", icon=":material/tips_and_updates:")
            if hint_used:
                st.info(mission.hint, icon=":material/tips_and_updates:")

with right:
    with st.container(border=True):
        st.subheader("怎么玩")
        st.markdown(
            "1. 读任务简报和密文。\n"
            "2. 输入明文，或选择你的判断。\n"
            "3. 提交后看解释，再进入下一关。"
        )
        st.caption("密码学新手也能从第一关开始。答错没有惩罚。")

    with st.container(border=True):
        st.subheader("行动路线")
        for route_index, route_mission in enumerate(MISSIONS):
            if route_mission.id in completed_ids:
                route_status, route_icon, route_color = "已完成", "check_circle", "green"
            elif route_index == selected_index:
                route_status, route_icon, route_color = "正在行动", "play_arrow", "violet"
            elif route_index <= furthest:
                route_status, route_icon, route_color = "已解锁", "radio_button_unchecked", "blue"
            else:
                route_status, route_icon, route_color = "待解锁", "lock", "gray"
            st.badge(
                f"{route_index + 1:02d} · {route_mission.title} · {route_status}",
                icon=f":material/{route_icon}:",
                color=route_color,
            )

    with st.container(border=True):
        st.subheader("本关训练")
        st.markdown(f"**{mission.category}**")
        st.write(
            "原理已解锁；完整解释在左侧任务卡片。"
            if solved
            else "完成任务后，这里会告诉你它对应哪种密码学思路。"
        )
        st.caption(f"进度：{len(completed_ids)} / {len(MISSIONS)} 关")

st.caption("积分、提示和通关记录只留在当前浏览器会话；关闭标签页后会重置。")
