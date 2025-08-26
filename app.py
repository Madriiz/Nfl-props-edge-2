
import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="NFL Props Edge — Live (FanDuel/DK)", layout="wide")
st.title("NFL Props Edge — Live (FanDuel/DK)")

st.caption("Uses 2024 Defense-vs-Position ranks (1 = most vulnerable, 32 = strongest). Pulls player props via The Odds API. If FanDuel returns nothing, try DraftKings or broaden markets.")

# --- 2024 DvP ranks (1 = softest, 32 = toughest) ---
DVP = {
    "San Francisco 49ers": {"QB": 26, "RB": 5, "WR": 25, "TE": 26},
    "Chicago Bears": {"QB": 32, "RB": 3, "WR": 30, "TE": 12},
    "Cincinnati Bengals": {"QB": 6, "RB": 14, "WR": 21, "TE": 1},
    "Buffalo Bills": {"QB": 14, "RB": 11, "WR": 16, "TE": 20},
    "Denver Broncos": {"QB": 22, "RB": 24, "WR": 28, "TE": 22},
    "Cleveland Browns": {"QB": 16, "RB": 21, "WR": 2, "TE": 6},
    "Tampa Bay Buccaneers": {"QB": 3, "RB": 27, "WR": 11, "TE": 8},
    "Arizona Cardinals": {"QB": 18, "RB": 9, "WR": 24, "TE": 32},
    "Los Angeles Chargers": {"QB": 19, "RB": 30, "WR": 14, "TE": 28},
    "Kansas City Chiefs": {"QB": 12, "RB": 31, "WR": 17, "TE": 7},
    "Indianapolis Colts": {"QB": 9, "RB": 12, "WR": 13, "TE": 5},
    "Washington Commanders": {"QB": 29, "RB": 10, "WR": 22, "TE": 17},
    "Dallas Cowboys": {"QB": 1, "RB": 13, "WR": 6, "TE": 19},
    "Miami Dolphins": {"QB": 31, "RB": 17, "WR": 31, "TE": 14},
    "Philadelphia Eagles": {"QB": 30, "RB": 32, "WR": 27, "TE": 29},
    "Atlanta Falcons": {"QB": 4, "RB": 23, "WR": 4, "TE": 11},
    "New York Giants": {"QB": 15, "RB": 7, "WR": 18, "TE": 27},
    "Jacksonville Jaguars": {"QB": 5, "RB": 2, "WR": 3, "TE": 9},
    "New York Jets": {"QB": 25, "RB": 20, "WR": 26, "TE": 25},
    "Detroit Lions": {"QB": 8, "RB": 26, "WR": 5, "TE": 31},
    "Green Bay Packers": {"QB": 28, "RB": 18, "WR": 29, "TE": 15},
    "Carolina Panthers": {"QB": 2, "RB": 1, "WR": 10, "TE": 2},
    "New England Patriots": {"QB": 27, "RB": 4, "WR": 20, "TE": 18},
    "Las Vegas Raiders": {"QB": 13, "RB": 15, "WR": 23, "TE": 3},
    "Los Angeles Rams": {"QB": 7, "RB": 19, "WR": 12, "TE": 4},
    "Baltimore Ravens": {"QB": 11, "RB": 29, "WR": 7, "TE": 13},
    "New Orleans Saints": {"QB": 21, "RB": 6, "WR": 8, "TE": 23},
    "Seattle Seahawks": {"QB": 24, "RB": 16, "WR": 15, "TE": 21},
    "Pittsburgh Steelers": {"QB": 23, "RB": 22, "WR": 19, "TE": 10},
    "Houston Texans": {"QB": 10, "RB": 28, "WR": 9, "TE": 16},
    "Tennessee Titans": {"QB": 17, "RB": 8, "WR": 32, "TE": 30},
    "Minnesota Vikings": {"QB": 20, "RB": 25, "WR": 1, "TE": 24},
}

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
SPORT = "americanfootball_nfl"

# Broader market coverage to increase chances of data
DEFAULT_MARKETS = [
    "player_pass_yards",
    "player_pass_attempts",
    "player_pass_completions",
    "player_pass_tds",
    "player_rush_yards",
    "player_rush_attempts",
    "player_receiving_yards",
    "player_receptions",
    "player_longest_reception",
    "player_longest_rush",
    "player_anytime_td"
]

def pos_from_market(m):
    m = m.lower()
    if "pass_" in m: return "QB"
    if "rush_" in m: return "RB"
    if "receiving" in m or "receptions" in m or "longest_reception" in m: return "WR"
    if "anytime_td" in m: return "WR"  # mixed; treat as WR for edge
    return None

