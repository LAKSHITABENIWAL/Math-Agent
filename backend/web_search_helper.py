# backend/web_search_helper.py (improved debug + sanitize)
from dotenv import load_dotenv
import os, time, html, json, re
from tavily import TavilyClient

load_dotenv()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", None)
if not TAVILY_API_KEY:
    raise RuntimeError("TAVILY_API_KEY missing in .env")

client = TavilyClient(api_key=TAVILY_API_KEY)

def _sanitize_query(q: str) -> str:
    # convert curly quotes to straight ones, remove stray unicode characters
    q = q.replace("’", "'").replace("“", '"').replace("”", '"')
    q = re.sub(r"[^\x00-\x7F]+", " ", q)  # remove non-ascii weird characters
    return q.strip()

def search_web(question: str, depth: str = "basic", limit: int = 3, timeout: int = 15):
    q = _sanitize_query(question)
    print(f"[web_search_helper] search_web called — question: {q!r}, depth={depth}, limit={limit}")
    try:
        resp = client.search(
            query=q,
            search_depth=depth,
            max_results=limit,
            include_snippets=True,
        )
    except Exception as e:
        print(f"[web_search_helper] Tavily client.search ERROR: {e}")
        return {"ok": False, "error": str(e), "results": []}

    # debug: print raw response summary (careful: can be large)
    try:
        print("[web_search_helper] RAW_RESP preview:", json.dumps(resp if isinstance(resp, dict) else resp.to_dict(), indent=2)[:2000])
    except Exception:
        print("[web_search_helper] RAW_RESP (could not pretty-print)")

    hits = []
    if isinstance(resp, dict):
        hits = resp.get("hits") or resp.get("results") or []
    else:
        hits = getattr(resp, "hits", None) or getattr(resp, "results", []) or []

    print(f"[web_search_helper] Tavily returned {len(hits)} hits")
    results = []
    for i, hit in enumerate(hits[:limit]):
        title = hit.get("title") or hit.get("url") or ""
        url = hit.get("url") or ""
        snippet = ""
        if "snippet" in hit and hit["snippet"]:
            snippet = hit["snippet"]
        elif "content_snippet" in hit:
            snippet = hit["content_snippet"]
        snippet = html.unescape(snippet).strip()
        score = hit.get("score", None)
        results.append({"title": title, "url": url, "snippet": snippet, "score": score})
        print(f"[web_search_helper] hit {i+1}: title={title!r}, url={url!r}, snippet_len={len(snippet)}, score={score}")

    # If no hits and depth == 'basic', try once with advanced (optional)
    if len(results) == 0 and depth == "basic":
        print("[web_search_helper] No hits returned for basic depth — retrying with advanced depth")
        return search_web(question, depth="advanced", limit=limit, timeout=timeout)

    return {"ok": True, "results": results}
