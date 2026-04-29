"""
IPL Head-to-Head Template Generator — Streamlit Web App
Player overrides + stadium dropdown + duplicate prevention + GitHub sync.
"""
import streamlit as st
import json
import base64
import requests
from pathlib import Path
from datetime import date

st.set_page_config(page_title="IPL Template Generator", page_icon="🏏", layout="centered")

BASE = Path(__file__).resolve().parent
MATCHES_CSV = BASE / "data" / "matches.csv"
PLAYERS_CSV = BASE / "data" / "players.csv"
CONFIG_FILE = BASE / "config.json"

GITHUB_REPO = "inkspilledmedia/ipl-system"
GITHUB_BRANCH = "main"

TEAMS = ["CSK", "MI", "RCB", "KKR", "SRH", "DC", "LSG", "RR", "GT", "PBKS"]
TEAM_FULL = {
    "CSK": "Chennai Super Kings", "MI": "Mumbai Indians",
    "RCB": "Royal Challengers Bengaluru", "KKR": "Kolkata Knight Riders",
    "SRH": "Sunrisers Hyderabad", "DC": "Delhi Capitals",
    "LSG": "Lucknow Super Giants", "RR": "Rajasthan Royals",
    "GT": "Gujarat Titans", "PBKS": "Punjab Kings",
}

STADIUMS = [
    "MA Chidambaram Stadium, Chennai",
    "Wankhede Stadium, Mumbai",
    "M Chinnaswamy Stadium, Bengaluru",
    "Eden Gardens, Kolkata",
    "Rajiv Gandhi Intl Stadium, Hyderabad",
    "Arun Jaitley Stadium, Delhi",
    "Ekana Cricket Stadium, Lucknow",
    "Sawai Mansingh Stadium, Jaipur",
    "Narendra Modi Stadium, Ahmedabad",
    "PCA New Stadium, Mullanpur",
    "HPCA Stadium, Dharamsala",
    "Barsapara Stadium, Guwahati",
    "ACA-VDCA Stadium, Visakhapatnam",
    "Dr DY Patil Stadium, Mumbai",
    "MCA Stadium, Pune",
]

TEAM_HOME_INDEX = {
    "CSK": 0, "MI": 1, "RCB": 2, "KKR": 3, "SRH": 4,
    "DC": 5, "LSG": 6, "RR": 7, "GT": 8, "PBKS": 9,
}

st.markdown("""
<style>
    .stApp { background-color: #1a1a2e; }
    h1, h2, h3 { color: #f6c428 !important; }
    .stTabs [data-baseweb="tab"] { color: white; font-weight: bold; }
    .stTabs [aria-selected="true"] { color: #f6c428 !important; }
</style>
""", unsafe_allow_html=True)

st.title("🏏 IPL HEAD TO HEAD")
st.caption("Template Generator")


def _get_github_token():
    try:
        return st.secrets["GITHUB_TOKEN"]
    except Exception:
        return None


def _github_get_file(filepath):
    token = _get_github_token()
    if not token:
        return None, None
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filepath}?ref={GITHUB_BRANCH}"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        sha = data["sha"]
        return content, sha
    return None, None


def _github_update_file(filepath, new_content, sha, message):
    token = _get_github_token()
    if not token:
        return False, "GitHub token not configured"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filepath}"
    payload = {
        "message": message,
        "content": base64.b64encode(new_content.encode("utf-8")).decode("utf-8"),
        "sha": sha,
        "branch": GITHUB_BRANCH,
    }
    r = requests.put(url, headers=headers, json=payload)
    if r.status_code == 200:
        return True, "Success"
    return False, r.json().get("message", "Unknown error")


def _normalize_date(date_str):
    date_str = date_str.strip().strip('"')
    if not date_str:
        return ""
    if len(date_str) == 10 and date_str[4] == "-":
        return date_str
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y",
                "%Y/%m/%d", "%d/%m/%y", "%m/%d/%y"):
        try:
            from datetime import datetime
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str


