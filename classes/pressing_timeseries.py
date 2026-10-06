"""
Per-match and intra-match pressing aggregates derived from the dynamic events
pressing cache. Powers the season trend and intra-match tools in PressingChat.

The cache (`_pressing_cache.parquet`) holds one row per dynamic event with a
`pressing_chain` flag. We deduplicate to one row per (match, team, chain) and
aggregate to either the per-match level (season trend) or the per-bucket level
(intra-match, default 5-minute windows).

The raw cache is large and licensed, so it is not part of the repo. The small
aggregate tables are exported to `data/pressing/timeseries/` (run
`python -m classes.pressing_timeseries`) and read from there when present;
the raw cache is only needed to regenerate them.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from settings import PRESSING_DATASET_PATH

AGGREGATES_DIR = Path("data/pressing/timeseries")


# Metric → (display label, "higher is better"). All metrics are computed
# from pressing chains that START in the opposition half (middle or attacking
# third) — this matches the high-press lens used by the rest of the project.
METRIC_DEFS = {
    "chains": ("Pressing Chains In Opp. Half", True),
    "regains": ("Regains In Opp. Half", True),
    "regain_rate": ("Regain Rate (Opp. Half)", True),
    "chain_length_avg": ("Avg Chain Length (Opp. Half)", True),
    "lead_to_shot_count": ("Press → Shot (Opp. Half)", True),
}


@st.cache_data(show_spinner="Loading pressing cache…")
def _load_chain_starts(dataset_path: str) -> pd.DataFrame:
    """One row per (match, team, pressing chain) with the columns we need."""
    cache_path = Path(dataset_path) / "_pressing_cache.parquet"
    df = pd.read_parquet(
        cache_path,
        columns=[
            "match_id",
            "team_shortname",
            "pressing_chain",
            "pressing_chain_index",
            "pressing_chain_length",
            "pressing_chain_end_type",
            "lead_to_shot",
            "minute_start",
            "period",
            "third_start",
        ],
    )
    chains = df[df["pressing_chain"] == True]  # noqa: E712 — pandas wants ==
    starts = chains.drop_duplicates(
        subset=["match_id", "team_shortname", "pressing_chain_index"], keep="first"
    ).copy()
    return starts


@st.cache_data(show_spinner=False)
def _load_match_meta(dataset_path: str) -> pd.DataFrame:
    """match_id → date, home/away short names."""
    meta = pd.read_parquet(Path(dataset_path) / "matches.parquet")
    rows = []
    for _, r in meta.iterrows():
        home = r["home_team"].get("short_name") if isinstance(r["home_team"], dict) else None
        away = r["away_team"].get("short_name") if isinstance(r["away_team"], dict) else None
        rows.append(
            {
                "match_id": r["id"],
                "date": pd.to_datetime(r["date_time"]).tz_localize(None),
                "home": home,
                "away": away,
            }
        )
    return pd.DataFrame(rows)


@st.cache_data(show_spinner="Aggregating per-match pressing metrics…")
def _per_match_aggregate(dataset_path: str) -> pd.DataFrame:
    """One row per (match, team) with the proxy metrics + composite z-score.

    All metrics are scoped to chains that start in the opposition half
    (middle or attacking third) — high-press lens.
    """
    starts = _load_chain_starts(dataset_path)
    opp = starts[starts["third_start"].isin(["middle_third", "attacking_third"])]

    agg = opp.groupby(["match_id", "team_shortname"], as_index=False).agg(
        chains=("pressing_chain_index", "count"),
        chain_length_avg=("pressing_chain_length", "mean"),
        regains=("pressing_chain_end_type", lambda s: (s == "regain").sum()),
        lead_to_shot_count=("lead_to_shot", lambda s: s.fillna(False).astype(bool).sum()),
    )
    agg["regain_rate"] = agg["regains"] / agg["chains"].clip(lower=1)

    # Standardise each metric across the whole season pool, then build composite.
    for metric, (_, higher_is_better) in METRIC_DEFS.items():
        col = agg[metric].astype(float)
        std = col.std()
        z = (col - col.mean()) / std if std > 0 else col * 0.0
        if not higher_is_better:
            z = -z
        agg[metric + "_Z"] = z

    z_cols = [m + "_Z" for m in METRIC_DEFS]
    agg["composite_Z"] = agg[z_cols].mean(axis=1)

    meta = _load_match_meta(dataset_path)
    agg = agg.merge(meta, on="match_id", how="left")
    agg["opponent"] = np.where(
        agg["team_shortname"] == agg["home"], agg["away"], agg["home"]
    )
    agg = agg.sort_values(["team_shortname", "date"]).reset_index(drop=True)
    return agg


@st.cache_data(show_spinner=False)
def _intra_match_buckets(dataset_path: str, bucket_min: int = 5) -> pd.DataFrame:
    """One row per (match, team, bucket) with chain count in that window.

    Restricted to chains starting in the opposition half (high-press lens),
    consistent with the per-match aggregate.
    """
    starts = _load_chain_starts(dataset_path)
    s = starts[
        starts["third_start"].isin(["middle_third", "attacking_third"])
    ].copy()
    # `minute_start` in this dataset is already cumulative across periods
    # (Period 1 ≈ 0–45, Period 2 ≈ 46–95+) — no offset needed.
    s["bucket"] = (s["minute_start"] // bucket_min) * bucket_min

    buckets = s.groupby(
        ["match_id", "team_shortname", "bucket"], as_index=False
    ).agg(
        chains=("pressing_chain_index", "count"),
        regains=("pressing_chain_end_type", lambda x: (x == "regain").sum()),
        chain_length_avg=("pressing_chain_length", "mean"),
        lead_to_shot=("lead_to_shot", lambda x: x.fillna(False).astype(bool).sum()),
    )
    return buckets


@st.cache_data(show_spinner=False)
def _half_counts(dataset_path: str) -> pd.DataFrame:
    """One row per (match, team, period) with the opp-half chain count."""
    starts = _load_chain_starts(dataset_path)
    s = starts[starts["third_start"].isin(["middle_third", "attacking_third"])]
    return s.groupby(["match_id", "team_shortname", "period"], as_index=False).agg(
        chains=("pressing_chain_index", "count")
    )


_BUILDERS = {
    "per_match": _per_match_aggregate,
    "intra": _intra_match_buckets,
    "halves": _half_counts,
    "matches": _load_match_meta,
}


@st.cache_data(show_spinner=False)
def _load_table(name: str, dataset_path: str) -> pd.DataFrame:
    """Exported aggregate if present, otherwise built from the raw cache."""
    path = AGGREGATES_DIR / f"{name}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return _BUILDERS[name](dataset_path)


def export_aggregates(dataset_path: str = PRESSING_DATASET_PATH, out_dir: Path = AGGREGATES_DIR):
    """Build every aggregate from the raw cache and write it to out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, build in _BUILDERS.items():
        df = build(dataset_path)
        df.to_parquet(out_dir / f"{name}.parquet", index=False)
        print(f"{name}: {len(df)} rows")


