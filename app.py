import os, sqlite3, time, requests
import xml.etree.ElementTree as ET
from flask import Flask, jsonify, request, send_file
from database import DB_NAME, init_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load KEY=value lines from .env (kept out of Git) without overriding real env vars
_env = os.path.join(BASE_DIR, ".env")
if os.path.exists(_env):
    for line in open(_env, encoding="utf-8"):
        k, sep, v = line.strip().partition("=")
        if sep and not k.startswith("#"):
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))

app = Flask(__name__)
REDDIT_ID, REDDIT_SECRET = os.environ.get("REDDIT_CLIENT_ID"), os.environ.get("REDDIT_CLIENT_SECRET")
HDRS = {"User-Agent": f"windows:nba-fan-hub:0.1 (by /u/{os.environ.get('REDDIT_USERNAME', 'unknown')})"}
ESPN = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"

# ESPN abbreviation -> team subreddit
SUBS = {
    "ATL": "atlantahawks", "BOS": "bostonceltics", "BKN": "GoNets", "CHA": "CharlotteHornets",
    "CHI": "chicagobulls", "CLE": "clevelandcavs", "DAL": "mavericks", "DEN": "denvernuggets",
    "DET": "DetroitPistons", "GS": "warriors", "HOU": "rockets", "IND": "pacers",
    "LAC": "LAClippers", "LAL": "lakers", "MEM": "memphisgrizzlies", "MIA": "heat",
    "MIL": "mkebucks", "MIN": "timberwolves", "NO": "NOLAPelicans", "NY": "nyknicks",
    "OKC": "Thunder", "ORL": "orlandomagic", "PHI": "sixers", "PHX": "suns",
    "POR": "ripcity", "SAC": "kings", "SA": "nbaspurs", "TOR": "torontoraptors",
    "UTAH": "utahjazz", "WSH": "washingtonwizards",
}

_cache = {}
def cached(key, ttl, fn):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    data = fn()
    _cache[key] = (time.time(), data)
    return data

def fetch(url, headers=HDRS, **kw):
    r = requests.get(url, headers=headers, timeout=10, **kw)
    r.raise_for_status()
    return r

_token = {"value": None, "expires": 0}
def reddit(path, **params):
    """GET a Reddit listing. Uses OAuth when .env has credentials, else the public (often blocked) JSON."""
    if not (REDDIT_ID and REDDIT_SECRET):
        return fetch(f"https://www.reddit.com{path}.json", params=params).json()
    if time.time() > _token["expires"] - 60:
        r = requests.post("https://www.reddit.com/api/v1/access_token", auth=(REDDIT_ID, REDDIT_SECRET),
                          data={"grant_type": "client_credentials"}, headers=HDRS, timeout=10)
        r.raise_for_status()
        t = r.json()
        if "access_token" not in t:
            raise RuntimeError(f"Reddit login failed: {t}")
        _token.update(value=t["access_token"], expires=time.time() + t.get("expires_in", 3600))
    return fetch(f"https://oauth.reddit.com{path}", params={**params, "raw_json": 1},
                 headers={**HDRS, "Authorization": f"Bearer {_token['value']}"}).json()

def safe(fn):
    try:
        return jsonify(fn())
    except Exception as e:
        return jsonify({"error": str(e)}), 502

@app.route("/")
def index():
    return send_file(os.path.join(BASE_DIR, "index.html"))

@app.route("/api/teams")
def teams():
    def go():
        d = fetch(f"{ESPN}/teams").json()
        out = []
        for t in d["sports"][0]["leagues"][0]["teams"]:
            t = t["team"]
            out.append({"abbr": t["abbreviation"], "name": t["name"], "full": t["displayName"],
                        "color": "#" + t.get("color", "552583"), "logo": t["logos"][0]["href"],
                        "sub": SUBS.get(t["abbreviation"])})
        return sorted(out, key=lambda x: x["full"])
    return safe(lambda: cached("teams", 86400, go))

@app.route("/api/scores")
def scores():
    def go():
        d = fetch(f"{ESPN}/scoreboard").json()
        games = []
        for e in d.get("events", []):
            c = e["competitions"][0]
            teams = {x["homeAway"]: x for x in c["competitors"]}
            games.append({"status": e["status"]["type"]["shortDetail"], "state": e["status"]["type"]["state"],
                          "home": {"abbr": teams["home"]["team"]["abbreviation"], "logo": teams["home"]["team"].get("logo"), "score": teams["home"].get("score", "0")},
                          "away": {"abbr": teams["away"]["team"]["abbreviation"], "logo": teams["away"]["team"].get("logo"), "score": teams["away"].get("score", "0")}})
        return games
    return safe(lambda: cached("scores", 20, go))