def _check_duplicate(content, team1, team2, match_date):
    """CSV format: match_id,season,team1,team2,winner,venue,date
    Indices: 0=match_id, 1=season, 2=team1, 3=team2, 4=winner, 5=venue, 6=date"""
    target_date = _normalize_date(str(match_date))
    for line in content.strip().split("\n")[1:]:
        parts = line.strip().split(",")
        if len(parts) >= 5:
            csv_t1 = parts[2].strip()
            csv_t2 = parts[3].strip()
            teams_match = (csv_t1 == team1 and csv_t2 == team2) or \
                          (csv_t1 == team2 and csv_t2 == team1)
            csv_date = _normalize_date(parts[6]) if len(parts) >= 7 else ""
            if teams_match and csv_date == target_date:
                return True
    return False


def _get_team_players(team):
    """Get list of players for a team from players.csv."""
    players = {"batsmen": [], "bowlers": []}
    if PLAYERS_CSV.exists():
        import pandas as pd
        df = pd.read_csv(PLAYERS_CSV)
        df = df[df["current_team"].str.upper() == team.upper()]
        df = df[df["active"] == 1]
        for _, row in df.iterrows():
            if row["role"] == "bat":
                players["batsmen"].append(row["name"])
            elif row["role"] == "bowl":
                players["bowlers"].append(row["name"])
    return players


def _save_config(config):
    config_str = json.dumps(config, indent=4)
    CONFIG_FILE.write_text(config_str)
    content, sha = _github_get_file("config.json")
    if sha:
        _github_update_file("config.json", config_str, sha, "Updated player overrides")


# ---- Tabs ----
tab1, tab2 = st.tabs(["⚡ Generate Template", "➕ Add Match Result"])

# ===================== TAB 1: GENERATE =====================
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        team_a = st.selectbox("Team A", TEAMS, index=0,
                               format_func=lambda x: f"{x} — {TEAM_FULL[x]}")
    with col2:
        team_b = st.selectbox("Team B", TEAMS, index=3,
                               format_func=lambda x: f"{x} — {TEAM_FULL[x]}")

    if team_a == team_b:
        st.warning("Please select two different teams.")
    else:
        # Player override section
        with st.expander("🔄 Override Players (optional — click to change predicted players)"):
            st.caption("Leave as 'Auto' to use predicted players. Select a name to override.")

            players_a = _get_team_players(team_a)
            players_b = _get_team_players(team_b)

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**{team_a} Batsmen**")
                ov_a_bat1 = st.selectbox("Batsman 1", ["Auto"] + players_a["batsmen"], key="ov_ab1")
                ov_a_bat2 = st.selectbox("Batsman 2", ["Auto"] + players_a["batsmen"], key="ov_ab2")
                st.markdown(f"**{team_a} Bowlers**")
                ov_a_bowl1 = st.selectbox("Bowler 1", ["Auto"] + players_a["bowlers"], key="ov_aw1")
                ov_a_bowl2 = st.selectbox("Bowler 2", ["Auto"] + players_a["bowlers"], key="ov_aw2")
            with col_b:
                st.markdown(f"**{team_b} Batsmen**")
                ov_b_bat1 = st.selectbox("Batsman 1", ["Auto"] + players_b["batsmen"], key="ov_bb1")
                ov_b_bat2 = st.selectbox("Batsman 2", ["Auto"] + players_b["batsmen"], key="ov_bb2")
                st.markdown(f"**{team_b} Bowlers**")
                ov_b_bowl1 = st.selectbox("Bowler 1", ["Auto"] + players_b["bowlers"], key="ov_bw1")
                ov_b_bowl2 = st.selectbox("Bowler 2", ["Auto"] + players_b["bowlers"], key="ov_bw2")

        if st.button("⚡ GENERATE TEMPLATE", type="primary", use_container_width=True):
            # Build overrides
            match_key = f"{team_a}_vs_{team_b}"
            overrides = {}
            if ov_a_bat1 != "Auto": overrides["teamA_bat1"] = ov_a_bat1
            if ov_a_bat2 != "Auto": overrides["teamA_bat2"] = ov_a_bat2
            if ov_a_bowl1 != "Auto": overrides["teamA_bowl1"] = ov_a_bowl1
            if ov_a_bowl2 != "Auto": overrides["teamA_bowl2"] = ov_a_bowl2
            if ov_b_bat1 != "Auto": overrides["teamB_bat1"] = ov_b_bat1
            if ov_b_bat2 != "Auto": overrides["teamB_bat2"] = ov_b_bat2
            if ov_b_bowl1 != "Auto": overrides["teamB_bowl1"] = ov_b_bowl1
            if ov_b_bowl2 != "Auto": overrides["teamB_bowl2"] = ov_b_bowl2

            # Save to config.json if any overrides
            if overrides:
                try:
                    config = json.loads(CONFIG_FILE.read_text()) if CONFIG_FILE.exists() else {}
                except Exception:
                    config = {}
                if "overrides" not in config:
                    config["overrides"] = {}
                config["overrides"][match_key] = overrides
                _save_config(config)

            with st.spinner(f"Generating {team_a} vs {team_b}..."):
                try:
                    from main import generate
                    output_path = generate(team_a, team_b)
                    output_file = Path(output_path)

                    if output_file.exists():
                        st.success(f"✅ {team_a} vs {team_b} generated!")
                        st.image(str(output_file), use_container_width=True)

                        with open(output_file, "rb") as f:
                            st.download_button(
                                label="📥 Download Image",
                                data=f.read(),
                                file_name=f"{team_a}vs{team_b}.png",
                                mime="image/png",
                                use_container_width=True,
                            )
                    else:
                        st.error("Generation completed but output file not found.")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# ===================== TAB 2: ADD MATCH =====================
