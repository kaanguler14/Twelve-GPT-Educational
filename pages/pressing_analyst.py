"""
Pressing Analyst — team pressing metrics vs league reference with wordalisation (LLM summary + chat).
"""

import streamlit as st

from classes.data_source import PressingStats
from classes.visual import DistributionPlot
from classes.chat import PressingChat
from classes.description import PressingDescription
from utils.page_components import add_common_page_elements
from utils.utils import select_team, create_chat

sidebar_container = add_common_page_elements()
st.sidebar.container()
sidebar_container = st.sidebar.container()

st.divider()

pressing = PressingStats()
metrics = PressingStats.metric_columns(pressing.df)
if "Score" in metrics:
    metrics = ["Score"] + [m for m in metrics if m != "Score"]
elif "Z_q" in metrics:
    metrics = ["Z_q"] + [m for m in metrics if m != "Z_q"]
if not metrics:
    st.error("No numeric metric columns found (excluding Team and Label).")
    st.stop()

negative_metrics = PressingStats.negative_metrics_for_columns(metrics)
pressing.calculate_statistics(metrics=metrics, negative_metrics=negative_metrics)

team = select_team(sidebar_container, pressing)

st.write(
    "This app can only handle three or four users at a time. Please [download](https://github.com/soccermatics/twelve-gpt-educational) and run on your own computer with your own Gemini key."
)

st.expander("Dataframe used", expanded=False).write(pressing.df)

to_hash = (team.id, "pressing_analyst")
chat = create_chat(to_hash, PressingChat, team, pressing)

if chat.state == "empty":
    n_metrics = len(metrics)
    visual = DistributionPlot(
        metrics[::-1],
        labels=["Worse", "Average", "Better"],
        plot_type="wvs",
        plot_height=min(940, 300 + 48 * n_metrics),
    )
    visual.add_title_from_player(team)
    visual.add_players(pressing, metrics=metrics)
    visual.add_player(team, len(pressing.df), metrics=metrics)

    description = PressingDescription(team)
    summary = description.stream_gpt(stream=True)

    chat.add_message(
        "Please can you summarise " + team.name + "'s pressing for me?",
        role="user",
        user_only=False,
        visible=False,
    )
    chat.add_message(visual)
    chat.add_message(summary)

    chat.state = "default"

chat.get_input()
chat.display_messages()
chat.save_state()
