"""
Pressing Analyst - team pressing metrics vs league reference with wordalisation
(LLM summary + chat).
"""

import streamlit as st

from classes.chat import PressingChat
from classes.data_source import PressingStats
from classes.description import PressingDescription
from classes.visual import DistributionPlot
from utils.page_components import add_common_page_elements
from utils.utils import create_chat, select_team

DETAILED_CSV = "data/pressing/pressing_detailed_metrics.csv"
DETAILED_METRICS = [
    "chains_pm",
    "recovery_opp_half_pm",
    "force_long_ball_pm",
    "press_break_rate_opp_half",
    "lead_to_goal_after_broken_pm",
    "pass_accuracy_under_pressure",
    "line_breaking_pass_rate_under_pressure",
    "ppda",
]
DETAILED_NEGATIVE_METRICS = [
    "ppda",
    "press_break_rate_opp_half",
    "lead_to_goal_after_broken_pm",
    "pass_accuracy_under_pressure",
    "line_breaking_pass_rate_under_pressure",
]

sidebar_container = add_common_page_elements()
st.sidebar.container()
sidebar_container = st.sidebar.container()

st.divider()

detailed_pressing = PressingStats(csv_path=DETAILED_CSV)
df_detailed = detailed_pressing.df.copy()
detailed_metrics = [
    metric for metric in DETAILED_METRICS if metric in detailed_pressing.df.columns
]
if not detailed_metrics:
    st.error("No detailed pressing metric columns found.")
    st.stop()

detailed_negative_metrics = [
    metric for metric in DETAILED_NEGATIVE_METRICS if metric in detailed_metrics
]
detailed_pressing.calculate_statistics(
    metrics=detailed_metrics,
    negative_metrics=detailed_negative_metrics,
)

team = select_team(sidebar_container, detailed_pressing)

st.write(
    "This app can only handle three or four users at a time. Please "
    "[download](https://github.com/soccermatics/twelve-gpt-educational) and run "
    "on your own computer with your own Gemini key."
)

st.expander("Dataframe used", expanded=False).write(detailed_pressing.df)

st.caption(
    "`Opp.` means the metric is describing the opposition. "
    "`Forced` means this team made the opponent do it."
)
st.caption(
    "`PPDA` here is opponent completed passes in the opposition's 60% "
    "divided by this team's meaningful pressure/pressing defensive actions in the "
    "same zone. Lower is better."
)
st.caption(
    "`Opp. Line-Breaking Pass Rate Under Pressure` is the share of opponent "
    "under-pressure pass attempts linked to pressure actions in the opponent's "
    "half that successfully break at least one defensive line. Lower is better."
)
st.caption(
    "`Press Break Rate In Opp. Half` is broken pressing chains divided by total "
    "pressing chains in the opponent's half. Lower is better."
)

to_hash = (team.id, "pressing_analyst_detailed_profile")
chat = create_chat(to_hash, PressingChat, team, detailed_pressing)

if chat.state == "empty":
    n_metrics = len(detailed_metrics)
    visual = DistributionPlot(
        detailed_metrics[::-1],
        labels=["Worse", "Average", "Better"],
        plot_type="wvs",
        plot_height=min(940, 300 + 48 * n_metrics),
    )
    visual.add_title(
        f"{team.name} - Detailed Pressing Profile",
        "Core pressing metrics vs league reference set",
    )
    visual.add_players(detailed_pressing, metrics=detailed_metrics)
    visual.add_player(team, len(detailed_pressing.df), metrics=detailed_metrics)

    description = PressingDescription(team)
    summary = description.stream_gpt(stream=True, temperature=0.3)

    chat.add_message(visual)
    chat.add_message(summary)

    chat.state = "default"
    st.session_state.chat_state = chat.state

chat.get_input()
chat.display_messages()
chat.save_state()
