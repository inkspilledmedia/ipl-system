"""
IPL Head-to-Head Template Generator — Streamlit Web App
Deploy on Streamlit Cloud or run locally: streamlit run streamlit_app.py
"""
import streamlit as st
import csv
from pathlib import Path
from datetime import date

# Must be first Streamlit command
st.set_page_config(page_title="IPL Template Generator", page_icon="🏏", layout="centered")

BASE = Path(__file__).resolve().parent
MATCHES_CSV = BASE / "data" / "matches.csv"

TEAMS = ["CSK", "MI", "RCB", "KKR", "SRH", "DC", "LSG", "RR", "GT", "PBKS"]
TEAM_FULL = {
    "CSK": "Chennai Super Kings", "MI": "Mumbai Indians",
    "RCB": "Royal Challengers Bengaluru", "KKR": "Kolkata Knight Riders",
    "SRH": "Sunrisers Hyderabad", "DC": "Delhi Capitals",
    "LSG": "Lucknow Super Giants", "RR": "Rajasthan Royals",
    "GT": "Gujarat Titans", "PBKS": "Punjab Kings",
}
VENUES = {
    "CSK": "Chepauk", "MI": "Wankhede", "RCB": "Chinnaswamy",
    "KKR": "Eden Gardens", "SRH": "Rajiv Gandhi Stadium",
    "DC": "Arun Jaitley Stadium", "LSG": "Ekana Stadium",
    "RR": "Sawai Mansingh", "GT": "Narendra Modi Stadium",
    "PBKS": "PCA Mullanpur",
}

# ---- Custom CSS ----
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

    col1, col2 = st.columns(2)
    with col1:
        m_team1 = st.selectbox("Team 1", TEAMS, index=0, key="m_t1",
                                format_func=lambda x: f"{x} — {TEAM_FULL[x]}")
    with col2:
        m_team2 = st.selectbox("Team 2", TEAMS, index=3, key="m_t2",
                                format_func=lambda x: f"{x} — {TEAM_FULL[x]}")

    winner = st.selectbox("Winner", [m_team1, m_team2], key="m_winner")
    venue = st.text_input("Venue", value=VENUES.get(m_team1, ""), key="m_venue")
    match_date = st.date_input("Match Date", value=date.today(), key="m_date")

    if m_team1 == m_team2:
        st.warning("Please select two different teams.")
    elif st.button("➕ Add Match", type="primary", use_container_width=True):
        # Get next match_id
        next_id = 1
        if MATCHES_CSV.exists():
            with open(MATCHES_CSV, "r", encoding="utf-8") as f:
                lines = f.readlines()
                next_id = len(lines)

        with open(MATCHES_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([next_id, "2026", m_team1, m_team2, winner, venue])

        st.success(f"✅ Added: {m_team1} vs {m_team2} → {winner} won at {venue}")

    # Show current match count
    if MATCHES_CSV.exists():
        with open(MATCHES_CSV, "r", encoding="utf-8") as f:
            count = sum(1 for _ in f) - 1
        st.info(f"📊 Currently {count} matches in database")