with tab2:
    st.subheader("Add Match Result")

    token = _get_github_token()
    if not token:
        st.error("⚠️ GitHub token not configured. Ask admin to add GITHUB_TOKEN in Streamlit secrets.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            m_team1 = st.selectbox("Team 1", TEAMS, index=0, key="m_t1",
                                    format_func=lambda x: f"{x} — {TEAM_FULL[x]}")
        with col2:
            m_team2 = st.selectbox("Team 2", TEAMS, index=3, key="m_t2",
                                    format_func=lambda x: f"{x} — {TEAM_FULL[x]}")

        winner = st.selectbox("Winner", [m_team1, m_team2], key="m_winner")

        default_idx = TEAM_HOME_INDEX.get(m_team1, 0)
        venue = st.selectbox("Stadium", STADIUMS, index=default_idx, key="m_venue")

        match_date = st.date_input("Match Date", value=date.today(), key="m_date")

        if m_team1 == m_team2:
            st.warning("Please select two different teams.")
        elif st.button("➕ Add Match", type="primary", use_container_width=True):
            with st.spinner("Checking for duplicates..."):
                content, sha = _github_get_file("data/matches.csv")
                if content is None:
                    st.error("❌ Could not fetch matches.csv from GitHub.")
                elif _check_duplicate(content, m_team1, m_team2, match_date):
                    st.error(f"⚠️ This match already exists: {m_team1} vs {m_team2} on {match_date}. Entry blocked.")
                else:
                    next_id = len(content.strip().split("\n"))
                    new_row = f"\n{next_id},2026,{m_team1},{m_team2},{winner},{venue},{match_date}"
                    new_content = content.rstrip() + new_row + "\n"

                    success, msg = _github_update_file(
                        "data/matches.csv", new_content, sha,
                        f"Added match: {m_team1} vs {m_team2} - {winner} won at {venue}"
                    )
                    if success:
                        st.success(f"✅ Added: {m_team1} vs {m_team2} → {winner} won at {venue}")
                        st.info("📤 Pushed to GitHub — all teammates will see this update.")
                    else:
                        st.error(f"❌ GitHub push failed: {msg}")

        content, _ = _github_get_file("data/matches.csv")
        if content:
            count = len(content.strip().split("\n")) - 1
            st.info(f"📊 Currently {count} matches in database (synced from GitHub)")
