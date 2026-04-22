"""Player prediction engine — 5-factor deterministic scoring.

Factors used (all normalized 0-100 so weights are comparable):
    1. Batting avg & strike rate        (batsmen only)
    2. Bowling wickets & economy        (bowlers only)
    3. Recent form (last 5 matches)     (both)
    4. Head-to-head record vs opponent  (both, via vs_opponent_avg)
    5. Venue / home advantage           (both, via home_boost)

Hard filters applied BEFORE scoring:
    - active == 1  (retired players excluded)
    - current_team == requested team  (handles player transfers)
"""
import pandas as pd
from pathlib import Path


# Weights — tuned so batting ability dominates for batters, wickets for bowlers,
# but form/H2H/venue still meaningfully shift the ranking.
W_BAT = {
    "skill":  0.35,   # avg + strike_rate blend
    "form":   0.25,
    "h2h":    0.25,
    "venue":  0.15,
}
W_BOWL = {
    "skill":  0.35,   # wickets + 1/economy blend
    "form":   0.25,
    "h2h":    0.25,
    "venue":  0.15,
}


def _norm(series: pd.Series) -> pd.Series:
    """Min-max normalize to 0-100. Constant series -> 50 (neutral)."""
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series([50.0] * len(series), index=series.index)
    return (series - lo) / (hi - lo) * 100.0


def _score_batsmen(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    # skill = avg (weight 0.6) + strike_rate (weight 0.4), each normalized
    skill_raw = 0.6 * _norm(df["avg"]) + 0.4 * _norm(df["strike_rate"])
    form      = _norm(df["recent_form"])
    h2h       = _norm(df["vs_opponent_avg"])
    venue     = _norm(df["home_boost"])
    df["score"] = (
        W_BAT["skill"] * skill_raw
        + W_BAT["form"] * form
        + W_BAT["h2h"] * h2h
        + W_BAT["venue"] * venue
    )
    return df


def _score_bowlers(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    inv_econ = 1.0 / df["economy"].replace(0, 1e-6)
    skill_raw = 0.6 * _norm(df["wickets"]) + 0.4 * _norm(inv_econ)
    form      = _norm(df["recent_form"])
    h2h       = _norm(df["vs_opponent_avg"])
    venue     = _norm(df["home_boost"])
    df["score"] = (
        W_BOWL["skill"] * skill_raw
        + W_BOWL["form"] * form
        + W_BOWL["h2h"] * h2h
        + W_BOWL["venue"] * venue
    )
    return df


def predict_top_players(players_csv: str, team: str, assets_dir: str = None) -> dict:
    """
    Return the 2 best batters + 2 best bowlers for `team`.
    Active-only, current-team filtered, deterministic tie-break on name.
    If assets_dir is provided, only players with an image file in
    assets/players/ are considered (withdrawn/ruled-out players excluded).
    """
    df = pd.read_csv(players_csv)

    # Hard filters
    df = df[df["active"] == 1]
    df = df[df["current_team"].str.upper() == team.upper()]

    # Filter out players without an image (ruled out / withdrawn)
    if assets_dir is not None:
        players_path = Path(assets_dir) / "players"
        def has_image(name):
            fname = name.lower()
            for ch in [" ", ".", "-", "'"]:
                fname = fname.replace(ch, "")
            return (players_path / (fname + ".png")).exists()
        mask = df["name"].apply(has_image)
        excluded = df[~mask]["name"].tolist()
        if excluded:
            print(f"  [info] excluded (no image): {excluded}")
        df = df[mask]

    bats  = df[df["role"].str.lower() == "bat"]
    bowls = df[df["role"].str.lower() == "bowl"]

    bats  = _score_batsmen(bats)
    bowls = _score_bowlers(bowls)

    bats  = bats.sort_values(["score", "name"], ascending=[False, True])
    bowls = bowls.sort_values(["score", "name"], ascending=[False, True])

    # Deduplicate names (all-rounders may appear in both, keep the best slot)
    top_bats_names  = bats["name"].head(2).tolist()
    top_bowls_names = bowls[~bowls["name"].isin(top_bats_names)]["name"].head(2).tolist()

    return {
        "batsmen": top_bats_names,
        "bowlers": top_bowls_names,
        "_debug_bat_scores":  bats[["name", "score"]].head(4).to_dict("records"),
        "_debug_bowl_scores": bowls[["name", "score"]].head(4).to_dict("records"),
    }


if __name__ == "__main__":
    base = Path(__file__).resolve().parent.parent
    csv = str(base / "data" / "players.csv")
    for t in ["RCB", "CSK", "MI", "RR"]:
        r = predict_top_players(csv, t)
        print(f"\n{t}:")
        print(f"  batsmen: {r['batsmen']}")
        print(f"  bowlers: {r['bowlers']}")
        print(f"  top bat scores: {r['_debug_bat_scores']}")
