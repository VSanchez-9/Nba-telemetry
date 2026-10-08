from nba_api.stats.endpoints import leaguegamefinder, boxscoretraditionalv3
from nba_api.stats.static import teams

# 1. Lookup Lakers franchise ID
lakers = teams.find_team_by_abbreviation("LAL")
team_id = lakers["id"]
print(f"Connecting to NBA Stats API for {lakers['full_name']} (ID: {team_id})...")

# 2. Query recent games played by the Lakers
finder = leaguegamefinder.LeagueGameFinder(team_id_nullable=team_id)
games = finder.get_data_frames()[0]

# 3. Pull latest game metadata
latest_game = games.iloc[0]
game_id = latest_game["GAME_ID"]

print("\n" + "=" * 55)
print(f"Matchup: {latest_game['MATCHUP']} | Date: {latest_game['GAME_DATE']}")
print(f"Result:  {latest_game['WL']} ({latest_game['PTS']} PTS)")
print("=" * 55 + "\n")

# 4. Fetch using V3 endpoint
box = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id)
player_stats = box.player_stats.get_data_frame()

# 5. Filter for Lakers players who logged minutes
lakers_stats = player_stats[
    (player_stats["teamId"] == team_id) & (player_stats["minutes"].notnull())
]

# 6. Format and display
columns = ["firstName", "familyName", "minutes", "points", "reboundsTotal", "assists", "plusMinusPoints"]
df_display = lakers_stats[columns].copy()
df_display["PLAYER"] = df_display["firstName"] + " " + df_display["familyName"]

clean_view = df_display[["PLAYER", "minutes", "points", "reboundsTotal", "assists", "plusMinusPoints"]].rename(
    columns={"minutes": "MIN", "points": "PTS", "reboundsTotal": "REB", "assists": "AST", "plusMinusPoints": "+/-"}
)

print(clean_view.to_string(index=False))