class PressingTimeSeries:
    """
    Thin façade over the cached per-match and intra-match aggregates. All heavy
    work is cached at module level via `st.cache_data` so instantiation is cheap.
    """

    def __init__(self, dataset_path: str = PRESSING_DATASET_PATH):
        self.dataset_path = dataset_path

    def _per_match(self) -> pd.DataFrame:
        return _load_table("per_match", self.dataset_path)

    def _intra(self) -> pd.DataFrame:
        return _load_table("intra", self.dataset_path)

    def half_split(self, team_name: str, match_id: int) -> tuple:
        """
        (first_half, second_half) opp-half chain counts, split by `period`.
        Minute buckets can't do this: first-half stoppage time runs past
        minute 45 and would otherwise be counted in the second half.
        """
        halves = _load_table("halves", self.dataset_path)
        sub = halves[
            (halves["match_id"] == match_id) & (halves["team_shortname"] == team_name)
        ].set_index("period")["chains"]
        return int(sub.get(1, 0)), int(sub.get(2, 0))

    def available_teams(self) -> list:
        return sorted(self._per_match()["team_shortname"].unique().tolist())

    def scheduled_match_count(self, team_name: str) -> int:
        """Matches the team played per matches.parquet, including any missing from the cache."""
        meta = _load_table("matches", self.dataset_path)
        return int(((meta["home"] == team_name) | (meta["away"] == team_name)).sum())

    def latest_match_id(self, team_name: str):
        df = self._per_match()
        team_df = df[df["team_shortname"] == team_name]
        if team_df.empty:
            return None
        return int(team_df.sort_values("date").iloc[-1]["match_id"])

    def season_trend(self, team_name: str, metric: str = None) -> pd.DataFrame:
        """
        Returns a DataFrame ordered by match date with columns:
            match_id, date, opponent, value, value_z
        """
        df = self._per_match()
        team_df = df[df["team_shortname"] == team_name].copy()
        if team_df.empty:
            return pd.DataFrame(columns=["match_id", "date", "opponent", "value", "value_z"])

        if metric is None:
            out = team_df[["match_id", "date", "opponent", "composite_Z"]].copy()
            out["value"] = out["composite_Z"]
            out["value_z"] = out["composite_Z"]
            out = out.drop(columns=["composite_Z"])
        else:
            if metric not in METRIC_DEFS:
                raise ValueError(
                    f"Unknown metric '{metric}'. Allowed: {list(METRIC_DEFS.keys())}"
                )
            z_col = metric + "_Z"
            out = team_df[["match_id", "date", "opponent", metric, z_col]].rename(
                columns={metric: "value", z_col: "value_z"}
            )
        return out.reset_index(drop=True)

    def intra_match(
        self, team_name: str, match_id: int = None, metric: str = "chains"
    ) -> pd.DataFrame:
        """
        Returns a DataFrame with columns: bucket (minute), value.
        `metric` is one of: chains, regains, chain_length_avg, lead_to_shot.
        Defaults to `chains` (most stable signal at 5-minute resolution).
        """
        if match_id is None:
            match_id = self.latest_match_id(team_name)
        if match_id is None:
            return pd.DataFrame(columns=["bucket", "value"])

        df = self._intra()
        sub = df[(df["match_id"] == match_id) & (df["team_shortname"] == team_name)]
        if sub.empty:
            return pd.DataFrame(columns=["bucket", "value"])

        if metric not in {"chains", "regains", "chain_length_avg", "lead_to_shot"}:
            raise ValueError(f"Unknown intra-match metric '{metric}'")

        return sub[["bucket", metric]].rename(columns={metric: "value"}).reset_index(drop=True)

    def match_label(self, team_name: str, match_id: int) -> str:
        """Returns 'YYYY-MM-DD vs Opponent' for the given match."""
        df = self._per_match()
        row = df[(df["match_id"] == match_id) & (df["team_shortname"] == team_name)]
        if row.empty:
            return f"match {match_id}"
        r = row.iloc[0]
        return f"{r['date'].strftime('%Y-%m-%d')} vs {r['opponent']}"


if __name__ == "__main__":
    export_aggregates()
