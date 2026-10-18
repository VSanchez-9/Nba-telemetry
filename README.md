# NBA Fan Hub

A real-time NBA fan page you run on your own computer. Pick your team and see live scores, the latest stories, what fans are saying on Reddit, memes, and box scores, all on one page that keeps itself up to date.

> **Status:** early development, working locally. The 2026-27 regular season starts this week.

---

## Table of contents

1. [Features](#features)
2. [Tech stack](#tech-stack)
3. [Project structure](#project-structure)
4. [Getting started (Windows / PowerShell)](#getting-started-windows--powershell)
5. [How it works](#how-it-works)
6. [API reference](#api-reference)
7. [Database schema](#database-schema)
8. [Data sources](#data-sources)
9. [Known issues and limitations](#known-issues-and-limitations)
10. [Roadmap](#roadmap)
11. [Troubleshooting](#troubleshooting)

---

## Features

| Feature | What it does | Refresh rate |
| --- | --- | --- |
| **Team picker** | Choose any of the 30 NBA teams. The page recolors to that team's colors and remembers your pick next time. | — |
| **Live score strip** | Every game on today's scoreboard. Games in progress are marked **● LIVE** with a red border. | every 30 s |
| **Stories** | The 20 most recent news headlines about your team from the last 3 days. | every 2 min |
| **Fan Talk** | Hot posts from your team's subreddit, plus the top fan comment on the three hottest threads. | every 2 min |
| **Bluesky** | The most-liked public Bluesky posts that mention your team (full name, English) from the last day, with images. Widens to 3 days on quiet days. No login needed. | every 2 min |
| **Memes** | Image posts from r/nbamemes about your team from the past week, sorted by upvotes. | every 2 min |
| **Box Score** | Player stat lines (MIN, PTS, REB, AST, +/-) from the most recent game saved in the local database. | on tab open |

---

## Tech stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| Language | Python 3.10+ | Backend, data ingest, database access |
| Web server | **Flask** | Serves the page and the JSON API |
| HTTP client | `requests` | Calls ESPN, Google News and Reddit |
| NBA stats | `nba_api` | Official NBA Stats endpoints for box scores |
| Data handling | `pandas` | Used by `nba_api` to return DataFrames |
| Database | SQLite (`sqlite3`, standard library) | Stores teams, games and player stats |
| Frontend | Plain HTML, CSS and JavaScript | Single page (`index.html`), no build step |

---

## Project structure

```text
nba-telemetry/
│
├── app.py               # Flask server: serves index.html and all /api/* endpoints
├── index.html           # The fan page (HTML + CSS + JavaScript in one file)
├── database.py          # Creates the SQLite tables and indexes (init_db)
├── lakers_boxscore.py   # Ingest script: saves the Lakers' latest box score to the DB
├── query_stats.py       # Command-line report: top scorers and team point totals
├── requirements.txt     # Python dependencies
├── .env.example         # Template for Reddit API keys (copy to .env)
├── README.md            # This file
├── .gitignore           # Keeps the database, caches and secrets out of Git
└── nba_telemetry.db     # SQLite database (created on first run, not committed)
```

---

## Getting started (Windows / PowerShell)

### 1. Prerequisites

- Python 3.10 or newer (`python --version`)
- Git (optional, for version control)

### 2. Create a virtual environment and install dependencies

```powershell
cd C:\Users\Admin\Projects\nba-telemetry
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> If PowerShell blocks the activate script, run this once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 3. Create the database and load a box score

```powershell
python database.py          # creates the tables (safe to run more than once)
python lakers_boxscore.py   # saves the Lakers' most recent game
python query_stats.py       # optional: print a quick stats report in the terminal
```

### 4. Connect Reddit (for Fan Talk and Memes)

Reddit blocks requests that aren't logged in, so the Fan Talk and Memes tabs need a free Reddit app:

1. Log in to Reddit and go to https://www.reddit.com/prefs/apps
2. Click **create another app**, choose **script**, give it a name, and set the redirect URI to `http://localhost:8080` (not used, but required).
3. Copy `.env.example` to `.env` and fill it in. The client ID is the short string under the app name, and the secret is labeled **secret**.

```powershell
Copy-Item .env.example .env
notepad .env
```

`.env` is in `.gitignore`, so your keys never get committed. Restart the server after editing it.

### 5. Start the server

```powershell
python app.py
```

Open **http://localhost:5000** in your browser. Press `Ctrl + C` in PowerShell to stop the server.

---

## How it works

```text
 Browser (index.html)                      Flask (app.py)                     Outside sources
 ────────────────────                      ──────────────                     ───────────────
 every 30 s  ── GET /api/scores ────────▶  cache 20 s  ── scoreboard ──────▶  ESPN
 every 2 min ── GET /api/news ──────────▶  cache 2 min ── RSS search ──────▶  Google News
             ── GET /api/fans ──────────▶  cache 90 s  ── hot.json ────────▶  Reddit (team sub)
             ── GET /api/memes ─────────▶  cache 3 min ── search.json ─────▶  Reddit (r/nbamemes)
             ── GET /api/buzz ──────────▶  cache 2 min ── searchPosts ─────▶  Bluesky
             ── GET /api/stats ─────────▶  SQL query   ── nba_telemetry.db
                                                              ▲
                                    lakers_boxscore.py ───────┘  (nba_api → NBA Stats)
```

- **Caching:** `app.py` keeps each API response in memory for a short time (the `cached()` helper). Many browser refreshes turn into one request to the outside source, which keeps the page fast and avoids rate limits.
- **Error handling:** every endpoint is wrapped in `safe()`. If an outside source fails, the endpoint returns `{"error": "..."}` with status 502 and the page shows a message for that one section. The rest of the page keeps working.
- **Team colors:** the page sets the CSS variable `--accent` to the selected team's color from ESPN.
- **Saved team:** your team choice is saved in the browser's `localStorage`.
- **Security:** all outside text is HTML-escaped (`esc()` in `index.html`) before it goes on the page.

---

## API reference

All endpoints return JSON.

| Endpoint | Parameters | Returns |
| --- | --- | --- |
| `GET /` | — | The fan page (`index.html`) |
| `GET /api/teams` | — | All 30 teams: `abbr`, `name`, `full`, `color`, `logo`, `sub` (subreddit) |
| `GET /api/scores` | — | Today's games: `status`, `state` (`pre` / `in` / `post`), `home` and `away` (`abbr`, `logo`, `score`) |
| `GET /api/news` | `team` (full name, default `Los Angeles Lakers`) | Up to 20 stories: `title`, `link`, `date`, `source` |
| `GET /api/fans` | `sub` (subreddit, default `lakers`) | Up to 15 posts: `title`, `score`, `comments`, `flair`, `url`, `top_comment` |
| `GET /api/memes` | `team` (short name, default `Lakers`) | Up to 18 image posts: `title`, `img`, `score`, `link` |
| `GET /api/buzz` | `team` (full name, default `Los Angeles Lakers`) | Up to 25 posts: `text`, `date`, `author`, `handle`, `avatar`, `likes`, `reposts`, `replies`, `images` (`thumb`, `full`, `alt`), `url` |
| `GET /api/stats` | `abbr` (NBA abbreviation, default `LAL`) | Latest saved game for that team plus player stat lines |

Example: `http://localhost:5000/api/stats?abbr=LAL`

---

## Database schema

File: `nba_telemetry.db` (SQLite). Created by `database.py`.

**`teams`**

| Column | Type | Notes |
| --- | --- | --- |
| `id` | INTEGER | Primary key (NBA team ID) |
| `abbreviation` | TEXT | Unique, e.g. `LAL` |
| `full_name` | TEXT | e.g. `Los Angeles Lakers` |

**`games`**

| Column | Type | Notes |
| --- | --- | --- |
| `id` | TEXT | Primary key (NBA game ID, e.g. `0012600010`) |
| `game_date` | TEXT | `YYYY-MM-DD` |
| `matchup` | TEXT | e.g. `LAL @ GSW` |
| `wl` | TEXT | `W` or `L` |
| `points` | INTEGER | Team's points |

**`player_stats`**

| Column | Type | Notes |
| --- | --- | --- |
| `id` | INTEGER | Primary key, auto-increment |
| `game_id` | TEXT | Foreign key → `games.id` |
| `team_id` | INTEGER | Foreign key → `teams.id` |
| `player_name` | TEXT | Full name |
| `minutes` | TEXT | `MM:SS` |
| `points`, `rebounds`, `assists` | INTEGER | |
| `plus_minus` | REAL | |

- `UNIQUE(game_id, player_name) ON CONFLICT REPLACE`: re-running the ingest updates rows instead of creating duplicates.
- Indexes on `player_stats(game_id)` and `player_stats(player_name)` speed up lookups.

---

## Data sources

| Source | Used for | Login needed |
| --- | --- | --- |
| ESPN public API (`site.api.espn.com`) | Teams, logos, colors, live scoreboard | No |
| Google News RSS | Team stories | No |
| Reddit API (`oauth.reddit.com`) | Fan posts, top comments, memes | Yes: free app keys in `.env` |
| Bluesky public API (`api.bsky.app`) | Fan posts on the Bluesky tab | No |
| NBA Stats via `nba_api` | Box scores saved to the database | No |

These are free, unofficial endpoints. They can change or rate-limit without notice. This is a personal, non-commercial student project.

---

## Known issues and limitations

- **Box scores are Lakers-only and one game at a time.** `lakers_boxscore.py` only saves the Lakers' most recent game. Other teams show "No box scores saved" on the Box Score tab.
- **Box scores aren't live.** They update only when you run the ingest script.
- **Fan Talk and Memes need Reddit keys.** Without a `.env`, the app falls back to Reddit's public JSON, which is usually blocked (403).
- **The cache is in memory.** It resets whenever the server restarts.
- **`games` is stored from one team's point of view** (`matchup`, `wl` and `points` belong to the team that was ingested).

---

## Roadmap

- [ ] **Favorite players:** follow players and see their recent stat lines and news
- [ ] **All teams, full season:** ingest every game's box score, not just the Lakers' latest
- [ ] **Live box scores:** player stats that update during games
- [ ] **Standings and schedule** for the selected team
- [ ] **Tests** with `pytest` for the API endpoints and database queries
- [ ] **Optional:** a Streamlit or Plotly page for fantasy and consistency analytics

---

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `ModuleNotFoundError: No module named 'flask'` | Activate the virtual environment, then `pip install -r requirements.txt` |
| Page shows "Scores unavailable" | Check your internet connection. ESPN may be briefly down. Scores retry every 30 s. |
| Box Score says "No box scores saved" | Run `python lakers_boxscore.py` (currently Lakers only) |
| `nba_api` times out | NBA Stats is slow sometimes. Wait a minute and try again. |
| Fan Talk / Memes show `403 ... Blocked` | Add Reddit keys to `.env` (see step 4 of Getting started) and restart the server |
| `401 Unauthorized ... access_token` | The Reddit client ID or secret in `.env` is wrong. Copy them again from reddit.com/prefs/apps |
| Port 5000 already in use | Change `port=5000` at the bottom of `app.py` to another number, like `5001` |
