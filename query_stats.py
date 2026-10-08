import sqlite3
from database import DB_NAME

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

print("\n--- Top Lakers Scorers from Latest Game ---")
query_top_scorers = """
SELECT 
    player_name, 
    minutes, 
    points, 
    rebounds, 
    assists, 
    plus_minus
FROM player_stats
ORDER BY points DESC
LIMIT 5;
"""

cursor.execute(query_top_scorers)
rows = cursor.fetchall()

print(f"{'PLAYER':<25} {'MIN':<8} {'PTS':<5} {'REB':<5} {'AST':<5} {'+/-':<5}")
print("-" * 55)
for row in rows:
    name, mins, pts, reb, ast, pm = row
    print(f"{name:<25} {mins:<8} {pts:<5} {reb:<5} {ast:<5} {pm:<5}")

print("\n--- Team Total Points Aggregation ---")
query_totals = """
SELECT 
    t.full_name,
    g.matchup,
    g.game_date,
    SUM(ps.points) AS calculated_pts,
    g.points AS reported_pts
FROM player_stats ps
JOIN games g ON ps.game_id = g.id
JOIN teams t ON ps.team_id = t.id
GROUP BY ps.game_id, ps.team_id;
"""

cursor.execute(query_totals)
totals = cursor.fetchone()
if totals:
    team_name, matchup, date, calc_pts, rep_pts = totals
    print(f"Team: {team_name}")
    print(f"Matchup: {matchup} ({date})")
    print(f"Sum of Player Points: {calc_pts} | Official Game Points: {rep_pts}")

conn.close()