def edge_from_rank(rank:int):
    if rank <= 8: return "Over", (9-rank)*10
    if rank >= 25: return "Under", (rank-24)*10
    return "Neutral", 0

# ---- Sidebar settings ----
with st.sidebar:
    st.header("Settings")
    api_key = st.secrets.get("ODDS_API_KEY", "")
    if not api_key:
        api_key = st.text_input("The Odds API key", type="password")
    regions = st.selectbox("Regions", ["us","us,us2"], index=1)
    primary_book = st.selectbox("Primary bookmaker", ["fanduel","draftkings"], index=0)
    secondary_book = st.checkbox("Also fetch DraftKings (fallback)") 
    markets = st.multiselect("Markets to request", DEFAULT_MARKETS, default=DEFAULT_MARKETS)
    diagnostics = st.checkbox("Show diagnostics")

teams = sorted(DVP.keys())
team = st.selectbox("Your offensive team", teams, index=teams.index("Philadelphia Eagles") if "Philadelphia Eagles" in teams else 0)

@st.cache_data(ttl=90)
def fetch_events(api_key, regions):
    url = f"{ODDS_API_BASE}/sports/{SPORT}/odds"
    params = {"apiKey": api_key, "regions": regions, "markets": "h2h", "bookmakers": ",".join(["fanduel","draftkings"]), "oddsFormat":"american"}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=90)
def fetch_props(api_key, event_id, bookmakers, markets, regions):
    url = f"{ODDS_API_BASE}/sports/{SPORT}/events/{event_id}/odds"
    params = {"apiKey": api_key, "regions": regions, "bookmakers": ",".join(bookmakers), "markets": ",".join(markets), "oddsFormat":"american"}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

# ---- Load events ----
if not api_key:
    st.info("Enter your API key in the sidebar.")
    st.stop()

try:
    events = fetch_events(api_key, regions)
except Exception as e:
    st.error(f"Failed to fetch events: {e}")
    if diagnostics:
        st.exception(e)
    st.stop()

# Build list for selection
event_labels = []
auto_idx = 0
for i, ev in enumerate(events):
    home, away = ev.get("home_team",""), ev.get("away_team","")
    label = f"{away} @ {home} — {ev.get('commence_time','')}"
    event_labels.append(label)
    if team in (home, away):
        auto_idx = i

sel = st.selectbox("Upcoming event", event_labels, index=auto_idx)
event = events[event_labels.index(sel)]
home, away = event["home_team"], event["away_team"]
opponent = away if home == team else home

colL, colR = st.columns([1,2], gap="large")

with colL:
    st.subheader("Opponent DvP (2024)")
    opp = pd.DataFrame([DVP.get(opponent, {"QB":"?","RB":"?","WR":"?","TE":"?"})], index=[opponent])
    st.dataframe(opp, use_container_width=True)

with colR:
    st.subheader("Player props & edge")
    books = [primary_book] + (["draftkings"] if (secondary_book and primary_book!="draftkings") else [])
    rows = []
    errors = []
    try:
        data = fetch_props(api_key, event["id"], books, markets, regions)
        for src in data:
            for bm in src.get("bookmakers", []):
                bk = bm.get("key")
                for market in bm.get("markets", []):
                    mkey = market.get("key","")
                    pos = pos_from_market(mkey)
                    rank = DVP.get(opponent, {}).get(pos, 16) if pos else 16
                    lean, edge = edge_from_rank(rank)
                    for out in market.get("outcomes", []):
                        rows.append({
                            "Book": bk,
                            "Market": mkey,
                            "Player": out.get("description") or out.get("name"),
                            "Line": out.get("point"),
                            "Price": out.get("price"),
                            "Position": pos or "?",
                            "Opp DVP Rank": rank if pos else "?",
                            "Lean": lean if pos else "Neutral",
                            "EdgeScore": edge if pos else 0
                        })
    except Exception as e:
        errors.append(str(e))

    if rows:
        df = pd.DataFrame(rows).sort_values(["Book","Market","EdgeScore"], ascending=[True, True, False])
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No player props returned for the chosen combo. Try: (1) adding DraftKings, (2) switching regions to 'us,us2', (3) picking a different event, (4) reducing markets to the core four. On some free keys, props coverage can be limited at certain times.")
        if errors and diagnostics:
            st.write("Errors:", errors)

if diagnostics:
    with st.expander("Diagnostics: raw event JSON"):
        st.write(event)