@app.route("/api/news")
def news():
    team = request.args.get("team", "Los Angeles Lakers")
    def go():
        url = "https://news.google.com/rss/search"
        root = ET.fromstring(fetch(url, params={"q": f"{team} NBA when:3d", "hl": "en-US", "gl": "US", "ceid": "US:en"}).content)
        return [{"title": i.findtext("title"), "link": i.findtext("link"),
                 "date": i.findtext("pubDate"), "source": i.findtext("source")}
                for i in root.iter("item")][:20]
    return safe(lambda: cached(f"news:{team}", 120, go))

@app.route("/api/fans")
def fans():
    sub = request.args.get("sub", "lakers")
    def go():
        posts = reddit(f"/r/{sub}/hot", limit=25)["data"]["children"]
        posts = [p["data"] for p in posts if not p["data"].get("stickied")][:15]
        out = [{"id": p["id"], "title": p["title"], "score": p["score"], "comments": p["num_comments"],
                "flair": p.get("link_flair_text"), "url": "https://reddit.com" + p["permalink"], "top_comment": None}
               for p in posts]
        for o in out[:3]:  # grab the top fan reaction on the hottest threads
            try:
                c = reddit(f"/comments/{o['id']}", limit=3, sort="top")
                kids = [k["data"] for k in c[1]["data"]["children"] if k["kind"] == "t1"]
                if kids:
                    o["top_comment"] = {"body": kids[0]["body"][:280], "score": kids[0]["score"]}
            except Exception:
                pass
        return out
    return safe(lambda: cached(f"fans:{sub}", 90, go))

@app.route("/api/memes")
def memes():
    q = request.args.get("team", "Lakers")
    def go():
        posts = reddit("/r/nbamemes/search", q=q, restrict_sr=1, sort="new", t="week", limit=50)["data"]["children"]
        out = []
        for p in posts:
            p = p["data"]
            if p.get("post_hint") == "image" or p["url"].lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                out.append({"title": p["title"], "img": p["url"], "score": p["score"], "link": "https://reddit.com" + p["permalink"]})
        return sorted(out, key=lambda x: -x["score"])[:18]
    return safe(lambda: cached(f"memes:{q}", 180, go))

@app.route("/api/buzz")
def buzz():
    team = request.args.get("team", "Los Angeles Lakers")
    def go():
        def search(days):  # quoted full name: "Heat" or "Kings" alone pulls in non-NBA posts
            since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - days * 86400))
            return fetch("https://api.bsky.app/xrpc/app.bsky.feed.searchPosts",
                         params={"q": f'"{team}"', "lang": "en", "sort": "top", "since": since, "limit": 100}).json()["posts"]
        posts = search(1)
        if len(posts) < 10:  # quiet day for this team: widen to 3 days
            posts = search(3)
        out = []
        for p in posts:
            a = p["author"]
            # skip authors who asked not to be shown to logged-out viewers
            if any(l.get("val") == "!no-unauthenticated" for l in a.get("labels", []) + p.get("labels", [])):
                continue
            e = p.get("embed") or {}
            e = e.get("media", e)  # images attached to a quote post sit under "media"
            out.append({"text": p["record"].get("text", ""), "date": p["record"].get("createdAt"),
                        "author": a.get("displayName") or a["handle"], "handle": a["handle"], "avatar": a.get("avatar"),
                        "likes": p.get("likeCount", 0), "reposts": p.get("repostCount", 0), "replies": p.get("replyCount", 0),
                        "images": [{"thumb": i["thumb"], "full": i["fullsize"], "alt": i.get("alt", "")} for i in e.get("images", [])],
                        "url": f"https://bsky.app/profile/{a['handle']}/post/{p['uri'].rsplit('/', 1)[-1]}"})
        return sorted(out, key=lambda x: -(x["likes"] + 2 * x["reposts"]))[:25]
    return safe(lambda: cached(f"buzz:{team}", 120, go))

@app.route("/api/stats")
def stats():
    abbr = request.args.get("abbr", "LAL")
    def go():
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        g = conn.execute("""SELECT g.id, g.matchup, g.game_date, g.wl, g.points FROM games g
            JOIN player_stats ps ON ps.game_id = g.id JOIN teams t ON t.id = ps.team_id
            WHERE t.abbreviation = ? ORDER BY g.game_date DESC LIMIT 1""", (abbr,)).fetchone()
        if not g:
            conn.close()
            return {"game": None, "players": []}
        rows = conn.execute("""SELECT player_name, minutes, points, rebounds, assists, plus_minus
            FROM player_stats WHERE game_id = ? ORDER BY points DESC""", (g["id"],)).fetchall()
        conn.close()
        return {"game": dict(g), "players": [dict(r) for r in rows]}
    return safe(go)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
