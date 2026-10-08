import sqlite3

DB_NAME = "nba_telemetry.db"

def init_db():
    """Initializes the database schema with relational constraints and indexes."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Teams Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY,
        abbreviation TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL
    );
    """)

    # 2. Games Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS games (
        id TEXT PRIMARY KEY,
        game_date TEXT NOT NULL,
        matchup TEXT NOT NULL,
        wl TEXT,
        points INTEGER
    );
    """)

    # 3. Player Stats Table (Child table with foreign keys)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS player_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id TEXT NOT NULL,
        team_id INTEGER NOT NULL,
        player_name TEXT NOT NULL,
        minutes TEXT,
        points INTEGER,
        rebounds INTEGER,
        assists INTEGER,
        plus_minus REAL,
        FOREIGN KEY (game_id) REFERENCES games (id),
        FOREIGN KEY (team_id) REFERENCES teams (id),
        UNIQUE(game_id, player_name) ON CONFLICT REPLACE
    );
    """)

    # 4. Performance Indexes (speeds up lookups on common query filters)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_player_stats_game ON player_stats(game_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_player_stats_name ON player_stats(player_name);")

    conn.commit()
    conn.close()
    print("[DB] Initialized SQLite tables with composite unique constraints and indexes.")

if __name__ == "__main__":
    init_db()