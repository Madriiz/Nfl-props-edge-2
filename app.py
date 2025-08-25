
import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="NFL Props Edge — FanDuel (Live)", layout="wide")
st.title("NFL Props Edge — FanDuel (Live)")

st.caption("Uses 2024 Defense-vs-Position ranks (1 = most vulnerable, 32 = strongest). Pulls FanDuel props via The Odds API.")

DVP = {"San Francisco 49ers": {"QB": 26, "RB": 5, "WR": 25, "TE": 26}, "Chicago Bears": {"QB": 32, "RB": 3, "WR": 30, "TE": 12}, "Cincinnati Bengals": {"QB": 6, "RB": 14, "WR": 21, "TE": 1}, "Buffalo Bills": {"QB": 14, "RB": 11, "WR": 16, "TE": 20}, "Denver Broncos": {"QB": 22, "RB": 24, "WR": 28, "TE": 22}, "Cleveland Browns": {"QB": 16, "RB": 21, "WR": 2, "TE": 6}, "Tampa Bay Buccaneers": {"QB": 3, "RB": 27, "WR": 11, "TE": 8}, "Arizona Cardinals": {"QB": 18, "RB": 9, "WR": 24, "TE": 32}, "Los Angeles Chargers": {"QB": 19, "RB": 30, "WR": 14, "TE": 28}, "Kansas City Chiefs": {"QB": 12, "RB": 31, "WR": 17, "TE": 7}, "Indianapolis Colts": {"QB": 9, "RB": 12, "WR": 13, "TE": 5}, "Washington Commanders": {"QB": 29, "RB": 10, "WR": 22, "TE": 17}, "Dallas Cowboys": {"QB": 1, "RB": 13, "WR": 6, "TE": 19}, "Miami Dolphins": {"QB": 31, "RB": 17, "WR": 31, "TE": 14}, "Philadelphia Eagles": {"QB": 30, "RB": 32, "WR": 27, "TE": 29}, "Atlanta Falcons": {"QB": 4, "RB": 23, "WR": 4, "TE": 11}, "New York Giants": {"QB": 15, "RB": 7, "WR": 18, "TE": 27}, "Jacksonville Jaguars": {"QB": 5, "RB": 2, "WR": 3, "TE": 9}, "New York Jets": {"QB": 25, "RB": 20, "WR": 26, "TE": 25}, "Detroit Lions": {"QB": 8, "RB": 26, "WR": 5, "TE": 31}, "Green Bay Packers": {"QB": 28, "RB": 18, "WR": 29, "TE": 15}, "Carolina Panthers": {"QB": 2, "RB": 1, "WR": 10, "TE": 2}, "New England Patriots": {"QB": 27, "RB": 4, "WR": 20, "TE": 18}, "Las Vegas Raiders": {"QB": 13, "RB": 15, "WR": 23, "TE": 3}, "Los Angeles Rams": {"QB": 7, "RB": 19, "WR": 12, "TE": 4}, "Baltimore Ravens": {"QB": 11, "RB": 29, "WR": 7, "TE": 13}, "New Orleans Saints": {"QB": 21, "RB": 6, "WR": 8, "TE": 23}, "Seattle Seahawks": {"QB": 24, "RB": 16, "WR": 15, "TE": 21}, "Pittsburgh Steelers": {"QB": 23, "RB": 22, "WR": 19, "TE": 10}, "Houston Texans": {"QB": 10, "RB": 28, "WR": 9, "TE": 16}, "Tennessee Titans": {"QB": 17, "RB": 8, "WR": 32, "TE": 30}, "Minnesota Vikings": {"QB": 20, "RB": 25, "WR": 1, "TE": 24}}

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
SPORT = "americanfootball_nfl"

# Prefer Streamlit secret, else text box
api_key = st.secrets.get("ODDS_API_KEY", "")
if not api_key:
    api_key = st.text_input("Enter your The Odds API key", type="password")

teams = sorted(DVP.keys())
team = st.selectbox("Select your offensive team", teams, index=teams.index("Philadelphia Eagles") if "Philadelphia Eagles" in teams else 0)

