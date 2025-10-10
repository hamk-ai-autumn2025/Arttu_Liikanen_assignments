from flask import Flask, request, redirect, url_for, render_template_string
import datetime
import os
import re
import requests
from markupsafe import Markup, escape
from openai import OpenAI

app = Flask(__name__)

# Configuration via environment variables
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Initialize OpenAI client compatible with openai>=1.0.0
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else OpenAI()

# Helper to compute "from" date based on user selection
def compute_from_date(period):
    now = datetime.datetime.now(datetime.timezone.utc)
    if period == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "last_week":
        return now - datetime.timedelta(weeks=1)
    if period == "last_month":
        return now - datetime.timedelta(days=30)
    if period == "last_year":
        return now - datetime.timedelta(days=365)
    return now - datetime.timedelta(weeks=1)

# Fetch news using GNews API (https://gnews.io/)
def fetch_news_gnews(query, from_date, to_date, max_results=12):
    if not GNEWS_API_KEY:
        return [], "GNEWS_API_KEY environment variable not set"
    url = "https://gnews.io/api/v4/search"
    params = {
        "q": query,
        "token": GNEWS_API_KEY,
        "lang": "en",
        "max": max_results,
        # GNews expects dates in YYYY-MM-DD format
        "from": from_date.strftime("%Y-%m-%d"),
        "to": to_date.strftime("%Y-%m-%d"),
    }
    headers = {"User-Agent": "news-summarizer/1.0"}
    try:
        resp = requests.get(url, params=params, timeout=10, headers=headers)
    except Exception as e:
        return [], f"request error: {e}"
    if resp.status_code != 200:
        try:
            data = resp.json()
            msg = data.get("message") or resp.text
        except Exception:
            msg = resp.text
        return [], f"gnews error {resp.status_code}: {msg}"
    try:
        data = resp.json()
        raw_articles = data.get("articles", [])
        articles = []
        for a in raw_articles:
            published = a.get("publishedAt")
            # Friendly published string
            try:
                # publishedAt typically like "2020-01-01T12:34:56Z"
                published_dt = datetime.datetime.fromisoformat(published.replace("Z", "+00:00"))
                published_str = published_dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            except Exception:
                published_str = published or ""
            articles.append({
                "title": a.get("title") or "",
                "url": a.get("url") or "#",
                "publishedAt": published_str,
                "description": a.get("description") or "",
                "source": a.get("source", {}).get("name", "")
            })
        return articles, None
    except Exception as e:
        return [], f"parsing error: {e}"

# Build a concise prompt for the OpenAI summarizer using top articles
def build_prompt(query, from_date, to_date, articles):
    from_str = from_date.strftime("%Y-%m-%d")
    to_str = to_date.strftime("%Y-%m-%d")
    lines = [f"Summarize the latest news about '{query}' between {from_str} and {to_str}."]
    lines.append("Provide a short (around 3-6 sentences) neutral summary, a short list of key points, and list up to 5 notable headlines with sources and links.")
    lines.append("")
    lines.append("Articles:")
    for a in articles:
        title = a.get("title", "").strip()
        desc = a.get("description", "").strip()
        source = a.get("source", "")
        published = a.get("publishedAt", "")
        url = a.get("url", "")
        # keep each article compact
        lines.append(f"- {title} ({source}, {published})\n  {desc}\n  {url}")
    lines.append("")
    lines.append("Do not invent facts; if information is missing, do not guess. Keep the tone informative and concise.")
    return "\n".join(lines)

def summarize_with_openai(prompt):
    if not OPENAI_API_KEY:
        return None, "OPENAI_API_KEY environment variable not set"
    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a concise news summarizer. Don't include markdown in your response"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=400,
        )
        # Try attribute-style extraction first (new OpenAI client returns objects)
        content = None
        try:
            choice = resp.choices[0]
            msg = getattr(choice, "message", None)
            if msg is not None:
                content = getattr(msg, "content", None)
        except Exception:
            content = None

        # Fallback to dict-style access if needed
        if content is None:
            try:
                content = resp["choices"][0]["message"]["content"]
            except Exception:
                content = str(resp)

        # Normalize possible content shapes (string, list, dict)
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict):
                content = first.get("content") or first.get("text") or ""
            else:
                content = str(first)
        if isinstance(content, dict):
            content = content.get("content") or content.get("text") or ""

        summary = (content or "").strip()
        return summary, None
    except Exception as e:
        return None, f"openai error: {e}"

