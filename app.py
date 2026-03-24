import streamlit as st
import feedparser
import pandas as pd
from rapidfuzz import fuzz

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(page_title="Starlink Gaming Intelligence", layout="wide")

FEEDS = {
    # CORE
    "PC Gamer": "https://www.pcgamer.com/rss/",
    "IGN": "https://feeds.ign.com/ign/games-all",
    "GameSpot": "https://www.gamespot.com/feeds/news/",
    "Polygon": "https://www.polygon.com/rss/index.xml",
    "Kotaku": "https://kotaku.com/rss",
    "VG247": "https://www.vg247.com/feed",

    # EU / DE
    "Eurogamer": "https://www.eurogamer.net/feed",
    "GameStar": "https://www.gamestar.de/rss/news.xml",
    "GamePro": "https://www.gamepro.de/rss/news.xml",

    # MODERN
    "VGC": "https://www.videogameschronicle.com/feed/",
    "Insider Gaming": "https://insider-gaming.com/feed/",
    "DualShockers": "https://www.dualshockers.com/feed/",

    # TECH
    "TechRadar Gaming": "https://www.techradar.com/rss/gaming",
    "Rock Paper Shotgun": "https://www.rockpapershotgun.com/feed",

    # PLATFORM
    "Steam": "https://store.steampowered.com/feeds/news/collection/steam",
}

# Source Importance
SOURCE_WEIGHTS = {
    "IGN": 3,
    "GameSpot": 3,
    "Polygon": 3,
    "Eurogamer": 3,

    "PC Gamer": 2,
    "VGC": 2,
    "TechRadar Gaming": 2,
    "Rock Paper Shotgun": 2,
    "Steam": 2,

    "DualShockers": 1,
    "Insider Gaming": 1,
}

# Keyword Intelligence
KEYWORDS = {
    "high_value": ["acquisition", "merger", "layoffs", "funding"],
    "mid_value": ["release", "launch", "update", "patch"],
    "hype": ["leak", "rumor", "announcement"],
}

# ---------------------------
# STYLE (Starlink)
# ---------------------------
st.markdown("""
<style>
body {
    background-color: #0a0a0a;
    color: #ffffff;
}
h1 {
    color: #00eaff;
}
.card {
    background-color: #111;
    padding: 18px;
    border-radius: 14px;
    margin-bottom: 15px;
    border: 1px solid #1f1f1f;
    transition: 0.3s;
}
.card:hover {
    border: 1px solid #00eaff;
    box-shadow: 0px 0px 15px rgba(0,234,255,0.2);
    transform: scale(1.02);
}
.title {
    font-size: 18px;
    font-weight: bold;
}
.meta {
    font-size: 12px;
    color: #888;
}
a {
    color: #00eaff;
    text-decoration: none;
}
</style>
""", unsafe_allow_html=True)

st.title("🛰️ Starlink Gaming Intelligence Feed")
st.caption("Aggregated • Deduplicated • Smart Ranked")

# ---------------------------
# FETCH
# ---------------------------
@st.cache_data(ttl=600)
def fetch_all():
    articles = []

    for source, url in FEEDS.items():
        feed = feedparser.parse(url)

        for entry in feed.entries[:15]:
            articles.append({
                "source": source,
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", "")
            })

    return pd.DataFrame(articles)

# ---------------------------
# SIMILARITY (FAST)
# ---------------------------
def similarity(a, b):
    return fuzz.token_set_ratio(a, b) / 100

# ---------------------------
# DEDUP
# ---------------------------
def deduplicate(df, threshold=0.8):
    unique = []
    seen = []

    for _, row in df.iterrows():
        duplicate = False

        for s in seen:
            if similarity(row["title"], s) > threshold:
                duplicate = True
                break

        if not duplicate:
            seen.append(row["title"])
            unique.append(row)

    return pd.DataFrame(unique)