def edge_from_rank(rank):
    if rank <= 8:
        return "Over", round((9 - rank) * 10, 1)
    if rank >= 25:
        return "Under", round((rank - 24) * 10, 1)
    return "Neutral", 0.0

def pos_from_market(m):
    m = m.lower()
    if "player_pass_yards" in m:
        return "QB"
    if "player_rush_yards" in m:
        return "RB"
    if "player_receiving_yards" in m or "player_rec_yards" in m:
        return "WR"  # receiving yards default to WR
    if "player_receptions" in m:
        return "WR"
    return None

@st.cache_data(ttl=120)
def fetch_events(api_key):
    url = f"{ODDS_API_BASE}/sports/{SPORT}/odds"
    params = { "apiKey": api_key, "regions": "us", "bookmakers": "fanduel", "markets": "h2h" }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=120)
def fetch_event_props(api_key, event_id):
    markets = ",".join(["player_pass_yards","player_rush_yards","player_receiving_yards","player_receptions"])
    url = f"{ODDS_API_BASE}/sports/{SPORT}/events/{event_id}/odds"
    params = { "apiKey": api_key, "regions": "us", "bookmakers": "fanduel", "markets": markets }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

colL, colR = st.columns([1,2], gap="large")

with colL:
    st.subheader("Opponent Defensive Ranks (2024)")
    if not api_key:
      st.info("Enter your API key to fetch the next opponent and FanDuel props.")
    else:
      try:
        events = fetch_events(api_key)
        # Find next event for selected team
        this_event = None
        for ev in events:
            if team in (ev.get("home_team",""), ev.get("away_team","")):
                this_event = ev
                break
        if not this_event:
            st.warning("No upcoming event found for this team from the API.")
        else:
            home, away = this_event["home_team"], this_event["away_team"]
            opponent = away if home == team else home
            st.write(f"**Next game:** {away} at {home}")
            st.write(f"**Opponent:** {opponent}")
            opp_ranks = pd.DataFrame([DVP.get(opponent, {'QB':'?', 'RB':'?', 'WR':'?', 'TE':'?'})], index=[opponent])
            st.dataframe(opp_ranks, use_container_width=True)
      except Exception as e:
        st.error(f"Failed to fetch events: {e}")

with colR:
    st.subheader("FanDuel Player Props & Edge")
    if api_key:
      try:
        if not locals().get("this_event"):
            events = fetch_events(api_key)
            for ev in events:
                if team in (ev.get("home_team",""), ev.get("away_team","")):
                    this_event = ev
                    break
        if locals().get("this_event"):
            opponent = this_event["away_team"] if this_event["home_team"] == team else this_event["home_team"]
            opp_dvp = DVP.get(opponent, None)
            if not opp_dvp:
                st.warning("Opponent not in DVP table; using neutral matchup.")
            props = fetch_event_props(api_key, this_event["id"])
            rows = []
            for book in props:
                for bm in book.get("bookmakers", []):
                    if bm.get("key") != "fanduel":
                        continue
                    for market in bm.get("markets", []):
                        pos = pos_from_market(market.get("key",""))
                        if not pos:
                            continue
                        rank = opp_dvp[pos] if opp_dvp else 16
                        lean, edge = edge_from_rank(rank)
                        for out in market.get("outcomes", []):
                            name = out.get("description") or out.get("name")
                            line = out.get("point")
                            price = out.get("price")
                            rows.append({
                                "Player": name,
                                "Market": market["key"],
                                "Line": line,
                                "Price": price,
                                "Position": pos,
                                "Opp DVP Rank": rank,
                                "Lean": lean,
                                "EdgeScore": edge
                            })
            if rows:
                df = pd.DataFrame(rows).sort_values(["EdgeScore","Position"], ascending=[False, True])
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No props returned for the selected markets yet.")
      except Exception as e:
        st.error(f"Error while fetching props: {e}")

st.divider()
st.markdown("**Notes**")
st.markdown("- EdgeScore is matchup-only (based on opponent DVP rank). Consider blending in projections for true EV.")
st.markdown("- Receiving props default to WR. I can add TE detection if you want TE-specific receiving edges.")