def format_summary_to_html(text):
    """
    Lightweight renderer: escapes HTML, converts markdown links [text](url) into anchors,
    auto-linkifies plain URLs, converts '- ' bullet lines into <ul><li> and paragraphs.
    Returns a Markup-safe HTML string.
    """
    if not text:
        return Markup("")
    s = escape(text)

    # Convert markdown links: [text](url)
    s = re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)

    # Auto-link plain URLs (that aren't already inside href)
    s = re.sub(r'(?<!href=")(https?://[^\s<]+)', r'<a href="\1" target="_blank" rel="noopener">\1</a>', s)

    # Build HTML paragraphs and lists
    lines = s.splitlines()
    out = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            item = stripped[2:].strip()
            out.append(f"<li>{item}</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            if stripped == "":
                out.append("")  # skip extra empty lines (we'll let CSS manage spacing)
            else:
                out.append(f"<p>{stripped}</p>")
    if in_list:
        out.append("</ul>")
    html = "".join(out)
    # If the renderer produced nothing but raw text (no tags), wrap with a paragraph
    if not re.search(r'<(p|ul|li|a)', html):
        html = f"<p>{s}</p>"
    return Markup(html)

INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>News Search & Summary</title>
<style>
  :root{
    --bg:#f5f7fb; --card:#ffffff; --muted:#6b7280; --accent:#0f62fe;
    --shadow: 0 6px 18px rgba(15,22,39,0.08);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial;
  }
  body{margin:0;background:var(--bg);color:#0b1117;line-height:1.4}
  .container{max-width:980px;margin:32px auto;padding:20px}
  header{display:flex;align-items:center;gap:16px;margin-bottom:18px}
  h1{margin:0;font-size:20px}
  .lead{color:var(--muted);font-size:13px}
  form.search{display:flex;gap:12px;align-items:center;background:var(--card);padding:14px;border-radius:10px;box-shadow:var(--shadow)}
  .field{flex:1;display:flex;flex-direction:column}
  label{font-size:13px;color:var(--muted);margin-bottom:6px}
  input[type="text"], select{padding:10px 12px;border:1px solid #e6e9ef;border-radius:8px;font-size:15px}
  button{background:var(--accent);color:white;border:none;padding:10px 14px;border-radius:8px;cursor:pointer;font-weight:600}
  button:hover{filter:brightness(.95)}
  .grid{display:grid;grid-template-columns:1fr 340px;gap:18px;margin-top:18px}
  @media (max-width:900px){.grid{grid-template-columns:1fr}}
  .panel{background:var(--card);padding:16px;border-radius:10px;box-shadow:var(--shadow)}
  .summary{
    font-size:14px;
    color:#0b1117;
    line-height:1.6;
  }
  .summary p{margin:8px 0}
  .summary ul{margin:8px 0 8px 20px}
  .summary a{
    color:var(--accent);
    text-decoration:underline;
    font-weight:600;
  }
  .articles{display:flex;flex-direction:column;gap:12px;margin-top:10px}
  .article{display:flex;flex-direction:column;padding:12px;border-radius:9px;border:1px solid #eef2f7;background:linear-gradient(180deg,rgba(255,255,255,0.9),rgba(250,252,255,0.9))}
  .article a.title{font-weight:700;color:#0b2f6b;text-decoration:none}
  .meta{font-size:12px;color:var(--muted);margin-top:6px}
  .desc{margin-top:8px;color:#263240;font-size:13px}
  footer{margin-top:20px;text-align:center;color:var(--muted);font-size:13px}
  .error{color:#b91c1c;background:#fff1f2;padding:10px;border-radius:8px;margin-top:12px}
  .loading{display:inline-block;margin-left:10px;font-size:13px;color:var(--muted)}
</style>
</head>
<body>
<div class="container">
  <header>
    <div>
      <h1>News Search & Summary</h1>
      <div class="lead">Enter a topic to fetch recent articles and get a concise summary.</div>
    </div>
  </header>

  <form class="search" action="{{ url_for('search') }}" method="post" onsubmit="showLoading()">
    <div class="field" style="flex:2">
      <label for="q">Search term or category</label>
      <input id="q" name="q" required value="{{ q }}" type="text" placeholder="e.g. climate change, Apple, Mars mission">
    </div>
    <div style="width:180px">
      <label for="period">Time period</label>
      <select id="period" name="period">
        <option value="today" {% if period=='today' %}selected{% endif %}>Today</option>
        <option value="last_week" {% if period=='last_week' %}selected{% endif %}>Last week</option>
        <option value="last_month" {% if period=='last_month' %}selected{% endif %}>Last month</option>
        <option value="last_year" {% if period=='last_year' %}selected{% endif %}>Last year</option>
      </select>
    </div>
    <div style="display:flex;flex-direction:column;gap:8px;justify-content:center">
      <button type="submit">Search & Summarize</button>
      <div id="loading" class="loading" style="display:none">Searching... Please wait</div>
    </div>
  </form>

  {% if error %}
    <div class="error panel">{{ error }}</div>
  {% endif %}

  <div class="grid">
    <div>
      {% if summary %}
      <div class="panel">
        <h3 style="margin:0 0 8px 0">Summary</h3>
        <div class="summary">{{ summary }}</div>
      </div>
      {% endif %}
      {% if articles %}
      <div class="panel" style="margin-top:12px">
        <h4 style="margin:0 0 10px 0">Top articles</h4>
        <div class="articles">
          {% for a in articles %}
            <article class="article">
              <a class="title" href="{{ a.url }}" target="_blank" rel="noopener">{{ a.title }}</a>
              <div class="meta">{{ a.publishedAt }} — {{ a.source }}</div>
              {% if a.description %}
                <div class="desc">{{ a.description }}</div>
              {% endif %}
            </article>
          {% endfor %}
        </div>
      </div>
      {% endif %}
    </div>

    <aside class="panel">
      <h4 style="margin-top:0">About</h4>
      <p class="lead" style="margin-top:6px">This tool fetches recent news and asks the model to produce a short neutral summary and key points. Data comes from GNews and a summarizer model.</p>
      <hr>
      <h5 style="margin:8px 0 6px 0">Tips</h5>
      <ul style="padding-left:18px;margin:0;color:var(--muted);font-size:14px">
        <li>Try company names, events, or topics.</li>
        <li>Use "last week" or "last month" for broader results.</li>
        <li>Click headlines to open original sources.</li>
      </ul>
    </aside>
  </div>

  <footer>
    <div>Built with GNews & OpenAI</div>
  </footer>
</div>

<script>
function showLoading(){
  var btn = document.getElementById('loading');
  if(btn) btn.style.display = 'inline-block';
}
</script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(INDEX_HTML, q="", period="last_week", summary=None, articles=None, error=None)

@app.route("/search", methods=["POST"])
def search():
    q = request.form.get("q", "").strip()
    period = request.form.get("period", "last_week")
    if not q:
        return redirect(url_for("index"))
    from_dt = compute_from_date(period)
    to_dt = datetime.datetime.now(datetime.timezone.utc)

    articles, err = fetch_news_gnews(q, from_dt, to_dt, max_results=15)
    if err:
        return render_template_string(INDEX_HTML, q=q, period=period, summary=None, articles=None, error=err)
    if not articles:
        return render_template_string(INDEX_HTML, q=q, period=period, summary=None, articles=None, error="No articles found for the query and period.")

    top_articles = articles[:10]
    prompt = build_prompt(q, from_dt, to_dt, top_articles)
    summary_text, err2 = summarize_with_openai(prompt)
    if err2:
        return render_template_string(INDEX_HTML, q=q, period=period, summary=None, articles=top_articles, error=err2)

    # Format the summary into safe HTML (convert markdown links, plain URLs, bullets, paragraphs)
    summary_html = format_summary_to_html(summary_text)

    return render_template_string(INDEX_HTML, q=q, period=period, summary=summary_html, articles=top_articles, error=None)

if __name__ == "__main__":
    # Run with: export GNEWS_API_KEY=... && export OPENAI_API_KEY=... && python assignment14.py
    app.run(host="0.0.0.0", port=5000, debug=True)
