import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="NFL Props Edge — FanDuel (Live)", layout="wide")
st.title("NFL Props Edge — FanDuel (Live)")

st.caption("Uses 2024 Defense-vs-Position ranks (1 = most vulnerable, 32 = strongest). Pulls player props via The Odds API. If FanDuel is empty on your plan, try DraftKings fallback.")

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

# --- Config panel ---
with st.sidebar:
    st.header("Settings")
    api_key = st.secrets.get("ODDS_API_KEY", "")
    if not api_key:
        api_key = st.text_input("The Odds API Key", type="password")
    regions = st.selectbox("Regions", ["us", "us,us2"], index=0)
    books = st.multiselect("Bookmakers (first is primary)", ["fanduel","draftkings"], default=["fanduel","draftkings"])
    show_diag = st.checkbox("Show diagnostics (raw JSON/errors)")

teams = sorted(DVP.keys())
team = st.selectbox("Your offensive team", teams, index=teams.index("Philadelphia Eagles") if "Philadelphia Eagles" in teams else 0)

def edge_from_rank(rank:int):
    if rank <= 8: return "Over", (9-rank)*10
    if rank >= 25: return "Under", (rank-24)*10
    return "Neutral", 0

def fetch_events(api_key, regions):
    url = f"{ODDS_API_BASE}/sports/{SPORT}/odds"
    params = {"apiKey": api_key, "regions": regions, "bookmakers": ",".join(["fanduel","draftkings"]), "markets": "h2h", "oddsFormat":"american"}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def fetch_event_props(api_key, event_id, bookmaker):
    markets = "player_pass_yards,player_rush_yards,player_receiving_yards,player_receptions"
    url = f"{ODDS_API_BASE}/sports/{SPORT}/events/{event_id}/odds"
    params = {"apiKey": api_key, "regions": regions, "bookmakers": bookmaker, "markets": markets, "oddsFormat":"american"}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

# --- Left: opponent ranks and event selector ---
colL, colR = st.columns([1,2], gap="large")

with colL:
    st.subheader("Opponent & DvP (2024)")
    if not api_key:
        st.info("Enter your The Odds API key to load events.")
        st.stop()
    try:
        events = fetch_events(api_key, regions)
    except Exception as e:
        st.error(f"Failed to fetch events: {e}")
        if show_diag:
            st.exception(e)
        st.stop()

    # auto-pick event; also provide a manual select
    idx_auto = None
    event_options = []
    for i, ev in enumerate(events):
        home, away = ev.get("home_team",""), ev.get("away_team","")
        event_options.append(f"{away} @ {home} — {ev.get('commence_time','')}")
        if team in (home, away):
            idx_auto = i
    sel = st.selectbox("Upcoming event", event_options, index=idx_auto if idx_auto is not None else 0)
    event = events[event_options.index(sel)]
    home, away = event["home_team"], event["away_team"]
    opponent = away if home == team else home

    st.write(f"**Selected game:** {away} @ {home}")
    st.write(f"**Opponent:** {opponent}")
    opp = pd.DataFrame([DVP.get(opponent, {"QB":"?","RB":"?","WR":"?","TE":"?"})], index=[opponent])
    st.dataframe(opp, use_container_width=True)

# --- Right: FanDuel props with DraftKings fallback ---
with colR:
    st.subheader("Player Props & Edge")
    rows = []
    errors = []

    for bk in books:
        try:
            props = fetch_event_props(api_key, event["id"], bk)
        except Exception as e:
            errors.append(f"{bk}: {e}")
            continue

        for src in props:
            for bm in src.get("bookmakers", []):
                if bm.get("key") != bk: 
                    continue
                for market in bm.get("markets", []):
                    mkey = market.get("key","").lower()
                    if "player_" not in mkey: 
                        continue
                    pos = "QB" if "pass_yards" in mkey else "RB" if "rush_yards" in mkey else "WR"
                    rank = DVP.get(opponent, {}).get(pos, 16)
                    lean, edge = edge_from_rank(rank)
                    for out in market.get("outcomes", []):
                        name = out.get("description") or out.get("name")
                        rows.append({
                            "Book": bk,
                            "Player": name,
                            "Market": mkey,
                            "Line": out.get("point"),
                            "Price": out.get("price"),
                            "Position": pos,
                            "Opp DVP Rank": rank,
                            "Lean": lean,
                            "EdgeScore": edge
                        })

    if rows:
        df = pd.DataFrame(rows).sort_values(["Book","EdgeScore","Position"], ascending=[True,False,True])
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No player props returned. This usually means your plan/coverage doesn't include props for this book/market yet.")
        if errors and show_diag:
            st.write("Errors:", errors)

    if show_diag:
        with st.expander("Diagnostics: raw events JSON"):
            st.write(events)
