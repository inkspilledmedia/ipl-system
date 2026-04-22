"""IPL Match Template Generator — main pipeline.

Usage: python main.py RCB CSK
"""
import sys
import json
from pathlib import Path

from engine.data_fetcher import fetch_head_to_head, get_venue_for_match
from engine.predictor import predict_top_players
from engine.renderer import render_template

BASE = Path(__file__).resolve().parent
TEMPLATE    = BASE / "templates" / "base_template.png"
MATCHES_CSV = BASE / "data" / "matches.csv"
PLAYERS_CSV = BASE / "data" / "players.csv"
TEAMS_CSV   = BASE / "data" / "teams.csv"
ASSETS_DIR  = BASE / "assets"
OUTPUT_DIR  = BASE / "output"
CONFIG_FILE = BASE / "config.json"


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception as e:
            print(f"  [warn] config.json parse error: {e}")
    return {}


def generate(team_a: str, team_b: str) -> str:
    team_a, team_b = team_a.upper(), team_b.upper()
    config = _load_config()

    match_key = f"{team_a}_vs_{team_b}"
    overrides = config.get("overrides", {}).get(match_key, {})
    font_overrides = config.get("font_sizes", {})

    print(f"[1/4] Head-to-head: {team_a} vs {team_b}")
    stats = fetch_head_to_head(str(MATCHES_CSV), team_a, team_b)
    venue = get_venue_for_match(str(TEAMS_CSV), team_a, team_b)

    for key in ["total_matches", "teamA_wins", "teamB_wins"]:
        val = overrides.get(key)
        if val is not None:
            stats[key] = val
            print(f"      [override] {key} = {val}")
    print(f"      {stats}  venue={venue}")

    print(f"[2/4] Predicting top players")
    players_a = predict_top_players(str(PLAYERS_CSV), team_a, str(ASSETS_DIR))
    players_b = predict_top_players(str(PLAYERS_CSV), team_b, str(ASSETS_DIR))

    for role, key_a, key_b in [
        ("batsmen", "teamA_bat", "teamB_bat"),
        ("bowlers", "teamA_bowl", "teamB_bowl"),
    ]:
        for i in range(2):
            val_a = overrides.get(f"{key_a}{i+1}")
            if val_a is not None:
                if i < len(players_a[role]):
                    players_a[role][i] = val_a
                else:
                    players_a[role].append(val_a)
                print(f"      [override] {key_a}{i+1} = {val_a}")
            val_b = overrides.get(f"{key_b}{i+1}")
            if val_b is not None:
                if i < len(players_b[role]):
                    players_b[role][i] = val_b
                else:
                    players_b[role].append(val_b)
                print(f"      [override] {key_b}{i+1} = {val_b}")

    print(f"      {team_a} bat:  {players_a['batsmen']}")
    print(f"      {team_a} bowl: {players_a['bowlers']}")
    print(f"      {team_b} bat:  {players_b['batsmen']}")
    print(f"      {team_b} bowl: {players_b['bowlers']}")

    print(f"[3/4] Rendering template")
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"{team_a}vs{team_b}.png"
    render_template(
        template_path=str(TEMPLATE),
        output_path=str(out_path),
        team_a=team_a,
        team_b=team_b,
        stats=stats,
        team_a_players=players_a,
        team_b_players=players_b,
        assets_dir=str(ASSETS_DIR),
        font_overrides=font_overrides,
    )
    print(f"[4/4] Saved: {out_path}")
    return str(out_path)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python main.py <TeamA> <TeamB>")
        sys.exit(1)
    generate(sys.argv[1], sys.argv[2])