# ---------------------------
# CLUSTER
# ---------------------------
def cluster(df, threshold=0.75):
    clusters = []

    for _, row in df.iterrows():
        placed = False

        for c in clusters:
            if similarity(row["title"], c[0]["title"]) > threshold:
                c.append(row)
                placed = True
                break

        if not placed:
            clusters.append([row])

    return clusters

# ---------------------------
# KEYWORD SCORE
# ---------------------------
def keyword_score(text):
    text = text.lower()
    score = 0

    for word in KEYWORDS["high_value"]:
        if word in text:
            score += 5

    for word in KEYWORDS["mid_value"]:
        if word in text:
            score += 3

    for word in KEYWORDS["hype"]:
        if word in text:
            score += 2

    return score

# ---------------------------
# SMART SCORE
# ---------------------------
def smart_score(cluster):
    source_score = 0
    keyword_total = 0

    for article in cluster:
        source_score += SOURCE_WEIGHTS.get(article["source"], 1)
        keyword_total += keyword_score(article["title"])

    coverage = len(cluster)

    return coverage * 2 + source_score + keyword_total

# ---------------------------
# RANK
# ---------------------------
def rank(clusters):
    results = []

    for c in clusters:
        results.append({
            "title": c[0]["title"],
            "sources": list(set([a["source"] for a in c])),
            "links": [a["link"] for a in c],
            "summary": c[0]["summary"],
            "score": smart_score(c),
            "count": len(c)
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)

# ---------------------------
# PIPELINE
# ---------------------------
df = fetch_all()
df = deduplicate(df)
clusters = cluster(df)
ranked = rank(clusters)

# ---------------------------
# UI CONTROLS
# ---------------------------
col1, col2 = st.columns([1,1])

with col1:
    min_sources = st.slider("Signal Strength (min sources)", 1, 5, 1)

with col2:
    limit = st.slider("Max Stories", 5, 30, 15)

# ---------------------------
# DISPLAY
# ---------------------------
cols = st.columns(3)

i = 0
for item in ranked:
    if item["count"] < min_sources:
        continue

    if i >= limit:
        break

    with cols[i % 3]:
        st.markdown(f"""
        <div class="card">
            <div class="title">{item['title']}</div>
            <div class="meta">
                Sources: {", ".join(item['sources'])}<br>
                Coverage: {item['count']} • Score: {round(item['score'],2)}
            </div>
            <p>{item['summary'][:140]}...</p>
            <a href="{item['links'][0]}" target="_blank">Read more →</a>
        </div>
        """, unsafe_allow_html=True)

    i += 1

# ---------------------------
# VISION SECTION
# ---------------------------
st.markdown("---")

st.markdown("""
## 🚀 Our Vision

**Starlink Gaming Intelligence** aims to become the decision-making layer for the global gaming industry.

In a world overwhelmed by fragmented information, we transform noise into structured, high-signal intelligence.

We believe that:
- Information advantage defines market leaders  
- Speed and clarity outperform volume  
- Aggregation alone is not enough — intelligence is the differentiator  

Our platform continuously analyzes thousands of signals across media, platforms, and insider channels to identify what truly matters.

**From news → to insight → to action.**

This is not just a feed.  
This is the foundation of a real-time gaming intelligence system.
""")

# ---------------------------
# FOOTER
# ---------------------------
st.markdown("""
<style>
.footer {
    margin-top: 50px;
    padding: 20px;
    text-align: center;
    font-size: 12px;
    color: #777;
    border-top: 1px solid #1f1f1f;
}
.footer a {
    color: #00eaff;
    margin: 0 10px;
}
</style>

<div class="footer">
    <div><strong>Starlink Gaming Intelligence</strong></div>
    <div>Real-time signal detection for the gaming industry</div>
    <br>
    <div>
        <a href="#">About</a> •
        <a href="#">Contact</a> •
        <a href="#">Privacy</a> •
        <a href="#">Terms</a>
    </div>
    <br>
    <div>© 2026 Starlink Intelligence • Built with Streamlit</div>
</div>
""", unsafe_allow_html=True)
