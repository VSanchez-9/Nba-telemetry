import sqlite3
from nba_api.stats.endpoints import leaguegamefinder, boxscoretraditionalv3
from nba_api.stats.static import teams
from database import DB_NAME, init_db

# Ensure tables exist
init_db()

# 1. Lookup Lakers franchise metadata
lakers = teams.find_team_by_abbreviation("LAL")
team_id = lakers["id"]

# 2. Query recent games
finder = leaguegamefinder.LeagueGameFinder(team_id_nullable=team_id)
games = finder.get_data_frames()[0]
latest_game = games.iloc[0]
game_id = latest_game["GAME_ID"]

print(f"\nProcessing Game: {latest_game['MATCHUP']} ({latest_game['GAME_DATE']})")

# 3. Fetch Boxscore
box = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id)
player_stats = box.player_stats.get_data_frame()

# Filter active players who logged minutes
lakers_stats = player_stats[
    (player_stats["teamId"] == team_id) & (player_stats["minutes"].str.len() > 0)
].copy()

# 4. Persist to SQLite Database
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Insert/Update Team
cursor.execute("""
INSERT OR IGNORE INTO teams (id, abbreviation, full_name)
VALUES (?, ?, ?)
""", (team_id, lakers["abbreviation"], lakers["full_name"]))

# Insert/Update Game
cursor.execute("""
INSERT OR REPLACE INTO games (id, game_date, matchup, wl, points)
VALUES (?, ?, ?, ?, ?)
""", (game_id, latest_game["GAME_DATE"], latest_game["MATCHUP"], latest_game["WL"], int(latest_game["PTS"])))

# Insert Player Rows
for _, row in lakers_stats.iterrows():
    player_full_name = f"{row['firstName']} {row['familyName']}"
    cursor.execute("""
    INSERT INTO player_stats (game_id, team_id, player_name, minutes, points, rebounds, assists, plus_minus)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        game_id,
        team_id,
        player_full_name,
        row["minutes"],
        int(row["points"]),
        int(row["reboundsTotal"]),
        int(row["assists"]),
        float(row["plusMinusPoints"]) if row["plusMinusPoints"] is not None else 0.0
    ))

conn.commit()
conn.close()

print(f"[DB] Successfully inserted {len(lakers_stats)} player records for game {game_id} into SQLite.")