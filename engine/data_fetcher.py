"""Head-to-head stats fetching.

Currently reads from local CSV for full determinism. A web-fetch stub is
included — drop in your API/scraper logic later without touching callers.
"""
import pandas as pd
from pathlib import Path


def fetch_head_to_head(matches_csv: str, team_a: str, team_b: str) -> dict:
    """
    Compute head-to-head stats between two teams.
    Handles reversed team1/team2 positions.
    """
    df = pd.read_csv(matches_csv)
    a, b = team_a.upper(), team_b.upper()
    df["t1"] = df["team1"].str.upper()
    df["t2"] = df["team2"].str.upper()
    df["w"] = df["winner"].str.upper()

    mask = ((df["t1"] == a) & (df["t2"] == b)) | ((df["t1"] == b) & (df["t2"] == a))
    h2h = df[mask]

    return {
        "total_matches": int(len(h2h)),
        "teamA_wins": int((h2h["w"] == a).sum()),
        "teamB_wins": int((h2h["w"] == b).sum()),
    }


def get_venue_for_match(teams_csv: str, team_a: str, team_b: str) -> str:
    """
    Determine the match venue. Convention: team_a is the home side in this
    pipeline, so venue = team_a's home ground. Adjust if your schedule has
    neutral venues.
    """
    df = pd.read_csv(teams_csv)
    row = df[df["team"].str.upper() == team_a.upper()]
    if row.empty:
        return ""
    return str(row.iloc[0]["home_venue"])


# ---------------------------------------------------------------------------
# STUB: plug a live fetcher in here later.
# ---------------------------------------------------------------------------
def fetch_head_to_head_live(team_a: str, team_b: str) -> dict:
    """
    Placeholder for a future Cricbuzz/ESPNCricinfo scraper. Return the same
    dict shape as fetch_head_to_head() so callers don't need changes.
    """
    raise NotImplementedError("Live fetch not enabled — using local CSV.")


if __name__ == "__main__":
    base = Path(__file__).resolve().parent.parent
    print(fetch_head_to_head(str(base / "data" / "matches.csv"), "RCB", "CSK"))
    print(get_venue_for_match(str(base / "data" / "teams.csv"), "RCB", "CSK"))
