"""
Pressing pitch visualisation — matplotlib scatter map of ball regains.

Coordinates are normalised so the pressing team always attacks to the right (+x).
Uses matplotlib for reliable rendering inside Streamlit (st.pyplot).
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Arc, FancyArrowPatch
import streamlit as st

# ── Config ────────────────────────────────────────────────────────────────────
DATASET_PATH = "dataset/dynamic_events_pl_24/_pressing_cache.parquet"

HALF_LEN = 52.5
HALF_WID = 34.0

PRESS_TYPES = ["pressing", "counter_press", "recovery_press"]
PRESS_TYPE_LABELS = {
    "pressing":       "Pressing",
    "counter_press":  "Counter Press",
    "recovery_press": "Recovery Press",
}
PRESS_TYPE_COLORS = {
    "pressing":       "#42a5f5",
    "counter_press":  "#ff7043",
    "recovery_press": "#66bb6a",
}
PRESS_TYPE_MARKERS = {
    "pressing":       "o",
    "counter_press":  "D",
    "recovery_press": "s",
}

OUTCOME_TYPES = ["regain", "disruption"]
OUTCOME_LABELS = {
    "regain":     "Regain",
    "disruption": "Disruption",
}


# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading pressing data…")
def load_pressing_regains() -> pd.DataFrame:
    df = pd.read_parquet(
        DATASET_PATH,
        columns=[
            "match_id", "team_shortname", "event_subtype",
            "pressing_chain_end_type", "pressing_chain_index",
            "index_in_pressing_chain", "pressing_chain_length",
            "x_start", "y_start", "attacking_side",
            "player_name", "third_start",
        ],
    )
    # Keep both regain and disruption outcomes
    has_outcome = df["pressing_chain_end_type"].isin(["regain", "disruption"])
    chains = df[has_outcome].copy()
    last = chains[
        chains["index_in_pressing_chain"] == chains["pressing_chain_length"]
    ].drop_duplicates(subset=["match_id", "pressing_chain_index"], keep="first").copy()

    flip = last["attacking_side"] == "left_to_right"
    last["x_norm"] = np.where(flip, -last["x_start"], last["x_start"])
    last["y_norm"] = np.where(flip, -last["y_start"], last["y_start"])
    return last.reset_index(drop=True)


def get_team_regains(df_all: pd.DataFrame, team_name: str) -> pd.DataFrame:
    return df_all[df_all["team_shortname"] == team_name].copy()


# ── Pitch drawing ─────────────────────────────────────────────────────────────
def _draw_pitch(ax):
    """Draw a full football pitch on the given axes."""
    L, W = HALF_LEN, HALF_WID
    lc = "white"
    lw = 1.5

    # Grass stripes
    band = (2 * L) / 10
    colors = ["#3a8c44", "#348040"]
    for i in range(10):
        x0 = -L + i * band
        ax.add_patch(patches.Rectangle(
            (x0, -W), band, 2 * W,
            facecolor=colors[i % 2], edgecolor="none", zorder=0,
        ))

    # Pitch outline
    ax.plot([-L, L, L, -L, -L], [-W, -W, W, W, -W],
            color=lc, lw=lw, zorder=1)

    # Halfway line
    ax.plot([0, 0], [-W, W], color=lc, lw=lw, zorder=1)

    # Centre circle + spot
    ax.add_patch(plt.Circle((0, 0), 9.15, fill=False,
                             edgecolor=lc, lw=lw, zorder=1))
    ax.add_patch(plt.Circle((0, 0), 0.5, color=lc, zorder=1))

    # ── Right side (attacking / opponent's half) ──────────────────────────
    # Penalty area
    ax.plot([L - 16.5, L - 16.5, L, L, L - 16.5],
            [-20.16, 20.16, 20.16, -20.16, -20.16],
            color=lc, lw=lw, zorder=1)
    # Goal area
    ax.plot([L - 5.5, L - 5.5, L, L, L - 5.5],
            [-9.16, 9.16, 9.16, -9.16, -9.16],
            color=lc, lw=lw, zorder=1)
    # Goal
    ax.plot([L, L + 2, L + 2, L],
            [-3.66, -3.66, 3.66, 3.66],
            color=(1, 1, 1, 0.5), lw=1.2, zorder=1)
    # Penalty spot
    ax.add_patch(plt.Circle((L - 11, 0), 0.4, color=lc, zorder=1))
    # Penalty arc
    ax.add_patch(Arc((L - 11, 0), 2 * 9.15, 2 * 9.15,
                      angle=0, theta1=-53, theta2=53,
                      edgecolor=lc, lw=lw, zorder=1))
    # Corner arcs
    ax.add_patch(Arc((L, -W), 2, 2, angle=0, theta1=90, theta2=180,
                      edgecolor=lc, lw=lw, zorder=1))
    ax.add_patch(Arc((L, W), 2, 2, angle=0, theta1=180, theta2=270,
                      edgecolor=lc, lw=lw, zorder=1))

    # ── Left side (defensive / own half) ──────────────────────────────────
    ax.plot([-L + 16.5, -L + 16.5, -L, -L, -L + 16.5],
            [-20.16, 20.16, 20.16, -20.16, -20.16],
            color=lc, lw=lw, zorder=1)
    ax.plot([-L + 5.5, -L + 5.5, -L, -L, -L + 5.5],
            [-9.16, 9.16, 9.16, -9.16, -9.16],
            color=lc, lw=lw, zorder=1)
    ax.plot([-L, -L - 2, -L - 2, -L],
            [-3.66, -3.66, 3.66, 3.66],
            color=(1, 1, 1, 0.5), lw=1.2, zorder=1)
    ax.add_patch(plt.Circle((-L + 11, 0), 0.4, color=lc, zorder=1))
    ax.add_patch(Arc((-L + 11, 0), 2 * 9.15, 2 * 9.15,
                      angle=0, theta1=127, theta2=233,
                      edgecolor=lc, lw=lw, zorder=1))
    ax.add_patch(Arc((-L, -W), 2, 2, angle=0, theta1=0, theta2=90,
                      edgecolor=lc, lw=lw, zorder=1))
    ax.add_patch(Arc((-L, W), 2, 2, angle=0, theta1=270, theta2=360,
                      edgecolor=lc, lw=lw, zorder=1))

    # Labels
    ax.text(-L / 2, W + 2, "← Own Half",
            ha="center", va="bottom", color="white", fontsize=9, alpha=0.7)
    ax.text(L / 2, W + 2, "Opponent's Half →",
            ha="center", va="bottom", color="white", fontsize=9, alpha=0.95)

    # Attack direction arrow
    ax.annotate("", xy=(L - 2, -W - 3), xytext=(-L + 2, -W - 3),
                arrowprops=dict(arrowstyle="->", color="white", lw=1.2, alpha=0.5))
    ax.text(0, -W - 3, "Attacking direction",
            ha="center", va="center", color="white", fontsize=8, alpha=0.5)

    # Axis limits and styling
    ax.set_xlim(-L - 5, L + 5)
    ax.set_ylim(-W - 6, W + 5)
    ax.set_aspect("equal")
    ax.axis("off")


# ── Main chart function ───────────────────────────────────────────────────────
def plot_pressing_regains(
    df_team: pd.DataFrame,
    team_name: str,
    selected_types: list | None = None,
    selected_outcomes: list | None = None,
    opponent_half_only: bool = True,
) -> tuple[plt.Figure, int]:
    """
    Build a matplotlib pitch figure showing ball regain/disruption locations.
    Returns (fig, n_points_shown).
    """
    if selected_types is None:
        selected_types = PRESS_TYPES
    if selected_outcomes is None:
        selected_outcomes = OUTCOME_TYPES

    df = df_team[
        df_team["event_subtype"].isin(selected_types)
        & df_team["pressing_chain_end_type"].isin(selected_outcomes)
    ].copy()
    if opponent_half_only:
        df = df[df["x_norm"] > 0]

    fig, ax = plt.subplots(figsize=(12, 7.5), facecolor="#1a1a2e")
    _draw_pitch(ax)

    total = 0
    for ptype in selected_types:
        sub = df[df["event_subtype"] == ptype]
        total += len(sub)
        if sub.empty:
            continue
        label = PRESS_TYPE_LABELS.get(ptype, ptype)

        ax.scatter(
            sub["x_norm"], sub["y_norm"],
            c=PRESS_TYPE_COLORS[ptype],
            marker=PRESS_TYPE_MARKERS[ptype],
            s=55,
            alpha=0.8,
            edgecolors="black",
            linewidths=0.5,
            zorder=3,
            label=label,
        )

    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.06),
        ncol=len(selected_types),
        fontsize=10,
        frameon=False,
        labelcolor="white",
        markerscale=1.3,
    )

    plt.tight_layout()
    return fig, total
