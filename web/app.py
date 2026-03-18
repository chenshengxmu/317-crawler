"""
Flask 新闻搜索前端
代理 FastAPI 后端，提供用户友好的搜索界面
"""

import requests
from flask import Flask, render_template, request, jsonify, abort

app = Flask(__name__)

API_BASE = "http://localhost:8000/api/v1"


def api_post(path, payload):
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def api_get(path, params=None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


@app.route("/")
def index():
    """首页 — 展示搜索框和热门话题。"""
    stats = api_get("/stats/sources")
    categories = api_get("/stats/categories")
    return render_template("index.html", stats=stats, categories=categories)


@app.route("/search")
def search():
    """搜索结果页。"""
    query = request.args.get("q", "").strip()
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("size", 10))
    sort_by = request.args.get("sort", "relevance")
    date_from = request.args.get("from", "")
    date_to = request.args.get("to", "")
    sources = request.args.getlist("source")
    categories = request.args.getlist("cat")

    if not query:
        return render_template("index.html",
                               stats=api_get("/stats/sources"),
                               categories=api_get("/stats/categories"))

    payload = {
        "query": query,
        "page": page,
        "page_size": page_size,
        "sort_by": sort_by,
    }
    if date_from:
        payload["date_from"] = date_from
    if date_to:
        payload["date_to"] = date_to
    if sources:
        payload["sources"] = sources
    if categories:
        payload["categories"] = categories

    results = api_post("/search", payload)
    total_pages = max(1, (results.get("total", 0) + page_size - 1) // page_size)

    return render_template(
        "search.html",
        query=query,
        results=results,
        page=page,
        page_size=page_size,
        total_pages=min(total_pages, 100),  # ES default limit
        sort_by=sort_by,
        date_from=date_from,
        date_to=date_to,
        selected_sources=sources,
        selected_cats=categories,
    )


@app.route("/article/<article_id>")
def article(article_id):
    """文章详情页。"""
    doc = api_get(f"/articles/{article_id}")
    if "error" in doc or not doc.get("title"):
        abort(404)
    return render_template("article.html", article=doc)


@app.route("/stats")
def stats():
    """统计页面。"""
    sources = api_get("/stats/sources")
    categories = api_get("/stats/categories")
    trending = api_get("/stats/trending", {"days": 7, "top_k": 20})
    return render_template("stats.html",
                           sources=sources,
                           categories=categories,
                           trending=trending)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
