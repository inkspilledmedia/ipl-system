"""
IPL Head-to-Head Template Generator — Streamlit Web App
Stadium dropdown + duplicate match prevention + GitHub sync.
"""
import streamlit as st
import base64
import requests
from pathlib import Path
from datetime import date

st.set_page_config(page_title="IPL Template Generator", page_icon="🏏", layout="centered")

BASE = Path(__file__).resolve().parent
MATCHES_CSV = BASE / "data" / "matches.csv"

GITHUB_REPO = "inkspilledmedia/ipl-system"
GITHUB_FILE = "data/matches.csv"
GITHUB_BRANCH = "main"

TEAMS = ["CSK", "MI", "RCB", "KKR", "SRH", "DC", "LSG", "RR", "GT", "PBKS"]
TEAM_FULL = {
    "CSK": "Chennai Super Kings", "MI": "Mumbai Indians",
    "RCB": "Royal Challengers Bengaluru", "KKR": "Kolkata Knight Riders",
    "SRH": "Sunrisers Hyderabad", "DC": "Delhi Capitals",
    "LSG": "Lucknow Super Giants", "RR": "Rajasthan Royals",
    "GT": "Gujarat Titans", "PBKS": "Punjab Kings",
}

# All IPL stadiums — team home grounds listed first
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

# Map team to their default home stadium index in STADIUMS list
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


def _github_get_file():
    token = _get_github_token()
    if not token:
        return None, None
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}?ref={GITHUB_BRANCH}"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        sha = data["sha"]
        return content, sha
    return None, None


def _github_update_file(new_content, sha, message):
    token = _get_github_token()
    if not token:
        return False, "GitHub token not configured"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
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


def _check_duplicate(content, team1, team2, match_date):
    """Check if a match between these teams on this date already exists.
    CSV format: match_id,season,team1,team2,winner,venue,date
    Date is column index 6 (if present)."""
    date_str = str(match_date)
    for line in content.strip().split("\n")[1:]:  # skip header
        parts = line.strip().split(",")
        if len(parts) >= 6:
            csv_t1 = parts[2].strip()
            csv_t2 = parts[3].strip()
            teams_match = (csv_t1 == team1 and csv_t2 == team2) or \
                          (csv_t1 == team2 and csv_t2 == team1)
            # Check date in column 6 if it exists
            csv_date = parts[6].strip() if len(parts) >= 7 else ""
            if teams_match and csv_date == date_str:
                return True
    return False


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
        if st.button("⚡ GENERATE TEMPLATE", type="primary", use_container_width=True):
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

        # Stadium dropdown — auto-selects Team 1 home ground
        default_idx = TEAM_HOME_INDEX.get(m_team1, 0)
        venue = st.selectbox("Stadium", STADIUMS, index=default_idx, key="m_venue")

        match_date = st.date_input("Match Date", value=date.today(), key="m_date")

        if m_team1 == m_team2:
            st.warning("Please select two different teams.")
        elif st.button("➕ Add Match", type="primary", use_container_width=True):
            with st.spinner("Checking for duplicates..."):
                content, sha = _github_get_file()
                if content is None:
                    st.error("❌ Could not fetch matches.csv from GitHub.")
                elif _check_duplicate(content, m_team1, m_team2, match_date):
                    st.error(f"⚠️ This match already exists: {m_team1} vs {m_team2} on {match_date}. Entry blocked.")
                else:
                    lines = content.strip().split("\n")
                    next_id = len(lines)

                    new_row = f"\n{next_id},2026,{m_team1},{m_team2},{winner},{venue},{match_date}"
                    new_content = content.rstrip() + new_row + "\n"

                    success, msg = _github_update_file(
                        new_content, sha,
                        f"Added match: {m_team1} vs {m_team2} - {winner} won at {venue}"
                    )
                    if success:
                        st.success(f"✅ Added: {m_team1} vs {m_team2} → {winner} won at {venue}")
                        st.info("📤 Pushed to GitHub — all teammates will see this update.")
                    else:
                        st.error(f"❌ GitHub push failed: {msg}")

        # Show current match count
        content, _ = _github_get_file()
        if content:
            count = len(content.strip().split("\n")) - 1
            st.info(f"📊 Currently {count} matches in database (synced from GitHub)")
